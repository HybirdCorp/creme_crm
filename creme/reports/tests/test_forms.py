# -*- coding: utf-8 -*-

try:
    from json import dumps as json_dump, loads as json_load

    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from creme.creme_core.constants import REL_SUB_HAS
    from creme.creme_core.core.entity_cell import (
        EntityCellRegularField,
        EntityCellRelation,
        EntityCellCustomField,
        EntityCellFunctionField,
    )
    from creme.creme_core.models import (
        CremeEntity,
        RelationType,
        CustomField,
        FieldsConfig,
        FakeOrganisation, FakeContact, FakeInvoiceLine,
    )
    from creme.creme_core.tests.forms.base import FieldTestCase

    from creme.reports import constants
    from creme.reports.core.graph import AbscissaInfo, OrdinateInfo
    from creme.reports.core.graph.cell_constraint import (
        ACCCount, ACCFieldAggregation,
        abscissa_constraints,
        ordinate_constraints,
    )
    from creme.reports.forms.graph import AbscissaField, OrdinateField

    from .base import AxisFieldsMixin
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class AbscissaFieldTestCase(AxisFieldsMixin, FieldTestCase):
    def test_clean_empty_not_required(self):
        with self.assertNoException():
            cleaned = AbscissaField(required=False).clean(None)

        self.assertIsNone(cleaned)

    def test_clean_invalid_json(self):
        self.assertFieldValidationError(AbscissaField, 'invalidformat',
                                        AbscissaField(required=False).clean,
                                        '{"entity_cell":{"cell_key":'
                                       )

    def test_clean_invalid_data_type(self):
        clean = AbscissaField(required=False).clean
        self.assertFieldValidationError(AbscissaField, 'invalidtype', clean, '"this is a string"')
        self.assertFieldValidationError(AbscissaField, 'invalidtype', clean, "[]")

    def test_clean_invalid_data(self):
        field = AbscissaField(required=False)
        self.assertFieldValidationError(
            AbscissaField,
            'invalidformat',
            field.clean,
            '{"graph_type":"notadict"}',
        )

    def test_clean_rfield_fk(self):
        model = FakeOrganisation
        field_name = 'sector'
        graph_type = constants.RGT_FK

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )
        widget = field.widget
        self.assertEqual(model, field.model)
        self.assertEqual(model, widget.model)
        self.assertEqual(abscissa_constraints, field.constraint_registry)
        self.assertEqual(abscissa_constraints, widget.constraint_registry)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=model._meta.get_field(field_name),
            graph_type=graph_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(model, cell.model)
        self.assertEqual(field_name, cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_rfield_date_year(self):
        model = FakeContact
        field_name = 'birthday'
        graph_type = constants.RGT_YEAR

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field(field_name),
            graph_type=graph_type,
        ))
        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(model, cell.model)
        self.assertEqual(field_name, cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_rfield_date_month(self):
        field = AbscissaField(model=FakeContact,
                              abscissa_constraints=abscissa_constraints,
                             )

        graph_type = constants.RGT_MONTH
        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field('birthday'),
            graph_type=graph_type,
        ))
        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_rfield_date_day(self):
        field = AbscissaField(model=FakeContact,
                              abscissa_constraints=abscissa_constraints,
                             )

        graph_type = constants.RGT_DAY
        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field('birthday'),
            graph_type=graph_type,
        ))
        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_rfield_range(self):
        model = FakeContact
        field_name = 'created'
        graph_type = constants.RGT_RANGE
        days = 3

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field(field_name),
            graph_type=graph_type,
            parameter=str(days),
        ))
        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(model, cell.model)
        self.assertEqual(field_name, cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertEqual(days, abs_info.parameter)

    def test_clean_rfield_error01(self):
        "Error on cell."
        model = FakeOrganisation
        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        self.assertFieldValidationError(
            AbscissaField, 'ecellrequired', field.clean,
            json_dump({
                # 'entity_cell': {
                #     'cell_key': ...,
                # },
                'graph_type': {
                    'type_id': constants.RGT_FK,
                },
                'parameter': '',
            })
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellrequired', field.clean,
            json_dump({
                'entity_cell': {
                    # 'cell_key': ...,
                },
                'graph_type': {
                    'type_id': constants.RGT_FK,
                },
                'parameter': '',
            })
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=model._meta.get_field('name'),  # <= forbidden field
                graph_type=constants.RGT_FK,
            ),
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            json_dump({
                'entity_cell': {
                    'cell_key': 'regular_field-sector__title',  # <= forbidden field
                },
                'graph_type': {
                    'type_id': constants.RGT_FK,
                },
                'parameter': '',
            })
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            json_dump({
                'entity_cell': {
                    'cell_key': 'regular_field-image__created',  # <= forbidden field
                },
                'graph_type': {
                    'type_id': constants.RGT_YEAR,
                },
                'parameter': '',
            })
        )

    def test_clean_rfield_error02(self):
        "Error on graph type."
        model = FakeOrganisation
        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        self.assertFieldValidationError(
            AbscissaField, 'graphtyperequired', field.clean,
            json_dump({
                'entity_cell': {
                    'cell_key': 'regular_field-sector',
                },
                # 'graph_type': {
                #     'type_id': ...,
                # },
                'parameter': '',
            })
        )
        self.assertFieldValidationError(
            AbscissaField, 'graphtyperequired', field.clean,
            json_dump({
                'entity_cell': {
                    'cell_key': 'regular_field-sector',
                },
                'graph_type': {
                    # 'type_id': ...,
                },
                'parameter': '',
            })
        )

        sector_field = model._meta.get_field('sector')
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=sector_field,
                graph_type=constants.RGT_YEAR,  # < ===
            ),
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=sector_field,
                graph_type=constants.RGT_MONTH,  # < ===
            ),
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=sector_field,
                graph_type=constants.RGT_DAY,  # < ===
            ),
        )

    def test_clean_rfield_error03(self):
        "Error on extra parameter."
        model = FakeContact
        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        abscissa = model._meta.get_field('created')
        graph_type = constants.RGT_RANGE

        with self.assertRaises(ValidationError) as cm1:
            field.clean(self.formfield_value_abscissa(
                abscissa=abscissa,
                graph_type=graph_type,
                # parameter='2',
            ))

        exception = cm1.exception
        self.assertEqual('invalidparameter', exception.code)
        self.assertEqual(
            _('The parameter is invalid. {}').format(_('This field is required.')),
            exception.message
        )

        # ---
        with self.assertRaises(ValidationError) as cm2:
            field.clean(self.formfield_value_abscissa(
                abscissa=abscissa,
                graph_type=graph_type,
                parameter='notanint',
            ))

        exception = cm2.exception
        self.assertEqual('invalidparameter', exception.code)
        self.assertEqual(
            _('The parameter is invalid. {}').format(_('Enter a whole number.')),
            exception.message
        )

    def test_clean_rfield_fields_config(self):
        model = FakeOrganisation
        field_name = 'sector'
        graph_type = constants.RGT_FK

        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[(field_name, {FieldsConfig.HIDDEN: True})],
        )

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )
        self.assertIsNone(field.initial)
        self.assertSetEqual(set(), field.not_hiddable_cell_keys)
        self.assertSetEqual(set(), field.widget.not_hiddable_cell_keys)

        sector_field = model._meta.get_field(field_name)
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=sector_field,
                graph_type=graph_type,
            ),
        )

        # ---
        cell = EntityCellRegularField.build(model, field_name)
        init_abs_info = AbscissaInfo(cell=cell, graph_type=graph_type)
        field.initial = init_abs_info
        self.assertEqual(init_abs_info, field.initial)
        self.assertSetEqual({cell.key}, field.not_hiddable_cell_keys)
        self.assertSetEqual({cell.key}, field.widget.not_hiddable_cell_keys)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=model._meta.get_field(field_name),
            graph_type=graph_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

    def test_clean_rtype(self):
        model = FakeOrganisation
        graph_type = constants.RGT_RELATION
        rtype = RelationType.objects.compatible(model)[0]

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=rtype,
            graph_type=graph_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(model, cell.model)
        self.assertEqual(rtype.id, cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_rtype_error(self):
        model = FakeOrganisation
        rtype = RelationType.create(
            ('test-subject_foobar', 'is loving',   [FakeContact]),
            ('test-object_foobar',  'is loved by', [FakeContact])
        )[0]

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=rtype,
                graph_type=constants.RGT_RELATION,
            ),
        )

    def test_clean_cfield_enum(self):
        model = FakeContact
        graph_type = constants.RGT_CUSTOM_FK
        cfield = CustomField.objects.create(
            content_type=model,
            name='Hair',
            field_type=CustomField.ENUM,
        )

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield,
            graph_type=graph_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(model, cell.model)
        self.assertEqual(str(cfield.id), cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_cfield_date_year(self):
        model = FakeContact
        graph_type = constants.RGT_CUSTOM_YEAR
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=CustomField.DATETIME,
        )

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield,
            graph_type=graph_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(model, cell.model)
        self.assertEqual(str(cfield.id), cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_cfield_date_month(self):
        model = FakeContact
        graph_type = constants.RGT_CUSTOM_MONTH
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=CustomField.DATETIME,
        )

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield,
            graph_type=graph_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(model, cell.model)
        self.assertEqual(str(cfield.id), cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_cfield_date_day(self):
        model = FakeContact
        graph_type = constants.RGT_CUSTOM_DAY
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=CustomField.DATETIME,
        )

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield,
            graph_type=graph_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(model, cell.model)
        self.assertEqual(str(cfield.id), cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_cfield_range(self):
        model = FakeContact
        graph_type = constants.RGT_CUSTOM_RANGE
        days = 5
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=CustomField.DATETIME,
        )

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield,
            graph_type=graph_type,
            parameter=str(days),
        ))

        cell = abs_info.cell
        self.assertEqual(model, cell.model)
        self.assertEqual(str(cfield.id), cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertEqual(days, abs_info.parameter)

    def test_clean_cfield_error01(self):
        "Error on cell."
        model = FakeOrganisation
        cfield1 = CustomField.objects.create(
            content_type=model,
            name='Number of countries',
            field_type=CustomField.INT,
        )

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=cfield1,
                graph_type=constants.RGT_CUSTOM_FK,
            ),
        )

        # ---
        cfield2 = CustomField.objects.create(
            content_type=FakeContact,  # <== wrong model
            name='Size',
            field_type=CustomField.ENUM,
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=cfield2,
                graph_type=constants.RGT_CUSTOM_FK,
            ),
        )

    def test_clean_cfield_error02(self):
        "Error on graph type."
        model = FakeOrganisation
        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        cfield_enum = CustomField.objects.create(
            content_type=model,
            name='Type',
            field_type=CustomField.ENUM,
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=cfield_enum,
                graph_type=constants.RGT_CUSTOM_YEAR,
            ),
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=cfield_enum,
                graph_type=constants.RGT_CUSTOM_MONTH,
            ),
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=cfield_enum,
                graph_type=constants.RGT_CUSTOM_DAY,
            ),
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=cfield_enum,
                graph_type=constants.RGT_CUSTOM_RANGE,
                parameter='7',
            ),
        )

        cfield_dt = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=CustomField.DATETIME,
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=cfield_dt,
                graph_type=constants.RGT_CUSTOM_FK,
            ),
        )

    def test_clean_cfield_error03(self):
        "Error on extra parameter."
        model = FakeContact
        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )
        graph_type = constants.RGT_CUSTOM_RANGE

        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=CustomField.DATETIME,
        )

        with self.assertRaises(ValidationError) as cm1:
            field.clean(self.formfield_value_abscissa(
                abscissa=cfield,
                graph_type=graph_type,
                # parameter='2',
            ))

        exception = cm1.exception
        self.assertEqual('invalidparameter', exception.code)
        self.assertEqual(
            _('The parameter is invalid. {}').format(_('This field is required.')),
            exception.message
        )

        # ---
        with self.assertRaises(ValidationError) as cm2:
            field.clean(self.formfield_value_abscissa(
                abscissa=cfield,
                graph_type=graph_type,
                parameter='notanint',
            ))

        exception = cm2.exception
        self.assertEqual('invalidparameter', exception.code)
        self.assertEqual(
            _('The parameter is invalid. {}').format(_('Enter a whole number.')),
            exception.message
        )

    def test_clean_error01(self):
        "Error on cell."
        model = FakeOrganisation
        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )
        cell = EntityCellFunctionField.build(FakeContact, 'get_pretty_properties')
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            json_dump({
                'entity_cell': {
                    'cell_key': cell.key,
                },
                'graph_type': {
                    'type_id': constants.RGT_FK,
                },
                'parameter': '',
            })
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            json_dump({
                'entity_cell': {
                    'cell_key': cell.key.replace('-', ''),
                },
                'graph_type': {
                    'type_id': constants.RGT_FK,
                },
                'parameter': '',
            })
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            json_dump({
                'entity_cell': {
                    'cell_key': 'regular_field-INVALID',
                },
                'graph_type': {
                    'type_id': constants.RGT_FK,
                },
                'parameter': '',
            })
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            json_dump({
                'entity_cell': {
                    'cell_key': 'INVALID-stuff',
                },
                'graph_type': {
                    'type_id': constants.RGT_FK,
                },
                'parameter': '',
            })
        )

    def test_clean_error02(self):
        "Error on graph type."
        model = FakeContact
        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )
        cell = EntityCellRegularField.build(FakeContact, 'position')
        self.assertFieldValidationError(
            AbscissaField, 'graphtypenotallowed', field.clean,
            json_dump({
                'entity_cell': {
                    'cell_key': cell.key,
                },
                'graph_type': {
                    'type_id': 1024,  # <==
                },
                'parameter': '',
            })
        )

    def test_clean_error03(self):
        "Error on parameter."
        model = FakeContact
        field_name = 'birthday'
        graph_type = constants.RGT_YEAR

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field(field_name),
            graph_type=graph_type,
            parameter='6',  # <== should be ignored
        ))
        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(model, cell.model)
        self.assertEqual(field_name, cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_not_required(self):
        model = FakeOrganisation
        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                              required=False,
                             )
        self.assertIsNone(field.clean(self.formfield_value_abscissa(
                                abscissa=None,
                                graph_type='',
                          ))
        )
        self.assertIsNone(field.clean(self.formfield_value_abscissa(
                                abscissa=model._meta.get_field('sector'),
                                graph_type='',
                          ))
        )

    def test_clean_no_model01(self):
        "Regular field."
        field = AbscissaField(abscissa_constraints=abscissa_constraints)
        self.assertIs(field.model, CremeEntity)

        field_name = 'created'
        graph_type = constants.RGT_YEAR
        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=CremeEntity._meta.get_field(field_name),
            graph_type=graph_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(CremeEntity, cell.model)
        self.assertEqual(field_name, cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_no_model02(self):
        "Relation."
        field = AbscissaField(abscissa_constraints=abscissa_constraints)

        rtype = RelationType.create(
            ('test-subject_likes', 'likes'),
            ('test-object_likes',  'is liked by')
        )[0]

        graph_type = constants.RGT_RELATION

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=rtype,
            graph_type=graph_type,
        ))

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(CremeEntity, cell.model)
        self.assertEqual(rtype.id, cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_from_python_rfield_fk(self):
        field = AbscissaField(model=FakeOrganisation,
                              abscissa_constraints=abscissa_constraints,
                             )
        cell = EntityCellRegularField.build(FakeOrganisation, 'sector')
        graph_type = constants.RGT_FK
        self.assertEqual(
            {
                'entity_cell': {
                    'cell_key': cell.key,
                    'grouping_category': 'regular_fk',
                },
                'graph_type': {
                    'type_id': graph_type,
                    'grouping_category': 'regular_fk',
                },
                'parameter': '',
            },
            json_load(field.from_python(AbscissaInfo(cell=cell, graph_type=graph_type)))
        )

    def test_from_python_rfield_date(self):
        from_python = AbscissaField(model=FakeOrganisation,
                                    abscissa_constraints=abscissa_constraints,
                                   ).from_python
        cell = EntityCellRegularField.build(FakeOrganisation, 'creation_date')

        graph_type1 = constants.RGT_YEAR
        self.assertEqual(
            {
                'entity_cell': {
                    'cell_key': cell.key,
                    'grouping_category': 'regular_date',
                },
                'graph_type': {
                    'type_id': graph_type1,
                    'grouping_category': 'regular_date',
                },
                'parameter': '',
            },
            json_load(from_python(AbscissaInfo(cell=cell, graph_type=graph_type1)))
        )

        graph_type2 = constants.RGT_RANGE
        parameter = '5'
        self.assertEqual(
            {
                'entity_cell': {
                    'cell_key': cell.key,
                    'grouping_category': 'regular_date',
                },
                'graph_type': {
                    'type_id': graph_type2,
                    'grouping_category': 'regular_date',
                },
                'parameter': parameter,
            },
            json_load(from_python(AbscissaInfo(cell=cell, graph_type=graph_type2, parameter=parameter)))
        )

    def test_from_python_relation(self):
        field = AbscissaField(model=FakeOrganisation,
                              abscissa_constraints=abscissa_constraints,
                             )
        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        cell = EntityCellRelation(model=FakeOrganisation, rtype=rtype)
        graph_type = constants.RGT_RELATION
        self.assertEqual(
            {
                'entity_cell': {
                    'cell_key': cell.key,
                    'grouping_category': 'rtype',
                },
                'graph_type': {
                    'type_id': graph_type,
                    'grouping_category': 'rtype',
                },
                'parameter': '',
            },
            json_load(field.from_python(AbscissaInfo(cell=cell, graph_type=graph_type)))
        )

    def test_from_python_cfield_enum(self):
        model = FakeContact
        cfield = CustomField.objects.create(
            content_type=model,
            name='Hair',
            field_type=CustomField.ENUM,
        )

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )
        cell = EntityCellCustomField(cfield)
        graph_type = constants.RGT_CUSTOM_FK
        self.assertEqual(
            {
                'entity_cell': {
                    'cell_key': cell.key,
                    'grouping_category': 'custom_enum',
                },
                'graph_type': {
                    'type_id': graph_type,
                    'grouping_category': 'custom_enum',
                },
                'parameter': '',
            },
            json_load(field.from_python(AbscissaInfo(cell=cell, graph_type=graph_type)))
        )

    def test_from_python_cfield_date(self):
        model = FakeContact
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=CustomField.DATETIME,
        )

        field = AbscissaField(model=model,
                              abscissa_constraints=abscissa_constraints,
                             )
        cell = EntityCellCustomField(cfield)
        graph_type = constants.RGT_CUSTOM_DAY
        self.assertEqual(
            {
                'entity_cell': {
                    'cell_key': cell.key,
                    'grouping_category': 'custom_date',
                },
                'graph_type': {
                    'type_id': graph_type,
                    'grouping_category': 'custom_date',
                },
                'parameter': '',
            },
            json_load(field.from_python(AbscissaInfo(cell=cell, graph_type=graph_type)))
        )


