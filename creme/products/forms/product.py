# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.forms.fields import MultiCremeEntityField

from creme.media_managers.models import Image
from creme.media_managers.forms.widgets import ImageM2MWidget

from creme.products.models import Product
from creme.products.forms.fields import CategoryField


class ProductForm(CremeEntityForm):
    sub_category = CategoryField(label=_(u'Sub-category'))
    images       = MultiCremeEntityField(label=_(u'Images'), model=Image,
                                         widget=ImageM2MWidget(), required=False,
                                        )

    class Meta(CremeEntityForm.Meta):
        model = Product
        exclude = CremeEntityForm.Meta.exclude + ('category', 'sub_category')

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        instance = self.instance

        if instance.pk is not None:
            self.fields['sub_category'].initial = instance.sub_category

    def save(self, *args, **kwargs):
        instance = self.instance
        sub_category = self.cleaned_data['sub_category']

        instance.category = sub_category.category
        instance.sub_category = sub_category

        return super(ProductForm, self).save(*args, **kwargs)
