# -*- coding: utf-8 -*-

try:
    from django.core.exceptions import ValidationError
    from django.utils.simplejson import loads as jsonloads
    from django.contrib.contenttypes.models import ContentType

    from creme_core.forms.entity_filter import *
    from creme_core.models import CremePropertyType, RelationType
    from creme_core.tests.forms.base import FieldTestCase

    from persons.models import Organisation, Contact
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('RegularFieldsConditionsFieldTestCase', 'DateFieldsConditionsFieldTestCase',
           'CustomFieldsConditionsFieldTestCase', 'DateCustomFieldsConditionsFieldTestCase',
           'PropertiesConditionsFieldTestCase', 'RelationsConditionsFieldTestCase',
           'RelationSubfiltersConditionsFieldTestCase',
          )


class RegularFieldsConditionsFieldTestCase(FieldTestCase):
    def test_clean_empty_required(self):
        clean = RegularFieldsConditionsField(required=True).clean
        self.assertFieldValidationError(RegularFieldsConditionsField, 'required', clean, None)
        self.assertFieldValidationError(RegularFieldsConditionsField, 'required', clean, "")
        self.assertFieldValidationError(RegularFieldsConditionsField, 'required', clean, "[]")

    def test_clean_empty_not_required(self):
        field = RegularFieldsConditionsField(required=False)

        with self.assertNoException():
            value = field.clean(None)

        self.assertEqual([], value)

    def test_clean_invalid_data_type(self):
        clean = RegularFieldsConditionsField().clean
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidformat', clean, '"this is a string"')
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidformat', clean, '"{}"')
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidformat', clean, '{"foobar":{"operator":"3","name":"first_name","value":"Rei"}}')
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidformat', clean, '1')

    def test_clean_invalid_data(self):
        clean = RegularFieldsConditionsField(model=Contact).clean
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidformat', clean,
                                        '[{"operator": "notanumber", "name": "first_name", "value": "Rei"}]'
                                       )

    def test_clean_incomplete_data_required(self):
        clean = RegularFieldsConditionsField(model=Contact).clean
        EQUALS = EntityFilterCondition.EQUALS
        self.assertFieldValidationError(RegularFieldsConditionsField, 'required', clean, '[{"operator": "%s", "name": "first_name"}]' % EQUALS)
        self.assertFieldValidationError(RegularFieldsConditionsField, 'required', clean, '[{"operator": "%s", "value": {"type":"%s", "value":"Rei"}}]' % (EQUALS, EQUALS))
        self.assertFieldValidationError(RegularFieldsConditionsField, 'required', clean, '[{"name": "first_name", "value": "Rei"}]')

    def test_clean_invalid_field(self):
        clean = RegularFieldsConditionsField(model=Contact).clean
        format_str = '[{"name": "%(name)s", "operator": "%(operator)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]'

        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        format_str % {'operator':  EntityFilterCondition.EQUALS,
                                                      'name':  '   boobies_size', #<---
                                                      'value':     '90',
                                                     }
                                        )
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        format_str % {'operator': EntityFilterCondition.IEQUALS,
                                                      'name':     'is_deleted',
                                                      'value':    'Faye',
                                                     }
                                        )
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        format_str % {'operator': EntityFilterCondition.IEQUALS,
                                                      'name':     'created',
                                                      'value':    '2011-5-12',
                                                     }
                                        )
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        format_str % {'operator': EntityFilterCondition.IEQUALS,
                                                      'name':     'civility__id',
                                                      'value':    '5',
                                                     }
                                        )
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        format_str % {'operator': EntityFilterCondition.IEQUALS,
                                                      'name':     'image__id',
                                                      'value':    '5',
                                                     }
                                       )
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        format_str % {'operator': EntityFilterCondition.IEQUALS,
                                                      'name':     'image__is_deleted',
                                                      'value':    '5',
                                                     }
                                       )
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        format_str % {'operator': EntityFilterCondition.IEQUALS,
                                                      'name':     'image__modified',
                                                      'value':    '2011-5-12',
                                                     }
                                       )
        #TODO: M2M

    def test_clean_invalid_operator(self):
        clean = RegularFieldsConditionsField(model=Contact).clean
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidoperator', clean,
                                        '[{"name": "%(name)s", "operator": "%(operator)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]' % {
                                                'operator': EntityFilterCondition.EQUALS + 1000, # <--
                                                'name':     'first_name',
                                                'value':    'Nana',
                                             }
                                       )

    def test_ok01(self):
        clean = RegularFieldsConditionsField(model=Contact).clean
        operator = EntityFilterCondition.IEQUALS
        name = 'first_name'
        value = 'Faye'
        conditions = clean('[{"name": "%(name)s", "operator": "%(operator)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]' % {
                                 'operator': operator,
                                 'name':     name,
                                 'value':    value,
                             }
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(name,                                      condition.name)
        self.assertEqual({'operator': operator, 'values': [value]}, condition.decoded_value)

    def test_ok02(self): #ISEMPTY -> boolean
        clean = RegularFieldsConditionsField(model=Contact).clean
        operator = EntityFilterCondition.ISEMPTY
        name = 'description'
        conditions = clean('[{"name": "%(name)s", "operator": "%(operator)s", "value": {"type": "%(operator)s", "value": false}}]' % {
                                 'operator': operator,
                                 'name':     name,
                             }
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(name,                                      condition.name)
        self.assertEqual({'operator': operator, 'values': [False]}, condition.decoded_value)

    def test_ok03(self): #FK field
        clean = RegularFieldsConditionsField(model=Contact).clean
        operator = EntityFilterCondition.ISTARTSWITH
        name = 'civility__title'
        value = 'Miss'
        conditions = clean('[{"name": "%(name)s", "operator": "%(operator)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]' % {
                                 'operator': operator,
                                 'name':     name,
                                 'value':    value,
                             }
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(name,                                      condition.name)
        self.assertEqual({'operator': operator, 'values': [value]}, condition.decoded_value)

    def test_ok04(self): #multivalues
        clean = RegularFieldsConditionsField(model=Contact).clean
        operator = EntityFilterCondition.IENDSWITH
        name = 'last_name'
        values = ['nagi', 'sume']
        conditions = clean('[{"name": "%(name)s", "operator": "%(operator)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]' % {
                                 'operator': operator,
                                 'name':     name,
                                 'value':    ','.join(values) + ',',
                             }
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,          condition.type)
        self.assertEqual(name,                                     condition.name)
        self.assertEqual({'operator': operator, 'values': values}, condition.decoded_value)

    def test_ok05(self): #M2M field
        clean = RegularFieldsConditionsField(model=Contact).clean
        operator = EntityFilterCondition.IEQUALS
        name = 'language__name'
        value = 'French'
        conditions = clean('[{"name": "%(name)s", "operator": "%(operator)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]' % {
                                 'operator': operator,
                                 'name':     name,
                                 'value':    value,
                             }
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(name,                                      condition.name)
        self.assertEqual({'operator': operator, 'values': [value]}, condition.decoded_value)


class DateFieldsConditionsFieldTestCase(FieldTestCase):
    def test_clean_invalid_data(self):
        clean = DateFieldsConditionsField(model=Contact).clean
        self.assertFieldValidationError(DateFieldsConditionsField, 'invalidfield', clean,
                                        '[{"field": "first_name", "range": {"type": "next_quarter", "start": "2011-5-12"}}]'
                                       )
        self.assertFieldValidationError(DateFieldsConditionsField, 'invalidformat', clean,
                                        '[{"field": "birthday", "range":"not a dict"}]'
                                       )
        self.assertFieldValidationError(DateFieldsConditionsField, 'invaliddaterange', clean,
                                       '[{"field": "birthday", "range": {"type":"unknow_range"}}]' #TODO: "start": '' ???
                                       )

        self.assertFieldValidationError(DateFieldsConditionsField, 'emptydates', clean,
                                       '[{"field": "birthday", "range": {"type":""}}]'
                                       )
        self.assertFieldValidationError(DateFieldsConditionsField, 'emptydates', clean,
                                       '[{"field": "birthday", "range": {"type":"", "start": "", "end": ""}}]'
                                       )

        try:   clean('[{"field": "created", "range": {"type": "", "start": "not a date"}}]')
        except ValidationError: pass
        else:  self.fail('No ValidationError')

        try:   clean('[{"field": "created", "range": {"type": "", "end": "2011-2-30"}}]') #30 february !!
        except ValidationError: pass
        else:  self.fail('No ValidationError')

    def test_ok01(self):
        field = DateFieldsConditionsField(model=Contact)
        type01 = 'current_year'
        name01 = 'created'
        type02 = 'next_quarter'
        name02 = 'birthday'
        conditions = field.clean('[{"field": "%(name01)s", "range": {"type": "%(type01)s"}},'
                                 ' {"field": "%(name02)s", "range": {"type": "%(type02)s"}}]' % {
                                        'type01': type01,
                                        'name01': name01,
                                        'type02': type02,
                                        'name02': name02,
                                    }
                                )
        self.assertEqual(2, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual(name01,                              condition.name)
        self.assertEqual({'name': type01},                    condition.decoded_value)

        condition = conditions[1]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual(name02,                              condition.name)
        self.assertEqual({'name': type02},                    condition.decoded_value)

    def test_ok02(self): #start/end
        field = DateFieldsConditionsField(model=Contact)
        name01 = 'created'
        name02 = 'birthday'
        conditions = field.clean('[{"field": "%(name01)s", "range": {"type": "", "start": "2011-5-12"}},'
                                 ' {"field": "%(name02)s", "range": {"type": "", "end": "2012-6-13"}}]' % {
                                        'name01': name01,
                                        'name02': name02,
                                    }
                                )
        self.assertEqual(2, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD,              condition.type)
        self.assertEqual(name01,                                           condition.name)
        self.assertEqual({'start': {'year': 2011, 'month': 5, 'day': 12}}, condition.decoded_value)

        condition = conditions[1]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD,            condition.type)
        self.assertEqual(name02,                                         condition.name)
        self.assertEqual({'end': {'year': 2012, 'month': 6, 'day': 13}}, condition.decoded_value)

    def test_ok03(self): #start + end
        clean = DateFieldsConditionsField(model=Contact).clean
        name = 'modified'
        conditions = clean('[{"field": "%s", "range": {"type": "", "start": "2010-3-24", "end": "2011-7-25"}}]' % name)
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual(name,                                condition.name)
        self.assertEqual({'start': {'year': 2010, 'month': 3, 'day': 24}, 'end': {'year': 2011, 'month': 7, 'day': 25}},
                         condition.decoded_value
                        )


class CustomFieldsConditionsFieldTestCase(FieldTestCase):
    def setUp(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.custom_field = CustomField.objects.create(name='Size', content_type=ct, field_type=CustomField.INT)

    def test_clean_invalid_data(self):
        field = CustomFieldsConditionsField(model=Contact)
        self.assertFieldValidationError(CustomFieldsConditionsField, 'invalidcustomfield', field.clean,
                                        '[{"field": "2054", "operator": "%(operator)s", "value":"170"}]' % {
                                                'operator': EntityFilterCondition.EQUALS,
                                            }
                                       )
        self.assertFieldValidationError(CustomFieldsConditionsField, 'invalidtype', field.clean,
                                        '[{"field": "%(cfield)s", "operator": "121266", "value":"170"}]' % {
                                                'cfield': self.custom_field.id,
                                            }
                                       )

    def test_ok(self):
        clean = CustomFieldsConditionsField(model=Contact).clean
        operator = EntityFilterCondition.EQUALS
        value = 180
        conditions = clean('[{"field":"%(cfield)s", "operator": "%(operator)s", "value":"%(value)s"}]' % {
                                'cfield':   self.custom_field.id,
                                'operator': operator,
                                'value':    value,
                              }
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(self.custom_field.id),             condition.name)
        self.assertEqual({'operator': operator, 'rname': 'customfieldinteger', 'value': unicode(value)},
                         condition.decoded_value
                        )


class DateCustomFieldsConditionsFieldTestCase(FieldTestCase):
    def setUp(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.cfield01 = CustomField.objects.create(name='Day', content_type=ct, field_type=CustomField.DATE)
        self.cfield02 = CustomField.objects.create(name='First flight', content_type=ct, field_type=CustomField.DATE)

    def test_clean_invalid_data(self):
        clean = DateCustomFieldsConditionsField(model=Contact).clean

        self.assertFieldValidationError(DateCustomFieldsConditionsField, 'invalidcustomfield', clean,
                                        '[{"field": "2054", "range": {"type": "current_year"}}]'
                                       )
        self.assertFieldValidationError(DateCustomFieldsConditionsField, 'invalidformat', clean,
                                        '[{"field": "%s", "range": "not a dict"}]' % self.cfield01.id
                                       )
        self.assertFieldValidationError(DateCustomFieldsConditionsField, 'invaliddaterange', clean,
                                       '[{"field": "%s", "range": {"type":"unknow_range"}}]' % self.cfield01.id
                                       )
        self.assertFieldValidationError(DateCustomFieldsConditionsField, 'emptydates', clean,
                                       '[{"field": "%s", "range": {"type":""}}]' % self.cfield01.id
                                       )
        self.assertFieldValidationError(DateCustomFieldsConditionsField, 'emptydates', clean,
                                       '[{"field": "%s", "range": {"type":"", "start": "", "end": ""}}]' % self.cfield01.id
                                       )

    def test_ok01(self):
        field = DateCustomFieldsConditionsField(model=Contact)
        rtype  = 'current_year'
        conditions = field.clean('[{"field": "%(cfield01)s", "range": {"type": "%(type)s"}},'
                                 ' {"field": "%(cfield02)s", "range": {"type": "", "start": "2011-5-12"}},'
                                 ' {"field": "%(cfield01)s", "range": {"type": "", "end": "2012-6-13"}},'
                                 ' {"field": "%(cfield02)s", "range": {"type": "", "start": "2011-5-12", "end": "2012-6-13"}}]' % {
                                        'type':     rtype,
                                        'cfield01': self.cfield01.id,
                                        'cfield02': self.cfield02.id,
                                    }
                                )
        self.assertEqual(4, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_DATECUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield01.id),                     condition.name)
        self.assertEqual({'rname': 'customfielddatetime', 'name': rtype}, condition.decoded_value)

        condition = conditions[1]
        self.assertEqual(EntityFilterCondition.EFC_DATECUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield02.id),                     condition.name)
        self.assertEqual({'rname': 'customfielddatetime', 'start': {'year': 2011, 'month': 5, 'day': 12}},
                         condition.decoded_value
                        )

        condition = conditions[2]
        self.assertEqual(EntityFilterCondition.EFC_DATECUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield01.id),                     condition.name)
        self.assertEqual({'rname': 'customfielddatetime', 'end': {'year': 2012, 'month': 6, 'day': 13}},
                         condition.decoded_value
                        )

        condition = conditions[3]
        self.assertEqual(EntityFilterCondition.EFC_DATECUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield02.id),                     condition.name)
        self.assertEqual({'rname': 'customfielddatetime',
                          'start': {'year': 2011, 'month': 5, 'day': 12},
                          'end':   {'year': 2012, 'month': 6, 'day': 13},
                         },
                         condition.decoded_value
                        )


class PropertiesConditionsFieldTestCase(FieldTestCase):
    def setUp(self):
        self.ptype01 = CremePropertyType.create('test-prop_active', 'Is active')
        self.ptype02 = CremePropertyType.create('test-prop_cute',   'Is cute', (Contact,))
        self.ptype03 = CremePropertyType.create('test-prop_evil',   'Is evil', (Organisation,))

    def test_clean_empty_required(self):
        clean = PropertiesConditionsField(required=True).clean
        self.assertFieldValidationError(PropertiesConditionsField, 'required', clean, None)
        self.assertFieldValidationError(PropertiesConditionsField, 'required', clean, "")
        self.assertFieldValidationError(PropertiesConditionsField, 'required', clean, "[]")

    def test_clean_empty_not_required(self):
        #try:
        with self.assertNoException():
            PropertiesConditionsField(required=False).clean(None)
        #except Exception, e:
            #self.fail(str(e))

    def test_clean_invalid_data_type(self):
        clean = PropertiesConditionsField(model=Contact).clean
        self.assertFieldValidationError(PropertiesConditionsField, 'invalidformat', clean, '"this is a string"')
        self.assertFieldValidationError(PropertiesConditionsField, 'invalidformat', clean, '"{}"')
        self.assertFieldValidationError(PropertiesConditionsField, 'invalidformat', clean, '{"foobar":{"ptype":"test-foobar","has":"true"}}')

#    def test_clean_invalid_data(self):
#        clean = PropertiesConditionsField(model=Contact).clean
#        self.assertFieldValidationError(PropertiesConditionsField, 'invalidformat', clean, '[{"ptype":"%s"}]' % self.ptype01.id)
#        self.assertFieldValidationError(PropertiesConditionsField, 'invalidformat', clean, '[{"has":"true"}]')
        #self.assertFieldValidationError(PropertiesConditionsField, 'invalidformat', clean, '[{"ptype":"%s","has":"not a boolean"}]' % self.ptype02.id)

    def test_clean_incomplete_data_required(self):
        clean = PropertiesConditionsField(model=Contact).clean
        self.assertFieldValidationError(PropertiesConditionsField, 'required', clean, '[{"ptype":"%s"}]' % self.ptype01.id)
        self.assertFieldValidationError(PropertiesConditionsField, 'required', clean, '[{"has":"true"}]')

    def test_unknown_ptype(self):
        self.assertFieldValidationError(PropertiesConditionsField, 'invalidptype',
                                        PropertiesConditionsField(model=Contact).clean,
                                        '[{"ptype":"%s","has":"true"}]' % self.ptype03.id
                                       )

    def test_ok(self):
        field = PropertiesConditionsField(model=Contact)
        conditions = field.clean('[{"ptype": "%s", "has": true}, {"ptype": "%s", "has": false}]' % (self.ptype01.id, self.ptype02.id))
        self.assertEqual(2, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_PROPERTY, condition.type)
        self.assertEqual(self.ptype01.id,                    condition.name)
        self.assertIs(condition.decoded_value, True)

        condition = conditions[1]
        self.assertEqual(EntityFilterCondition.EFC_PROPERTY, condition.type)
        self.assertEqual(self.ptype02.id,                    condition.name)
        self.assertIs(condition.decoded_value, False)


class RelationsConditionsFieldTestCase(FieldTestCase):
    def setUp(self):
        create = RelationType.create
        self.rtype01, self.rtype02 = create(('test-subject_love', u'Is loving', (Contact,)),
                                            ('test-object_love',  u'Is loved by')
                                           )
        self.rtype03, self.srtype04 = create(('test-subject_belong', u'(orga) belongs to (orga)', (Organisation,)),
                                             ('test-object_belong',  u'(orga) has (orga)',        (Organisation,))
                                            )

    def test_clean_empty_required(self):
        clean = RelationsConditionsField(required=True).clean
        self.assertFieldValidationError(RelationsConditionsField, 'required', clean, None)
        self.assertFieldValidationError(RelationsConditionsField, 'required', clean, "")
        self.assertFieldValidationError(RelationsConditionsField, 'required', clean, "[]")

    def test_clean_empty_not_required(self):
        #try:
        with self.assertNoException():
            RelationsConditionsField(required=False).clean(None)
        #except Exception, e:
            #self.fail(str(e))

    def test_clean_invalid_data_type(self):
        clean = RelationsConditionsField(model=Contact).clean
        self.assertFieldValidationError(RelationsConditionsField, 'invalidformat', clean, '"this is a string"')
        self.assertFieldValidationError(RelationsConditionsField, 'invalidformat', clean, '"{}"')
        self.assertFieldValidationError(RelationsConditionsField, 'invalidformat', clean, '{"foobar":{"rtype":"test-foobar","has":"true"}}')

    def test_clean_invalid_data(self):
        clean = RelationsConditionsField(model=Contact).clean
        ct = ContentType.objects.get_for_model(Contact)
        self.assertFieldValidationError(RelationsConditionsField, 'invalidformat', clean, '[{"rtype":"%s","has":"true", "ctype":"not an int"}]' % self.rtype01.id)
        self.assertFieldValidationError(RelationsConditionsField, 'invalidformat', clean, '[{"rtype":"%s","has":"true", "ctype":%d, "entity":"not an int"}]' % (self.rtype01.id, ct.id))

    def test_clean_incomplete_data_required(self):
        clean = RelationsConditionsField(model=Contact).clean
        self.assertFieldValidationError(RelationsConditionsField, 'required', clean, '[{"rtype":"%s"}]' % self.rtype01.id)
        self.assertFieldValidationError(RelationsConditionsField, 'required', clean, '[{"has":"true"}]')
        self.assertFieldValidationError(RelationsConditionsField, 'required', clean, '[{"rtype":"%s","has":"not a boolean"}]' % self.rtype01.id)

    def test_unknown_ct(self):
        clean = RelationsConditionsField(model=Contact).clean
        self.assertFieldValidationError(RelationsConditionsField, 'invalidct', clean, '[{"rtype":"%s","has":"true", "ctype":"2121545"}]' % self.rtype01.id)

    def test_unknown_entity(self):
        clean = RelationsConditionsField(model=Contact).clean
        self.assertFieldValidationError(RelationsConditionsField, 'invalidentity', clean,
                                        '[{"rtype":"%s","has":"true","ctype":"1","entity":"2121545"}]' % self.rtype01.id
                                       )

    def test_ok01(self): #no ct, no object entity
        field = RelationsConditionsField(model=Contact)
        conditions = field.clean('[{"rtype":"%s", "has": true, "ctype": "0", "entity": null},'
                                 ' {"rtype": "%s", "has": false, "ctype": "0", "entity": null}]' % (
                                    self.rtype01.id, self.rtype02.id)
                                )
        self.assertEqual(2, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_RELATION, condition.type)
        self.assertEqual(self.rtype01.id,                    condition.name)
        self.assertEqual({'has': True},                      condition.decoded_value)

        condition = conditions[1]
        self.assertEqual(EntityFilterCondition.EFC_RELATION, condition.type)
        self.assertEqual(self.rtype02.id,                    condition.name)
        self.assertEqual({'has': False},                     condition.decoded_value)

    def test_ok02(self): #wanted ct
        field = RelationsConditionsField(model=Contact)
        ct = ContentType.objects.get_for_model(Contact)
        conditions = field.clean('[{"rtype": "%(rtype01)s", "has": true,  "ctype": "%(ct)s", "entity": null},'
                                 ' {"rtype": "%(rtype02)s", "has": false, "ctype": "%(ct)s"}]' % {
                                        'rtype01': self.rtype01.id,
                                        'rtype02': self.rtype02.id,
                                        'ct':      ct.id,
                                    }
                                )
        self.assertEqual(2, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_RELATION, condition.type)
        self.assertEqual(self.rtype01.id,                    condition.name)
        self.assertEqual({'has': True, 'ct_id': ct.id},      condition.decoded_value)

        condition = conditions[1]
        self.assertEqual(EntityFilterCondition.EFC_RELATION, condition.type)
        self.assertEqual(self.rtype02.id,                    condition.name)
        self.assertEqual({'has': False, 'ct_id': ct.id},     condition.decoded_value)

    def test_ok03(self): #wanted entity
        self.login()

        naru = Contact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')
        field = RelationsConditionsField(model=Contact)
        ct = ContentType.objects.get_for_model(Contact)
        conditions = field.clean('[{"rtype":"%(rtype)s", "has":"true", "ctype":"%(ct)s", "entity":"%(entity)s"}]' % {
                                        'rtype':  self.rtype01.id,
                                        'ct':     ct.id,
                                        'entity': naru.id,
                                    }
                                )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_RELATION,  condition.type)
        self.assertEqual(self.rtype01.id,                     condition.name)
        self.assertEqual({'has': True, 'entity_id': naru.id}, condition.decoded_value)

    def test_ok04(self): #wanted ct + wanted entity
        self.login()

        ct = ContentType.objects.get_for_model(Contact)
        naru = Contact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')
        field = RelationsConditionsField(model=Contact)
        conditions = field.clean('[{"rtype": "%(rtype01)s", "has": true,  "ctype": "%(ct)s", "entity": null},'
                                 ' {"rtype": "%(rtype02)s", "has": false, "ctype": "%(ct)s", "entity":"%(entity)s"}]' % {
                                        'rtype01': self.rtype01.id,
                                        'rtype02': self.rtype02.id,
                                        'ct':      ct.id,
                                        'entity':  naru.id,
                                    }
                                )
        self.assertEqual(2, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_RELATION, condition.type)
        self.assertEqual(self.rtype01.id,                    condition.name)
        self.assertEqual({'has': True, 'ct_id': ct.id},      condition.decoded_value)

        condition = conditions[1]
        self.assertEqual(EntityFilterCondition.EFC_RELATION,   condition.type)
        self.assertEqual(self.rtype02.id,                      condition.name)
        self.assertEqual({'has': False, 'entity_id': naru.id}, condition.decoded_value)

    def test_ok05(self): #wanted entity is deleted
        self.login()

        naru  = Contact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')
        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=self.rtype01, has=True, entity=naru)])
        field = RelationsConditionsField(model=Contact)

        jsondict = {"entity": naru.id, "has": "true", "ctype": 0, "rtype": self.rtype01.id}
        self.assertEqual([jsondict], jsonloads(field.from_python(list(efilter.conditions.all()))))

        try:
            naru.delete()
        except Exception, e:
            self.fail('Problem with entity deletion:' + str(e))

        jsondict["entity"] = None
        self.assertEqual([jsondict], jsonloads(field.from_python(list(efilter.conditions.all()))))


