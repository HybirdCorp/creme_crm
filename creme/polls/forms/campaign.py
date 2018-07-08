# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2018  Hybird
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

from creme.creme_core.forms import CremeEntityForm
# from creme.creme_core.forms.widgets import CalendarWidget

from .. import get_pollcampaign_model


class PollCampaignForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = get_pollcampaign_model()

    # def __init__(self, *args, **kwargs):
    #     super(PollCampaignForm, self).__init__(*args, **kwargs)
    #     fields = self.fields
    #     print('OLA')
    #     fields['start'].widget = CalendarWidget()
    #     fields['due_date'].widget = CalendarWidget()
