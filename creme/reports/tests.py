# -*- coding: utf-8 -*-

from datetime import datetime, date
from itertools import chain
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db.models.query_utils import Q
from django.utils.datastructures import SortedDict as OrderedDict
from django.utils.translation import ugettext as _

from billing.constants import REL_OBJ_BILL_ISSUED, REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from billing.models.invoice import Invoice
from billing.models.other_models import InvoiceStatus
from billing.models.product_line import ProductLine

from creme_core.models import CremePropertyType, CremeProperty, RelationType, Relation
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CALCULATED
from creme_core.constants import REL_SUB_HAS, PROP_IS_MANAGED_BY_CREME
from creme_core.models.i18n import Language
from creme_core.tests.base import CremeTestCase
from creme_core.utils.meta import get_verbose_field_name, get_field_infos

from opportunities.constants import REL_SUB_EMIT_ORGA
from opportunities.models.opportunity import Opportunity, SalesPhase

from persons.constants import REL_SUB_EMPLOYED_BY, REL_OBJ_CUSTOMER_SUPPLIER, REL_SUB_CUSTOMER_SUPPLIER
from persons.models import Contact, Organisation
from persons.models.other_models import LegalForm

from reports.models import *


class ReportsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config', 'reports')
        self.login()

    def test_report_createview01(self):
        response = self.client.get('/reports/report/add')
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/reports/report/add',
                                    data={
                                            'user': self.user.pk,
                                            'name': 'name',
                                            'ct':   ContentType.objects.get_for_model(Contact).id,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)
        self.assert_(response.context['form'].errors, 'No view or field selected')

    def create_report(self, name):
        ct_id = ContentType.objects.get_for_model(Contact).id

        hf = HeaderFilter.create(pk='test_hf', name='name', model=Contact)
        create_hfi = HeaderFilterItem.objects.create
        create_hfi(pk='hfi1', order=1, name='last_name',             title='Last name',  type=HFI_FIELD,    header_filter=hf, filter_string="last_name__icontains")
        create_hfi(pk='hfi2', order=2, name='user',                  title='User',       type=HFI_FIELD,    header_filter=hf, filter_string="user__username__icontains")
        create_hfi(pk='hfi3', order=3, name='related_to',            title='Related to', type=HFI_RELATION, header_filter=hf, filter_string="", relation_predicat_id=REL_SUB_HAS)
        create_hfi(pk='hfi4', order=4, name='get_pretty_properties', title='Properties', type=HFI_FUNCTION, header_filter=hf, filter_string="")
        #hf.set_items([HeaderFilterItem.build_4_field(model=Contact, name='last_name'),
                      #HeaderFilterItem.build_4_field(model=Contact, name='user'),
                      #HeaderFilterItem.build_4_relation(RelationType.objects.get(pk=REL_SUB_RELATED_TO)),
                      #HeaderFilterItem.build_4_functionfield(Contact.function_fields.get('get_pretty_properties')),
                     #])

        response = self.client.post('/reports/report/add', follow=True,
                                    data={
                                            'user': self.user.pk,
                                            'name': name,
                                            'ct':   ct_id,
                                            'hf':   hf.id,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        try:
            report = Report.objects.get(name=name)
        except Report.DoesNotExist, e:
            self.fail('report not created ?!')

        return report

    def create_simple_report(self, name):
        ct = ContentType.objects.get_for_model(Contact)
        report = Report.objects.create(name=name, ct=ct, user=self.user)
        field_id=Field.objects.create(name=u'id', title=u'Id', order=1, type=HFI_FIELD)
        report.columns.add(field_id)
        return report

    def create_simple_contact(self):
        return Contact.objects.create(user=self.user)

    def get_field(self, report, field_name):
        try:
            return report.columns.get(name=field_name)
        except Field.DoesNotExist, e:
            self.fail(str(e))

    def test_report_createview02(self):
        name  = 'trinita'
        self.failIf(Report.objects.filter(name=name).exists())

        report  = self.create_report(name)
        columns = list(report.columns.order_by('order'))
        self.assertEqual(4, len(columns))

        field = columns[0]
        self.assertEqual('last_name', field.name)
        self.assertEqual('Last name', field.title)
        self.assertEqual(HFI_FIELD,   field.type)
        self.failIf(field.selected)
        self.failIf(field.report)

        self.assertEqual('user', columns[1].name)

        field = columns[2]
        self.assertEqual(REL_SUB_HAS, field.name)
        self.assertEqual('Related to',       field.title)
        self.assertEqual(HFI_RELATION,       field.type)
        self.failIf(field.selected)
        self.failIf(field.report)

        field = columns[3]
        self.assertEqual('get_pretty_properties', field.name)
        self.assertEqual('Properties', field.title)
        self.assertEqual(HFI_FUNCTION, field.type)

    def test_report_editview(self):
        report = self.create_report('trinita')

        response = self.client.get('/reports/report/edit/%s' % report.id)
        self.assertEqual(200, response.status_code)

        #TODO: complete this test

    def test_report_change_field_order01(self):
        report = self.create_report('trinita')
        field  = self.get_field(report, 'user')

        self.assertEqual(404, self.client.post('/reports/report/field/change_order').status_code)

        response = self.client.post('/reports/report/field/change_order',
                                    data={
                                            'report_id': report.id,
                                            'field_id':  field.id,
                                            'direction': 'up',
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        mod_report = Report.objects.get(pk=report.id) #seems useless but...
        self.assertEqual(['user', 'last_name', REL_SUB_HAS, 'get_pretty_properties'],
                         [f.name for f in mod_report.columns.order_by('order')])

    def test_report_change_field_order02(self):
        report = self.create_report('trinita')
        field  = self.get_field(report, 'user')

        response = self.client.post('/reports/report/field/change_order',
                                    data={
                                            'report_id': report.id,
                                            'field_id':  field.id,
                                            'direction': 'down',
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        mod_report = Report.objects.get(pk=report.id) #seems useless but...
        self.assertEqual(['last_name', REL_SUB_HAS, 'user', 'get_pretty_properties'],
                         [f.name for f in mod_report.columns.order_by('order')])

    def test_report_change_field_order03(self): #move 'up' the first field -> error
        report = self.create_report('trinita')
        field  = self.get_field(report, 'last_name')

        self.assertEqual(404, self.client.post('/reports/report/field/change_order').status_code)

        response = self.client.post('/reports/report/field/change_order',
                                    data={
                                            'report_id': report.id,
                                            'field_id':  field.id,
                                            'direction': 'up',
                                         }
                                   )
        self.assertEqual(response.status_code, 403)

    def test_report_csv01(self):
        report   = self.create_report('trinita')
        response = self.client.get('/reports/report/%s/csv' % report.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['CONTENT_TYPE'], 'text/html; charset=utf-8')
        self.assertEqual("Last name;User;Related to;Properties\r\n", response.content)

    def create_contacts(self):
        create_contact = Contact.objects.create
        asuka  = create_contact(user=self.user, last_name='Langley',   first_name='Asuka',  birthday=datetime(year=1981, month=7, day=25))
        rei    = create_contact(user=self.user, last_name='Ayanami',   first_name='Rei',    birthday=datetime(year=1981, month=3, day=26))
        misato = create_contact(user=self.user, last_name='Katsuragi', first_name='Misato', birthday=datetime(year=1976, month=8, day=12))
        nerv   = Organisation.objects.create(user=self.user, name='Nerv')

        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text='Kawaii')
        CremeProperty.objects.create(type=ptype, creme_entity=rei)

        Relation.objects.create(user=self.user, type_id=REL_SUB_HAS,
                                subject_entity=misato, object_entity=nerv)

    def test_report_csv02(self):
        self.create_contacts()
        report   = self.create_report('trinita')
        response = self.client.get('/reports/report/%s/csv' % report.id)
        self.assertEqual(response.status_code, 200)

        content = [s for s in response.content.split('\r\n') if s]
        self.assertEqual(4, len(content))
        self.assertEqual('Last name;User;Related to;Properties',     content[0])
        self.assertEqual('Ayanami;Kirika;;<ul><li>Kawaii</li></ul>', content[1]) #alphabetical ordering ??
        self.assertEqual('Katsuragi;Kirika;Nerv;<ul></ul>',          content[2])
        self.assertEqual('Langley;Kirika;;<ul></ul>',                content[3])

    def test_report_csv03(self): #with date filter
        self.create_contacts()
        report   = self.create_report('trinita')
        response = self.client.get('/reports/report/%s/csv' % report.id,
                                   data={
                                            'field': 'birthday',
                                            'start': datetime(year=1980, month=1, day=1).strftime('%s'),
                                            'end':   datetime(year=2000, month=1, day=1).strftime('%s'),
                                         }
                                  )
        self.assertEqual(response.status_code, 200)

        content = [s for s in response.content.split('\r\n') if s]
        self.assertEqual(3, len(content))
        self.assertEqual('Ayanami;Kirika;;<ul><li>Kawaii</li></ul>', content[1])
        self.assertEqual('Langley;Kirika;;<ul></ul>',                content[2])

    def test_report_field_add01(self):
        report = self.create_report('trinita')
        url = '/reports/report/%s/field/add' % report.id

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        try:
            form = response.context['form']
            fields_columns = form.fields['columns']
        except KeyError, e:
            self.fail(str(e))

        for i, (fname, fvname) in enumerate(fields_columns.choices):
            if fname == 'last_name': created_index = i; break
        else:
            self.fail('No "last_name" field')

        response = self.client.post(url,
                                    data={
                                            'user': self.user.pk,
                                            'columns_check_%s' % created_index: 'on',
                                            'columns_value_%s' % created_index: 'last_name',
                                            'columns_order_%s' % created_index: 1,
                                         }
                                   )

        self.assertEqual(response.status_code, 200)
        self.assertNoFormError(response)
        self.assertEqual(1, report.columns.count())

    def test_report_fetch01(self):
        report = self.create_simple_report("Contacts report")
        contact_ids = set([str(self.create_simple_contact().id) for i in xrange(10)])

        self.assertEqual(contact_ids, set(chain.from_iterable(report.fetch())))

    def test_get_predicates_choices_4_ct(self):
        response = self.client.post('/reports/get_predicates_choices_4_ct', data={'ct_id': ContentType.objects.get_for_model(Report).id})
        self.assertEqual(response.status_code, 200)

    def _setUp_big_report(self):
        ct_invoice     = ContentType.objects.get_for_model(Invoice)
        ct_orga        = ContentType.objects.get_for_model(Organisation)
        ct_contact     = ContentType.objects.get_for_model(Contact)
        ct_opportunity = ContentType.objects.get_for_model(Opportunity)
        user = self.user

        opp_fields_data = [
            #Opportunities
            {"name": "name",         "title": "Nom de l'opportunit\u00e9",     "selected": False, "report": None, "type": HFI_FIELD, "order": 1},
            {"name": "reference",    "title": "R\u00e9f\u00e9rence",           "selected": False, "report": None, "type": HFI_FIELD, "order": 2},
            {"name": "closing_date", "title": "Date de signature r\u00e9elle", "selected": False, "report": None, "type": HFI_FIELD, "order": 3},
        ]
        opp_fields = [Field.objects.create(**d) for d in opp_fields_data]
        report_opp = self.report_opp = Report.objects.create(**{"filter": None, "name": "Rapport des opportunit\u00e9s", "ct": ct_opportunity, "user": user})
        report_opp.columns = opp_fields

        invoice_fields_data = [
            #Invoice
            {"name": "name",           "title": "Nom",                           "selected": False, "report": None, "type": HFI_FIELD,      "order": 1},
            {"name": "issuing_date",   "title": "Date d'\u00e9mission",          "selected": False, "report": None, "type": HFI_FIELD,      "order": 2},
            {"name": "status__name",   "title": "Statut de la facture - Statut", "selected": False, "report": None, "type": HFI_FIELD,      "order": 3},
            {"name": "total_vat__sum", "title": "Somme - Total avec TVA",        "selected": False, "report": None, "type": HFI_CALCULATED, "order": 4},
        ]
        invoice_fields = [Field.objects.create(**d) for d in invoice_fields_data]
        report_invoice = self.report_invoice = Report.objects.create(filter=None, name="Rapport des factures", ct=ct_invoice, user=user)
        report_invoice.columns = invoice_fields

        orga_fields_data = [
            #Orga
            {"name": "name",                    "title": "Nom",                                                  "selected": False, "report": None,           "type": HFI_FIELD,      "order": 1},
            {"name": "user__username",          "title": "Utilisateur - nom d'utilisateur",                      "selected": False, "report": None,           "type": HFI_FIELD,      "order": 2},
            {"name": "legal_form__title",       "title": "Forme juridique - Intitul\u00e9",                      "selected": False, "report": None,           "type": HFI_FIELD,      "order": 3},
            {"name": REL_OBJ_BILL_ISSUED,       "title": "a \u00e9mis &mdash; a \u00e9t\u00e9 \u00e9mis(e) par", "selected": True,  "report": report_invoice, "type": HFI_RELATION,   "order": 4},
            {"name": REL_OBJ_CUSTOMER_SUPPLIER, "title": "est un fournisseur de &mdash; est client de",          "selected": False, "report": None,           "type": HFI_RELATION,   "order": 5},
            {"name": REL_SUB_EMIT_ORGA,         "title": "a g\u00e9n\u00e9r\u00e9 l'opportunit\u00e9 &mdash; a \u00e9t\u00e9 g\u00e9n\u00e9r\u00e9 par", "selected": False, "report": report_opp, "type": HFI_RELATION, "order": 6},
            {"name": "capital__min",            "title": "Minimum - Capital",                                    "selected": False, "report": None,           "type": HFI_CALCULATED, "order": 7},
            {"name": "get_pretty_properties",   "title": "Propriétés",                                           "selected": False, "report": None,           "type": HFI_FUNCTION,   "order": 8},
        ]
        orga_fields = [Field.objects.create(**d) for d in orga_fields_data]
        report_orga = self.report_orga = Report.objects.create(**{"filter": None, "name": "Rapport des organisations", "ct": ct_orga, "user": user})
        report_orga.columns = orga_fields

        contact_fields_data = [
            #Contact
            {"name": "last_name",         "title": "Nom",                            "selected": False, "report": None,        "type": HFI_FIELD,    "order": 1},
            {"name": "first_name",        "title": "Pr\u00e9nom",                    "selected": False, "report": None,        "type": HFI_FIELD,    "order": 2},
            {"name": "language__name",    "title": "Langue(s) parl\u00e9e(s) - Nom", "selected": False, "report": None,        "type": HFI_FIELD,    "order": 3},
            {"name": REL_SUB_EMPLOYED_BY, "title": "est salari\u00e9 de",            "selected": True,  "report": report_orga, "type": HFI_RELATION, "order": 4},
        ]
        contact_fields = [Field.objects.create(**d) for d in contact_fields_data]
        report_contact = self.report_contact = Report.objects.create(**{"filter": None, "name": "Rapport contact", "ct": ct_contact, "user": user})
        report_contact.columns = contact_fields

    def _setUp_data_for_big_report(self):
        now = datetime.now()
        managed_by_creme = CremePropertyType.objects.get(pk=PROP_IS_MANAGED_BY_CREME)

        user=self.user

        #Organisations
        self.nintendo_lf = LegalForm.objects.get_or_create(title=u"Nintendo SA")[0]
        self.nintendo    = Organisation.objects.create(user=user, name=u"Nintendo", legal_form=self.nintendo_lf, capital=100)
        CremeProperty.objects.create(type=managed_by_creme, creme_entity=self.nintendo)

        self.virgin_lf = LegalForm.objects.get_or_create(title=u"Virgin SA")[0]
        self.virgin    = Organisation.objects.create(user=user, name=u"Virgin", legal_form=self.virgin_lf, capital=200)

        self.sega_lf = LegalForm.objects.get_or_create(title=u"Sega SA")[0]
        self.sega    = Organisation.objects.create(user=user, name=u"SEGA", legal_form=self.sega_lf, capital=300)

        self.sony_lf = LegalForm.objects.get_or_create(title=u"Sony SA")[0]
        self.sony    = Organisation.objects.create(user=user, name=u"Sony", legal_form=self.sony_lf, capital=300)

        #Contacts
        self.mario = Contact.objects.create(first_name=u"Mario", last_name=u"Bros", user=user)
        self.mario.language = Language.objects.all()
        Relation.objects.create(subject_entity=self.mario, object_entity=self.nintendo, type_id=REL_SUB_EMPLOYED_BY, user=user)

        self.luigi = Contact.objects.create(first_name=u"Luigi", last_name=u"Bros", user=user)
        Relation.objects.create(subject_entity=self.luigi, object_entity=self.nintendo, type_id=REL_SUB_EMPLOYED_BY, user=user)

        self.sonic = Contact.objects.create(first_name=u"Sonic", last_name=u"Hedgehog", user=user)
        Relation.objects.create(subject_entity=self.sonic, object_entity=self.sega, type_id=REL_SUB_EMPLOYED_BY, user=user)

        self.crash = Contact.objects.create(first_name=u"Crash", last_name=u"Bandicoot", user=user)
        Relation.objects.create(subject_entity=self.crash, object_entity=self.sony, type_id=REL_SUB_EMPLOYED_BY, user=user)

        self.issuing_date = now.date()
        #Invoices
        def create_invoice(source, target, name="", total_vat=Decimal("0")):
            self.invoice_status = InvoiceStatus.objects.get_or_create(name=_(u"Draft"))[0]
            invoice = Invoice.objects.create(user=user, status=self.invoice_status, issuing_date=self.issuing_date, name=name, total_vat=total_vat)
#            invoice._productlines_cache = [ProductLine(quantity=Decimal("1"), unit_price=total_vat)]

            pl=ProductLine(quantity=Decimal("1"), unit_price=total_vat, user=user, vat=Decimal("0"))
            pl.save()
            pl.related_document = invoice
            invoice._productlines_cache = [pl]
            invoice.save()

            Relation.objects.create(subject_entity=invoice,
                            type_id=REL_SUB_BILL_ISSUED,
                            object_entity=source,
                            user=user
                           )

            Relation.objects.create(subject_entity=invoice,
                                    type_id=REL_SUB_BILL_RECEIVED,
                                    object_entity=target,
                                    user=user
                                   )
            return invoice

        self.invoices = {
            self.nintendo.pk: [
                create_invoice(self.nintendo, self.virgin, name="Invoice 1", total_vat=Decimal("10")),
                create_invoice(self.nintendo, self.sega,   name="Invoice 2", total_vat=Decimal("2")),
            ],
            self.virgin.pk: [],
            self.sega.pk:   [],
            self.sony.pk:   [],
        }

        def _create_opportunity(name="", reference=""):
            sales_phase = SalesPhase.objects.get_or_create(name="Forthcoming")[0]
            self.closing_date = date(year=2011, month=8, day=31)
            return Opportunity.objects.create(user=user, sales_phase=sales_phase, name=name, reference=reference, closing_date=self.closing_date)

        self.create_opportunity = create_opportunity = _create_opportunity

        self.opportunities = [create_opportunity(name="Opportunity %s" % i, reference=i) for i in xrange(1, 11)]

    def test_big_report_fetch01(self):
        self.populate('creme_core', 'persons', 'opportunities', 'billing')
        self._setUp_big_report()
        self._setUp_data_for_big_report()
        user = self.user

        targeted_organisations = [self.nintendo, self.sega, self.virgin, self.sony]
        targeted_contacts      = [self.crash, self.sonic, self.mario, self.luigi]
#        targeted_contacts      = [self.crash, ]#Temp

        #Target only own created organisations
        Organisation.objects.filter(~Q(id__in=[o.id for o in targeted_organisations])).delete()
        Contact.objects.filter(~Q(id__in=[c.id for c in targeted_contacts])).delete()

        #Test opportunities report
        report_opp = self.report_opp
        ##Headers
        self.assertEqual(set([u'name', u'reference', u'closing_date']), set(f.name for f in report_opp.get_children_fields_flat()))
        ##Data
        self.assertEqual([[u"Opportunity %s" % i, u"%s" % i, unicode(self.closing_date)] for i in xrange(1, 11)], report_opp.fetch_all_lines(user=user))

        #Test invoices report
        report_invoice = self.report_invoice
        ##Headers
        invoice_headers = ["name",  "issuing_date", "status__name", "total_vat__sum"]
        self.assertEqual(invoice_headers, list(f.name for f in report_invoice.get_children_fields_flat()))

        nintendo_invoice_1 = [u"Invoice 1", unicode(self.issuing_date), unicode(self.invoice_status.name), Decimal("12.00")]
        nintendo_invoice_2 = [u"Invoice 2", unicode(self.issuing_date), unicode(self.invoice_status.name), Decimal("12.00")]

        invoice_data = [
            nintendo_invoice_1,
            nintendo_invoice_2,
        ]
        self.assertEqual(invoice_data, report_invoice.fetch_all_lines(user=user))

        #Test organisations report
        ##Headers
        ##REL_OBJ_BILL_ISSUED replaced by invoice_headers because of explosion of subreport
        report_orga = self.report_orga
        orga_headers = list(chain([u"name", u"user__username", u"legal_form__title"], invoice_headers, [REL_OBJ_CUSTOMER_SUPPLIER, REL_SUB_EMIT_ORGA, u"capital__min", u'get_pretty_properties']))
        self.assertEqual(orga_headers, list(f.name for f in report_orga.get_children_fields_flat()))

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

        opportunity_nintendo_1 = self.create_opportunity(name="Opportunity nintendo 1", reference=u"1.1")
        Relation.objects.create(subject_entity=self.nintendo,
            type_id=REL_SUB_EMIT_ORGA,
            object_entity=opportunity_nintendo_1,
            user=user
        )

        opp_nintendo_values = " - ".join([u"%s: %s" % (get_verbose_field_name(model=Opportunity, separator="-", field_name=field_name), get_field_infos(opportunity_nintendo_1, field_name)[1]) for field_name in [u'name', u'reference', u'closing_date']])
        min_capital = min([o.capital for o in targeted_organisations])

        ##Data
        nintendo = self.nintendo
        sega     = self.sega
        sony     = self.sony
        virgin   = self.virgin

        orga_data = OrderedDict([
            ("nintendo_invoice1", list(chain([nintendo.name, unicode(nintendo.user.username), self.nintendo_lf.title], nintendo_invoice_1,                [u", ".join([unicode(sony), unicode(sega)]), opp_nintendo_values, min_capital, nintendo.get_pretty_properties()]))),
            ("nintendo_invoice2", list(chain([nintendo.name, unicode(nintendo.user.username), self.nintendo_lf.title], nintendo_invoice_2,                [u", ".join([unicode(sony), unicode(sega)]), opp_nintendo_values, min_capital, nintendo.get_pretty_properties()]))),
            ("sega",              list(chain([sega.name,     unicode(sega.user.username),     self.sega_lf.title],     [u"" for i in nintendo_invoice_2], [u"",                                        u""],               [min_capital, sega.get_pretty_properties()]))),
            ("sony",              list(chain([sony.name,     unicode(sony.user.username),     self.sony_lf.title],     [u"" for i in nintendo_invoice_2], [u"",                                        u""],               [min_capital, sony.get_pretty_properties()]))),
            ("virgin",            list(chain([virgin.name,   unicode(virgin.user.username),   self.virgin_lf.title],   [u"" for i in nintendo_invoice_2], [u"",                                        u""],               [min_capital, virgin.get_pretty_properties()]))),
        ])
        self.assertEqual(orga_data.values(), report_orga.fetch_all_lines(user=user))

        #Test contacts report
        ##Headers
        report_contact  = self.report_contact
        contact_headers = list(chain(["last_name", "first_name", "language__name"], orga_headers))
        self.assertEqual(contact_headers, list(f.name for f in report_contact.get_children_fields_flat()))

        self.maxDiff = None

        ##Data
        crash = self.crash
        luigi = self.luigi
        mario = self.mario
        sonic = self.sonic

        contact_data = [
            list(chain([crash.last_name, crash.first_name, u""], orga_data['sony'])),
            list(chain([luigi.last_name, luigi.first_name, u""], orga_data['nintendo_invoice1'])),
            list(chain([luigi.last_name, luigi.first_name, u""], orga_data['nintendo_invoice2'])),
            list(chain([mario.last_name, mario.first_name, u", ".join(mario.language.values_list("name", flat=True))], orga_data['nintendo_invoice1'])),
            list(chain([mario.last_name, mario.first_name, u", ".join(mario.language.values_list("name", flat=True))], orga_data['nintendo_invoice2'])),
            list(chain([sonic.last_name, sonic.first_name, u""], orga_data['sega'])),
        ]
        self.assertEqual(contact_data, report_contact.fetch_all_lines())

        #TODO: test HFI_RELATED, HFI_CUSTOM

#TODO: test with subreports, expanding etc...
