from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token

from core.models import AppUserProfile, Company, Customer

from .access import get_company_access
from .models import Package, Subscription
from .services import renew_subscription
from .testing import grant_package


def days_ago(days):
    return timezone.localdate() - timedelta(days=days)


@override_settings(SUBSCRIPTION_GRACE_DAYS=10)
class SubscriptionTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Sazak Zeytin', slug='sazak-zeytin')
        self.user = User.objects.create_user(username='sazak-admin', password='test-pass')
        AppUserProfile.objects.create(
            user=self.user,
            company=self.company,
            can_manage_users=True,
            can_manage_purchases=True,
            can_manage_sales=True,
        )
        self.auth = {'HTTP_AUTHORIZATION': f'Token {Token.objects.create(user=self.user).key}'}

    def login(self):
        return self.client.post('/api/login/', {'username': 'sazak-admin', 'password': 'test-pass'}, content_type='application/json')

    def grant_ended(self, days_since_end, code='full'):
        ends_on = days_ago(days_since_end)
        return grant_package(self.company, code=code, starts_on=ends_on - timedelta(days=364), ends_on=ends_on)


class SeedDataTest(TestCase):
    def test_packages_are_seeded_with_modules(self):
        modules = {package.code: set(package.modules.values_list('code', flat=True)) for package in Package.objects.all()}
        self.assertEqual(modules['zeytin'], {'olive'})
        self.assertEqual(modules['meysu'], {'meysu'})
        self.assertEqual(modules['full'], {'olive', 'olive_oil', 'fruit', 'meysu'})
        self.assertEqual(modules['demo'], modules['full'])

    def test_demo_package_lasts_ten_days_without_grace(self):
        demo = Package.objects.get(code='demo')

        self.assertEqual(demo.duration_days, 10)
        self.assertEqual(demo.effective_grace_days, 0)

    def test_no_subscription_is_created_for_existing_companies(self):
        self.assertFalse(Subscription.objects.exists())


class CompanyAccessStateTest(SubscriptionTestCase):
    def test_company_without_subscription_cannot_log_in(self):
        response = self.login()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'company_expired')

    def test_active_subscription_logs_in_with_access_details(self):
        grant_package(self.company, code='zeytin')

        response = self.login()

        self.assertEqual(response.status_code, 200)
        access = response.json()['access']
        self.assertEqual(access['state'], 'active')
        self.assertIn('olive', access['modules'])
        self.assertIn('users', access['modules'])
        self.assertNotIn('meysu', access['modules'])

    def test_access_stays_open_during_ten_day_grace_period(self):
        self.grant_ended(days_since_end=10)

        response = self.login()

        self.assertEqual(response.status_code, 200)
        access = response.json()['access']
        self.assertEqual(access['state'], 'grace')
        self.assertEqual(access['days_left'], 0)
        self.assertEqual(self.client.get('/api/customers/', **self.auth).status_code, 200)

    def test_access_closes_after_grace_period_and_reopens_after_renewal(self):
        subscription = self.grant_ended(days_since_end=11)
        Customer.objects.create(company=self.company, full_name='Ahmet Çiftçi')

        login_response = self.login()
        api_response = self.client.get('/api/customers/', **self.auth)
        self.assertEqual(login_response.status_code, 403)
        self.assertEqual(login_response.json()['code'], 'company_expired')
        self.assertEqual(api_response.status_code, 403)
        self.assertEqual(api_response.json()['code'], 'company_expired')

        renewed = renew_subscription(self.company, subscription.package, payment_status=Subscription.PAYMENT_PAID)

        self.assertEqual(renewed.starts_on, timezone.localdate())
        self.assertEqual(renewed.renewed_from, subscription)
        response = self.client.get('/api/customers/', **self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['full_name'] for item in response.json()], ['Ahmet Çiftçi'])

    def test_frozen_company_is_blocked_even_with_valid_subscription(self):
        grant_package(self.company)
        self.company.is_active = False
        self.company.save()

        response = self.client.get('/api/customers/', **self.auth)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'company_frozen')

    def test_demo_is_open_on_its_last_day(self):
        grant_package(self.company, code='demo', starts_on=days_ago(9))

        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['access']['state'], 'active')
        self.assertEqual(response.json()['access']['days_left'], 0)

    def test_demo_closes_the_day_after_it_ends_without_grace(self):
        grant_package(self.company, code='demo', starts_on=days_ago(10))

        response = self.login()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'company_expired')

    def test_cancelled_and_future_subscriptions_do_not_grant_access(self):
        grant_package(self.company, is_cancelled=True)
        grant_package(self.company, starts_on=timezone.localdate() + timedelta(days=5))

        self.assertEqual(get_company_access(self.company).state, 'expired')

    def test_me_endpoint_returns_user_and_access(self):
        grant_package(self.company)

        response = self.client.get('/api/me/', **self.auth)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['username'], 'sazak-admin')
        self.assertEqual(response.json()['access']['state'], 'active')

    def test_superuser_without_company_is_not_affected(self):
        User.objects.create_superuser(username='root', password='test-pass')

        response = self.client.post('/api/login/', {'username': 'root', 'password': 'test-pass'}, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['access'])


