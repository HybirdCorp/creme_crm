# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from logging import warning

from django.template.loader import get_template


class Button(object):
    id_           = None   #overload with an unicode object ; use generate_id()
    verbose_name  = 'BUTTON' #used in the user configuration (see ButtonMenuItem)
    template_name = 'creme_core/templatetags/button.html' #used to render the button of course

    def __init__(self):
        self._template = None

    @staticmethod
    def generate_id(app_name, name):
        return u'button_%s-%s' % (app_name, name)

    def get_ctypes(self):
        """
        @return a sequence of CremeEntity class that can have this type of button.
        Void sequence means that all types are ok.
        eg: (Contact, Organisation)
        """
        return ()

    def ok_4_display(self, entity):
        """
        @param entity CremeEntity which detailview is displayed.
        @return True The button can be displayed for 'entity'.
        """
        return True

    def render(self, context):
        if not self._template:
            self._template = get_template(self.template_name)
        return self._template.render(context)


class ButtonsRegistry(object):
    def __init__(self):
        self._buttons = {}

    def register(self, *buttons):
        """
        @type buttons creme_core.gui.menu_buttons.Button objects.
        """
        buttons_dic = self._buttons

        for button in buttons:
            button_id = button.id_

            if buttons_dic.has_key(button_id):
                warning("Duplicate button's id or button registered twice : %s", button_id) #exception instead ???

            buttons_dic[button_id] = button

    def get_buttons(self, id_list, entity):
        buttons = self._buttons
        buttons_2_display = []

        for button_id in id_list:
            button = buttons.get(button_id)

            if button is None:
                warning('Button seems deprecated: %s', button_id)
                #button = Button()
            elif button.ok_4_display(entity):
                buttons_2_display.append(button)

        return buttons_2_display

    def __iter__(self):
        return self._buttons.iteritems()

button_registry = ButtonsRegistry()
