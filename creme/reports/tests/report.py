# -*- coding: utf-8 -*-

try:
    from datetime import datetime, date
    from decimal import Decimal
    from functools import partial
    #from itertools import chain

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.utils.datastructures import SortedDict as OrderedDict
    from django.utils.translation import ugettext as _
    from django.utils.encoding import smart_str
    from django.utils.unittest.case import skipIf
    #from django.core.serializers.json import simplejson

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME, REL_SUB_HAS
    from creme.creme_core.models import (RelationType, Relation, SetCredentials,
        EntityFilter, EntityFilterCondition, CustomField, CustomFieldInteger,
        CremePropertyType, CremeProperty, HeaderFilterItem, HeaderFilter)
    from creme.creme_core.models.header_filter import (HFI_FIELD, HFI_CUSTOM,
            HFI_RELATION, HFI_FUNCTION, HFI_CALCULATED, HFI_RELATED)
    from creme.creme_core.tests.base import skipIfNotInstalled

    from creme.documents.models import Folder, Document

    from creme.media_managers.models import Image, MediaCategory

    from creme.persons.models import Contact, Organisation, LegalForm
    from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_OBJ_EMPLOYED_BY, REL_OBJ_CUSTOMER_SUPPLIER

    if 'creme.billing' in settings.INSTALLED_APPS:
        from creme.billing.constants import REL_OBJ_BILL_ISSUED
        from creme.billing.models import Invoice

    #from creme.opportunities.models import Opportunity
    from creme.opportunities.constants import REL_SUB_EMIT_ORGA

    from creme.emails.models import EmailCampaign, MailingList

    from ..models import Field, Report
    from .base import BaseReportsTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


try:
    from creme.creme_core.utils.xlrd_utils import XlrdReader
    from creme.creme_core.registry import export_backend_registry
    XlsImport = not 'xls' in export_backend_registry.iterkeys()
except Exception as e:
    XlsImport = True


__all__ = ('ReportTestCase',)


