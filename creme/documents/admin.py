# -*- coding: utf-8 -*-

from django.contrib import admin

from documents.models import Folder, FolderCategory, Document


class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'description')


class FolderAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'parent_folder', 'category')


register = admin.site.register
register(FolderCategory)
register(Document, DocumentAdmin)
register(Folder, FolderAdmin)