class PackageModuleAccessTest(SubscriptionTestCase):
    def test_module_outside_package_is_rejected_but_core_modules_work(self):
        grant_package(self.company, code='meyve')

        purchase_response = self.client.get('/api/customers/', **self.auth)
        driver_response = self.client.get('/api/drivers/', **self.auth)
        users_response = self.client.get('/api/users/', **self.auth)

        self.assertEqual(purchase_response.status_code, 403)
        self.assertEqual(purchase_response.json()['code'], 'module_not_in_package')
        self.assertEqual(driver_response.status_code, 200)
        self.assertEqual(users_response.status_code, 200)

    def test_package_added_mid_year_keeps_its_own_dates(self):
        grant_package(self.company, code='zeytin', starts_on=days_ago(200))
        grant_package(self.company, code='meyve', starts_on=days_ago(10))

        access = get_company_access(self.company)

        self.assertTrue({'olive', 'fruit'} <= access.modules)
        ends = {package['code']: package['ends_on'] for package in access.packages}
        self.assertEqual(ends['zeytin'], (days_ago(200) + timedelta(days=364)).isoformat())
        self.assertEqual(ends['meyve'], (days_ago(10) + timedelta(days=364)).isoformat())
        self.assertEqual(access.days_left, 164)

    def test_only_expired_package_modules_close(self):
        self.grant_ended(days_since_end=11, code='zeytin')
        grant_package(self.company, code='meyve')

        login_response = self.login()
        purchase_response = self.client.get('/api/customers/', **self.auth)

        self.assertEqual(login_response.status_code, 200)
        self.assertNotIn('olive', login_response.json()['access']['modules'])
        self.assertEqual(purchase_response.status_code, 403)
        self.assertEqual(purchase_response.json()['code'], 'module_not_in_package')

    def test_package_in_grace_keeps_modules_while_other_package_is_active(self):
        self.grant_ended(days_since_end=3, code='zeytin')
        grant_package(self.company, code='meyve')

        access = get_company_access(self.company)

        self.assertEqual(access.state, 'active')
        self.assertIn('olive', access.modules)
        states = {package['code']: package['state'] for package in access.packages}
        self.assertEqual(states['zeytin'], 'grace')


class RenewalTest(SubscriptionTestCase):
    def test_early_renewal_starts_after_current_period(self):
        current = grant_package(self.company, code='zeytin')

        renewed = renew_subscription(self.company, current.package)

        self.assertEqual(renewed.starts_on, current.ends_on + timedelta(days=1))
        self.assertEqual(renewed.ends_on, current.ends_on + timedelta(days=365))

    def test_renewal_during_grace_has_no_gap(self):
        current = self.grant_ended(days_since_end=4, code='zeytin')

        renewed = renew_subscription(self.company, current.package)

        self.assertEqual(renewed.starts_on, current.ends_on + timedelta(days=1))
        self.assertEqual(get_company_access(self.company).state, 'active')


