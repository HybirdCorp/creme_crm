################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from __future__ import annotations

import logging
# import warnings
from functools import partial
from typing import TYPE_CHECKING, Iterable, Iterator, Sequence, TypedDict

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models  # IntegrityError
from django.db.models import ProtectedError
from django.db.models.signals import post_save
from django.db.transaction import atomic
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..constants import (
    MODELBRICK_ID,
    SETTING_BRICK_DEFAULT_STATE_IS_OPEN,
    SETTING_BRICK_DEFAULT_STATE_SHOW_EMPTY_FIELDS,
)
from ..utils.content_type import entity_ctypes
from .auth import UserRole
from .base import CremeModel
from .entity import CremeEntity
from .fields import CTypeForeignKey
from .relation import RelationType
from .setting_value import SettingValue

if TYPE_CHECKING:
    from ..core.entity_cell import EntityCell
    from ..gui.bricks import Brick, InstanceBrick

__all__ = (
    'BrickDetailviewLocation', 'BrickHomeLocation', 'BrickMypageLocation',
    'RelationBrickItem', 'InstanceBrickConfigItem', 'CustomBrickConfigItem',
    'BrickState',
)
logger = logging.getLogger(__name__)


class BrickDetailviewLocationManager(models.Manager):
    # TODO: Enum for zone
    def create_if_needed(
            self,
            brick: type[Brick] | str,
            order: int,
            zone: int,
            model: type[CremeEntity] | ContentType | None = None,
            role: None | UserRole | str = None) -> BrickDetailviewLocation:
        """Create an instance of BrickDetailviewLocation, but only if the
        related brick is not already on the configuration.
        @param brick: Brick ID (string) or Brick class.
        @param order: Integer (see 'BrickDetailviewLocation.order').
        @param zone: Value in BrickDetailviewLocation.{TOP|LEFT|RIGHT|BOTTOM}
        @param model: Model corresponding to this configuration ; it can be :
               - A class inheriting CremeEntity.
               - An instance of ContentType (corresponding to a model inheriting CremeEntity).
               - None, which means <default configuration>.
        @param role: Can be None (i.e. 'Default configuration'), a UserRole instance,
               or the string 'superuser'.
        """
        class Kwargs(TypedDict):
            role: UserRole | None
            superuser: bool

        kwargs: Kwargs = {'role': None, 'superuser': False}

        if role:
            if model is None:
                raise ValueError('The default configuration cannot have a related role.')

            # if role == 'superuser':
            if isinstance(role, str):
                assert role == 'superuser'
                kwargs['superuser'] = True
            else:
                kwargs['role'] = role

        return self.get_or_create(
            content_type=(
                model
                if model is None or isinstance(model, ContentType) else
                ContentType.objects.get_for_model(model)
            ),
            # brick_id=brick if isinstance(brick, str) else brick.id_,
            brick_id=brick if isinstance(brick, str) else brick.id,
            defaults={'order': order, 'zone': zone},
            **kwargs
        )[0]

    def create_for_model_brick(self,
                               order: int,
                               zone: int,
                               model: type[CremeEntity] | ContentType | None = None,
                               role: None | UserRole | str = None,
                               ) -> BrickDetailviewLocation:
        return self.create_if_needed(
            brick=MODELBRICK_ID, order=order,
            zone=zone, model=model, role=role,
        )

    def filter_for_model(self, model: type[CremeEntity]) -> models.QuerySet:
        return self.filter(
            content_type=ContentType.objects.get_for_model(model),
        )

    def multi_create(self, *,
                     defaults: dict | None = None,
                     data: Iterable[dict],
                     ) -> list[BrickDetailviewLocation]:
        """Create several instances at once.
        Each instance is created only if related brick is not already on the
        configuration.

        @param defaults: dictionary used for default value of arguments.
               <None> means no default argument.
        @param data: Iterable of dictionaries used as creation arguments
               (see create_if_needed() for arguments).

        Each dictionary of 'data' is combined with 'defaults' ; notice that
        if no "brick" argument is given, the method create_for_model_brick()
        is used.
        """
        locations = []

        if defaults is None:
            defaults = {}

        for kwargs in data:
            final_kwargs = {**defaults, **kwargs}
            locations.append(
                self.create_if_needed(**final_kwargs)
                if 'brick' in final_kwargs else
                self.create_for_model_brick(**final_kwargs)
            )

        return locations


