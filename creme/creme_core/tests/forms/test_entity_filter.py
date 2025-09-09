from datetime import date
from functools import partial
from json import dumps as json_dump
from json import loads as json_load

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    EF_REGULAR,
    EntityFilterRegistry,
    entity_filter_registries,
    operands,
    operators,
)
from creme.creme_core.core.entity_filter.condition_handler import (
    CustomFieldConditionHandler,
    DateCustomFieldConditionHandler,
    DateRegularFieldConditionHandler,
    PropertyConditionHandler,
    RegularFieldConditionHandler,
    RelationConditionHandler,
    RelationSubFilterConditionHandler,
    SubFilterConditionHandler,
)
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.forms.entity_filter.fields import (
    CustomFieldsConditionsField,
    DateCustomFieldsConditionsField,
    DateFieldsConditionsField,
    PropertiesConditionsField,
    RegularFieldsConditionsField,
    RelationsConditionsField,
    RelationSubfiltersConditionsField,
    SubfiltersConditionsField,
)
from creme.creme_core.forms.entity_filter.forms import (
    EntityFilterCreationForm,
    EntityFilterEditionForm,
)
from creme.creme_core.forms.entity_filter.widgets import (
    CustomFieldConditionSelector,
    CustomFieldsConditionsWidget,
    DateCustomFieldsConditionsWidget,
    FieldConditionSelector,
    RelationsConditionsWidget,
    RelationSubfiltersConditionsWidget,
)
from creme.creme_core.models import (
    CremeEntity,
    CremePropertyType,
    CustomField,
    CustomFieldEnumValue,
    EntityFilter,
    FakeCivility,
    FakeContact,
    FakeImage,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    FakePosition,
    FieldsConfig,
    Language,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase

efilter_registry = EntityFilterRegistry(
    id='creme_core-test_efilter_forms',
    verbose_name='Form tests',
).register_condition_handlers(
    RegularFieldConditionHandler,
    DateRegularFieldConditionHandler,

    CustomFieldConditionHandler,
    DateCustomFieldConditionHandler,

    RelationConditionHandler,
    RelationSubFilterConditionHandler,

    PropertyConditionHandler,

    SubFilterConditionHandler,
).register_operators(
    *operators.all_operators,
).register_operands(
    *operands.all_operands,
)


class _ConditionsFieldTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        entity_filter_registries.register(efilter_registry)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        entity_filter_registries.unregister(efilter_registry.id)


class RegularFieldsConditionsFieldTestCase(_ConditionsFieldTestCase):
    @staticmethod
    def build_data(*conditions):
        return json_dump([
            {
                'field':    {'name': condition['name']},
                'operator': {'id': str(condition['operator'])},
                'value':    condition['value'],
            } for condition in conditions
        ])

    def test_clean_empty_required(self):
        field = RegularFieldsConditionsField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='[]')

    def test_clean_empty_not_required(self):
        field = RegularFieldsConditionsField(required=False)

        with self.assertNoException():
            value = field.clean(None)

        self.assertListEqual([], value)

    def test_clean_invalid_data_type(self):
        field = RegularFieldsConditionsField()
        msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidtype', value='"this is a string"',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidtype', value='"{}"',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidtype',
            value=json_dump({'foobar': {'operator': '3', 'name': 'first_name', 'value': 'Rei'}}),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidtype', value='1',
        )

    def test_clean_invalid_data(self):
        self.assertFormfieldError(
            field=RegularFieldsConditionsField(model=FakeContact),
            value=json_dump([{
                'operator': {'id': 'notanumber'},
                'field': {'name': 'first_name'},
                'value': 'Rei',
            }]),
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_incomplete_data_required(self):
        field = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )
        EQUALS = operators.EQUALS
        self.assertFormfieldError(
            field=field,
            value='[{"operator": {"id": "%s"}, "field": {"name": "first_name"}}]' % EQUALS,
            messages=_('This value is invalid.'),
            codes='invalidvalue',
        )
        self.assertFormfieldError(
            field=field,
            value='[{"operator": {"id": "%s"}, "value": "Rei"}]' % EQUALS,
            messages=_('This field is invalid with this model.'),
            codes='invalidfield',
        )
        self.assertFormfieldError(
            field=field,
            value='[{"field": {"name": "first_name"}, "value": "Rei"}]',
            messages=_('This operator is invalid.'),
            codes='invalidoperator',
        )

    def test_clean_invalid_field(self):
        field = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )
        build_data = self.build_data
        msg = _('This field is invalid with this model.')
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidfield',
            value=build_data({
                'operator': operators.EQUALS,
                'name':     '  height',  # <---
                'value':    160,
            }),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidfield',
            value=build_data({
                'operator': operators.IEQUALS,
                'name':     'is_deleted',
                'value':    '"Faye"',
            }),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidfield',
            value=build_data({
                'operator': operators.IEQUALS,
                'name':     'created',
                'value':    '"2011-5-12"',
            }),

        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidfield',
            value=build_data({
                'operator': operators.IEQUALS,
                'name':     'civility__id',
                'value':    5,
            }),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidfield',
            value=build_data({
                'operator': operators.IEQUALS,
                'name':     'image__id',
                'value':    5,
            }),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidfield',
            value=build_data({
                'operator': operators.IEQUALS,
                'name':     'image__is_deleted',
                'value':    5,
            }),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidfield',
            value=build_data({
                'operator': operators.IEQUALS,
                'name':     'image__modified',
                'value':    "2011-5-12",
            }),
        )
        # TODO: M2M

    def test_clean_invalid_operator(self):
        self.assertFormfieldError(
            field=RegularFieldsConditionsField(model=FakeContact),
            value=self.build_data({
                'operator': operators.EQUALS + 1000,  # <--
                'name':     'first_name',
                'value':    'Nana',
            }),
            messages=_('This operator is invalid.'),
            codes='invalidoperator',
        )

    def test_clean_invalid_fk_id(self):
        """FK field with invalid id."""
        self.assertFormfieldError(
            field=RegularFieldsConditionsField(
                model=FakeContact, efilter_type=efilter_registry.id,
            ),
            value=self.build_data({
                'operator': operators.EQUALS,
                'name':     'civility',
                'value':    'unknown',
            }),
            messages=_('Condition on field «{field}»: {error}').format(
                field=_('Civility'),
                error=_(
                    'Select a valid choice. That choice is not one of the available choices.'
                ),
            ),
        )

    def test_clean_invalid_static_choice(self):
        """Static choice field with invalid value."""
        self.assertFormfieldError(
            field=RegularFieldsConditionsField(
                model=FakeInvoiceLine, efilter_type=efilter_registry.id,
            ),
            value=self.build_data({
                'operator': operators.EQUALS,
                'name':     'discount_unit',
                'value':    'unknown',
            }),
            messages=_('Condition on field «{field}»: {error}').format(
                field=_('Discount Unit'),
                error=_(
                    'Select a valid choice. %(value)s is not one of the available choices.'
                ) % {'value': 'unknown'},
            ),
        )

    def test_clean_invalid_many2many_id(self):
        field = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )

        value = 12445
        self.assertFormfieldError(
            field=field,
            value=self.build_data({
                'operator': operators.EQUALS,
                'name':     'languages',
                'value':    f'{value}',
            }),
            messages=_('Condition on field «{field}»: {error}').format(
                field=_('Spoken language(s)'),
                error=_(
                    'Select a valid choice. %(value)s is not one of the available choices.'
                ) % {'value': value},
            ),
        )

    def test_clean_several_invalid_inputs(self):
        field = RegularFieldsConditionsField(
            model=FakeOrganisation, efilter_type=efilter_registry.id,
        )
        error_fmt = _('Condition on field «{field}»: {error}').format
        self.assertFormfieldError(
            field=field,
            value=self.build_data(
                {
                    'operator': operators.EQUALS,
                    'name':     'email',
                    'value':    'not_email',
                }, {
                    'operator': operators.EQUALS,
                    'name':     'url_site',
                    'value':    'not_url',
                },
            ),
            messages=[
                error_fmt(
                    field=_('Email address'),
                    error=_('Enter a valid email address.'),
                ),
                error_fmt(
                    field=_('Web Site'),
                    error=_('Enter a valid URL.'),
                ),
            ],
        )

    def test_iequals_condition(self):
        with self.assertNumQueries(0):
            field = RegularFieldsConditionsField(
                model=FakeContact, efilter_type=efilter_registry.id,
            )

        self.assertEqual(efilter_registry.id, field.efilter_type)
        self.assertIs(efilter_registry,       field.efilter_registry)
        self.assertEqual(efilter_registry.id, field.widget.efilter_type)

        operator = operators.IEQUALS
        name = 'first_name'
        value = 'Faye'
        condition = self.get_alone_element(field.clean(self.build_data({
            'operator': operator, 'name': name, 'value': value,
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertEqual(efilter_registry.id,                  condition.filter_type)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]}, condition.value,
        )

        self.assertJSONEqual(
            raw=field.from_python([condition]),
            expected_data=[{
                'field': {'name': name, 'type': 'string'},
                'operator': {'id': operator, 'types': 'string'},
                'value': value,
            }],
        )

    def test_initialize(self):
        "initialize() + filter_type."
        field = RegularFieldsConditionsField(efilter_type=EF_CREDENTIALS)
        field.initialize(ctype=ContentType.objects.get_for_model(FakeContact))

        operator = operators.IEQUALS
        name = 'first_name'
        value = 'Faye'
        condition = self.get_alone_element(field.clean(self.build_data({
            'operator': operator, 'name': name, 'value': value,
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertEqual(EF_CREDENTIALS,                       condition.filter_type)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]},
            condition.value,
        )

    def test_iequals_condition_multiple_as_string(self):
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.IEQUALS
        name = 'first_name'
        faye_name = 'Faye'
        ed_name = 'Ed'
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator,
            'name':     name,
            'value':    f'{faye_name},{ed_name}',
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [faye_name, ed_name]},
            condition.value,
        )

    def test_iequals_condition_multiple_as_list(self):
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.IEQUALS
        name = 'first_name'
        faye_name = 'Faye'
        ed_name = 'Ed'
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator,
            'name':     name,
            'value':    [faye_name, ed_name],
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [faye_name, ed_name]},
            condition.value,
        )

    def test_isempty_condition(self):
        "ISEMPTY (true) -> boolean."
        field = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )
        operator = operators.ISEMPTY
        name = 'description'
        condition = self.get_alone_element(field.clean(self.build_data({
            'operator': operator,
            'name':     name,
            'value':    True,
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [True]},
            condition.value,
        )

        # TODO: need ordered set for FIELDTYPES_NULLABLE...
        # self.assertJSONEqual(
        #     raw=field.from_python([condition]),
        #     expected_data=[{
        #         'field': {'name': name, 'type': 'string'},
        #         'operator': {
        #             'id': operator,
        #             'types': 'choices__null enum__null boolean__null user__null string fk__null',
        #         },
        #         'value': True,
        #     }],
        # )
        initial = json_load(field.from_python([condition]))
        self.assertIsList(initial, length=1)
        initial0 = initial[0]
        self.assertIsDict(initial0, length=3)
        self.assertDictEqual({'name': name, 'type': 'string'}, initial0.get('field'))
        self.assertIs(initial0.get('value'), True)

    def test_isnotempty_condition(self):
        "ISEMPTY (false) -> boolean."
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.ISEMPTY
        name = 'description'
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator,
            'name':     name,
            'value':    False,
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [False]},
            condition.value,
        )

    def test_equals_boolean_condition(self):
        field = RegularFieldsConditionsField(
            model=FakeOrganisation, efilter_type=efilter_registry.id,
        )
        operator = operators.EQUALS
        name = 'subject_to_vat'
        condition = self.get_alone_element(field.clean(self.build_data({
            'operator': operator, 'name': name, 'value': True,
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [True]}, condition.value,
        )

        # TODO: need ordered set for FIELDTYPES_*...
        # self.assertJSONEqual(
        #     raw=field.from_python([condition]),
        #     expected_data=[{
        #         'field': {'name': name, 'type': 'boolean'},
        #         'operator': {
        #             'id': operator,
        #             'types': '......',
        #         },
        #         'value': True,
        #     }],
        # )
        initial = json_load(field.from_python([condition]))
        self.assertIsList(initial, length=1)
        initial0 = initial[0]
        self.assertIsDict(initial0, length=3)
        self.assertDictEqual({'name': name, 'type': 'boolean'}, initial0.get('field'))
        self.assertIs(initial0.get('value'), True)

    def test_fk_subfield(self):
        "FK subfield."
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.ISTARTSWITH
        name = 'civility__title'
        value = 'Miss'
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator, 'name': name, 'value': value,
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]}, condition.value,
        )

    def test_fk(self):
        "FK field."
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        name = 'civility'
        value = FakeCivility.objects.all()[0].pk
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator, 'name': name, 'value': value,
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [str(value)]}, condition.value,
        )

    def test_multiple_fk_as_string(self):
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        name = 'civility'
        values = [c.pk for c in FakeCivility.objects.all()]
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator,
            'name':     name,
            'value':    ','.join(str(v) for v in values),
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [str(v) for v in values]},
            condition.value,
        )

    def test_multiple_fk_as_list(self):
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        name = 'civility'
        values = [str(c.pk) for c in FakeCivility.objects.all()]
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator, 'name': name, 'value': values,
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [str(v) for v in values]},
            condition.value,
        )

    def test_many2many(self):
        "ManyToMany field."
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        name = 'languages'
        value = Language.objects.all()[0].pk
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator, 'name': name, 'value': value,
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [str(value)]}, condition.value,
        )

    def test_multiple_many2many_as_list(self):
        "ManyToMany field."
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        name = 'languages'
        values = [str(v) for v in Language.objects.all().values_list('pk', flat=True)]
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator,
            'name':     name,
            'value':    values,
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': values}, condition.value,
        )

    def test_multiple_many2many_as_string(self):
        "ManyToMany field."
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        name = 'languages'
        values = Language.objects.all().values_list('pk', flat=True)
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator,
            'name':     name,
            'value':    ','.join(str(v) for v in values),
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {
                'operator': operator,
                'values': [str(v) for v in values],
            },
            condition.value,
        )

    def test_static_choices(self):
        "Static choice field."
        clean = RegularFieldsConditionsField(
            model=FakeInvoiceLine, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        name = 'discount_unit'
        value = FakeInvoiceLine.Discount.AMOUNT
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator,
            'name':     name,
            'value':    value,
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [str(value)]}, condition.value,
        )

    def test_choicetypes(self):
        "Field choice types."
        field_choicetype = FieldConditionSelector.field_choicetype
        get_contact_field = FakeContact._meta.get_field

        civility_field = get_contact_field('civility')
        self.assertTrue(civility_field.get_tag('enumerable'))
        self.assertTrue(civility_field.get_tag(FieldTag.ENUMERABLE))
        self.assertFalse(issubclass(civility_field.remote_field.model, CremeEntity))
        self.assertEqual(field_choicetype(civility_field), 'enum__null')

        self.assertEqual(field_choicetype(get_contact_field('birthday')), 'date__null')
        self.assertEqual(field_choicetype(get_contact_field('created')),  'date')

        self.assertEqual(field_choicetype(get_contact_field('address')),  'fk__null')

        self.assertEqual(field_choicetype(get_contact_field('user')),     'user')
        self.assertEqual(field_choicetype(get_contact_field('is_user')),  'user__null')

        image_field = get_contact_field('image')
        self.assertTrue(image_field.get_tag(FieldTag.ENUMERABLE))
        self.assertIsSubclass(image_field.remote_field.model, CremeEntity)
        self.assertEqual(field_choicetype(image_field), 'fk__null')

        self.assertEqual(field_choicetype(get_contact_field('languages')), 'enum__null')

        discount_unit_field = FakeInvoiceLine._meta.get_field('discount_unit')
        self.assertEqual(field_choicetype(discount_unit_field), 'choices__null')

    def test_iendswith_valuelist(self):
        "Multi values."
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.IENDSWITH
        name = 'last_name'
        values = ['nagi', 'sume']
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator,
            'name':     name,
            'value':    ','.join(values),
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': values}, condition.value,
        )

    def test_multi_conditions(self):
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean

        name1     = 'last_name'
        operator1 = operators.IENDSWITH
        value1    = 'Valentine'

        name2     = 'first_name'
        operator2 = operators.EQUALS
        value2    = 'Faye'

        conditions = clean(self.build_data(
            {
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

        type_id = RegularFieldConditionHandler.type_id
        condition1 = conditions[0]
        self.assertEqual(type_id, condition1.type)
        self.assertEqual(name1,   condition1.name)
        self.assertDictEqual(
            {'operator': operator1, 'values': [value1]},
            condition1.value,
        )

        condition2 = conditions[1]
        self.assertEqual(type_id, condition2.type)
        self.assertEqual(name2,   condition2.name)
        self.assertDictEqual(
            {'operator': operator2, 'values': [value2]},
            condition2.value,
        )

    def test_many2many_subfield(self):
        clean = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.IEQUALS
        name = 'languages__name'
        value = 'French'
        condition = self.get_alone_element(clean(self.build_data({
            'operator': operator, 'name': name, 'value': value,
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                 condition.name)
        self.assertDictEqual(
            {'operator': operator, 'values': [value]}, condition.value,
        )

    def test_fields_config01(self):
        hidden_fname = 'description'

        create_fc = FieldsConfig.objects.create
        create_fc(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )
        create_fc(
            content_type=FakeImage,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        field = RegularFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )

        EQUALS = operators.EQUALS
        data = [{
            'name': 'last_name',
            'operator': EQUALS,
            'value': 'Faye',
        }, {
            'name': 'image__name',
            'operator': EQUALS,
            'value': 'selfie',
        }]

        conditions = field.clean(self.build_data(*data))
        self.assertEqual(2, len(conditions))

        type_id = RegularFieldConditionHandler.type_id
        self.assertEqual(type_id, conditions[0].type)
        self.assertEqual(type_id, conditions[1].type)

        # ------
        data[1]['name'] = hidden_fname
        msg = _('This field is invalid with this model.')
        self.assertFormfieldError(
            field=field, value=self.build_data(*data),
            messages=msg, codes='invalidfield',
        )

        # ------
        data[1]['name'] = f'image__{hidden_fname}'
        self.assertFormfieldError(
            field=field, value=self.build_data(*data),
            messages=msg, codes='invalidfield',
        )

    def test_fields_config02(self):
        "FK hidden => sub-fields hidden."
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('image', {FieldsConfig.HIDDEN: True})],
        )
        self.assertFormfieldError(
            field=RegularFieldsConditionsField(
                model=FakeContact, efilter_type=efilter_registry.id,
            ),
            value=self.build_data({
                'name':     'image__name',
                'operator': operators.EQUALS,
                'value':    'selfie',
            }),
            messages=_('This field is invalid with this model.'),
            codes='invalidfield',
        )

    def test_fields_config03(self):
        "Field is already used => still proposed."
        hidden_fname = 'description'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        field = RegularFieldsConditionsField(efilter_type=efilter_registry.id)
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name=hidden_fname, values=['Ikari'],
                ),
            ],
        )

        condition = self.get_alone_element(field.clean(self.build_data({
            'operator': operators.EQUALS,
            'name':     hidden_fname,
            'value':    'Faye',
        })))
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(hidden_fname,                         condition.name)

    def test_fields_config04(self):
        "Sub-field is already used => still proposed."
        hidden_sfname = 'image__description'
        FieldsConfig.objects.create(
            content_type=FakeImage,
            descriptions=[('description', {FieldsConfig.HIDDEN: True})],
        )

        field = RegularFieldsConditionsField(efilter_type=efilter_registry.id)
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name=hidden_sfname, values=['Ikari'],
                ),
            ],
        )

        with self.assertNoException():
            conditions = field.clean(self.build_data({
                'name':     hidden_sfname,
                'operator': operators.EQUALS,
                'value':    'Faye',
            }))

        condition = self.get_alone_element(conditions)
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(hidden_sfname,                        condition.name)

    def test_fields_config05(self):
        "Sub-field is already used => still proposed (FK hidden)."
        hidden_sfname = 'image__description'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('image', {FieldsConfig.HIDDEN: True})],
        )

        field = RegularFieldsConditionsField(efilter_type=efilter_registry.id)
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name=hidden_sfname, values=['Ikari'],
                ),
            ],
        )

        with self.assertNoException():
            conditions = field.clean(self.build_data({
                'name':     hidden_sfname,
                'operator': operators.EQUALS,
                'value':    'Faye',
            }))

        condition = self.get_alone_element(conditions)
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(hidden_sfname,                        condition.name)

    def test_fields_config06(self):
        "Field (ForeignKey) is already used => still proposed."
        hidden_fname = 'position'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        position = FakePosition.objects.all()[0]
        field = RegularFieldsConditionsField(efilter_type=efilter_registry.id)
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name=hidden_fname, values=[position.id],
                ),
            ],
        )

        with self.assertNoException():
            conditions = field.clean(self.build_data({
                'operator': operators.EQUALS,
                'name':     hidden_fname,
                'value':    str(position.id),
            }))

        condition = self.get_alone_element(conditions)
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(hidden_fname,                         condition.name)

    def test_invalid_field(self):
        field = RegularFieldsConditionsField(
            model=FakeOrganisation, efilter_type=efilter_registry.id,
        )
        condition = self.get_alone_element(field.clean(self.build_data({
            'operator': operators.EQUALS, 'name': 'phone', 'value': True,
        })))
        condition.name = 'invalid'

        with self.assertLogs(level='WARNING') as logs_manager:
            with self.assertNoException():
                raw_json = field.from_python([condition])
        self.assertEqual('[]', raw_json)

        self.assertIn(
            "The condition is invalid & so we ignored it: "
            "FakeOrganisation has no field named 'invalid'",
            logs_manager.output[0],
        )


