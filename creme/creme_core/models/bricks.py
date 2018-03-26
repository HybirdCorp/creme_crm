# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
import warnings

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import (CharField, TextField, ForeignKey, OneToOneField,
        PositiveIntegerField, PositiveSmallIntegerField, BooleanField, CASCADE)
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from ..constants import (SETTING_BLOCK_DEFAULT_STATE_IS_OPEN,
        SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS, MODELBLOCK_ID)
from ..utils import creme_entity_content_types
from .auth import UserRole
from .base import CremeModel
from .entity import CremeEntity
from .fields import CTypeForeignKey
from .fields_config import FieldsConfig
from .relation import RelationType
from .setting_value import SettingValue


__all__ = ('BlockDetailviewLocation', 'BlockPortalLocation', 'BlockMypageLocation',
           'RelationBlockItem', 'InstanceBlockConfigItem', 'CustomBlockConfigItem',
           'BlockState',
          )
logger = logging.getLogger(__name__)


class BlockDetailviewLocation(CremeModel):
    content_type = CTypeForeignKey(verbose_name=_(u'Related type'), null=True)
    role         = ForeignKey(UserRole, verbose_name=_(u'Related role'), null=True, default=None, on_delete=CASCADE)
    # TODO: a UserRole for superusers instead ??
    superuser    = BooleanField(u'related to superusers', default=False, editable=False)
    # block_id     = CharField(max_length=100)
    brick_id     = CharField(max_length=100)
    order        = PositiveIntegerField()
    zone         = PositiveSmallIntegerField()

    TOP    = 1
    LEFT   = 2
    RIGHT  = 3
    BOTTOM = 4
    HAT    = 5

    ZONES = (HAT, TOP, LEFT, RIGHT, BOTTOM)   # DEPRECATED
    ZONE_NAMES = {
        HAT:    'hat',
        TOP:    'top',
        LEFT:   'left',
        RIGHT:  'right',
        BOTTOM: 'bottom',
    }

    class Meta:
        app_label = 'creme_core'
        ordering = ('order',)

    def __repr__(self):
        return 'BlockDetailviewLocation(id={id}, content_type_id={ct_id}, role={role}, ' \
                                       'brick_id="{brick_id}", order={order}, zone={zone})'.format(
                id=self.id,
                ct_id=self.content_type_id,
                role='superuser' if self.superuser else self.role,
                brick_id=self.brick_id,
                order=self.order,
                zone=self.zone,
        )

    @staticmethod
    def create(block_id, order, zone, model=None, role=None):
        warnings.warn('BlockDetailviewLocation.create() is deprecated ; '
                      'use create_if_needed() instead.',
                      DeprecationWarning
                     )
        return BlockDetailviewLocation.create_if_needed(brick_id=block_id, order=order, zone=zone, model=model, role=role)

    @staticmethod
    def create_if_needed(brick_id, order, zone, model=None, role=None):
        """Create an instance of BlockDetailviewLocation, but if only if the related
        brick is not already on the configuration.
        @param zone: Value in BlockDetailviewLocation.{TOP|LEFT|RIGHT|BOTTOM}
        @param model: A class inheriting CremeEntity ; None means default configuration.
        @param role: Can be None (ie: 'Default configuration'), a UserRole instance,
                     or the string 'superuser'.
        """
        kwargs = {'role': None, 'superuser': False}

        if role:
            if model is None:
                raise ValueError('The default configuration cannot have a related role.')

            if role == 'superuser':
                kwargs['superuser'] = True
            else:
                kwargs['role'] = role

        return BlockDetailviewLocation.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(model) if model else None,
                    brick_id=brick_id,
                    defaults={'order': order, 'zone': zone},
                    **kwargs
                )[0]

    @staticmethod
    def create_4_model_brick(order, zone, model=None, role=None):
        return BlockDetailviewLocation.create_if_needed(brick_id=MODELBLOCK_ID, order=order, zone=zone, model=model, role=role)

    # @staticmethod
    # def create_4_model_block(order, zone, model=None, role=None):
    #     warnings.warn('BlockDetailviewLocation.create_4_model_block() is deprecated ; '
    #                   'use create_4_model_brick() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return BlockDetailviewLocation.create(MODELBLOCK_ID, order, zone, model, role)

    @staticmethod
    # def id_is_4_model(block_id):
    def id_is_4_model(brick_id):
        return brick_id == MODELBLOCK_ID

    @staticmethod
    def config_exists(model):
        ct = ContentType.objects.get_for_model(model)
        return BlockDetailviewLocation.objects.filter(content_type=ct).exists()

    @staticmethod
    def create_empty_config(model=None):
        warnings.warn('BlockDetailviewLocation.create_empty_config() is deprecated.',
                      DeprecationWarning
                     )

        ct = ContentType.objects.get_for_model(model) if model else None

        if not BlockDetailviewLocation.objects.filter(content_type=ct).exists():
            create = BlockDetailviewLocation.objects.create

            for zone in BlockDetailviewLocation.ZONES:
                create(content_type=ct, brick_id='', order=1, zone=zone)


