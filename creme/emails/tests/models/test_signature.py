from creme.emails.models import EmailSignature

from ..base import _EmailsTestCase


class EmailSignatureTestCase(_EmailsTestCase):
    def test_portable_key(self):
        user = self.get_root_user()

        signature = EmailSignature.objects.create(
            user=user, name='Funny signature', body='I love you... not',
        )

        with self.assertNoException():
            key = signature.portable_key()
        self.assertIsInstance(key, str)
        self.assertUUIDEqual(signature.uuid, key)

        # ---
        with self.assertNoException():
            got_signature = EmailSignature.objects.get_by_portable_key(key)
        self.assertEqual(signature, got_signature)
