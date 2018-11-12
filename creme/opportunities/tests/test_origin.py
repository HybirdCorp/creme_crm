# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.urls import reverse

    from creme.creme_core.tests.base import CremeTestCase

    from creme.opportunities.models import Origin, SalesPhase

    from .base import Opportunity, skipIfCustomOpportunity, Organisation
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


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
        opp = Opportunity.objects.create(
            user=user, name='Opp', origin=origin,
            sales_phase=SalesPhase.objects.create(name='Forthcoming', order=1),
            emitter=create_orga(name='My society'),
            target=create_orga(name='Target renegade'),
        )

        self.assertPOST200(reverse('creme_config__delete_instance',
                                   args=('opportunities', 'origin'),
                                  ),
                           data={'id': origin.pk},
                          )
        self.assertDoesNotExist(origin)

        opp = self.get_object_or_fail(Opportunity, pk=opp.pk)
        self.assertIsNone(opp.origin)
