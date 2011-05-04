# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from django.contrib.contenttypes.models import ContentType
from activesync.models.active_sync import CremeExchangeMapping
from activities.models.activity import Meeting
from creme_core.models.relation import Relation

from creme_core.tests.base import CremeTestCase

from persons.models.contact import Contact
from persons.models.organisation import Organisation
from persons.constants import REL_SUB_EMPLOYED_BY

class ActiveSyncModelsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'persons', )
        self.login()

    def test_mapping_update_contact01(self):
        user = self.user
        contact = Contact.objects.create(user=user, first_name='Mario', last_name='Bros')
        ct_contact = ContentType.objects.get_for_model(contact)

        self.assertEqual(0, CremeExchangeMapping.objects.filter(user=user).count())

        CremeExchangeMapping.objects.create(user=user, synced=False, creme_entity_id=contact.pk, exchange_entity_id="fake id", creme_entity_ct=ct_contact)

        contact.email = 'mario@bros.com'
        contact.save()

        self.assertEqual(1, CremeExchangeMapping.objects.filter(user=user, creme_entity_id=contact.id).count())

        map = CremeExchangeMapping.objects.get(user=user, creme_entity_id=contact.id)

        self.assertTrue(map.is_creme_modified)


    def test_mapping_delete_contact01(self):
        user = self.user
        contact = Contact.objects.create(user=user, first_name='Mario', last_name='Bros')
        ct_contact = ContentType.objects.get_for_model(contact)

        map = CremeExchangeMapping.objects.create(user=user, synced=False, creme_entity_id=contact.pk, exchange_entity_id="fake id", creme_entity_ct=ct_contact)

        self.assertFalse(map.was_deleted)

        contact.delete()
        map = CremeExchangeMapping.objects.get(pk=map.id)#Refresh

        self.assertTrue(map.was_deleted)


    def test_mapping_create_relation_contact_orga01(self):
        user = self.user
        contact = Contact.objects.create(user=user, first_name='Mario', last_name='Bros')
        ct_contact = ContentType.objects.get_for_model(contact)
        
        orga = Organisation.objects.create(user=user, name='Nintendo')
        
        map = CremeExchangeMapping.objects.create(user=user, synced=False, creme_entity_id=contact.pk, exchange_entity_id="fake id", creme_entity_ct=ct_contact)

        self.assertFalse(map.is_creme_modified)
        self.assertEqual(0, Relation.objects.filter(subject_entity=contact, object_entity=orga, type__id=REL_SUB_EMPLOYED_BY).count())

        Relation.objects.create(subject_entity=contact, object_entity=orga, type_id=REL_SUB_EMPLOYED_BY, user=user)

        self.assertEqual(1, Relation.objects.filter(subject_entity=contact, object_entity=orga, type__id=REL_SUB_EMPLOYED_BY).count())

        map = CremeExchangeMapping.objects.get(pk=map.id)#Refresh
        self.assertTrue(map.is_creme_modified)

        
    def test_mapping_delete_relation_contact_orga01(self):
        user = self.user
        contact = Contact.objects.create(user=user, first_name='Mario', last_name='Bros')
        ct_contact = ContentType.objects.get_for_model(contact)
        
        orga = Organisation.objects.create(user=user, name='Nintendo')

        map = CremeExchangeMapping.objects.create(user=user, synced=False, creme_entity_id=contact.pk, exchange_entity_id="fake id", creme_entity_ct=ct_contact)

        self.assertFalse(map.is_creme_modified)
        self.assertEqual(0, Relation.objects.filter(subject_entity=contact, object_entity=orga, type__id=REL_SUB_EMPLOYED_BY).count())

        rel = Relation.objects.create(subject_entity=contact, object_entity=orga, type_id=REL_SUB_EMPLOYED_BY, user=user)

        self.assertEqual(1, Relation.objects.filter(subject_entity=contact, object_entity=orga, type__id=REL_SUB_EMPLOYED_BY).count())

        map.is_creme_modified = False
        map.save()

        rel.delete()
        
        map = CremeExchangeMapping.objects.get(pk=map.id)#Refresh

        self.assertTrue(map.is_creme_modified)


    def test_mapping_update_meeting01(self):
        user = self.user
        meeting = Meeting.objects.create(user=user, title="Meeting with Peach")
        ct_meeting = ContentType.objects.get_for_model(meeting)

        self.assertEqual(0, CremeExchangeMapping.objects.filter(user=user).count())

        CremeExchangeMapping.objects.create(user=user, synced=False, creme_entity_id=meeting.pk, exchange_entity_id="fake id", creme_entity_ct=ct_meeting)

        meeting.place = 'Mushroom castle'
        meeting.save()

        self.assertEqual(1, CremeExchangeMapping.objects.filter(user=user, creme_entity_id=meeting.id).count())

        map = CremeExchangeMapping.objects.get(user=user, creme_entity_id=meeting.id)

        self.assertTrue(map.is_creme_modified)


    def test_mapping_delete_meeting01(self):
        user = self.user
        meeting = Meeting.objects.create(user=user, title="Meeting with Peach")
        ct_meeting = ContentType.objects.get_for_model(meeting)

        map = CremeExchangeMapping.objects.create(user=user, synced=False, creme_entity_id=meeting.pk, exchange_entity_id="fake id", creme_entity_ct=ct_meeting)

        self.assertFalse(map.was_deleted)

        meeting.delete()
        map = CremeExchangeMapping.objects.get(pk=map.id)#Refresh

        self.assertTrue(map.was_deleted)