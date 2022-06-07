from uuid import uuid4

from django.contrib.auth.hashers import check_password
from django.test import TestCase
from django.utils import timezone

from creme.creme_api.models import Application, Token


class ApplicationTestCase(TestCase):
    def test_init(self):
        application = Application(name="TestCase")
        self.assertTrue(application.application_id)
        self.assertEqual(len(application.application_secret), 0)
        self.assertTrue(application.enabled)
        self.assertEqual(application.token_duration, 3600)
        self.assertEqual(application.application_secret, "")
        self.assertIsNone(application._application_secret)

    def test_str(self):
        application = Application(name="TestCase")
        self.assertEqual(str(application), "TestCase")

    def test_set_application_secret(self):
        application = Application(name="TestCase")
        application.set_application_secret("Password")
        self.assertEqual(application._application_secret, "Password")
        self.assertIsNotNone(application.application_secret)
        self.assertTrue(check_password("Password", application.application_secret))

    def test_save01(self):
        application = Application(name="TestCase")
        application.save()
        self.assertIsNotNone(application._application_secret)
        self.assertIsNotNone(application.application_secret)
        self.assertTrue(
            check_password(
                application._application_secret, application.application_secret
            )
        )

        application.save()
        self.assertTrue(
            check_password(
                application._application_secret, application.application_secret
            )
        )

    def test_save02(self):
        application = Application.objects.create(name="TestCase")
        self.assertIsNotNone(application._application_secret)
        self.assertIsNotNone(application.application_secret)
        self.assertTrue(
            check_password(
                application._application_secret, application.application_secret
            )
        )

    def test_check_application_secret(self):
        application = Application(name="TestCase")
        application.set_application_secret("Password")
        self.assertTrue(application.check_application_secret("Password"))
        self.assertFalse(application.check_application_secret("WrongPassword"))

    def test_can_authenticate(self):
        application = Application(name="TestCase", enabled=True)
        self.assertTrue(application.can_authenticate())
        application = Application(name="TestCase", enabled=False)
        self.assertFalse(application.can_authenticate())

    def test_authenticate01(self):
        self.assertIsNone(Application.authenticate("application_id", "Secret"))

    def test_authenticate02(self):
        self.assertIsNone(Application.authenticate(uuid4().hex, "WrongSecret"))

    def test_authenticate03(self):
        application = Application.objects.create(name="TestCase", enabled=False)
        self.assertIsNone(
            Application.authenticate(
                application.application_id, application._application_secret
            )
        )

    def test_authenticate04(self):
        application = Application.objects.create(name="TestCase")
        authenticated_application = Application.authenticate(
            application.application_id, application._application_secret
        )
        self.assertEqual(authenticated_application.pk, application.pk)


class TokenTestCase(TestCase):
    def test_init(self):
        application = Application.objects.create(name="TestCase")
        token = Token(application=application)
        self.assertEqual(len(token.code), 128)

    def test_save01(self):
        application = Application.objects.create(name="TestCase", token_duration=20)
        token = Token(application=application)
        self.assertIsNone(token.expires)
        token.save()
        expected_expires = timezone.now() + timezone.timedelta(seconds=20)
        self.assertAlmostEqual(
            token.expires, expected_expires, delta=timezone.timedelta(seconds=1)
        )

    def test_save02(self):
        application = Application.objects.create(name="TestCase", token_duration=20)
        expires = timezone.now() + timezone.timedelta(seconds=10)
        token = Token.objects.create(application=application, expires=expires)
        self.assertEqual(token.expires, expires)

    def test_is_expired01(self):
        application = Application.objects.create(name="TestCase")
        expires = timezone.now() + timezone.timedelta(seconds=10)
        token = Token.objects.create(application=application, expires=expires)
        self.assertFalse(token.is_expired())

    def test_is_expired02(self):
        application = Application.objects.create(name="TestCase")
        expires = timezone.now() - timezone.timedelta(seconds=10)
        token = Token.objects.create(application=application, expires=expires)
        self.assertTrue(token.is_expired())
