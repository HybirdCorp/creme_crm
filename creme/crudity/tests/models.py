# -*- coding: utf-8 -*-

try:
    from datetime import datetime

    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import CremeEntity

    from creme.persons.models import Contact

    from ..models import WaitingAction
    from .base import CrudityTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('WaitingActionTestCase',)


class WaitingActionTestCase(CrudityTestCase):
    def test_can_validate_or_delete01(self):
        "Sandbox for everyone"
        action = WaitingAction.objects.create(user=None, source="unknown", action="create", subject="",
                                              ct=ContentType.objects.get_for_model(CremeEntity)
                                             )
        self.assertTrue(action.can_validate_or_delete(self.user)[0])
        self.assertTrue(action.can_validate_or_delete(self.other_user)[0])

    def test_can_validate_or_delete02(self):
        "Sandbox by user"
        self._set_sandbox_by_user()
        ct = ContentType.objects.get_for_model(CremeEntity)
        action  = WaitingAction.objects.create(user=self.user, source="unknown", action="create", subject="", ct=ct)
        self.assert_(action.can_validate_or_delete(self.user)[0])
        self.assertFalse(action.can_validate_or_delete(self.other_user)[0])

        action2 = WaitingAction.objects.create(user=self.other_user, source="unknown", action="create", subject="", ct=ct)
        self.assertTrue(action2.can_validate_or_delete(self.user)[0])
        self.assertTrue(action2.can_validate_or_delete(self.other_user)[0])

    def test_auto_assignation01(self):
        """If the sandbox was not by user, but now it is all WaitingAction has
        to be assigned to someone.
        """
        action  = WaitingAction.objects.create(source="unknown", action="create", subject="",
                                               ct=ContentType.objects.get_for_model(CremeEntity)
                                              )
        self.assertIsNone(action.user)

        #Sandbox will be by user
        self._set_sandbox_by_user()
        self.assertEqual(0, WaitingAction.objects.filter(user=None).count())
        self.assertEqual(self.user, WaitingAction.objects.filter(user__isnull=False)[0].user)

    def test_auto_assignation02(self):
        action = WaitingAction.objects.create(source="unknown", action="create", subject="",
                                              ct=ContentType.objects.get_for_model(CremeEntity)
                                             )
        self.assertIsNone(action.user)

        #superuser1 = self.user

        superuser2 = User.objects.create(username='Kirika2')
        superuser2.set_password("Kirika2")
        superuser2.is_superuser = True
        superuser2.save()

        self._set_sandbox_by_user()
        self.assertEqual(0, WaitingAction.objects.filter(user=None).count())
        self.assertEqual(superuser2, WaitingAction.objects.filter(user__isnull=False)[0].user)

    def test_data_property01(self):
        action = WaitingAction(ct=ContentType.objects.get_for_model(Contact))
        expected_data = {u'first_name': u'Mario', u'last_name': u'Bros'}
        action.data = action.set_data(expected_data)
        action.save()

        self.assertEqual(expected_data, self.refresh(action).get_data())

    def test_data_property02(self):
        action = WaitingAction(ct=ContentType.objects.get_for_model(Contact))
        expected_data = {u'first_name': u'Mario', u'last_name': u'Bros', u"friends": [u"Yoshi", u"Toad"],
                         u"lives": 99, u"ennemies": {'Bowser': 1, 'Koopa':50}, "epoch": datetime.now()}
        action.data = action.set_data(expected_data)
        action.save()

        self.assertEqual(expected_data, self.refresh(action).get_data())
