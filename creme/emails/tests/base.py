# -*- coding: utf-8 -*-

try:
    from creme.creme_core.models import SettingValue
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models import Contact, Organisation

    from ..models import EntityEmail
    from ..constants import (REL_SUB_MAIL_RECEIVED,
        REL_SUB_MAIL_SENDED, REL_SUB_RELATED_TO, SETTING_EMAILCAMPAIGN_SENDER)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('EmailsTestCase',)


class _EmailsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core', 'emails')


class EmailsTestCase(_EmailsTestCase):
    def test_populate(self):
        self.get_relationtype_or_fail(REL_SUB_MAIL_RECEIVED, [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_MAIL_SENDED,   [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_RELATED_TO,    [EntityEmail])

        self.assertEqual(1, SettingValue.objects.filter(key_id=SETTING_EMAILCAMPAIGN_SENDER).count())

    def test_portal(self):
        self.login()
        self.assertGET200('/emails/')