class DateFieldsConditionsFieldTestCase(_ConditionsFieldTestCase):
    def test_clean_invalid_data(self):
        field = DateFieldsConditionsField(model=FakeContact)
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'field': {'name': 'first_name', 'type': 'string__null'},
                'range': {'type': 'next_quarter', 'start': '2011-5-12'},
            }]),
            messages=_('This field is not a date field for this model.'),
            codes='invalidfield',
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'field': {'name': 'birthday', 'type': 'date__null'},
                'range': 'not a dict',
            }]),
            messages=_('Invalid format'),
            codes='invalidformat',
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'field': {'name': 'birthday', 'type': 'date__null'},
                'range': {'type': 'unknown_range'},
            }]),  # TODO: "start": '' ???
            messages=_('This date range is invalid.'),
            codes='invaliddaterange',
        )

        empty_msg = _('Please enter a start date and/or a end date.')
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'field': {'name': 'birthday', 'type': 'date__null'},
                'range': {'type': ''},
            }]),
            messages=empty_msg, codes='emptydates',
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'field': {'name': 'birthday', 'type': 'date__null'},
                'range': {'type': '', 'start': '', 'end': ''},
            }]),
            messages=empty_msg, codes='emptydates',
        )

        invalid_msg = _('Enter a valid date.')
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'field': {'name': 'created', 'type': 'date'},
                'range': {'type': '', 'start': 'not a date'},
            }]),
            messages=invalid_msg, codes='invalid',
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'field': {'name': 'created', 'type': 'date'},
                'range': {'type': '', 'end': '2011-2-30'},  # 30 february!
            }]),
            messages=invalid_msg, codes='invalid',
        )

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

        type_id = DateRegularFieldConditionHandler.type_id
        condition1 = conditions[0]
        self.assertEqual(type_id, condition1.type)
        self.assertEqual(name01,  condition1.name)
        self.assertEqual(EF_REGULAR, condition1.filter_type)
        self.assertDictEqual({'name': type01}, condition1.value)

        condition2 = conditions[1]
        self.assertEqual(type_id,  condition2.type)
        self.assertEqual(name02,   condition2.name)
        self.assertDictEqual({'name': type02}, condition2.value)

    def test_ok02(self):
        "Start/end + filter_type."
        field = DateFieldsConditionsField(
            model=FakeContact, efilter_type=EF_CREDENTIALS,
        )
        name01 = 'created'
        name02 = 'birthday'
        conditions = field.clean(json_dump([
            {
                'field': {'name': name01, 'type': 'date'},
                'range': {'type': '', 'start': self.formfield_value_date(2011, 5, 12)},
            }, {
                'field': {'name': name02, 'type': 'date__null'},
                'range': {'type': '', 'end': self.formfield_value_date(2012, 6, 13)},
            },
        ]))
        self.assertEqual(2, len(conditions))

        type_id = DateRegularFieldConditionHandler.type_id
        condition1 = conditions[0]
        self.assertEqual(type_id,         condition1.type)
        self.assertEqual(name01,          condition1.name)
        self.assertEqual(EF_CREDENTIALS,  condition1.filter_type)
        self.assertDictEqual(
            {'start': {'year': 2011, 'month': 5, 'day': 12}},
            condition1.value,
        )

        condition2 = conditions[1]
        self.assertEqual(type_id, condition2.type)
        self.assertEqual(name02,  condition2.name)
        self.assertDictEqual(
            {'end': {'year': 2012, 'month': 6, 'day': 13}},
            condition2.value,
        )

    def test_ok03(self):
        "Start + end."
        clean = DateFieldsConditionsField(model=FakeContact).clean
        name = 'modified'
        condition = self.get_alone_element(
            clean(json_dump([{
                'field': {'name': name, 'type': 'date'},
                'range': {
                    'type': '',
                    'start': self.formfield_value_date(2010, 3, 24),
                    'end': self.formfield_value_date(2011, 7, 25),
                },
            }]))
        )
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(name,                                     condition.name)
        self.assertDictEqual(
            {
                'start': {'year': 2010, 'month': 3, 'day': 24},
                'end':   {'year': 2011, 'month': 7, 'day': 25},
            },
            condition.value,
        )

    def test_empty(self):
        clean = DateFieldsConditionsField(model=FakeContact).clean
        conditions = clean(json_dump([
            {
                'field': {'name': 'birthday', 'type': 'date__null'},
                'range': {'type': 'empty',     'start': '', 'end': ''},
            }, {
                'field': {'name': 'modified', 'type': 'date__null'},
                'range': {'type': 'not_empty', 'start': '', 'end': ''},
            },
        ]))
        self.assertEqual(2, len(conditions))

        condition = conditions[0]
        type_id = DateRegularFieldConditionHandler.type_id
        self.assertEqual(type_id,    condition.type)
        self.assertEqual('birthday', condition.name)
        self.assertDictEqual({'name': 'empty'}, condition.value)

        condition = conditions[1]
        self.assertEqual(type_id,    condition.type)
        self.assertEqual('modified', condition.name)
        self.assertDictEqual({'name': 'not_empty'}, condition.value)

    def test_clean_several_errors(self):
        self.assertFormfieldError(
            field=DateFieldsConditionsField(model=FakeContact),
            value=json_dump([
                {
                    'field': {'name': 'birthday', 'type': 'date__null'},
                    'range': {'type': '', 'start': '', 'end': ''},
                }, {
                    'field': {'name': 'modified', 'type': 'date__null'},
                    'range': {'type': '', 'start': '', 'end': ''},
                },
            ]),
            messages=[_('Please enter a start date and/or a end date.')] * 2,
            codes=['emptydates'] * 2,
        )

    def test_fields_config01(self):
        valid_fname  = 'issuing_date'
        hidden_fname = 'expiration_date'
        FieldsConfig.objects.create(
            content_type=FakeInvoice,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        field = DateFieldsConditionsField()
        field.initialize(ctype=ContentType.objects.get_for_model(FakeInvoice))

        def build_data(fname):
            return json_dump([{
                'field': {'name': fname, 'type': 'date__null'},
                'range': {
                    'type': '',
                    'start': self.formfield_value_date(2015, 3, 24),
                    'end':   self.formfield_value_date(2015, 7, 25),
                },
            }])

        condition = self.get_alone_element(field.clean(build_data(valid_fname)))
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(valid_fname,                              condition.name)

        # --------------
        self.assertFormfieldError(
            field=field,
            value=build_data(hidden_fname),
            messages=_('This field is not a date field for this model.'),
            codes='invalidfield',
        )

    def test_fields_config02(self):
        "Sub-fields."
        hidden_fname = 'expiration_date'
        FieldsConfig.objects.create(
            content_type=FakeInvoice,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        valid_fname = 'linked_invoice__issuing_date'

        def build_data(fname):
            return json_dump([{
                'field': {'name': fname, 'type': 'date__null'},
                'range': {
                    'type': '',
                    'start': self.formfield_value_date(2015, 3, 24),
                    'end':   self.formfield_value_date(2015, 7, 25),
                },
            }])

        field = DateFieldsConditionsField(model=FakeInvoiceLine)
        condition = self.get_alone_element(field.clean(build_data(valid_fname)))
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(valid_fname,                              condition.name)

        # --------------
        self.assertFormfieldError(
            field=field, value=build_data(f'linked_invoice__{hidden_fname}'),
            messages=_('This field is not a date field for this model.'),
            codes='invalidfield',
        )

    def test_fields_config03(self):
        "FK hidden => sub-fields hidden."
        hidden_fname = 'exif_date'
        FieldsConfig.objects.create(
            content_type=FakeImage,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )
        self.assertFormfieldError(
            field=DateFieldsConditionsField(model=FakeContact),
            value=json_dump([{
                'field': {'name': f'image__{hidden_fname}', 'type': 'date__null'},
                'range': {
                    'type': '',
                    'start': self.formfield_value_date(2015, 3, 24),
                    'end':   self.formfield_value_date(2015, 7, 25),
                },
            }]),
            messages=_('This field is not a date field for this model.'),
            codes='invalidfield',
        )

    def test_fields_config04(self):
        "Field is already used => still proposed."
        hidden_fname = 'birthday'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        field = DateFieldsConditionsField()
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    field_name=hidden_fname,
                    start=date(year=2000, month=1, day=1),
                ),
            ],
        )

        with self.assertNoException():
            conditions = field.clean(json_dump([{
                'field': {'name': hidden_fname, 'type': 'date__null'},
                'range': {'type': '', 'start': self.formfield_value_date(2000, 1, 1)},
            }]))

        condition = self.get_alone_element(conditions)
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(hidden_fname,                             condition.name)

    def test_fields_config05(self):
        "Sub-field is already used => still proposed."
        hidden_sfname = 'image__exif_date'
        FieldsConfig.objects.create(
            content_type=FakeImage,
            descriptions=[('exif_date', {FieldsConfig.HIDDEN: True})],
        )

        field = DateFieldsConditionsField()
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    field_name=hidden_sfname,
                    start=date(year=2000, month=1, day=1),
                ),
            ],
        )

        with self.assertNoException():
            conditions = field.clean(json_dump([{
                'field': {'name': hidden_sfname, 'type': 'date__null'},
                'range': {'type': '', 'start': self.formfield_value_date(2000, 1, 1)},
            }]))

        condition = self.get_alone_element(conditions)
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(hidden_sfname,                            condition.name)

    def test_fields_config06(self):
        "Sub-field is already used => still proposed (FK hidden)."
        hidden_sfname = 'image__exif_date'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('image', {FieldsConfig.HIDDEN: True})]
        )

        field = DateFieldsConditionsField()
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name=hidden_sfname,
                    start=date(year=2000, month=1, day=1),
                ),
            ],
        )

        with self.assertNoException():
            conditions = field.clean(json_dump([{
                'field': {'name': hidden_sfname, 'type': 'date__null'},
                'range': {'type': '', 'start': self.formfield_value_date(2000, 1, 1)},
            }]))

        condition = self.get_alone_element(conditions)
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(hidden_sfname,                            condition.name)

    def test_initial(self):
        fname1 = 'birthday'
        fname2 = 'modified'
        fname3 = 'created'

        date1 = date(year=2000, month=1, day=1)
        date2 = date(year=2001, month=2, day=2)

        drange3 = 'current_year'

        field = DateFieldsConditionsField()
        build_cond = partial(
            DateRegularFieldConditionHandler.build_condition, model=FakeContact,
        )
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                build_cond(field_name=fname1, start=date1),
                build_cond(field_name=fname2, end=date2),
                build_cond(field_name=fname3,  date_range=drange3),
            ],
        )

        with self.assertNoException():
            decoded_value = json_load(field.widget.from_python(field.initial))

        date_value = self.formfield_value_date
        self.assertListEqual(
            [
                {
                    'field': {'name': fname1, 'type': 'daterange__null'},
                    'range': {
                        'type': '', 'start': date_value(date1), 'end': '',
                    },
                }, {
                    'field': {'name': fname2, 'type': 'daterange'},
                    'range': {
                        'type': '', 'start': '', 'end': date_value(date2),
                    },
                }, {
                    'field': {'name': fname3, 'type': 'daterange'},
                    'range': {'end': '', 'start': '', 'type': drange3},
                },
            ],
            decoded_value,
        )

    def test_invalid_field(self):
        field = DateFieldsConditionsField()

        condition = DateRegularFieldConditionHandler.build_condition(
            model=FakeContact, field_name='created', date_range='current_year',
        )
        condition.name = 'invalid'

        with self.assertLogs(level='WARNING') as logs_manager:
            with self.assertNoException():
                raw_json = field.from_python([condition])
        self.assertEqual('[]', raw_json)

        self.assertIn(
            "The condition is invalid & so we ignored it: "
            "FakeContact has no field named 'invalid'",
            logs_manager.output[0],
        )


