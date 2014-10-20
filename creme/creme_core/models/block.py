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

from functools import partial
from json import loads as jsonloads, dumps as jsondumps
import logging

from django.db.models import (CharField, ForeignKey, PositiveIntegerField,
                              PositiveSmallIntegerField, BooleanField, TextField)
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from ..constants import (SETTING_BLOCK_DEFAULT_STATE_IS_OPEN,
        SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS, MODELBLOCK_ID)
from ..utils import creme_entity_content_types
from .base import CremeModel
from .entity import CremeEntity
from .fields import CTypeForeignKey
from .relation import RelationType
from .setting_value import SettingValue


__all__ = ('BlockDetailviewLocation', 'BlockPortalLocation', 'BlockMypageLocation',
           'RelationBlockItem', 'InstanceBlockConfigItem', 'CustomBlockConfigItem',
           'BlockState',
          )
logger = logging.getLogger(__name__)


class BlockDetailviewLocation(CremeModel):
    content_type = CTypeForeignKey(verbose_name=_(u'Related type'), null=True)
    block_id     = CharField(max_length=100)
    order        = PositiveIntegerField()
    zone         = PositiveSmallIntegerField()

    TOP    = 1
    LEFT   = 2
    RIGHT  = 3
    BOTTOM = 4

    ZONES = (TOP, LEFT, RIGHT, BOTTOM)

    class Meta:
        app_label = 'creme_core'
        ordering = ('order',)

    def __repr__(self):
        return 'BlockDetailviewLocation(id=%s, content_type_id=%s, block_id=%s, order=%s, zone=%s)' % (
                self.id, self.content_type_id, self.block_id, self.order, self.zone
            )

    @staticmethod
    def create(block_id, order, zone, model=None): #TODO: rename 'create_if_needed'
        ct = ContentType.objects.get_for_model(model) if model else None

        #TODO: get_or_create()
        try:
            loc = BlockDetailviewLocation.objects.get(content_type=ct, block_id=block_id)
        except Exception:
            loc = BlockDetailviewLocation.objects.create(content_type=ct, block_id=block_id, order=order, zone=zone)

        return loc

    @staticmethod
    def create_4_model_block(order, zone, model=None):
        return BlockDetailviewLocation.create(MODELBLOCK_ID, order, zone, model)

    @staticmethod
    def id_is_4_model(block_id):
        return block_id == MODELBLOCK_ID

    @staticmethod
    def create_empty_config(model=None):
        ct = ContentType.objects.get_for_model(model) if model else None

        if not BlockDetailviewLocation.objects.filter(content_type=ct).exists():
            create = BlockDetailviewLocation.objects.create

            for zone in BlockDetailviewLocation.ZONES:
                create(content_type=ct, block_id='', order=1, zone=zone)


class BlockPortalLocation(CremeModel):
    app_name = CharField(max_length=40)
    block_id = CharField(max_length=100)
    order    = PositiveIntegerField()

    class Meta:
        app_label = 'creme_core'
        ordering = ('order',)

    def __repr__(self):
        return 'BlockPortalLocation(id=%s, app_name=%s)' % (
                self.id, self.app_name
            )

    @staticmethod
    def create(block_id, order, app_name=''):
        try:
            loc = BlockPortalLocation.objects.get(app_name=app_name, block_id=block_id)
        except Exception:
            loc = BlockPortalLocation.objects.create(app_name=app_name, block_id=block_id, order=order)
        else:
            loc.order = order
            loc.save()

        return loc

    @staticmethod
    def create_empty_config(app_name=''):
        if not BlockPortalLocation.objects.filter(app_name=app_name).exists():
            BlockPortalLocation.objects.create(app_name=app_name, block_id='', order=1)


