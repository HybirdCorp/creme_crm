################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021-2025  Hybird
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

from django.db import models
from django.db.transaction import atomic

from .auth import UserRole
from .base import CremeModel


class MenuConfigItem(CremeModel):
    """Stores information about a <gui.menu.MenuEntry>."""
    role = models.ForeignKey(
        UserRole,
        # verbose_name='Related role',
        null=True, default=None, on_delete=models.CASCADE, editable=False,
    )
    # TODO: a UserRole for superusers instead ??
    superuser = models.BooleanField(
        'related to superusers', default=False, editable=False,
    )

    # NB: id of gui.menu.MenuEntry
    entry_id = models.CharField(max_length=100, editable=False)

    parent = models.ForeignKey(
        'self',
        null=True, on_delete=models.CASCADE, related_name='children',
        editable=False,
    )
    order = models.PositiveIntegerField(editable=False)
    # NB: see 'data' parameter of MenuEntry.__init__()
    entry_data = models.JSONField(default=dict, editable=False)

    class Meta:
        app_label = 'creme_core'
        ordering = ('order',)

    def __repr__(self):
        return (
            f'MenuConfigItem('
            f'entry_id="{self.entry_id}", '
            f'parent={self.parent_id}, '
            f'order={self.order}, '
            f'entry_data={self.entry_data}'
            f')'
        )

    def __str__(self):
        return self.entry_data.get('label', '??')

    @staticmethod
    @atomic
    def clone_for_role(qs: models.QuerySet, role: UserRole | None = None) -> None:
        model = qs.model
        create_item = partial(model.objects.create, role=role, superuser=role is None)

        # We must translate the parent<->children relation in cloned menu
        ids_translation: dict[int, MenuConfigItem] = {}

        # We order by ID to get parents first (so the cloned parents exists
        # when we clone the children)
        for item in qs.order_by('id'):
            cloned = create_item(
                entry_id=item.entry_id,
                entry_data=item.entry_data,

                parent=ids_translation.get(item.parent_id),
                order=item.order,
            )
            ids_translation[item.id] = cloned
