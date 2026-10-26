from datetime import timedelta

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.db.models import Max
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from core.admin import CompanyAdmin as BaseCompanyAdmin
from core.models import Company

from .access import get_company_access
from .forms import CompanySetupForm, RenewForm, SubscriptionAdminForm
from .models import Module, Package, Subscription
from .services import renew_subscription, setup_company, welcome_message

STATE_COLORS = {
    'active': '#15803d',
    'grace': '#c2410c',
    'expired': '#b91c1c',
    'frozen': '#475569',
    'upcoming': '#1d4ed8',
    'cancelled': '#64748b',
}

ACCESS_LABELS = {
    'active': 'Aktif',
    'grace': 'Ek süre',
    'expired': 'Süresi doldu',
    'frozen': 'Donduruldu',
}


def state_badge(state, label):
    return format_html(
        '<span style="color:#fff;background:{};padding:2px 8px;border-radius:10px;font-weight:600">{}</span>',
        STATE_COLORS.get(state, '#64748b'),
        label,
    )


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_core', 'sort_order')
    list_editable = ('sort_order',)
    readonly_fields = ('code',)

    def has_delete_permission(self, request, obj=None):
        # Modül kodları yetki kontrollerinde kullanılır
        return False


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'module_list', 'list_price', 'duration_days', 'grace_days', 'is_active')
    list_filter = ('is_active',)
    filter_horizontal = ('modules',)

    @admin.display(description='Modüller')
    def module_list(self, obj):
        return ', '.join(module.name for module in obj.modules.all())

    def has_delete_permission(self, request, obj=None):
        return False


class SubscriptionStateFilter(admin.SimpleListFilter):
    title = 'durum'
    parameter_name = 'durum'

    def lookups(self, request, model_admin):
        return [
            ('active', 'Aktif'),
            ('expiring', f'{settings.SUBSCRIPTION_WARNING_DAYS} gün içinde bitecek'),
            ('grace', 'Ek süredeki'),
            ('expired', 'Süresi dolmuş'),
            ('upcoming', 'Başlamamış'),
            ('cancelled', 'İptal'),
        ]

    def queryset(self, request, queryset):
        today = timezone.localdate()
        live = queryset.filter(is_cancelled=False)
        value = self.value()
        if value == 'active':
            return live.filter(starts_on__lte=today, ends_on__gte=today)
        if value == 'expiring':
            return live.filter(ends_on__gte=today, ends_on__lte=today + timedelta(days=settings.SUBSCRIPTION_WARNING_DAYS))
        if value in ('grace', 'expired'):
            # Ek süre pakete göre değiştiği için durum kayıt bazında hesaplanır
            ended = queryset.ended_before(today)
            in_grace = value == 'grace'
            return queryset.filter(pk__in=[item.pk for item in ended if (item.grace_ends_on >= today) == in_grace])
        if value == 'upcoming':
            return live.filter(starts_on__gt=today)
        if value == 'cancelled':
            return queryset.filter(is_cancelled=True)
        return queryset


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    form = SubscriptionAdminForm
    list_display = ('company', 'package', 'starts_on', 'ends_on', 'state_display', 'days_left_display', 'price', 'payment_status')
    list_filter = (SubscriptionStateFilter, 'payment_status', 'package')
    search_fields = ('company__name', 'payment_reference', 'order_reference')
    autocomplete_fields = ('company',)
    date_hierarchy = 'ends_on'
    readonly_fields = ('renewed_from', 'created_by', 'created_at', 'updated_at')
    actions = ('renew_selected', 'mark_paid', 'cancel_selected')
    fieldsets = (
        (None, {'fields': ('company', 'package', 'starts_on', 'ends_on', 'is_cancelled')}),
        ('Ödeme', {'fields': ('price', 'payment_status', 'paid_on', 'payment_method', 'payment_reference', 'order_reference')}),
        ('Diğer', {'fields': ('note', 'renewed_from', 'created_by', 'created_at', 'updated_at')}),
    )

    @admin.display(description='Durum')
    def state_display(self, obj):
        return state_badge(obj.state, obj.state_label)

    @admin.display(description='Kalan gün', ordering='ends_on')
    def days_left_display(self, obj):
        if obj.is_cancelled:
            return '-'
        days = obj.days_until_end()
        if days >= 0:
            return days
        grace_left = (obj.grace_ends_on - timezone.localdate()).days
        if grace_left >= 0:
            return format_html('<b style="color:#c2410c">ek süre: {} gün</b>', grace_left)
        return format_html('<b style="color:#b91c1c">{} gün önce doldu</b>', -days)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        if obj.payment_status == Subscription.PAYMENT_PAID and not obj.paid_on:
            obj.paid_on = timezone.localdate()
        super().save_model(request, obj, form, change)

    @admin.action(description='Seçilenleri bir dönem yenile')
    def renew_selected(self, request, queryset):
        queryset = queryset.filter(is_cancelled=False).select_related('company', 'package')
        if 'apply' in request.POST:
            form = RenewForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                # Aynı şirket + paket için birden fazla satır seçildiyse tek yenileme yapılır
                pairs = {(item.company, item.package) for item in queryset}
                for company, package in pairs:
                    renew_subscription(
                        company,
                        package,
                        created_by=request.user,
                        price=data['price'],
                        payment_status=data['payment_status'],
                        payment_method=data['payment_method'],
                        payment_reference=data['payment_reference'],
                    )
                self.message_user(request, f'{len(pairs)} abonelik bir dönem uzatıldı.', messages.SUCCESS)
                return None
        else:
            form = RenewForm()
        return TemplateResponse(request, 'admin/subscriptions/renew.html', {
            **self.admin_site.each_context(request),
            'title': 'Abonelik yenile',
            'subscriptions': queryset,
            'form': form,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'opts': self.model._meta,
        })

    @admin.action(description='Ödendi olarak işaretle')
    def mark_paid(self, request, queryset):
        updated = queryset.exclude(payment_status=Subscription.PAYMENT_PAID).update(
            payment_status=Subscription.PAYMENT_PAID,
            paid_on=timezone.localdate(),
        )
        self.message_user(request, f'{updated} abonelik ödendi olarak işaretlendi.', messages.SUCCESS)

    @admin.action(description='İptal et')
    def cancel_selected(self, request, queryset):
        updated = queryset.update(is_cancelled=True)
        self.message_user(request, f'{updated} abonelik iptal edildi.', messages.WARNING)

    def has_delete_permission(self, request, obj=None):
        # Ödeme geçmişi kaybolmasın; silmek yerine iptal edilir
        return False


