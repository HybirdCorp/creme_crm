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
# import warnings
from typing import TYPE_CHECKING, Iterable

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

# _NOT_PASSED = object()
logger = logging.getLogger(__name__)


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

    def create_if_needed(
            self,
            pk: str,
            name: str,
            model: type[CremeEntity],
            is_custom: bool = False,
            user: CremeUser | None = None,
            is_private: bool = False,
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


class HeaderFilter(models.Model):  # TODO: CremeModel? MinionModel?
    """View of list : sets of columns (see EntityCell) stored for a specific
    ContentType of CremeEntity.
    """
    id = models.CharField(primary_key=True, max_length=100, editable=False)
    name = models.CharField(_('Name of the view'), max_length=100)
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
            # return True, 'OK'
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
                 # content_type=_NOT_PASSED,
                 ) -> tuple[bool, str]:
        # if content_type is not _NOT_PASSED:
        #     warnings.warn(
        #         'In HeaderFilter.can_view(), the argument "content_type" is deprecated.',
        #         DeprecationWarning,
        #     )
        #
        #     if content_type and content_type != self.entity_type:
        #         return False, 'Invalid entity type'

        return self.can_edit(user)

    def _dump_cells(self, cells: Iterable[EntityCell]) -> None:
        # self.json_cells = [cell.to_dict() for cell in cells]
        self.json_cells = [cell.to_dict(portable=True) for cell in cells]

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
