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

from django.db.models import CharField, ForeignKey, PositiveIntegerField, BooleanField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeModel, RelationType


class BlockConfigItem(CremeModel):
    id           = CharField(primary_key=True, max_length=100)
    content_type = ForeignKey(ContentType, verbose_name=_(u"Type associé"), null=True)
    block_id     = CharField(_(u"Identifiant de bloc"), max_length=100, blank=False, null=False)
    order        = PositiveIntegerField(_(u"Priorité"))
    on_portal    = BooleanField(_(u"Affiché sur la page d'accueil ?"))

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Bloc')
        verbose_name_plural = _(u'Blocs')


class RelationBlockItem(CremeModel):
    block_id      = CharField(_(u"Identifiant de bloc"), max_length=100) #really useful ?? (can be retrieved with type)
    relation_type = ForeignKey(RelationType, verbose_name=_(u"Type de relation associé"), unique=True)

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Bloc de relation spécifique')
        verbose_name_plural = _(u'Blocs de relation spécifique')

    def delete(self):
        BlockConfigItem.objects.filter(block_id=self.block_id).delete()

        super(RelationBlockItem, self).delete()
