from json import loads as json_load

from django.db import migrations

from creme.creme_core.utils.serializers import json_encode


def hide_languages(apps, schema_editor):
    contact_ctype = apps.get_model(
        'contenttypes', 'ContentType',
    ).objects.filter(app_label='persons', model='contact').first()

    if contact_ctype is None:
        return

    if not apps.get_model('persons', 'Contact').objects.exists():
        # Fresh install
        return

    FieldsConfig = apps.get_model('creme_core', 'FieldsConfig')
    fconf = FieldsConfig.objects.filter(content_type=contact_ctype).first()
    new_desc = ('languages', {'hidden': True})

    if fconf is None:
        FieldsConfig.objects.create(
            # NB: <content_type=contact_ctype> does not work (why?)
            content_type_id=contact_ctype.id,
            raw_descriptions=json_encode([new_desc]),
        )
    else:
        descriptions = json_load(fconf.raw_descriptions)
        descriptions.append(new_desc)

        fconf.raw_descriptions = json_encode(descriptions)
        fconf.save()


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0025_v2_2__contact_languages01'),
    ]

    operations = [
        migrations.RunPython(hide_languages),
    ]
