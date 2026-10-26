from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from core.models import Company


def grace_days():
    return settings.SUBSCRIPTION_GRACE_DAYS


# Sistemdeki işlev grupları; paketler bu modüllerden oluşur
class Module(models.Model):
    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=255, blank=True, default='')
    is_core = models.BooleanField(
        default=False,
        help_text='Çekirdek modüller geçerli paketi olan her şirkette açıktır.',
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Modül'
        verbose_name_plural = 'Modüller'

    def __str__(self):
        return self.name


# ankaforge.com üzerinden satılan paketler
class Package(models.Model):
    DEMO_CODE = 'demo'

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True, default='')
    modules = models.ManyToManyField(Module, related_name='packages', blank=True)
    list_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    duration_days = models.PositiveIntegerField(default=365)
    grace_days = models.PositiveSmallIntegerField(
        'Ek süre (gün)',
        null=True,
        blank=True,
        help_text='Bitişten sonra erişimin açık kalacağı gün. Boş bırakılırsa varsayılan ek süre uygulanır; demo için 0.',
    )
    is_active = models.BooleanField(default=True, help_text='Pasif paketler yeni satışta seçilemez.')
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Paket'
        verbose_name_plural = 'Paketler'

    def __str__(self):
        return self.name

    @property
    def effective_grace_days(self):
        return grace_days() if self.grace_days is None else self.grace_days

    def period_end(self, starts_on):
        # Bitiş günü dahildir: 365 günlük paket 01.01'de başlarsa 31.12'de biter
        return starts_on + timedelta(days=self.duration_days - 1)


class SubscriptionQuerySet(models.QuerySet):
    def usable_on(self, day):
        # Başlamış, iptal edilmemiş ve ek süresi bitmemiş abonelikler.
        # Ek süre pakete göre değiştiği için en uzun ek süreyle daraltılıp kalan kontrol Python'da yapılır.
        longest_grace = max(grace_days(), Package.objects.aggregate(longest=models.Max('grace_days'))['longest'] or 0)
        candidates = self.filter(
            is_cancelled=False,
            starts_on__lte=day,
            ends_on__gte=day - timedelta(days=longest_grace),
        ).select_related('package')
        return [subscription for subscription in candidates if subscription.grace_ends_on >= day]

    def ended_before(self, day):
        return self.filter(is_cancelled=False, ends_on__lt=day).select_related('package')


# Şirketin bir paket için ödediği bir dönem; her yenileme yeni kayıttır
class Subscription(models.Model):
    STATE_UPCOMING = 'upcoming'
    STATE_ACTIVE = 'active'
    STATE_GRACE = 'grace'
    STATE_EXPIRED = 'expired'
    STATE_CANCELLED = 'cancelled'
    STATE_LABELS = {
        STATE_UPCOMING: 'Başlamadı',
        STATE_ACTIVE: 'Aktif',
        STATE_GRACE: 'Ek süre',
        STATE_EXPIRED: 'Süresi doldu',
        STATE_CANCELLED: 'İptal',
    }

    PAYMENT_PENDING = 'pending'
    PAYMENT_PAID = 'paid'
    PAYMENT_WAIVED = 'waived'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, 'Ödeme bekleniyor'),
        (PAYMENT_PAID, 'Ödendi'),
        (PAYMENT_WAIVED, 'Ücretsiz / deneme'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('transfer', 'Havale / EFT'),
        ('card', 'Kredi kartı'),
        ('cash', 'Nakit'),
        ('other', 'Diğer'),
    ]

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='subscriptions', verbose_name='Şirket')
    package = models.ForeignKey(Package, on_delete=models.PROTECT, related_name='subscriptions', verbose_name='Paket')
    starts_on = models.DateField('Başlangıç')
    ends_on = models.DateField('Bitiş')
    price = models.DecimalField('Ücret', max_digits=12, decimal_places=2, default=Decimal('0.00'))
    payment_status = models.CharField('Ödeme durumu', max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_PENDING)
    paid_on = models.DateField('Ödeme tarihi', null=True, blank=True)
    payment_method = models.CharField('Ödeme yöntemi', max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, default='')
    payment_reference = models.CharField('Dekont / fatura no', max_length=120, blank=True, default='')
    order_reference = models.CharField('ankaforge.com sipariş no', max_length=120, blank=True, default='')
    renewed_from = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='renewals', verbose_name='Yenilenen abonelik',
    )
    is_cancelled = models.BooleanField('İptal edildi', default=False)
    note = models.TextField('Not', blank=True, default='')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name='Kaydeden')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SubscriptionQuerySet.as_manager()

    class Meta:
        ordering = ['-ends_on', '-id']
        verbose_name = 'Abonelik'
        verbose_name_plural = 'Abonelikler'
        constraints = [
            models.CheckConstraint(condition=models.Q(ends_on__gte=models.F('starts_on')), name='subscription_ends_after_start'),
        ]

    def __str__(self):
        return f'{self.company} - {self.package} ({self.starts_on:%d.%m.%Y} - {self.ends_on:%d.%m.%Y})'

    @property
    def grace_ends_on(self):
        return self.ends_on + timedelta(days=self.package.effective_grace_days)

    def state_on(self, day=None):
        day = day or timezone.localdate()
        if self.is_cancelled:
            return self.STATE_CANCELLED
        if day < self.starts_on:
            return self.STATE_UPCOMING
        if day <= self.ends_on:
            return self.STATE_ACTIVE
        if day <= self.grace_ends_on:
            return self.STATE_GRACE
        return self.STATE_EXPIRED

    @property
    def state(self):
        return self.state_on()

    @property
    def state_label(self):
        return self.STATE_LABELS[self.state]

    def days_until_end(self, day=None):
        day = day or timezone.localdate()
        return (self.ends_on - day).days

    @classmethod
    def next_period_start(cls, company, package, day=None):
        # Süresi dolmamış dönem varsa yenileme onun bitişine eklenir, yoksa bugünden başlar
        day = day or timezone.localdate()
        latest = (
            cls.objects.filter(company=company, package=package, is_cancelled=False)
            .order_by('-ends_on')
            .first()
        )
        if latest and latest.grace_ends_on >= day:
            return latest.ends_on + timedelta(days=1), latest
        return day, latest
