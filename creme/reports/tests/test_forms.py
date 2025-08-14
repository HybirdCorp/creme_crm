from functools import partial
from json import dumps as json_dump
from json import loads as json_load

from django.contrib.contenttypes.models import ContentType
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
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_constants import (
    FAKE_REL_SUB_BILL_ISSUED,
    FAKE_REL_SUB_EMPLOYED_BY,
)
from creme.reports import constants
from creme.reports.bricks import ReportChartInstanceBrick
from creme.reports.core.chart import AbscissaInfo, OrdinateInfo
from creme.reports.core.chart.cell_constraint import (
    ACCCount,
    ACCFieldAggregation,
    abscissa_constraints,
    ordinate_constraints,
)
from creme.reports.core.chart.fetcher import (
    RegularFieldLinkedChartFetcher,
    RelationLinkedChartFetcher,
    SimpleChartFetcher,
)
from creme.reports.forms.bricks import (
    ChartFetcherField,
    ChartInstanceBrickForm,
    FetcherChoiceIterator,
)
from creme.reports.forms.chart import AbscissaField, OrdinateField
from creme.reports.forms.report import (
    ReportEntityCellCustomAggregate,
    ReportEntityCellRegularAggregate,
    ReportEntityCellRelated,
    ReportFieldsForm,
    ReportHandsField,
)
from creme.reports.models import (
    FakeReportsDocument,
    FakeReportsFolder,
    Field,
    ReportChart,
)
from creme.reports.report_aggregation_registry import FieldAggregation

from .base import (
    AxisFieldsMixin,
    BaseReportsTestCase,
    Report,
    skipIfCustomReport,
)


