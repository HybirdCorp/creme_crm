# -*- coding: utf-8 -*-

from functools import partial
from json import dumps as json_dump
from json import loads as json_load

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from parameterized import parameterized

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.forms.header_filter import UniformEntityCellsField
from creme.creme_core.models import (
    CremeEntity,
    CustomField,
    FakeContact,
    FakeInvoiceLine,
    FakeOrganisation,
    FieldsConfig,
    InstanceBrickConfigItem,
    RelationType,
)
from creme.creme_core.tests.fake_constants import (
    FAKE_REL_SUB_BILL_ISSUED,
    FAKE_REL_SUB_EMPLOYED_BY,
)
from creme.creme_core.tests.forms.base import FieldTestCase
from creme.reports import constants
from creme.reports.bricks import ReportGraphBrick
from creme.reports.core.graph import AbscissaInfo, OrdinateInfo
from creme.reports.core.graph.cell_constraint import (
    ACCCount,
    ACCFieldAggregation,
    abscissa_constraints,
    ordinate_constraints,
)
from creme.reports.core.graph.fetcher import (
    RegularFieldLinkedGraphFetcher,
    RelationLinkedGraphFetcher,
    SimpleGraphFetcher,
)
from creme.reports.forms.bricks import (
    FetcherChoiceIterator,
    GraphFetcherField,
    GraphInstanceBrickForm,
)
from creme.reports.forms.graph import AbscissaField, OrdinateField
from creme.reports.forms.report import (
    ReportEntityCellCustomAggregate,
    ReportEntityCellRegularAggregate,
    ReportEntityCellRelated,
    ReportFieldsForm,
    ReportHandsField,
)
from creme.reports.models import FakeReportsDocument, FakeReportsFolder, Field
from creme.reports.report_aggregation_registry import FieldAggregation

from .base import (
    AxisFieldsMixin,
    BaseReportsTestCase,
    Report,
    ReportGraph,
    skipIfCustomReport,
)


