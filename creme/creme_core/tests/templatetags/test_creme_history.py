# -*- coding: utf-8 -*-

from datetime import timedelta

from django.utils.timezone import now

from creme.creme_core.models.history import (
    TYPE_CREATION,
    TYPE_EDITION,
    HistoryLine,
)
from creme.creme_core.templatetags import creme_history

from ..base import CremeTestCase
from ..fake_models import FakeContact


class CremeHistoryTagsTestCase(CremeTestCase):
    def test_history_summary01(self):
        "No edition."
        user = self.login()
        togame = FakeContact.objects.create(user=user, first_name='Togame', last_name='Kisakushi')
        self.assertTrue(HistoryLine.objects.filter(entity=togame.id))

        summary = creme_history.history_summary(entity=togame, user=user)
        self.assertIsInstance(summary, dict)
        self.assertEqual(2, len(summary))

        creation = summary.get('creation')
        self.assertIsInstance(creation, HistoryLine)
        self.assertIsNotNone(creation.id)
        self.assertEqual(TYPE_CREATION,  creation.type)
        self.assertEqual(togame.id,      creation.entity_id)
        self.assertEqual(togame.created, creation.date)
        self.assertIsNone(creation.user)

        with self.assertNoException():
            edition = summary['last_edition']

        self.assertIsNone(edition)

    def test_history_summary02(self):
        "Edition"
        user = self.login()
        togame = FakeContact.objects.create(user=user, first_name='Togame', last_name='Kisakushi')

        togame = self.refresh(togame)  # Clean cache
        togame.last_name = togame.last_name.upper()
        togame.save()
        self.assertEqual(2, HistoryLine.objects.filter(entity=togame.id).count())

        summary = creme_history.history_summary(entity=togame, user=user)
        self.assertIsInstance(summary, dict)
        self.assertEqual(2, len(summary))

        creation = summary.get('creation')
        self.assertEqual(TYPE_CREATION, creation.type)

        edition = summary.get('last_edition')
        self.assertIsInstance(edition, HistoryLine)
        self.assertIsNotNone(edition.id)
        self.assertEqual(TYPE_EDITION,    edition.type)
        self.assertEqual(togame.id,       edition.entity_id)
        self.assertEqual(togame.modified, edition.date)
        self.assertIsNone(edition.user)

    def test_history_summary03(self):
        "No stored history lines"
        user = self.login()

        togame = FakeContact(
            user=user, first_name='Togame', last_name='Kisakushi',
            created=now() - timedelta(hours=2),
        )
        HistoryLine.disable(togame)
        togame.save()
        self.assertFalse(HistoryLine.objects.filter(entity=togame.id))

        summary = creme_history.history_summary(entity=togame, user=user)
        self.assertIsInstance(summary, dict)
        self.assertEqual(2, len(summary))

        creation = summary.get('creation')
        self.assertIsInstance(creation, HistoryLine)
        self.assertIsNone(creation.id)
        self.assertEqual(TYPE_CREATION,  creation.type)
        self.assertEqual(togame.created, creation.date)
        self.assertIsNone(creation.user)

        edition = summary.get('last_edition')
        self.assertIsInstance(edition, HistoryLine)
        self.assertIsNone(edition.id)
        self.assertEqual(TYPE_EDITION,    edition.type)
        self.assertEqual(togame.modified, edition.date)
        self.assertIsNone(edition.user)

    def test_history_summary04(self):
        "Users"
        user = self.login()

        last_name = 'Kisakushi'
        data = {
            'user':       user.id,
            'first_name': 'Togame',
            'last_name':  last_name,
        }
        response = self.client.post(FakeContact.get_create_absolute_url(), follow=True, data=data)
        self.assertNoFormError(response)

        togame = self.get_object_or_fail(FakeContact, last_name=last_name)
        response = self.client.post(
            togame.get_edit_absolute_url(),
            follow=True,
            data={**data, 'phone': '123456'},
        )
        self.assertNoFormError(response)
        self.assertEqual(2, HistoryLine.objects.filter(entity=togame.id).count())

        with self.assertNumQueries(2):
            summary = creme_history.history_summary(entity=togame, user=user)

        with self.assertNumQueries(0):
            user1 = summary.get('creation').user
            user2 = summary.get('last_edition').user

        self.assertEqual(user, user1)
        self.assertEqual(user, user2)
