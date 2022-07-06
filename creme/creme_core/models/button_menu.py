################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from typing import TYPE_CHECKING

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

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
                         ) -> ButtonMenuItem:
        """Creation helper ; useful for populate.py scripts.
        @param pk: Unique string.
        @param model: Class inheriting CremeEntity, or <None> for "all models".
        @param button: class inheriting <creme_core.gui.button_menu.Button>,
               or button's ID (string -- see Button.id).
        @param order: Order of the button if the menu (see ButtonMenuItem.order).
        @return A ButtonMenuItem instance.
        """
        # TODO: py 3.8
        # class ButtonItemDefaultDict(TypedDict):
        #     order: int
        ct = ContentType.objects.get_for_model(model) if model else None

        return self.get_or_create(
            content_type=ct,
            # button_id=button if isinstance(button, str) else button.id_,
            button_id=button if isinstance(button, str) else button.id,
            defaults={'order': order},
        )[0]


# TODO: what about button per role ?
class ButtonMenuItem(CremeModel):
    # 'null' means: all ContentTypes are accepted.
    # TODO: EntityCTypeForeignKey ??
    content_type = CTypeForeignKey(verbose_name=_('Related type'), null=True)
    button_id = models.CharField(_('Button ID'), max_length=100)
    order = models.PositiveIntegerField(_('Priority'))

    objects = ButtonMenuItemManager()

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Button to display')
        verbose_name_plural = _('Buttons to display')
        # TODO: unique_together = ('content_type', 'button_id') ??

    def __str__(self):
        from creme.creme_core.gui.button_menu import button_registry

        button = button_registry.get_button(self.button_id)
        return str(button.verbose_name) if button else gettext('Deprecated button')
