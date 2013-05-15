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

    from creme.creme_core.models import (CremePropertyType, CremeProperty, RelationType,
                                         Relation, InstanceBlockConfigItem)
    from creme.creme_core.models.header_filter import (HeaderFilterItem, HeaderFilter,
                                                       HFI_FIELD, HFI_RELATION, HFI_FUNCTION)
    from creme.creme_core.constants import REL_SUB_HAS
    from creme.creme_core.utils.meta import get_verbose_field_name, get_instance_field_info

    from creme.billing.models import Invoice
    from creme.billing.constants import REL_SUB_BILL_RECEIVED

    from creme.opportunities.models import Opportunity
    from creme.opportunities.constants import REL_SUB_EMIT_ORGA

    from creme.persons.models import Contact, Organisation
    from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_OBJ_CUSTOMER_SUPPLIER

    from ..models import Field, Report, ReportGraph
    from ..models.graph import RGT_MONTH

    from .base import BaseReportsTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


try:
    from creme.creme_core.utils.xlrd_utils import XlrdReader
    from creme.creme_core.registry import export_backend_registry
    XlsImport = not 'xls' in export_backend_registry.iterkeys()
except Exception as e:
    XlsImport = True


__all__ = ('ReportsTestCase',)


class ReportsTestCase(BaseReportsTestCase):
    def test_report_createview01(self):
        url = self.ADD_URL
        self.assertGET200(url)

        response = self.client.post(url, data={'user': self.user.pk,
                                               'name': 'name',
                                               'ct':   ContentType.objects.get_for_model(Contact).id,
                                              }
                                   )
        self.assertFormError(response, 'form', None,
                             [_(u"You must select an existing view, or at least one field from : %s") % 
                                ', '.join([_(u'Regular fields'), _(u'Related fields'),
                                           _(u'Custom fields'), _(u'Relations'), _(u'Functions'),
                                           _(u'Maximum'), _(u'Sum'), _(u'Average'), _(u'Minimum'),
                                          ])
                             ]
                            )

    def test_report_createview02(self):
        name  = 'trinita'
        self.assertFalse(Report.objects.filter(name=name).exists())

        report  = self.create_report(name)
        columns = list(report.columns.order_by('order'))
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

    def test_report_editview(self):
        report = self.create_report('trinita')
        self.assertGET200('/reports/report/edit/%s' % report.id)

        #TODO: complete this test

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

    def test_report_csv01(self): #void report
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

    def test_report_field_add01(self):
        report = self.create_report('trinita')
        url = '/reports/report/%s/field/add' % report.id

        response = self.assertGET200(url)

        with self.assertNoException():
            form = response.context['form']
            fields_columns = form.fields['columns']

        for i, (fname, fvname) in enumerate(fields_columns.choices):
            if fname == 'last_name': created_index = i; break
        else:
            self.fail('No "last_name" field')

        response = self.client.post(url, data={'user': self.user.pk,
                                               'columns_check_%s' % created_index: 'on',
                                               'columns_value_%s' % created_index: 'last_name',
                                               'columns_order_%s' % created_index: 1,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(1, report.columns.count())

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

        #opportunity_nintendo_1 = self.create_opportunity(name="Opportunity nintendo 1", reference=u"1.1")
        opportunity_nintendo_1 = self.create_opportunity(name="Opportunity nintendo 1", reference=u"1.1", emitter=self.nintendo)
        #Relation.objects.create(subject_entity=self.nintendo,
                                #type_id=REL_SUB_EMIT_ORGA,
                                #object_entity=opportunity_nintendo_1,
                                #user=user
                               #)

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

    def _create_report_n_graph(self):
        #self.populate('billing')

        report = Report.objects.create(user=self.user,
                                       name=u"All invoices of the current year",
                                       ct=ContentType.objects.get_for_model(Invoice),
                                      )
        self.rtype = RelationType.objects.get(pk=REL_SUB_BILL_RECEIVED)

        #TODO: we need helpers: Field.create_4_field(), Field.create_4_relation() etc...
        create_field = Field.objects.create
        report.columns = [create_field(name='name',         title=get_verbose_field_name(Invoice, 'name'),         order=1, type=HFI_FIELD),
                          create_field(name=self.rtype.id,  title=unicode(self.rtype),                             order=2, type=HFI_RELATION),
                          create_field(name='total_no_vat', title=get_verbose_field_name(Invoice, 'total_no_vat'), order=3, type=HFI_FIELD),
                          create_field(name='issuing_date', title=get_verbose_field_name(Invoice, 'issuing_date'), order=4, type=HFI_FIELD),
                         ]

        #TODO: we need a helper ReportGraph.create() ??
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Sum of current year invoices total without taxes / month",
                                            abscissa='issuing_date',
                                            ordinate='total_no_vat__sum',
                                            type=RGT_MONTH, is_count=False
                                           )

        return rgraph

    def test_add_graph_instance_block01(self):
        rgraph = self._create_report_n_graph()
        self.assertFalse(InstanceBlockConfigItem.objects.filter(entity=rgraph.id).exists())

        url = '/reports/graph/%s/block/add' % rgraph.id
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'graph': rgraph.name}))

        items = InstanceBlockConfigItem.objects.filter(entity=rgraph.id)
        self.assertEqual(1, len(items))

        item = items[0]
        self.assertEqual(u'instanceblock_reports-graph|%s-' % rgraph.id, item.block_id)
        self.assertEqual(u'%s - %s' % (rgraph.name, _(u'None')), item.verbose)
        self.assertEqual('', item.data)

        #-----------------------------------------------------------------------
        response = self.assertPOST200(url, data={'graph': rgraph.name})
        self.assertFormError(response, 'form', None,
                             [_(u'The instance block for %(graph)s with %(column)s already exists !') % {
                                        'graph':  rgraph.name,
                                        'column': _(u'None'),
                                    }
                             ]
                            )

    def test_add_graph_instance_block02(self):
        "Volatile relation"
        rgraph = self._create_report_n_graph()
        rtype_id = self.rtype.id
        response = self.client.post('/reports/graph/%s/block/add' % rgraph.id,
                                    data={'graph':           rgraph.name,
                                          'volatile_column': '%s|%s' % (rtype_id, HFI_RELATION),
                                         }
                                   )
        self.assertNoFormError(response)

        items = InstanceBlockConfigItem.objects.filter(entity=rgraph.id)
        self.assertEqual(1, len(items))

        item = items[0]
        self.assertEqual(u'instanceblock_reports-graph|%s-%s|%s' % (rgraph.id, rtype_id, HFI_RELATION),
                         item.block_id
                        )
        self.assertEqual(u'%s - %s' % (rgraph.name, self.rtype), item.verbose)
        self.assertEqual('%s|%s' % (rtype_id, HFI_RELATION), item.data)

    #def test_add_graph_instance_block03(self): #TODO: volatile field


#TODO: test with subreports, expanding etc...
