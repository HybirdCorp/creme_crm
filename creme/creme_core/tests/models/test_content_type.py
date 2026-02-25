from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.models import FakeContact, FakeOrganisation, Language

from ..base import CremeTestCase


class ContentTypeTestCase(CremeTestCase):
    def test_ordering(self):
        self.assertListEqual(['id'], ContentType._meta.ordering)

    def test_str(self):
        get_ct = ContentType.objects.get_for_model
        self.assertEqual('Test Organisation', str(get_ct(FakeOrganisation)))
        self.assertEqual('Test Contact',      str(get_ct(FakeContact)))
        self.assertEqual(_('Language'),       str(get_ct(Language)))

    def test_fields(self):
        get_field = ContentType._meta.get_field
        with self.assertNoException():
            app_label_f = get_field('app_label')
        self.assertFalse(app_label_f.get_tag(FieldTag.VIEWABLE))

        with self.assertNoException():
            model_f = get_field('model')
        self.assertFalse(model_f.get_tag(FieldTag.VIEWABLE))

    def test_portable_key(self):
        ct = ContentType.objects.get_for_model(FakeOrganisation)

        with self.assertNoException():
            key = ct.portable_key()
        self.assertEqual('creme_core.fakeorganisation', key)

        # ---
        with self.assertNoException():
            got_ct = ContentType.objects.get_by_portable_key(key)
        self.assertEqual(ct, got_ct)
