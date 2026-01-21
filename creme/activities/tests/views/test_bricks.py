from functools import partial

from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.activities.constants import (
    REL_SUB_ACTIVITY_SUBJECT,
    REL_SUB_LINKED_2_ACTIVITY,
    REL_SUB_PART_2_ACTIVITY,
    UUID_SUBTYPE_PHONECALL_OUTGOING,
)
from creme.activities.models import Calendar
from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.models import Relation
from creme.persons.constants import REL_SUB_EMPLOYED_BY
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..base import (
    Activity,
    Contact,
    Organisation,
    _ActivitiesTestCase,
    skipIfCustomActivity,
)


@skipIfCustomContact
@skipIfCustomActivity
class ParticipantsBrickViewsTestCase(_ActivitiesTestCase):
    RM_PARTICIPANT_URL = reverse('activities__remove_participant')

    @staticmethod
    def _build_add_participants_url(activity):
        return reverse('activities__add_participants', args=(activity.id,))

    def test_add_participants(self):
        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c2 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        url = self._build_add_participants_url(activity)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('Adding participants to activity «{entity}»').format(entity=activity),
            context.get('title')
        )
        self.assertEqual(_('Add the participants'), context.get('submit_label'))

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={'participants': self.formfield_value_multi_creator_entity(c1, c2)},
        ))
        self.assertCountEqual(
            [c1, c2],
            [
                r.subject_entity.get_real_entity()
                for r in Relation.objects.filter(
                    object_entity=activity.id, type=REL_SUB_PART_2_ACTIVITY,
                )
            ],
        )

    def test_add_participants__link_perm__activity(self):
        "Credentials error with the activity."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own='!LINK')

        activity = self._create_meeting(user=user)
        self.assertTrue(user.has_perm_to_change(activity))
        self.assertFalse(user.has_perm_to_link(activity))
        self.assertGET403(self._build_add_participants_url(activity))

    def test_add_participants__link_perm__subjects(self):
        "Credentials error with selected subjects."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own=['LINK'], all='!LINK')

        activity = self._create_meeting(user=user)
        self.assertTrue(user.has_perm_to_link(activity))

        contact = Contact.objects.create(
            user=self.get_root_user(), first_name='Musashi', last_name='Miyamoto',
        )
        self.assertTrue(user.has_perm_to_change(contact))
        self.assertFalse(user.has_perm_to_link(contact))

        uri = self._build_add_participants_url(activity)
        self.assertGET200(uri)

        response = self.assertPOST200(
            uri,
            data={'participants': self.formfield_value_multi_creator_entity(contact)},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='participants',
            errors=_('Some entities are not linkable: {}').format(contact),
        )
        self.assertFalse(Relation.objects.filter(
            object_entity=activity.id,
            type=REL_SUB_PART_2_ACTIVITY,
        ))

    def test_add_participants__useless_my_participation(self):
        "'My participation' field is removed when it is useless."
        user = self.login_as_root_and_get()
        activity = self._create_activity_by_view(user=user)

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c2 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        uri = self._build_add_participants_url(activity)
        response = self.assertGET200(uri)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('my_participation', fields)
        self.assertNotIn('my_calendar',      fields)

        self.assertNoFormError(self.client.post(
            uri,
            data={'participants': self.formfield_value_multi_creator_entity(c1, c2)},
        ))
        self.assertCountEqual(
            [c1.id, c2.id, user.linked_contact.id],
            [
                *Relation.objects
                         .filter(object_entity=activity.id, type=REL_SUB_PART_2_ACTIVITY)
                         .values_list('subject_entity_id', flat=True),
            ],
        )

    def test_add_participants__collision_floating(self):
        "Fix a bug when checking for collision for a floating activities."
        user = self.login_as_root_and_get()
        activity = self._create_activity_by_view(user=user)
        self.assertIsNone(activity.start)
        self.assertIsNone(activity.end)
        self.assertEqual(Activity.FloatingType.FLOATING, activity.floating_type)

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c2 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        uri = self._build_add_participants_url(activity)
        self.assertGET200(uri)
        self.assertNoFormError(self.client.post(
            uri,
            data={'participants': self.formfield_value_multi_creator_entity(c1, c2)},
        ))
        self.assertCountEqual(
            [c1.id, c2.id, user.linked_contact.id],
            [
                *Relation.objects
                         .filter(object_entity=activity.id, type=REL_SUB_PART_2_ACTIVITY)
                         .values_list('subject_entity_id', flat=True),
            ],
        )

    def test_add_participants__teams(self):
        "When Teams are selected, their teammates are participants."
        user1 = self.login_as_root_and_get()
        activity = self._create_meeting(user=user1)

        user2 = self.create_user(0)
        user3  = self.create_user(1)
        team = self.create_team('Samurais', user2, user3, user1)

        response = self.client.post(
            self._build_add_participants_url(activity),
            data={
                'my_participation_0':  True,
                'my_participation_1':  Calendar.objects.get_default_calendar(user1).pk,
                'participating_users': [team.id, user3.id],
            },
        )
        self.assertNoFormError(response)
        self.assertCountEqual(
            [user2.linked_contact, user3.linked_contact, user1.linked_contact],
            [
                r.subject_entity.get_real_entity()
                for r in Relation.objects.filter(
                    object_entity=activity.id, type=REL_SUB_PART_2_ACTIVITY,
                )
            ],
        )
        self.assertCountEqual(
            [
                Calendar.objects.get_default_calendar(user)
                for user in (user1, user2, user3, team)
            ],
            activity.calendars.all(),
        )

    @skipIfCustomOrganisation
    def test_add_participants__auto_subject(self):
        user = self.login_as_root_and_get()
        activity = self._create_meeting(user=user)

        akane = Contact.objects.create(user=user, first_name='Akane', last_name='Tendo')
        dojo = Organisation.objects.create(user=user, name='Tendo Dojo')

        Relation.objects.create(
            user=user, subject_entity=akane,
            type_id=REL_SUB_EMPLOYED_BY, object_entity=dojo,
        )

        self.assertNoFormError(self.client.post(
            self._build_add_participants_url(activity),
            data={'participants': self.formfield_value_multi_creator_entity(akane)},
        ))
        self.assertHaveRelation(subject=dojo, type=REL_SUB_ACTIVITY_SUBJECT, object=activity)

    def test_add_participants__duplicated_me(self):
        "I already participate + the selected team includes me."
        user = self.login_as_root_and_get()
        other_user = self.create_user()
        team = self.create_team('A-team', user, other_user)

        activity = self._create_meeting(user=user)
        Relation.objects.create(
            user=user,
            subject_entity=user.linked_contact,
            type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=activity,
        )
        get_default_calendar = Calendar.objects.get_default_calendar
        cal1 = get_default_calendar(user)
        activity.calendars.add(cal1)

        self.assertNoFormError(self.client.post(
            self._build_add_participants_url(activity),
            data={'participating_users': [team.id]},
        ))
        self.assertHaveRelation(user.linked_contact,       REL_SUB_PART_2_ACTIVITY, activity)
        self.assertHaveRelation(other_user.linked_contact, REL_SUB_PART_2_ACTIVITY, activity)
        self.assertCountEqual(
            [cal1, get_default_calendar(other_user), get_default_calendar(team)],
            activity.calendars.all(),
        )

    def test_remove_participants(self):
        user = self.login_as_activities_user()
        self.add_credentials(user.role, all='*')

        logged = user.linked_contact
        other = self.get_root_user().linked_contact
        contact3 = Contact.objects.create(user=user, first_name='Roy', last_name='Mustang')

        dt_now = now()
        sub_type = self._get_sub_type(UUID_SUBTYPE_PHONECALL_OUTGOING)
        phone_call = Activity.objects.create(
            title='Phone call to be deleted',
            start=dt_now, end=dt_now,
            user=user,
            type_id=sub_type.type_id, sub_type=sub_type,
        )

        self.assertPOST200(
            self._build_add_participants_url(phone_call), follow=True,
            data={
                'my_participation_0':  True,
                'my_participation_1':  Calendar.objects.get_default_calendar(logged.is_user).pk,
                'participating_users': [other.is_user_id],
                'participants':        self.formfield_value_multi_creator_entity(contact3),
            },
        )

        # Logged user, set in his calendar
        sym_rel = self.get_object_or_fail(
            Relation,
            subject_entity=logged, type=REL_SUB_PART_2_ACTIVITY, object_entity=phone_call,
        )
        # Other contact user, set in his calendar too
        self.assertHaveRelation(subject=other, type=REL_SUB_PART_2_ACTIVITY, object=phone_call)
        # Regular contact, has no calendar
        self.assertHaveRelation(subject=contact3, type=REL_SUB_PART_2_ACTIVITY, object=phone_call)
        self.assertEqual(2, phone_call.calendars.count())

        del_url = self.RM_PARTICIPANT_URL
        self.assertGET405(del_url)
        self.assertPOST404(del_url, data={'id': sym_rel.pk})
        self.assertStillExists(sym_rel)

        qs = Relation.objects.filter(
            type=REL_SUB_PART_2_ACTIVITY, object_entity=phone_call,
        )

        for participant_rel in qs.all():
            self.assertGET405(del_url)

            response = self.client.post(
                del_url, data={'id': participant_rel.symmetric_relation_id},
            )
            self.assertRedirects(response, phone_call.get_absolute_url())

        self.assertFalse(qs.all())
        self.assertFalse(phone_call.calendars.all())

    def test_remove_participants__unlink_perm__contact(self):
        "Cannot unlink the contact."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, all='!UNLINK', own=['VIEW', 'UNLINK'])

        contact = self.get_root_user().linked_contact
        self.assertFalse(user.has_perm_to_unlink(contact))

        sub_type = self._get_sub_type(UUID_SUBTYPE_PHONECALL_OUTGOING)
        phone_call = Activity.objects.create(
            title='A random activity',
            user=user,
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        self.assertTrue(user.has_perm_to_unlink(phone_call))

        rel = Relation.objects.create(
            user=user,
            subject_entity=contact,
            type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=phone_call,
        )
        self.assertPOST403(self.RM_PARTICIPANT_URL, data={'id': rel.symmetric_relation_id})

    def test_remove_participants__unlink_perm__activity(self):
        "Cannot unlink the activity."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, all='!UNLINK', own=['VIEW', 'UNLINK'])

        contact = user.linked_contact
        self.assertTrue(user.has_perm_to_unlink(contact))

        sub_type = self._get_sub_type(UUID_SUBTYPE_PHONECALL_OUTGOING)
        phone_call = Activity.objects.create(
            title='A random activity',
            user=self.get_root_user(),
            type_id=sub_type.type_id, sub_type=sub_type,
        )
        self.assertFalse(user.has_perm_to_unlink(phone_call))

        rel = Relation.objects.create(
            user=user,
            subject_entity=contact,
            type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=phone_call,
        )
        self.assertPOST403(self.RM_PARTICIPANT_URL, data={'id': rel.symmetric_relation_id})


