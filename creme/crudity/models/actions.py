# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from pickle import loads, dumps

from django.db.models import BinaryField, CharField
from django.utils.translation import gettext_lazy as _, gettext

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import CremeUserForeignKey, CTypeForeignKey


class WaitingAction(CremeModel):
    action  = CharField(_('Action'), max_length=100)  # Action (i.e: create, update...) # TODO: int instead ??
    # TODO: split into 2 CharFields 'fetcher' & 'input' ?
    # NB: - If default backend (subject="*"): fetcher_name.
    #     - If not  'fetcher_name - input_name'  (i.e: email - raw, email - infopath, sms - raw...).
    source  = CharField(_('Source'), max_length=100)
    raw_data = BinaryField(blank=True, null=True)  # Pickled data
    ct      = CTypeForeignKey(verbose_name=_('Type of resource'))  # Redundant, but faster bd recovery
    subject = CharField(_('Subject'), max_length=100)
    user    = CremeUserForeignKey(verbose_name=_('Owner'), blank=True, null=True, default=None)  # If sandbox per user

    class Meta:
        app_label = 'crudity'
        verbose_name = _('Waiting action')
        verbose_name_plural = _('Waiting actions')

    @property
    def data(self):
        return loads(self.raw_data)

    @data.setter
    def data(self, data):
        self.raw_data = dumps(data)

    def can_validate_or_delete(self, user):
        """self.user not None means that sandbox is by user"""
        if self.user is not None and self.user != user and not user.is_superuser:
            return False, gettext('You are not allowed to validate/delete the waiting action <{}>').format(self.id)

        return True, gettext('OK')
