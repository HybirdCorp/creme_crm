# -*- coding: utf-8 -*-

from django.contrib import admin

from opportunities.models import *


class OpportunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'reference', 'estimated_sales', 'made_sales',
                    'sales_phase', 'chance_to_win', 'expiration_date', 'origin')


register = admin.site.register

register(SalesPhase)
register(Origin)
register(Opportunity, OpportunityAdmin)