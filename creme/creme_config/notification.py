################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from creme.creme_core.core.notification import StringBaseContent


class PasswordChangeContent(StringBaseContent):
    id = StringBaseContent.generate_id('creme_config', 'password_change')

    subject = _('Password change')
    body = html_body = _('Your password has been changed by an administrator.')


class RoleSwitchContent(StringBaseContent):
    id = StringBaseContent.generate_id('creme_config', 'role_switch')

    subject = _('Role switch')
    body = html_body = _(
        'Your role has been switched to another role because it has been disabled.'
    )
