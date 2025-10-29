from django.core import mail
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core import constants, get_world_settings_model
from creme.creme_core.views.auth import PasswordReset

from ..base import CremeTestCase

WorldSettings = get_world_settings_model()


class UserViewsTestCase(CremeTestCase):
    def test_switch_role(self):
        user = self.login_as_standard()
        self.assertListEqual([user.role], [*user.roles.all()])

        role2 = self.create_role(name='Engineer')
        user.roles.add(role2)

        url = reverse('creme_core__switch_role', args=(user.id, role2.id))
        self.assertGET405(url)

        self.assertPOST200(url)
        self.assertEqual(role2, self.refresh(user).role)

        # ---
        role3 = self.create_role(name='Manager')
        response2 = self.client.post(
            reverse('creme_core__switch_role', args=(user.id, role3.id))
        )
        self.assertContains(
            response2,
            status_code=409, text=_('This role is not available for you'), html=True,
        )

    def test_switch_role__superuser(self):
        user = self.login_as_root_and_get()
        role = self.get_regular_role()

        response = self.client.post(
            reverse('creme_core__switch_role', args=(user.id, role.id))
        )
        self.assertContains(
            response,
            status_code=409, text=_('Superusers cannot switch their role'), html=True,
        )


class PasswordViewsTestCase(CremeTestCase):
    @override_settings(DEFAULT_FROM_EMAIL='admin@mycompagny.org')
    def test_reset_password(self):
        "Feature is enabled."
        user = self.create_user()

        software = 'My CRM'
        PasswordReset.extra_email_context['software'] = software

        w_settings = WorldSettings.objects.get()
        self.assertTrue(w_settings.password_reset_enabled)

        reset_url = reverse('creme_core__reset_password')
        response1 = self.assertGET200(reset_url)
        self.assertTemplateUsed(response1, 'creme_core/auth/password_reset/form.html')

        get_ctxt1 = response1.context.get
        self.assertEqual(_('Reset your password (Step 1/4)'), get_ctxt1('title'))
        self.assertEqual(_('Send me instructions'),           get_ctxt1('submit_label'))

        # ---
        response2 = self.client.post(reset_url, follow=True, data={'email': user.email})
        self.assertNoFormError(response2)
        self.assertRedirects(response2, reverse('creme_core__password_reset_done'))
        self.assertTemplateUsed(response2, 'creme_core/auth/password_reset/done.html')
        self.assertEqual(_('Reset your password (Step 2/4)'), response2.context.get('title'))

        message = self.get_alone_element(mail.outbox)
        self.assertListEqual([user.email], message.recipients())
        self.assertEqual('admin@mycompagny.org', message.from_email)
        self.assertListEqual([], message.alternatives)
        self.assertFalse(message.attachments)
        self.assertEqual(
            _('%(software)s > Reinitialisation of your password') % {'software': software},
            message.subject,
        )

        body = message.body
        self.assertIn(user.username, body)

        confirm_url_prefix = 'http://testserver'
        confirm_url_start_index = body.find(confirm_url_prefix)
        self.assertNotEqual(-1, confirm_url_start_index)

        with self.assertNoException():
            raw_confirm_url = body[confirm_url_start_index:].split(None, 1)[0]
            confirm_url_parts = raw_confirm_url.split('/')
            # TODO: meh (depends on the URL pattern) (retrieve from session?)
            token = confirm_url_parts[-1]
            b64uid = confirm_url_parts[-2]

        confirm_url = reverse('creme_core__password_reset_confirm', args=(b64uid, token))
        self.assertEqual(raw_confirm_url, confirm_url_prefix + confirm_url)

        self.assertEqual(
            _(
                'Hi,\n\n'
                'You receive this email because a reset of your password for '
                '%(software)s has been requested.\n\n'
                'Click on the following link to choose a new password: %(url)s\n\n'
                'Here your username in case you forgot it too: %(username)s\n\n'
                'Thanks for show an interest in %(software)s.\n\n'
                'Your %(software)s administrator\n'
            ) % {
                'software': software,
                'username': user.username,
                'url': raw_confirm_url,
            },
            body,
        )

        # ----
        response3 = self.assertGET200(confirm_url, follow=True)
        self.assertTemplateUsed(response3, 'creme_core/auth/password_reset/form.html')

        get_ctxt3 = response3.context.get
        self.assertEqual(_('Reset your password (Step 3/4)'), get_ctxt3('title'))
        self.assertEqual(_('Save the new password'),          get_ctxt3('submit_label'))

        # ---
        validated_confirm_url = reverse(
            'creme_core__password_reset_confirm', args=(b64uid, 'set-password'),
        )
        self.assertRedirects(response3, validated_confirm_url)

        password = 'Luf-ShmifAj4'
        response4 = self.client.post(
            validated_confirm_url,
            follow=True,
            data={
                'new_password1': password,
                'new_password2': password,
            },
        )
        self.assertNoFormError(response4)

        self.assertRedirects(response4, reverse('creme_core__password_reset_complete'))
        self.assertTemplateUsed(response4, 'creme_core/auth/password_reset/complete.html')

        self.assertTrue(self.refresh(user).check_password(password))

    def test_reset_password__disabled(self):
        "Feature is disabled."
        self.create_user()

        WorldSettings.objects.update(password_reset_enabled=False)

        url = reverse('creme_core__reset_password')
        self.assertGET403(url)
        self.assertPOST403(url)

    def test_change_own_password(self):
        "Feature is enabled."
        self.login_as_root()
        user = self.get_root_user()

        w_settings = WorldSettings.objects.get()
        self.assertTrue(w_settings.password_change_enabled)
        self.assertTrue(w_settings.password_reset_enabled)

        change_url = reverse('creme_core__change_own_password')
        response1 = self.assertGET200(change_url)
        self.assertTemplateUsed(response1, 'creme_core/generics/form/edit.html')
        self.assertContains(response1, reverse('creme_core__reset_password'))

        get_ctxt1 = response1.context.get
        self.assertEqual(_('Change your password'),  get_ctxt1('title'))
        self.assertEqual(_('Save the new password'), get_ctxt1('submit_label'))
        self.assertIsNotNone(get_ctxt1('help_message'))

        new_password = 'astElal5Op!'
        response2 = self.client.post(
            change_url,
            follow=True,
            data={
                'old_password': constants.ROOT_PASSWORD,
                'new_password1': new_password,
                'new_password2': new_password,
            },
        )
        self.assertNoFormError(response2)
        self.assertTrue(self.refresh(user).check_password(new_password))

        self.assertRedirects(response2, reverse('creme_core__own_password_change_done'))
        self.assertTemplateUsed(response2, 'creme_core/info.html')

        get_ctxt2 = response2.context.get
        self.assertEqual(_('Password change successful'),  get_ctxt2('title'))
        self.assertListEqual(
            [_('Use your new password the next time you want to login.')],
            get_ctxt2('information_messages'),
        )

    def test_change_own_password__disabled(self):
        "Feature is disabled."
        self.login_as_root()

        WorldSettings.objects.update(password_change_enabled=False)

        url = reverse('creme_core__change_own_password')
        self.assertGET403(url)
        self.assertPOST403(url)

    def test_change_own_password__reset_disabled(self):
        "Feature 'reset password' is disabled."
        self.login_as_root()

        w_settings = WorldSettings.objects.get()
        w_settings.password_reset_enabled = False
        w_settings.save()

        response = self.assertGET200(reverse('creme_core__change_own_password'))
        self.assertNotContains(response, reverse('creme_core__reset_password'))
