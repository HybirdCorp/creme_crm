################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2023  Hybird
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

from functools import partial

from dateutil.relativedelta import relativedelta
from django.db.transaction import atomic
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from creme.creme_core.creme_jobs.base import JobType
from creme.creme_core.models import CremeProperty, HistoryLine
from creme.gdpr.constants import PROP_IS_ANONYMIZED
from creme.gdpr.models import SoonAnonymized
from creme.persons import get_contact_model


class _AnonymiserType(JobType):
    id = JobType.generate_id('gpdr', 'anonymizer')
    verbose_name = _('Anonymizer (GDPR)')
    periodic = JobType.PERIODIC

    ANONYMIZED_FIELDS = {
        'first_name': '🙈🙉🙊',
        'last_name': '🙈🙉🙊',
        'email': '',
        'mobile': '',
        'phone': '',
    }
    ANONYMISATION_THRESHOLD = relativedelta(years=3)
    WARNING_DELAY = relativedelta(months=6)  # TODO: settings.py? SettingValue?

    def _execute(self, job):
        Contact = get_contact_model()
        mark_anonymized = partial(
            CremeProperty.objects.safe_create, type_id=PROP_IS_ANONYMIZED,
        )

        now_value = now()
        anonymisation_date = now_value - self.ANONYMISATION_THRESHOLD
        warning_date = anonymisation_date + self.WARNING_DELAY

        # TODO: paginator/iterator
        # TODO: bulk_create
        for contact in Contact.objects.filter(
                modified__lte=warning_date,
        ).exclude(
            # Optimization
            properties__type=PROP_IS_ANONYMIZED,
        ):
            if contact.modified <= anonymisation_date:
                with atomic():
                    HistoryLine.disable(contact)
                    for field_name, field_values in self.ANONYMIZED_FIELDS.items():
                        setattr(contact, field_name, field_values)
                    contact.save()  # TODO: update_fields?

                    # TODO: beware a (useless) HistoryLine is created here
                    mark_anonymized(creme_entity=contact)

                    # TODO: exclude relation hline + update them
                    HistoryLine.objects.filter(entity=contact.id).delete()

                    # TODO: remove SoonAnonymized if exists
            else:
                SoonAnonymized.objects.get_or_create(contact=contact)

        # TODO: JobResult.objects.create

    # TODO
    # def get_description(self, job: Job) -> list[str]:
    #     """Get a humanized description, as a list of strings.
    #     To be overloaded by child classes.
    #     """
    #     return []

    # TODO: ??
    # def get_stats(self, job):
    #     count = JobResult.objects.filter(job=job, raw_errors__isnull=True).count()
    #
    #     return [ungettext('%s entity has been successfully modified.',
    #                       '%s entities have been successfully modified.',
    #                       count
    #                      ) % count,
    #            ]


anonymiser_type = _AnonymiserType()
jobs = (anonymiser_type,)
