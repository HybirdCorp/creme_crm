################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

import logging

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from creme.creme_core import auth, models
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from ..bricks import NotificationChannelsBrick
from ..forms import notification as notif_forms
from . import base

logger = logging.getLogger(__name__)


class Portal(base.ConfigPortal):
    template_name = 'creme_config/portals/notification.html'
    brick_classes = [NotificationChannelsBrick]


class ChannelCreation(generic.CremeModelCreationPopup):
    model = models.NotificationChannel
    form_class = notif_forms.ChannelForm
    permissions = auth.SUPERUSER_PERM


class ChannelEdition(generic.CremeModelEditionPopup):
    # model = models.NotificationChannel
    queryset = models.NotificationChannel.objects.filter(deleted=None)
    form_class = notif_forms.ChannelForm
    pk_url_kwarg = 'channel_id'
    title = _('Edit the channel «{object}»')
    permissions = auth.SUPERUSER_PERM


class ChannelRequirementSetting(generic.CremeModelEditionPopup):
    # model = models.NotificationChannel
    queryset = models.NotificationChannel.objects.filter(deleted=None)
    form_class = notif_forms.ChannelRequirementForm
    pk_url_kwarg = 'channel_id'
    title = _('Is the channel «{object}» required?')
    permissions = auth.SUPERUSER_PERM

    def check_instance_permissions(self, instance, user):
        if instance.type_id and not user.is_staff:
            raise PermissionDenied(gettext(
                'Only staff users can change a system channel'
            ))


class ChannelDeletion(base.ConfigDeletion):
    id_arg = 'id'
    permissions = auth.SUPERUSER_PERM

    def perform_deletion(self, request):
        chan = get_object_or_404(
            models.NotificationChannel,
            id=get_from_POST_or_404(request.POST, self.id_arg),
        )

        if chan.type_id:
            raise ConflictError('You cannot delete this channel (not custom).')

        if chan.deleted:
            times_used = chan.notifications.count()

            if times_used:
                raise ConflictError(
                    ngettext(
                        'This channel is still used by {count} notification, '
                        'so it cannot be deleted.',
                        'This channel is still used by {count} notifications, '
                        'so it cannot be deleted.',
                        times_used
                    ).format(count=times_used)
                )

            chan.delete()
        else:
            chan.deleted = now()
            chan.save()


# Config Item ------------------------------------------------------------------
class ChannelConfigEdition(generic.CremeModelEditionPopup):
    model = models.NotificationChannelConfigItem
    form_class = notif_forms.ChannelConfigItemForm
    pk_url_kwarg = 'channel_id'
    title = _('Configure the channel «{object}»')

    def check_instance_permissions(self, instance, user):
        if instance.channel.deleted:
            raise ConflictError('Deleted channel cannot be configured')

    def get_object(self, queryset=None):
        # NB: select_for_update() is not very useful here
        #     (each user edits its own configuration)
        chan = get_object_or_404(
            models.NotificationChannel, id=self.kwargs[self.pk_url_kwarg],
        )
        user = self.request.user
        instance = self.model.objects.filter(channel=chan, user=user).first()

        if instance is None:
            logger.warning(
                'The configuration of the channel uuid=%s for user="%s" did not exist?!',
                chan.uuid, user.username,
            )

            instance = models.NotificationChannelConfigItem.objects.smart_create(
                user=user, channel=chan,
            )
        else:
            instance.channel = chan  # Avoid query

        self.check_instance_permissions(instance, user)

        return instance
