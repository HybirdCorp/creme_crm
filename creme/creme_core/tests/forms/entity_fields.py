# -*- coding: utf-8 -*-

#try:
    #from functools import partial

    #from django.db.models import Max

    #from .base import FieldTestCase
    #from creme.creme_core.forms.fields import _EntityField, CremeEntityField, MultiCremeEntityField
    #from creme.creme_core.models import CremeEntity

    #from creme.persons.models import Contact
#except Exception as e:
    #print('Error in <%s>: %s' % (__name__, e))


#class EntityFieldTestCase(FieldTestCase):
    #def test_empty01(self):
        #self.assertFieldValidationError(_EntityField, 'required', _EntityField().clean, None)

    #def test_properties(self):
        #field = _EntityField()
        #field.model = Contact
        #self.assertEqual(Contact, field.widget.model)

        #field.o2m = True
        #self.assertEqual(1, field.widget.o2m)

    #def test_invalid_choice01(self):
        #self.assertFieldValidationError(_EntityField, 'invalid_choice',
                                        #_EntityField().clean, [''],
                                        #message_args={'value': ['']},
                                       #)

    #def test_ok01(self):
        #self.assertEqual([1, 2], _EntityField().clean([u'1', u'2']))


#class CremeEntityFieldTestCase(FieldTestCase):
    #def test_empty01(self):
        #self.assertFieldValidationError(CremeEntityField, 'required', CremeEntityField().clean, None)

    #def test_empty02(self):
        #self.assertFieldValidationError(CremeEntityField, 'required', CremeEntityField().clean, [])

    #def test_invalid_choice01(self):
        #self.assertFieldValidationError(CremeEntityField, 'invalid_choice',
                                        #CremeEntityField().clean, [''],
                                        #message_args={'value': ['']}
                                       #)

    #def test_doesnotexist01(self):
        #self.assertFieldValidationError(CremeEntityField, 'doesnotexist',
                                        #CremeEntityField().clean, ['1024'],
                                        #message_args={'value': ['1024']},
                                       #)

    #def test_ok01(self):
        #self.login()
        #ce = CremeEntity.objects.create(user=self.user)
        #self.assertEqual(ce, CremeEntityField().clean([ce.id]))

    #def test_ok02(self):
        #self.login()
        #CremeEntity.objects.create(user=self.user)
        #self.assertIsNone(CremeEntityField(required=False).clean([]))

    #def test_ok03(self):
        #self.login()
        #CremeEntity.objects.create(user=self.user)
        #self.assertIsNone(CremeEntityField(required=False).clean(None))

    #def test_q_filter01(self):
        #self.login()

        #create_entity = partial(CremeEntity.objects.create, user=self.user)
        #ce1 = create_entity()
        #ce2 = create_entity()
        #ce3 = create_entity(is_deleted=True)

        #clean = CremeEntityField(q_filter={'~pk': ce1.id}).clean
        #self.assertFieldValidationError(CremeEntityField, 'doesnotexist', clean,
                                        #[ce1.id], message_args={'value': [ce1.id]}
                                       #)
        #self.assertEqual(ce2, clean([ce2.id]))
        #self.assertFieldValidationError(CremeEntityField, 'doesnotexist', clean,
                                        #[ce3.id], message_args={'value': [ce3.id]}
                                       #)

    #def test_q_filter02(self):
        #"'q_filter' property"
        #self.login()
        #ce = CremeEntity.objects.create(user=self.user)
        #field = CremeEntityField()
        #field.q_filter = {'~pk': ce.id}

        #self.assertFieldValidationError(CremeEntityField, 'doesnotexist', field.clean,
                                        #[ce.id], message_args={'value': [ce.id]}
                                       #)


#class MultiCremeEntityFieldTestCase(FieldTestCase):
    #def test_empty01(self):
        #self.assertFieldValidationError(MultiCremeEntityField, 'required',
                                        #MultiCremeEntityField().clean, None
                                       #)

    #def test_empty02(self):
        #self.assertFieldValidationError(MultiCremeEntityField, 'required',
                                        #MultiCremeEntityField().clean, []
                                       #)

    #def test_invalid_choice01(self):
        #self.assertFieldValidationError(MultiCremeEntityField, 'invalid_choice',
                                        #MultiCremeEntityField().clean, [''],
                                        #message_args={'value': ['']}
                                       #)

    #def test_invalid_choice02(self):
        #max_id = CremeEntity.objects.aggregate(Max('id'))['id__max'] or 0
        #ids = (max_id + 1, max_id + 2)

        #self.assertFieldValidationError(MultiCremeEntityField, 'invalid_choice',
                                        #MultiCremeEntityField().clean, [str(ids[0])],
                                        #message_args={'value': ids[0]},
                                       #)
        #self.assertFieldValidationError(MultiCremeEntityField, 'invalid_choice',
                                        #MultiCremeEntityField().clean, [str(i) for i in ids],
                                        #message_args={'value': '%s, %s' % ids},
                                       #)

    #def test_ok01(self):
        #self.login()

        #create_entity = partial(CremeEntity.objects.create, user=self.user)
        #ce1 = create_entity()
        #create_entity()

        #self.assertEqual([ce1], MultiCremeEntityField().clean([ce1.id]))

    #def test_ok02(self):
        #self.login()

        #create_entity = partial(CremeEntity.objects.create, user=self.user)
        #ce1 = create_entity()
        #ce2 = create_entity()

        #self.assertEqual(set([ce1, ce2]),
                         #set(MultiCremeEntityField().clean([ce1.id, ce2.id]))
                        #)

    #def test_ok03(self):
        #self.login()
        #self.assertEqual([], MultiCremeEntityField(required=False).clean([]))

    #def test_q_filter01(self):
        #self.login()

        #create_entity = partial(CremeEntity.objects.create, user=self.user)
        #ce1, ce2, ce3, ce4 = (create_entity() for i in xrange(4))
        #ce5 = create_entity(is_deleted=True)

        #field = MultiCremeEntityField(q_filter={'~pk__in': [ce1.id, ce2.id]})
        #self.assertFieldValidationError(MultiCremeEntityField, 'invalid_choice',
                                        #field.clean, [ce1.id, ce2.id],
                                        #message_args={'value': '%s, %s' % (ce1.id, ce2.id)},
                                       #)
        #self.assertEqual(set([ce3, ce4]),
                         #set(MultiCremeEntityField().clean([ce3.id, ce4.id]))
                        #)
        #self.assertFieldValidationError(MultiCremeEntityField, 'invalid_choice',
                                        #field.clean, [ce5.id],
                                        #message_args={'value': ce5.id},
                                       #)

    #def test_q_filter02(self):
        #"'q_filter' property"
        #self.login()

        #create_entity = partial(CremeEntity.objects.create, user=self.user)
        #ce1 = create_entity()
        #ce2 = create_entity()

        #field = MultiCremeEntityField()
        #field.q_filter={'~pk__in': [ce1.id, ce2.id]}

        #self.assertFieldValidationError(MultiCremeEntityField, 'invalid_choice',
                                        #field.clean, [ce1.id, ce2.id],
                                        #message_args={'value': '%s, %s' % (ce1.id, ce2.id)}
                                       #)