class BlockPortalLocation(CremeModel):
    app_name = CharField(max_length=40)
    # block_id = CharField(max_length=100)
    brick_id = CharField(max_length=100)
    order    = PositiveIntegerField()

    class Meta:
        app_label = 'creme_core'
        ordering = ('order',)

    def __repr__(self):
        return 'BlockPortalLocation(id={id}, app_name={app}, brick_id={brick_id}, order={order})'.format(
                id=self.id, app=self.app_name, brick_id=self.brick_id, order=self.order,
            )

    @staticmethod
    def create(block_id, order, app_name=''):
        warnings.warn('BlockPortalLocation.create() is deprecated ; '
                      'use create_or_update() instead.',
                      DeprecationWarning
                     )
        return BlockPortalLocation.create_or_update(brick_id=block_id, order=order, app_name=app_name)

    @staticmethod
    def create_or_update(brick_id, order, app_name=''):
        try:
            loc = BlockPortalLocation.objects.get(app_name=app_name, brick_id=brick_id)
        except Exception:
            loc = BlockPortalLocation.objects.create(app_name=app_name, brick_id=brick_id, order=order)
        else:
            loc.order = order
            loc.save()

        return loc

    @staticmethod
    def create_empty_config(app_name=''):
        warnings.warn('BlockPortalLocation.create_empty_config() is deprecated.',
                      DeprecationWarning
                     )

        if not BlockPortalLocation.objects.filter(app_name=app_name).exists():
            BlockPortalLocation.objects.create(app_name=app_name, brick_id='', order=1)

    # @property
    # def block_verbose_name(self):
    #     warnings.warn('BlockPortalLocation.block_verbose_name is deprecated ; use brick_verbose_name instead.',
    #                   DeprecationWarning
    #                  )
    #     return self.brick_verbose_name

    @property
    def brick_verbose_name(self):
        from ..gui.bricks import brick_registry

        return next(brick_registry.get_bricks((self.brick_id,))).verbose_name


# TODO: merge with BlockPortalLocation when portals have been removed ?
class BlockMypageLocation(CremeModel):
    user     = ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=CASCADE)
    # block_id = CharField(max_length=100)
    brick_id = CharField(max_length=100)
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
            from django.db.transaction import atomic

            create = BlockMypageLocation.objects.create

            with atomic():
                try:
                    for loc in BlockMypageLocation.objects.filter(user=None):
                        create(user=instance, brick_id=loc.brick_id, order=loc.order)
                except Exception:
                    # TODO: still useful ? (BlockMypageLocation table should exist when the first User is created)
                    logger.warn('Can not create brick config for this user: %s'
                                ' (if it is the first user, do not worry because it is normal)' % instance
                               )

    @staticmethod
    def create(block_id, order, user=None):
        warnings.warn('BlockMypageLocation.create() is deprecated ; '
                      'use create_or_update() instead.',
                      DeprecationWarning
                     )

        return BlockMypageLocation.create_or_update(brick_id=block_id, order=order, user=user)

    @staticmethod
    def create_or_update(brick_id, order, user=None):
        try:
            loc = BlockMypageLocation.objects.get(user=user, brick_id=brick_id)
        except Exception:
            loc = BlockMypageLocation.objects.create(user=user, brick_id=brick_id, order=order)
        else:
            loc.order = order
            loc.save()

        return loc

    # @property
    # def block_verbose_name(self):
    #     warnings.warn('BlockMypageLocation.block_verbose_name is deprecated ; use brick_verbose_name instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     from creme.creme_core.gui.bricks import brick_registry
    #
    #     return brick_registry.get_blocks((self.block_id,))[0].verbose_name

    # TODO: factorise ?
    @property
    def brick_verbose_name(self):
        from creme.creme_core.gui.bricks import brick_registry

        return next(brick_registry.get_bricks((self.brick_id,))).verbose_name


post_save.connect(BlockMypageLocation._copy_default_config, sender=settings.AUTH_USER_MODEL,
                  dispatch_uid='creme_core-blockmypagelocation._copy_default_config'
                 )


