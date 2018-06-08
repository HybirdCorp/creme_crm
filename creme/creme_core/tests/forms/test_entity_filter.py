# -*- coding: utf-8 -*-
try:
    from datetime import date
    from functools import partial
    from json import loads as json_load, dumps as json_dump

    from django.contrib.contenttypes.models import ContentType
    from django.core.exceptions import ValidationError
    from django.utils.translation import ugettext as _

    from ..fake_models import (FakeContact, FakeCivility, FakePosition,
            FakeOrganisation, FakeImage, FakeInvoice, FakeInvoiceLine)
    from .base import FieldTestCase
    from creme.creme_core.models import (RelationType, CremePropertyType,
            EntityFilter, EntityFilterCondition, FieldsConfig,
            CustomField, CustomFieldEnumValue, Language,
            CremeEntity)
    from creme.creme_core.forms.entity_filter import (FieldConditionWidget,
            RegularFieldsConditionsField, DateFieldsConditionsField,
            CustomFieldsConditionsField, CustomFieldConditionSelector,
            DateCustomFieldsConditionsField,
            PropertiesConditionsField,
            RelationsConditionsField, RelationSubfiltersConditionsField)
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class RegularFieldsConditionsFieldTestCase(FieldTestCase):
    @staticmethod
    def build_data(*conditions):
        return json_dump([
            {'field':    {'name': condition['name']},
             'operator': {'id': str(condition['operator'])},
             'value':    condition['value'],
            } for condition in conditions
        ])

    def test_clean_empty_required(self):
        clean = RegularFieldsConditionsField(required=True).clean
        self.assertFieldValidationError(RegularFieldsConditionsField, 'required', clean, None)
        self.assertFieldValidationError(RegularFieldsConditionsField, 'required', clean, '')
        self.assertFieldValidationError(RegularFieldsConditionsField, 'required', clean, '[]')

    def test_clean_empty_not_required(self):
        field = RegularFieldsConditionsField(required=False)

        with self.assertNoException():
            value = field.clean(None)

        self.assertEqual([], value)

    def test_clean_invalid_data_type(self):
        clean = RegularFieldsConditionsField().clean
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidtype', clean, '"this is a string"')
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidtype', clean, '"{}"')
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidtype', clean, '{"foobar":{"operator":"3","name":"first_name","value":"Rei"}}')
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidtype', clean, '1')

    def test_clean_invalid_data(self):
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        self.assertFieldValidationError(
                RegularFieldsConditionsField, 'invalidformat', clean,
                '[{"operator": {"id": "notanumber"}, "field": {"name":"first_name"}, "value": "Rei"}]'
        )

    def test_clean_incomplete_data_required(self):
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        EQUALS = EntityFilterCondition.EQUALS
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidvalue',    clean, '[{"operator": {"id": "%s"}, "field": {"name": "first_name"}}]' % EQUALS)
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield',    clean, '[{"operator": {"id": "%s"}, "value": "Rei"}]' % EQUALS)
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidoperator', clean, '[{"field": {"name": "first_name"}, "value": "Rei"}]')

    def test_clean_invalid_field(self):
        clean = RegularFieldsConditionsField(model=FakeContact).clean

        build_data = self.build_data
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        build_data({'operator': EntityFilterCondition.EQUALS,
                                                    'name':     '  boobies_size',  # <---
                                                    'value':    90,
                                                   },
                                       ))
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        build_data({'operator': EntityFilterCondition.IEQUALS,
                                                    'name':     'is_deleted',
                                                    'value':    '"Faye"',
                                                   },
                                       ))
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        build_data({'operator': EntityFilterCondition.IEQUALS,
                                                    'name':     'created',
                                                    'value':    '"2011-5-12"',
                                                   },
                                       ))
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        build_data({'operator': EntityFilterCondition.IEQUALS,
                                                    'name':     'civility__id',
                                                    'value':    5,
                                                   },
                                       ))
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        build_data({'operator': EntityFilterCondition.IEQUALS,
                                                    'name':     'image__id',
                                                    'value':    5,
                                                   },
                                       ))
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        build_data({'operator': EntityFilterCondition.IEQUALS,
                                                    'name':     'image__is_deleted',
                                                    'value':    5,
                                                   },
                                       ))
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidfield', clean,
                                        build_data({'operator': EntityFilterCondition.IEQUALS,
                                                    'name':     'image__modified',
                                                    'value':    "2011-5-12",
                                                   },
                                       ))
        # TODO: M2M

    def test_clean_invalid_operator(self):
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        self.assertFieldValidationError(RegularFieldsConditionsField, 'invalidoperator', clean,
                                        self.build_data({
                                                'operator': EntityFilterCondition.EQUALS + 1000,  # <--
                                                'name':     'first_name',
                                                'value':    'Nana',
                                            },
                                       ))

    def test_clean_invalid_fk_id(self):
        """FK field with invalid id"""
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        err = self.assertFieldRaises(ValidationError, clean,
                                     self.build_data({
                                             'operator': EntityFilterCondition.EQUALS,
                                             'name':     'civility',
                                             'value':    'unknown',
                                         },
                                     ))[0]
        self.assertEqual(err.messages[0],
                         unicode([_(u'Select a valid choice. That choice is not one of the available choices.')])
                        )

    def test_clean_invalid_many2many_id(self):
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        err = self.assertFieldRaises(ValidationError, clean,
                                     self.build_data({
                                             'operator': EntityFilterCondition.EQUALS,
                                             'name':     'languages',
                                             'value':    '12445',
                                         }
                                     ))[0]
        self.assertEqual(err.messages[0],
                         unicode([_('Select a valid choice. %(value)s is not one of the available choices.') % {'value': 12445}])
                        )

    def test_iequals_condition(self):
        with self.assertNumQueries(0):
            field = RegularFieldsConditionsField(model=FakeContact)

        operator = EntityFilterCondition.IEQUALS
        name = 'first_name'
        value = 'Faye'
        conditions = field.clean(self.build_data({
                                       'operator': operator,
                                       'name':     name,
                                       'value':    value,
                                   },
                                ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(name,                                      condition.name)
        self.assertEqual({'operator': operator, 'values': [value]}, condition.decoded_value)

    def test_initialize(self):
        field = RegularFieldsConditionsField()
        field.initialize(ctype=ContentType.objects.get_for_model(FakeContact))

        operator = EntityFilterCondition.IEQUALS
        name = 'first_name'
        value = 'Faye'
        conditions = field.clean(self.build_data({
                                       'operator': operator,
                                       'name':     name,
                                       'value':    value,
                                   },
                                ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(name,                                      condition.name)
        self.assertEqual({'operator': operator, 'values': [value]}, condition.decoded_value)

    def test_iequals_condition_multiple_as_string(self):
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.IEQUALS
        name = 'first_name'
        faye_name = 'Faye'
        ed_name = 'Ed'
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    '{},{}'.format(faye_name, ed_name),
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual(name,                            condition.name)
        self.assertEqual({'operator': operator, 'values': [faye_name, ed_name]},
                         condition.decoded_value
                        )

    def test_iequals_condition_multiple_as_list(self):
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.IEQUALS
        name = 'first_name'
        faye_name = 'Faye'
        ed_name = 'Ed'
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    [faye_name, ed_name],
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual(name,                            condition.name)
        self.assertEqual({'operator': operator, 'values': [faye_name, ed_name]},
                         condition.decoded_value
                        )

    def test_isempty_condition(self):
        "ISEMPTY (true) -> boolean"
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.ISEMPTY
        name = 'description'
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    True,
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,          condition.type)
        self.assertEqual(name,                                     condition.name)
        self.assertEqual({'operator': operator, 'values': [True]}, condition.decoded_value)

    def test_isnotempty_condition(self):
        "ISEMPTY (false) -> boolean"
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.ISEMPTY
        name = 'description'
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    False,
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(name,                                      condition.name)
        self.assertEqual({'operator': operator, 'values': [False]}, condition.decoded_value)

    def test_equals_boolean_condition(self):
        clean = RegularFieldsConditionsField(model=FakeOrganisation).clean
        operator = EntityFilterCondition.EQUALS
        name = 'subject_to_vat'
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    True,
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,          condition.type)
        self.assertEqual(name,                                     condition.name)
        self.assertEqual({'operator': operator, 'values': [True]}, condition.decoded_value)

    def test_fk_subfield(self):
        "FK subfield"
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.ISTARTSWITH
        name = 'civility__title'
        value = 'Miss'
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    value,
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(name,                                      condition.name)
        self.assertEqual({'operator': operator, 'values': [value]}, condition.decoded_value)

    def test_fk(self):
        "FK field"
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        name = 'civility'
        value = FakeCivility.objects.all()[0].pk
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    value,
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual(name,                            condition.name)
        self.assertEqual({'operator': operator, 'values': [str(value)]},
                         condition.decoded_value
                        )

    def test_multiple_fk_as_string(self):
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        name = 'civility'
        values = [c.pk for c in FakeCivility.objects.all()]
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    ','.join(str(v) for v in values),
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual(name,                            condition.name)
        self.assertEqual({'operator': operator,
                          'values':   [str(v) for v in values],
                         },
                         condition.decoded_value
                        )

    def test_multiple_fk_as_list(self):
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        name = 'civility'
        values = [str(c.pk) for c in FakeCivility.objects.all()]
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    values,
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual(name,                            condition.name)
        self.assertEqual({'operator': operator,
                          'values':   [str(v) for v in values],
                         },
                         condition.decoded_value
                        )

    def test_many2many(self):
        "ManyToMany field"
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        name = 'languages'
        value = Language.objects.all()[0].pk
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    value,
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual(name,                            condition.name)
        self.assertEqual({'operator': operator, 'values': [str(value)]},
                         condition.decoded_value
                        )

    def test_multiple_many2many_as_list(self):
        "ManyToMany field"
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        name = 'languages'
        values = [str(v) for v in Language.objects.all().values_list('pk', flat=True)]
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    values,
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual(name,                            condition.name)
        self.assertEqual({'operator': operator,
                          'values':   values,
                         },
                         condition.decoded_value
                        )

    def test_multiple_many2many_as_string(self):
        "ManyToMany field"
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        name = 'languages'
        values = Language.objects.all().values_list('pk', flat=True)
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    ','.join(str(v) for v in values),
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual(name,                            condition.name)
        self.assertEqual({'operator': operator,
                          'values': [str(v) for v in values]},
                         condition.decoded_value
                        )

    def test_choicetypes(self):
        "Field choice types"
        field_choicetype = FieldConditionWidget.field_choicetype
        get_field = FakeContact._meta.get_field

        civility_field = get_field('civility')
        self.assertTrue(civility_field.get_tag('enumerable'))
        # self.assertFalse(issubclass(civility_field.rel.to, CremeEntity))
        self.assertFalse(issubclass(civility_field.remote_field.model, CremeEntity))
        self.assertEqual(field_choicetype(civility_field), 'enum__null')

        self.assertEqual(field_choicetype(get_field('birthday')), 'date__null')
        self.assertEqual(field_choicetype(get_field('created')),  'date')

        self.assertEqual(field_choicetype(get_field('address')),  'fk__null')

        self.assertEqual(field_choicetype(get_field('user')),     'user')
        self.assertEqual(field_choicetype(get_field('is_user')),  'user__null')

        image_field = get_field('image')
        self.assertTrue(image_field.get_tag('enumerable'))
        # self.assertTrue(issubclass(image_field.rel.to, CremeEntity))
        self.assertTrue(issubclass(image_field.remote_field.model, CremeEntity))
        self.assertEqual(field_choicetype(image_field), 'fk__null')

        self.assertEqual(field_choicetype(get_field('languages')), 'enum__null')

    def test_iendswith_valuelist(self):
        "Multi values"
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.IENDSWITH
        name = 'last_name'
        values = ['nagi', 'sume']
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    ','.join(values),
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,          condition.type)
        self.assertEqual(name,                                     condition.name)
        self.assertEqual({'operator': operator, 'values': values}, condition.decoded_value)

    def test_multi_conditions(self):
        clean = RegularFieldsConditionsField(model=FakeContact).clean

        name1     = 'last_name'
        operator1 = EntityFilterCondition.IENDSWITH
        value1    = 'Valentine'

        name2     = 'first_name'
        operator2 = EntityFilterCondition.EQUALS
        value2    = 'Faye'

        conditions = clean(self.build_data({
                                 'name':     name1,
                                 'operator': operator1,
                                 'value':    value1,
                             }, {
                                 'name':     name2,
                                 'operator': operator2,
                                 'value':    value2,
                             },
                          ))
        self.assertEqual(2, len(conditions))

        EFC_FIELD = EntityFilterCondition.EFC_FIELD
        condition1 = conditions[0]
        self.assertEqual(EFC_FIELD, condition1.type)
        self.assertEqual(name1,     condition1.name)
        self.assertEqual({'operator': operator1, 'values': [value1]},
                         condition1.decoded_value
                        )

        condition2 = conditions[1]
        self.assertEqual(EFC_FIELD, condition2.type)
        self.assertEqual(name2,     condition2.name)
        self.assertEqual({'operator': operator2, 'values': [value2]},
                         condition2.decoded_value
                        )

    def test_many2many_subfield(self):
        "M2M field"
        clean = RegularFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.IEQUALS
        name = 'languages__name'
        value = 'French'
        conditions = clean(self.build_data({
                                 'operator': operator,
                                 'name':     name,
                                 'value':    value,
                             },
                          ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(name,                                      condition.name)
        self.assertEqual({'operator': operator, 'values': [value]}, condition.decoded_value)

    def test_fields_config01(self):
        hidden_fname = 'description'

        create_fc = FieldsConfig.create
        create_fc(FakeContact, descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})])
        create_fc(FakeImage,   descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})])

        clean = RegularFieldsConditionsField(model=FakeContact).clean

        EQUALS = EntityFilterCondition.EQUALS
        data = [{'name':     'last_name',
                 'operator': EQUALS,
                 'value':    'Faye',
                }, {
                 'name':     'image__name',
                 'operator': EQUALS,
                 'value':    'selfie',
                },
        ]

        conditions = clean(self.build_data(*data))
        self.assertEqual(2, len(conditions))

        EFC_FIELD = EntityFilterCondition.EFC_FIELD
        self.assertEqual(EFC_FIELD, conditions[0].type)
        self.assertEqual(EFC_FIELD, conditions[1].type)

        # ------
        data[1]['name'] = hidden_fname
        err = self.assertFieldRaises(ValidationError, clean, self.build_data(*data))[0]
        self.assertEqual(_(u'This field is invalid with this model.'), err.messages[0])

        # ------
        data[1]['name'] = 'image__' + hidden_fname
        err = self.assertFieldRaises(ValidationError, clean, self.build_data(*data))[0]
        self.assertEqual(_(u'This field is invalid with this model.'), err.messages[0])

    def test_fields_config02(self):
        "FK hidden => sub-fields hidden"
        FieldsConfig.create(FakeContact, descriptions=[('image', {FieldsConfig.HIDDEN: True})])

        err = self.assertFieldRaises(ValidationError,
                                     RegularFieldsConditionsField(model=FakeContact).clean,
                                     self.build_data({
                                        'name':     'image__name',
                                        'operator': EntityFilterCondition.EQUALS,
                                        'value':    'selfie',
                                     },
                                    ))[0]
        self.assertEqual(_(u'This field is invalid with this model.'), err.messages[0])

    def test_fields_config03(self):
        "Field is already used => still proposed"
        hidden_fname = 'description'
        FieldsConfig.create(FakeContact,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})]
                           )

        field = RegularFieldsConditionsField()
        field.initialize(ctype=ContentType.objects.get_for_model(FakeContact),
                         conditions=[EntityFilterCondition.build_4_field(
                                            model=FakeContact,
                                            operator=EntityFilterCondition.EQUALS,
                                            name=hidden_fname, values=['Ikari'],
                                        ),
                                    ],
                        )

        conditions = field.clean(self.build_data({
                                      'operator': EntityFilterCondition.EQUALS,
                                      'name':     hidden_fname,
                                      'value':    'Faye',
                                  },
                                ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual(hidden_fname,                    condition.name)

    def test_fields_config04(self):
        "Sub-field is already used => still proposed"
        hidden_sfname = 'image__description'
        FieldsConfig.create(FakeImage,
                            descriptions=[('description', {FieldsConfig.HIDDEN: True})]
                           )

        field = RegularFieldsConditionsField()
        field.initialize(ctype=ContentType.objects.get_for_model(FakeContact),
                         conditions=[EntityFilterCondition.build_4_field(
                                            model=FakeContact,
                                            operator=EntityFilterCondition.EQUALS,
                                            name=hidden_sfname, values=['Ikari'],
                                        ),
                                    ],
                        )

        with self.assertNoException():
            conditions = field.clean(self.build_data({
                                          'name':     hidden_sfname,
                                          'operator': EntityFilterCondition.EQUALS,
                                          'value':    'Faye',
                                      },
                                    ))

        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual(hidden_sfname,                   condition.name)

    def test_fields_config05(self):
        "Sub-field is already used => still proposed (FK hidden)"
        hidden_sfname = 'image__description'
        FieldsConfig.create(FakeContact,
                            descriptions=[('image', {FieldsConfig.HIDDEN: True})]
                           )

        field = RegularFieldsConditionsField()
        field.initialize(ctype=ContentType.objects.get_for_model(FakeContact),
                         conditions=[EntityFilterCondition.build_4_field(
                                            model=FakeContact,
                                            operator=EntityFilterCondition.EQUALS,
                                            name=hidden_sfname, values=['Ikari'],
                                        ),
                                    ],
                        )

        with self.assertNoException():
            conditions = field.clean(self.build_data({
                                          'name':     hidden_sfname,
                                          'operator': EntityFilterCondition.EQUALS,
                                          'value':    'Faye',
                                      },
                                    ))

        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual(hidden_sfname,                   condition.name)

    def test_fields_config06(self):
        "Field (ForeignKey) is already used => still proposed"
        hidden_fname = 'position'
        FieldsConfig.create(FakeContact,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})]
                           )

        position = FakePosition.objects.all()[0]
        field = RegularFieldsConditionsField()
        field.initialize(ctype=ContentType.objects.get_for_model(FakeContact),
                         conditions=[EntityFilterCondition.build_4_field(
                                            model=FakeContact,
                                            operator=EntityFilterCondition.EQUALS,
                                            name=hidden_fname, values=[position.id],
                                        ),
                                    ],
                        )

        with self.assertNoException():
            conditions = field.clean(self.build_data({
                                          'operator': EntityFilterCondition.EQUALS,
                                          'name':     hidden_fname,
                                          'value':    str(position.id),
                                      },
                                    ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual(hidden_fname,                    condition.name)


class DateFieldsConditionsFieldTestCase(FieldTestCase):
    def test_clean_invalid_data(self):
        clean = DateFieldsConditionsField(model=FakeContact).clean
        self.assertFieldValidationError(
            DateFieldsConditionsField, 'invalidfield', clean,
            '[{"field": {"name": "first_name", "type": "string__null"}, '
              '"range": {"type": "next_quarter", "start": "2011-5-12"}}]'
        )
        self.assertFieldValidationError(
            DateFieldsConditionsField, 'invalidformat', clean,
            '[{"field":  {"name": "birthday", "type": "date__null"}, "range":"not a dict"}]'
        )
        self.assertFieldValidationError(
            DateFieldsConditionsField, 'invaliddaterange', clean,
            '[{"field":  {"name": "birthday", "type": "date__null"}, '
              '"range": {"type":"unknow_range"}}]'  # TODO: "start": '' ???
        )

        self.assertFieldValidationError(
            DateFieldsConditionsField, 'emptydates', clean,
            '[{"field":  {"name": "birthday", "type": "date__null"}, "range": {"type":""}}]'
        )
        self.assertFieldValidationError(
            DateFieldsConditionsField, 'emptydates', clean,
            '[{"field":  {"name": "birthday", "type": "date__null"}, '
              '"range": {"type":"", "start": "", "end": ""}}]'
        )

        try:
            clean('[{"field": {"name": "created", "type": "date"}, '
                    '"range": {"type": "", "start": "not a date"}}]'
                 )
        except ValidationError: pass
        else:  self.fail('No ValidationError')

        try:
            clean('[{"field": {"name": "created", "type": "date"}, '
                    '"range": {"type": "", "end": "2011-2-30"}}]'
                 )  # 30 february !!
        except ValidationError: pass
        else:  self.fail('No ValidationError')

    def test_ok01(self):
        with self.assertNumQueries(0):
            field = DateFieldsConditionsField(model=FakeContact)

        type01 = 'current_year'
        name01 = 'created'
        type02 = 'next_quarter'
        name02 = 'birthday'
        conditions = field.clean(json_dump([
            {'field': {'name': name01, 'type': 'date'},       'range': {'type': type01}},
            {'field': {'name': name02, 'type': 'date__null'}, 'range': {'type': type02}},
        ]))
        self.assertEqual(2, len(conditions))

        EFC_DATEFIELD = EntityFilterCondition.EFC_DATEFIELD
        condition = conditions[0]
        self.assertEqual(EFC_DATEFIELD,    condition.type)
        self.assertEqual(name01,           condition.name)
        self.assertEqual({'name': type01}, condition.decoded_value)

        condition = conditions[1]
        self.assertEqual(EFC_DATEFIELD,    condition.type)
        self.assertEqual(name02,           condition.name)
        self.assertEqual({'name': type02}, condition.decoded_value)

    def test_ok02(self):
        "Start/end"
        field = DateFieldsConditionsField(model=FakeContact)
        name01 = 'created'
        name02 = 'birthday'
        conditions = field.clean(json_dump([
            {'field': {'name': name01, 'type': 'date'},       'range': {'type': '', 'start': '2011-5-12'}},
            {'field': {'name': name02, 'type': 'date__null'}, 'range': {'type': '', 'end': '2012-6-13'}},
        ]))
        self.assertEqual(2, len(conditions))

        EFC_DATEFIELD = EntityFilterCondition.EFC_DATEFIELD
        condition = conditions[0]
        self.assertEqual(EFC_DATEFIELD, condition.type)
        self.assertEqual(name01,        condition.name)
        self.assertEqual({'start': {'year': 2011, 'month': 5, 'day': 12}},
                         condition.decoded_value
                        )

        condition = conditions[1]
        self.assertEqual(EFC_DATEFIELD, condition.type)
        self.assertEqual(name02,        condition.name)
        self.assertEqual({'end': {'year': 2012, 'month': 6, 'day': 13}},
                         condition.decoded_value
                        )

    def test_ok03(self):
        "Start + end"
        clean = DateFieldsConditionsField(model=FakeContact).clean
        name = 'modified'
        conditions = clean(json_dump([
            {'field': {'name': name, 'type': 'date'},
             'range': {'type': '', 'start': '2010-3-24', 'end': '2011-7-25'},
            },
        ]))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual(name,                                condition.name)
        self.assertEqual({'start': {'year': 2010, 'month': 3, 'day': 24},
                          'end':   {'year': 2011, 'month': 7, 'day': 25},
                         },
                         condition.decoded_value
                        )

    def test_empty(self):
        clean = DateFieldsConditionsField(model=FakeContact).clean
        conditions = clean(json_dump([
            {'field': {'name': 'birthday', 'type': 'date__null'}, 'range': {'type': 'empty',     'start': '', 'end': ''}},
            {'field': {'name': 'modified', 'type': 'date__null'}, 'range': {'type': 'not_empty', 'start': '', 'end': ''}},
        ]))
        self.assertEqual(2, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual('birthday',                          condition.name)
        self.assertEqual({'name': 'empty'},                   condition.decoded_value)

        condition = conditions[1]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual('modified',                          condition.name)
        self.assertEqual({'name': 'not_empty'},               condition.decoded_value)

    def test_fields_config01(self):
        valid_fname  = 'issuing_date'
        hidden_fname = 'expiration_date'
        FieldsConfig.create(FakeInvoice,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
                           )

        field = DateFieldsConditionsField()
        field.initialize(ctype=ContentType.objects.get_for_model(FakeInvoice))

        def build_data(fname):
            return json_dump([
                {'field': {'name': fname, 'type': 'date__null'},
                 'range': {'type': '', 'start': '2015-3-24', 'end': '2015-7-25'},
                }
            ])

        conditions = field.clean(build_data(valid_fname))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual(valid_fname,                         condition.name)

        # --------------
        err = self.assertFieldRaises(ValidationError, field.clean, build_data(hidden_fname))[0]
        self.assertEqual(_(u'This field is not a date field for this model.'),
                         err.messages[0]
                        )

    def test_fields_config02(self):
        "Sub-fields"
        hidden_fname = 'expiration_date'
        FieldsConfig.create(FakeInvoice,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
                           )

        valid_fname = 'linked_invoice__issuing_date'

        def build_data(fname):
            return json_dump([
                {'field': {'name': fname, 'type': 'date__null'},
                 'range': {'type': '', 'start': '2015-3-24', 'end': '2015-7-25'},
                }
            ])

        clean = DateFieldsConditionsField(model=FakeInvoiceLine).clean
        conditions = clean(build_data(valid_fname))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual(valid_fname,                         condition.name)

        # --------------
        err = self.assertFieldRaises(ValidationError, clean,
                                     build_data('linked_invoice__' + hidden_fname)
                                    )[0]
        self.assertEqual(_(u'This field is not a date field for this model.'),
                         err.messages[0]
                        )

    def test_fields_config03(self):
        "FK hidden => sub-fields hidden"
        hidden_fname = 'exif_date'
        FieldsConfig.create(FakeImage,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
                           )
        err = self.assertFieldRaises(
            ValidationError,
            DateFieldsConditionsField(model=FakeContact).clean,
            json_dump([{'field': {'name': 'image__' + hidden_fname, 'type': 'date__null'},
                        'range': {'type': '', 'start': '2015-3-24', 'end': '2015-7-25'}
                       },
                      ]),
        )[0]
        self.assertEqual(_(u'This field is not a date field for this model.'),
                         err.messages[0]
                        )

    def test_fields_config04(self):
        "Field is already used => still proposed"
        hidden_fname = 'birthday'
        FieldsConfig.create(FakeContact,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
                           )

        field = DateFieldsConditionsField()
        field.initialize(ctype=ContentType.objects.get_for_model(FakeContact),
                         conditions=[EntityFilterCondition.build_4_date(
                                            model=FakeContact, name=hidden_fname,
                                            start=date(year=2000, month=1, day=1),
                                        ),
                                    ],
                        )

        with self.assertNoException():
            conditions = field.clean(json_dump([
                {'field': {'name': hidden_fname, 'type': 'date__null'},
                 'range': {'type': '', 'start': '2000-1-1'},
                },
            ]))

        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual(hidden_fname,                        condition.name)

    def test_fields_config05(self):
        "Sub-field is already used => still proposed"
        hidden_sfname = 'image__exif_date'
        FieldsConfig.create(FakeImage,
                            descriptions=[('exif_date', {FieldsConfig.HIDDEN: True})],
                           )

        field = DateFieldsConditionsField()
        field.initialize(ctype=ContentType.objects.get_for_model(FakeContact),
                         conditions=[EntityFilterCondition.build_4_date(
                                            model=FakeContact, name=hidden_sfname,
                                            start=date(year=2000, month=1, day=1),
                                        ),
                                    ],
                        )

        with self.assertNoException():
            conditions = field.clean(json_dump([
                {'field': {'name': hidden_sfname, 'type': 'date__null'},
                 'range': {'type': '', 'start': '2000-1-1'},
                },
            ]))

        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual(hidden_sfname,                       condition.name)

    def test_fields_config06(self):
        "Sub-field is already used => still proposed (FK hidden)"
        hidden_sfname = 'image__exif_date'
        FieldsConfig.create(FakeContact,
                            descriptions=[('image', {FieldsConfig.HIDDEN: True})]
                           )

        field = DateFieldsConditionsField()
        field.initialize(ctype=ContentType.objects.get_for_model(FakeContact),
                         conditions=[EntityFilterCondition.build_4_date(
                                            model=FakeContact, name=hidden_sfname,
                                            start=date(year=2000, month=1, day=1),
                                        ),
                                    ],
                        )

        with self.assertNoException():
            conditions = field.clean(json_dump([
                {'field': {'name': hidden_sfname, 'type': 'date__null'},
                 'range': {'type': '', 'start': '2000-1-1'},
                },
            ]))

        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual(hidden_sfname,                       condition.name)


class CustomFieldsConditionsFieldTestCase(FieldTestCase):
    @staticmethod
    def build_data(field, operator, value):
        return json_dump(
            [{'field': {'id': str(field)}, 'operator': {'id': str(operator)}, 'value': value}]
        )

    def setUp(self):
        ct = ContentType.objects.get_for_model(FakeContact)
        create_cfield = partial(CustomField.objects.create, content_type=ct)
        self.cfield_int       = create_cfield(name='Size',      field_type=CustomField.INT)
        self.cfield_bool      = create_cfield(name='Valid',     field_type=CustomField.BOOL)
        self.cfield_str       = create_cfield(name='Name',      field_type=CustomField.STR)
        self.cfield_date      = create_cfield(name='Date',      field_type=CustomField.DATETIME)
        self.cfield_float     = create_cfield(name='Number',    field_type=CustomField.FLOAT)
        self.cfield_enum      = create_cfield(name='Enum',      field_type=CustomField.ENUM)
        self.cfield_multienum = create_cfield(name='MultiEnum', field_type=CustomField.MULTI_ENUM)

        create_evalue = partial(CustomFieldEnumValue.objects.create,
                                custom_field=self.cfield_enum,
                               )
        self.cfield_enum_A = create_evalue(value='A')
        self.cfield_enum_B = create_evalue(value='B')
        self.cfield_enum_C = create_evalue(value='C')

        create_evalue = partial(CustomFieldEnumValue.objects.create,
                                custom_field=self.cfield_multienum,
                               )
        self.cfield_multienum_F = create_evalue(value='F')
        self.cfield_multienum_G = create_evalue(value='G')
        self.cfield_multienum_H = create_evalue(value='H')

    def _get_allowed_types(self, operator):
        return ' '.join(EntityFilterCondition._OPERATOR_MAP[operator].allowed_fieldtypes)

    def test_frompython_custom_int(self):
        EQUALS = EntityFilterCondition.EQUALS
        field = CustomFieldsConditionsField(model=FakeContact)
        condition = EntityFilterCondition.build_4_customfield(self.cfield_int, EQUALS, [150])
        data = field._value_to_jsonifiable([condition])

        self.assertEqual([{'field': {'id': self.cfield_int.id, 'type': 'number__null'},
                           'operator': {'id': EQUALS,
                                        'types': self._get_allowed_types(EQUALS),
                                       },
                           'value': '150',
                          }
                         ], data)

    def test_frompython_custom_string(self):
        EQUALS = EntityFilterCondition.EQUALS
        field = CustomFieldsConditionsField(model=FakeContact)
        condition = EntityFilterCondition.build_4_customfield(self.cfield_str, EQUALS, ['abc'])
        data = field._value_to_jsonifiable([condition])

        self.assertEqual([{'field': {'id': self.cfield_str.id, 'type': 'string'},
                           'operator': {'id': EQUALS,
                                        'types': self._get_allowed_types(EQUALS),
                                       },
                           'value': 'abc',
                          }
                         ], data)

    def test_frompython_custom_bool(self):
        EQUALS = EntityFilterCondition.EQUALS
        field = CustomFieldsConditionsField(model=FakeContact)
        condition = EntityFilterCondition.build_4_customfield(self.cfield_bool, EQUALS, [False])
        data = field._value_to_jsonifiable([condition])

        self.assertEqual([{'field': {'id': self.cfield_bool.id, 'type': 'boolean__null'},
                           'operator': {'id': EQUALS,
                                         'types': self._get_allowed_types(EQUALS),
                                       },
                           'value': u'false',
                          }
                         ], data)

        # Old format
        condition = EntityFilterCondition.build_4_customfield(self.cfield_bool, EQUALS, ['False'])
        data = field._value_to_jsonifiable([condition])

        self.assertEqual([{'field': {'id': self.cfield_bool.id, 'type': 'boolean__null'},
                           'operator': {'id': EQUALS,
                                        'types': self._get_allowed_types(EQUALS),
                                       },
                           'value': u'false',
                          }
                         ], data)

    def test_frompython_custom_enum(self):
        EQUALS = EntityFilterCondition.EQUALS
        field = CustomFieldsConditionsField(model=FakeContact)
        condition = EntityFilterCondition.build_4_customfield(self.cfield_enum, EQUALS, [self.cfield_enum_A.id])
        data = field._value_to_jsonifiable([condition])

        self.assertEqual([{'field': {'id': self.cfield_enum.id, 'type': 'enum__null'},
                           'operator': {'id': EQUALS,
                                        'types': self._get_allowed_types(EQUALS),
                                       },
                           'value': unicode(self.cfield_enum_A.id),
                          }
                         ], data)

    def test_clean_invalid_data_format(self):
        field = CustomFieldsConditionsField(model=FakeContact)
        self.assertFieldValidationError(CustomFieldsConditionsField, 'invalidformat', field.clean,
                                        self.build_data(field='notanumber',
                                                        operator=EntityFilterCondition.EQUALS,
                                                        value=170,
                                        ),
                                       )

    def test_clean_invalid_field(self):
        field = CustomFieldsConditionsField(model=FakeContact)
        self.assertFieldValidationError(CustomFieldsConditionsField, 'invalidcustomfield', field.clean,
                                        self.build_data(field=2054,
                                                        operator=EntityFilterCondition.EQUALS,
                                                        value=170,
                                        ),
                                       )

        self.assertFieldValidationError(CustomFieldsConditionsField, 'invalidcustomfield', field.clean,
                                        json_dump([{'operator': {'id': str(EntityFilterCondition.EQUALS)},
                                                    'value': [170],
                                                   },
                                           ])
                                       )

    def test_clean_invalid_operator(self):
        field = CustomFieldsConditionsField(model=FakeContact)
        self.assertFieldValidationError(CustomFieldsConditionsField, 'invalidoperator', field.clean,
                                        self.build_data(field=self.cfield_int.id,
                                                        operator=121266,
                                                        value=170,
                                        )
                                       )
        self.assertFieldValidationError(CustomFieldsConditionsField, 'invalidoperator', field.clean,
                                        json_dump([{'field': {'id': str(self.cfield_int.id)}, 'value': 170}])
                                       )

    def test_clean_missing_value(self):
        field = CustomFieldsConditionsField(model=FakeContact)
        self.assertFieldValidationError(CustomFieldsConditionsField, 'invalidvalue', field.clean,
                                        json_dump([
                                            {'field':    {'id': str(self.cfield_int.id)},
                                             'operator': {'id': str(EntityFilterCondition.EQUALS)},
                                            }
                                        ])
                                       )

    def test_clean_integer01(self):
        with self.assertNumQueries(0):
            field = CustomFieldsConditionsField(model=FakeContact)

        operator = EntityFilterCondition.EQUALS
        value = 180
        conditions = field.clean(self.build_data(field=self.cfield_int.id,
                                                 operator=operator,
                                                 value=value,
                                                )
                                )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield_int.id), condition.name)
        self.assertEqual({'operator': operator,
                          'rname': 'customfieldinteger',
                          'value': [unicode(value)],
                         },
                         condition.decoded_value
                        )

    def test_clean_integer02(self):
        "'model' property"
        with self.assertNumQueries(0):
            field = CustomFieldsConditionsField()
            field.model = FakeContact

        operator = EntityFilterCondition.EQUALS
        value = 180
        conditions = field.clean(self.build_data(field=self.cfield_int.id,
                                                 operator=operator,
                                                 value=value,
                                                ),
                                )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield_int.id), condition.name)
        self.assertEqual({'operator': operator,
                          'rname': 'customfieldinteger',
                          'value': [unicode(value)],
                         },
                         condition.decoded_value
                        )

    def test_clean_enum(self):
        clean = CustomFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        value = str(self.cfield_enum_A.pk)
        conditions = clean(self.build_data(field=self.cfield_enum.id,
                                           operator=operator,
                                           value=value,
                                          )
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield_enum.id), condition.name)
        self.assertEqual({'operator': operator,
                          'rname': 'customfieldenum',
                          'value': [value],
                         },
                         condition.decoded_value
                        )

    def test_clean_enum_as_string(self):
        clean = CustomFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        conditions = clean(self.build_data(
                                field=self.cfield_enum.id,
                                operator=operator,
                                value='{},{}'.format(self.cfield_enum_A.pk,
                                                     self.cfield_enum_B.pk,
                                                    ),
                            )
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield_enum.id), condition.name)
        self.assertEqual({'operator': operator,
                          'rname': 'customfieldenum',
                          'value': [str(self.cfield_enum_A.pk),
                                    str(self.cfield_enum_B.pk)
                                   ],
                         },
                         condition.decoded_value
                        )

    def test_clean_enum_as_list(self):
        clean = CustomFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        conditions = clean(self.build_data(
                                field=self.cfield_enum.id,
                                operator=operator,
                                value=[self.cfield_enum_A.pk, self.cfield_enum_B.pk],
                            )
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield_enum.id), condition.name)
        self.assertEqual({'operator': operator,
                          'rname': 'customfieldenum',
                          'value': [str(self.cfield_enum_A.pk),
                                    str(self.cfield_enum_B.pk),
                                   ],
                         },
                         condition.decoded_value
                        )

    def test_clean_multienum(self):
        clean = CustomFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        value = str(self.cfield_multienum_F.pk)
        conditions = clean(self.build_data(field=self.cfield_multienum.id,
                                           operator=operator,
                                           value=value,
                                          )
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield_multienum.id), condition.name)
        self.assertEqual({'operator': operator,
                          'rname': 'customfieldmultienum',
                          'value': [value],
                         },
                         condition.decoded_value
                        )

    def test_clean_multienum_as_string(self):
        clean = CustomFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        conditions = clean(self.build_data(
                                field=self.cfield_multienum.id,
                                operator=operator,
                                value='{},{}'.format(self.cfield_multienum_F.pk,
                                                     self.cfield_multienum_H.pk,
                                                    ),
                            )
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield_multienum.id), condition.name)
        self.assertEqual({'operator': operator,
                          'rname': 'customfieldmultienum',
                          'value': [str(self.cfield_multienum_F.pk),
                                    str(self.cfield_multienum_H.pk)
                                   ],
                         },
                         condition.decoded_value
                        )

    def test_clean_multienum_as_list(self):
        clean = CustomFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        conditions = clean(self.build_data(
                                field=self.cfield_multienum.id,
                                operator=operator,
                                value=[self.cfield_multienum_F.pk,
                                       self.cfield_multienum_H.pk,
                                      ],
                            )
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield_multienum.id), condition.name)
        self.assertEqual({'operator': operator,
                          'rname': 'customfieldmultienum',
                          'value': [str(self.cfield_multienum_F.pk),
                                    str(self.cfield_multienum_H.pk)
                                   ],
                         },
                         condition.decoded_value
                        )

    def test_clean_empty_string(self):
        clean = CustomFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        conditions = clean(self.build_data(field=self.cfield_str.id,
                                           operator=operator,
                                           value='',
                                          )
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield_str.id),               condition.name)
        self.assertEqual({'operator': operator, 'rname': 'customfieldstring', 'value': []},
                         condition.decoded_value
                        )

    def test_equals_boolean_condition(self):
        clean = CustomFieldsConditionsField(model=FakeContact).clean
        operator = EntityFilterCondition.EQUALS
        conditions = clean(self.build_data(field=self.cfield_bool.id,
                                           operator=operator,
                                           value=False,
                                          )
                          )
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(self.cfield_bool.id),               condition.name)
        self.assertEqual({'operator': operator, 'rname': 'customfieldboolean', 'value': ['False']},
                         condition.decoded_value
                        )

    def test_customfield_choicetype(self):
        """custom field choice types"""
        field_choicetype = CustomFieldConditionSelector.customfield_choicetype

        self.assertEqual(field_choicetype(self.cfield_enum),  'enum__null')
        self.assertEqual(field_choicetype(self.cfield_date),  'date__null')
        self.assertEqual(field_choicetype(self.cfield_bool),  'boolean__null')
        self.assertEqual(field_choicetype(self.cfield_int),   'number__null')
        self.assertEqual(field_choicetype(self.cfield_float), 'number__null')


