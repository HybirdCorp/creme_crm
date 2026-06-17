from creme.creme_core.models import CremeProperty, Relation
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.utils.model import safe_model


class ModelTestCase(CremeTestCase):
    def test_safe_model(self):
        self.assertEqual(CremeProperty, safe_model(CremeProperty))
        self.assertEqual(Relation,      safe_model(Relation))

        self.assertEqual(CremeProperty, safe_model('creme_core.CremeProperty'))
        self.assertEqual(Relation,      safe_model('creme_core.Relation'))