class SubscriptionInline(admin.TabularInline):
    model = Subscription
    form = SubscriptionAdminForm
    extra = 0
    fields = ('package', 'starts_on', 'ends_on', 'price', 'payment_status', 'is_cancelled', 'state_display')
    readonly_fields = ('state_display',)
    ordering = ('-ends_on',)
    show_change_link = True

    @admin.display(description='Durum')
    def state_display(self, obj):
        if not obj.pk:
            return '-'
        return state_badge(obj.state, obj.state_label)

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.unregister(Company)


@admin.register(Company)
class CompanyAdmin(BaseCompanyAdmin):
    list_display = ('name', 'access_display', 'packages_display', 'last_end_display', 'phone', 'is_active')
    search_fields = ('name', 'slug', 'contact_name', 'phone', 'email', 'tax_number')
    inlines = (SubscriptionInline,)
    actions = ('freeze_selected', 'activate_selected')
    change_list_template = 'admin/subscriptions/company_change_list.html'
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'is_active')}),
        ('İletişim ve fatura', {'fields': ('contact_name', 'phone', 'email', 'tax_number', 'tax_office', 'address')}),
        ('Not', {'fields': ('notes',)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(last_end=Max('subscriptions__ends_on'))

    @admin.display(description='Erişim')
    def access_display(self, obj):
        access = get_company_access(obj)
        return state_badge(access.state, ACCESS_LABELS[access.state])

    @admin.display(description='Paketler')
    def packages_display(self, obj):
        access = get_company_access(obj)
        return ', '.join(package['name'] for package in access.packages) or '-'

    @admin.display(description='Son bitiş', ordering='last_end')
    def last_end_display(self, obj):
        return obj.last_end.strftime('%d.%m.%Y') if obj.last_end else '-'

    def save_formset(self, request, form, formset, change):
        for subscription in formset.save(commit=False):
            if not subscription.pk:
                subscription.created_by = request.user
            if subscription.payment_status == Subscription.PAYMENT_PAID and not subscription.paid_on:
                subscription.paid_on = timezone.localdate()
            subscription.save()
        formset.save_m2m()

    @admin.action(description='Seçili şirketleri dondur')
    def freeze_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} şirket donduruldu. Veriler korunuyor.', messages.WARNING)

    @admin.action(description='Seçili şirketleri yeniden aktifleştir')
    def activate_selected(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} şirket aktifleştirildi. Geçerli paketi olmayan şirketler için abonelik de yenilenmelidir.',
            messages.SUCCESS,
        )

    def get_urls(self):
        return [
            path('kurulum/', self.admin_site.admin_view(self.setup_view), name='core_company_setup'),
        ] + super().get_urls()

    def setup_view(self, request):
        if not self.has_add_permission(request):
            return self.admin_site.login(request)
        result = None
        if request.method == 'POST':
            form = CompanySetupForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                package = data['package']
                company, subscription, user, password = setup_company(
                    company_data=form.company_data(),
                    package=package,
                    starts_on=data['starts_on'],
                    price=package.list_price if data['price'] is None else data['price'],
                    payment_status=data['payment_status'],
                    admin_data=form.admin_data(),
                    created_by=request.user,
                )
                result = {
                    'company': company,
                    'subscription': subscription,
                    'user': user,
                    'password': password,
                    'message': welcome_message(company, subscription, user, password, settings.FRONTEND_URL),
                    'change_url': reverse('admin:core_company_change', args=[company.pk]),
                }
        else:
            form = CompanySetupForm()
        return TemplateResponse(request, 'admin/subscriptions/company_setup.html', {
            **self.admin_site.each_context(request),
            'title': 'Yeni şirket kur',
            'form': form,
            'result': result,
            'opts': self.model._meta,
        })