# Testlerde collectstatic çalışmadığı için admin sayfaları manifest olmadan render edilir
@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class AdminTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username='ankaforge', password='test-pass')
        self.client.force_login(self.admin_user)

    def test_company_setup_creates_company_subscription_and_general_admin(self):
        response = self.client.post(reverse('admin:core_company_setup'), {
            'name': 'İzorya Zeytinyağı',
            'slug': 'izorya',
            'phone': '05550000000',
            'package': Package.objects.get(code='zeytinyagi').pk,
            'starts_on': timezone.localdate().isoformat(),
            'price': '15000',
            'payment_status': Subscription.PAYMENT_PAID,
            'admin_username': 'izorya-admin',
            'admin_first_name': 'Ayşe',
        })

        self.assertEqual(response.status_code, 200)
        company = Company.objects.get(slug='izorya')
        subscription = company.subscriptions.get()
        self.assertEqual(subscription.package.code, 'zeytinyagi')
        self.assertEqual(subscription.created_by, self.admin_user)
        self.assertIsNotNone(subscription.paid_on)
        profile = AppUserProfile.objects.get(user__username='izorya-admin')
        self.assertEqual(profile.company, company)
        self.assertTrue(profile.can_manage_users)
        password = response.context['result']['password']
        self.assertIn(password, response.context['result']['message'])
        login = self.client.post('/api/login/', {'username': 'izorya-admin', 'password': password}, content_type='application/json')
        self.assertEqual(login.status_code, 200)

    def test_company_setup_with_demo_is_free(self):
        self.client.post(reverse('admin:core_company_setup'), {
            'name': 'Deneme Tarım',
            'package': Package.objects.get(code='demo').pk,
            'starts_on': timezone.localdate().isoformat(),
            'price': '5000',
            'payment_status': Subscription.PAYMENT_PENDING,
            'admin_username': 'deneme-admin',
        })

        subscription = Subscription.objects.get(company__slug='deneme-tarim')
        self.assertEqual(subscription.price, 0)
        self.assertEqual(subscription.payment_status, Subscription.PAYMENT_WAIVED)
        self.assertEqual(subscription.ends_on, timezone.localdate() + timedelta(days=9))

    def test_admin_pages_render(self):
        company = Company.objects.create(name='Sazak', slug='sazak')
        grant_package(company)
        for url in (
            reverse('admin:core_company_changelist'),
            reverse('admin:core_company_change', args=[company.pk]),
            reverse('admin:core_company_setup'),
            reverse('admin:subscriptions_subscription_changelist') + '?durum=expiring',
            reverse('admin:subscriptions_package_changelist'),
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_renew_action_creates_next_period(self):
        company = Company.objects.create(name='Sazak', slug='sazak')
        current = grant_package(company, code='zeytin')

        response = self.client.post(reverse('admin:subscriptions_subscription_changelist'), {
            'action': 'renew_selected',
            '_selected_action': [current.pk],
            'apply': '1',
            'payment_status': Subscription.PAYMENT_PAID,
            'payment_reference': 'DEKONT-1',
        })

        self.assertEqual(response.status_code, 302)
        renewed = company.subscriptions.exclude(pk=current.pk).get()
        self.assertEqual(renewed.renewed_from, current)
        self.assertEqual(renewed.payment_reference, 'DEKONT-1')


class CheckSubscriptionsCommandTest(SubscriptionTestCase):
    def test_lists_expiring_and_grace_subscriptions(self):
        grant_package(self.company, code='zeytin', starts_on=days_ago(360))
        self.grant_ended(days_since_end=2, code='meyve')
        # Dün biten demo ek süreye girmez, bugün kapananlar arasında görünür
        grant_package(self.company, code='demo', starts_on=days_ago(10))

        output = StringIO()
        call_command('check_subscriptions', stdout=output)

        text = output.getvalue()
        self.assertIn('gün içinde bitecek: 1', text)
        self.assertIn('Ek sürede: 1', text)
        self.assertIn('Erişimi bugün kapandı: 1', text)
