from functools import partial

from creme.emails.models import EmailRecipient

from ..base import (
    Contact,
    MailingList,
    Organisation,
    _EmailsTestCase,
    skipIfCustomMailingList,
)


@skipIfCustomMailingList
class MailingListTestCase(_EmailsTestCase):
    def test_clone(self):
        user = self.login_as_root_and_get()
        create_ml = partial(MailingList.objects.create, user=user)
        mlist = create_ml(name='ml01')
        child = create_ml(name='ml02')

        mlist.children.add(child)

        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
        )
        mlist.contacts.add(contact)

        orga = Organisation.objects.create(user=user, name='Bepop')
        mlist.organisations.add(orga)

        email = 'faye@bebop.mrs'
        EmailRecipient.objects.create(ml=mlist, address=email)

        cloned_mlist = self.clone(mlist)
        self.assertIsInstance(cloned_mlist, MailingList)
        self.assertNotEqual(mlist.pk, cloned_mlist.pk)
        self.assertEqual(mlist.name, cloned_mlist.name)
        self.assertCountEqual([child],   cloned_mlist.children.all())
        self.assertCountEqual([contact], cloned_mlist.contacts.all())
        self.assertCountEqual([orga],    cloned_mlist.organisations.all())
        self.assertCountEqual(
            [email], cloned_mlist.emailrecipient_set.values_list('address', flat=True),
        )

    # def test_clone__method(self):  # DEPRECATED
    #     user = self.get_root_user()
    #     create_ml = partial(MailingList.objects.create, user=user)
    #     mlist = create_ml(name='ml01')
    #     child = create_ml(name='ml02')
    #
    #     mlist.children.add(child)
    #
    #     contact = Contact.objects.create(
    #         user=user, first_name='Spike', last_name='Spiegel',
    #     )
    #     mlist.contacts.add(contact)
    #
    #     orga = Organisation.objects.create(user=user, name='Bepop')
    #     mlist.organisations.add(orga)
    #
    #     email = 'faye@bebop.mrs'
    #     EmailRecipient.objects.create(ml=mlist, address=email)
    #
    #     cloned_mlist = mlist.clone()
    #     self.assertIsInstance(cloned_mlist, MailingList)
    #     self.assertNotEqual(mlist.pk, cloned_mlist.pk)
    #     self.assertEqual(mlist.name, cloned_mlist.name)
    #     self.assertCountEqual([child],   cloned_mlist.children.all())
    #     self.assertCountEqual([contact], cloned_mlist.contacts.all())
    #     self.assertCountEqual([orga],    cloned_mlist.organisations.all())
    #     self.assertCountEqual(
    #         [email], cloned_mlist.emailrecipient_set.values_list('address', flat=True),
    #     )
