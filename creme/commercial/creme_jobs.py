# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.mail import get_connection
from django.core.mail.message import EmailMessage
from django.db.models.query_utils import Q
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme.creme_core.creme_jobs.base import JobType
from creme.creme_core.models import JobResult  # SettingValue

from creme.persons.constants import REL_SUB_CUSTOMER_SUPPLIER

# from .constants import IS_COMMERCIAL_APPROACH_EMAIL_NOTIFICATION_ENABLED


class _ComApproachesEmailsSendType(JobType):
    id           = JobType.generate_id('commercial', 'com_approaches_emails_send')
    verbose_name = _('Send emails for commercials approaches')
    periodic     = JobType.PERIODIC  # It would be too difficult/inefficient to
                                     # compute the next wake up, so it is not PSEUDO_PERIODIC.

    # TODO: add a config form which stores the rules in job.data
    list_target_orga = [(Q(relations__type=REL_SUB_CUSTOMER_SUPPLIER,
                           relations__object_entity__properties__type=PROP_IS_MANAGED_BY_CREME,
                          ),
                         30  # delay in days # TODO: in settings/SettingKey/job.data ?
                        ),
                       ]

    def _execute(self, job):
        # if not SettingValue.objects.get(key_id=IS_COMMERCIAL_APPROACH_EMAIL_NOTIFICATION_ENABLED).value:
        #     return

        from creme.persons import get_contact_model, get_organisation_model

        from creme.opportunities import get_opportunity_model
        from creme.opportunities.constants import REL_SUB_TARGETS

        from .models import CommercialApproach

        Organisation = get_organisation_model()
        Contact = get_contact_model()
        Opportunity = get_opportunity_model()

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

            # TODO: are 'values_list' real optimizations here ??
            #       ==> remove them when CommercialApproach use real ForeignKey
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

                emails.append(EmailMessage(ugettext(u"[CremeCRM] The organisation «%s» seems neglected") % orga,
                                           ugettext(u"It seems you haven't created a commercial approach for "
                                                    u"the organisation «%(orga)s» since %(delay)s days.") % {
                                               'orga':  orga,
                                               'delay': delay,
                                           },
                                           EMAIL_SENDER, [orga.user.email],
                                          )
                             )

        # TODO: factorise jobs which send emails
        if emails:
            try:
                with get_connection() as connection:
                    connection.send_messages(emails)
            except Exception as e:
                JobResult.objects.create(job=job,
                                         messages=[ugettext(u'An error has occurred while sending emails'),
                                                   ugettext(u'Original error: %s') % e,
                                                  ],
                                        )

    def get_description(self, job):
        return [ugettext("For each customer organisation, an email is sent to its owner (ie: a Creme user), "
                         "if there is no commercial approach since %s days linked to: "
                         "the organisation, one of its managers/employees, "
                         "or an Opportunity which targets this organisation."
                        ) % self.list_target_orga[0][1],
               ]


com_approaches_emails_send_type = _ComApproachesEmailsSendType()
jobs = (com_approaches_emails_send_type,)
