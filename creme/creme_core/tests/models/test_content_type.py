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

    def test_get_fresh_for_id(self):
        ct = ContentType.objects.get_for_model(FakeOrganisation)
        self.assertEqual(ct, ContentType.objects.get_fresh_for_id(ct.id))

        # ---
        with self.assertNoLogs():
            with self.assertRaises(ContentType.DoesNotExist) as exc_cm1:
                ContentType.objects.get_fresh_for_id(self.UNUSED_PK)
            self.assertEqual(
                'ContentType matching query does not exist.', str(exc_cm1.exception),
            )

        # ---
        stale_ct = ContentType.objects.create(app_label='creme_core', model='i_am_stale')
        with self.assertLogs(level='CRITICAL') as logs_cm:
            with self.assertRaises(ContentType.DoesNotExist) as exc_cm2:
                ContentType.objects.get_fresh_for_id(stale_ct.id)
        self.assertEqual(
            f'ContentType with id={stale_ct.id} is stale.', str(exc_cm2.exception),
        )
        self.assertListEqual(
            [
                f'CRITICAL:creme.creme_core.models.content_type:'
                f'ContentType with id={stale_ct.id} is stale; it seems the '
                f'model has been removed but not the related ContentType.'
            ],
            logs_cm.output,
        )
        stale_ct.delete()  # Cleanup