class DateCustomFieldsConditionsFieldTestCase(FieldTestCase):
    def setUp(self):
        create_cfield = partial(CustomField.objects.create,
                                field_type=CustomField.DATETIME,
                                content_type=ContentType.objects.get_for_model(FakeContact),
                                )
        self.cfield01 = create_cfield(name='Day')
        self.cfield02 = create_cfield(name='First flight')

    def test_clean_invalid_data(self):
        clean = DateCustomFieldsConditionsField(model=FakeContact).clean

        self.assertFieldValidationError(DateCustomFieldsConditionsField, 'invalidcustomfield', clean,
                                        '[{"field": "2054", "range": {"type": "current_year"}}]'
                                       )
        self.assertFieldValidationError(DateCustomFieldsConditionsField, 'invalidformat', clean,
                                        json_dump([{'field': str(self.cfield01.id), 'range': 'not a dict'}])
                                       )
        self.assertFieldValidationError(DateCustomFieldsConditionsField, 'invaliddaterange', clean,
                                        json_dump([{'field': str(self.cfield01.id), 'range': {'type': 'unknow_range'}}])
                                       )
        self.assertFieldValidationError(DateCustomFieldsConditionsField, 'emptydates', clean,
                                        json_dump([{'field': str(self.cfield01.id), 'range': {'type': ''}}])
                                       )
        self.assertFieldValidationError(DateCustomFieldsConditionsField, 'emptydates', clean,
                                        json_dump([{'field': str(self.cfield01.id),
                                                    'range': {'type':'', 'start': '', 'end': ''},
                                                   },
                                        ])
                                       )

    def test_ok01(self):
        with self.assertNumQueries(0):
            field = DateCustomFieldsConditionsField(model=FakeContact)

        rtype = 'current_year'
        cfield01 = self.cfield01
        cfield02 = self.cfield02
        conditions = field.clean(json_dump([
            {'field': str(cfield01.id), 'range': {'type': rtype}},
            {'field': str(cfield02.id), 'range': {'type': '', 'start': '2011-5-12'}},
            {'field': str(cfield01.id), 'range': {'type': '', 'end': '2012-6-13'}},
            {'field': str(cfield02.id), 'range': {'type': '', 'start': '2011-5-12', 'end': '2012-6-13'}},
        ]))
        self.assertEqual(4, len(conditions))

        EFC_DATECUSTOMFIELD = EntityFilterCondition.EFC_DATECUSTOMFIELD
        condition = conditions[0]
        self.assertEqual(EFC_DATECUSTOMFIELD,   condition.type)
        self.assertEqual(str(cfield01.id), condition.name)
        self.assertEqual({'rname': 'customfielddatetime', 'name': rtype},
                         condition.decoded_value,
                        )

        condition = conditions[1]
        self.assertEqual(EFC_DATECUSTOMFIELD,   condition.type)
        self.assertEqual(str(cfield02.id), condition.name)
        self.assertEqual({'rname': 'customfielddatetime',
                          'start': {'year': 2011, 'month': 5, 'day': 12},
                         },
                         condition.decoded_value
                        )

        condition = conditions[2]
        self.assertEqual(EFC_DATECUSTOMFIELD,   condition.type)
        self.assertEqual(str(cfield01.id), condition.name)
        self.assertEqual({'rname': 'customfielddatetime',
                          'end': {'year': 2012, 'month': 6, 'day': 13},
                         },
                         condition.decoded_value
                        )

        condition = conditions[3]
        self.assertEqual(EFC_DATECUSTOMFIELD,   condition.type)
        self.assertEqual(str(cfield02.id), condition.name)
        self.assertEqual({'rname': 'customfielddatetime',
                          'start': {'year': 2011, 'month': 5, 'day': 12},
                          'end':   {'year': 2012, 'month': 6, 'day': 13},
                         },
                         condition.decoded_value
                        )

    def test_empty(self):
        with self.assertNumQueries(0):
            field = DateCustomFieldsConditionsField()
            field.model = FakeContact

        conditions = field.clean(json_dump([
            {'field': str(self.cfield01.id), 'range': {'type': 'empty'}},
            {'field': str(self.cfield02.id), 'range': {'type': 'not_empty'}},
        ]))
        self.assertEqual(2, len(conditions))

        EFC_DATECUSTOMFIELD = EntityFilterCondition.EFC_DATECUSTOMFIELD
        condition = conditions[0]
        self.assertEqual(EFC_DATECUSTOMFIELD,   condition.type)
        self.assertEqual(str(self.cfield01.id), condition.name)
        self.assertEqual({'rname': 'customfielddatetime', 'name': 'empty'},
                         condition.decoded_value
                        )

        condition = conditions[1]
        self.assertEqual(EFC_DATECUSTOMFIELD,   condition.type)
        self.assertEqual(str(self.cfield02.id), condition.name)
        self.assertEqual({'rname': 'customfielddatetime', 'name': 'not_empty'},
                         condition.decoded_value
                        )


