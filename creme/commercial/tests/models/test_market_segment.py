from creme.commercial.models import MarketSegment

from ..base import CommercialBaseTestCase


class MarketSegmentTestCase(CommercialBaseTestCase):
    def test_unique_segment_with_ptype(self):
        self.get_object_or_fail(MarketSegment, property_type=None)

        with self.assertRaises(ValueError):
            MarketSegment.objects.create(name='Foobar', property_type=None)

    def test_portable_key(self):
        self.login_as_root()

        segment1 = self._create_segment(name='Industry')

        with self.assertNoException():
            key1 = segment1.portable_key()
        self.assertIsInstance(key1, str)
        self.assertUUIDEqual(segment1.property_type.uuid, key1)

        # ---
        with self.assertNoException():
            got_segment = MarketSegment.objects.get_by_portable_key(key1)
        self.assertEqual(segment1, got_segment)

        # ---
        segment2 = self._create_segment(name='Tourism')
        key2 = segment2.portable_key()
        self.assertUUIDEqual(segment2.property_type.uuid, key2)
        with self.assertNumQueries(1):
            got_segments = [*MarketSegment.objects.get_by_portable_keys([key1, key2])]
        self.assertCountEqual([segment1, segment2], got_segments)

    def test_portable_key__null(self):
        self.login_as_root()

        segment1 = self.get_object_or_fail(MarketSegment, property_type=None)
        all_key = 'all'
        self.assertEqual(all_key, segment1.portable_key())

        # ---
        with self.assertNoException():
            got_segment = MarketSegment.objects.get_by_portable_key(all_key)
        self.assertEqual(segment1, got_segment)

        # ---
        segment2 = self._create_segment(name='Tourism')
        key2 = segment2.portable_key()

        with self.assertNumQueries(1):
            got_segments = [*MarketSegment.objects.get_by_portable_keys([all_key, key2])]
        self.assertCountEqual([segment1, segment2], got_segments)