class RelationSubfiltersConditionsFieldTestCase(FieldTestCase):
    def setUp(self):
        create = RelationType.create
        self.rtype01, self.rtype02 = create(('test-subject_love', u'Is loving', (Contact,)),
                                            ('test-object_love',  u'Is loved by')
                                           )
        self.rtype03, self.srtype04 = create(('test-subject_belong', u'(orga) belongs to (orga)', (Organisation,)),
                                             ('test-object_belong',  u'(orga) has (orga)',        (Organisation,))
                                            )

        self.sub_efilter01 = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        self.sub_efilter02 = EntityFilter.create(pk='test-filter02', name='Filter 02', model=Organisation)

    def test_clean_empty_required(self):
        clean = RelationsConditionsField(required=True).clean
        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'required', clean, None)
        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'required', clean, "")
        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'required', clean, "[]")

#    def test_clean_invalid_data(self):
#        clean = RelationSubfiltersConditionsField(model=Contact).clean
#        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'invalidformat', clean, '[{"rtype":"%s"}]' % self.rtype01.id)
#        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'invalidformat', clean, '[{"has":"true"}]')

    def test_clean_incomplete_data_required(self):
        clean = RelationSubfiltersConditionsField(model=Contact).clean
        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'required', clean, '[{"rtype":"%s"}]' % self.rtype01.id)
        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'required', clean, '[{"has":"true"}]')

    def test_unknown_filter(self):
        clean = RelationSubfiltersConditionsField(model=Contact).clean
        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'invalidfilter', clean,
                                        '[{"rtype": "%(rtype)s", "has": "false", "ctype": "%(ct)s", "filter":"%(filter)s"}]' % {
                                                'rtype':  self.rtype01.id,
                                                'ct':     ContentType.objects.get_for_model(Contact).id,
                                                'filter': 3213213543,
                                            }
                                       )

    def test_ok(self):
        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)
        ct_orga    = get_ct(Organisation)

        field = RelationSubfiltersConditionsField(model=Contact)
        conditions = field.clean('[{"rtype": "%(rtype01)s", "has": true,  "ctype": "%(ct_contact)s", "filter":"%(filter01)s"},'
                                 ' {"rtype": "%(rtype02)s", "has": false, "ctype": "%(ct_orga)s",    "filter":"%(filter02)s"}]' % {
                                        'rtype01':    self.rtype01.id,
                                        'rtype02':    self.rtype02.id,
                                        'ct_contact': ct_contact,
                                        'ct_orga':    ct_orga,
                                        'filter01':   self.sub_efilter01.id,
                                        'filter02':   self.sub_efilter02.id,
                                    }
                                )
        self.assertEqual(2, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_RELATION_SUBFILTER,      condition.type)
        self.assertEqual(self.rtype01.id,                                   condition.name)
        self.assertEqual({'has': True, 'filter_id': self.sub_efilter01.id}, condition.decoded_value)

        condition = conditions[1]
        self.assertEqual(EntityFilterCondition.EFC_RELATION_SUBFILTER,       condition.type)
        self.assertEqual(self.rtype02.id,                                    condition.name)
        self.assertEqual({'has': False, 'filter_id': self.sub_efilter02.id}, condition.decoded_value)
