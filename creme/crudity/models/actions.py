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

from pickle import dumps, loads
from typing import Tuple

from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeModel
from creme.creme_core.models import fields as creme_fields


class WaitingAction(CremeModel):
    # Action (i.e: create, update...) # TODO: int instead ??
    action = models.CharField(_('Action'), max_length=100)

    # TODO: split into 2 CharFields 'fetcher' & 'input' ?
    # NB: - If default backend (subject="*"): fetcher_name.
    #     - If not  'fetcher_name - input_name'  (eg: email - raw, email - infopath, sms - raw...).
    source = models.CharField(_('Source'), max_length=100)

    raw_data = models.BinaryField(blank=True, null=True)  # Pickled data

    # Redundant, but faster bd recovery
    ct = creme_fields.CTypeForeignKey(verbose_name=_('Type of resource'))

    subject = models.CharField(_('Subject'), max_length=100)

    # If sandbox per user
    user = creme_fields.CremeUserForeignKey(
        verbose_name=_('Owner'), blank=True, null=True, default=None,
    )

    class Meta:
        app_label = 'crudity'
        verbose_name = _('Waiting action')
        verbose_name_plural = _('Waiting actions')

    @property
    def data(self) -> dict:
        return loads(self.raw_data)

    @data.setter
    def data(self, data: dict):
        self.raw_data = dumps(data)

    def can_validate_or_delete(self, user) -> Tuple[bool, str]:
        """self.user not None means that sandbox is by user"""
        if self.user is not None and self.user != user and not user.is_superuser:
            return (
                False,
                gettext(
                    'You are not allowed to validate/delete the waiting action <{}>'
                ).format(self.id)
            )

        return True, gettext('OK')
