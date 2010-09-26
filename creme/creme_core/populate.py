# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.utils.translation import ugettext as _

from creme_core.models import *
from creme_core.utils import create_or_update_models_instance as create
from creme_core.constants import PROP_IS_MANAGED_BY_CREME, REL_SUB_RELATED_TO, REL_OBJ_RELATED_TO, REL_SUB_HAS, REL_OBJ_HAS
from creme_core.management.commands.creme_populate import BasePopulator
from creme_core.pop_data.populate_data import set_up as set_up_credentials #TODO: remove

DATE_RANGE_FILTER = 23

class Populator(BasePopulator):
    def populate(self, *args, **kwargs):
        create(FilterType,  1, name=_(u'Equals'),                                 pattern_key='%s__exact',        pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType,  2, name=_(u'Equals (case insensitive)'),              pattern_key='%s__iexact',       pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType,  3, name=_(u"Does not equal"),                         pattern_key='%s__exact',        pattern_value='%s',      is_exclude=True , type_champ="CharField", value_field_type='textfield')
        create(FilterType,  4, name=_(u"Does not equal (case insensitive)"),      pattern_key='%s__iexact',       pattern_value='%s',      is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType,  5, name=_(u"Contains"),                               pattern_key='%s__contains',     pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType,  6, name=_(u"Contains (case insensitive)"),            pattern_key='%s__icontains',    pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType,  7, name=_(u"Does not contain"),                       pattern_key='%s__contains',     pattern_value='%s',      is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType,  8, name=_(u"Does not contain (case insensitive)"),    pattern_key='%s__icontains',    pattern_value='%s',      is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType,  9, name=_(u">"),                                      pattern_key='%s__gt',           pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 10, name=_(u">="),                                     pattern_key='%s__gte',          pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 11, name=_(u"<"),                                      pattern_key='%s__lt',           pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 12, name=_(u"<="),                                     pattern_key='%s__lte',          pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 13, name=_(u"Starts with"),                            pattern_key='%s__startswith',   pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 14, name=_(u"Starts with (case insensitive)"),         pattern_key='%s__istartswith',  pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 15, name=_(u"Does not start with"),                    pattern_key='%s__startswith',   pattern_value='%s',      is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType, 16, name=_(u"Does not start with (case insensitive)"), pattern_key='%s__istartswith',  pattern_value='%s',      is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType, 17, name=_(u"Ends with"),                              pattern_key='%s__endswith',     pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 18, name=_(u"Ends with (case insensitive)"),           pattern_key='%s__iendswith',    pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 19, name=_(u"Does not end with"),                      pattern_key='%s__endswith',     pattern_value='%s',      is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType, 20, name=_(u"Does not end with (case insensitive)"),   pattern_key='%s__iendswith',    pattern_value='%s',      is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType, 21, name=_(u"Is empty"),                               pattern_key='%s__isnull',       pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 22, name=_(u"Is not empty"),                           pattern_key='%s__isnull',       pattern_value='%s',      is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType, DATE_RANGE_FILTER, name=_(u"Date range"),              pattern_key='%s__range',        pattern_value='(%s,%s)', is_exclude=False, type_champ="CharField", value_field_type='textfield')

        create(CremeTypeDroit, 1, name=_(u"Read"))
        create(CremeTypeDroit, 2, name=_(u"Create"))
        create(CremeTypeDroit, 3, name=_(u"Modify"))
        create(CremeTypeDroit, 4, name=_(u"Delete"))
        create(CremeTypeDroit, 5, name=_(u"Create relation with"))

        create(CremeTypeEnsembleFiche,  1, name=_(u"His own pages"))
        create(CremeTypeEnsembleFiche,  2, name=_(u"All pages"))
        create(CremeTypeEnsembleFiche,  3, name=_(u"Pages of the team"))
        create(CremeTypeEnsembleFiche,  4, name=_(u"The pages of subordinates"))
        create(CremeTypeEnsembleFiche,  5, name=_(u"The pages of a role"))
        create(CremeTypeEnsembleFiche,  6, name=_(u"The pages of a role and its subordinates"))
        create(CremeTypeEnsembleFiche,  7, name=_(u"His page"))
        create(CremeTypeEnsembleFiche,  8, name=_(u"The other pages"))
        create(CremeTypeEnsembleFiche,  9, name=_(u"Unique page"))
        create(CremeTypeEnsembleFiche, 10, name=_(u"Pages related to his page"))

        create(CremeAppTypeDroit, 1, name=_(u"Is administrator"))
        create(CremeAppTypeDroit, 2, name=_(u"Has access"))

        create(Language, 1, name=_(u'French'),  code='FRA')
        create(Language, 2, name=_(u'English'), code='EN')

        CremePropertyType.create(PROP_IS_MANAGED_BY_CREME, _(u'managed by Creme'))

        RelationType.create((REL_SUB_RELATED_TO, _(u'related to')),
                            (REL_OBJ_RELATED_TO, _(u'related to')))
        RelationType.create((REL_SUB_HAS,        _(u'owns')),
                            (REL_OBJ_HAS,        _(u'belongs to')))

        set_up_credentials()
