# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def populate_numbers(apps, schema_editor):
    if settings.TICKETS_TICKET_MODEL != 'tickets.Ticket':
        return

    # NB: we create, then delete, TicketNumbers in order to keep the sequence
    get_model = apps.get_model
    TicketNumber = get_model('tickets', 'TicketNumber')
    create_number = TicketNumber.objects.create
    last_number = None

    # (PostgreSQL) correct, in an easy way.
    for ticket in get_model('tickets', 'Ticket').objects.order_by('id'):
        last_number = create_number()
        ticket.number = last_number.id
        ticket.save()

    if last_number:
        TicketNumber.objects.exclude(id=last_number.id).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0002_v1_6__titles_not_unique__add_number'),
    ]

    operations = [
        migrations.RunPython(populate_numbers),
    ]
