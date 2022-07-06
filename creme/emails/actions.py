################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2019  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme import emails
from creme.creme_core.gui import actions

EntityEmail = emails.get_entityemail_model()


class EntityEmailResendAction(actions.UIAction):
    id = actions.UIAction.generate_id('emails', 'resend')

    model = EntityEmail
    type = 'email-resend'
    url_name = 'emails__resend_emails'
    label = _('Re-send email')
    icon = 'email'

    def _get_options(self):
        return {
            'selection': [self.instance.id],
        }


class BulkEntityEmailResendAction(actions.BulkEntityAction):
    id = actions.BulkEntityAction.generate_id('emails', 'bulk_resend')

    model = EntityEmail
    type = 'email-resend-selection'
    url_name = 'emails__resend_emails'
    label = _('Re-send email(s)')
    icon = 'email'
