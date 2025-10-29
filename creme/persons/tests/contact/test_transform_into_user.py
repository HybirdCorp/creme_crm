from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import CremeUser

from ..base import Contact, _BaseTestCase, skipIfCustomContact


@skipIfCustomContact
class TransformationIntoUserTestCase(_BaseTestCase):
    @staticmethod
    def _build_as_user_url(contact):
        return reverse('persons__transform_contact_into_user', args=(contact.id,))

    def test_transform_into_user(self):
        user = self.login_as_root_and_get()
        first_name = 'Spike'
        last_name = 'Spiegel'
        email = 'spike@bebop.mrs'
        contact = Contact.objects.create(
            user=user, first_name=first_name, last_name=last_name, email=email,
        )

        old_contact_count = Contact.objects.count()
        old_user_count    = CremeUser.objects.count()

        url = self._build_as_user_url(contact)
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Transform «{object}» into a user').format(object=contact),
            context1.get('title'),
        )
        self.assertEqual(
            _('Save the user').format(object=contact),
            context1.get('submit_label'),
        )

        with self.assertNoException():
            fields = context1['form'].fields
            # role_f = fields['role']
            email_f = fields['email']

        self.assertIn('username', fields)
        self.assertIn('displayed_name', fields)
        self.assertIn('password_1', fields)
        self.assertIn('password_2', fields)
        self.assertIn('roles', fields)
        self.assertNotIn('last_name', fields)
        self.assertNotIn('first_name', fields)

        # self.assertEqual('*{}*'.format(_('Superuser')), role_f.empty_label)

        self.assertTrue(email_f.required)
        self.assertEqual(email, email_f.initial)
        self.assertEqual(
            _('The email of the Contact will be updated if you change it.'),
            email_f.help_text,
        )

        # ---
        username = 'spikes'
        password = '$33 yo|_| sp4c3 c0wb0Y'
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'username': username,
                # 'displayed_name': ...
                'password_1': password,
                'password_2': password,
                # 'role': ...
                'roles': [],
                'email': email,
            },
        )
        self.assertNoFormError(response2)

        self.assertEqual(old_user_count + 1, CremeUser.objects.count())
        self.assertEqual(old_contact_count, Contact.objects.count())

        contact = self.refresh(contact)
        self.assertEqual(last_name,  contact.last_name)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(email,      contact.email)

        contact_user = contact.is_user
        self.assertIsNotNone(contact_user)
        self.assertEqual(username,   contact_user.username)
        self.assertEqual(last_name,  contact_user.last_name)
        self.assertEqual(first_name, contact_user.first_name)
        self.assertEqual(email,      contact_user.email)
        self.assertFalse(contact_user.displayed_name)
        self.assertTrue(contact_user.is_superuser)
        self.assertIsNone(contact_user.role)
        self.assertFalse(contact_user.roles.all())
        self.assertTrue(contact_user.check_password(password))

        self.assertRedirects(response2, contact.get_absolute_url())

        # Already related to a user ---
        self.assertGET409(url)

    def test_transform_into_user__not_superuser(self):
        user = self.login_as_persons_user(admin_4_apps=['persons'])
        self.add_credentials(user.role, own='*')

        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel', email='spike@bebop.mrs',
        )
        self.assertGET403(self._build_as_user_url(contact))

    def test_transform_into_user__no_email(self):
        user = self.login_as_root_and_get()
        first_name = 'Jet'
        last_name = 'Black'
        contact = Contact.objects.create(
            user=user, first_name=first_name, last_name=last_name,
            # email=...,  # <====
        )
        role = self.create_role(name='Pilot')

        url = self._build_as_user_url(contact)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            email_f = fields['email']
            # role_f = fields['role']
            roles_f = fields['roles']

        self.assertTrue(email_f.required)
        self.assertEqual(
            _('The email of the Contact will be updated.'),
            email_f.help_text,
        )

        # self.assertInChoices(value=role.id, label=role.name, choices=role_f.choices)
        self.assertInChoices(value=role.id, label=role.name, choices=roles_f.choices)

        # ---
        username = 'jet'
        password = 'sp4c3 c0wb0Y'
        displayed_name = 'jetto'
        email = 'jet@bebop.mrs'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'username': username,
                'displayed_name': displayed_name,
                'password_1': password,
                'password_2': password,
                'email': email,
                # 'role': role.id,
                'roles': [role.id],
            },
        ))

        contact = self.refresh(contact)
        self.assertEqual(email, contact.email)

        contact_user = contact.is_user
        self.assertIsNotNone(contact_user)
        self.assertEqual(username,       contact_user.username)
        self.assertEqual(last_name,      contact_user.last_name)
        self.assertEqual(first_name,     contact_user.first_name)
        self.assertEqual(displayed_name, contact_user.displayed_name)
        self.assertEqual(email,          contact_user.email)
        self.assertEqual(role,           contact_user.role)
        self.assertFalse(contact_user.is_superuser)
        self.assertListEqual([role], [*contact_user.roles.all()])

    def test_transform_into_user__no_first_name(self):
        user = self.login_as_root_and_get()
        last_name = 'Valentine'
        email = 'faye@bebop.mrs'
        contact = Contact.objects.create(
            user=user, last_name=last_name, email=email,
            # first_name=...,
        )

        url = self._build_as_user_url(contact)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            first_name_f = response1.context['form'].fields['first_name']

        self.assertTrue(first_name_f.required)
        self.assertEqual(
            _('The first name of the Contact will be updated.'),
            first_name_f.help_text,
        )

        # ---
        password = 'sp4c3 c0wg1rL'
        first_name = 'Faye'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'username': 'fayev',
                'first_name': first_name,
                'password_1': password,
                'password_2': password,
                'email': 'faye@bebop.mrs',
            },
        ))

        contact = self.refresh(contact)
        self.assertEqual(first_name, contact.first_name)

        contact_user = contact.is_user
        self.assertEqual(last_name,  contact_user.last_name)
        self.assertEqual(first_name, contact_user.first_name)
        self.assertEqual(email,      contact_user.email)

    def test_transform_into_user__password_mismatch(self):
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(
            user=user, last_name='Spiegel',
            first_name='Spike',
            email='spiegel@bebop.mrs',
        )

        response = self.assertPOST200(
            self._build_as_user_url(contact),
            data={
                'username': 'spike',
                'password_1': 'sp4c3 c0wg1rL',
                'password_2': 'not sp4c3 c0wg1rL',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='password_2',
            errors=_("The two password fields didn’t match."),
        )

    def test_transform_into_user__existing_user(self):
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(
            user=user, last_name='Spiegel',
            first_name='Spike',
            email='spiegel@bebop.mrs',
        )

        password = 'sp4c3 c0wg1rL'
        response = self.assertPOST200(
            self._build_as_user_url(contact),
            data={
                'username': 'ROOT',
                'password_1': password,
                'password_2': password,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='username',
            errors=_('A user with that username already exists.'),
        )

    def test_transform_into_user__duplicated_user_email(self):
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(
            user=user, last_name='Spiegel',
            first_name='Spike',
            email=user.email,  # <==
        )

        url = self._build_as_user_url(contact)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            email_f = response1.context['form'].fields['email']

        self.assertTrue(email_f.required)
        self.assertFalse(email_f.initial)
        self.assertEqual(
            _('BEWARE: the email of the Contact is already used by a user & will be updated.'),
            email_f.help_text,
        )

        # ---
        password = 'sp4c3 c0wg1rL'
        data = {
            'username': 'spike',
            'password_1': password,
            'password_2': password,
            'email': user.email,
        }
        response2 = self.assertPOST200(url, data=data)
        self.assertFormError(
            self.get_form_or_fail(response2),
            field='email',
            errors=_('An active user with the same email address already exists.'),
        )

        # ---
        email = 'spiegel@bebop.mrs'
        self.assertNoFormError(self.client.post(
            url, follow=True, data={**data, 'email': email},
        ))
        self.assertEqual(email, self.refresh(contact).email)

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[{
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        }],
    )
    def test_transform_into_user__password_similarity01(self):
        "Similarity with field in form."
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(
            user=user, last_name='Spiegel',  # first_name=..., email=...,
        )

        username = 'megapilot'
        first_name = 'Spike'
        email = 'spiegel@bebop.mrs'
        url = self._build_as_user_url(contact)

        def assertSimilarityError(password, field_verbose_name):
            response = self.assertPOST200(
                url,
                follow=True,
                data={
                    'username': username,
                    'first_name': first_name,
                    'email': email,

                    'password_1': password,
                    'password_2': password,
                },
            )
            self.assertFormError(
                self.get_form_or_fail(response),
                field='password_2',
                errors=_('The password is too similar to the %(verbose_name)s.') % {
                    'verbose_name': field_verbose_name,
                },
            )

        assertSimilarityError(username,   _('Username'))
        assertSimilarityError(first_name, _('First name'))
        assertSimilarityError(email,      _('Email address'))

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[{
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        }],
    )
    def test_transform_into_user__password_similarity02(self):
        "Similarity with field not in form."
        user = self.login_as_root_and_get()
        first_name = 'Spike'
        email = 'spiegel@bebop.mrs'
        contact = Contact.objects.create(
            user=user, last_name='Spiegel',
            first_name=first_name,
            email=email,
        )

        username = 'megapilot'
        url = self._build_as_user_url(contact)

        def assertSimilarityError(password, field_verbose_name):
            response = self.assertPOST200(
                url,
                follow=True,
                data={
                    'username': username,

                    'password_1': password,
                    'password_2': password,

                    'email': email,
                },
            )
            self.assertFormError(
                self.get_form_or_fail(response),
                field='password_2',
                errors=_('The password is too similar to the %(verbose_name)s.') % {
                    'verbose_name': field_verbose_name,
                },
            )

        assertSimilarityError(username, _('Username'))
        assertSimilarityError(contact.last_name, _('Last name'))
        assertSimilarityError(first_name, _('First name'))
        assertSimilarityError(email,      _('Email address'))