class CustomFieldsConditionsFieldTestCase(_ConditionsFieldTestCase):
    # TODO: factorise?
    @staticmethod
    def build_data(*conditions):
        return json_dump([
            {
                'field':    {'id': condition['field']},
                'operator': {'id': str(condition['operator'])},
                'value':    condition['value'],
            } for condition in conditions
        ])

    # TODO: setUpClass?
    def setUp(self):
        super().setUp()

        ct = ContentType.objects.get_for_model(FakeContact)
        create_cfield = partial(CustomField.objects.create, content_type=ct)
        self.cfield_int       = create_cfield(name='Size',      field_type=CustomField.INT)
        self.cfield_bool      = create_cfield(name='Valid',     field_type=CustomField.BOOL)
        self.cfield_str       = create_cfield(name='Name',      field_type=CustomField.STR)
        self.cfield_datetime  = create_cfield(name='Datetime',  field_type=CustomField.DATETIME)
        self.cfield_date      = create_cfield(name='Date',      field_type=CustomField.DATE)
        self.cfield_float     = create_cfield(name='Number',    field_type=CustomField.FLOAT)
        self.cfield_enum      = create_cfield(name='Enum',      field_type=CustomField.ENUM)
        self.cfield_multienum = create_cfield(name='MultiEnum', field_type=CustomField.MULTI_ENUM)

        create_evalue = partial(
            CustomFieldEnumValue.objects.create,
            custom_field=self.cfield_enum,
        )
        self.cfield_enum_A = create_evalue(value='A')
        self.cfield_enum_B = create_evalue(value='B')
        self.cfield_enum_C = create_evalue(value='C')

        create_evalue = partial(
            CustomFieldEnumValue.objects.create,
            custom_field=self.cfield_multienum,
        )
        self.cfield_multienum_F = create_evalue(value='F')
        self.cfield_multienum_G = create_evalue(value='G')
        self.cfield_multienum_H = create_evalue(value='H')

    @staticmethod
    def _get_allowed_types(operator_id):
        return ' '.join(efilter_registry.get_operator(operator_id).allowed_fieldtypes)

    def test_choices(self):
        field = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )
        cfields = [*field.widget.fields]
        self.assertInChoices(value=self.cfield_int.id,   label=self.cfield_int,   choices=cfields)
        self.assertInChoices(value=self.cfield_bool.id,  label=self.cfield_bool,  choices=cfields)
        self.assertInChoices(value=self.cfield_str.id,   label=self.cfield_str,   choices=cfields)
        self.assertInChoices(value=self.cfield_float.id, label=self.cfield_float, choices=cfields)
        self.assertInChoices(value=self.cfield_enum.id,  label=self.cfield_enum,  choices=cfields)
        self.assertInChoices(
            value=self.cfield_multienum.id, label=self.cfield_multienum, choices=cfields,
        )

        self.assertNotInChoices(value=self.cfield_datetime.id, choices=cfields)
        self.assertNotInChoices(value=self.cfield_date.id,     choices=cfields)

    def test_frompython_custom_int(self):
        EQUALS = operators.EQUALS
        field = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )
        condition = CustomFieldConditionHandler.build_condition(
            custom_field=self.cfield_int, operator=EQUALS, values=[150],
        )
        self.assertListEqual(
            [{
                'field': {'id': self.cfield_int.id, 'type': 'number__null'},
                'operator': {
                    'id': EQUALS,
                    'types': self._get_allowed_types(EQUALS),
                },
                'value': '150',
            }],
            field._value_to_jsonifiable([condition]),
        )

    def test_frompython_custom_string(self):
        EQUALS = operators.EQUALS
        field = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )
        condition = CustomFieldConditionHandler.build_condition(
            custom_field=self.cfield_str, operator=EQUALS, values=['abc'],
        )
        self.assertListEqual(
            [{
                'field': {'id': self.cfield_str.id, 'type': 'string'},
                'operator': {
                    'id': EQUALS,
                    'types': self._get_allowed_types(EQUALS),
                },
                'value': 'abc',
            }],
            field._value_to_jsonifiable([condition]),
        )

    def test_frompython_custom_bool(self):
        EQUALS = operators.EQUALS
        field = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )
        condition = CustomFieldConditionHandler.build_condition(
            custom_field=self.cfield_bool, operator=EQUALS, values=[False],
        )
        self.assertListEqual(
            [{
                'field': {'id': self.cfield_bool.id, 'type': 'boolean__null'},
                'operator': {
                    'id': EQUALS,
                    'types': self._get_allowed_types(EQUALS),
                },
                'value': 'false',
            }],
            field._value_to_jsonifiable([condition]),
        )

        # Old format
        condition = CustomFieldConditionHandler.build_condition(
            custom_field=self.cfield_bool, operator=EQUALS, values=['False'],
        )
        self.assertListEqual(
            [{
                'field': {'id': self.cfield_bool.id, 'type': 'boolean__null'},
                'operator': {
                    'id': EQUALS,
                    'types': self._get_allowed_types(EQUALS),
                },
                'value': 'false',
            }],
            field._value_to_jsonifiable([condition]),
        )

    def test_frompython_custom_enum(self):
        EQUALS = operators.EQUALS
        field = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )
        condition = CustomFieldConditionHandler.build_condition(
            custom_field=self.cfield_enum, operator=EQUALS,
            values=[self.cfield_enum_A.id],
        )
        self.assertListEqual(
            [{
                'field': {'id': self.cfield_enum.id, 'type': 'enum__null'},
                'operator': {
                    'id': EQUALS,
                    'types': self._get_allowed_types(EQUALS),
                },
                'value': str(self.cfield_enum_A.id),
            }],
            field._value_to_jsonifiable([condition]),
        )

    def test_clean_invalid_data_format(self):
        self.assertFormfieldError(
            field=CustomFieldsConditionsField(
                model=FakeContact, efilter_type=efilter_registry.id,
            ),
            value=self.build_data({
                'field':    'notanumber',
                'operator': operators.EQUALS,
                'value':    170,
            }),
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_invalid_field(self):
        field = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )
        msg = _('This custom field is invalid with this model.')
        self.assertFormfieldError(
            field=field,
            value=self.build_data({
                'field':    2054,
                'operator': operators.EQUALS,
                'value':    170,
            }),
            messages=msg,
            codes='invalidcustomfield',
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'operator': {'id': str(operators.EQUALS)},
                'value': [170],
            }]),
            messages=msg,
            codes='invalidcustomfield',
        )

    def test_clean_invalid_operator(self):
        field = CustomFieldsConditionsField(model=FakeContact)

        cfield = self.cfield_int
        value = 170
        msg = _('This operator is invalid.')
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidoperator',
            value=self.build_data({
                'field':    cfield.id,
                'operator': 121266,
                'value':    value,
            }),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidoperator',
            value=json_dump([
                {'field': {'id': str(cfield.id)}, 'value': value},
            ]),
        )

    def test_clean_missing_value(self):
        self.assertFormfieldError(
            field=CustomFieldsConditionsField(
                model=FakeContact, efilter_type=efilter_registry.id,
            ),
            value=json_dump([{
                'field':    {'id': str(self.cfield_int.id)},
                'operator': {'id': str(operators.EQUALS)},
            }]),
            messages=_('This value is invalid.'),
            codes='invalidvalue',
        )

    def test_clean_integer01(self):
        with self.assertNumQueries(0):
            field = CustomFieldsConditionsField(
                model=FakeContact, efilter_type=efilter_registry.id,
            )

        operator = operators.EQUALS
        value = 180
        condition = self.get_alone_element(
            field.clean(self.build_data({
                'field': self.cfield_int.id,
                'operator': operator,
                'value': value,
            }))
        )
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(self.cfield_int.uuid),           condition.name)
        self.assertEqual(efilter_registry.id,                 condition.filter_type)
        self.assertDictEqual(
            {
                'operator': operator,
                'rname': 'customfieldinteger',
                'values': [str(value)],
            },
            condition.value,
        )

    def test_clean_integer02(self):
        "'model' property + filter_type."
        with self.assertNumQueries(0):
            field = CustomFieldsConditionsField(efilter_type=EF_CREDENTIALS)
            field.model = FakeContact

        cfield = self.cfield_int
        operator = operators.EQUALS
        value = 180
        condition = self.get_alone_element(
            field.clean(self.build_data({
                'field':    cfield.id,
                'operator': operator,
                'value':    value,
            }))
        )
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(cfield.uuid),                    condition.name)
        self.assertEqual(EF_CREDENTIALS,                      condition.filter_type)
        self.assertDictEqual(
            {
                'operator': operator,
                'rname': 'customfieldinteger',
                'values': [str(value)],
            },
            condition.value,
        )

    def test_clean_integer_error(self):
        "Invalid value."
        field = CustomFieldsConditionsField(efilter_type=efilter_registry.id)
        field.model = FakeContact

        cfield = self.cfield_int

        self.assertFormfieldError(
            field=field,
            value=self.build_data({
                'field':    cfield.id,
                'operator': operators.EQUALS,
                'value':    'Nan',
            }),
            messages=_('Condition on field «{field}»: {error}').format(
                field=cfield.name,
                error=_('Enter a whole number.'),
            ),
        )

    def test_clean_enum(self):
        clean = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        value = str(self.cfield_enum_A.pk)
        condition = self.get_alone_element(
            clean(self.build_data({
                'field':    self.cfield_enum.id,
                'operator': operator,
                'value':    value,
            }))
        )
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(self.cfield_enum.uuid),          condition.name)
        self.assertDictEqual(
            {
                'operator': operator,
                'rname': 'customfieldenum',
                'values': [value],
            },
            condition.value,
        )

    def test_clean_enum_as_string(self):
        clean = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        condition = self.get_alone_element(
            clean(self.build_data({
                'field':    self.cfield_enum.id,
                'operator': operator,
                'value':    f'{self.cfield_enum_A.pk},{self.cfield_enum_B.pk}',
            }))
        )
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(self.cfield_enum.uuid),          condition.name)
        self.assertDictEqual(
            {
                'operator': operator,
                'rname': 'customfieldenum',
                'values': [
                    str(self.cfield_enum_A.pk),
                    str(self.cfield_enum_B.pk)
                ],
            },
            condition.value,
        )

    def test_clean_enum_as_list(self):
        clean = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        condition = self.get_alone_element(
            clean(self.build_data({
                'field':    self.cfield_enum.id,
                'operator': operator,
                'value':    [self.cfield_enum_A.pk, self.cfield_enum_B.pk],
            }))
        )
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(self.cfield_enum.uuid),          condition.name)
        self.assertDictEqual(
            {
                'operator': operator,
                'rname': 'customfieldenum',
                'values': [
                    str(self.cfield_enum_A.pk),
                    str(self.cfield_enum_B.pk),
                ],
            },
            condition.value,
        )

    def test_clean_multienum(self):
        clean = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        value = str(self.cfield_multienum_F.pk)
        condition = self.get_alone_element(clean(self.build_data({
            'field': self.cfield_multienum.id,
            'operator': operator,
            'value': value,
        })))
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(self.cfield_multienum.uuid),     condition.name)
        self.assertDictEqual(
            {
                'operator': operator,
                'rname': 'customfieldmultienum',
                'values': [value],
            },
            condition.value,
        )

    def test_clean_multienum_as_string(self):
        clean = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        condition = self.get_alone_element(
            clean(self.build_data({
                'field': self.cfield_multienum.id,
                'operator': operator,
                'value': f'{self.cfield_multienum_F.pk},{self.cfield_multienum_H.pk}',
            }))
        )
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(self.cfield_multienum.uuid),     condition.name)
        self.assertDictEqual(
            {
                'operator': operator,
                'rname': 'customfieldmultienum',
                'values': [
                    str(self.cfield_multienum_F.pk),
                    str(self.cfield_multienum_H.pk)
                ],
            },
            condition.value,
        )

    def test_clean_multienum_as_list(self):
        clean = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        cfield = self.cfield_multienum
        operator = operators.EQUALS
        condition = self.get_alone_element(clean(self.build_data({
            'field': cfield.id,
            'operator': operator,
            'value': [
                self.cfield_multienum_F.pk,
                self.cfield_multienum_H.pk,
            ],
        })))
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(cfield.uuid),                    condition.name)
        self.assertDictEqual(
            {
                'operator': operator,
                'rname': 'customfieldmultienum',
                'values': [
                    str(self.cfield_multienum_F.pk),
                    str(self.cfield_multienum_H.pk),
                ],
            },
            condition.value,
        )

    def test_clean_empty_string(self):
        clean = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        operator = operators.EQUALS
        condition = self.get_alone_element(clean(self.build_data({
            'field':    self.cfield_str.id,
            'operator': operator,
            'value':    '',
        })))
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(self.cfield_str.uuid),           condition.name)
        self.assertDictEqual(
            {'operator': operator, 'rname': 'customfieldstring', 'values': []},
            condition.value,
        )

    def test_clean_bad_cfield_types(self):
        field = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )
        msg = _('This custom field is invalid with this model.')
        self.assertFormfieldError(
            field=field,
            value=self.build_data({
                'field': self.cfield_datetime.id,
                'operator': operators.EQUALS,
                'value': '',
            }),
            messages=msg, codes='invalidcustomfield',
        )
        self.assertFormfieldError(
            field=field,
            value=self.build_data({
                'field': self.cfield_date.id,
                'operator': operators.EQUALS,
                'value': '',
            }),
            messages=msg, codes='invalidcustomfield',
        )

    def test_clean_several_invalid_inputs(self):
        field = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        )
        error_fmt = _('Condition on field «{field}»: {error}').format
        self.assertFormfieldError(
            field=field,
            value=self.build_data(
                {
                    'field': self.cfield_int.id,
                    'operator': operators.EQUALS,
                    'value': 'Nan',
                }, {
                    'field': self.cfield_float.id,
                    'operator': operators.EQUALS,
                    'value': 'Nan',
                },
            ),
            messages=[
                error_fmt(
                    field=self.cfield_int.name,
                    error=_('Enter a whole number.'),
                ),
                error_fmt(
                    field=self.cfield_float.name,
                    error=_('Enter a number.'),
                ),
            ],
        )

    def test_equals_boolean_condition(self):
        clean = CustomFieldsConditionsField(
            model=FakeContact, efilter_type=efilter_registry.id,
        ).clean
        cfield = self.cfield_bool
        operator = operators.EQUALS
        condition = self.get_alone_element(clean(self.build_data({
            'field': cfield.id,
            'operator': operator,
            'value': False,
        })))
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(cfield.uuid),                    condition.name)
        self.assertDictEqual(
            {'operator': operator, 'rname': 'customfieldboolean', 'values': ['False']},
            condition.value,
        )

    def test_customfield_choicetype(self):
        """custom field choice types."""
        field_choicetype = CustomFieldConditionSelector.customfield_choicetype

        self.assertEqual(field_choicetype(self.cfield_enum),     'enum__null')
        self.assertEqual(field_choicetype(self.cfield_datetime), 'date__null')
        self.assertEqual(field_choicetype(self.cfield_date),     'date__null')
        self.assertEqual(field_choicetype(self.cfield_bool),     'boolean__null')
        self.assertEqual(field_choicetype(self.cfield_int),      'number__null')
        self.assertEqual(field_choicetype(self.cfield_float),    'number__null')

    def test_render_empty(self):
        widget = CustomFieldsConditionsWidget()
        self.assertHTMLEqual(
            f'<input type="text" name="test" style="display:none;">'
            f'<span>{_("No custom field at present.")}</span>',
            widget.render('test', ''),
        )

    def test_deleted01(self):
        cfield_str = self.cfield_str
        cfield_str.is_deleted = True
        cfield_str.save()

        self.assertFormfieldError(
            field=CustomFieldsConditionsField(
                efilter_type=efilter_registry.id, model=FakeContact,
            ),
            value=self.build_data({
                'field': cfield_str.id,
                'operator': operators.ICONTAINS,
                'value': '[pilot]',
            }),
            messages=_('This custom field is invalid with this model.'),
            codes='invalidcustomfield',
        )

    def test_deleted02(self):
        "Deleted Custom-field is already used => still proposed."
        cfield_str = self.cfield_str
        cfield_str.is_deleted = True
        cfield_str.save()

        field = CustomFieldsConditionsField(
            efilter_type=efilter_registry.id, model=FakeContact
        )
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                CustomFieldConditionHandler.build_condition(
                    custom_field=cfield_str,
                    operator=operators.CONTAINS,
                    values=['(pilot)'],
                ),
            ],
        )

        operator = operators.ICONTAINS
        value = '[pilot]'
        condition = self.get_alone_element(field.clean(self.build_data({
            'field': cfield_str.id,
            'operator': operator,
            'value': value,
        })))
        self.assertEqual(CustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(cfield_str.uuid),                condition.name)
        self.assertDictEqual(
            {
                'operator': operator,
                'rname': 'customfieldstring',
                'values': [str(value)],
            },
            condition.value,
        )


