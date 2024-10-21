################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2024  Hybird
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

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models.sending import EmailSending


@receiver(post_save, sender=EmailSending, dispatch_uid='emails-refresh_campaign_job')
def _refresh_campaign_job(sender, instance, created, **kwargs):
    from .creme_jobs import campaign_emails_send_type

    if created:
        campaign_emails_send_type.refresh_job()
