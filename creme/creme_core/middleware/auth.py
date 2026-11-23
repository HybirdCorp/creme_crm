################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.transaction import atomic
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils.html import format_html
from django.utils.translation import gettext as _

# TODO: move to core
from creme.creme_config.notification import RoleSwitchContent
from creme.creme_core.constants import UUID_CHANNEL_ADMIN
from creme.creme_core.http import is_ajax
from creme.creme_core.models import Notification


class RoleMiddleware(MiddlewareMixin):
    """A regular user with only deactivated roles is not allowed to do anything.

    We try to avoid a such situation (the configuration for roles refuses to
    deactivate a role if it leads to this case), but we can imagine it happens
    because of:
     - race condition.
     - business code bug.
     - code which has no choice to disable a role (like config import).
    """
    excluded_url_prefixes = [
        settings.PRODUCTION_MEDIA_URL,  # The error page can display an image
        '/creme_logout',  # We redirect to it & it should work
    ]

    def process_request(self, request):
        if any(map(request.path.startswith, self.excluded_url_prefixes)):
            return None

        user = request.user
        role = getattr(user, 'role', None)
        if role and role.deactivated_on:
            valid_role = user.roles.filter(deactivated_on=None).first()

            if valid_role is None:
                message = _(
                    'All your roles are deactivated; please contact your administrator.'
                )

                raise PermissionDenied(
                    message
                    if is_ajax(request) else
                    format_html(
                        '{message}'
                        '<br>'
                        '<form id="logout-form" method="post" action="{url}">'
                        # see django.template.backends.utils.csrf_input()
                        ' <input type="hidden" name="csrfmiddlewaretoken" value="{token}">'
                        ' <button type="submit">{label}</button>'
                        '</form>',
                        message=message,
                        url=reverse('creme_logout'),
                        label=_('Log out'),
                        token=get_token(request),
                    )
                )

            with atomic():
                user.role = valid_role
                user.save(update_fields=['role'])

                Notification.objects.send(
                    users=[user],
                    channel=UUID_CHANNEL_ADMIN,
                    content=RoleSwitchContent(),
                )

        return None
