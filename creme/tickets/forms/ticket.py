# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from datetime import datetime

from creme_core.forms import CremeEntityForm

from tickets.models import Ticket
from tickets.models.status import OPEN_PK, CLOSED_PK


class TicketCreateForm(CremeEntityForm):
    class Meta:
        model = Ticket
        exclude = CremeEntityForm.Meta.exclude + ('status', 'closing_date')

    def save(self):
        self.instance.status_id = OPEN_PK
        return super(TicketCreateForm, self).save()


class TicketEditForm(CremeEntityForm):
    class Meta:
        model = Ticket
        exclude = CremeEntityForm.Meta.exclude + ('closing_date', )

    def __init__(self, *args, **kwargs):
        super(TicketEditForm, self).__init__(*args, **kwargs)
        self.old_status_id = self.instance.status_id

    def save(self):
        instance = self.instance

        if (instance.status_id == CLOSED_PK) and (self.old_status_id != CLOSED_PK):
            instance.closing_date = datetime.now()

        return super(TicketEditForm, self).save()
