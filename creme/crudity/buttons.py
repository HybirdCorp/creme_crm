# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from creme_core.gui.button_menu import Button

class InfopathCreateFormButton(Button):
    id_           = Button.generate_id('crudity', 'infopath_create_form')
    verbose_name  = u""
    template_name = 'crudity/templatetags/button_infopath_create_form.html'

infopath_create_form_button = InfopathCreateFormButton()

class EmailTemplateCreateButton(Button):
    id_           = Button.generate_id('crudity', 'email_template_create')
    verbose_name  = u""
    template_name = 'crudity/templatetags/button_email_template_create.html'

email_template_create_button = EmailTemplateCreateButton()
