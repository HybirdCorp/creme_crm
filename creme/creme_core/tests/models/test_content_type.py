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
        ct1 = ContentType.objects.get_for_model(FakeOrganisation)

        with self.assertNoException():
            key1 = ct1.portable_key()
        self.assertEqual('creme_core.fakeorganisation', key1)

        # ---
        with self.assertNoException():
            got_ctype = ContentType.objects.get_by_portable_key(key1)
        self.assertEqual(ct1, got_ctype)

        # ---
        ct2 = ContentType.objects.get_for_model(FakeContact)
        key2 = ct2.portable_key()
        self.assertEqual('creme_core.fakecontact', key2)
        with self.assertNumQueries(0):
            got_ctypes = ContentType.objects.get_by_portable_keys([key1, key2])
        self.assertCountEqual([ct1, ct2], got_ctypes)

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

        # Cleanup
        stale_ct.delete()
        ContentType.objects.clear_cache()