class OrdinateFieldTestCase(AxisFieldsMixin, FieldTestCase):
    def test_clean_empty_not_required(self):
        with self.assertNoException():
            cleaned = OrdinateField(required=False).clean(None)

        self.assertIsNone(cleaned)

    def test_clean_invalid_json(self):
        self.assertFieldValidationError(OrdinateField, 'invalidformat',
                                        OrdinateField(required=False).clean,
                                        '{"entity_cell":{"cell_key":'
                                       )

    def test_clean_invalid_data_type(self):
        clean = OrdinateField(required=False).clean
        self.assertFieldValidationError(OrdinateField, 'invalidtype', clean, '"this is a string"')
        self.assertFieldValidationError(OrdinateField, 'invalidtype', clean, '[]')

    def test_clean_invalid_data(self):
        field = OrdinateField(required=False)
        self.assertFieldValidationError(
            OrdinateField,
            'invalidformat',
            field.clean,
            '{"aggregator":"notadict"}',
        )

    def test_clean_count(self):
        model = FakeOrganisation
        aggr_id =  constants.RGA_COUNT

        field = OrdinateField(model=model,
                              ordinate_constraints=ordinate_constraints,
                             )
        widget = field.widget
        self.assertEqual(model, field.model)
        self.assertEqual(model, widget.model)
        self.assertEqual(ordinate_constraints, field.constraint_registry)
        self.assertEqual(ordinate_constraints, widget.constraint_registry)

        ord_info = field.clean(self.formfield_value_ordinate(aggr_id=aggr_id))
        self.assertIsInstance(ord_info, OrdinateInfo)
        self.assertEqual(aggr_id, ord_info.aggr_id)
        self.assertIsNone(ord_info.cell)

    def test_clean_rfield_int(self):
        model = FakeOrganisation
        field_name = 'capital'
        aggr_id = constants.RGA_SUM

        field = OrdinateField(model=model,
                              ordinate_constraints=ordinate_constraints,
                             )
        ord_info = field.clean(self.formfield_value_ordinate(
            aggr_id=aggr_id,
            cell=EntityCellRegularField.build(model, field_name),
        ))
        self.assertIsInstance(ord_info, OrdinateInfo)
        self.assertEqual(aggr_id, ord_info.aggr_id)

        cell = ord_info.cell
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(model, cell.model)
        self.assertEqual(field_name, cell.value)

    def test_clean_rfield_decimal(self):
        model = FakeInvoiceLine
        field_name = 'quantity'
        aggr_id = constants.RGA_AVG

        field = OrdinateField(
            model=model,
            ordinate_constraints=ordinate_constraints,
        )

        ord_info = field.clean(self.formfield_value_ordinate(
            aggr_id=aggr_id,
            cell=EntityCellRegularField.build(model, field_name),
        ))
        self.assertIsInstance(ord_info, OrdinateInfo)
        self.assertEqual(aggr_id, ord_info.aggr_id)

        cell = ord_info.cell
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(model, cell.model)
        self.assertEqual(field_name, cell.value)

    def test_clean_rfield_error01(self):
        "Error on aggregation ID."
        model = FakeOrganisation
        field = OrdinateField(
            model=model,
            ordinate_constraints=ordinate_constraints,
        )

        self.assertFieldValidationError(
            OrdinateField, 'aggridrequired', field.clean,
            json_dump({
                # 'aggregator': {
                #     'aggr_id': ...,
                # },
                'entity_cell': {
                    'cell_key': 'regular_field-capital',
                },
            })
        )
        self.assertFieldValidationError(
            OrdinateField, 'aggridrequired', field.clean,
            json_dump({
                'aggregator': {
                    # 'type_id': ...,
                },
                'entity_cell': {
                    'cell_key': 'regular_field-capital',
                },
            })
        )
        self.assertFieldValidationError(
            OrdinateField, 'aggridinvalid', field.clean,
            json_dump({
                'aggregator': {
                    'aggr_id': 'invalid',
                },
                'entity_cell': {
                    'cell_key': 'regular_field-capital',
                },
            })
        )

    def test_clean_rfield_error02(self):
        "Error on cell."
        model = FakeInvoiceLine
        field = OrdinateField(model=model,
                              ordinate_constraints=ordinate_constraints,
                             )

        self.assertFieldValidationError(
            OrdinateField, 'ecellrequired', field.clean,
            json_dump({
                'aggregator': {
                    'aggr_id': constants.RGA_MIN,
                },
                # 'entity_cell': {
                #     'cell_key': ...,
                # },
            })
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellrequired', field.clean,
            json_dump({
                'aggregator': {
                    'aggr_id': constants.RGA_MIN,
                },
                'entity_cell': {
                    # 'cell_key': ...,
                },
            })
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellrequired', field.clean,
            self.formfield_value_ordinate(
                aggr_id=constants.RGA_MIN,
                # cell=...
            )
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                aggr_id=constants.RGA_SUM,
                cell=EntityCellRegularField.build(model, 'item'),  # < === forbidden field
            ),
        )

        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                aggr_id=constants.RGA_SUM,
                cell=EntityCellRegularField.build(model, 'linked_invoice__total_vat'),  # < === field too deep
            ),
        )

        # TODO: not viewable

    def test_clean_rfield_fields_config(self):
        model = FakeOrganisation
        field_name = 'capital'
        aggr_id1 = constants.RGA_SUM

        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[(field_name, {FieldsConfig.HIDDEN: True})],
        )

        field = OrdinateField(model=model,
                              ordinate_constraints=ordinate_constraints,
                             )

        self.assertIsNone(field.initial)
        self.assertSetEqual(set(), field.not_hiddable_cell_keys)
        self.assertSetEqual(set(), field.widget.not_hiddable_cell_keys)

        cell = EntityCellRegularField.build(model, field_name)
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                aggr_id=aggr_id1,
                cell=cell,
            ),
        )

        # ---
        init_ord_info1 = OrdinateInfo(aggr_id=aggr_id1, cell=cell)
        field.initial = init_ord_info1
        self.assertEqual(init_ord_info1, field.initial)
        self.assertSetEqual({cell.key}, field.not_hiddable_cell_keys)
        self.assertSetEqual({cell.key}, field.widget.not_hiddable_cell_keys)

        ord_info1 = field.clean(self.formfield_value_ordinate(
            aggr_id=aggr_id1,
            cell=cell,
        ))
        self.assertIsInstance(ord_info1, OrdinateInfo)

        # cell is None ---
        aggr_id2 = constants.RGA_COUNT
        init_ord_info2 = OrdinateInfo(aggr_id=aggr_id2)
        field.initial = init_ord_info2
        self.assertEqual(init_ord_info2, field.initial)
        self.assertSetEqual(set(), field.not_hiddable_cell_keys)
        self.assertSetEqual(set(), field.widget.not_hiddable_cell_keys)

    def test_clean_cfield_int(self):
        model = FakeContact
        aggr_id = constants.RGA_MAX
        cfield = CustomField.objects.create(
            content_type=model,
            name='Hair length',
            field_type=CustomField.INT,
        )

        field = OrdinateField(
            model=model,
            ordinate_constraints=ordinate_constraints,
        )

        ord_info = field.clean(self.formfield_value_ordinate(
            aggr_id=aggr_id,
            cell=EntityCellCustomField(cfield),
        ))
        self.assertIsInstance(ord_info, OrdinateInfo)
        self.assertEqual(aggr_id, ord_info.aggr_id)

        cell = ord_info.cell
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(model, cell.model)
        self.assertEqual(str(cfield.id), cell.value)

    def test_clean_cfield_error01(self):
        "Error on aggregation."
        model = FakeOrganisation
        field = OrdinateField(model=model,
                              ordinate_constraints=ordinate_constraints,
                             )

        cfield_str = CustomField.objects.create(
            content_type=model,
            name='Tags',
            field_type=CustomField.STR,
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                aggr_id=constants.RGA_SUM,
                cell=EntityCellCustomField(cfield_str),
            ),
        )

    def test_clean_cfield_error02(self):
        "Error on cell."
        field = OrdinateField(model=FakeOrganisation,
                              ordinate_constraints=ordinate_constraints,
                             )

        cfield = CustomField.objects.create(
            content_type=FakeContact,  # <== wrong model
            name='Size',
            field_type=CustomField.ENUM,
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                aggr_id=constants.RGA_SUM,
                cell=EntityCellCustomField(cfield),
            ),
        )

        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                aggr_id=constants.RGA_COUNT,
                cell=EntityCellRegularField.build(FakeOrganisation, 'capital'),
            ),
        )

    def test_clean_error(self):
        "Error on cell."
        model = FakeOrganisation
        field = OrdinateField(model=model,
                              ordinate_constraints=ordinate_constraints,
                             )
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                aggr_id=constants.RGA_SUM,
                cell=EntityCellFunctionField.build(FakeContact, 'get_pretty_properties'),
            ),
        )
        self.assertFieldValidationError(
            # OrdinateField, 'ecellinvalid', field.clean,
            OrdinateField, 'ecellnotallowed', field.clean,
            json_dump({
                'aggregator': {
                    'aggr_id': constants.RGA_SUM,
                    'aggr_category': 'not used',
                },
                'entity_cell': {
                    'cell_key': 'not_hyphened_str',
                    'aggr_category': 'not used',
                },
            })
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            json_dump({
                'aggregator': {
                    'aggr_id': constants.RGA_SUM,
                    'aggr_category': 'not used',
                },
                'entity_cell': {
                    'cell_key': 'regular_field-INVALID',
                    'aggr_category': 'not used',
                },
            })
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            json_dump({
                'aggregator': {
                    'aggr_id': 'sum',
                    'aggr_category': 'not used',
                },
                'entity_cell': {
                    'cell_key': 'INVALID-stuff',
                    'aggr_category': 'not used',
                },
            })
        )

    def test_clean_not_required(self):
        model = FakeOrganisation
        field = OrdinateField(model=model,
                              ordinate_constraints=ordinate_constraints,
                              required=False,
                             )
        self.assertIsNone(field.clean(self.formfield_value_ordinate(aggr_id='')))

    def test_clean_no_model(self):
        "Regular field."
        field = OrdinateField(ordinate_constraints=ordinate_constraints)
        self.assertIs(field.model, CremeEntity)

        # TODO: test empty choices ??

    def test_from_python_count(self):
        field = OrdinateField(model=FakeOrganisation,
                              ordinate_constraints=ordinate_constraints,
                             )
        aggr_id = constants.RGA_COUNT
        self.assertEqual(
            {
                'aggregator': {
                    'aggr_id': aggr_id,
                    'aggr_category': ACCCount.type_id,
                },
                'entity_cell': None,
            },
            json_load(field.from_python(OrdinateInfo(aggr_id=aggr_id)))
        )

    def test_from_python_rfield_int(self):
        field = OrdinateField(model=FakeOrganisation,
                              ordinate_constraints=ordinate_constraints,
                             )
        cell = EntityCellRegularField.build(FakeOrganisation, 'capital')
        aggr_id = constants.RGA_AVG
        category = ACCFieldAggregation.type_id
        self.assertEqual(
            {
                'aggregator': {
                    'aggr_id': aggr_id,
                    'aggr_category': category,
                },
                'entity_cell': {
                    'cell_key': cell.key,
                    'aggr_category': category,
                },
            },
            json_load(field.from_python(OrdinateInfo(aggr_id=aggr_id, cell=cell)))
        )

    def test_from_python_cfield_int(self):
        model = FakeContact
        cfield = CustomField.objects.create(
            content_type=model,
            name='Hair',
            field_type=CustomField.INT,
        )

        field = OrdinateField(model=model,
                              ordinate_constraints=ordinate_constraints,
                             )
        cell = EntityCellCustomField(cfield)
        aggr_id = constants.RGA_SUM
        category = ACCFieldAggregation.type_id
        self.assertEqual(
            {
                'aggregator': {
                    'aggr_id': aggr_id,
                    'aggr_category': category,
                },
                'entity_cell': {
                    'cell_key': cell.key,
                    'aggr_category': category,
                },
            },
            json_load(field.from_python(OrdinateInfo(aggr_id=aggr_id, cell=cell)))
        )
