# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2017  Hybird
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

from functools import partial

from django.db.models.query import QuerySet
from django.forms.utils import ValidationError
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms.fields import JSONField, ChoiceModelIterator
from creme.creme_core.forms.widgets import ChainedInput
from creme.creme_core.utils.url import TemplateURLBuilder

from ..models import Category, SubCategory


class CategorySelector(ChainedInput):
    def __init__(self, categories=(), attrs=None, creation_allowed=True):
        super(CategorySelector, self).__init__(attrs)
        self.creation_allowed = creation_allowed  # TODO: useless at the moment...
        self.categories = categories

    def render(self, name, value, attrs=None):
        add = partial(self.add_dselect, attrs={'auto': False})
        add('category', options=self.categories, label=_(u'Category'))
        add('subcategory',
            # options='/products/sub_category/${category}/json',
            options=TemplateURLBuilder(category_id=(TemplateURLBuilder.Int, '${category}'))
                                      .resolve('products__subcategories'),
            label=_(u'Sub-category'),
           )

        return super(CategorySelector, self).render(name, value, attrs)


class CategoryField(JSONField):
    widget = CategorySelector  # need 'categories' "attribute"
    default_error_messages = {
        'doesnotexist':          _(u"This category doesn't exist."),
        'categorynotallowed':    _(u'This category causes constraint error.'),
        'subcategorynotallowed': _(u'This sub-category causes constraint error.'),
    }
    value_type = dict

    def __init__(self, categories=Category.objects.all(), *args, **kwargs):
        super(CategoryField, self).__init__(*args, **kwargs)
        self.categories = categories

    def __deepcopy__(self, memo):
        result = super(CategoryField, self).__deepcopy__(memo)

        # Need to force a new ChoiceModelIterator to be created.
        result.categories = result.categories

        return result

    def widget_attrs(self, widget):  # See Field.widget_attrs()
        return {'reset': False, 'direction': ChainedInput.VERTICAL}

    def _clean_subcategory(self, category_pk, subcategory_pk):
        self._clean_category(category_pk)

        try:
            subcategory = SubCategory.objects.get(pk=subcategory_pk)
        except SubCategory.DoesNotExist:
            raise ValidationError(self.error_messages['doesnotexist'], code='doesnotexist')

        if subcategory.category_id != category_pk:
            raise ValidationError(self.error_messages['subcategorynotallowed'],
                                  code='subcategorynotallowed',
                                 )

        return subcategory

    def _clean_category(self, category_pk):
        # Check category in allowed ones
        try:
            category = self._categories.get(id=category_pk)
        except Category.DoesNotExist:
            raise ValidationError(self.error_messages['categorynotallowed'],
                                  code='categorynotallowed',
                                 )

        return category

    @property
    def categories(self):
        return self._categories

    @categories.setter
    def categories(self, categories):
        if not isinstance(categories, QuerySet):
            categories = Category.objects.filter(id__in=list(categories))

        self._categories = categories
        self.widget.categories = ChoiceModelIterator(categories)

    def _value_to_jsonifiable(self, value):
        if isinstance(value, SubCategory):
            category_id    = value.category_id
            subcategory_id = value.id
        else:
            category_id, subcategory_id = value

        return {'category': category_id, 'subcategory': subcategory_id}

    def _value_from_unjsonfied(self, data):
        clean_value = self.clean_value

        return self._clean_subcategory(clean_value(data, 'category', int),
                                       clean_value(data, 'subcategory', int),
                                      )