class BrickDetailviewLocation(CremeModel):
    content_type = CTypeForeignKey(verbose_name=_('Related type'), null=True)

    role = models.ForeignKey(
        UserRole, verbose_name=_('Related role'),
        null=True, default=None, on_delete=models.CASCADE,
    )
    # TODO: a UserRole for superusers instead ??
    superuser = models.BooleanField(
        'related to superusers', default=False, editable=False,
    )

    brick_id = models.CharField(max_length=100)
    order = models.PositiveIntegerField()
    zone = models.PositiveSmallIntegerField()

    objects = BrickDetailviewLocationManager()

    TOP    = 1
    LEFT   = 2
    RIGHT  = 3
    BOTTOM = 4
    HAT    = 5

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
        return (
            'BrickDetailviewLocation('
            'id={id}, content_type_id={ct_id}, role={role}, '
            'brick_id="{brick_id}", order={order}, zone={zone}'
            ')'.format(
                id=self.id,
                ct_id=self.content_type_id,
                role='superuser' if self.superuser else self.role,
                brick_id=self.brick_id,
                order=self.order,
                zone=self.zone,
            )
        )

    def __str__(self):
        # TODO: @property "brick" ?? (or method to pass registry)
        from ..gui.bricks import brick_registry  # TODO: in attribute ?

        ct = self.content_type
        role = self.role

        if ct is None:
            msg = gettext(
                'Default block configuration for detail-views uses «{block}»'
            )
        elif role:
            msg = gettext(
                'Block configuration for detail-views of «{model}» '
                'for role «{role}» uses «{block}»'
            )
        elif self.superuser:
            msg = gettext(
                'Block configuration for detail-views of «{model}» '
                'for superusers uses «{block}»'
            )
        else:
            msg = gettext(
                'Block configuration for detail-views of «{model}» uses «{block}»'
            )

        model = ct.model_class() if ct else CremeEntity
        brick = next(
            (brick_registry.get_bricks(brick_ids=(self.brick_id,), entity=model())),
            None
        )

        return msg.format(
            model=ct, role=role, block='??' if brick is None else brick.verbose_name,
        )


class BrickHomeLocation(CremeModel):
    role = models.ForeignKey(
        UserRole, verbose_name=_('Related role'),
        null=True, default=None, on_delete=models.CASCADE,
    )
    # TODO: a UserRole for superusers instead ??
    superuser = models.BooleanField(
        'related to superusers', default=False, editable=False,
    )

    brick_id = models.CharField(max_length=100)
    order = models.PositiveIntegerField()

    class Meta:
        app_label = 'creme_core'
        ordering = ('order',)

    def __repr__(self):
        return (
            'BrickHomeLocation('
            'id={id}, role={role}, brick_id={brick_id}, order={order}'
            ')'.format(
                id=self.id, brick_id=self.brick_id, order=self.order,
                role='superuser' if self.superuser else self.role,
            )
        )

    def __str__(self):
        # return repr(self)
        # TODO: see remark in BrickDetailviewLocation.__str__
        #  (+ see uses of {% brick_get_by_ids %}
        from ..gui.bricks import brick_registry

        role = self.role

        if role:
            msg = gettext(
                'Block configuration of Home for role «{role}» uses «{block}»'
            )
        elif self.superuser:
            msg = gettext(
                'Block configuration of Home for superusers uses «{block}»'
            )
        else:
            msg = gettext('Block configuration of Home uses «{block}»')

        return msg.format(
            role=role,
            block=next(brick_registry.get_bricks((self.brick_id,))).verbose_name,
        )


class BrickMypageLocation(CremeModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)
    brick_id = models.CharField(max_length=100)
    order = models.PositiveIntegerField()

    class Meta:
        app_label = 'creme_core'
        ordering = ('order',)

    def __repr__(self):
        return f'BrickMypageLocation(id={self.id}, user={self.user_id})'

    def __str__(self):
        # TODO: see remark in BrickDetailviewLocation.__str__
        from ..gui.bricks import brick_registry

        user = self.user
        msg = gettext(
            'Block configuration of "My page" for «{user}» uses «{block}»'
        ) if user else gettext(
            'Default block configuration of "My page" uses «{block}»'
        )

        return msg.format(
            user=user,
            block=next(brick_registry.get_bricks((self.brick_id,))).verbose_name,
        )

    @classmethod
    def _copy_default_config(cls, sender, instance, created, **kwargs):
        if created:
            create = cls.objects.create

            with atomic():
                for loc in cls.objects.filter(user=None):
                    create(user=instance, brick_id=loc.brick_id, order=loc.order)


