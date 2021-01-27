# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from django.utils.timezone import now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.creme_jobs.base import JobType
from creme.creme_core.models import JobResult
from creme.persons.constants import REL_SUB_CUSTOMER_SUPPLIER


class _ComApproachesEmailsSendType(JobType):
    id = JobType.generate_id('commercial', 'com_approaches_emails_send')
    verbose_name = _('Send emails for commercials approaches')

    # It would be too difficult/inefficient to compute the next wake up,
    # so it is not PSEUDO_PERIODIC.
    periodic = JobType.PERIODIC

    # TODO: add a config form which stores the rules in job.data
    list_target_orga = [(REL_SUB_CUSTOMER_SUPPLIER, 30)]

    def _execute(self, job):
        from creme import persons
        from creme.opportunities import get_opportunity_model
        from creme.opportunities.constants import REL_SUB_TARGETS

        from .models import CommercialApproach

        Organisation = persons.get_organisation_model()
        Contact = persons.get_contact_model()
        Opportunity = get_opportunity_model()

        emails = []

        get_ct = ContentType.objects.get_for_model
        ct_orga    = get_ct(Organisation)
        ct_contact = get_ct(Contact)
        ct_opp     = get_ct(Opportunity)

        now_value = now()
        managed_orga_ids = [
            *Organisation.objects.filter(is_managed=True).values_list('id', flat=True),
        ]
        opp_filter = Opportunity.objects.filter

        EMAIL_SENDER = settings.EMAIL_SENDER

        for rtype, delay in self.list_target_orga:
            com_apps_filter = CommercialApproach.objects.filter(
                creation_date__gt=now_value - timedelta(days=delay),
            ).filter

            # TODO: are 'values_list' real optimizations here ??
            #       ==> remove them when CommercialApproach use real ForeignKey
            for orga in Organisation.objects.filter(
                is_managed=False,
                relations__type=rtype,
                relations__object_entity__in=managed_orga_ids,
            ):
                if com_apps_filter(entity_content_type=ct_orga, entity_id=orga.id).exists():
                    continue

                if com_apps_filter(
                    entity_content_type=ct_contact,
                    entity_id__in=orga.get_managers().values_list('id', flat=True),
                ).exists():
                    continue

                if com_apps_filter(
                    entity_content_type=ct_contact,
                    entity_id__in=orga.get_employees().values_list('id', flat=True),
                ).exists():
                    continue

                if com_apps_filter(
                    entity_content_type=ct_opp,
                    entity_id__in=opp_filter(
                        relations__type=REL_SUB_TARGETS,
                        relations__object_entity=orga,
                    ).values_list('id', flat=True),
                ).exists():
                    continue

                emails.append(EmailMessage(
                    gettext('[CremeCRM] The organisation «{}» seems neglected').format(orga),
                    gettext(
                        "It seems you haven't created a commercial approach for "
                        "the organisation «{orga}» since {delay} days."
                    ).format(
                        orga=orga,
                        delay=delay,
                    ),
                    EMAIL_SENDER, [orga.user.email],
                ))

        # TODO: factorise jobs which send emails
        if emails:
            try:
                with get_connection() as connection:
                    connection.send_messages(emails)
            except Exception as e:
                JobResult.objects.create(
                    job=job,
                    messages=[
                        gettext('An error has occurred while sending emails'),
                        gettext('Original error: {}').format(e),
                    ],
                )

    def get_description(self, job):
        return [
            gettext(
                "For each customer organisation, an email is sent to its owner "
                "(ie: a Creme user), if there is no commercial approach since "
                "{} days linked to: the organisation, one of its managers/employees, "
                "or an Opportunity which targets this organisation."
            ).format(self.list_target_orga[0][1]),
            gettext(
                "Hint: to create commercial approaches, activate the field "
                "«Is a commercial approach?» in the configuration of Activities' forms ; "
                "so when you create an Activity, if you check the box, some approaches "
                "will be created for participants, subjects & linked entities."
            ),
            gettext(
                "Hint: to see commercial approaches, activate the related block "
                "on detail-views."
            ),
        ]


com_approaches_emails_send_type = _ComApproachesEmailsSendType()
jobs = (com_approaches_emails_send_type,)
