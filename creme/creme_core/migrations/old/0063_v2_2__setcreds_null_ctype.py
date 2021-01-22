from django.db import migrations


def convert_ct_id(apps, schema_editor):
    sc_manager = apps.get_model('creme_core', 'SetCredentials').objects

    if not sc_manager.exclude(ctype=None).exists():
        return

    entity_ctype = apps.get_model('contenttypes', 'ContentType')\
                       .objects\
                       .filter(app_label='creme_core', model='cremeentity')\
                       .first()

    if entity_ctype is None:
        return

    sc_manager.filter(ctype_id=entity_ctype.id).update(ctype=None)


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0062_v2_2__trash_cleaning_command'),
    ]

    operations = [
        migrations.RunPython(convert_ct_id),
    ]
