# -*- coding: utf-8 -*-

try:
    from creme_core.models import CremeEntity
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact

    from assistants.models import UserMessagePriority
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('AssistantsAppTestCase',)


class AssistantsAppTestCase(CremeTestCase):
    def test_populate(self):
        self.populate('assistants')
        self.assertEqual(3, UserMessagePriority.objects.count())


class AssistantsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.login()
        #self.entity = CremeEntity.objects.create(user=self.user)
        self.entity = Contact.objects.create(user=self.user, first_name='Ranma', last_name='Saotome')

    def aux_test_merge(self, creator, assertor):
        user = self.user
        create_contact = Contact.objects.create
        contact01 = create_contact(user=user, first_name='Ryoga', last_name='Hibiki')
        contact02 = create_contact(user=user, first_name='Ryoag', last_name='Hibiik')

        creator(contact01, contact02)

        response = self.client.post('/creme_core/entity/merge/%s,%s' % (contact01.id, contact02.id),
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
