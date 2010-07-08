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

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import CharField
from django.db.models import ForeignKey
from django.db.models import PositiveIntegerField
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode

from creme_core.models import CremeModel

DEFAULT_PATTERN = '__icontains'

class SearchConfigItem(CremeModel):
    content_type = ForeignKey(ContentType, verbose_name=_(u"Type associé"))
#    role         = ForeignKey(CremeRole,   verbose_name=_(u"Rôle associé"),        null=True)#TODO:To be done ?
    user         = ForeignKey(User,        verbose_name=_(u"Utilisateur associé"), null=True)

    _searchfields = None

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Recherche')
        verbose_name_plural = _(u'Recherches')

    def get_fields(self):
        if self._searchfields is None:
            self._searchfields = SearchField.objects.filter(search_config_item=self).order_by('order')
        
        return self._searchfields

    @staticmethod
    def populate_searchfields(search_config_items):
        #list(search_config_items) is needed because of mysql
        all_searchfields = SearchField.objects.filter(search_config_item__in=list(search_config_items)).order_by('order')

        from collections import defaultdict

        sfci_dict = defaultdict(list)

        for sf in all_searchfields:
            sfci_dict[sf.search_config_item_id].append(sf)

        for sfci in search_config_items:
            sfci._searchfields = sfci_dict[sfci.id]


class SearchField(CremeModel):
    field              = CharField(_(u"Champ"), max_length=100)
    field_verbose_name = CharField(_(u"Champ"), max_length=100)
    search_config_item = ForeignKey(SearchConfigItem, verbose_name=_(u"Configuration de recherche associée"))
    order              = PositiveIntegerField(_(u"Priorité"))

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Champ de recherche')
        verbose_name_plural = _(u'Champs de recherche')

    def __unicode__(self):
        return force_unicode(self.field_verbose_name)