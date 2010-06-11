# -*- coding: utf-8 -*-

from django.contrib import admin

from projects.models import *


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'status', 'start_date', 'end_date', 'effective_end_date')


class ResourceAdmin(admin.ModelAdmin):
    list_display = ('linked_contact', 'hourly_cost', 'task')


class ProjectTaskAdmin(admin.ModelAdmin):
    list_display = ('project', 'order', 'duration', 'status')


register = admin.site.register

register(TaskStatus)
register(ProjectStatus)
register(Project, ProjectAdmin)
register(Resource, ResourceAdmin)
register(WorkingPeriod)
register(ProjectTask, ProjectTaskAdmin)
