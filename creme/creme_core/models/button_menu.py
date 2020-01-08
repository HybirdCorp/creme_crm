# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

import warnings

from django.db import models
from django.utils.translation import gettext_lazy as _, gettext

from .base import CremeModel
from .fields import CTypeForeignKey


class ButtonMenuItemManager(models.Manager):
    def create_if_needed(self, pk, *, model=None, button, order):
        """Creation helper ; useful for populate.py scripts.
        @param pk: Unique string.
        @param model: Class inheriting CremeEntity, or <None> for "all models".
        @param button: class inheriting <creme_core.gui.button_menu.Button>,
               or button's ID (string -- see Button.id_).
        @param order: Order of the button if the menu (see ButtonMenuItem.order).
        @return A ButtonMenuItem instance.
        """
        return self.get_or_create(
            pk=pk,
            defaults={
                'content_type': model,
                'button_id': button if isinstance(button, str) else button.id_,
                'order': order,
            },
        )[0]


# TODO: remove pkstring & use ('content_type', 'button_id') as PK ?
#       (what about button per role ?)
class ButtonMenuItem(CremeModel):
    id           = models.CharField(primary_key=True, max_length=100)
    # 'null' means: all ContentTypes are accepted.
    content_type = CTypeForeignKey(verbose_name=_('Related type'), null=True)
    button_id    = models.CharField(_('Button ID'), max_length=100, blank=False, null=False)
    order        = models.PositiveIntegerField(_('Priority'))

    objects = ButtonMenuItemManager()

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Button to display')
        verbose_name_plural = _('Buttons to display')

    def __str__(self):
        from creme.creme_core.gui.button_menu import button_registry

        button = button_registry.get_button(self.button_id)
        return str(button.verbose_name) if button else gettext('Deprecated button')

    @staticmethod
    def create_if_needed(pk, model, button, order):
        """Creation helper ; useful for populate.py scripts.
        @param model: Can be None for 'all models'.
        """
        warnings.warn('ButtonMenuItem.create_if_needed() is deprecated ; '
                      'use ButtonMenuItem.objects.create_if_needed() instead.',
                      DeprecationWarning,
                     )

        from django.contrib.contenttypes.models import ContentType

        return ButtonMenuItem.objects.get_or_create(
            pk=pk,
            defaults={
                'content_type': ContentType.objects.get_for_model(model) if model else None,
                'button_id':    button.id_,
                'order':        order,
            },
       )[0]