post_save.connect(
    BrickMypageLocation._copy_default_config,
    sender=settings.AUTH_USER_MODEL,
    dispatch_uid='creme_core-brickmypagelocation._copy_default_config',
)


class StoredBrickClassMixin:
    @staticmethod
    def check_detail_configuration(brick_id: str):
        locations = BrickDetailviewLocation.objects.filter(brick_id=brick_id)

        if locations:
            def get_message():
                for loc in locations:
                    if loc.content_type is None:
                        return gettext(
                            'This block is used in the default detail-view configuration'
                        )

                for loc in locations:
                    if not loc.superuser and loc.role is None:
                        return gettext(
                            'This block is used in the detail-view configuration of «{model}»'
                        ).format(model=loc.content_type)

                for loc in locations:
                    if loc.superuser:
                        return gettext(
                            'This block is used in the detail-view configuration '
                            'of «{model}» for superusers'
                        ).format(model=loc.content_type)

                for loc in locations:
                    if loc.role is not None:
                        return gettext(
                            'This block is used in the detail-view configuration '
                            'of «{model}» for role «{role}»'
                        ).format(model=loc.content_type, role=loc.role)

                return 'This block is used in a detail-view configuration (unexpected case)'

            raise ProtectedError(get_message(), [*locations])

    @staticmethod
    def check_home_configuration(brick_id: str):
        locations = BrickHomeLocation.objects.filter(brick_id=brick_id)

        if locations:
            if any(not hl.superuser and hl.role is None for hl in locations):
                msg = gettext(
                    'This block is used in the default Home configuration'
                )
            elif any(hl.superuser for hl in locations):
                msg = gettext(
                    'This block is used in the Home configuration for superusers'
                )
            else:
                for hl in locations:
                    if hl.role:
                        msg = gettext(
                            'This block is used in the Home configuration of role «{}»'
                        ).format(hl.role)
                        break
                else:
                    msg = 'This block is used in the Home configuration (unexpected case)'

            raise ProtectedError(msg, [*locations])

    @staticmethod
    def check_mypage_configuration(brick_id: str):
        locations = BrickMypageLocation.objects.filter(brick_id=brick_id)

        if locations:
            if any(mpl.user is None for mpl in locations):
                msg = gettext(
                    'This block is used in the default configuration for "My page"'
                )
            else:
                for mpl in locations:
                    if mpl.user:
                        msg = gettext(
                            'This block is used in the configuration of «{}» for "My page"'
                        ).format(mpl.user)
                        break
                else:
                    msg = 'This block is used in the "My page" configuration (unexpected case)'

            raise ProtectedError(msg, [*locations])


# TODO: remove this class?
class RelationBrickItemManager(models.Manager):
    pass
    # def create_if_needed(self, relation_type: RelationType | str) -> RelationBrickItem:
    #     """Create an instance of RelationBrickItem corresponding to a RelationType
    #     or return the existing one.
    #
    #     @param relation_type: Instance of RelationType, or RelationType ID.
    #     @return: A saved instance of RelationBrickItem.
    #     """
    #     # from creme.creme_core.gui.bricks import SpecificRelationsBrick
    #     warnings.warn(
    #         'The method RelationBrickItemManager.create_if_needed() is deprecated ; '
    #         'use <get_or_create(relation_type=rtype)[0]> instead.',
    #         DeprecationWarning,
    #     )
    #
    #     rtype_id = relation_type.id if isinstance(relation_type, RelationType) else relation_type
    #
    #     for _i in range(10):
    #         try:
    #             rbi = self.get(relation_type=rtype_id)
    #         except self.model.DoesNotExist:
    #             try:
    #                 rbi = self.create(
    #                     # brick_id=SpecificRelationsBrick.generate_id('creme_config', rtype_id),
    #                     relation_type_id=rtype_id,
    #                 )
    #             except IntegrityError:
    #                 logger.exception(
    #                     'Avoid a RelationBrickItem duplicate: %s ?!',
    #                     relation_type,
    #                 )
    #                 continue
    #
    #         break
    #     else:
    #         raise RuntimeError(
    #             f'It seems the RelationBrickItem <{rtype_id}> keeps being '
    #             f'created & deleted.'
    #         )
    #
    #     return rbi