class ReportHandsFieldTestCase(FieldTestCase):
    # TODO: factorise with EntityCellsFieldTestCase
    def _find_sub_widget(self, field, cell_class_type_id):
        for sub_widget in field.widget.sub_widgets:
            if sub_widget.type_id == cell_class_type_id:
                return sub_widget

        self.fail(f'Sub-widget not found: {cell_class_type_id}')

    # TODO: factorise with EntityCellsFieldTestCase
    def assertCellInChoices(self, cell_key, label, choices):
        for choice_cell_key, choice_cell in choices:
            if cell_key == choice_cell_key:
                if choice_cell.key != cell_key:
                    self.fail(
                        'The cell has been found, but choice Id does not match the cell key.'
                    )

                cell_str = str(choice_cell)
                if label != cell_str:
                    self.fail(
                        f'The cell has been found, but with the label "{cell_str}".'
                    )

                return choice_cell

        self.fail(
            f'The choice for cell-key="{cell_key}" has not been found.'
        )

    def test_entity_cell_related(self):
        rname = 'fakereportsdocument'
        cell = ReportEntityCellRelated.build(FakeReportsFolder, rname)
        self.assertIsInstance(cell, ReportEntityCellRelated)
        self.assertEqual(FakeReportsFolder, cell.model)
        self.assertEqual(rname,             cell.value)
        self.assertFalse(cell.is_hidden)
        self.assertFalse(cell.is_excluded)
        self.assertEqual('Test (reports) Document', cell.title)

        self.assertIsNone(
            ReportEntityCellRelated.build(FakeReportsFolder, 'invalid')
        )
        self.assertIsNone(
            ReportEntityCellRelated.build(FakeReportsFolder, 'title')
        )
        self.assertIsNone(
            ReportEntityCellRelated.build(FakeReportsFolder, 'parent')
        )

    def test_entity_cell_regular_aggregate(self):
        agg_id = 'capital__avg'
        cell = ReportEntityCellRegularAggregate.build(FakeOrganisation, agg_id)
        self.assertIsInstance(cell, ReportEntityCellRegularAggregate)
        self.assertEqual(FakeOrganisation, cell.model)
        self.assertEqual(agg_id,           cell.value)
        self.assertFalse(cell.is_hidden)
        self.assertFalse(cell.is_excluded)
        self.assertEqual(f"{_('Average')} - {_('Capital')}", cell.title)
        self.assertEqual(FakeOrganisation._meta.get_field('capital'), cell.field)

        aggregation = cell.aggregation
        self.assertIsInstance(aggregation, FieldAggregation)
        self.assertEqual('avg', aggregation.name)

        self.assertIsNone(
            ReportEntityCellRegularAggregate.build(FakeOrganisation, 'invalid__avg')
        )
        self.assertIsNone(
            ReportEntityCellRegularAggregate.build(FakeOrganisation, 'capital__invalid')
        )
        self.assertIsNone(
            ReportEntityCellRegularAggregate.build(FakeOrganisation, 'name__avg')
        )
        self.assertIsNone(
            ReportEntityCellRegularAggregate.build(FakeOrganisation, 'invalid')
        )

    def test_entity_cell_custom_aggregate(self):
        create_cf = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        cf1 = create_cf(field_type=CustomField.INT, name='Rank')
        cf2 = create_cf(field_type=CustomField.STR, name='Tag')
        cf3 = create_cf(field_type=CustomField.INT, name='Size (cm)', content_type=FakeContact)

        agg_id = f'{cf1.id}__avg'
        cell = ReportEntityCellCustomAggregate.build(FakeOrganisation, agg_id)
        self.assertIsInstance(cell, ReportEntityCellCustomAggregate)
        self.assertEqual(FakeOrganisation, cell.model)
        self.assertEqual(agg_id,           cell.value)
        self.assertFalse(cell.is_hidden)
        self.assertFalse(cell.is_excluded)
        self.assertEqual(f"{_('Average')} - {cf1.name}", cell.title)
        self.assertEqual(cf1, cell.custom_field)

        aggregation = cell.aggregation
        self.assertIsInstance(aggregation, FieldAggregation)
        self.assertEqual('avg', aggregation.name)

        self.assertIsNone(
            ReportEntityCellCustomAggregate.build(FakeOrganisation, f'{cf1.id}__invalid')
        )
        self.assertIsNone(
            ReportEntityCellCustomAggregate.build(FakeOrganisation, '1024__avg')
        )
        self.assertIsNone(
            ReportEntityCellCustomAggregate.build(FakeOrganisation, 'notanint__avg')
        )
        self.assertIsNone(
            ReportEntityCellCustomAggregate.build(FakeOrganisation, 'invalid')
        )

        self.assertIsNone(
            ReportEntityCellCustomAggregate.build(FakeOrganisation, f'{cf2.id}__avg')
        )
        self.assertIsNone(
            ReportEntityCellCustomAggregate.build(FakeOrganisation, f'{cf3.id}__avg')
        )

    def test_clean_empty_required(self):
        clean = ReportHandsField(required=True, model=FakeOrganisation).clean
        self.assertFieldValidationError(ReportHandsField, 'required', clean, None)
        self.assertFieldValidationError(ReportHandsField, 'required', clean, '')

    def test_clean_empty_not_required(self):
        field = ReportHandsField(required=False, model=FakeOrganisation)

        with self.assertNoException():
            value = field.clean(None)

        self.assertListEqual([], value)

    def test_regularfields01(self):
        field = ReportHandsField(model=FakeOrganisation)
        self.assertListEqual([], field.non_hiddable_cells)

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices(
            'regular_field-name',
            label=_('Name'),
            choices=choices,
        )
        self.assertCellInChoices(
            'regular_field-sector',
            label=_('Sector'),
            choices=choices,
        )
        self.assertCellInChoices(
            'regular_field-sector__title',
            # TODO: test that's the title in the render...
            label=f"{_('Sector')} - {_('Title')}",
            choices=choices,
        )

        fname1 = 'name'
        self.assertListEqual(
            [EntityCellRegularField.build(FakeOrganisation, fname1)],
            field.clean(f'regular_field-{fname1}')
        )

        fname2 = 'unknown'
        self.assertFieldValidationError(
            UniformEntityCellsField, 'invalid_value', field.clean,
            f'regular_field-{fname2}',
            message_args={'value': fname2},
        )

    def test_regularfields02(self):
        "Avoid FK to CremeEntity as sub-field."
        field = ReportHandsField(model=FakeReportsDocument)

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices(
            'regular_field-title',
            label=_('Title'),
            choices=choices,
        )
        self.assertCellInChoices(
            'regular_field-linked_folder',
            label=_('Folder'),
            choices=choices,
        )
        self.assertCellInChoices(
            'regular_field-linked_folder__title',
            label=f"{_('Folder')} - {_('Title')}",
            choices=choices,
        )
        self.assertNotInChoices(
            'regular_field-linked_folder__parent',
            choices=choices,
        )

        fname1 = 'linked_folder'
        fname2 = 'linked_folder__title'
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeReportsDocument, fname1),
                EntityCellRegularField.build(FakeReportsDocument, fname2),
            ],
            field.clean(f'regular_field-{fname1},regular_field-{fname2}'),
        )

        fname3 = 'linked_folder__parent'
        self.assertFieldValidationError(
            UniformEntityCellsField, 'invalid_value', field.clean,
            f'regular_field-{fname3}',
            message_args={'value': fname3},
        )

    def test_regular_aggregates01(self):
        field = ReportHandsField()
        self.assertListEqual(
            [],
            [*self._find_sub_widget(field, 'regular_aggregate').choices],
        )

        field.model = FakeOrganisation
        fvname = _('Capital')
        choices = self._find_sub_widget(field, 'regular_aggregate').choices
        self.assertCellInChoices(
            'regular_aggregate-capital__avg',
            label=f"{_('Average')} - {fvname}",
            choices=choices,
        )
        self.assertCellInChoices(
            'regular_aggregate-capital__min',
            label=f"{_('Minimum')} - {fvname}",
            choices=choices,
        )
        self.assertCellInChoices(
            'regular_aggregate-capital__max',
            label=f"{_('Maximum')} - {fvname}",
            choices=choices,
        )
        self.assertCellInChoices(
            'regular_aggregate-capital__sum',
            label=f"{_('Sum')} - {fvname}",
            choices=choices,
        )

        agg_id1 = 'capital__avg'
        self.assertListEqual(
            [ReportEntityCellRegularAggregate.build(FakeOrganisation, agg_id1)],
            field.clean(f'regular_aggregate-{agg_id1}'),
        )

        agg_id2 = 'invalid'
        self.assertFieldValidationError(
            UniformEntityCellsField, 'invalid_value', field.clean,
            f'regular_aggregate-{agg_id2}',
            message_args={'value': agg_id2},
        )

    def test_regular_aggregates02(self):
        "Field is hidden."
        field_name = 'capital'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(field_name, {FieldsConfig.HIDDEN: True})],
        )

        field = ReportHandsField(model=FakeOrganisation)
        self.assertListEqual(
            [],
            [*self._find_sub_widget(field, 'regular_aggregate').choices],
        )
        self.assertFieldValidationError(
            UniformEntityCellsField, 'invalid_value', field.clean,
            'regular_aggregate-capital__avg',
            message_args={'value': 'capital__avg'},
        )

    def test_regular_aggregates03(self):
        "Field is hidden but already used => it is still proposed."
        hidden_fname = 'capital'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        field = ReportHandsField(model=FakeOrganisation)
        field.non_hiddable_cells = [
            ReportEntityCellRegularAggregate.build(FakeOrganisation, f'{hidden_fname}__avg'),
        ]

        self.assertListEqual(
            [('regular_aggregate-capital__avg', f"{_('Average')} - {_('Capital')}")],
            [
                (choice_id, str(cell))
                for choice_id, cell in self._find_sub_widget(field, 'regular_aggregate').choices
            ],
        )

        agg_id = 'capital__avg'
        self.assertListEqual(
            [ReportEntityCellRegularAggregate.build(FakeOrganisation, agg_id)],
            field.clean(f'regular_aggregate-{agg_id}')
        )

    def test_custom_aggregates01(self):
        create_cf = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        cf1 = create_cf(field_type=CustomField.INT, name='Rank')
        create_cf(field_type=CustomField.STR, name='Tag')
        create_cf(
            field_type=CustomField.BOOL, name='Operational?',
            content_type=FakeContact,
        )

        field = ReportHandsField()
        self.assertListEqual(
            [],
            [*self._find_sub_widget(field, 'custom_aggregate').choices],
        )

        field.model = FakeOrganisation
        choices = self._find_sub_widget(field, 'custom_aggregate').choices
        value = f'custom_aggregate-{cf1.id}__avg'
        self.assertCellInChoices(
            value,
            label=f"{_('Average')} - {cf1.name}",
            choices=choices,
        )
        self.assertCellInChoices(
            f'custom_aggregate-{cf1.id}__min',
            label=f"{_('Minimum')} - {cf1.name}",
            choices=choices,
        )
        self.assertCellInChoices(
            f'custom_aggregate-{cf1.id}__max',
            label=f"{_('Maximum')} - {cf1.name}",
            choices=choices,
        )
        self.assertCellInChoices(
            f'custom_aggregate-{cf1.id}__sum',
            label=f"{_('Sum')} - {cf1.name}",
            choices=choices,
        )

        self.assertListEqual(
            [ReportEntityCellCustomAggregate.build(FakeOrganisation, f'{cf1.id}__avg')],
            field.clean(value),
        )

    def test_custom_aggregates02(self):
        "Field is deleted."
        cfield = CustomField.objects.create(
            content_type=FakeOrganisation,
            field_type=CustomField.INT, name='Rank',
            is_deleted=True,
        )

        field = ReportHandsField(model=FakeOrganisation)
        self.assertListEqual(
            [],
            [*self._find_sub_widget(field, 'custom_aggregate').choices]
        )
        self.assertFieldValidationError(
            UniformEntityCellsField, 'invalid_value', field.clean,
            f'custom_aggregate-{cfield.id}__avg',
            message_args={'value': f'{cfield.id}__avg'},
        )

    def test_custom_aggregates03(self):
        "Field is deleted but already used => it is still proposed."
        cfield = CustomField.objects.create(
            content_type=FakeOrganisation,
            field_type=CustomField.INT, name='Rank',
            is_deleted=True,
        )

        field = ReportHandsField(model=FakeOrganisation)
        field.non_hiddable_cells = [
            ReportEntityCellCustomAggregate.build(FakeOrganisation, f'{cfield.id}__avg'),
        ]

        agg_id = f'custom_aggregate-{cfield.id}__avg'
        self.assertListEqual(
            [(agg_id, f"{_('Average')} - {cfield.name}")],
            [
                (choice_id, str(cell))
                for choice_id, cell in self._find_sub_widget(field, 'custom_aggregate').choices
            ],
        )

        self.assertListEqual(
            [ReportEntityCellCustomAggregate.build(FakeOrganisation, f'{cfield.id}__avg')],
            field.clean(agg_id),
        )

    def test_related(self):
        field = ReportHandsField()
        self.assertListEqual(
            [],
            [*self._find_sub_widget(field, 'related').choices],
        )

        field.model = FakeReportsFolder
        rname = 'fakereportsdocument'
        value = f'related-{rname}'
        self.assertCellInChoices(
            value,
            label='Test (reports) Document',
            choices=self._find_sub_widget(field, 'related').choices,
        )

        self.assertListEqual(
            [ReportEntityCellRelated.build(model=FakeReportsFolder, related_name=rname)],
            field.clean(value),
        )


