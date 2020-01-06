from django.conf import settings
from django.db import migrations
# from django.db.models.expressions import F


def copy_description(apps, schema_editor):
    # NB: <F('description_tmp')> does not work, only see the fields of CremeEntity
    if settings.PERSONS_CONTACT_MODEL == 'persons.Contact':
        # apps.get_model('persons', 'Contact').objects.update(description=F('description_tmp'))
        for contact in apps.get_model('persons', 'Contact').objects.exclude(description_tmp=''):
            contact.description = contact.description_tmp
            contact.save()

    if settings.PERSONS_ORGANISATION_MODEL == 'persons.Organisation':
        # apps.get_model('persons', 'Organisation').objects.update(description=F('description_tmp'))
        for orga in apps.get_model('persons', 'Organisation').objects.exclude(description_tmp=''):
            orga.description = orga.description_tmp
            orga.save()


class Migration(migrations.Migration):

    dependencies = [
        ('persons', '0023_v2_1__move_description_to_entity_1'),
        ('creme_core', '0055_v2_1__cremeentity_description'),
    ]

    operations = [
        migrations.RunPython(copy_description),
    ]

