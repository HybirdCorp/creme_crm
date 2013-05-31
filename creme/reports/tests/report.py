# -*- coding: utf-8 -*-

try:
    from datetime import datetime
    from decimal import Decimal
    from functools import partial
    from itertools import chain

    from django.contrib.contenttypes.models import ContentType
    from django.utils.datastructures import SortedDict as OrderedDict
    from django.utils.translation import ugettext as _
    from django.utils.encoding import smart_str
    from django.utils.unittest.case import skipIf
    from django.core.serializers.json import simplejson

    from creme.creme_core.models import (RelationType, Relation,
                                         EntityFilter, EntityFilterCondition)
    from creme.creme_core.models.header_filter import (HeaderFilterItem, HeaderFilter,
                                                       HFI_FIELD, HFI_RELATION, HFI_FUNCTION)
    from creme.creme_core.constants import REL_SUB_HAS
    from creme.creme_core.utils.meta import get_verbose_field_name, get_instance_field_info

    from creme.documents.models import Folder, Document

    from creme.media_managers.models import Image

    from creme.persons.models import Contact, Organisation
    from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_OBJ_CUSTOMER_SUPPLIER

    from creme.billing.models import Invoice

    from creme.opportunities.models import Opportunity
    from creme.opportunities.constants import REL_SUB_EMIT_ORGA

    from ..models import Field, Report
    from ..models.report import HFI_RELATED
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
    def test_portal(self):
        self.assertGET200('/reports/')

    def test_report_createview01(self):
        url = self.ADD_URL
        response = self.assertGET200(url)

        with self.assertNoException():
            response.context['form'].fields['regular_fields']

        name = 'My report on Contact'
        data = {'user': self.user.pk,
                'name': name,
                'ct':   ContentType.objects.get_for_model(Contact).id,
               }
        self.assertFormError(self.client.post(url, data=data), 'form', None,
                             [_(u"You must select an existing view, or at least one field from : %s") % 
                                ', '.join([_(u'Regular fields'), _(u'Related fields'),
                                           _(u'Custom fields'), _(u'Relations'), _(u'Functions'),
                                           _(u'Maximum'), _(u'Sum'), _(u'Average'), _(u'Minimum'),
                                          ])
                             ]
                            )

        response = self.client.post(url, follow=True,
                                    data=dict(data,
                                              **{'regular_fields_check_%s' % 1: 'on',
                                                 'regular_fields_value_%s' % 1: 'last_name',
                                                 'regular_fields_order_%s' % 1: 1,
                                                }
                                             )
                                   )
        self.assertNoFormError(response)

        report = self.get_object_or_fail(Report, name=name)
        self.assertEqual(1, report.columns.count())

    def test_report_createview02(self):
        name  = 'trinita'
        self.assertFalse(Report.objects.filter(name=name).exists())

        report  = self.create_report(name)
        self.assertEqual(self.user, report.user)
        self.assertEqual(Contact,   report.ct.model_class())
        self.assertIsNone(report.filter)

        columns = list(report.columns.all())
        self.assertEqual(4, len(columns))

        field = columns[0]
        self.assertEqual('last_name',     field.name)
        self.assertEqual(_(u'Last name'), field.title)
        self.assertEqual(HFI_FIELD,       field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.report)

        self.assertEqual('user', columns[1].name)

        field = columns[2]
        self.assertEqual(REL_SUB_HAS,  field.name)
        self.assertEqual(_(u'owns'),   field.title)
        self.assertEqual(HFI_RELATION, field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.report)

        field = columns[3]
        self.assertEqual('get_pretty_properties', field.name)
        self.assertEqual(_(u'Properties'),        field.title)
        self.assertEqual(HFI_FUNCTION,            field.type)

    def test_report_createview03(self):
        efilter = EntityFilter.create('test-filter', 'Mihana family', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=['Mihana']
                                                                   )
                               ])

        report  = self.create_report('My awesome report', efilter)
        self.assertEqual(efilter, report.filter)

    def test_report_editview(self):
        name = 'my report'
        report = self.create_report(name)
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
        reports = [self.create_report('Report#1'),
                   self.create_report('Report#2'),
                  ]

        response = self.assertGET200('/reports/reports')

        with self.assertNoException():
            reports_page = response.context['entities']

        for report in reports:
            self.assertIn(report, reports_page.object_list)

    def test_preview(self):
        create_c  = partial(Contact.objects.create, user=self.user)
        chiyo = create_c(first_name='Chiyo', last_name='Mihana', birthday=datetime(year=1995, month=3, day=26))
        osaka = create_c(first_name='Ayumu', last_name='Kasuga', birthday=datetime(year=1990, month=4, day=1))

        report = self.create_report('My report')
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
        url = self.SET_FIELD_ORDER_URL
        self.assertPOST404(url)

        report = self.create_report('trinita')
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
        report = self.create_report('trinita')
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
        report = self.create_report('trinita')
        field  = self.get_field_or_fail(report, 'last_name')
        self.assertPOST403(self.SET_FIELD_ORDER_URL,
                           data={'report_id': report.id,
                                 'field_id':  field.id,
                                 'direction': 'up',
                                }
                          )

    def test_date_filter_form(self):
        report = self.create_report('My report')
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

    def test_report_csv01(self):
        "Empty report"
        self.assertFalse(Invoice.objects.all())

        rt = RelationType.objects.get(pk=REL_SUB_HAS)
        hf = HeaderFilter.create(pk='test_hf', name='Invoice view', model=Invoice)
        hf.set_items([HeaderFilterItem.build_4_field(model=Invoice, name='name'),
                      HeaderFilterItem.build_4_field(model=Invoice, name='user'),
                      HeaderFilterItem.build_4_relation(rt),
                      HeaderFilterItem.build_4_functionfield(Invoice.function_fields.get('get_pretty_properties')),
                     ])

        name = 'Report on invoices'
        self.assertPOST200(self.ADD_URL, follow=True, #TODO: factorise ??
                           data={'user': self.user.pk,
                                 'name': name,
                                 'ct':   ContentType.objects.get_for_model(Invoice).id,
                                 'hf':   hf.id,
                                }
                          )

        report = self.get_object_or_fail(Report, name=name)

        response = self.assertGET200('/reports/report/export/%s/csv' % report.id)
        self.assertEqual('text/html; charset=utf-8', response.request['CONTENT_TYPE'])
        self.assertEqual(smart_str('"%s","%s","%s","%s"\r\n' % (
                                      _(u'Name'), _(u'User'), rt.predicate, _(u'Properties')
                                    )
                                  ),
                         response.content
                        )

    def test_report_csv02(self):
        self.create_contacts()
        self.assertEqual(4, Contact.objects.count()) #create_contacts + Fulbert

        report   = self.create_report('trinita')
        response = self.assertGET200('/reports/report/export/%s/csv' % report.id)

        content = [s for s in response.content.split('\r\n') if s]
        self.assertEqual(5, len(content)) #4 contacts + header
        self.assertEqual(smart_str('"%s","%s","%s","%s"' % (
                                      _(u'Last name'), _(u'User'), _(u'owns'), _(u'Properties')
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
        self.create_contacts()
        report   = self.create_report('trinita')
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
        self.create_contacts()
        report   = self.create_report('trinita')
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

    def test_get_related_fields(self):
        url = '/reports/get_related_fields'
        self.assertGET404(url)

        get_ct = ContentType.objects.get_for_model

        def post(model):
            response = self.assertPOST200(url, data={'ct_id': get_ct(model).id})
            return simplejson.loads(response.content)

        self.assertEqual([], post(Organisation))
        self.assertEqual([['document', _('Document')]],
                         post(Folder)
                        )

    def test_report_field_add01(self):
        report = self.create_report('trinita')
        url = '/reports/report/%s/field/add' % report.id
        response = self.assertGET200(url)

        with self.assertNoException():
            form = response.context['form']
            choices = form.fields['regular_fields'].choices

        f_name = 'last_name'
        for i, (fname, fvname) in enumerate(choices):
            if fname == f_name: created_index = i; break
        else:
            self.fail('No "last_name" field')

        response = self.client.post(url, data={'user': self.user.pk,
                                               'regular_fields_check_%s' % created_index: 'on',
                                               'regular_fields_value_%s' % created_index: f_name,
                                               'regular_fields_order_%s' % created_index: 1,
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
        self.assertIsNone(column.report)

    #def test_report_field_add02(self): TODO: other types

    def _build_image_report(self):
        img_report = Report.objects.create(user=self.user, name="Report on images",
                                           ct=ContentType.objects.get_for_model(Image),
                                          )
        create_field = partial(Field.objects.create, selected=False, report=None, type=HFI_FIELD)
        img_report.columns = [
            create_field(name="name",        title="Name",        order=1),
            create_field(name="description", title="Description", order=2),
          ]

        return img_report

    def _build_orga_report(self):
        orga_report = Report.objects.create(user=self.user, name="Report on organisations",
                                            ct=ContentType.objects.get_for_model(Organisation),
                                           )
        create_field = partial(Field.objects.create, selected=False, report=None, type=HFI_FIELD)
        orga_report.columns = [
            create_field(name="name",              title="Name",               order=1),
            create_field(name="legal_form__title", title="Legal form - title", order=2),
          ]

        return orga_report

    def test_link_report01(self):
        contact_report = Report.objects.create(user=self.user, name="Report on contacts", 
                                               ct=ContentType.objects.get_for_model(Contact),
                                              )

        create_field = partial(Field.objects.create, selected=False, report=None, type=HFI_FIELD)
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
        self.assertEqual(img_report, rfield.report)

        #unlink --------------------------------------------------------------
        rfield.selected = True
        rfield.save()
        url = '/reports/report/field/unlink_report'
        self.assertGET404(url)
        self.assertPOST404(url, data={'field_id': rfields[0].id})
        self.assertPOST200(url, data={'field_id': rfield.id})

        rfield = self.refresh(rfield)
        self.assertIsNone(rfield.report)
        self.assertFalse(rfield.selected)

    def test_link_report02(self):
        get_ct = ContentType.objects.get_for_model
        contact_report = Report.objects.create(user=self.user, ct=get_ct(Contact),
                                               name="Report on contacts",
                                              )

        create_field = partial(Field.objects.create, selected=False, report=None, type=HFI_FIELD)
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
        self.assertEqual(orga_report, self.refresh(rfields[1]).report)

    def test_link_report03(self):
        self.assertEqual([('document', _(u'Document'))],
                         Report.get_related_fields_choices(Folder)
                        )
        get_ct = ContentType.objects.get_for_model
        create_field = partial(Field.objects.create, selected=False, report=None, type=HFI_FIELD)
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
        self.assertEqual(doc_report, self.refresh(rfields[1]).report)

    def test_set_selected(self):
        img_report = self._build_image_report()
        orga_report = self._build_orga_report()

        contact_report = Report.objects.create(user=self.user, name="Report on contacts",
                                               ct=ContentType.objects.get_for_model(Contact),
                                              )
        create_field = partial(Field.objects.create, selected=False, report=None, type=HFI_FIELD)
        contact_report.columns = rfields = [
            create_field(name="last_name",         title="Last name",      order=1),
            create_field(name="image__name",       title="Image - Name",   order=2, report=img_report),
            create_field(name=REL_SUB_EMPLOYED_BY, title="Is employed by", order=3, 
                         report=orga_report, type=HFI_RELATION, selected=True,
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

    def test_report_fetch01(self):
        create_contact = partial(Contact.objects.create, user=self.user)
        for i in xrange(5):
            create_contact(last_name='Mister %s' % i)

        create_contact(last_name='Mister X', is_deleted=True)

        report = self.create_simple_report("Contacts report")

        self.assertEqual(set(str(cid) for cid in Contact.objects.filter(is_deleted=False)
                                                                .values_list('id', flat=True)
                            ),
                         set(chain.from_iterable(report.fetch()))
                        )

    def test_get_predicates_choices_4_ct(self):
        response = self.assertPOST200('/reports/get_predicates_choices_4_ct',
                                      data={'ct_id': ContentType.objects.get_for_model(Report).id}
                                     )
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertIsInstance(content, list)
        self.assertTrue(content)

        def relationtype_2_tuple(rtype_id):
            rt = RelationType.objects.get(pk=rtype_id)
            return [rt.id, rt.predicate]

        self.assertIn(relationtype_2_tuple(REL_SUB_HAS), content)
        self.assertNotIn(relationtype_2_tuple(REL_SUB_EMPLOYED_BY), content)

    def test_big_report_fetch01(self):
        #self.populate('creme_core', 'persons', 'opportunities', 'billing')
        self._create_reports()
        self._setUp_data_for_big_report()
        user = self.user

        targeted_organisations = [self.nintendo, self.sega, self.virgin, self.sony]
        targeted_contacts      = [self.crash, self.sonic, self.mario, self.luigi]

        #Target only own created organisations
        #Organisation.objects.exclude(id__in=[o.id for o in targeted_organisations]).delete()
        Contact.objects.exclude(id__in=[c.id for c in targeted_contacts]).delete()

        #Test opportunities report
        ##Headers
        self.assertEqual(set([u'name', u'reference', u'closing_date']),
                         set(f.name for f in self.report_opp.get_children_fields_flat())
                        )
        ##Data
        self.assertEqual([[u"Opportunity %s" % i, u"%s" % i, unicode(self.closing_date)] for i in xrange(1, 11)],
                         self.report_opp.fetch_all_lines(user=user)
                        )

        #Test invoices report
        ##Headers
        invoice_headers = ["name", "issuing_date", "status__name", "total_vat__sum"]
        self.assertEqual(invoice_headers, list(f.name for f in self.report_invoice.get_children_fields_flat()))

        nintendo_invoice_1 = [u"Invoice 1", unicode(self.issuing_date), unicode(self.invoice_status.name), Decimal("12.00")]
        nintendo_invoice_2 = [u"Invoice 2", unicode(self.issuing_date), unicode(self.invoice_status.name), Decimal("12.00")]
        self.assertEqual([nintendo_invoice_1, nintendo_invoice_2],
                         self.report_invoice.fetch_all_lines(user=user)
                        )

        #Test organisations report
        ##Headers
        ##REL_OBJ_BILL_ISSUED replaced by invoice_headers because of explosion of subreport
        orga_headers = list(chain([u"name", u"user__username", u"legal_form__title"],
                                  invoice_headers,
                                  [REL_OBJ_CUSTOMER_SUPPLIER, REL_SUB_EMIT_ORGA, u"capital__min", u'get_pretty_properties']
                                 )
                           )
        self.assertEqual(orga_headers, list(f.name for f in self.report_orga.get_children_fields_flat()))

        Relation.objects.create(subject_entity=self.nintendo,
                                type_id=REL_OBJ_CUSTOMER_SUPPLIER,
                                object_entity=self.sony,
                                user=user
                               )
        Relation.objects.create(subject_entity=self.nintendo,
                                type_id=REL_OBJ_CUSTOMER_SUPPLIER,
                                object_entity=self.sega,
                                user=user
                               )

        opportunity_nintendo_1 = self.create_opportunity(name="Opportunity nintendo 1", reference=u"1.1", emitter=self.nintendo)
        opp_nintendo_values = " - ".join(u"%s: %s" % (get_verbose_field_name(model=Opportunity, separator="-", field_name=field_name),
                                                      get_instance_field_info(opportunity_nintendo_1, field_name)[1]
                                                     )
                                           for field_name in [u'name', u'reference', u'closing_date']
                                        )
        min_capital = min(o.capital for o in targeted_organisations)

        ##Data
        nintendo = self.nintendo
        sega     = self.sega
        sony     = self.sony
        virgin   = self.virgin

        funf = Organisation.function_fields.get('get_pretty_properties')

        orga_data = OrderedDict([
            ("nintendo_invoice1", list(chain([nintendo.name, unicode(nintendo.user.username), self.nintendo_lf.title], nintendo_invoice_1,                [u", ".join([unicode(sony), unicode(sega)]), opp_nintendo_values, min_capital, funf(nintendo).for_csv()]))),
            ("nintendo_invoice2", list(chain([nintendo.name, unicode(nintendo.user.username), self.nintendo_lf.title], nintendo_invoice_2,                [u", ".join([unicode(sony), unicode(sega)]), opp_nintendo_values, min_capital, funf(nintendo).for_csv()]))),
            ("sega",              list(chain([sega.name,     unicode(sega.user.username),     self.sega_lf.title],     [u"" for i in nintendo_invoice_2], [u"",                                        u""],               [min_capital, funf(sega).for_csv()]))),
            ("sony",              list(chain([sony.name,     unicode(sony.user.username),     self.sony_lf.title],     [u"" for i in nintendo_invoice_2], [u"",                                        u""],               [min_capital, funf(sony).for_csv()]))),
            ("virgin",            list(chain([virgin.name,   unicode(virgin.user.username),   self.virgin_lf.title],   [u"" for i in nintendo_invoice_2], [u"",                                        u""],               [min_capital, funf(virgin).for_csv()]))),
        ])
        #self.assertEqual(orga_data.values(), self.report_orga.fetch_all_lines(user=user))
        self.assertListContainsSubset(orga_data.values(), self.report_orga.fetch_all_lines(user=user))

        #Test contacts report
        ##Headers
        self.assertEqual(list(chain(["last_name", "first_name", "language__name"], orga_headers)),
                         list(f.name for f in self.report_contact.get_children_fields_flat())
                        )

        #self.maxDiff = None

        ##Data
        crash = self.crash
        luigi = self.luigi
        mario = self.mario
        sonic = self.sonic

        self.assertEqual([list(chain([crash.last_name, crash.first_name, u""], orga_data['sony'])),
                          list(chain([luigi.last_name, luigi.first_name, u""], orga_data['nintendo_invoice1'])),
                          list(chain([luigi.last_name, luigi.first_name, u""], orga_data['nintendo_invoice2'])),
                          list(chain([mario.last_name, mario.first_name, u", ".join(mario.language.values_list("name", flat=True))], orga_data['nintendo_invoice1'])),
                          list(chain([mario.last_name, mario.first_name, u", ".join(mario.language.values_list("name", flat=True))], orga_data['nintendo_invoice2'])),
                          list(chain([sonic.last_name, sonic.first_name, u""], orga_data['sega'])),
                        ],
                       self.report_contact.fetch_all_lines()
                      )

        #TODO: test HFI_RELATED, HFI_CUSTOM

    def test_get_aggregate_fields(self):
        url = '/reports/get_aggregate_fields'
        self.assertGET404(url)
        self.assertPOST404(url)

        data = {'ct_id': ContentType.objects.get_for_model(Organisation).id}
        response = self.assertPOST200(url, data=data)
        self.assertEqual([], simplejson.loads(response.content))

        response = self.assertPOST200(url, data=dict(data, aggregate_name='stuff'))
        self.assertEqual([], simplejson.loads(response.content))

        response = self.assertPOST200(url, data=dict(data, aggregate_name='sum'))
        self.assertEqual([['capital__sum', _('Capital')]],
                         simplejson.loads(response.content)
                        )

#TODO: test with subreports, expanding etc...