class RelationBrickItem(StoredBrickClassMixin, CremeModel):
    relation_type = models.OneToOneField(
        RelationType, on_delete=models.CASCADE,
        verbose_name=_('Related type of relationship'),
    )
    json_cells_map = models.JSONField(editable=False, default=dict)

    objects = RelationBrickItemManager()

    creation_label = _('Create a type of block')
    save_label     = _('Save the block')

    _cells_map = None
    _brick_id_prefix = 'rtype_brick'

    class Meta:
        app_label = 'creme_core'

    def __str__(self):  # NB: useful for creme_config titles
        return self.relation_type.predicate

    def delete(self, *args, **kwargs):
        brick_id = self.brick_id
        self.check_detail_configuration(brick_id)

        BrickState.objects.filter(brick_id=brick_id).delete()

        super().delete(*args, **kwargs)

    @property
    def all_ctypes_configured(self) -> bool:
        # TODO: cache (object_ctypes) ??
        compat_ctype_ids = {
            *self.relation_type.object_ctypes.values_list('id', flat=True),
        } or {ct.id for ct in entity_ctypes()}

        for ct_id in self._cells_by_ct():
            compat_ctype_ids.discard(ct_id)

        return not bool(compat_ctype_ids)

    @property
    def brick_id(self) -> str:
        my_id = self.id

        if my_id is None:
            raise ValueError(
                f'{type(self).__name__}.brick_id: must be called on a saved instance.'
            )

        return f'{self._brick_id_prefix}-{my_id}'

    @classmethod
    def id_from_brick_id(cls, brick_id: str) -> int | None:
        try:
            prefix, rbi_id = brick_id.split('-', 1)
        except ValueError:  # Unpacking error
            return None

        if prefix != cls._brick_id_prefix:
            return None

        try:
            return int(rbi_id)
        except ValueError:
            logger.critical(
                '%s.id_from_brick_id(): invalid instance ID stored in Brick ID: %s',
                cls.__name__, brick_id,
            )

        return None

    def _dump_cells_map(self):
        self.json_cells_map = {
            ct_id: [cell.to_dict() for cell in cells]
            for ct_id, cells in self._cells_map.items()
        }

    def _cells_by_ct(self):
        cells_map = self._cells_map

        if cells_map is None:
            from ..core.entity_cell import CELLS_MAP

            self._cells_map = cells_map = {}
            get_ct = ContentType.objects.get_for_id
            build = CELLS_MAP.build_cells_from_dicts
            total_errors = False

            for ct_id, cells_as_dicts in self.json_cells_map.items():
                ct = get_ct(ct_id)
                # TODO: do it lazily ??
                cells, errors = build(model=ct.model_class(), dicts=cells_as_dicts)

                if errors:
                    total_errors = True

                cells_map[ct.id] = cells

            if total_errors:
                logger.warning('RelationBrickItem (id="%s") is saved with valid cells.', self.id)
                self._dump_cells_map()
                self.save()

        return cells_map

    def delete_cells(self, ctype: ContentType) -> None:
        del self._cells_by_ct()[ctype.id]
        self._dump_cells_map()

    # TODO: accept model too ?
    def get_cells(self, ctype: ContentType) -> list[EntityCell]:
        return self._cells_by_ct().get(ctype.id)

    def iter_cells(self) -> Iterator[tuple[ContentType, list[EntityCell]]]:
        "Beware: do not modify the returned objects."
        get_ct = ContentType.objects.get_for_id

        for ct_id, cells in self._cells_by_ct().items():
            yield get_ct(ct_id), cells  # TODO: copy dicts ?? (if 'yes' -> iter_ctypes() too)

    # TODO: accept model too ?
    def set_cells(self, ctype: ContentType, cells: list[EntityCell]) -> RelationBrickItem:
        self._cells_by_ct()[ctype.id] = cells
        self._dump_cells_map()

        return self


