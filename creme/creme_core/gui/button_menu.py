# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import logging

from django.template.loader import get_template


logger = logging.getLogger(__name__)


class Button:
    id_           = None  # Overload with an unicode object ; use generate_id()
    verbose_name  = 'BUTTON'  # Used in the user configuration (see ButtonMenuItem)
    template_name = 'creme_core/buttons/place-holder.html'  # Used to render the button of course
    permission    = None  # None means not permission needed ; overload to set to 'myapp.add_mymodel' for example.
                          # BEWARE: you have to use the context variable 'has_perm' yourself !!

    @staticmethod
    def generate_id(app_name, name):
        return u'button_{}-{}'.format(app_name, name)

    def get_ctypes(self):
        """
        @return A sequence of CremeEntity class that can have this type of button.
                Void sequence means that all types are ok.
                eg: (Contact, Organisation)
        """
        return ()

    def has_perm(self, context):
        permission = self.permission
        return context['request'].user.has_perm(permission) if permission else True

    def ok_4_display(self, entity):
        """Can this button be displayed on this entity's detail-view ?
        @param entity: CremeEntity which detail-view is displayed.
        @return True if the button can be displayed for 'entity'.
        """
        return True

    def render(self, context):
        context['has_perm'] = self.has_perm(context)

        return get_template(self.template_name).render(context)


class ButtonsRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._button_classes = {}

    def register(self, *button_classes):
        """
        @type button_classes: creme_core.gui.menu_buttons.Button child classes.
        """
        setdefault = self._button_classes.setdefault

        for button_cls in button_classes:
            if setdefault(button_cls.id_, button_cls) is not button_cls:
                raise self.RegistrationError("Duplicated button's ID (or button registered twice) : {}".format(button_cls.id_))

    def get_button(self, button_id):
        cls = self._button_classes.get(button_id)

        return cls() if cls else None

    def get_buttons(self, id_list, entity):
        """Generate the Buttons to be displayed on the detail-view of an entity.
        Deprecated buttons & buttons that should not be displayed for this entity
        are ignored.
        @param id_list: Sequence of button IDs.
        @param entity: CremeEntity instance.
        @yield creme_core.gui.button_menu.Button instances.
        """
        button_classes = self._button_classes

        for button_id in id_list:
            button_cls = button_classes.get(button_id)

            if button_cls is None:
                logger.warning('Button seems deprecated: %s', button_id)
            else:
                button = button_cls()

                if button.ok_4_display(entity):
                    yield button

    def __iter__(self):
        for b_id, b_cls in self._button_classes.items():
            yield b_id, b_cls()


button_registry = ButtonsRegistry()
