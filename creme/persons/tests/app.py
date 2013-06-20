# -*- coding: utf-8 -*-

try:
    from creme.creme_core.models import EntityFilter, EntityFilterCondition
    from creme.creme_core.tests.base import CremeTestCase

    from ..models import Contact, Organisation
    from ..constants import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('PersonsAppTestCase',)


class PersonsAppTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config', 'persons')

    def test_populate(self):
        self.get_relationtype_or_fail(REL_SUB_EMPLOYED_BY,       [Contact],               [Organisation])
        self.get_relationtype_or_fail(REL_SUB_CUSTOMER_SUPPLIER, [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(REL_SUB_MANAGES,           [Contact],               [Organisation])
        self.get_relationtype_or_fail(REL_SUB_PROSPECT,          [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(REL_SUB_SUSPECT,           [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(REL_SUB_PARTNER,           [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(REL_SUB_INACTIVE,          [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(REL_SUB_SUBSIDIARY,        [Organisation],          [Organisation])
        self.get_relationtype_or_fail(REL_SUB_COMPETITOR,        [Contact, Organisation], [Contact, Organisation])

        efilter = self.get_object_or_fail(EntityFilter, pk=FILTER_MANAGED_ORGA)
        self.assertFalse(efilter.is_custom)
        self.assertEqual(Organisation, efilter.entity_type.model_class())
        self.assertEqual([EntityFilterCondition.EFC_PROPERTY], [c.type for c in efilter.conditions.all()])

    def test_portal(self):
        self.login()
        self.assertGET200('/persons/')

#TODO: tests for portal stats