class InstanceBrickConfigItem(StoredBrickClassMixin, CremeModel):
    brick_class_id = models.CharField(
        'Block class ID',
        max_length=300, editable=False,
    )
    entity = models.ForeignKey(
        CremeEntity,
        verbose_name=_('Block related entity'),
        on_delete=models.CASCADE, editable=False,
    )

    # NB1: do not use directly ; use the function get_extra_data() & set_extra_data()
    # NB: if you want to refer instances, you should store UUID instead of local
    #     IDs, in order to make import/export more reliable.
    json_extra_data = models.JSONField(
        editable=False,
        default=dict,
    ).set_tags(viewable=False)

    creation_label = _('Create a block')
    save_label     = _('Save the block')

    _brick: InstanceBrick | None = None
    # TODO: 'instance_brick'
    _brick_id_prefix = 'instanceblock'

    class Meta:
        app_label = 'creme_core'
        ordering = ('id',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._extra_data = self.json_extra_data

    def __str__(self):
        return self.brick.verbose_name

    @atomic
    def delete(self, *args, **kwargs):
        brick_id = self.brick_id
        self.check_detail_configuration(brick_id)
        self.check_home_configuration(brick_id)
        self.check_mypage_configuration(brick_id)

        BrickState.objects.filter(brick_id=brick_id).delete()

        super().delete(*args, **kwargs)

    @property
    def brick(self) -> InstanceBrick:
        brick = self._brick

        if brick is None:
            from ..gui.bricks import brick_registry
            self._brick = brick = brick_registry.get_brick_4_instance(self, entity=self.entity)

        return brick

    @property
    def brick_id(self) -> str:
        my_id = self.id

        if my_id is None:
            raise ValueError(
                f'{type(self).__name__}.brick_id: must be called on a saved instance.'
            )

        return f'{self._brick_id_prefix}-{my_id}'

    # TODO ?
    # def del_extra_data(self, key: str) -> None:
    #     del self._extra_data[key]

    def get_extra_data(self, key: str):
        return self._extra_data.get(key)

    def set_extra_data(self, key: str, value) -> bool:
        old_value = self._extra_data.get(key)
        self._extra_data[key] = value

        return old_value != value

    @property
    def extra_data_items(self):
        return iter(self._extra_data.items())

    @classmethod
    def id_from_brick_id(cls, brick_id: str) -> int | None:
        try:
            prefix, ibci_id = brick_id.split('-', 1)
        except ValueError:  # Unpacking error
            return None

        if prefix != cls._brick_id_prefix:
            return None

        try:
            return int(ibci_id)
        except ValueError:
            logger.critical(
                '%s.id_from_brick_id(): invalid instance ID stored in Brick ID: %s',
                cls.__name__, brick_id,
            )

        return None

    @classmethod
    def generate_base_id(cls, app_name: str, name: str) -> str:
        return f'{cls._brick_id_prefix}_{app_name}-{name}'

    def save(self, **kwargs):
        # Should we manage argument 'update_fields'? (if you set explicitly the
        # extra data you probably save() the field explicitly...)
        self.json_extra_data = self._extra_data
        super().save(**kwargs)


class CustomBrickConfigItem(StoredBrickClassMixin, CremeModel):
    id = models.CharField(primary_key=True, max_length=100, editable=False)
    content_type = CTypeForeignKey(verbose_name=_('Related type'), editable=False)
    name = models.CharField(_('Name'), max_length=200)
    json_cells = models.JSONField(editable=False, default=list)

    _cells = None

    # TODO: replace by "custom_brick" (needs data migration)
    _brick_id_prefix = 'customblock'

    class Meta:
        app_label = 'creme_core'

    def __str__(self):
        return self.name

    @property
    def brick_id(self) -> str:
        return f'{self._brick_id_prefix}-{self.id}'

    @atomic
    def delete(self, *args, **kwargs):
        brick_id = self.brick_id
        self.check_detail_configuration(brick_id)

        BrickState.objects.filter(brick_id=brick_id).delete()

        super().delete(*args, **kwargs)

    @classmethod
    def id_from_brick_id(cls, brick_id: str) -> str | None:
        try:
            prefix, cbci_id = brick_id.split('-', 1)
        except ValueError:  # Unpacking error
            return None

        return None if prefix != cls._brick_id_prefix else cbci_id

    def _dump_cells(self, cells: Iterable[EntityCell]) -> None:
        # TODO: custom encoder instead?
        self.json_cells = [cell.to_dict() for cell in cells]

    # TODO: factorise with HeaderFilter.cells
    @property
    def cells(self) -> list[EntityCell]:
        cells = self._cells

        if cells is None:
            from ..core.entity_cell import CELLS_MAP

            cells, errors = CELLS_MAP.build_cells_from_dicts(
                model=self.content_type.model_class(),
                dicts=self.json_cells,
            )

            if errors:
                logger.warning(
                    'CustomBrickConfigItem (id="%s") is saved with valid cells.',
                    self.id,
                )
                self._dump_cells(cells)
                self.save()

            self._cells = cells

        return cells

    @cells.setter
    def cells(self, cells: Iterable[EntityCell]) -> None:
        self._cells = cells = [cell for cell in cells if cell]
        self._dump_cells(cells)

    @property
    def filtered_cells(self) -> Iterator[EntityCell]:
        """Generators which yields non excluded EntityCell instances.
        (e.g. fields not hidden with FieldsConfig, CustomFields not deleted).
        """
        for cell in self.cells:
            if not cell.is_excluded:
                yield cell


class BrickStateManager(models.Manager):
    FIELDS: dict[str, str] = {
        # SettingKey ID                                 BrickState field-name
        SETTING_BRICK_DEFAULT_STATE_IS_OPEN:           'is_open',  # TODO: constants....
        SETTING_BRICK_DEFAULT_STATE_SHOW_EMPTY_FIELDS: 'show_empty_fields',
    }

    def _get_fields_values(self):
        FIELDS = self.FIELDS
        svalues = SettingValue.objects.get_4_keys(
            *[{'key': skey_id} for skey_id in FIELDS.keys()]
        )

        return {FIELDS[svalue.key_id]: svalue.value for svalue in svalues.values()}

    def get_for_brick_id(self, *, brick_id: str, user) -> BrickState:
        """Returns current state of a brick.
        @param brick_id: A brick id.
        @param user: owner of the BrickState.
        @returns: An instance of BrickState.
        """
        try:
            return self.get(brick_id=brick_id, user=user)
        except self.model.DoesNotExist:
            return self.model(brick_id=brick_id, user=user, **self._get_fields_values())

    def get_for_brick_ids(self, *, brick_ids: Sequence[str], user) -> dict[str, BrickState]:
        """Get current states of several bricks.
        @param brick_ids: a list of brick IDs.
        @param user: owner of the BrickStates.
        @returns: A dict with brick_id as key and state as value.
        """
        states = {}

        for state in self.filter(brick_id__in=brick_ids, user=user):
            states[state.brick_id] = state

        missing_brick_ids = {*brick_ids} - {*states.keys()}  # IDs of bricks without state

        if missing_brick_ids:
            cls = partial(self.model, user=user, **self._get_fields_values())

            for brick_id in missing_brick_ids:
                states[brick_id] = cls(brick_id=brick_id)

        return states


class BrickState(CremeModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    brick_id = models.CharField(_('Block ID'), max_length=100)

    # Is brick has to appear as opened or closed
    is_open = models.BooleanField(default=True)

    # Are empty fields in brick have to be shown or not
    show_empty_fields = models.BooleanField(default=True)

    # NB: do not use directly ; use the function get_extra_data() & set_extra_data()
    json_extra_data = models.JSONField(
        editable=False, default=dict,
    ).set_tags(viewable=False)

    objects = BrickStateManager()

    class Meta:
        app_label = 'creme_core'
        unique_together = ('user', 'brick_id')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._extra_data = self.json_extra_data

    def __str__(self):
        return (
            f'BrickState('
            f'user="{self.user}", '
            f'brick_id="{self.brick_id}", '
            f'is_open={self.is_open}, '
            f'show_empty_fields={self.show_empty_fields}, '
            f'json_extra_data={self.json_extra_data}'
            f')'
        )

    def del_extra_data(self, key: str) -> None:
        del self._extra_data[key]

    def get_extra_data(self, key: str, default=None):
        return self._extra_data.get(key, default)

    def set_extra_data(self, key: str, value) -> bool:
        old_value = self._extra_data.get(key)
        self._extra_data[key] = value

        return old_value != value

    def save(self, **kwargs):
        # Should we manage argument 'update_fields'? (if you set explicitly the
        # extra data you probably save() the field explicitly...)
        self.json_extra_data = self._extra_data
        super().save(**kwargs)
