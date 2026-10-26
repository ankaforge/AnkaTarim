from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from subscriptions.models import Subscription


class Command(BaseCommand):
    help = 'Bitişi yaklaşan, ek süredeki ve yeni kapanan abonelikleri listeler (günlük cron için).'

    def handle(self, *args, **options):
        # Erişim kararı tarih üzerinden anlık verildiği için bu komut kayıt değiştirmez, sadece raporlar
        today = timezone.localdate()
        live = Subscription.objects.filter(is_cancelled=False).select_related('company', 'package').order_by('ends_on')
        # Aynı paketin sonraki dönemi alınmışsa eski dönem için uyarı gerekmez
        renewed_ids = set(live.exclude(renewed_from=None).values_list('renewed_from_id', flat=True))
        # Ek süre pakete göre değişir (demo paketinde 0)
        ended = list(Subscription.objects.ended_before(today).select_related('company'))

        sections = [
            (
                f'{settings.SUBSCRIPTION_WARNING_DAYS} gün içinde bitecek',
                live.filter(ends_on__gte=today, ends_on__lte=today + timedelta(days=settings.SUBSCRIPTION_WARNING_DAYS)),
            ),
            ('Ek sürede', [item for item in ended if item.grace_ends_on >= today]),
            ('Erişimi bugün kapandı', [item for item in ended if item.grace_ends_on == today - timedelta(days=1)]),
        ]
        for title, queryset in sections:
            rows = [item for item in queryset if item.pk not in renewed_ids]
            self.stdout.write(self.style.MIGRATE_HEADING(f'{title}: {len(rows)}'))
            for item in rows:
                self.stdout.write(
                    f'  {item.company.name} | {item.package.name} | bitiş {item.ends_on:%d.%m.%Y} | '
                    f'tel {item.company.phone or "-"} | {item.get_payment_status_display()}'
                )
