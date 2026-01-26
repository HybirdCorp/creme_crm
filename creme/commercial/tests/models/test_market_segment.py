from creme.commercial.models import MarketSegment

from ..base import CommercialBaseTestCase


class MarketSegmentTestCase(CommercialBaseTestCase):
    def test_unique_segment_with_ptype(self):
        self.get_object_or_fail(MarketSegment, property_type=None)

        with self.assertRaises(ValueError):
            MarketSegment.objects.create(name='Foobar', property_type=None)

    def test_portable_key(self):
        self.login_as_root()

        segment = self._create_segment(name='Industry')

        with self.assertNoException():
            key = segment.portable_key()
        self.assertIsInstance(key, str)
        self.assertUUIDEqual(segment.property_type.uuid, key)

        # ---
        with self.assertNoException():
            got_segment = MarketSegment.objects.get_by_portable_key(key)
        self.assertEqual(segment, got_segment)

    def test_portable_key__null(self):
        self.login_as_root()

        segment = self.get_object_or_fail(MarketSegment, property_type=None)
        key = 'all'
        self.assertEqual(key, segment.portable_key())

        # ---
        with self.assertNoException():
            got_segment = MarketSegment.objects.get_by_portable_key(key)
        self.assertEqual(segment, got_segment)
