from django.conf import settings
from django.db import migrations
# from django.db.models.expressions import F


def copy_description(apps, schema_editor):
    if settings.RECURRENTS_RGENERATOR_MODEL == 'recurrents.RecurrentGenerator':
        # NB: <F('description_tmp')> does not work, only see the fields of CremeEntity
        # apps.get_model('recurrents', 'RecurrentGenerator').objects.update(description=F('description_tmp'))
        for rgen in apps.get_model('recurrents', 'RecurrentGenerator').objects.exclude(description_tmp=''):
            rgen.description = rgen.description_tmp
            rgen.save()


class Migration(migrations.Migration):
    dependencies = [
        ('recurrents', '0006_v2_1__move_description_to_entity_1'),
        ('creme_core', '0055_v2_1__cremeentity_description'),
    ]

    operations = [
        migrations.RunPython(copy_description),
    ]
