# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    # from django.urls import reverse

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.views.base import BrickTestCaseMixin
    from creme.creme_core.models import (RelationType, Vat,
            SettingValue, BrickDetailviewLocation)

    from creme.persons.tests.base import skipIfCustomOrganisation

    from .. import bricks, constants
    from ..models import (InvoiceStatus, SalesOrderStatus, CreditNoteStatus,
            ConfigBillingAlgo, SimpleBillingAlgo)
    from .base import (_BillingTestCase,
            Organisation, Contact, Product, Service,
            CreditNote, Invoice, Quote, SalesOrder, TemplateBase,
            ProductLine, ServiceLine)
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class AppTestCase(_BillingTestCase, CremeTestCase, BrickTestCaseMixin):
    def test_populate(self):
        billing_classes = [Invoice, Quote, SalesOrder,
                           CreditNote, TemplateBase,
                          ]
        lines_clases = [ProductLine, ServiceLine]

        self.get_relationtype_or_fail(constants.REL_SUB_BILL_ISSUED,       billing_classes, [Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_BILL_RECEIVED,     billing_classes, [Organisation, Contact])
        self.get_relationtype_or_fail(constants.REL_SUB_HAS_LINE,          billing_classes, lines_clases)
        self.get_relationtype_or_fail(constants.REL_SUB_LINE_RELATED_ITEM, lines_clases,    [Product, Service])

        self.assertEqual(1, SalesOrderStatus.objects.filter(pk=1).count())
        self.assertEqual(2, InvoiceStatus.objects.filter(pk__in=(1, 2)).count())
        self.assertEqual(1, CreditNoteStatus.objects.filter(pk=1).count())

        self.assertTrue(Vat.objects.exists())  # In creme_core populate...

        # Contribution to activities
        from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

        rtype = self.get_object_or_fail(RelationType, pk=REL_SUB_ACTIVITY_SUBJECT)
        get_ct = ContentType.objects.get_for_model
        ct_ids = [get_ct(m).id for m in (Invoice, Quote, SalesOrder)]
        self.assertEqual(len(ct_ids), rtype.subject_ctypes.filter(id__in=ct_ids).count())
        self.assertTrue(rtype.subject_ctypes.filter(id=get_ct(Contact).id).exists())
        self.assertEqual(len(ct_ids), rtype.symmetric_type.object_ctypes.filter(id__in=ct_ids).count())

    # def test_portal(self):
    #     self.login()
    #     self.assertGET200(reverse('billing__portal'))

    @skipIfCustomOrganisation
    def test_algoconfig(self):
        user = self.login()
        orga = Organisation.objects.create(user=user, name='NERV')

        self.assertFalse(ConfigBillingAlgo.objects.filter(organisation=orga))
        self.assertFalse(SimpleBillingAlgo.objects.filter(organisation=orga))

        self._set_managed(orga)

        algoconfs = ConfigBillingAlgo.objects.filter(organisation=orga)
        self.assertEqual(['SIMPLE_ALGO'] * 3, [algoconf.name_algo for algoconf in algoconfs])
        self.assertEqual({Quote, Invoice, SalesOrder},
                         {algoconf.ct.model_class() for algoconf in algoconfs}
                        )

        simpleconfs = SimpleBillingAlgo.objects.filter(organisation=orga)
        self.assertEqual([0] * 3, [simpleconf.last_number for simpleconf in simpleconfs])
        self.assertEqual({Quote, Invoice, SalesOrder},
                         {simpleconf.ct.model_class() for simpleconf in simpleconfs}
                        )

    def _merge_organisations(self, orga1, orga2):
        user = self.user
        response = self.client.post(self.build_merge_url(orga1, orga2), follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'name_1':      orga1.name,
                                          'name_2':      orga2.name,
                                          'name_merged': orga1.name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertStillExists(orga1)
        self.assertDoesNotExist(orga2)

    def _ids_list(self, queryset, length):
        ids_list = list(queryset.values_list('id', flat=True))
        self.assertEqual(length, len(ids_list))

        return ids_list

    @skipIfCustomOrganisation
    def test_merge_algoconfig01(self):
        "One managed organisation"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='NERV'); self._set_managed(orga1)
        orga2 = create_orga(name='Nerv')

        cba_filter = ConfigBillingAlgo.objects.filter
        sba_filter = SimpleBillingAlgo.objects.filter
        self.assertFalse(cba_filter(organisation=orga2))
        self.assertFalse(sba_filter(organisation=orga2))

        cba_ids_list1 = self._ids_list(cba_filter(organisation=orga1), 3)
        sba_ids_list1 = self._ids_list(sba_filter(organisation=orga1), 3)

        self._merge_organisations(orga1, orga2)

        cba_list1 = list(cba_filter(pk__in=cba_ids_list1))
        self.assertEqual(3, len(cba_list1))
        self.assertEqual(orga1, cba_list1[0].organisation)

        sba_list1 = list(sba_filter(pk__in=sba_ids_list1))
        self.assertEqual(3, len(sba_list1))
        self.assertEqual(orga1, sba_list1[0].organisation)

    @skipIfCustomOrganisation
    def test_merge_algoconfig02(self):
        "Two managed organisations"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='NERV'); self._set_managed(orga1)
        orga2 = create_orga(name='Nerv'); self._set_managed(orga2)

        cba_filter = ConfigBillingAlgo.objects.filter
        sba_filter = SimpleBillingAlgo.objects.filter
        cba_ids_list1 = self._ids_list(cba_filter(organisation=orga1), 3)
        sba_ids_list1 = self._ids_list(sba_filter(organisation=orga1), 3)

        cba_ids_list2 = self._ids_list(cba_filter(organisation=orga2), 3)
        sba_ids_list2 = self._ids_list(sba_filter(organisation=orga2), 3)

        self._merge_organisations(orga1, orga2)

        self.assertFalse(cba_filter(pk__in=cba_ids_list2))
        self.assertEqual(3, cba_filter(pk__in=cba_ids_list1).count())

        self.assertFalse(sba_filter(pk__in=sba_ids_list2))
        self.assertEqual(3, sba_filter(pk__in=sba_ids_list1).count())

    @skipIfCustomOrganisation
    def test_merge_algoconfig03(self):
        "Two organisations with algo config, but not managed (anymore)"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='NERV'); self._set_managed(orga1)
        orga2 = create_orga(name='Nerv'); self._set_managed(orga2)

        self._set_managed(orga1, False)
        self._set_managed(orga2, False)

        cba_filter = ConfigBillingAlgo.objects.filter
        sba_filter = SimpleBillingAlgo.objects.filter
        cba_ids_list1 = self._ids_list(cba_filter(organisation=orga1), 3)
        sba_ids_list1 = self._ids_list(sba_filter(organisation=orga1), 3)

        cba_ids_list2 = self._ids_list(cba_filter(organisation=orga2), 3)
        sba_ids_list2 = self._ids_list(sba_filter(organisation=orga2), 3)

        self._merge_organisations(orga1, orga2)

        self.assertFalse(cba_filter(pk__in=cba_ids_list2))
        self.assertEqual(3, cba_filter(pk__in=cba_ids_list1).count())

        self.assertFalse(sba_filter(pk__in=sba_ids_list2))
        self.assertEqual(3, sba_filter(pk__in=sba_ids_list1).count())

    @skipIfCustomOrganisation
    def test_merge_algoconfig04(self):
        """Two organisations with algo config, but only one is still managed
            => we delete the config of the other one.
        """
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='NERV'); self._set_managed(orga1)
        orga2 = create_orga(name='Nerv'); self._set_managed(orga2)

        self._set_managed(orga2, False)

        cba_filter = ConfigBillingAlgo.objects.filter
        sba_filter = SimpleBillingAlgo.objects.filter
        cba_ids_list1 = self._ids_list(cba_filter(organisation=orga1), 3)
        sba_ids_list1 = self._ids_list(sba_filter(organisation=orga1), 3)

        cba_ids_list2 = self._ids_list(cba_filter(organisation=orga2), 3)
        sba_ids_list2 = self._ids_list(sba_filter(organisation=orga2), 3)

        self._merge_organisations(orga1, orga2)

        self.assertEqual(3, cba_filter(pk__in=cba_ids_list1).count())
        self.assertFalse(cba_filter(pk__in=cba_ids_list2))

        self.assertEqual(3, sba_filter(pk__in=sba_ids_list1).count())
        self.assertFalse(sba_filter(pk__in=sba_ids_list2))

    @skipIfCustomOrganisation
    def test_merge_algoconfig05(self):
        "Second organisation has algo config (none is managed anymore)"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='NERV')
        orga2 = create_orga(name='Nerv'); self._set_managed(orga2)

        self._set_managed(orga2, False)

        cba_filter = ConfigBillingAlgo.objects.filter
        sba_filter = SimpleBillingAlgo.objects.filter
        self.assertFalse(cba_filter(organisation=orga1))
        self.assertFalse(sba_filter(organisation=orga1))

        cba_ids_list2 = self._ids_list(cba_filter(organisation=orga2), 3)
        sba_ids_list2 = self._ids_list(sba_filter(organisation=orga2), 3)

        self._merge_organisations(orga1, orga2)

        cba_list1 = list(cba_filter(pk__in=cba_ids_list2))
        self.assertEqual(3, len(cba_list1))
        self.assertEqual(orga1, cba_list1[0].organisation)

        sba_list1 = list(sba_filter(pk__in=sba_ids_list2))
        self.assertEqual(3, len(sba_list1))
        self.assertEqual(orga1, sba_list1[0].organisation)

    def _get_setting_value(self):
        return self.get_object_or_fail(SettingValue, key_id=constants.DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA)

    @skipIfCustomOrganisation
    def test_brick_orga01(self):
        self.login()

        sv = self._get_setting_value()
        self.assertIs(True, sv.value)

        orga = Organisation.objects.create(user=self.user, name='NERV')

        response = self.assertGET200(orga.get_absolute_url())
        payment_info_tlpt = 'billing/bricks/orga-payment-information.html'
        self.assertTemplateNotUsed(response, payment_info_tlpt)
        self.assertTemplateUsed(response, 'billing/bricks/received-invoices.html')
        self.assertTemplateUsed(response, 'billing/bricks/received-billing-documents.html')

        sv.value = False
        sv.save()

        response = self.assertGET200(orga.get_absolute_url())
        self.assertTemplateUsed(response, payment_info_tlpt)

    @skipIfCustomOrganisation
    def test_brick_orga02(self):
        "Managed organisation"
        self.login()

        orga = Organisation.objects.create(user=self.user, name='NERV')
        self._set_managed(orga)

        response = self.assertGET200(orga.get_absolute_url())
        payment_info_tlpt = 'billing/bricks/orga-payment-information.html'
        self.assertTemplateUsed(response, payment_info_tlpt)
        self.assertTemplateUsed(response, 'billing/bricks/received-invoices.html')
        self.assertTemplateUsed(response, 'billing/bricks/received-billing-documents.html')

        sv = self._get_setting_value()
        sv.value = False
        sv.save()

        response = self.assertGET200(orga.get_absolute_url())
        self.assertTemplateUsed(response, payment_info_tlpt)

    @skipIfCustomOrganisation
    def test_brick_orga03(self):
        "Statistics"
        self.login()

        orga = Organisation.objects.create(user=self.user, name='NERV')
        brick_id = bricks.PersonsStatisticsBrick.id_

        BrickDetailviewLocation.create_if_needed(brick_id=brick_id, order=1000,
                                                 zone=BrickDetailviewLocation.LEFT,
                                                 model=Organisation,
                                                )

        response = self.assertGET200(orga.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/bricks/persons-statistics.html')

        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, brick_id)
