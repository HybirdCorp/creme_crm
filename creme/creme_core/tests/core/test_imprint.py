# -*- coding: utf-8 -*-

from datetime import timedelta

from django.utils.timezone import now

from creme.creme_core.core.imprint import _ImprintManager
from creme.creme_core.models import FakeContact, FakeDocument, Imprint

from ..base import CremeTestCase


class ImprintManagerTestCase(CremeTestCase):
    def test_register_n_get(self):
        manager = _ImprintManager()
        self.assertIsNone(manager.get_granularity(FakeContact))

        manager.register(FakeContact, minutes=60)
        self.assertEqual(timedelta(minutes=60), manager.get_granularity(FakeContact))

        manager.register(FakeDocument, hours=2)
        self.assertEqual(timedelta(hours=2), manager.get_granularity(FakeDocument))

    def test_chained_registering(self):
        manager = _ImprintManager().register(
            FakeContact, minutes=60,
        ).register(
            FakeDocument, hours=2,
        )

        get_granularity = manager.get_granularity
        self.assertEqual(timedelta(minutes=60), get_granularity(FakeContact))
        self.assertEqual(timedelta(hours=2),    get_granularity(FakeDocument))

    def test_double_registering(self):
        manager = _ImprintManager()
        manager.register(FakeContact, minutes=60)

        with self.assertRaises(manager.RegistrationError):
            manager.register(FakeContact, minutes=90)

    def test_create01(self):
        manager = _ImprintManager()
        manager.register(FakeContact, minutes=60)

        user = self.login()
        willy = FakeContact.objects.create(user=user, first_name='Willy', last_name='Wonka')
        self.assertFalse(Imprint.objects.all())

        imprint = manager.create_imprint(entity=willy, user=user)
        self.assertIsInstance(imprint, Imprint)
        self.assertIsNotNone(imprint.id)
        self.assertDatetimesAlmostEqual(now(), imprint.date)
        self.assertEqual(imprint.entity.get_real_entity(), willy)
        self.assertEqual(imprint.user, user)

    def test_create02(self):
        "Delay is not passed."
        manager = _ImprintManager()
        manager.register(FakeContact, minutes=60)

        user = self.login()
        willy = FakeContact.objects.create(user=user, first_name='Willy', last_name='Wonka')

        imprint1 = Imprint.objects.create(entity=willy, user=user)
        self.assertIsNone(manager.create_imprint(entity=willy, user=user))

        # Other entity
        charlie = FakeContact.objects.create(user=user, first_name='Charlie', last_name='Bucket')
        self.assertIsNotNone(manager.create_imprint(entity=charlie, user=user))

        # Other user
        other_user = self.other_user
        imprint3 = manager.create_imprint(entity=willy, user=other_user)
        self.assertIsNotNone(imprint3)
        self.assertEqual(imprint3.user, other_user)

        # With older imprint
        Imprint.objects.filter(id=imprint1.id).update(date=now() - timedelta(minutes=59))
        self.assertIsNone(manager.create_imprint(entity=willy, user=user))

    def test_create03(self):
        "Delay_is passed."
        manager = _ImprintManager()
        manager.register(FakeContact, minutes=30)

        user = self.login()
        willy = FakeContact.objects.create(user=user, first_name='Willy', last_name='Wonka')

        imprint1 = Imprint.objects.create(entity=willy, user=user)
        Imprint.objects.filter(id=imprint1.id).update(date=now() - timedelta(minutes=31))

        self.assertIsNotNone(manager.create_imprint(entity=willy, user=user))

    def test_create04(self):
        "Model not registered."
        manager = _ImprintManager()
        manager.register(FakeDocument, minutes=60)

        user = self.login()
        willy = FakeContact.objects.create(user=user, first_name='Willy', last_name='Wonka')

        self.assertIsNone(manager.create_imprint(entity=willy, user=user))
