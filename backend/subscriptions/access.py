from dataclasses import dataclass, field
from datetime import date

from django.conf import settings
from django.utils import timezone

from .models import Module, Subscription


# Şirketin bugünkü erişim durumu; API yetkileri ve arayüz uyarıları buradan beslenir
@dataclass
class CompanyAccess:
    state: str
    modules: frozenset = field(default_factory=frozenset)
    ends_on: date | None = None
    grace_ends_on: date | None = None
    days_left: int | None = None
    packages: tuple = ()

    STATE_ACTIVE = 'active'
    STATE_GRACE = 'grace'
    STATE_EXPIRED = 'expired'
    STATE_FROZEN = 'frozen'

    @property
    def allowed(self):
        return self.state in (self.STATE_ACTIVE, self.STATE_GRACE)

    def has_module(self, code):
        return self.allowed and code in self.modules

    @property
    def message(self):
        if self.state == self.STATE_FROZEN:
            return 'Şirket hesabınız dondurulmuştur. Lütfen AnkaForge ile iletişime geçin.'
        if self.state == self.STATE_EXPIRED:
            return 'Paket süreniz dolmuştur. Hesabınızı yeniden açmak için AnkaForge ile iletişime geçin.'
        if self.state == self.STATE_GRACE:
            return (
                f'Paket süreniz {self.ends_on:%d.%m.%Y} tarihinde doldu. '
                f'{self.grace_ends_on:%d.%m.%Y} tarihine kadar yenilenmezse erişim kapanacaktır.'
            )
        return ''

    def as_dict(self):
        return {
            'state': self.state,
            'allowed': self.allowed,
            'modules': sorted(self.modules),
            'ends_on': self.ends_on.isoformat() if self.ends_on else None,
            'grace_ends_on': self.grace_ends_on.isoformat() if self.grace_ends_on else None,
            'days_left': self.days_left,
            'warning_days': settings.SUBSCRIPTION_WARNING_DAYS,
            'message': self.message,
            'packages': list(self.packages),
        }


def get_company_access(company, day=None):
    day = day or timezone.localdate()
    if not company.is_active:
        return CompanyAccess(state=CompanyAccess.STATE_FROZEN)

    subscriptions = Subscription.objects.filter(company=company).prefetch_related('package__modules').usable_on(day)
    if not subscriptions:
        return CompanyAccess(state=CompanyAccess.STATE_EXPIRED)

    packages = tuple(
        {
            'name': subscription.package.name,
            'code': subscription.package.code,
            'ends_on': subscription.ends_on.isoformat(),
            'state': subscription.state_on(day),
        }
        for subscription in sorted(subscriptions, key=lambda item: item.ends_on)
    )
    # Ek süredeki paketlerin modülleri de 10 gün boyunca açık kalır
    modules = {module.code for module in Module.objects.filter(is_core=True)}
    for subscription in subscriptions:
        modules.update(module.code for module in subscription.package.modules.all())

    in_period = [subscription for subscription in subscriptions if subscription.ends_on >= day]
    if in_period:
        ends_on = min(subscription.ends_on for subscription in in_period)
        return CompanyAccess(
            state=CompanyAccess.STATE_ACTIVE,
            modules=frozenset(modules),
            ends_on=ends_on,
            days_left=(ends_on - day).days,
            packages=packages,
        )

    # Hiçbir paketin dönemi sürmüyor; şirket ek süresinde
    ends_on = max(subscription.ends_on for subscription in subscriptions)
    grace_ends_on = max(subscription.grace_ends_on for subscription in subscriptions)
    return CompanyAccess(
        state=CompanyAccess.STATE_GRACE,
        modules=frozenset(modules),
        ends_on=ends_on,
        grace_ends_on=grace_ends_on,
        days_left=(grace_ends_on - day).days,
        packages=packages,
    )


def get_request_access(request):
    # Aynı istek içinde tekrar hesaplanmasın
    cached = getattr(request, '_company_access', None)
    if cached is not None:
        return cached
    profile = getattr(request.user, 'app_profile', None)
    access = get_company_access(profile.company) if profile else None
    request._company_access = access
    return access
