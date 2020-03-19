# -*- coding: utf-8 -*-

try:
    from functools import partial
    from json import dumps as json_dump, loads as json_load

    from django import forms
    from django.core.exceptions import ValidationError
    from django.db.models import Field
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
        FakeOrganisation, FakeContact,
    )
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.forms.base import FieldTestCase

    from creme.reports import constants
    from creme.reports.constants import (
        RGT_FK,
        RGT_MONTH, RGT_YEAR,
        RGT_RELATION,
        RGT_RANGE,
        RGT_CUSTOM_RANGE,
    )
    from creme.reports.core.graph import AbscissaInfo
    from creme.reports.core.graph.cell_constraint import (
        GraphHandCellConstraint,
        GHCCRegularFK, GHCCRegularDate, GHCCRelation, GHCCCustomEnum, GHCCCustomDate,
        GraphHandConstraintsRegistry, abscissa_constraints,
    )
    from creme.reports.forms.graph import AbscissaField

    from .base import AbcissaFieldMixin
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class GraphHandConstraintsRegistryTestCase(CremeTestCase):
    def test_empty(self):
        registry = GraphHandConstraintsRegistry()
        self.assertListEqual([], [*registry.cell_constraints(FakeContact)])
        self.assertListEqual([], [*registry.rgraph_types])
        self.assertListEqual([], [*registry.parameter_validators])
        self.assertIsNone(registry.get_constraint_by_rgraph_type(FakeContact, RGT_FK))
        self.assertIsNone(registry.get_parameter_validator(RGT_FK))

    def test_cell_constraints01(self):
        registry = GraphHandConstraintsRegistry().register_cell_constraint(
            constraint_class=GHCCRegularFK,
            rgraph_types=[RGT_FK],
        )

        constraints = [*registry.cell_constraints(FakeContact)]
        self.assertEqual(1, len(constraints))
        self.assertIsInstance(constraints[0], GHCCRegularFK)

        # ---
        get_constraint = registry.get_constraint_by_rgraph_type
        self.assertIsInstance(get_constraint(FakeContact, RGT_FK), GHCCRegularFK)
        self.assertIsNone(get_constraint(FakeContact, RGT_RELATION))

        # ---
        self.assertListEqual([RGT_FK], [*registry.rgraph_types])

    def test_cell_constraints02(self):
        "Several constraints."
        registry = GraphHandConstraintsRegistry(
        ).register_cell_constraint(
            constraint_class=GHCCRegularFK,
            rgraph_types=[RGT_FK],
        ).register_cell_constraint(
            constraint_class=GHCCRelation,
            rgraph_types=[RGT_RELATION],
        )

        self.assertEqual(2, len([*registry.cell_constraints(FakeContact)]))

        # ---
        get_constraint = registry.get_constraint_by_rgraph_type
        self.assertIsInstance(get_constraint(FakeContact, RGT_FK), GHCCRegularFK)
        self.assertIsInstance(get_constraint(FakeContact, RGT_RELATION), GHCCRelation)

        # ---
        self.assertCountEqual([RGT_FK, RGT_RELATION], [*registry.rgraph_types])

    def test_cell_constraints03(self):
        "Several constraints."
        registry = GraphHandConstraintsRegistry().register_cell_constraint(
            constraint_class=GHCCRegularDate,
            rgraph_types=[RGT_MONTH, RGT_YEAR],
        )

        constraints = [*registry.cell_constraints(FakeContact)]
        self.assertEqual(1, len(constraints))  # Not 2
        self.assertIsInstance(constraints[0], GHCCRegularDate)

    def test_cell_constraints04(self):
        "Duplicates constraints."
        registry = GraphHandConstraintsRegistry().register_cell_constraint(
            constraint_class=GHCCRegularFK,
            rgraph_types=[RGT_FK],
        )

        with self.assertRaises(GraphHandConstraintsRegistry.RegistrationError):
            registry.register_cell_constraint(
                constraint_class=GHCCRegularDate,
                rgraph_types=[RGT_FK],  # <==
            )

        # ---
        class TestGHCC(GraphHandCellConstraint):
            type_id = GHCCRegularFK.type_id   # <==

        with self.assertRaises(GraphHandConstraintsRegistry.RegistrationError):
            registry.register_cell_constraint(
                constraint_class=TestGHCC,
                rgraph_types=[RGT_CUSTOM_RANGE],
            )

    def test_validators01(self):
        formfield = forms.IntegerField(label='Number of days')
        registry = GraphHandConstraintsRegistry().register_parameter_validator(
            rgraph_types=[RGT_RANGE, RGT_CUSTOM_RANGE],
            formfield=formfield,
        )
        self.assertCountEqual(
            [(RGT_RANGE, formfield), (RGT_CUSTOM_RANGE, formfield)],
            [*registry.parameter_validators]
        )

        get_validator = registry.get_parameter_validator
        self.assertIsNone(get_validator(RGT_FK))
        self.assertEqual(formfield, get_validator(RGT_RANGE))
        self.assertEqual(formfield, get_validator(RGT_CUSTOM_RANGE))

    def test_validators02(self):
        "Duplicates."
        registry = GraphHandConstraintsRegistry().register_parameter_validator(
            rgraph_types=[RGT_RANGE, RGT_CUSTOM_RANGE],
            formfield=forms.IntegerField(label='Number of days'),
        )

        with self.assertRaises(GraphHandConstraintsRegistry.RegistrationError):
            registry.register_parameter_validator(
                rgraph_types=[RGT_CUSTOM_RANGE],  # <==
                formfield=forms.DecimalField(),
            )


