import secrets

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from core.models import AppUserProfile, Company

from .models import Subscription

PASSWORD_ALPHABET = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generate_password(length=12):
    return ''.join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


def renew_subscription(company, package, *, created_by=None, price=None, payment_status=Subscription.PAYMENT_PENDING, **extra):
    """Paketi bir dönem uzatır. Dönem bitmeden yenilenirse yeni dönem eskisinin bitişine eklenir."""
    starts_on, previous = Subscription.next_period_start(company, package)
    return Subscription.objects.create(
        company=company,
        package=package,
        starts_on=starts_on,
        ends_on=package.period_end(starts_on),
        price=package.list_price if price is None else price,
        payment_status=payment_status,
        paid_on=timezone.localdate() if payment_status == Subscription.PAYMENT_PAID else None,
        renewed_from=previous,
        created_by=created_by,
        **extra,
    )


@transaction.atomic
def setup_company(*, company_data, package, starts_on, price, payment_status, admin_data, created_by=None):
    """Yeni şirketi, ilk aboneliğini ve şirketin genel admin kullanıcısını tek adımda oluşturur."""
    company = Company.objects.create(**company_data)
    subscription = Subscription.objects.create(
        company=company,
        package=package,
        starts_on=starts_on,
        ends_on=package.period_end(starts_on),
        price=price,
        payment_status=payment_status,
        paid_on=timezone.localdate() if payment_status == Subscription.PAYMENT_PAID else None,
        created_by=created_by,
    )
    password = generate_password()
    user = User.objects.create_user(
        username=admin_data['username'],
        password=password,
        first_name=admin_data.get('first_name', ''),
        last_name=admin_data.get('last_name', ''),
        email=admin_data.get('email', ''),
    )
    AppUserProfile.objects.create(
        user=user,
        company=company,
        can_manage_users=True,
        can_manage_purchases=True,
        can_manage_sales=True,
    )
    return company, subscription, user, password


def welcome_message(company, subscription, user, password, login_url):
    """WhatsApp veya e-posta ile genel admine gönderilecek hazır metin."""
    full_name = user.get_full_name() or user.username
    return '\n'.join([
        f'Merhaba {full_name},',
        '',
        f'{company.name} için Anka Tarım hesabınız oluşturuldu.',
        '',
        f'Paket: {subscription.package.name}',
        f'Geçerlilik: {subscription.starts_on:%d.%m.%Y} - {subscription.ends_on:%d.%m.%Y}',
        '',
        f'Giriş adresi: {login_url}',
        f'Kullanıcı adı: {user.username}',
        f'Geçici şifre: {password}',
        '',
        'Genel admin olarak çalışanlarınızı "Kullanıcılar" bölümünden ekleyebilirsiniz.',
        'İlk girişten sonra şifrenizi değiştirmenizi öneririz.',
        '',
        'AnkaForge',
    ])
