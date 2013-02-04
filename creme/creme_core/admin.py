# -*- coding: utf-8 -*-

from django.contrib import admin

from creme_core.models import *


register = admin.site.register

register(CremeEntity)

register(CremeProperty)
register(CremePropertyType)

register(RelationType)
register(Relation)

register(UserRole)
register(SetCredentials)

register(HeaderFilterItem)
register(HeaderFilter)

register(EntityFilter)

register(Language)

register(PreferedMenuItem)
register(BlockDetailviewLocation)
register(BlockPortalLocation)
register(ButtonMenuItem)

register(DateReminder)
