# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _
    from django.core.serializers.json import simplejson

    from creme.creme_core.models import (RelationType, InstanceBlockConfigItem,
                                BlockDetailviewLocation, BlockPortalLocation)
    from creme.creme_core.models.header_filter import HFI_FIELD, HFI_RELATION
    from creme.creme_core.utils.meta import get_verbose_field_name

    from creme.persons.models import Organisation

    from creme.billing.models import Invoice
    from creme.billing.constants import REL_SUB_BILL_RECEIVED

    from ..models import Field, Report, ReportGraph
    from ..models.graph import RGT_DAY, RGT_MONTH, RGT_YEAR, RGT_RANGE, RGT_FK, RGT_RELATION

    from .base import BaseReportsTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ReportGraphTestCase',)


class ReportGraphTestCase(BaseReportsTestCase):
    def _build_add_graph_url(self, rgraph):
        return '/reports/graph/%s/block/add' % rgraph.id

    def _builf_fetch_url(self, rgraph, order='ASC'):
        return '/reports/graph/fetch_graph/%s/%s' % (rgraph.id, order)

    def _build_fetchfromblock_url_(self, ibi, entity, order='ASC'):
        return '/reports/graph/fetch_from_instance_block/%s/%s/%s' % (
                        ibi.id, entity.id, order,
                    )

    def _create_report_n_graph(self):
        self.report = report = Report.objects.create(user=self.user,
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
                                            type=RGT_MONTH, is_count=False,
                                           )

        return rgraph

    def test_createview01(self):
        report = self.create_report()

        url = '/reports/graph/%s/add' % report.id
        response = self.assertGET200(url)
        self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            fields_choices = fields['abscissa_fields'].choices[0][1]

        choices_set = set(c[0] for c in fields_choices)
        self.assertIn('created', choices_set)
        self.assertIn('sector', choices_set)
        self.assertNotIn('name', choices_set)

        name = 'My Graph #1'
        abscissa = 'sector'
        gtype = RGT_FK
        response = self.client.post(url, data={'user': self.user.pk, #TODO: report.user used instead ??
                                               'name':              name,
                                               'abscissa_fields':   abscissa,
                                               'abscissa_group_by': gtype,
                                               'is_count':          True,
                                              })
        self.assertNoFormError(response)

        rgraph = self.get_object_or_fail(ReportGraph, report=report, name=name)
        self.assertEqual(self.user, rgraph.user)
        self.assertEqual(abscissa,  rgraph.abscissa)
        self.assertEqual('',        rgraph.ordinate)
        self.assertEqual(gtype,     rgraph.type)
        self.assertIsNone(rgraph.days)
        self.assertIs(rgraph.is_count, True)

        #------------------------------------------------------------
        response = self.assertGET200(rgraph.get_absolute_url())
        self.assertTemplateUsed(response, 'reports/view_graph.html')

        #------------------------------------------------------------
        self.assertGET200(self._builf_fetch_url(rgraph, 'ASC'))
        #TODO: test collected data !!!!!!!!!!!!!

        self.assertGET200(self._builf_fetch_url(rgraph, 'DESC'))
        self.assertGET404(self._builf_fetch_url(rgraph, 'STUFF'))

    def test_editview(self):
        rgraph = self._create_report_n_graph()
        url = '/reports/graph/edit/%s'  % rgraph.id
        self.assertGET200(url)

        name = rgraph.name[:10] + '...'
        abscissa = 'created'
        gtype = RGT_DAY
        #TODO: if 'aggregates_fields'= 'total_vat' but no 'aggregates ==> ordinate = 'total_vat__' ?!
        response = self.client.post(url, data={'user':              self.user.pk,
                                               'name':              name,
                                               'abscissa_fields':   abscissa,
                                               'abscissa_group_by': gtype,
                                               'aggregates_fields': 'total_vat',
                                               'aggregates':        'avg',
                                              })
        self.assertNoFormError(response)

        rgraph = self.refresh(rgraph)
        self.assertEqual(abscissa,         rgraph.abscissa)
        self.assertEqual('total_vat__avg', rgraph.ordinate)
        self.assertEqual(gtype,            rgraph.type)
        self.assertIsNone(rgraph.days)
        self.assertFalse(rgraph.is_count)

        #------------------------------------------------------------
        self.assertGET200(rgraph.get_absolute_url())

        #------------------------------------------------------------
        self.assertGET200(self._builf_fetch_url(rgraph, 'ASC'))
        #TODO: test collected data !!!!!!!!!!!!!

    #TODO: RGT_RANGE + 'days'

    def test_add_graph_instance_block01(self):
        rgraph = self._create_report_n_graph()
        self.assertFalse(InstanceBlockConfigItem.objects.filter(entity=rgraph.id).exists())

        url = self._build_add_graph_url(rgraph)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'graph': rgraph.name}))

        items = InstanceBlockConfigItem.objects.filter(entity=rgraph.id)
        self.assertEqual(1, len(items))

        item = items[0]
        self.assertEqual(u'instanceblock_reports-graph|%s-' % rgraph.id, item.block_id)
        self.assertEqual(u'%s - %s' % (rgraph.name, _(u'None')), item.verbose)
        self.assertEqual('', item.data)

        #---------------------------------------------------------------------
        response = self.assertPOST200(url, data={'graph': rgraph.name})
        self.assertFormError(response, 'form', None,
                             [_(u'The instance block for %(graph)s with %(column)s already exists !') % {
                                        'graph':  rgraph.name,
                                        'column': _(u'None'),
                                    }
                             ]
                            )
        #---------------------------------------------------------------------
        #Display on home
        BlockPortalLocation.objects.all().delete()
        BlockPortalLocation.create(app_name='creme_core', block_id=item.block_id, order=1)
        response = self.assertGET200('/')
        self.assertTemplateUsed(response, 'reports/templatetags/block_report_graph.html')
        self.assertContains(response, ' id="%s"' % item.block_id)

        #---------------------------------------------------------------------
        #Display on detailview
        ct = ContentType.objects.get_for_model(Invoice)
        BlockDetailviewLocation.objects.filter(content_type=ct).delete()
        BlockDetailviewLocation.create(block_id=item.block_id, order=1,
                                       zone=BlockDetailviewLocation.RIGHT, model=Invoice,
                                      )

        create_orga = partial(Organisation.objects.create, user=self.user)
        invoice = self._create_invoice(create_orga(name='BullFrog'), create_orga(name='Maxis'))

        response = self.assertGET200(invoice.get_absolute_url())
        self.assertTemplateUsed(response, 'reports/templatetags/block_report_graph.html')
        self.assertContains(response, ' id="%s"' % item.block_id)

        #---------------------------------------------------------------------
        response = self.assertGET200(self._build_fetchfromblock_url_(item, invoice, 'ASC'))

        #NB: RGT_MONTH
        dt = now()
        data = {'month': dt.month, 'year':  dt.year}
        expected = {'y': [['0.00',
                           '/billing/invoices?q_filter={"issuing_date__year": %(year)s, "issuing_date__month": %(month)s}' % data,
                          ]
                         ],
                    'x': ['%(month)02i/%(year)s' % data],
                   }
        self.assertEqual(expected, simplejson.loads(response.content))

        response = self.assertGET200(self._build_fetchfromblock_url_(item, invoice, 'DESC'))
        self.assertEqual(expected, simplejson.loads(response.content))

        self.assertGET404(self._build_fetchfromblock_url_(item, invoice, 'FOOBAR'))

    def test_add_graph_instance_block02(self):
        "Volatile relation"
        rgraph = self._create_report_n_graph()
        rtype_id = self.rtype.id
        response = self.client.post(self._build_add_graph_url(rgraph),
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

    def test_get_available_report_graph_types(self):
        ct = ContentType.objects.get_for_model(Invoice)
        url = '/reports/graph/get_available_types/%s' % ct.id
        self.assertGET404(url)
        self.assertPOST404(url)

        response = self.assertPOST200(url, data={'record_id': 'name'})
        self.assertEqual({'result': [{'text': _(u'Choose an abscissa field'), 'id': ''}]},
                         simplejson.loads(response.content)
                        )

        response = self.assertPOST200(url, data={'record_id': 'issuing_date'})
        self.assertEqual({'result': [{'id': RGT_DAY,   'text': _(u"By days")},
                                     {'id': RGT_MONTH, 'text': _(u"By months")},
                                     {'id': RGT_YEAR,  'text': _(u"By years")},
                                     {'id': RGT_RANGE, 'text': _(u"By X days")},
                                    ],
                         },
                         simplejson.loads(response.content)
                        )

        response = self.assertPOST200(url, data={'record_id': 'status'})
        self.assertEqual({'result': [{'id': RGT_FK, 'text': _(u"By values")}]},
                         simplejson.loads(response.content)
                        )

        response = self.assertPOST200(url, data={'record_id': REL_SUB_BILL_RECEIVED})
        self.assertEqual({'result': [{'id': RGT_RELATION, 'text': _(u"By values")}]},
                         simplejson.loads(response.content)
                        )
