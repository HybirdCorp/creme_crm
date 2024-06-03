################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import MinionModel
from creme.creme_core.models import fields as core_fields


class Status(MinionModel):
    """Status of a ticket: open, closed, invalid..."""
    name = models.CharField(_('Name'), max_length=100, unique=True)
    is_closed = models.BooleanField(
        _('Is a "closed" status?'),
        default=False,
        help_text=_(
            'If you set as closed, existing tickets which use this status will '
            'not be updated automatically (i.e. closing dates will not be set).'
        ),
    )
    order = core_fields.BasicAutoField()  # Used by creme_config
    color = core_fields.ColorField(default=core_fields.ColorField.random)

    creation_label = pgettext_lazy('tickets-status', 'Create a status')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'tickets'
        verbose_name = _('Ticket status')
        verbose_name_plural = _('Ticket statuses')
        ordering = ('order',)
