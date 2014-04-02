# -*- coding: utf-8 -*-

try:
    from datetime import datetime
    from decimal import Decimal
    from functools import partial

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.utils.timezone import now
    #from django.utils.translation import ugettext as _

    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.models import (CremePropertyType, CremeProperty,
            HeaderFilter, Relation, RelationType, Vat)
    from creme.creme_core.constants import REL_SUB_HAS
    from creme.creme_core.tests.base import CremeTestCase

    from creme.documents.models import Folder

    from creme.persons.models import Contact, Organisation
    from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_OBJ_CUSTOMER_SUPPLIER

    if 'creme.billing' in settings.INSTALLED_APPS:
        from creme.billing.models import Invoice, InvoiceStatus, ProductLine
        from creme.billing.constants import REL_OBJ_BILL_ISSUED, REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

    if 'creme.opportunities' in settings.INSTALLED_APPS:
        from creme.opportunities.models import Opportunity, SalesPhase
        from creme.opportunities.constants import REL_SUB_EMIT_ORGA

    from ..constants import RFT_FIELD, RFT_RELATION, RFT_AGG_FIELD #RFT_AGGREGATE
    from ..models import Field, Report
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class BaseReportsTestCase(CremeTestCase):
    ADD_URL = '/reports/report/add'
    SET_FIELD_ORDER_URL = '/reports/report/field/change_order'

    @classmethod
    def setUpClass(cls):
        apps = ['creme_core', 'creme_config', 'reports', 'persons']

        if 'creme.billing' in settings.INSTALLED_APPS:
            apps.append('billing')

        if 'creme.opportunities' in settings.INSTALLED_APPS:
            apps.append('opportunities')

        cls.populate(*apps)

        Folder.objects.all().delete()

    def _create_report(self, name='Report #1', efilter=None, extra_cells=()):
        cells = [EntityCellRegularField.build(model=Contact, name='last_name'),
                 EntityCellRegularField.build(model=Contact, name='user'),
                 EntityCellRelation(RelationType.objects.get(pk=REL_SUB_HAS)),
                 EntityCellFunctionField(Contact.function_fields.get('get_pretty_properties')),
                ]
        cells.extend(extra_cells)

        hf = HeaderFilter.create(pk='test_hf', name='name', model=Contact, cells_desc=cells)

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

    def _create_simple_contacts_report(self, name='Contact report', efilter=None):
        ct = ContentType.objects.get_for_model(Contact)
        report = Report.objects.create(user=self.user, name=name, ct=ct, filter=efilter)
        Field.objects.create(report=report, name='last_name', type=RFT_FIELD, order=1)

        return report

    def _create_simple_organisations_report(self, name='Orga report', efilter=None):
        ct = ContentType.objects.get_for_model(Organisation)
        report = Report.objects.create(user=self.user, name=name, ct=ct, filter=efilter)
        Field.objects.create(report=report, name=u'name', type=RFT_FIELD, order=1)

        return report

    def get_field_or_fail(self, report, field_name):
        try:
            return report.fields.get(name=field_name)
        except Field.DoesNotExist as e:
            self.fail(str(e))

    def _create_persons(self):
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
        create_field = partial(Field.objects.create, sub_report=None, selected=False, type=RFT_FIELD)
        create_report = partial(Report.objects.create, user=self.user, filter=None)

        report_opp = self.report_opp = create_report(name="Report on opportunities", ct=get_ct(Opportunity))
        create_field(report=report_opp, name='name',      order=1)
        create_field(report=report_opp, name='reference', order=2)

        report_invoice = self.report_invoice = create_report(name="Report on invoices", ct=get_ct(Invoice))
        create_field(report=report_invoice, name='name',                               order=1)
        #create_field(report=report_invoice, name='total_vat__sum', type=RFT_AGGREGATE, order=2)
        create_field(report=report_invoice, name='total_vat__sum', type=RFT_AGG_FIELD, order=2)

        report_orga = self.report_orga = create_report(name="Organisations report", ct=get_ct(Organisation))
        create_field(report=report_orga, name='name',                                                                                   order=1)
        create_field(report=report_orga, name=REL_OBJ_BILL_ISSUED,       type=RFT_RELATION,   sub_report=report_invoice, selected=True, order=2)
        create_field(report=report_orga, name=REL_OBJ_CUSTOMER_SUPPLIER, type=RFT_RELATION,                                             order=3)
        create_field(report=report_orga, name=REL_SUB_EMIT_ORGA,         type=RFT_RELATION,   sub_report=report_opp,                    order=4)
        #create_field(report=report_orga, name='capital__min',            type=RFT_AGGREGATE,                                           order=5)
        create_field(report=report_orga, name='capital__min',            type=RFT_AGG_FIELD,                                            order=5)

        report_contact = self.report_contact = create_report(name="Report on contacts", ct=get_ct(Contact))
        create_field(report=report_contact, name='last_name',                                                                   order=1)
        create_field(report=report_contact, name='first_name',                                                                  order=2)
        create_field(report=report_contact, name=REL_SUB_EMPLOYED_BY, type=RFT_RELATION, sub_report=report_orga, selected=True, order=3)

    def _create_invoice(self, source, target, name="", total_vat=Decimal("0")):
        # TODO: improve billing to make this code simpler
        user = self.user
        self.issuing_date = getattr(self, 'issuing_date', None) or now().date()
        invoice = Invoice.objects.create(user=user,
                                         status=InvoiceStatus.objects.all()[0],
                                         issuing_date=self.issuing_date,
                                         name=name,
                                         total_vat=total_vat,
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
        user = self.user

        #Organisations
        create_orga = partial(Organisation.objects.create, user=user)
        self.nintendo = create_orga(name=u"Nintendo", capital=100)
        self.virgin   = create_orga(name=u"Virgin", capital=200)
        self.sega     = create_orga(name=u"SEGA", capital=300)
        self.sony     = create_orga(name=u"Sony", capital=300)

        #Contacts
        create_contact = partial(Contact.objects.create, user=user)
        self.mario = create_contact(first_name='Mario', last_name='Bros')
        self.luigi = create_contact(first_name='Luigi', last_name='Bros')
        self.sonic = create_contact(first_name='Sonic', last_name='Hedgehog')
        self.crash = create_contact(first_name='Crash', last_name='Bandicoot')

        create_rel = partial(Relation.objects.create, type_id=REL_SUB_EMPLOYED_BY, user=user)
        create_rel(subject_entity=self.mario, object_entity=self.nintendo)
        create_rel(subject_entity=self.luigi, object_entity=self.nintendo)
        create_rel(subject_entity=self.sonic, object_entity=self.sega)
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

        def _create_opportunity(name, reference, emitter=None):
            return Opportunity.objects.create(user=user, name=name, reference=reference,
                                              sales_phase=sales_phase,
                                              emitter=emitter or create_orga(name='Emitter organisation #%s' %i),
                                              target=create_orga(name='Target organisation #%s' %i),
                                             )

        self.create_opportunity = _create_opportunity
        self.opportunities = [_create_opportunity(name="Opportunity %s" % i, reference=str(i)) for i in xrange(1, 11)]
