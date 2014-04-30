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
    from django.utils.formats import date_format
    from django.utils.timezone import now
    from django.utils.unittest.case import skipIf
    #from django.core.serializers.json import simplejson

    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME, REL_SUB_HAS
    from creme.creme_core.models import (RelationType, Relation, SetCredentials,
            EntityFilter, EntityFilterCondition, CustomField, CustomFieldInteger,
            CremePropertyType, CremeProperty, HeaderFilter)
    from creme.creme_core.tests.base import skipIfNotInstalled

    from creme.documents.models import Folder, Document

    from creme.media_managers.models import Image, MediaCategory

    from creme.persons.models import Contact, Organisation, LegalForm
    from creme.persons.constants import (REL_SUB_EMPLOYED_BY, REL_OBJ_EMPLOYED_BY,
            REL_OBJ_CUSTOMER_SUPPLIER)

    if 'creme.billing' in settings.INSTALLED_APPS:
        from creme.billing.constants import REL_OBJ_BILL_ISSUED
        from creme.billing.models import Invoice

    if 'creme.emails' in settings.INSTALLED_APPS:
        from creme.emails.models import EmailCampaign, MailingList

    from ..constants import (RFT_FIELD, RFT_CUSTOM, RFT_RELATION, RFT_FUNCTION,
            RFT_AGG_FIELD, RFT_AGG_CUSTOM, RFT_RELATED) #RFT_AGGREGATE
    from ..models import Field, Report
    from .base import BaseReportsTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


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

    def _build_doc_report(self):
        doc_report = Report.objects.create(name="Documents report", user=self.user,
                                           ct=ContentType.objects.get_for_model(Document)
                                          )

        create_field = partial(Field.objects.create, type=RFT_FIELD)
        create_field(report=doc_report, name='title',       order=1)
        create_field(report=doc_report, name="description", order=2)

        return doc_report

    def _build_image_report(self):
        img_report = Report.objects.create(user=self.user, name="Report on images",
                                           ct=ContentType.objects.get_for_model(Image),
                                          )

        create_field = partial(Field.objects.create, report=img_report, selected=False, sub_report=None, type=RFT_FIELD)
        create_field(name="name",        order=1)
        create_field(name="description", order=2)

        return img_report

    def _build_orga_report(self):
        orga_report = Report.objects.create(user=self.user, name="Report on organisations",
                                            ct=ContentType.objects.get_for_model(Organisation),
                                           )

        create_field = partial(Field.objects.create, report=orga_report, selected=False, sub_report=None, type=RFT_FIELD)
        create_field(name="name",              order=1)
        create_field(name="legal_form__title", order=2)

        return orga_report

    def _build_linkreport_url(self, rfield):
        return '/reports/report/field/%s/link_report' % rfield.id

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

    def test_report_createview01(self):
        self.login()
        cf = self._create_cf_int()

        name  = 'trinita'
        self.assertFalse(Report.objects.filter(name=name).exists())

        report = self._create_report(name, extra_cells=[EntityCellCustomField(cf)])
        self.assertEqual(self.user, report.user)
        self.assertEqual(Contact,   report.ct.model_class())
        self.assertIsNone(report.filter)

        columns = report.columns
        self.assertEqual(5, len(columns))

        field = columns[0]
        self.assertEqual('last_name',     field.name)
        self.assertEqual(_(u'Last name'), field.title)
        self.assertEqual(RFT_FIELD,       field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.sub_report)

        field = columns[1]
        self.assertEqual('user',          field.name)
        self.assertEqual(_('Owner user'), field.title)

        field = columns[2]
        self.assertEqual(REL_SUB_HAS,  field.name)
        self.assertEqual(_(u'owns'),   field.title)
        self.assertEqual(RFT_RELATION, field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.sub_report)

        field = columns[3]
        self.assertEqual('get_pretty_properties', field.name)
        self.assertEqual(_(u'Properties'),        field.title)
        self.assertEqual(RFT_FUNCTION,            field.type)

        field = columns[4]
        self.assertEqual(str(cf.id), field.name)
        self.assertEqual(cf.name,    field.title)
        self.assertEqual(RFT_CUSTOM, field.type)

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
        self.assertTemplateUsed(response, 'reports/preview_report.html')
        self.assertContains(response, chiyo.last_name)
        self.assertContains(response, osaka.last_name)

        response = self.assertPOST200(url,
                                      data={'date_filter_0': '',
                                            'date_filter_1': '1990-01-01',
                                            'date_filter_2': '1990-12-31',
                                            'date_field':    'birthday',
                                           }
                                     )
        self.assertTemplateUsed(response, 'reports/preview_report.html')
        self.assertNoFormError(response)
        self.assertContains(response, osaka.last_name)
        self.assertNotContains(response, chiyo.last_name)

    def test_report_change_field_order01(self):
        self.login()

        url = self.SET_FIELD_ORDER_URL
        self.assertPOST404(url)

        report = self._create_report('trinita')
        field  = self.get_field_or_fail(report, 'user')
        response = self.client.post(url, data={'field_id':  field.id,
                                               'direction': 'up',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(['user', 'last_name', REL_SUB_HAS, 'get_pretty_properties'],
                         [f.name for f in report.fields.order_by('order')]
                        )

    def test_report_change_field_order02(self):
        self.login()

        report = self._create_report('trinita')
        field  = self.get_field_or_fail(report, 'user')
        self.assertPOST200(self.SET_FIELD_ORDER_URL,
                           data={'field_id':  field.id,
                                 'direction': 'down',
                                }
                          )
        self.assertEqual(['last_name', REL_SUB_HAS, 'user', 'get_pretty_properties'],
                         [f.name for f in report.fields.order_by('order')]
                        )

    def test_report_change_field_order03(self):
        "Move 'up' the first field -> error"
        self.login()

        report = self._create_report('trinita')
        field  = self.get_field_or_fail(report, 'last_name')
        self.assertPOST403(self.SET_FIELD_ORDER_URL,
                           data={'field_id':  field.id,
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
        hf = HeaderFilter.create(pk='test_hf', name='Invoice view', model=Invoice,
                                 cells_desc=[EntityCellRegularField.build(model=Invoice, name='name'),
                                             EntityCellRegularField.build(model=Invoice, name='user'),
                                             EntityCellRelation(rt),
                                             EntityCellFunctionField(Invoice.function_fields.get('get_pretty_properties')),
                                            ],
                                )

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
        self.assertEqual(6, Contact.objects.count()) #create_persons + users' Contacts

        report   = self._create_report('trinita')
        response = self.assertGET200('/reports/report/export/%s/csv' % report.id)

        content = (s for s in response.content.split('\r\n') if s)
        self.assertEqual(smart_str('"%s","%s","%s","%s"' % (
                                      _(u'Last name'), _(u'Owner user'), _(u'owns'), _(u'Properties')
                                    )
                                  ),
                         content.next()
                        )

        user_str = unicode(self.user)
        self.assertEqual('"Ayanami","%s","","Kawaii"' % user_str,  content.next()) #alphabetical ordering ??
        self.assertEqual('"Bouquet","%s","",""' % self.other_user, content.next())
        self.assertEqual('"Creme","Fulbert C.","",""',             content.next())
        self.assertEqual('"Katsuragi","%s","Nerv",""' % user_str,  content.next())
        self.assertEqual('"Langley","%s","",""' % user_str,        content.next())
        self.assertEqual('"Yumura","%s","",""' % user_str,         content.next())
        self.assertRaises(StopIteration, content.next)

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

        user_str = unicode(self.user)
        self.assertEqual('"Ayanami","%s","","Kawaii"' % user_str, content[1])
        self.assertEqual('"Langley","%s","",""' % user_str,       content[2])

    def test_report_csv04(self):
        "With date filter and registered range"
        self.login()
        user = self.user

        self._create_persons()
        baby_joe = Contact.objects.create(user=user, last_name='Baby', first_name='Joe',
                                          birthday=datetime(year=now().year, month=1, day=1)
                                         )
        report   = self._create_report('trinita')
        response = self.assertGET200('/reports/report/export/%s/csv' % report.id,
                                     data={'field': 'birthday',
                                           'range_name': 'current_year',
                                           'start': datetime(year=1980, month=1, day=1).strftime('%d|%m|%Y|%H|%M|%S'),
                                           'end':   datetime(year=2000, month=1, day=1).strftime('%d|%m|%Y|%H|%M|%S'),
                                          }
                                    )

        content = [s for s in response.content.split('\r\n') if s]
        self.assertEqual(2, len(content))
        self.assertEqual('"Baby","%s","",""' % user, content[1])

    def test_report_csv05(self):
        "Errors: invalid GET param"
        self.login()

        self._create_persons()
        report = self._create_report('trinita')
        url = '/reports/report/export/%s/csv' % report.id #TODO: factorise
        data = {'field': 'birthday',
                'start': datetime(year=1980, month=1, day=1).strftime('%d|%m|%Y|%H|%M|%S'),
                'end':   datetime(year=2000, month=1, day=1).strftime('%d|%m|%Y|%H|%M|%S'),
               }
        count = Contact.objects.count()

        def post(**kwargs):
            response = self.assertGET200(url, data=dict(data, **kwargs))
            self.assertEqual(count + 1, # "+1" for header
                             sum(1 if s else 0 for s in response.content.split('\r\n'))
                            )

        post(field='invalidfield')
        post(field='first_name') #not a date field
        post(start='1980-01-01') #invalid format
        post(end='2000-01-01')   #invalid format

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

        user_str = unicode(self.user)
        self.assertEqual(['Ayanami', user_str, '', 'Kawaii'], result[1])
        self.assertEqual(['Langley', user_str, '', ''],       result[2])

    def _build_editfields_url(self, report):
        return '/reports/report/%s/edit_fields' % report.id

    def test_edit_fields01(self):
        self.login()

        report = self._create_simple_contacts_report('Report #1')
        url = self._build_editfields_url(report)
        self.assertGET200(url)

        old_rfield = report.columns[0]

        self.assertNoFormError(self.client.post(url, data={'columns': 'regular_field-last_name,regular_field-first_name'}))

        columns = self.refresh(report).columns
        self.assertEqual(2, len(columns))

        column = columns[0]
        self.assertEqual('last_name',     column.name)
        self.assertEqual(_(u'Last name'), column.title)
        self.assertEqual(1,               column.order)
        self.assertEqual(RFT_FIELD,       column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)
        self.assertEqual(old_rfield.id, column.id)
        self.assertEqual(old_rfield,    column)

        column = columns[1]
        self.assertEqual('first_name',     column.name)
        self.assertEqual(_(u'First name'), column.title)
        self.assertEqual(2,                column.order)

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
        #aggr_id = 'cf__%s__%s__max' % (cf.field_type, cf_id)
        aggr_id = '%s__max' % cf_id
        response = self.client.post(self._build_editfields_url(report),
                                    data={'columns': 'regular_field-%(rfield)s,custom_field-%(cfield)s,custom_aggregate-%(agg)s,regular_field-%(fkfield)s' % {
                                                            'rfield':  f_name,
                                                            'cfield':  cf_id,
                                                            'agg':     aggr_id,
                                                            'fkfield': fk_name
                                                        }
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
        self.assertEqual('%s - %s' % (_('Maximum'), cf.name), column.title)
        #self.assertEqual(RFT_AGGREGATE,                      column.type)
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

        rtype_id = REL_SUB_EMPLOYED_BY
        rtype = self.get_object_or_fail(RelationType, pk=rtype_id)

        funcfield = Contact.function_fields.get('get_pretty_properties')
        self.assertIsNotNone(funcfield)

        response = self.client.post(self._build_editfields_url(report),
                                    data={'columns': 'relation-%(rtype)s,regular_field-%(rfield)s,function_field-%(ffield)s' % {
                                                            'rfield': f_name,
                                                            'rtype':  rtype_id,
                                                            'ffield': funcfield.name,
                                                        }
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
        self.login()

        report = Report.objects.create(name='Secret report', user=self.user,
                                       ct=ContentType.objects.get_for_model(Organisation),
                                      )
        f_name = 'name'
        aggr_id = 'capital__min'
        response = self.client.post(self._build_editfields_url(report),
                                    data={'columns': 'regular_field-%(rfield)s,regular_aggregate-%(agg)s' % {
                                                            'rfield': f_name,
                                                            'agg':    aggr_id,
                                                        }
                                         }
                                   )
        self.assertNoFormError(response)

        columns = report.columns
        self.assertEqual(2, len(columns))

        self.assertEqual(f_name, columns[0].name)

        column = columns[1]
        self.assertEqual(aggr_id,                              column.name)
        self.assertEqual(_('Minimum') + ' - ' +  _('Capital'), column.title)
        self.assertEqual(2,                                    column.order)
        #self.assertEqual(RFT_AGGREGATE,                       column.type)
        self.assertEqual(RFT_AGG_FIELD,                        column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)

    def test_edit_fields05(self):
        "Related entity"
        self.login()

        report = Report.objects.create(name='Folder report', user=self.user,
                                       ct=ContentType.objects.get_for_model(Folder),
                                      )

        f_name = 'title'
        rel_name = 'document'
        response = self.client.post(self._build_editfields_url(report),
                                    data={'columns': 'regular_field-%(rfield)s,related-%(related)s' % {
                                                            'rfield':  f_name,
                                                            'related': rel_name,
                                                        }
                                              }
                                   )
        self.assertNoFormError(response)

        columns = report.columns
        self.assertEqual(2, len(columns))

        self.assertEqual(f_name, columns[0].name)

        column = columns[1]
        self.assertEqual(rel_name,      column.name)
        self.assertEqual(_('Document'), column.title)
        self.assertEqual(2,             column.order)
        self.assertEqual(RFT_RELATED,   column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.sub_report)

    def test_edit_fields06(self):
        "Edit field with sub-report"
        self.login()

        get_ct = ContentType.objects.get_for_model
        create_report = partial(Report.objects.create, user=self.user)
        report_orga    = create_report(name='Report on Organisations', ct=get_ct(Organisation))
        report_contact = create_report(name="Report on Contacts",      ct=get_ct(Contact))
        report_img     = create_report(name="Report on Images",        ct=get_ct(Image))

        create_field = partial(Field.objects.create, report=report_orga)
        create_field(name=REL_OBJ_EMPLOYED_BY, type=RFT_RELATION, order=1, selected=True, sub_report=report_contact)
        create_field(name='name',              type=RFT_FIELD,    order=2)
        create_field(name='image',             type=RFT_FIELD,    order=3, selected=False, sub_report=report_img)

        response = self.client.post(self._build_editfields_url(report_orga),
                                    data={'columns': 'regular_field-%(rfield1)s,relation-%(rtype)s,regular_field-%(rfield2)s,regular_field-%(rfield3)s' % {
                                                            'rfield1': 'name',
                                                            'rtype': REL_OBJ_EMPLOYED_BY,
                                                            'rfield2': 'description',
                                                            'rfield3': 'image', #TODO: and with image__name ???
                                                        }
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
        self.assertEqual(REL_OBJ_EMPLOYED_BY, column.name)
        self.assertEqual(RFT_RELATION,        column.type)
        self.assertEqual(report_contact  ,    column.sub_report)
        self.assertTrue(column.selected)

        self.assertEqual('description', columns[2].name)

        column = columns[3]
        self.assertEqual('image',    column.name)
        self.assertEqual(RFT_FIELD,  column.type)
        self.assertEqual(report_img, column.sub_report)
        self.assertFalse(column.selected)

    def test_edit_fields_errors(self):
        self.login()

        report = self._create_simple_contacts_report()
        response = self.assertPOST200(self._build_editfields_url(report),
                                      data={'columns': 'regular_field-image__categories'},
                                     )
        self.assertFormError(response, 'form', 'columns', _('Enter a valid value.'))

    def test_invalid_hands(self):
        self.login()
        report = self._create_simple_contacts_report()

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD, order=2)
        rfield = create_field(name='image__categories__name')
        self.assertIsNone(rfield.hand)
        self.assertDoesNotExist(rfield)

        rfield = create_field(name='image__categories')
        self.assertIsNone(rfield.hand)
        self.assertDoesNotExist(rfield)

    def test_link_report_regular(self):
        "RFT_FIELD (FK) field"
        self.login()

        contact_report = Report.objects.create(user=self.user, name="Report on contacts",
                                               ct=ContentType.objects.get_for_model(Contact),
                                              )

        create_field = partial(Field.objects.create, report=contact_report, selected=False, sub_report=None, type=RFT_FIELD)
        str_field    = create_field(name="last_name",             order=1)
        fk_field     = create_field(name="sector__title",         order=2)
        fk_img_field = create_field(name="image__name",           order=3)
        func_field   = create_field(name="get_pretty_properties", order=4, type=RFT_FUNCTION)

        self.assertIsNone(func_field.hand.get_linkable_ctypes())
        self.assertGET409(self._build_linkreport_url(func_field)) #not a RFT_FIELD Field

        self.assertIsNone(str_field.hand.get_linkable_ctypes())
        self.assertGET409(self._build_linkreport_url(str_field)) #not a FK field

        self.assertIsNone(fk_field.hand.get_linkable_ctypes())
        self.assertGET409(self._build_linkreport_url(fk_field)) #not a FK to a CremeEntity

        self.assertEqual([ContentType.objects.get_for_model(Image)],
                         list(fk_img_field.hand.get_linkable_ctypes())
                        )

        img_report = self._build_image_report()
        url = self._build_linkreport_url(fk_img_field)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'report': img_report.id}))

        fk_img_field = self.refresh(fk_img_field)
        self.assertEqual(img_report, fk_img_field.sub_report)
        self.assertTrue(fk_img_field.selected)

        #unlink --------------------------------------------------------------
        fk_img_field.selected = True
        fk_img_field.save()
        url = '/reports/report/field/unlink_report'
        self.assertGET404(url)
        self.assertPOST409(url, data={'field_id': str_field.id})
        self.assertPOST200(url, data={'field_id': fk_img_field.id})

        fk_img_field = self.refresh(fk_img_field)
        self.assertIsNone(fk_img_field.sub_report)
        self.assertFalse(fk_img_field.selected)

    def test_link_report_relation01(self):
        "RelationType has got constraints on CT"
        self.login()

        contact_report = Report.objects.create(user=self.user, name="Report on contacts",
                                               ct=ContentType.objects.get_for_model(Contact),
                                              )

        create_field = partial(Field.objects.create, report=contact_report, selected=False, sub_report=None)
        reg_rfield = create_field(name='last_name',         type=RFT_FIELD,    order=1)
        rel_rfield = create_field(name=REL_SUB_EMPLOYED_BY, type=RFT_RELATION, order=2)

        self.assertGET409(self._build_linkreport_url(reg_rfield)) #not a RFT_RELATION Field

        url = self._build_linkreport_url(rel_rfield)
        self.assertGET200(url)

        #incompatible CT
        response = self.assertPOST200(url, data={'report': self._build_image_report().id})
        self.assertFormError(response, 'form', 'report', _("This entity doesn't exist."))

        orga_report = self._build_orga_report()
        self.assertNoFormError(self.client.post(url, data={'report': orga_report.id}))
        self.assertEqual(orga_report, self.refresh(rel_rfield).sub_report)

    def test_link_report_relation02(self):
        "RelationType hasn't any constraint on CT"
        self.login()

        contact_report = Report.objects.create(user=self.user,
                                               ct=ContentType.objects.get_for_model(Contact),
                                               name="Report on contacts",
                                              )
        rtype = RelationType.create(('reports-subject_obeys',   'obeys to'),
                                    ('reports-object_commands', 'commands'),
                                   )[0]

        create_field = partial(Field.objects.create, report=contact_report, selected=False, sub_report=None)
        reg_rfield = create_field(name='last_name', type=RFT_FIELD,    order=1)
        rel_rfield = create_field(name=rtype.id,    type=RFT_RELATION, order=2)

        url = self._build_linkreport_url(rel_rfield)
        img_report = self._build_image_report()
        self.assertNoFormError(self.client.post(url, data={'report': img_report.id}))
        self.assertEqual(img_report, self.refresh(rel_rfield).sub_report)

    def test_link_report_related(self):
        "RFT_RELATED field"
        self.login()

        self.assertEqual([('document', _(u'Document'))],
                         Report.get_related_fields_choices(Folder)
                        )

        folder_report = Report.objects.create(name="Report on folders", user=self.user,
                                              ct=ContentType.objects.get_for_model(Folder),
                                             )

        create_field = Field.objects.create
        rfield1 = create_field(report=folder_report, name='title',    type=RFT_FIELD,   order=1)
        rfield2 = create_field(report=folder_report, name='document', type=RFT_RELATED, order=2)

        self.assertGET409(self._build_linkreport_url(rfield1)) #not a RFT_RELATION Field

        doc_report = self._build_doc_report()
        url = self._build_linkreport_url(rfield2)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'report': doc_report.id}))
        self.assertEqual(doc_report, self.refresh(rfield2).sub_report)

    def test_link_report_error(self):
        "Cycle error"
        self.login()

        get_ct = ContentType.objects.get_for_model
        contact_report = Report.objects.create(user=self.user, ct=get_ct(Contact),
                                               name="Report on contacts",
                                              )

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=RFT_RELATION)
        create_field(report=contact_report, name='last_name', type=RFT_FIELD, order=1)
        rel_rfield = create_field(report=contact_report, name=REL_SUB_EMPLOYED_BY, order=2)

        orga_report = self._build_orga_report()
        create_field(report=orga_report, name=REL_OBJ_EMPLOYED_BY, title="Employs", order=3, sub_report=contact_report),

        url = self._build_linkreport_url(rel_rfield)
        self.assertGET200(url)

        response = self.assertPOST200(url, data={'report': orga_report.id})
        self.assertFormError(response, 'form', 'report', _(u"This entity doesn't exist."))

        #invalid field -> no 500 error
        rfield = create_field(report=contact_report, name='invalid', type=RFT_FIELD, order=3)
        self.assertGET409(self._build_linkreport_url(rfield))

    def test_link_report_selected(self):
        "selected=True if only one sub-report"
        self.login()

        img_report = self._build_image_report()
        contact_report = Report.objects.create(user=self.user, name="Report on contacts",
                                               ct=ContentType.objects.get_for_model(Contact),
                                              )

        create_field = partial(Field.objects.create, report=contact_report, type=RFT_FIELD)
        create_field(name="last_name",   order=1)
        img_field  = create_field(name="image__name", order=2, sub_report=img_report)
        rel_rfield = create_field(name=REL_SUB_EMPLOYED_BY, order=3, type=RFT_RELATION)


        orga_report = self._build_orga_report()
        self.assertNoFormError(self.client.post(self._build_linkreport_url(rel_rfield),
                                                data={'report': orga_report.id},
                                               )
                              )

        rel_rfield = self.refresh(rel_rfield)
        self.assertEqual(orga_report, rel_rfield.sub_report)
        self.assertFalse(rel_rfield.selected)

        #'columns' property avoid several selected sub-reports
        img_field.selected  = True; img_field.save()
        rel_rfield.selected = True; rel_rfield.save()
        self.assertEqual(1, len([f for f in self.refresh(contact_report).columns if f.selected]))

    def test_set_selected(self):
        self.login()

        img_report = self._build_image_report()
        orga_report = self._build_orga_report()

        contact_report = Report.objects.create(user=self.user, name="Report on contacts",
                                               ct=ContentType.objects.get_for_model(Contact),
                                              )

        create_field = partial(Field.objects.create, report=contact_report, selected=False, sub_report=None, type=RFT_FIELD)
        reg_rfield = create_field(name="last_name",         order=1)
        fk_rfield  = create_field(name="image__name",       order=2, sub_report=img_report)
        rel_rfield = create_field(name=REL_SUB_EMPLOYED_BY, order=3,
                                  sub_report=orga_report, type=RFT_RELATION, selected=True,
                                 )

        url = '/reports/report/field/set_selected'
        self.assertGET404(url)

        data = {'report_id': contact_report.id, 
                'field_id':  reg_rfield.id,
                'checked':   1,
               }
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

    def _aux_test_fetch_persons(self, create_contacts=True, create_relations=True, report_4_contact=True):
        user = self.user

        if create_contacts:
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

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD)

        if report_4_contact:
            self.report_contact = report = create_report(name="Report on Contacts", ct=get_ct(Contact))

            create_field(report=report, name='last_name',  order=1)
            create_field(report=report, name='first_name', order=2)

        self.report_orga = create_report(name="Report on Organisations", ct=get_ct(Organisation), filter=efilter)
        create_field(report=self.report_orga, name='name', order=1)

    def test_fetch_field_01(self):
        self.login()

        create_contact = partial(Contact.objects.create, user=self.user)
        for i in xrange(5):
            create_contact(last_name='Mister %s' % i)

        create_contact(last_name='Mister X', is_deleted=True)

        report = self._create_simple_contacts_report("Contacts report")
        self.assertEqual([[ln] for ln in Contact.objects.filter(is_deleted=False)
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
        starks.legal_form = lform = LegalForm.objects.get_or_create(title="Hord")[0]
        starks.creation_date = date(year=2013, month=9, day=24)
        starks.save()

        username = self.user.username
        self.assertEqual([[self.lannisters.name, username, '',          ''],
                          #[starks.name,          username, lform.title, '2013-09-24'],
                          [starks.name,          username, lform.title, date_format(starks.creation_date, 'DATE_FORMAT')],
                         ],
                         report.fetch_all_lines()
                        )

    def test_fetch_field_03(self):
        "View credentials"
        self.login_as_basic_user()

        self._aux_test_fetch_persons(report_4_contact=False, create_contacts=False, create_relations=False)

        Field.objects.create(report=self.report_orga, name='image__name',
                             order=2, selected=False, sub_report=None, type=RFT_FIELD,
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
        from creme.opportunities.constants import REL_SUB_EMIT_ORGA

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
        opp_nintendo_values = u"%s: %s/%s: %s" % (
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
        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD)

        self.folder_report = Report.objects.create(name="Folders report", user=self.user,
                                                   ct=ContentType.objects.get_for_model(Folder), filter=efilter
                                                  )
        create_field(report=self.folder_report, name='title',       order=1)
        create_field(report=self.folder_report, name='description', order=2)

        self.doc_report = self._build_doc_report()
        create_field(report=self.doc_report, name='folder__title', order=3,
                     sub_report=self.folder_report, selected=selected,
                    )

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
        fmt = '%s: %%s/%s: %%s' % (_(u'Title'), _(u'Description'))
        self.assertEqual([[doc1.title,      doc1.description, fmt % (self.folder1.title, '')],
                          [self.doc2.title, '',               fmt % (folder2.title,      folder2.description)],
                         ],
                         self.doc_report.fetch_all_lines()
                        )

    def test_fetch_fk_04(self):
        "Not Entity, no (sub) attribute"
        self.login()

        self._aux_test_fetch_persons(report_4_contact=False, create_contacts=False, create_relations=False)
        starks = self.starks

        starks.legal_form = lform = LegalForm.objects.get_or_create(title="Hord")[0]
        starks.save()

        report = self.report_orga

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        lf_field   = create_field(name='legal_form', order=2)
        user_field = create_field(name='user',       order=3)

        self.assertEqual(_('Legal form'), lf_field.title)
        self.assertEqual(_('Owner user'), user_field.title)

        user_str = unicode(self.user)
        self.assertEqual([[self.lannisters.name, '',          user_str],
                          [starks.name,          lform.title, user_str],
                         ],
                         report.fetch_all_lines()
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
        report.fields.all().delete()

        create_field = partial(Field.objects.create, report=report, selected=False, sub_report=None)
        create_field(name='first_name', type=RFT_FIELD,  order=1)
        create_field(name=cf.id,        type=RFT_CUSTOM, order=2)
        create_field(name=1024,         type=RFT_CUSTOM, order=3) #simulates deleted CustomField

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

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD)
        create_field(report=report_img, name='name', order=1)
        create_field(report=report_img, name=cf.id,  order=2, type=RFT_CUSTOM)

        report_contact = create_report(name="Report on Contacts", ct=get_ct(Contact), filter=self.efilter)
        create_field(report=report_contact, name='first_name',  order=1)
        create_field(report=report_contact, name='image__name', order=2,
                     sub_report=report_img, selected=True,
                    )

        lines = [[self.aria.first_name, aria_face.name, '150'],
                 [self.ned.first_name,  ned_face.name,  '190'],
                 [self.robb.first_name, '',             ''],
                ]
        self.assertEqual(lines, report_contact.fetch_all_lines())

        lines.pop() #robb is not visible
        ned_line = lines[1]
        ned_line[1] = ned_line[2] = settings.HIDDEN_VALUE #ned_face is not visible
        self.assertEqual(lines, report_contact.fetch_all_lines(user=user))

    @skipIfNotInstalled('creme.emails')
    def test_fetch_m2m_01(self):
        "No sub report"
        self.login()

        hf = HeaderFilter.create(pk='test_hf', name='Campaign view', model=EmailCampaign,
                                 cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                             (EntityCellRegularField, {'name': 'mailing_lists__name'}),
                                            ],
                                )

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

        create_hf = HeaderFilter.create
        hf_camp = create_hf(pk='test_hf_camp', name='Campaign view', model=EmailCampaign,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                        (EntityCellRegularField, {'name': 'mailing_lists__name'}),
                                       ]
                           )
        hf_ml   = create_hf(pk='test_hf_ml', name='MList view', model=MailingList,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                        (EntityCellFunctionField, {'func_field_name': 'get_pretty_properties'}),
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

    @skipIfNotInstalled('creme.emails')
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
        rfield = report_camp.fields.get(name='mailing_lists__name')
        rfield.sub_report = report_ml
        rfield.selected = True
        rfield.save()

        self.assertEqual([ContentType.objects.get_for_model(MailingList)],
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

    @skipIfNotInstalled('creme.emails')
    def test_fetch_m2m_03(self):
        "Sub report (not expanded)"
        self._aux_test_fetch_m2m()

        report_camp = self.report_camp

        #Let's go for the sub-report
        rfield = report_camp.fields.get(name='mailing_lists__name')
        rfield.sub_report = self.report_ml
        rfield.selected = False
        rfield.save()

        report_camp = self.refresh(report_camp)
        self.assertHeaders(['name', 'mailing_lists__name'], report_camp)

        fmt = '%s: %%s/%s: %%s' % (_(u'Name of the mailing list'), _('Properties'))
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

        self.assertEqual(_('Categories') + ' - ' + _('Name of media category'), rfield1.title)
        self.assertEqual(_('Categories'),                                       rfield2.title)

        create_img = partial(Image.objects.create, user=self.user)
        img1 = create_img(name='Img#1', description='Pretty picture')
        img2 = create_img(name='Img#2')

        create_cat = MediaCategory.objects.create
        cat1 = create_cat(name='Photo of contact')
        cat2 = create_cat(name='Photo of product')

        img1.categories = [cat1, cat2]

        cats_str = u'%s, %s' % (cat1.name, cat2.name)
        self.assertEqual([[img1.name, img1.description, cats_str, cats_str],
                          [img2.name, '',               '',       ''],
                        ],
                        report.fetch_all_lines()
                    )

    def _aux_test_fetch_related(self, select_doc_report=None, invalid_one=False):
        user = self.user
        get_ct = ContentType.objects.get_for_model
        create_report = partial(Report.objects.create, user=user, filter=None)
        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD)

        self.doc_report = self._build_doc_report() if select_doc_report is not None else None

        self.folder_report = create_report(name="Report on folders", ct=get_ct(Folder))
        create_field(report=self.folder_report, name='title',    order=1)
        create_field(report=self.folder_report, name='document', order=2,
                     type=RFT_RELATED, sub_report=self.doc_report, selected=select_doc_report or False,
                    )

        if invalid_one:
            create_field(report=self.folder_report, name='invalid', order=3, type=RFT_RELATED)

        create_folder = partial(Folder.objects.create, user=user)
        self.folder1 = create_folder(title='Internal')
        self.folder2 = create_folder(title='External')

        create_doc = partial(Document.objects.create, user=user)
        self.doc11 = create_doc(title='Doc#1-1', folder=self.folder1, description='Boring !')
        self.doc12 = create_doc(title='Doc#1-2', folder=self.folder1, user=self.other_user)
        self.doc21 = create_doc(title='Doc#2-1', folder=self.folder2)

    def test_fetch_related_01(self):
        self.login_as_basic_user()

        self._aux_test_fetch_related(select_doc_report=None, invalid_one=True)

        report = self.refresh(self.folder_report)
        self.assertEqual(2, len(report.columns))

        doc11 = self.doc11; doc12 = self.doc12
        fetch = report.fetch_all_lines
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
        fmt = '%s: %%s/%s: %%s' % (_('Title'), _('Description'))
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

        report = self.report_orga
        create_field = partial(Field.objects.create, report=report,
                               selected=False, sub_report=None, type=RFT_FUNCTION,
                              )
        create_field(name='get_pretty_properties', order=2)
        create_field(name='invalid_funfield',      order=3)

        report = self.refresh(report)
        self.assertEqual(2, len(report.columns)) #invalid column is deleted
        self.assertEqual(2, report.fields.count())

        self.assertEqual([[self.lannisters.name, ''],
                          [self.starks.name,     ptype.text],
                         ],
                         report.fetch_all_lines()
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

        create_field = partial(Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD)
        create_field(report=report_img, name='name',                  order=1)
        create_field(report=report_img, name='get_pretty_properties', order=2, type=RFT_FUNCTION)

        report_contact = create_report(name="Report on Contacts", ct=get_ct(Contact), filter=self.efilter)
        create_field(report=report_contact, name='first_name',  order=1)
        create_field(report=report_contact, name='image__name', order=2,
                     sub_report=report_img, selected=True,
                    )

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
        report = self.report_orga

        ned = self.ned
        ned.user = self.other_user
        ned.save()

        create_field = partial(Field.objects.create, report=report,
                               type=RFT_RELATION, selected=False, sub_report=None,
                              )
        create_field(name=REL_OBJ_EMPLOYED_BY, order=2)
        create_field(name='invalid',           order=3)

        report = self.refresh(report)
        self.assertEqual(2, len(report.columns))
        self.assertEqual(2, report.fields.count())

        fetch = self.report_orga.fetch_all_lines
        lines = [[self.lannisters.name, unicode(self.tyrion)],
                 [self.starks.name,     u'%s, %s' % (ned, self.robb)],
                ]
        self.assertEqual(lines, fetch())

        lines[1][1] = unicode(self.robb)
        self.assertEqual(lines, fetch(user=self.user))

    def test_fetch_relation_02(self):
        "Sub-report (expanded)"
        self.login_as_basic_user()
        self._aux_test_fetch_persons()

        report = self.report_orga
        Field.objects.create(report=report, name=REL_OBJ_EMPLOYED_BY, order=2,
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

        lines.pop() #robb line removed
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
        create_field(report=report_orga, name=REL_OBJ_EMPLOYED_BY, order=2,
                     type=RFT_RELATION, selected=False, sub_report=report_contact,
                    )
        self.assertHeaders(['name', 'persons-object_employed_by'], report_orga)

        ned = self.ned; robb = self.robb; tyrion = self.tyrion

        robb.user = self.other_user
        robb.save()

        ned.image = img = Image.objects.create(name='Ned pic', user=self.user,
                                               description='Ned Stark selfie',
                                              )
        ned.save()

        fmt = '%s: %%s/%s: %%s/%s: %%s/%s: %%s' % (
                    _('Last name'), _('First name'), _(u'Properties'), _(u'Photograph'),
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

        Field.objects.create(report=report_contact, name='image__name', order=3,
                             type=RFT_FIELD, selected=True, sub_report=img_report,
                            )

        report = self.report_orga
        Field.objects.create(report=report, name=REL_OBJ_EMPLOYED_BY, order=2,
                             type=RFT_RELATION, selected=True, sub_report=self.report_contact,
                            )

        self.assertEqual([[self.lannisters.name, tyrion.last_name, tyrion.first_name, tyrion_face.name, ''],
                          [self.starks.name,     '',               '',                '',               ''],
                         ],
                         report.fetch_all_lines()
                        )

    def test_fetch_relation_05(self):
        "Several expanded sub-reports"
        self.login()
        self._aux_test_fetch_persons()
        user = self.user
        tyrion = self.tyrion; ned = self.ned; robb = self.robb; starks = self.starks

        report_orga = self.report_orga
        create_field = partial(Field.objects.create, type=RFT_RELATION)
        create_field(report=report_orga, name=REL_OBJ_EMPLOYED_BY, order=2,
                     selected=True, sub_report=self.report_contact,
                    )

        folder = Folder.objects.create(user=user, title='Ned folder')

        create_doc = partial(Document.objects.create, user=user)
        doc1 = create_doc(title='Sword',  folder=folder, description='Blbalabla')
        doc2 = create_doc(title='Helmet', folder=folder)

        rtype = RelationType.objects.get(pk=REL_SUB_HAS)
        doc_report = self._build_doc_report()
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
                          [starks.name,          ned.last_name,    ned.first_name,    doc1.title, doc1.description],
                          [starks.name,          ned.last_name,    ned.first_name,    doc2.title, ''],
                          [starks.name,          robb.last_name,   robb.first_name,   '',         '']
                         ],
                         report_orga.fetch_all_lines()
                        )

    def _aux_test_fetch_aggregate(self, invalid_ones=False):
        self.login()
        self._aux_test_fetch_persons(create_contacts=False, report_4_contact=False)

        #should not be used in aggregate
        self.guild = Organisation.objects.create(name='Guild of merchants', user=self.user, capital=700)

        create_cf = partial(CustomField.objects.create, content_type=ContentType.objects.get_for_model(Organisation))
        self.cf = cf = create_cf(name='Gold', field_type=CustomField.INT)
        str_cf = create_cf(name='Motto', field_type=CustomField.STR)

        #fmt = ('cf__%s' % cf.field_type) + '__%s__max'
        fmt = '%s__max'
        create_field = partial(Field.objects.create, report=self.report_orga, selected=False,
                               sub_report=None, #type=RFT_AGGREGATE,
                              )
        create_field(name='capital__sum', order=2, type=RFT_AGG_FIELD)
        create_field(name=fmt % cf.id,    order=3, type=RFT_AGG_CUSTOM)

        if invalid_ones:
            create_field(name=fmt % 1000,         order=4, type=RFT_AGG_CUSTOM) #invalid CustomField id
            create_field(name='capital__invalid', order=5, type=RFT_AGG_FIELD) #invalid aggregation
            create_field(name='invalid__sum',     order=6, type=RFT_AGG_FIELD) #invalid field (unknown)
            create_field(name='name__sum',        order=7, type=RFT_AGG_FIELD) #invalid field (bad type)
            create_field(name=fmt % str_cf.id,    order=8, type=RFT_AGG_CUSTOM) #invalid CustomField (bad type)
            #create_field(name='cf__%s__%s__additionalarg__max' % (cf.field_type, cf.id),
            create_field(name='%s__additionalarg__max' % cf.id,
                         order=9, type=RFT_AGG_CUSTOM,
                        ) #invalid string

    def test_fetch_aggregate_01(self):
        "Regular field, Custom field (valid & invalid ones)"
        self._aux_test_fetch_aggregate(invalid_ones=True)
        starks = self.starks; lannisters = self.lannisters
        starks.capital = 500;      starks.save()
        lannisters.capital = 1000; lannisters.save()

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=self.cf)
        create_cfval(entity=starks,     value=100)
        create_cfval(entity=lannisters, value=500)
        create_cfval(entity=self.guild, value=50) #should not be used

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

    @skipIfNotInstalled('creme.billing')
    def test_fetch_aggregate_03(self):
        "Aggregate in sub-lines (expanded sub-report)"
        self.login()
        self._aux_test_fetch_persons(create_contacts=False, report_4_contact=False)

        report_invoice = Report.objects.create(user=self.user, name="Report on invoices",
                                               ct=ContentType.objects.get_for_model(Invoice)
                                              )

        create_field = partial(Field.objects.create, selected=False, sub_report=None)
        create_field(report=report_invoice, name='name',           type=RFT_FIELD,     order=1)
        #create_field(report=report_invoice, name='total_vat__sum', type=RFT_AGGREGATE, order=2)
        create_field(report=report_invoice, name='total_vat__sum', type=RFT_AGG_FIELD, order=2)

        report = self.report_orga
        create_field(report=report, name=REL_OBJ_BILL_ISSUED, order=2,
                     selected=True, sub_report=report_invoice, type=RFT_RELATION,
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
