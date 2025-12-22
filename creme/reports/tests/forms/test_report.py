from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.models import (
    CustomField,
    FakeContact,
    FakeOrganisation,
    FieldsConfig,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.reports import constants
from creme.reports.forms.report import (
    ReportEntityCellCustomAggregate,
    ReportEntityCellRegularAggregate,
    ReportEntityCellRelated,
    ReportFieldsForm,
    ReportHandsField,
)
from creme.reports.models import FakeReportsDocument, FakeReportsFolder, Field
from creme.reports.report_aggregation_registry import FieldAggregation
from creme.reports.tests.base import (
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

    def test_entity_cell__related(self):
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

    def test_entity_cell__regular_aggregate(self):
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

    def test_entity_cell__custom_aggregate(self):
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

    def test_clean__empty__required(self):
        field = ReportHandsField(required=True, model=FakeOrganisation)
        code = 'required'
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='')

    def test_clean__empty__not_required(self):
        field = ReportHandsField(required=False, model=FakeOrganisation)

        with self.assertNoException():
            value = field.clean(None)

        self.assertListEqual([], value)

    def test_regular_fields(self):
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

    def test_regular_fields__no_fk_to_entity(self):
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

    def test_regular_aggregates(self):
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

    def test_regular_aggregates__hidden__not_used(self):
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

    def test_regular_aggregates__hidden__used(self):
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

    def test_custom_aggregates(self):
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

    def test_custom_aggregates__deleted__not_used(self):
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

    def test_custom_aggregates__deleted__used(self):
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
    def test_initial(self):
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

    def test_initial__regular_aggregate(self):
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

    def test_initial__custom_aggregate(self):
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

    def test_initial__related_field(self):
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

# TODO: test Report's forms