class ReportHandsFieldTestCase(CremeTestCase):
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

        agg_id = f'{cf1.uuid}__avg'
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
        field = ReportHandsField(required=True, model=FakeOrganisation)
        code = 'required'
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='')

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
            field.clean(f'regular_field-{fname1}'),
        )

        fname2 = 'unknown'
        self.assertFormfieldError(
            field=field,
            value=f'regular_field-{fname2}',
            messages=_('This value is invalid: %(value)s') % {'value': fname2},
            codes='invalid_value',
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
        self.assertFormfieldError(
            field=field,
            value=f'regular_field-{fname3}',
            messages=_('This value is invalid: %(value)s') % {'value': fname3},
            codes='invalid_value',
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
        self.assertFormfieldError(
            field=field,
            value=f'regular_aggregate-{agg_id2}',
            codes='invalid_value',
            messages=_('This value is invalid: %(value)s') % {'value': agg_id2},
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
        self.assertFormfieldError(
            field=field,
            value='regular_aggregate-capital__avg',
            messages=_('This value is invalid: %(value)s') % {'value': 'capital__avg'},
            codes='invalid_value',
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
        value = f'custom_aggregate-{cf1.uuid}__avg'
        self.assertCellInChoices(
            value,
            label=f"{_('Average')} - {cf1.name}",
            choices=choices,
        )
        self.assertCellInChoices(
            f'custom_aggregate-{cf1.uuid}__min',
            label=f"{_('Minimum')} - {cf1.name}",
            choices=choices,
        )
        self.assertCellInChoices(
            f'custom_aggregate-{cf1.uuid}__max',
            label=f"{_('Maximum')} - {cf1.name}",
            choices=choices,
        )
        self.assertCellInChoices(
            f'custom_aggregate-{cf1.uuid}__sum',
            label=f"{_('Sum')} - {cf1.name}",
            choices=choices,
        )

        self.assertListEqual(
            [ReportEntityCellCustomAggregate.build(FakeOrganisation, f'{cf1.uuid}__avg')],
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
            [*self._find_sub_widget(field, 'custom_aggregate').choices],
        )
        self.assertFormfieldError(
            field=field,
            value=f'custom_aggregate-{cfield.id}__avg',
            codes='invalid_value',
            messages=_('This value is invalid: %(value)s') % {'value': f'{cfield.id}__avg'},
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
            ReportEntityCellCustomAggregate.build(FakeOrganisation, f'{cfield.uuid}__avg'),
        ]

        agg_id = f'custom_aggregate-{cfield.uuid}__avg'
        self.assertListEqual(
            [(agg_id, f"{_('Average')} - {cfield.name}")],
            [
                (choice_id, str(cell))
                for choice_id, cell in self._find_sub_widget(field, 'custom_aggregate').choices
            ],
        )

        self.assertListEqual(
            [ReportEntityCellCustomAggregate.build(FakeOrganisation, f'{cfield.uuid}__avg')],
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
        user = self.get_root_user()
        report = self._create_simple_contacts_report(user=user)

        rtype = self.get_object_or_fail(RelationType, id=REL_SUB_HAS)
        func_name = 'get_pretty_properties'
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            name='Hair',
            field_type=CustomField.ENUM,
        )

        create_rfield = partial(Field.objects.create, report=report)
        create_rfield(type=constants.RFT_RELATION, name=rtype.id,         order=3)
        create_rfield(type=constants.RFT_FUNCTION, name=func_name,        order=3)
        create_rfield(type=constants.RFT_CUSTOM,   name=str(cfield.uuid), order=4)

        form = ReportFieldsForm(user=user, instance=report)

        columns_f = form.fields['columns']
        self.assertIsInstance(columns_f, ReportHandsField)
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
        user = self.get_root_user()
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

        user = self.get_root_user()
        report = Report.objects.create(
            user=user,
            name='Contact report',
            ct=self.ct_contact,
        )

        agg_id = f'{cfield.uuid}__max'
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
        user = self.get_root_user()
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


class AbscissaFieldTestCase(AxisFieldsMixin, CremeTestCase):
    def test_clean_empty_not_required(self):
        with self.assertNoException():
            cleaned = AbscissaField(required=False).clean(None)

        self.assertIsNone(cleaned)

    def test_clean_invalid_json(self):
        self.assertFormfieldError(
            field=AbscissaField(required=False),
            value='{"entity_cell":{"cell_key":',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_invalid_data_type(self):
        field = AbscissaField(required=False)
        msg = _('Invalid type')
        code = 'invalidtype'
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"this is a string"',
        )
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='[]')

    def test_clean_invalid_data(self):
        self.assertFormfieldError(
            field=AbscissaField(required=False),
            value='{"chart_type":"notadict"}',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_rfield_fk(self):
        model = FakeOrganisation
        field_name = 'sector'
        chart_type = ReportChart.Group.FK

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)
        widget = field.widget
        self.assertEqual(model, field.model)
        self.assertEqual(model, widget.model)
        self.assertEqual(abscissa_constraints, field.constraint_registry)
        self.assertEqual(abscissa_constraints, widget.constraint_registry)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=model._meta.get_field(field_name),
            chart_type=chart_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(model, cell.model)
        self.assertEqual(field_name, cell.value)

        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_rfield_date_year(self):
        model = FakeContact
        field_name = 'birthday'
        chart_type = ReportChart.Group.YEAR

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field(field_name),
            chart_type=chart_type,
        ))
        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(model, cell.model)
        self.assertEqual(field_name, cell.value)

        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_rfield_date_month(self):
        field = AbscissaField(model=FakeContact, abscissa_constraints=abscissa_constraints)

        chart_type = ReportChart.Group.MONTH
        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field('birthday'),
            chart_type=chart_type,
        ))
        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_rfield_date_day(self):
        field = AbscissaField(model=FakeContact, abscissa_constraints=abscissa_constraints)

        chart_type = ReportChart.Group.DAY
        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field('birthday'),
            chart_type=chart_type,
        ))
        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_rfield_range(self):
        model = FakeContact
        field_name = 'created'
        chart_type = ReportChart.Group.RANGE
        days = 3

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field(field_name),
            chart_type=chart_type,
            parameter=str(days),
        ))
        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(model, cell.model)
        self.assertEqual(field_name, cell.value)

        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertEqual(days, abs_info.parameter)

    def test_clean_rfield_error01(self):
        "Error on cell."
        model = FakeOrganisation
        field = AbscissaField(
            model=model, abscissa_constraints=abscissa_constraints,
        )
        req_msg = 'The entity cell is required.'
        req_code = 'ecellrequired'
        self.assertFormfieldError(
            field=field, codes=req_code, messages=req_msg,
            value=json_dump({
                # 'entity_cell': {
                #     'cell_key': ...,
                # },
                'chart_type': {'type_id': ReportChart.Group.FK},
                'parameter': '',
            })
        )
        self.assertFormfieldError(
            field=field, codes=req_code, messages=req_msg,
            value=json_dump({
                'entity_cell': {
                    # 'cell_key': ...,
                },
                'chart_type': {'type_id': ReportChart.Group.FK},
                'parameter': '',
            })
        )

        allow_code = 'ecellnotallowed'
        allow_msg = 'This entity cell is not allowed.'
        self.assertFormfieldError(
            field=field, codes=allow_code, messages=allow_msg,
            value=self.formfield_value_abscissa(
                abscissa=model._meta.get_field('name'),  # <= forbidden field
                chart_type=ReportChart.Group.FK,
            ),
        )
        self.assertFormfieldError(
            field=field, codes=allow_code, messages=allow_msg,
            value=json_dump({
                'entity_cell': {
                    'cell_key': 'regular_field-sector__title',  # <= forbidden field
                },
                'chart_type': {
                    'type_id': ReportChart.Group.FK,
                },
                'parameter': '',
            }),
        )
        self.assertFormfieldError(
            field=field, codes=allow_code, messages=allow_msg,
            value=json_dump({
                'entity_cell': {
                    'cell_key': 'regular_field-image__created',  # <= forbidden field
                },
                'chart_type': {
                    'type_id': ReportChart.Group.YEAR,
                },
                'parameter': '',
            }),
        )

    def test_clean_rfield_error02(self):
        "Error on chart type."
        model = FakeOrganisation
        field = AbscissaField(
            model=model, abscissa_constraints=abscissa_constraints,
        )
        req_code = 'charttyperequired'
        req_msg = 'The chart type is required.'
        self.assertFormfieldError(
            field=field, codes=req_code, messages=req_msg,
            value=json_dump({
                'entity_cell': {'cell_key': 'regular_field-sector'},
                # 'chart_type': {
                #     'type_id': ...,
                # },
                'parameter': '',
            }),
        )
        self.assertFormfieldError(
            field=field, codes=req_code, messages=req_msg,
            value=json_dump({
                'entity_cell': {'cell_key': 'regular_field-sector'},
                'chart_type': {
                    # 'type_id': ...,
                },
                'parameter': '',
            })
        )

        sector_field = model._meta.get_field('sector')
        allow_code = 'ecellnotallowed'
        allow_msg = 'This entity cell is not allowed.'
        self.assertFormfieldError(
            field=field, codes=allow_code, messages=allow_msg,
            value=self.formfield_value_abscissa(
                abscissa=sector_field,
                chart_type=ReportChart.Group.YEAR,  # <===
            ),
        )
        self.assertFormfieldError(
            field=field, codes=allow_code, messages=allow_msg,
            value=self.formfield_value_abscissa(
                abscissa=sector_field,
                chart_type=ReportChart.Group.MONTH,  # <===
            ),
        )
        self.assertFormfieldError(
            field=field, codes=allow_code, messages=allow_msg,
            value=self.formfield_value_abscissa(
                abscissa=sector_field,
                chart_type=ReportChart.Group.DAY,  # <===
            ),
        )

    def test_clean_rfield_error03(self):
        "Error on extra parameter."
        model = FakeContact
        field = AbscissaField(
            model=model, abscissa_constraints=abscissa_constraints,
        )

        abscissa = model._meta.get_field('created')
        chart_type = ReportChart.Group.RANGE

        self.assertFormfieldError(
            field=field,
            value=self.formfield_value_abscissa(
                abscissa=abscissa,
                chart_type=chart_type,
                # parameter='2',
            ),
            messages=_('The parameter is invalid. {}').format(_('This field is required.')),
            codes='invalidparameter',
        )

        # ---
        self.assertFormfieldError(
            field=field,
            value=self.formfield_value_abscissa(
                abscissa=abscissa,
                chart_type=chart_type,
                parameter='notanint',
            ),
            messages=_('The parameter is invalid. {}').format(_('Enter a whole number.')),
            codes='invalidparameter',
        )

    def test_clean_rfield_fields_config(self):
        model = FakeOrganisation
        field_name = 'sector'
        chart_type = ReportChart.Group.FK

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
        self.assertFormfieldError(
            field=field,
            value=self.formfield_value_abscissa(
                abscissa=sector_field,
                chart_type=chart_type,
            ),
            messages='This entity cell is not allowed.',
            codes='ecellnotallowed',
        )

        # ---
        cell = EntityCellRegularField.build(model, field_name)
        init_abs_info = AbscissaInfo(cell=cell, chart_type=chart_type)
        field.initial = init_abs_info
        self.assertEqual(init_abs_info, field.initial)
        self.assertSetEqual({cell.key}, field.not_hiddable_cell_keys)
        self.assertSetEqual({cell.key}, field.widget.not_hiddable_cell_keys)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=model._meta.get_field(field_name),
            chart_type=chart_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

    def test_clean_rtype(self):
        model = FakeOrganisation
        chart_type = ReportChart.Group.RELATION
        rtype = RelationType.objects.compatible(model)[0]

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=rtype, chart_type=chart_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(model, cell.model)
        self.assertEqual(rtype.id, cell.value)

        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_rtype_error(self):
        model = FakeOrganisation
        rtype = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is loving', models=[FakeContact],
        ).symmetric(
            id='test-object_foobar',  predicate='is loved by', models=[FakeContact],
        ).get_or_create()[0]

        field = AbscissaField(
            model=model, abscissa_constraints=abscissa_constraints,
        )
        self.assertFormfieldError(
            field=field,
            value=self.formfield_value_abscissa(
                abscissa=rtype,
                chart_type=ReportChart.Group.RELATION,
            ),
            messages='This entity cell is not allowed.',
            codes='ecellnotallowed',
        )

    def test_clean_cfield_enum01(self):
        model = FakeContact
        chart_type = ReportChart.Group.CUSTOM_FK
        cfield = CustomField.objects.create(
            content_type=model,
            name='Hair',
            field_type=CustomField.ENUM,
        )

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield, chart_type=chart_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(model, cell.model)
        self.assertEqual(str(cfield.id), cell.value)

        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_cfield_enum02(self):
        "Field is deleted."
        model = FakeContact
        chart_type = ReportChart.Group.CUSTOM_FK
        cfield = CustomField.objects.create(
            content_type=model,
            name='Hair',
            field_type=CustomField.ENUM,
            is_deleted=True,
        )

        field = AbscissaField(
            model=model, abscissa_constraints=abscissa_constraints,
        )
        self.assertFormfieldError(
            field=field,
            value=self.formfield_value_abscissa(abscissa=cfield, chart_type=chart_type),
            messages='This entity cell is not allowed.',
            codes='ecellnotallowed',
        )

        # ---
        cell = EntityCellCustomField(cfield)
        init_abs_info = AbscissaInfo(cell=cell, chart_type=chart_type)
        field.initial = init_abs_info
        self.assertSetEqual({cell.key}, field.not_hiddable_cell_keys)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield, chart_type=chart_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

    @parameterized.expand([CustomField.DATETIME, CustomField.DATE])
    def test_clean_cfield_date_year(self, cfield_type):
        model = FakeContact
        chart_type = ReportChart.Group.CUSTOM_YEAR
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=cfield_type,
        )

        field = AbscissaField(
            model=model, abscissa_constraints=abscissa_constraints,
        )

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield, chart_type=chart_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(model, cell.model)
        self.assertEqual(str(cfield.id), cell.value)

        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    @parameterized.expand([CustomField.DATETIME, CustomField.DATE])
    def test_clean_cfield_date_month(self, cfield_type):
        model = FakeContact
        chart_type = ReportChart.Group.CUSTOM_MONTH
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=cfield_type,
        )

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield, chart_type=chart_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(model, cell.model)
        self.assertEqual(str(cfield.id), cell.value)

        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    @parameterized.expand([CustomField.DATETIME, CustomField.DATE])
    def test_clean_cfield_date_day(self, cfield_type):
        model = FakeContact
        chart_type = ReportChart.Group.CUSTOM_DAY
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=cfield_type,
        )

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield, chart_type=chart_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(model, cell.model)
        self.assertEqual(str(cfield.id), cell.value)

        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_cfield_range(self):
        model = FakeContact
        chart_type = ReportChart.Group.CUSTOM_RANGE
        days = 5
        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=CustomField.DATETIME,
        )
        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)
        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=cfield,
            chart_type=chart_type,
            parameter=str(days),
        ))

        cell = abs_info.cell
        self.assertEqual(model, cell.model)
        self.assertEqual(str(cfield.id), cell.value)

        self.assertEqual(chart_type, abs_info.chart_type)
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
        msg = 'This entity cell is not allowed.'
        code = 'ecellnotallowed'
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=self.formfield_value_abscissa(
                abscissa=cfield1,
                chart_type=ReportChart.Group.CUSTOM_FK,
            ),
        )

        # ---
        cfield2 = CustomField.objects.create(
            content_type=FakeContact,  # <== wrong model
            name='Size',
            field_type=CustomField.ENUM,
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=self.formfield_value_abscissa(
                abscissa=cfield2,
                chart_type=ReportChart.Group.CUSTOM_FK,
            ),
        )

    def test_clean_cfield_error02(self):
        "Error on chart type."
        model = FakeOrganisation
        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

        cfield_enum = CustomField.objects.create(
            content_type=model,
            name='Type',
            field_type=CustomField.ENUM,
        )
        msg = 'This entity cell is not allowed.'
        code = 'ecellnotallowed'
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=self.formfield_value_abscissa(
                abscissa=cfield_enum,
                chart_type=ReportChart.Group.CUSTOM_YEAR,
            ),
        )
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=self.formfield_value_abscissa(
                abscissa=cfield_enum,
                chart_type=ReportChart.Group.CUSTOM_MONTH,
            ),
        )
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=self.formfield_value_abscissa(
                abscissa=cfield_enum,
                chart_type=ReportChart.Group.CUSTOM_DAY,
            ),
        )
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=self.formfield_value_abscissa(
                abscissa=cfield_enum,
                chart_type=ReportChart.Group.CUSTOM_RANGE,
                parameter='7',
            ),
        )

        cfield_dt = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=CustomField.DATETIME,
        )
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=self.formfield_value_abscissa(
                abscissa=cfield_dt,
                chart_type=ReportChart.Group.CUSTOM_FK,
            ),
        )

    def test_clean_cfield_error03(self):
        "Error on extra parameter."
        model = FakeContact
        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)
        chart_type = ReportChart.Group.CUSTOM_RANGE

        cfield = CustomField.objects.create(
            content_type=model,
            name='First fight',
            field_type=CustomField.DATETIME,
        )

        self.assertFormfieldError(
            field=field,
            value=self.formfield_value_abscissa(
                abscissa=cfield,
                chart_type=chart_type,
                # parameter='2',
            ),
            messages=_('The parameter is invalid. {}').format(_('This field is required.')),
            codes='invalidparameter',
        )
        self.assertFormfieldError(
            field=field,
            value=self.formfield_value_abscissa(
                abscissa=cfield,
                chart_type=chart_type,
                parameter='notanint',
            ),
            messages=_('The parameter is invalid. {}').format(_('Enter a whole number.')),
            codes='invalidparameter',
        )

    def test_clean_error01(self):
        "Error on cell."
        model = FakeOrganisation
        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)
        cell = EntityCellFunctionField.build(FakeContact, 'get_pretty_properties')
        msg = 'This entity cell is not allowed.'
        code = 'ecellnotallowed'
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=json_dump({
                'entity_cell': {'cell_key': cell.key},
                'chart_type': {'type_id': ReportChart.Group.FK},
                'parameter': '',
            }),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=json_dump({
                'entity_cell': {'cell_key': cell.key.replace('-', '')},
                'chart_type': {'type_id': ReportChart.Group.FK},
                'parameter': '',
            }),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=json_dump({
                'entity_cell': {'cell_key': 'regular_field-INVALID'},
                'chart_type': {'type_id': ReportChart.Group.FK},
                'parameter': '',
            }),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=json_dump({
                'entity_cell': {'cell_key': 'INVALID-stuff'},
                'chart_type': {'type_id': ReportChart.Group.FK},
                'parameter': '',
            }),
        )

    def test_clean_error02(self):
        "Error on chart type."
        model = FakeContact
        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)
        cell = EntityCellRegularField.build(FakeContact, 'position')
        self.assertFormfieldError(
            field=field,
            value=json_dump({
                'entity_cell': {'cell_key': cell.key},
                'chart_type': {
                    'type_id': 1024,  # <==
                },
                'parameter': '',
            }),
            codes='charttypenotallowed',
            messages='The chart type is not allowed.',
        )

    def test_clean_error03(self):
        "Error on parameter."
        model = FakeContact
        field_name = 'birthday'
        chart_type = ReportChart.Group.YEAR

        field = AbscissaField(model=model, abscissa_constraints=abscissa_constraints)

        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field(field_name),
            chart_type=chart_type,
            parameter='6',  # <== should be ignored
        ))
        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(model, cell.model)
        self.assertEqual(field_name, cell.value)

        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_not_required(self):
        model = FakeOrganisation
        field = AbscissaField(
            model=model,
            abscissa_constraints=abscissa_constraints,
            required=False,
        )
        self.assertIsNone(field.clean(self.formfield_value_abscissa(
            abscissa=None, chart_type='',
        )))
        self.assertIsNone(field.clean(self.formfield_value_abscissa(
            abscissa=model._meta.get_field('sector'),
            chart_type='',
        )))

    def test_clean_no_model01(self):
        "Regular field."
        field = AbscissaField(abscissa_constraints=abscissa_constraints)
        self.assertIs(field.model, CremeEntity)

        field_name = 'created'
        chart_type = ReportChart.Group.YEAR
        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=CremeEntity._meta.get_field(field_name),
            chart_type=chart_type,
        ))
        self.assertIsInstance(abs_info, AbscissaInfo)

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(CremeEntity, cell.model)
        self.assertEqual(field_name, cell.value)

        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean_no_model02(self):
        "Relation."
        field = AbscissaField(abscissa_constraints=abscissa_constraints)

        rtype = RelationType.objects.builder(
            id='test-subject_likes', predicate='likes',
        ).symmetric(id='test-object_likes',  predicate='is liked by').get_or_create()[0]

        chart_type = ReportChart.Group.RELATION
        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=rtype, chart_type=chart_type,
        ))

        cell = abs_info.cell
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(CremeEntity, cell.model)
        self.assertEqual(rtype.id, cell.value)

        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    def test_from_python_rfield_fk(self):
        field = AbscissaField(
            model=FakeOrganisation, abscissa_constraints=abscissa_constraints,
        )
        cell = EntityCellRegularField.build(FakeOrganisation, 'sector')
        chart_type = ReportChart.Group.FK
        self.assertEqual(
            {
                'entity_cell': {
                    'cell_key': cell.key,
                    'grouping_category': 'regular_fk',
                },
                'chart_type': {
                    'type_id': chart_type,
                    'grouping_category': 'regular_fk',
                },
                'parameter': '',
            },
            json_load(field.from_python(
                AbscissaInfo(cell=cell, chart_type=chart_type)
            )),
        )

    def test_from_python_rfield_date(self):
        from_python = AbscissaField(
            model=FakeOrganisation,
            abscissa_constraints=abscissa_constraints,
        ).from_python
        cell = EntityCellRegularField.build(FakeOrganisation, 'creation_date')

        chart_type1 = ReportChart.Group.YEAR
        self.assertDictEqual(
            {
                'entity_cell': {
                    'cell_key': cell.key,
                    'grouping_category': 'regular_date',
                },
                'chart_type': {
                    'type_id': chart_type1,
                    'grouping_category': 'regular_date',
                },
                'parameter': '',
            },
            json_load(from_python(AbscissaInfo(cell=cell, chart_type=chart_type1))),
        )

        chart_type2 = ReportChart.Group.RANGE
        parameter = '5'
        self.assertDictEqual(
            {
                'entity_cell': {
                    'cell_key': cell.key,
                    'grouping_category': 'regular_date',
                },
                'chart_type': {
                    'type_id': chart_type2,
                    'grouping_category': 'regular_date',
                },
                'parameter': parameter,
            },
            json_load(from_python(AbscissaInfo(
                cell=cell, chart_type=chart_type2, parameter=parameter,
            ))),
        )

    def test_from_python_relation(self):
        field = AbscissaField(
            model=FakeOrganisation, abscissa_constraints=abscissa_constraints,
        )
        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        cell = EntityCellRelation(model=FakeOrganisation, rtype=rtype)
        chart_type = ReportChart.Group.RELATION
        self.assertDictEqual(
            {
                'entity_cell': {
                    'cell_key': cell.key,
                    'grouping_category': 'rtype',
                },
                'chart_type': {
                    'type_id': chart_type,
                    'grouping_category': 'rtype',
                },
                'parameter': '',
            },
            json_load(field.from_python(
                AbscissaInfo(cell=cell, chart_type=chart_type)
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
        chart_type = ReportChart.Group.CUSTOM_FK
        self.assertEqual(
            {
                'entity_cell': {
                    'cell_key': cell.key,
                    'grouping_category': 'custom_enum',
                },
                'chart_type': {
                    'type_id': chart_type,
                    'grouping_category': 'custom_enum',
                },
                'parameter': '',
            },
            json_load(field.from_python(
                AbscissaInfo(cell=cell, chart_type=chart_type)
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
        chart_type = ReportChart.Group.CUSTOM_DAY
        self.assertDictEqual(
            {
                'entity_cell': {
                    'cell_key': cell.key,
                    'grouping_category': 'custom_date',
                },
                'chart_type': {
                    'type_id': chart_type,
                    'grouping_category': 'custom_date',
                },
                'parameter': '',
            },
            json_load(field.from_python(
                AbscissaInfo(cell=cell, chart_type=chart_type))
            ),
        )


class OrdinateFieldTestCase(AxisFieldsMixin, CremeTestCase):
    def test_clean_empty_not_required(self):
        with self.assertNoException():
            cleaned = OrdinateField(required=False).clean(None)

        self.assertIsNone(cleaned)

    def test_clean_invalid_json(self):
        self.assertFormfieldError(
            field=OrdinateField(required=False),
            value='{"entity_cell":{"cell_key":',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_invalid_data_type(self):
        field = OrdinateField(required=False)
        code = 'invalidtype'
        msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"this is a string"'
        )
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='[]')

    def test_clean_invalid_data(self):
        self.assertFormfieldError(
            field=OrdinateField(required=False),
            value='{"aggregator":"notadict"}',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_count(self):
        model = FakeOrganisation
        aggr_id = ReportChart.Aggregator.COUNT

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
        aggr_id = ReportChart.Aggregator.SUM

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
        aggr_id = ReportChart.Aggregator.AVG

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
        req_msg = 'The aggregation id is required.'
        self.assertFormfieldError(
            field=field, codes='aggridrequired', messages=req_msg,
            value=json_dump({
                # 'aggregator': {
                #     'aggr_id': ...,
                # },
                'entity_cell': {'cell_key': 'regular_field-capital'},
            }),
        )
        self.assertFormfieldError(
            field=field, codes='aggridrequired', messages=req_msg,
            value=json_dump({
                'aggregator': {
                    # 'type_id': ...,
                },
                'entity_cell': {'cell_key': 'regular_field-capital'},
            }),
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump({
                'aggregator': {
                    'aggr_id': 'invalid',
                },
                'entity_cell': {
                    'cell_key': 'regular_field-capital',
                },
            }),
            codes='aggridinvalid', messages='The aggregation id is invalid.',
        )

    def test_clean_rfield_error02(self):
        "Error on cell."
        model = FakeInvoiceLine
        field = OrdinateField(
            model=model, ordinate_constraints=ordinate_constraints,
        )
        req_code = 'ecellrequired'
        req_msg = 'The entity cell is required.'
        self.assertFormfieldError(
            field=field, codes=req_code, messages=req_msg,
            value=json_dump({
                'aggregator': {
                    # 'aggr_id': constants.RGA_MIN,
                    'aggr_id': ReportChart.Aggregator.MIN,
                },
                # 'entity_cell': {
                #     'cell_key': ...,
                # },
            }),
        )
        self.assertFormfieldError(
            field=field, codes=req_code, messages=req_msg,
            value=json_dump({
                'aggregator': {'aggr_id': ReportChart.Aggregator.MIN},
                'entity_cell': {
                    # 'cell_key': ...,
                },
            }),
        )
        self.assertFormfieldError(
            field=field, codes=req_code, messages=req_msg,
            value=self.formfield_value_ordinate(
                aggr_id=ReportChart.Aggregator.MIN,
                # cell=...
            ),
        )

        allow_code = 'ecellnotallowed'
        allow_msg = 'This entity cell is not allowed.'
        self.assertFormfieldError(
            field=field, codes=allow_code, messages=allow_msg,
            value=self.formfield_value_ordinate(
                aggr_id=ReportChart.Aggregator.SUM,
                # forbidden field:
                cell=EntityCellRegularField.build(model, 'item'),
            ),
        )
        self.assertFormfieldError(
            field=field, codes=allow_code, messages=allow_msg,
            value=self.formfield_value_ordinate(
                aggr_id=ReportChart.Aggregator.SUM,
                # field too deep:
                cell=EntityCellRegularField.build(model, 'linked_invoice__total_vat'),
            ),
        )

        # TODO: not viewable

    def test_clean_rfield_fields_config(self):
        model = FakeOrganisation
        field_name = 'capital'
        aggr_id1 = ReportChart.Aggregator.SUM

        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[(field_name, {FieldsConfig.HIDDEN: True})],
        )

        field = OrdinateField(model=model, ordinate_constraints=ordinate_constraints)

        self.assertIsNone(field.initial)
        self.assertSetEqual(set(), field.not_hiddable_cell_keys)
        self.assertSetEqual(set(), field.widget.not_hiddable_cell_keys)

        cell = EntityCellRegularField.build(model, field_name)
        self.assertFormfieldError(
            field=field,
            value=self.formfield_value_ordinate(aggr_id=aggr_id1, cell=cell),
            codes='ecellnotallowed',
            messages='This entity cell is not allowed.',
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
        aggr_id2 = ReportChart.Aggregator.COUNT
        init_ord_info2 = OrdinateInfo(aggr_id=aggr_id2)
        field.initial = init_ord_info2
        self.assertEqual(init_ord_info2, field.initial)
        self.assertSetEqual(set(), field.not_hiddable_cell_keys)
        self.assertSetEqual(set(), field.widget.not_hiddable_cell_keys)

    def test_clean_cfield_int(self):
        model = FakeContact
        aggr_id = ReportChart.Aggregator.MAX
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
        self.assertFormfieldError(
            field=field,
            value=self.formfield_value_ordinate(
                aggr_id=ReportChart.Aggregator.SUM,
                cell=EntityCellCustomField(cfield_str),
            ),
            codes='ecellnotallowed',
            messages='This entity cell is not allowed.',
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
        code = 'ecellnotallowed'
        msg = 'This entity cell is not allowed.'
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=self.formfield_value_ordinate(
                aggr_id=ReportChart.Aggregator.SUM,
                cell=EntityCellCustomField(cfield),
            ),
        )
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=self.formfield_value_ordinate(
                aggr_id=ReportChart.Aggregator.COUNT,
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
        code = 'ecellnotallowed'
        msg = 'This entity cell is not allowed.'
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=self.formfield_value_ordinate(
                aggr_id=ReportChart.Aggregator.SUM,
                cell=EntityCellCustomField(cfield),
            ),
        )
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=self.formfield_value_ordinate(
                aggr_id=ReportChart.Aggregator.COUNT,
                cell=EntityCellRegularField.build(FakeOrganisation, 'capital'),
            ),
        )

    def test_clean_error(self):
        "Error on cell."
        model = FakeOrganisation
        field = OrdinateField(model=model, ordinate_constraints=ordinate_constraints)
        code = 'ecellnotallowed'
        msg = 'This entity cell is not allowed.'
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=self.formfield_value_ordinate(
                aggr_id=ReportChart.Aggregator.SUM,
                cell=EntityCellFunctionField.build(FakeContact, 'get_pretty_properties'),
            ),
        )
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=json_dump({
                'aggregator': {
                    'aggr_id': ReportChart.Aggregator.SUM,
                    'aggr_category': 'not used',
                },
                'entity_cell': {
                    'cell_key': 'not_hyphened_str',
                    'aggr_category': 'not used',
                },
            }),
        )
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=json_dump({
                'aggregator': {
                    'aggr_id': ReportChart.Aggregator.SUM,
                    'aggr_category': 'not used',
                },
                'entity_cell': {
                    'cell_key': 'regular_field-INVALID',
                    'aggr_category': 'not used',
                },
            }),
        )
        self.assertFormfieldError(
            field=field, codes=code, messages=msg,
            value=json_dump({
                'aggregator': {
                    'aggr_id': 'sum',
                    'aggr_category': 'not used',
                },
                'entity_cell': {
                    'cell_key': 'INVALID-stuff',
                    'aggr_category': 'not used',
                },
            }),
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
        aggr_id = ReportChart.Aggregator.COUNT
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
        aggr_id = ReportChart.Aggregator.AVG
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
        aggr_id = ReportChart.Aggregator.SUM
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


class ChartFetcherFieldTestCase(CremeTestCase):
    def _build_chart(self):
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)

        return ReportChart(name='Field Test', linked_report=report)

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            cleaned = ChartFetcherField(required=False).clean(None)

        self.assertIsNone(cleaned)

    def test_clean_empty_required(self):
        field = ChartFetcherField()
        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field, value=None,
            codes='required', messages=_('This field is required.'),
        )

    def test_chart_n_iterator01(self):
        chart = self._build_chart()

        field = ChartFetcherField()
        self.assertIsNone(field.chart)
        self.assertEqual('|', field.choice_separator)

        choices_it1 = field.widget.choices
        self.assertIsInstance(choices_it1, FetcherChoiceIterator)
        self.assertIsNone(choices_it1.chart)
        self.assertEqual('|', choices_it1.separator)
        self.assertFalse([*choices_it1])

        # ---
        field.chart = chart
        self.assertEqual(chart, field.chart)

        choices_it2 = field.widget.choices
        self.assertEqual(chart, choices_it2.chart)

        choices = [*choices_it2]
        self.assertInChoices(
            # value=f'{constants.RGF_NOLINK}|',
            value=f'{SimpleChartFetcher.type_id}|',
            label=pgettext('reports-volatile_choice', 'None'),
            choices=choices,
        )

        fields_group = self.get_choices_group_or_fail(_('Fields'), choices)
        self.assertInChoices(
            # value=f'{constants.RGF_FK}|image',
            value=f'{RegularFieldLinkedChartFetcher.type_id}|image',
            label=_('Photograph'),
            choices=fields_group,
        )
        # self.assertNotInChoices(f'{constants.RGF_FK}|is_user', fields_group)
        self.assertNotInChoices(
            f'{RegularFieldLinkedChartFetcher.type_id}|is_user', fields_group,
        )

        relations_group = self.get_choices_group_or_fail(_('Relationships'), choices)
        self.assertInChoices(
            # value=f'{constants.RGF_RELATION}|{FAKE_REL_SUB_EMPLOYED_BY}',
            value=f'{RelationLinkedChartFetcher.type_id}|{FAKE_REL_SUB_EMPLOYED_BY}',
            label='is an employee of — employs',
            choices=relations_group,
        )
        self.assertNotInChoices(
            # f'{constants.RGF_RELATION}|{FAKE_REL_SUB_BILL_ISSUED}',
            f'{RelationLinkedChartFetcher.type_id}|{FAKE_REL_SUB_BILL_ISSUED}',
            relations_group,
        )

    def test_chart_n_iterator02(self):
        "Hidden field."
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('image', {FieldsConfig.HIDDEN: True})],
        )

        chart = self._build_chart()

        field = ChartFetcherField(chart=chart)
        choices = [*field.widget.choices]
        self.get_choices_group_or_fail(_('Relationships'), choices)

        empty_group_name = _('Fields')
        for choice in choices:
            if choice[0] == empty_group_name:
                self.fail(f'Group "{empty_group_name}" unexpectedly found.')

    def test_clean_ok(self):
        chart = self._build_chart()

        field = ChartFetcherField(chart=chart)
        self.assertEqual(chart, field.chart)

        # No Link ---
        # fetcher1a = field.clean(value=constants.RGF_NOLINK)
        fetcher1a = field.clean(value=SimpleChartFetcher.type_id)
        self.assertIsInstance(fetcher1a, SimpleChartFetcher)
        self.assertIsNone(fetcher1a.error)

        # fetcher1b = field.clean(value=f'{constants.RGF_NOLINK}|')
        fetcher1b = field.clean(value=f'{SimpleChartFetcher.type_id}|')
        self.assertIsInstance(fetcher1b, SimpleChartFetcher)
        self.assertIsNone(fetcher1b.error)

        # FK link ---
        # fetcher2 = field.clean(value=f'{constants.RGF_FK}|image')
        fetcher2 = field.clean(value=f'{RegularFieldLinkedChartFetcher.type_id}|image')
        self.assertIsInstance(fetcher2, RegularFieldLinkedChartFetcher)
        self.assertIsNone(fetcher2.error)
        rfield = fetcher2._field
        self.assertEqual('image',     rfield.name)
        self.assertEqual(FakeContact, rfield.model)

        # Relation link ---
        fetcher3 = field.clean(
            # value=f'{constants.RGF_RELATION}|{FAKE_REL_SUB_EMPLOYED_BY}',
            value=f'{RelationLinkedChartFetcher.type_id}|{FAKE_REL_SUB_EMPLOYED_BY}',
        )
        self.assertIsInstance(fetcher3, RelationLinkedChartFetcher)
        self.assertIsNone(fetcher3.error)
        self.assertEqual(FAKE_REL_SUB_EMPLOYED_BY, fetcher3._rtype.id)

    def test_clean_error__no_link(self):
        chart = self._build_chart()
        field = ChartFetcherField(chart=chart)
        # value = f'{constants.RGF_NOLINK}|whatever'
        value = f'{SimpleChartFetcher.type_id}|whatever'
        self.assertFormfieldError(
            field=field, value=value, codes='invalid_choice',
            messages=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': value},
        )

    def test_clean_error__fk(self):
        hidden_fname = 'image'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        chart = self._build_chart()
        field = ChartFetcherField(chart=chart)

        # Empty field
        code = 'invalid_choice'
        msg = _(
            'Select a valid choice. %(value)s is not one of the available choices.'
        )
        # value1 = constants.RGF_FK
        value1 = RegularFieldLinkedChartFetcher.type_id
        self.assertFormfieldError(
            field=field, value=value1,
            messages=msg % {'value': value1},
            codes=code,
        )

        # Unknown field
        # value2 = f'{constants.RGF_FK}|invalid'
        value2 = f'{RegularFieldLinkedChartFetcher.type_id}|invalid'
        self.assertFormfieldError(
            field=field, value=value2,
            messages=msg % {'value': value2},
            codes=code,
        )

        # Invalid field (not FK)
        # value3 = f'{constants.RGF_FK}|last_name'
        value3 = f'{RegularFieldLinkedChartFetcher.type_id}|last_name'
        self.assertFormfieldError(
            field=field, value=value3,
            messages=msg % {'value': value3},
            codes=code,
        )

        # Invalid field (not FK to CremeEntity)
        # value4 = f'{constants.RGF_FK}|sector'
        value4 = f'{RegularFieldLinkedChartFetcher.type_id}|sector'
        self.assertFormfieldError(
            field=field, value=value4,
            messages=msg % {'value': value4}, codes=code,
        )

        # Hidden field
        # value5 = f'{constants.RGF_FK}|{hidden_fname}'
        value5 = f'{RegularFieldLinkedChartFetcher.type_id}|{hidden_fname}'
        self.assertFormfieldError(
            field=field, value=value5,
            messages=msg % {'value': value5}, codes=code,
        )

    def test_clean_error__relation(self):
        chart = self._build_chart()
        # value = f'{constants.RGF_RELATION}|{FAKE_REL_SUB_BILL_ISSUED}'
        value = f'{RelationLinkedChartFetcher.type_id}|{FAKE_REL_SUB_BILL_ISSUED}'
        self.assertFormfieldError(
            field=ChartFetcherField(chart=chart),
            value=value,
            codes='invalid_choice',
            messages=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': value},
        )

    def test_separator01(self):
        field = ChartFetcherField(choice_separator='#')
        self.assertEqual('#', field.choice_separator)

        self.assertEqual('#', field.widget.choices.separator)

        # ---
        field.chart = self._build_chart()
        choices_it = field.widget.choices
        self.assertEqual('#', choices_it.separator)

        fields_group = self.get_choices_group_or_fail(_('Fields'), [*choices_it])
        # value = f'{constants.RGF_FK}#image'
        value = f'{RegularFieldLinkedChartFetcher.type_id}#image'
        self.assertInChoices(
            value=value,
            label=_('Photograph'),
            choices=fields_group,
        )

        fetcher = field.clean(value=value)
        self.assertIsInstance(fetcher, RegularFieldLinkedChartFetcher)
        self.assertIsNone(fetcher.error)

        rfield = fetcher._field
        self.assertEqual('image',     rfield.name)
        self.assertEqual(FakeContact, rfield.model)

    def test_separator02(self):
        "Set chart then separator."
        field = ChartFetcherField(chart=self._build_chart())
        field.choice_separator = '#'
        self.assertEqual('#', field.choice_separator)
        self.assertEqual('#', field.widget.choices.separator)


