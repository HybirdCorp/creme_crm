# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.forms.util import ValidationError

from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeEntityForm
from creme_core.forms.fields import MultiCremeEntityField, JSONField
from creme_core.forms.widgets import ChainedInput, DynamicSelect

from media_managers.models import Image
from media_managers.forms.widgets import ImageM2MWidget

from products.models import Product, Category, SubCategory

class ProductCategorySelector(ChainedInput):#TODO Rename to CategorySelector as its used for Service too
    def __init__(self, categories, attrs=None, creation_allowed=True):
        super(ProductCategorySelector, self).__init__(attrs)
        input_attrs = {'auto': False}
        self.creation_allowed = creation_allowed

        self.add_dselect("category", options=categories, attrs=input_attrs, label=_(u'Category'))
        self.add_dselect("subcategory", options='/products/sub_category/${category}/json', attrs=input_attrs, label=_(u'Sub-category'))

class ProductCategoryField(JSONField):#TODO Rename to CategoryField as its used for Service too
    default_error_messages = {
        'doesnotexist' : _(u"This category doesn't exist."),
        'categorynotallowed' : _(u"This category cause constraint error."),
        'subcategorynotallowed' : _(u"This sub-category cause constraint error."),
    }

    def __init__(self, categories=None, *args, **kwargs):
        super(ProductCategoryField, self).__init__(*args, **kwargs)
        self._categories = categories or []
        self._build_widget()

    def _create_widget(self):
        return ProductCategorySelector(self._get_categories_options(self._get_categories_objects()), 
                                       attrs={'reset':False, 'direction':ChainedInput.VERTICAL})
    #TODO : wait for django 1.2 and new widget api to remove this hack
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        if isinstance(value, SubCategory):
            category = value.category_id
            subcategory = value.id
        else:
            category, subcategory = value

        return self.format_json({'category': category, 'subcategory': subcategory})

    def clean(self, value):
        data = self.clean_json(value)

        if data is not None and not isinstance(data, dict):
            raise ValidationError(self.error_messages['invalidformat'])

        if not data:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return None

        return self.clean_subcategory(self.clean_value(data, 'category', int), self.clean_value(data, 'subcategory', int))

    def clean_subcategory(self, category_pk, subcategory_pk):
        self.clean_category(category_pk)

        try:
            subcategory = SubCategory.objects.get(pk=subcategory_pk)
        except SubCategory.DoesNotExist:
            if self.required:
                raise ValidationError(self.error_messages['doesnotexist'])

        if subcategory.category.id != category_pk:
            raise ValidationError(self.error_messages['subcategorynotallowed'])

        return subcategory

    def clean_category(self, category_pk):
        # check category in allowed ones
        for category in (category for category in self._get_categories_objects() if category.pk == category_pk):
            return category

        raise ValidationError(self.error_messages['categorynotallowed'])

    def _get_categories_options(self, categories):
        return ((category.pk, unicode(category)) for category in categories)

    def _get_categories_objects(self):
        return Category.objects.filter(id__in=self._categories) if self._categories else Category.objects.all()

    def _set_categories(self, categories=None):
        self._categories = categories or []
        self._build_widget()

    categories = property(lambda self: self._categories, _set_categories); del _set_categories


class ProductCreateForm(CremeEntityForm):
    sub_category = ProductCategoryField(label=_(u'Sub-category'))

    images       = MultiCremeEntityField(label=_(u'Images'), model=Image, widget=ImageM2MWidget(), required=False)

    class Meta(CremeEntityForm.Meta):
        model = Product
        exclude = CremeEntityForm.Meta.exclude + ('category', 'sub_category',)

    def __init__(self, *args, **kwargs):
        super(ProductCreateForm, self).__init__(*args, **kwargs)

        instance = self.instance

        if instance.pk is not None: #TODO: create a ProductEditForm instead of this test ?????
            self.fields['sub_category'].initial = instance.sub_category
#            cat_widget = self.fields['category'].widget
#            cat_widget.set_source(instance.category.pk)
#            cat_widget.set_target(instance.sub_category.pk)

    def save(self, *args, **kwargs):
        instance = self.instance
        sub_category = self.cleaned_data['sub_category']

        instance.category = sub_category.category
        instance.sub_category = sub_category

        return super(ProductCreateForm, self).save(*args, **kwargs)