class DateCustomFieldsConditionsFieldTestCase(_ConditionsFieldTestCase):
    def setUp(self):
        super().setUp()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        self.cfield01 = create_cfield(name='Day',          field_type=CustomField.DATE)
        self.cfield02 = create_cfield(name='First flight', field_type=CustomField.DATETIME)

    def test_clean_invalid_data(self):
        field = DateCustomFieldsConditionsField(model=FakeContact)
        self.assertFormfieldError(
            field=field,
            value='[{"field": "2054", "range": {"type": "current_year"}}]',
            messages=_('This date custom field is invalid with this model.'),
            codes='invalidcustomfield',
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump([{'field': str(self.cfield01.id), 'range': 'not a dict'}]),
            messages=_('Invalid format'),
            codes='invalidformat',
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'field': str(self.cfield01.id),
                'range': {'type': 'unknown_range'}},
            ]),
            messages=_('This date range is invalid.'),
            codes='invaliddaterange',
        )

        msg = _('Please enter a start date and/or a end date.')
        self.assertFormfieldError(
            field=field,
            value=json_dump([{'field': str(self.cfield01.id), 'range': {'type': ''}}]),
            messages=msg, codes='emptydates',
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'field': str(self.cfield01.id),
                'range': {'type': '', 'start': '', 'end': ''},
            }]),
            messages=msg, codes='emptydates',
        )

    def test_clean_several_errors(self):
        msg = _('Please enter a start date and/or a end date.')
        self.assertFormfieldError(
            field=DateCustomFieldsConditionsField(model=FakeContact),
            value=json_dump([
                {
                    'field': str(self.cfield01.id),
                    'range': {'type': '', 'start': '', 'end': ''},
                }, {
                    'field': str(self.cfield02.id),
                    'range': {'type': '', 'start': '', 'end': ''},
                },
            ]),
            messages=[msg, msg],
        )

    def test_ok(self):
        with self.assertNumQueries(0):
            field = DateCustomFieldsConditionsField(model=FakeContact)

        range_type = 'current_year'
        cfield01 = self.cfield01
        cfield02 = self.cfield02
        date_value = self.formfield_value_date
        conditions = field.clean(json_dump([
            {'field': str(cfield01.id), 'range': {'type': range_type}},
            {'field': str(cfield02.id), 'range': {'type': '', 'start': date_value(2011, 5, 12)}},
            {'field': str(cfield01.id), 'range': {'type': '', 'end': date_value(2012, 6, 13)}},
            {
                'field': str(cfield02.id),
                'range': {
                    'type': '', 'start': date_value(2011, 5, 12), 'end': date_value(2012, 6, 13),
                },
            },
        ]))
        self.assertEqual(4, len(conditions))

        type_id = DateCustomFieldConditionHandler.type_id
        condition1 = conditions[0]
        self.assertEqual(type_id,            condition1.type)
        self.assertEqual(str(cfield01.uuid), condition1.name)
        self.assertEqual(EF_REGULAR,         condition1.filter_type)
        self.assertDictEqual(
            {'rname': 'customfielddate', 'name': range_type},
            condition1.value,
        )

        condition2 = conditions[1]
        self.assertEqual(type_id,            condition2.type)
        self.assertEqual(str(cfield02.uuid), condition2.name)
        self.assertDictEqual(
            {
                'rname': 'customfielddatetime',
                'start': {'year': 2011, 'month': 5, 'day': 12},
            },
            condition2.value,
        )

        condition3 = conditions[2]
        self.assertEqual(type_id,            condition3.type)
        self.assertEqual(str(cfield01.uuid), condition3.name)
        self.assertDictEqual(
            {
                'rname': 'customfielddate',
                'end': {'year': 2012, 'month': 6, 'day': 13},
            },
            condition3.value,
        )

        condition4 = conditions[3]
        self.assertEqual(type_id,            condition4.type)
        self.assertEqual(str(cfield02.uuid), condition4.name)
        self.assertDictEqual(
            {
                'rname': 'customfielddatetime',
                'start': {'year': 2011, 'month': 5, 'day': 12},
                'end':   {'year': 2012, 'month': 6, 'day': 13},
            },
            condition4.value,
        )

    def test_empty(self):
        "Empty operator + filter_type."
        with self.assertNumQueries(0):
            field = DateCustomFieldsConditionsField(efilter_type=EF_CREDENTIALS)
            field.model = FakeContact

        conditions = field.clean(json_dump([
            {'field': str(self.cfield01.id), 'range': {'type': 'empty'}},
            {'field': str(self.cfield02.id), 'range': {'type': 'not_empty'}},
        ]))
        self.assertEqual(2, len(conditions))

        type_id = DateCustomFieldConditionHandler.type_id
        condition = conditions[0]
        self.assertEqual(type_id,                 condition.type)
        self.assertEqual(str(self.cfield01.uuid), condition.name)
        self.assertEqual(EF_CREDENTIALS,          condition.filter_type)
        self.assertDictEqual(
            {'rname': 'customfielddate', 'name': 'empty'},
            condition.value,
        )

        condition = conditions[1]
        self.assertEqual(type_id,                 condition.type)
        self.assertEqual(str(self.cfield02.uuid), condition.name)
        self.assertDictEqual(
            {'rname': 'customfielddatetime', 'name': 'not_empty'},
            condition.value,
        )

    def test_render_empty(self):
        widget = DateCustomFieldsConditionsWidget()

        self.assertHTMLEqual(
            f'<input type="text" name="test" style="display:none;">'
            f'<span>{_("No date custom field at present.")}</span>',
            widget.render('test', ''),
        )

    def test_deleted01(self):
        cfield = self.cfield01
        cfield.is_deleted = True
        cfield.save()

        self.assertFormfieldError(
            field=DateCustomFieldsConditionsField(model=FakeContact),
            value=json_dump([
                {'field': str(cfield.id), 'range': {'type': 'current_year'}},
            ]),
            messages=_('This date custom field is invalid with this model.'),
            codes='invalidcustomfield',
        )

    def test_deleted02(self):
        "Deleted Custom-field is already used => still proposed."
        cfield = self.cfield01
        cfield.is_deleted = True
        cfield.save()

        field = DateCustomFieldsConditionsField(model=FakeContact)
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                DateCustomFieldConditionHandler.build_condition(
                    custom_field=cfield,
                    start=date(year=2020, month=1, day=1),
                ),
            ],
        )

        condition = self.get_alone_element(
            field.clean(json_dump([
                {'field': str(cfield.id), 'range': {'type': 'current_year'}},
            ]))
        )
        self.assertEqual(DateCustomFieldConditionHandler.type_id, condition.type)
        self.assertEqual(str(cfield.uuid),                        condition.name)


