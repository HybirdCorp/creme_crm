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

from typing import TYPE_CHECKING, Literal

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .auth import UserRole
from .base import CremeModel
from .entity import CremeEntity
from .fields import CTypeForeignKey

if TYPE_CHECKING:
    from creme.creme_core.gui.button_menu import Button


class ButtonMenuItemManager(models.Manager):
    def create_if_needed(self, *,
                         model: type[CremeEntity] | None = None,
                         button: type[Button] | str,
                         order: int,
                         role: None | UserRole | Literal['superuser'] = None,
                         ) -> ButtonMenuItem:
        """Creation helper ; useful for populate.py scripts.
        @param model: Class inheriting CremeEntity, or <None> for "all models".
        @param button: class inheriting <creme_core.gui.button_menu.Button>,
               or button's ID (string -- see Button.id).
        @param order: Order of the button if the menu (see ButtonMenuItem.order).
        @return: A ButtonMenuItem instance.
        """
        ct = ContentType.objects.get_for_model(model) if model else None

        return self.get_or_create(
            content_type=ct,
            button_id=button if isinstance(button, str) else button.id,
            superuser=(role == 'superuser'),
            role=role if isinstance(role, UserRole) else None,
            defaults={'order': order},
        )[0]

    create_if_needed.alters_data = True


class ButtonMenuItem(CremeModel):
    # 'null' means: all ContentTypes are accepted.
    # TODO: EntityCTypeForeignKey ??
    content_type = CTypeForeignKey(verbose_name=_('Related type'), null=True)

    role = models.ForeignKey(
        UserRole, verbose_name=_('Related role'),
        null=True, default=None, on_delete=models.CASCADE,
    )
    superuser = models.BooleanField(
        'related to superusers', default=False, editable=False,
    )

    button_id = models.CharField(_('Button ID'), max_length=100)
    order = models.PositiveIntegerField(_('Priority'))

    objects = ButtonMenuItemManager()

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Button to display')
        verbose_name_plural = _('Buttons to display')
        ordering = ('order',)

    def __str__(self):
        button = self.button
        return str(button.verbose_name) if button else gettext('Deprecated button')

    @property
    def button(self):
        from ..gui.button_menu import button_registry

        return button_registry.get_button(self.button_id)

    @button.setter
    def button(self, value: Button | type[Button]):
        self.button_id = value.id

    # TODO?
    # def __eq__(self, other):
    #     return (
    #         isinstance(other, type(self))
    #         and self.content_type == other.content_type
    #         and self.button_id == other.button_id
    #         and self.order == other.order
    #         and self.superuser == other.superuser
    #         and self.role == other.role
    #     )

    def clone_for_role(self, role: UserRole | None) -> ButtonMenuItem:
        """Clone an instance to create the configuration of another role.
        The returned instance is not saved (hint: you can use it in bulk_create()).
        @param role: None means 'superuser'.
        """
        return type(self)(
            content_type=self.content_type,
            button_id=self.button_id,
            order=self.order,
            role=role,
            superuser=(role is None),
        )
