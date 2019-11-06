# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.auth import get_user_model
    from django.urls import reverse
    from django.utils.timezone import now
    from django.utils.translation import gettext as _, ngettext

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.constants import REL_SUB_HAS
    from creme.creme_core.models import Relation, SetCredentials

    from creme.persons.constants import REL_SUB_EMPLOYED_BY
    from creme.persons.tests.base import skipIfCustomContact, skipIfCustomOrganisation

    from .base import (
        _ActivitiesTestCase,
        skipIfCustomActivity, Activity,
       Contact, Organisation,
    )
    from .. import constants
    from ..models import Calendar
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIfCustomActivity
class ActivityBricksTestCase(_ActivitiesTestCase):
    RM_PARTICIPANT_URL = reverse('activities__remove_participant')

    def _buid_add_participants_url(self, activity):
        return reverse('activities__add_participants', args=(activity.id,))

    def _buid_add_subjects_url(self, activity):
        return reverse('activities__add_subjects', args=(activity.id,))

    @skipIfCustomContact
    def test_add_participants01(self):
        user = self.login()
        activity = self._create_meeting()

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c2 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        url = self._buid_add_participants_url(activity)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('Adding participants to activity «{entity}»').format(entity=activity),
            context.get('title')
        )
        self.assertEqual(_('Add the participants'), context.get('submit_label'))

        # ---
        self.assertNoFormError(
            self.client.post(url, data={'participants': self.formfield_value_multi_creator_entity(c1, c2)})
        )

        relations = Relation.objects.filter(subject_entity=activity.id, type=constants.REL_OBJ_PART_2_ACTIVITY)
        self.assertEqual(2, len(relations))
        self.assertSetEqual({c1.id, c2.id}, {r.object_entity_id for r in relations})

    def test_add_participants02(self):
        "Credentials error with the activity."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        activity = self._create_meeting()
        self.assertTrue(user.has_perm_to_change(activity))
        self.assertFalse(user.has_perm_to_link(activity))
        self.assertGET403(self._buid_add_participants_url(activity))

    @skipIfCustomContact
    def test_add_participants03(self):
        "Credentials error with selected subjects."
        user = self.login(is_superuser=False)
        self._build_nolink_setcreds()

        activity = self._create_meeting()
        self.assertTrue(user.has_perm_to_link(activity))

        contact = Contact.objects.create(user=self.other_user, first_name='Musashi', last_name='Miyamoto')
        self.assertTrue(user.has_perm_to_change(contact))
        self.assertFalse(user.has_perm_to_link(contact))

        uri = self._buid_add_participants_url(activity)
        self.assertGET200(uri)

        response = self.assertPOST200(
            uri,
            data={'participants': self.formfield_value_multi_creator_entity(contact)},
        )
        self.assertFormError(
            response, 'form', 'participants',
            _('Some entities are not linkable: {}').format(contact)
        )
        self.assertFalse(
            Relation.objects.filter(subject_entity=activity.id,
                                    type=constants.REL_OBJ_PART_2_ACTIVITY,
                                   )
        )

    @skipIfCustomContact
    def test_add_participants04(self):
        "'My participation' field is removed when it is useless."
        activity = self._create_activity_by_view()

        create_contact = partial(Contact.objects.create, user=self.user)
        c1 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c2 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        uri = self._buid_add_participants_url(activity)
        response = self.assertGET200(uri)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('my_participation', fields)
        self.assertNotIn('my_calendar',      fields)

        self.assertNoFormError(
            self.client.post(uri, data={'participants': self.formfield_value_multi_creator_entity(c1, c2)})
        )

        relations = Relation.objects.filter(subject_entity=activity.id, type=constants.REL_OBJ_PART_2_ACTIVITY)
        self.assertEqual(3, len(relations))
        self.assertSetEqual({c1.id, c2.id, self.user.linked_contact.id},
                            {r.object_entity_id for r in relations}
                           )

    @skipIfCustomContact
    def test_add_participants05(self):
        "Fix a bug when checking for collision for a floating activities."
        activity = self._create_activity_by_view()
        self.assertIsNone(activity.start)
        self.assertIsNone(activity.end)
        self.assertEqual(constants.FLOATING, activity.floating_type)

        create_contact = partial(Contact.objects.create, user=self.user)
        c1 = create_contact(first_name='Musashi', last_name='Miyamoto')
        c2 = create_contact(first_name='Kojiro',  last_name='Sasaki')

        uri = self._buid_add_participants_url(activity)
        self.assertGET200(uri)
        self.assertNoFormError(
                self.client.post(uri, data={'participants': self.formfield_value_multi_creator_entity(c1, c2)})
        )

        relations = Relation.objects.filter(subject_entity=activity.id, type=constants.REL_OBJ_PART_2_ACTIVITY)
        self.assertEqual(3, len(relations))
        self.assertSetEqual({c1.id, c2.id, self.user.linked_contact.id},
                            {r.object_entity_id for r in relations},
                           )

    def test_add_participants06(self):
        "When Teams are selected, their teammates are participants."
        user = self.login()
        activity = self._create_meeting()

        create_user = get_user_model().objects.create
        musashi = create_user(username='musashi', first_name='Musashi',
                              last_name='Miyamoto', email='musashi@miyamoto.jp',
                             )
        kojiro  = create_user(username='kojiro', first_name='Kojiro',
                              last_name='Sasaki', email='kojiro@sasaki.jp',
                             )

        team = create_user(username='Samurais', is_team=True, role=None)
        team.teammates = [musashi, kojiro, user]

        response = self.client.post(
            self._buid_add_participants_url(activity),
            data={'my_participation_0':  True,
                  'my_participation_1':  Calendar.objects.get_default_calendar(user).pk,
                  'participating_users': [team.id, kojiro.id],
                 },
        )
        self.assertNoFormError(response)

        relations = Relation.objects.filter(subject_entity=activity.id, type=constants.REL_OBJ_PART_2_ACTIVITY)
        self.assertEqual(3, len(relations))
        self.assertSetEqual(
            {musashi.linked_contact, kojiro.linked_contact, user.linked_contact},
            {r.object_entity.get_real_entity() for r in relations},
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_add_participants07(self):
        "Auto-subject."
        user = self.login()
        activity = self._create_meeting()

        akane = Contact.objects.create(user=user, first_name='Akane', last_name='Tendo')
        dojo = Organisation.objects.create(user=user, name='Tendo Dojo')

        Relation.objects.create(user=user, subject_entity=akane,
                                type_id=REL_SUB_EMPLOYED_BY, object_entity=dojo,
                               )

        self.assertNoFormError(
            self.client.post(self._buid_add_participants_url(activity),
                             data={'participants': self.formfield_value_multi_creator_entity(akane)},
                            )
        )

        self.assertRelationCount(1, dojo, constants.REL_SUB_ACTIVITY_SUBJECT, activity)

    @skipIfCustomContact
    def test_remove_participants01(self):
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW   |
                  EntityCredentials.CHANGE |
                  EntityCredentials.DELETE |
                  EntityCredentials.LINK |
                  EntityCredentials.UNLINK,
            set_type=SetCredentials.ESET_ALL,
        )

        logged = user.linked_contact
        other = self.other_user.linked_contact
        contact3 = Contact.objects.create(user=user, first_name='Roy', last_name='Mustang')

        dt_now = now()
        phone_call = Activity.objects.create(
            title='a random activity',
            start=dt_now, end=dt_now,
            user=user, type_id=constants.ACTIVITYTYPE_PHONECALL,
        )

        self.assertPOST200(
            self._buid_add_participants_url(phone_call), follow=True,
            data={'my_participation_0':  True,
                  'my_participation_1':  Calendar.objects.get_default_calendar(logged.is_user).pk,
                  'participating_users': [other.is_user_id],
                  'participants':        self.formfield_value_multi_creator_entity(contact3),
                 },
        )

        self.assertRelationCount(1, phone_call, constants.REL_OBJ_PART_2_ACTIVITY, logged)   # logged user, push in his calendar
        self.assertRelationCount(1, phone_call, constants.REL_OBJ_PART_2_ACTIVITY, other)    # other contact user, push in his calendar too
        self.assertRelationCount(1, phone_call, constants.REL_OBJ_PART_2_ACTIVITY, contact3) # classic contact, has no calendar
        self.assertEqual(2, phone_call.calendars.count())

        sym_rel = Relation.objects.get(subject_entity=logged, type=constants.REL_SUB_PART_2_ACTIVITY, object_entity=phone_call)

        del_url = self.RM_PARTICIPANT_URL
        # self.assertGET404(del_url)
        self.assertGET405(del_url)
        self.assertPOST404(del_url, data={'id': sym_rel.pk})
        self.get_object_or_fail(Relation, pk=sym_rel.pk)

        qs = Relation.objects.filter(type=constants.REL_OBJ_PART_2_ACTIVITY, subject_entity=phone_call)

        for participant_rel in qs.all():
            # self.assertGET404(del_url)
            self.assertGET405(del_url)
            response = self.client.post(del_url, data={'id': participant_rel.pk})
            self.assertRedirects(response, phone_call.get_absolute_url())

        self.assertFalse(qs.all())
        self.assertFalse(phone_call.calendars.all())

    @skipIfCustomContact
    def test_remove_participants02(self):
        "Cannot unlink the contact"
        user = self.login(is_superuser=False)
        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(value=EntityCredentials.VIEW | EntityCredentials.UNLINK,
                     set_type=SetCredentials.ESET_OWN,
                    )
        create_creds(value=EntityCredentials.VIEW   |
                           EntityCredentials.CHANGE |
                           EntityCredentials.DELETE |
                           EntityCredentials.LINK,
                     set_type=SetCredentials.ESET_ALL,
                    )

        contact = self.other_user.linked_contact
        self.assertFalse(user.has_perm_to_unlink(contact))

        phone_call = Activity.objects.create(
            title='A random activity',
            user=user, type_id=constants.ACTIVITYTYPE_PHONECALL,
        )
        self.assertTrue(user.has_perm_to_unlink(phone_call))

        rel = Relation.objects.create(user=user,
                                      subject_entity=phone_call,
                                      type_id=constants.REL_OBJ_PART_2_ACTIVITY,
                                      object_entity=contact,
                                     )

        self.assertPOST403(self.RM_PARTICIPANT_URL, data={'id': rel.id})

    @skipIfCustomContact
    def test_remove_participants03(self):
        "Cannot unlink the activity"
        user = self.login(is_superuser=False)
        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(value=EntityCredentials.VIEW | EntityCredentials.UNLINK,
                     set_type=SetCredentials.ESET_OWN,
                    )
        create_creds(value=EntityCredentials.VIEW   |
                           EntityCredentials.CHANGE |
                           EntityCredentials.DELETE |
                           EntityCredentials.LINK,
                     set_type=SetCredentials.ESET_ALL,
                    )

        contact = user.linked_contact
        self.assertTrue(user.has_perm_to_unlink(contact))

        phone_call = Activity.objects.create(
            title='A random activity',
            user=self.other_user, type_id=constants.ACTIVITYTYPE_PHONECALL,
        )
        self.assertFalse(user.has_perm_to_unlink(phone_call))

        rel = Relation.objects.create(user=user,
                                      subject_entity=phone_call,
                                      type_id=constants.REL_OBJ_PART_2_ACTIVITY,
                                      object_entity=contact,
                                     )

        self.assertPOST403(self.RM_PARTICIPANT_URL, data={'id': rel.id})

    @skipIfCustomOrganisation
    def test_add_subjects01(self):
        user = self.login()

        activity = self._create_meeting()
        orga = Organisation.objects.create(user=user, name='Ghibli')

        url = self._buid_add_subjects_url(activity)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(_('Adding subjects to activity «{entity}»').format(entity=activity),
                         context.get('title')
                        )
        self.assertEqual(_('Add the subjects'), context.get('submit_label'))

        # ---
        data = {'subjects': self.formfield_value_multi_generic_entity(orga)}
        self.assertNoFormError(self.client.post(url, data=data))

        relations = Relation.objects.filter(subject_entity=activity.id,
                                            type=constants.REL_OBJ_ACTIVITY_SUBJECT,
                                           )
        self.assertEqual(1, len(relations))
        self.assertEqual(orga.id, relations[0].object_entity_id)

        # Avoid duplicates
        response = self.assertPOST200(url, data=data)
        self.assertFormError(
            response, 'form', 'subjects',
            ngettext('This entity is already a subject: %(duplicates)s',
                     'These entities are already subjects: %(duplicates)s',
                     1
                    ) % {'duplicates': orga}
        )

    def test_add_subjects02(self):
        "Credentials error with the activity."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        activity = self._create_meeting()
        self.assertTrue(user.has_perm_to_change(activity))
        self.assertFalse(user.has_perm_to_link(activity))
        self.assertGET403(self._buid_add_subjects_url(activity))

    @skipIfCustomOrganisation
    def test_add_subjects03(self):
        "Credentials error with selected subjects."
        user = self.login(is_superuser=False)
        self._build_nolink_setcreds()

        activity = self._create_meeting()
        self.assertTrue(user.has_perm_to_link(activity))

        orga = Organisation.objects.create(user=self.other_user, name='Ghibli')
        self.assertTrue(user.has_perm_to_change(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        uri = self._buid_add_subjects_url(activity)
        self.assertGET200(uri)

        response = self.assertPOST200(
            uri,
            data={'subjects': self.formfield_value_multi_generic_entity(orga)},
        )
        self.assertFormError(
            response, 'form', 'subjects',
            _('Some entities are not linkable: {}').format(orga)
        )
        self.assertFalse(
            Relation.objects.filter(subject_entity=activity.id,
                                    type=constants.REL_OBJ_ACTIVITY_SUBJECT,
                                   )
        )

    def test_add_subjects04(self):
        "Bad ContentType (relationType constraint error)."
        self.login()

        create_meeting = self._create_meeting
        activity    = create_meeting(title='My meeting')
        bad_subject = create_meeting(title="I'm bad heeheeeee")

        response = self.assertPOST200(
            self._buid_add_subjects_url(activity),
            data={'subjects': self.formfield_value_multi_generic_entity(bad_subject)},
        )
        self.assertFormError(response, 'form', 'subjects',
                             _('This content type is not allowed.')
                            )

    @skipIfCustomContact
    def test_unlink01(self):
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        activity = self._create_meeting()
        contact = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')

        create_rel = partial(Relation.objects.create, subject_entity=contact,
                             object_entity=activity, user=user,
                            )
        r1 = create_rel(type_id=constants.REL_SUB_PART_2_ACTIVITY)
        r2 = create_rel(type_id=constants.REL_SUB_ACTIVITY_SUBJECT)
        r3 = create_rel(type_id=constants.REL_SUB_LINKED_2_ACTIVITY)
        r4 = create_rel(type_id=REL_SUB_HAS)
        self.assertEqual(3, contact.relations.filter(pk__in=[r1.id, r2.id, r3.id]).count())

        url = reverse('activities__unlink_activity')
        self.assertPOST200(url, data={'id': activity.id, 'object_id': contact.id}, follow=True)
        self.assertFalse(contact.relations.filter(pk__in=[r1.id, r2.id, r3.id]))
        self.assertEqual(1, contact.relations.filter(pk=r4.id).count())

        # Errors
        self.assertPOST404(url, data={'id': activity.id})
        self.assertPOST404(url, data={'object_id': contact.id})
        self.assertPOST404(url)
        self.assertPOST404(url, data={'id': 1024,        'object_id': contact.id})
        self.assertPOST404(url, data={'id': activity.id, 'object_id': 1024})

    @skipIfCustomContact
    def test_unlink02(self):
        "Can not unlink the activity."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        activity = self._create_meeting()
        contact = Contact.objects.create(user=user, first_name='Musashi', last_name='Miyamoto')
        relation = Relation.objects.create(
            subject_entity=contact, type_id=constants.REL_SUB_PART_2_ACTIVITY,
            object_entity=activity, user=user,
        )

        self.assertPOST403(reverse('activities__unlink_activity'),
                           data={'id': activity.id, 'object_id': contact.id},
                          )
        self.assertEqual(1, contact.relations.filter(pk=relation.id).count())

    @skipIfCustomContact
    def test_unlink03(self):
        "Can not unlink the contact."
        user = self.login(is_superuser=False)

        create_creds = partial(SetCredentials.objects.create, role=self.role)
        create_creds(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                           EntityCredentials.DELETE | EntityCredentials.LINK   |
                           EntityCredentials.UNLINK,
                     set_type=SetCredentials.ESET_OWN,
                    )
        create_creds(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                           EntityCredentials.DELETE | EntityCredentials.LINK,
                     set_type=SetCredentials.ESET_ALL,
                    )

        activity = self._create_meeting()
        contact = Contact.objects.create(user=self.other_user, first_name='Musashi', last_name='Miyamoto')
        relation = Relation.objects.create(subject_entity=contact, type_id=constants.REL_SUB_PART_2_ACTIVITY,
                                           object_entity=activity, user=user,
                                          )

        self.assertPOST403(reverse('activities__unlink_activity'),
                           data={'id': activity.id, 'object_id': contact.id},
                          )
        self.get_object_or_fail(Relation, pk=relation.id)
