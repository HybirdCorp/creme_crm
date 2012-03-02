# -*- coding: utf-8 -*-

try:
    from creme_core.forms.fields import _EntityField, CremeEntityField, MultiCremeEntityField
    from creme_core.models import CremeEntity
    from creme_core.tests.forms.base import FieldTestCase

    from persons.models import Contact
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class EntityFieldTestCase(FieldTestCase):
    def test_empty01(self):
        self.assertFieldValidationError(_EntityField, 'required', _EntityField().clean, None)

    def test_properties(self):
        field = _EntityField()
        field.model = Contact
        self.assertEqual(Contact, field.widget.model)

        field.o2m = True
        self.assertEqual(1, field.widget.o2m)

    def test_invalid_choice01(self):
        self.assertFieldValidationError(_EntityField, 'invalid_choice',
                                        _EntityField().clean, [u''],
                                        message_args={"value": [u'']}
                                       )

    def test_ok01(self):
        self.assertEqual([1, 2], _EntityField().clean([u'1', u'2']))


class CremeEntityFieldTestCase(FieldTestCase):
    def test_empty01(self):
        self.assertFieldValidationError(CremeEntityField, 'required', CremeEntityField().clean, None)

    def test_empty02(self):
        self.assertFieldValidationError(CremeEntityField, 'required', CremeEntityField().clean, [])

    def test_invalid_choice01(self):
        self.assertFieldValidationError(CremeEntityField, 'invalid_choice',
                                        CremeEntityField().clean, [u''],
                                        message_args={"value": [u'']}
                                       )

    def test_doesnotexist01(self):
        field = CremeEntityField()
        self.assertFieldValidationError(CremeEntityField, 'doesnotexist', field.clean, [u'2'], message_args={"value":[u'2']})

    def test_ok01(self):
        self.login()
        field = CremeEntityField()
        ce = CremeEntity.objects.create(user=self.user)
        self.assertEqual(ce, field.clean([ce.id]))

    def test_ok02(self):
        self.login()
        field = CremeEntityField(required=False)
        ce = CremeEntity.objects.create(user=self.user)
        self.assertEqual(None, field.clean([]))

    def test_ok03(self):
        self.login()
        field = CremeEntityField(required=False)
        ce = CremeEntity.objects.create(user=self.user)
        self.assertEqual(None, field.clean(None))

    def test_q_filter01(self):
        self.login()
        ce = CremeEntity.objects.create(user=self.user)
        field = CremeEntityField(q_filter={'~pk': ce.id})

        self.assertFieldValidationError(CremeEntityField, 'doesnotexist', field.clean,
                                        [ce.id], message_args={"value": [ce.id]}
                                       )

    def test_q_filter02(self):
        self.login()
        ce = CremeEntity.objects.create(user=self.user)
        field = CremeEntityField()
        field.q_filter={'~pk': ce.id}

        self.assertFieldValidationError(CremeEntityField, 'doesnotexist', field.clean,
                                        [ce.id], message_args={"value": [ce.id]}
                                       )


class MultiCremeEntityFieldTestCase(FieldTestCase):
    def test_empty01(self):
        self.assertFieldValidationError(MultiCremeEntityField, 'required', MultiCremeEntityField().clean, None)

    def test_empty02(self):
        self.assertFieldValidationError(MultiCremeEntityField, 'required',
                                        MultiCremeEntityField().clean, []
                                       )

    def test_invalid_choice01(self):
        self.assertFieldValidationError(MultiCremeEntityField, 'invalid_choice',
                                        MultiCremeEntityField().clean, [u''],
                                        message_args={"value": [u'']}
                                       )

    def test_invalid_choice02(self):
        last_entities = CremeEntity.objects.order_by('-id')[:1]
        max_id = last_entities[0].id + 1 if last_entities else 1
        ids = (max_id, max_id + 1)
        self.assertFieldValidationError(MultiCremeEntityField, 'invalid_choice',
                                        MultiCremeEntityField().clean, [str(i) for i in ids],
                                        message_args={"value": '%s, %s' % ids}
                                       )

    def test_ok01(self):
        self.login()
        field = MultiCremeEntityField()
        ce1 = CremeEntity.objects.create(user=self.user)
        ce2 = CremeEntity.objects.create(user=self.user)
        self.assertEqual(set([ce1, ce2]), set(field.clean([ce1.id, ce2.id])))

    def test_ok02(self):
        self.login()
        self.assertEqual([], MultiCremeEntityField(required=False).clean([]))

    def test_q_filter01(self):
        self.login()
        ce1 = CremeEntity.objects.create(user=self.user)
        ce2 = CremeEntity.objects.create(user=self.user)
        field = MultiCremeEntityField(q_filter={'~pk__in': [ce1.id, ce2.id]})

        self.assertFieldValidationError(MultiCremeEntityField, 'invalid_choice',
                                        field.clean, [ce1.id, ce2.id],
                                        message_args={"value": '%s, %s' % (ce1.id, ce2.id)}
                                       )

    def test_q_filter02(self):
        self.login()
        ce1 = CremeEntity.objects.create(user=self.user)
        ce2 = CremeEntity.objects.create(user=self.user)
        field = MultiCremeEntityField()
        field.q_filter={'~pk__in': [ce1.id, ce2.id]}

        self.assertFieldValidationError(MultiCremeEntityField, 'invalid_choice',
                                        field.clean, [ce1.id, ce2.id],
                                        message_args={"value": '%s, %s' % (ce1.id, ce2.id)}
                                       )