class ReportTestCase(BaseReportsTestCase):
    def assertHeaders(self, names, report):
        self.assertEqual(names, [f.name for f in report.get_children_fields_flat()])

    def _build_contacts_n_images(self):
        user = self.user

        create_img = Image.objects.create
        self.ned_face   = create_img(name='Ned face',  user=self.other_user)
        self.aria_face  = create_img(name='Aria face', user=user)

        create_contact = partial(Contact.objects.create, user=user)
        self.ned  = create_contact(first_name='Eddard', last_name='Stark', image=self.ned_face)
        self.robb = create_contact(first_name='Robb',   last_name='Stark', user=self.other_user)
        self.aria = create_contact(first_name='Aria',   last_name='Stark', image=self.aria_face)

        self.efilter = EntityFilter.create('test-filter', 'Starks', Contact, is_custom=True)
        self.efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                         operator=EntityFilterCondition.IEQUALS,
                                                                         name='last_name', values=[self.ned.last_name]
                                                                        )
                                    ])

    def _create_cf_int(self):
        return CustomField.objects.create(content_type=ContentType.objects.get_for_model(Contact),
                                          name='Size (cm)', field_type=CustomField.INT
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

    def login_as_basic_user(self):
        self.login(is_superuser=False,
                   allowed_apps=('creme_core', 'documents', 'persons', 'reports', 'media_managers'),
                  )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

    def test_portal(self):
        self.login()
        self.assertGET200('/reports/')

    #def test_report_createview01(self):
        #cf = self._create_cf_int()

        #url = self.ADD_URL
        #response = self.assertGET200(url)

        #with self.assertNoException():
            #response.context['form'].fields['regular_fields']

        #name = 'My report on Contact'
        #data = {'user': self.user.pk,
                #'name': name,
                #'ct':   ContentType.objects.get_for_model(Contact).id,
               #}
        #self.assertFormError(self.client.post(url, data=data), 'form', None,
                             #[_(u"You must select an existing view, or at least one field from : %s") %
                                #', '.join([_(u'Regular fields'), _(u'Related fields'),
                                           #_(u'Custom fields'), _(u'Relations'), _(u'Functions'),
                                           #_(u'Maximum'), _(u'Sum'), _(u'Average'), _(u'Minimum'),
                                          #])
                             #]
                            #)

        #response = self.client.post(url, follow=True,
                                    #data=dict(data,
                                              #**{'regular_fields_check_%s' % 1: 'on',
                                                 #'regular_fields_value_%s' % 1: 'last_name',
                                                 #'regular_fields_order_%s' % 1: 1,

                                                 #'custom_fields_check_%s' %  1: 'on',
                                                 #'custom_fields_value_%s' %  1: cf.id,
                                                 #'custom_fields_order_%s' %  1: 2,
                                                #}
                                             #)
                                   #)
        #self.assertNoFormError(response)

        #report = self.get_object_or_fail(Report, name=name)
        #columns = list(report.columns.all())
        #self.assertEqual(2, len(columns))

        #field = columns[0]
        #self.assertEqual('last_name',     field.name)
        #self.assertEqual(_(u'Last name'), field.title)
        #self.assertEqual(HFI_FIELD,       field.type)
        #self.assertFalse(field.selected)
        #self.assertFalse(field.report)

        #field = columns[1]
        #self.assertEqual(str(cf.id), field.name)
        #self.assertEqual(cf.name,    field.title)
        #self.assertEqual(HFI_CUSTOM, field.type)

    #def test_report_createview02(self):
    def test_report_createview01(self):
        self.login()
        cf = self._create_cf_int()

        name  = 'trinita'
        self.assertFalse(Report.objects.filter(name=name).exists())

        report = self._create_report(name, extra_hfitems=[HeaderFilterItem.build_4_customfield(cf)])
        self.assertEqual(self.user, report.user)
        self.assertEqual(Contact,   report.ct.model_class())
        self.assertIsNone(report.filter)

        columns = list(report.columns.all())
        self.assertEqual(5, len(columns))

        field = columns[0]
        self.assertEqual('last_name',     field.name)
        self.assertEqual(_(u'Last name'), field.title)
        self.assertEqual(HFI_FIELD,       field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.sub_report)

        self.assertEqual('user', columns[1].name)

        field = columns[2]
        self.assertEqual(REL_SUB_HAS,  field.name)
        self.assertEqual(_(u'owns'),   field.title)
        self.assertEqual(HFI_RELATION, field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.sub_report)

        field = columns[3]
        self.assertEqual('get_pretty_properties', field.name)
        self.assertEqual(_(u'Properties'),        field.title)
        self.assertEqual(HFI_FUNCTION,            field.type)

        field = columns[4]
        self.assertEqual(str(cf.id), field.name)
        self.assertEqual(cf.name,    field.title)
        self.assertEqual(HFI_CUSTOM, field.type)

    #def test_report_createview03(self):
    def test_report_createview02(self):
        "With EntityFilter"
        self.login()
        efilter = EntityFilter.create('test-filter', 'Mihana family', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=['Mihana']
                                                                   )
                               ])

        report  = self._create_report('My awesome report', efilter)
        self.assertEqual(efilter, report.filter)

    def test_report_createview03(self):
        "Validation errors"
        self.login()

        def post(hf_id, filter_id):
            return self.assertPOST200(self.ADD_URL, follow=True,
                                      data={'user':   self.user.pk,
                                            'name':   'Report #1',
                                            'ct':     ContentType.objects.get_for_model(Contact).id,
                                            'hf':     hf_id,
                                            'filter': filter_id,
                                           }
                                     )

        response = post('unknown', 'unknown')
        msg = _('Select a valid choice. That choice is not one of the available choices.')
        self.assertFormError(response, 'form', 'hf',     msg)
        self.assertFormError(response, 'form', 'filter', msg)

        hf = HeaderFilter.create(pk='test_hf', name='name', model=Organisation)
        efilter = EntityFilter.create('test-filter', 'Bad filter', Organisation, is_custom=True)
        response = post(hf.id, efilter.id)
        self.assertFormError(response, 'form', 'hf',     msg)
        self.assertFormError(response, 'form', 'filter', msg)

    def test_report_editview(self):
        self.login()

        name = 'my report'
        report = self._create_report(name)
        url = '/reports/report/edit/%s' % report.id
        self.assertGET200(url)

        name = name.title()
        response = self.client.post(url, follow=True, 
                                    data={'user': self.user.pk,
                                          'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(report).name)

    def test_listview(self):
        self.login()

        reports = [self._create_report('Report#1'),
                   self._create_report('Report#2'),
                  ]

        response = self.assertGET200('/reports/reports')

        with self.assertNoException():
            reports_page = response.context['entities']

        for report in reports:
            self.assertIn(report, reports_page.object_list)

    def test_preview(self):
        self.login()

        create_c = partial(Contact.objects.create, user=self.user)
        chiyo = create_c(first_name='Chiyo', last_name='Mihana', birthday=datetime(year=1995, month=3, day=26))
        osaka = create_c(first_name='Ayumu', last_name='Kasuga', birthday=datetime(year=1990, month=4, day=1))

        report = self._create_report('My report')
        url = '/reports/report/preview/%s' % report.id

        response = self.assertGET200(url)
        self.assertTemplateUsed('reports/preview_report.html')
        self.assertContains(response, chiyo.last_name)
        self.assertContains(response, osaka.last_name)

        response = self.assertPOST200(url,
                                      data={'date_filter_0': '',
                                            'date_filter_1': '1990-01-01',
                                            'date_filter_2': '1990-12-31',
                                            'date_field':    'birthday',
                                           }
                                     )
        self.assertTemplateUsed('reports/preview_report.html')
        self.assertNoFormError(response)
        self.assertContains(response, osaka.last_name)
        self.assertNotContains(response, chiyo.last_name)

    def test_report_change_field_order01(self):
        self.login()

        url = self.SET_FIELD_ORDER_URL
        self.assertPOST404(url)

        report = self._create_report('trinita')
        field  = self.get_field_or_fail(report, 'user')
        response = self.client.post(url, data={'report_id': report.id,
                                               'field_id':  field.id,
                                               'direction': 'up',
                                              }
                                   )
        self.assertNoFormError(response)

        report = self.refresh(report) #seems useless but...
        self.assertEqual(['user', 'last_name', REL_SUB_HAS, 'get_pretty_properties'],
                         [f.name for f in report.columns.order_by('order')]
                        )

    def test_report_change_field_order02(self):
        self.login()

        report = self._create_report('trinita')
        field  = self.get_field_or_fail(report, 'user')
        self.assertPOST200(self.SET_FIELD_ORDER_URL,
                           data={'report_id': report.id,
                                 'field_id':  field.id,
                                 'direction': 'down',
                                }
                          )

        report = self.refresh(report) #seems useless but...
        self.assertEqual(['last_name', REL_SUB_HAS, 'user', 'get_pretty_properties'],
                         [f.name for f in report.columns.order_by('order')]
                        )

    def test_report_change_field_order03(self):
        "Move 'up' the first field -> error"
        self.login()

        report = self._create_report('trinita')
        field  = self.get_field_or_fail(report, 'last_name')
        self.assertPOST403(self.SET_FIELD_ORDER_URL,
                           data={'report_id': report.id,
                                 'field_id':  field.id,
                                 'direction': 'up',
                                }
                          )

    def test_date_filter_form01(self):
        self.login()

        report = self._create_report('My report')
        url = '/reports/date_filter_form/%s' % report.id
        response = self.assertGET200(url)

        date_field = 'birthday'
        response = self.assertPOST200(url,
                                      data={'date_filter_0': '',
                                            'date_filter_1': '1990-01-01',
                                            'date_filter_2': '1990-12-31',
                                            'date_field':    date_field,
                                           }
                                     )
        self.assertNoFormError(response)

        with self.assertNoException():
            callback_url = response.context['callback_url']

        self.assertEqual('/reports/report/export/%s/?field=%s'
                                                   '&range_name=base_date_range'
                                                   '&start=01|01|1990|00|00|00'
                                                   '&end=31|12|1990|23|59|59' % (
                                report.id, date_field,
                            ),
                         callback_url
                        )

    def test_date_filter_form02(self):
        self.login()

        report = self._create_report('My report')
        url = '/reports/date_filter_form/%s' % report.id
        response = self.assertGET200(url)

        date_field = 'birthday'
        response = self.assertPOST200(url, data={'date_field': date_field,
                                                 'date_filter_0': '',
                                                }
                                     )
        self.assertFormError(response, 'form', 'date_filter',
                             [_(u"If you chose a Date field, and select «customized» "
                                 "you have to specify a start date and/or an end date."
                               )
                             ]
                            )

    def test_date_filter_form03(self):
        self.login()

        report = self._create_report('My report')
        url = '/reports/date_filter_form/%s' % report.id
        response = self.assertGET200(url)

        date_field = ''
        doc_type = 'csv'
        response = self.client.post(url, data={'doc_type':      doc_type,
                                               'date_filter_0': '',
                                               'date_field':    date_field,
                                              }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            callback_url = response.context['callback_url']

        self.assertEqual('/reports/report/export/%s/%s' % (
                                report.id, doc_type,
                            ),
                         callback_url
                        )

    @skipIfNotInstalled('creme.billing')
    def test_report_csv01(self):
        "Empty report"
        self.login()

        self.assertFalse(Invoice.objects.all())

        rt = RelationType.objects.get(pk=REL_SUB_HAS)
        hf = HeaderFilter.create(pk='test_hf', name='Invoice view', model=Invoice)
        hf.set_items([HeaderFilterItem.build_4_field(model=Invoice, name='name'),
                      HeaderFilterItem.build_4_field(model=Invoice, name='user'),
                      HeaderFilterItem.build_4_relation(rt),
                      HeaderFilterItem.build_4_functionfield(Invoice.function_fields.get('get_pretty_properties')),
                     ])

        report = self.create_from_view('Report on invoices', Invoice, hf)

        response = self.assertGET200('/reports/report/export/%s/csv' % report.id)
        self.assertEqual('text/html; charset=utf-8', response.request['CONTENT_TYPE'])
        self.assertEqual(smart_str('"%s","%s","%s","%s"\r\n' % (
                                      _(u'Name'), _(u'Owner user'), rt.predicate, _(u'Properties')
                                    )
                                  ),
                         response.content
                        )

    def test_report_csv02(self):
        self.login()

        self._create_persons()
        self.assertEqual(4, Contact.objects.count()) #create_persons + Fulbert

        report   = self._create_report('trinita')
        response = self.assertGET200('/reports/report/export/%s/csv' % report.id)

        content = [s for s in response.content.split('\r\n') if s]
        self.assertEqual(5, len(content)) #4 contacts + header
        self.assertEqual(smart_str('"%s","%s","%s","%s"' % (
                                      _(u'Last name'), _(u'Owner user'), _(u'owns'), _(u'Properties')
                                    )
                                  ),
                         content[0]
                        )
        self.assertEqual('"Ayanami","Kirika","","Kawaii"', content[1]) #alphabetical ordering ??
        self.assertEqual('"Creme","root","",""',           content[2])
        self.assertEqual('"Katsuragi","Kirika","Nerv",""', content[3])
        self.assertEqual('"Langley","Kirika","",""',       content[4])

    def test_report_csv03(self):
        "With date filter"
        self.login()

        self._create_persons()
        report   = self._create_report('trinita')
        response = self.assertGET200('/reports/report/export/%s/csv' % report.id,
                                     data={'field': 'birthday',
                                           'start': datetime(year=1980, month=1, day=1).strftime('%d|%m|%Y|%H|%M|%S'),
                                           'end':   datetime(year=2000, month=1, day=1).strftime('%d|%m|%Y|%H|%M|%S'),
                                          }
                                    )

        content = [s for s in response.content.split('\r\n') if s]
        self.assertEqual(3, len(content))
        self.assertEqual('"Ayanami","Kirika","","Kawaii"', content[1])
        self.assertEqual('"Langley","Kirika","",""',       content[2])

    @skipIf(XlsImport, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_report_xls(self):
        "With date filter"
        self.login()

        self._create_persons()
        report   = self._create_report('trinita')
        response = self.assertGET200('/reports/report/export/%s/xls' % report.id,
                                     data={'field': 'birthday',
                                           'start': datetime(year=1980, month=1, day=1).strftime('%d|%m|%Y|%H|%M|%S'),
                                           'end':   datetime(year=2000, month=1, day=1).strftime('%d|%m|%Y|%H|%M|%S'),
                                          },
                                     follow=True,
                                    )
        result = list(XlrdReader(None, file_contents=response.content))

        self.assertEqual(3, len(result))
        self.assertEqual(["Ayanami", "Kirika", "", "Kawaii"], result[1])
        self.assertEqual(["Langley", "Kirika", "", ""],       result[2])

    #def test_get_related_fields(self):
        #url = '/reports/get_related_fields'
        #self.assertGET404(url)

        #get_ct = ContentType.objects.get_for_model

        #def post(model):
            #response = self.assertPOST200(url, data={'ct_id': get_ct(model).id})
            #return simplejson.loads(response.content)

        #self.assertEqual([], post(Organisation))
        #self.assertEqual([['document', _('Document')]],
                         #post(Folder)
                        #)

    def _find_choice(self, searched, choices):
        for i, (k, v) in enumerate(choices):
            if k == searched:
                return i
        else:
            self.fail('No "%s" choice' % searched)

    def _build_editfields_url(self, report):
        return '/reports/report/%s/field/add' % report.id

    def test_add_field01(self):
        self.login()

        report = self._create_simple_contacts_report('Report #1')
        url = self._build_editfields_url(report)
        response = self.assertGET200(url)

        rfield = report.columns.all()[0]

        with self.assertNoException():
            choices = response.context['form'].fields['regular_fields'].choices

        f_name = 'last_name'
        rf_index = self._find_choice(f_name, choices)
        response = self.client.post(url, data={'user': self.user.pk,
                                               'regular_fields_check_%s' % rf_index: 'on',
                                               'regular_fields_value_%s' % rf_index: f_name,
                                               'regular_fields_order_%s' % rf_index: 1,
                                              }
                                   )
        self.assertNoFormError(response)

        columns = list(report.columns.all())
        self.assertEqual(1, len(columns))

        column = columns[0]
        self.assertEqual(f_name,          column.name)
        self.assertEqual(_(u'Last name'), column.title)
        self.assertEqual(1,               column.order)
        self.assertEqual(HFI_FIELD,       column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)
        self.assertEqual(rfield.id, column.id)
        self.assertEqual(rfield,    column)

    def test_add_field02(self):
        "Custom field, aggregate on CustomField; additional old Field deleted"
        self.login()

        cf = self._create_cf_int()

        report = self._create_report('My beloved Report')
        old_rfields = list(report.columns.all())
        self.assertEqual(4, len(old_rfields))

        url = self._build_editfields_url(report)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            rf_choices = fields['regular_fields'].choices
            cf_choices = fields['custom_fields'].choices

            max_choices = fields['max'].choices
            min_choices = fields['min'].choices
            sum_choices = fields['sum'].choices
            avg_choices = fields['avg'].choices

        f_name = 'last_name'
        rf_index = self._find_choice(f_name, rf_choices)

        cf_id = str(cf.id)
        cf_index = self._find_choice(cf_id, cf_choices)

        aggr_id_base = 'cf__%s__%s' % (cf.field_type, cf_id)
        aggr_id = aggr_id_base + '__max'
        aggr_index = self._find_choice(aggr_id, max_choices)
        self._find_choice(aggr_id_base + '__min', min_choices)
        self._find_choice(aggr_id_base + '__sum', sum_choices)
        self._find_choice(aggr_id_base + '__avg', avg_choices)

        response = self.client.post(url, data={'user': self.user.pk,
                                               'regular_fields_check_%s' % rf_index: 'on',
                                               'regular_fields_value_%s' % rf_index: f_name,
                                               'regular_fields_order_%s' % rf_index: 1,

                                               'custom_fields_check_%s' %  cf_index: 'on',
                                               'custom_fields_value_%s' %  cf_index: cf_id,
                                               'custom_fields_order_%s' %  cf_index: 1,

                                               'max_check_%s' %  aggr_index: 'on',
                                               'max_value_%s' %  aggr_index: aggr_id,
                                               'max_order_%s' %  aggr_index: 1,
                                              }
                                   )
        self.assertNoFormError(response)

        columns = list(report.columns.all())
        self.assertEqual(3, len(columns))

        column = columns[0]
        self.assertEqual(f_name, column.name)
        self.assertEqual(old_rfields[0].id, column.id)

        column = columns[1]
        self.assertEqual(cf_id,      column.name)
        self.assertEqual(cf.name,    column.title)
        self.assertEqual(2,          column.order)
        self.assertEqual(HFI_CUSTOM, column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)
        self.assertEqual(old_rfields[1].id, column.id)

        column = columns[2]
        self.assertEqual(aggr_id,                             column.name)
        self.assertEqual('%s - %s' % (_('Maximum'), cf.name), column.title)
        self.assertEqual(3,                                   column.order)
        self.assertEqual(HFI_CALCULATED,                      column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)
        self.assertEqual(old_rfields[2].id, column.id)

        self.assertDoesNotExist(old_rfields[3])

    def test_add_field03(self):
        "Other types: relationships, function fields"
        self.login()

        report = self._create_report('My beloved Report')

        url = self._build_editfields_url(report)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            rf_choices = fields['regular_fields'].choices
            rt_choices = fields['relations'].choices
            ff_choices = fields['functions'].choices

        f_name = 'last_name'
        rf_index = self._find_choice(f_name, rf_choices)

        rtype_id = REL_SUB_EMPLOYED_BY
        rtype = self.get_object_or_fail(RelationType, pk=rtype_id)
        rt_index = self._find_choice(rtype_id, rt_choices)

        funfield = Contact.function_fields.get('get_pretty_properties')
        self.assertIsNotNone(funfield)
        ff_index = self._find_choice(funfield.name, ff_choices)

        response = self.client.post(url, data={'user': self.user.pk,
                                               'regular_fields_check_%s' % rf_index: 'on',
                                               'regular_fields_value_%s' % rf_index: f_name,
                                               'regular_fields_order_%s' % rf_index: 1,

                                               'relations_check_%s' %  rt_index: 'on',
                                               'relations_value_%s' %  rt_index: rtype_id,
                                               'relations_order_%s' %  rt_index: 1,

                                               'functions_check_%s' %  ff_index: 'on',
                                               'functions_value_%s' %  ff_index: funfield.name,
                                               'functions_order_%s' %  ff_index: 1,
                                              }
                                   )
        self.assertNoFormError(response)

        columns = list(report.columns.all())
        self.assertEqual(3, len(columns))

        self.assertEqual(f_name, columns[0].name)

        column = columns[1]
        self.assertEqual(rtype_id,        column.name)
        self.assertEqual(rtype.predicate, column.title)
        self.assertEqual(2,               column.order)
        self.assertEqual(HFI_RELATION,    column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)

        column = columns[2]
        self.assertEqual(funfield.name,         column.name)
        self.assertEqual(funfield.verbose_name, column.title)
        self.assertEqual(3,                     column.order)
        self.assertEqual(HFI_FUNCTION,          column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)

    def test_add_field04(self):
        "Aggregate on regular fields"
        self.login()

        ct = ContentType.objects.get_for_model(Organisation)
        report = Report.objects.create(name='Secret report', ct=ct, user=self.user)

        url = self._build_editfields_url(report)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            rf_choices = fields['regular_fields'].choices
            max_choices = fields['max'].choices
            min_choices = fields['min'].choices

        f_name = 'name'
        rf_index = self._find_choice(f_name, rf_choices)

        vname = _('Capital')
        self.assertEqual([('capital__max', vname)], max_choices)
        aggr_id = 'capital__min'
        self.assertEqual([(aggr_id, vname)], min_choices)

        response = self.client.post(url, data={'user': self.user.pk,
                                               'regular_fields_check_%s' % rf_index: 'on',
                                               'regular_fields_value_%s' % rf_index: f_name,
                                               'regular_fields_order_%s' % rf_index: 1,

                                               'min_check_%s' %  0: 'on',
                                               'min_value_%s' %  0: aggr_id,
                                               'min_order_%s' %  0: 1,
                                              }
                                   )
        self.assertNoFormError(response)

        columns = list(report.columns.all())
        self.assertEqual(2, len(columns))

        self.assertEqual(f_name, columns[0].name)

        column = columns[1]
        self.assertEqual(aggr_id,                           column.name)
        self.assertEqual('%s - %s' % (_('Minimum'), vname), column.title)
        self.assertEqual(2,                                 column.order)
        self.assertEqual(HFI_CALCULATED,                    column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)

    def test_add_field05(self):
        "Related entity"
        self.login()

        ct = ContentType.objects.get_for_model(Folder)
        report = Report.objects.create(name='Folder report', ct=ct, user=self.user)

        url = self._build_editfields_url(report)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            rf_choices = fields['regular_fields'].choices
            rel_choices = fields['related_fields'].choices

        f_name = 'title'
        rf_index = self._find_choice(f_name, rf_choices)

        rel_name = 'document'
        rel_index = self._find_choice(rel_name, rel_choices)

        response = self.client.post(url, data={'user': self.user.pk,
                                               'regular_fields_check_%s' % rf_index: 'on',
                                               'regular_fields_value_%s' % rf_index: f_name,
                                               'regular_fields_order_%s' % rf_index: 1,

                                               'related_fields_check_%s' %  rel_index: 'on',
                                               'related_fields_value_%s' %  rel_index: rel_name,
                                               'related_fields_order_%s' %  rel_index: 1,
                                              }
                                   )
        self.assertNoFormError(response)

        columns = list(report.columns.all())
        self.assertEqual(2, len(columns))

        self.assertEqual(f_name, columns[0].name)

        column = columns[1]
        self.assertEqual(rel_name,      column.name)
        self.assertEqual(_('Document'), column.title)
        self.assertEqual(2,             column.order)
        self.assertEqual(HFI_RELATED,   column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)

    def _build_image_report(self):
        img_report = Report.objects.create(user=self.user, name="Report on images",
                                           ct=ContentType.objects.get_for_model(Image),
                                          )
        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FIELD)
        img_report.columns = [
            create_field(name="name",        title="Name",        order=1),
            create_field(name="description", title="Description", order=2),
          ]

        return img_report

    def _build_orga_report(self):
        orga_report = Report.objects.create(user=self.user, name="Report on organisations",
                                            ct=ContentType.objects.get_for_model(Organisation),
                                           )
        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FIELD)
        orga_report.columns = [
            create_field(name="name",              title="Name",               order=1),
            create_field(name="legal_form__title", title="Legal form - title", order=2),
          ]

        return orga_report

    def test_link_report01(self):
        "HFI_FIELD (FK) field"
        self.login()

        contact_report = Report.objects.create(user=self.user, name="Report on contacts", 
                                               ct=ContentType.objects.get_for_model(Contact),
                                              )

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FIELD)
        contact_report.columns = rfields = [
            create_field(name="last_name",             title="Last name",      order=1),
            create_field(name="sector__title",         title="Sector - Title", order=2),
            create_field(name="image__name",           title="Image - Name",   order=3),
            create_field(name="get_pretty_properties", title="Properties",     order=4, type=HFI_FUNCTION),
          ]

        img_report = self._build_image_report()

        url_fmt = '/reports/report/%s/field/%s/link_report'
        self.assertGET404(url_fmt % (contact_report.id, rfields[3].id)) #not a HFI_FIELD Field
        self.assertGET404(url_fmt % (contact_report.id, rfields[0].id)) #not a FK field
        self.assertGET404(url_fmt % (contact_report.id, rfields[1].id)) #not a FK to a CremeEntity

        rfield = rfields[2]
        url = url_fmt % (contact_report.id, rfield.id)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'report': img_report.id}))

        rfield = self.refresh(rfield)
        self.assertEqual(img_report, rfield.sub_report)

        #unlink --------------------------------------------------------------
        rfield.selected = True
        rfield.save()
        url = '/reports/report/field/unlink_report'
        self.assertGET404(url)
        self.assertPOST404(url, data={'field_id': rfields[0].id})
        self.assertPOST200(url, data={'field_id': rfield.id})

        rfield = self.refresh(rfield)
        self.assertIsNone(rfield.sub_report)
        self.assertFalse(rfield.selected)

    def test_link_report02(self):
        "HFI_RELATION field"
        self.login()

        get_ct = ContentType.objects.get_for_model
        contact_report = Report.objects.create(user=self.user, ct=get_ct(Contact),
                                               name="Report on contacts",
                                              )

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FIELD)
        contact_report.columns = rfields = [
            create_field(name='last_name',         title="Last name",      order=1),
            create_field(name=REL_SUB_EMPLOYED_BY, title="Is employed by", order=2, type=HFI_RELATION),
          ]

        orga_ct = get_ct(Organisation)
        orga_report = self._build_orga_report()

        url_fmt = '/reports/report/%s/field/%s/link_relation_report/%s'
        self.assertGET404(url_fmt % (contact_report.id, rfields[0].id, orga_ct.id)) #not a HFI_RELATION Field
        self.assertGET404(url_fmt % (contact_report.id, rfields[1].id, get_ct(Image).id)) #ct not compatible

        url = url_fmt % (contact_report.id, rfields[1].id, orga_ct.id)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'report': orga_report.id}))
        self.assertEqual(orga_report, self.refresh(rfields[1]).sub_report)

    def test_link_report03(self):
        "HFI_RELATED field"
        self.login()

        self.assertEqual([('document', _(u'Document'))],
                         Report.get_related_fields_choices(Folder)
                        )
        get_ct = ContentType.objects.get_for_model
        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FIELD)
        create_report = partial(Report.objects.create, user=self.user, filter=None)

        folder_report = create_report(name="Report on folders", ct=get_ct(Folder))
        folder_report.columns = rfields = [
            create_field(name='title',    title='Title',    order=1),
            create_field(name='document', title='Document', order=2, type=HFI_RELATED),
          ]

        doc_report = create_report(name="Documents report", ct=get_ct(Document))
        doc_report.columns = [
            create_field(name='title',       title='Title',       order=1),
            create_field(name="description", title='Description', order=2),
          ]

        url_fmt = '/reports/report/%s/field/%s/link_related_report'
        self.assertGET404(url_fmt % (folder_report.id, rfields[0].id)) #not a HFI_RELATION Field

        url = url_fmt % (folder_report.id, rfields[1].id)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'report': doc_report.id}))
        self.assertEqual(doc_report, self.refresh(rfields[1]).sub_report)

    def test_link_report04(self):
        "Cycle error"
        self.login()

        get_ct = ContentType.objects.get_for_model
        contact_report = Report.objects.create(user=self.user, ct=get_ct(Contact),
                                               name="Report on contacts",
                                              )

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_RELATION)
        contact_report.columns = rfields = [
            create_field(name='last_name',         title="Last name",      order=1, type=HFI_FIELD),
            create_field(name=REL_SUB_EMPLOYED_BY, title="Is employed by", order=2),
          ]

        orga_ct = get_ct(Organisation)
        orga_report = self._build_orga_report()
        orga_report.columns.add(
            create_field(name=REL_OBJ_EMPLOYED_BY, title="Employs", order=3, sub_report=contact_report),
        )

        url = '/reports/report/%s/field/%s/link_relation_report/%s' % (contact_report.id, rfields[1].id, orga_ct.id)
        self.assertGET200(url)

        response = self.assertPOST200(url, data={'report': orga_report.id})
        self.assertFormError(response, 'form', 'report', _(u"This entity doesn't exist."))

    def test_set_selected(self):
        self.login()

        img_report = self._build_image_report()
        orga_report = self._build_orga_report()

        contact_report = Report.objects.create(user=self.user, name="Report on contacts",
                                               ct=ContentType.objects.get_for_model(Contact),
                                              )
        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FIELD)
        contact_report.columns = rfields = [
            create_field(name="last_name",         title="Last name",      order=1),
            create_field(name="image__name",       title="Image - Name",   order=2, sub_report=img_report),
            create_field(name=REL_SUB_EMPLOYED_BY, title="Is employed by", order=3, 
                         sub_report=orga_report, type=HFI_RELATION, selected=True,
                        ),
          ]

        url = '/reports/report/field/set_selected'
        self.assertGET404(url)

        data = {'report_id': contact_report.id, 
                'field_id':  rfields[0].id,
                'checked':   1,
               }
        self.assertPOST404(url, data=data)

        fk_rfield = rfields[1]
        rel_rfield = rfields[2]
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

    def _aux_test_fetch_persons(self, create_contacts=True, create_relations=True, report_4_contact=True):
        user = self.user

        if create_contacts:
            #self._create_contacts()
            create_contact = partial(Contact.objects.create, user=user)
            self.ned    = create_contact(first_name='Eddard', last_name='Stark')
            self.robb   = create_contact(first_name='Robb',   last_name='Stark')
            self.tyrion = create_contact(first_name='Tyrion', last_name='Lannister')

        create_orga = partial(Organisation.objects.create, user=user)
        self.starks     = create_orga(name='House Stark')
        self.lannisters = create_orga(name='House Lannister')

        if create_contacts and create_relations:
            create_rel = partial(Relation.objects.create, type_id=REL_OBJ_EMPLOYED_BY, user=user)
            create_rel(subject_entity=self.starks, object_entity=self.ned)
            create_rel(subject_entity=self.starks, object_entity=self.robb)
            create_rel(subject_entity=self.lannisters, object_entity=self.tyrion)

        efilter = EntityFilter.create('test-filter', 'Houses', Organisation, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='name', values=['House '],
                                                                   )
                               ])

        get_ct = ContentType.objects.get_for_model
        create_report = partial(Report.objects.create, user=self.user, filter=None)

        if report_4_contact:
            self.report_contact = create_report(name="Report on Contacts", ct=get_ct(Contact))

            create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FIELD)
            self.report_contact.columns = [
                create_field(name='last_name',  title="Last name",  order=1),
                create_field(name='first_name', title="First name", order=2),
            ]

        self.report_orga = create_report(name="Report on Organisations", ct=get_ct(Organisation), filter=efilter)
        self.report_orga.columns = [
                Field.objects.create(name='name', title="Name", order=1, type=HFI_FIELD, selected=False, sub_report=None), #TODO: use create_field
            ]

    def test_fetch_field_01(self):
        self.login()

        create_contact = partial(Contact.objects.create, user=self.user)
        for i in xrange(5):
            create_contact(last_name='Mister %s' % i)

        create_contact(last_name='Mister X', is_deleted=True)

        report = self._create_simple_contacts_report("Contacts report")
        #self.assertEqual(set(Contact.objects.filter(is_deleted=False)
                                            #.values_list('last_name', flat=True)
                            #),
                         #set(chain.from_iterable(report.fetch()))
                        #)
        self.assertEqual([[ln] for ln in Contact.objects.filter(is_deleted=False)
                                                        .values_list('last_name', flat=True)
                         ],
                         report.fetch_all_lines()
                        )

    def test_fetch_field_02(self):
        "FK, date, filter"
        self.login()

        self._aux_test_fetch_persons(report_4_contact=False, create_contacts=False, create_relations=False)

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FIELD)
        self.report_orga.columns.add(
            create_field(name='user__username',    title="User - username",    order=2),
            create_field(name='legal_form__title', title="Legal form - title", order=3),
            create_field(name='creation_date',     title="Date of creation",   order=4),
          )

        starks = self.starks
        starks.legal_form = lform = LegalForm.objects.get_or_create(title="Hord")[0]
        starks.creation_date = date(year=2013, month=9, day=24)
        starks.save()

        username = self.user.username
        self.assertEqual([[self.lannisters.name, username, '',          ''],
                          [starks.name,          username, lform.title, '2013-09-24'],
                         ],
                         self.report_orga.fetch_all_lines()
                        )

    def test_fetch_field_03(self):
        "View credentials"
        self.login_as_basic_user()

        self._aux_test_fetch_persons(report_4_contact=False, create_contacts=False, create_relations=False)

        self.report_orga.columns.add(Field.objects.create(name='image__name', title="Image - Name",
                                                          order=2, selected=False, sub_report=None, type=HFI_FIELD,
                                                         ),
                                    )
        baratheons = Organisation.objects.create(user=self.other_user, name='House Baratheon')
        self.assertFalse(self.user.has_perm_to_view(baratheons))

        create_img     = Image.objects.create
        starks_img     = create_img(name='Stark emblem',     user=self.user)
        lannisters_img = create_img(name='Lannister emblem', user=self.other_user)
        self.assertTrue(self.user.has_perm_to_view(starks_img))
        self.assertFalse(self.user.has_perm_to_view(lannisters_img))

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
        self.assertEqual(lines, fetch_all_lines(user=self.other_user)) #super user

        lines.pop(0)
        lines[0][1] = settings.HIDDEN_VALUE #lannisters_img not visible
        self.assertEqual(lines, fetch_all_lines(user=self.user))

    @skipIfNotInstalled('creme.billing')
    @skipIfNotInstalled('creme.opportunities')
    def test_fetch_complex(self): #TODO: move
        self.login()

        self._create_reports()
        self._setUp_data_for_big_report()
        user = self.user

        nintendo = self.nintendo; sega = self.sega; sony = self.sony; virgin = self.virgin
        crash = self.crash; luigi = self.luigi; mario = self.mario; sonic = self.sonic

        #targeted_organisations = [self.nintendo, self.sega, self.virgin, self.sony]

        #Target only own created organisations
        #Organisation.objects.exclude(id__in=[o.id for o in targeted_organisations]).delete()
        Contact.objects.exclude(id__in=[c.id for c in (crash, sonic, mario, luigi)]).delete() #TODO: use a filter in the report instead

        # Invoices report
        invoice_headers = ['name', 'total_vat__sum']
        self.assertHeaders(invoice_headers, self.report_invoice)

        nintendo_invoice_1 = ["Invoice 1", Decimal("12.00")]
        nintendo_invoice_2 = ["Invoice 2", Decimal("12.00")]
        self.assertEqual([nintendo_invoice_1, nintendo_invoice_2],
                         self.report_invoice.fetch_all_lines(user=user)
                        )

        # Organisations report
        orga_headers = ['name'] + invoice_headers + \
                       [REL_OBJ_CUSTOMER_SUPPLIER, REL_SUB_EMIT_ORGA, 'capital__min']
        self.assertHeaders(orga_headers, self.report_orga)

        create_rel = partial(Relation.objects.create, subject_entity=nintendo,
                             type_id=REL_OBJ_CUSTOMER_SUPPLIER, user=user,
                            )
        create_rel(object_entity=sony)
        create_rel(object_entity=sega)

        opportunity_nintendo_1 = self.create_opportunity(name="Opportunity nintendo 1", reference="1.1", emitter=nintendo)
        opp_nintendo_values = u"%s: %s - %s: %s" % (
                                    _(u"Name of the opportunity"), opportunity_nintendo_1.name,
                                    _(u"Reference"),               opportunity_nintendo_1.reference,
                                )
        min_capital = nintendo.capital

        orga_data = OrderedDict([
            ("nintendo_invoice1", [nintendo.name] + nintendo_invoice_1 + [u'%s, %s' % (sony, sega), opp_nintendo_values, min_capital]),
            ("nintendo_invoice2", [nintendo.name] + nintendo_invoice_2 + [u'%s, %s' % (sony, sega), opp_nintendo_values, min_capital]),
            ("sega",              [sega.name,       '', '',               '',                       '',                  min_capital]),
            ("sony",              [sony.name,       '', '',               '',                       '',                  min_capital]),
            ("virgin",            [virgin.name,     '', '',               '',                       '',                  min_capital]),
        ])
        self.assertListContainsSubset(orga_data.values(), self.report_orga.fetch_all_lines(user=user))

        #update minimum capital no narrow by orga (sub-report)
        orga_data['sony'][-1] = sony.capital
        orga_data['sega'][-1] = sega.capital
        #orga_data['virgin'][-1] = virgin.capital #useless

        # Contacts report
        self.assertHeaders(['last_name', 'first_name'] + orga_headers, self.report_contact)
        self.assertEqual([[crash.last_name, crash.first_name] + orga_data['sony'],
                          [luigi.last_name, luigi.first_name] + orga_data['nintendo_invoice1'],
                          [luigi.last_name, luigi.first_name] + orga_data['nintendo_invoice2'],
                          [mario.last_name, mario.first_name] + orga_data['nintendo_invoice1'],
                          [mario.last_name, mario.first_name] + orga_data['nintendo_invoice2'],
                          [sonic.last_name, sonic.first_name] + orga_data['sega'],
                        ],
                       self.report_contact.fetch_all_lines()
                      )

    def _aux_test_fetch_documents(self, efilter=None, selected=True):
        get_ct = ContentType.objects.get_for_model
        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FIELD)
        create_report = partial(Report.objects.create, user=self.user, filter=None)

        self.folder_report = create_report(name="Folders report", ct=get_ct(Folder), filter=efilter)
        self.folder_report.columns = [
            create_field(name='title',       title='Title',       order=1),
            create_field(name='description', title='Description', order=2),
          ]

        self.doc_report = create_report(name="Documents report", ct=get_ct(Document))
        self.doc_report.columns = [
            create_field(name='title',         title='Title',       order=1),
            create_field(name='description',   title='Description', order=2),
            create_field(name='folder__title', title='Folders',     order=3,
                         sub_report=self.folder_report, selected=selected,
                        ),
        ]

        create_folder = partial(Folder.objects.create, user=self.user)
        self.folder1 = create_folder(title='Internal')
        self.folder2 = create_folder(title='External', description='Boring description')

        create_doc = partial(Document.objects.create, user=self.user)
        self.doc1 = create_doc(title='Doc#1', folder=self.folder1, description='Blbalabla')
        self.doc2 = create_doc(title='Doc#2', folder=self.folder2)

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

        efilter = EntityFilter.create('test-filter', 'Internal folders', Folder, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Folder,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='title', values=['Inter']
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
        "Sub report (not expanded)"
        self.login()
        self._aux_test_fetch_documents(selected=False)

        doc1 = self.doc1; folder2 = self.folder2
        fmt = '%s: %%s - %s: %%s' % (_(u'Title'), _(u'Description'))
        self.assertEqual([[doc1.title,      doc1.description, fmt % (self.folder1.title, '')],
                          [self.doc2.title, '',               fmt % (folder2.title,      folder2.description)],
                         ],
                         self.doc_report.fetch_all_lines()
                        )

    def test_fetch_cf_01(self):
        "Custom fields"
        self.login()

        create_contact = partial(Contact.objects.create, user=self.user)
        ned  = create_contact(first_name='Eddard', last_name='Stark')
        robb = create_contact(first_name='Robb',   last_name='Stark')
        aria = create_contact(first_name='Aria',   last_name='Stark')

        efilter = EntityFilter.create('test-filter', 'Starks', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=[ned.last_name]
                                                                   )
                               ])

        cf = self._create_cf_int()
        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=ned,  value=190)
        create_cfval(entity=aria, value=150)

        report = self._create_report('Contacts with CField', efilter=efilter)

        create_field = partial(Field.objects.create, selected=False, sub_report=None)
        report.columns = [ #TODO: create Field builder like HFI...
            create_field(name='first_name', title='First Name', type=HFI_FIELD,  order=1),
            create_field(name=cf.id,        title=cf.name,      type=HFI_CUSTOM, order=2),
            create_field(name=1024,         title='Invalid',    type=HFI_CUSTOM, order=3), #simulates deleted CustomField
          ]

        self.assertEqual([[aria.first_name, '150', ''],
                          [ned.first_name,  '190', ''],
                          [robb.first_name, '',    ''],
                         ],
                         report.fetch_all_lines()
                        )

    def test_fetch_cf_02(self):
        "In FK, credentials"
        self.login_as_basic_user()
        user = self.user

        self._build_contacts_n_images()
        ned_face = self.ned_face; aria_face = self.aria_face

        get_ct = ContentType.objects.get_for_model
        cf = CustomField.objects.create(content_type=get_ct(Image),
                                        name='Popularity', field_type=CustomField.INT
                                       )

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=ned_face,  value=190)
        create_cfval(entity=aria_face, value=150)

        create_report = partial(Report.objects.create, user=user, filter=None)
        report_img = create_report(name="Report on Images", ct=get_ct(Image))

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FIELD)
        report_img.columns = [create_field(name='name', title="Name",  order=1),
                              create_field(name=cf.id,  title=cf.name, order=2, type=HFI_CUSTOM),
                             ]

        report_contact = create_report(name="Report on Contacts", ct=get_ct(Contact), filter=self.efilter)
        report_contact.columns = [create_field(name='first_name',  title='First Name',   order=1),
                                  create_field(name='image__name', title='Image - Name', order=2,
                                               sub_report=report_img, selected=True,
                                              ),
                                 ]

        lines = [[self.aria.first_name, aria_face.name, '150'],
                 [self.ned.first_name,  ned_face.name,  '190'],
                 [self.robb.first_name, '',             ''],
                ]
        self.assertEqual(lines, report_contact.fetch_all_lines())

        lines.pop() #robb is not visible
        ned_line = lines[1]
        ned_line[1] = ned_line[2] = settings.HIDDEN_VALUE #ned_face is not visible
        self.assertEqual(lines, report_contact.fetch_all_lines(user=user))

    def test_fetch_m2m_01(self):
        "No sub report"
        self.login()

        hf = HeaderFilter.create(pk='test_hf', name='Campaign view', model=EmailCampaign)

        build_hfi = partial(HeaderFilterItem.build_4_field, model=EmailCampaign)
        hf.set_items([build_hfi(name='name'), build_hfi(name='mailing_lists__name')])

        report = self.create_from_view('Campaign Report', EmailCampaign, hf)

        create_camp = partial(EmailCampaign.objects.create, user=self.user)
        name1 = 'Camp#1'; camp1 = create_camp(name=name1)
        name2 = 'Camp#2'; camp2 = create_camp(name=name2)

        create_ml = partial(MailingList.objects.create, user=self.user)
        camp1.mailing_lists = [create_ml(name='ML#1'), create_ml(name='ML#2')]
        camp2.mailing_lists = [create_ml(name='ML#3')]

        self.assertHeaders(['name', 'mailing_lists__name'], report)
        self.assertEqual([[name1, 'ML#1, ML#2'],
                          [name2, 'ML#3'],
                         ],
                         report.fetch_all_lines()
                        )

    def _aux_test_fetch_m2m(self):
        self.login()
        user = self.user

        create_ptype = CremePropertyType.create
        self.ptype1 = create_ptype(str_pk='test-prop_important',    text='Important')
        self.ptype2 = create_ptype(str_pk='test-prop_notimportant', text='Not important')

        hf_camp = HeaderFilter.create(pk='test_hf_camp', name='Campaign view', model=EmailCampaign)
        hf_ml   = HeaderFilter.create(pk='test_hf_ml',   name='MList view',    model=MailingList)

        build_hfi = partial(HeaderFilterItem.build_4_field, model=EmailCampaign)
        hf_camp.set_items([build_hfi(name='name'), build_hfi(name='mailing_lists__name')])
        hf_ml.set_items([build_hfi(name='name', model=MailingList),
                         HeaderFilterItem.build_4_functionfield(
                                MailingList.function_fields.get('get_pretty_properties')
                            ),
                        ]
                       )

        create_report = self.create_from_view
        self.report_camp = create_report('Campaign Report', EmailCampaign, hf_camp)
        self.report_ml   = create_report('Campaign ML',     MailingList,   hf_ml)

        create_camp = partial(EmailCampaign.objects.create, user=user)
        self.camp1 = create_camp(name='Camp#1')
        self.camp2 = create_camp(name='Camp#2')
        self.camp3 = create_camp(name='Camp#3') #empty one

        create_ml = partial(MailingList.objects.create, user=user)
        self.ml1 = ml1 = create_ml(name='ML#1')
        self.ml2 = ml2 = create_ml(name='ML#2')
        self.ml3 = ml3 = create_ml(name='ML#3')

        self.camp1.mailing_lists = [ml1, ml2]
        self.camp2.mailing_lists = [ml3]

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

        #Let's go for the sub-report
        rfield = report_camp.columns.get(name='mailing_lists__name')
        rfield.sub_report = report_ml
        rfield.selected = True
        rfield.save()

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

        #Let's go for the sub-report
        rfield = report_camp.columns.get(name='mailing_lists__name')
        rfield.sub_report = self.report_ml
        rfield.selected = False
        rfield.save()

        report_camp = self.refresh(report_camp)
        self.assertHeaders(['name', 'mailing_lists__name'], report_camp)

        fmt = '%s: %%s - %s: %%s' % (_(u'Name of the mailing list'), '') #TODO: _('Properties')
        self.assertEqual([[self.camp1.name, fmt % (self.ml1.name, '') + ', ' + fmt % (self.ml2.name, '')],
                          [self.camp2.name, fmt % (self.ml3.name, '')],
                          [self.camp3.name, ''],
                         ],
                         report_camp.fetch_all_lines()
                        )

    def test_fetch_m2m_04(self):
        "Not CremeEntity model"
        self.login()

        report = self._build_image_report()
        report.columns.add(
            Field.objects.create(name='categories__name', title="Categories", order=3,
                                 type=HFI_FIELD, selected=False, sub_report=None,
                                ),
           )

        create_img = partial(Image.objects.create, user=self.user)
        img1 = create_img(name='Img#1', description='Pretty picture')
        img2 = create_img(name='Img#2')

        create_cat = MediaCategory.objects.create
        cat1 = create_cat(name='Photo of contact')
        cat2 = create_cat(name='Photo of product')

        img1.categories = [cat1, cat2]

        self.assertEqual([[img1.name, img1.description, u'%s, %s' % (cat1.name, cat2.name)],
                          [img2.name, '',               ''],
                        ],
                        report.fetch_all_lines()
                    )

    def _aux_test_fetch_related(self, select_doc_report=None):
        user = self.user
        get_ct = ContentType.objects.get_for_model
        create_report = partial(Report.objects.create, user=user, filter=None)
        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FIELD)

        if select_doc_report is not None:
            self.doc_report = create_report(name="Documents report", ct=get_ct(Document))
            self.doc_report.columns = [
                create_field(name='title',       title='Title',       order=1),
                create_field(name="description", title='Description', order=2),
            ]
        else:
            self.doc_report = None

        self.folder_report = create_report(name="Report on folders", ct=get_ct(Folder))
        self.folder_report.columns = [
            create_field(name='title',    title='Title',    order=1),
            create_field(name='document', title='Document', order=2, type=HFI_RELATED,
                         sub_report=self.doc_report, selected=select_doc_report or False,
                        ),
          ]

        create_folder = partial(Folder.objects.create, user=user)
        self.folder1 = create_folder(title='Internal')
        self.folder2 = create_folder(title='External')

        create_doc = partial(Document.objects.create, user=user)
        self.doc11 = create_doc(title='Doc#1-1', folder=self.folder1, description='Boring !')
        self.doc12 = create_doc(title='Doc#1-2', folder=self.folder1, user=self.other_user)
        self.doc21 = create_doc(title='Doc#2-1', folder=self.folder2)

    def test_fetch_related_01(self):
        self.login_as_basic_user()

        self._aux_test_fetch_related(select_doc_report=None)

        doc11 = self.doc11; doc12 = self.doc12
        fetch = self.folder_report.fetch_all_lines
        lines = [[self.folder1.title, unicode(doc11) + ', ' + unicode(doc12)],
                 [self.folder2.title, unicode(self.doc21)],
                ]
        self.assertEqual(lines, fetch())

        lines[0][1] = unicode(doc11)
        self.assertEqual(lines, fetch(user=self.user))

    def test_fetch_related_02(self):
        "Sub-report (expanded)"
        self.login_as_basic_user()

        self._aux_test_fetch_related(select_doc_report=True)
        folder3 = Folder.objects.create(user=self.user, title='Empty')

        folder1 = self.folder1; doc11 = self.doc11
        lines = [[folder1.title,      doc11.title,      doc11.description],
                 [folder1.title,      self.doc12.title, ''],
                 [self.folder2.title, self.doc21.title, ''],
                 [folder3.title,      '',               ''],
                ]
        fetch = self.folder_report.fetch_all_lines
        self.assertEqual(lines, fetch())

        lines.pop(1)
        self.assertEqual(lines, fetch(user=self.user))

    def test_fetch_related_03(self):
        "Sub-report (not expanded)"
        self.login_as_basic_user()

        self._aux_test_fetch_related(select_doc_report=False)
        folder3 = Folder.objects.create(user=self.user, title='Empty')

        folder1 = self.folder1; doc11 = self.doc11
        fmt = '%s: %%s - %s: %%s' % (_('Title'), _('Description'))
        doc11_str = fmt % (doc11.title, doc11.description)
        lines = [[folder1.title,      doc11_str + ', ' + fmt % (self.doc12.title, '')],
                 [self.folder2.title, fmt % (self.doc21.title, '')],
                 [folder3.title,      ''],
                ]
        fetch = self.folder_report.fetch_all_lines
        self.assertEqual(lines, fetch())

        lines[0][1] = doc11_str
        self.assertEqual(lines, fetch(user=self.user))

    def test_fetch_funcfield_01(self):
        self.login()

        self._aux_test_fetch_persons(report_4_contact=False, create_contacts=False, create_relations=False)

        ptype = CremePropertyType.objects.get(pk=PROP_IS_MANAGED_BY_CREME)
        CremeProperty.objects.create(type=ptype, creme_entity=self.starks)

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FUNCTION)
        self.report_orga.columns.add(
            create_field(name='get_pretty_properties', title="Properties", order=2),
            create_field(name='invalid_funfield',      title="??",         order=3),
          )

        error_msg = _("Problem with function field")
        self.assertEqual([[self.lannisters.name, '',         error_msg],
                          [self.starks.name,     ptype.text, error_msg],
                         ],
                         self.report_orga.fetch_all_lines()
                        )

    def test_fetch_funcfield_02(self):
        self.login_as_basic_user()
        user = self.user

        self._build_contacts_n_images()
        ned_face = self.ned_face; aria_face = self.aria_face

        self.assertFalse(user.has_perm_to_view(ned_face))
        self.assertTrue(user.has_perm_to_view(aria_face))

        get_ct = ContentType.objects.get_for_model
        create_report = partial(Report.objects.create, user=user, filter=None)
        report_img = create_report(name="Report on Images", ct=get_ct(Image))

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_FIELD)
        report_img.columns = [create_field(name='name', title="Name",  order=1),
                              create_field(name='get_pretty_properties', title="Properties", order=2, type=HFI_FUNCTION),
                             ]

        report_contact = create_report(name="Report on Contacts", ct=get_ct(Contact), filter=self.efilter)
        report_contact.columns = [create_field(name='first_name',  title='First Name',   order=1),
                                  create_field(name='image__name', title='Image - Name', order=2,
                                               sub_report=report_img, selected=True,
                                              ),
                                 ]

        ptype = CremePropertyType.objects.get(pk=PROP_IS_MANAGED_BY_CREME)

        create_prop = partial(CremeProperty.objects.create, type=ptype)
        create_prop(creme_entity=aria_face)
        create_prop(creme_entity=ned_face)

        lines = [[self.aria.first_name, aria_face.name, ptype.text],
                 [self.ned.first_name,  ned_face.name,  ptype.text],
                 [self.robb.first_name, '',             ''],
                ]
        self.assertEqual(lines, report_contact.fetch_all_lines())

        lines.pop() #robb is not visible
        ned_line = lines[1]
        ned_line[1] = ned_line[2] = settings.HIDDEN_VALUE #ned_face is not visible
        self.assertEqual(lines, report_contact.fetch_all_lines(user=user))

    def test_fetch_relation_01(self):
        "No sub-report"
        self.login_as_basic_user()

        self._aux_test_fetch_persons(report_4_contact=False)

        ned = self.ned
        ned.user = self.other_user
        ned.save()

        create_field = partial(Field.objects.create, type=HFI_RELATION, selected=False, sub_report=None)
        self.report_orga.columns.add(
            create_field(name=REL_OBJ_EMPLOYED_BY, title="employs", order=2),
            create_field(name='invalid',           title="??",      order=3),
           )

        fetch = self.report_orga.fetch_all_lines
        lines = [[self.lannisters.name, unicode(self.tyrion),         ''],
                 [self.starks.name,     u'%s, %s' % (ned, self.robb), ''],
                ]
        self.assertEqual(lines, fetch())

        lines[1][1] = unicode(self.robb)
        self.assertEqual(lines, fetch(user=self.user))

    def test_fetch_relation_02(self):
        "Sub-report (expanded)"
        self.login_as_basic_user()
        self._aux_test_fetch_persons()

        report = self.report_orga
        report.columns.add(Field.objects.create(name=REL_OBJ_EMPLOYED_BY, title="employs", order=2,
                                                type=HFI_RELATION, selected=True,
                                                sub_report=self.report_contact,
                                               ),
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

        lines.pop() #robb line removed
        self.assertEqual(lines, report.fetch_all_lines(user=self.user))

    def test_fetch_relation_03(self):
        "Sub-report (not expanded)"
        self.login_as_basic_user()
        self._aux_test_fetch_persons()

        report = self.report_orga
        report.columns.add(Field.objects.create(name=REL_OBJ_EMPLOYED_BY, title="employs", order=2,
                                                type=HFI_RELATION, selected=False,
                                                sub_report=self.report_contact,
                                               ),
                          )
        self.assertHeaders(['name', 'persons-object_employed_by'], report)

        ned = self.ned; robb = self.robb; tyrion = self.tyrion

        robb.user = self.other_user
        robb.save()

        fmt = '%s: %%s - %s: %%s' % (_('Last name'), _('First name'))
        ned_str = fmt % (ned.last_name,  ned.first_name)
        lines = [[self.lannisters.name, fmt % (tyrion.last_name, tyrion.first_name)],
                 [self.starks.name,     ned_str + ', ' + fmt % (robb.last_name, robb.first_name)],
                ]
        self.assertEqual(lines, report.fetch_all_lines())

        lines[1][1] = ned_str
        self.assertEqual(lines, report.fetch_all_lines(user=self.user))

    def test_fetch_relation_04(self):
        "Sub-report (expanded) with a filter"
        self.login()
        self._aux_test_fetch_persons()
        tyrion = self.tyrion

        tyrion_face = Image.objects.create(name='Tyrion face', user=self.user)
        tyrion.image = tyrion_face
        tyrion.save()

        ptype = CremePropertyType.create(str_pk='test-prop_dwarf', text='Is a dwarf')
        CremeProperty.objects.create(type=ptype, creme_entity=self.tyrion)

        dwarves_filter = EntityFilter.create('test-filter_dwarves', 'Dwarves', Contact, is_custom=True)
        dwarves_filter.set_conditions([EntityFilterCondition.build_4_property(ptype, has=True)])

        report_contact = self.report_contact
        report_contact.filter = dwarves_filter
        report_contact.save()

        img_report = self._build_image_report()

        report_contact.columns.add(
            Field.objects.create(name='image__name', title="Name", order=3,
                                 type=HFI_FIELD, selected=True, sub_report=img_report,
                                ),
           )

        report = self.report_orga
        report.columns.add(Field.objects.create(name=REL_OBJ_EMPLOYED_BY, title="employs", order=2,
                                                type=HFI_RELATION, selected=True,
                                                sub_report=self.report_contact,
                                               ),
                          )

        self.assertEqual([[self.lannisters.name, tyrion.last_name, tyrion.first_name, tyrion_face.name, ''],
                          [self.starks.name,     '',               '',                '',               ''],
                         ],
                         report.fetch_all_lines()
                        )

    def _aux_test_fetch_calculated(self):
        self.login()

        self._aux_test_fetch_persons(create_contacts=False, report_4_contact=False)

        #should not be used in aggregate
        self.guild = Organisation.objects.create(name='Guild of merchants', user=self.user, capital=700)

        self.cf = cf = CustomField.objects.create(content_type=ContentType.objects.get_for_model(Organisation),
                                                  name='Gold', field_type=CustomField.INT
                                                 )

        fmt = ('cf__%s' % cf.field_type) + '__%s__max'
        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=HFI_CALCULATED)
        self.report_orga.columns.add(
            create_field(name='capital__sum', title="Sum - Capital", order=2),
            create_field(name=fmt % cf.id,    title="Sum - Gold",    order=3),
            create_field(name=fmt % 1000,     title="Invalid",       order=4),
        )

    def test_fetch_calculated_01(self):
        "Regular field, Custom field (valid & invalid ones)"
        self._aux_test_fetch_calculated()
        starks = self.starks; lannisters = self.lannisters
        starks.capital = 500;      starks.save()
        lannisters.capital = 1000; lannisters.save()

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=self.cf)
        create_cfval(entity=starks,     value=100)
        create_cfval(entity=lannisters, value=500)
        create_cfval(entity=self.guild, value=50) #should not be used

        self.assertEqual([[lannisters.name, 1500, 500, ''],
                          [starks.name,     1500, 500, ''],
                         ],
                         self.report_orga.fetch_all_lines()
                        )

    def test_fetch_calculated_02(self):
        "Regular field, Custom field (valid & invalid ones): None replaced by 0"
        self._aux_test_fetch_calculated()
        self.assertEqual([[self.lannisters.name, 0, 0, ''],
                          [self.starks.name,     0, 0, ''],
                         ],
                         self.report_orga.fetch_all_lines()
                        )

    @skipIfNotInstalled('creme.billing')
    def test_fetch_calculated_03(self):
        "Aggregate in sub-lines (expanded sub-report)"
        self.login()
        self._aux_test_fetch_persons(create_contacts=False, report_4_contact=False)

        report_invoice = Report.objects.create(user=self.user, name="Report on invoices",
                                               ct=ContentType.objects.get_for_model(Invoice)
                                              )

        create_field = partial(Field.objects.create, selected=False, sub_report=None)
        report_invoice.columns = [
            create_field(name='name',           title="Name",                         type=HFI_FIELD,      order=1),
            create_field(name='total_vat__sum', title="Sum - Total inclusive of tax", type=HFI_CALCULATED, order=2),
          ]

        report = self.report_orga
        report.columns.add(
            create_field(name=REL_OBJ_BILL_ISSUED, title="has issued", order=2,
                         selected=True, sub_report=report_invoice, type=HFI_RELATION,
                        ),
        )

        starks = self.starks; lannisters = self.lannisters

        create_orga = partial(Organisation.objects.create, user=self.user)
        guild = create_orga(name='Guild of merchants')
        hord  = create_orga(name='Hord')

        create_invoice = partial(self._create_invoice, target=guild)
        invoice1 = create_invoice(starks,     name="Invoice#1", total_vat=Decimal('100.5'))
        invoice2 = create_invoice(lannisters, name="Invoice#2", total_vat=Decimal('200.5'))
        invoice3 = create_invoice(lannisters, name="Invoice#3", total_vat=Decimal('50.1'))
        create_invoice(hord, name="Invoice#4", total_vat=Decimal('1000')) #should not be used

        total_lannisters = invoice2.total_vat + invoice3.total_vat
        total_starks     = invoice1.total_vat
        self.assertEqual([[lannisters.name, invoice2.name, total_lannisters],
                          [lannisters.name, invoice3.name, total_lannisters],
                          [starks.name,     invoice1.name, total_starks],
                         ],
                         report.fetch_all_lines()
                        )

    #def test_get_aggregate_fields(self):
        #url = '/reports/get_aggregate_fields'
        #self.assertGET404(url)
        #self.assertPOST404(url)

        #data = {'ct_id': ContentType.objects.get_for_model(Organisation).id}
        #response = self.assertPOST200(url, data=data)
        #self.assertEqual([], simplejson.loads(response.content))

        #response = self.assertPOST200(url, data=dict(data, aggregate_name='stuff'))
        #self.assertEqual([], simplejson.loads(response.content))

        #response = self.assertPOST200(url, data=dict(data, aggregate_name='sum'))
        #self.assertEqual([['capital__sum', _('Capital')]],
                         #simplejson.loads(response.content)
                        #)


    #def test_get_predicates_choices_4_ct(self):
        #response = self.assertPOST200('/reports/get_predicates_choices_4_ct',
                                      #data={'ct_id': ContentType.objects.get_for_model(Report).id}
                                     #)
        #self.assertEqual('text/javascript', response['Content-Type'])

        #content = simplejson.loads(response.content)
        #self.assertIsInstance(content, list)
        #self.assertTrue(content)

        #def relationtype_2_tuple(rtype_id):
            #rt = RelationType.objects.get(pk=rtype_id)
            #return [rt.id, rt.predicate]

        #self.assertIn(relationtype_2_tuple(REL_SUB_HAS), content)
        #self.assertNotIn(relationtype_2_tuple(REL_SUB_EMPLOYED_BY), content)
