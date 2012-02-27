# -*- coding: utf-8 -*-

from creme_core.models import CremePropertyType
from creme_core.tests.base import CremeTestCase

from commercial.models import MarketSegment


class CommercialBaseTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.login()

    def _create_segment(self):
        #TODO: use a true segment creation view ??
        ptype = CremePropertyType.create('commercial-_prop_unitest', 'Segment type')
        return MarketSegment.objects.create(name='Segment#1', property_type=ptype)
