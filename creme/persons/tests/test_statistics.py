from functools import partial

from django.utils.translation import gettext as _

from creme.creme_core.models import Relation
from creme.creme_core.tests.base import CremeTestCase

from .. import constants, statistics
from .base import Contact, Organisation


class PersonsStatisticsTestCase(CremeTestCase):
    def _aux_test(self, cls, rtype_id):
        user = self.login_as_root_and_get()

        stat = cls(Organisation)
        self.assertListEqual([], stat())

        create_orga = partial(Organisation.objects.create, user=user)
        managed2 = create_orga(name='Managed#2', is_managed=True)
        # Created after to test order by name
        managed1 = create_orga(name='Managed#1', is_managed=True)

        customer1 = create_orga(name='Customer#1')
        customer2 = create_orga(name='Customer#2')
        customer3 = create_orga(name='Customer#3')
        customer4 = Contact.objects.create(
            user=user, first_name='Customer#4', last_name='Customer#4',
        )

        create_rel = partial(Relation.objects.create, user=user, type_id=rtype_id)
        create_rel(subject_entity=customer1, object_entity=managed1)
        create_rel(subject_entity=customer2, object_entity=managed1)
        create_rel(subject_entity=customer3, object_entity=managed1)
        create_rel(
            subject_entity=customer3, object_entity=managed1,
            type_id=constants.REL_SUB_PARTNER,
        )
        create_rel(subject_entity=customer1, object_entity=managed2)
        create_rel(subject_entity=customer4, object_entity=managed2)

        fmt = _('For {name}: {related_count}').format
        self.assertListEqual(
            [
                fmt(name=managed1.name, related_count=3),
                fmt(name=managed2.name, related_count=2),
            ],
            stat(),
        )

    def test_customers(self):
        self._aux_test(statistics.CustomersStatistics, constants.REL_SUB_CUSTOMER_SUPPLIER)

    def test_prospects(self):
        self._aux_test(statistics.ProspectsStatistics, constants.REL_SUB_PROSPECT)

    def test_suspects(self):
        self._aux_test(statistics.SuspectsStatistics, constants.REL_SUB_SUSPECT)
