################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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

# import warnings
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .. import get_address_model


class PersonWithAddressesMixin(models.Model):
    billing_address = models.ForeignKey(
        settings.PERSONS_ADDRESS_MODEL,
        verbose_name=_('Billing address'),
        null=True, on_delete=models.SET_NULL,
        editable=False, related_name='+',
    ).set_tags(enumerable=False, optional=True)  # NB: "clonable=False" is useless
    shipping_address = models.ForeignKey(
        settings.PERSONS_ADDRESS_MODEL,
        verbose_name=_('Shipping address'),
        null=True, on_delete=models.SET_NULL,
        editable=False, related_name='+',
    ).set_tags(enumerable=False, optional=True)

    class Meta:
        abstract = True

    # def _aux_post_save_clone(self, source):
    #     warnings.warn(
    #         'The method PersonWithAddressesMixin._post_save_clone() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     save = False
    #
    #     if source.billing_address is not None:
    #         self.billing_address = source.billing_address.clone(self)
    #         save = True
    #
    #     if source.shipping_address is not None:
    #         self.shipping_address = source.shipping_address.clone(self)
    #         save = True
    #
    #     if save:
    #         self.save()
    #
    #     for address in source.other_addresses:
    #         address.clone(self)

    @property
    def other_addresses(self):
        excluded_ids = filter(
            None,
            (self.billing_address_id, self.shipping_address_id),
        )

        return get_address_model().objects.filter(
            object_id=self.id,
        ).exclude(pk__in=excluded_ids)