@skipIfCustomReport
class ReportFieldsFormTestCase(BaseReportsTestCase):
    def test_initial01(self):
        user = self.create_user()
        report = self._create_simple_contacts_report(user=user)

        rtype = self.get_object_or_fail(RelationType, id=REL_SUB_HAS)
        func_name = 'get_pretty_properties'
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            name='Hair',
            field_type=CustomField.ENUM,
        )

        create_rfield = partial(Field.objects.create, report=report)
        create_rfield(type=constants.RFT_RELATION, name=rtype.id,       order=3)
        create_rfield(type=constants.RFT_FUNCTION, name=func_name,      order=3)
        create_rfield(type=constants.RFT_CUSTOM,   name=str(cfield.id), order=4)

        form = ReportFieldsForm(user=user, instance=report)

        columns_f = form.fields['columns']
        self.assertIsInstance(columns_f, ReportHandsField)
        # self.assertEqual(self.ct_contact, columns_f.content_type)
        self.assertEqual(FakeContact, columns_f.model)

        cells = [
            EntityCellRegularField.build(FakeContact, 'last_name'),
            EntityCellRelation(model=FakeContact, rtype=rtype),
            EntityCellFunctionField.build(FakeContact, func_name),
            EntityCellCustomField(cfield),
        ]
        self.assertListEqual(cells, columns_f.initial)
        self.assertListEqual(cells, columns_f.non_hiddable_cells)

    def test_initial02(self):
        "Regular aggregate."
        user = self.create_user()
        report = Report.objects.create(
            user=user,
            name='Organisation report',
            ct=FakeOrganisation,
        )

        agg_id = 'capital__max'
        Field.objects.create(
            report=report,
            type=constants.RFT_AGG_FIELD, name=agg_id,
            order=1,
        )

        form = ReportFieldsForm(user=user, instance=report)

        columns_f = form.fields['columns']
        # self.assertEqual(self.ct_orga, columns_f.content_type)
        self.assertEqual(FakeOrganisation, columns_f.model)
        self.assertListEqual(
            [ReportEntityCellRegularAggregate.build(FakeOrganisation, agg_id)],
            columns_f.initial,
        )

    def test_initial03(self):
        "Custom aggregate."
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            name='Hair size',
            field_type=CustomField.INT,
        )

        user = self.create_user()
        report = Report.objects.create(
            user=user,
            name='Contact report',
            ct=self.ct_contact,
        )

        agg_id = f'{cfield.id}__max'
        Field.objects.create(
            report=report,
            type=constants.RFT_AGG_CUSTOM, name=agg_id,
            order=1,
        )

        form = ReportFieldsForm(user=user, instance=report)
        self.assertListEqual(
            [ReportEntityCellCustomAggregate.build(FakeContact, agg_id)],
            form.fields['columns'].initial,
        )

    def test_initial04(self):
        "Related field."
        user = self.create_user()
        report = Report.objects.create(
            user=user,
            name='Folder report',
            ct=self.ct_folder,
        )

        name = 'fakereportsdocument'
        Field.objects.create(
            report=report,
            type=constants.RFT_RELATED, name=name,
            order=1,
        )

        form = ReportFieldsForm(user=user, instance=report)
        self.assertListEqual(
            [ReportEntityCellRelated.build(FakeReportsFolder, name)],
            form.fields['columns'].initial,
        )