class BlockMypageLocation(CremeModel):
    user     = ForeignKey(User, null=True)
    block_id = CharField(max_length=100)
    order    = PositiveIntegerField()

    class Meta:
        app_label = 'creme_core'
        ordering = ('order',)

    def __repr__(self):
        return 'BlockMypageLocation(id=%s, user=%s)' % (
                self.id, self.user_id
            )

    @staticmethod
    def _copy_default_config(sender, instance, created, **kwargs):
        if created:
            from django.db.transaction import commit_on_success

            create = BlockMypageLocation.objects.create

            with commit_on_success():
                try:
                    for loc in BlockMypageLocation.objects.filter(user=None):
                        create(user=instance, block_id=loc.block_id, order=loc.order)
                except Exception:
                    #TODO: if should not be true anymore when south is built-in django (BlockMypageLocation table exists when the first User is created)
                    logger.warn('Can not create block config for this user: %s (if it is the first user, do not worry because it is normal)' % instance)

    @staticmethod
    def create(block_id, order, user=None):
        try:
            loc = BlockMypageLocation.objects.get(user=user, block_id=block_id)
        except Exception:
            loc = BlockMypageLocation.objects.create(user=user, block_id=block_id, order=order)
        else:
            loc.order = order
            loc.save()

        return loc

    @property
    def block_verbose_name(self):
        from creme.creme_core.gui.block import block_registry
        #try:
            #return block_registry[self.block_id].verbose_name
        #except:
            #return '???'
        return block_registry.get_blocks((self.block_id,))[0].verbose_name


post_save.connect(BlockMypageLocation._copy_default_config, sender=User,
                  dispatch_uid='creme_core-blockmypagelocation._copy_default_config'
                 )


class RelationBlockItem(CremeModel):
    block_id       = CharField(_(u"Block ID"), max_length=100, editable=False) #TODO: not really useful (can be retrieved with type)
    relation_type  = ForeignKey(RelationType, verbose_name=_(u"Related type of relationship"), unique=True)
    json_cells_map = TextField(editable=False, null=True) #TODO: JSONField

    _cells_map = None

    class Meta:
        app_label = 'creme_core'
        #verbose_name = _(u'Specific relationship block')
        #verbose_name_plural = _(u'Specific relationship blocks')

    def __init__(self, *args, **kwargs):
        super(RelationBlockItem, self).__init__(*args, **kwargs)
        if self.json_cells_map is None:
            self._cells_map = {}
            self._dump_cells_map()

    def delete(self):
        BlockDetailviewLocation.objects.filter(block_id=self.block_id).delete()

        super(RelationBlockItem, self).delete()

    @property
    def all_ctypes_configured(self):
        #TODO: cache (object_ctypes) ??
        compat_ctype_ids = set(self.relation_type.object_ctypes.values_list('id', flat=True)) or \
                           {ct.id for ct in creme_entity_content_types()}

        for ct_id in self._cells_by_ct().iterkeys():
            compat_ctype_ids.discard(ct_id)

        return not bool(compat_ctype_ids)

    @staticmethod
    def create(relation_type_id):
        try:
            rbi = RelationBlockItem.objects.get(relation_type=relation_type_id)
        except RelationBlockItem.DoesNotExist:
            from creme.creme_core.gui.block import SpecificRelationsBlock
            rbi = RelationBlockItem.objects.create(block_id=SpecificRelationsBlock.generate_id('creme_config', relation_type_id),
                                                   relation_type_id=relation_type_id
                                                  )

        return rbi

    def _dump_cells_map(self):
        self.json_cells_map = jsondumps(
                {ct_id: [cell.to_dict() for cell in cells]
                    for ct_id, cells in self._cells_map.iteritems()
                }
            )

    def _cells_by_ct(self):
        cells_map = self._cells_map

        if cells_map is None:
            from ..core.entity_cell import CELLS_MAP

            self._cells_map = cells_map = {}
            get_ct = ContentType.objects.get_for_id
            build = CELLS_MAP.build_cells_from_dicts
            total_errors = False

            for ct_id, cells_as_dicts in jsonloads(self.json_cells_map).iteritems():
                ct = get_ct(ct_id)
                cells, errors = build(model=ct.model_class(), dicts=cells_as_dicts) #TODO: do it lazily ??

                if errors:
                    total_errors = True

                cells_map[ct.id] = cells

            if total_errors:
                logger.warn('RelationBlockItem (id="%s") is saved with valid cells.', self.id)
                self._dump_cells_map()
                self.save()

        return cells_map

    def delete_cells(self, ctype):
        del self._cells_by_ct()[ctype.id]
        self._dump_cells_map()

    def get_cells(self, ctype):
        return self._cells_by_ct().get(ctype.id)

    def iter_cells(self):
        "Beware: do not modify the returned objects"
        get_ct = ContentType.objects.get_for_id

        for ct_id, cells in self._cells_by_ct().iteritems():
            yield get_ct(ct_id), cells #TODO: copy dicts ?? (if 'yes' -> iter_ctypes() too)

    def set_cells(self, ctype, cells):
        self._cells_by_ct()[ctype.id] = cells
        self._dump_cells_map()


