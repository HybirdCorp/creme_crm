from django.db import migrations


def fix_default(apps, schema_editor):
    first = apps.get_model('creme_core', 'Currency').objects.order_by('id').first()
    if first is not None:
        first.is_default = True
        first.save()


def fix_uuids(apps, schema_editor):
    Currency = apps.get_model('creme_core', 'Currency')

    def fix_uuid(new_uuid, **kwargs):
        currency = Currency.objects.filter(**kwargs).first()
        if currency is not None:
            old_uuid = str(currency.uuid)
            if old_uuid != new_uuid:
                currency.extra_data['old_uuid'] = old_uuid
                currency.uuid = new_uuid
                currency.save()

    fix_uuid('5777ec02-5b60-4276-9923-c833ba32df22', id=1)
    fix_uuid('97d30dd5-fd4d-4579-9a15-ddda78443bdd', id=2, local_symbol='$')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0167_v2_7__currency_is_default01'),
    ]

    operations = [
        migrations.RunPython(fix_default),
        migrations.RunPython(fix_uuids),
    ]