class ChartInstanceBrickFormTestCase(BaseReportsTestCase):
    def test_init_n_clean(self):
        user = self.get_root_user()
        chart = self._create_documents_chart(user)

        form1 = ChartInstanceBrickForm(user=user, chart=chart)

        fetcher_f = form1.fields.get('fetcher')
        self.assertIsInstance(fetcher_f, ChartFetcherField)
        self.assertEqual(chart, fetcher_f.chart)

        fk_name = 'linked_folder'
        form2 = ChartInstanceBrickForm(
            user=user, chart=chart,
            # data={'fetcher': f'{constants.RGF_FK}|{fk_name}'},
            data={'fetcher': f'{RegularFieldLinkedChartFetcher.type_id}|{fk_name}'},
        )
        self.assertTrue(form2.is_valid())

        ibci = form2.save()
        self.assertIsInstance(ibci, InstanceBrickConfigItem)
        self.assertEqual(chart.linked_report_id, ibci.entity_id)
        # self.assertEqual(constants.RGF_FK, ibci.get_extra_data('type'))
        self.assertEqual(RegularFieldLinkedChartFetcher.type_id, ibci.get_extra_data('type'))
        self.assertEqual(fk_name, ibci.get_extra_data('value'))
        self.assertUUIDEqual(chart.uuid, ibci.get_extra_data('chart'))

    def test_uniqueness01(self):
        user = self.get_root_user()
        chart = self._create_documents_chart(user)

        fk_name = 'linked_folder'
        RegularFieldLinkedChartFetcher(
            chart=chart, value=fk_name,
        ).create_brick_config_item(
            brick_class=ReportChartInstanceBrick,
        )

        form1 = ChartInstanceBrickForm(
            user=user, chart=chart,
            # data={'fetcher': f'{constants.RGF_FK}|{fk_name}'},
            data={'fetcher': f'{RegularFieldLinkedChartFetcher.type_id}|{fk_name}'},
        )
        self.assertFormInstanceErrors(
            form1,
            (
                'fetcher',
                _(
                    'The instance block for «{chart}» with these parameters'
                    ' already exists!'
                ).format(chart=chart),
            ),
        )

        form2 = ChartInstanceBrickForm(
            # user=user, chart=chart, data={'fetcher': constants.RGF_NOLINK},
            user=user, chart=chart, data={'fetcher': SimpleChartFetcher.type_id},
        )
        self.assertTrue(form2.is_valid())

    def test_uniqueness02(self):
        "Not same chart."
        user = self.get_root_user()
        chart1 = self._create_documents_chart(user)
        chart2 = self._create_documents_chart(user)

        fk_name = 'linked_folder'
        RegularFieldLinkedChartFetcher(
            chart=chart2,  # Not same chart => collision
            value=fk_name,
        ).create_brick_config_item(
            brick_class=ReportChartInstanceBrick
        )

        form = ChartInstanceBrickForm(
            user=user, chart=chart1,
            # data={'fetcher': f'{constants.RGF_FK}|{fk_name}'},
            data={'fetcher': f'{RegularFieldLinkedChartFetcher.type_id}|{fk_name}'},
        )
        self.assertTrue(form.is_valid())

    def test_uniqueness03(self):
        "Not same brick class."
        user = self.get_root_user()
        chart = self._create_documents_chart(user)

        class OtherReportChartBrick(ReportChartInstanceBrick):
            id = ReportChartInstanceBrick.generate_id('reports', 'other_chart')

        fk_name = 'linked_folder'
        RegularFieldLinkedChartFetcher(
            chart=chart, value=fk_name,
        ).create_brick_config_item(
            brick_class=OtherReportChartBrick,
        )

        form = ChartInstanceBrickForm(
            user=user, chart=chart,
            # data={'fetcher': f'{constants.RGF_FK}|{fk_name}'},
            data={'fetcher': f'{RegularFieldLinkedChartFetcher.type_id}|{fk_name}'},
        )
        self.assertTrue(form.is_valid())

# TODO: test Report's forms
# TODO: test ReportChartForm
