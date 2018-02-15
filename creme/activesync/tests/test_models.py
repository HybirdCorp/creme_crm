# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import Relation, Job
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons import get_contact_model, get_organisation_model
    from creme.persons.constants import REL_SUB_EMPLOYED_BY
    from creme.persons.tests.base import skipIfCustomContact, skipIfCustomOrganisation

    from creme.activities.models import Activity
    from creme.activities.constants import ACTIVITYTYPE_MEETING
    from creme.activities.tests.base import skipIfCustomActivity

    from ..creme_jobs import activesync_type
    from ..models import UserSynchronizationHistory, CremeExchangeMapping
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


Contact = get_contact_model()
Organisation = get_organisation_model()


class ActiveSyncModelsTestCase(CremeTestCase):
    def setUp(self):
        self.login()

    def test_populate(self):
        job = self.get_object_or_fail(Job, type_id=activesync_type.id)
        self.assertIsNone(job.user)
        self.assertEqual({'type': 'minutes', 'value': 30}, job.periodicity.as_dict())

    @skipIfCustomContact
    def test_mapping_update_contact01(self):
        user = self.user
        contact = Contact.objects.create(user=user, first_name='Mario', last_name='Bros')
        ct_contact = ContentType.objects.get_for_model(contact)
        self.assertEqual(0, CremeExchangeMapping.objects.filter(user=user).count())

        CremeExchangeMapping.objects.create(user=user, synced=False, creme_entity_id=contact.pk,
                                            exchange_entity_id="fake id", creme_entity_ct=ct_contact
                                           )

        contact.email = 'mario@bros.com'
        contact.save()
        self.assertEqual(1, CremeExchangeMapping.objects.filter(user=user, creme_entity_id=contact.id).count())

        mapping = CremeExchangeMapping.objects.get(user=user, creme_entity_id=contact.id)
        self.assertTrue(mapping.is_creme_modified)

    @skipIfCustomContact
    def test_mapping_delete_contact01(self):
        user = self.user
        contact = Contact.objects.create(user=user, first_name='Mario', last_name='Bros')
        ct_contact = ContentType.objects.get_for_model(contact)

        mapping = CremeExchangeMapping.objects.create(user=user, synced=False, creme_entity_id=contact.pk,
                                                      exchange_entity_id="fake id", creme_entity_ct=ct_contact
                                                     )
        self.assertFalse(mapping.was_deleted)

        contact.delete()
        self.assertTrue(self.refresh(mapping).was_deleted)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_mapping_create_relation_contact_orga01(self):
        user = self.user
        contact = Contact.objects.create(user=user, first_name='Mario', last_name='Bros')
        ct_contact = ContentType.objects.get_for_model(contact)
        orga = Organisation.objects.create(user=user, name='Nintendo')

        mapping = CremeExchangeMapping.objects.create(user=user, synced=False, creme_entity_id=contact.pk,
                                                      exchange_entity_id="fake id", creme_entity_ct=ct_contact
                                                     )
        self.assertFalse(mapping.is_creme_modified)
        self.assertRelationCount(0, contact, REL_SUB_EMPLOYED_BY, orga)

        Relation.objects.create(subject_entity=contact, object_entity=orga, type_id=REL_SUB_EMPLOYED_BY, user=user)
        self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, orga)

        self.assertTrue(self.refresh(mapping).is_creme_modified)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_mapping_delete_relation_contact_orga01(self):
        user = self.user
        contact = Contact.objects.create(user=user, first_name='Mario', last_name='Bros')
        ct_contact = ContentType.objects.get_for_model(contact)
        orga = Organisation.objects.create(user=user, name='Nintendo')

        mapping = CremeExchangeMapping.objects.create(user=user, synced=False, creme_entity_id=contact.pk,
                                                      exchange_entity_id="fake id", creme_entity_ct=ct_contact
                                                     )
        self.assertFalse(mapping.is_creme_modified)
        self.assertRelationCount(0, contact, REL_SUB_EMPLOYED_BY, orga)

        rel = Relation.objects.create(subject_entity=contact, object_entity=orga, type_id=REL_SUB_EMPLOYED_BY, user=user)
        self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, orga)

        mapping.is_creme_modified = False
        mapping.save()

        rel.delete()
        self.assertTrue(self.refresh(mapping).is_creme_modified)

    @skipIfCustomActivity
    def test_mapping_update_meeting01(self):
        user = self.user
        meeting = Activity.objects.create(user=user, title="Meeting with Peach", type_id=ACTIVITYTYPE_MEETING)
        ct_activity = ContentType.objects.get_for_model(Activity)

        self.assertEqual(0, CremeExchangeMapping.objects.filter(user=user).count())

        CremeExchangeMapping.objects.create(user=user, synced=False, creme_entity_id=meeting.pk,
                                            exchange_entity_id="fake id", creme_entity_ct=ct_activity
                                           )

        meeting.place = 'Mushroom castle'
        meeting.save()
        self.assertEqual(1, CremeExchangeMapping.objects.filter(user=user, creme_entity_id=meeting.id).count())

        mapping = CremeExchangeMapping.objects.get(user=user, creme_entity_id=meeting.id)
        self.assertTrue(mapping.is_creme_modified)

    @skipIfCustomActivity
    def test_mapping_delete_meeting01(self):
        user = self.user
        meeting = Activity.objects.create(user=user, title="Meeting with Peach", type_id=ACTIVITYTYPE_MEETING)
        ct_activity = ContentType.objects.get_for_model(meeting)

        mapping = CremeExchangeMapping.objects.create(user=user, synced=False, creme_entity_id=meeting.pk,
                                                      exchange_entity_id="fake id", creme_entity_ct=ct_activity
                                                     )
        self.assertFalse(mapping.was_deleted)

        meeting.delete()
        self.assertTrue(self.refresh(mapping).was_deleted)

    @skipIfCustomContact
    def test_user_synchronization_history01(self):
        """Property and cache"""
        u = UserSynchronizationHistory()
        self.assertIsNone(u.entity)

        contact = Contact.objects.create(user=self.user, first_name='Mario', last_name='Bros')

        u.entity = contact
        self.assertEqual(contact, u.entity)  # Set
        self.assertEqual(contact, u.entity)  # Hit

        u._entity = None
        self.assertEqual(contact, u.entity)  # Set again

        u._entity   = None
        u.entity_pk = None
        self.assertIsNone(u.entity)
