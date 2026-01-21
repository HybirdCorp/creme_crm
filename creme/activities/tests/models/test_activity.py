from datetime import timedelta
from functools import partial

from django.test.utils import override_settings
from django.urls import reverse

from creme.activities import constants, setting_keys
from creme.activities.models import Status
from creme.creme_core.creme_jobs import trash_cleaner_type
from creme.creme_core.models import Job, Relation, RelationType, SettingValue
from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from creme.persons.tests.base import skipIfCustomContact

from ..base import (
    Activity,
    Contact,
    Organisation,
    _ActivitiesTestCase,
    skipIfCustomActivity,
)


@skipIfCustomActivity
class ActivityManagerTestCase(_ActivitiesTestCase):
    def test_future_linked(self):
        user = self.login_as_root_and_get()
        create_dt = self.create_datetime
        today = create_dt(year=2019, month=8, day=26, hour=8)

        rtype1 = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is loving',
        ).symmetric(id='test-object_foobar', predicate='is loved by').get_or_create()[0]

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING)
        create_activity = partial(
            Activity.objects.create, user=user,
            type_id=sub_type.type_id, sub_type=sub_type,
            start=today + timedelta(hours=3),
            end=today + timedelta(hours=4),
        )
        activity1 = create_activity(title='Meeting#1')
        create_activity(title='Meeting#2')  # No relation
        activity3 = create_activity(title='Meeting#3')  # Ignored type of relation
        activity4 = create_activity(title='Meeting#4', is_deleted=True)
        activity5 = create_activity(
            title='Meeting#5',
            start=today - timedelta(hours=15),
            end=today   - timedelta(hours=14),
        )  # In the past
        activity6 = create_activity(
            title='Meeting#6',
            start=today + timedelta(hours=1),
            end=today + timedelta(hours=2),
        )

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Ranma', last_name='Saotome')
        c2 = create_contact(first_name='Genma', last_name='Saotome')

        create_orga = partial(Organisation.objects.create, user=user)
        o1 = create_orga(name='Saotome dojo')
        o2 = create_orga(name='Tendou dojo')

        create_rel = partial(
            Relation.objects.create,
            user=user, object_entity=activity1, type_id=constants.REL_SUB_PART_2_ACTIVITY,
        )

        create_rel(subject_entity=c1)
        # Second relation on the same activity => return once
        create_rel(subject_entity=c1, type_id=constants.REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=o1, type_id=constants.REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=o2, type_id=constants.REL_SUB_LINKED_2_ACTIVITY)
        create_rel(subject_entity=c2, type_id=rtype1.id, object_entity=activity3)
        create_rel(subject_entity=c1, object_entity=activity4)
        create_rel(subject_entity=c1, object_entity=activity5)
        create_rel(subject_entity=c1, object_entity=activity6)

        self.assertListEqual(
            [activity6, activity1],
            [*Activity.objects.future_linked(entity=c1, today=today)]
        )
        self.assertListEqual(
            [activity1],
            [*Activity.objects.future_linked(entity=o1, today=today)]
        )
        self.assertListEqual(
            [activity1],
            [*Activity.objects.future_linked(entity=o2, today=today)]
        )
        self.assertFalse(Activity.objects.future_linked(entity=c2, today=today))

    def test_past_linked(self):
        user = self.login_as_root_and_get()
        create_dt = self.create_datetime
        today = create_dt(year=2019, month=8, day=26, hour=8)

        rtype1 = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is loving',
        ).symmetric(id='test-object_foobar', predicate='is loved by').get_or_create()[0]

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING)
        create_activity = partial(
            Activity.objects.create, user=user,
            type_id=sub_type.type_id, sub_type=sub_type,
            start=today - timedelta(hours=24),
            end=today - timedelta(hours=23),
        )
        activity1 = create_activity(title='Meeting#1')
        create_activity(title='Meeting#2')  # No relation
        activity3 = create_activity(title='Meeting#3')  # Ignored type of relation
        activity4 = create_activity(title='Meeting#4', is_deleted=True)
        activity5 = create_activity(
            title='Meeting#5',
            start=today + timedelta(hours=4),
            end=today + timedelta(hours=5),
        )  # In the future
        activity6 = create_activity(
            title='Meeting#6',
            start=today - timedelta(hours=15),
            end=today   - timedelta(hours=14),
        )

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Ranma', last_name='Saotome')
        c2 = create_contact(first_name='Genma', last_name='Saotome')

        create_orga = partial(Organisation.objects.create, user=user)
        o1 = create_orga(name='Saotome dojo')
        o2 = create_orga(name='Tendou dojo')

        create_rel = partial(
            Relation.objects.create,
            user=user, object_entity=activity1, type_id=constants.REL_SUB_PART_2_ACTIVITY,
        )

        create_rel(subject_entity=c1)
        # Second relation on the same activity => return once
        create_rel(subject_entity=c1, type_id=constants.REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=o1, type_id=constants.REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=o2, type_id=constants.REL_SUB_LINKED_2_ACTIVITY)
        create_rel(subject_entity=c2, type_id=rtype1.id, object_entity=activity3)
        create_rel(subject_entity=c1, object_entity=activity4)
        create_rel(subject_entity=c1, object_entity=activity5)
        create_rel(subject_entity=c1, object_entity=activity6)

        self.assertListEqual(
            [activity6, activity1],
            [*Activity.objects.past_linked(entity=c1, today=today)],
        )
        self.assertListEqual(
            [activity1],
            [*Activity.objects.past_linked(entity=o1, today=today)],
        )
        self.assertListEqual(
            [activity1],
            [*Activity.objects.past_linked(entity=o2, today=today)],
        )
        self.assertFalse(Activity.objects.past_linked(entity=c2, today=today))

    def test_future_linked_to_organisation(self):
        user = self.login_as_root_and_get()

        sv = self.get_object_or_fail(SettingValue, key_id=setting_keys.auto_subjects_key.id)
        sv.value = False  # We disable the auto subjects feature
        sv.save()

        create_dt = self.create_datetime
        today = create_dt(year=2019, month=8, day=26, hour=8)

        rtype1 = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is loving',
        ).symmetric(id='test-object_foobar', predicate='is loved by').get_or_create()[0]

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        create_activity = partial(
            Activity.objects.create,
            user=user,
            type_id=sub_type.type_id, sub_type=sub_type,
            start=today + timedelta(hours=3),
            end=today   + timedelta(hours=4),
        )
        activity1 = create_activity(title='Meeting#1')
        activity2 = create_activity(title='Meeting#2')
        activity3 = create_activity(title='Meeting#3')
        activity4 = create_activity(title='Meeting#4', is_deleted=True)
        activity5 = create_activity(
            title='Meeting#5',
            start=today - timedelta(hours=15),
            end=today   - timedelta(hours=14),
        )  # In the past => ignored
        activity6 = create_activity(
            title='Meeting#6',
            start=today + timedelta(hours=1),
            end=today   + timedelta(hours=2),
        )  # Before <activity1> when ordering by 'start'
        activity7 = create_activity(title='Meeting#2')

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Saotome dojo')
        orga2 = create_orga(name='Tendou dojo')
        orga3 = create_orga(name='Hibiki dojo')
        orga4 = create_orga(name='Happosai dojo')

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Ranma', last_name='Saotome')
        c2 = create_contact(first_name='Ryoga', last_name='Hibiki')
        c3 = create_contact(first_name='Akane', last_name='Tendou')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=c1, type_id=REL_SUB_EMPLOYED_BY, object_entity=orga2)
        create_rel(subject_entity=c2, type_id=REL_SUB_MANAGES,     object_entity=orga3)
        create_rel(subject_entity=c3, type_id=REL_SUB_EMPLOYED_BY, object_entity=orga4)

        SUBJECT = constants.REL_SUB_ACTIVITY_SUBJECT

        # About <orga1> ---
        create_rel(
            subject_entity=orga1, type_id=SUBJECT,  object_entity=activity1,
        )
        # Ignored type of relation
        create_rel(subject_entity=orga1, type_id=rtype1.id, object_entity=activity3)
        create_rel(subject_entity=orga1, type_id=SUBJECT, object_entity=activity4)
        create_rel(subject_entity=orga1, type_id=SUBJECT, object_entity=activity5)
        create_rel(subject_entity=orga1, type_id=SUBJECT, object_entity=activity6)

        # About <orga2> ---
        create_rel(
            subject_entity=c1,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity2,
        )

        # About <orga3> ---
        create_rel(
            subject_entity=c2,
            type_id=constants.REL_SUB_LINKED_2_ACTIVITY,
            object_entity=activity3,
        )

        # About <orga4> (2 relationships on the same activity => return only one)
        create_rel(subject_entity=orga4, type_id=SUBJECT, object_entity=activity7)
        create_rel(
            subject_entity=c3,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity7,
        )

        self.assertListEqual(
            [activity6, activity1],
            [*Activity.objects.future_linked_to_organisation(orga1, today=today)],
        )

        self.assertFalse(Relation.objects.filter(subject_entity=activity2, object_entity=orga2))
        self.assertListEqual(
            [activity2],
            [*Activity.objects.future_linked_to_organisation(orga=orga2, today=today)],
        )

        self.assertListEqual(
            [activity3],
            [*Activity.objects.future_linked_to_organisation(orga=orga3, today=today)],
        )

        self.assertListEqual(
            [activity7],
            [*Activity.objects.future_linked_to_organisation(orga=orga4, today=today)],
        )

    def test_past_linked_to_organisation(self):
        user = self.login_as_root_and_get()

        sv = self.get_object_or_fail(SettingValue, key_id=setting_keys.auto_subjects_key.id)
        sv.value = False  # We disable the auto subjects feature
        sv.save()

        create_dt = self.create_datetime
        today = create_dt(year=2019, month=8, day=26, hour=8)

        rtype1 = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is loving',
        ).symmetric(id='test-object_foobar', predicate='is loved by').get_or_create()[0]

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_MEETING)
        create_activity = partial(
            Activity.objects.create,
            user=user,
            type_id=sub_type.type_id, sub_type=sub_type,
            start=today - timedelta(hours=16),
            end=today   - timedelta(hours=15),
        )
        activity1 = create_activity(title='Meeting#1')
        activity2 = create_activity(title='Meeting#2')
        activity3 = create_activity(title='Meeting#3')
        activity4 = create_activity(title='Meeting#4', is_deleted=True)
        activity5 = create_activity(
            title='Meeting#5',
            start=today + timedelta(hours=1),
            end=today   + timedelta(hours=2),
        )  # In the Future => ignored
        activity6 = create_activity(
            title='Meeting#6',
            start=today - timedelta(hours=15),
            end=today   - timedelta(hours=14),
        )  # Before <activity1> when ordering by '-start'
        activity7 = create_activity(title='Meeting#2')

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Saotome dojo')
        orga2 = create_orga(name='Tendou dojo')
        orga3 = create_orga(name='Hibiki dojo')
        orga4 = create_orga(name='Happosai dojo')

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Ranma', last_name='Saotome')
        c2 = create_contact(first_name='Ryoga', last_name='Hibiki')
        c3 = create_contact(first_name='Akane', last_name='Tendou')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=c1, type_id=REL_SUB_EMPLOYED_BY, object_entity=orga2)
        create_rel(subject_entity=c2, type_id=REL_SUB_MANAGES,     object_entity=orga3)
        create_rel(subject_entity=c3, type_id=REL_SUB_EMPLOYED_BY, object_entity=orga4)

        SUBJECT = constants.REL_SUB_ACTIVITY_SUBJECT

        # About <orga1> ---
        create_rel(subject_entity=orga1, type_id=SUBJECT,  object_entity=activity1)
        create_rel(subject_entity=orga1, type_id=rtype1.id, object_entity=activity3)
        # Ignored type of relation
        create_rel(subject_entity=orga1, type_id=SUBJECT,  object_entity=activity4)
        create_rel(subject_entity=orga1, type_id=SUBJECT,  object_entity=activity5)
        create_rel(subject_entity=orga1, type_id=SUBJECT,  object_entity=activity6)

        # About <orga2> ---
        create_rel(
            subject_entity=c1,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity2,
        )

        # About <orga3> ---
        create_rel(
            subject_entity=c2,
            type_id=constants.REL_SUB_LINKED_2_ACTIVITY,
            object_entity=activity3,
        )

        # About <orga4> (2 relationships on the same activity => return only one)
        create_rel(
            subject_entity=orga4,
            type_id=SUBJECT,
            object_entity=activity7,
        )
        create_rel(
            subject_entity=c3,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity7,
        )

        self.assertListEqual(
            [activity6, activity1],
            [*Activity.objects.past_linked_to_organisation(orga1, today=today)]
        )

        self.assertFalse(Relation.objects.filter(subject_entity=activity2, object_entity=orga2))
        self.assertListEqual(
            [activity2],
            [*Activity.objects.past_linked_to_organisation(orga=orga2, today=today)],
        )

        self.assertListEqual(
            [activity3],
            [*Activity.objects.past_linked_to_organisation(orga=orga3, today=today)],
        )

        self.assertListEqual(
            [activity7],
            [*Activity.objects.past_linked_to_organisation(orga=orga4, today=today)],
        )


