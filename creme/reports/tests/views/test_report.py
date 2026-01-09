from datetime import date, datetime
from functools import partial

from django.test.utils import override_settings
from django.urls import reverse
from django.utils.encoding import smart_str
from django.utils.formats import get_format
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext, pgettext

from creme.creme_config.forms.fields import CreatorModelChoiceField
from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    condition_handler,
    operators,
)
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.forms import ReadonlyMessageField
from creme.creme_core.gui import actions
from creme.creme_core.models import CustomField, EntityFilter, FakeContact
from creme.creme_core.models import FakeDocument as FakeCoreDocument
from creme.creme_core.models import (
    FakeImage,
    FakeInvoice,
    FakeOrganisation,
    FieldsConfig,
    HeaderFilter,
    RelationType,
)
from creme.creme_core.tests.fake_constants import (
    FAKE_REL_OBJ_EMPLOYED_BY,
    FAKE_REL_SUB_EMPLOYED_BY,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.xlrd_utils import XlrdReader
from creme.reports.actions import ExportReportAction
from creme.reports.bricks import ReportChartsBrick, ReportFieldsBrick
from creme.reports.constants import (
    EF_REPORTS,
    RFT_AGG_CUSTOM,
    RFT_AGG_FIELD,
    RFT_CUSTOM,
    RFT_FIELD,
    RFT_FUNCTION,
    RFT_RELATED,
    RFT_RELATION,
)
from creme.reports.forms.report import ReportExportPreviewFilterForm
from creme.reports.models import FakeReportsDocument, Field
from creme.reports.tests.base import (
    BaseReportsTestCase,
    Report,
    skipIfCustomReport,
)


@skipIfCustomReport
class ReportTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    @staticmethod
    def _build_preview_url(report):
        return reverse('reports__export_report_preview', args=(report.id,))

    def test_detailview(self):
        user = self.login_as_root_and_get()

        report = self._create_simple_contacts_report(user=user, name='My report')
        response = self.assertGET200(report.get_absolute_url())
        self.assertTemplateUsed(response, 'reports/view_report.html')

        tree = self.get_html_tree(response.content)
        brick_node1 = self.get_brick_node(tree, brick=ReportFieldsBrick)
        self.assertEqual(
            _('Columns of the report'), self.get_brick_title(brick_node1),
        )

        brick_node2 = self.get_brick_node(tree, brick=ReportChartsBrick)
        self.assertEqual(_('Charts'), self.get_brick_title(brick_node2))

    def test_creation__no_filter(self):
        "No EntityFilter, no HeaderFilter."
        user = self.login_as_root_and_get()
        cf = self._create_cf_int()

        name = 'trinita'
        self.assertFalse(Report.objects.filter(name=name).exists())

        url = self.ADD_URL
        response0 = self.assertGET200(url)

        with self.assertNoException():
            initial_user_id = response0.context['form']['user'].value()

        self.assertEqual(user.id, initial_user_id)

        # ---
        step_key = 'report_creation_wizard-current_step'
        response1 = self.client.post(
            url,
            data={
                step_key: 0,

                '0-user': user.id,
                '0-name': name,

                '0-cform_extra-reports_filtered_ctype':
                    self.formfield_value_filtered_entity_type(self.ct_contact),
            },
        )
        self.assertNoWizardFormError(response1)

        with self.assertNoException():
            wizard = response1.context['wizard']
            steps = wizard['steps']
            count = steps.count
            current = steps.current

        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add-wizard.html')
        self.assertEqual(3, count)
        self.assertEqual('1', current)

        # ---
        response2 = self.client.post(
            url,
            follow=True,
            data={
                step_key: 1,

                # '1-header_filter': ...,
            },
        )
        self.assertNoWizardFormError(response2)

        with self.assertNoException():
            columns_f = response2.context['wizard']['form'].fields['columns']

        self.assertEqual((), columns_f.initial)

        # ---
        rtype = RelationType.objects.builder(
            id='test-subject_loves', predicate='loves',
        ).symmetric(id='test-object_loves', predicate='is loved').get_or_create()[0]

        fname1 = 'last_name'
        fname2 = 'user'
        funcfield_name = 'get_pretty_properties'
        response3 = self.client.post(
            url,
            follow=True,
            data={
                step_key: 2,

                '2-columns': f'regular_field-{fname1},'
                             f'regular_field-{fname2},'
                             f'relation-{rtype.id},'
                             f'function_field-{funcfield_name},'
                             f'custom_field-{cf.id}',
            },
        )
        self.assertNoWizardFormError(response3)

        report = self.get_object_or_fail(Report, name=name)
        self.assertEqual(user,        report.user)
        self.assertEqual(FakeContact, report.ct.model_class())
        self.assertIsNone(report.filter)

        columns = report.columns
        self.assertEqual(5, len(columns))

        field = columns[0]
        self.assertEqual(RFT_FIELD,      field.type)
        self.assertEqual(fname1,         field.name)
        self.assertEqual(_('Last name'), field.title)
        self.assertFalse(field.selected)
        self.assertFalse(field.sub_report)

        field = columns[1]
        self.assertEqual(fname2,          field.name)
        self.assertEqual(_('Owner user'), field.title)

        field = columns[2]
        self.assertEqual(RFT_RELATION,    field.type)
        self.assertEqual(rtype.id,        field.name)
        self.assertEqual(rtype.predicate, field.title)
        self.assertFalse(field.selected)
        self.assertFalse(field.sub_report)

        field = columns[3]
        self.assertEqual(RFT_FUNCTION,    field.type)
        self.assertEqual(funcfield_name,  field.name)
        self.assertEqual(_('Properties'), field.title)

        field = columns[4]
        self.assertEqual(RFT_CUSTOM,   field.type)
        # self.assertEqual(str(cf.id), field.name)
        self.assertEqual(str(cf.uuid), field.name)
        self.assertEqual(cf.name,      field.title)

    def test_creation__filters(self):
        "With EntityFilter & HeaderFilter; other ContentType."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        cf = CustomField.objects.create(
            content_type=self.ct_orga,
            name='Baseline',
            field_type=CustomField.STR,
        )

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Mihana corp.', FakeOrganisation,
            is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.ICONTAINS,
                    field_name='name', values=['Mihana'],
                ),
            ],
        )

        initial_fname1 = 'user'
        initial_fname2 = 'name'
        hidden_fname = 'sector'
        hfilter_orga = HeaderFilter.objects.proxy(
            id='test_hf', name='name', model=FakeOrganisation,
            is_custom=True,
            cells=[
                (EntityCellRegularField, initial_fname1),
                (EntityCellRegularField, initial_fname2),
                (EntityCellRegularField, hidden_fname),
            ],
        ).get_or_create()[0]

        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        hfilter_orga_forbidden = HeaderFilter.objects.proxy(
            id='test_hf_forbidden', name='name', model=FakeOrganisation,
            is_custom=True, is_private=True, user=other_user,
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'description'),
            ],
        ).get_or_create()[0]
        hfilter_contact = HeaderFilter.objects.filter(
            entity_type=self.ct_contact, is_private=False,
        )[0]

        url = self.ADD_URL
        step_key = 'report_creation_wizard-current_step'
        name = 'My awesome organisation report'
        response1 = self.client.post(
            url,
            data={
                step_key: 0,

                '0-user': user.id,
                '0-name': name,

                '0-cform_extra-reports_filtered_ctype':
                    self.formfield_value_filtered_entity_type(
                        ctype=self.ct_orga, efilter=efilter,
                    ),
            },
        )
        self.assertNoWizardFormError(response1)

        with self.assertNoException():
            hfilter_choices = response1.context['wizard']['form'].fields['header_filter'].choices

        self.assertInChoices(
            value=hfilter_orga.id,
            label=str(hfilter_orga),
            choices=hfilter_choices,
        )
        self.assertNotInChoices(value=hfilter_contact.id,        choices=hfilter_choices)
        self.assertNotInChoices(value=hfilter_orga_forbidden.id, choices=hfilter_choices)

        response2 = self.client.post(
            url,
            follow=True,
            data={
                step_key: 1,

                '1-header_filter': hfilter_orga.id,
            },
        )
        self.assertNoWizardFormError(response2)

        with self.assertNoException():
            columns_f = response2.context['wizard']['form'].fields['columns']

        self.assertListEqual(
            [
                EntityCellRegularField.build(
                    model=FakeOrganisation, name=fname,
                ) for fname in (initial_fname1, initial_fname2)
            ],
            columns_f.initial,
        )

        fname1 = 'name'
        fname2 = 'capital'
        response3 = self.client.post(
            url,
            follow=True,
            data={
                step_key: 2,

                '2-columns': f'regular_field-{fname1},'
                             f'regular_field-{fname2},'
                             f'custom_field-{cf.id}',
            },
        )
        self.assertNoWizardFormError(response3)

        report = self.get_object_or_fail(Report, name=name)
        self.assertEqual(user,             report.user)
        self.assertEqual(FakeOrganisation, report.ct.model_class())
        self.assertEqual(efilter,          report.filter)

        columns = report.columns
        self.assertEqual(3, len(columns))
        self.assertListEqual(
            [RFT_FIELD, RFT_FIELD, RFT_CUSTOM],
            [field.type for field in columns],
        )
        self.assertListEqual(
            [fname1, fname2, str(cf.uuid)],
            [field.name for field in columns],
        )

    def test_creation__report_filter(self):
        user = self.login_as_root_and_get()

        efilter = EntityFilter.objects.create(
            id='reports-test_report_creation03',
            name='Mihana corp.',
            entity_type=FakeOrganisation,
            filter_type=EF_REPORTS,  # <===
        )

        url = self.ADD_URL
        step_key = 'report_creation_wizard-current_step'
        name = 'My awesome organisation report'
        self.assertNoWizardFormError(self.client.post(
            url,
            data={
                step_key: 0,

                '0-user': user.id,
                '0-name': name,

                '0-cform_extra-reports_filtered_ctype':
                    self.formfield_value_filtered_entity_type(
                        ctype=self.ct_orga, efilter=efilter,
                    ),
            },
        ))
        self.assertNoWizardFormError(self.client.post(
            url, follow=True, data={step_key: 1},
        ))
        self.assertNoWizardFormError(self.client.post(
            url,
            follow=True,
            data={
                step_key: 2,
                '2-columns': 'regular_field-name,regular_field-capital',
            },
        ))

        report = self.get_object_or_fail(Report, name=name)
        self.assertEqual(user,             report.user)
        self.assertEqual(FakeOrganisation, report.ct.model_class())
        self.assertEqual(efilter,          report.filter)

    def test_creation__error(self):
        "No column selected."
        user = self.login_as_root_and_get()
        url = self.ADD_URL

        step_key = 'report_creation_wizard-current_step'
        self.assertNoWizardFormError(self.client.post(
            url,
            data={
                step_key: 0,

                '0-user': user.id,
                '0-name': 'Contact report',

                '0-cform_extra-reports_filtered_ctype':
                    self.formfield_value_filtered_entity_type(self.ct_contact),
            },
        ))

        self.assertNoWizardFormError(self.client.post(
            url, follow=True, data={step_key: 1},
        ))

        response3 = self.client.post(
            url,
            follow=True,
            data={
                step_key: 2,

                # '2-columns': '',
            },
        )
        form3 = response3.context['wizard']['form']
        self.assertFormError(form3, field='columns', errors=_('This field is required.'))

    def test_edition(self):
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        name = 'my report'
        report = self._create_simple_contacts_report(user=user, name=name)

        name = name.title()
        create_ef = partial(EntityFilter.objects.smart_update_or_create, is_custom=True)
        efilter = create_ef(
            'test-filter1', 'Filter', FakeContact,
            is_private=True, user=user,
        )
        system_efilter = EntityFilter.objects.create(
            id='test-filter2',
            name='Agencies',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )
        orga_efilter = create_ef('test-filter3', 'Mihana house', FakeOrganisation)
        private_filter = create_ef(
            'test-filter4', 'XXX', FakeContact, is_private=True, user=other_user,
        )

        # GET ---
        url = report.get_edit_absolute_url()
        response = self.assertGET200(url)

        filter_key = 'cform_extra-reports_filter'

        with self.assertNoException():
            filter_choices = response.context['form'].fields[filter_key].choices

        self.assertInChoices(value=efilter.id, label=str(efilter), choices=filter_choices)
        self.assertNotInChoices(value=system_efilter.id, choices=filter_choices)
        self.assertNotInChoices(value=orga_efilter.id,   choices=filter_choices)
        self.assertNotInChoices(value=private_filter.id, choices=filter_choices)

        # POST ---
        response = self.client.post(
            url, follow=True,
            data={
                'user': user.pk,
                'name': name,
                filter_key: efilter.id,
            },
        )
        self.assertNoFormError(response)

        report = self.refresh(report)
        self.assertEqual(name,    report.name)
        self.assertEqual(efilter, report.filter)

    def test_edition__forbidden_filter(self):
        """Cannot edit the 'filter' field when it's a private filter which
        belongs to another user.
        """
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        create_efilter = EntityFilter.objects.smart_update_or_create
        ef_priv = create_efilter(
            'test-private_filter', 'Private filter',
            FakeContact, is_custom=True,
            user=other_user, is_private=True,
        )
        report = Report.objects.create(
            name='Report', user=user, filter=ef_priv, ct=self.ct_contact,
        )

        ef_pub = create_efilter(
            'test-public_filter', 'Public filter', FakeContact, is_custom=True,
        )
        response = self.client.post(
            report.get_edit_absolute_url(),
            follow=True,
            data={
                'user': user.pk,
                'name': 'Report edited',
                'cform_extra-reports_filter': ef_pub.id,  # Should not be used
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(ef_priv, self.refresh(report).filter)

    def test_edition__reset_filter(self):
        "Reset filter to None."
        user = self.login_as_root_and_get()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'A filter', FakeContact, is_custom=True,
        )
        report = Report.objects.create(
            name='Report', user=user, filter=efilter, ct=self.ct_contact,
        )

        url = report.get_edit_absolute_url()
        response1 = self.assertGET200(url)

        filter_key = 'cform_extra-reports_filter'

        with self.assertNoException():
            filter_f = response1.context['form'].fields[filter_key]

        self.assertEqual(efilter, filter_f.initial)

        # ---
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user': user.pk,
                'name': 'Report edited',
                # filter_key: efilter.id,
            },
        )
        self.assertNoFormError(response2)
        self.assertIsNone(self.refresh(report).filter)

    def test_edition__report_filter(self):
        user = self.login_as_root_and_get()

        ctype = self.ct_contact
        efilter = EntityFilter.objects.create(
            id='reports-test_edition_filter',
            name='A filter specific to reports',
            entity_type=ctype,
            filter_type=EF_REPORTS,  # <===
        )
        report = Report.objects.create(name='Report', user=user, filter=efilter, ct=ctype)

        url = report.get_edit_absolute_url()
        response1 = self.assertGET200(url)

        filter_key = 'cform_extra-reports_filter'

        with self.assertNoException():
            filter_f = response1.context['form'].fields[filter_key]
            filter_choices = [*filter_f.choices]

        self.assertEqual(efilter, filter_f.initial)
        self.assertInChoices(
            value=efilter.id, label=str(efilter), choices=filter_choices,
        )

        # ---
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user': user.pk,
                'name': 'Report edited',
                filter_key: efilter.id,
            },
        ))
        self.assertEqual(efilter, self.refresh(report).filter)

    @override_settings(FORM_ENUMERABLE_LIMIT=100)
    def test_inner_edition__filter(self):
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        FieldsConfig.objects.create(
            content_type=Report,
            descriptions=[('description', {FieldsConfig.REQUIRED: True})],
        )  # Should not be used

        create_ef = partial(EntityFilter.objects.smart_update_or_create, is_custom=True)
        contact_filter = create_ef('test-filter1', 'Mihana family', FakeContact)
        orga_filter    = create_ef('test-filter2', 'Mihana house', FakeOrganisation)
        private_filter = create_ef(
            'test-filter3', 'XXX', FakeContact, is_private=True, user=other_user,
        )

        report = self._create_simple_contacts_report(
            user=user, name='A', description='Simple report',
        )
        self.assertIsNone(report.filter)

        field_name = 'filter'
        uri = self.build_inneredit_uri(report, field_name)
        response1 = self.assertGET200(uri)
        form_field_name = f'override-{field_name}'

        with self.assertNoException():
            filter_f1 = response1.context['form'].fields[form_field_name]
            choices = [*filter_f1.choices]

        self.assertIsInstance(filter_f1, CreatorModelChoiceField)

        self.assertInChoices(value=contact_filter.id, label=contact_filter.name, choices=choices)
        self.assertInChoices(value='', label=pgettext('creme_core-filter', 'All'), choices=choices)
        # Excluded from filter choices because report targets a Contact:
        self.assertNotInChoices(value=orga_filter.id,    choices=choices)
        self.assertNotInChoices(value=private_filter.id, choices=choices)

        self.assertIsNone(filter_f1.initial)
        self.assertFalse(filter_f1.required)

        # ---
        response2 = self.assertPOST200(uri, data={form_field_name: orga_filter.pk})
        self.assertFormError(
            response2.context['form'],
            field=form_field_name,
            errors=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
        )

        # ---
        response3 = self.client.post(uri, data={form_field_name: contact_filter.pk})
        self.assertNoFormError(response3)
        self.assertEqual(contact_filter, self.refresh(report).filter)

        # ---
        response4 = self.assertGET200(uri)

        with self.assertNoException():
            filter_f4 = response4.context['form'].fields[form_field_name]

        self.assertEqual(contact_filter.id, filter_f4.initial)

    def test_inner_edition__filter__private(self):
        "Private filter to another user -> cannot edit."
        # self.login_as_root()
        user = self.login_as_standard(allowed_apps=['reports', 'creme_core'])
        self.add_credentials(role=user.role, all='*')
        # other_user = self.create_user()
        other_user = self.create_user(index=1)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Mihana family', FakeContact,
            is_custom=True, is_private=True, user=other_user,
        )
        report = Report.objects.create(
            user=other_user, name="Other's report",
            ct=efilter.entity_type, filter=efilter,
        )

        field_name = 'filter'
        uri = self.build_inneredit_uri(report, field_name)
        self.assertContains(
            self.client.get(uri),
            ngettext(
                'The filter cannot be changed because it is private.',
                'The filters cannot be changed because they are private.',
                1,
            ),
            html=True,
        )

        response = self.assertPOST200(uri, data={f'override-{field_name}': ''})
        self.assertFormError(
            self.get_form_or_fail(response),
            field=f'override-{field_name}',
            errors=_('The filter cannot be changed because it is private.'),
        )
        self.assertEqual(efilter, self.refresh(report).filter)

        # Public filter => OK
        efilter.is_private = False
        efilter.save()
        self.assertNoFormError(self.client.post(uri, data={f'override-{field_name}': ''}))
        self.assertIsNone(self.refresh(report).filter)

    def test_inner_edition__filter__set_required(self):
        user = self.login_as_root_and_get()

        field_name = 'filter'
        FieldsConfig.objects.create(
            content_type=Report,
            descriptions=[(field_name, {FieldsConfig.REQUIRED: True})],
        )

        report = self._create_simple_contacts_report(user=user, name='A')

        response = self.assertGET200(self.build_inneredit_uri(report, field_name))

        with self.assertNoException():
            filter_f = response.context['form'].fields[f'override-{field_name}']

        self.assertTrue(filter_f.required)

    @override_settings(FORM_ENUMERABLE_LIMIT=100)
    def test_inner_edition__filter__report_filter(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(
            user=user, name='A', description='Simple report',
        )
        self.assertIsNone(report.filter)

        efilter = EntityFilter.objects.create(
            id='reports-test_inneredit_report_filter', name='Contacts',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,  # <===
        )

        field_name = 'filter'
        uri = self.build_inneredit_uri(report, field_name)
        response1 = self.assertGET200(uri)
        form_field_name = f'override-{field_name}'

        with self.assertNoException():
            efilter_choices = [*response1.context['form'].fields[form_field_name].choices]

        self.assertInChoices(value=efilter.id, label=str(efilter), choices=efilter_choices)

        self.assertNoFormError(self.client.post(uri, data={form_field_name: efilter.pk}))
        self.assertEqual(efilter, self.refresh(report).filter)

    def test_bulk_edition__filter(self):
        "Reports are related to the same ContentType -> OK."
        user = self.login_as_root_and_get()

        create_ef = partial(EntityFilter.objects.smart_update_or_create, is_custom=True)
        contact_filter = create_ef('test-filter1', 'Mihana family', FakeContact)
        orga_filter    = create_ef('test-filter2', 'Mihana house', FakeOrganisation)

        report1 = self._create_simple_contacts_report(user=user, name='Filter #1')
        report2 = self._create_simple_contacts_report(user=user, name='Filter #2')

        reports = [report1, report2]
        field_name = 'filter'
        build_uri = partial(self.build_bulkupdate_uri, model=Report, field=field_name)
        response1 = self.assertGET200(build_uri(entities=reports))
        formfield_name = f'override-{field_name}'

        with self.assertNoException():
            filter_f = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(filter_f, CreatorModelChoiceField)
        self.assertEqual(pgettext('creme_core-filter', 'All'), filter_f.empty_label)

        # ---
        response2 = self.assertPOST200(
            build_uri(),
            data={
                'entities': [report.id for report in reports],
                formfield_name: orga_filter.id,
            },
        )
        self.assertFormError(
            response2.context['form'],
            field=formfield_name,
            errors=_(
                'Select a valid choice. '
                'That choice is not one of the available choices.'
            ),
        )

        response2 = self.client.post(
            build_uri(),
            data={
                'entities': [report.id for report in reports],
                formfield_name: contact_filter.id,
            },
        )
        self.assertNoFormError(response2)

        self.assertEqual(self.refresh(report1).filter, contact_filter)
        self.assertEqual(self.refresh(report2).filter, contact_filter)

    def test_bulk_edition__filter__different_ctypes(self):
        "Reports are related to different ContentTypes -> error."
        user = self.login_as_root_and_get()

        field_name = 'filter'
        FieldsConfig.objects.create(
            content_type=Report,
            descriptions=[(field_name, {FieldsConfig.REQUIRED: True})],
        )

        contact_filter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Mihana family', FakeContact, is_custom=True,
        )

        report1 = self._create_simple_contacts_report(user=user, name='Contact report')
        report2 = self._create_simple_organisations_report(user=user, name='Orga report')

        reports = [report1, report2]
        build_uri = partial(self.build_bulkupdate_uri, model=Report, field=field_name)
        response1 = self.assertGET200(build_uri(entities=reports))
        formfield_name = f'override-{field_name}'

        with self.assertNoException():
            filter_f = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(filter_f, ReadonlyMessageField)
        self.assertEqual(_('Filter'), filter_f.label)
        self.assertTrue(filter_f.initial)
        self.assertFalse(filter_f.required)

        # ----
        response2 = self.assertPOST200(
            build_uri(),
            data={
                'entities': [report.id for report in reports],
                formfield_name: contact_filter.id,
            },
        )
        self.assertFormError(
            response2.context['form'],
            field=formfield_name,
            errors=_(
                'Filter field can only be updated when reports '
                'target the same type of entities (e.g: only contacts).'
            ),
        )

    def test_bulk_edition__filter__not_viewable_filters(self):
        "Some filters are not visible (private) -> errors."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        create_ef = partial(
            EntityFilter.objects.smart_update_or_create,
            is_custom=True, model=FakeContact,
        )
        efilter1 = create_ef('test-filter1', name='Filter #1')
        efilter2 = create_ef('test-filter2', name='Filter #2', is_private=True, user=other_user)
        efilter3 = create_ef('test-filter3', name='Filter #3', is_private=True, user=user)

        report1 = self._create_simple_contacts_report(user=user, name='Filter#1', efilter=efilter1)
        report2 = self._create_simple_contacts_report(user=user, name='Filter #2')
        report3 = Report.objects.create(
            user=other_user, name="Other's report",
            ct=efilter2.entity_type, filter=efilter2,
        )

        field_name = 'filter'
        formfield_name = f'override-{field_name}'
        reports = [report1, report2, report3]
        build_uri = partial(self.build_bulkupdate_uri, model=Report, field=field_name)
        response1 = self.assertGET200(build_uri(entities=reports))

        with self.assertNoException():
            filter_f = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(filter_f, CreatorModelChoiceField)
        self.assertEqual(
            ngettext(
                'Beware! The filter of {count} report cannot be changed '
                'because it is private.',
                'Beware! The filters of {count} reports cannot be changed '
                'because they are private.',
                1,
            ).format(count=1),
            filter_f.help_text,
        )

        # ---
        response2 = self.client.post(
            build_uri(),
            data={
                'entities': [report.id for report in reports],
                formfield_name: efilter3.id,
            },
        )
        self.assertNoFormError(response2)

        self.assertEqual(efilter3, self.refresh(report1).filter)
        self.assertEqual(efilter3, self.refresh(report2).filter)
        self.assertEqual(efilter2, self.refresh(report3).filter)  # No change

    def test_listview(self):
        user = self.login_as_root_and_get()

        reports = [
            self._create_simple_contacts_report(user=user, name='Report#1'),
            self._create_simple_contacts_report(user=user, name='Report#2'),
        ]

        response = self.assertGET200(Report.get_lv_absolute_url())

        with self.assertNoException():
            reports_page = response.context['page_obj']

        for report in reports:
            self.assertIn(report, reports_page.object_list)

    def test_listview_actions(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(user=user, name='Report#1')

        export_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=report)
            if isinstance(action, ExportReportAction)
        )
        self.assertEqual('reports-export', export_action.id)
        self.assertEqual('reports-export', export_action.type)
        self.assertEqual(
            reverse('reports__export_report_filter', args=(report.id,)),
            export_action.url,
        )
        self.assertEqual(
            pgettext('reports-report', 'Export «{object}»').format(object=report),
            export_action.help_text,
        )
        self.assertTrue(export_action.is_enabled)
        self.assertTrue(export_action.is_visible)

    def test_preview(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        chiyo = create_contact(
            first_name='Chiyo', last_name='Mihana', birthday=date(year=1995, month=3, day=26),
        )
        osaka = create_contact(
            first_name='Ayumu', last_name='Kasuga', birthday=date(year=1990, month=4, day=1),
        )

        report = self._create_contacts_report(user=user, name='My report')
        url = self._build_preview_url(report)

        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'reports/preview_report.html')

        context1 = response1.context
        self.assertEqual(report, context1.get('object'))
        self.assertEqual(25,     context1.get('limit_to'))
        self.assertFalse(context1.get('empty_message'))

        form = context1.get('form')
        self.assertIsInstance(form, ReportExportPreviewFilterForm)

        with self.assertNoException():
            field_choices = form.fields['date_field'].choices

        self.assertInChoices(value='created', label=_('Creation date'), choices=field_choices)
        self.assertInChoices(value='birthday', label=_('Birthday'),     choices=field_choices)
        self.assertInChoices(
            value='image__modified',
            label='[{}] - {}'.format(_('Photograph'), _('Last modification')),
            choices=field_choices,
        )
        self.assertInChoices(
            value='image__exif_date',
            label='[{}] - {}'.format(_('Photograph'), _('Exif date')),
            choices=field_choices,
        )
        self.assertNotInChoices(value='last_name',   choices=field_choices)
        self.assertNotInChoices(value='image',       choices=field_choices)
        self.assertNotInChoices(value='image__name', choices=field_choices)

        columns = context1.get('flat_columns')
        self.assertIsList(columns, length=4)
        self.assertIsInstance(columns[0], Field)
        self.assertListEqual(
            ['last_name', 'user', 'creme_core-subject_has', 'get_pretty_properties'],
            [f.name for f in columns],
        )

        self.assertContains(response1, chiyo.last_name)
        self.assertContains(response1, osaka.last_name)

        # ---
        response2 = self.client.get(
            url,
            data={
                'doc_type': 'csv',
                'date_filter_0': '',
                'date_filter_1': self.formfield_value_date(1990,  1,  1),
                'date_filter_2': self.formfield_value_date(1990, 12, 31),
                'date_field':    'birthday',
            },
        )
        self.assertTemplateUsed(response2, 'reports/preview_report.html')
        self.assertNoFormError(response2)
        self.assertContains(response2, osaka.last_name)
        self.assertNotContains(response2, chiyo.last_name)

    def test_preview__empty__no_contact(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(user=user, name='My report')

        response = self.assertGET200(self._build_preview_url(report))
        self.assertTemplateUsed(response, 'reports/preview_report.html')
        self.assertContains(
            response,
            _('You can see no «{model}»').format(model='Test Contact'),
        )

    def test_preview__empty__no_allowed_contact(self):
        user = self.login_as_basic_user(creatable_models=[Report])

        FakeContact.objects.create(
            user=self.get_root_user(), first_name='Chiyo', last_name='Mihana',
        )

        report = self._create_simple_contacts_report(user=user, name='My report')
        response = self.assertGET200(self._build_preview_url(report))
        self.assertContains(
            response,
            _('You can see no «{model}»').format(model='Test Contact'),
        )

    def test_preview__empty__no_filtered_contact__string(self):
        "Empty: no contact after string filtering."
        user = self.login_as_root_and_get()
        tomo = FakeContact.objects.create(user=user, first_name='Tomo', last_name='Takino')

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Kasuga family', FakeContact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=['Kasuga'],
                ),
            ],
        )
        report = self._create_simple_contacts_report(user=user, name='My report', efilter=efilter)

        response = self.assertGET200(self._build_preview_url(report))
        self.assertNotContains(response, tomo.last_name)
        self.assertContains(
            response,
            _('No «{model}» matches the filter «{filter}»').format(
                model='Test Contact',
                filter=report.filter,
            ),
        )

    def test_preview__empty__no_filtered_contact__date(self):
        "Empty: no contact after date filtering."
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(user=user, name='My report')

        FakeContact.objects.create(
            user=user, first_name='Chiyo', last_name='Mihana',
            birthday=date(year=1995, month=3, day=26),
        )

        response = self.assertGET200(
            self._build_preview_url(report),
            data={
                'doc_type':      'csv',
                'date_filter_0': '',
                'date_filter_1': self.formfield_value_date(1990,  1,  1),
                'date_filter_2': self.formfield_value_date(1990, 12, 31),
                'date_field':    'birthday',
            }
        )
        msg = _('No «{model}» matches your date filter').format(model='Test Contact')
        self.assertEqual(msg, response.context.get('empty_message'))
        self.assertContains(response, msg)

    def test_preview__hidden_fields(self):
        user = self.login_as_root_and_get()

        hidden = 'birthday'
        img_hidden = 'exif_date'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden, {FieldsConfig.HIDDEN: True})],
        )
        FieldsConfig.objects.create(
            content_type=FakeImage,
            descriptions=[(img_hidden, {FieldsConfig.HIDDEN: True})],
        )

        report = self._create_contacts_report(user=user, name='My report')
        response = self.assertGET200(self._build_preview_url(report))

        with self.assertNoException():
            field_choices = response.context['form'].fields['date_field'].choices

        self.assertInChoices(value='created',  label=_('Creation date'),     choices=field_choices)
        self.assertInChoices(value='modified', label=_('Last modification'), choices=field_choices)
        self.assertNotInChoices(value=hidden,                 choices=field_choices)
        self.assertNotInChoices(value=f'image__{img_hidden}', choices=field_choices)

    def test_preview__filter_on_sub_field(self):
        user = self.login_as_root_and_get()

        create_image = partial(FakeImage.objects.create, user=user)
        img1 = create_image(name='Chiyo pix', exif_date=date(year=1995, month=3, day=26))
        img2 = create_image(name='Ayumu pix', exif_date=date(year=1990, month=4, day=1))

        create_contact = partial(FakeContact.objects.create, user=user)
        chiyo = create_contact(first_name='Chiyo', last_name='Mihana', image=img1)
        osaka = create_contact(first_name='Ayumu', last_name='Kasuga', image=img2)

        report = self._create_contacts_report(user=user, name='My report')
        response = self.client.get(
            self._build_preview_url(report),
            data={
                'doc_type': 'csv',
                'date_filter_0': '',
                'date_filter_1': self.formfield_value_date(1990,  1,  1),
                'date_filter_2': self.formfield_value_date(1990, 12, 31),
                'date_field':    'image__exif_date',
            },
        )
        self.assertNoFormError(response)
        self.assertContains(response, osaka.last_name)
        self.assertNotContains(response, chiyo.last_name)