class PropertiesConditionsFieldTestCase(FieldTestCase):
    def setUp(self):
        create_ptype = CremePropertyType.create
        self.ptype01 = create_ptype('test-prop_active', 'Is active')
        self.ptype02 = create_ptype('test-prop_cute',   'Is cute', (FakeContact,))
        self.ptype03 = create_ptype('test-prop_evil',   'Is evil', (FakeOrganisation,))

    def test_clean_empty_required(self):
        with self.assertNumQueries(0):
            field = PropertiesConditionsField(required=True)

        clean = field.clean
        self.assertFieldValidationError(PropertiesConditionsField, 'required', clean, None)
        self.assertFieldValidationError(PropertiesConditionsField, 'required', clean, '')
        self.assertFieldValidationError(PropertiesConditionsField, 'required', clean, '[]')

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            PropertiesConditionsField(required=False).clean(None)

    def test_clean_invalid_data_type(self):
        clean = PropertiesConditionsField(model=FakeContact).clean
        self.assertFieldValidationError(PropertiesConditionsField, 'invalidtype', clean, '"this is a string"')
        self.assertFieldValidationError(PropertiesConditionsField, 'invalidtype', clean, '"{}"')
        self.assertFieldValidationError(PropertiesConditionsField, 'invalidtype', clean, '{"foobar":{"ptype": "test-foobar", "has": true}}')

    def test_clean_incomplete_data_required(self):
        clean = PropertiesConditionsField(model=FakeContact).clean
        self.assertFieldValidationError(PropertiesConditionsField, 'required', clean, '[{"ptype": "%s"}]' % self.ptype01.id)
        self.assertFieldValidationError(PropertiesConditionsField, 'required', clean, '[{"has": true}]')

    def test_unknown_ptype(self):
        self.assertFieldValidationError(PropertiesConditionsField, 'invalidptype',
                                        PropertiesConditionsField(model=FakeContact).clean,
                                        json_dump([{'ptype': self.ptype03.id, 'has': True}])
                                       )

    def test_ok01(self):
        with self.assertNumQueries(0):
            field = PropertiesConditionsField(model=FakeContact)

        conditions = field.clean(json_dump([{'ptype': self.ptype01.id, 'has': True},
                                            {'ptype': self.ptype02.id, 'has': False},
                                           ]
                                          )
                                )
        self.assertEqual(2, len(conditions))

        EFC_PROPERTY = EntityFilterCondition.EFC_PROPERTY
        condition = conditions[0]
        self.assertEqual(EFC_PROPERTY,    condition.type)
        self.assertEqual(self.ptype01.id, condition.name)
        self.assertIs(condition.decoded_value, True)

        condition = conditions[1]
        self.assertEqual(EFC_PROPERTY,    condition.type)
        self.assertEqual(self.ptype02.id, condition.name)
        self.assertIs(condition.decoded_value, False)

    def test_ok02(self):
        ptype = self.ptype01

        with self.assertNumQueries(0):
            field = PropertiesConditionsField()
            field.model = FakeContact

        conditions = field.clean(json_dump([{'ptype': ptype.id, 'has': True}]))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_PROPERTY, condition.type)
        self.assertEqual(ptype.id, condition.name)


