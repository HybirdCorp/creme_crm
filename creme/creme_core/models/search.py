# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from collections import defaultdict
from functools import partial
from logging import warn

from django.db.models import CharField, ForeignKey, PositiveIntegerField, Q
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeModel
from creme_core.utils.meta import get_verbose_field_name, ModelFieldEnumerator


class SearchConfigItem(CremeModel):
    content_type = ForeignKey(ContentType, verbose_name=_(u"Related type"))
#    role         = ForeignKey(UserRole,   verbose_name=_(u"Related role"),        null=True)#TODO:To be done ?
    user         = ForeignKey(User, verbose_name=_(u"Related user"), null=True)

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

    @staticmethod
    def _build_query(research, fields, is_or=True): #TODO: 'is_or' useful ??
        """Build a Q with all params fields"""
        result_q = Q()

        for f in fields:
            q = Q(**{'%s__icontains' % f.field: research})

            if is_or:
                result_q |= q
            else:
                result_q &= q

        return result_q

    @staticmethod
    def _get_modelfields_choices(model):
        excluded = SearchConfigItem.EXCLUDED_FIELDS_TYPES
        return ModelFieldEnumerator(model, deep=1) \
                .filter(viewable=True) \
                .exclude(lambda f: f.get_internal_type() in excluded) \
                .choices()

    def get_fields(self):
        if self._searchfields is None:
            self._searchfields = list(SearchField.objects.filter(search_config_item=self))

        return self._searchfields

    def get_modelfields_choices(self):
        """TODO
        """
        return self._get_modelfields_choices(self.content_type.model_class())

    @staticmethod
    def create_if_needed(model, fields, user=None):
        """Create a config item & its fields if one does not already exists.
        SearchConfigItem.create_if_needed(SomeDjangoModel, ['SomeDjangoModel_field1', 'SomeDjangoModel_field2', ..])
        """
        ct = ContentType.objects.get_for_model(model)
        sci, created = SearchConfigItem.objects.get_or_create(content_type=ct, user=user)

        if created:
            create_sf = partial(SearchField.objects.create, search_config_item=sci)
            i = 1

            for field in fields:
                if get_verbose_field_name(model, field):
                    create_sf(field=field, order=i,
                              field_verbose_name=get_verbose_field_name(model, field),
                             )
                    i += 1
                else:
                    warn('SearchConfigItem.create_if_needed(): invalid field "%s"', field)

        return sci

    @staticmethod
    def get_searchfields_4_model(model, user):
        "Get the list of SearchField instances corresponding to the given model"
        sc_items = SearchConfigItem.objects.filter(content_type=ContentType.objects.get_for_model(model)) \
                                           .filter(Q(user=user) | Q(user__isnull=True)) \
                                           .order_by('-user') #config of the user has higher priority than default one

        for sc_item in sc_items:
            fields = sc_item.get_fields()
            if fields:
                fields = list(fields)
                break
        else: #Fallback
            fields = [SearchField(field=name, field_verbose_name=verbose_name, order=i)
                        for i, (name, verbose_name) in enumerate(SearchConfigItem._get_modelfields_choices(model))
                     ]

        return fields

    @staticmethod
    def populate_searchfields(search_config_items):
        #list(search_config_items) is needed because of mysql
        all_searchfields = SearchField.objects.filter(search_config_item__in=list(search_config_items)).order_by('order')
        sfci_dict = defaultdict(list)

        for sf in all_searchfields:
            sfci_dict[sf.search_config_item_id].append(sf)

        for sfci in search_config_items:
            sfci._searchfields = sfci_dict[sfci.id]

    @staticmethod
    def search(model, searchfields, research):
        """Return the models which fields contain the wanted value.
        @param model Class inheriting django.db.Model (CremeEntity)
        @param searchfields Sequence of strings representing fields on the model.
        @param research Searched string.
        @return Queryset on model.
        """
        return model.objects.filter(is_deleted=False) \
                            .filter(SearchConfigItem._build_query(research, searchfields)) \
                            .distinct()


#TODO: is this model really useful ??? (store fields in a textfield in SearchConfigItem ?)
class SearchField(CremeModel):
    field              = CharField(_(u"Field"), max_length=100)
    field_verbose_name = CharField(_(u"Field (long name)"), max_length=100)
    search_config_item = ForeignKey(SearchConfigItem, verbose_name=_(u"Associated configuration"))
    order              = PositiveIntegerField(_(u"Priority"))

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Search field')
        verbose_name_plural = _(u'Search fields')
        ordering = ('order',)

    def __unicode__(self):
        return self.field_verbose_name
