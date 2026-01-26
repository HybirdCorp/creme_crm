from functools import partial

from creme.activities.constants import (
    REL_SUB_PART_2_ACTIVITY,
    UUID_SUBTYPE_MEETING_QUALIFICATION,
)
from creme.activities.models import ActivitySubType
from creme.activities.tests.base import skipIfCustomActivity
from creme.commercial.models import CommercialApproach
from creme.creme_core.models import FakeOrganisation, Relation
from creme.creme_core.models.history import TYPE_DELETION, HistoryLine
from creme.creme_core.tests.base import CremeTestCase

from ..base import Activity, Contact, Organisation


class CommercialApproachTestCase(CremeTestCase):
    def test_merge(self):
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='NERV')
        orga2 = create_orga(name='Nerv')

        create_commapp = partial(CommercialApproach.objects.create, description='...')
        create_commapp(title='Commapp01', creme_entity=orga1)
        create_commapp(title='Commapp02', creme_entity=orga2)
        self.assertEqual(2, CommercialApproach.objects.count())

        old_count = HistoryLine.objects.count()

        response = self.client.post(
            self.build_merge_url(orga1, orga2),
            follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'name_1':      orga1.name,
                'name_2':      orga2.name,
                'name_merged': orga1.name,

                'subject_to_vat_merged': orga1.subject_to_vat,
            },
        )
        self.assertNoFormError(response)

        self.assertDoesNotExist(orga2)

        with self.assertNoException():
            orga1 = self.refresh(orga1)

        commapps = CommercialApproach.objects.all()
        self.assertEqual(2, len(commapps))

        for commapp in commapps:
            self.assertEqual(orga1, commapp.creme_entity)

        hlines = [*HistoryLine.objects.order_by('id')]
        self.assertEqual(old_count + 1, len(hlines))  # No edition for 'entity_id'

        hline = hlines[-1]
        self.assertEqual(TYPE_DELETION, hline.type)
        self.assertEqual(str(orga2), hline.entity_repr)

    def test_delete_entity(self):
        user = self.login_as_root_and_get()

        orga = FakeOrganisation.objects.create(user=user, name='NERV')
        comapp = CommercialApproach.objects.create(
            title='Commapp01',
            description='A commercial approach',
            creme_entity=orga,
        )

        orga.delete()
        self.assertDoesNotExist(comapp)

    @skipIfCustomActivity
    def test_sync_with_activity(self):
        user = self.login_as_root_and_get()
        title = 'meeting #01'
        description = 'Stuffs about the fighting'
        create_dt = self.create_datetime
        sub_type = self.get_object_or_fail(
            ActivitySubType, uuid=UUID_SUBTYPE_MEETING_QUALIFICATION,
        )
        meeting = Activity.objects.create(
            user=user, title=title, description=description,
            type_id=sub_type.type_id,
            sub_type=sub_type,
            start=create_dt(year=2011, month=5, day=18, hour=14, minute=0),
            end=create_dt(year=2011,   month=6, day=1,  hour=15, minute=0),
        )
        contact = user.linked_contact

        Relation.objects.create(
            subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=meeting, user=user,
        )

        comapp = CommercialApproach.objects.create(
            title=title,
            description=description,
            # TODO: related_activity=instance after activities refactoring ?
            related_activity_id=meeting.id,
            creme_entity=contact,
        )

        title = title.upper()
        meeting.title = title
        meeting.save()
        self.assertEqual(title, self.refresh(comapp).title)

    def test_get_approaches__not_related(self):
        "Related to entity."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        nerv  = create_orga(name='NERV')
        seele = create_orga(name='Seele')

        create_commapp = CommercialApproach.objects.create
        commapp1 = create_commapp(title='Commapp #1', creme_entity=nerv)
        create_commapp(title='Commapp #2', creme_entity=seele)

        self.assertListEqual(
            [commapp1], [*CommercialApproach.get_approaches(nerv.id)]
        )

    def test_get_approaches__related(self):
        "Not related to entity."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        nerv  = create_orga(name='NERV')
        seele = create_orga(name='Seele', is_deleted=True)

        misato = Contact.objects.create(user=user, last_name='Katsuragi', first_name='Misato')

        create_commapp = CommercialApproach.objects.create
        commapp1 = create_commapp(title='Commapp #1', creme_entity=nerv)
        create_commapp(title='Commapp #2', creme_entity=seele)
        commapp3 = create_commapp(title='Commapp #2', creme_entity=misato)

        self.assertListEqual(
            [commapp1, commapp3],
            [*CommercialApproach.get_approaches().order_by('id')],
        )
