# -*- coding: utf-8 -*-

skip_opportunity_tests = False

try:
    from datetime import date
    from decimal import Decimal
    from functools import partial
    from unittest import skipIf

    from django.apps import apps
    from django.contrib.contenttypes.models import ContentType
    from django.core.exceptions import ValidationError
    from django.db.models import Max
    from django.test.utils import override_settings
    from django.urls import reverse
    from django.utils.formats import number_format
    from django.utils.translation import ugettext as _, ungettext

    from creme.creme_core.tests.base import CremeTestCase, skipIfNotInstalled
    from creme.creme_core.tests.views.base import CSVImportBaseTestCaseMixin
    from creme.creme_core.models import (CremeEntity, RelationType, Relation,
            SetCredentials, Currency, SettingValue, FieldsConfig)
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.constants import DEFAULT_CURRENCY_PK

    from creme.documents import get_document_model

    from creme.persons import get_contact_model, get_organisation_model
    from creme.persons.constants import REL_SUB_PROSPECT, REL_SUB_CUSTOMER_SUPPLIER
    from creme.persons.tests.base import skipIfCustomOrganisation, skipIfCustomContact

    from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

    from creme.products import get_product_model, get_service_model

    if apps.is_installed('creme.billing'):
        from creme.billing import (get_invoice_model, get_quote_model,
                get_sales_order_model, get_service_line_model, quote_model_is_custom)
        from creme.billing.models import QuoteStatus
        from creme.billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

        skip_billing = False
        Invoice = get_invoice_model()
        Quote = get_quote_model()
        SalesOrder = get_sales_order_model()
        ServiceLine = get_service_line_model()
    else:
        skip_billing = True

    from . import opportunity_model_is_custom, get_opportunity_model
    from .models import SalesPhase, Origin
    from . import constants

    skip_opportunity_tests = opportunity_model_is_custom()
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


Organisation = get_organisation_model()
Contact = get_contact_model()

Opportunity = get_opportunity_model()


def skipIfCustomOpportunity(test_func):
    return skipIf(skip_opportunity_tests, 'Custom opportunity model in use')(test_func)


