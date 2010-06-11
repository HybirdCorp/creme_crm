# -*- coding: utf-8 -*-

from django.contrib import admin

from recurrents.models import *


class RecurrentGeneratorAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'first_generation', 'last_generation',
                    'periodicity', 'ct', 'template', 'is_working')


register = admin.site.register

register(Periodicity)
register(RecurrentGenerator, RecurrentGeneratorAdmin)
