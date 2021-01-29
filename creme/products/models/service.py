# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity
from creme.documents.models.fields import ImageEntityManyToManyField

from . import other_models


# TODO: use an abstract base class for Service and Products ??
class AbstractService(CremeEntity):
    name = models.CharField(_('Name'), max_length=100)
    reference = models.CharField(_('Reference'), max_length=100)

    category = models.ForeignKey(
        other_models.Category, verbose_name=_('Category'), on_delete=models.PROTECT,
    )
    sub_category = models.ForeignKey(
        other_models.SubCategory, verbose_name=_('Sub-category'), on_delete=models.PROTECT,
    )

    countable = models.BooleanField(_('Countable'), default=False).set_tags(optional=True)
    unit = models.CharField(_('Unit'), max_length=100, blank=True).set_tags(optional=True)
    quantity_per_unit = models.IntegerField(
        _('Quantity/Unit'), blank=True, null=True,
    ).set_tags(optional=True)
    unit_price = models.DecimalField(_('Unit price'), max_digits=8, decimal_places=2)

    web_site = models.CharField(_('Web Site'), max_length=100, blank=True).set_tags(optional=True)
    images = ImageEntityManyToManyField(verbose_name=_('Images'), blank=True)

    creation_label = _('Create a service')
    save_label = _('Save the service')

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'products'
        verbose_name = _('Service')
        verbose_name_plural = _('Services')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products__view_service', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('products__create_service')

    def get_edit_absolute_url(self):
        return reverse('products__edit_service', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('products__list_services')


class Service(AbstractService):
    class Meta(AbstractService.Meta):
        swappable = 'PRODUCTS_SERVICE_MODEL'
