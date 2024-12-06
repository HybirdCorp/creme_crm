################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

# from django.http import Http404
from django.shortcuts import get_object_or_404

from ..models.custom_entity import CustomEntityType, custom_classes
from . import generic


class CustomEntityDetail(generic.EntityDetail):
    @property
    def model(self):
        type_number = int(self.kwargs.get('type_number'))
        # TODO: errors
        # TODO: cache
        get_object_or_404(CustomEntityType, number=type_number)

        # TODO: errors
        # try:
        # TODO: item.entity_model?
        return custom_classes[type_number]
        # except KeyError:
        #     raise Http404('Invalid model')
