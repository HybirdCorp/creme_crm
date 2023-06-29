from creme.emails.models import EmailSyncConfigItem
from creme.emails.tests.base import _EmailsTestCase


class SynchronizationModelsTestCase(_EmailsTestCase):
    def test_config_item(self):
        password = 'c0w|3OY B3b0P'
        item = EmailSyncConfigItem.objects.create(
            host='pop.mydomain.org',
            username='spike',
            password=password,
            port=112,
            use_ssl=False,
        )
        self.assertIsNone(item.default_user)

        with self.assertNoException():
            _ = EmailSyncConfigItem._meta.get_field('encoded_password')

        self.assertNotIn(
            'password',
            {f.name for f in EmailSyncConfigItem._meta.concrete_fields},
        )

        item = self.refresh(item)
        self.assertNotEqual(password, item.encoded_password)
        self.assertEqual(password, item.password)

        # Bad signature ---
        item.encoded_password = 'invalid'

        with self.assertLogs(level='CRITICAL') as logs_manager:
            password = item.password

        self.assertEqual('', password)
        self.assertListEqual(
            logs_manager.output,
            [
                f'CRITICAL:'
                f'creme.emails.models.synchronization:creme.emails.models.synchronization: '
                f'issue with password of EmailSyncConfigItem with id={item.id}: '
                f'SymmetricEncrypter.decrypt: invalid token'
            ],
        )
