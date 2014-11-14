# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2014  Hybird
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

from django.forms.util import ValidationError
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms.fields import JSONField
from creme.creme_core.forms.widgets import ChainedInput

from ..models import Category, SubCategory


class CategorySelector(ChainedInput):
    def __init__(self, categories, attrs=None, creation_allowed=True):
        super(CategorySelector, self).__init__(attrs)
        input_attrs = {'auto': False}
        self.creation_allowed = creation_allowed

        add = self.add_dselect
        add('category', options=categories, attrs=input_attrs, label=_(u'Category'))
        add('subcategory', options='/products/sub_category/${category}/json',
            attrs=input_attrs, label=_(u'Sub-category'),
           )


class CategoryField(JSONField):
    default_error_messages = {
        'doesnotexist':          _(u"This category doesn't exist."),
        'categorynotallowed':    _(u"This category causes constraint error."),
        'subcategorynotallowed': _(u"This sub-category causes constraint error."),
    }
    value_type = dict

    def __init__(self, categories=None, *args, **kwargs):
        super(CategoryField, self).__init__(*args, **kwargs)
        self.categories = categories

    def __deepcopy__(self, memo):
        result = super(CategoryField, self).__deepcopy__(memo)
        result._build_widget() #refresh the list of categories
        return result

    def _create_widget(self):
        return CategorySelector(self._get_categories_options(self._get_categories_objects()),
                                attrs={'reset': False, 'direction': ChainedInput.VERTICAL},
                               )

    def _clean_subcategory(self, category_pk, subcategory_pk):
        self._clean_category(category_pk)

        try:
            subcategory = SubCategory.objects.get(pk=subcategory_pk)
        except SubCategory.DoesNotExist:
            raise ValidationError(self.error_messages['doesnotexist'])

        if subcategory.category_id != category_pk:
            raise ValidationError(self.error_messages['subcategorynotallowed'])

        return subcategory

    def _clean_category(self, category_pk):
        # check category in allowed ones
        for category in self._get_categories_objects():
            if category.pk == category_pk:
                return category

        raise ValidationError(self.error_messages['categorynotallowed'])

    def _get_categories_options(self, categories): #TODO: factorise ??
        return ((category.pk, unicode(category)) for category in categories)

    def _get_categories_objects(self):
        ids = self._categories
        return Category.objects.filter(id__in=ids) if ids else Category.objects.all()

    @property
    def categories(self):
        return self._categories

    @categories.setter
    def categories(self, categories):
        self._categories = categories or []
        self._build_widget()

    def _value_to_jsonifiable(self, value):
        if isinstance(value, SubCategory):
            category = value.category_id
            subcategory = value.id
        else:
            category, subcategory = value

        return {'category': category, 'subcategory': subcategory}

    def _value_from_unjsonfied(self, data):
        clean_value = self.clean_value

        return self._clean_subcategory(clean_value(data, 'category', int),
                                       clean_value(data, 'subcategory', int),
                                      )