class PropertiesConditionsFieldTestCase(_ConditionsFieldTestCase):
    def setUp(self):
        super().setUp()

        create_ptype = CremePropertyType.objects.create
        self.ptype01 = create_ptype(text='Is active')
        self.ptype02 = create_ptype(text='Is cute').set_subject_ctypes(FakeContact)
        self.ptype03 = create_ptype(text='Is evil').set_subject_ctypes(FakeOrganisation)

    def test_clean_empty_required(self):
        with self.assertNumQueries(0):
            field = PropertiesConditionsField(required=True)

        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='[]')

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            PropertiesConditionsField(required=False).clean(None)

    def test_clean_invalid_data_type(self):
        field = PropertiesConditionsField(model=FakeContact)
        msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, value='"this is a string"', messages=msg, codes='invalidtype',
        )
        self.assertFormfieldError(
            field=field, value='"{}"', messages=msg, codes='invalidtype',
        )
        self.assertFormfieldError(
            field=field,
            value='{"foobar":{"ptype": "test-foobar", "has": true}}',
            messages=msg, codes='invalidtype',
        )

    def test_clean_incomplete_data_required(self):
        field = PropertiesConditionsField(model=FakeContact)
        msg = _('This field is required.')
        self.assertFormfieldError(
            field=field,
            value=json_dump([{'ptype': self.ptype01.id}]),
            messages=msg, codes='required',
        )
        self.assertFormfieldError(
            field=field, codes='required', messages=msg, value='[{"has": true}]',
        )

    def test_unknown_ptype(self):
        self.assertFormfieldError(
            field=PropertiesConditionsField(model=FakeContact),
            value=json_dump([{'ptype': self.ptype03.id, 'has': True}]),
            messages=_('This property type is invalid with this model.'),
            codes='invalidptype',
        )

    def test_ok01(self):
        with self.assertNumQueries(0):
            field = PropertiesConditionsField(model=FakeContact)

        conditions = field.clean(json_dump([
            {'ptype': self.ptype01.id, 'has': True},
            {'ptype': self.ptype02.id, 'has': False},
        ]))
        self.assertEqual(2, len(conditions))

        type_id = PropertyConditionHandler.type_id
        condition1 = conditions[0]
        self.assertEqual(type_id,         condition1.type)
        self.assertEqual(str(self.ptype01.uuid), condition1.name)
        self.assertDictEqual({'has': True}, condition1.value)

        condition2 = conditions[1]
        self.assertEqual(type_id,                condition2.type)
        self.assertEqual(str(self.ptype02.uuid), condition2.name)
        self.assertEqual(EF_REGULAR,             condition2.filter_type)
        self.assertDictEqual({'has': False}, condition2.value)

    def test_ok02(self):
        ptype = self.ptype01

        with self.assertNumQueries(0):
            field = PropertiesConditionsField(efilter_type=EF_CREDENTIALS)
            field.model = FakeContact

        condition = self.get_alone_element(
            field.clean(json_dump([{'ptype': ptype.id, 'has': True}]))
        )
        self.assertEqual(PropertyConditionHandler.type_id, condition.type)
        self.assertEqual(str(ptype.uuid),                  condition.name)
        self.assertEqual(EF_CREDENTIALS,                   condition.filter_type)

    def test_disabled_ptype01(self):
        "Disabled type are ignored."
        ptype = self.ptype01
        ptype.enabled = False
        ptype.save()

        self.assertFormfieldError(
            field=PropertiesConditionsField(model=FakeContact),
            value=json_dump([{'ptype': ptype.id, 'has': True}]),
            messages=_('This property type is invalid with this model.'),
            codes='invalidptype',
        )

    def test_disabled_ptype02(self):
        "Disabled type but already used => not ignored."
        ptype = self.ptype01
        ptype.enabled = False
        ptype.save()

        field = PropertiesConditionsField(model=FakeContact)
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                PropertyConditionHandler.build_condition(
                    model=FakeContact, ptype=ptype,
                ),
            ],
        )

        condition = self.get_alone_element(
            field.clean(json_dump([{'ptype': ptype.id, 'has': True}]))
        )
        self.assertEqual(str(ptype.uuid), condition.name)
        self.assertDictEqual({'has': True}, condition.value)


