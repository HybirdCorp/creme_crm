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

from datetime import datetime

from creme_core.forms import CremeEntityForm

from tickets.models.ticket import Ticket
from tickets.models.status import OPEN_PK, CLOSED_PK


class CreateForm(CremeEntityForm):
    class Meta:
        model = Ticket
        exclude = CremeEntityForm.Meta.exclude + ('status', 'closing_date')

    def save(self):
        self.instance.status_id = OPEN_PK
        super(CreateForm, self).save()


class EditForm(CremeEntityForm):
    class Meta:
        model = Ticket
        exclude = CremeEntityForm.Meta.exclude + ('closing_date', )

    def save(self):
        instance = self.instance
        new_status_pk = self.cleaned_data['status'].pk
        old_status_pk = instance.status_id

        if (new_status_pk == CLOSED_PK) and (old_status_pk != CLOSED_PK):
            instance.closing_date = datetime.now()

        super(EditForm, self).save()
