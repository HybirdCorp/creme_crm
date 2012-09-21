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

from collections import defaultdict
from functools import partial
from logging import warn

from django.db.models import CharField, ForeignKey, PositiveIntegerField
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeModel
from creme_core.utils.meta import get_model_field_infos, get_verbose_field_name


DEFAULT_PATTERN = '__icontains'

class SearchConfigItem(CremeModel):
    content_type = ForeignKey(ContentType, verbose_name=_(u"Related type"))
#    role         = ForeignKey(UserRole,   verbose_name=_(u"Related role"),        null=True)#TODO:To be done ?
    user         = ForeignKey(User, verbose_name=_(u"Related user"), null=True)

    _searchfields = None

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Search')
        verbose_name_plural = _(u'Searches')

    def __unicode__(self):
        return ugettext(u'Search configuration of "%(user)s" for "%(type)s"') % {
                    'user': self.user or ugettext(u'all users'),
                    'type': self.content_type,
                }

    def get_fields(self):
        if self._searchfields is None:
            self._searchfields = list(SearchField.objects.filter(search_config_item=self))

        return self._searchfields

    @staticmethod
    def populate_searchfields(search_config_items):
        #list(search_config_items) is needed because of mysql
        all_searchfields = SearchField.objects.filter(search_config_item__in=list(search_config_items))
        sfci_dict = defaultdict(list)

        for sf in all_searchfields:
            sfci_dict[sf.search_config_item_id].append(sf)

        for sfci in search_config_items:
            sfci._searchfields = sfci_dict[sfci.id]

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