class RelationsConditionsFieldTestCase(_ConditionsFieldTestCase):
    def _create_rtype(self, **kwargs):
        return RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving', models=[FakeContact],
            **kwargs
        ).symmetric(
            id='test-object_love', predicate='Is loved by',
        ).get_or_create()[0]

    def test_clean_empty_required(self):
        field = RelationsConditionsField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='[]')

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            RelationsConditionsField(required=False).clean(None)

    def test_clean_invalid_data_type(self):
        field = RelationsConditionsField(model=FakeContact)
        msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidtype', value='"this is a string"',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidtype', value='"{}"',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidtype',
            value=json_dump({'foobar': {'rtype': 'test-foobar', 'has': True}}),
        )

    def test_clean_invalid_data(self):
        rt_id = self._create_rtype().id
        field = RelationsConditionsField(model=FakeContact)
        msg = _('Invalid format')
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidformat',
            value=json_dump([{'rtype': rt_id, 'has': True, 'ctype': 'not an int'}]),
        )

        ct = ContentType.objects.get_for_model(FakeContact)
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidformat',
            value=json_dump([
                {'rtype': rt_id, 'has': True, 'ctype': ct.id, 'entity': 'not an int'},
            ]),
        )

    def test_clean_incomplete_data_required(self):
        field = RelationsConditionsField(model=FakeContact)
        rt_id = self._create_rtype().id
        msg = _('This field is required.')
        self.assertFormfieldError(
            field=field, messages=msg, codes='required',
            value=json_dump([{'rtype': rt_id}]),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='required',
            value=json_dump([{'has': True}]),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='required',
            value=json_dump([{'rtype': rt_id, 'has': 'not a boolean'}]),
        )

    def test_unknown_ct(self):
        rtype = self._create_rtype()
        self.assertFormfieldError(
            field=RelationsConditionsField(model=FakeContact),
            value=json_dump([{'rtype': rtype.id, 'has': True, 'ctype': 2121545}]),
            messages=_('This content type is invalid.'),
            codes='invalidct',
        )

    def test_unknown_entity(self):
        rtype = self._create_rtype()
        ct = ContentType.objects.get_for_model(FakeContact)
        self.assertFormfieldError(
            field=RelationsConditionsField(model=FakeContact),
            value=json_dump([
                {'rtype': rtype.id, 'has': True, 'ctype': ct.id, 'entity': 2121545},
            ]),
            messages=_('This entity is invalid.'),
            codes='invalidentity',
        )

    def test_ok01(self):
        "No CT, no object entity."
        rtype1 = self._create_rtype()
        rtype2 = rtype1.symmetric_type

        with self.assertNumQueries(0):
            field = RelationsConditionsField(model=FakeContact)

        conditions = field.clean(json_dump([
            {'rtype': rtype1.id, 'has': True,  'ctype': 0, 'entity': None},
            {'rtype': rtype2.id, 'has': False, 'ctype': 0, 'entity': None},
        ]))
        self.assertEqual(2, len(conditions))

        type_id = RelationConditionHandler.type_id
        condition1 = conditions[0]
        self.assertEqual(type_id,   condition1.type)
        self.assertEqual(rtype1.id, condition1.name)
        self.assertEqual(EF_REGULAR, condition1.filter_type)
        self.assertDictEqual({'has': True}, condition1.value)

        condition2 = conditions[1]
        self.assertEqual(type_id,   condition2.type)
        self.assertEqual(rtype2.id, condition2.name)
        self.assertDictEqual({'has': False},  condition2.value)

        # ---
        self.assertListEqual(
            [
                {
                    'has':    'true',
                    'rtype':  rtype1.id,
                    'ctype':  0,
                    'entity': None,
                }, {
                    'has':    'false',
                    'rtype':  rtype2.id,
                    'ctype':  0,
                    'entity': None,
                },
            ],
            json_load(field.from_python(conditions)),
        )

    def test_ok02(self):
        "Wanted CT + filter_type."
        rtype1 = self._create_rtype()
        rtype2 = rtype1.symmetric_type

        field = RelationsConditionsField(
            model=FakeContact, efilter_type=EF_CREDENTIALS,
        )
        ct_id = ContentType.objects.get_for_model(FakeContact).id
        conditions = field.clean(json_dump([
            {'rtype': rtype1.id, 'has': True,  'ctype': ct_id, 'entity': None},
            {'rtype': rtype2.id, 'has': False, 'ctype': ct_id},
        ]))
        self.assertEqual(2, len(conditions))

        type_id = RelationConditionHandler.type_id
        condition1 = conditions[0]
        self.assertEqual(type_id,        condition1.type)
        self.assertEqual(rtype1.id,      condition1.name)
        self.assertEqual(EF_CREDENTIALS, condition1.filter_type)
        self.assertDictEqual({'has': True, 'ct': 'creme_core.fakecontact'}, condition1.value)

        condition2 = conditions[1]
        self.assertEqual(type_id,   condition2.type)
        self.assertEqual(rtype2.id, condition2.name)
        self.assertDictEqual({'has': False, 'ct': 'creme_core.fakecontact'}, condition2.value)

        # ---
        self.assertListEqual(
            [
                {
                    'has':    'true',
                    'rtype':  rtype1.id,
                    'ctype':  ct_id,
                    'entity': None,
                }, {
                    'has':    'false',
                    'rtype':  rtype2.id,
                    'ctype':  ct_id,
                    'entity': None,
                },
            ],
            json_load(field.from_python(conditions)),
        )

    def test_ok03(self):
        "Wanted entity."
        rtype = self._create_rtype()
        user = self.get_root_user()

        naru = FakeContact.objects.create(user=user, first_name='Naru', last_name='Narusegawa')
        field = RelationsConditionsField(model=FakeContact)
        ct = ContentType.objects.get_for_model(FakeContact)
        conditions = field.clean(json_dump([
            {'rtype': rtype.id, 'has': True, 'ctype': ct.id, 'entity': str(naru.id)},
        ]))
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(RelationConditionHandler.type_id, condition.type)
        self.assertEqual(rtype.id,                         condition.name)
        self.assertDictEqual({'has': True, 'entity': str(naru.uuid)}, condition.value)

        # ---
        self.assertListEqual(
            [{
                'has':    'true',
                'rtype':  rtype.id,
                'ctype':  ct.id,
                'entity': naru.id,
            }],
            json_load(field.from_python(conditions)),
        )

    def test_ok04(self):
        "Wanted CT + wanted entity."
        rtype1 = self._create_rtype()
        rtype2 = rtype1.symmetric_type
        user = self.get_root_user()

        ct_id = ContentType.objects.get_for_model(FakeContact).id
        naru = FakeContact.objects.create(user=user, first_name='Naru', last_name='Narusegawa')
        field = RelationsConditionsField(model=FakeContact)
        conditions = field.clean(json_dump([
            {'rtype': rtype1.id, 'has': True,  'ctype': ct_id, 'entity': None},
            {'rtype': rtype2.id, 'has': False, 'ctype': ct_id, 'entity': str(naru.id)},
        ]))
        self.assertEqual(2, len(conditions))

        type_id = RelationConditionHandler.type_id
        condition = conditions[0]
        self.assertEqual(type_id,   condition.type)
        self.assertEqual(rtype1.id, condition.name)
        self.assertDictEqual({'has': True, 'ct': 'creme_core.fakecontact'}, condition.value)

        condition = conditions[1]
        self.assertEqual(type_id,   condition.type)
        self.assertEqual(rtype2.id, condition.name)
        self.assertDictEqual({'has': False, 'entity': str(naru.uuid)}, condition.value)

    def test_ok05(self):
        "Wanted entity is deleted."
        rtype = self._create_rtype()
        user = self.get_root_user()

        naru = FakeContact.objects.create(user=user, first_name='Naru', last_name='Narusegawa')
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Filter 01',
            model=FakeContact, is_custom=True,
            conditions=[
                RelationConditionHandler.build_condition(
                    model=FakeContact, rtype=rtype, has=True, entity=naru,
                ),
            ],
        )
        field = RelationsConditionsField(model=FakeContact)

        jsondict = {
            'entity': naru.id,
            'has':    'true',
            'ctype':  naru.entity_type_id,
            'rtype':  rtype.id,
        }
        self.assertListEqual(
            [jsondict],
            json_load(field.from_python([*efilter.conditions.all()])),
        )

        try:
            naru.delete()
        except Exception as e:
            self.fail(f'Problem with entity deletion: {e}')

        jsondict['entity'] = None
        jsondict['ctype'] = 0
        self.assertListEqual(
            [jsondict],
            json_load(field.from_python([*efilter.conditions.all()])),
        )

    def test_ok06(self):
        "'model' property."
        rtype = self._create_rtype()

        with self.assertNumQueries(0):
            field = RelationsConditionsField()
            field.model = FakeContact

        rt_id = rtype.id
        condition = self.get_alone_element(
            field.clean(json_dump([
                {'rtype': rt_id, 'has': True,  'ctype': 0, 'entity': None},
            ]))
        )
        self.assertEqual(RelationConditionHandler.type_id, condition.type)
        self.assertEqual(rt_id,                            condition.name)
        self.assertDictEqual({'has': True}, condition.value)

    def test_disabled_rtype01(self):
        rtype = self._create_rtype(enabled=False)

        self.assertFormfieldError(
            field=RelationsConditionsField(model=FakeContact),
            value=json_dump([
                {'rtype': rtype.id, 'has': True, 'ctype': 0, 'entity': None},
            ]),
            messages=_('This type of relationship type is invalid with this model.'),
            codes='invalidrtype',
        )

    def test_disabled_rtype02(self):
        "Disabled RelationType is already used => still proposed."
        rtype = self._create_rtype(enabled=False)

        field = RelationsConditionsField(model=FakeContact)
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                RelationConditionHandler.build_condition(
                    model=FakeContact, rtype=rtype, has=True,
                ),
            ],
        )

        condition = self.get_alone_element(
            field.clean(json_dump([
                {'rtype': rtype.id, 'has': True,  'ctype': 0, 'entity': None},
            ]))
        )
        self.assertEqual(RelationConditionHandler.type_id, condition.type)
        self.assertEqual(rtype.id,                         condition.name)
        self.assertDictEqual({'has': True}, condition.value)

    def test_render_empty(self):
        widget = RelationsConditionsWidget()

        self.assertHTMLEqual(
            f'<input type="text" name="test" style="display:none;">'
            f'<span>{_("No choice available.")}</span>',
            widget.render('test', ''),
        )