class GraphHandConstraintsTestCase(CremeTestCase):
    def find_rfield_cell(self, cells, field_name):
        for cell in cells:
            finfo = cell.field_info
            if len(finfo) == 1 and finfo[0].name == field_name:
                return

        self.fail(f'{field_name} not found in cells.')

    def test_regular_fk01(self):
        constraint = GHCCRegularFK(model=FakeOrganisation)

        build_cell = EntityCellRegularField.build
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'sector')), True)
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'name')), False)
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'created')), False)

        # ---
        cell1 = constraint.get_cell(cell_key='regular_field-sector')
        self.assertIsInstance(cell1, EntityCellRegularField)
        finfo = cell1.field_info
        self.assertEqual(1, len(finfo))
        self.assertEqual('sector', finfo[0].name)

        self.assertIsNone(constraint.get_cell(cell_key='regular_field-created'))

        # ---
        cells = [*constraint.cells()]
        self.assertEqual(3, len(cells))
        self.assertIsInstance(cells[0], EntityCellRegularField)

        self.find_rfield_cell(cells, 'user')
        self.find_rfield_cell(cells, 'sector')
        self.find_rfield_cell(cells, 'legal_form')

    def test_regular_fk02(self):
        "Fields config."
        constraint = GHCCRegularFK(FakeOrganisation)
        hidden_fname = 'sector'

        other_cell_key = 'regular_field-legal_form'
        hidden_cell_key = f'regular_field-{hidden_fname}'

        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        cells1 = [*constraint.cells()]
        self.assertEqual(2, len(cells1))
        self.assertIsInstance(cells1[0], EntityCellRegularField)

        self.find_rfield_cell(cells1, 'user')
        # self.find_rfield_cell(cells1, 'sector')  # NOPE
        self.find_rfield_cell(cells1, 'legal_form')

        cells2 = [
            *constraint.cells(not_hiddable_cell_keys={other_cell_key})
        ]
        self.assertEqual(2, len(cells2))

        cells3 = [
            *constraint.cells(not_hiddable_cell_keys={other_cell_key, hidden_cell_key})
        ]
        self.assertEqual(3, len(cells3))
        self.find_rfield_cell(cells3, 'sector')

        # ---
        self.assertFalse(
            constraint.check_cell(
                EntityCellRegularField.build(FakeOrganisation, hidden_fname)
            )
        )

        # ---
        cell = constraint.get_cell(cell_key='regular_field-legal_form')
        self.assertIsInstance(cell, EntityCellRegularField)
        finfo = cell.field_info
        self.assertEqual(1, len(finfo))
        self.assertEqual('legal_form', finfo[0].name)


        self.assertIsNone(constraint.get_cell(cell_key=hidden_cell_key))
        self.assertIsNone(constraint.get_cell(cell_key=hidden_cell_key,
                                              not_hiddable_cell_keys={other_cell_key},
                                             )
                         )

        self.assertIsInstance(
            constraint.get_cell(cell_key=hidden_cell_key,
                                not_hiddable_cell_keys={other_cell_key, hidden_cell_key},
                               ),
            EntityCellRegularField
        )

    def test_regular_date01(self):
        constraint = GHCCRegularDate(model=FakeOrganisation)

        build_cell = EntityCellRegularField.build
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'created')), True)
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'name')), False)
        self.assertIs(constraint.check_cell(build_cell(FakeOrganisation, 'sector')), False)

        # ---
        cell1 = constraint.get_cell(cell_key='regular_field-creation_date')
        self.assertIsInstance(cell1, EntityCellRegularField)
        finfo = cell1.field_info
        self.assertEqual(1, len(finfo))
        self.assertEqual('creation_date', finfo[0].name)

        self.assertIsNone(constraint.get_cell(cell_key='regular_field-sector'))

        # ---
        cells = [*constraint.cells(FakeOrganisation)]
        self.assertEqual(3, len(cells))
        self.assertIsInstance(cells[0], EntityCellRegularField)

        self.find_rfield_cell(cells, 'created')
        self.find_rfield_cell(cells, 'modified')
        self.find_rfield_cell(cells, 'creation_date')

    def test_regular_date02(self):
        "Fields config."
        constraint = GHCCRegularDate(model=FakeOrganisation)
        hidden_fname = 'birthday'

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        for cell in constraint.cells(FakeContact):
            finfo = cell.field_info
            if len(finfo) == 1 and finfo[0].name == hidden_fname:
                self.fail(f'{hidden_fname} found in cells (should be hidden).')

        # ---
        self.assertFalse(
            constraint.check_cell(
                EntityCellRegularField.build(FakeContact, hidden_fname)
            )
        )

        # ---
        cell = constraint.get_cell(cell_key='regular_field-created')
        self.assertIsInstance(cell, EntityCellRegularField)

        finfo = cell.field_info
        self.assertEqual(1, len(finfo))
        self.assertEqual('created', finfo[0].name)

        self.assertIsNone(constraint.get_cell(cell_key=f'regular_field-{hidden_fname}'))

    def test_relationship(self):
        constraint = GHCCRelation(model=FakeContact)

        rtype1 = RelationType.create(
            ('test-subject_likes', 'likes'),
            ('test-object_likes',  'is liked by'),
        )[0]
        self.assertTrue(constraint.check_cell(EntityCellRelation(FakeContact, rtype1)))

        rtype2 = RelationType.create(
            ('test-subject_loves', 'is loving',   [FakeContact]),
            ('test-object_loves',  'is loved by', [FakeContact]),
        )[0]
        self.assertTrue(constraint.check_cell(EntityCellRelation(FakeContact, rtype2)))

        rtype3 = RelationType.create(
            ('test-subject_branch', 'has branch',     [FakeOrganisation]),
            ('test-object_branch',  'is a branch of', [FakeOrganisation]),
        )[0]
        self.assertFalse(constraint.check_cell(EntityCellRelation(FakeContact, rtype3)))

        # ---
        cell1 = constraint.get_cell(cell_key=f'relation-{rtype2.id}')
        self.assertIsInstance(cell1, EntityCellRelation)
        self.assertEqual(rtype2, cell1.relation_type)

        self.assertIsNone(constraint.get_cell(cell_key=f'relation-{rtype3.id}'))

        # ---
        cells = [*constraint.cells(FakeContact)]
        self.assertGreaterEqual(len(cells), 2)
        self.assertIsInstance(cells[0], EntityCellRelation)

        def find_cell(rtype):
            for cell in cells:
                if cell.relation_type == rtype:
                    return

            self.fail(f'{rtype} not found in cells.')

        find_cell(rtype1)
        find_cell(rtype2)

        for cell in cells:
            if cell.relation_type == rtype3:
                self.fail(f'{rtype3} should not be found in cells.')

    def test_custom_enum(self):
        constraint = GHCCCustomEnum(model=FakeContact)

        create_cfield = partial(CustomField.objects.create,
                                content_type=FakeContact,
                                field_type=CustomField.ENUM,
                               )
        cfield1 = create_cfield(name='Hair')
        cfield2 = create_cfield(name='First fight', field_type=CustomField.DATETIME)
        cfield3 = create_cfield(name='Main sector', content_type=FakeOrganisation)

        self.assertTrue(constraint.check_cell(EntityCellCustomField(cfield1)))
        self.assertFalse(constraint.check_cell(EntityCellCustomField(cfield2)))

        # ---
        get_cell = constraint.get_cell
        cell1 = get_cell(cell_key=f'custom_field-{cfield1.id}')
        self.assertIsInstance(cell1, EntityCellCustomField)
        self.assertEqual(cfield1, cell1.custom_field)

        self.assertIsNone(get_cell(cell_key=f'custom_field-{cfield2.id}'))
        self.assertIsNone(get_cell(cell_key=f'custom_field-{cfield3.id}'))

        # ---
        cells = [*constraint.cells(FakeContact)]
        self.assertEqual(1, len(cells))

        cell2 = cells[0]
        self.assertIsInstance(cell2, EntityCellCustomField)
        self.assertEqual(cfield1, cell2.custom_field)

    def test_custom_date(self):
        constraint = GHCCCustomDate(model=FakeContact)

        create_cfield = partial(CustomField.objects.create,
                                content_type=FakeContact,
                                field_type=CustomField.DATETIME,
                               )
        cfield1 = create_cfield(name='First fight')
        cfield2 = create_cfield(name='Hair', field_type=CustomField.ENUM)
        cfield3 = create_cfield(name='Main sector', content_type=FakeOrganisation)

        self.assertTrue(constraint.check_cell(EntityCellCustomField(cfield1)))
        self.assertFalse(constraint.check_cell(EntityCellCustomField(cfield2)))

        # ---
        get_cell = constraint.get_cell
        cell1 = get_cell(cell_key=f'custom_field-{cfield1.id}')
        self.assertIsInstance(cell1, EntityCellCustomField)
        self.assertEqual(cfield1, cell1.custom_field)

        self.assertIsNone(get_cell(cell_key=f'custom_field-{cfield2.id}'))
        self.assertIsNone(get_cell(cell_key=f'custom_field-{cfield3.id}'))

        # ---
        cells = [*constraint.cells(FakeContact)]
        self.assertEqual(1, len(cells))

        cell2 = cells[0]
        self.assertIsInstance(cell2, EntityCellCustomField)
        self.assertEqual(cfield1, cell2.custom_field)


class AbscissaFieldTestCase(AbcissaFieldMixin, FieldTestCase):
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
