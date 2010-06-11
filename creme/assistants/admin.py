# -*- coding: utf-8 -*-

from django.contrib import admin

from assistants.models import *


class ActionAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'creation_date', 'expected_reaction', 'deadline', 'validation_date')


class AlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'trigger_date', 'for_user')


class MemoAdmin(admin.ModelAdmin):
    list_display = ('content', 'creation_date', 'user')


class ToDoAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'creation_date', 'deadline', 'for_user')


register = admin.site.register
register(Action, ActionAdmin)
register(Alert, AlertAdmin)
register(Memo, MemoAdmin)
register(ToDo, ToDoAdmin)