@skipIfCustomActivity
class ActivityTestCase(_ActivitiesTestCase):
    @skipIfCustomContact
    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_participant(self):
        "Cannot delete a participant."
        user = self.login_as_root_and_get()

        activity = self._create_meeting(user=user)
        participant = Contact.objects.create(
            user=user, first_name='Musashi', last_name='Miyamoto', is_deleted=True,
        )
        rel = Relation.objects.create(
            user=user, subject_entity=participant,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity,
        )

        self.assertPOST409(participant.get_delete_absolute_url(), follow=True)
        self.assertStillExists(participant)
        self.assertStillExists(activity)
        self.assertStillExists(rel)

    @skipIfCustomContact
    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete__rel_part_2_activity(self):
        "Relations constants.REL_SUB_PART_2_ACTIVITY are removed when the Activity is deleted."
        user = self.login_as_root_and_get()

        activity = self._create_meeting(user=user)
        activity.trash()

        musashi = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')
        rel = Relation.objects.create(
            user=user, subject_entity=musashi,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity,
        )

        self.assertPOST200(activity.get_delete_absolute_url(), follow=True)
        self.assertDoesNotExist(activity)
        self.assertDoesNotExist(rel)
        self.assertStillExists(musashi)

    @skipIfCustomContact
    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete__rel_activity_subject(self):
        "Relations constants.REL_SUB_ACTIVITY_SUBJECT are removed when the Activity is deleted."
        user = self.login_as_root_and_get()

        activity = self._create_meeting(user=user)
        activity.trash()

        musashi = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')
        rel = Relation.objects.create(
            user=user, subject_entity=musashi,
            type_id=constants.REL_SUB_ACTIVITY_SUBJECT,
            object_entity=activity,
        )

        self.assertPOST200(activity.get_delete_absolute_url(), follow=True)
        self.assertDoesNotExist(activity)
        self.assertDoesNotExist(rel)
        self.assertStillExists(musashi)

    @skipIfCustomContact
    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_empty_trash__participant_not_deleted(self):
        """Relations constants.REL_SUB_PART_2_ACTIVITY are removed when the
        Activity is deleted (empty_trash).
        """
        user = self.login_as_root_and_get()

        activity = self._create_meeting(user=user)
        activity.trash()

        musashi = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')
        rel = Relation.objects.create(
            user=user, subject_entity=musashi,
            type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity,
        )

        self.assertPOST200(reverse('creme_core__empty_trash'))

        job = self.get_object_or_fail(Job, type_id=trash_cleaner_type.id)
        trash_cleaner_type.execute(job)
        self.assertDoesNotExist(activity)
        self.assertDoesNotExist(rel)
        self.assertStillExists(musashi)

    @skipIfCustomContact
    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_empty_trash__participant_deleted(self):
        """If an Activity & its participants are in the trash, the relationships
        cannot avoid the trash emptying.
        """
        user = self.login_as_root_and_get()

        create_contact = partial(Contact.objects.create, user=user)
        musashi = create_contact(first_name='Musashi', last_name='Miyamoto')

        activity = self._create_meeting(user=user)

        kojiro = create_contact(first_name='Kojiro',  last_name='Sasaki')
        # we want that at least one contact tries to delete() before the activity
        self.assertLess(musashi.id, activity.id)
        self.assertLess(activity.id, kojiro.id)

        create_rel = partial(
            Relation.objects.create,
            user=user, type_id=constants.REL_SUB_PART_2_ACTIVITY, object_entity=activity,
        )
        create_rel(subject_entity=musashi)
        create_rel(subject_entity=kojiro)

        activity.trash()
        musashi.trash()
        kojiro.trash()

        self.assertPOST200(reverse('creme_core__empty_trash'))

        job = self.get_object_or_fail(Job, type_id=trash_cleaner_type.id)
        trash_cleaner_type.execute(job)
        self.assertDoesNotExist(activity)
        self.assertDoesNotExist(musashi)
        self.assertDoesNotExist(kojiro)

    @skipIfCustomContact
    def test_clone(self):
        user = self.login_as_root_and_get()

        rtype_participant = RelationType.objects.get(pk=constants.REL_SUB_PART_2_ACTIVITY)

        sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
        create_dt = self.create_datetime
        activity1 = Activity.objects.create(
            user=user,
            type_id=sub_type.type_id, sub_type=sub_type,
            title='Meeting', description='Desc',
            start=create_dt(year=2015, month=3, day=20, hour=9),
            end=create_dt(year=2015, month=3, day=20, hour=11),
            is_all_day=False, busy=True,
            place='Here', minutes='123',
            status=Status.objects.all()[0],
        )

        create_contact = partial(Contact.objects.create, user=user, last_name='Saotome')
        create_rel = partial(
            Relation.objects.create, user=user, type=rtype_participant, object_entity=activity1,
        )
        create_rel(subject_entity=create_contact(first_name='Ranma'))
        create_rel(subject_entity=create_contact(first_name='Genma'))

        activity2 = self.clone(activity1)

        for attr in (
            'user', 'title', 'start', 'end', 'description', 'minutes',
            'type', 'sub_type', 'is_all_day', 'status', 'place',
        ):
            self.assertEqual(getattr(activity1, attr), getattr(activity2, attr))

        self.assertNotEqual(activity1.busy, activity2.busy)
        self.assertSameRelationsNProperties(activity1, activity2, exclude_internal=False)

    # def test_clone__method01(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     activity1 = self._create_meeting(user=user)
    #     activity2 = activity1.clone()
    #     self.assertNotEqual(activity1.pk, activity2.pk)
    #
    #     for attr in (
    #         'user', 'title', 'start', 'end', 'description', 'minutes',
    #         'type', 'sub_type', 'is_all_day', 'status', 'busy',
    #     ):
    #         self.assertEqual(getattr(activity1, attr), getattr(activity2, attr))
    #
    # @skipIfCustomContact
    # def test_clone__method02(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     rtype_participant = RelationType.objects.get(pk=constants.REL_SUB_PART_2_ACTIVITY)
    #
    #     sub_type = self._get_sub_type(constants.UUID_SUBTYPE_MEETING_OTHER)
    #     create_dt = self.create_datetime
    #     activity1 = Activity.objects.create(
    #         user=user,
    #         type_id=sub_type.type_id, sub_type=sub_type,
    #         title='Meeting', description='Desc',
    #         start=create_dt(year=2015, month=3, day=20, hour=9),
    #         end=create_dt(year=2015, month=3, day=20, hour=11),
    #         is_all_day=False, busy=True,
    #         place='Here', minutes='123',
    #         status=Status.objects.all()[0],
    #     )
    #
    #     create_contact = partial(Contact.objects.create, user=user, last_name='Saotome')
    #     create_rel = partial(
    #         Relation.objects.create, user=user, type=rtype_participant, object_entity=activity1,
    #     )
    #     create_rel(subject_entity=create_contact(first_name='Ranma'))
    #     create_rel(subject_entity=create_contact(first_name='Genma'))
    #
    #     activity2 = activity1.clone().clone().clone().clone().clone().clone().clone()
    #     self.assertNotEqual(activity1.pk, activity2.pk)
    #
    #     for attr in (
    #         'user', 'title', 'start', 'end', 'description', 'minutes',
    #         'type', 'sub_type', 'is_all_day', 'status', 'place',
    #     ):
    #         self.assertEqual(getattr(activity1, attr), getattr(activity2, attr))
    #
    #     self.assertNotEqual(activity1.busy, activity2.busy)
    #     self.assertSameRelationsNProperties(activity1, activity2, exclude_internal=False)
