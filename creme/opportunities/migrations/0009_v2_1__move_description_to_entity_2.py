from django.conf import settings
from django.db import migrations
# from django.db.models.expressions import F


def copy_description(apps, schema_editor):
    if settings.OPPORTUNITIES_OPPORTUNITY_MODEL == 'opportunities.Opportunity':
        # NB: <F('description_tmp')> does not work, only see the fields of CremeEntity
        # apps.get_model('opportunities', 'Opportunity').objects.update(description=F('description_tmp'))

        for opp in apps.get_model('opportunities', 'Opportunity').objects.exclude(description_tmp=''):
            opp.description = opp.description_tmp
            opp.save()


class Migration(migrations.Migration):
    dependencies = [
        ('opportunities', '0008_v2_1__move_description_to_entity_1'),
        ('creme_core',    '0055_v2_1__cremeentity_description'),
    ]

    operations = [
        migrations.RunPython(copy_description),
    ]