class InstanceBlockConfigItem(CremeModel):
    block_id = CharField(_(u"Block ID"), max_length=300, blank=False, null=False, editable=False)
    entity   = ForeignKey(CremeEntity, verbose_name=_(u"Block related entity"))
    data     = TextField(blank=True, null=True)
    verbose  = CharField(_(u"Verbose"), max_length=200, blank=True, null=True) #TODO: remove

    _block = None

    class Meta:
        app_label = 'creme_core'
        #verbose_name = _(u"Instance's Block to display")
        #verbose_name_plural = _(u"Instance's Blocks to display")
        ordering = ('id',)

    def __unicode__(self):
        #return unicode(self.verbose or self.entity)
        return self.block.verbose_name

    def delete(self):
        block_id = self.block_id
        BlockDetailviewLocation.objects.filter(block_id=block_id).delete()
        BlockState.objects.filter(block_id=block_id).delete()

        super(InstanceBlockConfigItem, self).delete()

    @property
    def block(self):
        block = self._block

        if block is None:
            from ..gui.block import block_registry
            self._block = block = block_registry.get_block_4_instance(self, entity=self.entity)

        return block

    @property
    def errors(self):
        return getattr(self.block, 'errors', None)

    @staticmethod
    def id_is_specific(block_id):
        return block_id.startswith(u'instanceblock_')

    @staticmethod
    def generate_base_id(app_name, name):
        return u'instanceblock_%s-%s' % (app_name, name)

    @staticmethod
    def generate_id(block_class, entity, key):
        """@param key String that allows to make the difference between 2 instances
                      of the same Block class and the same CremeEntity instance.
        """
        if key and any((c in key) for c in ('#', '@', '&', ':', ' ')):
            raise ValueError('InstanceBlockConfigItem.generate_id: usage of a forbidden character in key "%s"' % key)

        return u'%s|%s-%s' % (block_class.id_, entity.id, key)

    @staticmethod
    def get_base_id(block_id):
        return block_id.split('|', 1)[0]


class CustomBlockConfigItem(CremeModel):
    id           = CharField(primary_key=True, max_length=100, editable=False)
    content_type = CTypeForeignKey(verbose_name=_(u'Related type'), editable=False)
    name         = CharField(_(u'Name'), max_length=200)
    json_cells   = TextField(editable=False, null=True) #TODO: JSONField

    _cells = None

    class Meta:
        app_label = 'creme_core'

    def __init__(self, *args, **kwargs):
        super(CustomBlockConfigItem, self).__init__(*args, **kwargs)
        if self.json_cells is None:
            self.cells = []

    def __unicode__(self):
        return self.name

    def delete(self):
        block_id = self.generate_id()
        BlockDetailviewLocation.objects.filter(block_id=block_id).delete()
        BlockState.objects.filter(block_id=block_id).delete()

        super(CustomBlockConfigItem, self).delete()

    def generate_id(self):
        return 'customblock-%s' % self.id

    @staticmethod
    def id_from_block_id(block_id):
        try:
            prefix, cbci_id = block_id.split('-', 1)
        except ValueError: #unpacking error
            return None

        return None if prefix != 'customblock' else cbci_id

    #TODO: factorise with HeaderFilter.cells
    @property
    def cells(self):
        cells = self._cells

        if cells is None:
            from ..core.entity_cell import CELLS_MAP

            cells, errors = CELLS_MAP.build_cells_from_dicts(model=self.content_type.model_class(),
                                                             dicts=jsonloads(self.json_cells),
                                                            )

            if errors:
                logger.warn('CustomBlockConfigItem (id="%s") is saved with valid cells.', self.id)
                self._dump_cells(cells)
                self.save()

            self._cells = cells

        return cells

    def _dump_cells(self, cells):
        self.json_cells = jsondumps([cell.to_dict() for cell in cells])

    @cells.setter
    def cells(self, cells):
        self._cells = cells = [cell for cell in cells if cell]
        self._dump_cells(cells)


