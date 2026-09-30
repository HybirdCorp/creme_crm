from django.template.loader import get_template
from django.utils.translation import gettext as _

from creme.creme_core.menu import CremeEntry

from ..menu import UserContactEntry
from .base import _PersonsTestCase


class UserContactEntryTestCase(_PersonsTestCase):
    def _build_context(self, user=None):
        user = user or self.get_root_user()

        return {
            'request': self.build_request(user=user),
            'user': user,
        }

    def _render_entry(self, *, page_context, entry):
        context = entry if isinstance(entry, dict) else entry.get_context(page_context)

        return get_template(context['template_name']).render({
            **page_context, 'entry': context,
        })

    def test_main(self):
        user = self.login_as_persons_user()
        url = user.linked_contact.get_absolute_url()
        self.assertEqual(url, user.get_absolute_url())

        self.add_credentials(user.role, all=['VIEW'])

        entry = UserContactEntry()
        self.assertEqual('persons-user_contact', entry.id)
        self.assertEqual(_("*User's contact*"), entry.label)

        context = self._build_context(user=user)
        entry_context = entry.get_context(context=context)
        self.assertDictEqual(
            {
                'id': entry.id,
                'label': entry.label,
                'permission_error': '',
                'template_name': 'persons/menu/user-contact.html',
                'type': '',
                'user': user,
            },
            entry_context,
        )
        self.assertHTMLEqual(
            f'<a href="{url}">{user}</a>',
            # entry.render({
            #     # 'request': self.build_request(user=user),
            #     'user': user,
            # }),
            self._render_entry(page_context=context, entry=entry_context),
        )

        # ---
        creme_children = [*CremeEntry().children]

        for child in creme_children:
            if isinstance(child, UserContactEntry):
                break
        else:
            self.fail(f'No user entry found in {creme_children}.')  # pragma: no cover

    def test_forbidden(self):
        user = self.login_as_standard()
        context = self._build_context(user=user)

        self.assertHTMLEqual(
            f'<span class="ui-creme-navigation-text-entry forbidden">{user}</span>',
            # UserContactEntry().render({
            #     # 'request': self.build_request(user=user),
            #     'user': user,
            # }),
            self._render_entry(page_context=context, entry=UserContactEntry()),
        )

    def test_is_staff(self):
        user = self.login_as_super(is_staff=True)
        self.assertFalse(user.get_absolute_url())

        context = self._build_context(user=user)
        self.assertHTMLEqual(
            f'<span class="ui-creme-navigation-text-entry forbidden">{user}</span>',
            # UserContactEntry().render({
            #     'user': user,
            # }),
            self._render_entry(page_context=context, entry=UserContactEntry()),
        )
