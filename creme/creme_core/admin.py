# -*- coding: utf-8 -*-

from django.contrib import admin

from creme_core.models import *

register = admin.site.register

register(CremeEntity)

register(CremeProperty)
register(CremePropertyType)

register(RelationType)
register(Relation)

register(CremeRole)
register(CremeProfile)
register(CremeTypeDroit)
register(CremeTypeEnsembleFiche)
register(CremeDroitEntityType)
register(CremeAppTypeDroit)
register(CremeAppDroit)

#register(CustomFields)
#register(ValueOfCustomFieldsList)
#register(CustomFieldsValue, CustomFieldsValueAdmin)

register(HeaderFilterItem)
register(HeaderFilter)

register(FilterType)
register(FilterCondition)
register(Filter)
register(FilterValue)

register(Language)

register(PreferedMenuItem)
register(BlockConfigItem)
register(ButtonMenuItem)

register(DateReminder)
