# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import SettingValue, FieldsConfig

    # from creme.persons import get_contact_model, get_organisation_model
    from creme.persons.tests.base import skipIfCustomContact

    # from .. import get_entityemail_model
    from ..constants import (REL_SUB_MAIL_RECEIVED, REL_SUB_MAIL_SENDED,
            REL_SUB_RELATED_TO, SETTING_EMAILCAMPAIGN_SENDER)
    from .base import _EmailsTestCase, Contact, Organisation, EntityEmail
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class EmailsTestCase(_EmailsTestCase):
    def test_populate(self):
        # EntityEmail = get_entityemail_model()
        # Contact = get_contact_model()
        # Organisation = get_organisation_model()

        self.get_relationtype_or_fail(REL_SUB_MAIL_RECEIVED, [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_MAIL_SENDED,   [EntityEmail], [Organisation, Contact])
        self.get_relationtype_or_fail(REL_SUB_RELATED_TO,    [EntityEmail])

        self.assertEqual(1, SettingValue.objects.filter(key_id=SETTING_EMAILCAMPAIGN_SENDER).count())

    def test_portal(self):
        self.login()
        self.assertGET200('/emails/')

    @skipIfCustomContact
    def test_fieldconfigs_warning(self):
        "If Contact/Organisation.email is hidden => warning"
        self.login()

        # fconf = FieldsConfig.create(get_contact_model())
        fconf = FieldsConfig.create(Contact)
        self.assertEqual([], fconf.errors_on_hidden)

        fconf.descriptions = [('email', {FieldsConfig.HIDDEN: True})]
        fconf.save()
        fconf = self.refresh(fconf)
        self.assertEqual([_(u'Warning: the app «%(app)s» need the field «%(field)s».') % {
                                'app':   _(u'Emails'),
                                'field': _(u'Email address'),
                            }
                         ],
                         fconf.errors_on_hidden
                        )
