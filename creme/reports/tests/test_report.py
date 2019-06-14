# -*- coding: utf-8 -*-

try:
    from datetime import datetime, date
    from decimal import Decimal
    from functools import partial
    from unittest import skipIf

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.encoding import smart_str
    from django.utils.formats import date_format
    from django.utils.html import escape
    from django.utils.timezone import now
    from django.utils.translation import gettext as _, ngettext, pgettext

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.constants import REL_SUB_HAS
    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.core.function_field import function_field_registry
    from creme.creme_core.gui import actions
    from creme.creme_core.models import (RelationType, Relation, SetCredentials,
            EntityFilter, EntityFilterCondition, CustomField, CustomFieldInteger,
            CremePropertyType, CremeProperty, HeaderFilter, FieldsConfig)
    from creme.creme_core.tests.fake_constants import (FAKE_REL_SUB_EMPLOYED_BY,
            FAKE_REL_OBJ_EMPLOYED_BY, FAKE_REL_OBJ_BILL_ISSUED)
    from creme.creme_core.tests.fake_models import (FakeContact, FakeOrganisation, FakeLegalForm, FakePosition,
            FakeImage, FakeImageCategory, FakeEmailCampaign, FakeMailingList, FakeInvoice,
            FakeFolderCategory, FakeFolder as FakeCoreFolder, FakeDocument as FakeCoreDocument)

    from .base import BaseReportsTestCase, skipIfCustomReport, Report
    from .fake_models import FakeReportsFolder, FakeReportsDocument, Guild

    from ..actions import ExportReportAction
    from ..constants import (RFT_FIELD, RFT_CUSTOM, RFT_RELATION, RFT_FUNCTION,
            RFT_AGG_FIELD, RFT_AGG_CUSTOM, RFT_RELATED)
    from ..forms.report import ReportExportPreviewFilterForm
    from ..models import Field
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))

try:
    from creme.creme_core.backends import export_backend_registry
    from creme.creme_core.utils.xlrd_utils import XlrdReader

    XlsImport = not 'xls' in export_backend_registry.extensions
except Exception:
    XlsImport = True


