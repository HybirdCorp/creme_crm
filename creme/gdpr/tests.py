from datetime import date, timedelta
from functools import partial

from dateutil.relativedelta import relativedelta
# from django.utils.translation import gettext as _
from django.urls import reverse
from django.utils.timezone import now

# import creme.activities.constants as a_constants
# from creme.activities import get_activity_model
# from creme.activities.models import ActivitySubType, ActivityType, Calendar
# from creme.activities.tests.base import skipIfCustomActivity
from creme.creme_core.models import CremeEntity, HistoryLine, Job
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons import get_contact_model, get_organisation_model
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .bricks import SoonAnonymizedEntitiesBrick
from .constants import PROP_IS_ANONYMIZED
from .creme_jobs import anonymiser_type
from .models import SoonAnonymized

Organisation = get_organisation_model()
# Activity = get_activity_model()
Contact = get_contact_model()


class GDPRTestCase(BrickTestCaseMixin, CremeTestCase):
    def assertSoonAnonymized(self, entity):
        # self.get_object_or_fail(SoonAnonymized, entity_id=entity.id)
        self.get_object_or_fail(SoonAnonymized, contact_id=entity.id)

    def assertNotSoonAnonymized(self, entity):
        # if SoonAnonymized.objects.filter(entity_id=entity.id).exists():
        if SoonAnonymized.objects.filter(contact_id=entity.id).exists():
            self.fail(f'<{entity}> is marked as soon anonymized')

    def get_job(self):
        return self.get_object_or_fail(Job, type_id=anonymiser_type.id)

    def test_populate(self):
        job = self.get_job()
        self.assertEqual(Job.STATUS_OK, job.status)
        self.assertFalse(job.enabled)
        self.assertIsNotNone(job.periodicity)
        self.assertIsNotNone(timedelta(days=1), job.periodicity.as_timedelta())

        ptype = self.get_propertytype_or_fail(PROP_IS_ANONYMIZED)
        self.assertFalse(ptype.is_custom)

    @skipIfCustomContact
    def test_soon_anonymized(self):
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        contacts = [
            create_contact(first_name='Bilbo', last_name='Baggins'),
            create_contact(first_name='Frodo', last_name='Baggins'),
            create_contact(first_name='Frodo', last_name='Baggins'),
        ]

        create_sa = SoonAnonymized.objects.create
        # create_sa(real_entity=contacts[0])
        # create_sa(real_entity=contacts[1])
        create_sa(contact=contacts[0])
        create_sa(contact=contacts[1])

        response = self.assertGET200(reverse('gdpr__list_soon_anonymized'))
        self.assertTemplateUsed(response, 'gdpr/list-soon-anonymized.html')

        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=SoonAnonymizedEntitiesBrick)
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Entity soon anonymized',
            plural_title='{count} Entities soon anonymized',
        )
        self.assertInstanceLink(brick_node, contacts[0])
        self.assertInstanceLink(brick_node, contacts[1])
        self.assertNoInstanceLink(brick_node, contacts[2])

    # TODO: move to base?
    @staticmethod
    def _oldify(*entities, **delta_kwargs):
        CremeEntity.objects.filter(
            id__in=[e.id for e in entities],
        ).update(modified=now() - relativedelta(**delta_kwargs))

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_job(self):
        "2 thresholds (soon anonymized & anonymized)."
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        contacts = [
            create_contact(first_name='Bilbo', last_name='Baggins'),
            create_contact(first_name='Frodo', last_name='Baggins'),
            create_contact(first_name='Gandalf', last_name='The grey'),
        ]

        orga = Organisation.objects.create(user=user, name='Gondor')

        self._oldify(contacts[0], years=3, months=1)
        self._oldify(contacts[1], years=2, months=7)
        self._oldify(orga, year=4)

        anonymiser_type.execute(self.get_job())

        contact1 = contacts[0]
        self.assertHasProperty(contact1, PROP_IS_ANONYMIZED)
        self.assertNotSoonAnonymized(contact1)

        contact2 = contacts[1]
        self.assertHasNoProperty(contact2, PROP_IS_ANONYMIZED)
        self.assertSoonAnonymized(contact2)

        contact3 = contacts[2]
        self.assertHasNoProperty(contact3, PROP_IS_ANONYMIZED)
        self.assertNotSoonAnonymized(contact3)

        self.assertHasNoProperty(orga, PROP_IS_ANONYMIZED)
        self.assertNotSoonAnonymized(orga)

        # Second pass ---
        anonymiser_type.execute(self.get_job())
        self.assertSoonAnonymized(contact2)  # Marked once

    @skipIfCustomContact
    def test_job_sensible_info_removed(self):
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        birthday = date(year=1980, month=2, day=12)
        contact1 = create_contact(
            first_name='Bilbo', last_name='Baggins',
            email='bilbo@shire.mdl', phone='123456', mobile='741258',
            birthday=birthday,
        )
        contact2 = create_contact(first_name='Gandalf', last_name='The grey')

        self._oldify(contact1, years=3, months=1)

        anonymiser_type.execute(self.get_job())

        contact1 = self.refresh(contact1)
        self.assertHasProperty(contact1, PROP_IS_ANONYMIZED)
        self.assertEqual('🙈🙉🙊',  contact1.first_name)
        self.assertEqual('🙈🙉🙊',  contact1.last_name)
        self.assertEqual('',       contact1.email)
        self.assertEqual('',       contact1.mobile)
        self.assertEqual('',       contact1.phone)
        self.assertEqual(birthday, contact1.birthday)

        self.assertFalse(HistoryLine.objects.filter(entity=contact1.id))
        self.assertEqual(1, HistoryLine.objects.filter(entity=contact2.id).count())

    @skipIfCustomContact
    def test_job_related_entities_cleaned(self):
        pass
        # user = self.login()
        #
        # create_contact = partial(Contact.objects.create, user=user)
        # birthday = date(year=1980, month=2, day=12)
        # contact1 = create_contact(
        #     first_name='Bilbo', last_name='Baggins',
        #     email='bilbo@shire.mdl', phone='123456', mobile = '741258',
        #     birthday=birthday,
        # )
        # # # We generate a HistoryLine with type EDITION
        # # contact1 = self.refresh(contact1)
        # # contact1.mobile = '741258'
        # # contact1.save()
        #
        # contact2 = create_contact(first_name='Gandalf', last_name='The grey')
        #
        # self._oldify(contact1, years=3, months=1)
        #
        # # # TODO: move?
        # # def get_hlines(entity):
        # #     return HistoryLine.objects.filter(entity=entity.id).order_by('-id')
        # #
        # # old_hlines = [*get_hlines(contact1)]
        # # self.assertEqual(2, len(old_hlines))
        # # self.assertEqual('', old_hlines[0].value)
        #
        # anonymiser_type.execute(self.get_job())
        #
        # contact1 = self.refresh(contact1)
        # self.assertHasProperty(contact1, PROP_IS_ANONYMIZED)
        # self.assertEqual('🙈🙉🙊',  contact1.first_name)
        # self.assertEqual('🙈🙉🙊',  contact1.last_name)
        # self.assertEqual('',       contact1.email)
        # self.assertEqual('',       contact1.mobile)
        # self.assertEqual('',       contact1.phone)
        # self.assertEqual(birthday, contact1.birthday)
        #
        # # new_hlines = [
        # #     *get_hlines(contact1).exclude(id__in=[line.id for line in old_hlines])
        # # ]
        # # self.assertEqual(1, len(new_hlines))
        # # self.assertEqual(TYPE_PROP_ADD, new_hlines[0].type)
        # self.assertFalse(HistoryLine.objects.filter(entity=contact1.id))
        # self.assertEqual(1, HistoryLine.objects.filter(entity=contact2.id).count())

    # TODO: use Relation too
    #       + removed info in related entities
    #       + exclude relation hlines from deletion
    # TODO: billing which cannot be anonymized? (optional dependency)
