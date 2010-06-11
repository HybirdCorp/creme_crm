# -*- coding: utf-8 -*-

from django.contrib import admin

from media_managers.models import *


class ImageAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'height', 'width')


register = admin.site.register
register(Image, ImageAdmin)
register(MediaCategory)
