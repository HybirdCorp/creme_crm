# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.gui.button_menu import Button
from creme.creme_core.gui.merge import merge_form_registry


class MergeEntitiesButton(Button):
    id_           = Button.generate_id('creme_core', 'merge_entities')
    verbose_name  = _(u'Merge two entities')
    template_name = 'creme_core/templatetags/button_merge_entities.html'

    def get_ctypes(self):
        return merge_form_registry.models

    def ok_4_display(self, entity):
        return merge_form_registry.get(entity.__class__) is not None


merge_entities_button = MergeEntitiesButton()
