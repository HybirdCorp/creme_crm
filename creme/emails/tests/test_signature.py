# -*- coding: utf-8 -*-

from django.urls import reverse
from django.utils.translation import gettext as _

from ..models import EmailSignature
from .base import EmailTemplate, _EmailsTestCase, skipIfCustomEmailTemplate


class SignaturesTestCase(_EmailsTestCase):
    def test_create(self):
        self.login(is_superuser=False)
        self.assertFalse(EmailSignature.objects.count())

        url = reverse('emails__create_signature')
        context = self.assertGET200(url).context
        self.assertEqual(EmailSignature.creation_label, context.get('title'))
        self.assertEqual(EmailSignature.save_label,     context.get('submit_label'))

        name = 'Polite signature'
        body = 'I love you'
        self.assertNoFormError(self.client.post(url, data={'name': name, 'body': body}))

        signature = self.get_object_or_fail(EmailSignature, name=name)
        self.assertEqual(body,      signature.body)
        self.assertEqual(self.user, signature.user)
        self.assertEqual(0,         signature.images.count())

    def test_create_not_allowed(self):
        self.login(is_superuser=False, allowed_apps=['persons'])
        self.assertGET403(reverse('emails__create_signature'))

    # TODO: create with images....

    def test_edit01(self):
        user = self.login()

        name = 'Funny signature'
        body = 'I love you... not'
        signature = EmailSignature.objects.create(user=user, name=name, body=body)

        url = signature.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Edit «{object}»').format(object=signature),
            response.context.get('title')
        )

        # ---
        name += '_edited'
        body += '_edited'
        self.assertNoFormError(self.client.post(url, data={'name': name, 'body': body}))

        signature = self.refresh(signature)
        self.assertEqual(name, signature.name)
        self.assertEqual(body, signature.body)
        self.assertEqual(user, signature.user)
        self.assertFalse(signature.images.exists())

    # TODO: edit with images....

    def test_edit02(self):
        "'perm' error."
        self.login(is_superuser=False)

        signature = EmailSignature.objects.create(
            user=self.other_user, name='Funny signature', body='I love you... not',
        )
        self.assertGET403(signature.get_edit_absolute_url())

    def test_edit03(self):
        "Superuser can edit all signatures."
        self.login()

        signature = EmailSignature.objects.create(
            user=self.other_user, name='Funny signature', body='I love you... not',
        )
        self.assertGET200(signature.get_edit_absolute_url())

    def _delete(self, signature):
        return self.client.post(
            reverse('emails__delete_signature'), data={'id': signature.id}, follow=True,
        )

    def test_delete01(self):
        user = self.login()

        signature = EmailSignature.objects.create(
            user=user, name="Spike's one", body='See U space cowboy',
        )
        self.assertEqual(200, self._delete(signature).status_code)
        self.assertDoesNotExist(signature)

    def test_delete02(self):
        "'perm' error."
        self.login(is_superuser=False)

        signature = EmailSignature.objects.create(
            user=self.other_user, name="Spike's one", body='See U space cowboy',
        )
        self.assertEqual(403, self._delete(signature).status_code)
        self.assertEqual(1, EmailSignature.objects.filter(pk=signature.id).count())

    @skipIfCustomEmailTemplate
    def test_delete03(self):
        "Dependencies problem."
        user = self.login()

        signature = EmailSignature.objects.create(
            user=user, name="Spike's one", body='See U space cowboy',
        )
        template = EmailTemplate.objects.create(
            user=user, name='name', signature=signature,
            subject='Hello', body='Do you know the real folk blues ?',
        )
        email = self._create_email(signature=signature)

        self.assertEqual(200, self._delete(signature).status_code)
        self.assertDoesNotExist(signature)

        template = self.assertStillExists(template)
        self.assertIsNone(template.signature)

        email = self.assertStillExists(email)
        self.assertIsNone(email.signature)
