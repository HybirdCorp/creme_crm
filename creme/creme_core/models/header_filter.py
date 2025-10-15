################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
import warnings
from copy import deepcopy
from typing import TYPE_CHECKING, Iterable
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q, QuerySet
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ..setting_keys import global_filters_edition_key
from . import CremeEntity, CremeUser
from . import fields as core_fields

if TYPE_CHECKING:
    from ..core.entity_cell import EntityCell

logger = logging.getLogger(__name__)

_DEFAULT_IS_PRIVATE = False


class HeaderFilterList(list):
    """Contains all the HeaderFilter objects corresponding to a CremeEntity's ContentType.
    Indeed, it's a cache.
    """
    def __init__(self, content_type: ContentType, user: CremeUser):
        super().__init__(
            HeaderFilter.objects.filter_by_user(user)
                                .filter(entity_type=content_type)
        )
        self._selected: HeaderFilter | None = None

    @property
    def selected(self) -> HeaderFilter | None:
        return self._selected

    def select_by_id(self, *ids: str) -> HeaderFilter | None:
        """Try several HeaderFilter ids"""
        # Linear search but with few items after all...
        for hf_id in ids:
            for hf in self:
                if hf.id == hf_id:
                    self._selected = hf
                    return hf

        if self:
            self._selected = self[0]
        else:
            self._selected = None

        return self._selected


class HeaderFilterProxy:
    """This class is useful to build HeaderFilter instances in a declarative
    way, notably in 'populate' scripts.

    The value for the field 'HeaderFilter.entity_type' is store as a model class
    in order to avoid some issues with ContentTypes which are cached & can have
    different IDs in the test DBs.

    The EntityCells can be passed as tuples (cell_class, cell_value), and the
    potential queries (to retrieve RelationTypes for example) are made only
    when the HeaderFilter is created (see the method 'get_or_create()').

    The owner user can be passed as UUID (string or instance), and the instance
    is retrieved as late as possible (classically the method 'get_or_create()').

    Hint: use HeaderFilter.objects.proxy().
    """
    def __init__(self, *,
                 instance: HeaderFilter,
                 model: type[CremeEntity],
                 user: CremeUser | UUID | str | None = None,
                 cells: Iterable[EntityCell | tuple[type[EntityCell], str]],
                 ):
        """
        @param instance: Instance of HeaderFilter; no need to set the value
               for these fields: "user", "entity_type", "json_cells".
        @param model: used to set the field 'entity_type' of the underlying
               HeaderFilter instance.
        @param user: used to set the field 'user' of the underlying
               HeaderFilter instance. It can be:
               - None (no owner)
               - A CremeUser instance.
               - An UUID (instance or string).
        @param cells: used to set the field 'json_cells' of the underlying
               HeaderFilter instance. Elements of the iterable can be:
               - EntityCell instance
               - tuple (cell_class, cell_value)
        """
        # TODO: when uuid
        #  if instance.pk is not None:
        #     raise ValueError(f'HeaderFilter(uuid={instance.uuid}) is already saved in DB')

        self._instance = instance
        self._model = model
        self._user = user
        self.cells = cells

    # NB: not settable (create another instance should be a better idea)
    @property
    def id(self) -> str:
        return self._instance.id

    # NB: not settable (create another instance should be a better idea)
    @property
    def entity_type(self) -> ContentType:
        return ContentType.objects.get_for_model(self._model)

    # NB: not settable (create another instance should be a better idea)
    @property
    def model(self) -> type[CremeEntity]:
        return self._model

    @property
    def is_custom(self) -> bool:
        return self._instance.is_custom

    @is_custom.setter
    def is_custom(self, value: bool) -> None:
        self._instance.is_custom = value

    @property
    def is_private(self) -> bool:
        return self._instance.is_private

    @is_private.setter
    def is_private(self, value: bool) -> None:
        self._instance.is_private = value

    @property
    def extra_data(self) -> dict:
        return self._instance.extra_data

    @extra_data.setter
    def extra_data(self, value: dict) -> None:
        self._instance.extra_data = value

    @property
    def name(self) -> str:
        return self._instance.name

    @name.setter
    def name(self, value: str) -> None:
        self._instance.name = value

    @property
    def user(self) -> CremeUser | None:
        user_info = self._user
        if user_info is None:
            return None

        if isinstance(user_info, CremeUser):
            return user_info

        return CremeUser.objects.get(uuid=user_info)

    @user.setter
    def user(self, value: CremeUser | UUID | str | None) -> None:
        """Set the field 'user' of the underlying HeaderFilter instance.

        @param value: It can be:
           - None (no owner)
           - A CremeUser instance.
           - An UUID (instance or string).
        """
        self._user = value

    @property
    def cells(self) -> list[EntityCell]:
        from ..core.entity_cell import EntityCell

        cells = []

        for cell_info in self._cells_info:
            if isinstance(cell_info, EntityCell):
                cells.append(cell_info)
            else:
                cell_class, cell_name = cell_info
                cell = cell_class.build(model=self._model, name=cell_name)
                if cell is not None:
                    cells.append(cell)

        return cells

    @cells.setter
    def cells(self, cells: Iterable[EntityCell | tuple[type[EntityCell], str]]) -> None:
        """Set the field 'json_cells' of the underlying HeaderFilter instance.

        @param value: Elements of the iterable can be:
               - EntityCell instance
               - tuple (cell_class, cell_value)

        Exemple:
            proxy.cells = [
                EntityCellRegularField.build(model, 'name'),  # Instance case
                (EntityCellRelation, REL_SUB_HAS),            # Tuple case
            ]
        """
        self._cells_info = [*cells]

    def get_or_create(self) -> tuple[HeaderFilter, bool]:
        instance = self._instance
        saved_instance = type(instance).objects.filter(id=instance.id).first()
        if saved_instance is not None:
            return saved_instance, False

        user = self.user
        if user and user.is_staff:
            # Staff users cannot be owner in order to stay 'invisible'.
            raise ValueError(
                f'{type(self)}.get_or_create(): the owner cannot be a staff user.'
            )

        if self.is_private:
            if not user:
                raise ValueError(
                    f'{type(self)}.get_or_create(): a private filter must belong to a User.'
                )

            if not self.is_custom:
                # NB: It should not be useful to create a private HeaderFilter
                #     (so it belongs to a user) which cannot be deleted.
                raise ValueError(
                    f'{type(self)}.get_or_create(): a private filter must be custom.'
                )

        saved_instance = deepcopy(instance)
        saved_instance.entity_type = self._model
        saved_instance.cells = self.cells
        saved_instance.user = user
        saved_instance.save()

        return saved_instance, True


