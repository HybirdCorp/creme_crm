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

from imp import find_module
from functools import partial
from logging import warn

from django.db.models import (CharField, ForeignKey, PositiveIntegerField, 
                              PositiveSmallIntegerField, BooleanField, TextField)
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeModel, RelationType, CremeEntity
from creme_core.constants import SETTING_BLOCK_DEFAULT_STATE_IS_OPEN, SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS, MODELBLOCK_ID

from creme_config.models.setting import SettingValue


__all__ = ('BlockDetailviewLocation', 'BlockPortalLocation', 'BlockMypageLocation',
           'RelationBlockItem', 'InstanceBlockConfigItem',
           'BlockState',
          )


class BlockDetailviewLocation(CremeModel):
    content_type = ForeignKey(ContentType, verbose_name=_(u"Related type"), null=True)
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

    def __repr__(self):
        return 'BlockDetailviewLocation(id=%s, content_type_id=%s, block_id=%s, order=%s, zone=%s)' % (
                self.id, self.content_type_id, self.block_id, self.order, self.zone
            )

    @staticmethod
    def create(block_id, order, zone, model=None):
        ct = ContentType.objects.get_for_model(model) if model else None

        try:
            loc = BlockDetailviewLocation.objects.get(content_type=ct, block_id=block_id)
        except Exception:
            loc = BlockDetailviewLocation.objects.create(content_type=ct, block_id=block_id, order=order, zone=zone)
        else:
            loc.order = order
            loc.zone  = zone
            loc.save()

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

    def __repr__(self):
        return 'BlockMypageLocation(id=%s, user=%s)' % (
                self.id, self.user_id
            )

    @staticmethod
    def _copy_default_config(sender, instance, created, **kwargs):
        if created:
            create = BlockMypageLocation.objects.create

            try:
                for loc in BlockMypageLocation.objects.filter(user=None):
                    create(user=instance, block_id=loc.block_id, order=loc.order)
            except Exception:
                warn('Can not create block config for this user: %s (if it is the first user, do not worry because it is normal)' % instance)

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
        from creme_core.gui.block import block_registry
        try:
            return block_registry[self.block_id].verbose_name
        except:
            return '???'


post_save.connect(BlockMypageLocation._copy_default_config, sender=User,
                  dispatch_uid='creme_core-blockmypagelocation._copy_default_config'
                 )


class RelationBlockItem(CremeModel):
    block_id      = CharField(_(u"Block ID"), max_length=100) #really useful ?? (can be retrieved with type)
    relation_type = ForeignKey(RelationType, verbose_name=_(u"Related type of relation"), unique=True)

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Specific relation block')
        verbose_name_plural = _(u'Specific relation blocks')

    def delete(self):
        BlockDetailviewLocation.objects.filter(block_id=self.block_id).delete()

        super(RelationBlockItem, self).delete()

    @staticmethod
    def create(relation_type_id):
        try:
            rbi = RelationBlockItem.objects.get(relation_type=relation_type_id)
        except RelationBlockItem.DoesNotExist:
            from creme_core.gui.block import SpecificRelationsBlock
            rbi = RelationBlockItem.objects.create(block_id=SpecificRelationsBlock.generate_id('creme_config', relation_type_id),
                                                   relation_type_id=relation_type_id
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
        BlockDetailviewLocation.objects.filter(block_id=self.block_id).delete()

        super(InstanceBlockConfigItem, self).delete()

    @staticmethod
    def id_is_specific(block_id):
        return block_id.startswith(u'instanceblock-') #TODO: use constant

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


class BlockState(CremeModel):
    user               = ForeignKey(User)
    block_id           = CharField(_(u"Block ID"), max_length=100)
    is_open            = BooleanField(default=True)#Is block has to appear as opened or closed
    show_empty_fields  = BooleanField(default=True)#Are empty fields in block have to be shown or not

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Block state')
        verbose_name_plural = _(u'Blocks states')
        unique_together = ("user", "block_id")

    @staticmethod
    def get_for_block_id(block_id, user):
        """Returns current state of a block"""
        try:
            return BlockState.objects.get(block_id=block_id, user=user)
        except BlockState.DoesNotExist:
            states = SettingValue.objects.filter(key__in=[SETTING_BLOCK_DEFAULT_STATE_IS_OPEN, SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS])

            #TODO: optimisation does not work
            is_default_open             = states.get(key=SETTING_BLOCK_DEFAULT_STATE_IS_OPEN).value
            is_default_fields_displayed = states.get(key=SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS).value

#            is_default_open = SettingValue.objects.get(key=SETTING_BLOCK_DEFAULT_STATE_IS_OPEN).value
#            is_default_fields_displayed = SettingValue.objects.get(key=SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS).value
            return BlockState(block_id=block_id, is_open=is_default_open, show_empty_fields=is_default_fields_displayed, user=user)

    @staticmethod
    def get_for_block_ids(block_ids, user):
        """Get current states of blocks

            @params block_ids: a list of block ids
            @params user: owner of a blockstate
            @returns: a dict with block_id as key and state as value
        """
        states = {}

        is_default_open = SettingValue.objects.get(key=SETTING_BLOCK_DEFAULT_STATE_IS_OPEN).value
        is_default_fields_displayed = SettingValue.objects.get(key=SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS).value#TODO: Method for get_default_states?

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