@skipIfCustomActivity
class SubjectsBrickViewsTestCase(_ActivitiesTestCase):
    RM_SUBJECT_URL = reverse('activities__remove_subject')

    @staticmethod
    def _build_add_subjects_url(activity):
        return reverse('activities__add_subjects', args=(activity.id,))

    @skipIfCustomOrganisation
    def test_add_subjects(self):
        user = self.login_as_root_and_get()

        activity = self._create_meeting(user=user)
        orga = Organisation.objects.create(user=user, name='Ghibli')

        url = self._build_add_subjects_url(activity)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        context = response1.context
        self.assertEqual(
            _('Adding subjects to activity «{entity}»').format(entity=activity),
            context.get('title'),
        )
        self.assertEqual(_('Add the subjects'), context.get('submit_label'))

        # ---
        data = {'subjects': self.formfield_value_multi_generic_entity(orga)}
        self.assertNoFormError(self.client.post(url, data=data))
        self.assertCountEqual(
            [orga.id],
            [
                *Relation.objects
                         .filter(object_entity=activity.id, type=REL_SUB_ACTIVITY_SUBJECT)
                         .values_list('subject_entity_id', flat=True)
            ],
        )

        # Avoid duplicates
        response2 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response2.context['form'],
            field='subjects',
            errors=ngettext(
                'This entity is already a subject: %(duplicates)s',
                'These entities are already subjects: %(duplicates)s',
                1,
            ) % {'duplicates': orga},
        )

    def test_add_subjects__link_perm__activity(self):
        "Credentials error with the activity."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own='!LINK')

        activity = self._create_meeting(user=user)
        self.assertTrue(user.has_perm_to_change(activity))
        self.assertFalse(user.has_perm_to_link(activity))
        self.assertGET403(self._build_add_subjects_url(activity))

    @skipIfCustomOrganisation
    def test_add_subjects__link_perm__subjects(self):
        "Credentials error with selected subjects."
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own=['LINK'], all='!LINK')

        activity = self._create_meeting(user=user)
        self.assertTrue(user.has_perm_to_link(activity))

        orga = Organisation.objects.create(user=self.get_root_user(), name='Ghibli')
        self.assertTrue(user.has_perm_to_change(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        uri = self._build_add_subjects_url(activity)
        self.assertGET200(uri)

        response = self.assertPOST200(
            uri, data={'subjects': self.formfield_value_multi_generic_entity(orga)},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='subjects',
            errors=_('Some entities are not linkable: {}').format(orga),
        )
        self.assertFalse(Relation.objects.filter(
            object_entity=activity.id,
            type=REL_SUB_ACTIVITY_SUBJECT,
        ))

    def test_add_subjects__bad_ctype(self):
        "Bad ContentType (relationType constraint error)."
        user = self.login_as_root_and_get()

        create_meeting = partial(self._create_meeting, user=user)
        activity    = create_meeting(title='My meeting')
        bad_subject = create_meeting(title="I'm bad heeheeeee")

        response = self.assertPOST200(
            self._build_add_subjects_url(activity),
            data={'subjects': self.formfield_value_multi_generic_entity(bad_subject)},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='subjects', errors=_('This content type is not allowed.'),
        )

    @skipIfCustomContact
    def test_remove_subject(self):
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own='*')

        activity = self._create_meeting(user=user)
        contact = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')

        create_rel = partial(
            Relation.objects.create,
            subject_entity=contact, object_entity=activity, user=user,
        )
        r1 = create_rel(type_id=REL_SUB_PART_2_ACTIVITY)
        r2 = create_rel(type_id=REL_SUB_ACTIVITY_SUBJECT)
        r3 = create_rel(type_id=REL_SUB_LINKED_2_ACTIVITY)
        r4 = create_rel(type_id=REL_SUB_HAS)

        url = self.RM_SUBJECT_URL
        self.assertGET405(url)

        response = self.assertPOST200(url, data={'id': r2.symmetric_relation_id}, follow=True)
        self.assertDoesNotExist(r2)
        self.assertRedirects(response, activity.get_absolute_url())

        # Errors
        self.assertPOST404(url, data={'id': r1.symmetric_relation_id})
        self.assertPOST404(url, data={'id': r3.symmetric_relation_id})
        self.assertPOST404(url, data={'id': r4.symmetric_relation_id})
        self.assertPOST404(url)

    @skipIfCustomContact
    def test_remove_subject__unlink_perm__activity(self):
        "Can not unlink the activity."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='!UNLINK')

        activity = self._create_meeting(user=user)
        contact = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')
        relation = Relation.objects.create(
            subject_entity=contact,
            type_id=REL_SUB_ACTIVITY_SUBJECT,
            object_entity=activity,
            user=user,
        )

        self.assertPOST403(
            self.RM_SUBJECT_URL,
            data={'id': relation.symmetric_relation_id},
        )
        self.assertStillExists(relation)

    @skipIfCustomContact
    def test_remove_subject__unlink_perm__contact(self):
        "Can not unlink the contact."
        user = self.login_as_standard()
        self.add_credentials(user.role, all='!UNLINK', own='*')

        activity = self._create_meeting(user=user)
        contact = Contact.objects.create(
            user=self.get_root_user(), first_name='Musashi', last_name='Miyamoto',
        )
        relation = Relation.objects.create(
            subject_entity=contact,
            type_id=REL_SUB_ACTIVITY_SUBJECT,
            object_entity=activity,
            user=user,
        )
        self.assertPOST403(
            self.RM_SUBJECT_URL,
            data={'id': relation.symmetric_relation_id},
        )
        self.assertStillExists(relation)