@skipIfCustomOpportunity
class OpportunitiesTestCase(CremeTestCase, CSVImportBaseTestCaseMixin):
    lvimport_data = {'step': 1,
                     # 'document': doc.id,
                     # has_header

                     # 'user':    user.id,
                     # 'emitter': emitter1.id,

                     # 'name_colselect':            1,
                     # 'estimated_sales_colselect': 3,
                     # 'made_sales_colselect':      4,

                     # 'sales_phase_colselect': 2,
                     # 'sales_phase_create':    True,
                     # 'sales_phase_defval':    sp5.pk,

                     # 'target_persons_organisation_colselect': 5,
                     # 'target_persons_organisation_create':    True,
                     # 'target_persons_contact_colselect':      6,
                     # 'target_persons_contact_create':         True,

                     'currency_colselect': 0,
                     'currency_defval':    DEFAULT_CURRENCY_PK,

                     'reference_colselect':              0,
                     'chance_to_win_colselect':          0,
                     'expected_closing_date_colselect':  0,
                     'closing_date_colselect':           0,
                     'origin_colselect':                 0,
                     'description_colselect':            0,
                     'first_action_date_colselect':      0,

                     # 'property_types',
                     # 'fixed_relations',
                     # 'dyn_relations',
                    }

    @classmethod
    def setUpClass(cls):
        super(OpportunitiesTestCase, cls).setUpClass()

        try:
            cls.ADD_URL = reverse('opportunities__create_opportunity')
        except Exception as e:
            print('Error in OpportunitiesTestCase.setUpClass(): {}'.format(e))

    def _build_addrelated_url(self, entity):
        return reverse('opportunities__create_related_opportunity', args=(entity.id,))

    def _genericfield_format_entity(self, entity):
        return '{"ctype": {"id": "%s"}, "entity":"%s"}' % (entity.entity_type_id, entity.id)

    def _create_target_n_emitter(self, managed=True, contact=False):
        user = self.user
        create_orga = Organisation.objects.create
        emitter = create_orga(user=user, name='My society', is_managed=managed)
        target  = create_orga(user=user, name='Target renegade') if not contact else \
                  Contact.objects.create(user=user, first_name='Target', last_name='Renegade')

        return target, emitter

    def _create_opportunity_n_organisations(self, name='Opp'):
        target, emitter = self._create_target_n_emitter()
        opp = Opportunity.objects.create(user=self.user, name=name,
                                         sales_phase=SalesPhase.objects.all()[0],
                                         emitter=emitter, target=target,
                                        )

        return opp, target, emitter

    def test_populate(self):  # test get_compatible_ones() too
        get_ct = ContentType.objects.get_for_model
        ct = get_ct(Opportunity)
        # relation_types = {rtype.id: rtype for rtype in RelationType.get_compatible_ones(ct)}
        relation_types = RelationType.get_compatible_ones(ct).in_bulk()

        Product = get_product_model()
        Service = get_service_model()

        self.assertNotIn(constants.REL_SUB_TARGETS, relation_types)
        self.get_relationtype_or_fail(constants.REL_SUB_TARGETS, [Opportunity], [Contact, Organisation])

        self.assertNotIn(constants.REL_SUB_EMIT_ORGA, relation_types)
        self.get_relationtype_or_fail(constants.REL_OBJ_EMIT_ORGA, [Opportunity], [Organisation])

        self.assertIn(constants.REL_OBJ_LINKED_PRODUCT, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_PRODUCT, relation_types)
        self.get_relationtype_or_fail(constants.REL_OBJ_LINKED_PRODUCT, [Opportunity], [Product])

        self.assertIn(constants.REL_OBJ_LINKED_SERVICE, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_SERVICE, relation_types)
        self.get_relationtype_or_fail(constants.REL_OBJ_LINKED_SERVICE, [Opportunity], [Service])

        self.assertIn(constants.REL_OBJ_LINKED_CONTACT, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_CONTACT, relation_types)
        self.get_relationtype_or_fail(constants.REL_OBJ_LINKED_CONTACT, [Opportunity], [Contact])

        if not skip_billing:
            self.assertIn(constants.REL_OBJ_LINKED_SALESORDER, relation_types)
            self.assertNotIn(constants.REL_SUB_LINKED_SALESORDER, relation_types)
            self.get_relationtype_or_fail(constants.REL_OBJ_LINKED_SALESORDER, [Opportunity], [SalesOrder])

            self.assertIn(constants.REL_OBJ_LINKED_INVOICE, relation_types)
            self.assertNotIn(constants.REL_SUB_LINKED_INVOICE, relation_types)
            self.get_relationtype_or_fail(constants.REL_OBJ_LINKED_INVOICE, [Opportunity], [Invoice])

            self.assertIn(constants.REL_OBJ_LINKED_QUOTE, relation_types)
            self.assertNotIn(constants.REL_SUB_LINKED_QUOTE, relation_types)
            self.get_relationtype_or_fail(constants.REL_OBJ_LINKED_QUOTE, [Opportunity], [Quote])

            self.get_relationtype_or_fail(constants.REL_OBJ_CURRENT_DOC, [Opportunity], [Invoice, Quote, SalesOrder])

        self.assertIn(constants.REL_OBJ_RESPONSIBLE, relation_types)
        self.assertNotIn(constants.REL_SUB_RESPONSIBLE, relation_types)
        self.get_relationtype_or_fail(constants.REL_OBJ_RESPONSIBLE, [Opportunity], [Contact])

        self.assertTrue(SalesPhase.objects.exists())
        self.assertTrue(Origin.objects.exists())

        self.assertEqual(1, SettingValue.objects.filter(key_id=constants.SETTING_USE_CURRENT_QUOTE).count())

        # Contribution to activities
        rtype = self.get_object_or_fail(RelationType, pk=REL_SUB_ACTIVITY_SUBJECT)
        self.assertTrue(rtype.subject_ctypes.filter(id=ct.id).exists())
        self.assertTrue(rtype.subject_ctypes.filter(id=get_ct(Contact).id).exists())
        self.assertTrue(rtype.symmetric_type.object_ctypes.filter(id=ct.id).exists())

    # def test_portal(self):
    #     self.login()
    #     self.assertGET200(reverse('opportunities__portal'))

    @skipIfCustomOrganisation
    def test_createview01(self):
        user = self.login()

        url = self.ADD_URL
        self.assertGET200(url)

        target, emitter = self._create_target_n_emitter()
        name  = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user':                  user.pk,
                                          'name':                  name,
                                          'sales_phase':           phase.id,
                                          'expected_closing_date': '2010-9-20',
                                          'closing_date':          '2010-10-11',
                                          'target':                self._genericfield_format_entity(target),
                                          'emitter':               emitter.id,
                                          'first_action_date':     '2010-7-13',
                                          'currency':              DEFAULT_CURRENCY_PK,
                                         }
                                   )
        self.assertNoFormError(response)

        opportunity =  self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(phase,              opportunity.sales_phase)
        self.assertEqual(date(2010, 9,  20), opportunity.expected_closing_date)
        self.assertEqual(date(2010, 10, 11), opportunity.closing_date)
        self.assertEqual(date(2010, 7,  13), opportunity.first_action_date)

        self.assertRelationCount(1, target,  constants.REL_OBJ_TARGETS,   opportunity)
        self.assertEqual(target, opportunity.target)

        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertEqual(emitter, opportunity.emitter)

        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

    @skipIfCustomOrganisation
    def test_createview02(self):
        user = self.login()

        target, emitter = self._create_target_n_emitter()
        name  = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user':                  user.pk,
                                          'name':                  name,
                                          'sales_phase':           phase.id,
                                          'expected_closing_date': '2010-9-20',
                                          'closing_date':          '2010-10-11',
                                          'target':                self._genericfield_format_entity(target),
                                          'emitter':               emitter.id,
                                          'first_action_date':     '2010-7-13',
                                          'currency':              DEFAULT_CURRENCY_PK,
                                         }
                                   )
        self.assertNoFormError(response)

        opportunity =  self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(phase,              opportunity.sales_phase)
        self.assertEqual(date(2010, 9,  20), opportunity.expected_closing_date)
        self.assertEqual(date(2010, 10, 11), opportunity.closing_date)
        self.assertEqual(date(2010, 7,  13), opportunity.first_action_date)

        self.assertRelationCount(1, target,  constants.REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

        with self.assertNumQueries(1):
            prop_emitter = opportunity.emitter
        self.assertEqual(emitter, prop_emitter)

        with self.assertNumQueries(3):
            prop_target = opportunity.target
        self.assertEqual(target, prop_target)

    @skipIfNotInstalled('creme.billing')
    def test_createview03(self):
        "Only contact & orga models are allowed as target"
        user = self.login()

        target = emitter = Invoice.objects.create(user=user, name='Invoice01',
                                                  expiration_date=date(year=2012, month=12, day=15),
                                                  status_id=1, number='INV0001',
                                                  currency_id=DEFAULT_CURRENCY_PK,
                                                 )
        name  = 'Opportunity01'
        phase = SalesPhase.objects.all()[0]
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user':                  user.pk,
                                          'name':                  name,
                                          'sales_phase':           phase.id,
                                          'expected_closing_date': '2010-9-20',
                                          'closing_date':          '2010-10-11',
                                          'target':                self._genericfield_format_entity(target),
                                          'emitter':               emitter.id,
                                          'first_action_date':     '2010-7-13',
                                          'currency':              DEFAULT_CURRENCY_PK,
                                         }
                                   )
        self.assertFormError(response, 'form', 'target', _('This content type is not allowed.'))
        self.assertFormError(response, 'form', 'emitter',
                             _('Select a valid choice. That choice is not one of the available choices.')
                            )
        self.assertRaises(Opportunity.DoesNotExist, Opportunity.objects.get, name=name)

    @skipIfCustomOrganisation
    def test_createview04(self):
        "LINK credentials error"
        self.login(is_superuser=False, allowed_apps=['opportunities'], creatable_models=[Opportunity])

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE | EntityCredentials.UNLINK, #no LINK
                                      set_type=SetCredentials.ESET_OWN
                                     )

        target, emitter = self._create_target_n_emitter()
        response = self.assertPOST200(self.ADD_URL, follow=True,
                                      data={'user':         self.user.pk,
                                            'name':         'My opportunity',
                                            'sales_phase':  SalesPhase.objects.all()[0].id,
                                            'closing_date': '2011-03-14',
                                            'target':       self._genericfield_format_entity(target),
                                            'emitter':      emitter.id,
                                            'currency':     DEFAULT_CURRENCY_PK,
                                           }
                                     )

        fmt1 = _(u'You are not allowed to link this entity: {}').format
        fmt2 = _(u'Entity #{id} (not viewable)').format
        self.assertFormError(response, 'form', 'target',  fmt1(fmt2(id=target.id)))
        self.assertFormError(response, 'form', 'emitter', fmt1(fmt2(id=emitter.id)))

    @skipIfCustomOrganisation
    def test_createview05(self):
        "Emitter not managed by Creme"
        self.login()

        target, emitter = self._create_target_n_emitter(managed=False)
        response = self.assertPOST200(self.ADD_URL, follow=True,
                                      data={'user':         self.user.pk,
                                            'name':         'My opportunity',
                                            'sales_phase':  SalesPhase.objects.all()[0].id,
                                            'closing_date': '2011-03-14',
                                            'target':       self._genericfield_format_entity(target),
                                            'emitter':      emitter.id,
                                            }
                                     )
        self.assertFormError(response, 'form', 'emitter',
                             _('Select a valid choice. That choice is not one of the available choices.')
                            )

    @skipIfCustomOrganisation
    def test_add_to_orga01(self):
        user = self.login()

        target, emitter = self._create_target_n_emitter()
        url = self._build_addrelated_url(target)
        self.assertGET200(url)

        salesphase = SalesPhase.objects.all()[0]
        name = 'Opportunity linked to {}'.format(target)
        response = self.client.post(url, data={'user':         user.pk,
                                               'name':         name,
                                               'sales_phase':  salesphase.id,
                                               'closing_date': '2011-03-12',
                                               'target':       self._genericfield_format_entity(target),
                                               'emitter':      emitter.id,
                                               'currency':     DEFAULT_CURRENCY_PK,
                                              }
                                   )
        self.assertNoFormError(response, status=302)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  constants.REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

        response = self.client.post(url, follow=True,
                                    data={'user':         user.pk,
                                          'name':         'Opportunity Two linked to {}'.format(target),
                                          'sales_phase':  salesphase.id,
                                          'closing_date': '2011-03-12',
                                          'target':       self._genericfield_format_entity(target),
                                          'emitter':      emitter.id,
                                          'currency':     DEFAULT_CURRENCY_PK,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    @skipIfCustomOrganisation
    def test_add_to_orga02(self):
        user = self.login()

        target, emitter = self._create_target_n_emitter()
        url = reverse('opportunities__create_related_opportunity_popup', args=(target.id,))
        self.assertGET200(url)

        salesphase = SalesPhase.objects.all()[0]
        name = 'Opportunity linked to {}'.format(target)
        response = self.client.post(url, data={'user':         user.pk,
                                               'name':         name,
                                               'sales_phase':  salesphase.id,
                                               'closing_date': '2011-03-12',
                                               'target':       self._genericfield_format_entity(target),
                                               'emitter':      emitter.id,
                                               'currency':     DEFAULT_CURRENCY_PK,
                                              }
                                   )
        self.assertNoFormError(response)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  constants.REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

    def test_add_to_orga03(self):
        "Try to add with wrong credentials (no link credentials)"
        self.login(is_superuser=False, allowed_apps=['opportunities'], creatable_models=[Opportunity])

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE | EntityCredentials.UNLINK,  # Not LINK
                                      set_type=SetCredentials.ESET_OWN
                                     )

        target = Organisation.objects.create(user=self.user, name='Target renegade')
        self.assertGET403(self._build_addrelated_url(target))

    @skipIfCustomContact
    def test_add_to_contact01(self):
        "Target is a Contact"
        user = self.login()

        target, emitter = self._create_target_n_emitter(contact=True)
        url = self._build_addrelated_url(target)
        self.assertGET200(url)

        salesphase = SalesPhase.objects.all()[0]
        name = 'Opportunity linked to {}'.format(target)
        response = self.client.post(url, follow=True,
                                    data={'user':         user.pk,
                                          'name':         name,
                                          'sales_phase':  salesphase.id,
                                          'closing_date': '2011-03-12',
                                          'target':       self._genericfield_format_entity(target),
                                          'emitter':      emitter.id,
                                          'currency':     DEFAULT_CURRENCY_PK,
                                         }
                                   )
        self.assertNoFormError(response)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  constants.REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

        response = self.client.post(url, follow=True,
                                    data={'user':         user.pk,
                                          'name':         'Opportunity 2 linked to {}'.format(target),
                                          'sales_phase':  salesphase.id,
                                          'closing_date': '2011-03-12',
                                          'target':       self._genericfield_format_entity(target),
                                          'emitter':      emitter.id,
                                          'currency':     DEFAULT_CURRENCY_PK,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    @skipIfCustomContact
    def test_add_to_contact02(self):
        "Popup version"
        user = self.login()

        target, emitter = self._create_target_n_emitter(contact=True)
        url = reverse('opportunities__create_related_opportunity_popup', args=(target.id,))
        self.assertGET200(url)

        salesphase = SalesPhase.objects.all()[0]
        name = 'Opportunity linked to {}'.format(target)
        response = self.client.post(url, data={'user':         user.pk,
                                               'name':         name,
                                               'sales_phase':  salesphase.id,
                                               'closing_date': '2011-03-12',
                                               'target':       self._genericfield_format_entity(target),
                                               'emitter':      emitter.id,
                                               'currency':     DEFAULT_CURRENCY_PK,
                                              }
                                   )
        self.assertNoFormError(response)

        opportunity = self.get_object_or_fail(Opportunity, name=name)
        self.assertEqual(salesphase, opportunity.sales_phase)

        self.assertRelationCount(1, target,  constants.REL_OBJ_TARGETS,   opportunity)
        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, target,  REL_SUB_PROSPECT,  emitter)

    @skipIfCustomContact
    def test_add_to_contact03(self):
        "User can not link to the Contact target"
        self.login(is_superuser=False, allowed_apps=['persons', 'opportunities'],
                   creatable_models=[Opportunity],
                  )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE | EntityCredentials.UNLINK, #no LINK
                                      set_type=SetCredentials.ESET_OWN
                                     )

        target = Contact.objects.create(user=self.user, first_name='Target', last_name='Renegade')
        self.assertGET403(self._build_addrelated_url(target))

    def test_add_to_something01(self):
        "Target is not a Contact/Organisation"
        user = self.login()

        target  = CremeEntity.objects.create(user=user)
        emitter = Organisation.objects.create(user=user, name='My society', is_managed=True)
        opportunity_count = Opportunity.objects.count()

        url = self._build_addrelated_url(target)
        self.assertGET200(url)  # TODO: is it normal ??

        response = self.client.post(url, data={'user':         user.pk,
                                               'name':         'Opp #1',
                                               'sales_phase':  SalesPhase.objects.all()[0].id,
                                               'closing_date': '2011-03-12',
                                               'target':       self._genericfield_format_entity(target),
                                               'emitter':      emitter.id,
                                              }
                                   )
        self.assertFormError(response, 'form', 'target', _(u'This content type is not allowed.'))
        self.assertEqual(opportunity_count, Opportunity.objects.count())  # No new opportunity was created

    @skipIfCustomOrganisation
    def test_editview01(self):
        user = self.login()

        name = 'opportunity01'
        opp, target, emitter = self._create_opportunity_n_organisations(name)
        url = opp.get_edit_absolute_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            target_f = response.context['form'].fields['target']

        self.assertEqual(target, target_f.initial)

        name = name.title()
        reference = '1256'
        phase = SalesPhase.objects.all()[1]
        currency = Currency.objects.create(name='Oolong', local_symbol='0', international_symbol='OOL')
        target_rel = self.get_object_or_fail(Relation, subject_entity=opp.id, object_entity=target.id)
        response = self.client.post(url, follow=True,
                                    data={'user':                  user.pk,
                                          'name':                  name,
                                          'reference':             reference,
                                          'sales_phase':           phase.id,
                                          'expected_closing_date': '2011-4-26',
                                          'closing_date':          '2011-5-15',
                                          'first_action_date':     '2011-5-1',
                                          'currency':              currency.id,
                                          'target':                self._genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)

        opp = self.refresh(opp)
        self.assertEqual(name,                             opp.name)
        self.assertEqual(reference,                        opp.reference)
        self.assertEqual(phase,                            opp.sales_phase)
        self.assertEqual(currency,                         opp.currency)
        self.assertEqual(date(year=2011, month=4, day=26), opp.expected_closing_date)
        self.assertEqual(date(year=2011, month=5, day=15), opp.closing_date)
        self.assertEqual(date(year=2011, month=5, day=1),  opp.first_action_date)

        self.assertEqual(target, opp.target)
        self.assertStillExists(target_rel)
        self.assertRelationCount(1, opp, constants.REL_SUB_TARGETS, target)

    @skipIfCustomOrganisation
    @skipIfCustomContact
    def test_editview02(self):
        user = self.login()

        name = 'opportunity01'
        opp, target1, emitter = self._create_opportunity_n_organisations(name)
        target2 = Contact.objects.create(user=user, first_name='Mike', last_name='Danton')

        target_rel = self.get_object_or_fail(Relation, subject_entity=opp.id,
                                             object_entity=target1.id,
                                            )
        response = self.client.post(opp.get_edit_absolute_url(), follow=True,
                                    data={'user':                  user.pk,
                                          'name':                  name,
                                          'reference':             '1256',
                                          'sales_phase':           opp.sales_phase_id,
                                          'expected_closing_date': '2013-4-26',
                                          'closing_date':          '2013-5-15',
                                          'first_action_date':     '2013-5-1',
                                          'currency':              opp.currency_id,
                                          'target':                self._genericfield_format_entity(target2),
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(target2, self.refresh(opp).target)
        self.assertDoesNotExist(target_rel)
        self.assertRelationCount(1, target2, REL_SUB_PROSPECT, emitter)

    @skipIfCustomOrganisation
    def test_listview(self):
        self.login()

        opp1 = self._create_opportunity_n_organisations('Opp1')[0]
        opp2 = self._create_opportunity_n_organisations('Opp2')[0]

        response = self.assertGET200(reverse('opportunities__list_opportunities'))

        with self.assertNoException():
            opps_page = response.context['entities']

        self.assertEqual(2, opps_page.paginator.count)
        self.assertEqual({opp1, opp2}, set(opps_page.object_list))

    @skipIfCustomOrganisation
    def test_delete01(self):
        "Cannot delete the target & the source"
        self.login()

        opp, target, emitter = self._create_opportunity_n_organisations('My Opp')
        target.trash()
        emitter.trash()

        self.assertPOST403(target.get_delete_absolute_url(), follow=True)
        self.assertStillExists(target)
        self.assertStillExists(opp)
        self.assertEqual(target, self.refresh(opp).target)

        self.assertPOST403(emitter.get_delete_absolute_url(), follow=True)
        self.assertStillExists(emitter)
        self.assertStillExists(opp)
        self.assertEqual(emitter, self.refresh(opp).emitter)

    @skipIfCustomOrganisation
    def test_delete02(self):
        "Can delete the Opportunity"
        self.login()

        opp, target, emitter = self._create_opportunity_n_organisations('My Opp')
        opp.trash()

        self.assertPOST200(opp.get_delete_absolute_url(), follow=True)
        self.assertDoesNotExist(opp)
        self.assertStillExists(target)
        self.assertStillExists(emitter)

    def test_clone(self):
        self.login()

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        cloned = opportunity.clone()

        self.assertEqual(opportunity.name,         cloned.name)
        self.assertEqual(opportunity.sales_phase,  cloned.sales_phase)
        self.assertEqual(opportunity.closing_date, cloned.closing_date)

        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, opportunity)
        self.assertRelationCount(1, emitter, constants.REL_SUB_EMIT_ORGA, cloned)

        self.assertRelationCount(1, target, constants.REL_OBJ_TARGETS, opportunity)
        self.assertRelationCount(1, target, constants.REL_OBJ_TARGETS, cloned)  # <== internal

    def _build_gendoc_url(self, opportunity, model=None):
        model = model or Quote
        return reverse('opportunities__generate_billing_doc',
                       args=(opportunity.id, ContentType.objects.get_for_model(model).id),
                      )

    @skipIfNotInstalled('creme.billing')
    @skipIfCustomOrganisation
    def test_generate_new_doc01(self):
        self.login()

        self.assertEqual(0, Quote.objects.count())

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        url = self._build_gendoc_url(opportunity)

        self.assertGET404(url)
        self.assertPOST200(url, follow=True)

        quotes = Quote.objects.all()
        self.assertEqual(1, len(quotes))

        quote = quotes[0]
        self.assertDatetimesAlmostEqual(date.today(), quote.issuing_date)
        self.assertEqual(1, quote.status_id)
        self.assertTrue(quote.number)

        name = quote.name
        self.assertIn(unicode(quote.number), name)
        self.assertIn(str(opportunity.name), name)

        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote, constants.REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote, constants.REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    @skipIfNotInstalled('creme.billing')
    @skipIfCustomOrganisation
    def test_generate_new_doc02(self):
        self.login()

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        url = self._build_gendoc_url(opportunity)

        self.client.post(url)
        quote1 = Quote.objects.all()[0]

        self.client.post(url)
        quotes = Quote.objects.exclude(pk=quote1.id)
        self.assertEqual(1, len(quotes))
        quote2 = quotes[0]

        self.assertRelationCount(1, quote2, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote2, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote2, constants.REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote2, constants.REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, quote1, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote1, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote1, constants.REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote1, constants.REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    @skipIfNotInstalled('creme.billing')
    @skipIfCustomOrganisation
    def test_generate_new_doc03(self):
        self.login()

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        url = self._build_gendoc_url(opportunity, Invoice)

        self.client.post(url)
        invoice1 = Invoice.objects.all()[0]

        self.client.post(url)
        invoices = Invoice.objects.exclude(pk=invoice1.id)
        self.assertEqual(1, len(invoices))

        invoices2 = invoices[0]
        self.assertRelationCount(1, invoices2, REL_SUB_BILL_ISSUED,    emitter)
        self.assertRelationCount(1, invoices2, REL_SUB_BILL_RECEIVED,  target)
        self.assertRelationCount(1, invoices2, constants.REL_SUB_LINKED_INVOICE, opportunity)

        self.assertRelationCount(1, invoice1, REL_SUB_BILL_ISSUED,    emitter)
        self.assertRelationCount(1, invoice1, REL_SUB_BILL_RECEIVED,  target)
        self.assertRelationCount(1, invoice1, constants.REL_SUB_LINKED_INVOICE, opportunity)

        self.assertRelationCount(1, target, REL_SUB_CUSTOMER_SUPPLIER, emitter)

    @skipIfNotInstalled('creme.billing')
    @skipIfCustomOrganisation
    def test_generate_new_doc_error01(self):
        "Invalid target type"
        self.login()

        contact_count = Contact.objects.count()

        opportunity = self._create_opportunity_n_organisations()[0]
        self.assertPOST404(self._build_gendoc_url(opportunity, Contact))
        self.assertEqual(contact_count, Contact.objects.count())  # No Contact created

    @skipIfNotInstalled('creme.billing')
    @skipIfCustomOrganisation
    def test_generate_new_doc_error02(self):
        "Credentials problems"
        self.login(is_superuser=False, allowed_apps=['billing', 'opportunities'],
                   creatable_models=[Opportunity],  # Not Quote
                  )

        opportunity = self._create_opportunity_n_organisations()[0]
        url = self._build_gendoc_url(opportunity)
        self.assertPOST403(url)

        role = self.role
        get_ct = ContentType.objects.get_for_model
        quote_ct = get_ct(Quote)
        role.creatable_ctypes.add(quote_ct)
        self.assertPOST403(url)

        create_sc = partial(SetCredentials.objects.create, role=role,
                            set_type=SetCredentials.ESET_ALL,
                           )
        create_sc(value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE)
        self.assertPOST403(url)

        create_sc(value=EntityCredentials.LINK, ctype=get_ct(Opportunity))
        self.assertPOST403(url)

        create_sc(value=EntityCredentials.LINK, ctype=quote_ct)
        self.assertPOST200(url, follow=True)

    def _build_currentquote_url(self, opportunity, quote, action='set_current'):
        return reverse('opportunities__linked_quote_is_current',
                       args=(opportunity.id, quote.id, action),
                      )

    @skipIfNotInstalled('creme.billing')
    @skipIfCustomOrganisation
    def test_current_quote_1(self):
        self.login()

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        gendoc_url = self._build_gendoc_url(opportunity)

        self.client.post(gendoc_url)
        quote1 = Quote.objects.all()[0]

        self.client.post(gendoc_url)
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]

        self.assertRelationCount(1, quote2, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote2, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote2, constants.REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote2, constants.REL_SUB_CURRENT_DOC,   opportunity)

        url = self._build_currentquote_url(opportunity, quote1)
        self.assertGET404(url)
        self.assertPOST200(url, follow=True)

        self.assertRelationCount(1, quote2, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote2, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote2, constants.REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote2, constants.REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, quote1, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote1, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote1, constants.REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote1, constants.REL_SUB_CURRENT_DOC,   opportunity)

    def _set_quote_config(self, use_current_quote):
        sv = SettingValue.objects.get(key_id=constants.SETTING_USE_CURRENT_QUOTE)
        sv.value = use_current_quote
        sv.save()

    @skipIfNotInstalled('creme.billing')
    @skipIfCustomOrganisation
    def test_current_quote_2(self):
        "Refresh the estimated_sales when we change which quote is the current"
        user = self.login()

        opportunity = self._create_opportunity_n_organisations()[0]
        url = self._build_gendoc_url(opportunity)

        opportunity.estimated_sales = Decimal('1000')
        opportunity.made_sales = Decimal('0')
        opportunity.save()

        create_sline = partial(ServiceLine.objects.create, user=user)
        self.client.post(url)
        quote1 = Quote.objects.all()[0]
        create_sline(related_document=quote1, on_the_fly_item='Stuff1', unit_price=Decimal("300"))

        self.client.post(url)
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]
        quote2.status = QuoteStatus.objects.create(name="WONStatus", order=15, won=True)
        quote2.save()

        create_sline(related_document=quote2, on_the_fly_item='Stuff1', unit_price=Decimal("500"))
        self.assertPOST200(self._build_currentquote_url(opportunity, quote1, action='unset_current'), follow=True)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote2, action='unset_current'), follow=True)

        self._set_quote_config(True)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote1), follow=True)
        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote1.total_no_vat)  # 300
        self.assertEqual(opportunity.made_sales, Decimal('0'))  # 300

        self.assertPOST200(self._build_currentquote_url(opportunity, quote1, action='unset_current'), follow=True)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote2), follow=True)
        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote2.total_no_vat)  # 500
        self.assertEqual(opportunity.made_sales, quote2.total_no_vat)  # 300

        self.assertPOST200(self._build_currentquote_url(opportunity, quote1), follow=True)
        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote1.total_no_vat + quote2.total_no_vat)  # 800
        self.assertEqual(opportunity.made_sales, quote2.total_no_vat)  # 300

    @skipIfNotInstalled('creme.billing')
    @skipIfCustomOrganisation
    def test_current_quote_3(self):
        user = self.login()

        opportunity = self._create_opportunity_n_organisations()[0]
        self._set_quote_config(False)

        estimated_sales = Decimal('69')
        opportunity.estimated_sales = estimated_sales
        opportunity.save()

        self.client.post(self._build_gendoc_url(opportunity))
        quote1 = Quote.objects.all()[0]
        ServiceLine.objects.create(user=user, related_document=quote1,
                                   on_the_fly_item='Foobar', unit_price=Decimal("300")
                                  )

        self.assertPOST200(self._build_currentquote_url(opportunity, quote1), follow=True)

        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, opportunity.get_total())  # 69
        self.assertEqual(opportunity.estimated_sales, estimated_sales)  # 69

    @skipIfNotInstalled('creme.billing')
    @skipIfCustomOrganisation
    def test_current_quote_4(self):
        user = self.login()
        self._set_quote_config(True)

        opportunity = self._create_opportunity_n_organisations()[0]
        self.client.post(self._build_gendoc_url(opportunity))

        quote = Quote.objects.all()[0]
        self.assertEqual(self.refresh(opportunity).estimated_sales, quote.total_no_vat)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote), follow=True)

        ServiceLine.objects.create(user=user, related_document=quote,
                                   on_the_fly_item='Stuff', unit_price=Decimal("300"),
                                  )
        self.assertEqual(300, self.refresh(quote).total_no_vat)
        self.assertEqual(300, self.refresh(opportunity).estimated_sales)

    @skipIfNotInstalled('creme.billing')
    @skipIfCustomOrganisation
    def test_current_quote_5(self):
        user = self.login()
        self._set_quote_config(True)

        opportunity = self._create_opportunity_n_organisations()[0]
        self.client.post(self._build_gendoc_url(opportunity))

        quote = Quote.objects.all()[0]
        self.assertEqual(self.refresh(opportunity).estimated_sales, quote.total_no_vat)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote), follow=True)

        self.assertEqual(0, self.refresh(quote).total_no_vat)
        self.assertEqual(0, self.refresh(opportunity).estimated_sales)

        ServiceLine.objects.create(user=user, related_document=quote,
                                   on_the_fly_item='Stuff', unit_price=Decimal("300"),
                                  )
        self.assertEqual(300, self.refresh(quote).total_no_vat)
        self.assertEqual(300, self.refresh(opportunity).estimated_sales)

        Relation.objects.filter(type__in=(constants.REL_SUB_CURRENT_DOC, constants.REL_OBJ_CURRENT_DOC)).delete()

        self.assertEqual(0, self.refresh(opportunity).estimated_sales)

    @skipIfNotInstalled('creme.billing')
    def test_current_quote_6(self):
        "Avoid queries when the billing instance has just been created"
        if quote_model_is_custom():
            return

        user = self.login()

        from django.db import DEFAULT_DB_ALIAS, connections
        from django.test.utils import CaptureQueriesContext

        context = CaptureQueriesContext(connections[DEFAULT_DB_ALIAS])

        status = QuoteStatus.objects.all()[0]

        with context:
            quote = Quote.objects.create(user=user,
                                         name='My Quote',
                                         status=status,
                                        )

        self.assertTrue(quote.pk)

        key_id = constants.SETTING_USE_CURRENT_QUOTE

        for query_info in context.captured_queries:
            self.assertNotIn(key_id, query_info['sql'])

    @skipIfCustomOrganisation
    def test_get_weighted_sales01(self):
        user = self.login()

        opportunity = self._create_opportunity_n_organisations()[0]
        funf = opportunity.function_fields.get('get_weighted_sales')
        self.assertIsNotNone(funf)

        self.assertIsNone(opportunity.estimated_sales)
        self.assertIsNone(opportunity.chance_to_win)
        self.assertEqual(0, opportunity.get_weighted_sales())
        self.assertEqual(number_format('0.0', use_l10n=True),
                         funf(opportunity, user).for_html()
                        )

        opportunity.estimated_sales = 1000
        opportunity.chance_to_win   =  10
        self.assertEqual(100, opportunity.get_weighted_sales())
        self.assertEqual(number_format('100.0', use_l10n=True),
                         funf(opportunity, user).for_html()
                        )

    @skipIfCustomOrganisation
    def test_get_weighted_sales02(self):
        "With field 'estimated_sales' hidden with FieldsConfig"
        self.login()

        FieldsConfig.create(Opportunity,
                            descriptions=[('estimated_sales', {FieldsConfig.HIDDEN: True})]
                           )

        opportunity = self._create_opportunity_n_organisations()[0]

        FieldsConfig.get_4_model(Opportunity)

        with self.assertNumQueries(0):
            w_sales = opportunity.get_weighted_sales()

        self.assertEqual(_(u'Error: «Estimated sales» is hidden'), w_sales)

    def test_delete_currency(self):
        user = self.login()

        currency = Currency.objects.create(name=u'Berry', local_symbol=u'B', international_symbol=u'BRY')

        create_orga = partial(Organisation.objects.create, user=user)
        opp = Opportunity.objects.create(user=user, name='Opp', currency=currency,
                                         sales_phase=SalesPhase.objects.all()[0],
                                         emitter=create_orga(name='My society'),
                                         target=create_orga(name='Target renegade'),
                                        )
        self.assertPOST404(reverse('creme_config__delete_instance', args=('creme_core', 'currency')),
                           data={'id': currency.pk}
                          )
        self.assertStillExists(currency)

        opp = self.get_object_or_fail(Opportunity, pk=opp.pk)
        self.assertEqual(currency, opp.currency)

    @skipIfCustomContact
    def test_csv_import01(self):
        user = self.login()

        count = Opportunity.objects.count()

        # Opportunity #1
        emitter1 = Organisation.objects.filter(is_managed=True)[0]
        target1  = Organisation.objects.create(user=user, name='Acme')
        sp1 = SalesPhase.objects.create(name='Testphase - test_csv_import01')

        max_order = SalesPhase.objects.aggregate(max_order=Max('order'))['max_order']

        # Opportunity #2
        target2_name = 'Black label society'
        sp2_name = 'IAmNotSupposedToAlreadyExist'
        self.assertFalse(SalesPhase.objects.filter(name=sp2_name))

        # Opportunity #3
        target3 = Contact.objects.create(user=user, first_name='Mike', last_name='Danton')

        # Opportunity #4
        target4_last_name = 'Renegade'

        # Opportunity #5
        sp5 = SalesPhase.objects.all()[1]

        lines = [('Opp01', sp1.name, '1000', '2000', target1.name, ''),
                 ('Opp02', sp2_name, '100',  '200',  target2_name, ''),
                 ('Opp03', sp1.name, '100',  '200',  '',           target3.last_name),
                 ('Opp04', sp1.name, '100',  '200',  '',           target4_last_name),
                 ('Opp05', '',       '100',  '200',  target1.name, ''),
                 # TODO emitter by name
                ]

        doc = self._build_csv_doc(lines)
        url = self._build_import_url(Opportunity)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'step':     0,
                                                           'document': doc.id,
                                                           # has_header
                                                          }
                                               )
                              )

        response = self.client.post(url, follow=True,
                                    data=dict(self.lvimport_data,
                                              document=doc.id,
                                              user=user.id,
                                              emitter=emitter1.id,

                                              name_colselect=1,
                                              estimated_sales_colselect=3,
                                              made_sales_colselect=4,

                                              sales_phase_colselect=2,
                                              sales_phase_subfield='name',
                                              sales_phase_create=True,
                                              sales_phase_defval=sp5.pk,

                                              target_persons_organisation_colselect=5,
                                              target_persons_organisation_create=True,
                                              target_persons_contact_colselect=6,
                                              target_persons_contact_create=True,
                                             )
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self._assertNoResultError(self._get_job_results(job))

        self.assertEqual(count + len(lines), Opportunity.objects.count())

        opp1 = self.get_object_or_fail(Opportunity, name='Opp01')
        self.assertEqual(user, opp1.user)
        self.assertEqual(1000, opp1.estimated_sales)
        self.assertEqual(2000, opp1.made_sales)
        self.assertEqual(1,    SalesPhase.objects.filter(name=sp1.name).count())
        self.assertEqual(sp1,  opp1.sales_phase)
        self.assertFalse(opp1.reference)
        self.assertIsNone(opp1.origin)
        self.assertEqual(emitter1, opp1.emitter)
        self.assertEqual(target1,  opp1.target)

        sp2 = self.get_object_or_fail(SalesPhase, name=sp2_name)
        self.assertEqual(max_order + 1, sp2.order)

        opp2 = self.get_object_or_fail(Opportunity, name='Opp02')
        self.assertEqual(user, opp2.user)
        self.assertEqual(100,  opp2.estimated_sales)
        self.assertEqual(200,  opp2.made_sales)
        self.assertEqual(sp2,  opp2.sales_phase)
        self.assertEqual(self.get_object_or_fail(Organisation, name=target2_name),
                         opp2.target
                        )

        opp3 = self.get_object_or_fail(Opportunity, name='Opp03')
        self.assertEqual(target3, opp3.target)

        opp4 = self.get_object_or_fail(Opportunity, name='Opp04')
        self.assertEqual(self.get_object_or_fail(Contact, last_name=target4_last_name),
                         opp4.target
                        )

        opp5 = self.get_object_or_fail(Opportunity, name='Opp05')
        self.assertEqual(sp5, opp5.sales_phase)

    def test_csv_import02(self):
        "SalesPhase creation forbidden by the user"
        user = self.login()

        count = Opportunity.objects.count()

        emitter = Organisation.objects.filter(is_managed=True)[0]
        target1 = Organisation.objects.create(user=user, name='Acme')

        sp1_name = 'IAmNotSupposedToAlreadyExist'
        self.assertFalse(SalesPhase.objects.filter(name=sp1_name))

        lines = [('Opp01', sp1_name, '1000', '2000', target1.name, '')]
        doc = self._build_csv_doc(lines)
        response = self.client.post(self._build_import_url(Opportunity),
                                    follow=True,
                                    data=dict(self.lvimport_data,
                                              document=doc.id,
                                              user=user.id,
                                              emitter=emitter.id,

                                              name_colselect=1,
                                              estimated_sales_colselect=3,
                                              made_sales_colselect=4,

                                              sales_phase_colselect=2,
                                              sales_phase_subfield='name',
                                              sales_phase_create='',  # <=======
                                              # sales_phase_defval=[...],  # <=======

                                              target_persons_organisation_colselect=5,
                                              target_persons_organisation_create=True,
                                              target_persons_contact_colselect=6,
                                              target_persons_contact_create=True,
                                             )
                                     )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        self.assertEqual(count, Opportunity.objects.count())
        self.assertFalse(SalesPhase.objects.filter(name=sp1_name).count())

        results = self._get_job_results(job)
        self.assertEqual(1, len(results))

        result = results[0]
        self.assertIsNone(result.entity)
        # 2 errors: retrieving of SalesPhase failed, creation of Opportunity failed
        self.assertEqual(2, len(result.messages))

        vname = _(u'Opportunity')
        self.assertEqual([_(u'No «{model}» has been created.').format(model=vname),
                          _(u'No «{model}» has been updated.').format(model=vname),
                          ungettext(u'{count} line in the file.',
                                    u'{count} lines in the file.',
                                    1
                                   ).format(count=1),
                         ],
                         job.stats
                        )

    def test_csv_import03(self):
        "SalesPhase is required"
        user = self.login()

        emitter = Organisation.objects.filter(is_managed=True)[0]
        target  = Organisation.objects.create(user=user, name='Acme')

        lines = [('Opp01', '1000', '2000', target.name)]
        doc = self._build_csv_doc(lines)
        response = self.assertPOST200(self._build_import_url(Opportunity),
                                      data=dict(self.lvimport_data,
                                                document=doc.id,
                                                user=user.id,
                                                emitter=emitter.id,

                                                name_colselect=1,
                                                estimated_sales_colselect=2,
                                                made_sales_colselect=3,

                                                sales_phase_colselect=0,  # <=======
                                                sales_phase_subfield='name',
                                                sales_phase_create='',
                                                # sales_phase_defval=[...],

                                                target_persons_organisation_colselect=4,
                                                target_persons_organisation_create='',
                                                target_persons_contact_colselect=0,
                                                target_persons_contact_create='',
                                               )
                                     )
        self.assertFormError(response, 'form', 'sales_phase',
                             _(u'This field is required.')
                            )

    def test_csv_import04(self):
        "Creation of Organisation/Contact is not wanted"
        user = self.login()

        count = Opportunity.objects.count()
        emitter = Organisation.objects.filter(is_managed=True)[0]

        orga_name = 'NERV'
        contact_name = 'Ikari'
        lines = [('Opp01', 'SP name', '1000', '2000', orga_name, ''),
                 ('Opp02', 'SP name', '1000', '2000', '',        contact_name),
                ]
        doc = self._build_csv_doc(lines)
        response = self.client.post(self._build_import_url(Opportunity),
                                    follow=True,
                                    data=dict(self.lvimport_data,
                                              document=doc.id,
                                              user=user.id,
                                              emitter=emitter.id,

                                              name_colselect=1,
                                              estimated_sales_colselect=3,
                                              made_sales_colselect=4,

                                              sales_phase_colselect=2,
                                              sales_phase_subfield='name',
                                              sales_phase_create=True,

                                              target_persons_organisation_colselect=5,
                                              target_persons_organisation_create='',  # <===
                                              target_persons_contact_colselect=6,
                                              target_persons_contact_create='',  # <===
                                             )
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)

        self.assertEqual(count, Opportunity.objects.count())
        self.assertFalse(Organisation.objects.filter(name=orga_name))
        self.assertFalse(Contact.objects.filter(last_name=contact_name))

        # TODO
        # errors = list(form.import_errors)
        # self.assertEqual(4, len(errors)) #4 errors: retrieving of Organisation/Contact failed, creation of Opportunities failed
        # self.assertIn(_('Organisation'), errors[0].message)
        # self.assertIn(_('Contact'),      errors[2].message)

        # self.assertEqual(0, form.imported_objects_count)

    @override_settings(MAX_JOBS_PER_USER=2)
    def test_csv_import05(self):
        "Creation credentials for Organisation & SalesPhase are forbidden."
        self.login(is_superuser=False,
                   allowed_apps=['persons', 'documents', 'opportunities'],
                   creatable_models=[Opportunity, get_document_model()],  # Not Organisation
                  )
        role = self.role
        SetCredentials.objects.create(role=role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_ALL,
                                     )
        # TODO: factorise
        emitter = Organisation.objects.filter(is_managed=True)[0]
        doc = self._build_csv_doc([('Opp01', '1000', '2000', 'Acme', 'New phase')])
        url = self._build_import_url(Opportunity)
        data = dict(self.lvimport_data,
                    document=doc.id,
                    user=self.user.id,
                    emitter=emitter.id,

                    name_colselect=1,
                    estimated_sales_colselect=2,
                    made_sales_colselect=3,

                    sales_phase_colselect=5,
                    sales_phase_subfield='name',
                    sales_phase_create=True,

                    target_persons_organisation_colselect=4,
                    # target_persons_organisation_create=True,
                    target_persons_contact_colselect=0,
                    target_persons_contact_create='',
                   )

        response = self.client.post(url, data=dict(data, target_persons_organisation_create=True))
        self.assertFormError(response, 'form', 'target',
                             _(u'You are not allowed to create: %(model)s') % {
                                    'model': _(u'Organisation'),
                                }
                            )
        self.assertFormError(response, 'form', 'sales_phase',
                             'You can not create instances'
                            )

        role.admin_4_apps = ['opportunities']
        role.save()
        response = self.client.post(url, follow=True, data=data)
        self.assertNoFormError(response)

        role.creatable_ctypes.add(ContentType.objects.get_for_model(Organisation))
        response = self.client.post(url, follow=True,
                                    data=dict(data, target_persons_organisation_create=True),
                                   )
        self.assertNoFormError(response)

    @skipIfCustomOrganisation
    def test_csv_import06(self):
        "Update"
        user = self.login()

        opp1, target1, emitter = self._create_opportunity_n_organisations()
        target2 = Organisation.objects.create(user=user, name='Acme')

        count = Opportunity.objects.count()

        phase1 = SalesPhase.objects.create(name='Testphase - test_csv_import06 #1')
        phase2 = SalesPhase.objects.create(name='Testphase - test_csv_import06 #2')

        opp1.sales_phase = phase1
        opp1.save()

        doc = self._build_csv_doc([(opp1.name, '1000', '2000', target2.name, phase1.name),  # Should be updated
                                   (opp1.name, '1000', '2000', target2.name, phase2.name),  # Phase is different => not updated
                                  ]
                                 )
        response = self.client.post(self._build_import_url(Opportunity),
                                    follow=True,
                                    data=dict(self.lvimport_data,
                                              document=doc.id,
                                              user=user.id,
                                              emitter=emitter.id,

                                              key_fields=['name', 'sales_phase'],

                                              name_colselect=1,
                                              estimated_sales_colselect=2,
                                              made_sales_colselect=3,

                                              sales_phase_colselect=5,
                                              sales_phase_subfield='name',

                                              target_persons_organisation_colselect=4,
                                              target_persons_organisation_create=True,
                                              target_persons_contact_colselect=0,
                                              target_persons_contact_create='',
                                             )
                                     )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(count + 1, Opportunity.objects.count())

        with self.assertNoException():
            opp2 = Opportunity.objects.exclude(id=opp1.id).get(name=opp1.name)

        self.assertEqual(target2, opp2.target)

        self._assertNoResultError(self._get_job_results(job))

        opp1 = self.refresh(opp1)
        self.assertEqual(target2, opp1.target)


class SalesPhaseTestCase(CremeTestCase):
    DELETE_URL = reverse('creme_config__delete_instance', args=('opportunities', 'sales_phase'))
    PORTAL_URL = reverse('creme_config__model_portal', args=('opportunities', 'sales_phase'))

    @classmethod
    def setUpClass(cls):
        super(SalesPhaseTestCase, cls).setUpClass()

        cls._phase_backup = list(SalesPhase.objects.all())
        SalesPhase.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        super(SalesPhaseTestCase, cls).tearDownClass()

        try:
            SalesPhase.objects.bulk_create(cls._phase_backup)
        except:
            print('SalesPhaseTestCase: test-data backup problem.')

    def test_create_n_order(self):
        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=2)
        sp2 = create_phase(name='Abandoned',   order=1)

        self.assertEqual([sp2, sp1], list(SalesPhase.objects.all()))

    def test_auto_order(self):
        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming')
        sp2 = create_phase(name='Abandoned')

        self.assertEqual(1, sp1.order)
        self.assertEqual(2, sp2.order)

    def test_creme_config_block(self):
        self.login()
        self.assertGET200(reverse('creme_config__app_portal', args=('opportunities',)))

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=2)
        sp2 = create_phase(name='Abandoned',   order=1)

        response = self.assertGET200(self.PORTAL_URL)

        sp1_index = response.content.index(sp1.name)
        self.assertNotEqual(-1, sp1_index)

        sp2_index = response.content.index(sp2.name)
        self.assertNotEqual(-1, sp2_index)

        self.assertLess(sp2_index, sp1_index)  # order_by('order')

    def test_creme_config_block_reordering(self):
        self.login()

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=2)
        sp2 = create_phase(name='Abandoned',   order=1)
        sp3 = create_phase(name='Won',         order=1)  # 2 x '1' !!
        sp4 = create_phase(name='Lost',        order=3)

        self.assertGET200(self.PORTAL_URL)

        refresh = self.refresh
        self.assertEqual(3, refresh(sp1).order)
        self.assertEqual(1, refresh(sp2).order)
        self.assertEqual(2, refresh(sp3).order)
        self.assertEqual(4, refresh(sp4).order)

    def test_delete01(self):
        self.login()

        sp = SalesPhase.objects.create(name='Forthcoming', order=1)
        self.assertPOST200(self.DELETE_URL, data={'id': sp.pk})
        self.assertDoesNotExist(sp)

    @skipIfCustomOpportunity
    def test_delete02(self):
        user = self.login()

        sp = SalesPhase.objects.create(name='Forthcoming', order=1)

        create_orga = Organisation.objects.create
        opp = Opportunity.objects.create(user=user, name='Opp', sales_phase=sp,
                                         emitter=create_orga(user=user, name='My society'),
                                         target=create_orga(user=user,  name='Target renegade'),
                                        )
        self.assertPOST404(self.DELETE_URL, data={'id': sp.pk})
        self.assertStillExists(sp)

        opp = self.get_object_or_fail(Opportunity, pk=opp.pk)
        self.assertEqual(sp, opp.sales_phase)

    def test_full_clean(self):
        sp = SalesPhase(name='Forthcoming', won=True, lost=True)

        with self.assertRaises(ValidationError):
            sp.full_clean()


