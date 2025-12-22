from json import dumps as json_dump
from json import loads as json_load

from django.utils.translation import gettext as _
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
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.reports.core.chart import AbscissaInfo, OrdinateInfo
from creme.reports.core.chart.cell_constraint import (
    ACCCount,
    ACCFieldAggregation,
    abscissa_constraints,
    ordinate_constraints,
)
from creme.reports.forms.chart import AbscissaField, OrdinateField
from creme.reports.models import ReportChart
from creme.reports.tests.base import AxisFieldsMixin


class AbscissaFieldTestCase(AxisFieldsMixin, CremeTestCase):
    def test_clean__empty__not_required(self):
        with self.assertNoException():
            cleaned = AbscissaField(required=False).clean(None)

        self.assertIsNone(cleaned)

    def test_clean__invalid_json(self):
        self.assertFormfieldError(
            field=AbscissaField(required=False),
            value='{"entity_cell":{"cell_key":',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean__invalid_data_type(self):
        field = AbscissaField(required=False)
        msg = _('Invalid type')
        code = 'invalidtype'
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"this is a string"',
        )
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='[]')

    def test_clean__invalid_data(self):
        self.assertFormfieldError(
            field=AbscissaField(required=False),
            value='{"chart_type":"notadict"}',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean__rfield__fk(self):
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

    def test_clean__rfield__date_year(self):
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

    def test_clean__rfield__date__month(self):
        field = AbscissaField(model=FakeContact, abscissa_constraints=abscissa_constraints)

        chart_type = ReportChart.Group.MONTH
        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field('birthday'),
            chart_type=chart_type,
        ))
        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean__rfield__date__day(self):
        field = AbscissaField(model=FakeContact, abscissa_constraints=abscissa_constraints)

        chart_type = ReportChart.Group.DAY
        abs_info = field.clean(self.formfield_value_abscissa(
            abscissa=FakeContact._meta.get_field('birthday'),
            chart_type=chart_type,
        ))
        self.assertEqual(chart_type, abs_info.chart_type)
        self.assertIsNone(abs_info.parameter)

    def test_clean__rfield__range(self):
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

    def test_clean__rfield__error__cell(self):
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

    def test_clean__rfield__error__chart_type(self):
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

    def test_clean__rfield__error__extra(self):
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

    def test_clean__rfield__fields_config(self):
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

    def test_clean__rtype(self):
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

    def test_clean__rtype__error(self):
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

    def test_clean__cfield__enum(self):
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

    def test_clean__cfield__enum__deleted(self):
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
    def test_clean__cfield__date__year(self, cfield_type):
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
    def test_clean__cfield__date__month(self, cfield_type):
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
    def test_clean__cfield__date__day(self, cfield_type):
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

    def test_clean__cfield__range(self):
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

    def test_clean__cfield__error__cell(self):
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

    def test_clean__cfield__error__chart_type(self):
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

    def test_clean__cfield__error__extra(self):
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

    def test_clean__error__cell(self):
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

    def test_clean__error__chart_type(self):
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

    def test_clean__error__extra(self):
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

    def test_clean__not_required(self):
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

    def test_clean__no_model__regular_field(self):
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

    def test_clean__no_model__relation(self):
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

    def test_from_python__rfield__fk(self):
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

    def test_from_python__rfield__date(self):
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

    def test_from_python__relation(self):
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

    def test_from_python__cfield__enum(self):
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

    def test_from_python__cfield__date(self):
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
    def test_clean__empty__not_required(self):
        with self.assertNoException():
            cleaned = OrdinateField(required=False).clean(None)

        self.assertIsNone(cleaned)

    def test_clean__invalid_json(self):
        self.assertFormfieldError(
            field=OrdinateField(required=False),
            value='{"entity_cell":{"cell_key":',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean__invalid_data_type(self):
        field = OrdinateField(required=False)
        code = 'invalidtype'
        msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"this is a string"'
        )
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='[]')

    def test_clean__invalid_data(self):
        self.assertFormfieldError(
            field=OrdinateField(required=False),
            value='{"aggregator":"notadict"}',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean__count(self):
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

    def test_clean__rfield__int(self):
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

    def test_clean__rfield__decimal(self):
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

    def test_clean__rfield__error__agg_id(self):
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

    def test_clean__rfield__error__cell(self):
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

    def test_clean__rfield__fields_config(self):
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

    def test_clean__cfield__int(self):
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

    def test_clean__cfield__error__agg(self):
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

    def test_clean__cfield__error__cell(self):
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

    def test_clean__cfield__error__deleted(self):
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

    def test_clean__error(self):
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

    def test_clean__not_required(self):
        model = FakeOrganisation
        field = OrdinateField(
            model=model,
            ordinate_constraints=ordinate_constraints,
            required=False,
        )
        self.assertIsNone(field.clean(self.formfield_value_ordinate(aggr_id='')))

    def test_clean__no_model(self):
        "Regular field."
        field = OrdinateField(ordinate_constraints=ordinate_constraints)
        self.assertIs(field.model, CremeEntity)

        # TODO: test empty choices ??

    def test_from_python__count(self):
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

    def test_from_python__rfield__int(self):
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

    def test_from_python__cfield__int(self):
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

# TODO: test ReportChartForm
