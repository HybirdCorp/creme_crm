# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.db.models import Model, CharField, BooleanField
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.models import CremeModel


OPEN_PK       = 1
CLOSED_PK     = 2
INVALID_PK    = 3
DUPLICATED_PK = 4
WONTFIX_PK    = 5

BASE_STATUS = ((OPEN_PK,        ugettext('Open')),
               (CLOSED_PK,      ugettext('Closed')),
               (INVALID_PK,     ugettext('Invalid')),
               (DUPLICATED_PK,  ugettext('Duplicated')),
               (WONTFIX_PK,     ugettext("Won't fix")),
              )

class Status(CremeModel):
    """Status of a ticket: open, closed, invalid... """
    name      = CharField(_(u'Name'), max_length=100, blank=False, null=False, unique=True)
    deletable = BooleanField(_(u'Deletable'))

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'tickets'
        verbose_name = _(u'Ticket status')
        verbose_name_plural  = _(u'Ticket status')
