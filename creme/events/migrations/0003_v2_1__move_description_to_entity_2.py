from django.conf import settings
from django.db import migrations
# from django.db.models.expressions import F


def copy_description(apps, schema_editor):
    if settings.EVENTS_EVENT_MODEL == 'events.Event':
        # NB: <F('description_tmp')> does not work, only see the fields of CremeEntity
        # apps.get_model('events', 'Event').objects.update(description=F('description_tmp'))

        for event in apps.get_model('events', 'Event').objects.exclude(description_tmp=''):
            event.description = event.description_tmp
            event.save()


class Migration(migrations.Migration):
    dependencies = [
        ('events',     '0002_v2_1__move_description_to_entity_1'),
        ('creme_core', '0055_v2_1__cremeentity_description'),
    ]

    operations = [
        migrations.RunPython(copy_description),
    ]
