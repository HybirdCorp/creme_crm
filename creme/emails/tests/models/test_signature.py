from creme.emails.models import EmailSignature

from ..base import _EmailsTestCase


class EmailSignatureTestCase(_EmailsTestCase):
    def test_portable_key(self):
        user = self.get_root_user()
        signature1 = EmailSignature.objects.create(
            user=user, name='Funny signature', body='I love you... not',
        )

        with self.assertNoException():
            key1 = signature1.portable_key()
        self.assertIsInstance(key1, str)
        self.assertUUIDEqual(signature1.uuid, key1)

        # ---
        with self.assertNoException():
            got_signature = EmailSignature.objects.get_by_portable_key(key1)
        self.assertEqual(signature1, got_signature)

        # ---
        signature2 = EmailSignature.objects.create(
            user=user, name='Other signature', body='Have a good day',
        )
        with self.assertNumQueries(1):
            got_signatures = [*EmailSignature.objects.get_by_portable_keys(
                [key1, signature2.portable_key()]
            )]
        self.assertCountEqual([signature1, signature2], got_signatures)