class HeaderFilterManager(models.Manager):
    def filter_by_user(self, user: CremeUser) -> QuerySet:
        if user.is_team:
            raise ValueError(
                f'HeaderFilterManager.filter_by_user(): '
                f'user cannot be a team ({user})'
            )

        qs = self.all()

        return (
            qs
            if user.is_staff else
            qs.filter(
                Q(is_private=False)
                | Q(is_private=True, user__in=[user, *user.teams]),
            )
        )

    def get_by_portable_key(self, key) -> HeaderFilter:
        return self.get(id=key)

    def create_if_needed(
            self,
            pk: str,
            name: str,
            model: type[CremeEntity],
            is_custom: bool = False,
            user: CremeUser | None = None,
            is_private: bool = _DEFAULT_IS_PRIVATE,
            cells_desc: Iterable[EntityCell | tuple[type[EntityCell], dict]] = (),
            extra_data: dict | None = None,
    ) -> HeaderFilter:
        """Creation helper ; useful for populate.py scripts.
        @param cells_desc: List of objects where each one can other:
            - an instance of EntityCell (one of its child class of course).
            - a tuple (class, args)
              where 'class' is child class of EntityCell, & 'args' is a dict
              containing parameters for the build() method of the previous class.
        """
        warnings.warn(
            'HeaderFilterManager.create_if_needed() is deprecated; '
            'use proxy() instead.',
            DeprecationWarning,
        )

        from ..core.entity_cell import EntityCell

        if user and user.is_staff:
            # Staff users cannot be owner in order to stay 'invisible'.
            raise ValueError('HeaderFilter.create(): the owner cannot be a staff user.')

        if is_private:
            if not user:
                raise ValueError('HeaderFilter.create(): a private filter must belong to a User.')

            if not is_custom:
                # It should not be useful to create a private HeaderFilter (so it
                # belongs to a user) which cannot be deleted.
                raise ValueError('HeaderFilter.create(): a private filter must be custom.')

        try:
            hf = self.get(pk=pk)
        except self.model.DoesNotExist:
            cells = []

            for cell_desc in cells_desc:
                if cell_desc is None:
                    continue

                if isinstance(cell_desc, EntityCell):
                    cells.append(cell_desc)
                else:
                    cell = cell_desc[0].build(model=model, **cell_desc[1])

                    if cell is not None:
                        cells.append(cell)

            hf = self.create(
                pk=pk, name=name, user=user,
                is_custom=is_custom, is_private=is_private,
                entity_type=model,
                cells=cells,
                extra_data=extra_data or {},
            )

        return hf

    create_if_needed.alters_data = True

    def proxy(self, *,
              id: str,
              model: type[CremeEntity],
              name: str,
              cells: Iterable[EntityCell | tuple[type[EntityCell], str]],
              user: CremeUser | UUID | str | None = None,
              is_custom: bool = False,  # TODO: change the default value in models?
              is_private: bool = _DEFAULT_IS_PRIVATE,
              extra_data: dict | None = None,
              ) -> HeaderFilterProxy:
        """Helper method to create a HeaderFilterProxy instance, useful to create
        easily HeaderFilter.
        They are notably used in 'populate' script to declare HeaderFilters to
        built in the populator class attribute 'HEADER_FILTERS' (without
        performing SQL queries).

        @param id: Value of the field 'id' of the future instance of HeaderFilter.
        @param model: Used to set the value of the field 'entity_type' of the
               future instance of HeaderFilter.
        @param name: Value of the field 'name' of the future instance of HeaderFilter.
        @param cells: Used to set the value of the field 'json_cells' of the
               future instance of HeaderFilter. EntityCells can be passed as
               simple tuples (cell_class, cell_value).
        @param user: Used to set the value of the field 'user' of the future
               instance of HeaderFilter. User can be passed as a simple UUID
               (instance or string).
        @param is_custom: Value of the field 'is_custom' of the future instance
               of HeaderFilter.
        @param is_private: Value of the field 'is_private' of the future
               instance of HeaderFilter.
        @param extra_data: Value of the field 'extra_data' of the future
               instance of HeaderFilter.

        @return: A HeaderFilterProxy instance.

        Example:
            header_filter = HeaderFilter.objects.proxy(
                id=constants.DEFAULT_HFILTER_MY_MODEL,
                name=_('My model view'),
                model=MyModel,
                cells=[
                    (EntityCellRegularField, 'name'),
                    (EntityCellRegularField, 'status'),
                    (EntityCellRelation,     constants.REL_OBJ_RELATED),
                ],
            ).get_or_create()[0]
        """
        return HeaderFilterProxy(
            model=model, cells=cells, user=user,
            instance=self.model(
                id=id, name=name,
                is_custom=is_custom, is_private=is_private,
                extra_data=extra_data or {},
            ),
        )


