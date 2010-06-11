# -*- coding: utf-8 -*-

from django.contrib import admin

from tickets.models import *


class TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'status', 'closing_date', 'priority', 'criticity', 'solution')


register = admin.site.register

register(Ticket, TicketAdmin)
register(Status)
register(Priority)
register(Criticity)