class SubfiltersConditionsFieldTestCase(_ConditionsFieldTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        create_efilter = partial(
            EntityFilter.objects.smart_update_or_create,
            is_custom=True,
        )
        cls.sub_efilter01 = create_efilter(
            pk='creme_core-test_subfilter01', name='Public filter for Contact (not custom)',
            model=FakeContact,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name',
                    values=['Spike'],
                ),
            ],
        )
        cls.sub_efilter02 = create_efilter(
            pk='creme_core-test_subfilter02', name='Public filter for Contact (custom)',
            model=FakeContact,
        )
        cls.sub_efilter03 = create_efilter(
            pk='creme_core-test_subfilter03', name='Public filter for Organisation',
            model=FakeOrganisation,
        )

    def test_choices(self):
        user = self.get_root_user()
        other = self.create_user()

        filter1 = self.sub_efilter01
        filter2 = self.sub_efilter02

        create_private_efilter = partial(
            EntityFilter.objects.smart_update_or_create,
            model=FakeContact, is_custom=True, is_private=True
        )
        private_efilter1 = create_private_efilter(
            pk='creme_core-test_private_subfilter01',
            name='Private filter for Contact (mine)',
            user=user,
        )
        create_private_efilter(
            pk='creme_core-test_private_subfilter02',
            name='Private filter for Contact (not mine)',
            user=other,
        )

        field = SubfiltersConditionsField(model=FakeContact)
        field.user = user

        self.assertFalse([*field.choices])

        # ---
        ctype = ContentType.objects.get_for_model(FakeContact)
        field.initialize(ctype=ctype)

        choices2 = [*field.choices]
        self.assertInChoices(value=filter1.id, label=str(filter1), choices=choices2)
        self.assertInChoices(value=filter2.id, label=str(filter2), choices=choices2)
        self.assertInChoices(
            value=private_efilter1.id, label=str(private_efilter1), choices=choices2,
        )
        self.assertEqual(3, len(choices2))

        # ---
        field.initialize(ctype=ctype, efilter=filter1)
        choices3 = [*field.choices]
        self.assertInChoices(value=filter2.id, label=str(filter2), choices=choices3)
        self.assertNotInChoices(value=filter1.id, choices=choices3)

    def test_choices__deep(self):
        user = self.get_root_user()

        filter1 = self.sub_efilter01
        filter2 = self.sub_efilter02

        filter1 = self.refresh(filter1)  # reset cache
        parent_efilter = EntityFilter.objects.smart_update_or_create(
            pk='creme_core-test_parent_filter',
            name='Filter with child',
            model=FakeContact,
            is_custom=True,
            conditions=[SubFilterConditionHandler.build_condition(subfilter=filter1)],
        )

        field = SubfiltersConditionsField(model=FakeContact)
        field.user = user
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            efilter=filter1,
        )

        choices = [*field.choices]
        self.assertInChoices(value=filter2.id, label=str(filter2), choices=choices)
        self.assertNotInChoices(value=parent_efilter.id, choices=choices)

    def test_ok(self):
        user = self.get_root_user()

        with self.assertNumQueries(0):
            field = SubfiltersConditionsField(model=FakeContact)
            field.user = user

        self.assertEqual(EF_REGULAR,                           field.efilter_type)
        self.assertEqual(entity_filter_registries[EF_REGULAR], field.efilter_registry)

        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
        )

        filter_id1 = self.sub_efilter01.id
        filter_id2 = self.sub_efilter02.id
        conditions = field.clean([filter_id1, filter_id2])
        self.assertEqual(2, len(conditions))

        type_id = SubFilterConditionHandler.type_id
        condition1 = conditions[0]
        self.assertEqual(type_id,   condition1.type)
        self.assertEqual(EF_REGULAR, condition1.filter_type)
        self.assertDictEqual({}, condition1.value)

        self.assertCountEqual(
            [filter_id1, filter_id2], [cond.name for cond in conditions],
        )

    def test_filter_type(self):
        user = self.get_root_user()

        field = SubfiltersConditionsField(
            model=FakeContact, user=user, efilter_type=EF_CREDENTIALS,
        )
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
        )
        self.assertEqual(EF_CREDENTIALS,                           field.efilter_type)
        self.assertEqual(entity_filter_registries[EF_CREDENTIALS], field.efilter_registry)

        condition = self.get_alone_element(field.clean([self.sub_efilter01.id]))
        self.assertEqual(SubFilterConditionHandler.type_id, condition.type)
        self.assertEqual(EF_CREDENTIALS, condition.filter_type)


