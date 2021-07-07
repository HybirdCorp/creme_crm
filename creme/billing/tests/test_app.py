# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.contenttypes.models import ContentType

from creme.creme_core.models import (
    BrickDetailviewLocation,
    RelationType,
    SettingValue,
    Vat,
)
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import skipIfCustomOrganisation

from .. import bricks, constants, setting_keys
from ..algos import SimpleAlgo
from ..models import (
    ConfigBillingAlgo,
    CreditNoteStatus,
    InvoiceStatus,
    SalesOrderStatus,
    SimpleBillingAlgo,
)
from ..registry import AlgoRegistry
from .base import (
    Contact,
    CreditNote,
    Invoice,
    Organisation,
    Product,
    ProductLine,
    Quote,
    SalesOrder,
    Service,
    ServiceLine,
    TemplateBase,
    _BillingTestCase,
)


class AppTestCase(BrickTestCaseMixin, _BillingTestCase):
    def test_populate(self):
        billing_classes = [
            Invoice, Quote, SalesOrder, CreditNote, TemplateBase,
        ]
        lines_classes = [ProductLine, ServiceLine]

        self.get_relationtype_or_fail(
            constants.REL_SUB_BILL_ISSUED, billing_classes, [Organisation],
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_BILL_RECEIVED, billing_classes, [Organisation, Contact],
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_HAS_LINE, billing_classes, lines_classes,
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_LINE_RELATED_ITEM, lines_classes, [Product, Service],
        )

        self.assertEqual(1, SalesOrderStatus.objects.filter(pk=1).count())
        self.assertEqual(2, InvoiceStatus.objects.filter(pk__in=(1, 2)).count())
        self.assertEqual(1, CreditNoteStatus.objects.filter(pk=1).count())

        self.assertTrue(Vat.objects.exists())  # In creme_core populate...

        sv = self.get_object_or_fail(
            SettingValue, key_id=setting_keys.button_redirection_key.id,
        )
        self.assertIs(True, sv.value)

    @skipIfNotInstalled('creme.activities')
    def test_populate_activities(self):
        # Contribution to activities
        from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

        rtype = self.get_object_or_fail(RelationType, pk=REL_SUB_ACTIVITY_SUBJECT)
        get_ct = ContentType.objects.get_for_model
        ct_ids = [get_ct(m).id for m in (Invoice, Quote, SalesOrder)]
        self.assertEqual(len(ct_ids), rtype.subject_ctypes.filter(id__in=ct_ids).count())
        self.assertTrue(rtype.subject_ctypes.filter(id=get_ct(Contact).id).exists())

    def test_registry(self):
        registry = AlgoRegistry()
        registry.register((SimpleBillingAlgo.ALGO_NAME, SimpleAlgo))

        self.assertEqual(SimpleAlgo, registry.get_algo(SimpleBillingAlgo.ALGO_NAME))
        self.assertIsNone(registry.get_algo('billing-unknown'))

        self.assertListEqual(
            [(SimpleBillingAlgo.ALGO_NAME, SimpleAlgo)], [*registry]
        )
        self.assertListEqual([SimpleAlgo], [*registry.algorithms])

        # ---
        with self.assertRaises(registry.RegistrationError):
            registry.register((SimpleBillingAlgo.ALGO_NAME, SimpleAlgo))

    @skipIfCustomOrganisation
    def test_algoconfig(self):
        user = self.create_user()
        orga = Organisation.objects.create(user=user, name='NERV')

        self.assertFalse(ConfigBillingAlgo.objects.filter(organisation=orga))
        self.assertFalse(SimpleBillingAlgo.objects.filter(organisation=orga))

        self._set_managed(orga)

        algoconfs = ConfigBillingAlgo.objects.filter(organisation=orga)
        self.assertListEqual(
            ['SIMPLE_ALGO'] * 3,
            [algoconf.name_algo for algoconf in algoconfs],
        )
        self.assertSetEqual(
            {Quote, Invoice, SalesOrder},
            {algoconf.ct.model_class() for algoconf in algoconfs}
        )

        simpleconfs = SimpleBillingAlgo.objects.filter(organisation=orga)
        self.assertListEqual(
            [0] * 3,
            [simpleconf.last_number for simpleconf in simpleconfs]
        )
        self.assertSetEqual(
            {Quote, Invoice, SalesOrder},
            {simpleconf.ct.model_class() for simpleconf in simpleconfs}
        )

    def _merge_organisations(self, orga1, orga2):
        user = self.user
        response = self.client.post(
            self.build_merge_url(orga1, orga2), follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'name_1':      orga1.name,
                'name_2':      orga2.name,
                'name_merged': orga1.name,
            },
        )
        self.assertNoFormError(response)
        self.assertStillExists(orga1)
        self.assertDoesNotExist(orga2)

    def _ids_list(self, queryset, length):
        ids_list = [*queryset.values_list('id', flat=True)]
        self.assertEqual(length, len(ids_list))

        return ids_list

    @skipIfCustomOrganisation
    def test_merge_algoconfig01(self):
        "One managed organisation."
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = self._set_managed(create_orga(name='NERV'))
        orga2 = create_orga(name='Nerv')

        cba_filter = ConfigBillingAlgo.objects.filter
        sba_filter = SimpleBillingAlgo.objects.filter
        self.assertFalse(cba_filter(organisation=orga2))
        self.assertFalse(sba_filter(organisation=orga2))

        cba_ids_list1 = self._ids_list(cba_filter(organisation=orga1), 3)
        sba_ids_list1 = self._ids_list(sba_filter(organisation=orga1), 3)

        self._merge_organisations(orga1, orga2)

        cba_list1 = [*cba_filter(pk__in=cba_ids_list1)]
        self.assertEqual(3, len(cba_list1))
        self.assertEqual(orga1, cba_list1[0].organisation)

        sba_list1 = [*sba_filter(pk__in=sba_ids_list1)]
        self.assertEqual(3, len(sba_list1))
        self.assertEqual(orga1, sba_list1[0].organisation)

    @skipIfCustomOrganisation
    def test_merge_algoconfig02(self):
        "Two managed organisations."
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = self._set_managed(create_orga(name='NERV'))
        orga2 = self._set_managed(create_orga(name='Nerv'))

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
        "Two organisations with algo config, but not managed (anymore)."
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = self._set_managed(create_orga(name='NERV'))
        orga2 = self._set_managed(create_orga(name='Nerv'))

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
        orga1 = self._set_managed(create_orga(name='NERV'))
        orga2 = self._set_managed(create_orga(name='Nerv'))

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
        "Second organisation has algo config (none is managed anymore)."
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='NERV')
        orga2 = self._set_managed(create_orga(name='Nerv'))

        self._set_managed(orga2, False)

        cba_filter = ConfigBillingAlgo.objects.filter
        sba_filter = SimpleBillingAlgo.objects.filter
        self.assertFalse(cba_filter(organisation=orga1))
        self.assertFalse(sba_filter(organisation=orga1))

        cba_ids_list2 = self._ids_list(cba_filter(organisation=orga2), 3)
        sba_ids_list2 = self._ids_list(sba_filter(organisation=orga2), 3)

        self._merge_organisations(orga1, orga2)

        cba_list1 = [*cba_filter(pk__in=cba_ids_list2)]
        self.assertEqual(3, len(cba_list1))
        self.assertEqual(orga1, cba_list1[0].organisation)

        sba_list1 = [*sba_filter(pk__in=sba_ids_list2)]
        self.assertEqual(3, len(sba_list1))
        self.assertEqual(orga1, sba_list1[0].organisation)

    @skipIfCustomOrganisation
    def test_brick_orga01(self):
        self.login()

        sv = self.get_object_or_fail(SettingValue, key_id=setting_keys.payment_info_key.id)
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
        "Managed organisation."
        self.login()

        orga = self._set_managed(
            Organisation.objects.create(user=self.user, name='NERV')
        )

        response = self.assertGET200(orga.get_absolute_url())
        payment_info_tlpt = 'billing/bricks/orga-payment-information.html'
        self.assertTemplateUsed(response, payment_info_tlpt)
        self.assertTemplateUsed(response, 'billing/bricks/received-invoices.html')
        self.assertTemplateUsed(response, 'billing/bricks/received-billing-documents.html')

        sv = self.get_object_or_fail(SettingValue, key_id=setting_keys.payment_info_key.id)
        sv.value = False
        sv.save()

        response = self.assertGET200(orga.get_absolute_url())
        self.assertTemplateUsed(response, payment_info_tlpt)

    @skipIfCustomOrganisation
    def test_brick_orga03(self):
        "Statistics."
        self.login()

        orga = Organisation.objects.create(user=self.user, name='NERV')
        brick_id = bricks.PersonsStatisticsBrick.id_

        BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_id, order=1000,
            zone=BrickDetailviewLocation.LEFT,
            model=Organisation,
        )

        response = self.assertGET200(orga.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/bricks/persons-statistics.html')

        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, brick_id)