class RelationBlockItem(CremeModel):
    # TODO: 'brick_id' not really useful (can be dynamically generated with the RelationType)
    #        + in the 'brick_id': 1)remove the app_name  2)"specificblock_" => "rtypebrick_" (need data migration)
    # block_id       = CharField(_(u"Block ID"), max_length=100, editable=False)
    brick_id       = CharField(_(u'Block ID'), max_length=100, editable=False)
    relation_type  = OneToOneField(RelationType, verbose_name=_(u'Related type of relationship'), on_delete=CASCADE)
    json_cells_map = TextField(editable=False, null=True)  # TODO: JSONField  # TODO: null=False ('{}' by default with current code)

    _cells_map = None

    class Meta:
        app_label = 'creme_core'

    def __init__(self, *args, **kwargs):
        super(RelationBlockItem, self).__init__(*args, **kwargs)
        if self.json_cells_map is None:
            self._cells_map = {}
            self._dump_cells_map()

    def __unicode__(self):  # NB: useful for creme_config titles
        return self.relation_type.predicate

    def delete(self, using=None):
        BlockDetailviewLocation.objects.filter(brick_id=self.brick_id).delete()

        super(RelationBlockItem, self).delete(using=using)

    @property
    def all_ctypes_configured(self):
        # TODO: cache (object_ctypes) ??
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
            from creme.creme_core.gui.bricks import SpecificRelationsBrick
            rbi = RelationBlockItem.objects.create(
                brick_id=SpecificRelationsBrick.generate_id('creme_config', relation_type_id),
                relation_type_id=relation_type_id,
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
                cells, errors = build(model=ct.model_class(), dicts=cells_as_dicts)  # TODO: do it lazily ??

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
            yield get_ct(ct_id), cells  # TODO: copy dicts ?? (if 'yes' -> iter_ctypes() too)

    def set_cells(self, ctype, cells):
        self._cells_by_ct()[ctype.id] = cells
        self._dump_cells_map()


class InstanceBlockConfigItem(CremeModel):
    # block_id = CharField(_(u'Brick ID'), max_length=300, blank=False, null=False, editable=False)
    brick_id = CharField(_(u'Brick ID'), max_length=300, blank=False, null=False, editable=False)
    entity   = ForeignKey(CremeEntity, verbose_name=_(u'Block related entity'), on_delete=CASCADE)
    data     = TextField(blank=True, null=True)
    verbose  = CharField(_(u'Verbose'), max_length=200, blank=True, null=True)  # TODO: remove

    # _block = None
    _brick = None

    class Meta:
        app_label = 'creme_core'
        ordering = ('id',)

    def __unicode__(self):
        return self.brick.verbose_name

    def delete(self, using=None):
        brick_id = self.brick_id
        BlockDetailviewLocation.objects.filter(brick_id=brick_id).delete()
        BlockState.objects.filter(brick_id=brick_id).delete()

        super(InstanceBlockConfigItem, self).delete(using=using)

    # @property
    # def block(self):
    #     warnings.warn('InstanceBlockConfigItem.block is deprecated ; use "brick" instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return self.brick

    @property
    def brick(self):
        brick = self._brick

        if brick is None:
            from ..gui.bricks import brick_registry
            self._brick = brick = brick_registry.get_brick_4_instance(self, entity=self.entity)

        return brick

    @property
    def errors(self):
        return getattr(self.brick, 'errors', None)

    @staticmethod
    # def id_is_specific(block_id):
    def id_is_specific(brick_id):
        return brick_id.startswith(u'instanceblock_')

    @staticmethod
    def generate_base_id(app_name, name):
        return u'instanceblock_%s-%s' % (app_name, name)

    @staticmethod
    # def generate_id(block_class, entity, key):
    def generate_id(brick_class, entity, key):
        """@param key: String that allows to make the difference between 2 instances
                       of the same Block class and the same CremeEntity instance.
        """
        if key and any((c in key) for c in ('#', '@', '&', ':', ' ')):
            raise ValueError('InstanceBlockConfigItem.generate_id: usage of a '
                             'forbidden character in key "%s"' % key
                            )

        # return u'%s|%s-%s' % (block_class.id_, entity.id, key)
        return u'%s|%s-%s' % (brick_class.id_, entity.id, key)

    @staticmethod
    # def get_base_id(block_id):
    def get_base_id(brick_id):
        return brick_id.split('|', 1)[0]


class CustomBlockConfigItem(CremeModel):
    id           = CharField(primary_key=True, max_length=100, editable=False)
    content_type = CTypeForeignKey(verbose_name=_(u'Related type'), editable=False)
    name         = CharField(_(u'Name'), max_length=200)
    json_cells   = TextField(editable=False, null=True)  # TODO: JSONField  # TODO: null=False

    _cells = None

    class Meta:
        app_label = 'creme_core'

    def __init__(self, *args, **kwargs):
        super(CustomBlockConfigItem, self).__init__(*args, **kwargs)
        if self.json_cells is None:
            self.cells = []

    def __unicode__(self):
        return self.name

    def delete(self, using=None):
        brick_id = self.generate_id()
        BlockDetailviewLocation.objects.filter(brick_id=brick_id).delete()
        BlockState.objects.filter(brick_id=brick_id).delete()

        super(CustomBlockConfigItem, self).delete(using=using)

    def generate_id(self):
        return 'customblock-%s' % self.id

    # @staticmethod
    # def id_from_block_id(block_id):
    #     warnings.warn('CustomBlockConfigItem.id_from_block_id() is deprecated ; use id_from_brick_id() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return CustomBlockConfigItem.id_from_brick_id(block_id)

    @staticmethod
    def id_from_brick_id(brick_id):
        try:
            prefix, cbci_id = brick_id.split('-', 1)
        except ValueError:  # Unpacking error
            return None

        return None if prefix != 'customblock' else cbci_id

    def _dump_cells(self, cells):
        self.json_cells = jsondumps([cell.to_dict() for cell in cells])

    # TODO: factorise with HeaderFilter.cells
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

    @cells.setter
    def cells(self, cells):
        self._cells = cells = [cell for cell in cells if cell]
        self._dump_cells(cells)

    @property
    def filtered_cells(self):
        """Generators which yields EntityCell instances, but it excluded the
        ones which are related to fields hidden with FieldsConfig.
        """
        return FieldsConfig.filter_cells(self.content_type.model_class(), self.cells)


class BlockState(CremeModel):
    user              = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE)
    # block_id          = CharField(_(u"Block ID"), max_length=100)
    brick_id          = CharField(_(u"Block ID"), max_length=100)
    is_open           = BooleanField(default=True)  # Is brick has to appear as opened or closed
    show_empty_fields = BooleanField(default=True)  # Are empty fields in brick have to be shown or not

    class Meta:
        app_label = 'creme_core'
        unique_together = ('user', 'brick_id')

    # @staticmethod
    # def get_for_block_id(block_id, user):
    #     warnings.warn('BlockState.get_for_block_id() is deprecated ; use get_for_brick_id() instead.',
    #                   DeprecationWarning
    #                  )
    #     return BlockState.get_for_brick_id(block_id, user)

    @staticmethod
    def get_for_brick_id(brick_id, user):
        """Returns current state of a brick"""
        try:
            return BlockState.objects.get(brick_id=brick_id, user=user)
        except BlockState.DoesNotExist:
            states = {sv.key_id: sv.value
                        for sv in SettingValue.objects.filter(key_id__in=[SETTING_BLOCK_DEFAULT_STATE_IS_OPEN,
                                                                          SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS,
                                                                         ],
                                                             )
                     }

            return BlockState(brick_id=brick_id, user=user,
                              is_open=states[SETTING_BLOCK_DEFAULT_STATE_IS_OPEN],
                              show_empty_fields=states[SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS],
                             )

    # @staticmethod
    # def get_for_block_ids(block_ids, user):
    #     warnings.warn('BlockState.get_for_block_ids() is deprecated ; use get_for_brick_ids() instead.',
    #                   DeprecationWarning
    #                  )
    #     return BlockState.get_for_brick_ids(block_ids, user)

    @staticmethod
    def get_for_brick_ids(brick_ids, user):
        """Get current states of bricks
        @param brick_ids: a list of brick ids.
        @param user: owner of a BlockState.
        @returns: a dict with block_id as key and state as value
        """
        states = {}

        # TODO: Method for get_default_states?
        get_sv = SettingValue.objects.get  # TODO: group queries ?? + cache ?
        is_default_open             = get_sv(key_id=SETTING_BLOCK_DEFAULT_STATE_IS_OPEN).value
        is_default_fields_displayed = get_sv(key_id=SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS).value

        for state in BlockState.objects.filter(brick_id__in=brick_ids, user=user):
            states[state.brick_id] = state

        block_state = partial(BlockState, is_open=is_default_open, user=user,
                              show_empty_fields=is_default_fields_displayed,
                             )

        for brick_id in set(brick_ids) - set(states.keys()):  # Bricks with unset state
            states[brick_id] = block_state(brick_id=brick_id)

        return states

    # @property
    # def classes(self):
    #     """Generate CSS classes for current state"""
    #     warnings.warn('BlockState.classes is deprecated ; '
    #                   'use the templatetag creme_bricks.brick_state_classes instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     classes = []
    #     if not self.is_open:
    #         classes.append('collapsed')
    #
    #     if not self.show_empty_fields:
    #         classes.append('hide_empty_fields')
    #
    #     return ' '.join(classes)
