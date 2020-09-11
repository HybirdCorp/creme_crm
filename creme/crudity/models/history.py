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

from typing import Optional

from django.db import models
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity, CremeModel
from creme.creme_core.models import fields as core_fields


class History(CremeModel):
    entity = models.ForeignKey(
        CremeEntity, verbose_name=_('Entity'), on_delete=models.CASCADE,
    )
    created = core_fields.CreationDateTimeField(_('Creation date'))

    # Action (i.e: create, update...)
    action = models.CharField(_('Action'), max_length=100)

    # Source (i.e: email raw, email from infopath, sms raw...)
    source = models.CharField(_('Source'), max_length=100)

    description = models.TextField(_('Description'), blank=True, null=True)

    user = core_fields.CremeUserForeignKey(
        verbose_name=_('Owner'), blank=True, null=True, default=None,
    )  # Case of sandboxes are by user

    class Meta:
        app_label = 'crudity'
        verbose_name = _('History')
        verbose_name_plural = _('History')

    def get_entity(self) -> Optional[CremeEntity]:
        entity = self.entity

        if entity:
            entity = entity.get_real_entity()

        return entity

    def __str__(self):
        e = self.get_entity()
        return f'History of "{e}"' if e else 'History'
