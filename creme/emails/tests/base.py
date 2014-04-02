# -*- coding: utf-8 -*-

try:
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models import Contact, Organisation

    from ..models import EntityEmail
    from ..constants import REL_SUB_MAIL_RECEIVED, REL_SUB_MAIL_SENDED, REL_SUB_RELATED_TO
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('EmailsTestCase',)


class _EmailsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'emails')


class EmailsTestCase(_EmailsTestCase):
    def test_populate(self):
        self.get_relationtype_or_fail(REL_SUB_MAIL_RECEIVED, [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_MAIL_SENDED,   [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_RELATED_TO,    [EntityEmail])

    def test_portal(self):
        self.login()
        self.assertGET200('/emails/')