class AbscissaFieldTestCase(AxisFieldsMixin, FieldTestCase):
    def test_clean_empty_not_required(self):
        with self.assertNoException():
            cleaned = AbscissaField(required=False).clean(None)

        self.assertIsNone(cleaned)

    def test_clean_invalid_json(self):
        self.assertFieldValidationError(
            AbscissaField, 'invalidformat',
            AbscissaField(required=False).clean,
            '{"entity_cell":{"cell_key":',
        )

    def test_clean_invalid_data_type(self):
        clean = AbscissaField(required=False).clean
        self.assertFieldValidationError(AbscissaField, 'invalidtype', clean, '"this is a string"')
        self.assertFieldValidationError(AbscissaField, 'invalidtype', clean, '[]')

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
        # graph_type = constants.RGT_FK
        graph_type = ReportGraph.Group.FK

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)
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
        # graph_type = constants.RGT_YEAR
        graph_type = ReportGraph.Group.YEAR

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

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
        field = AbscissaField(model=FakeContact, abscissa_constraints=abscissa_constraints)

        # graph_type = constants.RGT_MONTH
        graph_type = ReportGraph.Group.MONTH
        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field('birthday'),
            graph_type=graph_type,
        ))
        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_rfield_date_day(self):
        field = AbscissaField(model=FakeContact, abscissa_constraints=abscissa_constraints)

        # graph_type = constants.RGT_DAY
        graph_type = ReportGraph.Group.DAY
        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field('birthday'),
            graph_type=graph_type,
        ))
        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_rfield_range(self):
        model = FakeContact
        field_name = 'created'
        # graph_type = constants.RGT_RANGE
        graph_type = ReportGraph.Group.RANGE
        days = 3

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

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
        field = AbscissaField(
            model=model, abscissa_constraints=abscissa_constraints,
        )

        self.assertFieldValidationError(
            AbscissaField, 'ecellrequired', field.clean,
            json_dump({
                # 'entity_cell': {
                #     'cell_key': ...,
                # },
                'graph_type': {
                    # 'type_id': constants.RGT_FK,
                    'type_id': ReportGraph.Group.FK,
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
                    # 'type_id': constants.RGT_FK,
                    'type_id': ReportGraph.Group.FK,
                },
                'parameter': '',
            })
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=model._meta.get_field('name'),  # <= forbidden field
                # graph_type=constants.RGT_FK,
                graph_type=ReportGraph.Group.FK,
            ),
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            json_dump({
                'entity_cell': {
                    'cell_key': 'regular_field-sector__title',  # <= forbidden field
                },
                'graph_type': {
                    # 'type_id': constants.RGT_FK,
                    'type_id': ReportGraph.Group.FK,
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
                    # 'type_id': constants.RGT_YEAR,
                    'type_id': ReportGraph.Group.YEAR,
                },
                'parameter': '',
            })
        )

    def test_clean_rfield_error02(self):
        "Error on graph type."
        model = FakeOrganisation
        field = AbscissaField(
            model=model, abscissa_constraints=abscissa_constraints,
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
                # graph_type=constants.RGT_YEAR,  # < ===
                graph_type=ReportGraph.Group.YEAR,  # < ===
            ),
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=sector_field,
                # graph_type=constants.RGT_MONTH,  # < ===
                graph_type=ReportGraph.Group.MONTH,  # < ===
            ),
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=sector_field,
                # graph_type=constants.RGT_DAY,  # < ===
                graph_type=ReportGraph.Group.DAY,  # < ===
            ),
        )

    def test_clean_rfield_error03(self):
        "Error on extra parameter."
        model = FakeContact
        field = AbscissaField(
            model=model, abscissa_constraints=abscissa_constraints,
        )

        abscissa = model._meta.get_field('created')
        # graph_type = constants.RGT_RANGE
        graph_type = ReportGraph.Group.RANGE

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
            exception.message,
        )

    def test_clean_rfield_fields_config(self):
        model = FakeOrganisation
        field_name = 'sector'
        # graph_type = constants.RGT_FK
        graph_type = ReportGraph.Group.FK

        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[(field_name, {FieldsConfig.HIDDEN: True})],
        )

        field = AbscissaField(
            model=model, abscissa_constraints=abscissa_constraints,
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
        # graph_type = constants.RGT_RELATION
        graph_type = ReportGraph.Group.RELATION
        rtype = RelationType.objects.compatible(model)[0]

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

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
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving',   [FakeContact]),
            ('test-object_foobar',  'is loved by', [FakeContact]),
        )[0]

        field = AbscissaField(
            model=model, abscissa_constraints=abscissa_constraints,
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=rtype,
                # graph_type=constants.RGT_RELATION,
                graph_type=ReportGraph.Group.RELATION,
            ),
        )

    def test_clean_cfield_enum01(self):
        model = FakeContact
        # graph_type = constants.RGT_CUSTOM_FK
        graph_type = ReportGraph.Group.CUSTOM_FK
        cfield = CustomField.objects.create(
            content_type=model,
            name='Hair',
            field_type=CustomField.ENUM,
        )

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

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

    def test_clean_cfield_enum02(self):
        "Field is deleted."
        model = FakeContact
        # graph_type = constants.RGT_CUSTOM_FK
        graph_type = ReportGraph.Group.CUSTOM_FK
        cfield = CustomField.objects.create(
            content_type=model,
            name='Hair',
            field_type=CustomField.ENUM,
            is_deleted=True,
        )

        field = AbscissaField(
            model=model,
            abscissa_constraints=abscissa_constraints,
        )

        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(abscissa=cfield, graph_type=graph_type),
        )

        # ---
        cell = EntityCellCustomField(cfield)
        init_abs_info = AbscissaInfo(cell=cell, graph_type=graph_type)
        field.initial = init_abs_info
        self.assertSetEqual({cell.key}, field.not_hiddable_cell_keys)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield,
            graph_type=graph_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

    @parameterized.expand([
        (CustomField.DATETIME,),
        (CustomField.DATE,),
    ])
    # def test_clean_cfield_date_year(self):
    def test_clean_cfield_date_year(self, cfield_type):
        model = FakeContact
        # graph_type = constants.RGT_CUSTOM_YEAR
        graph_type = ReportGraph.Group.CUSTOM_YEAR
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            # field_type=CustomField.DATETIME,
            field_type=cfield_type,
        )

        field = AbscissaField(
            model=model, abscissa_constraints=abscissa_constraints,
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

    @parameterized.expand([
        (CustomField.DATETIME,),
        (CustomField.DATE,),
    ])
    # def test_clean_cfield_date_month(self):
    def test_clean_cfield_date_month(self, cfield_type):
        model = FakeContact
        # graph_type = constants.RGT_CUSTOM_MONTH
        graph_type = ReportGraph.Group.CUSTOM_MONTH
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            # field_type=CustomField.DATETIME,
            field_type=cfield_type,
        )

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield, graph_type=graph_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(model, cell.model)
        self.assertEqual(str(cfield.id), cell.value)

        self.assertEqual(graph_type, abs_info.graph_type)
        self.assertIsNone(abs_info.parameter)

    @parameterized.expand([
        (CustomField.DATETIME,),
        (CustomField.DATE,),
    ])
    # def test_clean_cfield_date_day(self):
    def test_clean_cfield_date_day(self, cfield_type):
        model = FakeContact
        # graph_type = constants.RGT_CUSTOM_DAY
        graph_type = ReportGraph.Group.CUSTOM_DAY
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            # field_type=CustomField.DATETIME,
            field_type=cfield_type,
        )

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield, graph_type=graph_type,
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
        # graph_type = constants.RGT_CUSTOM_RANGE
        graph_type = ReportGraph.Group.CUSTOM_RANGE
        days = 5
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=CustomField.DATETIME,
        )
        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)
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
        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=cfield1,
                # graph_type=constants.RGT_CUSTOM_FK,
                graph_type=ReportGraph.Group.CUSTOM_FK,
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
                # graph_type=constants.RGT_CUSTOM_FK,
                graph_type=ReportGraph.Group.CUSTOM_FK,
            ),
        )

    def test_clean_cfield_error02(self):
        "Error on graph type."
        model = FakeOrganisation
        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

        cfield_enum = CustomField.objects.create(
            content_type=model,
            name='Type',
            field_type=CustomField.ENUM,
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=cfield_enum,
                # graph_type=constants.RGT_CUSTOM_YEAR,
                graph_type=ReportGraph.Group.CUSTOM_YEAR,
            ),
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=cfield_enum,
                # graph_type=constants.RGT_CUSTOM_MONTH,
                graph_type=ReportGraph.Group.CUSTOM_MONTH,
            ),
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=cfield_enum,
                # graph_type=constants.RGT_CUSTOM_DAY,
                graph_type=ReportGraph.Group.CUSTOM_DAY,
            ),
        )
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            self.formfield_value_abscissa(
                abscissa=cfield_enum,
                # graph_type=constants.RGT_CUSTOM_RANGE,
                graph_type=ReportGraph.Group.CUSTOM_RANGE,
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
                # graph_type=constants.RGT_CUSTOM_FK,
                graph_type=ReportGraph.Group.CUSTOM_FK,
            ),
        )

    def test_clean_cfield_error03(self):
        "Error on extra parameter."
        model = FakeContact
        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)
        # graph_type = constants.RGT_CUSTOM_RANGE
        graph_type = ReportGraph.Group.CUSTOM_RANGE

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
            exception.message,
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
            exception.message,
        )

    def test_clean_error01(self):
        "Error on cell."
        model = FakeOrganisation
        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)
        cell = EntityCellFunctionField.build(FakeContact, 'get_pretty_properties')
        self.assertFieldValidationError(
            AbscissaField, 'ecellnotallowed', field.clean,
            json_dump({
                'entity_cell': {
                    'cell_key': cell.key,
                },
                'graph_type': {
                    # 'type_id': constants.RGT_FK,
                    'type_id': ReportGraph.Group.FK,
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
                    # 'type_id': constants.RGT_FK,
                    'type_id': ReportGraph.Group.FK,
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
                    # 'type_id': constants.RGT_FK,
                    'type_id': ReportGraph.Group.FK,
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
                    # 'type_id': constants.RGT_FK,
                    'type_id': ReportGraph.Group.FK,
                },
                'parameter': '',
            })
        )

    def test_clean_error02(self):
        "Error on graph type."
        model = FakeContact
        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)
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
        # graph_type = constants.RGT_YEAR
        graph_type = ReportGraph.Group.YEAR

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

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
        field = AbscissaField(
            model=model,
            abscissa_constraints=abscissa_constraints,
            required=False,
        )
        self.assertIsNone(field.clean(self.formfield_value_abscissa(
            abscissa=None,
            graph_type='',
        )))
        self.assertIsNone(field.clean(self.formfield_value_abscissa(
            abscissa=model._meta.get_field('sector'),
            graph_type='',
        )))

    def test_clean_no_model01(self):
        "Regular field."
        field = AbscissaField(abscissa_constraints=abscissa_constraints)
        self.assertIs(field.model, CremeEntity)

        field_name = 'created'
        # graph_type = constants.RGT_YEAR
        graph_type = ReportGraph.Group.YEAR
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

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_likes', 'likes'),
            ('test-object_likes',  'is liked by'),
        )[0]

        # graph_type = constants.RGT_RELATION
        graph_type = ReportGraph.Group.RELATION

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
        field = AbscissaField(
            model=FakeOrganisation, abscissa_constraints=abscissa_constraints,
        )
        cell = EntityCellRegularField.build(FakeOrganisation, 'sector')
        # graph_type = constants.RGT_FK
        graph_type = ReportGraph.Group.FK
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
            json_load(field.from_python(
                AbscissaInfo(cell=cell, graph_type=graph_type)
            )),
        )

    def test_from_python_rfield_date(self):
        from_python = AbscissaField(
            model=FakeOrganisation,
            abscissa_constraints=abscissa_constraints,
        ).from_python
        cell = EntityCellRegularField.build(FakeOrganisation, 'creation_date')

        # graph_type1 = constants.RGT_YEAR
        graph_type1 = ReportGraph.Group.YEAR
        self.assertDictEqual(
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
            json_load(from_python(AbscissaInfo(cell=cell, graph_type=graph_type1))),
        )

        # graph_type2 = constants.RGT_RANGE
        graph_type2 = ReportGraph.Group.RANGE
        parameter = '5'
        self.assertDictEqual(
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
            json_load(from_python(AbscissaInfo(
                cell=cell, graph_type=graph_type2, parameter=parameter,
            ))),
        )

    def test_from_python_relation(self):
        field = AbscissaField(
            model=FakeOrganisation, abscissa_constraints=abscissa_constraints,
        )
        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        cell = EntityCellRelation(model=FakeOrganisation, rtype=rtype)
        # graph_type = constants.RGT_RELATION
        graph_type = ReportGraph.Group.RELATION
        self.assertDictEqual(
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
            json_load(field.from_python(
                AbscissaInfo(cell=cell, graph_type=graph_type)
            )),
        )

    def test_from_python_cfield_enum(self):
        model = FakeContact
        cfield = CustomField.objects.create(
            content_type=model,
            name='Hair',
            field_type=CustomField.ENUM,
        )

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)
        cell = EntityCellCustomField(cfield)
        # graph_type = constants.RGT_CUSTOM_FK
        graph_type = ReportGraph.Group.CUSTOM_FK
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
            json_load(field.from_python(
                AbscissaInfo(cell=cell, graph_type=graph_type)
            )),
        )

    def test_from_python_cfield_date(self):
        model = FakeContact
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=CustomField.DATETIME,
        )

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)
        cell = EntityCellCustomField(cfield)
        # graph_type = constants.RGT_CUSTOM_DAY
        graph_type = ReportGraph.Group.CUSTOM_DAY
        self.assertDictEqual(
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
            json_load(field.from_python(
                AbscissaInfo(cell=cell, graph_type=graph_type))
            ),
        )


