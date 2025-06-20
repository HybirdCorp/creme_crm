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
from collections import defaultdict
from collections.abc import Iterable, Iterator, Sequence
from heapq import heappop, heappush
from typing import DefaultDict, Literal

from django.core.exceptions import PermissionDenied
from django.db.models import Model

from ..core.exceptions import ConflictError
from ..models import CremeEntity

logger = logging.getLogger(__name__)


class Button:
    "Button displayed above the bricks in detail-views of CremeEntities."

    # Can be used as a value in 'dependencies' to design the model of the
    # instance which the detail-view is about (think <context['object']>).
    CURRENT = 'CURRENT'

    # ID of the button, stored in DB (i.e. the button configuration), to
    # retrieve the right button class (so it must be unique)
    # Override it in child class with a value generated by 'generate_id()'.
    id: str = ''

    # Label used in the configuration GUI to display the button (see models.ButtonMenuItem)
    # Tips: use gettext_lazy()
    verbose_name: str = 'BUTTON'

    # Description used as tool-tips
    # Tips: use gettext_lazy()
    description: str = ''

    # List of the models on which the button depends (i.e. generally the button
    # is designed to create/modify instances of these models); it also can be
    # the string Button.CURRENT (see above).
    # Notice: it's globally the same thing as <Brick.dependencies>, excepted
    # there is no wildcard (at the moment it seems useless), & there is CURRENT.
    dependencies: \
        list[type[Model] | Literal['CURRENT']] | tuple[type[Model] | Literal['CURRENT'], ...]\
        = ()

    # List of IDs of RelationType objects on which the brick depends ;
    # only used for Buttons which have the model 'Relation' in their dependencies.
    # Notice: it's the same thing as <Brick.relation_type_deps>.
    relation_type_deps: Sequence[str] = ()

    # Name/path of the template used to render the button.
    template_name: str = 'creme_core/buttons/place-holder.html'

    # Permission string(s) ; an empty value means no permission is needed.
    # Example: <'myapp.add_mymodel'>
    # BEWARE: you have to use the template context variable "button.is_allowed"
    #         (computed from 'permissions' -- see 'is_allowed()' ) yourself !!
    permissions: str | Sequence[str] = ''

    def __eq__(self, other):
        return other.id == self.id

    @staticmethod
    def generate_id(app_name: str, name: str) -> str:
        """Helper used to create the value of the class attribute 'id'."""
        return f'{app_name}-{name}'

    def check_permissions(self, *, entity: CremeEntity, request) -> None:
        """Raises an error if the button has to be disabled.
        The error is injected in the context (see get_context()).
        @raise PermissionDenied, ConflictError.
        """
        request.user.has_perms_or_die(self.permissions)

    def get_context(self, *, entity: CremeEntity, request) -> dict:
        """Context used by the template system to render the button."""
        # return {
        #     'verbose_name': self.verbose_name,
        #     'description': self.description,
        #     'is_allowed': self.is_allowed(entity=entity, request=request),
        #     'template_name': self.template_name,
        # }
        is_allowed = True

        def _get_is_allowed():  # TODO: to be removed in creme2.8
            logger.critical(
                'The template "%s" for the button <%s> is using the variable '
                '"button.is_allowed"; use "button.permission_error" instead.',
                self.template_name, type(self).__name__,
            )
            return is_allowed

        ctxt = {
            'is_allowed': _get_is_allowed,

            # 'id': self.id, # TODO?
            'verbose_name': self.verbose_name,
            'description': self.description,
            'template_name': self.template_name,
        }

        try:
            self.check_permissions(entity=entity, request=request)
        except (PermissionDenied, ConflictError) as e:
            ctxt['permission_error'] = str(e)
            is_allowed = False

        return ctxt

    # TODO: replace with an attribute (like Brick.target_ctypes) -> "compatible_models"?
    def get_ctypes(self) -> Sequence[type[CremeEntity]]:
        """
        @return A sequence of CremeEntity classes that can have this type of button.
                Void sequence means that all types are ok.
                For example: (Contact, Organisation)
        """
        return ()

    # def is_allowed(self, *, entity, request) -> bool:
    #     permissions = self.permissions
    #     if not permissions:
    #         return True
    #
    #     return (
    #         request.user.has_perm(permissions)
    #         if isinstance(permissions, str) else
    #         request.user.has_perms(permissions)
    #     )

    # TODO: pass 'request' too ? (see Restrict2SuperusersButton)
    def ok_4_display(self, entity: CremeEntity) -> bool:
        """Can this button be displayed on this entity's detail-view?
        @param entity: CremeEntity which detail-view is displayed.
        @return True if the button can be displayed for 'entity'.
        """
        return True


