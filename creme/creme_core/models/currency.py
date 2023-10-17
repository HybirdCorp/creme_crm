################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.db import models
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from ..global_info import cached_per_request
from . import base

logger = logging.getLogger(__name__)


# TODO: factorise? (VAT etc...)
class CurrencyManager(base.MinionManager):
    @cached_per_request('creme_core-default_currency')
    def default(self):
        return self.filter(is_default=True)[0]


class Currency(base.MinionModel):
    name = models.CharField(_('Currency'), max_length=100)
    local_symbol = models.CharField(_('Local symbol'), max_length=100)
    # TODO: unique?
    international_symbol = models.CharField(_('International symbol'), max_length=100)
    is_default = models.BooleanField(_('Is default?'), default=False)

    objects = CurrencyManager()

    creation_label = _('Create a currency')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Currency')
        verbose_name_plural = _('Currencies')
        ordering = ('name',)

    # TODO: factorise (VAT etc...)
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
            first = type(self).objects.exclude(id=self.id).first()

            if first:
                first.is_default = True
                first.save()

        super().delete(*args, **kwargs)


# Can be used as default value for ForeignKey
def get_default_currency_pk():
    try:
        return Currency.objects.default().pk
    except IndexError:
        logger.warning('No default Currency instance found.')
        return None
