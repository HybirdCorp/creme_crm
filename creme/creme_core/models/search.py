# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

import logging

from django.db.models import TextField, ForeignKey, Q, FieldDoesNotExist #PositiveIntegerField, CharField
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from ..utils.meta import FieldInfo, ModelFieldEnumerator #get_verbose_field_name
from .base import CremeModel
from .fields import EntityCTypeForeignKey


logger = logging.getLogger(__name__)


class SearchField(object):
    __slots__ = ('__name', '__verbose_name')

    def __init__(self, field_name, field_verbose_name): 
        self.__name = field_name
        self.__verbose_name = field_verbose_name

    def __unicode__(self):
        return self.__verbose_name

    @property
    def name(self):
        return self.__name

    @property
    def verbose_name(self):
        return self.__verbose_name


class SearchConfigItem(CremeModel):
    content_type = EntityCTypeForeignKey(verbose_name=_(u'Related resource'))
#    role         = ForeignKey(UserRole, verbose_name=_(u"Related role"), null=True) #TODO: To be done ?
    user         = ForeignKey(User, verbose_name=_(u"Related user"), null=True)
    field_names  = TextField(null=True) #Do not this field directly; use 'searchfields' property

    _searchfields = None
    EXCLUDED_FIELDS_TYPES = frozenset(['DateTimeField', 'DateField', 'FileField', 'ImageField'])

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Search')
        verbose_name_plural = _(u'Searches')

    def __unicode__(self):
        return ugettext(u'Search configuration of "%(user)s" for "%(type)s"') % {
                    'user': self.user or ugettext(u'all users'),
                    'type': self.content_type,
                }

    @property
    def all_fields(self):
        "@return True means that all fields are used."
        self.searchfields #compute self._all_fields
        return self._all_fields

    @staticmethod
    def _get_modelfields_choices(model):
        excluded = SearchConfigItem.EXCLUDED_FIELDS_TYPES
        return ModelFieldEnumerator(model, deep=1) \
                .filter(viewable=True) \
                .exclude(lambda f, depth: f.get_internal_type() in excluded) \
                .choices()

    def _build_searchfields(self, model, fields, save=True):
        sfields = []
        old_field_names = self.field_names

        for field_name in fields:
            try:
                #verbose_name = get_verbose_field_name(model, field_name, silent=False)
                field_info = FieldInfo(model, field_name)
            except FieldDoesNotExist as e:
                logger.warn('%s => SearchField removed', e)
            else:
                #sfields.append(SearchField(field_name=field_name, field_verbose_name=verbose_name))
                sfields.append(SearchField(field_name=field_name, field_verbose_name=field_info.verbose_name))

        self.field_names = ','.join(sf.name for sf in sfields) or None

        if not sfields: # field_names is empty => use all compatible fields
            sfields.extend(SearchField(field_name=field_name, field_verbose_name=verbose_name)
                                for field_name, verbose_name in self._get_modelfields_choices(model)
                          )
            self._all_fields = True
        else:
            self._all_fields = False

        self._searchfields = tuple(sfields) #we can pass the reference to this immutable collections (and SearchFields are hardly mutable)

        if save and old_field_names != self.field_names:
            self.save()

    @property
    def searchfields(self):
        if self._searchfields is None:
            names = self.field_names
            self._build_searchfields(self.content_type.model_class(), names.split(',') if names else ())

        return self._searchfields

    @searchfields.setter
    def searchfields(self, fields):
        "@param fields Sequence of strings representing field names"
        self._build_searchfields(self.content_type.model_class(), fields, save=False)

    def get_modelfields_choices(self):
        """Return a list of tuples (useful for Select.choices) representing
        Fields that can be chosen by the user.
        """
        return self._get_modelfields_choices(self.content_type.model_class())

    @staticmethod
    def create_if_needed(model, fields, user=None):
        """Create a config item & its fields if one does not already exists.
        SearchConfigItem.create_if_needed(SomeDjangoModel, ['YourEntity_field1', 'YourEntity_field2', ..])
        @param fields Sequence of strings representing field names.
        """
        ct = ContentType.objects.get_for_model(model)
        sci, created = SearchConfigItem.objects.get_or_create(content_type=ct, user=user)

        if created:
            sci._build_searchfields(model, fields)

        return sci

    @staticmethod
    def get_4_model(model, user):
        "Get the SearchConfigItem instance corresponding to the given model"
        ct = ContentType.objects.get_for_model(model)
        sc_items = SearchConfigItem.objects.filter(content_type=ct) \
                                           .filter(Q(user=user) | Q(user__isnull=True)) \
                                           .order_by('-user')[:1] #config of the user has higher priority than default one

        return sc_items[0] if sc_items else SearchConfigItem(content_type=ct)

#class SearchField(CremeModel):
    #field              = CharField(_(u"Field"), max_length=100)
    #field_verbose_name = CharField(_(u"Field (long name)"), max_length=100)
    #search_config_item = ForeignKey(SearchConfigItem, verbose_name=_(u"Associated configuration"))
    #order              = PositiveIntegerField(_(u"Priority"))

    #class Meta:
        #app_label = 'creme_core'
