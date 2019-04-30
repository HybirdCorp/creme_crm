# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from .core.function_field import FunctionField, FunctionFieldLink, FunctionFieldResultsList
from .forms.listview import BaseChoiceField
from .models import CremeEntity, CremePropertyType


class PropertiesSearchField(BaseChoiceField):
    def _build_choices(self, null_label=_('* no property *')):
        choices = super()._build_choices(null_label=null_label)
        choices.extend(
            {'value': ptype.id, 'label': str(ptype)}
                for ptype in CremePropertyType.objects.compatible(self.cell.model)
        )

        return choices

    def _get_q_for_choice(self, choice_value):
        return Q(properties__type=choice_value)

    def _get_q_for_null_choice(self):
        return Q(properties__isnull=True)


class PropertiesField(FunctionField):
    name         = 'get_pretty_properties'
    verbose_name = _('Properties')
    # has_filter   = True
    result_type  = FunctionFieldResultsList
    search_field_builder = PropertiesSearchField

    # @classmethod
    # def filter_in_result(cls, search_string):
    #     # Should we make a separated query to retrieve first the searched types ?
    #     return Q(properties__type__text__icontains=search_string)

    def __call__(self, entity, user):
        return FunctionFieldResultsList(
            FunctionFieldLink(label=str(p), url=p.type.get_absolute_url())
                for p in entity.get_properties()
        )

    @classmethod
    def populate_entities(cls, entities, user):
        CremeEntity.populate_properties(entities)
