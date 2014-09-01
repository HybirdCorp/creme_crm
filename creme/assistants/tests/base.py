# -*- coding: utf-8 -*-

try:
    from functools import partial

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.models import SettingValue

    from creme.persons.models import Contact

    from ..constants import MIN_HOUR_4_TODO_REMINDER
    from ..models import UserMessagePriority
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('AssistantsAppTestCase',)


class AssistantsAppTestCase(CremeTestCase):
    def test_populate(self):
        self.populate('assistants')
        self.assertEqual(3, UserMessagePriority.objects.count())

        self.autodiscover()

        sv = self.get_object_or_fail(SettingValue, key_id=MIN_HOUR_4_TODO_REMINDER)
        self.assertEqual('assistants', sv.key.app_label)
        self.assertEqual(9, sv.value)


class AssistantsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'assistants')

    def setUp(self):
        self.login()
        self.entity = Contact.objects.create(user=self.user, first_name='Ranma', last_name='Saotome')

    def aux_test_merge(self, creator, assertor):
        user = self.user
        create_contact = partial(Contact.objects.create, user=user)
        contact01 = create_contact(first_name='Ryoga', last_name='Hibiki')
        contact02 = create_contact(first_name='Ryoag', last_name='Hibiik')

        creator(contact01, contact02)

        response = self.client.post(self.build_merge_url(contact01, contact02),
                                    follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'first_name_1':      contact01.first_name,
                                          'first_name_2':      contact02.first_name,
                                          'first_name_merged': contact01.first_name,

                                          'last_name_1':      contact01.last_name,
                                          'last_name_2':      contact02.last_name,
                                          'last_name_merged': contact01.last_name,
                                         }
                                   )
        self.assertNoFormError(response)

        self.assertFalse(Contact.objects.filter(pk=contact02).exists())

        with self.assertNoException():
            contact01 = self.refresh(contact01)

        assertor(contact01)
