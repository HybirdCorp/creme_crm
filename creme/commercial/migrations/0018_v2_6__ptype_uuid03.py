from django.db import migrations

from creme.commercial import constants

PROP_IS_A_SALESMAN = 'commercial-is_a_salesman'


def create_salesman_new_ptype(apps, schema_editor):
    old_ptype = apps.get_model('creme_core', 'OldCremePropertyType').objects.filter(
        id=PROP_IS_A_SALESMAN,
    ).first()

    if old_ptype is not None:
        apps.get_model('creme_core', 'CremePropertyType').objects.get_or_create(
            old_id=old_ptype.id,
            defaults={
                'uuid': constants.UUID_PROP_IS_A_SALESMAN,
                'app_label': 'commercial',
                'text': old_ptype.text,
                'is_custom': old_ptype.is_custom,
                'is_copiable': old_ptype.is_copiable,
                'enabled': old_ptype.enabled,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0017_v2_6__ptype_uuid02'),
        ('creme_core', '0132_v2_6__propertytype_uuid03'),
    ]
    run_before = [
        ('creme_core', '0133_v2_6__propertytype_uuid04'),
    ]

    operations = [
        migrations.RunPython(create_salesman_new_ptype),
    ]
