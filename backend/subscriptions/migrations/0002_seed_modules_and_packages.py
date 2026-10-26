from django.db import migrations


MODULES = [
    # code, ad, açıklama, çekirdek mi
    ('users', 'Kullanıcı yönetimi', 'Şirket kullanıcıları ve yetkileri', True),
    ('parties', 'Cari hesaplar', 'Çiftçi, tüccar ve müşteri kartları', True),
    ('logistics', 'Araç ve şoför', 'Araç, şoför ve sevkiyat kayıtları', True),
    ('reports', 'Raporlar', 'Genel raporlar ve dışa aktarma', True),
    ('olive', 'Zeytin', 'Zeytin alımı, eleme, satış ve sevkiyat', False),
    ('olive_oil', 'Zeytinyağı', 'Yağ sıkımı, makineler, tanklar ve yağ satışı', False),
    ('fruit', 'Meyve', 'Kayısı, erik ve diğer meyvelerin alım satımı', False),
    ('meysu', 'Meysu', 'Meysu kantar, müstahsil ve fabrikaya giden takibi', False),
]

PACKAGES = [
    # code, ad, modüller, süre (gün), ek süre (gün; None = varsayılan)
    ('zeytin', 'Zeytin Paketi', ['olive'], 365, None),
    ('zeytinyagi', 'Zeytinyağı Paketi', ['olive_oil'], 365, None),
    ('meyve', 'Meyve Paketi', ['fruit'], 365, None),
    ('meysu', 'Meysu Paketi', ['meysu'], 365, None),
    ('full', 'Full Paket', ['olive', 'olive_oil', 'fruit', 'meysu'], 365, None),
    # Deneme: tüm modüller açık, bitince ek süre olmadan kapanır
    ('demo', 'Demo (10 gün)', ['olive', 'olive_oil', 'fruit', 'meysu'], 10, 0),
]


def seed(apps, schema_editor):
    Module = apps.get_model('subscriptions', 'Module')
    Package = apps.get_model('subscriptions', 'Package')

    modules = {}
    for order, (code, name, description, is_core) in enumerate(MODULES):
        modules[code], _ = Module.objects.update_or_create(
            code=code,
            defaults={'name': name, 'description': description, 'is_core': is_core, 'sort_order': order},
        )

    for order, (code, name, module_codes, duration_days, grace_days) in enumerate(PACKAGES):
        package, _ = Package.objects.update_or_create(
            code=code,
            defaults={'name': name, 'sort_order': order, 'duration_days': duration_days, 'grace_days': grace_days},
        )
        package.modules.set([modules[module_code] for module_code in module_codes])


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
