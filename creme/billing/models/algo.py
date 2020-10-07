# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import CTypeForeignKey


class ConfigBillingAlgo(CremeModel):
    organisation = models.ForeignKey(
        settings.PERSONS_ORGANISATION_MODEL,
        verbose_name=_('Organisation'), on_delete=models.CASCADE,
    )
    name_algo = models.CharField(_('Algo name'), max_length=400)
    ct = CTypeForeignKey()

    class Meta:
        app_label = 'billing'
        # TODO unique_together = ("organisation", "name_algo", "ct") ??

    def __str__(self):
        return (
            f'ConfigBillingAlgo('
            f'organisation="{self.organisation}", '
            f'name_algo="{self.name_algo}", '
            f'ct="{self.ct}"'
            f')'
        )


class SimpleBillingAlgo(models.Model):
    organisation = models.ForeignKey(
        settings.PERSONS_ORGANISATION_MODEL,
        verbose_name=_('Organisation'), on_delete=models.CASCADE,
    )
    last_number = models.IntegerField()
    prefix = models.CharField(_('Invoice prefix'), max_length=400)
    ct = CTypeForeignKey()

    ALGO_NAME = 'SIMPLE_ALGO'  # TODO: prefix with app name

    class Meta:
        app_label = 'billing'
        unique_together = ('organisation', 'last_number', 'ct')

    def __str__(self):
        return (
            f'SimpleBillingAlgo('
            f'organisation="{self.organisation}", '
            f'ct="{self.ct}", '
            f'last_number={self.last_number}, '
            f'prefix="{self.prefix}"'
            f')'
        )
