# -*- coding: utf-8 -*-

from django.test import TestCase
from django.contrib.auth.models import User

from creme_core.models import RelationType, Relation
from creme_core.management.commands.creme_populate import Command as PopulateCommand

from persons.models import Contact

from events.models import *
from events.constants import *


class EventsTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.create(username='Guts')
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        PopulateCommand().handle(application=['creme_core', 'events']) #'persons'
        self.password = 'test'
        self.user = None

    def test_populate(self):
        rtypes_pks = [REL_SUB_IS_INVITED_TO, REL_SUB_ACCEPTED_INVITATION, REL_SUB_REFUSED_INVITATION, REL_SUB_CAME_EVENT, REL_SUB_NOT_CAME_EVENT]
        rtypes = RelationType.objects.filter(pk__in=rtypes_pks)
        self.assertEqual(len(rtypes_pks), len(rtypes))

        self.assert_(EventType.objects.count())

    def create_event(self, name, etype):
        response = self.client.post('/events/event/add', follow=True,
                                    data={
                                            'user':        self.user.pk,
                                            'name':        name,
                                            'type':        etype.pk,
                                            'start_date':  '2010-11-3',
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        try:
            event = Event.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        return event

    def test_event_createview(self):
        self.login()

        response = self.client.get('/events/event/add')
        self.assertEqual(response.status_code, 200)

        name  = 'Eclipse'
        etype = EventType.objects.all()[0]
        event = self.create_event(name, etype)

        self.assertEqual(1,        Event.objects.count())
        self.assertEqual(name,     event.name)
        self.assertEqual(etype.id, event.type_id)

        start = event.start_date
        self.assertEqual(2010, start.year)
        self.assertEqual(11,   start.month)
        self.assertEqual(3,    start.day)

    def test_event_editview(self):
        self.login()

        name  = 'Eclipse'
        etype = EventType.objects.all()[0]
        event = self.create_event(name, etype)

        response = self.client.get('/events/event/edit/%s' % event.id)
        self.assertEqual(response.status_code, 200)

        name += '_edited'
        response = self.client.post('/events/event/edit/%s' % event.id, follow=True,
                                    data={
                                            'user':        self.user.pk,
                                            'name':        name,
                                            'type':        etype.pk,
                                            'start_date':  '2010-11-4',
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        event = Event.objects.get(pk=event.id)
        self.assertEqual(name, event.name)
        self.assertEqual(4,    event.start_date.day)

    def test_listview(self):
        self.login()

        etype = EventType.objects.all()[0]
        event1 = self.create_event('Eclipse', etype)
        event2 = self.create_event('Show', etype)

        response = self.client.get('/events/events')
        self.assertEqual(response.status_code, 200)

        try:
            events_page = response.context['entities']
        except KeyError, e:
            self.fail(str(e))

        self.assertEqual(2, events_page.paginator.count)

        self.assertEqual(set((event1.id, event2.id)), set(event.id for event in events_page.object_list))

    def test_stats01(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])
        stats = event.get_stats()

        self.assertEqual(4, len(stats))
        try:
            self.assertEqual(0, stats['invations_count'])
            self.assertEqual(0, stats['accepted_count'])
            self.assertEqual(0, stats['refused_count'])
            self.assertEqual(0, stats['visitors_count'])
        except Exception, e:
            self.fail(str(e))

    def test_stats02(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])

        casca    = Contact.objects.create(user=self.user, first_name='Casca',    last_name='Miura')
        judo     = Contact.objects.create(user=self.user, first_name='Judo',     last_name='Miura')
        griffith = Contact.objects.create(user=self.user, first_name='Griffith', last_name='Miura')
        rickert  = Contact.objects.create(user=self.user, first_name='Rickert',  last_name='Miura')

        create_relation = Relation.objects.create
        create_relation(subject_entity=casca,    type_id=REL_SUB_IS_INVITED_TO, object_entity=event, user=self.user)
        create_relation(subject_entity=judo,     type_id=REL_SUB_IS_INVITED_TO, object_entity=event, user=self.user)
        create_relation(subject_entity=griffith, type_id=REL_SUB_IS_INVITED_TO, object_entity=event, user=self.user)
        create_relation(subject_entity=rickert,  type_id=REL_SUB_IS_INVITED_TO, object_entity=event, user=self.user)

        create_relation(subject_entity=griffith, type_id=REL_SUB_ACCEPTED_INVITATION, object_entity=event, user=self.user)

        create_relation(subject_entity=casca, type_id=REL_SUB_REFUSED_INVITATION, object_entity=event, user=self.user)
        create_relation(subject_entity=judo,  type_id=REL_SUB_REFUSED_INVITATION, object_entity=event, user=self.user)

        create_relation(subject_entity=casca,    type_id=REL_SUB_CAME_EVENT, object_entity=event, user=self.user)
        create_relation(subject_entity=judo,     type_id=REL_SUB_CAME_EVENT, object_entity=event, user=self.user)
        create_relation(subject_entity=griffith, type_id=REL_SUB_CAME_EVENT, object_entity=event, user=self.user)

        stats = event.get_stats()
        self.assertEqual(4, stats['invations_count'])
        self.assertEqual(1, stats['accepted_count'])
        self.assertEqual(2, stats['refused_count'])
        self.assertEqual(3, stats['visitors_count'])
