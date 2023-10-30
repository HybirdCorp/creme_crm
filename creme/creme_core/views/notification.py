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

from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import STAFF_PERM
from creme.creme_core.core.notification import OUTPUT_WEB
from creme.creme_core.forms.notification import SystemUpgradeAnnouncementForm
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.models import Notification
from creme.creme_core.views import generic


class Notifications(generic.BricksView):
    template_name = 'creme_core/notifications.html'


class LastWebNotifications(generic.CheckedView):
    response_class = CremeJsonResponse
    limit = 10

    def get(self, request, *args, **kwargs):
        return self.response_class(self.get_data(request))

    def get_queryset(self, user):
        return Notification.objects.filter(
            user=user, discarded=None, output=OUTPUT_WEB,
        )

    def get_data(self, request):
        user = request.user
        qs = self.get_queryset(user=user)

        return {
            'count': qs.count(),
            'notifications': [
                notif.to_dict(user)
                for notif in qs.order_by('-id').select_related('channel')[:self.limit]
            ],
        }


class NotificationDiscarding(generic.CremeModelDeletion):
    model = Notification

    def get_queryset(self):
        return super().get_queryset().filter(discarded=None, user=self.request.user)

    def perform_deletion(self, request):
        notif = self.get_object()
        notif.discarded = now()
        notif.save()


class SystemUpgradeAnnouncement(generic.CremeFormView):
    form_class = SystemUpgradeAnnouncementForm
    title = _('Announce a system upgrade to users')
    submit_label = Notification.save_label
    permissions = STAFF_PERM

    def get_success_url(self):
        # TODO: <return self.request.POST.get('back_url') or reverse(...)>?
        return reverse('creme_core__notifications')
