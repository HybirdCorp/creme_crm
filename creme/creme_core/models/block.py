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

from imp import find_module

from django.db.models import (CharField, ForeignKey, PositiveIntegerField,
                              BooleanField, TextField)
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeModel, RelationType, CremeEntity


class BlockConfigItem(CremeModel):
    id           = CharField(primary_key=True, max_length=100)
    content_type = ForeignKey(ContentType, verbose_name=_(u"Related type"), null=True)
    block_id     = CharField(_(u"Block ID"), max_length=100, blank=False, null=False)
    order        = PositiveIntegerField(_(u"Priority"))
    on_portal    = BooleanField(_(u"Displayed on portal ?"))

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Block to display')
        verbose_name_plural = _(u'Blocks to display')


class RelationBlockItem(CremeModel):
    block_id      = CharField(_(u"Block ID"), max_length=100) #really useful ?? (can be retrieved with type)
    relation_type = ForeignKey(RelationType, verbose_name=_(u"Related type of relation"), unique=True)

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Specific relation block')
        verbose_name_plural = _(u'Specific relation blocks')

    def delete(self):
        BlockConfigItem.objects.filter(block_id=self.block_id).delete()

        super(RelationBlockItem, self).delete()

    @staticmethod
    def create(relation_type_id):
        try:
            rbi = RelationBlockItem.objects.get(relation_type=relation_type_id)
        except RelationBlockItem.DoesNotExist:
            from creme_core.gui.block import SpecificRelationsBlock
            rbi = RelationBlockItem.objects.create(block_id=SpecificRelationsBlock.generate_id('creme_config', relation_type_id),
                                                   relation_type_id=REL_OBJ_LINKED_2_TICKET
                                                  )

        return rbi


class InstanceBlockConfigItem(CremeModel):
    block_id = CharField(_(u"Block ID"), max_length=300, blank=False, null=False)
    entity   = ForeignKey(CremeEntity, verbose_name=_(u"Block related entity"))
    data     = TextField(blank=True, null=True)
    verbose  = CharField(_(u"Verbose"), max_length=200, blank=True, null=True)

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u"Instance's Block to display")
        verbose_name_plural = _(u"Instance's Blocks to display")

    def __unicode__(self):
        return unicode(self.verbose or self.entity)

    def delete(self):
        BlockConfigItem.objects.filter(block_id=self.block_id).delete()

        super(InstanceBlockConfigItem, self).delete()

    @staticmethod
    def id_is_specific(id_):
        return id_.startswith(u'instanceblock-')

    @staticmethod
    def generate_id(import_path, app_name, name):
        if app_name.find('-') != -1 or name.find('-') != -1:
            raise InstanceBlockConfigItem.BadImportIdFormat(u"app_name and name mustn't contains '-'")
        if import_path.find('_') == -1:
            raise InstanceBlockConfigItem.BadImportIdFormat(u"import_path have to be separated by '_'")
        return u'instanceblock-%s-%s_%s' % (import_path, app_name, name)

    @staticmethod
    def get_import_path(id_):
        id_ = str(id_)
        _path = id_.split('-')[1]
        path = _path.split('_')

        block_class = path[-1]
        path = path[:-1]

        module = path[-1]

        try:
            find_module(module, __import__('.'.join(path[:-1]), {}, {}, [module]).__path__)
        except ImportError, e:
            return None

        return (".".join(path), block_class)

    class BadImportIdFormat(Exception):
        pass