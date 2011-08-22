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
from logging import error, info

from datetime import datetime, timedelta, timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.mail import get_connection
from django.core.mail.message import EmailMessage
from django.core.management.base import BaseCommand
from django.db.models.query_utils import Q
from django.utils.translation import ugettext_lazy as _, ugettext, activate
from django.conf import settings

from creme_core.constants import PROP_IS_MANAGED_BY_CREME

from persons.constants import REL_SUB_CUSTOMER_SUPPLIER


LOCK_NAME = "com_approaches_sending_emails"

#NB: python manage.py com_approaches_emails_send

class Command(BaseCommand):
    help = """Send emails for commercials approaches.
              Rules:
               - IS_COMMERCIAL_APPROACH_EMAIL_NOTIFICATION_ENABLED (setting key) has to be True
               - For each organisation if no Com app since 30 days:
                - In the organisation
                - In the organisation managers
                - In the organisation employees
                - In the organisation opportunities
    """

    list_target_orga = [(Q(relations__type=REL_SUB_CUSTOMER_SUPPLIER, relations__object_entity__properties__type=PROP_IS_MANAGED_BY_CREME), 30),]


    def handle(self, *args, **options):
        from creme_config.models.setting import SettingValue
        from creme_core.models.lock import Mutex, MutexLockedException

        from commercial.constants import DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW
        from commercial.models import CommercialApproach

        from opportunities.constants import REL_SUB_TARGETS
        from opportunities.models import Opportunity

        from persons.models    import Organisation, Contact

        try:
            lock = Mutex.get_n_lock(LOCK_NAME)

        except MutexLockedException, e:
            print 'A process is already running'

        else:
            if SettingValue.objects.get(key__id=DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW).value:
                for extra_q, delay in self.list_target_orga:

                    now             = datetime.now()
                    thirty_days_ago = now - timedelta(days=delay)


                    com_apps         = CommercialApproach.objects.filter(entity_content_type__in=[ContentType.objects.get_for_model(model) for model in (Organisation, Contact, Opportunity)], creation_date__range=(thirty_days_ago, now))
                    com_apps_filter  = com_apps.filter

                    opportunities_targets_orga = Opportunity.objects.filter(relations__type=REL_SUB_TARGETS)

                    emails_to_send = []
                    emails_append  = emails_to_send.append

                    EMAIL_SENDER = settings.EMAIL_SENDER

                    for organisation in Organisation.objects.filter(~Q(properties__type=PROP_IS_MANAGED_BY_CREME) & extra_q):
                        have_to_send_mail = False

                        is_any_com_app_in_orga = com_apps_filter(entity_id=organisation.id).exists()

                        if not is_any_com_app_in_orga:
                            is_any_com_app_in_managers = com_apps_filter(entity_id__in=organisation.get_managers().values_list('id',flat=True)).exists()

                            if not is_any_com_app_in_managers:
                                is_any_com_app_in_employees = com_apps_filter(entity_id__in=organisation.get_employees().values_list('id',flat=True)).exists()

                                if not is_any_com_app_in_employees and \
                                   not com_apps_filter(entity_id__in=opportunities_targets_orga.filter(relations__object_entity=organisation).values_list('id',flat=True)).exists():
                                    have_to_send_mail = True

                        if have_to_send_mail:
                            activate(settings.LANGUAGE_CODE)#TODO: Activate in the user's language ?
                            emails_append(EmailMessage(_(u"[CremeCRM] The organisation <%s> seems neglected") % organisation,
                                                       _(u"It seems you haven't created a commercial approach for the organisation <%s> since 30 days.") % organisation,
                                                       EMAIL_SENDER, [organisation.user.email]))

                    try:
                        connection = get_connection()
                        connection.open()
                        connection.send_messages(emails_to_send)
                        connection.close()

                        info(u"Emails sended")
                    except Exception, e:
                        error(u"An error has occurred during sending mails (%s)" % e)
        finally:
            Mutex.graceful_release(LOCK_NAME)