@skipIfCustomReport
class ExportTestCase(BaseReportsTestCase):
    @staticmethod
    def _build_export_url(report):
        return reverse('reports__export_report', args=(report.id,))

    def test_filter__custom_range(self):
        user = self.login_as_root_and_get()

        report = self._create_simple_contacts_report(user=user, name='My report')
        url = reverse('reports__export_report_filter', args=(report.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'reports/forms/report-export-filter.html')

        context = response.context
        self.assertEqual(
            pgettext('reports-report', 'Export «{object}»').format(object=report),
            context.get('title'),
        )
        self.assertEqual(
            pgettext('reports-report', 'Export'),
            context.get('submit_label'),
        )

        # ---
        date_field = 'birthday'
        start = self.formfield_value_date(1990, 1, 1)
        end = self.formfield_value_date(1990, 12, 31)
        response = self.assertPOST200(
            url,
            data={
                'doc_type':      'csv',
                'date_filter_0': '',
                'date_filter_1': start,
                'date_filter_2': end,
                'date_field':    date_field,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(
            '{url}?doc_type=csv'
            '&date_field={field}'
            '&date_filter_0='
            '&date_filter_1={start}'
            '&date_filter_2={end}'.format(
                url=reverse('reports__export_report', args=(report.id,)),
                field=date_field,
                start=start,
                end=end
            ),
            response.text,
        )

    def test_filter__regular_user(self):
        user = self.login_as_standard(allowed_apps=['reports'])
        self.add_credentials(user.role, all=['VIEW'])

        report = Report.objects.create(name='Report', user=user, ct=self.ct_orga)
        self.assertGET200(reverse('reports__export_report_filter', args=(report.id,)))

    def test_filter__view_perms(self):
        user = self.login_as_standard(allowed_apps=['reports'])

        report = Report.objects.create(name='Report', user=user, ct=self.ct_orga)
        self.assertGET403(reverse('reports__export_report_filter', args=(report.id,)))

    def test_filter__missing_doctype(self):
        user = self.login_as_root_and_get()

        report = self._create_simple_contacts_report(user=user, name='My report')
        url = reverse('reports__export_report_filter', args=(report.id,))
        self.assertGET200(url)

        date_field = 'birthday'
        response = self.assertPOST200(url, data={'date_field': date_field})

        self.assertFormError(
            self.get_form_or_fail(response),
            field='doc_type', errors=_('This field is required.'),
        )

    def test_filter__missing_custom_range(self):
        user = self.login_as_root_and_get()

        report = self._create_simple_contacts_report(user=user, name='My report')
        url = reverse('reports__export_report_filter', args=(report.id,))
        self.assertGET200(url)

        # ---
        response = self.assertPOST200(
            url,
            data={
                'doc_type': 'csv',
                'date_field': 'birthday',

                'date_filter_0': '',
                'date_filter_1': '',
                'date_filter_2': '',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_(
                'If you chose a Date field, and select «customized» '
                'you have to specify a start date and/or an end date.'
            ),
        )

    def test_filter__invalid_filter(self):
        user = self.login_as_root_and_get()

        report = self._create_simple_contacts_report(user=user, name='My report')
        url = reverse('reports__export_report_filter', args=(report.id,))
        self.assertGET200(url)

        date_field = 'birthday'
        response = self.assertPOST200(
            url,
            data={
                'date_field': date_field,
                'date_filter_0': 'unknown',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='date_filter',
            errors=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': 'unknown'},
        )

    def test_filter__no_date_field(self):
        user = self.login_as_root_and_get()

        report = self._create_simple_contacts_report(user=user, name='My report')
        url = reverse('reports__export_report_filter', args=(report.id,))
        self.assertGET200(url)

        date_field = ''
        doc_type = 'csv'
        response = self.client.post(
            url,
            data={
                'doc_type':      doc_type,
                'date_filter_0': '',
                'date_field':    date_field,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(
            reverse(
                'reports__export_report',
                args=(report.id,), query={'doc_type': doc_type, 'date_field': ''},
            ),
            response.text,
        )

    def test_empty(self):
        "Empty report."
        user = self.login_as_root_and_get()
        self.assertFalse(FakeInvoice.objects.all())

        rt = RelationType.objects.get(pk=REL_SUB_HAS)
        report = Report.objects.create(
            user=user, name='Report on invoices', ct=FakeInvoice,
        )
        create_field = partial(Field.objects.create, report=report)
        create_field(name='name',                  type=RFT_FIELD,    order=1)
        create_field(name='user',                  type=RFT_FIELD,    order=2)
        create_field(name=rt.id,                   type=RFT_RELATION, order=3)
        create_field(name='get_pretty_properties', type=RFT_FUNCTION, order=4)

        response = self.assertGET200(self._build_export_url(report), data={'doc_type': 'csv'})
        self.assertEqual('doc_type=csv', response.request['QUERY_STRING'])
        self.assertEqual(
            '"{}","{}","{}","{}"\r\n'.format(
                _('Name'), _('Owner user'), rt.predicate, _('Properties'),
            ),
            response.text,
        )

    def test_perms(self):
        user = self.login_as_standard(
            allowed_apps=['creme_core'],  # 'reports'
            # exportable_models=[FakeContact],
        )
        role = user.role
        self.add_credentials(role=role, own=['VIEW'])

        report = self._create_contacts_report(user=user, name='trinita')
        url = self._build_export_url(report)
        data = {'doc_type': 'csv'}

        # App permission --
        response1 = self.client.get(url, data=data)
        self.assertContains(
            response1,
            status_code=403,
            text=_('You are not allowed to access to the app: {}').format(_('Reports')),
            html=True,
        )

        # Export permission --
        role.allowed_apps = ['creme_core', 'reports']
        role.save()
        response2 = self.client.get(url, data=data)
        self.assertContains(
            response2,
            status_code=403,
            text=_('You are not allowed to export: {}').format('Test Contact'),
            html=True,
        )
        # print(response.content)

    def test_no_filter(self):
        user = self.login_as_standard(
            allowed_apps=['creme_core', 'reports'],
            exportable_models=[FakeContact],
        )
        self.add_credentials(role=user.role, own=['VIEW'])

        self._create_persons(user=user)
        self.assertEqual(3, FakeContact.objects.count())

        report = self._create_contacts_report(user=user, name='trinita')
        response = self.assertGET200(
            self._build_export_url(report), data={'doc_type': 'csv'},
        )

        content = (s for s in response.text.split('\r\n') if s)
        self.assertEqual(
            smart_str('"{}","{}","{}","{}"'.format(
                _('Last name'), _('Owner user'), _('owns'), _('Properties'),
            )),
            next(content),
        )

        user_str = str(user)
        # Alphabetical ordering ??
        self.assertEqual(f'"Ayanami","{user_str}","","Kawaii"',  next(content))
        self.assertEqual(f'"Katsuragi","{user_str}","Nerv",""',  next(content))
        self.assertEqual(f'"Langley","{user_str}","",""',        next(content))
        with self.assertRaises(StopIteration):
            next(content)

    def test_date_filter__custom(self):
        "With date filter."
        user = self.login_as_root_and_get()

        self._create_persons(user=user)
        report = self._create_contacts_report(user=user, name='trinita')
        response = self.assertGET200(
            self._build_export_url(report),
            data={
                'doc_type': 'csv',
                'date_field': 'birthday',
                'date_filter_0': '',
                'date_filter_1': self.formfield_value_date(1980, 1, 1),
                'date_filter_2': self.formfield_value_date(2000, 1, 1),
            },
        )

        content = [s for s in response.text.split('\r\n') if s]
        self.assertEqual(3, len(content))

        self.assertEqual(f'"Ayanami","{user}","","Kawaii"', content[1])
        self.assertEqual(f'"Langley","{user}","",""',       content[2])

    def test_date_filter__registered(self):
        "With date filter and registered range."
        user = self.login_as_root_and_get()

        self._create_persons(user=user)
        FakeContact.objects.create(
            user=user,
            last_name='Baby', first_name='Joe',
            birthday=datetime(year=now().year, month=1, day=1)
        )
        report = self._create_contacts_report(user=user, name='trinita')
        response1 = self.assertGET200(
            self._build_export_url(report),
            data={
                'doc_type': 'csv',
                'date_field': 'birthday',
                'date_filter_0': 'current_year',
            },
        )

        content1 = [s for s in response1.text.split('\r\n') if s]
        self.assertEqual(2, len(content1))
        self.assertEqual(f'"Baby","{user}","",""', content1[1])

        # ---
        response2 = self.assertGET200(
            self._build_export_url(report),
            data={
                'doc_type': 'csv',
                'date_field': 'birthday',
                'date_filter_0': 'current_year',
                # Should not be used
                'date_filter_1': self.formfield_value_date(1980, 1, 1),
                'date_filter_2': self.formfield_value_date(2000, 1, 1),
            },
        )

        content2 = [s for s in response2.text.split('\r\n') if s]
        self.assertEqual(2, len(content2))
        self.assertEqual(f'"Baby","{user}","",""', content2[1])

    def test_date_filter__errors(self):
        "Errors: invalid GET param."
        user = self.login_as_root_and_get()

        self._create_persons(user=user)
        report = self._create_contacts_report(user=user, name='trinita')
        url = self._build_export_url(report)
        data = {
            'doc_type': 'csv',
            'date_field': 'birthday',
            'date_filter_0': '',
            'date_filter_1': self.formfield_value_date(1980, 1, 1),
            'date_filter_2': self.formfield_value_date(2000, 1, 1),
        }

        def export(status, **kwargs):
            self.assertGET(status, url, data={**data, **kwargs})

        export(409, date_field='invalidfield')
        export(409, date_field='first_name')  # Not a date field

        self.assertNotIn(r'%Y\%m\%d', get_format('DATE_INPUT_FORMATS'))
        export(409, date_filter_1=r'1980\01\01')  # Invalid format
        export(409, date_filter_2=r'2000\01\01')  # Invalid format

    def test_fields_config(self):
        "With FieldsConfig."
        user = self.login_as_root_and_get()

        hidden_fname1 = 'phone'
        hidden_fname2 = 'image'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        self._create_persons(user=user)

        report = self._create_simple_contacts_report(user=user)

        create_rfield = partial(Field.objects.create, report=report, type=RFT_FIELD)
        create_rfield(order=2, name=hidden_fname1)
        create_rfield(order=3, name=hidden_fname2 + '__description')

        response = self.assertGET200(self._build_export_url(report), data={'doc_type': 'csv'})

        content = (s for s in response.text.split('\r\n') if s)
        self.assertEqual(smart_str('"{}"'.format(_('Last name'))), next(content))

        self.assertEqual('"Ayanami"',   next(content))
        self.assertEqual('"Katsuragi"', next(content))

    def test_fields_config__subfield(self):
        "With FieldsConfig on sub-field."
        user = self.login_as_root_and_get()

        hidden_fname = 'description'
        FieldsConfig.objects.create(
            content_type=FakeImage,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        self._create_persons(user=user)

        report = self._create_simple_contacts_report(user=user)
        Field.objects.create(
            report=report, type=RFT_FIELD, order=2, name=f'image__{hidden_fname}',
        )

        response = self.assertGET200(self._build_export_url(report), data={'doc_type': 'csv'})

        # content = (s for s in response.content.decode().split('\r\n') if s)
        content = (s for s in response.text.split('\r\n') if s)
        self.assertEqual(smart_str('"{}"'.format(_('Last name'))), next(content))

        self.assertEqual('"Ayanami"',   next(content))
        self.assertEqual('"Katsuragi"', next(content))

    def test_disabled_rtype(self):
        "With disabled RelationType."
        user = self.login_as_root_and_get()

        rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='[disabled]',
            enabled=False,
        ).symmetric(id='test-object_disabled', predicate='what ever').get_or_create()[0]

        report = self._create_simple_contacts_report(user=user)

        create_rfield = partial(Field.objects.create, report=report, type=RFT_RELATION)
        create_rfield(order=2, name=FAKE_REL_SUB_EMPLOYED_BY)
        create_rfield(order=3, name=rtype.id)

        response = self.assertGET200(self._build_export_url(report), data={'doc_type': 'csv'})

        content = (s for s in response.text.split('\r\n') if s)
        self.assertEqual(
            smart_str('"{}","is an employee of"'.format(_('Last name'))),
            next(content),
        )

    def test_date_filter__sub_field(self):
        user = self.login_as_root_and_get()

        create_image = partial(FakeImage.objects.create, user=user)
        img1 = create_image(name='Chiyo pix', exif_date=date(year=1995, month=3, day=26))
        img2 = create_image(name='Ayumu pix', exif_date=date(year=1990, month=4, day=1))

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Chiyo', last_name='Mihana', image=img1)
        osaka = create_contact(first_name='Ayumu', last_name='Kasuga', image=img2)

        report = self._create_simple_contacts_report(user=user, name='My report')
        response = self.assertGET200(
            self._build_export_url(report),
            data={
                'doc_type': 'csv',
                'date_field': 'image__exif_date',
                'date_filter_0': '',
                'date_filter_1': self.formfield_value_date(1990,  1,  1),
                'date_filter_2': self.formfield_value_date(1990, 12, 31),
            },
        )

        content = [s for s in response.text.split('\r\n') if s]
        self.assertEqual(2, len(content))
        self.assertEqual('"{}"'.format(_('Last name')), content[0])
        self.assertEqual(f'"{osaka.last_name}"',        content[1])

    def test_xls(self):
        "With date filter."
        user = self.login_as_root_and_get()

        self._create_persons(user=user)
        report = self._create_contacts_report(user=user, name='trinita')
        response = self.assertGET200(
            reverse('reports__export_report', args=(report.id,)),
            data={
                'doc_type': 'xls',
                'date_field': 'birthday',
                'date_filter_0': '',
                'date_filter_1': self.formfield_value_date(1980, 1, 1),
                'date_filter_2': self.formfield_value_date(2000, 1, 1),
            },
            follow=True,
        )
        result = [*XlrdReader(None, file_contents=b''.join(response.streaming_content))]

        self.assertEqual(3, len(result))

        user_str = str(user)
        self.assertEqual(['Ayanami', user_str, '', 'Kawaii'], result[1])
        self.assertEqual(['Langley', user_str, '', ''],       result[2])


@skipIfCustomReport
class ReportFieldTestCase(BaseReportsTestCase):
    @staticmethod
    def _build_edit_fields_url(report):
        return reverse('reports__edit_fields', args=(report.id,))

    @staticmethod
    def _build_link_report_url(rfield):
        return reverse('reports__link_report', args=(rfield.id,))

    def test_reorder(self):
        user = self.login_as_root_and_get()

        report = self._create_contacts_report(user=user, name='trinita')
        rfield = self.get_field_or_fail(report, 'user')
        url = reverse('reports__reorder_field', args=(report.id, rfield.id,))
        self.assertGET405(url, data={'target': 1})

        self.client.post(url, data={'target': 1})
        self.assertListEqual(
            ['user', 'last_name', REL_SUB_HAS, 'get_pretty_properties'],
            [f.name for f in report.fields.order_by('order')],
        )

    def test_reorder__error(self):
        "Report & Field do not match."
        user = self.login_as_root_and_get()

        report1 = self._create_simple_contacts_report(user=user, name='Hill')
        report2 = self._create_simple_contacts_report(user=user, name='Spencer')

        rfield = self.get_field_or_fail(report1, 'last_name')
        self.assertPOST404(
            reverse('reports__reorder_field', args=(report2.id, rfield.id,)),
            data={'target': 1},
        )

    def test_edition(self):
        user = self.login_as_root_and_get()

        report = self._create_simple_contacts_report(user=user, name='Report #1')
        url = self._build_edit_fields_url(report)
        self.assertGET200(url)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Edit columns of «{object}»').format(object=report),
            response.context.get('title'),
        )

        # ---
        old_rfield = report.columns[0]

        self.assertNoFormError(self.client.post(
            url,
            data={
                'columns': 'regular_field-last_name,'
                           'regular_field-first_name',
            },
        ))

        columns = self.refresh(report).columns
        self.assertEqual(2, len(columns))

        column = columns[0]
        self.assertEqual('last_name',    column.name)
        self.assertEqual(_('Last name'), column.title)
        self.assertEqual(1,              column.order)
        self.assertEqual(RFT_FIELD,      column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)
        self.assertEqual(old_rfield.id, column.id)
        self.assertEqual(old_rfield,    column)

        column = columns[1]
        self.assertEqual('first_name',    column.name)
        self.assertEqual(_('First name'), column.title)
        self.assertEqual(2,               column.order)

    def test_edition__fk_n_cfield(self):
        "FK, Custom field, aggregate on CustomField; additional old Field deleted."
        user = self.login_as_root_and_get()

        cf = self._create_cf_int()

        report = self._create_contacts_report(user=user, name='My beloved Report')
        Field.objects.create(report=report, type=RFT_FIELD, name='description', order=5)

        old_rfields = self.refresh(report).columns
        self.assertEqual(5, len(old_rfields))

        f_name = 'last_name'
        fk_name = 'image'
        cf_id = str(cf.id)
        aggr_id = f'{cf.uuid}__max'
        response = self.client.post(
            self._build_edit_fields_url(report),
            data={
                'columns': f'regular_field-{f_name},'
                           f'custom_field-{cf_id},'
                           f'custom_aggregate-{aggr_id},'
                           f'regular_field-{fk_name}',
            },
        )
        self.assertNoFormError(response)

        columns = [*report.fields.all()]
        self.assertEqual(4, len(columns))

        column1 = columns[0]
        self.assertEqual(f_name,            column1.name)
        self.assertEqual(old_rfields[0].id, column1.id)

        column2 = columns[1]
        # self.assertEqual(cf_id,      column2.name)
        self.assertEqual(str(cf.uuid), column2.name)
        self.assertEqual(cf.name,      column2.title)
        self.assertEqual(RFT_CUSTOM,   column2.type)
        self.assertFalse(column2.selected)
        self.assertIsNone(column2.sub_report)
        self.assertEqual(old_rfields[1].id, column2.id)

        column3 = columns[2]
        self.assertEqual(aggr_id,                       column3.name)
        self.assertEqual(f"{_('Maximum')} - {cf.name}", column3.title)
        self.assertEqual(RFT_AGG_CUSTOM,                column3.type)
        self.assertEqual(old_rfields[2].id,             column3.id)

        column4 = columns[3]
        self.assertEqual(fk_name,         column4.name)
        self.assertEqual(_('Photograph'), column4.title)
        self.assertEqual(RFT_FIELD,       column4.type)

        self.assertDoesNotExist(old_rfields[4])

    def test_edition__relation_n_function_field(self):
        "Other types: relationships, function fields."
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(user=user, name='My beloved Report')
        f_name = 'user__username'

        rtype_id = FAKE_REL_SUB_EMPLOYED_BY
        rtype = self.get_object_or_fail(RelationType, pk=rtype_id)

        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')
        self.assertIsNotNone(funcfield)

        response = self.client.post(
            self._build_edit_fields_url(report),
            data={
                'columns': f'relation-{rtype_id},'
                           f'regular_field-{f_name},'
                           f'function_field-{funcfield.name}',
            },
        )
        self.assertNoFormError(response)

        columns = report.columns
        self.assertEqual(3, len(columns))

        column1 = columns[0]
        self.assertEqual(rtype_id,        column1.name)
        self.assertEqual(rtype.predicate, column1.title)
        self.assertEqual(1,               column1.order)
        self.assertEqual(RFT_RELATION,    column1.type)
        self.assertFalse(column1.selected)
        self.assertIsNone(column1.sub_report)

        column2 = columns[1]
        self.assertEqual(f_name,                                 column2.name)
        self.assertEqual(RFT_FIELD,                              column2.type)
        self.assertEqual(f"{_('Owner user')} - {_('Username')}", column2.title)

        column3 = columns[2]
        self.assertEqual(funcfield.name,         column3.name)
        self.assertEqual(funcfield.verbose_name, column3.title)
        self.assertEqual(3,                      column3.order)
        self.assertEqual(RFT_FUNCTION,           column3.type)
        self.assertFalse(column3.selected)
        self.assertIsNone(column3.sub_report)

    def test_edition__aggregate_rfield(self):
        "Aggregate on regular fields."
        user = self.login_as_root_and_get()

        report = Report.objects.create(name='Secret report', user=user, ct=self.ct_orga)
        f_name = 'name'
        aggr_id = 'capital__min'
        response = self.client.post(
            self._build_edit_fields_url(report),
            data={
                'columns': f'regular_field-{f_name},'
                           f'regular_aggregate-{aggr_id}',
            },
        )
        self.assertNoFormError(response)

        columns = report.columns
        self.assertEqual(2, len(columns))

        self.assertEqual(f_name, columns[0].name)

        column = columns[1]
        self.assertEqual(aggr_id,                            column.name)
        self.assertEqual(f"{_('Minimum')} - {_('Capital')}", column.title)
        self.assertEqual(2,                                  column.order)
        self.assertEqual(RFT_AGG_FIELD,                      column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)

    def test_edition__related_entity(self):
        user = self.login_as_root_and_get()

        report = Report.objects.create(
            name='Folder report', user=user, ct=self.ct_folder,
        )

        f_name = 'title'
        rel_name = 'fakereportsdocument'
        response = self.client.post(
            self._build_edit_fields_url(report),
            data={
                'columns': f'regular_field-{f_name},'
                           f'related-{rel_name}',
            },
        )
        self.assertNoFormError(response)

        columns = report.columns
        self.assertEqual(2, len(columns))

        self.assertEqual(f_name, columns[0].name)

        column = columns[1]
        self.assertEqual(rel_name,      column.name)
        self.assertEqual('Test (reports) Document', column.title)
        self.assertEqual(2,             column.order)
        self.assertEqual(RFT_RELATED,   column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)

    def test_edition__sub_report(self):
        "Edit field with sub-report."
        user = self.login_as_root_and_get()

        create_report = partial(Report.objects.create, user=user)
        report_orga    = create_report(name='Report on Organisations', ct=self.ct_orga)
        report_contact = create_report(name='Report on Contacts',      ct=self.ct_contact)
        report_img     = create_report(name='Report on Images',        ct=self.ct_image)

        # TODO: we need helpers: Field.create_4_field(), Field.create_4_relation() etc...
        create_field = partial(Field.objects.create, report=report_orga)
        create_field(
            name=FAKE_REL_OBJ_EMPLOYED_BY, type=RFT_RELATION, order=1,
            selected=True, sub_report=report_contact,
        )
        create_field(name='name', type=RFT_FIELD, order=2)
        create_field(name='image', type=RFT_FIELD, order=3, selected=False, sub_report=report_img)

        response = self.client.post(
            self._build_edit_fields_url(report_orga),
            data={
                'columns': f'regular_field-name,'
                           f'relation-{FAKE_REL_OBJ_EMPLOYED_BY},'
                           f'regular_field-description,'
                           f'regular_field-image',  # TODO: and with image__name ???
            },
        )
        self.assertNoFormError(response)

        columns = report_orga.columns
        self.assertEqual(4, len(columns))

        column1 = columns[0]
        self.assertEqual('name',    column1.name)
        self.assertEqual(RFT_FIELD, column1.type)
        self.assertIsNone(column1.sub_report)

        column2 = columns[1]
        self.assertEqual(FAKE_REL_OBJ_EMPLOYED_BY, column2.name)
        self.assertEqual(RFT_RELATION,             column2.type)
        self.assertEqual(report_contact,           column2.sub_report)
        self.assertTrue(column2.selected)

        self.assertEqual('description', columns[2].name)

        column4 = columns[3]
        self.assertEqual('image',    column4.name)
        self.assertEqual(RFT_FIELD,  column4.type)
        self.assertEqual(report_img, column4.sub_report)
        self.assertFalse(column4.selected)

    def test_edition__fields_config(self):
        "With FieldsConfig."
        user = self.login_as_root_and_get()

        valid_fname = 'last_name'
        hidden_fname1 = 'phone'
        hidden_fname2 = 'birthday'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        report = self._create_simple_contacts_report(user=user, name='Report #1')
        Field.objects.create(report=report, name=hidden_fname2, type=RFT_FIELD, order=2)

        url = self._build_edit_fields_url(report)
        response1 = self.assertPOST200(
            url,
            data={
                'columns': f'regular_field-{hidden_fname1}',
            },
        )
        self.assertFormError(
            response1.context['form'],
            field='columns',
            errors=_('This value is invalid: %(value)s') % {'value': hidden_fname1},
        )

        # ---
        response2 = self.client.post(
            url,
            data={
                'columns': f'regular_field-{valid_fname},'
                           f'regular_field-{hidden_fname2}',
            },
        )
        self.assertNoFormError(response2)

        columns = self.refresh(report).columns
        self.assertEqual(2, len(columns))
        self.assertEqual(valid_fname,   columns[0].name)
        self.assertEqual(hidden_fname2, columns[1].name)

    def test_edition__fk_deep(self):
        "FK with <depth=2>."
        user = self.login_as_root_and_get()

        report = Report.objects.create(name='Docs report', user=user, ct=FakeCoreDocument)

        fname = 'linked_folder__category'
        response = self.client.post(
            self._build_edit_fields_url(report),
            data={
                'columns': f'regular_field-title,'
                           f'regular_field-{fname}',
            },
        )
        self.assertNoFormError(response)

        columns = report.columns
        self.assertEqual(2, len(columns))

        column = columns[1]
        self.assertEqual(fname, column.name)
        self.assertEqual(RFT_FIELD, column.type)

    def test_edition__m2m_deep(self):
        "M2M with <depth=2>."
        user = self.login_as_root_and_get()

        report = Report.objects.create(
            name='Contact report', user=user, ct=self.ct_contact,
        )

        fname = 'image__categories'
        response = self.client.post(
            self._build_edit_fields_url(report),
            data={
                'columns': f'regular_field-last_name,'
                           f'regular_field-{fname}',
            },
        )
        self.assertNoFormError(response)

        columns = report.columns
        self.assertEqual(2, len(columns))

        column = columns[1]
        self.assertEqual(fname, column.name)
        self.assertEqual(RFT_FIELD, column.type)

    def test_edition__regular_user(self):
        user = self.login_as_standard(allowed_apps=['reports'])
        self.add_credentials(user.role, own=['VIEW', 'CHANGE'])

        report = Report.objects.create(name='Contact report', user=user, ct=self.ct_contact)
        self.assertGET200(self._build_edit_fields_url(report))

    def test_edition__regular_user__edition_perms(self):
        "Edition permission on Report are needed."
        user = self.login_as_standard(allowed_apps=['reports'])
        self.add_credentials(user.role, own=['VIEW'])  # 'CHANGE'

        report = Report.objects.create(name='Contact report', user=user, ct=self.ct_contact)
        self.assertGET403(self._build_edit_fields_url(report))

    def test_edition__errors__too_deep(self):
        user = self.login_as_root_and_get()

        report = self._create_simple_contacts_report(user=user)
        fname = 'image__categories__name'
        response = self.assertPOST200(
            self._build_edit_fields_url(report),
            data={'columns': f'regular_field-{fname}'},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='columns',
            errors=_('This value is invalid: %(value)s') % {'value': fname},
        )

    def test_edition__errors__no_entity(self):
        "No entity at depth=1."
        user = self.login_as_root_and_get()
        report = Report.objects.create(user=user, name='Report on docs', ct=FakeReportsDocument)

        fname = 'linked_folder__parent'
        response = self.assertPOST200(
            self._build_edit_fields_url(report),
            data={'columns': f'regular_field-{fname}'},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='columns',
            errors=_('This value is invalid: %(value)s') % {'value': fname},
        )

    def test_link_report__regular_field(self):
        "RFT_FIELD (FK) field."
        user = self.login_as_root_and_get()

        contact_report = Report.objects.create(
            user=user, name='Report on contacts', ct=self.ct_contact,
        )

        create_field = partial(
            Field.objects.create,
            report=contact_report,
            selected=False, sub_report=None,
            type=RFT_FIELD,
        )
        str_field    = create_field(name='last_name',             order=1)
        fk_field     = create_field(name='sector__title',         order=2)
        fk_img_field = create_field(name='image__name',           order=3)
        func_field   = create_field(name='get_pretty_properties', order=4, type=RFT_FUNCTION)

        self.assertIsNone(func_field.hand.get_linkable_ctypes())
        self.assertGET409(self._build_link_report_url(func_field))  # Not a RFT_FIELD Field

        self.assertIsNone(str_field.hand.get_linkable_ctypes())
        self.assertGET409(self._build_link_report_url(str_field))  # Not a FK field

        self.assertIsNone(fk_field.hand.get_linkable_ctypes())
        self.assertGET409(self._build_link_report_url(fk_field))  # Not a FK to a CremeEntity

        self.assertListEqual([self.ct_image], [*fk_img_field.hand.get_linkable_ctypes()])

        img_report = self._create_image_report(user=user)
        url = self._build_link_report_url(fk_img_field)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('Link of the column «{object}»').format(object=fk_img_field),
            context.get('title'),
        )
        self.assertEqual(_('Link'), context.get('submit_label'))

        # ---
        self.assertNoFormError(self.client.post(url, data={'report': img_report.id}))

        fk_img_field = self.refresh(fk_img_field)
        self.assertEqual(img_report, fk_img_field.sub_report)
        self.assertTrue(fk_img_field.selected)

        # Unlink ---------------------------------------------------------------
        fk_img_field.selected = True
        fk_img_field.save()
        url = reverse('reports__unlink_report')
        self.assertGET405(url)
        self.assertPOST409(url, data={'field_id': str_field.id})
        self.assertPOST200(url, data={'field_id': fk_img_field.id})

        fk_img_field = self.refresh(fk_img_field)
        self.assertIsNone(fk_img_field.sub_report)
        self.assertFalse(fk_img_field.selected)

    def test_link_report__regular_user(self):
        user = self.login_as_standard(allowed_apps=['reports'])
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        report = Report.objects.create(user=user, name='Report', ct=self.ct_contact)

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        create_field(name='last_name', order=1)
        fk_img_field = create_field(name='image__name', order=2)
        self.assertGET200(self._build_link_report_url(fk_img_field))

    def test_link_report__regular_user__link_perms(self):
        user = self.login_as_standard(allowed_apps=['reports'])
        self.add_credentials(user.role, own=['VIEW'])  # 'LINK'

        report = Report.objects.create(user=user, name='Report', ct=self.ct_contact)

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        create_field(name='last_name', order=1)
        fk_img_field = create_field(name='image__name', order=2)
        self.assertGET403(self._build_link_report_url(fk_img_field))

    def test_link_report__relation__ctype_constraint(self):
        "RelationType has got constraints on ContentType."
        user = self.login_as_root_and_get()

        contact_report = Report.objects.create(
            user=user, name='Report on contacts', ct=self.ct_contact,
        )

        create_field = partial(
            Field.objects.create,
            report=contact_report,
            selected=False, sub_report=None,
        )
        reg_rfield = create_field(name='last_name',              type=RFT_FIELD,    order=1)
        rel_rfield = create_field(name=FAKE_REL_SUB_EMPLOYED_BY, type=RFT_RELATION, order=2)

        self.assertGET409(self._build_link_report_url(reg_rfield))  # Not a RFT_RELATION Field

        # ---
        url = self._build_link_report_url(rel_rfield)
        self.assertGET200(url)

        # Incompatible CT
        img_report = self._create_image_report(user=user)
        response3 = self.assertPOST200(url, data={'report': img_report.id})
        self.assertFormError(
            response3.context['form'],
            field='report',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': img_report},
        )

        # ---
        orga_report = self._build_orga_report(user=user)
        self.assertNoFormError(self.client.post(url, data={'report': orga_report.id}))
        self.assertEqual(orga_report, self.refresh(rel_rfield).sub_report)

    def test_link_report__relation__no_constraint(self):
        "RelationType hasn't any constraint on ContentType."
        user = self.login_as_root_and_get()

        contact_report = Report.objects.create(
            user=user, ct=self.ct_contact, name='Report on contacts',
        )
        rtype = RelationType.objects.builder(
            id='reports-subject_obeys', predicate='obeys to',
        ).symmetric(id='reports-object_commands', predicate='commands').get_or_create()[0]

        create_field = partial(
            Field.objects.create,
            report=contact_report,
            selected=False, sub_report=None,
        )
        create_field(name='last_name', type=RFT_FIELD, order=1)
        rel_rfield = create_field(name=rtype.id, type=RFT_RELATION, order=2)

        url = self._build_link_report_url(rel_rfield)
        img_report = self._create_image_report(user=user)
        self.assertNoFormError(self.client.post(url, data={'report': img_report.id}))
        self.assertEqual(img_report, self.refresh(rel_rfield).sub_report)

    def test_link_report__related(self):
        "RFT_RELATED field."
        user = self.login_as_root_and_get()

        folder_report = Report.objects.create(
            name='Report on folders', user=user, ct=self.ct_folder,
        )

        create_field = partial(Field.objects.create, report=folder_report)
        rfield1 = create_field(name='title',               type=RFT_FIELD,   order=1)
        rfield2 = create_field(name='fakereportsdocument', type=RFT_RELATED, order=2)

        self.assertGET409(self._build_link_report_url(rfield1))  # Not a RFT_RELATION Field

        doc_report = self._create_simple_documents_report(user=user)
        url = self._build_link_report_url(rfield2)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'report': doc_report.id}))
        self.assertEqual(doc_report, self.refresh(rfield2).sub_report)

    def test_link_report__cycle(self):
        "Cycle error."
        user = self.login_as_root_and_get()

        contact_report = Report.objects.create(
            user=user, ct=self.ct_contact, name='Report on contacts',
        )

        create_field = partial(
            Field.objects.create,
            report=contact_report,
            selected=False, sub_report=None, type=RFT_RELATION,
        )
        create_field(name='last_name', type=RFT_FIELD, order=1)
        rel_rfield = create_field(name=FAKE_REL_SUB_EMPLOYED_BY, order=2)

        orga_report = self._build_orga_report(user=user)
        create_field(
            report=orga_report, name=FAKE_REL_OBJ_EMPLOYED_BY, order=3,
            sub_report=contact_report,
        )

        url = self._build_link_report_url(rel_rfield)
        self.assertGET200(url)

        # ---
        response2 = self.assertPOST200(url, data={'report': orga_report.id})
        self.assertFormError(
            response2.context['form'],
            field='report',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': orga_report},
        )

        # Invalid field -> no 500 error
        rfield = create_field(name='invalid', type=RFT_FIELD, order=3)
        self.assertGET409(self._build_link_report_url(rfield))

    def test_link_report__selected(self):
        "selected=True if only one sub-report."
        user = self.login_as_root_and_get()

        img_report = self._create_image_report(user=user)
        contact_report = Report.objects.create(
            user=user, name='Report on contacts', ct=self.ct_contact,
        )

        create_field = partial(Field.objects.create, report=contact_report, type=RFT_FIELD)
        create_field(name='last_name', order=1)
        img_field  = create_field(name='image__name', order=2, sub_report=img_report)
        rel_rfield = create_field(name=FAKE_REL_SUB_EMPLOYED_BY, order=3, type=RFT_RELATION)

        orga_report = self._build_orga_report(user=user)
        self.assertNoFormError(self.client.post(
            self._build_link_report_url(rel_rfield),
            data={'report': orga_report.id},
        ))

        rel_rfield = self.refresh(rel_rfield)
        self.assertEqual(orga_report, rel_rfield.sub_report)
        self.assertFalse(rel_rfield.selected)

        # 'columns' property avoid several selected sub-reports
        img_field.selected = True
        img_field.save()

        rel_rfield.selected = True
        rel_rfield.save()
        self.assertEqual(
            1,
            sum(1 for f in self.refresh(contact_report).columns if f.selected),
        )

    def test_set_selected(self):
        user = self.login_as_root_and_get()

        img_report = self._create_image_report(user=user)
        orga_report = self._build_orga_report(user=user)

        contact_report = Report.objects.create(
            user=user, name='Report on contacts', ct=self.ct_contact,
        )

        create_field = partial(
            Field.objects.create,
            report=contact_report,
            selected=False, sub_report=None, type=RFT_FIELD,
        )
        reg_rfield = create_field(name='last_name',   order=1)
        fk_rfield  = create_field(name='image__name', order=2, sub_report=img_report)
        rel_rfield = create_field(
            name=FAKE_REL_SUB_EMPLOYED_BY, order=3,
            sub_report=orga_report, type=RFT_RELATION, selected=True,
        )

        url = reverse('reports__set_selected_field')
        self.assertGET405(url)

        data = {
            'field_id':  reg_rfield.id,
            'checked':   1,
        }
        self.assertPOST404(url, data=data)

        data['report_id'] = contact_report.id
        self.assertPOST409(url, data=data)

        data['field_id'] = fk_rfield.id
        self.assertPOST200(url, data=data)
        self.assertTrue(self.refresh(fk_rfield).selected)
        self.assertFalse(self.refresh(rel_rfield).selected)

        self.assertPOST200(url, data=data)
        self.assertTrue(self.refresh(fk_rfield).selected)
        self.assertFalse(self.refresh(rel_rfield).selected)

        self.assertPOST200(url, data={**data, 'checked': 0})
        self.assertFalse(self.refresh(fk_rfield).selected)
        self.assertFalse(self.refresh(rel_rfield).selected)

    def test_set_selected__missing_field(self):
        "Missing Field ID."
        user = self.login_as_root_and_get()

        contact_report = Report.objects.create(
            user=user, name='Report on contacts', ct=self.ct_contact,
        )
        self.assertPOST404(
            reverse('reports__set_selected_field'),
            data={
                'report_id': contact_report.id,
                # 'field_id':  fk_rfield.id,
                'checked':   1,
            },
        )

    def test_set_selected__other_report_s_field(self):
        "Field & report do not match."
        user = self.login_as_root_and_get()

        img_report = self._create_image_report(user=user)
        orga_report = self._build_orga_report(user=user)
        contact_report = Report.objects.create(
            user=user, name='Report on contacts', ct=self.ct_contact,
        )
        fk_rfield = Field.objects.create(
            report=contact_report, name='image__name',
            order=1, type=RFT_FIELD, sub_report=img_report,
        )

        self.assertPOST409(
            reverse('reports__set_selected_field'),
            data={
                'report_id': orga_report.id,
                'field_id':  fk_rfield.id,
                'checked':   1,
            },
        )
