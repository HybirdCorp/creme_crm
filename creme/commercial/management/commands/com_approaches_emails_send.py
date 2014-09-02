# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from datetime import timedelta
import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.mail import get_connection
from django.core.mail.message import EmailMessage
from django.core.management.base import BaseCommand
from django.db.models.query_utils import Q
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, activate

from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME

from creme.persons.constants import REL_SUB_CUSTOMER_SUPPLIER


logger = logging.getLogger(__name__)
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

    list_target_orga = [(Q(relations__type=REL_SUB_CUSTOMER_SUPPLIER,
                           relations__object_entity__properties__type=PROP_IS_MANAGED_BY_CREME,
                          ),
                         30 #delay in days #TODO: in settings/SettingKey ?
                        ),
                       ]


    def handle(self, *args, **options):
        from creme.creme_core.models import SettingValue
        from creme.creme_core.models.lock import Mutex, MutexLockedException

        from creme.commercial.constants import IS_COMMERCIAL_APPROACH_EMAIL_NOTIFICATION_ENABLED
        from creme.commercial.models import CommercialApproach

        from creme.opportunities.constants import REL_SUB_TARGETS
        from creme.opportunities.models import Opportunity

        from creme.persons.models import Organisation, Contact

        try:
            lock = Mutex.get_n_lock(LOCK_NAME)
        except MutexLockedException:
            print 'A process is already running'
        else:
            if SettingValue.objects.get(key_id=IS_COMMERCIAL_APPROACH_EMAIL_NOTIFICATION_ENABLED).value:
                activate(settings.LANGUAGE_CODE)#TODO: Activate in the user's language ?

                emails = []

                get_ct = ContentType.objects.get_for_model
                ct_orga    = get_ct(Organisation)
                ct_contact = get_ct(Contact)
                ct_opp     = get_ct(Opportunity)

                now_value = now()
                unmanaged_orgas = Organisation.objects.exclude(properties__type=PROP_IS_MANAGED_BY_CREME)
                opp_filter = Opportunity.objects.filter

                EMAIL_SENDER = settings.EMAIL_SENDER

                for extra_q, delay in self.list_target_orga:
                    com_apps_filter = CommercialApproach.objects \
                                                        .filter(creation_date__gt=now_value - timedelta(days=delay)) \
                                                        .filter

                    #TODO: are 'values_list' real optimizations here ?? ==> remove them when CommercialApproach use real ForeignKey
                    for orga in unmanaged_orgas.filter(extra_q):
                        if com_apps_filter(entity_content_type=ct_orga, entity_id=orga.id).exists():
                            continue

                        if com_apps_filter(entity_content_type=ct_contact,
                                           entity_id__in=orga.get_managers().values_list('id', flat=True)
                                          ).exists():
                            continue

                        if com_apps_filter(entity_content_type=ct_contact,
                                           entity_id__in=orga.get_employees().values_list('id', flat=True)
                                          ).exists():
                            continue

                        if com_apps_filter(entity_content_type=ct_opp,
                                           entity_id__in=opp_filter(relations__type=REL_SUB_TARGETS,
                                                                    relations__object_entity=orga,
                                                                   ).values_list('id', flat=True)
                                          ).exists():
                            continue

                        emails.append(EmailMessage(_(u"[CremeCRM] The organisation <%s> seems neglected") % orga,
                                                   _(u"It seems you haven't created a commercial approach for "
                                                     u"the organisation «%(orga)s» since %(delay)s days.") % {
                                                            'orga':  orga,
                                                            'delay': delay,
                                                        },
                                                   EMAIL_SENDER, [orga.user.email],
                                                  )
                                     )

                #TODO: factorise commands which send emails
                if emails:
                    try:
                        connection = get_connection()
                        connection.open()
                        connection.send_messages(emails)
                        connection.close()

                        logger.info(u"Emails sended")
                    except Exception as e:
                        logger.error(u"An error has occurred during sending mails (%s)" % e)

            Mutex.graceful_release(LOCK_NAME)
