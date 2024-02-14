from django.utils.translation import gettext as _

from creme.creme_core.models import FieldsConfig
from creme.persons.tests.base import skipIfCustomContact

from ..constants import (
    REL_SUB_MAIL_RECEIVED,
    REL_SUB_MAIL_SENT,
    REL_SUB_RELATED_TO,
)
from .base import Contact, EntityEmail, Organisation, _EmailsTestCase


class EmailsTestCase(_EmailsTestCase):
    def test_populate(self):
        self.get_relationtype_or_fail(
            REL_SUB_MAIL_RECEIVED, [EntityEmail], [Organisation, Contact],
        )
        self.get_relationtype_or_fail(
            REL_SUB_MAIL_SENT, [EntityEmail], [Organisation, Contact],
        )
        self.get_relationtype_or_fail(REL_SUB_RELATED_TO, [EntityEmail])

    @skipIfCustomContact
    def test_fieldconfigs_warning(self):
        "If Contact/Organisation.email is hidden => warning."
        self.login_as_root()

        fconf = FieldsConfig.objects.create(content_type=Contact, descriptions=[])
        self.assertListEqual([], fconf.errors_on_hidden)

        fconf.descriptions = [('email', {FieldsConfig.HIDDEN: True})]
        fconf.save()
        fconf = self.refresh(fconf)
        self.assertListEqual(
            [
                _('Warning: the app «{app}» need the field «{field}».').format(
                    app=_('Emails'),
                    field=_('Email address'),
                ),
            ],
            fconf.errors_on_hidden,
        )
