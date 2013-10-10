# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial
    from json import loads as json_load

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import (RelationType, Relation,
            InstanceBlockConfigItem, BlockDetailviewLocation, BlockPortalLocation,
            EntityFilter, EntityFilterCondition,
            CustomField, CustomFieldEnumValue, CustomFieldEnum, CustomFieldInteger)
    from creme.creme_core.models.header_filter import HFI_FIELD, HFI_RELATION
    from creme.creme_core.utils.meta import get_verbose_field_name
    from creme.creme_core.tests.base import skipIfNotInstalled

    from creme.persons.models import Organisation, Contact, Position, Sector
    from creme.persons.constants import REL_OBJ_EMPLOYED_BY, REL_SUB_EMPLOYED_BY

    if 'creme.billing' in settings.INSTALLED_APPS:
        from creme.billing.models import Invoice
        from creme.billing.constants import REL_SUB_BILL_RECEIVED

    from .base import BaseReportsTestCase
    from ..models import Field, Report, ReportGraph
    from ..constants import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ReportGraphTestCase',)


class ReportGraphTestCase(BaseReportsTestCase):
    @classmethod
    def setUpClass(cls):
        BaseReportsTestCase.setUpClass()

        get_ct = ContentType.objects.get_for_model
        cls.ct_contact = get_ct(Contact)
        cls.ct_orga    = get_ct(Organisation)

        if 'creme.billing' in settings.INSTALLED_APPS:
            cls.ct_invoice = get_ct(Invoice)

    def setUp(self):
        self.login()

    def assertURL(self, url, prefix, json_arg):
        self.assertTrue(url.startswith(prefix))

        with self.assertNoException():
            qfilter = json_load(url[len(prefix):])

        self.assertEqual(json_arg, qfilter)

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
                                                     ct=self.ct_invoice,
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
        report = self._create_simple_organisations_report()
        cf = CustomField.objects.create(content_type=report.ct,
                                        name='Soldiers', field_type=CustomField.INT,
                                       )

        url = self._build_add_graph_url(report)
        response = self.assertGET200(url)
        self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            abscissa_choices = fields['abscissa_field'].choices
            aggrfields_choices = fields['aggregate_field'].choices

        self.assertEqual(2, len(abscissa_choices))

        fields_choices = abscissa_choices[0]
        self.assertEqual(_('Fields'), fields_choices[0])
        choices_set = set(c[0] for c in fields_choices[1])
        self.assertIn('created', choices_set)
        self.assertIn('sector',  choices_set)
        self.assertNotIn('name', choices_set) #string can not be used to group
        self.assertNotIn('billing_address', choices_set) #not enumerable

        rel_choices = abscissa_choices[1]
        self.assertEqual(_('Relationships'), rel_choices[0])
        self.get_object_or_fail(RelationType, pk=rel_choices[1][0][0])

        self.assertEqual([(_('Fields'),        [('capital', _(u'Capital'))]),
                          (_('Custom fields'), [(cf.id,     cf.name)]),
                         ],
                         aggrfields_choices
                        )

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

        hand = rgraph.hand
        self.assertEqual(_('Sector'), hand.verbose_abscissa)
        self.assertEqual(_('Count'),  hand.verbose_ordinate)
        self.assertIsNone(hand.abscissa_error)
        self.assertIsNone(hand.ordinate_error)

        #------------------------------------------------------------
        response = self.assertGET200(rgraph.get_absolute_url())
        self.assertTemplateUsed(response, 'reports/view_graph.html')

        #------------------------------------------------------------
        response = self.assertGET200(self._builf_fetch_url(rgraph, 'ASC'))
        with self.assertNoException():
            data = json_load(response.content)

        self.assertIsInstance(data, dict)
        self.assertEqual(3, len(data))
        self.assertEqual(str(rgraph.id), data.get('graph_id'))

        x_asc = data.get('x')
        self.assertEqual(list(Sector.objects.values_list('title', flat=True)), x_asc)

        y_asc = data.get('y')
        self.assertIsInstance(y_asc, list)
        self.assertEqual(len(x_asc), len(y_asc))
        self.assertEqual([0, '/persons/organisations?q_filter={"sector": 1}'],
                         y_asc[0]
                        )

        #------------------------------------------------------------
        self.assertGET200(self._builf_fetch_url(rgraph, 'DESC'))
        self.assertGET404(self._builf_fetch_url(rgraph, 'STUFF'))

    def test_createview02(self):
        "Ordinate with aggregate + RGT_DAY"
        report = self._create_simple_organisations_report()
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

        self.assertEqual(_('Creation date'), rgraph.hand.verbose_abscissa)
        self.assertEqual(u'%s - %s' % (_('Capital'), _('Maximum')),
                         rgraph.hand.verbose_ordinate
                        )

    def test_createview03(self):
        "'aggregate_field' empty ==> 'is_count' mandatory"
        report = self._create_simple_contacts_report()

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
        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        gtype = RGT_RELATION

        def post(abscissa):
            return self.client.post(url, data={'user': self.user.pk,
                    'name':              name,
                    'abscissa_field':    abscissa,
                    'abscissa_group_by': gtype,
                    'is_count':          True,
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

        self.assertEqual(_('employs'), rgraph.hand.verbose_abscissa)

    def _aux_test_createview_with_date(self, gtype, gtype_vname):
        report = self._create_simple_organisations_report()
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
        report = self._create_simple_organisations_report()
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
                             _("You have to specify a day range if you use 'by X days'")
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

    def test_createview08(self):
        "RGT_CUSTOM_FK"
        create_cf = partial(CustomField.objects.create, content_type=self.ct_contact)
        cf_enum    = create_cf(name='Hair',        field_type=CustomField.ENUM)     #OK for abscissa (group by), not for ordinate (aggregate)
        cf_dt      = create_cf(name='First fight', field_type=CustomField.DATETIME) #idem
        cf_int     = create_cf(name='Size (cm)',   field_type=CustomField.INT)      #INT -> not usable for abscissa , but OK for ordinate
        cf_decimal = create_cf(name='Weight (kg)', field_type=CustomField.FLOAT)    #FLOAT -> not usable for abscissa , but OK for ordinate

        #bad CT
        ct_orga = self.ct_orga
        create_cf(content_type=ct_orga, name='Totem', field_type=CustomField.ENUM) 
        create_cf(content_type=ct_orga, name='Gold',  field_type=CustomField.INT)

        create_enum_value = partial(CustomFieldEnumValue.objects.create, custom_field=cf_enum)
        blue = create_enum_value(value='Blue')
        red  = create_enum_value(value='Red')
        create_enum_value(value='Black') #not used

        create_contact = partial(Contact.objects.create, user=self.user)
        ryomou  = create_contact(first_name='Ryomou',  last_name='Shimei')
        kanu    = create_contact(first_name=u'Kan-u',  last_name=u'Unchô')
        sonsaku = create_contact(first_name='Sonsaku', last_name='Hakufu')

        create_enum = partial(CustomFieldEnum.objects.create, custom_field=cf_enum)
        create_enum(entity=ryomou,  value=blue)
        create_enum(entity=kanu,    value=blue)
        create_enum(entity=sonsaku, value=red)

        report = self._create_simple_contacts_report()
        url = self._build_add_graph_url(report)

        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            abs_choices = fields['abscissa_field'].choices
            ord_choices = fields['aggregate_field'].choices

        self.assertEqual(3, len(abs_choices))
        self.assertEqual((_('Custom fields'), 
                          [(cf_enum.id, cf_enum.name),
                           (cf_dt.id,   cf_dt.name),
                          ]
                         ),
                         abs_choices[2]
                        )

        self.assertEqual([(cf_int.id, cf_int.name), (cf_decimal.id, cf_decimal.name)],
                         ord_choices
                        )

        name = 'My Graph #1'
        gtype = RGT_CUSTOM_FK

        def post(cf_id):
            return self.client.post(url, data={'user':              self.user.pk,
                                               'name':              name,
                                               'abscissa_field':    cf_id,
                                               'abscissa_group_by': gtype,
                                               'is_count':          True,
                                              }
                                   )

        response = post(1000)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'abscissa_field',
                             'Unknown or invalid custom field.'
                            )

        self.assertNoFormError(post(cf_enum.id))

        rgraph = self.get_object_or_fail(ReportGraph, report=report, name=name)
        self.assertEqual(self.user,  rgraph.user)
        self.assertEqual(str(cf_enum.id), rgraph.abscissa)
        self.assertEqual(gtype,      rgraph.type)

    def _aux_test_createview_with_customdate(self, gtype):
        create_cf = partial(CustomField.objects.create, content_type=self.ct_orga)
        cf_dt  = create_cf(name='First victory', field_type=CustomField.DATETIME)
        cf_int = create_cf(name='Gold',          field_type=CustomField.INT)

        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'

        def post(**kwargs):
            data = {'user':              self.user.pk,
                    'name':              name,
                    'abscissa_group_by': gtype,
                    'is_count':          True,
                   }
            data.update(**kwargs)
            return self.client.post(url, data=data)

        response = post(abscissa_field=cf_int.id)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'abscissa_field',
                             'Unknown or invalid custom field.'
                            )

        self.assertNoFormError(post(abscissa_field=cf_dt.id))

        rgraph = self.get_object_or_fail(ReportGraph, report=report, name=name)
        self.assertEqual(self.user,     rgraph.user)
        self.assertEqual(str(cf_dt.id), rgraph.abscissa)
        self.assertEqual(gtype,         rgraph.type)

        self.assertEqual(cf_dt.name, rgraph.hand.verbose_abscissa)

    def test_createview09(self):
        "RGT_CUSTOM_DAY"
        self._aux_test_createview_with_customdate(RGT_CUSTOM_DAY)

    def test_createview10(self):
        "RGT_CUSTOM_MONTH"
        self._aux_test_createview_with_customdate(RGT_CUSTOM_MONTH)

    def test_createview11(self):
        "RGT_CUSTOM_YEAR"
        self._aux_test_createview_with_customdate(RGT_CUSTOM_YEAR)

    def test_createview12(self):
        "RGT_CUSTOM_RANGE"
        create_cf = partial(CustomField.objects.create, content_type=self.ct_orga)
        cf_dt  = create_cf(name='First victory', field_type=CustomField.DATETIME)
        cf_int = create_cf(name='Gold',          field_type=CustomField.INT)

        report = self._create_simple_organisations_report()
        url = self._build_add_graph_url(report)

        name = 'My Graph #1'
        gtype = RGT_CUSTOM_RANGE

        def post(**kwargs):
            data = {'user':              self.user.pk,
                    'name':              name,
                    'abscissa_group_by': gtype,
                    'is_count':          True,
                   }
            data.update(**kwargs)
            return self.client.post(url, data=data)

        response = post(abscissa_field=cf_int.id)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'abscissa_field',
                             'Unknown or invalid custom field.'
                            )
        self.assertFormError(response, 'form', 'days',
                             _("You have to specify a day range if you use 'by X days'")
                            )

        days = 25
        self.assertNoFormError(post(abscissa_field=cf_dt.id, days=days))

        rgraph = self.get_object_or_fail(ReportGraph, report=report, name=name)
        self.assertEqual(self.user,     rgraph.user)
        self.assertEqual(str(cf_dt.id), rgraph.abscissa)
        self.assertEqual(gtype,         rgraph.type)
        self.assertEqual(days,          rgraph.days)

        self.assertEqual(cf_dt.name, rgraph.hand.verbose_abscissa)

    @skipIfNotInstalled('creme.billing')
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
                                              }
                                   )
        self.assertNoFormError(response)

        rgraph = self.refresh(rgraph)
        self.assertEqual(abscissa,         rgraph.abscissa)
        self.assertEqual('total_vat__avg', rgraph.ordinate)
        self.assertEqual(gtype,            rgraph.type)
        self.assertIsNone(rgraph.days)
        self.assertFalse(rgraph.is_count)

    def test_fetch_with_fk_01(self):
        "Count"
        create_position = Position.objects.create
        hand = create_position(title='Hand of the king')
        lord = create_position(title='Lord')

        last_name = 'Stark'
        create_contact = partial(Contact.objects.create, user=self.user, last_name=last_name)
        create_contact(first_name='Eddard', position=hand)
        create_contact(first_name='Robb',   position=lord)
        create_contact(first_name='Bran',   position=lord)
        create_contact(first_name='Aria')

        efilter = EntityFilter.create('test-filter', 'Starks', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=[last_name]
                                                                   )
                               ])

        report = self._create_simple_contacts_report(efilter=efilter)
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
        x_desc, y_desc = rgraph.fetch(order='DESC')
        self.assertEqual(list(reversed(x_asc)), x_desc)
        self.assertEqual([1, fmt % hand.id], y_asc[x_asc.index(hand.title)])

    def test_fetch_with_fk_02(self):
        "Aggregate"
        create_sector = Sector.objects.create
        war   = create_sector(title='War')
        trade = create_sector(title='Trade')
        peace = create_sector(title='Peace')

        create_orga = partial(Organisation.objects.create, user=self.user)
        create_orga(name='House Lannister', capital=1000, sector=trade)
        create_orga(name='House Stark',     capital=100,  sector=war)
        create_orga(name='House Targaryen', capital=10,   sector=war)

        efilter = EntityFilter.create('test-filter', 'Houses', Organisation, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='name', values=['House '],
                                                                   )
                               ])

        report = self._create_simple_organisations_report(efilter=efilter)
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name='Capital max by sector',
                                            abscissa='sector', type=RGT_FK,
                                            ordinate='capital__max', is_count=False,
                                           )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch()

        self.assertEqual(list(Sector.objects.values_list('title', flat=True)), x_asc)

        fmt = '/persons/organisations?q_filter={"sector": %s}'
        index = x_asc.index
        self.assertEqual([100,  fmt % war.id],   y_asc[index(war.title)])
        self.assertEqual([1000, fmt % trade.id], y_asc[index(trade.title)])
        self.assertEqual([0,    fmt % peace.id], y_asc[index(peace.title)])

    def test_fetch_with_fk_03(self):
        "Aggregate ordinate with custom field"
        create_sector = Sector.objects.create
        war   = create_sector(title='War')
        trade = create_sector(title='Trade')
        peace = create_sector(title='Peace')

        create_orga = partial(Organisation.objects.create, user=self.user)
        lannisters = create_orga(name='House Lannister', sector=trade)
        starks     = create_orga(name='House Stark',     sector=war)
        targaryens = create_orga(name='House Targaryen', sector=war)

        cf = CustomField.objects.create(content_type=self.ct_orga, name='Soldiers',
                                        field_type=CustomField.INT,
                                       )

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=lannisters, value=500)
        create_cfval(entity=starks,     value=400)
        create_cfval(entity=targaryens, value=200)

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name='Max soldiers by sector',
                                            abscissa='sector', type=RGT_FK,
                                            ordinate='%s__max' % cf.id,
                                            is_count=False,
                                           )

        self.assertEqual(u'%s - %s' % (cf, _('Maximum')), rgraph.hand.verbose_ordinate)

        x_asc, y_asc = rgraph.fetch()

        self.assertEqual(list(Sector.objects.values_list('title', flat=True)), x_asc)

        fmt = '/persons/organisations?q_filter={"sector": %s}'
        index = x_asc.index
        self.assertEqual([400, fmt % war.id],   y_asc[index(war.title)])
        self.assertEqual([500, fmt % trade.id], y_asc[index(trade.title)])
        self.assertEqual([0,   fmt % peace.id], y_asc[index(peace.title)])

    def test_fetch_with_fk_04(self):
        "Aggregate ordinate with invalid field"
        rgraph = ReportGraph.objects.create(user=self.user,
                                            report=self._create_simple_organisations_report(),
                                            name='Max soldiers by sector',
                                            abscissa='sector', type=RGT_FK,
                                            ordinate='unknown__max', #<=====
                                            is_count=False,
                                           )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch()

        self.assertEqual(list(Sector.objects.values_list('title', flat=True)), x_asc)
        self.assertEqual([0, '/persons/organisations?q_filter={"sector": 1}'],
                         y_asc[0]
                        )
        self.assertEqual(_('the field does not exist any more.'),
                         rgraph.hand.ordinate_error
                        )

    def test_fetch_with_fk_05(self):
        "Aggregate ordinate with invalid custom field"
        rgraph = ReportGraph.objects.create(user=self.user,
                                            report=self._create_simple_organisations_report(),
                                            name='Max soldiers by sector',
                                            abscissa='sector', type=RGT_FK,
                                            ordinate='1000__max', #<=====
                                            is_count=False,
                                           )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch()

        self.assertEqual(list(Sector.objects.values_list('title', flat=True)), x_asc)
        self.assertEqual([0, '/persons/organisations?q_filter={"sector": 1}'],
                         y_asc[0]
                        )
        self.assertEqual(_('the custom field does not exist any more.'),
                         rgraph.hand.ordinate_error
                        )

    def test_fetch_with_date_range01(self):
        "Count"
        report = self._create_simple_organisations_report()

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
        report = self._create_simple_organisations_report()

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

    def test_fetch_with_custom_date_range01(self):
        "Count"
        create_cf = partial(CustomField.objects.create, content_type=self.ct_orga,
                            field_type=CustomField.DATETIME,
                           )
        cf = create_cf(name='First victory')
        cf2 = create_cf(name='First defeat') #this one is annoying because the values are in the same table
                                             #so the query must be more complex to not retrieve them

        create_orga = partial(Organisation.objects.create, user=self.user)
        targaryens = create_orga(name='House Targaryen')
        lannisters = create_orga(name='House Lannister')
        starks     = create_orga(name='House Stark')
        baratheons = create_orga(name='House Baratheon')
        tullies    = create_orga(name='House Tully')
        arryns     = create_orga(name='House Arryn')

        create_cf_value = partial(cf.get_value_class().objects.create, custom_field=cf)
        create_dt = partial(self.create_datetime, utc=True)
        create_cf_value(entity=targaryens, value=create_dt(year=2013, month=12, day=21))
        create_cf_value(entity=lannisters, value=create_dt(year=2013, month=12, day=26))
        create_cf_value(entity=starks,     value=create_dt(year=2013, month=12, day=31))
        create_cf_value(entity=baratheons, value=create_dt(year=2014, month=1,  day=3))
        create_cf_value(entity=tullies,    value=create_dt(year=2014, month=1,  day=5))
        create_cf_value(entity=arryns,     value=create_dt(year=2014, month=1,  day=7))

        create_cf_value(custom_field=cf2, entity=lannisters, value=create_dt(year=2013, month=11, day=6))
        create_cf_value(custom_field=cf2, entity=starks,     value=create_dt(year=2014, month=1,  day=6))

        days = 15
        rgraph = ReportGraph.objects.create(user=self.user,
                                            report=self._create_simple_organisations_report(),
                                            name='First victory / %s day(s)' % days,
                                            abscissa=cf.id,
                                            type=RGT_CUSTOM_RANGE, days=days,
                                            ordinate='', is_count=True,
                                           )

        #ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(['21/12/2013-04/01/2014', '05/01/2014-19/01/2014'],
                         x_asc
                        )

        base_url = '/persons/organisations?q_filter='
        base_qdict = {'customfielddatetime__custom_field': cf.id}
        self.assertEqual(4, y_asc[0][0])
        self.assertURL(y_asc[0][1], base_url,
                       dict(base_qdict, customfielddatetime__value__range=['2013-12-21', '2014-01-04'])
                      )

        self.assertEqual(2, y_asc[1][0])
        self.assertURL(y_asc[1][1], base_url,
                       dict(base_qdict, customfielddatetime__value__range=['2014-01-05', '2014-01-19'])
                      )

        #DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC')
        self.assertEqual(['07/01/2014-24/12/2013', '23/12/2013-09/12/2013'],
                         x_desc
                        )

        self.assertEqual(5, y_desc[0][0])
        self.assertURL(y_desc[0][1], base_url,
                       dict(base_qdict, customfielddatetime__value__range=['2013-12-24', '2014-01-07'])
                      )

        self.assertEqual(1, y_desc[1][0])
        self.assertURL(y_desc[1][1], base_url,
                       dict(base_qdict, customfielddatetime__value__range=['2013-12-09', '2013-12-23'])
                      )

    def test_fetch_with_custom_date_range02(self):
        "Invalid CustomField"
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name="Useless name",
                                            abscissa=1000, # <====
                                            type=RGT_CUSTOM_RANGE, days=11,
                                            ordinate='', is_count=True,
                                           )

        x_asc, y_asc = rgraph.fetch()
        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)

    def test_fetch_by_day01(self):
        "Aggregate"
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Average of capital by creation date (by day)",
                                            abscissa='creation_date',
                                            type=RGT_DAY,
                                            ordinate='capital__avg',
                                            is_count=False,
                                           )

        create_orga = partial(Organisation.objects.create, user=self.user)
        create_orga(name='Orga1', creation_date='2013-06-22', capital=100)
        create_orga(name='Orga2', creation_date='2013-06-22', capital=200)
        create_orga(name='Orga3', creation_date='2013-07-5',  capital=130)

        #ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(['22/06/2013', '05/07/2013'], x_asc)

        self.assertEqual(150, y_asc[0][0])
        self.assertURL(y_asc[0][1], '/persons/organisations?q_filter=',
                       {'creation_date__day':   22,
                        'creation_date__month': 6,
                        'creation_date__year':  2013,
                       }
                      )

        self.assertEqual(130, y_asc[1][0])

        #DESC ----------------------------------------------------------------
        self.assertEqual(['05/07/2013', '22/06/2013'], rgraph.fetch(order='DESC')[0])

    def test_fetch_by_customday01(self):
        "Aggregate"
        create_cf_dt = partial(CustomField.objects.create,
                               content_type=self.ct_contact,
                               field_type=CustomField.DATETIME,
                              )
        cf  = create_cf_dt(name='First victory')
        cf2 = create_cf_dt(name='First defeat') #this one is annoying because the values are in the same table
                                                #so the query must be more complex to not retrieve them

        create_orga = partial(Organisation.objects.create, user=self.user)
        lannisters = create_orga(name='House Lannister', capital=100)
        baratheons = create_orga(name='House Baratheon', capital=200)
        targaryens = create_orga(name='House Targaryen', capital=130)

        create_cf_value = partial(cf.get_value_class().objects.create, custom_field=cf)
        create_dt = partial(self.create_datetime, utc=True, year=2013)
        create_cf_value(entity=lannisters, value=create_dt(month=6, day=22))
        create_cf_value(entity=baratheons, value=create_dt(month=6, day=22))
        create_cf_value(entity=targaryens, value=create_dt(month=7, day=5))

        create_cf_value(custom_field=cf2, entity=lannisters, value=create_dt(month=7, day=6))
        create_cf_value(custom_field=cf2, entity=lannisters, value=create_dt(month=7, day=5))

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Average of capital by 1rst victory (by day)",
                                            abscissa=cf.id, type=RGT_CUSTOM_DAY,
                                            ordinate='capital__avg',
                                            is_count=False,
                                           )

        #ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(['22/06/2013', '05/07/2013'], x_asc)
        self.assertEqual(150, y_asc[0][0])
        self.assertEqual(130, y_asc[1][0])

        url = y_asc[0][1]
        self.assertURL(url, '/persons/organisations?q_filter=',
                       {'customfielddatetime__value__day':   22,
                        'customfielddatetime__value__month': 6,
                        'customfielddatetime__value__year':  2013,
                        'customfielddatetime__custom_field': cf.id,
                       }
                      )

        #DESC ----------------------------------------------------------------
        self.assertEqual(['05/07/2013', '22/06/2013'], rgraph.fetch(order='DESC')[0])

    def test_fetch_by_customday02(self):
        "Invalid CustomField"
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Minimum of capital by creation date (by day)",
                                            abscissa=1000, # <====
                                            type=RGT_CUSTOM_DAY,
                                            ordinate='capital__avg',
                                            is_count=False,
                                           )

        x_asc, y_asc = rgraph.fetch()
        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(_('the custom field does not exist any more.'),
                         hand.abscissa_error
                        )

    def test_fetch_by_month01(self):
        "Count"
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Number of orgas by creation date (period of 1 month)",
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

        self.assertEqual(2, y_asc[0][0])
        self.assertURL(y_asc[0][1], '/persons/organisations?q_filter=',
                       {'creation_date__month': 6,
                        'creation_date__year':  2013,
                       }
                      )

        self.assertEqual(1, y_asc[1][0])

        #DESC ----------------------------------------------------------------
        self.assertEqual(['08/2013', '06/2013'], rgraph.fetch(order='DESC')[0])

    def test_fetch_by_custommonth01(self):
        "Count"
        cf = CustomField.objects.create(content_type=self.ct_contact,
                                        name='First victory',
                                        field_type=CustomField.DATETIME,
                                       )
        create_orga = partial(Organisation.objects.create, user=self.user)
        lannisters = create_orga(name='House Lannister')
        baratheons = create_orga(name='House Baratheon')
        targaryens = create_orga(name='House Targaryen')

        create_cf_value = partial(cf.get_value_class().objects.create, custom_field=cf)
        create_dt = partial(self.create_datetime, utc=True, year=2013)
        create_cf_value(entity=lannisters, value=create_dt(month=6, day=22))
        create_cf_value(entity=baratheons, value=create_dt(month=6, day=25))
        create_cf_value(entity=targaryens, value=create_dt(month=8, day=5))

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Number of houses by 1rst victory (period of 1 month)",
                                            abscissa=cf.id, type=RGT_CUSTOM_MONTH,
                                            ordinate='', is_count=True,
                                           )

        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(['06/2013', '08/2013'], x_asc)
        self.assertEqual(2, y_asc[0][0])

    def test_fetch_by_year01(self):
        "Count"
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Number of orgas by creation date (period of 1 year)",
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

    def test_fetch_by_year02(self):
        "Aggregate ordinate with custom field"
        user = self.user

        create_orga = partial(Organisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister', creation_date='2013-06-22')
        starks     = create_orga(name='House Stark',     creation_date='2013-07-25')
        baratheons = create_orga(name='House Baratheon', creation_date='2014-08-5')
        targaryens = create_orga(name='House Targaryen', creation_date='2015-08-5')
        tullies    = create_orga(name='House Tully',     creation_date='2016-08-5')

        cf = CustomField.objects.create(content_type=self.ct_orga,
                                        name='Vine', field_type=CustomField.FLOAT,
                                       )

        create_cfval = partial(cf.get_value_class().objects.create, custom_field=cf)
        create_cfval(entity=lannisters, value='20.2')
        create_cfval(entity=starks,     value='50.5')
        create_cfval(entity=baratheons, value='100.0')
        create_cfval(entity=tullies,    value='0.0')

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=user, report=report,
                                            name=u"Maximum of vine by creation date (period of 1 year)",
                                            abscissa='creation_date',
                                            type=RGT_YEAR,
                                            ordinate='%s__sum' % cf.id,
                                            is_count=False,
                                           )

        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(['2013', '2014', '2015', '2016'], x_asc)

        fmt = '/persons/organisations?q_filter={"creation_date__year": %s}'
        self.assertEqual([Decimal('70.70'), fmt % 2013], y_asc[0])
        self.assertEqual([Decimal('100'),   fmt % 2014], y_asc[1])
        self.assertEqual([0,                fmt % 2015], y_asc[2])
        self.assertEqual([0,                fmt % 2016], y_asc[3])

    def test_fetch_by_year03(self):
        "Invalid field"
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Number of orgas by creation date (period of 1 year)",
                                            abscissa='invalid', #<=====
                                            type=RGT_YEAR,
                                            ordinate='', is_count=True,
                                           )

        x_asc, y_asc = rgraph.fetch()
        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(_('the field does not exist any more.'),
                         hand.abscissa_error
                        )

    def test_fetch_by_customyear01(self):
        "Count"
        cf = CustomField.objects.create(content_type=self.ct_contact,
                                        name='First victory',
                                        field_type=CustomField.DATETIME,
                                       )

        create_orga = partial(Organisation.objects.create, user=self.user)
        lannisters = create_orga(name='House Lannister')
        baratheons = create_orga(name='House Baratheon')
        targaryens = create_orga(name='House Targaryen')

        create_cf_value = partial(cf.get_value_class().objects.create, custom_field=cf)
        create_dt = partial(self.create_datetime, utc=True)
        create_cf_value(entity=lannisters, value=create_dt(year=2013, month=6, day=22))
        create_cf_value(entity=baratheons, value=create_dt(year=2013, month=7, day=25))
        create_cf_value(entity=targaryens, value=create_dt(year=2014, month=8, day=5))

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Number of house by 1rst victory (period of 1 year)",
                                            abscissa=cf.id, type=RGT_CUSTOM_YEAR,
                                            ordinate='', is_count=True,
                                           )

        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(['2013', '2014'], x_asc)
        self.assertEqual(2, y_asc[0][0])

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
        jon    = create_contact(first_name='Jon',    last_name='Snow')

        efilter = EntityFilter.create('test-filter', 'Not bastard', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=[tyrion.last_name, ned.last_name]
                                                                   )
                               ])

        create_rel = partial(Relation.objects.create, user=user, type_id=REL_OBJ_EMPLOYED_BY)
        create_rel(subject_entity=lannisters, object_entity=tyrion)
        create_rel(subject_entity=starks,     object_entity=ned)
        create_rel(subject_entity=starks,     object_entity=aria)
        create_rel(subject_entity=starks,     object_entity=jon)

        report = self._create_simple_contacts_report(efilter=efilter)
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
        self.assertEqual(2, y_asc[1]) #not 3, because of the filter

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

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name="Capital by lords",
                                            abscissa=rtype.id,
                                            type=RGT_RELATION,
                                            ordinate='capital__sum',
                                            is_count=False,
                                           )

        #ASC -----------------------------------------------------------------
        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(2, len(x_asc))

        ned_index = x_asc.index(unicode(ned))
        self.assertNotEqual(-1,  ned_index)

        tywin_index = x_asc.index(unicode(tywin))
        self.assertNotEqual(-1,  tywin_index)

        self.assertEqual(100, y_asc[tywin_index])
        self.assertEqual(90,  y_asc[ned_index])

        #DESC ----------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC')
        self.assertEqual(x_asc, x_desc)
        self.assertEqual(y_asc, y_asc)

    def test_fetch_by_relation03(self):
        "Aggregate ordinate with custom field"
        user = self.user

        create_cf = CustomField.objects.create
        cf = create_cf(content_type=self.ct_contact,
                       name='HP', field_type=CustomField.INT,
                      )
        create_cf(content_type=self.ct_contact,
                  name='Title', field_type=CustomField.ENUM,
                 ) #can not perform aggregates
        create_cf(content_type=self.ct_orga,
                  name='Gold', field_type=CustomField.INT,
                 ) #bad CT

        create_orga = partial(Organisation.objects.create, user=user)
        lannisters = create_orga(name='House Lannister')
        starks     = create_orga(name='House Stark')

        create_contact = partial(Contact.objects.create, user=user)
        ned    = create_contact(first_name='Eddard', last_name='Stark')
        robb   = create_contact(first_name='Robb',   last_name='Stark')
        jaime  = create_contact(first_name='Jaime',  last_name='Lannister')
        tyrion = create_contact(first_name='Tyrion', last_name='Lannister')

        rtype_id = REL_SUB_EMPLOYED_BY
        create_rel = partial(Relation.objects.create, user=user, type_id=rtype_id)
        create_rel(subject_entity=ned,    object_entity=starks)
        create_rel(subject_entity=robb,   object_entity=starks)
        create_rel(subject_entity=jaime,  object_entity=lannisters)
        create_rel(subject_entity=tyrion, object_entity=lannisters)

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=ned,    value=500)
        create_cfval(entity=robb,   value=300)
        create_cfval(entity=jaime,  value=400)
        create_cfval(entity=tyrion, value=200)

        report = self._create_simple_contacts_report()
        rgraph = ReportGraph.objects.create(user=user, report=report,
                                            name='Contacts HP by house',
                                            abscissa=rtype_id, type=RGT_RELATION,
                                            ordinate='%s__sum' % cf.id,
                                            is_count=False,
                                           )

        x_asc, y_asc = rgraph.fetch()
        self.assertEqual(set([unicode(lannisters), unicode(starks)]), set(x_asc))

        index = x_asc.index
        self.assertEqual(600, y_asc[index(unicode(lannisters))])
        self.assertEqual(800, y_asc[index(unicode(starks))])

    def test_fetch_by_relation04(self):
        "Invalid RelationType"
        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name=u"Minimum of capital by creation date (by day)",
                                            abscissa='invalidrtype', # <====
                                            type=RGT_RELATION,
                                            ordinate='capital__avg',
                                            is_count=False,
                                           )

        x_asc, y_asc = rgraph.fetch()
        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(_('the relationship type does not exist any more.'),
                         hand.abscissa_error
                        )

    def test_fetch_with_customfk_01(self):
        report = self._create_simple_contacts_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name='Contacts by title',
                                            abscissa=1000, #<========= 
                                            type=RGT_CUSTOM_FK,
                                            ordinate='', is_count=True,
                                           )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch()

        self.assertEqual([], x_asc)
        self.assertEqual([], y_asc)

        hand = rgraph.hand
        self.assertEqual('??', hand.verbose_abscissa)
        self.assertEqual(_('the custom field does not exist any more.'),
                         hand.abscissa_error
                        )

    def test_fetch_with_customfk_02(self):
        "Count"
        cf = CustomField.objects.create(content_type=self.ct_contact,
                                        name='Title', field_type=CustomField.ENUM,
                                       )
        create_enum_value = partial(CustomFieldEnumValue.objects.create, custom_field=cf)
        hand = create_enum_value(value='Hand')
        lord = create_enum_value(value='Lord')

        create_contact = partial(Contact.objects.create, user=self.user, last_name='Stark')
        ned  = create_contact(first_name='Eddard')
        robb = create_contact(first_name='Robb')
        bran = create_contact(first_name='Bran')
        create_contact(first_name='Aria')

        create_enum = partial(CustomFieldEnum.objects.create, custom_field=cf)
        create_enum(entity=ned,  value=hand)
        create_enum(entity=robb, value=lord)
        create_enum(entity=bran, value=lord)

        report = self._create_simple_contacts_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name='Contacts by title',
                                            abscissa=cf.id, type=RGT_CUSTOM_FK,
                                            ordinate='', is_count=True,
                                           )

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch()

        self.assertEqual([hand.value, lord.value], x_asc)

        fmt = '/persons/contacts?q_filter={"customfieldenum__value": %s}'
        self.assertEqual([1, fmt % hand.id], y_asc[0])
        self.assertEqual([2, fmt % lord.id], y_asc[1])

        # DESC ---------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC')
        self.assertEqual(list(reversed(x_asc)), x_desc)
        self.assertEqual(list(reversed(y_asc)), y_desc)

    def test_fetch_with_customfk_03(self):
        "Aggregate"
        cf = CustomField.objects.create(content_type=self.ct_orga,
                                        name='Policy', field_type=CustomField.ENUM,
                                       )
        create_enum_value = partial(CustomFieldEnumValue.objects.create, custom_field=cf)
        fight     = create_enum_value(value='Fight')
        smartness = create_enum_value(value='Smartness')

        create_orga = partial(Organisation.objects.create, user=self.user)
        starks     = create_orga(name='Starks',     capital=30)
        baratheons = create_orga(name='Baratheon',  capital=60)
        lannisters = create_orga(name='Lannisters', capital=100)

        create_enum = partial(CustomFieldEnum.objects.create, custom_field=cf)
        create_enum(entity=starks,     value=fight)
        create_enum(entity=baratheons, value=fight)
        create_enum(entity=lannisters, value=smartness)

        report = self._create_simple_organisations_report()
        rgraph = ReportGraph.objects.create(user=self.user, report=report,
                                            name='Capital by policy',
                                            abscissa=cf.id, type=RGT_CUSTOM_FK,
                                            ordinate='capital__sum', is_count=False,
                                           )

        self.assertEqual(cf.name, rgraph.hand.verbose_abscissa)

        with self.assertNoException():
            x_asc, y_asc = rgraph.fetch()

        self.assertEqual([fight.value, smartness.value], x_asc)

        fmt = '/persons/organisations?q_filter={"customfieldenum__value": %s}'
        self.assertEqual([90,  fmt % fight.id],     y_asc[0])
        self.assertEqual([100, fmt % smartness.id], y_asc[1])

        # DESC ---------------------------------------------------------------
        x_desc, y_desc = rgraph.fetch(order='DESC')
        self.assertEqual(list(reversed(x_asc)), x_desc)
        self.assertEqual(list(reversed(y_asc)), y_desc)

    @skipIfNotInstalled('creme.billing')
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
        ct = self.ct_invoice
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

        response = self.assertGET200(self._build_fetchfromblock_url_(item, invoice, 'DESC'))
        result = json_load(response.content)
        self.assertIsInstance(result, dict)
        self.assertEqual(2, len(result))
        self.assertEqual(['%(month)02i/%(year)s' % {'month': dt.month, 'year':  dt.year}],
                         result.get('x')
                        )

        y = result.get('y')
        self.assertEqual(0, y[0][0])
        self.assertURL(y[0][1], '/billing/invoices?q_filter=',
                       {'issuing_date__month': dt.month,
                        'issuing_date__year':  dt.year,
                       }
                      )

        self.assertGET404(self._build_fetchfromblock_url_(item, invoice, 'FOOBAR'))

    @skipIfNotInstalled('creme.billing')
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

    @skipIfNotInstalled('creme.billing')
    def test_get_available_report_graph_types(self):
        ct = self.ct_invoice
        url = '/reports/graph/get_available_types/%s' % ct.id
        self.assertGET404(url)
        self.assertPOST404(url)

        response = self.assertPOST200(url, data={'record_id': 'name'})
        self.assertEqual({'result': [{'text': _(u'Choose an abscissa field'), 'id': ''}]},
                         json_load(response.content)
                        )

        response = self.assertPOST200(url, data={'record_id': 'issuing_date'})
        self.assertEqual({'result': [{'id': RGT_DAY,   'text': _(u"By days")},
                                     {'id': RGT_MONTH, 'text': _(u"By months")},
                                     {'id': RGT_YEAR,  'text': _(u"By years")},
                                     {'id': RGT_RANGE, 'text': _(u"By X days")},
                                    ],
                         },
                         json_load(response.content)
                        )

        response = self.assertPOST200(url, data={'record_id': 'status'})
        self.assertEqual({'result': [{'id': RGT_FK, 'text': _(u"By values")}]},
                         json_load(response.content)
                        )

        response = self.assertPOST200(url, data={'record_id': REL_SUB_BILL_RECEIVED})
        self.assertEqual({'result': [{'id': RGT_RELATION, 'text': _(u"By values (of related entities)")}]},
                         json_load(response.content)
                        )

        create_cf = partial(CustomField.objects.create, content_type=ct)
        cf_enum = create_cf(name='Type', field_type=CustomField.ENUM)
        response = self.assertPOST200(url, data={'record_id': cf_enum.id})
        self.assertEqual({'result': [{'id': RGT_CUSTOM_FK, 'text': _(u"By values (of custom choices)")}]},
                         json_load(response.content)
                        )

        cf_dt = create_cf(name='First payment', field_type=CustomField.DATETIME)
        response = self.assertPOST200(url, data={'record_id': cf_dt.id})
        self.assertEqual({'result': [{'id': RGT_CUSTOM_DAY,   'text': _(u"By days")},
                                     {'id': RGT_CUSTOM_MONTH, 'text': _(u"By months")},
                                     {'id': RGT_CUSTOM_YEAR,  'text': _(u"By years")},
                                     {'id': RGT_CUSTOM_RANGE, 'text': _(u"By X days")},
                                    ],
                         },
                         json_load(response.content)
                        )