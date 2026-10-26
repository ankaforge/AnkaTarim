from datetime import timedelta

from django.utils import timezone

from .models import Package, Subscription


def grant_package(company, code='full', starts_on=None, ends_on=None, **extra):
    """Testlerde şirkete paket tanımlar. Varsayılan: bugün başlayan bir yıllık Full paket."""
    package = Package.objects.get(code=code)
    starts_on = starts_on or timezone.localdate() - timedelta(days=1)
    return Subscription.objects.create(
        company=company,
        package=package,
        starts_on=starts_on,
        ends_on=ends_on or package.period_end(starts_on),
        **extra,
    )