class HeaderFilter(models.Model):  # TODO: CremeModel? MinionModel?
    """View of list: set of columns (see EntityCell) stored for a specific
    ContentType of CremeEntity.
    """
    id = models.CharField(primary_key=True, max_length=100, editable=False)
    name = models.CharField(_('Name of the view'), max_length=100)

    # Not viewable by users, For administrators currently.
    created = core_fields.CreationDateTimeField().set_tags(viewable=False)
    modified = core_fields.ModificationDateTimeField().set_tags(viewable=False)

    user = core_fields.CremeUserForeignKey(
        verbose_name=_('Owner user'), blank=True, null=True,
        help_text=_('If you assign an owner, only the owner can edit or delete the view'),
    )  # TODO: .set_null_label(_('No owner'))  # must fix the enumerable view

    entity_type = core_fields.CTypeForeignKey(editable=False)

    # 'False' means: cannot be deleted (to be sure that a ContentType
    #  has always at least one existing HeaderFilter)
    is_custom = models.BooleanField(blank=False, default=True, editable=False)

    # 'True' means: can only be viewed (and so edited/deleted) by its owner.
    is_private = models.BooleanField(
        pgettext_lazy('creme_core-header_filter', 'Is private?'),
        default=False,
        help_text=_(
            'A private view of list can only be used by its owner '
            '(or the teammates if the owner is a team)'
        ),
    )

    # TODO: CellsField? (what about auto saving on invalid cells?)
    json_cells = models.JSONField(editable=False, default=list)

    # Can be used by third party code to store the data they want,
    # without having to modify the code.
    extra_data = models.JSONField(editable=False, default=dict).set_tags(viewable=False)

    objects = HeaderFilterManager()

    creation_label = _('Create a view')
    save_label     = _('Save the view')

    _cells = None

    class Meta:
        app_label = 'creme_core'
        ordering = ('name',)

    def __str__(self):
        return self.name

    def can_delete(self, user: CremeUser) -> tuple[bool, str]:
        if not self.is_custom:
            return False, gettext("This view can't be deleted")

        return self.can_edit(user)

    # TODO: factorise with EntityFilter.can_edit ???
    def can_edit(self, user: CremeUser) -> tuple[bool, str]:
        if not user.has_perm(self.entity_type.app_label):
            return False, gettext('You are not allowed to access to this app')

        if not self.user_id:  # All users allowed
            from .setting_value import SettingValue

            return (
                (True, 'OK')
                if user.is_superuser
                or SettingValue.objects.get_4_key(global_filters_edition_key).value else
                (False, gettext('Only superusers can edit/delete this view (no owner)'))
            )

        if user.is_staff:
            return True, 'OK'

        if user.is_superuser and not self.is_private:
            return True, 'OK'

        if not self.user.is_team:
            if self.user_id == user.id:
                return True, 'OK'
        elif user.id in self.user.teammates:
            return True, 'OK'

        return False, gettext('You are not allowed to edit/delete this view')

    def can_view(self,
                 user: CremeUser,
                 ) -> tuple[bool, str]:
        return self.can_edit(user)

    def _dump_cells(self, cells: Iterable[EntityCell]) -> None:
        self.json_cells = [cell.to_dict(portable=True) for cell in cells]

    # TODO: return a deepcopy? generator?
    @property
    def cells(self) -> list[EntityCell]:
        cells = self._cells

        if cells is None:
            from ..core.entity_cell import CELLS_MAP

            cells, errors = CELLS_MAP.build_cells_from_dicts(
                model=self.entity_type.model_class(),
                dicts=self.json_cells,
            )

            if errors:
                logger.warning(
                    'HeaderFilter (id="%s") is saved with valid cells.',
                    self.id,
                )
                self._dump_cells(cells)
                self.save()

            self._cells = cells

        return cells

    # TODO: accept tuples like HeaderFilterProxy?
    @cells.setter
    def cells(self, cells: Iterable[EntityCell]) -> None:
        self._cells = cells = [cell for cell in cells if cell]
        self._dump_cells(cells)

    @property
    def filtered_cells(self) -> list[EntityCell]:
        """List of not excluded EntityCell instances.
        (e.g. fields not hidden with FieldsConfig, CustomFields not deleted).
        """
        return [cell for cell in self.cells if not cell.is_excluded]

    def get_edit_absolute_url(self):
        return reverse('creme_core__edit_hfilter', args=(self.id,))

    # TODO: way to mean QuerySet[CremeEntity] ??
    def populate_entities(self, entities: QuerySet, user: CremeUser) -> None:
        """Fill caches of CremeEntity objects, related to the columns that will
        be displayed with this HeaderFilter.
        @param entities: QuerySet on CremeEntity (or subclass).
        @param user: Current user.
        """
        from ..core.entity_cell import EntityCell
        EntityCell.mixed_populate_entities(
            cells=self.cells, entities=entities, user=user,
        )

    def portable_key(self) -> str:
        return self.id