class RelationsConditionsFieldTestCase(FieldTestCase):
    def setUp(self):
        create = RelationType.create
        self.rtype01, self.rtype02 = create(('test-subject_love', u'Is loving', (FakeContact,)),
                                            ('test-object_love',  u'Is loved by')
                                           )
        self.rtype03, self.srtype04 = create(('test-subject_belong', u'(orga) belongs to (orga)', (FakeOrganisation,)),
                                             ('test-object_belong',  u'(orga) has (orga)',        (FakeOrganisation,))
                                            )

    def test_clean_empty_required(self):
        clean = RelationsConditionsField(required=True).clean
        self.assertFieldValidationError(RelationsConditionsField, 'required', clean, None)
        self.assertFieldValidationError(RelationsConditionsField, 'required', clean, "")
        self.assertFieldValidationError(RelationsConditionsField, 'required', clean, "[]")

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            RelationsConditionsField(required=False).clean(None)

    def test_clean_invalid_data_type(self):
        clean = RelationsConditionsField(model=FakeContact).clean
        self.assertFieldValidationError(RelationsConditionsField, 'invalidtype', clean,
                                        '"this is a string"'
                                       )
        self.assertFieldValidationError(RelationsConditionsField, 'invalidtype', clean, '"{}"')
        self.assertFieldValidationError(RelationsConditionsField, 'invalidtype', clean,
                                        '{"foobar": {"rtype": "test-foobar", "has": true}}'
                                       )

    def test_clean_invalid_data(self):
        clean = RelationsConditionsField(model=FakeContact).clean
        ct = ContentType.objects.get_for_model(FakeContact)
        rt_id = self.rtype01.id
        self.assertFieldValidationError(RelationsConditionsField, 'invalidformat', clean,
                                        json_dump([{'rtype': rt_id, 'has': True, 'ctype': 'not an int'}])
                                       )
        self.assertFieldValidationError(RelationsConditionsField, 'invalidformat', clean,
                                        json_dump([{'rtype': rt_id, 'has': True, 'ctype': ct.id, 'entity': 'not an int'}])
                                       )

    def test_clean_incomplete_data_required(self):
        clean = RelationsConditionsField(model=FakeContact).clean
        rt_id = self.rtype01.id
        self.assertFieldValidationError(RelationsConditionsField, 'required', clean,
                                        json_dump([{'rtype': rt_id}])
                                       )
        self.assertFieldValidationError(RelationsConditionsField, 'required', clean,
                                        json_dump([{'has': True}])
                                       )
        self.assertFieldValidationError(RelationsConditionsField, 'required', clean,
                                        json_dump([{'rtype': rt_id, 'has': 'not a boolean'}])
                                       )

    def test_unknown_ct(self):
        clean = RelationsConditionsField(model=FakeContact).clean
        self.assertFieldValidationError(RelationsConditionsField, 'invalidct', clean,
                                        json_dump([{'rtype': self.rtype01.id, 'has': True, 'ctype': 2121545}])
                                       )

    def test_unknown_entity(self):
        clean = RelationsConditionsField(model=FakeContact).clean
        self.assertFieldValidationError(RelationsConditionsField, 'invalidentity', clean,
                                        json_dump([{'rtype': self.rtype01.id, 'has': True, 'ctype': 1, 'entity': 2121545}])
                                       )

    def test_ok01(self):
        "No ct, no object entity"
        with self.assertNumQueries(0):
            field = RelationsConditionsField(model=FakeContact)

        conditions = field.clean(json_dump([
            {'rtype': self.rtype01.id, 'has': True,  'ctype': 0, 'entity': None},
            {'rtype': self.rtype02.id, 'has': False, 'ctype': 0, 'entity': None},
        ]))
        self.assertEqual(2, len(conditions))

        EFC_RELATION = EntityFilterCondition.EFC_RELATION
        condition = conditions[0]
        self.assertEqual(EFC_RELATION,    condition.type)
        self.assertEqual(self.rtype01.id, condition.name)
        self.assertEqual({'has': True},   condition.decoded_value)

        condition = conditions[1]
        self.assertEqual(EFC_RELATION,    condition.type)
        self.assertEqual(self.rtype02.id, condition.name)
        self.assertEqual({'has': False},  condition.decoded_value)

    def test_ok02(self):
        "Wanted ct"
        field = RelationsConditionsField(model=FakeContact)
        ct = ContentType.objects.get_for_model(FakeContact)
        conditions = field.clean(json_dump([
            {'rtype': self.rtype01.id, 'has': True,  'ctype': ct.id, 'entity': None},
            {'rtype': self.rtype02.id, 'has': False, 'ctype': ct.id}
        ]))
        self.assertEqual(2, len(conditions))

        EFC_RELATION = EntityFilterCondition.EFC_RELATION
        condition = conditions[0]
        self.assertEqual(EFC_RELATION,                  condition.type)
        self.assertEqual(self.rtype01.id,               condition.name)
        self.assertEqual({'has': True, 'ct_id': ct.id}, condition.decoded_value)

        condition = conditions[1]
        self.assertEqual(EFC_RELATION,                   condition.type)
        self.assertEqual(self.rtype02.id,                condition.name)
        self.assertEqual({'has': False, 'ct_id': ct.id}, condition.decoded_value)

    def test_ok03(self):
        "Wanted entity"
        user = self.login()

        naru = FakeContact.objects.create(user=user, first_name='Naru', last_name='Narusegawa')
        field = RelationsConditionsField(model=FakeContact)
        ct = ContentType.objects.get_for_model(FakeContact)
        conditions = field.clean(json_dump(
                [{'rtype': self.rtype01.id, 'has': True, 'ctype': ct.id, 'entity': str(naru.id)}]
        ))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_RELATION,  condition.type)
        self.assertEqual(self.rtype01.id,                     condition.name)
        self.assertEqual({'has': True, 'entity_id': naru.id}, condition.decoded_value)

    def test_ok04(self):
        "Wanted ct + wanted entity"
        user = self.login()

        ct_id = ContentType.objects.get_for_model(FakeContact).id
        naru = FakeContact.objects.create(user=user, first_name='Naru', last_name='Narusegawa')
        field = RelationsConditionsField(model=FakeContact)
        conditions = field.clean(json_dump([
            {'rtype': self.rtype01.id, 'has': True,  'ctype': ct_id, 'entity': None},
            {'rtype': self.rtype02.id, 'has': False, 'ctype': ct_id, 'entity': str(naru.id)},
        ]))
        self.assertEqual(2, len(conditions))

        EFC_RELATION = EntityFilterCondition.EFC_RELATION
        condition = conditions[0]
        self.assertEqual(EFC_RELATION,                  condition.type)
        self.assertEqual(self.rtype01.id,               condition.name)
        self.assertEqual({'has': True, 'ct_id': ct_id}, condition.decoded_value)

        condition = conditions[1]
        self.assertEqual(EFC_RELATION,                         condition.type)
        self.assertEqual(self.rtype02.id,                      condition.name)
        self.assertEqual({'has': False, 'entity_id': naru.id}, condition.decoded_value)

    def test_ok05(self):
        "Wanted entity is deleted"
        user = self.login()

        naru = FakeContact.objects.create(user=user, first_name='Naru', last_name='Narusegawa')
        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01',
                                      model=FakeContact, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_relation(
                                                        rtype=self.rtype01, has=True, entity=naru,
                                                    ),
                                                 ],
                                     )
        field = RelationsConditionsField(model=FakeContact)

        jsondict = {'entity': naru.id,
                    'has':    'true',
                    'ctype':  naru.entity_type_id,
                    'rtype':  self.rtype01.id,
                   }
        self.assertEqual([jsondict], json_load(field.from_python(list(efilter.conditions.all()))))

        try:
            naru.delete()
        except Exception as e:
            self.fail('Problem with entity deletion: {}'.format(e))

        jsondict['entity'] = None
        jsondict['ctype'] = 0
        self.assertEqual([jsondict], json_load(field.from_python(list(efilter.conditions.all()))))

    def test_ok06(self):
        "'model' property"
        with self.assertNumQueries(0):
            field = RelationsConditionsField()
            field.model = FakeContact

        rt_id = self.rtype01.id
        conditions = field.clean(json_dump([{'rtype': rt_id, 'has': True,  'ctype': 0, 'entity': None}]))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_RELATION, condition.type)
        self.assertEqual(rt_id, condition.name)
        self.assertEqual({'has': True}, condition.decoded_value)


