from functools import partial

from django.urls import reverse

from creme.creme_core.tests.base import CremeTestCase
from creme.opportunities.models import Origin, SalesPhase

from .base import Opportunity, Organisation, skipIfCustomOpportunity


class OriginTestCase(CremeTestCase):
    @skipIfCustomOpportunity
    def test_delete01(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        origin = Origin.objects.create(name='Web site')

        create_orga = partial(Organisation.objects.create, user=user)
        opp = Opportunity.objects.create(
            user=user, name='Opp', origin=origin,
            sales_phase=SalesPhase.objects.create(name='Forthcoming', order=1),
            emitter=create_orga(name='My society'),
            target=create_orga(name='Target renegade'),
        )

        self.assertNoFormError(self.client.post(reverse(
            'creme_config__delete_instance',
            args=('opportunities', 'origin', origin.id),
        )))

        job = self.get_deletion_command_or_fail(Origin).job
        job.type.execute(job)
        self.assertDoesNotExist(origin)

        opp = self.assertStillExists(opp)
        self.assertIsNone(opp.origin)

    @skipIfCustomOpportunity
    def test_delete02(self):
        "Set to another value."
        user = self.login_as_root_and_get()

        origin1 = Origin.objects.create(name='Web site')
        origin2 = Origin.objects.exclude(id=origin1.id)[0]

        create_orga = partial(Organisation.objects.create, user=user)
        opp = Opportunity.objects.create(
            user=user, name='Opp', origin=origin1,
            sales_phase=SalesPhase.objects.create(name='Forthcoming', order=1),
            emitter=create_orga(name='My society'),
            target=create_orga(name='Target renegade'),
        )

        self.assertNoFormError(self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('opportunities', 'origin', origin1.id)
            ),
            data={'replace_opportunities__opportunity_origin': origin2.id},
        ))

        job = self.get_deletion_command_or_fail(Origin).job
        job.type.execute(job)
        self.assertDoesNotExist(origin1)

        opp = self.assertStillExists(opp)
        self.assertEqual(origin2, opp.origin)
