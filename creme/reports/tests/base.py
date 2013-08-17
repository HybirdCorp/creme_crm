# -*- coding: utf-8 -*-

try:
    from datetime import datetime, date
    from decimal import Decimal
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import CremePropertyType, CremeProperty, Relation, Language, RelationType
    from creme.creme_core.models.header_filter import HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CALCULATED, HeaderFilterItem, HeaderFilter
    from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME, REL_SUB_HAS
    from creme.creme_core.tests.base import CremeTestCase

    from creme.billing.models import Invoice, InvoiceStatus, ProductLine, Vat
    from creme.billing.constants import REL_OBJ_BILL_ISSUED, REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

    from creme.opportunities.models import Opportunity, SalesPhase
    from creme.opportunities.constants import REL_SUB_EMIT_ORGA

    from creme.persons.models import Contact, Organisation, LegalForm
    from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_OBJ_CUSTOMER_SUPPLIER

    from ..models import Field, Report
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class BaseReportsTestCase(CremeTestCase):
    ADD_URL = '/reports/report/add'
    SET_FIELD_ORDER_URL = '/reports/report/field/change_order'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'reports',
                     'persons', 'opportunities', 'billing',
                    )

    def setUp(self):
        self.login()

    def create_report(self, name='Report #1', efilter=None, extra_hfitems=()):
        hf = HeaderFilter.create(pk='test_hf', name='name', model=Contact)

        hf_items = [HeaderFilterItem.build_4_field(model=Contact, name='last_name'),
                    HeaderFilterItem.build_4_field(model=Contact, name='user'),
                    HeaderFilterItem.build_4_relation(RelationType.objects.get(pk=REL_SUB_HAS)),
                    HeaderFilterItem.build_4_functionfield(Contact.function_fields.get('get_pretty_properties')),
                   ]
        hf_items.extend(extra_hfitems)
        hf.set_items(hf_items)

        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user':   self.user.pk,
                                          'name':   name,
                                          'ct':     ContentType.objects.get_for_model(Contact).id,
                                          'hf':     hf.id,
                                          'filter': efilter.id if efilter else '',
                                         }
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Report, name=name)

    def create_simple_contacts_report(self, name='Contact report', efilter=None):
        ct = ContentType.objects.get_for_model(Contact)
        report = Report.objects.create(user=self.user, name=name, ct=ct, filter=efilter)
        report.columns.add(Field.objects.create(name=u'last_name',
                                                title=u'Last name',
                                                order=1, type=HFI_FIELD,
                                               )
                          )

        return report

    def create_simple_organisations_report(self, name='Orga report', efilter=None):
        ct = ContentType.objects.get_for_model(Organisation)
        report = Report.objects.create(user=self.user, name=name, ct=ct, filter=efilter)
        report.columns.add(Field.objects.create(name=u'name',
                                                title=u'Name',
                                                order=1, type=HFI_FIELD,
                                               )
                          )

        return report

    def get_field_or_fail(self, report, field_name):
        try:
            return report.columns.get(name=field_name)
        except Field.DoesNotExist as e:
            self.fail(str(e))

    def create_contacts(self):
        user = self.user
        create_contact = partial(Contact.objects.create, user=user)
        create_contact(last_name='Langley',   first_name='Asuka',  birthday=datetime(year=1981, month=7, day=25))
        rei    = create_contact(last_name='Ayanami',   first_name='Rei',    birthday=datetime(year=1981, month=3, day=26))
        misato = create_contact(last_name='Katsuragi', first_name='Misato', birthday=datetime(year=1976, month=8, day=12))
        nerv   = Organisation.objects.create(user=user, name='Nerv')

        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text='Kawaii')
        CremeProperty.objects.create(type=ptype, creme_entity=rei)

        Relation.objects.create(user=user, type_id=REL_SUB_HAS,
                                subject_entity=misato, object_entity=nerv
                               )

    def _create_reports(self):
        get_ct = ContentType.objects.get_for_model
        create_field = Field.objects.create
        create_report = partial(Report.objects.create, user=self.user, filter=None)

        report_opp = self.report_opp = create_report(name="Report on opportunities", ct=get_ct(Opportunity))
        report_opp.columns = [
            create_field(name="name",         title="Name",         selected=False, report=None, type=HFI_FIELD, order=1),
            create_field(name="reference",    title="Reference",    selected=False, report=None, type=HFI_FIELD, order=2),
            create_field(name="closing_date", title="Closing date", selected=False, report=None, type=HFI_FIELD, order=3),
          ]

        report_invoice = self.report_invoice = create_report(name="Report on invoices", ct=get_ct(Invoice))
        report_invoice.columns = [
            create_field(name="name",           title="Name",                         selected=False, report=None, type=HFI_FIELD,      order=1),
            create_field(name="issuing_date",   title="Issuing date",                 selected=False, report=None, type=HFI_FIELD,      order=2),
            create_field(name="status__name",   title="Status - title",               selected=False, report=None, type=HFI_FIELD,      order=3),
            create_field(name="total_vat__sum", title="Sum - Total inclusive of tax", selected=False, report=None, type=HFI_CALCULATED, order=4),
          ]

        report_orga = self.report_orga = create_report(name="Organisations report", ct=get_ct(Organisation))
        report_orga.columns = [
            create_field(name="name",                    title="Name",                                                        selected=False, report=None,           type=HFI_FIELD,      order=1),
            create_field(name="user__username",          title="User - username",                                             selected=False, report=None,           type=HFI_FIELD,      order=2),
            create_field(name="legal_form__title",       title="Legal form - title",                                          selected=False, report=None,           type=HFI_FIELD,      order=3),
            create_field(name=REL_OBJ_BILL_ISSUED,       title="has issued &mdash; issued by",                                selected=True,  report=report_invoice, type=HFI_RELATION,   order=4),
            create_field(name=REL_OBJ_CUSTOMER_SUPPLIER, title="is a supplier of &mdash; is a customer of",                   selected=False, report=None,           type=HFI_RELATION,   order=5),
            create_field(name=REL_SUB_EMIT_ORGA,         title="has generated the opportunity &mdash; has been generated by", selected=False, report=report_opp,     type=HFI_RELATION,   order=6),
            create_field(name="capital__min",            title="Minimum - Capital",                                           selected=False, report=None,           type=HFI_CALCULATED, order=7),
            create_field(name="get_pretty_properties",   title="Properties",                                                  selected=False, report=None,           type=HFI_FUNCTION,   order=8),
          ]

        report_contact = self.report_contact = create_report(name="Report on contacts", ct=get_ct(Contact))
        report_contact.columns = [
            create_field(name="last_name",         title="Last name",          selected=False, report=None,        type=HFI_FIELD,    order=1),
            create_field(name="first_name",        title="First name",         selected=False, report=None,        type=HFI_FIELD,    order=2),
            create_field(name="language__name",    title="Language(s) - Name", selected=False, report=None,        type=HFI_FIELD,    order=3),
            create_field(name=REL_SUB_EMPLOYED_BY, title="is employed by",     selected=True,  report=report_orga, type=HFI_RELATION, order=4),
          ]

    def _create_invoice(self, source, target, name="", total_vat=Decimal("0")):
        # TODO: improve billing to make this code simpler
        self.invoice_status = InvoiceStatus.objects.get_or_create(name=_(u"Draft"))[0]
        user = self.user
        self.issuing_date = getattr(self, 'issuing_date', None) or now().date()
        invoice = Invoice.objects.create(user=user, status=self.invoice_status,
                                         issuing_date=self.issuing_date, name=name,
                                         total_vat=total_vat
                                        )
        ProductLine.objects.create(user=user, related_document=invoice,
                                   on_the_fly_item='Stuff',
                                   quantity=Decimal("1"), unit_price=total_vat,
                                   vat_value=Vat.objects.create(value=Decimal()),
                                  )

        create_rel = partial(Relation.objects.create, subject_entity=invoice, user=user)
        create_rel(type_id=REL_SUB_BILL_ISSUED,   object_entity=source)
        create_rel(type_id=REL_SUB_BILL_RECEIVED, object_entity=target)

        return invoice

    def _setUp_data_for_big_report(self):
        managed_by_creme = CremePropertyType.objects.get(pk=PROP_IS_MANAGED_BY_CREME)
        user = self.user

        #Organisations
        create_orga = partial(Organisation.objects.create, user=user)
        self.nintendo_lf = LegalForm.objects.get_or_create(title=u"Nintendo SA")[0]
        self.nintendo    = create_orga(name=u"Nintendo", legal_form=self.nintendo_lf, capital=100)
        CremeProperty.objects.create(type=managed_by_creme, creme_entity=self.nintendo)

        self.virgin_lf = LegalForm.objects.get_or_create(title=u"Virgin SA")[0]
        self.virgin    = create_orga(name=u"Virgin", legal_form=self.virgin_lf, capital=200)

        self.sega_lf = LegalForm.objects.get_or_create(title=u"Sega SA")[0]
        self.sega    = create_orga(name=u"SEGA", legal_form=self.sega_lf, capital=300)

        self.sony_lf = LegalForm.objects.get_or_create(title=u"Sony SA")[0]
        self.sony    = create_orga(name=u"Sony", legal_form=self.sony_lf, capital=300)

        #Contacts
        create_contact = partial(Contact.objects.create, user=user)
        create_rel = partial(Relation.objects.create, type_id=REL_SUB_EMPLOYED_BY, user=user)
        self.mario = create_contact(first_name='Mario', last_name='Bros')
        self.mario.language = Language.objects.all()
        create_rel(subject_entity=self.mario, object_entity=self.nintendo)

        self.luigi = create_contact(first_name='Luigi', last_name='Bros')
        create_rel(subject_entity=self.luigi, object_entity=self.nintendo)

        self.sonic = create_contact(first_name='Sonic', last_name='Hedgehog')
        create_rel(subject_entity=self.sonic, object_entity=self.sega)

        self.crash = create_contact(first_name='Crash', last_name='Bandicoot')
        create_rel(subject_entity=self.crash, object_entity=self.sony)

        create_invoice = partial(self._create_invoice, self.nintendo)
        self.invoices = {
            self.nintendo.pk: [create_invoice(self.virgin, name="Invoice 1", total_vat=Decimal("10")),
                               create_invoice(self.sega,   name="Invoice 2", total_vat=Decimal("2")),
                              ],
            self.virgin.pk:   [],
            self.sega.pk:     [],
            self.sony.pk:     [],
        }

        sales_phase = SalesPhase.objects.get_or_create(name="Forthcoming")[0]
        self.closing_date = date(year=2011, month=8, day=31)

        def _create_opportunity(name, reference, emitter=None):
            return Opportunity.objects.create(user=user, name=name, reference=reference,
                                              sales_phase=sales_phase,
                                              closing_date=self.closing_date,
                                              emitter=emitter or create_orga(name='Emitter organisation #%s' %i),
                                              target=create_orga(name='Target organisation #%s' %i),
                                             )

        self.create_opportunity = _create_opportunity
        self.opportunities = [_create_opportunity(name="Opportunity %s" % i, reference=str(i)) for i in xrange(1, 11)]