@skipIfCustomContact
@skipIfCustomActivity
class RelatedActivitiesBricksViewsTestCase(_ActivitiesTestCase):
    RM_RELATED_URL = reverse('activities__unlink_activity')

    def test_unlink(self):
        user = self.login_as_activities_user()
        self.add_credentials(user.role, own='*')

        activity = self._create_meeting(user=user)
        contact = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')

        create_rel = partial(
            Relation.objects.create,
            subject_entity=contact, object_entity=activity, user=user,
        )
        r1 = create_rel(type_id=REL_SUB_PART_2_ACTIVITY)
        r2 = create_rel(type_id=REL_SUB_ACTIVITY_SUBJECT)
        r3 = create_rel(type_id=REL_SUB_LINKED_2_ACTIVITY)
        r4 = create_rel(type_id=REL_SUB_HAS)
        self.assertEqual(3, contact.relations.filter(pk__in=[r1.id, r2.id, r3.id]).count())

        url = self.RM_RELATED_URL
        self.assertPOST200(url, data={'id': activity.id, 'object_id': contact.id}, follow=True)
        self.assertFalse(contact.relations.filter(pk__in=[r1.id, r2.id, r3.id]))
        self.assertEqual(1, contact.relations.filter(pk=r4.id).count())

        # Errors
        self.assertPOST404(url, data={'id': activity.id})
        self.assertPOST404(url, data={'object_id': contact.id})
        self.assertPOST404(url)
        self.assertPOST404(url, data={'id': self.UNUSED_PK, 'object_id': contact.id})
        self.assertPOST404(url, data={'id': activity.id,    'object_id': self.UNUSED_PK})

    def test_unlink__unlink_perm__activity(self):
        "Can not unlink the activity."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='!UNLINK')

        activity = self._create_meeting(user=user)
        contact = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')
        relation = Relation.objects.create(
            subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=activity, user=user,
        )
        self.assertPOST403(
            self.RM_RELATED_URL,
            data={'id': activity.id, 'object_id': contact.id},
        )
        self.assertStillExists(relation)

    def test_unlink__unlink_perm__contact(self):
        "Can not unlink the contact."
        user = self.login_as_standard()
        self.add_credentials(user.role, all='!UNLINK', own='*')

        activity = self._create_meeting(user=user)
        contact = Contact.objects.create(
            user=self.get_root_user(), first_name='Musashi', last_name='Miyamoto',
        )
        relation = Relation.objects.create(
            subject_entity=contact,
            type_id=REL_SUB_PART_2_ACTIVITY,
            object_entity=activity, user=user,
        )

        self.assertPOST403(
            self.RM_RELATED_URL,
            data={'id': activity.id, 'object_id': contact.id},
        )
        self.assertStillExists(relation)
