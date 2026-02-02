from functools import partial

from creme.billing.models import NumberGeneratorItem
from creme.persons.tests.base import skipIfCustomOrganisation

from .base import Organisation, _BillingTestCase

# TODO: complete


@skipIfCustomOrganisation
class HandleMergeOrganisationsTestCase(_BillingTestCase):
    def _merge_organisations(self, orga1, orga2, swapped=False):
        self.assertNoFormError(self.client.post(
            self.build_merge_url(orga1, orga2),
            follow=True,
            data={
                'user_1':      orga1.user_id,
                'user_2':      orga2.user_id,
                'user_merged': orga1.user_id,

                'name_1':      orga1.name,
                'name_2':      orga2.name,
                'name_merged': orga1.name,
            },
        ))
        if swapped:
            self.assertStillExists(orga2)
            self.assertDoesNotExist(orga1)
        else:
            self.assertStillExists(orga1)
            self.assertDoesNotExist(orga2)

    def test_first_is_managed(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = self._set_managed(create_orga(name='NERV'))
        orga2 = create_orga(name='Nerv')

        generators1 = NumberGeneratorItem.objects.filter(organisation=orga1)
        self.assertEqual(4, len(generators1))
        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=orga2))

        self._merge_organisations(orga1, orga2)

        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=orga2))
        self.maxDiff = None
        self.assertCountEqual(
            generators1, NumberGeneratorItem.objects.filter(organisation=orga1),
        )

    def test_second_is_managed(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='NERV')
        orga2 = self._set_managed(create_orga(name='Nerv'))

        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=orga1))
        generators2 = NumberGeneratorItem.objects.filter(organisation=orga2)
        self.assertEqual(4, len(generators2))

        self._merge_organisations(orga1, orga2, swapped=True)

        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=orga1))
        self.maxDiff = None
        self.assertCountEqual(
            generators2, NumberGeneratorItem.objects.filter(organisation=orga2),
        )

    def test_two_managed(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = self._set_managed(create_orga(name='NERV'))
        orga2 = self._set_managed(create_orga(name='Nerv'))

        generators1 = NumberGeneratorItem.objects.filter(organisation=orga1)
        self.assertEqual(4, len(generators1))

        generators2 = NumberGeneratorItem.objects.filter(organisation=orga2)
        self.assertEqual(4, len(generators2))

        self._merge_organisations(orga1, orga2)

        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=orga2))
        self.maxDiff = None
        self.assertCountEqual(
            generators1, NumberGeneratorItem.objects.filter(organisation=orga1),
        )
