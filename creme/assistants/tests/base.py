# -*- coding: utf-8 -*-

try:
    from functools import partial

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import FakeContact as Contact
    from creme.creme_core.models.history import HistoryLine, TYPE_DELETION

    #from creme.persons.models import Contact
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class AssistantsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core', 'assistants')

    def setUp(self):
        self.login()
        self.entity = Contact.objects.create(user=self.user, first_name='Ranma', last_name='Saotome')

    def aux_test_merge(self, creator, assertor):
        user = self.user
        create_contact = partial(Contact.objects.create, user=user)
        contact01 = create_contact(first_name='Ryoga', last_name='Hibiki')
        contact02 = create_contact(first_name='Ryoag', last_name='Hibiik')

        creator(contact01, contact02)
        old_count = HistoryLine.objects.count()

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

        self.assertDoesNotExist(contact02)

        with self.assertNoException():
            contact01 = self.refresh(contact01)

        assertor(contact01)

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 1, len(hlines))  # No edition for 'entity_id'

        hline = hlines[-1]
        self.assertEqual(TYPE_DELETION, hline.type)
        self.assertEqual(unicode(contact02), hline.entity_repr)
