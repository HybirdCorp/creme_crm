# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation
from creme_core.tests.base import CremeTestCase

from persons.models import Contact

from events.models import *
from events.constants import *


class EventsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'events') #'persons'

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

    def test_set_invitation_status01(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        stats = event.get_stats()
        self.assertEqual(0, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])
        self.assertEqual(0, stats['visitors_count'])

        response = self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, casca.id),
                                    data={'status': str(INV_STATUS_NO_ANSWER)}
                                   )
        self.assertEqual(response.status_code, 200)

        stats = event.get_stats()
        self.assertEqual(1, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])
        self.assertEqual(0, stats['visitors_count'])

        response = self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, casca.id),
                                    data={'status': str(INV_STATUS_NOT_INVITED)}
                                   )
        self.assertEqual(response.status_code, 200)

        stats = event.get_stats()
        self.assertEqual(0, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])
        self.assertEqual(0, stats['visitors_count'])

    def test_set_invitation_status02(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        response = self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, casca.id),
                                    data={'status': str(INV_STATUS_ACCEPTED)}
                                   )
        self.assertEqual(response.status_code, 200)

        stats = event.get_stats()
        self.assertEqual(1, stats['invations_count'])
        self.assertEqual(1, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

        self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, casca.id),
                         data={'status': str(INV_STATUS_NOT_INVITED)})
        stats = event.get_stats()
        self.assertEqual(0, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

    def test_set_invitation_status03(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, casca.id),
                         data={'status': str(INV_STATUS_REFUSED)})
        stats = event.get_stats()
        self.assertEqual(1, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(1, stats['refused_count'])

        self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, casca.id),
                         data={'status': str(INV_STATUS_NOT_INVITED)})
        stats = event.get_stats()
        self.assertEqual(0, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

    def test_set_invitation_status04(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, casca.id),
                         data={'status': str(INV_STATUS_ACCEPTED)})
        self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, casca.id),
                         data={'status': str(INV_STATUS_REFUSED)})
        stats = event.get_stats()
        self.assertEqual(1, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(1, stats['refused_count'])

        self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, casca.id),
                         data={'status': str(INV_STATUS_NO_ANSWER)})
        stats = event.get_stats()
        self.assertEqual(1, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

    def test_set_invitation_status05(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, casca.id),
                         data={'status': str(INV_STATUS_REFUSED)})
        self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, casca.id),
                         data={'status': str(INV_STATUS_ACCEPTED)})
        stats = event.get_stats()
        self.assertEqual(1, stats['invations_count'])
        self.assertEqual(1, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])

    def test_set_presence_status01(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        response = self.client.post('/events/event/%s/contact/%s/set_presence_status' % (event.id, casca.id),
                                    data={'status': str(PRES_STATUS_COME)})
        self.assertEqual(response.status_code, 200)

        stats = event.get_stats()
        self.assertEqual(0, stats['invations_count'])
        self.assertEqual(0, stats['accepted_count'])
        self.assertEqual(0, stats['refused_count'])
        self.assertEqual(1, stats['visitors_count'])

        self.client.post('/events/event/%s/contact/%s/set_presence_status' % (event.id, casca.id),
                         data={'status': str(PRES_STATUS_DONT_KNOW)})
        self.assertEqual(0, event.get_stats()['visitors_count'])
        self.assertEqual(0, Relation.objects.filter(subject_entity=casca, object_entity=event, type=REL_SUB_NOT_CAME_EVENT).count())

    def test_set_presence_status02(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        self.client.post('/events/event/%s/contact/%s/set_presence_status' % (event.id, casca.id),
                         data={'status': str(PRES_STATUS_COME)})
        self.assertEqual(1, event.get_stats()['visitors_count'])

        self.client.post('/events/event/%s/contact/%s/set_presence_status' % (event.id, casca.id),
                         data={'status': str(PRES_STATUS_NOT_COME)})
        self.assertEqual(0, event.get_stats()['visitors_count'])
        self.assertEqual(1, Relation.objects.filter(subject_entity=casca, object_entity=event, type=REL_SUB_NOT_CAME_EVENT).count())

        self.client.post('/events/event/%s/contact/%s/set_presence_status' % (event.id, casca.id),
                         data={'status': str(PRES_STATUS_DONT_KNOW)})
        self.assertEqual(0, event.get_stats()['visitors_count'])
        self.assertEqual(0, Relation.objects.filter(subject_entity=casca, object_entity=event, type=REL_SUB_NOT_CAME_EVENT).count())

    def test_set_presence_status03(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        self.client.post('/events/event/%s/contact/%s/set_presence_status' % (event.id, casca.id),
                         data={'status': str(PRES_STATUS_NOT_COME)})
        self.assertEqual(0, event.get_stats()['visitors_count'])
        self.assertEqual(1, Relation.objects.filter(subject_entity=casca, object_entity=event, type=REL_SUB_NOT_CAME_EVENT).count())

        self.client.post('/events/event/%s/contact/%s/set_presence_status' % (event.id, casca.id),
                         data={'status': str(PRES_STATUS_COME)})
        self.assertEqual(1, event.get_stats()['visitors_count'])
        self.assertEqual(0, Relation.objects.filter(subject_entity=casca, object_entity=event, type=REL_SUB_NOT_CAME_EVENT).count())

    def test_list_contacts(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])

        create_contact = Contact.objects.create
        casca    = create_contact(user=self.user, first_name='Casca',    last_name='Miura')
        judo     = create_contact(user=self.user, first_name='Judo',     last_name='Miura')
        griffith = create_contact(user=self.user, first_name='Griffith', last_name='Miura')

        self.client.post('/events/event/%s/contact/%s/set_presence_status' % (event.id, casca.id),
                         data={'status': str(PRES_STATUS_COME)})
        self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, judo.id),
                         data={'status': str(INV_STATUS_NO_ANSWER)})
        self.client.post('/events/event/%s/contact/%s/set_invitation_status' % (event.id, griffith.id),
                         data={'status': str(INV_STATUS_ACCEPTED)})

        self.populate('persons') #HeaderFilter....

        response = self.client.get('/events/event/%s/contacts' % event.id)
        self.assertEqual(response.status_code, 200)

        try:
            contacts_page = response.context['entities']
        except KeyError, e:
            self.fail(str(e))

        self.assertEqual(3, contacts_page.paginator.count)
        self.assertEqual(set((casca.id, judo.id, griffith.id)), set(contact.id for contact in contacts_page.object_list))

    @staticmethod
    def relations_types(contact, event):
        return list(Relation.objects.filter(subject_entity=contact, object_entity=event) \
                                    .values_list('type_id', flat=True))

    def test_link_contacts01(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        response = self.client.get('/events/event/%s/link_contacts' % event.id)
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/events/event/%s/link_contacts' % event.id, follow=True,
                                    data= {
                                            "related_contacts": '(%s,%s,%s);' % (REL_OBJ_CAME_EVENT, ContentType.objects.get_for_model(Contact).id, casca.id),
                                          }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertEqual([REL_SUB_CAME_EVENT], self.relations_types(casca, event))

    def test_link_contacts02(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])

        create_contact = Contact.objects.create
        casca    = create_contact(user=self.user, first_name='Casca',    last_name='Miura')
        judo     = create_contact(user=self.user, first_name='Judo',     last_name='Miura')
        griffith = create_contact(user=self.user, first_name='Griffith', last_name='Miura')
        rickert  = create_contact(user=self.user, first_name='Rickert',  last_name='Miura')
        carcus   = create_contact(user=self.user, first_name='Carcus',   last_name='Miura')

        ct_id = ContentType.objects.get_for_model(Contact).id

        response = self.client.post('/events/event/%s/link_contacts' % event.id, follow=True,
                                    data= {
                                            "related_contacts": '(%s,%s,%s);(%s,%s,%s);(%s,%s,%s);(%s,%s,%s);(%s,%s,%s);' % \
                                                (REL_OBJ_IS_INVITED_TO,  ct_id, casca.id,
                                                 REL_OBJ_CAME_EVENT,     ct_id, judo.id,
                                                 REL_OBJ_NOT_CAME_EVENT, ct_id, griffith.id,
                                                 REL_OBJ_IS_INVITED_TO,  ct_id, rickert.id,
                                                 REL_OBJ_CAME_EVENT,     ct_id, carcus.id,
                                                ),
                                          }
                                   )
        self.assertEqual(200, response.status_code)

        rel_filter = Relation.objects.filter

        self.assertEqual([REL_SUB_IS_INVITED_TO],  self.relations_types(casca, event))
        self.assertEqual([REL_SUB_CAME_EVENT],     self.relations_types(judo, event))
        self.assertEqual([REL_SUB_NOT_CAME_EVENT], self.relations_types(griffith, event))
        self.assertEqual([REL_SUB_IS_INVITED_TO],  self.relations_types(rickert, event))
        self.assertEqual([REL_SUB_CAME_EVENT],     self.relations_types(carcus, event))

        response = self.client.post('/events/event/%s/link_contacts' % event.id, follow=True,
                                    data= {
                                            "related_contacts": '(%s,%s,%s);(%s,%s,%s);(%s,%s,%s);(%s,%s,%s);(%s,%s,%s);' % \
                                                (REL_OBJ_IS_INVITED_TO,  ct_id, casca.id,
                                                 REL_OBJ_NOT_CAME_EVENT, ct_id, judo.id,
                                                 REL_OBJ_CAME_EVENT,     ct_id, griffith.id,
                                                 REL_OBJ_CAME_EVENT,     ct_id, rickert.id,
                                                 REL_OBJ_CAME_EVENT,     ct_id, carcus.id,
                                                ),
                                          }
                                   )
        self.assertEqual(200, response.status_code)

        self.assertEqual([REL_SUB_IS_INVITED_TO],  self.relations_types(casca, event))
        self.assertEqual([REL_SUB_NOT_CAME_EVENT], self.relations_types(judo, event))
        self.assertEqual([REL_SUB_CAME_EVENT],     self.relations_types(griffith, event))
        self.assertEqual(set([REL_SUB_IS_INVITED_TO, REL_SUB_CAME_EVENT]), set(self.relations_types(rickert, event)))
        self.assertEqual([REL_SUB_CAME_EVENT],     self.relations_types(carcus, event))

    def test_link_contacts03(self):
        self.login()

        event = self.create_event('Eclipse', EventType.objects.all()[0])
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')
        ct_id = ContentType.objects.get_for_model(Contact).id

        response = self.client.post('/events/event/%s/link_contacts' % event.id, follow=True,
                                    data= {
                                            "related_contacts": '(%s,%s,%s);(%s,%s,%s);' % \
                                                (REL_OBJ_IS_INVITED_TO,  ct_id, casca.id,
                                                 REL_OBJ_CAME_EVENT,     ct_id, casca.id,
                                                ),
                                          }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'related_contacts', [_(u'Contact %s is present twice.') % casca])

    #TODO: add a test for related opportunity creation