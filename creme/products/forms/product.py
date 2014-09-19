# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.utils.translation import ugettext as _

from creme.creme_core.forms.bulk import EntityInnerEditForm
from creme.creme_core.forms.widgets import Label
from creme.creme_core.gui.bulk_update import bulk_update_registry
from creme.creme_core.utils.meta import FieldInfo

from ..models import Product
from .base import _BaseCreateForm, _BaseEditForm


class ProductCreateForm(_BaseCreateForm):
    class Meta(_BaseCreateForm.Meta):
        model = Product


class ProductEditForm(_BaseEditForm):
    class Meta(_BaseEditForm.Meta):
        model = Product

class ProductInnerEditCategory(_BaseEditForm):
    class Meta(_BaseEditForm.Meta):
        model = Product
        fields = ('sub_category',)

    def __init__(self, model, field_name, user, instance, *args, **kwargs):
        super(ProductInnerEditCategory, self).__init__(instance=instance, user=user, *args, **kwargs)
        del self.fields['user']

    def clean(self, *args, **kwargs):
        return super(ProductInnerEditCategory, self).clean(*args, **kwargs)
