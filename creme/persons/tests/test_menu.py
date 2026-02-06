from django.utils.translation import gettext as _

from creme.creme_core.menu import CremeEntry

from ..menu import UserContactEntry
from .base import _PersonsTestCase


class UserContactEntryTestCase(_PersonsTestCase):
    def test_main(self):
        user = self.login_as_persons_user()
        url = user.linked_contact.get_absolute_url()
        self.assertEqual(url, user.get_absolute_url())

        self.add_credentials(user.role, all=['VIEW'])

        entry = UserContactEntry()
        self.assertEqual('persons-user_contact', entry.id)
        self.assertEqual(_("*User's contact*"), entry.label)
        self.assertHTMLEqual(
            f'<a href="{url}">{user}</a>',
            entry.render({
                # 'request': self.build_request(user=user),
                'user': user,
            }),
        )

        # ---
        creme_children = [*CremeEntry().children]

        for child in creme_children:
            if isinstance(child, UserContactEntry):
                break
        else:
            self.fail(f'No user entry found in {creme_children}.')

    def test_forbidden(self):
        user = self.login_as_standard()

        self.assertHTMLEqual(
            f'<span class="ui-creme-navigation-text-entry forbidden">{user}</span>',
            UserContactEntry().render({
                # 'request': self.build_request(user=user),
                'user': user,
            }),
        )

    def test_is_staff(self):
        user = self.login_as_super(is_staff=True)
        self.assertFalse(user.get_absolute_url())

        self.assertHTMLEqual(
            f'<span class="ui-creme-navigation-text-entry forbidden">{user}</span>',
            UserContactEntry().render({
                'user': user,
            }),
        )