# class ButtonsRegistry:
class ButtonRegistry:
    """Registry of <Button> classes, to retrieve them by their ID."""
    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    def __init__(self) -> None:
        self._button_classes: dict[str, type[Button]] = {}
        self._mandatory_classes: DefaultDict[
            type[CremeEntity] | None,
            dict[str, tuple[int, type[Button]]]
        ] = defaultdict(dict)

    def __iter__(self) -> Iterator[tuple[str, Button]]:
        """Yield tuples (button_id, button) for all registered classes.
        Notice that mandatory button classes are not returned.
        """
        for button_id, button_cls in self._button_classes.items():
            yield button_id, button_cls()

    def register(self, *button_classes: type[Button]) -> ButtonRegistry:
        """Register several classes of Button at once.
        @return The registry instance to chain calls in a fluent way.
        """
        setdefault = self._button_classes.setdefault

        for button_cls in button_classes:
            button_id = button_cls.id

            if not button_id:
                raise self.RegistrationError(
                    f'Button class with empty ID: {button_cls}'
                )

            if setdefault(button_id, button_cls) is not button_cls:
                raise self.RegistrationError(
                    f"Duplicated button's ID (or button registered twice): {button_id}"
                )

            # TODO: to be removed in creme2.8
            if hasattr(button_cls, 'is_allowed'):
                logger.critical(
                    'The button class %s still defines a method "is_allowed()"; '
                    'define the new method "check_permissions()" instead, '
                    'and update the related template to use the variable '
                    '"button.permission_error" instead of "button.is_allowed".',
                    button_cls,
                )

        return self

    def register_mandatory(self,
                           button_class: type[Button],
                           priority: int = 0,
                           ) -> ButtonRegistry:
        """Register a class of Button which is mandatory.
        It means an instance of this class will be displayed in the button menu
        whatever is the button configuration.
         - The class should not be registered with <register()> too (& so will
           not be available in the configuration).
         - The button will be present is the detail-views of the models returned
           by the method <get_ctypes()> of the given button. <None> means the
           button will be on all detail-views.

        @param priority: The priority of ordering (see the method <mandatory_buttons()>).
               0 means <start of the mandatory section>.
               Greater priority means the button is displayed after.
        @return The registry instance to chain calls in a fluent way.
        """
        button_id = button_class.id
        if not button_id:
            raise self.RegistrationError(
                f'Button class with empty ID: {button_class}'
            )

        classes = self._mandatory_classes
        models: Iterable[type[CremeEntity] | None] = button_class().get_ctypes() or [None]

        for model in models:
            buttons = classes[model]

            if button_id in buttons:
                raise self.RegistrationError(
                    f"Duplicated button's ID (or button registered twice): "
                    f"{button_id}"
                )

            buttons[button_id] = (priority, button_class)

        return self

    def unregister(self, *button_classes: type[Button]) -> ButtonRegistry:
        """Unregister several Button classes at once.
        All classes must be registered.
        """
        for button_cls in button_classes:
            button_id = button_cls.id

            if not button_id:
                raise self.UnRegistrationError(
                    f'Button class with empty ID: {button_cls}'
                )

            if self._button_classes.pop(button_id, None) is None:
                raise self.UnRegistrationError(
                    f'Button class with invalid ID (already unregistered?): {button_cls}'
                )

        return self

    def unregister_mandatory(self, button_class: type[Button]) -> ButtonRegistry:
        """Unregister several Button classes at once.
        All classes must be registered with <register_mandatory()>.
        """
        button_id = button_class.id
        if not button_id:
            raise self.UnRegistrationError(
                f'Button class with empty ID: {button_class}'
            )

        classes = self._mandatory_classes
        models: Iterable[type[CremeEntity] | None] = button_class().get_ctypes() or [None]

        for model in models:
            if classes[model].pop(button_id, None) is None:
                raise self.UnRegistrationError(
                    f'Button class with invalid ID (already unregistered?): {button_class}'
                )

        return self

    def get_button(self, button_id: str) -> Button | None:
        "Get a button instance found by its ID."
        cls = self._button_classes.get(button_id)

        return cls() if cls else None

    # TODO?
    # def get_mandatory_button(self, button_id: str, model: type[CremeEntity]):
    #     pass

    def get_buttons(self, id_list: Iterable[str], entity: CremeEntity) -> Iterator[Button]:
        """Generate the Buttons to be displayed on the detail-view of an entity.
        Deprecated buttons & buttons that should not be displayed for this entity
        are ignored.
        @param id_list: Sequence of button IDs.
        @param entity: CremeEntity instance.
        @yield creme_core.gui.button_menu.Button instances.
        """
        button_classes = self._button_classes
        mandatory_classes = self._mandatory_classes
        model = type(entity)

        for button_id in id_list:
            button_cls = button_classes.get(button_id)

            if button_cls is None:
                prio_n_cls = (
                    mandatory_classes[None].get(button_id)
                    or mandatory_classes[model].get(button_id)
                )

                if prio_n_cls is None:
                    logger.warning('Button seems deprecated: %s', button_id)
                    continue

                button_cls = prio_n_cls[1]

            button = button_cls()

            allowed_models = button.get_ctypes()
            if allowed_models and model not in allowed_models:
                logger.warning(
                    'This button cannot be displayed on this content type '
                    '(you have a config problem): %s',
                    button_id,
                )
                continue

            if button.ok_4_display(entity):
                yield button

    def mandatory_buttons(self, entity: CremeEntity) -> Iterator[Button]:
        """Get instances of all mandatory classes corresponding to an entity
        (based of its model).
        Instances are ordered by their priority (see <register_mandatory()>).
        """
        heap: list[tuple[int, type[Button]]] = []
        classes = self._mandatory_classes

        for prio_n_cls in classes[None].values():
            heappush(heap, prio_n_cls)

        for prio_n_cls in classes[type(entity)].values():
            heappush(heap, prio_n_cls)

        while heap:
            button = heappop(heap)[1]()

            if button.ok_4_display(entity=entity):
                yield button


button_registry = ButtonRegistry()


def __getattr__(name):
    if name == 'ButtonsRegistry':
        warnings.warn(
            '"ButtonsRegistry" is deprecated; use "ButtonRegistry" instead.',
            DeprecationWarning,
        )
        return ButtonRegistry

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
