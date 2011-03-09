# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from logging import info

from django.utils.translation import ugettext as _
from django.contrib.auth.models import User

from creme_core.models import *
from creme_core.utils import create_or_update as create
from creme_core.constants import *
from creme_core.management.commands.creme_populate import BasePopulator


DATE_RANGE_FILTER = 23
DATE_RANGE_FILTER_VOLATILE = 24

class Populator(BasePopulator):
    def populate(self, *args, **kwargs):
        #TODO: Make other constants for FilterType
        create(FilterType,  FILTER_TYPE_EQUALS, name=_(u'Equals'),                pattern_key='%s__exact',        pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
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
        create(FilterType, DATE_RANGE_FILTER_VOLATILE, name=_(u"Date range"),     pattern_key='%s__range',        pattern_value='(%s,%s)', is_exclude=False, type_champ="CharField", value_field_type='textfield')

        create(Language, 1, name=_(u'French'),  code='FRA')
        create(Language, 2, name=_(u'English'), code='EN')

        CremePropertyType.create(PROP_IS_MANAGED_BY_CREME, _(u'managed by Creme'))

        RelationType.create((REL_SUB_RELATED_TO, _(u'related to')),
                            (REL_OBJ_RELATED_TO, _(u'related to')))
        RelationType.create((REL_SUB_HAS,        _(u'owns')),
                            (REL_OBJ_HAS,        _(u'belongs to')))


        try:
            root = User.objects.get(pk=1)
        except User.DoesNotExist:
            login = password = 'root'

            root = User(username=login, is_superuser=True)
            root.set_password(password)
            root.save()

            info('A super-user has been created with login="%(login)s" and password="%(password)s".' % {
                            'login':    login,
                            'password': password,
                        })
