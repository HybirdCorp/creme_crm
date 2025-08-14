from datetime import date, datetime
from decimal import Decimal
from functools import partial
from uuid import uuid4

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.encoding import smart_str
from django.utils.formats import get_format, number_format
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.utils.translation import override as override_language
from django.utils.translation import pgettext

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
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldInteger,
    EntityFilter,
    FakeContact,
)
from creme.creme_core.models import FakeDocument as FakeCoreDocument
from creme.creme_core.models import FakeEmailCampaign
from creme.creme_core.models import FakeFolder as FakeCoreFolder
from creme.creme_core.models import (
    FakeFolderCategory,
    FakeImage,
    FakeImageCategory,
    FakeInvoice,
    FakeLegalForm,
    FakeMailingList,
    FakeOrganisation,
    FakePosition,
    FieldsConfig,
    HeaderFilter,
    Relation,
    RelationType,
)
from creme.creme_core.tests.fake_constants import (
    FAKE_REL_OBJ_BILL_ISSUED,
    FAKE_REL_OBJ_EMPLOYED_BY,
    FAKE_REL_SUB_EMPLOYED_BY,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.xlrd_utils import XlrdReader

from ..actions import ExportReportAction
from ..bricks import ReportChartsBrick, ReportFieldsBrick
from ..constants import (
    EF_REPORTS,
    RFT_AGG_CUSTOM,
    RFT_AGG_FIELD,
    RFT_CUSTOM,
    RFT_FIELD,
    RFT_FUNCTION,
    RFT_RELATED,
    RFT_RELATION,
)
from ..forms.report import ReportExportPreviewFilterForm
from ..models import FakeReportsDocument, FakeReportsFolder, Field, Guild
from .base import BaseReportsTestCase, Report, skipIfCustomReport


@skipIfCustomReport
class ReportTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    def assertHeaders(self, names, report):
        self.assertEqual(names, [f.name for f in report.get_children_fields_flat()])

    def _build_contacts_n_images(self, user, other_user):
        create_img = FakeImage.objects.create
        self.ned_face  = create_img(name='Ned face',  user=other_user)
        self.aria_face = create_img(name='Aria face', user=user)

        create_contact = partial(FakeContact.objects.create, user=user)
        self.ned  = create_contact(first_name='Eddard', last_name='Stark', image=self.ned_face)
        self.robb = create_contact(first_name='Robb',   last_name='Stark', user=other_user)
        self.aria = create_contact(first_name='Aria',   last_name='Stark', image=self.aria_face)

        self.efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Starks', FakeContact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name',
                    values=[self.ned.last_name],
                ),
            ],
        )

    def _build_image_report(self, user):
        img_report = Report.objects.create(
            user=user, name='Report on images', ct=self.ct_image,
        )

        create_field = partial(
            Field.objects.create,
            report=img_report, selected=False, sub_report=None, type=RFT_FIELD,
        )
        create_field(name='name',        order=1)
        create_field(name='description', order=2)

        return img_report

    def _build_orga_report(self, user):
        orga_report = Report.objects.create(
            user=user, name='Report on organisations', ct=self.ct_orga,
        )

        create_field = partial(
            Field.objects.create, report=orga_report,
            selected=False, sub_report=None, type=RFT_FIELD,
        )
        create_field(name='name',              order=1)
        create_field(name='legal_form__title', order=2)

        return orga_report

    @staticmethod
    def _build_linkreport_url(rfield):
        return reverse('reports__link_report', args=(rfield.id,))

    @staticmethod
    def _build_export_url(report):
        return reverse('reports__export_report', args=(report.id,))

    @staticmethod
    def _build_preview_url(report):
        return reverse('reports__export_report_preview', args=(report.id,))

    def _create_cf_int(self):
        return CustomField.objects.create(
            content_type=self.ct_contact,
            name='Size (cm)',
            field_type=CustomField.INT,
        )

    def login_as_basic_user(self, **kwargs):
        user = self.login_as_standard(
            allowed_apps=('creme_core', 'reports'),
            **kwargs
        )
        self.add_credentials(user.role, own=['VIEW'])

        return user

    def test_columns(self):
        user = self.login_as_root_and_get()
        report = self._build_orga_report(user=user)
        report = self.refresh(report)

        with self.assertNumQueries(1):
            columns = report.columns

        self.assertIsList(columns, length=2)

        field = columns[0]
        self.assertIsInstance(field, Field)
        self.assertEqual('name',     field.name)
        self.assertEqual(_('Name'),  field.title)
        self.assertEqual(RFT_FIELD,  field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.sub_report)

        with self.assertNumQueries(0):
            f_report = field.report

        self.assertEqual(report, f_report)

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

    def test_createview01(self):
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

    def test_createview02(self):
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

    def test_createview__report_filter(self):
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

    def test_createview_error(self):
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

    def test_editview01(self):
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

    def test_editview__forbidden_filter(self):
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

    def test_editview__reset_filter(self):
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

    def test_editview__report_filter(self):
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
    def test_report_inneredit_filter(self):
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

    def test_report_inneredit_filter__private(self):
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

    def test_report_inneredit_filter__set_required(self):
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
    def test_report_inneredit_filter__report_filter(self):
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

    def test_report_bulkedit_filter01(self):
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

    def test_report_bulkedit_filter02(self):
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

    def test_report_bulkedit_filter03(self):
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

    def test_clone(self):
        user = self.login_as_root_and_get()
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Mihana family', FakeContact, is_custom=True,
        )
        report = Report.objects.create(
            user=user, name='Contact report', ct=FakeContact, filter=efilter,
        )

        create_field = partial(Field.objects.create, report=report)
        rfield1 = create_field(name='last_name',             order=1, type=RFT_FIELD)
        rfield2 = create_field(name='get_pretty_properties', order=2, type=RFT_FUNCTION)

        cloned_report = self.clone(report)
        self.assertIsInstance(cloned_report, Report)
        self.assertNotEqual(report.id, cloned_report.id)
        self.assertEqual(report.name,   cloned_report.name)
        self.assertEqual(report.ct,     cloned_report.ct)
        self.assertEqual(report.filter, cloned_report.filter)

        rfields = cloned_report.fields.all()
        self.assertEqual(2, len(rfields))

        def check_clone(source_field, cloned_field):
            self.assertNotEqual(source_field.id, cloned_field.id)
            self.assertEqual(source_field.name,       cloned_field.name)
            self.assertEqual(source_field.order,      cloned_field.order)
            self.assertEqual(source_field.type,       cloned_field.type)
            self.assertEqual(source_field.selected,   cloned_field.selected)
            self.assertEqual(source_field.sub_report, cloned_field.sub_report)

        check_clone(rfield1, rfields[0])
        check_clone(rfield2, rfields[1])

    # def test_clone__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #     efilter = EntityFilter.objects.smart_update_or_create(
    #         'test-filter', 'Mihana family', FakeContact, is_custom=True,
    #     )
    #     report = Report.objects.create(
    #         user=user, name='Contact report', ct=FakeContact, filter=efilter,
    #     )
    #
    #     create_field = partial(Field.objects.create, report=report)
    #     rfield1 = create_field(name='last_name',             order=1, type=RFT_FIELD)
    #     rfield2 = create_field(name='get_pretty_properties', order=2, type=RFT_FUNCTION)
    #
    #     cloned_report = report.clone()
    #     self.assertIsInstance(cloned_report, Report)
    #     self.assertNotEqual(report.id, cloned_report.id)
    #     self.assertEqual(report.name,   cloned_report.name)
    #     self.assertEqual(report.ct,     cloned_report.ct)
    #     self.assertEqual(report.filter, cloned_report.filter)
    #
    #     rfields = cloned_report.fields.all()
    #     self.assertEqual(2, len(rfields))
    #
    #     def check_clone(source_field, cloned_field):
    #         self.assertNotEqual(source_field.id, cloned_field.id)
    #         self.assertEqual(source_field.name,       cloned_field.name)
    #         self.assertEqual(source_field.order,      cloned_field.order)
    #         self.assertEqual(source_field.type,       cloned_field.type)
    #         self.assertEqual(source_field.selected,   cloned_field.selected)
    #         self.assertEqual(source_field.sub_report, cloned_field.sub_report)
    #
    #     check_clone(rfield1, rfields[0])
    #     check_clone(rfield2, rfields[1])

    def test_delete_efilter(self):
        "The filter should not be deleted."
        user = self.login_as_root_and_get()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Mihana family', FakeContact, is_custom=True,
        )
        report = self._create_simple_contacts_report(
            user=user, name='My awesome report', efilter=efilter,
        )

        url = reverse('creme_core__delete_efilter', args=(efilter.id,))
        self.assertPOST409(url, follow=True)
        self.assertStillExists(efilter)
        self.assertStillExists(report)

        # AJAX version
        self.assertPOST409(
            url, follow=True, headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        self.assertStillExists(efilter)
        self.assertStillExists(report)

    def test_preview01(self):
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

    def test_preview02(self):
        "Empty: no contact."
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(user=user, name='My report')

        response = self.assertGET200(self._build_preview_url(report))
        self.assertTemplateUsed(response, 'reports/preview_report.html')
        self.assertContains(
            response,
            _('You can see no «{model}»').format(model='Test Contact'),
        )

    def test_preview03(self):
        "Empty: no allowed contact."
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

    def test_preview04(self):
        "Empty: no contact after date filtering."
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

    def test_preview05(self):
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

    def test_preview06(self):
        "Hidden fields."
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

    def test_preview07(self):
        "Filter on sub-field."
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

    def test_report_reorder_field01(self):
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

    def test_report_reorder_field02(self):
        "Report & Field do not match."
        user = self.login_as_root_and_get()

        report1 = self._create_simple_contacts_report(user=user, name='Hill')
        report2 = self._create_simple_contacts_report(user=user, name='Spencer')

        rfield = self.get_field_or_fail(report1, 'last_name')
        self.assertPOST404(
            reverse('reports__reorder_field', args=(report2.id, rfield.id,)),
            data={'target': 1},
        )

    def test_export_filter_form_customrange(self):
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

    def test_export_filter_not_superuser01(self):
        user = self.login_as_standard(allowed_apps=['reports'])
        self.add_credentials(user.role, all=['VIEW'])

        report = Report.objects.create(name='Report', user=user, ct=self.ct_orga)
        self.assertGET200(reverse('reports__export_report_filter', args=(report.id,)))

    def test_export_filter_not_superuser02(self):
        "VIEW permission."
        user = self.login_as_standard(allowed_apps=['reports'])

        report = Report.objects.create(name='Report', user=user, ct=self.ct_orga)
        self.assertGET403(reverse('reports__export_report_filter', args=(report.id,)))

    def test_export_filter_form_missing_doctype(self):
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

    def test_export_filter_form_missing_customrange(self):
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

    def test_export_filter_form_invalid_filter(self):
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

    def test_export_filter_form_no_datefield(self):
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

    def test_report_csv__empty(self):
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

    def test_report_csv__no_filter(self):
        user = self.login_as_root_and_get()

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

    def test_report_csv__date_filter__custom(self):
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

    def test_report_csv__date_filter__registered(self):
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

    def test_report_csv__date_filter__errors(self):
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

    def test_report_csv__fields_config(self):
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

    def test_report_csv__fields_config__subfield(self):
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

    def test_report_csv__disabled_rtype(self):
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

    def test_report__date_filter__subfield(self):
        "Date filter on sub-field."
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

    def test_report_xls(self):
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

    @staticmethod
    def _build_editfields_url(report):
        return reverse('reports__edit_fields', args=(report.id,))

    def test_edit_fields01(self):
        user = self.login_as_root_and_get()

        report = self._create_simple_contacts_report(user=user, name='Report #1')
        url = self._build_editfields_url(report)
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

    def test_edit_fields02(self):
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
            self._build_editfields_url(report),
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

    def test_edit_fields03(self):
        "Other types: relationships, function fields."
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(user=user, name='My beloved Report')
        f_name = 'user__username'

        rtype_id = FAKE_REL_SUB_EMPLOYED_BY
        rtype = self.get_object_or_fail(RelationType, pk=rtype_id)

        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')
        self.assertIsNotNone(funcfield)

        response = self.client.post(
            self._build_editfields_url(report),
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

    def test_edit_fields04(self):
        "Aggregate on regular fields."
        user = self.login_as_root_and_get()

        report = Report.objects.create(name='Secret report', user=user, ct=self.ct_orga)
        f_name = 'name'
        aggr_id = 'capital__min'
        response = self.client.post(
            self._build_editfields_url(report),
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

    def test_edit_fields05(self):
        "Related entity."
        user = self.login_as_root_and_get()

        report = Report.objects.create(
            name='Folder report', user=user, ct=self.ct_folder,
        )

        f_name = 'title'
        rel_name = 'fakereportsdocument'
        response = self.client.post(
            self._build_editfields_url(report),
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

    def test_edit_fields06(self):
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
            self._build_editfields_url(report_orga),
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

    def test_edit_fields07(self):
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

        url = self._build_editfields_url(report)
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

    def test_edit_fields08(self):
        "FK with <depth=2>."
        user = self.login_as_root_and_get()

        report = Report.objects.create(name='Docs report', user=user, ct=FakeCoreDocument)

        fname = 'linked_folder__category'
        response = self.client.post(
            self._build_editfields_url(report),
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

    def test_edit_fields09(self):
        "M2M with <depth=2>."
        user = self.login_as_root_and_get()

        report = Report.objects.create(
            name='Contact report', user=user, ct=self.ct_contact,
        )

        fname = 'image__categories'
        response = self.client.post(
            self._build_editfields_url(report),
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

    def test_edit_fields_not_super_user01(self):
        user = self.login_as_standard(allowed_apps=['reports'])
        self.add_credentials(user.role, own=['VIEW', 'CHANGE'])

        report = Report.objects.create(name='Contact report', user=user, ct=self.ct_contact)
        self.assertGET200(self._build_editfields_url(report))

    def test_edit_fields_not_super_user02(self):
        "Edition permission on Report are needed."
        user = self.login_as_standard(allowed_apps=['reports'])
        self.add_credentials(user.role, own=['VIEW'])  # 'CHANGE'

        report = Report.objects.create(name='Contact report', user=user, ct=self.ct_contact)
        self.assertGET403(self._build_editfields_url(report))

    def test_edit_fields_errors01(self):
        user = self.login_as_root_and_get()

        report = self._create_simple_contacts_report(user=user)
        fname = 'image__categories__name'
        response = self.assertPOST200(
            self._build_editfields_url(report),
            data={'columns': f'regular_field-{fname}'},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='columns',
            errors=_('This value is invalid: %(value)s') % {'value': fname},
        )

    def test_edit_fields_errors02(self):
        user = self.login_as_root_and_get()
        report = Report.objects.create(user=user, name='Report on docs', ct=FakeReportsDocument)

        fname = 'linked_folder__parent'
        response = self.assertPOST200(
            self._build_editfields_url(report),
            data={'columns': f'regular_field-{fname}'},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='columns',
            errors=_('This value is invalid: %(value)s') % {'value': fname},
        )

    def test_invalid_hands01(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(user=user)

        rfield = Field.objects.create(
            report=report, type=RFT_FIELD, order=2,
            name='image__categories__name',
        )
        self.assertIsNone(rfield.hand)
        self.assertDoesNotExist(rfield)

    def test_invalid_hands02(self):
        user = self.login_as_root_and_get()
        report = Report.objects.create(
            user=user, name='Report on docs', ct=FakeReportsDocument,
        )

        rfield = Field.objects.create(
            name='linked_folder__parent',
            report=report, type=RFT_FIELD, order=2,
        )
        self.assertIsNone(rfield.hand)
        self.assertDoesNotExist(rfield)

    def test_link_report_regular(self):
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
        self.assertGET409(self._build_linkreport_url(func_field))  # Not a RFT_FIELD Field

        self.assertIsNone(str_field.hand.get_linkable_ctypes())
        self.assertGET409(self._build_linkreport_url(str_field))  # Not a FK field

        self.assertIsNone(fk_field.hand.get_linkable_ctypes())
        self.assertGET409(self._build_linkreport_url(fk_field))  # Not a FK to a CremeEntity

        self.assertListEqual([self.ct_image], [*fk_img_field.hand.get_linkable_ctypes()])

        img_report = self._build_image_report(user=user)
        url = self._build_linkreport_url(fk_img_field)
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

    def test_link_report_not_superuser01(self):
        user = self.login_as_standard(allowed_apps=['reports'])
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        report = Report.objects.create(user=user, name='Report', ct=self.ct_contact)

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        create_field(name='last_name', order=1)
        fk_img_field = create_field(name='image__name', order=2)
        self.assertGET200(self._build_linkreport_url(fk_img_field))

    def test_link_report_not_superuser02(self):
        "LINK permission."
        user = self.login_as_standard(allowed_apps=['reports'])
        self.add_credentials(user.role, own=['VIEW'])  # 'LINK'

        report = Report.objects.create(user=user, name='Report', ct=self.ct_contact)

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        create_field(name='last_name', order=1)
        fk_img_field = create_field(name='image__name', order=2)
        self.assertGET403(self._build_linkreport_url(fk_img_field))

    def test_link_report_relation01(self):
        "RelationType has got constraints on CT."
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

        self.assertGET409(self._build_linkreport_url(reg_rfield))  # Not a RFT_RELATION Field

        # ---
        url = self._build_linkreport_url(rel_rfield)
        self.assertGET200(url)

        # Incompatible CT
        img_report = self._build_image_report(user=user)
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

    def test_link_report_relation02(self):
        "RelationType hasn't any constraint on CT."
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

        url = self._build_linkreport_url(rel_rfield)
        img_report = self._build_image_report(user=user)
        self.assertNoFormError(self.client.post(url, data={'report': img_report.id}))
        self.assertEqual(img_report, self.refresh(rel_rfield).sub_report)

    def test_link_report_related(self):
        "RFT_RELATED field."
        user = self.login_as_root_and_get()

        folder_report = Report.objects.create(
            name='Report on folders', user=user, ct=self.ct_folder,
        )

        create_field = partial(Field.objects.create, report=folder_report)
        rfield1 = create_field(name='title',               type=RFT_FIELD,   order=1)
        rfield2 = create_field(name='fakereportsdocument', type=RFT_RELATED, order=2)

        self.assertGET409(self._build_linkreport_url(rfield1))  # Not a RFT_RELATION Field

        doc_report = self._create_simple_documents_report(user=user)
        url = self._build_linkreport_url(rfield2)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'report': doc_report.id}))
        self.assertEqual(doc_report, self.refresh(rfield2).sub_report)

    def test_link_report_error(self):
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

        url = self._build_linkreport_url(rel_rfield)
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
        self.assertGET409(self._build_linkreport_url(rfield))

    def test_link_report_selected(self):
        "selected=True if only one sub-report."
        user = self.login_as_root_and_get()

        img_report = self._build_image_report(user=user)
        contact_report = Report.objects.create(
            user=user, name='Report on contacts', ct=self.ct_contact,
        )

        create_field = partial(Field.objects.create, report=contact_report, type=RFT_FIELD)
        create_field(name='last_name', order=1)
        img_field  = create_field(name='image__name', order=2, sub_report=img_report)
        rel_rfield = create_field(name=FAKE_REL_SUB_EMPLOYED_BY, order=3, type=RFT_RELATION)

        orga_report = self._build_orga_report(user=user)
        self.assertNoFormError(self.client.post(
            self._build_linkreport_url(rel_rfield),
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

    def test_set_selected01(self):
        user = self.login_as_root_and_get()

        img_report = self._build_image_report(user=user)
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

    def test_set_selected02(self):
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

    def test_set_selected03(self):
        "Field & report do not match."
        user = self.login_as_root_and_get()

        img_report = self._build_image_report(user=user)
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

    def _aux_test_fetch_persons(
            self,
            user,
            create_contacts=True,
            create_relations=True,
            report_4_contact=True):
        if create_contacts:
            create_contact = partial(FakeContact.objects.create, user=user)
            self.ned    = create_contact(first_name='Eddard', last_name='Stark')
            self.robb   = create_contact(first_name='Robb',   last_name='Stark')
            self.tyrion = create_contact(first_name='Tyrion', last_name='Lannister')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        self.starks     = create_orga(name='House Stark')
        self.lannisters = create_orga(name='House Lannister')

        if create_contacts and create_relations:
            create_rel = partial(
                Relation.objects.create,
                type_id=FAKE_REL_OBJ_EMPLOYED_BY, user=user,
            )
            create_rel(subject_entity=self.starks, object_entity=self.ned)
            create_rel(subject_entity=self.starks, object_entity=self.robb)
            create_rel(subject_entity=self.lannisters, object_entity=self.tyrion)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Houses', FakeOrganisation, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.ISTARTSWITH,
                    field_name='name', values=['House '],
                ),
            ],
        )

        create_report = partial(Report.objects.create, user=user, filter=None)
        create_field = partial(
            Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD,
        )

        if report_4_contact:
            self.report_contact = report = create_report(
                name='Report on Contacts', ct=self.ct_contact,
            )

            create_field(report=report, name='last_name',  order=1)
            create_field(report=report, name='first_name', order=2)

        self.report_orga = create_report(
            name='Report on Organisations', ct=self.ct_orga, filter=efilter,
        )
        create_field(report=self.report_orga, name='name', order=1)

    def test_fetch_field_01(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        for i in range(5):
            create_contact(last_name=f'Mister {i}')

        create_contact(last_name='Mister X', is_deleted=True)

        report = self._create_simple_contacts_report(user=user, name='Contacts report')
        self.assertListEqual(
            [
                [ln]
                for ln in FakeContact.objects
                                     .filter(is_deleted=False)
                                     .values_list('last_name', flat=True)
            ],
            report.fetch_all_lines(),
        )

    # @override_settings(USE_L10N=True)
    @override_language('en')
    def test_fetch_field_02(self):
        "FK, date, filter, invalid one."
        user = self.login_as_root_and_get()

        self._aux_test_fetch_persons(
            user=user, report_4_contact=False, create_contacts=False, create_relations=False,
        )

        report = self.report_orga
        create_field = partial(
            Field.objects.create,
            report=report, selected=False, sub_report=None, type=RFT_FIELD,
        )
        create_field(name='user__username',    order=2)
        create_field(name='legal_form__title', order=3)
        create_field(name='creation_date',     order=4)
        create_field(name='invalid',           order=5)
        create_field(name='user__invalid',     order=6)
        create_field(name='dontcare',          order=7, type=1000)

        self.assertEqual(4, len(report.columns))

        starks = self.starks
        starks.legal_form = lform = FakeLegalForm.objects.get_or_create(title='Hord')[0]
        starks.creation_date = date(year=2013, month=9, day=24)
        starks.save()

        username = user.username
        self.assertListEqual(
            [
                [
                    self.lannisters.name,
                    username,
                    '',
                    '',
                ],
                [
                    starks.name,
                    username,
                    lform.title,
                    starks.creation_date.strftime('%Y-%m-%d'),
                ],
            ],
            report.fetch_all_lines(),
        )

    def test_fetch_field_03(self):
        "View credentials."
        user = self.login_as_basic_user()
        other_user = self.get_root_user()

        self._aux_test_fetch_persons(
            user=user, report_4_contact=False, create_contacts=False, create_relations=False,
        )

        Field.objects.create(
            report=self.report_orga, name='image__name',
            order=2, selected=False, sub_report=None, type=RFT_FIELD,
        )

        baratheons = FakeOrganisation.objects.create(user=other_user, name='House Baratheon')
        self.assertFalse(user.has_perm_to_view(baratheons))

        create_img     = FakeImage.objects.create
        starks_img     = create_img(name='Stark emblem',     user=user)
        lannisters_img = create_img(name='Lannister emblem', user=other_user)
        self.assertTrue(user.has_perm_to_view(starks_img))
        self.assertFalse(user.has_perm_to_view(lannisters_img))

        self.starks.image = starks_img
        self.starks.save()

        self.lannisters.image = lannisters_img
        self.lannisters.save()

        fetch_all_lines = self.report_orga.fetch_all_lines
        lines = [
            [baratheons.name,      ''],
            [self.lannisters.name, lannisters_img.name],
            [self.starks.name,     starks_img.name],
        ]
        self.assertEqual(lines, fetch_all_lines())
        self.assertEqual(lines, fetch_all_lines(user=other_user))  # Superuser

        lines.pop(0)
        lines[0][1] = settings.HIDDEN_VALUE  # 'lannisters_img' not visible
        self.assertEqual(lines, fetch_all_lines(user=user))

    def _aux_test_fetch_documents(self, *, user, efilter=None, selected=True):
        create_field = partial(
            Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD,
        )

        self.folder_report = Report.objects.create(
            name='Folders report', user=user,
            ct=self.ct_folder,
            filter=efilter,
        )
        create_field(report=self.folder_report, name='title',       order=1)
        create_field(report=self.folder_report, name='description', order=2)

        self.doc_report = self._create_simple_documents_report(user=user)
        create_field(
            report=self.doc_report, name='linked_folder__title', order=3,
            sub_report=self.folder_report, selected=selected,
        )

        create_folder = partial(FakeReportsFolder.objects.create, user=user)
        self.folder1 = create_folder(title='Internal')
        self.folder2 = create_folder(title='External', description='Boring description')

        create_doc = partial(FakeReportsDocument.objects.create, user=user)
        self.doc1 = create_doc(title='Doc#1', linked_folder=self.folder1, description='Blablabla')
        self.doc2 = create_doc(title='Doc#2', linked_folder=self.folder2)

    def test_fetch_fk_01(self):
        "Sub report: no sub-filter."
        user = self.login_as_root_and_get()

        self._aux_test_fetch_documents(user=user)
        self.assertHeaders(['title', 'description', 'title', 'description'], self.doc_report)

        doc1 = self.doc1
        folder2 = self.folder2
        self.assertEqual(
            [
                [doc1.title,      doc1.description, self.folder1.title, ''],
                [self.doc2.title, '',               folder2.title,      folder2.description],
            ],
            self.doc_report.fetch_all_lines(),
        )

    def test_fetch_fk_02(self):
        "Sub report: sub-filter."
        user = self.login_as_root_and_get()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Internal folders', FakeReportsFolder,
            is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeReportsFolder,
                    operator=operators.ISTARTSWITH,
                    field_name='title', values=['Inter'],
                ),
            ],
        )

        self._aux_test_fetch_documents(user=user, efilter=efilter)

        doc1 = self.doc1
        self.assertListEqual(
            [
                [doc1.title,      doc1.description, self.folder1.title, ''],
                [self.doc2.title, '',               '',                 ''],
            ],
            self.doc_report.fetch_all_lines(),
        )

    def test_fetch_fk_03(self):
        "Sub report (flattened)."
        user = self.login_as_root_and_get()
        self._aux_test_fetch_documents(user=user, selected=False)

        doc1 = self.doc1
        folder2 = self.folder2
        fmt = f"{_('Title')}: %s/{_('Description')}: %s"
        self.assertListEqual(
            [
                [doc1.title,      doc1.description, fmt % (self.folder1.title, '')],
                [self.doc2.title, '',               fmt % (folder2.title, folder2.description)],
            ],
            self.doc_report.fetch_all_lines(),
        )

    def test_fetch_fk_04(self):
        "Not Entity, no (sub) attribute."
        user = self.login_as_root_and_get()

        self._aux_test_fetch_persons(
            user=user, report_4_contact=False, create_contacts=False, create_relations=False,
        )
        starks = self.starks

        starks.legal_form = lform = FakeLegalForm.objects.get_or_create(title='Hord')[0]
        starks.save()

        report = self.report_orga

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        lf_field   = create_field(name='legal_form', order=2)
        user_field = create_field(name='user',       order=3)

        self.assertEqual(_('Legal form'), lf_field.title)
        self.assertEqual(_('Owner user'), user_field.title)

        user_str = str(user)
        self.assertListEqual(
            [
                [self.lannisters.name, '',          user_str],
                [starks.name,          lform.title, user_str],
            ],
            report.fetch_all_lines(),
        )

    def test_fetch_fk_05(self):
        "FK with depth=2."
        user = self.login_as_root_and_get()

        cat = FakeFolderCategory.objects.create(name='Maps')

        create_folder = partial(FakeCoreFolder.objects.create, user=user)
        folder1 = create_folder(title='Earth maps', category=cat)
        folder2 = create_folder(title="Faye's pix")

        create_doc = partial(FakeCoreDocument.objects.create, user=user)
        doc1 = create_doc(title='Japan map',   linked_folder=folder1)
        doc2 = create_doc(title='Mars city 1', linked_folder=folder2)

        report = Report.objects.create(
            name='Docs report', user=user, ct=FakeCoreDocument,
        )

        create_field = partial(
            Field.objects.create, report=report,
            selected=False, sub_report=None, type=RFT_FIELD,
        )
        create_field(name='title',                   order=1)
        create_field(name='linked_folder__category', order=2)

        self.assertListEqual(
            [
                [doc1.title, cat.name],
                [doc2.title, ''],
            ],
            report.fetch_all_lines(),
        )

    def test_fetch_fk_06(self):
        "M2M at <depth=2>."
        user = self.login_as_root_and_get()

        create_cat = FakeImageCategory.objects.create
        cat1 = create_cat(name='Selfie')
        cat2 = create_cat(name='Official')

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='Faye pix')
        img2 = create_img(name='Spike pix')
        img3 = create_img(name='Jet pix')

        img1.categories.set([cat1, cat2])
        img2.categories.set([cat1])

        description = 'Bebop member'
        create_contact = partial(
            FakeContact.objects.create,
            user=user, description=description,
        )
        faye  = create_contact(last_name='Valentine', image=img1)
        spike = create_contact(last_name='Spiegel',   image=img2)
        jet   = create_contact(last_name='Black',     image=img3)
        ed    = create_contact(last_name='Wong')

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Bebop member', FakeContact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='description',
                    values=[description],
                ),
            ],
        )

        report = Report.objects.create(
            name='Contact report', user=user, filter=efilter, ct=self.ct_contact,
        )

        create_field = partial(
            Field.objects.create, report=report,
            selected=False, sub_report=None, type=RFT_FIELD,
        )
        create_field(name='last_name',         order=1)
        create_field(name='image__categories', order=2)

        self.assertListEqual(
            [
                [jet.last_name,   ''],
                [spike.last_name, cat1.name],
                [faye.last_name,  f'{cat2.name}/{cat1.name}'],
                [ed.last_name,    ''],
            ],
            report.fetch_all_lines(),
        )

    def test_fetch_cf_01(self):
        "Custom fields."
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        ned  = create_contact(first_name='Eddard', last_name='Stark')
        robb = create_contact(first_name='Robb',   last_name='Stark')
        aria = create_contact(first_name='Aria',   last_name='Stark')

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Starks', FakeContact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.IEQUALS, values=[ned.last_name],
                ),
            ],
        )

        cf = self._create_cf_int()
        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=ned,  value=190)
        create_cfval(entity=aria, value=150)

        report = Report.objects.create(
            user=user,
            name='Contacts with CField',
            ct=FakeContact,
            filter=efilter,
        )

        create_field = partial(Field.objects.create, report=report)
        create_field(name='first_name', type=RFT_FIELD,  order=1)
        create_field(name=str(cf.uuid), type=RFT_CUSTOM, order=2)
        create_field(name=str(uuid4()), type=RFT_CUSTOM, order=3)

        report = self.refresh(report)
        self.assertEqual(2, len(report.columns))
        self.assertEqual(2, report.fields.count())
        self.assertListEqual(
            [
                [aria.first_name, '150'],
                [ned.first_name,  '190'],
                [robb.first_name, ''],
            ],
            report.fetch_all_lines(),
        )

    def test_fetch_cf_02(self):
        "In FK, credentials."
        user = self.login_as_basic_user()

        self._build_contacts_n_images(user=user, other_user=self.get_root_user())
        ned_face = self.ned_face
        aria_face = self.aria_face

        cf = CustomField.objects.create(
            content_type=self.ct_image,
            name='Popularity', field_type=CustomField.INT,
        )

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=ned_face,  value=190)
        create_cfval(entity=aria_face, value=150)

        create_report = partial(Report.objects.create, user=user, filter=None)
        report_img = create_report(name='Report on Images', ct=self.ct_image)

        create_field = partial(
            Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD,
        )
        create_field(report=report_img, name='name', order=1)
        create_field(report=report_img, name=str(cf.uuid), order=2, type=RFT_CUSTOM)

        report_contact = create_report(
            name='Report on Contacts', ct=self.ct_contact, filter=self.efilter,
        )
        create_field(report=report_contact, name='first_name',  order=1)
        create_field(
            report=report_contact, name='image__name', order=2,
            sub_report=report_img, selected=True,
        )

        lines = [
            [self.aria.first_name, aria_face.name, '150'],
            [self.ned.first_name,  ned_face.name,  '190'],
            [self.robb.first_name, '',             ''],
        ]
        self.assertListEqual(lines, report_contact.fetch_all_lines())

        lines.pop()  # 'robb' is not visible
        ned_line = lines[1]
        ned_line[1] = ned_line[2] = settings.HIDDEN_VALUE  # 'ned_face' is not visible
        self.assertEqual(lines, report_contact.fetch_all_lines(user=user))

    def test_fetch_m2m_01(self):
        "No sub report."
        user = self.login_as_root_and_get()

        report = Report.objects.create(
            user=user, name='Campaign Report', ct=FakeEmailCampaign,
        )
        create_field = partial(Field.objects.create, report=report)
        create_field(name='name',                type=RFT_FIELD, order=1)
        create_field(name='mailing_lists__name', type=RFT_FIELD, order=2)

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        camp1 = create_camp(name='Camp#1')
        camp2 = create_camp(name='Camp#2')

        create_ml = partial(FakeMailingList.objects.create, user=user)
        camp1.mailing_lists.set([create_ml(name='ML#1'), create_ml(name='ML#2')])
        camp2.mailing_lists.set([create_ml(name='ML#3')])

        self.assertHeaders(['name', 'mailing_lists__name'], report)
        self.assertListEqual(
            [
                [camp1.name, 'ML#1, ML#2'],
                [camp2.name, 'ML#3'],
            ],
            report.fetch_all_lines(),
        )

    def _aux_test_fetch_m2m(self):
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.create
        self.ptype1 = create_ptype(text='Important')
        self.ptype2 = create_ptype(text='Not important')

        self.report_camp = report_camp = Report.objects.create(
            user=user, name='Campaign Report', ct=FakeEmailCampaign,
        )
        create_field1 = partial(Field.objects.create, report=report_camp, type=RFT_FIELD)
        create_field1(name='name',                order=1)
        create_field1(name='mailing_lists__name', order=2)

        self.report_ml = report_ml = Report.objects.create(
            user=user,
            name='Campaign ML',
            ct=FakeMailingList,
        )
        create_field2 = partial(Field.objects.create, report=report_ml)
        create_field2(name='name',                  type=RFT_FIELD,    order=1)
        create_field2(name='get_pretty_properties', type=RFT_FUNCTION, order=2)

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        self.camp1 = create_camp(name='Camp#1')
        self.camp2 = create_camp(name='Camp#2')
        self.camp3 = create_camp(name='Camp#3')  # Empty one

        create_ml = partial(FakeMailingList.objects.create, user=user)
        self.ml1 = ml1 = create_ml(name='ML#1')
        self.ml2 = ml2 = create_ml(name='ML#2')
        self.ml3 = ml3 = create_ml(name='ML#3')

        self.camp1.mailing_lists.set([ml1, ml2])
        self.camp2.mailing_lists.set([ml3])

        create_prop = CremeProperty.objects.create
        create_prop(type=self.ptype1, creme_entity=ml1)
        create_prop(type=self.ptype2, creme_entity=ml2)

    def test_fetch_m2m_02(self):
        "Sub report (expanded)."
        self._aux_test_fetch_m2m()

        report_camp = self.report_camp
        report_ml = self.report_ml

        name1 = self.camp1.name
        name2 = self.camp2.name
        name3 = self.camp3.name

        ml1 = self.ml1
        ml2 = self.ml2
        ml3 = self.ml3

        ptype1 = self.ptype1
        ptype2 = self.ptype2

        self.assertHeaders(['name', 'mailing_lists__name'], report_camp)
        self.assertListEqual(
            [
                [name1, f'{ml1.name}, {ml2.name}'],
                [name2, ml3.name],
                [name3, ''],
            ],
            report_camp.fetch_all_lines(),
        )

        self.assertListEqual(
            [[ml1.name, ptype1.text], [ml2.name, ptype2.text], [ml3.name, '']],
            report_ml.fetch_all_lines(),
        )

        # Let's go for the sub-report
        rfield = report_camp.fields.get(name='mailing_lists__name')
        rfield.sub_report = report_ml
        rfield.selected = True
        rfield.save()

        self.assertListEqual(
            [ContentType.objects.get_for_model(FakeMailingList)],
            [*rfield.hand.get_linkable_ctypes()],
        )

        report_camp = self.refresh(report_camp)
        self.assertHeaders(['name', 'name', 'get_pretty_properties'], report_camp)
        self.assertListEqual(
            [
                [name1, ml1.name, ptype1.text],
                [name1, ml2.name, ptype2.text],
                [name2, ml3.name, ''],
                [name3, '',       ''],
            ],
            report_camp.fetch_all_lines(),
        )

    def test_fetch_m2m_03(self):
        "Sub report (not expanded)."
        self._aux_test_fetch_m2m()

        report_camp = self.report_camp

        # Let's go for the sub-report
        rfield = report_camp.fields.get(name='mailing_lists__name')
        rfield.sub_report = self.report_ml
        rfield.selected = False
        rfield.save()

        report_camp = self.refresh(report_camp)
        self.assertHeaders(['name', 'mailing_lists__name'], report_camp)

        fmt = f"{_('Name of the mailing list')}: %s/{_('Properties')}: %s"
        self.assertListEqual(
            [
                [
                    self.camp1.name,
                    '{}, {}'.format(
                        fmt % (self.ml1.name, self.ptype1.text),
                        fmt % (self.ml2.name, self.ptype2.text),
                    ),
                ],
                [self.camp2.name, fmt % (self.ml3.name, '')],
                [self.camp3.name, ''],
            ],
            report_camp.fetch_all_lines(),
        )

    def test_fetch_m2m_04(self):
        "Not CremeEntity model."
        user = self.login_as_root_and_get()

        report = self._build_image_report(user=user)

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        rfield1 = create_field(name='categories__name', order=3)
        rfield2 = create_field(name='categories',       order=4)

        self.assertIsNone(rfield1.hand.get_linkable_ctypes())
        self.assertIsNone(rfield2.hand.get_linkable_ctypes())

        self.assertEqual(f"{_('Categories')} - {_('Name')}", rfield1.title)
        self.assertEqual(_('Categories'),                    rfield2.title)

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='Img#1', description='Pretty picture')
        img2 = create_img(name='Img#2')

        create_cat = FakeImageCategory.objects.create
        cat1 = create_cat(name='Photo of contact')
        cat2 = create_cat(name='Photo of product')

        img1.categories.set([cat1, cat2])

        cats_str = f'{cat1.name}, {cat2.name}'
        self.assertListEqual(
            [
                [img1.name, img1.description, cats_str, cats_str],
                [img2.name, '',               '',       ''],
            ],
            report.fetch_all_lines(),
        )

    def test_fetch_m2m_05(self):
        "FK at <depth=2>."
        user = self.login_as_root_and_get()

        create_positon = FakePosition.objects.create
        leader    = create_positon(title='Leader')
        side_kick = create_positon(title='Side kick')

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(last_name='Merchants#1', position=leader)
        contact2 = create_contact(last_name='Merchants#2', position=side_kick)
        contact3 = create_contact(last_name='Merchants#3')
        contact4 = create_contact(last_name='Assassin', position=leader)

        create_guild = partial(Guild.objects.create, user=user)
        guild1 = create_guild(name='Guild of merchants')
        guild2 = create_guild(name='Guild of assassins')
        guild3 = create_guild(name='Guild of mercenaries')

        guild1.members.set([contact1, contact2, contact3])
        guild2.members.set([contact4])

        report = Report.objects.create(name='Guilds report', user=user, ct=Guild)

        create_field = partial(
            Field.objects.create,
            report=report, selected=False, sub_report=None, type=RFT_FIELD,
        )
        create_field(name='name',              order=1)
        create_field(name='members__position', order=2)

        self.assertListEqual(
            [
                [guild2.name, leader.title],
                [guild3.name, ''],
                [guild1.name, f'{leader.title}, {side_kick.title}, '],
            ],
            report.fetch_all_lines(),
        )

    def _aux_test_fetch_related(self, *, user, other_user,
                                select_doc_report=None, invalid_one=False):
        create_report = partial(Report.objects.create, user=user, filter=None)
        self.doc_report = (
            self._create_simple_documents_report(user=user)
            if select_doc_report is not None else
            None
        )
        self.folder_report = create_report(name='Report on folders', ct=self.ct_folder)

        create_field = partial(
            Field.objects.create,
            report=self.folder_report,
            type=RFT_FIELD,
        )
        create_field(name='title', order=1)
        create_field(
            name='fakereportsdocument', order=2,
            type=RFT_RELATED,
            sub_report=self.doc_report, selected=select_doc_report or False,
        )

        if invalid_one:
            create_field(name='invalid', order=3, type=RFT_RELATED)

        create_folder = partial(FakeReportsFolder.objects.create, user=user)
        self.folder1 = create_folder(title='External')
        self.folder2 = create_folder(title='Internal')

        create_doc = partial(FakeReportsDocument.objects.create, user=user)
        self.doc11 = create_doc(
            title='Doc#1-1', linked_folder=self.folder1, description='Boring !',
        )
        self.doc12 = create_doc(
            title='Doc#1-2', linked_folder=self.folder1, user=other_user,
        )
        self.doc21 = create_doc(title='Doc#2-1', linked_folder=self.folder2)

    def test_fetch_related_01(self):
        user = self.login_as_basic_user()

        self._aux_test_fetch_related(
            select_doc_report=None, invalid_one=True, user=user, other_user=self.get_root_user(),
        )

        report = self.refresh(self.folder_report)
        self.assertEqual(2, len(report.columns))

        doc11 = self.doc11
        doc12 = self.doc12
        fetch = report.fetch_all_lines
        lines = [
            [self.folder1.title, f'{doc11}, {doc12}'],
            [self.folder2.title, str(self.doc21)],
        ]
        self.assertEqual(lines, fetch())

        lines[0][1] = str(doc11)
        self.assertEqual(lines, fetch(user=user))

    def test_fetch_related_02(self):
        "Sub-report (expanded)."
        user = self.login_as_basic_user()

        self._aux_test_fetch_related(
            select_doc_report=True, user=user, other_user=self.get_root_user(),
        )
        folder3 = FakeReportsFolder.objects.create(user=user, title='Empty')

        folder1 = self.folder1
        doc11 = self.doc11
        # Beware: folders are ordered by title
        lines = [
            [folder3.title,      '',               ''],
            [folder1.title,      doc11.title,      doc11.description],
            [folder1.title,      self.doc12.title, ''],
            [self.folder2.title, self.doc21.title, ''],
        ]
        fetch = self.folder_report.fetch_all_lines
        self.assertEqual(lines, fetch())

        lines.pop(2)  # doc12
        self.assertEqual(lines, fetch(user=user))

    def test_fetch_related_03(self):
        "Sub-report (not expanded)."
        user = self.login_as_basic_user()

        self._aux_test_fetch_related(
            select_doc_report=False, user=user, other_user=self.get_root_user(),
        )
        folder3 = FakeReportsFolder.objects.create(user=user, title='Empty')

        folder1 = self.folder1
        doc11 = self.doc11
        fmt = f'{_("Title")}: %s/{_("Description")}: %s'
        doc11_str = fmt % (doc11.title, doc11.description)
        lines = [
            [folder3.title,      ''],
            [folder1.title,      doc11_str + ', ' + fmt % (self.doc12.title, '')],
            [self.folder2.title, fmt % (self.doc21.title, '')],
        ]
        fetch = self.folder_report.fetch_all_lines
        self.assertEqual(lines, fetch())

        lines[1][1] = doc11_str
        self.assertEqual(lines, fetch(user=user))

    def test_fetch_funcfield_01(self):
        user = self.login_as_root_and_get()

        self._aux_test_fetch_persons(
            user=user, report_4_contact=False, create_contacts=False, create_relations=False,
        )

        ptype = CremePropertyType.objects.create(text='I am not dead!')
        CremeProperty.objects.create(type=ptype, creme_entity=self.starks)

        report = self.report_orga
        create_field = partial(
            Field.objects.create,
            report=report,
            selected=False, sub_report=None, type=RFT_FUNCTION,
        )
        create_field(name='get_pretty_properties', order=2)
        create_field(name='invalid_funfield',      order=3)

        report = self.refresh(report)
        self.assertEqual(2, len(report.columns))  # Invalid column is deleted
        self.assertEqual(2, report.fields.count())
        self.assertListEqual(
            [
                [self.lannisters.name, ''],
                [self.starks.name,     ptype.text],
            ],
            report.fetch_all_lines(),
        )

    def test_fetch_funcfield_02(self):
        user = self.login_as_basic_user()

        self._build_contacts_n_images(user=user, other_user=self.get_root_user())
        ned_face = self.ned_face
        aria_face = self.aria_face

        self.assertFalse(user.has_perm_to_view(ned_face))
        self.assertTrue(user.has_perm_to_view(aria_face))

        create_report = partial(Report.objects.create, user=user, filter=None)
        report_img = create_report(name='Report on Images', ct=self.ct_image)

        create_field = partial(Field.objects.create, type=RFT_FIELD)
        create_field(report=report_img, name='name',                  order=1)
        create_field(report=report_img, name='get_pretty_properties', order=2, type=RFT_FUNCTION)

        report_contact = create_report(
            name='Report on Contacts', ct=self.ct_contact, filter=self.efilter,
        )
        create_field(report=report_contact, name='first_name',  order=1)
        create_field(
            report=report_contact, name='image__name', order=2,
            sub_report=report_img, selected=True,
        )

        ptype = CremePropertyType.objects.create(text='I am waiting the winter')

        create_prop = partial(CremeProperty.objects.create, type=ptype)
        create_prop(creme_entity=aria_face)
        create_prop(creme_entity=ned_face)

        lines = [
            [self.aria.first_name, aria_face.name, ptype.text],
            [self.ned.first_name,  ned_face.name,  ptype.text],
            [self.robb.first_name, '',             ''],
        ]
        self.assertEqual(lines, report_contact.fetch_all_lines())

        lines.pop()  # 'robb' is not visible
        ned_line = lines[1]
        ned_line[1] = ned_line[2] = settings.HIDDEN_VALUE  # 'ned_face' is not visible
        self.assertEqual(lines, report_contact.fetch_all_lines(user=user))

    def test_fetch_relation_01(self):
        "No sub-report."
        user = self.login_as_basic_user()

        self._aux_test_fetch_persons(user=user, report_4_contact=False)
        report = self.report_orga

        ned = self.ned
        ned.user = self.get_root_user()
        ned.save()

        create_field = partial(
            Field.objects.create, report=report,
            type=RFT_RELATION, selected=False, sub_report=None,
        )
        create_field(name=FAKE_REL_OBJ_EMPLOYED_BY, order=2)
        create_field(name='invalid',                order=3)

        report = self.refresh(report)
        self.assertEqual(2, len(report.columns))
        self.assertEqual(2, report.fields.count())

        fetch = self.report_orga.fetch_all_lines
        lines = [
            [self.lannisters.name, str(self.tyrion)],
            [self.starks.name,     f'{ned}, {self.robb}'],
        ]
        self.assertEqual(lines, fetch())

        lines[1][1] = str(self.robb)
        self.assertEqual(lines, fetch(user=user))

    def test_fetch_relation_02(self):
        "Sub-report (expanded)."
        user = self.login_as_basic_user()
        self._aux_test_fetch_persons(user=user)

        report = self.report_orga
        Field.objects.create(
            report=report, name=FAKE_REL_OBJ_EMPLOYED_BY, order=2,
            type=RFT_RELATION, selected=True, sub_report=self.report_contact,
        )

        self.assertHeaders(['name', 'last_name', 'first_name'], report)

        starks = self.starks
        ned = self.ned
        robb = self.robb
        tyrion = self.tyrion

        robb.user = self.get_root_user()
        robb.save()

        lines = [
            [self.lannisters.name, tyrion.last_name, tyrion.first_name],
            [starks.name,          ned.last_name,    ned.first_name],
            [starks.name,          robb.last_name,   robb.first_name],
        ]
        self.assertEqual(lines, report.fetch_all_lines())

        lines.pop()  # 'robb' line removed
        self.assertEqual(lines, report.fetch_all_lines(user=user))

    def test_fetch_relation_03(self):
        "Sub-report (not expanded)."
        user = self.login_as_basic_user()
        self._aux_test_fetch_persons(user=user)

        ptype = CremePropertyType.objects.create(text='Dwarf')
        CremeProperty.objects.create(type=ptype, creme_entity=self.tyrion)

        report_contact = self.report_contact

        create_field = partial(Field.objects.create, report=report_contact)
        create_field(name='get_pretty_properties', type=RFT_FUNCTION, order=3)
        create_field(
            name='image__name', type=RFT_FIELD, order=4,
            sub_report=self._build_image_report(user=user), selected=True,
        )

        report_orga = self.report_orga
        create_field(
            report=report_orga, name=FAKE_REL_OBJ_EMPLOYED_BY, order=2,
            type=RFT_RELATION, selected=False, sub_report=report_contact,
        )
        self.assertHeaders(['name', FAKE_REL_OBJ_EMPLOYED_BY], report_orga)

        ned = self.ned
        robb = self.robb
        tyrion = self.tyrion

        robb.user = self.get_root_user()
        robb.save()

        ned.image = img = FakeImage.objects.create(
            name='Ned pic', user=user, description='Ned Stark selfie',
        )
        ned.save()

        fmt = (
            f"{_('Last name')}: %s/{_('First name')}: %s/"
            f"{_('Properties')}: %s/{_('Photograph')}: %s"
        )

        ned_str = fmt % (
            ned.last_name,  ned.first_name, '',
            f"{_('Name')}: {img.name}/{_('Description')}: {img.description}",
        )
        lines = [
            [
                self.lannisters.name,
                fmt % (tyrion.last_name, tyrion.first_name, ptype.text, ''),
            ],
            [
                self.starks.name,
                ned_str + ', ' + fmt % (robb.last_name, robb.first_name, '', ''),
            ],
        ]
        self.assertEqual(lines, report_orga.fetch_all_lines())

        lines[1][1] = ned_str
        self.assertEqual(lines, report_orga.fetch_all_lines(user=user))

    def test_fetch_relation_04(self):
        "Sub-report (expanded) with a filter."
        user = self.login_as_root_and_get()
        self._aux_test_fetch_persons(user=user)
        tyrion = self.tyrion

        tyrion_face = FakeImage.objects.create(name='Tyrion face', user=user)
        tyrion.image = tyrion_face
        tyrion.save()

        ptype = CremePropertyType.objects.create(text='Is a dwarf')
        CremeProperty.objects.create(type=ptype, creme_entity=self.tyrion)

        dwarves_filter = EntityFilter.objects.smart_update_or_create(
            'test-filter_dwarves', 'Dwarves', FakeContact, is_custom=True,
            conditions=[
                condition_handler.PropertyConditionHandler.build_condition(
                    model=FakeContact, ptype=ptype, has=True,
                ),
            ],
        )

        report_contact = self.report_contact
        report_contact.filter = dwarves_filter
        report_contact.save()

        img_report = self._build_image_report(user=user)

        create_field = Field.objects.create
        create_field(
            report=report_contact, name='image__name', order=3,
            type=RFT_FIELD,
            sub_report=img_report, selected=True,
        )

        report = self.report_orga
        create_field(
            report=report, name=FAKE_REL_OBJ_EMPLOYED_BY, order=2,
            type=RFT_RELATION,
            sub_report=self.report_contact, selected=True,
        )

        self.assertListEqual(
            [
                [self.lannisters.name, tyrion.last_name, tyrion.first_name, tyrion_face.name, ''],
                [self.starks.name,     '',               '',                '',               ''],
            ],
            report.fetch_all_lines(),
        )

    def test_fetch_relation_05(self):
        "Several expanded sub-reports."
        user = self.login_as_root_and_get()
        self._aux_test_fetch_persons(user=user)

        tyrion = self.tyrion
        ned = self.ned
        robb = self.robb
        starks = self.starks

        report_orga = self.report_orga
        create_field = partial(Field.objects.create, type=RFT_RELATION)
        create_field(
            report=report_orga, name=FAKE_REL_OBJ_EMPLOYED_BY, order=2,
            sub_report=self.report_contact, selected=True,
        )

        folder = FakeReportsFolder.objects.create(user=user, title='Ned folder')

        create_doc = partial(FakeReportsDocument.objects.create, user=user)
        doc1 = create_doc(title='Sword',  linked_folder=folder, description='Blablabla')
        doc2 = create_doc(title='Helmet', linked_folder=folder)

        rtype = RelationType.objects.get(pk=REL_SUB_HAS)
        doc_report = self._create_simple_documents_report(user=user)
        create_field(
            report=self.report_contact, name=rtype.id, order=3,
            sub_report=doc_report, selected=True,
        )

        create_rel = partial(Relation.objects.create, type=rtype, user=user, subject_entity=ned)
        create_rel(object_entity=doc1)
        create_rel(object_entity=doc2)

        self.assertListEqual(
            [_('Name'), _('Last name'), _('First name'), _('Title'), _('Description')],
            [column.title for column in report_orga.get_children_fields_flat()],
        )
        self.assertListEqual(
            [
                [self.lannisters.name, tyrion.last_name, tyrion.first_name, '', ''],

                # Beware Documents are ordered by title
                [starks.name, ned.last_name, ned.first_name, doc2.title, ''],
                [starks.name, ned.last_name, ned.first_name, doc1.title, doc1.description],

                [starks.name, robb.last_name, robb.first_name, '', ''],
            ],
            report_orga.fetch_all_lines(),
        )

    def _aux_test_fetch_aggregate(self, invalid_ones=False):
        user = self.login_as_root_and_get()
        self._aux_test_fetch_persons(user=user, create_contacts=False, report_4_contact=False)

        # Should not be used in aggregate
        self.guild = FakeOrganisation.objects.create(
            name='Guild of merchants', user=user, capital=700,
        )

        create_cf = partial(CustomField.objects.create, content_type=self.ct_orga)
        self.cf = cf = create_cf(name='Gold', field_type=CustomField.INT)
        str_cf = create_cf(name='Motto', field_type=CustomField.STR)

        fmt = '{}__max'.format
        create_field = partial(Field.objects.create, report=self.report_orga)
        create_field(name='capital__sum', order=2, type=RFT_AGG_FIELD)
        create_field(name=fmt(cf.uuid),   order=3, type=RFT_AGG_CUSTOM)

        if invalid_ones:
            # Invalid CustomField id
            create_field(name=fmt(uuid4()), order=4, type=RFT_AGG_CUSTOM)
            # Invalid aggregation
            create_field(name='capital__invalid', order=5, type=RFT_AGG_FIELD)
            # Invalid field (unknown)
            create_field(name='invalid__sum', order=6, type=RFT_AGG_FIELD)
            # Invalid field (bad type)
            create_field(name='name__sum', order=7, type=RFT_AGG_FIELD)
            # Invalid CustomField (bad type)
            create_field(name=fmt(str_cf.uuid), order=8, type=RFT_AGG_CUSTOM)
            # Invalid string
            create_field(name=f'{cf.uuid}__additionalarg__max', order=9, type=RFT_AGG_CUSTOM)

    def test_fetch_aggregate_01(self):
        "Regular field, Custom field (valid & invalid ones)."
        self._aux_test_fetch_aggregate(invalid_ones=True)

        starks = self.starks
        starks.capital = 500
        starks.save()

        lannisters = self.lannisters
        lannisters.capital = 1000
        lannisters.save()

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=self.cf)
        create_cfval(entity=starks,     value=100)
        create_cfval(entity=lannisters, value=500)
        create_cfval(entity=self.guild, value=50)  # Should not be used

        report = self.refresh(self.report_orga)
        self.assertEqual(3, len(report.columns))

        self.assertListEqual(
            [
                [lannisters.name, '1500', '500'],
                [starks.name,     '1500', '500'],
            ],
            report.fetch_all_lines(),
        )

    def test_fetch_aggregate_02(self):
        "Regular field, Custom field (valid & invalid ones): None replaced by 0."
        self._aux_test_fetch_aggregate()
        self.assertListEqual(
            [
                [self.lannisters.name, '0', '0'],
                [self.starks.name,     '0', '0'],
            ],
            self.report_orga.fetch_all_lines(),
        )

    def test_fetch_aggregate_03(self):
        "Aggregate in sub-lines (expanded sub-report)."
        user = self.login_as_root_and_get()
        self._aux_test_fetch_persons(user=user, create_contacts=False, report_4_contact=False)

        report_invoice = Report.objects.create(
            user=user, name='Report on invoices', ct=FakeInvoice,
        )

        create_field = partial(Field.objects.create, selected=False, sub_report=None)
        create_field(report=report_invoice, name='name',           type=RFT_FIELD,     order=1)
        create_field(report=report_invoice, name='total_vat__sum', type=RFT_AGG_FIELD, order=2)

        report = self.report_orga
        create_field(
            report=report, name=FAKE_REL_OBJ_BILL_ISSUED, order=2,
            selected=True, sub_report=report_invoice, type=RFT_RELATION,
        )

        starks = self.starks
        lannisters = self.lannisters

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        guild = create_orga(name='Guild of merchants')
        hord  = create_orga(name='Hord')

        create_invoice = partial(self._create_invoice, target=guild)
        invoice1 = create_invoice(starks,     name='Invoice#1', total_vat=Decimal('100.5'))
        invoice2 = create_invoice(lannisters, name='Invoice#2', total_vat=Decimal('200.5'))
        invoice3 = create_invoice(lannisters, name='Invoice#3', total_vat=Decimal('50.1'))
        create_invoice(hord, name='Invoice#4', total_vat=Decimal('1000'))  # Should not be used

        def fmt_number(n):
            return number_format(n, decimal_pos=2)

        total_lannisters = fmt_number(invoice2.total_vat + invoice3.total_vat)
        total_starks     = fmt_number(invoice1.total_vat)
        self.assertListEqual(
            [
                [lannisters.name, invoice2.name, total_lannisters],
                [lannisters.name, invoice3.name, total_lannisters],
                [starks.name,     invoice1.name, total_starks],
            ],
            report.fetch_all_lines(),
        )

    def test_fetch_aggregate_04(self):
        "Decimal Custom field."
        user = self.login_as_root_and_get()
        self._aux_test_fetch_persons(user=user, create_contacts=False, report_4_contact=False)

        starks = self.starks
        lannisters = self.lannisters

        cfield = CustomField.objects.create(
            content_type=self.ct_orga,
            name='Gold',
            field_type=CustomField.FLOAT,
        )

        create_cfval = partial(cfield.value_class.objects.create, custom_field=cfield)

        starks_gold = Decimal('100.5')
        create_cfval(entity=starks, value=starks_gold)

        lannisters_gold = Decimal('500.3')
        create_cfval(entity=lannisters, value=lannisters_gold)

        report = self.report_orga
        Field.objects.create(
            report=report, name=f'{cfield.uuid}__sum', type=RFT_AGG_CUSTOM, order=2,
        )

        agg_value = number_format(starks_gold + lannisters_gold, decimal_pos=2)
        self.assertListEqual(
            [
                [lannisters.name, agg_value],
                [starks.name,     agg_value],
            ],
            report.fetch_all_lines(),
        )
