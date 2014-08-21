# -*- coding: utf-8 -*-

from creme.creme_core.models import CremePropertyType
from creme.creme_core.tests.base import CremeTestCase

from ..models import MarketSegment


class CommercialBaseTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'commercial')

    def setUp(self):
        self.login()

    #def _build_ctypefilter_field(self, ctype, efilter=None):
        #return '{"ctype": "%s", "efilter": "%s"}' % (ctype.id, efilter.id if efilter else '')
    def _build_ctypefilter_field(self, ctype=None, efilter=None):
        return '{"ctype": "%s", "efilter": "%s"}' % (ctype.id if ctype else 0, efilter.id if efilter else '')

    def _create_segment(self):
        #TODO: use a true segment creation view ??
        ptype = CremePropertyType.create('commercial-_prop_unitest', 'Segment type')
        return MarketSegment.objects.create(name='Segment#1', property_type=ptype)