@skipIfCustomReport
class ReportTestCase(BaseReportsTestCase):
    def assertHeaders(self, names, report):
        self.assertEqual(names, [f.name for f in report.get_children_fields_flat()])

    def _build_contacts_n_images(self):
        user = self.user

        create_img = FakeImage.objects.create
        self.ned_face   = create_img(name='Ned face',  user=self.other_user)
        self.aria_face  = create_img(name='Aria face', user=user)

        create_contact = partial(FakeContact.objects.create, user=user)
        self.ned  = create_contact(first_name='Eddard', last_name='Stark', image=self.ned_face)
        self.robb = create_contact(first_name='Robb',   last_name='Stark', user=self.other_user)
        self.aria = create_contact(first_name='Aria',   last_name='Stark', image=self.aria_face)

        self.efilter = EntityFilter.create('test-filter', 'Starks', FakeContact, is_custom=True,
                                           conditions=[EntityFilterCondition.build_4_field(
                                                            model=FakeContact,
                                                            operator=EntityFilterCondition.IEQUALS,
                                                            name='last_name',
                                                            values=[self.ned.last_name],
                                                        ),
                                                      ],
                                           )

    def _build_image_report(self):
        img_report = Report.objects.create(user=self.user, name='Report on images',
                                           ct=self.ct_image,
                                          )

        create_field = partial(Field.objects.create, report=img_report,
                               selected=False, sub_report=None, type=RFT_FIELD,
                              )
        create_field(name='name',        order=1)
        create_field(name='description', order=2)

        return img_report

    def _build_orga_report(self):
        orga_report = Report.objects.create(user=self.user, name='Report on organisations',
                                            ct=self.ct_orga,
                                           )

        create_field = partial(Field.objects.create, report=orga_report,
                               selected=False, sub_report=None, type=RFT_FIELD,
                              )
        create_field(name='name',              order=1)
        create_field(name='legal_form__title', order=2)

        return orga_report

    def _build_linkreport_url(self, rfield):
        return reverse('reports__link_report', args=(rfield.id,))

    def _build_export_url(self, report):
        return reverse('reports__export_report', args=(report.id,))

    def _build_preview_url(self, report):
        return reverse('reports__export_report_preview', args=(report.id,))

    def _create_cf_int(self):
        return CustomField.objects.create(content_type=self.ct_contact,
                                          name='Size (cm)', field_type=CustomField.INT,
                                         )

    def create_from_view(self, name, model, hf):
        self.assertNoFormError(self.client.post(self.ADD_URL, follow=True,
                                                data={'user': self.user.pk,
                                                      'name': name,
                                                      'ct':   ContentType.objects.get_for_model(model).id,
                                                      'hf':   hf.id,
                                                     }
                                               )
                              )

        return self.get_object_or_fail(Report, name=name)

    def login_as_basic_user(self, **kwargs):
        user = self.login(is_superuser=False,
                          allowed_apps=('creme_core', 'reports'),
                          **kwargs
                         )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        return user

    def test_columns(self):
        self.login()
        report = self._build_orga_report()
        report = self.refresh(report)

        with self.assertNumQueries(1):
            columns = report.columns

        self.assertIsInstance(columns, list)
        self.assertEqual(2, len(columns))

        field = columns[0]
        self.assertIsInstance(field, Field)
        self.assertEqual('name',     field.name)
        self.assertEqual(_('Name'), field.title)
        self.assertEqual(RFT_FIELD,  field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.sub_report)

        with self.assertNumQueries(0):
            f_report = field.report

        self.assertEqual(report, f_report)

    def test_detailview(self):
        self.login()

        report = self._create_report('My report')
        response = self.assertGET200(report.get_absolute_url())
        self.assertTemplateUsed(response, 'reports/view_report.html')

    def test_createview01(self):
        user = self.login()
        cf = self._create_cf_int()

        name = 'trinita'
        self.assertFalse(Report.objects.filter(name=name).exists())

        self.assertGET200(self.ADD_URL)

        report = self._create_report(name, extra_cells=[EntityCellCustomField(cf)])
        self.assertEqual(user,        report.user)
        self.assertEqual(FakeContact, report.ct.model_class())
        self.assertIsNone(report.filter)

        columns = report.columns
        self.assertEqual(5, len(columns))

        field = columns[0]
        self.assertEqual('last_name',     field.name)
        self.assertEqual(_('Last name'), field.title)
        self.assertEqual(RFT_FIELD,       field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.sub_report)

        field = columns[1]
        self.assertEqual('user',          field.name)
        self.assertEqual(_('Owner user'), field.title)

        field = columns[2]
        self.assertEqual(REL_SUB_HAS,  field.name)
        self.assertEqual(_('owns'),   field.title)
        self.assertEqual(RFT_RELATION, field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.sub_report)

        field = columns[3]
        self.assertEqual('get_pretty_properties', field.name)
        self.assertEqual(_('Properties'),         field.title)
        self.assertEqual(RFT_FUNCTION,            field.type)

        field = columns[4]
        self.assertEqual(str(cf.id), field.name)
        self.assertEqual(cf.name,    field.title)
        self.assertEqual(RFT_CUSTOM, field.type)

    def test_createview02(self):
        "With EntityFilter"
        self.login()
        efilter = EntityFilter.create('test-filter', 'Mihana family', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=['Mihana'],
                                                                   )
                               ])

        report = self._create_report('My awesome report', efilter)
        self.assertEqual(efilter, report.filter)

    def test_createview03(self):
        "Validation errors"
        user = self.login()

        def post(hf_id, filter_id):
            return self.assertPOST200(self.ADD_URL, follow=True,
                                      data={'user':   user.pk,
                                            'name':   'Report #1',
                                            'ct':     self.ct_contact.id,
                                            'hf':     hf_id,
                                            'filter': filter_id,
                                           }
                                     )

        response = post('unknown', 'unknown')
        msg = _('Select a valid choice. That choice is not one of the available choices.')
        self.assertFormError(response, 'form', 'hf',     msg)
        self.assertFormError(response, 'form', 'filter', msg)

        # ------
        hf_orga = HeaderFilter.create(pk='test_hf-orga', name='name', model=FakeOrganisation)
        efilter = EntityFilter.create('test-filter', 'Bad filter', FakeOrganisation, is_custom=True)
        response = post(hf_orga.id, efilter.id)
        self.assertFormError(response, 'form', 'hf',     msg)
        self.assertFormError(response, 'form', 'filter', msg)

        # ------
        hf_priv = HeaderFilter.create(pk='test_hf-private', name='name', model=FakeContact,
                                      is_private=True, user=self.other_user,
                                      is_custom=True,
                                     )
        response = post(hf_priv.id, '')
        self.assertFormError(response, 'form', 'hf', msg)

        # ------
        ef_priv = EntityFilter.create('test-private_filter', 'Private filter',
                                      FakeContact, is_custom=True,
                                      user=self.other_user, is_private=True,
                                     )
        response = post('', ef_priv.id)
        self.assertFormError(response, 'form', 'filter', msg)

    def test_createview04(self):
        "No HeaderFilter -> no column"
        user = self.login()

        name = 'Report #1'
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user': user.pk,
                                          'name': name,
                                          'ct':   self.ct_contact.id,
                                          'hf':   '',
                                         }
                                   )
        self.assertNoFormError(response)

        report = self.get_object_or_fail(Report, name=name)
        self.assertFalse(report.columns)

    def test_createview05(self):
        "With FieldsConfig: hidden fields are not copied"
        user = self.login()

        valid_fname = 'last_name'
        hidden_fname = 'phone'
        build_cell =  partial(EntityCellRegularField.build, model=FakeContact)
        hf = HeaderFilter.create(pk='test_hf', name='Contact view', model=FakeContact,
                                 cells_desc=[build_cell(name=valid_fname),
                                             build_cell(name=hidden_fname),
                                            ],
                                 )

        FieldsConfig.create(FakeContact,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})]
                            )

        name = 'Report #1'
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user': user.pk,
                                          'name': name,
                                          'ct':   self.ct_contact.id,
                                          'hf':   hf.id,
                                         }
                                   )
        self.assertNoFormError(response)

        report = self.get_object_or_fail(Report, name=name)

        columns = report.columns
        self.assertEqual(1, len(columns))

        column = columns[0]
        self.assertEqual(valid_fname, column.name)
        self.assertEqual(RFT_FIELD,   column.type)

    def test_editview01(self):
        user = self.login()

        name = 'my report'
        report = self._create_report(name)
        url = report.get_edit_absolute_url()
        self.assertGET200(url)

        name = name.title()
        efilter = EntityFilter.create('test-filter', 'Filter', FakeContact, is_custom=True,
                                      is_private=True, user=user,
                                      )
        response = self.client.post(url, follow=True, 
                                    data={'user': user.pk,
                                          'name': name,
                                          'filter': efilter.id,
                                         }
                                   )
        self.assertNoFormError(response)

        report = self.refresh(report)
        self.assertEqual(name,    report.name)
        self.assertEqual(efilter, report.filter)

    def test_editview02(self):
        "Cannot edit the 'filter' field when its a private filter which belongs to another user"
        user = self.login()

        ef_priv = EntityFilter.create('test-private_filter', 'Private filter',
                                      FakeContact, is_custom=True,
                                      user=self.other_user, is_private=True,
                                     )
        report = Report.objects.create(name='Report', user=user, filter=ef_priv,
                                       ct=self.ct_contact,
                                      )

        ef_pub = EntityFilter.create('test-public_filter', 'Public filter',
                                     FakeContact, is_custom=True,
                                    )
        response = self.client.post(report.get_edit_absolute_url(), follow=True, 
                                    data={'user': user.pk,
                                          'name': 'Report edited',
                                          'filter': ef_pub.id,  # Should not be used
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(ef_priv, self.refresh(report).filter)

    def test_report_inneredit_filter01(self):
        self.login()

        create_ef = partial(EntityFilter.create, is_custom=True)
        contact_filter = create_ef('test-filter1', 'Mihana family', FakeContact)
        orga_filter    = create_ef('test-filter2', 'Mihana house', FakeOrganisation)
        private_filter = create_ef('test-filter3', 'XXX', FakeContact,
                                   is_private=True, user=self.other_user
                                  )

        report = self._create_report('A')
        self.assertIsNone(report.filter)

        url = self.build_inneredit_url(report, 'filter')
        response = self.assertGET200(url)
        self.assertContains(response, contact_filter.name)
        self.assertNotContains(response, orga_filter.name)  # Excluded from filter choices because report targets a Contact.
        self.assertNotContains(response, private_filter.name)

        response = self.assertPOST200(url, data={'field_value': orga_filter.pk})
        self.assertFormError(response, 'form', 'field_value',
                             _('Select a valid choice. That choice is not one of the available choices.')
                            )

        response = self.client.post(url, data={'field_value': contact_filter.pk})
        self.assertNoFormError(response)
        self.assertEqual(contact_filter, self.refresh(report).filter)

    def test_report_inneredit_filter02(self):
        "Private filter to another user -> cannot edit"
        self.login()
        other_user = self.other_user

        efilter = EntityFilter.create('test-filter', 'Mihana family', FakeContact,
                                      is_custom=True, is_private=True, user=other_user,
                                     )
        report = Report.objects.create(user=other_user, name="Other's report",
                                       ct=efilter.entity_type, filter=efilter,
                                      )

        url = self.build_inneredit_url(report, 'filter')
        response = self.assertGET200(url)
        self.assertContains(response,
                            escape(ngettext('The filter cannot be changed because it is private.',
                                            'The filters cannot be changed because they are private.',
                                            1
                                           )
                                  )
                           )

        response = self.assertPOST200(url, data={'field_value': ''})
        self.assertFormError(response, 'form', None,
                             _('The filter cannot be changed because it is private.')
                            )
        self.assertEqual(efilter, self.refresh(report).filter)

    def test_report_bulkedit_filter01(self):
        "Reports are related to the same ContentType -> OK"
        self.login()

        create_ef = partial(EntityFilter.create, is_custom=True)
        contact_filter = create_ef('test-filter1', 'Mihana family', FakeContact)
        orga_filter    = create_ef('test-filter2', 'Mihana house', FakeOrganisation)

        report_1 = self._create_report('Filter #1')
        report_2 = self._create_report('Filter #2')

        url = self.build_bulkupdate_url(Report, 'filter')
        self.assertGET200(url)

        response = self.assertPOST200(url,
                                      data={'field_value': orga_filter.id,
                                            'entities': [report_1.id, report_2.id],
                                           }
                                     )
        self.assertFormError(response, 'form', 'field_value',
                             _('Select a valid choice. That choice is not one of the available choices.')
                            )

        response = self.client.post(url,
                                    data={'field_value': contact_filter.id,
                                          'entities': [report_1.id, report_2.id],
                                         }
                                   )
        self.assertNoFormError(response)

        self.assertEqual(self.refresh(report_1).filter, contact_filter)
        self.assertEqual(self.refresh(report_2).filter, contact_filter)

    def test_report_bulkedit_filter02(self):
        "Reports are related to different ContentTypes -> error"
        self.login()

        contact_filter = EntityFilter.create('test-filter', 'Mihana family', FakeContact, is_custom=True)

        report_1 = self._create_report('Contact report')
        report_2 = self._create_simple_organisations_report('Orga report')

        url = self.build_bulkupdate_url(Report, 'filter')
        self.assertGET200(url)

        response = self.assertPOST200(url,
                                      data={'field_value': contact_filter.id,
                                            'entities': [report_1.id, report_2.id],
                                           })
        self.assertFormError(response, 'form', None,
                             _('Filter field can only be updated when reports '
                               'target the same type of entities (e.g: only contacts).'
                              )
                            )

    def test_report_bulkedit_filter03(self):
        "Some filters are not visible (private) -> errors"
        user = self.login()
        other_user = self.other_user

        create_ef = partial(EntityFilter.create, is_custom=True, model=FakeContact)
        efilter1 = create_ef('test-filter1', name='Filter #1')
        efilter2 = create_ef('test-filter2', name='Filter #2', is_private=True, user=other_user)
        efilter3 = create_ef('test-filter3', name='Filter #3', is_private=True, user=user)

        report_1 = self._create_report('Filter #1', efilter=efilter1)
        report_2 = self._create_report('Filter #2')
        report_3 = Report.objects.create(user=other_user, name="Other's report",
                                         ct=efilter2.entity_type, filter=efilter2,
                                        )

        response = self.client.post(self.build_bulkupdate_url(Report, 'filter'),
                                    data={'field_value': efilter3.id,
                                          'entities': [report_1.id, report_2.id, report_3.id],
                                         }
                                   )
        self.assertNoFormError(response)

        self.assertEqual(efilter3, self.refresh(report_1).filter)
        self.assertEqual(efilter3, self.refresh(report_2).filter)
        self.assertEqual(efilter2, self.refresh(report_3).filter)  # No change

    def test_listview(self):
        self.login()

        reports = [self._create_report('Report#1'),
                   self._create_report('Report#2'),
                  ]

        response = self.assertGET200(Report.get_lv_absolute_url())

        with self.assertNoException():
            # reports_page = response.context['entities']
            reports_page = response.context['page_obj']

        for report in reports:
            self.assertIn(report, reports_page.object_list)

    def test_listview_actions(self):
        user = self.login()
        report = self._create_report('Report#1')

        export_actions = [
            action for action in actions.actions_registry
                                        .instance_actions(user=user, instance=report)
                if isinstance(action, ExportReportAction)
        ]
        self.assertEqual(1, len(export_actions))

        export_action = export_actions[0]
        self.assertEqual('reports-export', export_action.id)
        self.assertEqual('reports-export', export_action.type)
        self.assertEqual(reverse('reports__export_report_filter', args=(report.id,)),
                         export_action.url
                        )
        self.assertEqual(pgettext('reports-report', 'Export «{object}»').format(object=report),
                         export_action.help_text
                        )
        self.assertTrue(export_action.is_enabled)
        self.assertTrue(export_action.is_visible)

    def test_clone(self):
        user = self.login()
        efilter = EntityFilter.create('test-filter', 'Mihana family', FakeContact, is_custom=True)
        ct = ContentType.objects.get_for_model(FakeContact)
        report = Report.objects.create(user=user, name='Contact report', ct=ct, filter=efilter)

        create_field = partial(Field.objects.create, report=report)
        rfield1 = create_field(name='last_name',             order=1, type=RFT_FIELD)
        rfield2 = create_field(name='get_pretty_properties', order=2, type=RFT_FUNCTION)

        cloned_report = report.clone()
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

    def test_delete_efilter(self):
        "The filter should not be deleted."
        self.login()

        efilter = EntityFilter.create('test-filter', 'Mihana family', FakeContact, is_custom=True)
        report = self._create_report('My awesome report', efilter)

        url = reverse('creme_core__delete_efilter')
        data = {'id': efilter.id}
        response = self.assertPOST200(url, data=data, follow=True)
        self.assertStillExists(efilter)
        self.assertStillExists(report)
        self.assertRedirects(response, FakeContact.get_lv_absolute_url())

        # AJAX version
        self.assertPOST(400, url, data=data, follow=True, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertStillExists(efilter)
        self.assertStillExists(report)

    def test_preview01(self):
        user = self.login()

        create_c = partial(FakeContact.objects.create, user=user)
        chiyo = create_c(first_name='Chiyo', last_name='Mihana', birthday=date(year=1995, month=3, day=26))
        osaka = create_c(first_name='Ayumu', last_name='Kasuga', birthday=date(year=1990, month=4, day=1))

        report = self._create_report('My report')
        url = self._build_preview_url(report)

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'reports/preview_report.html')

        context = response.context
        self.assertEqual(report, context.get('object'))
        self.assertEqual(25,     context.get('limit_to'))
        self.assertFalse(context.get('empty_message'))
        self.assertIsInstance(context.get('form'), ReportExportPreviewFilterForm)

        columns = context.get('flat_columns')
        self.assertIsInstance(columns, list)
        self.assertEqual(4, len(columns))
        self.assertIsInstance(columns[0], Field)
        self.assertEqual(['last_name', 'user', 'creme_core-subject_has', 'get_pretty_properties'],
                         [f.name for f in columns]
                        )

        self.assertContains(response, chiyo.last_name)
        self.assertContains(response, osaka.last_name)

        response = self.assertGET200(url,
                                     data={'doc_type': 'csv',
                                           'date_filter_0': '',
                                           'date_filter_1': '1990-01-01',
                                           'date_filter_2': '1990-12-31',
                                           'date_field':    'birthday',
                                          }
                                    )
        self.assertTemplateUsed(response, 'reports/preview_report.html')
        self.assertNoFormError(response)
        self.assertContains(response, osaka.last_name)
        self.assertNotContains(response, chiyo.last_name)

    def test_preview02(self):
        "Empty: no contact"
        self.login()
        report = self._create_report('My report')

        response = self.assertGET200(self._build_preview_url(report))
        self.assertTemplateUsed(response, 'reports/preview_report.html')
        self.assertContains(response,
                            _('You can see no «{model}»').format(model='Test Contact')
                           )

    def test_preview03(self):
        "Empty: no allowed contact"
        self.login_as_basic_user(creatable_models=[Report])

        FakeContact.objects.create(user=self.other_user, first_name='Chiyo', last_name='Mihana')

        report = self._create_report('My report')
        response = self.assertGET200(self._build_preview_url(report))
        self.assertContains(response,
                            _('You can see no «{model}»').format(model='Test Contact')
                           )

    def test_preview04(self):
        "Empty: no contact after date filtering"
        user = self.login()
        tomo = FakeContact.objects.create(user=user, first_name='Tomo', last_name='Takino')

        efilter = EntityFilter.create('test-filter', 'Kasuga family', FakeContact, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=FakeContact,
                                                        operator=EntityFilterCondition.IEQUALS,
                                                        name='last_name', values=['Kasuga'],
                                                    ),
                                                 ],
                                     )
        report = self._create_report('My report', efilter=efilter)

        response = self.assertGET200(self._build_preview_url(report))
        self.assertNotContains(response, tomo.last_name)
        self.assertContains(response,
                            _('No «{model}» matches the filter «{filter}»').format(
                                    model='Test Contact',
                                    filter=report.filter,
                                )
                           )

    def test_preview05(self):
        "Empty: no contact after date filtering"
        user = self.login()
        report = self._create_report('My report')

        FakeContact.objects.create(user=user, first_name='Chiyo', last_name='Mihana',
                                   birthday=date(year=1995, month=3, day=26),
                                  )

        response = self.assertGET200(self._build_preview_url(report),
                                     data={'doc_type': 'csv',
                                           'date_filter_0': '',
                                           'date_filter_1': '1990-01-01',
                                           'date_filter_2': '1990-12-31',
                                           'date_field':    'birthday',
                                          }
                                    )
        msg = _('No «{model}» matches your date filter').format(model='Test Contact')
        self.assertEqual(msg, response.context.get('empty_message'))
        self.assertContains(response, msg)

    def test_report_reorder_field01(self):
        self.login()

        report = self._create_report('trinita')
        rfield = self.get_field_or_fail(report, 'user')
        url = reverse('reports__reorder_field', args=(report.id, rfield.id,))
        # self.assertGET404(url, data={'target': 1})
        self.assertGET405(url, data={'target': 1})

        self.client.post(url, data={'target': 1})
        self.assertEqual(['user', 'last_name', REL_SUB_HAS, 'get_pretty_properties'],
                         [f.name for f in report.fields.order_by('order')]
                        )

    def test_report_reorder_field02(self):
        "Report & Field do not match"
        self.login()

        report1 = self._create_report('Hill')
        report2 = self._create_report('Spencer')

        rfield = self.get_field_or_fail(report1, 'user')
        # self.assertPOST409(reverse('reports__reorder_field', args=(report2.id, rfield.id,)),
        self.assertPOST404(reverse('reports__reorder_field', args=(report2.id, rfield.id,)),
                           data={'target': 1}
                          )

    def test_export_filter_form_customrange(self):
        self.login()

        report = self._create_report('My report')
        url = reverse('reports__export_report_filter', args=(report.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'reports/forms/report-export-filter.html')

        context = response.context
        self.assertEqual(pgettext('reports-report', 'Export «{object}»').format(object=report),
                         context.get('title')
                        )
        self.assertEqual(pgettext('reports-report', 'Export'), context.get('submit_label'))

        # ---
        date_field = 'birthday'
        response = self.assertPOST200(url,
                                      data={'doc_type': 'csv',
                                            'date_filter_0': '',
                                            'date_filter_1': '01-01-1990',
                                            'date_filter_2': '31-12-1990',
                                            'date_field':    date_field,
                                           }
                                     )
        self.assertNoFormError(response)
        self.assertEqual('{url}?doc_type=csv'
                         '&date_field={date}'
                         '&date_filter_0='
                         '&date_filter_1=01-01-1990'
                         '&date_filter_2=31-12-1990'.format(
                                url=reverse('reports__export_report', args=(report.id,)),
                                date=date_field,
                            ),
                         response.content.decode()
                        )

    def test_export_filter_not_superuser01(self):
        user = self.login(is_superuser=False, allowed_apps=['reports'])
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL,
                                     )

        report = Report.objects.create(name='Report', user=user, ct=self.ct_orga)
        self.assertGET200(reverse('reports__export_report_filter', args=(report.id,)))

    def test_export_filter_not_superuser02(self):
        "VIEW permission"
        user = self.login(is_superuser=False, allowed_apps=['reports'])
        # SetCredentials.objects.create(role=self.role,
        #                               value=EntityCredentials.VIEW,
        #                               set_type=SetCredentials.ESET_ALL,
        #                              )

        report = Report.objects.create(name='Report', user=user, ct=self.ct_orga)
        self.assertGET403(reverse('reports__export_report_filter', args=(report.id,)))

    def test_export_filter_form_missing_doctype(self):
        self.login()

        report = self._create_report('My report')
        url = reverse('reports__export_report_filter', args=(report.id,))
        self.assertGET200(url)

        date_field = 'birthday'
        response = self.assertPOST200(url, data={'date_field': date_field,})

        self.assertFormError(response, 'form', 'doc_type',
                             _('This field is required.')
                            )

    def test_export_filter_form_missing_customrange(self):
        self.login()

        report = self._create_report('My report')
        url = reverse('reports__export_report_filter', args=(report.id,))
        self.assertGET200(url)

        date_field = 'birthday'
        response = self.assertPOST200(url, data={'doc_type': 'csv',
                                                 'date_filter_0': '',
                                                 'date_filter_1': '',
                                                 'date_filter_2': '',
                                                 'date_field': date_field,
                                                }
                                     )

        self.assertFormError(response, 'form', '',
                             _('If you chose a Date field, and select «customized» '
                               'you have to specify a start date and/or an end date.'
                              )
                            )

    def test_export_filter_form_invalid_filter(self):
        self.login()

        report = self._create_report('My report')
        url = reverse('reports__export_report_filter', args=(report.id,))
        self.assertGET200(url)

        date_field = 'birthday'
        response = self.assertPOST200(url, data={'date_field': date_field,
                                                 'date_filter_0': 'unknown',
                                                }
                                     )

        self.assertFormError(response, 'form', 'date_filter',
                             _('Select a valid choice. %(value)s is not one of the available choices.') % {
                                    'value': 'unknown',
                                }
                            )

    def test_export_filter_form_no_datefield(self):
        self.login()

        report = self._create_report('My report')
        url = reverse('reports__export_report_filter', args=(report.id,))
        self.assertGET200(url)

        date_field = ''
        doc_type = 'csv'
        response = self.client.post(url, data={'doc_type':      doc_type,
                                               'date_filter_0': '',
                                               'date_field':    date_field,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual('{url}?doc_type={type}&date_field='.format(
                                url=reverse('reports__export_report', args=(report.id,)),
                                type=doc_type,
                            ),
                         response.content.decode()
                        )

    def test_report_csv01(self):
        "Empty report"
        self.login()

        self.assertFalse(FakeInvoice.objects.all())

        rt = RelationType.objects.get(pk=REL_SUB_HAS)
        hf = HeaderFilter.create(pk='test_hf', name='Invoice view', model=FakeInvoice,
                                 cells_desc=[EntityCellRegularField.build(model=FakeInvoice, name='name'),
                                             EntityCellRegularField.build(model=FakeInvoice, name='user'),
                                             EntityCellRelation(model=FakeInvoice, rtype=rt),
                                             EntityCellFunctionField.build(model=FakeInvoice, func_field_name='get_pretty_properties'),
                                            ],
                                 )

        report = self.create_from_view('Report on invoices', FakeInvoice, hf)

        response = self.assertGET200(self._build_export_url(report), data={'doc_type': 'csv'})
        self.assertEqual('doc_type=csv', response.request['QUERY_STRING'])
        self.assertEqual('"{}","{}","{}","{}"\r\n'.format(
                              _('Name'), _('Owner user'), rt.predicate, _('Properties')
                            ),
                         response.content.decode()
                        )

    def test_report_csv02(self):
        self.login()

        self._create_persons()
        self.assertEqual(3, FakeContact.objects.count())

        report   = self._create_report('trinita')
        response = self.assertGET200(self._build_export_url(report), data={'doc_type': 'csv'})

        content = (s for s in response.content.decode().split('\r\n') if s)
        self.assertEqual(smart_str('"{}","{}","{}","{}"'.format(
                                      _('Last name'), _('Owner user'), _('owns'), _('Properties')
                                    )
                                  ),
                         next(content)
                        )

        user_str = str(self.user)
        self.assertEqual('"Ayanami","{}","","Kawaii"'.format(user_str),  next(content))  # Alphabetical ordering ??
        self.assertEqual('"Katsuragi","{}","Nerv",""'.format(user_str),  next(content))
        self.assertEqual('"Langley","{}","",""'.format(user_str),        next(content))
        with self.assertRaises(StopIteration):
            next(content)

    def test_report_csv03(self):
        "With date filter"
        user = self.login()

        self._create_persons()
        report   = self._create_report('trinita')
        response = self.assertGET200(self._build_export_url(report),
                                     data={'doc_type': 'csv',
                                           'date_field': 'birthday',
                                           'date_filter_0': '',
                                           'date_filter_1': datetime(year=1980, month=1, day=1).strftime('%d-%m-%Y'),
                                           'date_filter_2': datetime(year=2000, month=1, day=1).strftime('%d-%m-%Y'),
                                          }
                                    )

        content = [s for s in response.content.decode().split('\r\n') if s]
        self.assertEqual(3, len(content))

        self.assertEqual('"Ayanami","{}","","Kawaii"'.format(user), content[1])
        self.assertEqual('"Langley","{}","",""'.format(user),       content[2])

    def test_report_csv04(self):
        "With date filter and registered range"
        user = self.login()

        self._create_persons()
        FakeContact.objects.create(user=user, last_name='Baby', first_name='Joe',
                                   birthday=datetime(year=now().year, month=1, day=1)
                                   )
        report   = self._create_report('trinita')
        response = self.assertGET200(self._build_export_url(report),
                                     data={'doc_type': 'csv',
                                           'date_field': 'birthday',
                                           'date_filter_0': 'current_year',
                                          }
                                    )

        content = [s for s in response.content.decode().split('\r\n') if s]
        self.assertEqual(2, len(content))
        self.assertEqual('"Baby","{}","",""'.format(user), content[1])

    def test_report_csv05(self):
        "Errors: invalid GET param"
        self.login()

        self._create_persons()
        report = self._create_report('trinita')
        url = self._build_export_url(report)
        data = {'doc_type': 'csv',
                'date_field': 'birthday',
                'date_filter_0': '',
                'date_filter_1': datetime(year=1980, month=1, day=1).strftime('%d-%m-%Y'),
                'date_filter_2': datetime(year=2000, month=1, day=1).strftime('%d-%m-%Y'),
               }

        def export(status, **kwargs):
            self.assertGET(status, url, data=dict(data, **kwargs))

        export(404, date_field='invalidfield')
        export(404, date_field='first_name')  # Not a date field
        export(200, date_filter_1='1980-01-01')  # Invalid format
        export(200, date_filter_2='2000-01-01')  # Invalid format

    def test_report_csv06(self):
        "With FieldsConfig"
        self.login()

        hidden_fname1 = 'phone'
        hidden_fname2 = 'image'
        FieldsConfig.create(FakeContact,
                            descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True}),
                                          (hidden_fname2, {FieldsConfig.HIDDEN: True}),
                                         ],
                            )

        self._create_persons()

        report = self._create_simple_contacts_report()

        create_rfield = partial(Field.objects.create, report=report, type=RFT_FIELD)
        create_rfield(order=2, name=hidden_fname1)
        create_rfield(order=3, name=hidden_fname2 + '__description')

        response = self.assertGET200(self._build_export_url(report), data={'doc_type': 'csv'})

        content = (s for s in response.content.decode().split('\r\n') if s)
        self.assertEqual(smart_str('"{}"'.format(_('Last name'))), next(content))

        self.assertEqual('"Ayanami"',   next(content))
        self.assertEqual('"Katsuragi"', next(content))

    def test_report_csv07(self):
        "With FieldsConfig on sub-field"
        self.login()

        hidden_fname = 'description'
        FieldsConfig.create(FakeImage,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
                           )

        self._create_persons()

        report = self._create_simple_contacts_report()
        Field.objects.create(report=report, type=RFT_FIELD, order=2, name='image__' + hidden_fname)

        response = self.assertGET200(self._build_export_url(report), data={'doc_type': 'csv'})

        content = (s for s in response.content.decode().split('\r\n') if s)
        self.assertEqual(smart_str('"{}"'.format(_('Last name'))), next(content))

        self.assertEqual('"Ayanami"',   next(content))
        self.assertEqual('"Katsuragi"', next(content))

    @skipIf(XlsImport, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_report_xls(self):
        "With date filter"
        self.login()

        self._create_persons()
        report   = self._create_report('trinita')
        response = self.assertGET200(reverse('reports__export_report', args=(report.id,)),
                                     data={'doc_type': 'xls',
                                           'date_field': 'birthday',
                                           'date_filter_0': '',
                                           'date_filter_1': datetime(year=1980, month=1, day=1).strftime('%d-%m-%Y'),
                                           'date_filter_2': datetime(year=2000, month=1, day=1).strftime('%d-%m-%Y'),
                                          },
                                     follow=True,
                                    )
        result = list(XlrdReader(None, file_contents=response.content))

        self.assertEqual(3, len(result))

        user_str = str(self.user)
        self.assertEqual(['Ayanami', user_str, '', 'Kawaii'], result[1])
        self.assertEqual(['Langley', user_str, '', ''],       result[2])

    def _build_editfields_url(self, report):
        return reverse('reports__edit_fields', args=(report.id,))

    def test_edit_fields01(self):
        self.login()

        report = self._create_simple_contacts_report('Report #1')
        url = self._build_editfields_url(report)
        self.assertGET200(url)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(_('Edit columns of «{object}»').format(object=report),
                         response.context.get('title')
                        )

        # ---
        old_rfield = report.columns[0]

        self.assertNoFormError(
            self.client.post(url, data={'columns': 'regular_field-last_name,'
                                                   'regular_field-first_name',
                                       }
                            )
        )

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
        "FK, Custom field, aggregate on CustomField; additional old Field deleted"
        self.login()

        cf = self._create_cf_int()

        report = self._create_report('My beloved Report')
        Field.objects.create(report=report, type=RFT_FIELD, name='description', order=5)

        old_rfields = self.refresh(report).columns
        self.assertEqual(5, len(old_rfields))

        f_name = 'last_name'
        fk_name = 'image'
        cf_id = str(cf.id)
        aggr_id = '{}__max'.format(cf_id)
        response = self.client.post(self._build_editfields_url(report),
                                    data={'columns': 'regular_field-{rfield},'
                                                     'custom_field-{cfield},'
                                                     'custom_aggregate-{agg},'
                                                     'regular_field-{fkfield}'.format(
                                                            rfield=f_name,
                                                            cfield=cf_id,
                                                            agg=aggr_id,
                                                            fkfield=fk_name,
                                                        ),
                                         }
                                   )
        self.assertNoFormError(response)

        columns = list(report.fields.all())
        self.assertEqual(4, len(columns))

        column = columns[0]
        self.assertEqual(f_name, column.name)
        self.assertEqual(old_rfields[0].id, column.id)

        column = columns[1]
        self.assertEqual(cf_id,      column.name)
        self.assertEqual(cf.name,    column.title)
        self.assertEqual(RFT_CUSTOM, column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)
        self.assertEqual(old_rfields[1].id, column.id)

        column = columns[2]
        self.assertEqual(aggr_id,                             column.name)
        self.assertEqual('{} - {}'.format(_('Maximum'), cf.name), column.title)
        self.assertEqual(RFT_AGG_CUSTOM,                      column.type)
        self.assertEqual(old_rfields[2].id, column.id)

        column = columns[3]
        self.assertEqual(fk_name,         column.name)
        self.assertEqual(_('Photograph'), column.title)
        self.assertEqual(RFT_FIELD,       column.type)

        self.assertDoesNotExist(old_rfields[4])

    def test_edit_fields03(self):
        "Other types: relationships, function fields"
        self.login()
        report = self._create_report('My beloved Report')
        f_name = 'user__username'

        rtype_id = FAKE_REL_SUB_EMPLOYED_BY
        rtype = self.get_object_or_fail(RelationType, pk=rtype_id)

        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')
        self.assertIsNotNone(funcfield)

        response = self.client.post(self._build_editfields_url(report),
                                    data={'columns': 'relation-{rtype},'
                                                     'regular_field-{rfield},'
                                                     'function_field-{ffield}'.format(
                                                            rfield=f_name,
                                                            rtype=rtype_id,
                                                            ffield=funcfield.name,
                                                        ),
                                         }
                                   )
        self.assertNoFormError(response)

        columns = report.columns
        self.assertEqual(3, len(columns))

        column = columns[0]
        self.assertEqual(rtype_id,        column.name)
        self.assertEqual(rtype.predicate, column.title)
        self.assertEqual(1,               column.order)
        self.assertEqual(RFT_RELATION,    column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)

        column = columns[1]
        self.assertEqual(f_name, column.name)
        self.assertEqual(RFT_FIELD,    column.type)
        self.assertEqual(_('Owner user') + ' - ' + _('Username'), column.title)

        column = columns[2]
        self.assertEqual(funcfield.name,         column.name)
        self.assertEqual(funcfield.verbose_name, column.title)
        self.assertEqual(3,                      column.order)
        self.assertEqual(RFT_FUNCTION,           column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)

    def test_edit_fields04(self):
        "Aggregate on regular fields"
        user = self.login()

        report = Report.objects.create(name='Secret report', user=user, ct=self.ct_orga)
        f_name = 'name'
        aggr_id = 'capital__min'
        response = self.client.post(self._build_editfields_url(report),
                                    data={'columns': 'regular_field-{rfield},regular_aggregate-{agg}'.format(
                                                            rfield=f_name,
                                                            agg=aggr_id,
                                                        ),
                                         }
                                   )
        self.assertNoFormError(response)

        columns = report.columns
        self.assertEqual(2, len(columns))

        self.assertEqual(f_name, columns[0].name)

        column = columns[1]
        self.assertEqual(aggr_id,                             column.name)
        self.assertEqual(_('Minimum') + ' - ' + _('Capital'), column.title)
        self.assertEqual(2,                                   column.order)
        self.assertEqual(RFT_AGG_FIELD,                       column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)

    def test_edit_fields05(self):
        "Related entity"
        user = self.login()

        report = Report.objects.create(name='Folder report', user=user, ct=self.ct_folder)

        f_name = 'title'
        rel_name = 'fakereportsdocument'
        response = self.client.post(self._build_editfields_url(report),
                                    data={'columns': 'regular_field-{rfield},'
                                                     'related-{related}'.format(
                                                            rfield=f_name,
                                                            related=rel_name,
                                                        ),
                                              }
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
        "Edit field with sub-report"
        user = self.login()

        create_report = partial(Report.objects.create, user=user)
        report_orga    = create_report(name='Report on Organisations', ct=self.ct_orga)
        report_contact = create_report(name='Report on Contacts',      ct=self.ct_contact)
        report_img     = create_report(name='Report on Images',        ct=self.ct_image)

        # TODO: we need helpers: Field.create_4_field(), Field.create_4_relation() etc...
        create_field = partial(Field.objects.create, report=report_orga)
        create_field(name=FAKE_REL_OBJ_EMPLOYED_BY, type=RFT_RELATION, order=1, selected=True, sub_report=report_contact)
        create_field(name='name',              type=RFT_FIELD,    order=2)
        create_field(name='image',             type=RFT_FIELD,    order=3, selected=False, sub_report=report_img)

        response = self.client.post(self._build_editfields_url(report_orga),
                                    data={'columns': 'regular_field-{rfield1},'
                                                     'relation-{rtype},'
                                                     'regular_field-{rfield2},'
                                                     'regular_field-{rfield3}'.format(
                                                            rfield1='name',
                                                            rtype=FAKE_REL_OBJ_EMPLOYED_BY,
                                                            rfield2='description',
                                                            rfield3='image',  # TODO: and with image__name ???
                                                        ),
                                              }
                                   )
        self.assertNoFormError(response)

        columns = report_orga.columns
        self.assertEqual(4, len(columns))

        column = columns[0]
        self.assertEqual('name',    column.name)
        self.assertEqual(RFT_FIELD, column.type)
        self.assertIsNone(column.sub_report)

        column = columns[1]
        self.assertEqual(FAKE_REL_OBJ_EMPLOYED_BY, column.name)
        self.assertEqual(RFT_RELATION,        column.type)
        self.assertEqual(report_contact,      column.sub_report)
        self.assertTrue(column.selected)

        self.assertEqual('description', columns[2].name)

        column = columns[3]
        self.assertEqual('image',    column.name)
        self.assertEqual(RFT_FIELD,  column.type)
        self.assertEqual(report_img, column.sub_report)
        self.assertFalse(column.selected)

    def test_edit_fields07(self):
        "With FieldsConfig"
        self.login()

        valid_fname = 'last_name'
        hidden_fname1 = 'phone'
        hidden_fname2 = 'birthday'
        FieldsConfig.create(FakeContact,
                            descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True}),
                                          (hidden_fname2, {FieldsConfig.HIDDEN: True}),
                                         ]
                            )

        report = self._create_simple_contacts_report('Report #1')
        Field.objects.create(report=report, name=hidden_fname2, type=RFT_FIELD, order=2)

        url = self._build_editfields_url(report)
        response = self.assertGET200(url)

        with self.assertNoException():
            widget = response.context['form'].fields['columns'].widget
            choices_keys = {c[0] for c in widget.model_fields}

        self.assertIn('regular_field-' + valid_fname,     choices_keys)
        self.assertNotIn('regular_field-' + hidden_fname1, choices_keys)
        self.assertIn('regular_field-' + hidden_fname2, choices_keys)  # <== already in report: still proposed

        response = self.client.post(url,
                                    data={'columns': 'regular_field-{},regular_field-{}'.format(
                                                            valid_fname,
                                                            hidden_fname2,
                                                        ),
                                         }
                                   )
        self.assertNoFormError(response)

        columns = self.refresh(report).columns
        self.assertEqual(2, len(columns))
        self.assertEqual(valid_fname,   columns[0].name)
        self.assertEqual(hidden_fname2, columns[1].name)

    def test_edit_fields08(self):
        "FK with depth=2"
        user = self.login()

        report = Report.objects.create(name='Docs report', user=user,
                                       ct=ContentType.objects.get_for_model(FakeCoreDocument),
                                      )

        # fname = 'folder__category'
        fname = 'linked_folder__category'
        response = self.client.post(self._build_editfields_url(report),
                                    data={'columns': 'regular_field-{rfield1},regular_field-{rfield2}'.format(
                                                            rfield1='title',
                                                            rfield2=fname,
                                                        ),
                                              }
                                   )
        self.assertNoFormError(response)

        columns = report.columns
        self.assertEqual(2, len(columns))

        column = columns[1]
        self.assertEqual(fname, column.name)
        self.assertEqual(RFT_FIELD, column.type)

    def test_edit_fields09(self):
        "M2M with depth=2"
        user = self.login()

        report = Report.objects.create(name='Contact report', user=user,
                                       ct=self.ct_contact,
                                      )

        fname = 'image__categories'
        response = self.client.post(self._build_editfields_url(report),
                                    data={'columns': 'regular_field-{rfield1},'
                                                     'regular_field-{rfield2}'.format(
                                                            rfield1='last_name',
                                                            rfield2=fname,
                                                        ),
                                         }
                                   )
        self.assertNoFormError(response)

        columns = report.columns
        self.assertEqual(2, len(columns))

        column = columns[1]
        self.assertEqual(fname, column.name)
        self.assertEqual(RFT_FIELD, column.type)

    def test_edit_fields_not_super_user01(self):
        user = self.login(is_superuser=False, allowed_apps=['reports'])
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        report = Report.objects.create(name='Contact report', user=user, ct=self.ct_contact)
        self.assertGET200(self._build_editfields_url(report))

    def test_edit_fields_not_super_user02(self):
        "Edition permission on Report are needed."
        user = self.login(is_superuser=False, allowed_apps=['reports'])
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW,  # EntityCredentials.CHANGE
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        report = Report.objects.create(name='Contact report', user=user, ct=self.ct_contact)
        self.assertGET403(self._build_editfields_url(report))

    def test_edit_fields_errors01(self):
        self.login()

        report = self._create_simple_contacts_report()
        response = self.assertPOST200(self._build_editfields_url(report),
                                      data={'columns': 'regular_field-image__categories__name'},
                                     )
        self.assertFormError(response, 'form', 'columns', _('Enter a valid value.'))

    def test_edit_fields_errors02(self):
        user = self.login()
        report = Report.objects.create(user=user, name='Report on docs',
                                       ct=ContentType.objects.get_for_model(FakeReportsDocument),
                                      )
        response = self.assertPOST200(self._build_editfields_url(report),
                                      data={'columns': 'regular_field-linked_folder__parent'},
                                     )
        self.assertFormError(response, 'form', 'columns', _('Enter a valid value.'))

    def test_invalid_hands01(self):
        self.login()
        report = self._create_simple_contacts_report()

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD, order=2)  # TODO: inline
        rfield = create_field(name='image__categories__name')
        self.assertIsNone(rfield.hand)
        self.assertDoesNotExist(rfield)

    def test_invalid_hands02(self):
        user = self.login()

        report = Report.objects.create(user=user, name='Report on docs',
                                       ct=ContentType.objects.get_for_model(FakeReportsDocument),
                                      )

        rfield = Field.objects.create(name='linked_folder__parent', report=report, type=RFT_FIELD, order=2)
        self.assertIsNone(rfield.hand)
        self.assertDoesNotExist(rfield)

    def test_link_report_regular(self):
        "RFT_FIELD (FK) field"
        user = self.login()

        contact_report = Report.objects.create(user=user, name='Report on contacts',
                                               ct=self.ct_contact,
                                              )

        create_field = partial(Field.objects.create, report=contact_report, selected=False, sub_report=None, type=RFT_FIELD)
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

        self.assertEqual([self.ct_image], list(fk_img_field.hand.get_linkable_ctypes()))

        img_report = self._build_image_report()
        url = self._build_linkreport_url(fk_img_field)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(_('Link of the column «{object}»').format(object=fk_img_field),
                         context.get('title')
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
        self.assertGET404(url)
        self.assertPOST409(url, data={'field_id': str_field.id})
        self.assertPOST200(url, data={'field_id': fk_img_field.id})

        fk_img_field = self.refresh(fk_img_field)
        self.assertIsNone(fk_img_field.sub_report)
        self.assertFalse(fk_img_field.selected)

    def test_link_report_not_superuser01(self):
        user = self.login(is_superuser=False, allowed_apps=['reports'])
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.LINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        report = Report.objects.create(user=user, name='Report', ct=self.ct_contact)

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        create_field(name='last_name', order=1)
        fk_img_field = create_field(name='image__name', order=2)
        self.assertGET200(self._build_linkreport_url(fk_img_field))

    def test_link_report_not_superuser02(self):
        "LINK permission"
        user = self.login(is_superuser=False, allowed_apps=['reports'])
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW,  # EntityCredentials.LINK
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        report = Report.objects.create(user=user, name='Report', ct=self.ct_contact)

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        create_field(name='last_name', order=1)
        fk_img_field = create_field(name='image__name', order=2)
        self.assertGET403(self._build_linkreport_url(fk_img_field))

    def test_link_report_relation01(self):
        "RelationType has got constraints on CT"
        user = self.login()

        contact_report = Report.objects.create(user=user, name='Report on contacts',
                                               ct=self.ct_contact,
                                              )

        create_field = partial(Field.objects.create, report=contact_report, selected=False, sub_report=None)
        reg_rfield = create_field(name='last_name',         type=RFT_FIELD,    order=1)
        rel_rfield = create_field(name=FAKE_REL_SUB_EMPLOYED_BY, type=RFT_RELATION, order=2)

        self.assertGET409(self._build_linkreport_url(reg_rfield))  # Not a RFT_RELATION Field

        url = self._build_linkreport_url(rel_rfield)
        self.assertGET200(url)

        # Incompatible CT
        response = self.assertPOST200(url, data={'report': self._build_image_report().id})
        self.assertFormError(response, 'form', 'report', _('This entity does not exist.'))

        orga_report = self._build_orga_report()
        self.assertNoFormError(self.client.post(url, data={'report': orga_report.id}))
        self.assertEqual(orga_report, self.refresh(rel_rfield).sub_report)

    def test_link_report_relation02(self):
        "RelationType hasn't any constraint on CT"
        user = self.login()

        contact_report = Report.objects.create(user=user, ct=self.ct_contact,
                                               name='Report on contacts',
                                              )
        rtype = RelationType.create(('reports-subject_obeys',   'obeys to'),
                                    ('reports-object_commands', 'commands'),
                                   )[0]

        create_field = partial(Field.objects.create, report=contact_report, selected=False, sub_report=None)
        create_field(name='last_name', type=RFT_FIELD, order=1)
        rel_rfield = create_field(name=rtype.id, type=RFT_RELATION, order=2)

        url = self._build_linkreport_url(rel_rfield)
        img_report = self._build_image_report()
        self.assertNoFormError(self.client.post(url, data={'report': img_report.id}))
        self.assertEqual(img_report, self.refresh(rel_rfield).sub_report)

    def test_link_report_related(self):
        "RFT_RELATED field"
        user = self.login()

        self.assertEqual([('fakereportsdocument', 'Test (reports) Document')],
                         Report.get_related_fields_choices(FakeReportsFolder)
                        )

        folder_report = Report.objects.create(name='Report on folders', user=user,
                                              ct=self.ct_folder,
                                             )

        create_field = partial(Field.objects.create, report=folder_report)
        rfield1 = create_field(name='title',    type=RFT_FIELD,   order=1)
        rfield2 = create_field(name='fakereportsdocument', type=RFT_RELATED, order=2)

        self.assertGET409(self._build_linkreport_url(rfield1))  # Not a RFT_RELATION Field

        doc_report = self._create_simple_documents_report()
        url = self._build_linkreport_url(rfield2)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'report': doc_report.id}))
        self.assertEqual(doc_report, self.refresh(rfield2).sub_report)

    def test_link_report_error(self):
        "Cycle error"
        user = self.login()

        contact_report = Report.objects.create(user=user, ct=self.ct_contact,
                                               name='Report on contacts',
                                              )

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=RFT_RELATION)
        create_field(report=contact_report, name='last_name', type=RFT_FIELD, order=1)
        rel_rfield = create_field(report=contact_report, name=FAKE_REL_SUB_EMPLOYED_BY, order=2)

        orga_report = self._build_orga_report()
        create_field(report=orga_report, name=FAKE_REL_OBJ_EMPLOYED_BY, order=3,
                     sub_report=contact_report,
                    )

        url = self._build_linkreport_url(rel_rfield)
        self.assertGET200(url)

        response = self.assertPOST200(url, data={'report': orga_report.id})
        self.assertFormError(response, 'form', 'report', _('This entity does not exist.'))

        # Invalid field -> no 500 error
        rfield = create_field(report=contact_report, name='invalid', type=RFT_FIELD, order=3)
        self.assertGET409(self._build_linkreport_url(rfield))

    def test_link_report_selected(self):
        "selected=True if only one sub-report"
        user = self.login()

        img_report = self._build_image_report()
        contact_report = Report.objects.create(user=user, name='Report on contacts',
                                               ct=self.ct_contact,
                                              )

        create_field = partial(Field.objects.create, report=contact_report, type=RFT_FIELD)
        create_field(name='last_name',   order=1)
        img_field  = create_field(name='image__name', order=2, sub_report=img_report)
        rel_rfield = create_field(name=FAKE_REL_SUB_EMPLOYED_BY, order=3, type=RFT_RELATION)

        orga_report = self._build_orga_report()
        self.assertNoFormError(self.client.post(self._build_linkreport_url(rel_rfield),
                                                data={'report': orga_report.id},
                                               )
                              )

        rel_rfield = self.refresh(rel_rfield)
        self.assertEqual(orga_report, rel_rfield.sub_report)
        self.assertFalse(rel_rfield.selected)

        # 'columns' property avoid several selected sub-reports
        img_field.selected  = True; img_field.save()
        rel_rfield.selected = True; rel_rfield.save()
        self.assertEqual(1, len([f for f in self.refresh(contact_report).columns if f.selected]))

    def test_set_selected01(self):
        user = self.login()

        img_report = self._build_image_report()
        orga_report = self._build_orga_report()

        contact_report = Report.objects.create(user=user, name='Report on contacts',
                                               ct=self.ct_contact,
                                              )

        create_field = partial(Field.objects.create, report=contact_report,
                               selected=False, sub_report=None, type=RFT_FIELD,
                              )
        reg_rfield = create_field(name='last_name',         order=1)
        fk_rfield  = create_field(name='image__name',       order=2, sub_report=img_report)
        rel_rfield = create_field(name=FAKE_REL_SUB_EMPLOYED_BY, order=3,
                                  sub_report=orga_report, type=RFT_RELATION, selected=True,
                                 )

        url = reverse('reports__set_selected_field')
        self.assertGET404(url)

        data = {'field_id':  reg_rfield.id,
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

        self.assertPOST200(url, data=dict(data, checked=0))
        self.assertFalse(self.refresh(fk_rfield).selected)
        self.assertFalse(self.refresh(rel_rfield).selected)

    def test_set_selected02(self):
        "Missing Field ID"
        user = self.login()

        contact_report = Report.objects.create(user=user, name='Report on contacts',
                                               ct=self.ct_contact,
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
        "Field & report do not match"
        user = self.login()

        img_report = self._build_image_report()
        orga_report = self._build_orga_report()
        contact_report = Report.objects.create(user=user, name='Report on contacts',
                                               ct=self.ct_contact,
                                              )
        fk_rfield = Field.objects.create(report=contact_report, name='image__name',
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

    def _aux_test_fetch_persons(self, create_contacts=True, create_relations=True, report_4_contact=True):
        user = self.user

        if create_contacts:
            create_contact = partial(FakeContact.objects.create, user=user)
            self.ned    = create_contact(first_name='Eddard', last_name='Stark')
            self.robb   = create_contact(first_name='Robb',   last_name='Stark')
            self.tyrion = create_contact(first_name='Tyrion', last_name='Lannister')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        self.starks     = create_orga(name='House Stark')
        self.lannisters = create_orga(name='House Lannister')

        if create_contacts and create_relations:
            create_rel = partial(Relation.objects.create, type_id=FAKE_REL_OBJ_EMPLOYED_BY, user=user)
            create_rel(subject_entity=self.starks, object_entity=self.ned)
            create_rel(subject_entity=self.starks, object_entity=self.robb)
            create_rel(subject_entity=self.lannisters, object_entity=self.tyrion)

        efilter = EntityFilter.create('test-filter', 'Houses', FakeOrganisation, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeOrganisation,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='name', values=['House '],
                                                                    )
                               ])

        create_report = partial(Report.objects.create, user=self.user, filter=None)

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD)

        if report_4_contact:
            self.report_contact = report = create_report(name='Report on Contacts', ct=self.ct_contact)

            create_field(report=report, name='last_name',  order=1)
            create_field(report=report, name='first_name', order=2)

        self.report_orga = create_report(name='Report on Organisations', ct=self.ct_orga, filter=efilter)
        create_field(report=self.report_orga, name='name', order=1)

    def test_fetch_field_01(self):
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        for i in range(5):
            create_contact(last_name='Mister {}'.format(i))

        create_contact(last_name='Mister X', is_deleted=True)

        report = self._create_simple_contacts_report('Contacts report')
        self.assertEqual([[ln] for ln in FakeContact.objects.filter(is_deleted=False)
                                                        .values_list('last_name', flat=True)
                          ],
                         report.fetch_all_lines()
                        )

    def test_fetch_field_02(self):
        "FK, date, filter, invalid one"
        self.login()

        self._aux_test_fetch_persons(report_4_contact=False, create_contacts=False, create_relations=False)

        report = self.report_orga
        create_field = partial(Field.objects.create, report=report,
                               selected=False, sub_report=None, type=RFT_FIELD,
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

        username = self.user.username
        self.assertEqual([[self.lannisters.name, username, '',          ''],
                          [starks.name,          username, lform.title, date_format(starks.creation_date, 'DATE_FORMAT')],
                         ],
                         report.fetch_all_lines()
                        )

    def test_fetch_field_03(self):
        "View credentials"
        user = self.login_as_basic_user()

        self._aux_test_fetch_persons(report_4_contact=False, create_contacts=False, create_relations=False)

        Field.objects.create(report=self.report_orga, name='image__name',
                             order=2, selected=False, sub_report=None, type=RFT_FIELD,
                            )

        baratheons = FakeOrganisation.objects.create(user=self.other_user, name='House Baratheon')
        self.assertFalse(user.has_perm_to_view(baratheons))

        create_img     = FakeImage.objects.create
        starks_img     = create_img(name='Stark emblem',     user=user)
        lannisters_img = create_img(name='Lannister emblem', user=self.other_user)
        self.assertTrue(user.has_perm_to_view(starks_img))
        self.assertFalse(user.has_perm_to_view(lannisters_img))

        self.starks.image = starks_img
        self.starks.save()

        self.lannisters.image = lannisters_img
        self.lannisters.save()

        fetch_all_lines = self.report_orga.fetch_all_lines
        lines = [[baratheons.name,      ''],
                 [self.lannisters.name, lannisters_img.name],
                 [self.starks.name,     starks_img.name]
                ]
        self.assertEqual(lines, fetch_all_lines())
        self.assertEqual(lines, fetch_all_lines(user=self.other_user))  # Super user

        lines.pop(0)
        lines[0][1] = settings.HIDDEN_VALUE  # 'lannisters_img' not visible
        self.assertEqual(lines, fetch_all_lines(user=user))

    def _aux_test_fetch_documents(self, efilter=None, selected=True):
        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD)

        self.folder_report = Report.objects.create(name='Folders report', user=self.user,
                                                   ct=self.ct_folder, filter=efilter,
                                                  )
        create_field(report=self.folder_report, name='title',       order=1)
        create_field(report=self.folder_report, name='description', order=2)

        self.doc_report = self._create_simple_documents_report()
        create_field(report=self.doc_report, name='linked_folder__title', order=3,
                     sub_report=self.folder_report, selected=selected,
                    )

        create_folder = partial(FakeReportsFolder.objects.create, user=self.user)
        self.folder1 = create_folder(title='Internal')
        self.folder2 = create_folder(title='External', description='Boring description')

        create_doc = partial(FakeReportsDocument.objects.create, user=self.user)
        self.doc1 = create_doc(title='Doc#1', linked_folder=self.folder1, description='Blbalabla')
        self.doc2 = create_doc(title='Doc#2', linked_folder=self.folder2)

    def test_fetch_fk_01(self):
        "Sub report: no sub-filter"
        self.login()

        self._aux_test_fetch_documents()
        self.assertHeaders(['title', 'description', 'title', 'description'], self.doc_report)

        doc1 = self.doc1; folder2 = self.folder2
        self.assertEqual([[doc1.title,      doc1.description, self.folder1.title, ''],
                          [self.doc2.title, '',               folder2.title,      folder2.description],
                         ],
                         self.doc_report.fetch_all_lines()
                        )

    def test_fetch_fk_02(self):
        "Sub report: sub-filter"
        self.login()

        efilter = EntityFilter.create('test-filter', 'Internal folders', FakeReportsFolder, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeReportsFolder,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='title', values=['Inter'],
                                                                   )
                               ])

        self._aux_test_fetch_documents(efilter)

        doc1 = self.doc1
        self.assertEqual([[doc1.title,      doc1.description, self.folder1.title, ''],
                          [self.doc2.title, '',               '',                 ''],
                         ],
                         self.doc_report.fetch_all_lines()
                        )

    def test_fetch_fk_03(self):
        "Sub report (flattened)"
        self.login()
        self._aux_test_fetch_documents(selected=False)

        doc1 = self.doc1; folder2 = self.folder2
        fmt = '%s: %%s/%s: %%s' % (_('Title'), _('Description'))
        self.assertEqual([[doc1.title,      doc1.description, fmt % (self.folder1.title, '')],
                          [self.doc2.title, '',               fmt % (folder2.title,      folder2.description)],
                         ],
                         self.doc_report.fetch_all_lines()
                        )

    def test_fetch_fk_04(self):
        "Not Entity, no (sub) attribute"
        user = self.login()

        self._aux_test_fetch_persons(report_4_contact=False, create_contacts=False, create_relations=False)
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
        self.assertEqual([[self.lannisters.name, '',          user_str],
                          [starks.name,          lform.title, user_str],
                         ],
                         report.fetch_all_lines()
                        )

    def test_fetch_fk_05(self):
        "FK with depth=2"
        user = self.login()

        cat = FakeFolderCategory.objects.create(name='Maps')

        create_folder = partial(FakeCoreFolder.objects.create, user=user)
        folder1 = create_folder(title='Earth maps', category=cat)
        folder2 = create_folder(title="Faye's pix")

        create_doc = partial(FakeCoreDocument.objects.create, user=user)
        doc1 = create_doc(title='Japan map',   linked_folder=folder1)
        doc2 = create_doc(title='Mars city 1', linked_folder=folder2)

        report = Report.objects.create(name='Docs report', user=user,
                                       ct=ContentType.objects.get_for_model(FakeCoreDocument),
                                      )

        create_field = partial(Field.objects.create, report=report,
                               selected=False, sub_report=None, type=RFT_FIELD,
                              )
        create_field(name='title',                   order=1)
        create_field(name='linked_folder__category', order=2)

        self.assertEqual([[doc1.title, cat.name],
                          [doc2.title, ''],
                         ],
                         report.fetch_all_lines()
                        )

    def test_fetch_fk_06(self):
        "M2M at depth=2"
        user = self.login()

        create_cat = FakeImageCategory.objects.create
        cat1 = create_cat(name='Selfy')
        cat2 = create_cat(name='Official')

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='Faye pix')
        img2 = create_img(name='Spike pix')
        img3 = create_img(name='Jet pix')

        img1.categories.set([cat1, cat2])
        img2.categories.set([cat1])

        description = 'Bebop member'
        create_contact = partial(FakeContact.objects.create, user=user, description=description)
        faye  = create_contact(last_name='Valentine', image=img1)
        spike = create_contact(last_name='Spiegel',   image=img2)
        jet   = create_contact(last_name='Black',     image=img3)
        ed    = create_contact(last_name='Wong')

        efilter = EntityFilter.create('test-filter', 'Bebop member', FakeContact, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                            model=FakeContact,
                                                            operator=EntityFilterCondition.IEQUALS,
                                                            name='description',
                                                            values=[description],
                                                        ),
                                                 ],
                                      )

        report = Report.objects.create(name='Contact report', user=user, filter=efilter,
                                       ct=self.ct_contact,
                                      )

        create_field = partial(Field.objects.create, report=report,
                               selected=False, sub_report=None, type=RFT_FIELD,
                              )
        create_field(name='last_name',         order=1)
        create_field(name='image__categories', order=2)

        self.assertEqual([[jet.last_name,   ''],
                          [spike.last_name, cat1.name],
                          [faye.last_name,  cat2.name + '/' + cat1.name],
                          [ed.last_name,    ''],
                         ],
                         report.fetch_all_lines()
                        )

    def test_fetch_cf_01(self):
        "Custom fields"
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        ned  = create_contact(first_name='Eddard', last_name='Stark')
        robb = create_contact(first_name='Robb',   last_name='Stark')
        aria = create_contact(first_name='Aria',   last_name='Stark')

        efilter = EntityFilter.create('test-filter', 'Starks', FakeContact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=FakeContact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=[ned.last_name]
                                                                    )
                               ])

        cf = self._create_cf_int()
        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=ned,  value=190)
        create_cfval(entity=aria, value=150)

        report = self._create_report('Contacts with CField', efilter=efilter)
        report.fields.all().delete()

        create_field = partial(Field.objects.create, report=report, selected=False, sub_report=None)
        create_field(name='first_name', type=RFT_FIELD,  order=1)
        create_field(name=cf.id,        type=RFT_CUSTOM, order=2)
        create_field(name=1024,         type=RFT_CUSTOM, order=3)  # Simulates deleted CustomField

        report = self.refresh(report)
        self.assertEqual(2, len(report.columns))
        self.assertEqual(2, report.fields.count())

        self.assertEqual([[aria.first_name, '150'],
                          [ned.first_name,  '190'],
                          [robb.first_name, ''],
                         ],
                         report.fetch_all_lines()
                        )

    def test_fetch_cf_02(self):
        "In FK, credentials"
        user = self.login_as_basic_user()

        self._build_contacts_n_images()
        ned_face = self.ned_face; aria_face = self.aria_face

        cf = CustomField.objects.create(content_type=self.ct_image,
                                        name='Popularity', field_type=CustomField.INT
                                       )

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=ned_face,  value=190)
        create_cfval(entity=aria_face, value=150)

        create_report = partial(Report.objects.create, user=user, filter=None)
        report_img = create_report(name='Report on Images', ct=self.ct_image)

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD)
        create_field(report=report_img, name='name', order=1)
        create_field(report=report_img, name=cf.id,  order=2, type=RFT_CUSTOM)

        report_contact = create_report(name='Report on Contacts', ct=self.ct_contact, filter=self.efilter)
        create_field(report=report_contact, name='first_name',  order=1)
        create_field(report=report_contact, name='image__name', order=2,
                     sub_report=report_img, selected=True,
                    )

        lines = [[self.aria.first_name, aria_face.name, '150'],
                 [self.ned.first_name,  ned_face.name,  '190'],
                 [self.robb.first_name, '',             ''],
                ]
        self.assertEqual(lines, report_contact.fetch_all_lines())

        lines.pop()  # 'robb' is not visible
        ned_line = lines[1]
        ned_line[1] = ned_line[2] = settings.HIDDEN_VALUE  # 'ned_face' is not visible
        self.assertEqual(lines, report_contact.fetch_all_lines(user=user))

    def test_fetch_m2m_01(self):
        "No sub report"
        user = self.login()

        hf = HeaderFilter.create(pk='test_hf', name='Campaign view', model=FakeEmailCampaign,
                                 cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                             (EntityCellRegularField, {'name': 'mailing_lists__name'}),
                                            ],
                                 )

        report = self.create_from_view('Campaign Report', FakeEmailCampaign, hf)

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        name1 = 'Camp#1'; camp1 = create_camp(name=name1)
        name2 = 'Camp#2'; camp2 = create_camp(name=name2)

        create_ml = partial(FakeMailingList.objects.create, user=user)
        camp1.mailing_lists.set([create_ml(name='ML#1'), create_ml(name='ML#2')])
        camp2.mailing_lists.set([create_ml(name='ML#3')])

        self.assertHeaders(['name', 'mailing_lists__name'], report)
        self.assertEqual([[name1, 'ML#1, ML#2'],
                          [name2, 'ML#3'],
                         ],
                         report.fetch_all_lines()
                        )

    def _aux_test_fetch_m2m(self):
        user = self.login()

        create_ptype = CremePropertyType.create
        self.ptype1 = create_ptype(str_pk='test-prop_important',    text='Important')
        self.ptype2 = create_ptype(str_pk='test-prop_notimportant', text='Not important')

        create_hf = HeaderFilter.create
        hf_camp = create_hf(pk='test_hf_camp', name='Campaign view', model=FakeEmailCampaign,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                        (EntityCellRegularField, {'name': 'mailing_lists__name'}),
                                       ]
                            )
        hf_ml   = create_hf(pk='test_hf_ml', name='MList view', model=FakeMailingList,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                        (EntityCellFunctionField, {'func_field_name': 'get_pretty_properties'}),
                                       ]
                            )

        create_report = self.create_from_view
        self.report_camp = create_report('Campaign Report', FakeEmailCampaign, hf_camp)
        self.report_ml   = create_report('Campaign ML', FakeMailingList, hf_ml)

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
        "Sub report (expanded)"
        self._aux_test_fetch_m2m()

        report_camp = self.report_camp; report_ml= self.report_ml
        name1 = self.camp1.name; name2 = self.camp2.name; name3 = self.camp3.name
        ml1 = self.ml1; ml2 = self.ml2; ml3 = self.ml3
        ptype1 = self.ptype1; ptype2 = self.ptype2

        self.assertHeaders(['name', 'mailing_lists__name'], report_camp)
        self.assertEqual([[name1, ml1.name + ', ' + ml2.name],
                          [name2, ml3.name],
                          [name3, ''],
                         ],
                         report_camp.fetch_all_lines()
                        )

        self.assertEqual([[ml1.name, ptype1.text], [ml2.name, ptype2.text], [ml3.name, '']],
                         report_ml.fetch_all_lines()
                        )

        # Let's go for the sub-report
        rfield = report_camp.fields.get(name='mailing_lists__name')
        rfield.sub_report = report_ml
        rfield.selected = True
        rfield.save()

        self.assertEqual([ContentType.objects.get_for_model(FakeMailingList)],
                         list(rfield.hand.get_linkable_ctypes())
                         )

        report_camp = self.refresh(report_camp)
        self.assertHeaders(['name', 'name', 'get_pretty_properties'], report_camp)
        self.assertEqual([[name1, ml1.name, ptype1.text],
                          [name1, ml2.name, ptype2.text],
                          [name2, ml3.name, ''],
                          [name3, '',       ''],
                         ],
                         report_camp.fetch_all_lines()
                        )

    def test_fetch_m2m_03(self):
        "Sub report (not expanded)"
        self._aux_test_fetch_m2m()

        report_camp = self.report_camp

        # Let's go for the sub-report
        rfield = report_camp.fields.get(name='mailing_lists__name')
        rfield.sub_report = self.report_ml
        rfield.selected = False
        rfield.save()

        report_camp = self.refresh(report_camp)
        self.assertHeaders(['name', 'mailing_lists__name'], report_camp)

        fmt = '%s: %%s/%s: %%s' % (_('Name of the mailing list'), _('Properties'))
        self.assertEqual([[self.camp1.name, fmt % (self.ml1.name, self.ptype1.text) + ', ' +
                                            fmt % (self.ml2.name, self.ptype2.text),
                          ],
                          [self.camp2.name, fmt % (self.ml3.name, '')],
                          [self.camp3.name, ''],
                         ],
                         report_camp.fetch_all_lines()
                        )

    def test_fetch_m2m_04(self):
        "Not CremeEntity model"
        self.login()

        report = self._build_image_report()

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        rfield1 = create_field(name='categories__name', order=3)
        rfield2 = create_field(name='categories',       order=4)

        self.assertIsNone(rfield1.hand.get_linkable_ctypes())
        self.assertIsNone(rfield2.hand.get_linkable_ctypes())

        self.assertEqual(_('Categories') + ' - ' + _('Name'), rfield1.title)
        self.assertEqual(_('Categories'),                     rfield2.title)

        create_img = partial(FakeImage.objects.create, user=self.user)
        img1 = create_img(name='Img#1', description='Pretty picture')
        img2 = create_img(name='Img#2')

        create_cat = FakeImageCategory.objects.create
        cat1 = create_cat(name='Photo of contact')
        cat2 = create_cat(name='Photo of product')

        # img1.categories = [cat1, cat2]
        img1.categories.set([cat1, cat2])

        cats_str = '{}, {}'.format(cat1.name, cat2.name)
        self.assertEqual([[img1.name, img1.description, cats_str, cats_str],
                          [img2.name, '',               '',       ''],
                        ],
                        report.fetch_all_lines()
                    )

    def test_fetch_m2m_05(self):
        "FK at depth=2"
        user = self.login()

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

        report = Report.objects.create(name='Guilds report', user=user,
                                       ct=ContentType.objects.get_for_model(Guild),
                                      )

        create_field = partial(Field.objects.create, report=report,
                               selected=False, sub_report=None, type=RFT_FIELD,
                              )
        create_field(name='name',              order=1)
        create_field(name='members__position', order=2)

        self.assertEqual([[guild2.name, leader.title],
                          [guild3.name, ''],
                          [guild1.name, '{}, {}, '.format(leader.title, side_kick.title)],
                         ],
                         report.fetch_all_lines()
                        )

    def _aux_test_fetch_related(self, select_doc_report=None, invalid_one=False):
        user = self.user
        create_report = partial(Report.objects.create, user=user, filter=None)
        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD)

        self.doc_report = self._create_simple_documents_report() if select_doc_report is not None else None

        self.folder_report = create_report(name='Report on folders', ct=self.ct_folder)
        create_field(report=self.folder_report, name='title',    order=1)
        create_field(report=self.folder_report, name='fakereportsdocument', order=2,
                     type=RFT_RELATED, sub_report=self.doc_report, selected=select_doc_report or False,
                    )

        if invalid_one:
            create_field(report=self.folder_report, name='invalid', order=3, type=RFT_RELATED)

        create_folder = partial(FakeReportsFolder.objects.create, user=user)
        self.folder1 = create_folder(title='External')
        self.folder2 = create_folder(title='Internal')

        create_doc = partial(FakeReportsDocument.objects.create, user=user)
        self.doc11 = create_doc(title='Doc#1-1', linked_folder=self.folder1, description='Boring !')
        self.doc12 = create_doc(title='Doc#1-2', linked_folder=self.folder1, user=self.other_user)
        self.doc21 = create_doc(title='Doc#2-1', linked_folder=self.folder2)

    def test_fetch_related_01(self):
        self.login_as_basic_user()

        self._aux_test_fetch_related(select_doc_report=None, invalid_one=True)

        report = self.refresh(self.folder_report)
        self.assertEqual(2, len(report.columns))

        doc11 = self.doc11; doc12 = self.doc12
        fetch = report.fetch_all_lines
        lines = [[self.folder1.title, '{}, {}'.format(doc11, doc12)],
                 [self.folder2.title, str(self.doc21)],
                ]
        self.assertEqual(lines, fetch())

        lines[0][1] = str(doc11)
        self.assertEqual(lines, fetch(user=self.user))

    def test_fetch_related_02(self):
        "Sub-report (expanded)"
        user = self.login_as_basic_user()

        self._aux_test_fetch_related(select_doc_report=True)
        folder3 = FakeReportsFolder.objects.create(user=user, title='Empty')

        folder1 = self.folder1; doc11 = self.doc11
        # Beware: folders are ordered by title
        lines = [[folder3.title,      '',               ''],
                 [folder1.title,      doc11.title,      doc11.description],
                 [folder1.title,      self.doc12.title, ''],
                 [self.folder2.title, self.doc21.title, ''],
                ]
        fetch = self.folder_report.fetch_all_lines
        self.assertEqual(lines, fetch())

        lines.pop(2)  # doc12
        self.assertEqual(lines, fetch(user=user))

    def test_fetch_related_03(self):
        "Sub-report (not expanded)"
        user = self.login_as_basic_user()

        self._aux_test_fetch_related(select_doc_report=False)
        folder3 = FakeReportsFolder.objects.create(user=user, title='Empty')

        folder1 = self.folder1; doc11 = self.doc11
        fmt = '%s: %%s/%s: %%s' % (_('Title'), _('Description'))
        doc11_str = fmt % (doc11.title, doc11.description)
        lines = [[folder3.title,      ''],
                 [folder1.title,      doc11_str + ', ' + fmt % (self.doc12.title, '')],
                 [self.folder2.title, fmt % (self.doc21.title, '')],
                ]
        fetch = self.folder_report.fetch_all_lines
        self.assertEqual(lines, fetch())

        lines[1][1] = doc11_str
        self.assertEqual(lines, fetch(user=user))

    def test_fetch_funcfield_01(self):
        self.login()

        self._aux_test_fetch_persons(report_4_contact=False, create_contacts=False, create_relations=False)

        ptype = CremePropertyType.objects.create(pk='reports-test_fetch_funcfield_01', text='I am not dead !')
        CremeProperty.objects.create(type=ptype, creme_entity=self.starks)

        report = self.report_orga
        create_field = partial(Field.objects.create, report=report,
                               selected=False, sub_report=None, type=RFT_FUNCTION,
                              )
        create_field(name='get_pretty_properties', order=2)
        create_field(name='invalid_funfield',      order=3)

        report = self.refresh(report)
        self.assertEqual(2, len(report.columns))  # Invalid column is deleted
        self.assertEqual(2, report.fields.count())

        self.assertEqual([[self.lannisters.name, ''],
                          [self.starks.name,     ptype.text],
                         ],
                         report.fetch_all_lines()
                        )

    def test_fetch_funcfield_02(self):
        user = self.login_as_basic_user()

        self._build_contacts_n_images()
        ned_face = self.ned_face; aria_face = self.aria_face

        self.assertFalse(user.has_perm_to_view(ned_face))
        self.assertTrue(user.has_perm_to_view(aria_face))

        create_report = partial(Report.objects.create, user=user, filter=None)
        report_img = create_report(name='Report on Images', ct=self.ct_image)

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD)
        create_field(report=report_img, name='name',                  order=1)
        create_field(report=report_img, name='get_pretty_properties', order=2, type=RFT_FUNCTION)

        report_contact = create_report(name='Report on Contacts', ct=self.ct_contact, filter=self.efilter)
        create_field(report=report_contact, name='first_name',  order=1)
        create_field(report=report_contact, name='image__name', order=2,
                     sub_report=report_img, selected=True,
                    )

        ptype = CremePropertyType.objects.create(pk='reports-test_fetch_funcfield_02',
                                                 text='I am waiting the winter',
                                                )

        create_prop = partial(CremeProperty.objects.create, type=ptype)
        create_prop(creme_entity=aria_face)
        create_prop(creme_entity=ned_face)

        lines = [[self.aria.first_name, aria_face.name, ptype.text],
                 [self.ned.first_name,  ned_face.name,  ptype.text],
                 [self.robb.first_name, '',             ''],
                ]
        self.assertEqual(lines, report_contact.fetch_all_lines())

        lines.pop()  # 'robb' is not visible
        ned_line = lines[1]
        ned_line[1] = ned_line[2] = settings.HIDDEN_VALUE  # 'ned_face' is not visible
        self.assertEqual(lines, report_contact.fetch_all_lines(user=user))

    def test_fetch_relation_01(self):
        "No sub-report"
        self.login_as_basic_user()

        self._aux_test_fetch_persons(report_4_contact=False)
        report = self.report_orga

        ned = self.ned
        ned.user = self.other_user
        ned.save()

        create_field = partial(Field.objects.create, report=report,
                               type=RFT_RELATION, selected=False, sub_report=None,
                              )
        create_field(name=FAKE_REL_OBJ_EMPLOYED_BY, order=2)
        create_field(name='invalid',           order=3)

        report = self.refresh(report)
        self.assertEqual(2, len(report.columns))
        self.assertEqual(2, report.fields.count())

        fetch = self.report_orga.fetch_all_lines
        lines = [[self.lannisters.name, str(self.tyrion)],
                 [self.starks.name,     '{}, {}'.format(ned, self.robb)],
                ]
        self.assertEqual(lines, fetch())

        lines[1][1] = str(self.robb)
        self.assertEqual(lines, fetch(user=self.user))

    def test_fetch_relation_02(self):
        "Sub-report (expanded)"
        self.login_as_basic_user()
        self._aux_test_fetch_persons()

        report = self.report_orga
        Field.objects.create(report=report, name=FAKE_REL_OBJ_EMPLOYED_BY, order=2,
                             type=RFT_RELATION, selected=True, sub_report=self.report_contact,
                             )

        self.assertHeaders(['name', 'last_name', 'first_name'], report)

        starks = self.starks; ned = self.ned; robb = self.robb; tyrion = self.tyrion

        robb.user = self.other_user
        robb.save()

        lines = [[self.lannisters.name, tyrion.last_name, tyrion.first_name],
                 [starks.name,          ned.last_name,    ned.first_name],
                 [starks.name,          robb.last_name,   robb.first_name],
                ]
        self.assertEqual(lines, report.fetch_all_lines())

        lines.pop()  # 'robb' line removed
        self.assertEqual(lines, report.fetch_all_lines(user=self.user))

    def test_fetch_relation_03(self):
        "Sub-report (not expanded)"
        self.login_as_basic_user()
        self._aux_test_fetch_persons()

        ptype = CremePropertyType.create(str_pk='test-prop_dwarf', text='Dwarf')
        CremeProperty.objects.create(type=ptype, creme_entity=self.tyrion)

        report_contact = self.report_contact

        create_field = Field.objects.create
        create_field(report=report_contact, name='get_pretty_properties',
                     type=RFT_FUNCTION, order=3,
                    )
        create_field(report=report_contact, name='image__name',
                     type=RFT_FIELD, order=4,
                     sub_report=self._build_image_report(), selected=True,
                    )

        report_orga = self.report_orga
        create_field(report=report_orga, name=FAKE_REL_OBJ_EMPLOYED_BY, order=2,
                     type=RFT_RELATION, selected=False, sub_report=report_contact,
                     )
        self.assertHeaders(['name', FAKE_REL_OBJ_EMPLOYED_BY], report_orga)

        ned = self.ned; robb = self.robb; tyrion = self.tyrion

        robb.user = self.other_user
        robb.save()

        ned.image = img = FakeImage.objects.create(name='Ned pic', user=self.user,
                                                   description='Ned Stark selfie',
                                                  )
        ned.save()

        fmt = '%s: %%s/%s: %%s/%s: %%s/%s: %%s' % (
                    _('Last name'), _('First name'), _('Properties'), _('Photograph'),
                )
        ned_str = fmt % (ned.last_name,  ned.first_name, '',
                         '%s: %s/%s: %s' % (_('Name'), img.name, _('Description'), img.description)
                        )
        lines = [[self.lannisters.name, fmt % (tyrion.last_name, tyrion.first_name, ptype.text, '')],
                 [self.starks.name,     ned_str + ', ' +
                                        fmt % (robb.last_name, robb.first_name, '', '')
                 ],
                ]
        self.assertEqual(lines, report_orga.fetch_all_lines())

        lines[1][1] = ned_str
        self.assertEqual(lines, report_orga.fetch_all_lines(user=self.user))

    def test_fetch_relation_04(self):
        "Sub-report (expanded) with a filter"
        self.login()
        self._aux_test_fetch_persons()
        tyrion = self.tyrion

        tyrion_face = FakeImage.objects.create(name='Tyrion face', user=self.user)
        tyrion.image = tyrion_face
        tyrion.save()

        ptype = CremePropertyType.create(str_pk='test-prop_dwarf', text='Is a dwarf')
        CremeProperty.objects.create(type=ptype, creme_entity=self.tyrion)

        dwarves_filter = EntityFilter.create('test-filter_dwarves', 'Dwarves', FakeContact, is_custom=True)
        dwarves_filter.set_conditions([EntityFilterCondition.build_4_property(ptype, has=True)])

        report_contact = self.report_contact
        report_contact.filter = dwarves_filter
        report_contact.save()

        img_report = self._build_image_report()

        Field.objects.create(report=report_contact, name='image__name', order=3,
                             type=RFT_FIELD, selected=True, sub_report=img_report,
                            )

        report = self.report_orga
        Field.objects.create(report=report, name=FAKE_REL_OBJ_EMPLOYED_BY, order=2,
                             type=RFT_RELATION, selected=True, sub_report=self.report_contact,
                             )

        self.assertEqual([[self.lannisters.name, tyrion.last_name, tyrion.first_name, tyrion_face.name, ''],
                          [self.starks.name,     '',               '',                '',               ''],
                         ],
                         report.fetch_all_lines()
                        )

    def test_fetch_relation_05(self):
        "Several expanded sub-reports"
        user = self.login()
        self._aux_test_fetch_persons()
        tyrion = self.tyrion; ned = self.ned; robb = self.robb; starks = self.starks

        report_orga = self.report_orga
        create_field = partial(Field.objects.create, type=RFT_RELATION)
        create_field(report=report_orga, name=FAKE_REL_OBJ_EMPLOYED_BY, order=2,
                     selected=True, sub_report=self.report_contact,
                    )

        folder = FakeReportsFolder.objects.create(user=user, title='Ned folder')

        create_doc = partial(FakeReportsDocument.objects.create, user=user)
        doc1 = create_doc(title='Sword',  linked_folder=folder, description='Blbalabla')
        doc2 = create_doc(title='Helmet', linked_folder=folder)

        rtype = RelationType.objects.get(pk=REL_SUB_HAS)
        doc_report = self._create_simple_documents_report()
        create_field(report=self.report_contact, name=rtype.id, order=3,
                     selected=True, sub_report=doc_report,
                    )

        create_rel = partial(Relation.objects.create, type=rtype, user=user, subject_entity=ned)
        create_rel(object_entity=doc1)
        create_rel(object_entity=doc2)

        self.assertEqual([_('Name'), _('Last name'), _('First name'), _('Title'), _('Description')],
                         [column.title for column in report_orga.get_children_fields_flat()]
                        )
        self.assertEqual([[self.lannisters.name, tyrion.last_name, tyrion.first_name, '',         ''],

                          # Beware Documents are ordered by title
                          [starks.name,          ned.last_name,    ned.first_name,    doc2.title, ''],
                          [starks.name,          ned.last_name,    ned.first_name,    doc1.title, doc1.description],

                          [starks.name,          robb.last_name,   robb.first_name,   '',         '']
                         ],
                         report_orga.fetch_all_lines()
                        )

    def _aux_test_fetch_aggregate(self, invalid_ones=False):
        user = self.login()
        self._aux_test_fetch_persons(create_contacts=False, report_4_contact=False)

        # Should not be used in aggregate
        self.guild = FakeOrganisation.objects.create(name='Guild of merchants', user=user, capital=700)

        create_cf = partial(CustomField.objects.create, content_type=self.ct_orga)
        self.cf = cf = create_cf(name='Gold', field_type=CustomField.INT)
        str_cf = create_cf(name='Motto', field_type=CustomField.STR)

        fmt = '{}__max'.format
        create_field = partial(Field.objects.create, report=self.report_orga,
                               selected=False, sub_report=None,
                              )
        create_field(name='capital__sum', order=2, type=RFT_AGG_FIELD)
        create_field(name=fmt(cf.id),     order=3, type=RFT_AGG_CUSTOM)

        if invalid_ones:
            create_field(name=fmt(1000),          order=4, type=RFT_AGG_CUSTOM)  # Invalid CustomField id
            create_field(name='capital__invalid', order=5, type=RFT_AGG_FIELD)   # Invalid aggregation
            create_field(name='invalid__sum',     order=6, type=RFT_AGG_FIELD)   # Invalid field (unknown)
            create_field(name='name__sum',        order=7, type=RFT_AGG_FIELD)   # Invalid field (bad type)
            create_field(name=fmt(str_cf.id),     order=8, type=RFT_AGG_CUSTOM)  # Invalid CustomField (bad type)
            create_field(name='{}__additionalarg__max'.format(cf.id),
                         order=9, type=RFT_AGG_CUSTOM,
                        )  # Invalid string

    def test_fetch_aggregate_01(self):
        "Regular field, Custom field (valid & invalid ones)"
        self._aux_test_fetch_aggregate(invalid_ones=True)
        starks = self.starks; lannisters = self.lannisters
        starks.capital = 500;      starks.save()
        lannisters.capital = 1000; lannisters.save()

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=self.cf)
        create_cfval(entity=starks,     value=100)
        create_cfval(entity=lannisters, value=500)
        create_cfval(entity=self.guild, value=50)  # Should not be used

        report = self.refresh(self.report_orga)
        self.assertEqual(3, len(report.columns))

        self.assertEqual([[lannisters.name, 1500, 500],
                          [starks.name,     1500, 500],
                         ],
                         report.fetch_all_lines()
                        )

    def test_fetch_aggregate_02(self):
        "Regular field, Custom field (valid & invalid ones): None replaced by 0"
        self._aux_test_fetch_aggregate()
        self.assertEqual([[self.lannisters.name, 0, 0],
                          [self.starks.name,     0, 0],
                         ],
                         self.report_orga.fetch_all_lines()
                        )

    def test_fetch_aggregate_03(self):
        "Aggregate in sub-lines (expanded sub-report)"
        user = self.login()
        self._aux_test_fetch_persons(create_contacts=False, report_4_contact=False)

        report_invoice = Report.objects.create(user=user, name='Report on invoices',
                                               ct=ContentType.objects.get_for_model(FakeInvoice)
                                              )

        create_field = partial(Field.objects.create, selected=False, sub_report=None)
        create_field(report=report_invoice, name='name',           type=RFT_FIELD,     order=1)
        create_field(report=report_invoice, name='total_vat__sum', type=RFT_AGG_FIELD, order=2)

        report = self.report_orga
        create_field(report=report, name=FAKE_REL_OBJ_BILL_ISSUED, order=2,
                     selected=True, sub_report=report_invoice, type=RFT_RELATION,
                    )

        starks = self.starks; lannisters = self.lannisters

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        guild = create_orga(name='Guild of merchants')
        hord  = create_orga(name='Hord')

        create_invoice = partial(self._create_invoice, target=guild)
        invoice1 = create_invoice(starks,     name='Invoice#1', total_vat=Decimal('100.5'))
        invoice2 = create_invoice(lannisters, name='Invoice#2', total_vat=Decimal('200.5'))
        invoice3 = create_invoice(lannisters, name='Invoice#3', total_vat=Decimal('50.1'))
        create_invoice(hord, name='Invoice#4', total_vat=Decimal('1000'))  # Should not be used

        total_lannisters = invoice2.total_vat + invoice3.total_vat
        total_starks     = invoice1.total_vat
        self.assertEqual([[lannisters.name, invoice2.name, total_lannisters],
                          [lannisters.name, invoice3.name, total_lannisters],
                          [starks.name,     invoice1.name, total_starks],
                         ],
                         report.fetch_all_lines()
                        )
