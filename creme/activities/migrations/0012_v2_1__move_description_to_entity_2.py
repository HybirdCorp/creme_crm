from django.conf import settings
from django.db import migrations
# from django.db.models.expressions import F


def copy_description(apps, schema_editor):
    if settings.ACTIVITIES_ACTIVITY_MODEL == 'activities.Activity':
        # NB: <F('description_tmp')> does not work, only see the fields of CremeEntity
        # apps.get_model('activities', 'Activity').objects.update(description=F('description_tmp'))

        for activity in apps.get_model('activities', 'Activity').objects.exclude(description_tmp=''):
            activity.description = activity.description_tmp
            activity.save()



class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0011_v2_1__move_description_to_entity_1'),
        ('creme_core', '0055_v2_1__cremeentity_description'),
    ]

    operations = [
        migrations.RunPython(copy_description),
    ]
