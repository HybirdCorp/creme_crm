# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2020  Hybird
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

# from django.utils.translation import gettext_lazy as _
from django.db.models.query_utils import Q

# from creme.creme_core.forms.listview import BaseChoiceField
from creme.creme_core.forms import listview
from creme.persons import get_address_model


# NB: keep as example
# class AddressFKField(BaseChoiceField):
#     FILLED = 'FILLED'
#
#     def _build_choices(self, null_label=None):
#         if null_label is None:
#             fk = self.cell.field_info[0]
#             if fk.null:
#                 null_label = fk.get_null_label() or _('* is empty *')
#
#         choices = super()._build_choices(null_label=null_label)
#         choices.append({'value': self.FILLED, 'label': _('* filled *')})
#
#         return choices
#
#     def _get_q_for_choice(self, choice_value):
#         return ~self._get_q_for_null_choice()
#
#     def _get_q_for_null_choice(self):
#         # todo: remove not-editable fields ??
#         # todo: factorise with mass_import
#         address_field_names = list(get_address_model().info_field_names())
#         try:
#            address_field_names.remove('name')
#         except ValueError:
#            pass
#
#         fk_name = self.cell.value
#
#         empty_q = Q()
#         for fname in address_field_names:
#             empty_q &= Q(**{'{}__{}__regex'.format(fk_name, fname): r'^(\s)*$'})
#
#         return (Q(**{'{}__isnull'.format(fk_name): True}) | empty_q) \
#                if self.cell.field_info[0].null else empty_q
class AddressFKField(listview.ListViewSearchField):
    widget = listview.TextLVSWidget

    def to_python(self, value):
        if not value:
            return Q()

        # TODO: remove not-editable fields ??
        # TODO: factorise with mass_import
        address_field_names = [*get_address_model().info_field_names()]
        try:
            address_field_names.remove('name')
        except ValueError:
            pass

        fk_name = self.cell.value

        q = Q()
        for fname in address_field_names:
            q |= Q(**{f'{fk_name}__{fname}__icontains': value})

        return q