class OrdinateFieldTestCase(AxisFieldsMixin, FieldTestCase):
    def test_clean_empty_not_required(self):
        with self.assertNoException():
            cleaned = OrdinateField(required=False).clean(None)

        self.assertIsNone(cleaned)

    def test_clean_invalid_json(self):
        self.assertFieldValidationError(
            OrdinateField, 'invalidformat',
            OrdinateField(required=False).clean,
            '{"entity_cell":{"cell_key":',
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
        # aggr_id =  constants.RGA_COUNT
        aggr_id = ReportGraph.Aggregator.COUNT

        field = OrdinateField(model=model, ordinate_constraints=ordinate_constraints)
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
        # aggr_id = constants.RGA_SUM
        aggr_id = ReportGraph.Aggregator.SUM

        field = OrdinateField(model=model, ordinate_constraints=ordinate_constraints)
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
        # aggr_id = constants.RGA_AVG
        aggr_id = ReportGraph.Aggregator.AVG

        field = OrdinateField(model=model, ordinate_constraints=ordinate_constraints)

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
        field = OrdinateField(model=model, ordinate_constraints=ordinate_constraints)

        self.assertFieldValidationError(
            OrdinateField, 'aggridrequired', field.clean,
            json_dump({
                # 'aggregator': {
                #     'aggr_id': ...,
                # },
                'entity_cell': {
                    'cell_key': 'regular_field-capital',
                },
            }),
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
            }),
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
            }),
        )

    def test_clean_rfield_error02(self):
        "Error on cell."
        model = FakeInvoiceLine
        field = OrdinateField(
            model=model, ordinate_constraints=ordinate_constraints,
        )

        self.assertFieldValidationError(
            OrdinateField, 'ecellrequired', field.clean,
            json_dump({
                'aggregator': {
                    # 'aggr_id': constants.RGA_MIN,
                    'aggr_id': ReportGraph.Aggregator.MIN,
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
                    # 'aggr_id': constants.RGA_MIN,
                    'aggr_id': ReportGraph.Aggregator.MIN,
                },
                'entity_cell': {
                    # 'cell_key': ...,
                },
            })
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellrequired', field.clean,
            self.formfield_value_ordinate(
                # aggr_id=constants.RGA_MIN,
                aggr_id=ReportGraph.Aggregator.MIN,
                # cell=...
            ),
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                # aggr_id=constants.RGA_SUM,
                aggr_id=ReportGraph.Aggregator.SUM,
                # forbidden field:
                cell=EntityCellRegularField.build(model, 'item'),
            ),
        )

        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                # aggr_id=constants.RGA_SUM,
                aggr_id=ReportGraph.Aggregator.SUM,
                # field too deep:
                cell=EntityCellRegularField.build(model, 'linked_invoice__total_vat'),
            ),
        )

        # TODO: not viewable

    def test_clean_rfield_fields_config(self):
        model = FakeOrganisation
        field_name = 'capital'
        # aggr_id1 = constants.RGA_SUM
        aggr_id1 = ReportGraph.Aggregator.SUM

        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[(field_name, {FieldsConfig.HIDDEN: True})],
        )

        field = OrdinateField(model=model, ordinate_constraints=ordinate_constraints)

        self.assertIsNone(field.initial)
        self.assertSetEqual(set(), field.not_hiddable_cell_keys)
        self.assertSetEqual(set(), field.widget.not_hiddable_cell_keys)

        cell = EntityCellRegularField.build(model, field_name)
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(aggr_id=aggr_id1, cell=cell),
        )

        # ---
        init_ord_info1 = OrdinateInfo(aggr_id=aggr_id1, cell=cell)
        field.initial = init_ord_info1
        self.assertEqual(init_ord_info1, field.initial)
        self.assertSetEqual({cell.key}, field.not_hiddable_cell_keys)
        self.assertSetEqual({cell.key}, field.widget.not_hiddable_cell_keys)

        ord_info1 = field.clean(self.formfield_value_ordinate(
            aggr_id=aggr_id1, cell=cell,
        ))
        self.assertIsInstance(ord_info1, OrdinateInfo)

        # cell is None ---
        # aggr_id2 = constants.RGA_COUNT
        aggr_id2 = ReportGraph.Aggregator.COUNT
        init_ord_info2 = OrdinateInfo(aggr_id=aggr_id2)
        field.initial = init_ord_info2
        self.assertEqual(init_ord_info2, field.initial)
        self.assertSetEqual(set(), field.not_hiddable_cell_keys)
        self.assertSetEqual(set(), field.widget.not_hiddable_cell_keys)

    def test_clean_cfield_int(self):
        model = FakeContact
        # aggr_id = constants.RGA_MAX
        aggr_id = ReportGraph.Aggregator.MAX
        cfield = CustomField.objects.create(
            content_type=model,
            name='Hair length',
            field_type=CustomField.INT,
        )

        field = OrdinateField(
            model=model, ordinate_constraints=ordinate_constraints,
        )

        ord_info = field.clean(self.formfield_value_ordinate(
            aggr_id=aggr_id, cell=EntityCellCustomField(cfield),
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
        field = OrdinateField(
            model=model, ordinate_constraints=ordinate_constraints,
        )

        cfield_str = CustomField.objects.create(
            content_type=model,
            name='Tags',
            field_type=CustomField.STR,
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                # aggr_id=constants.RGA_SUM,
                aggr_id=ReportGraph.Aggregator.SUM,
                cell=EntityCellCustomField(cfield_str),
            ),
        )

    def test_clean_cfield_error02(self):
        "Error on cell."
        field = OrdinateField(
            model=FakeOrganisation,
            ordinate_constraints=ordinate_constraints,
        )

        cfield = CustomField.objects.create(
            content_type=FakeContact,  # <== wrong model
            name='Size',
            field_type=CustomField.INT,
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                # aggr_id=constants.RGA_SUM,
                aggr_id=ReportGraph.Aggregator.SUM,
                cell=EntityCellCustomField(cfield),
            ),
        )

        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                # aggr_id=constants.RGA_COUNT,
                aggr_id=ReportGraph.Aggregator.COUNT,
                cell=EntityCellRegularField.build(FakeOrganisation, 'capital'),
            ),
        )

    def test_clean_cfield_error03(self):
        "Field is deleted."
        field = OrdinateField(
            model=FakeOrganisation,
            ordinate_constraints=ordinate_constraints,
        )

        cfield = CustomField.objects.create(
            content_type=FakeOrganisation,
            name='Size',
            field_type=CustomField.INT,
            is_deleted=True,
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                # aggr_id=constants.RGA_SUM,
                aggr_id=ReportGraph.Aggregator.SUM,
                cell=EntityCellCustomField(cfield),
            ),
        )

        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                # aggr_id=constants.RGA_COUNT,
                aggr_id=ReportGraph.Aggregator.COUNT,
                cell=EntityCellRegularField.build(FakeOrganisation, 'capital'),
            ),
        )

    def test_clean_error(self):
        "Error on cell."
        model = FakeOrganisation
        field = OrdinateField(model=model, ordinate_constraints=ordinate_constraints)
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            self.formfield_value_ordinate(
                # aggr_id=constants.RGA_SUM,
                aggr_id=ReportGraph.Aggregator.SUM,
                cell=EntityCellFunctionField.build(FakeContact, 'get_pretty_properties'),
            ),
        )
        self.assertFieldValidationError(
            OrdinateField, 'ecellnotallowed', field.clean,
            json_dump({
                'aggregator': {
                    # 'aggr_id': constants.RGA_SUM,
                    'aggr_id': ReportGraph.Aggregator.SUM,
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
                    # 'aggr_id': constants.RGA_SUM,
                    'aggr_id': ReportGraph.Aggregator.SUM,
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
        field = OrdinateField(
            model=model,
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
        field = OrdinateField(
            model=FakeOrganisation,
            ordinate_constraints=ordinate_constraints,
        )
        # aggr_id = constants.RGA_COUNT
        aggr_id = ReportGraph.Aggregator.COUNT
        self.assertDictEqual(
            {
                'aggregator': {
                    'aggr_id': aggr_id,
                    'aggr_category': ACCCount.type_id,
                },
                'entity_cell': None,
            },
            json_load(field.from_python(OrdinateInfo(aggr_id=aggr_id))),
        )

    def test_from_python_rfield_int(self):
        field = OrdinateField(
            model=FakeOrganisation,
            ordinate_constraints=ordinate_constraints,
        )
        cell = EntityCellRegularField.build(FakeOrganisation, 'capital')
        # aggr_id = constants.RGA_AVG
        aggr_id = ReportGraph.Aggregator.AVG
        category = ACCFieldAggregation.type_id
        self.assertDictEqual(
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
            json_load(field.from_python(OrdinateInfo(aggr_id=aggr_id, cell=cell))),
        )

    def test_from_python_cfield_int(self):
        model = FakeContact
        cfield = CustomField.objects.create(
            content_type=model,
            name='Hair',
            field_type=CustomField.INT,
        )

        field = OrdinateField(
            model=model, ordinate_constraints=ordinate_constraints,
        )
        cell = EntityCellCustomField(cfield)
        # aggr_id = constants.RGA_SUM
        aggr_id = ReportGraph.Aggregator.SUM
        category = ACCFieldAggregation.type_id
        self.assertDictEqual(
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
            json_load(field.from_python(OrdinateInfo(aggr_id=aggr_id, cell=cell))),
        )


class GraphFetcherFieldTestCase(FieldTestCase):
    def _build_graph(self):
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)

        return ReportGraph(user=user, name='Field Test', linked_report=report)

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            cleaned = GraphFetcherField(required=False).clean(None)

        self.assertIsNone(cleaned)

    def test_clean_empty_required(self):
        field = GraphFetcherField()
        self.assertTrue(field.required)

        with self.assertRaises(ValidationError) as cm:
            field.clean(None)

        exception = cm.exception
        self.assertEqual('required', exception.code)
        self.assertEqual(_('This field is required.'), exception.message)

    def test_graph_n_iterator01(self):
        graph = self._build_graph()

        field = GraphFetcherField()
        self.assertIsNone(field.graph)
        self.assertEqual('|', field.choice_separator)

        choices_it1 = field.widget.choices
        self.assertIsInstance(choices_it1, FetcherChoiceIterator)
        self.assertIsNone(choices_it1.graph)
        self.assertEqual('|', choices_it1.separator)
        self.assertFalse([*choices_it1])

        # ---
        field.graph = graph
        self.assertEqual(graph, field.graph)

        choices_it2 = field.widget.choices
        self.assertEqual(graph, choices_it2.graph)

        choices = [*choices_it2]
        self.assertInChoices(
            value=f'{constants.RGF_NOLINK}|',
            label=pgettext('reports-volatile_choice', 'None'),
            choices=choices,
        )

        fields_group = self.get_choices_group_or_fail(_('Fields'), choices)
        self.assertInChoices(
            value=f'{constants.RGF_FK}|image',
            label=_('Photograph'),
            choices=fields_group,
        )
        self.assertNotInChoices(f'{constants.RGF_FK}|is_user', fields_group)

        relations_group = self.get_choices_group_or_fail(_('Relationships'), choices)
        self.assertInChoices(
            value=f'{constants.RGF_RELATION}|{FAKE_REL_SUB_EMPLOYED_BY}',
            label='is an employee of — employs',
            choices=relations_group,
        )
        self.assertNotInChoices(
            f'{constants.RGF_RELATION}|{FAKE_REL_SUB_BILL_ISSUED}',
            relations_group,
        )

    def test_graph_n_iterator02(self):
        "Hidden field."
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('image', {FieldsConfig.HIDDEN: True})],
        )

        graph = self._build_graph()

        field = GraphFetcherField(graph=graph)
        choices = [*field.widget.choices]
        self.get_choices_group_or_fail(_('Relationships'), choices)

        empty_group_name = _('Fields')
        for choice in choices:
            if choice[0] == empty_group_name:
                self.fail(f'Group "{empty_group_name}" unexpectedly found.')

    def test_clean_ok(self):
        graph = self._build_graph()

        field = GraphFetcherField(graph=graph)
        self.assertEqual(graph, field.graph)

        # RGF_NOLINK ---
        fetcher1a = field.clean(value=constants.RGF_NOLINK)
        self.assertIsInstance(fetcher1a, SimpleGraphFetcher)
        self.assertIsNone(fetcher1a.error)

        fetcher1b = field.clean(value=f'{constants.RGF_NOLINK}|')
        self.assertIsInstance(fetcher1b, SimpleGraphFetcher)
        self.assertIsNone(fetcher1b.error)

        # RGF_FK ---
        fetcher2 = field.clean(value=f'{constants.RGF_FK}|image')
        self.assertIsInstance(fetcher2, RegularFieldLinkedGraphFetcher)
        self.assertIsNone(fetcher2.error)
        rfield = fetcher2._field
        self.assertEqual('image',     rfield.name)
        self.assertEqual(FakeContact, rfield.model)

        # RGF_RELATION ---
        fetcher3 = field.clean(
            value=f'{constants.RGF_RELATION}|{FAKE_REL_SUB_EMPLOYED_BY}',
        )
        self.assertIsInstance(fetcher3, RelationLinkedGraphFetcher)
        self.assertIsNone(fetcher3.error)
        self.assertEqual(FAKE_REL_SUB_EMPLOYED_BY, fetcher3._rtype.id)

    def test_clean_ko01(self):
        "type=RGF_NOLINK."
        graph = self._build_graph()

        field = GraphFetcherField(graph=graph)

        value = f'{constants.RGF_NOLINK}|whatever'
        self.assertFieldValidationError(
            GraphFetcherField, 'invalid_choice', field.clean, value,
            message_args={'value': value},
        )

    def test_clean_ko02(self):
        "type=RGF_FK."
        hidden_fname = 'image'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        graph = self._build_graph()
        field = GraphFetcherField(graph=graph)

        # Empty field
        value1 = constants.RGF_FK
        self.assertFieldValidationError(
            GraphFetcherField, 'invalid_choice', field.clean, value1,
            message_args={'value': value1},
        )

        # Unknown field
        value2 = f'{constants.RGF_FK}|invalid'
        self.assertFieldValidationError(
            GraphFetcherField, 'invalid_choice', field.clean, value2,
            message_args={'value': value2},
        )

        # Invalid field (not FK)
        value3 = f'{constants.RGF_FK}|last_name'
        self.assertFieldValidationError(
            GraphFetcherField, 'invalid_choice', field.clean, value3,
            message_args={'value': value3},
        )

        # Invalid field (not FK to CremeEntity)
        value4 = f'{constants.RGF_FK}|sector'
        self.assertFieldValidationError(
            GraphFetcherField, 'invalid_choice', field.clean, value4,
            message_args={'value': value4},
        )

        # Hidden field
        value5 = f'{constants.RGF_FK}|{hidden_fname}'
        self.assertFieldValidationError(
            GraphFetcherField, 'invalid_choice', field.clean, value5,
            message_args={'value': value5},
        )

    def test_clean_ko03(self):
        "type=RGF_RELATIONS."
        graph = self._build_graph()
        field = GraphFetcherField(graph=graph)
        value = f'{constants.RGF_RELATION}|{FAKE_REL_SUB_BILL_ISSUED}'
        self.assertFieldValidationError(
            GraphFetcherField, 'invalid_choice', field.clean, value,
            message_args={'value': value},
        )

    def test_separator01(self):
        field = GraphFetcherField(choice_separator='#')
        self.assertEqual('#', field.choice_separator)

        self.assertEqual('#', field.widget.choices.separator)

        # ---
        field.graph = self._build_graph()
        choices_it = field.widget.choices
        self.assertEqual('#', choices_it.separator)

        fields_group = self.get_choices_group_or_fail(_('Fields'), [*choices_it])
        value = f'{constants.RGF_FK}#image'
        self.assertInChoices(
            value=value,
            label=_('Photograph'),
            choices=fields_group,
        )

        fetcher = field.clean(value=value)
        self.assertIsInstance(fetcher, RegularFieldLinkedGraphFetcher)
        self.assertIsNone(fetcher.error)

        rfield = fetcher._field
        self.assertEqual('image',     rfield.name)
        self.assertEqual(FakeContact, rfield.model)

    def test_separator02(self):
        "Set graph then separator."
        field = GraphFetcherField(graph=self._build_graph())
        field.choice_separator = '#'
        self.assertEqual('#', field.choice_separator)
        self.assertEqual('#', field.widget.choices.separator)


class GraphInstanceBrickFormTestCase(BaseReportsTestCase):
    def test_init_n_clean(self):
        user = self.create_user()
        graph = self._create_documents_rgraph(user)

        form1 = GraphInstanceBrickForm(user=user, graph=graph)

        fetcher_f = form1.fields.get('fetcher')
        self.assertIsInstance(fetcher_f, GraphFetcherField)
        self.assertEqual(graph, fetcher_f.graph)

        fk_name = 'linked_folder'
        form2 = GraphInstanceBrickForm(
            user=user, graph=graph,
            data={'fetcher': f'{constants.RGF_FK}|{fk_name}'},
        )
        self.assertTrue(form2.is_valid())

        ibci = form2.save()
        self.assertIsInstance(ibci, InstanceBrickConfigItem)
        self.assertEqual(graph.id, ibci.entity_id)
        self.assertEqual(constants.RGF_FK, ibci.get_extra_data('type'))
        self.assertEqual(fk_name,          ibci.get_extra_data('value'))

    def test_uniqueness01(self):
        user = self.create_user()
        graph = self._create_documents_rgraph(user)

        fk_name = 'linked_folder'
        RegularFieldLinkedGraphFetcher(
            graph=graph,
            value=fk_name,
        ).create_brick_config_item()

        form1 = GraphInstanceBrickForm(
            user=user, graph=graph,
            data={'fetcher': f'{constants.RGF_FK}|{fk_name}'},
        )
        self.assertFormInstanceErrors(
            form1,
            (
                'fetcher',
                _(
                    'The instance block for «{graph}» with these parameters'
                    ' already exists!'
                ).format(graph=graph),
            ),
        )

        form2 = GraphInstanceBrickForm(
            user=user, graph=graph, data={'fetcher': constants.RGF_NOLINK},
        )
        self.assertTrue(form2.is_valid())

    def test_uniqueness02(self):
        "Not same graph."
        user = self.create_user()
        graph1 = self._create_documents_rgraph(user)
        graph2 = self._create_documents_rgraph(user)

        fk_name = 'linked_folder'
        RegularFieldLinkedGraphFetcher(
            graph=graph2,  # Not same graph => collision
            value=fk_name,
        ).create_brick_config_item()

        form = GraphInstanceBrickForm(
            user=user, graph=graph1,
            data={'fetcher': f'{constants.RGF_FK}|{fk_name}'},
        )
        self.assertTrue(form.is_valid())

    def test_uniqueness03(self):
        "Not same brick class."
        user = self.create_user()
        graph = self._create_documents_rgraph(user)

        class OtherReportGraphBrick(ReportGraphBrick):
            id_ = ReportGraphBrick.generate_id('reports', 'other_graph')

        fk_name = 'linked_folder'
        RegularFieldLinkedGraphFetcher(
            graph=graph, value=fk_name,
        ).create_brick_config_item(
            brick_class=OtherReportGraphBrick,
        )

        form = GraphInstanceBrickForm(
            user=user, graph=graph,
            data={'fetcher': f'{constants.RGF_FK}|{fk_name}'},
        )
        self.assertTrue(form.is_valid())

# TODO: test Report's forms
# TODO: test ReportGraphForm
