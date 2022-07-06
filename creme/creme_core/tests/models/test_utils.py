from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_models import FakeAddress
from creme.creme_core.utils import truncate_str


class ModelUtilsTestCase(CremeTestCase):
    def test_assign_2_charfield01(self):
        "Short value"
        self.assertEqual(40, FakeAddress._meta.get_field('country').max_length)

        addr = FakeAddress()
        val = 'Groland'
        assign_2_charfield(addr, 'country', val)
        self.assertEqual(val, addr.country)

    def test_assign_2_charfield02(self):
        "Long value"
        addr = FakeAddress()

        val = 'A country with a very very very long name'
        self.assertEqual(41, len(val))

        assign_2_charfield(addr, 'country', val)
        self.assertEqual(
            'A country with a very very very long na…',
            addr.country,
        )

    def test_assign_2_charfield03(self):
        "Other truncate policy"
        addr = FakeAddress()

        val = 'A country with a very very very long name'
        self.assertEqual(41, len(val))

        assign_2_charfield(addr, 'country', val, truncate=truncate_str)
        self.assertEqual(
            'A country with a very very very long nam',
            addr.country,
        ),
