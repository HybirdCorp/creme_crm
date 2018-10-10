# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017  Hybird
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

from creme.creme_core.forms.base import CremeModelForm

from ..models import SubCategory


class SubCategoryForm(CremeModelForm):
    class Meta:
        model = SubCategory
        fields = ('name', 'description', 'category')

    def update_from_widget_response_data(self):
        instance = self.instance
        category = instance.category

        return {
            'value': {'category': str(category.id), 'subcategory': str(instance.id)},
            'added': [
                {
                    'category': (str(category.id), str(category)),
                    'subcategory': (str(instance.id), str(instance)),
                },
            ],
        }
