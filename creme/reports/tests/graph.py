# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _
    from django.core.serializers.json import simplejson

    from creme.creme_core.models import (RelationType, Relation,
            InstanceBlockConfigItem, BlockDetailviewLocation, BlockPortalLocation,
            EntityFilter, EntityFilterCondition)
    from creme.creme_core.models.header_filter import HFI_FIELD, HFI_RELATION
    from creme.creme_core.utils.meta import get_verbose_field_name

    from creme.persons.models import Organisation, Contact, Position, Sector
    from creme.persons.constants import REL_OBJ_EMPLOYED_BY, REL_SUB_EMPLOYED_BY

    from creme.billing.models import Invoice
    from creme.billing.constants import REL_SUB_BILL_RECEIVED

    from ..models import Field, Report, ReportGraph
    from ..models.graph import RGT_DAY, RGT_MONTH, RGT_YEAR, RGT_RANGE, RGT_FK, RGT_RELATION

    from .base import BaseReportsTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ReportGraphTestCase',)


class ReportGraphTestCase(BaseReportsTestCase):
    def _build_add_graph_url(self, report):
        return '/reports/graph/%s/add' % report.id

    def _build_add_block_url(self, rgraph):
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
        "RGT_FK"
        report = self.create_simple_organisations_report()

        url = self._build_add_graph_url(report)
        response = self.assertGET200(url)
        self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            fields_choices = fields['abscissa_field'].choices[0][1]
            aggrfields_choices = fields['aggregate_field'].choices

        choices_set = set(c[0] for c in fields_choices)
        self.assertIn('created', choices_set)
        self.assertIn('sector', choices_set)
        self.assertNotIn('name', choices_set)

        self.assertEqual([('capital', _(u'Capital'))], aggrfields_choices)

        name = 'My Graph #1'
        abscissa = 'sector'
        gtype = RGT_FK
        response = self.client.post(url, data={'user': self.user.pk, #TODO: report.user used instead ??
                                               'name':              name,
                                               'abscissa_field':    abscissa,
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

    def test_createview02(self):
        "Ordinate with aggregate + RGT_DAY"
        report = self.create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        ordinate = 'capital'
        gtype = RGT_DAY

        def post(**kwargs):
            data = {'user': self.user.pk,
                    'name':              name,
                    'abscissa_group_by': gtype,
                   }
            data.update(**kwargs)
            return self.client.post(url, data=data)

        response = post(abscissa_field='modified')
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', None,
                             _(u"If you don't choose an ordinate field (or none available) "
                                "you have to check 'Make a count instead of aggregate ?'"
                              )
                            )

        response = post(abscissa_field='staff_size', aggregate_field=ordinate)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'abscissa_field',
                             '"%s" groups are only compatible with {DateField, DateTimeField}' % _('By days')
                            )
        self.assertFormError(response, 'form', 'aggregate',
                             _(u'This field is required if you choose a field to aggregate.')
                            )

        aggregate = 'max'
        abscissa = 'created'
        self.assertNoFormError(post(abscissa_field=abscissa,
                                    aggregate_field=ordinate,
                                    aggregate=aggregate,
                                   )
                              )

        rgraph = self.get_object_or_fail(ReportGraph, report=report, name=name)
        self.assertEqual(self.user,                        rgraph.user)
        self.assertEqual(abscissa,                         rgraph.abscissa)
        self.assertEqual('%s__%s' % (ordinate, aggregate), rgraph.ordinate)
        self.assertEqual(gtype,                            rgraph.type)
        self.assertIsNone(rgraph.days)
        self.assertFalse(rgraph.is_count)

    def test_createview03(self):
        "'aggregate_field' empty ==> 'is_count' mandatory"
        report = self.create_simple_contacts_report()

        url = self._build_add_graph_url(report)
        response = self.assertGET200(url)
        self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            fields_choices = fields['abscissa_field'].choices[0][1]

        choices_set = set(c[0] for c in fields_choices)
        self.assertIn('created', choices_set)
        self.assertIn('sector', choices_set)
        self.assertIn('civility', choices_set)
        self.assertNotIn('last_name', choices_set)

        name = 'My Graph #1'
        abscissa = 'sector'
        self.assertNoFormError(self.client.post(url,
                                                data={'user': self.user.pk, #TODO: report.user used instead ??
                                                      'name':             name,
                                                      'abscissa_field':   abscissa,
                                                      'abscissa_group_by': RGT_FK,
                                                      #'is_count': True, #useless
                                                    }
                                               )
                              )
        rgraph = self.get_object_or_fail(ReportGraph, report=report, name=name)
        self.assertEqual(abscissa, rgraph.abscissa)
        self.assertEqual('',       rgraph.ordinate)
        self.assertTrue(rgraph.is_count)

    def test_createview04(self):
        "RGT_RELATION"
        report = self.create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        gtype = RGT_RELATION

        def post(abscissa):
            return self.client.post(url, data={'user': self.user.pk,
                    'name':              name,
                    'abscissa_field':    abscissa,
                    'abscissa_group_by': gtype,
                    'is_count': True,
                   })

        fname = 'staff_size'
        response = post(fname)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'abscissa_field',
                             'Unknown relationship type.'
                            )

        rtype_id = REL_OBJ_EMPLOYED_BY
        self.assertNoFormError(post(rtype_id))

        rgraph = self.get_object_or_fail(ReportGraph, report=report, name=name)
        self.assertEqual(self.user, rgraph.user)
        self.assertEqual(rtype_id,  rgraph.abscissa)
        self.assertEqual('',        rgraph.ordinate)
        self.assertTrue(rgraph.is_count)

    def _aux_test_createview_with_date(self, gtype, gtype_vname):
        report = self.create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        ordinate = 'capital'

        def post(**kwargs):
            data = {'user': self.user.pk,
                    'name':              name,
                    'abscissa_group_by': gtype,
                    'aggregate_field':   ordinate,
                    'aggregate':         'max',
                   }
            data.update(**kwargs)
            return self.client.post(url, data=data)

        response = post(abscissa_field='staff_size')
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'abscissa_field',
                             '"%s" groups are only compatible with {DateField, DateTimeField}' % gtype_vname
                            )

        aggregate = 'min'
        abscissa = 'created'
        self.assertNoFormError(post(abscissa_field=abscissa, aggregate=aggregate))

        rgraph = self.get_object_or_fail(ReportGraph, report=report, name=name)
        self.assertEqual(self.user,                        rgraph.user)
        self.assertEqual(abscissa,                         rgraph.abscissa)
        self.assertEqual('%s__%s' % (ordinate, aggregate), rgraph.ordinate)
        self.assertEqual(gtype,                            rgraph.type)
        self.assertIsNone(rgraph.days)
        self.assertFalse(rgraph.is_count)

    def test_createview05(self):
        "RGT_MONTH"
        self._aux_test_createview_with_date(RGT_MONTH, _('By months'))

    def test_createview06(self):
        "RGT_YEAR"
        self._aux_test_createview_with_date(RGT_YEAR, _('By years'))

    def test_createview07(self):
        "RGT_RANGE"
        report = self.create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        ordinate = 'capital'
        gtype = RGT_RANGE

        def post(**kwargs):
            data = {'user': self.user.pk,
                    'name':              name,
                    'abscissa_group_by': gtype,
                    'aggregate_field':   ordinate,
                    'aggregate':       'max',
                   }
            data.update(**kwargs)
            return self.client.post(url, data=data)

        response = post(abscissa_field='staff_size')
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'abscissa_field',
                             '"%s" groups are only compatible with {DateField, DateTimeField}' % _('By X days')
                            )
        self.assertFormError(response, 'form', 'days',
                             "You have to specify a day range if you use 'by X days'"
                            )

        aggregate = 'avg'
        abscissa = 'modified'
        days = 25
        self.assertNoFormError(post(abscissa_field=abscissa, aggregate=aggregate, days=days))

        rgraph = self.get_object_or_fail(ReportGraph, report=report, name=name)
        self.assertEqual(self.user,                        rgraph.user)
        self.assertEqual(abscissa,                         rgraph.abscissa)
        self.assertEqual('%s__%s' % (ordinate, aggregate), rgraph.ordinate)
        self.assertEqual(gtype,                            rgraph.type)
        self.assertEqual(days,                             rgraph.days)
        self.assertFalse(rgraph.is_count)

    def test_editview(self):
        rgraph = self._create_report_n_graph()
        url = '/reports/graph/edit/%s'  % rgraph.id
        self.assertGET200(url)

        name = rgraph.name[:10] + '...'
        abscissa = 'created'
        gtype = RGT_DAY
        response = self.client.post(url, data={'user':              self.user.pk,
                                               'name':              name,
                                               'abscissa_field':    abscissa,
                                               'abscissa_group_by': gtype,
                                               'aggregate_field':   'total_vat',
                                               'aggregate':         'avg',
                                              })
        self.assertNoFormError(response)

        rgraph = self.refresh(rgraph)
        self.assertEqual(abscissa,         rgraph.abscissa)
        self.assertEqual('total_vat__avg', rgraph.ordinate)
        self.assertEqual(gtype,            rgraph.type)
        self.assertIsNone(rgraph.days)
        self.assertFalse(rgraph.is_count)

        #------------------------------------------------------------
        self.assertGET200(self._builf_fetch_url(rgraph, 'ASC'))
        #TODO: test collected data !!!!!!!!!!!!!

    def test_fetch_with_fk_01(self):
        "Count"
        create_position = Position.objects.create
        hand = create_position(title='Hand of the king')
        lord = create_position(title='Lord')

        create_contact = partial(Contact.objects.create, user=self.user)
        ned  = create_contact(first_name='Eddard', last_name='Stark', position=hand)
        robb = create_contact(first_name='Robb',   last_name='Stark', position=lord)
        bran = create_contact(first_name='Bran',   last_name='Stark', position=lord)
        aria = create_contact(first_name='Aria',   last_name='Stark')

        efilter = EntityFilter.create('test-filter', 'Starks', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=[ned.last_name]
                                                                   )
                               ])

        report = self.create_simple_contacts_report(efilter=efilter)
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name='Contacts by position',
                                            abscissa='position', type=RGT_FK,
                                            ordinate='', is_count=True,
                                           )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch()

        self.assertEqual(list(Position.objects.values_list('title', flat=True)), x_asc)

        self.assertIsInstance(y_asc, list)
        self.assertEqual(len(x_asc), len(y_asc))

        fmt = '/persons/contacts?q_filter={"position": %s}'
        self.assertEqual([1, fmt % hand.id], y_asc[x_asc.index(hand.title)])
        self.assertEqual([2, fmt % lord.id], y_asc[x_asc.index(lord.title)])

        # DESC ---------------------------------------------------------------
        desc_x_asc, desc_y_asc = rgraph.fetch(order='DESC')
        self.assertEqual(x_asc, desc_x_asc)
        self.assertEqual(y_asc, desc_y_asc)

    def test_fetch_with_fk_02(self):
        "Aggregate"
        create_sector = Sector.objects.create
        war   = create_sector(title='War')
        trade = create_sector(title='Trade')

        create_orga = partial(Organisation.objects.create, user=self.user)
        lannisters = create_orga(name='House Lannister', capital=1000, sector=trade)
        starks     = create_orga(name='House Stark',     capital=100,  sector=war)
        targaryens = create_orga(name='House Targaryen', capital=10,   sector=war)

        efilter = EntityFilter.create('test-filter', 'Houses', Organisation, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='name', values=['House '],
                                                                   )
                               ])

        report = self.create_simple_organisations_report(efilter=efilter)
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name='Capital max by sector',
                                            abscissa='sector', type=RGT_FK,
                                            ordinate='capital__max', is_count=False,
                                           )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch()

        self.assertEqual(list(Sector.objects.values_list('title', flat=True)), x_asc)

        fmt = '/persons/organisations?q_filter={"sector": %s}'
        self.assertEqual([100,  fmt % war.id],   y_asc[x_asc.index(war.title)])
        self.assertEqual([1000, fmt % trade.id], y_asc[x_asc.index(trade.title)])

    def test_fetch_with_date_range01(self):
        "Count"
        report = self.create_simple_organisations_report()

        def create_graph(days):
            return ReportGraph.objects.create(user=self.user, report=report,
                                              name=u"Number of organisation created / %s day(s)" % days,
                                              abscissa='creation_date',
                                              type=RGT_RANGE, days=days,
                                              is_count=True,
                                             )

        rgraph = create_graph(15)
        create_orga = partial(Organisation.objects.create, user=self.user)
        create_orga(name='Target Orga1', creation_date='2013-06-01')
        create_orga(name='Target Orga2', creation_date='2013-06-05')
        create_orga(name='Target Orga3', creation_date='2013-06-14')
        create_orga(name='Target Orga4', creation_date='2013-06-15')
        create_orga(name='Target Orga5', creation_date='2013-06-16')
        create_orga(name='Target Orga6', creation_date='2013-06-30')

        #ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(['01/06/2013-15/06/2013', '16/06/2013-30/06/2013'],
                         x_asc
                        )

        self.assertEqual(len(y_asc), 2)
        fmt = '/persons/organisations?q_filter={"creation_date__range": ["%s", "%s"]}'
        self.assertEqual([4, fmt % ("2013-06-01", "2013-06-15")], y_asc[0])
        self.assertEqual([2, fmt % ("2013-06-16", "2013-06-30")], y_asc[1])

        #DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(None, 'DESC')
        self.assertEqual(['30/06/2013-16/06/2013', '15/06/2013-01/06/2013'],
                         x_desc
                        )
        self.assertEqual([2, fmt % ('2013-06-16', '2013-06-30')], y_desc[0])
        self.assertEqual([4, fmt % ('2013-06-01', '2013-06-15')], y_desc[1])

        #Days = 1 ------------------------------------------------------------
        rgraph_one_day = create_graph(1)
        x_one_day, y_one_day = rgraph_one_day.fetch()
        self.assertEqual(len(y_one_day), 30)
        self.assertEqual(y_one_day[0][0],  1)
        self.assertEqual(y_one_day[1][0],  0)
        self.assertEqual(y_one_day[12][0], 0)
        self.assertEqual(y_one_day[13][0], 1)
        self.assertEqual(y_one_day[14][0], 1)
        self.assertEqual(y_one_day[15][0], 1)
        self.assertEqual(y_one_day[16][0], 0)
        self.assertEqual(y_one_day[29][0], 1)

    def test_fetch_with_date_range02(self):
        "Aggregate"
        report = self.create_simple_organisations_report()

        days = 10
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Minimum of capital by creation date (period of %s days)" % days,
                                            abscissa='creation_date',
                                            type=RGT_RANGE, days=days,
                                            ordinate='capital__sum',
                                            is_count=False,
                                           )

        create_orga = partial(Organisation.objects.create, user=self.user)
        create_orga(name='Orga1', creation_date='2013-06-22', capital=100)
        create_orga(name='Orga2', creation_date='2013-06-25', capital=200)
        create_orga(name='Orga3', creation_date='2013-07-5',  capital=150)

        #ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(['22/06/2013-01/07/2013', '02/07/2013-11/07/2013'],
                         x_asc
                        )
        fmt = '/persons/organisations?q_filter={"creation_date__range": ["%s", "%s"]}'
        self.assertEqual([300, fmt % ('2013-06-22', '2013-07-01')], y_asc[0])
        self.assertEqual([150, fmt % ('2013-07-02', '2013-07-11')], y_asc[1])

        #DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC')
        self.assertEqual(['05/07/2013-26/06/2013', '25/06/2013-16/06/2013'],
                         x_desc
                        )
        fmt = '/persons/organisations?q_filter={"creation_date__range": ["%s", "%s"]}'
        self.assertEqual([150, fmt % ('2013-06-26', '2013-07-05')], y_desc[0])
        self.assertEqual([300, fmt % ('2013-06-16', '2013-06-25')], y_desc[1])

    def test_fetch_by_day01(self):
        "Aggregate"
        report = self.create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Minimum of capital by creation date (by day)",
                                            abscissa='creation_date',
                                            type=RGT_DAY,
                                            ordinate='capital__avg',
                                            is_count=False,
                                           )

        create_orga = partial(Organisation.objects.create, user=self.user)
        create_orga(name='Orga1', creation_date='2013-06-22', capital=100)
        create_orga(name='Orga2', creation_date='2013-06-22', capital=200)
        create_orga(name='Orga3', creation_date='2013-07-5',  capital=130)

        ##ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(['22/06/2013', '05/07/2013'], x_asc)
        fmt = '/persons/organisations?q_filter={"creation_date__day": %s, "creation_date__month": %s, "creation_date__year": %s}'
        self.assertEqual([150, fmt % (22, 6, 2013)], y_asc[0])
        self.assertEqual([130, fmt % (5, 7, 2013)], y_asc[1])

        #DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC')
        self.assertEqual(['05/07/2013', '22/06/2013'], x_desc)
        self.assertEqual([130, fmt % (5, 7, 2013)], y_desc[0])
        self.assertEqual([150, fmt % (22, 6, 2013)], y_desc[1])

    def test_fetch_by_month01(self):
        "Count"
        report = self.create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Minimum of capital by creation date (period of 1 month)",
                                            abscissa='creation_date',
                                            type=RGT_MONTH,
                                            ordinate='', is_count=True,
                                           )

        create_orga = partial(Organisation.objects.create, user=self.user)
        create_orga(name='Orga1', creation_date='2013-06-22')
        create_orga(name='Orga2', creation_date='2013-06-25')
        create_orga(name='Orga3', creation_date='2013-08-5')

        #ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(['06/2013', '08/2013'], x_asc)
        fmt = '/persons/organisations?q_filter={"creation_date__month": %s, "creation_date__year": %s}'
        self.assertEqual([2, fmt % (6, 2013)], y_asc[0])
        self.assertEqual([1, fmt % (8, 2013)], y_asc[1])

        #DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC')
        self.assertEqual(['08/2013', '06/2013'], x_desc)
        self.assertEqual([1, fmt % (8, 2013)], y_desc[0])
        self.assertEqual([2, fmt % (6, 2013)], y_desc[1])

    def test_fetch_by_year01(self):
        "Count"
        report = self.create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Minimum of capital by creation date (period of 1 year)",
                                            abscissa='creation_date',
                                            type=RGT_YEAR,
                                            ordinate='', is_count=True,
                                           )

        create_orga = partial(Organisation.objects.create, user=self.user)
        create_orga(name='Orga1', creation_date='2013-06-22')
        create_orga(name='Orga2', creation_date='2013-07-25')
        create_orga(name='Orga3', creation_date='2014-08-5')

        #ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(['2013', '2014'], x_asc)
        fmt = '/persons/organisations?q_filter={"creation_date__year": %s}'
        self.assertEqual([2, fmt % 2013], y_asc[0])
        self.assertEqual([1, fmt % 2014], y_asc[1])

        #DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC')
        self.assertEqual(['2014', '2013'], x_desc)
        self.assertEqual([1, fmt % 2014], y_desc[0])
        self.assertEqual([2, fmt % 2013], y_desc[1])

    def test_fetch_by_relation01(self):
        "Count"
        user = self.user
        create_orga = partial(Organisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister')
        starks     = create_orga(name='House Stark')

        create_contact = partial(Contact.objects.create, user=user)
        tyrion = create_contact(first_name='Tyrion', last_name='Lannister')
        ned    = create_contact(first_name='Eddard', last_name='Stark')
        aria   = create_contact(first_name='Aria',   last_name='Stark')

        create_rel = partial(Relation.objects.create, user=user, type_id=REL_OBJ_EMPLOYED_BY)
        create_rel(subject_entity=lannisters, object_entity=tyrion)
        create_rel(subject_entity=starks,     object_entity=ned)
        create_rel(subject_entity=starks,     object_entity=aria)

        report = self.create_simple_contacts_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name="Number of employees",
                                            abscissa=REL_SUB_EMPLOYED_BY,
                                            type=RGT_RELATION,
                                            ordinate='', is_count=True,
                                           )

        #ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch()
        self.assertEqual([unicode(lannisters), unicode(starks)], x_asc)
        self.assertEqual(1, y_asc[0])
        self.assertEqual(2, y_asc[1])

        #DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC')
        self.assertEqual(x_asc, x_desc)
        self.assertEqual(y_asc, y_asc)

    def test_fetch_by_relation02(self):
        "Aggregate"
        user = self.user
        create_orga = partial(Organisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', capital=100)
        starks     = create_orga(name='House Stark',     capital=50)
        tullies    = create_orga(name='House Tully',     capital=40)

        create_contact = partial(Contact.objects.create, user=user)
        tywin = create_contact(first_name='Tywin',  last_name='Lannister')
        ned   = create_contact(first_name='Eddard', last_name='Stark')

        rtype = RelationType.create(('reports-subject_obeys',   'obeys to', [Organisation]),
                                    ('reports-object_commands', 'commands', [Contact]),
                                   )[0]

        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        create_rel(subject_entity=lannisters, object_entity=tywin)
        create_rel(subject_entity=starks,     object_entity=ned)
        create_rel(subject_entity=tullies,    object_entity=ned)

        report = self.create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name="Capital by lords",
                                            abscissa=rtype.id,
                                            type=RGT_RELATION,
                                            ordinate='capital__sum',
                                            is_count=False,
                                           )

        #ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch()
        self.assertEqual([unicode(tywin), unicode(ned)], x_asc)
        self.assertEqual(100, y_asc[0])
        self.assertEqual(90,  y_asc[1])

        #DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC')
        self.assertEqual(x_asc, x_desc)
        self.assertEqual(y_asc, y_asc)

    def test_add_graph_instance_block01(self):
        rgraph = self._create_report_n_graph()
        self.assertFalse(InstanceBlockConfigItem.objects.filter(entity=rgraph.id).exists())

        url = self._build_add_block_url(rgraph)
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
        response = self.client.post(self._build_add_block_url(rgraph),
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
        self.assertEqual({'result': [{'id': RGT_RELATION, 'text': _(u"By values (of related entities)")}]},
                         simplejson.loads(response.content)
                        )
