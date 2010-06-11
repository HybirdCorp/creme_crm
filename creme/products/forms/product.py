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

from django.forms import ModelChoiceField, Select
from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeModelForm
from creme_core.forms.fields import MultiCremeEntityField
from creme_core.forms.widgets import DependentSelect

from media_managers.models import Image
from media_managers.forms.widgets import ImageM2MWidget

from products.models import Product, Category, SubCategory


#class ProductListViewForm(CremeModelForm):
    #class Meta:
        #model   = Product
        #exclude = ('category', 'sub_category', 'images')


class ProductCreateForm(CremeModelForm):
    class Meta:
        model = Product
        exclude = CremeModelForm.exclude

    category     = ModelChoiceField(queryset=Category.objects.all(), label=_(u'Catégorie'),
                                    widget=DependentSelect(target_id='id_sub_category', target_url='/products/sub_category/load'))
    sub_category = ModelChoiceField(queryset=SubCategory.objects.all(),
                                    label=_(u'Sous-catégorie'),
                                    widget=Select(attrs={'id': 'id_sub_category'}))

    images = MultiCremeEntityField(required=False, model=Image,
                                   widget=ImageM2MWidget())

    def __init__(self, *args, **kwargs):
        CremeModelForm.__init__(self, *args, **kwargs)

        instance = self.instance

        if instance.pk is not None: #TODO: create a ProductEditForm instead of this test ?????
            cat_widget = self.fields['category'].widget
            cat_widget.set_source(instance.category.pk)
            cat_widget.set_target(instance.sub_category.pk)
