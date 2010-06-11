# -*- coding: utf-8 -*-

from django.contrib import admin

from persons.models import *


class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name','email','phone','url_site','capital')
    list_filter = ['capital']
    search_fields = ['name']

class ContactAdmin(admin.ModelAdmin):
    list_display = ('civility','first_name','last_name','landline','mobile','skype','email','sector','function')
    list_filter = ['civility','sector','function']
    search_fields = ['civility','sector','function','first_name','last_name','landline','mobile']


register = admin.site.register

register(Address)

register(Organisation, OrganisationAdmin)
register(StaffSize)
register(LegalForm)

register(Contact, ContactAdmin)
register(Sector)
register(PeopleFunction)
register(Civility)
