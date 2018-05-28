# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2018  Hybird
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
# import warnings

from django.db.models.query import QuerySet
from django.forms.utils import ValidationError
from django.utils.translation import ugettext as _

from creme.creme_core.forms.fields import JSONField, ChoiceModelIterator
from creme.creme_core.forms.widgets import ChainedInput, ActionButtonList
from creme.creme_core.utils.url import TemplateURLBuilder

from ..models import Category, SubCategory


class CreatorCategorySelector(ActionButtonList):
    def __init__(self, categories=(), attrs=None, creation_url='', creation_allowed=False):
        super(CreatorCategorySelector, self).__init__(attrs)
        self.categories = categories
        self.creation_allowed = creation_allowed
        self.creation_url = creation_url

    def _is_disabled(self, attrs):
        if attrs is not None:
            return 'disabled' in attrs or 'readonly' in attrs

        return False

    def _build_actions(self, attrs):
        is_disabled = self._is_disabled(attrs)

        self.clear_actions()

        if not is_disabled:
            allowed = self.creation_allowed and bool(self.creation_url)
            url = self.creation_url + '?category=${_delegate_.category}'

            self.add_action('create', SubCategory.creation_label, enabled=allowed, popupUrl=url,
                            title=_(u'Create') if allowed else _(u"Can't create"),
                            # TODO : Temporarily disable this title for UI consistency.
                            # popupTitle=SubCategory.creation_label,
                           )

    def get_context(self, name, value, attrs):
        selector = ChainedInput(self.attrs)
        add = partial(selector.add_dselect, attrs={'auto': False})
        add('category', options=self.categories, label=_(u'Category'))
        add('subcategory', options=TemplateURLBuilder(category_id=(TemplateURLBuilder.Int, '${category}'))
                                                     .resolve('products__subcategories'),
            label=_(u'Sub-category')
           )

        self.delegate = selector
        self._build_actions(attrs)

        return super(CreatorCategorySelector, self).get_context(name=name, value=value, attrs=attrs)


class CategoryField(JSONField):
    widget = CreatorCategorySelector  # need 'categories' "attribute"
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

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self._update_creation_info()

    def _update_creation_info(self):
        from creme.creme_config.registry import config_registry

        widget = self.widget
        widget.creation_url, widget.creation_allowed = config_registry.get_model_creation_info(SubCategory, self.user)

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