class BlockState(CremeModel):
    user              = ForeignKey(User)
    block_id          = CharField(_(u"Block ID"), max_length=100)
    is_open           = BooleanField(default=True) #Is block has to appear as opened or closed
    show_empty_fields = BooleanField(default=True) #Are empty fields in block have to be shown or not

    class Meta:
        app_label = 'creme_core'
        #verbose_name = _(u'Block state')
        #verbose_name_plural = _(u'Blocks states')
        unique_together = ("user", "block_id")

    @staticmethod
    def get_for_block_id(block_id, user):
        """Returns current state of a block"""
        try:
            return BlockState.objects.get(block_id=block_id, user=user)
        except BlockState.DoesNotExist:
            #states = SettingValue.objects.filter(key__in=[SETTING_BLOCK_DEFAULT_STATE_IS_OPEN, SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS])
            states = {sv.key_id: sv.value
                        for sv in SettingValue.objects.filter(key_id__in=[SETTING_BLOCK_DEFAULT_STATE_IS_OPEN,
                                                                          SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS,
                                                                         ]
                                                             )
                     }

            #todo: optimisation does not work
            #is_default_open             = states.get(key=SETTING_BLOCK_DEFAULT_STATE_IS_OPEN).value
            #is_default_fields_displayed = states.get(key=SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS).value

            #return BlockState(block_id=block_id, is_open=is_default_open, show_empty_fields=is_default_fields_displayed, user=user)

            return BlockState(block_id=block_id, user=user,
                              is_open=states[SETTING_BLOCK_DEFAULT_STATE_IS_OPEN],
                              show_empty_fields=states[SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS],
                             )

    @staticmethod
    def get_for_block_ids(block_ids, user):
        """Get current states of blocks
        @params block_ids: a list of block ids
        @params user: owner of a blockstate
        @returns: a dict with block_id as key and state as value
        """
        states = {}

        #is_default_open = SettingValue.objects.get(key=SETTING_BLOCK_DEFAULT_STATE_IS_OPEN).value
        #is_default_fields_displayed = SettingValue.objects.get(key=SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS).value#TODO: Method for get_default_states?
        get_sv = SettingValue.objects.get #TODO: group queries ??
        is_default_open             = get_sv(key_id=SETTING_BLOCK_DEFAULT_STATE_IS_OPEN).value
        is_default_fields_displayed = get_sv(key_id=SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS).value #TODO: Method for get_default_states?

        for state in BlockState.objects.filter(block_id__in=block_ids, user=user):
            states[state.block_id] = state

        block_state = partial(BlockState, is_open=is_default_open, show_empty_fields=is_default_fields_displayed, user=user)
        for block_id in set(block_ids) - set(states.keys()):#Blocks with unset state
            states[block_id] = block_state(block_id=block_id)

        return states

    @property
    def classes(self):
        """Generate css classes for current state"""
        classes = []
        if not self.is_open:
            classes.append('collapsed')

        if not self.show_empty_fields:
            classes.append('hide_empty_fields')

        return ' '.join(classes)