class OriginTestCase(CremeTestCase):
    def setUp(self):
        self.login()

    # def test_config(self):
    #     create_origin = Origin.objects.create
    #     origin1 = create_origin(name='Web site')
    #     origin2 = create_origin(name='Mouth')
    #
    #     response = self.assertGET200(reverse('creme_config__model_portal', args=('opportunities', 'origin')))
    #     self.assertContains(response, origin1.name)
    #     self.assertContains(response, origin2.name)
    #
    #     self.assertPOST404(reverse('creme_config__move_instance_down', args=('opportunities', 'origin', origin1.id)))

    @skipIfCustomOpportunity
    def test_delete(self):
        "Set to null"
        origin = Origin.objects.create(name='Web site')

        user = self.user
        create_orga = partial(Organisation.objects.create, user=user)
        opp = Opportunity.objects.create(user=user, name='Opp', origin=origin,
                                         sales_phase=SalesPhase.objects.create(name='Forthcoming', order=1),
                                         emitter=create_orga(name='My society'),
                                         target=create_orga(name='Target renegade'),
                                        )

        self.assertPOST200(reverse('creme_config__delete_instance', args=('opportunities', 'origin')),
                           data={'id': origin.pk}
                          )
        self.assertDoesNotExist(origin)

        opp = self.get_object_or_fail(Opportunity, pk=opp.pk)
        self.assertIsNone(opp.origin)
