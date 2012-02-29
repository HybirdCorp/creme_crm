# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.db.models import (CharField, ForeignKey, BooleanField, IntegerField,
                              DecimalField, ManyToManyField, PROTECT)
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity

from media_managers.models import Image

from other_models import Category, SubCategory


#TODO: use an abstract base class for Service and Products ??

class Service(CremeEntity):
    name              = CharField(_(u'Name'), max_length=100)
    description       = CharField(_(u'Description'), max_length=200)
    reference         = CharField(_(u'Reference'), max_length=100)
    category          = ForeignKey(Category, verbose_name=_(u'Category'))
    sub_category      = ForeignKey(SubCategory, verbose_name=_(u'Sub-category'), on_delete=PROTECT)
    countable         = BooleanField(_(u'Countable'))
    unit              = CharField(_(u'Unit'), max_length=100)
    quantity_per_unit = IntegerField(_(u'Quantity/Unit'), blank=True, null=True)
    unit_price        = DecimalField(_(u'Unit price'), max_digits=8, decimal_places=2)
    web_site          = CharField(_(u'Web Site'), max_length=100, blank=True, null=True)
    images            = ManyToManyField(Image, blank=True, null=True, verbose_name=_(u'Images'), related_name='ServiceImages_set' )

    research_fields = CremeEntity.research_fields + ['name', 'reference', 'description', 'sub_category__name', 'category__name']

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/products/service/%s" % self.id

    def get_edit_absolute_url(self):
        return "/products/service/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/products/services"

    class Meta:
        app_label = 'products'
        verbose_name = _(u'Service')
        verbose_name_plural = _(u'Services')
