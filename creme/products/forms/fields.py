################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2026  Hybird
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

from creme.creme_config.forms.fields import CreatorEnumerableModelChoiceField
from creme.creme_core.forms.enumerable import NO_LIMIT
from creme.products import get_product_model


# TODO: factorise with ActivitySubTypeField?
class SubCategoryField(CreatorEnumerableModelChoiceField):
    def __init__(self, *,
                 model=get_product_model(), field_name='sub_type',
                 limit_choices_to=None,
                 **kwargs):
        super().__init__(model, field_name, **kwargs)
        self.limit_choices_to = limit_choices_to
        # Bypass limits here to prevent usage of "more" feature that does not
        # support the "limit_choice_to" yet
        self.limit = NO_LIMIT

    # TODO: unit test
    @property
    def limit_choices_to(self):
        return self.enum.enumerator.limit_choices_to

    @limit_choices_to.setter
    def limit_choices_to(self, limit_choices_to: Q | dict):
        """
        @param limit_choices_to: A Q object or a dictionary of keyword lookup
               arguments.
        """
        self.enum.enumerator.limit_choices_to = limit_choices_to

    # TODO: unit test
    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)
        result.limit_choices_to = self.limit_choices_to
        return result

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs['data-selection-show-group'] = 'true'
        return attrs
