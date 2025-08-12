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

from copy import deepcopy
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .auth import UserRole
from .base import CremeModel
from .entity import CremeEntity
from .fields import CTypeForeignKey

if TYPE_CHECKING:
    from creme.creme_core.gui.button_menu import Button


class ButtonMenuItemProxy:
    """This class is useful to build ButtonMenuItem instances in a
    declarative way in 'populate' scripts.

    - The field 'ButtonMenuItem.entity_type' references ContentTypes, and it's
    a bad idea to retrieve ContentType instances immediately at import time
    (notably in unit tests -- the internal cache could be thrown later); this
    proxy stores the model & retrieve the model when it's more relevant.
    - The field 'role' can reference a UserRole instance which odes not exist
    yet when the script is imported.

    Hint: use ButtonMenuItem.objects.proxy().
    """
    __slots__ = ('_instance', 'model', '_role')

    def __init__(self,
                 instance: ButtonMenuItem,
                 model: type[CremeEntity] | None,
                 role: None | str | UUID | UserRole | Literal['superuser'],
                 ):
        """
        @param instance: Instance of ButtonMenuItem which should not be saved
               (i.e. no PK).
        @param model: used to set the field 'entity_type' of the
               underlying ButtonMenuItem.
        @param role: used to set the fields 'superuser' & 'role' of the
               underlying ButtonMenuItem.
               See <role> property setter.
        """
        if model is not None and not issubclass(model, CremeEntity):
            raise ValueError(
                f'<model> must be None or a CremeEntity child class, found {model}'
            )

        for field_name in ('pk', 'content_type', 'role', 'superuser'):
            if getattr(instance, field_name):
                raise ValueError(
                    f'The field "{field_name}" of the ButtonMenuItem must not be set: {instance!r}'
                )

        self._instance = instance
        self.model = model
        self.role = role

    @property
    def content_type(self):
        model = self.model
        return ContentType.objects.get_for_model(model) if model else None

    @property
    def button(self) -> Button | None:
        return self._instance.button

    @button.setter
    def button(self, value: type[Button]) -> None:
        self._instance.button = value

    # NB: use the property <role> to set the value
    @property
    def superuser(self) -> bool:
        return self._role == 'superuser'

    @property
    def role(self) -> UserRole | None:
        role = self._role

        if not role or role == 'superuser':
            return None

        if isinstance(role, UserRole):
            return role

        return UserRole.objects.get(uuid=role)

    @role.setter
    def role(self, value: None | str | UUID | UserRole | Literal['superuser']) -> None:
        """
        To assign <None> as 'role' & <False> to 'superuser', pass <None>.

        To set a UserRole, you can pass:
            - An instance of UserRole.
            - A UserRole's UUID as a UUID instance.
            - A UserRole's UUID as a string instance.

        To assign <True> to 'superuser' (& <None> to 'role'), pass the literal
        string "superuser".
        """
        if isinstance(value, str):
            if value != 'superuser':
                value = UUID(value)
        elif value is not None and not isinstance(value, (UUID, UserRole)):
            raise ValueError(
                '<role> must be None/UUID string/UUID/UserRole instance/"superuser".'
            )

        self._role = value

    def __getattr__(self, name):
        try:
            type(self._instance)._meta.get_field(name)
        except FieldDoesNotExist as e:
            raise AttributeError(
                f'{type(self).__name__} has no attribute "{name}" ({e})'
            ) from e

        return getattr(self._instance, name)

    @property
    def order(self) -> int:
        return self._instance.order

    @order.setter
    def order(self, value: int) -> None:
        self._instance.order = value

    # TODO? (+remove some properties)
    # def __setattr__(self, name, value):
    #     if name in ('_instance', ....):
    #         object.__setattr__(self, name, value)
    #     elif name in ('id', 'pk'):
    #         raise AttributeError(f"can't set attribute '{name}'")
    #     else:
    #         self._instance.__setattr__(name, value)

    def get_or_create(self) -> tuple[ButtonMenuItem, bool]:
        instance = self._instance
        ctype = self.content_type
        superuser = self.superuser
        role = self.role
        saved_instance = type(instance).objects.filter(
            content_type=ctype,
            button_id=instance.button_id,
            superuser=superuser,
            role=role,
        ).first()
        if saved_instance is not None:
            return saved_instance, False

        saved_instance = deepcopy(instance)
        saved_instance.content_type = ctype
        saved_instance.superuser = superuser
        saved_instance.role = role
        saved_instance.save()

        return saved_instance, True


class ButtonMenuItemManager(models.Manager):
    # TODO: deprecate?
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

    def proxy(self, *,
              model: type[CremeEntity] | None = None,
              button: type[Button],
              order: int,
              role: None | str | Literal['superuser'] = None,
              ):
        return ButtonMenuItemProxy(
            instance=self.model(button=button, order=order),
            model=model, role=role,
        )


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
    def button(self) -> Button | None:
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
