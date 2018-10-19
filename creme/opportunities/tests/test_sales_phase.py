# -*- coding: utf-8 -*-

try:
    from django.core.exceptions import ValidationError
    from django.urls import reverse

    from creme.creme_core.tests.base import CremeTestCase

    from creme.opportunities.models import SalesPhase

    from .base import Opportunity, skipIfCustomOpportunity, Organisation
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class SalesPhaseTestCase(CremeTestCase):
    DELETE_URL = reverse('creme_config__delete_instance', args=('opportunities', 'sales_phase'))
    PORTAL_URL = reverse('creme_config__model_portal', args=('opportunities', 'sales_phase'))

    @classmethod
    def setUpClass(cls):
        # super(SalesPhaseTestCase, cls).setUpClass()
        super().setUpClass()

        cls._phase_backup = list(SalesPhase.objects.all())
        SalesPhase.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        # super(SalesPhaseTestCase, cls).tearDownClass()
        super().tearDownClass()

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

    def test_creme_config_brick(self):
        self.login()
        self.assertGET200(reverse('creme_config__app_portal', args=('opportunities',)))

        create_phase = SalesPhase.objects.create
        sp1 = create_phase(name='Forthcoming', order=2)
        sp2 = create_phase(name='Abandoned',   order=1)

        response = self.assertGET200(self.PORTAL_URL)
        content = response.content.decode()

        # sp1_index = response.content.index(sp1.name)
        sp1_index = content.index(sp1.name)
        self.assertNotEqual(-1, sp1_index)

        # sp2_index = response.content.index(sp2.name)
        sp2_index = content.index(sp2.name)
        self.assertNotEqual(-1, sp2_index)

        self.assertLess(sp2_index, sp1_index)  # order_by('order')

    def test_creme_config_brick_reordering(self):
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