class RelationSubfiltersConditionsFieldTestCase(_ConditionsFieldTestCase):
    def _create_rtype(self, **kwargs):
        return RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving', models=[FakeContact],
            **kwargs
        ).symmetric(
            id='test-object_love', predicate='Is loved by',
        ).get_or_create()[0]

    def _create_subfilters(self):
        create_efilter = partial(
            EntityFilter.objects.smart_update_or_create,
            is_custom=True,
        )
        self.sub_efilter01 = create_efilter(
            pk='test-filter01', name='Filter 01', model=FakeContact,
        )
        self.sub_efilter02 = create_efilter(
            pk='test-filter02', name='Filter 02', model=FakeOrganisation,
        )

    def test_clean_empty_required(self):
        field = RelationSubfiltersConditionsField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='[]')

    def test_clean_incomplete_data_required(self):
        rtype = self._create_rtype()
        field = RelationSubfiltersConditionsField(model=FakeContact)
        msg = _('This field is required.')
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=json_dump([{'rtype': rtype.id}]),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=json_dump([{'has': True}]),
        )

    def test_unknown_filter(self):
        rtype = self._create_rtype()
        field = RelationSubfiltersConditionsField(model=FakeContact)
        field.user = self.get_root_user()
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'rtype': rtype.id, 'has': False,
                'ctype': ContentType.objects.get_for_model(FakeContact).id,
                'filter': '3213213543',  # <==
            }]),
            messages=_('This filter is invalid.'),
            codes='invalidfilter',
        )

    def test_ok(self):
        rtype1 = self._create_rtype()
        rtype2 = rtype1.symmetric_type

        self._create_subfilters()
        user = self.get_root_user()

        with self.assertNumQueries(0):
            field = RelationSubfiltersConditionsField(model=FakeContact)
            field.user = user

        get_ct = ContentType.objects.get_for_model
        filter_id1 = self.sub_efilter01.id
        filter_id2 = self.sub_efilter02.id
        conditions = field.clean(json_dump([
            {
                'rtype': rtype1.id,
                'has': True,
                'ctype': get_ct(FakeContact).id,
                'filter': filter_id1,
            }, {
                'rtype': rtype2.id,
                'has': False,
                'ctype': get_ct(FakeOrganisation).id,
                'filter': filter_id2,
            },
        ]))
        self.assertEqual(2, len(conditions))

        type_id = RelationSubFilterConditionHandler.type_id
        condition1 = conditions[0]
        self.assertEqual(type_id,    condition1.type)
        self.assertEqual(rtype1.id,  condition1.name)
        self.assertEqual(EF_REGULAR, condition1.filter_type)
        self.assertDictEqual(
            {'has': True, 'filter_id': filter_id1},
            condition1.value,
        )

        condition2 = conditions[1]
        self.assertEqual(type_id,   condition2.type)
        self.assertEqual(rtype2.id, condition2.name)
        self.assertDictEqual(
            {'has': False, 'filter_id': filter_id2},
            condition2.value,
        )

    def test_filter_type(self):
        self._create_subfilters()

        rtype = self._create_rtype()
        field = RelationSubfiltersConditionsField(
            model=FakeContact,
            user=self.get_root_user(),
            efilter_type=EF_CREDENTIALS,
        )

        filter_id = self.sub_efilter01.id
        rt_id = rtype.id
        condition = self.get_alone_element(
            field.clean(json_dump([{
                'rtype': rt_id, 'has': True,
                'ctype': ContentType.objects.get_for_model(FakeContact).id,
                'filter': filter_id,
            }]))
        )
        self.assertEqual(RelationSubFilterConditionHandler.type_id, condition.type)
        self.assertEqual(rt_id,          condition.name)
        self.assertEqual(EF_CREDENTIALS, condition.filter_type)
        self.assertDictEqual(
            {'has': True, 'filter_id': filter_id},
            condition.value,
        )

    def test_disabled_rtype01(self):
        self._create_subfilters()

        rtype = self._create_rtype(enabled=False)

        self.assertFormfieldError(
            field=RelationSubfiltersConditionsField(
                model=FakeContact, user=self.get_root_user(),
            ),
            value=json_dump([{
                'rtype': rtype.id, 'has': True,
                'ctype': ContentType.objects.get_for_model(FakeContact).id,
                'filter': self.sub_efilter01.id,
            }]),
            messages=_('This type of relationship type is invalid with this model.'),
            codes='invalidrtype',
        )

    def test_disabled_rtype02(self):
        "Disabled RelationType is already used => still proposed."
        self._create_subfilters()

        rtype = self._create_rtype(enabled=False)

        field = RelationSubfiltersConditionsField(
            model=FakeContact, user=self.get_root_user(),
        )
        field.initialize(
            ctype=ContentType.objects.get_for_model(FakeContact),
            conditions=[
                RelationSubFilterConditionHandler.build_condition(
                    model=FakeContact,
                    rtype=rtype,
                    subfilter=self.sub_efilter01,
                ),
            ],
        )
        filter_id = self.sub_efilter01.id
        condition = self.get_alone_element(
            field.clean(json_dump([{
                'rtype': rtype.id, 'has': True,
                'ctype': ContentType.objects.get_for_model(FakeContact).id,
                'filter': filter_id,
            }]))
        )
        self.assertEqual(RelationSubFilterConditionHandler.type_id, condition.type)
        self.assertEqual(rtype.id, condition.name)
        self.assertDictEqual(
            {'has': True, 'filter_id': filter_id},
            condition.value,
        )

    def test_render_empty(self):
        widget = RelationSubfiltersConditionsWidget()

        self.assertHTMLEqual(
            f'<input type="text" name="test" style="display:none;">'
            f'<span>{_("No relation type at present.")}</span>',
            widget.render('test', ''),
        )


class EntityFilterFormsTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self.efilter_registry = EntityFilterRegistry(
            id='creme_core-efilter_forms_testcase',
            verbose_name='Test',
        )
        entity_filter_registries.register(self.efilter_registry)

    def tearDown(self):
        entity_filter_registries.unregister(self.efilter_registry.id)

    def test_creation_form01(self):
        user = self.get_root_user()

        efilter_registry = self.efilter_registry
        efilter_registry.register_condition_handlers(
            RegularFieldConditionHandler,
            DateRegularFieldConditionHandler,
        ).register_operators(*operators.all_operators)

        kwargs = {
            'ctype': ContentType.objects.get_for_model(FakeContact),
            'user': user,
            'efilter_registry': efilter_registry,
        }

        form1 = EntityFilterCreationForm(**kwargs)

        regular_f = form1.fields.get('regularfieldcondition')
        self.assertIsInstance(regular_f, RegularFieldsConditionsField)
        self.assertEqual(user,             regular_f.user)
        self.assertEqual(FakeContact,      regular_f.model)
        self.assertEqual(efilter_registry, regular_f.efilter_registry)

        date_f = form1.fields.get('dateregularfieldcondition')
        self.assertIsInstance(date_f, DateFieldsConditionsField)

        self.assertNotIn('propertycondition', form1.fields)

        # ---
        name = 'My filter'
        foperator = operators.IEQUALS
        fname = 'first_name'
        fvalue = 'Faye'
        form2 = EntityFilterCreationForm(
            data={
                'name': name,
                'use_or': 'False',
                'regularfieldcondition': RegularFieldsConditionsFieldTestCase.build_data({
                    'operator': foperator,
                    'name':     fname,
                    'value':    fvalue,
                }),
            },
            **kwargs
        )
        self.assertFalse(form2.errors)
        self.assertTrue(form2.is_valid())

        efilter = form2.save()
        self.assertIsInstance(efilter, EntityFilter)
        self.assertEqual(name, efilter.name)
        self.assertIs(efilter.use_or, False)
        self.assertIsNone(efilter.user, False)
        self.assertIs(efilter.is_private, False)

        condition = self.get_alone_element(efilter.get_conditions())
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(fname,                                condition.name)
        self.assertDictEqual(
            {'operator': foperator, 'values': [fvalue]},
            condition.value,
        )

    def test_creation_form02(self):
        user = self.get_root_user()

        efilter_registry = self.efilter_registry
        efilter_registry.register_condition_handlers(
            RegularFieldConditionHandler,
            PropertyConditionHandler,
        )

        form = EntityFilterCreationForm(
            ctype=ContentType.objects.get_for_model(FakeOrganisation),
            user=user,
            efilter_registry=efilter_registry,
        )
        self.assertIn('regularfieldcondition', form.fields)
        self.assertNotIn('dateregularfieldcondition', form.fields)

        prop_f = form.fields.get('propertycondition')
        self.assertIsInstance(prop_f, PropertiesConditionsField)
        self.assertEqual(FakeOrganisation, prop_f.model)

    def test_edition_form01(self):
        user = self.get_root_user()

        efilter_registry = self.efilter_registry
        efilter_registry.register_condition_handlers(
            RegularFieldConditionHandler,
            DateRegularFieldConditionHandler,
        ).register_operators(*operators.all_operators)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Filter 01', model=FakeContact,
            is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name',
                    values=['Spike'],
                ),
            ],
        )

        kwargs = {
            'instance': efilter,
            'user': user,
            'efilter_registry': efilter_registry,
        }

        form1 = EntityFilterEditionForm(**kwargs)
        self.assertIn('name',       form1.fields)
        self.assertIn('is_private', form1.fields)

        regular_f = form1.fields.get('regularfieldcondition')
        self.assertIsInstance(regular_f, RegularFieldsConditionsField)
        self.assertEqual(user,             regular_f.user)
        self.assertEqual(FakeContact,      regular_f.model)
        self.assertEqual(efilter_registry, regular_f.efilter_registry)

        date_f = form1.fields.get('dateregularfieldcondition')
        self.assertIsInstance(date_f, DateFieldsConditionsField)

        self.assertNotIn('relationcondition', form1.fields)

        # ---
        name = 'My filter'
        foperator = operators.IEQUALS
        fname = 'first_name'
        fvalue = 'Faye'
        form2 = EntityFilterEditionForm(
            data={
                'name': name,
                'use_or': 'True',
                'regularfieldcondition': RegularFieldsConditionsFieldTestCase.build_data({
                    'operator': foperator,
                    'name':     fname,
                    'value':    fvalue,
                }),
            },
            **kwargs
        )
        self.assertFalse(form2.errors)
        self.assertTrue(form2.is_valid())

        efilter_edited = self.refresh(form2.save())
        self.assertEqual(efilter.id, efilter_edited.id)
        self.assertEqual(name, efilter_edited.name)
        self.assertIs(efilter_edited.use_or, True)

        condition = self.get_alone_element(efilter.get_conditions())
        self.assertEqual(RegularFieldConditionHandler.type_id, condition.type)
        self.assertEqual(fname,                                condition.name)
        self.assertDictEqual(
            {'operator': foperator, 'values': [fvalue]},
            condition.value,
        )

    def test_edition_form02(self):
        user = self.get_root_user()

        efilter_registry = self.efilter_registry
        efilter_registry.register_condition_handlers(
            RegularFieldConditionHandler,
            RelationConditionHandler,
        ).register_operators(*operators.all_operators)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', name='Filter 01', model=FakeContact,
            is_custom=False,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name',
                    values=['Spike'],
                ),
            ],
        )

        form1 = EntityFilterEditionForm(
            instance=efilter,
            user=user,
            efilter_registry=efilter_registry,
        )
        self.assertNotIn('name',       form1.fields)
        self.assertNotIn('is_private', form1.fields)

        self.assertIn('regularfieldcondition', form1.fields)
        self.assertNotIn('dateregularfieldcondition', form1.fields)

        relation_f = form1.fields.get('relationcondition')
        self.assertIsInstance(relation_f, RelationsConditionsField)

    # TODO: complete (other type of handlers, handlers added/removed...)
