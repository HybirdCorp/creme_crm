# -*- coding: utf-8 -*-

try:
    from creme.creme_core.models import SettingValue

    from creme.persons import get_contact_model, get_organisation_model

    from .. import get_entityemail_model
    from ..constants import (REL_SUB_MAIL_RECEIVED, REL_SUB_MAIL_SENDED,
            REL_SUB_RELATED_TO, SETTING_EMAILCAMPAIGN_SENDER)
    from .base import _EmailsTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('EmailsTestCase',)


class EmailsTestCase(_EmailsTestCase):
    def test_populate(self):
        EntityEmail = get_entityemail_model()
        Contact = get_contact_model()
        Organisation = get_organisation_model()

        self.get_relationtype_or_fail(REL_SUB_MAIL_RECEIVED, [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_MAIL_SENDED,   [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_RELATED_TO,    [EntityEmail])

        self.assertEqual(1, SettingValue.objects.filter(key_id=SETTING_EMAILCAMPAIGN_SENDER).count())

    def test_portal(self):
        self.login()
        self.assertGET200('/emails/')
