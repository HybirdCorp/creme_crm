# -*- coding: utf-8 -*-

try:
    from datetime import datetime

    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import CremeEntity

    from assistants.models import Alert
    from assistants.tests.base import AssistantsTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('AlertTestCase',)


class AlertTestCase(AssistantsTestCase):
    def _build_add_url(self, entity):
        return '/assistants/alert/add/%s/' % entity.id

    def _create_alert(self, title='TITLE', description='DESCRIPTION', trigger_date='2010-9-29', entity=None):
        entity = entity or self.entity
        response = self.client.post(self._build_add_url(entity),
                                    data={'user':         self.user.pk,
                                          'title':        title,
                                          'description':  description,
                                          'trigger_date': trigger_date,
                                         }
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Alert, title=title, description=description)

    def test_create01(self):
        self.assertFalse(Alert.objects.exists())

        entity = self.entity
        self.assertGET200(self._build_add_url(entity))

        alert = self._create_alert('Title', 'Description', '2010-9-29')
        self.assertEqual(1, Alert.objects.count())

        self.assertIs(False,        alert.is_validated)
        self.assertEqual(self.user, alert.user)

        self.assertEqual(entity.id,             alert.entity_id)
        self.assertEqual(entity.entity_type_id, alert.entity_content_type_id)
        self.assertEqual(datetime(year=2010, month=9, day=29), alert.trigger_date)

    def test_create02(self): #create with errors
        def _fail_creation(**post_data):
            response = self.client.post(self._build_add_url(self.entity), data=post_data)
            self.assertEqual(200, response.status_code)

            with self.assertNoException():
                form = response.context['form']

            self.assertFalse(form.is_valid(), 'Creation should fail with data=%s' % post_data)

        user_pk = self.user.pk
        _fail_creation(user=user_pk, title='',      description='description', trigger_date='2010-9-29')
        _fail_creation(user=user_pk, title='title', description='description', trigger_date='')

    def test_edit(self):
        title       = 'Title'
        description = 'Description'
        alert = self._create_alert(title, description, '2010-9-29')

        url = '/assistants/alert/edit/%s/' % alert.id
        self.assertEqual(200, self.client.get(url).status_code)

        title       += '_edited'
        description += '_edited'
        response = self.client.post(url, data={'user':         self.user.pk,
                                               'title':        title,
                                               'description':  description,
                                               'trigger_date': '2011-10-30',
                                               'trigger_time': '15:12:32',
                                              }
                                   )
        self.assertNoFormError(response)

        alert = self.refresh(alert)
        self.assertEqual(title,       alert.title)
        self.assertEqual(description, alert.description)

        #don't care about seconds
        self.assertEqual(datetime(year=2011, month=10, day=30, hour=15, minute=12), alert.trigger_date)

    def test_delete01(self): #delete related entity
        self._create_alert()
        self.assertEqual(1, Alert.objects.count())

        self.entity.delete()
        self.assertEqual(0, Alert.objects.count())

    def test_delete02(self): #delete
        alert = self._create_alert()
        self.assertEqual(1, Alert.objects.count())

        ct = ContentType.objects.get_for_model(Alert)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': alert.id})
        self.assertEqual(0, Alert.objects.count())

    def test_validate(self): #validate
        alert = self._create_alert()
        self.assertFalse(alert.is_validated)

        response = self.client.post('/assistants/alert/validate/%s/' % alert.id)
        self.assertEqual(302, response.status_code)

        self.assertTrue(self.refresh(alert).is_validated)

    def test_function_field01(self):
        funf = CremeEntity.function_fields.get('assistants-get_alerts')
        self.assertIsNotNone(funf)
        self.assertEqual(u'<ul></ul>', funf(self.entity).for_html())

    def test_function_field02(self):
        funf = CremeEntity.function_fields.get('assistants-get_alerts')

        self._create_alert('Alert01', 'Description01', trigger_date='2011-10-21')
        self._create_alert('Alert02', 'Description02', trigger_date='2010-10-20')

        alert3 = self._create_alert('Alert03', 'Description03', trigger_date='2010-10-3')
        alert3.is_validated = True
        alert3.save()

        with self.assertNumQueries(1):
            result = funf(self.entity)

        self.assertEqual(u'<ul><li>Alert02</li><li>Alert01</li></ul>', result.for_html())

    def test_function_field03(self): #prefetch with 'populate_entities()'
        self._create_alert('Alert01', 'Description01', trigger_date='2011-10-21')
        self._create_alert('Alert02', 'Description02', trigger_date='2010-10-20')

        entity02 = CremeEntity.objects.create(user=self.user)

        alert3 = self._create_alert('Alert03', 'Description03', trigger_date='2010-10-3', entity=entity02)
        alert3.is_validated = True
        alert3.save()

        self._create_alert('Alert04', 'Description04', trigger_date='2010-10-3', entity=entity02)

        funf = CremeEntity.function_fields.get('assistants-get_alerts')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02])

        with self.assertNumQueries(0):
            result1 = funf(self.entity)
            result2 = funf(entity02)

        self.assertEqual(u'<ul><li>Alert02</li><li>Alert01</li></ul>', result1.for_html())
        self.assertEqual(u'<ul><li>Alert04</li></ul>',                 result2.for_html())

    def test_merge(self):
        def creator(contact01, contact02):
            self._create_alert('Alert01', 'Fight against him', '2011-1-9',  contact01)
            self._create_alert('Alert02', 'Train with him',    '2011-1-10', contact02)
            self.assertEqual(2, Alert.objects.count())

        def assertor(contact01):
            alerts = Alert.objects.all()
            self.assertEqual(2, len(alerts))

            for alert in alerts:
                self.assertEqual(contact01, alert.creme_entity)

        self.aux_test_merge(creator, assertor)
