# -*- coding: utf-8 -*-

try:
    from django.utils.translation import gettext as _

    from creme.creme_core.models import SettingValue, FieldsConfig

    from creme.persons.tests.base import skipIfCustomContact

    from ..constants import (REL_SUB_MAIL_RECEIVED, REL_SUB_MAIL_SENDED,
            REL_SUB_RELATED_TO, SETTING_EMAILCAMPAIGN_SENDER)
    from .base import _EmailsTestCase, Contact, Organisation, EntityEmail
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class EmailsTestCase(_EmailsTestCase):
    def test_populate(self):
        self.get_relationtype_or_fail(REL_SUB_MAIL_RECEIVED, [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_MAIL_SENDED,   [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_RELATED_TO,    [EntityEmail])

        self.assertEqual(1, SettingValue.objects.filter(key_id=SETTING_EMAILCAMPAIGN_SENDER).count())

    @skipIfCustomContact
    def test_fieldconfigs_warning(self):
        "If Contact/Organisation.email is hidden => warning"
        self.login()

        fconf = FieldsConfig.create(Contact)
        self.assertEqual([], fconf.errors_on_hidden)

        fconf.descriptions = [('email', {FieldsConfig.HIDDEN: True})]
        fconf.save()
        fconf = self.refresh(fconf)
        self.assertEqual([_('Warning: the app «{app}» need the field «{field}».').format(
                                app=_('Emails'),
                                field=_('Email address'),
                            ),
                         ],
                         fconf.errors_on_hidden
                        )
