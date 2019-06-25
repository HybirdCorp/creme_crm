# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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
from json import loads as json_load  # dumps as json_dump
import logging

from django.db.models import Model, CharField, TextField, BooleanField, Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _, gettext, pgettext_lazy

from ..utils.serializers import json_encode

from .fields import CremeUserForeignKey, CTypeForeignKey
from .fields_config import FieldsConfig

logger = logging.getLogger(__name__)


class HeaderFilterList(list):
    """Contains all the HeaderFilter objects corresponding to a CremeEntity's ContentType.
    Indeed, it's a cache.
    """
    def __init__(self, content_type, user):
        super().__init__(HeaderFilter.get_for_user(user, content_type))
        self._selected = None

    @property
    def selected(self):
        return self._selected

    def select_by_id(self, *ids):
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


class HeaderFilter(Model):  # CremeModel ???
    """View of list : sets of columns (see EntityCell) stored for a specific
    ContentType of CremeEntity.
    """
    id          = CharField(primary_key=True, max_length=100, editable=False)
    name        = CharField(_('Name of the view'), max_length=100)
    user        = CremeUserForeignKey(verbose_name=_('Owner user'), blank=True, null=True)
    entity_type = CTypeForeignKey(editable=False)

    # 'False' means: cannot be deleted (to be sure that a ContentType
    #  has always at least one existing HeaderFilter)
    is_custom = BooleanField(blank=False, default=True, editable=False)

    # 'True' means: can only be viewed (and so edited/deleted) by its owner.
    is_private = BooleanField(pgettext_lazy('creme_core-header_filter', 'Is private?'), default=False)

    json_cells = TextField(editable=False, null=True)  # TODO: JSONField ? CellsField ?

    creation_label = _('Create a view')
    save_label     = _('Save the view')

    _cells = None

    class Meta:
        app_label = 'creme_core'
        ordering = ('name',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO: a true CellsField ??
        if self.json_cells is None:
            self.cells = []

    def __str__(self):
        return self.name

    def can_delete(self, user):
        if not self.is_custom:
            return (False, gettext("This view can't be deleted"))

        return self.can_edit(user)

    # TODO: factorise with EntityFilter.can_edit ???
    def can_edit(self, user):
        if not self.user_id:  # All users allowed
            return True, 'OK'

        if user.is_staff:
            return True, 'OK'

        if user.is_superuser and not self.is_private:
            return True, 'OK'

        if not user.has_perm(self.entity_type.app_label):
            return False, gettext('You are not allowed to access to this app')

        if not self.user.is_team:
            if self.user_id == user.id:
                return True, 'OK'
        elif user.id in self.user.teammates:
            return True, 'OK'

        return False, gettext('You are not allowed to edit/delete this view')

    def can_view(self, user, content_type=None):
        if content_type and content_type != self.entity_type:
            return False, 'Invalid entity type'

        return self.can_edit(user)

    @staticmethod
    def create(pk, name, model, is_custom=False, user=None, is_private=False, cells_desc=()):
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
            hf = HeaderFilter.objects.get(pk=pk)
        except HeaderFilter.DoesNotExist:
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

            hf = HeaderFilter.objects.create(
                pk=pk, name=name, user=user,
                is_custom=is_custom, is_private=is_private,
                entity_type=model,
                cells=cells,
            )

        return hf

    def _dump_cells(self, cells):
        # self.json_cells = json_dump([cell.to_dict() for cell in cells])
        self.json_cells = json_encode([cell.to_dict() for cell in cells])

    @property
    def cells(self):
        cells = self._cells

        if cells is None:
            from ..core.entity_cell import CELLS_MAP

            cells, errors = CELLS_MAP.build_cells_from_dicts(
                model=self.entity_type.model_class(),
                dicts=json_load(self.json_cells),
            )

            if errors:
                logger.warning('HeaderFilter (id="%s") is saved with valid cells.', self.id)
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
        """List of EntityCell instances, but it excluded the ones which are
        related to fields hidden with FieldsConfig.
        """
        return list(FieldsConfig.filter_cells(self.entity_type.model_class(), self.cells))

    def get_edit_absolute_url(self):
        return reverse('creme_core__edit_hfilter', args=(self.id,))

    @staticmethod
    def get_for_user(user, content_type=None):
        assert not user.is_team

        qs = HeaderFilter.objects.all()

        if content_type:
            qs = qs.filter(entity_type=content_type)

        return qs if user.is_staff else \
               qs.filter(Q(is_private=False) |
                         Q(is_private=True, user__in=[user] + user.teams)
                        )

    # TODO: dispatch this job in Cells classes
    def populate_entities(self, entities, user):
        """Fill caches of CremeEntity objects, related to the columns that will
        be displayed with this HeaderFilter.
        @param entities: QuerySet on CremeEntity (or subclass).
        """
        cell_groups = defaultdict(list)

        for cell in self.cells:
            cell_groups[cell.__class__].append(cell)

        for cell_cls, cell_group in cell_groups.items():
            cell_cls.populate_entities(cell_group, entities, user)
