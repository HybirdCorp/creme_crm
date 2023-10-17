################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2025  Hybird
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

import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.db.transaction import atomic
from django.utils.formats import number_format
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..constants import DEFAULT_VAT
from ..global_info import cached_per_request
from . import base
from .fields import DecimalPercentField

logger = logging.getLogger(__name__)


class VatManager(base.MinionManager):
    @cached_per_request('creme_core-default_vat')
    def default(self):
        return self.filter(is_default=True)[0]


class Vat(base.MinionModel):
    # TODO: unique? (if key, what about edition?)
    value = DecimalPercentField(_('VAT'), default=DEFAULT_VAT)
    is_default = models.BooleanField(_('Is default?'), default=False)

    objects = VatManager()

    creation_label = _('Create a VAT value')

    def __str__(self):
        return f'{number_format(self.value, force_grouping=True)} %'

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('VAT')
        verbose_name_plural = _('VAT')
        ordering = ('value',)

    # TODO: True uniqueness for the field 'value'
    #       => need a data migration (beware to filters & workflow conditions)
    def clean(self):
        qs = type(self).objects.filter(value=self.value)
        if self.id:
            qs = qs.exclude(id=self.id)

        if qs.exists():
            raise ValidationError({
                'value': ValidationError(
                    gettext('There is already a VAT with this value.'),
                    # code='TODO',
                ),
            })

    @atomic
    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.is_default:
            type(self).objects.update(is_default=False)
        elif not type(self).objects.filter(is_default=True).exclude(pk=self.id).exists():
            self.is_default = True

        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    @atomic
    def delete(self, *args, **kwargs):
        if self.is_default:
            first_vat = type(self).objects.exclude(id=self.id).first()

            if first_vat:
                first_vat.is_default = True
                first_vat.save()

        super().delete(*args, **kwargs)


# Can be used as default value for ForeignKey
def get_default_vat_pk():
    try:
        return Vat.objects.default().pk
    except IndexError:
        logger.warning('No default VAT instance found.')
        return None