class RelationSubfiltersConditionsFieldTestCase(FieldTestCase):
    def setUp(self):
        create = RelationType.create
        self.rtype01, self.rtype02 = create(('test-subject_love', u'Is loving', (FakeContact,)),
                                            ('test-object_love',  u'Is loved by')
                                           )
        self.rtype03, self.srtype04 = create(('test-subject_belong', u'(orga) belongs to (orga)', (FakeOrganisation,)),
                                             ('test-object_belong',  u'(orga) has (orga)',        (FakeOrganisation,))
                                            )

        self.sub_efilter01 = EntityFilter.create(pk='test-filter01', name='Filter 01', model=FakeContact, is_custom=True)
        self.sub_efilter02 = EntityFilter.create(pk='test-filter02', name='Filter 02', model=FakeOrganisation, is_custom=True)

    def test_clean_empty_required(self):
        clean = RelationSubfiltersConditionsField(required=True).clean
        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'required', clean, None)
        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'required', clean, '')
        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'required', clean, '[]')

    def test_clean_incomplete_data_required(self):
        clean = RelationSubfiltersConditionsField(model=FakeContact).clean
        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'required', clean, json_dump([{'rtype': self.rtype01.id}]))
        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'required', clean, json_dump([{'has': True}]))

    def test_unknown_filter(self):
        user = self.login()
        field = RelationSubfiltersConditionsField(model=FakeContact)
        field.user = user
        self.assertFieldValidationError(RelationSubfiltersConditionsField, 'invalidfilter', field.clean,
                                        json_dump([
                                            {'rtype': self.rtype01.id, 'has': False,
                                             'ctype': ContentType.objects.get_for_model(FakeContact).id,
                                             'filter': '3213213543',  # <==
                                            }
                                        ])
                                       )

    def test_ok(self):
        user = self.login()

        with self.assertNumQueries(0):
            field = RelationSubfiltersConditionsField(model=FakeContact)
            field.user = user

        get_ct = ContentType.objects.get_for_model
        filter_id1 = self.sub_efilter01.id
        filter_id2 = self.sub_efilter02.id
        conditions = field.clean(json_dump([
            {'rtype': self.rtype01.id, 'has': True,  'ctype': get_ct(FakeContact).id,      'filter': filter_id1},
            {'rtype': self.rtype02.id, 'has': False, 'ctype': get_ct(FakeOrganisation).id, 'filter': filter_id2}
        ]))
        self.assertEqual(2, len(conditions))

        EFC_RELATION_SUBFILTER = EntityFilterCondition.EFC_RELATION_SUBFILTER
        condition = conditions[0]
        self.assertEqual(EFC_RELATION_SUBFILTER, condition.type)
        self.assertEqual(self.rtype01.id,        condition.name)
        self.assertEqual({'has': True, 'filter_id': filter_id1},
                         condition.decoded_value
                        )

        condition = conditions[1]
        self.assertEqual(EFC_RELATION_SUBFILTER, condition.type)
        self.assertEqual(self.rtype02.id,        condition.name)
        self.assertEqual({'has': False, 'filter_id': filter_id2},
                         condition.decoded_value
                        )
