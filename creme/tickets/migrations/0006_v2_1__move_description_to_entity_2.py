from django.conf import settings
from django.db import migrations
# from django.db.models.expressions import F


def copy_description(apps, schema_editor):
    # NB: <F('description_tmp')> does not work, only see the fields of CremeEntity

    if settings.TICKETS_TICKET_MODEL == 'tickets.Ticket':
        # apps.get_model('tickets', 'Ticket').objects.update(description=F('description_tmp'))
        for ticket in apps.get_model('tickets', 'Ticket').objects.exclude(description_tmp=''):
            ticket.description = ticket.description_tmp
            ticket.save()

    if settings.TICKETS_TEMPLATE_MODEL == 'tickets.TicketTemplate':
        # apps.get_model('tickets', 'TicketTemplate').objects.update(description=F('description_tmp'))
        for ttemplate in apps.get_model('tickets', 'TicketTemplate').objects.exclude(description_tmp=''):
            ttemplate.description = ttemplate.description_tmp
            ttemplate.save()


class Migration(migrations.Migration):
    dependencies = [
        ('tickets',    '0005_v2_1__move_description_to_entity_1'),
        ('creme_core', '0055_v2_1__cremeentity_description'),
    ]

    operations = [
        migrations.RunPython(copy_description),
    ]
