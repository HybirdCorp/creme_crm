# -*- coding: utf-8 -*-

try:
    #from datetime import datetime

    from django.core.serializers.json import simplejson
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import CremeEntity

    from creme.persons.models import Contact

    from ..models import ToDo
    from ..blocks import todos_block
    from .base import AssistantsTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('TodoTestCase',)


class TodoTestCase(AssistantsTestCase):
    def _build_add_url(self, entity):
        return '/assistants/todo/add/%s/' % entity.id

    def _build_edit_url(self, todo):
        return '/assistants/todo/edit/%s/' % todo.id

    def _create_todo(self, title='TITLE', description='DESCRIPTION', entity=None, user=None):
        entity = entity or self.entity
        user   = user or self.user

        response = self.client.post(self._build_add_url(entity),
                                    data={'user':        user.pk,
                                          'title':       title,
                                          'description': description,
                                         }
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(ToDo, title=title, description=description)

    def test_create01(self):
        self.assertFalse(ToDo.objects.exists())

        entity = self.entity
        response = self.assertGET200(self._build_add_url(entity))

        with self.assertNoException():
            hours = response.context['form'].fields['deadline_hour'].choices

        self.assertIn((0, '0h'), hours)
        self.assertIn((23, '23h'), hours)
        self.assertEqual(24, len(hours))

        title = 'Title'
        todo = self._create_todo(title, 'Description')
        self.assertEqual(1, ToDo.objects.count())
        self.assertEqual(entity.id,             todo.entity_id)
        self.assertEqual(entity.entity_type_id, todo.entity_content_type_id)
        self.assertLess((now() - todo.creation_date).seconds, 10)
        self.assertIsNone(todo.deadline)

        self.assertEqual(title, unicode(todo))

    def test_create02(self):
        "Dealine"
        url = self._build_add_url(self.entity)
        title = 'my Todo'
        data = {'user':        self.user.pk,
                'title':       title,
                'description': '',
                'deadline':    '2013-6-7',
               }
        response = self.assertPOST200(url, data=data)
        self.assertFormError(response, 'form', 'deadline_hour',
                             [_(u'The hour is required if you set a date.')]
                            )

        self.assertNoFormError(self.client.post(url, data=dict(data, deadline_hour=9)))

        todo = self.get_object_or_fail(ToDo, title=title)
        self.assertEqual(self.create_datetime(year=2013, month=6, day=7, hour=9),
                         todo.deadline
                        )

    def test_edit01(self):
        title       = 'Title'
        description = 'Description'
        todo = self._create_todo(title, description)

        url = self._build_edit_url(todo)
        self.assertGET200(url)

        title       += '_edited'
        description += '_edited'
        response = self.client.post(url, data={'user':        self.user.pk,
                                               'title':       title,
                                               'description': description,
                                              }
                                   )
        self.assertNoFormError(response)

        todo = self.refresh(todo)
        self.assertEqual(title,       todo.title)
        self.assertEqual(description, todo.description)

    def test_edit02(self):
        "Entity is deleted"
        todo = self._create_todo()

        entity = self.entity
        entity.trash()

        with self.assertNoException():
            todo = self.refresh(todo)
            entity2 = todo.creme_entity

        self.assertEqual(entity, entity2)
        self.assertGET403(self._build_edit_url(todo))

    def test_delete_related01(self):
        self._create_todo()
        self.assertEqual(1, ToDo.objects.count())

        self.entity.delete()
        self.assertEqual(0, ToDo.objects.count())

    def test_delete02(self):
        todo = self._create_todo()
        self.assertEqual(1, ToDo.objects.count())

        ct   = ContentType.objects.get_for_model(ToDo)
        self.assertPOST(302, '/creme_core/entity/delete_related/%s' % ct.id, data={'id': todo.id})
        self.assertFalse(ToDo.objects.all())

    def test_validate(self):
        todo = self._create_todo()
        self.assertFalse(todo.is_ok)

        response = self.assertPOST200('/assistants/todo/validate/%s/' % todo.id, follow=True)
        self.assertRedirects(response, self.entity.get_absolute_url())
        self.assertIs(True, self.refresh(todo).is_ok)

    def test_block_reload01(self): #detailview
        for i in xrange(1, 4):
            self._create_todo('Todo%s' % i, 'Description %s' % i)

        todos = ToDo.get_todos(self.entity)
        self.assertEqual(3, len(todos))
        self.assertEqual(set(t.id for t in ToDo.objects.all()), set(t.id for t in todos))

        self.assertGreaterEqual(todos_block.page_size, 2)

        response = self.assertGET200('/creme_core/blocks/reload/%s/%s/' % (todos_block.id_, self.entity.id))
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertEqual(1, len(content))
        self.assertEqual(2, len(content[0]))
        self.assertEqual(todos_block.id_, content[0][0])

        with self.assertNoException():
            page = response.context['page']

        self.assertEqual(3, len(page.object_list))
        self.assertEqual(set(todos), set(page.object_list))

    def _create_several_todos(self):
        self._create_todo('Todo01', 'Description01')

        entity02 = Contact.objects.create(user=self.user, first_name='Akane', last_name='Tendo')
        self._create_todo('Todo02', 'Description02', entity=entity02)

        user02 = User.objects.create_user('user02', 'user@creme.org', 'password02')
        self._create_todo('Todo03', 'Description03', user=user02)

    def test_block_reload02(self): #home
        self._create_several_todos()
        self.assertEqual(3, ToDo.objects.count())

        todos = ToDo.get_todos_for_home(self.user)
        self.assertEqual(2, len(todos))

        response = self.assertGET200('/creme_core/blocks/reload/home/%s/' % todos_block.id_)
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertEqual(1, len(content))
        self.assertEqual(2, len(content[0]))
        self.assertEqual(todos_block.id_, content[0][0])

        with self.assertNoException():
            page = response.context['page']

        self.assertEqual(2, len(page.object_list))
        self.assertEqual(set(todos), set(page.object_list))

    def test_block_reload03(self): #portal
        self._create_several_todos()

        ct_id = ContentType.objects.get_for_model(Contact).id
        todos = ToDo.get_todos_for_ctypes([ct_id], self.user)
        self.assertEqual(2, len(todos))

        response = self.assertGET200('/creme_core/blocks/reload/portal/%s/%s/' % (todos_block.id_, str(ct_id)))
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertEqual(1, len(content))
        self.assertEqual(2, len(content[0]))
        self.assertEqual(todos_block.id_, content[0][0])

        with self.assertNoException():
            page = response.context['page']

        self.assertEqual(2, len(page.object_list))
        self.assertEqual(set(todos), set(page.object_list))

    def _oldify_todo(self, todo, years_delta=1):
        cdate = todo.creation_date
        todo.creation_date = cdate.replace(year=cdate.year - years_delta)
        todo.save()

    def test_function_field01(self):
        funf = CremeEntity.function_fields.get('assistants-get_todos')
        self.assertIsNotNone(funf)
        self.assertEqual(u'<ul></ul>', funf(self.entity).for_html())

    def test_function_field02(self):
        funf = CremeEntity.function_fields.get('assistants-get_todos')
        self._oldify_todo(self._create_todo('Todo01', 'Description01'))
        self._create_todo('Todo02', 'Description02')

        todo3 = self._create_todo('Todo03', 'Description03')
        todo3.is_ok = True
        todo3.save()

        with self.assertNumQueries(1):
            result = funf(self.entity)

        self.assertEqual(u'<ul><li>Todo02</li><li>Todo01</li></ul>', result.for_html())

        # limit to 3 ToDos
        #self._create_todo('Todo03', 'Description03')
        #self._create_todo('Todo04', 'Description04')
        #self.assertEqual(u'<ul><li>Todo04</li><li>Todo03</li><li>Todo02</li></ul>', funf(self.entity))

    def test_function_field03(self):
        "Prefetch with 'populate_entities()'"
        self._oldify_todo(self._create_todo('Todo01', 'Description01'))
        self._create_todo('Todo02', 'Description02')

        todo3 = self._create_todo('Todo03', 'Description03')
        todo3.is_ok = True
        todo3.save()

        entity02 = CremeEntity.objects.create(user=self.user)
        self._create_todo('Todo04', 'Description04', entity=entity02)

        funf = CremeEntity.function_fields.get('assistants-get_todos')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02])

        with self.assertNumQueries(0):
            result1 = funf(self.entity)
            result2 = funf(entity02)

        self.assertEqual(u'<ul><li>Todo02</li><li>Todo01</li></ul>', result1.for_html())
        self.assertEqual(u'<ul><li>Todo04</li></ul>',                result2.for_html())

    def test_merge(self):
        def creator(contact01, contact02):
            self._create_todo('Todo01', 'Fight against him', contact01)
            self._create_todo('Todo02', 'Train with him',    contact02)
            self.assertEqual(2, ToDo.objects.count())

        def assertor(contact01):
            todos = ToDo.objects.all()
            self.assertEqual(2, len(todos))

            for todo in todos:
                self.assertEqual(contact01, todo.creme_entity)

        self.aux_test_merge(creator, assertor)
