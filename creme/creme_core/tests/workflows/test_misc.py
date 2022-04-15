from django.utils.translation import gettext as _

from creme.creme_core.core.workflow import WorkflowBrokenData
from creme.creme_core.models import FakeContact, FakeOrganisation
from creme.creme_core.workflows import model_as_key, model_from_key

from ..base import CremeTestCase


class UtilsTestCase(CremeTestCase):
    def test_model_to_key(self):
        self.assertEqual('creme_core.fakecontact', model_as_key(FakeContact))
        self.assertEqual('creme_core.fakeorganisation', model_as_key(FakeOrganisation))

    def test_key_to_model(self):
        self.assertEqual(FakeContact, model_from_key('creme_core.fakecontact'))
        self.assertEqual(FakeOrganisation, model_from_key('creme_core.fakeorganisation'))

    def test_key_to_model__error(self):
        key = 'uninstalled_app.model'
        with self.assertRaises(WorkflowBrokenData) as cm:
            model_from_key(key)
        self.assertEqual(
            _('The model «{key}» is invalid').format(key=key), str(cm.exception)
        )

        self.assertRaises(WorkflowBrokenData, model_from_key, '')
        self.assertRaises(WorkflowBrokenData, model_from_key, 'creme_core')
        self.assertRaises(WorkflowBrokenData, model_from_key, 'creme_core.fakecontact.suffix')
