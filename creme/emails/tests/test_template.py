from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import FakeOrganisation, SetCredentials
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.documents.tests.base import (
    Document,
    _DocumentsTestCase,
    skipIfCustomDocument,
)

from ..bricks import AttachmentsBrick, TemplateHTMLBodyBrick
from .base import EmailTemplate, _EmailsTestCase, skipIfCustomEmailTemplate


@skipIfCustomEmailTemplate
class TemplatesTestCase(BrickTestCaseMixin, _DocumentsTestCase, _EmailsTestCase):
    @staticmethod
    def _build_rm_attachment_url(template):
        return reverse('emails__remove_attachment_from_template', args=(template.id,))

    def test_createview01(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        url = reverse('emails__create_template')
        self.assertGET200(url)

        # ---
        name = 'my_template'
        subject = 'Insert a joke *here*'
        body = 'blablabla {{first_name}}'
        body_html = '<p>blablabla {{last_name}}</p>'
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':      user.pk,
                'name':      name,
                'subject':   subject,
                'body':      body,
                'body_html': body_html,
            },
        )
        self.assertNoFormError(response2)

        template = self.get_object_or_fail(EmailTemplate, name=name)
        self.assertEqual(subject,   template.subject)
        self.assertEqual(body,      template.body)
        self.assertEqual(body_html, template.body_html)
        self.assertFalse([*template.attachments.all()])

        # ----
        response3 = self.assertGET200(template.get_absolute_url())
        self.assertTemplateUsed(response3, 'emails/view_template.html')

        brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=TemplateHTMLBodyBrick,
        )
        iframe_node = brick_node.find('.//iframe')
        self.assertIsNotNone(iframe_node)
        self.assertEqual(
            reverse('creme_core__sanitized_html_field', args=(template.id, 'body_html')),
            iframe_node.attrib.get('src'),
        )

    def test_createview02(self):
        "Attachments."
        # user = self.login()
        user = self.login_as_root_and_get()

        file_obj1 = self.build_filedata('Content #1')
        doc1 = self._create_doc(user=user, title='My doc #1', file_obj=file_obj1)

        file_obj2 = self.build_filedata('Content #2')
        doc2 = self._create_doc(user=user, title='My doc #2', file_obj=file_obj2)

        name = 'My first template'
        subject = 'Very important'
        body = 'Hello {{name}}'
        body_html = '<p>Hi {{name}}</p>'
        response1 = self.client.post(
            reverse('emails__create_template'),
            follow=True,
            data={
                'user':      user.pk,
                'name':      name,
                'subject':   subject,
                'body':      body,
                'body_html': body_html,
                'attachments': self.formfield_value_multi_creator_entity(doc1, doc2),
            },
        )
        self.assertNoFormError(response1)

        template = self.get_object_or_fail(EmailTemplate, name=name)
        self.assertEqual(subject,   template.subject)
        self.assertEqual(body,      template.body)
        self.assertEqual(body_html, template.body_html)
        self.assertCountEqual([doc1, doc2], template.attachments.all())

        # ----
        response2 = self.assertGET200(template.get_absolute_url())

        brick_node = self.get_brick_node(
            self.get_html_tree(response2.content), brick=AttachmentsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2, title='{count} Attachment', plural_title='{count} Attachments',
        )
        self.assertInstanceLink(brick_node, doc1)
        self.assertInstanceLink(brick_node, doc2)

    def test_createview03(self):
        "Validation error."
        # user = self.login()
        user = self.login_as_root_and_get()

        response = self.assertPOST200(
            reverse('emails__create_template'),
            follow=True,
            data={
                'user':      user.pk,
                'name':      'my_template',
                'subject':   'Insert a joke *here*',
                'body':      'blablabla {{unexisting_var}}',
                'body_html': '<p>blablabla</p> {{foobar_var}}',
            },
        )

        form = response.context['form']
        error_msg = _('The following variables are invalid: %(vars)s')
        self.assertFormError(
            form, field='body', errors=error_msg % {'vars': 'unexisting_var'},
        )
        self.assertFormError(
            form, field='body_html', errors=error_msg % {'vars': 'foobar_var'},
        )

    def test_editview01(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        file_obj = self.build_filedata('My Content')
        doc = self._create_doc(user=user, title='My doc #1', file_obj=file_obj)

        name = 'my template'
        subject = 'Insert a joke *here*'
        body = 'blablabla'
        template = EmailTemplate.objects.create(
            user=user, name=name, subject=subject, body=body,
        )

        url = template.get_edit_absolute_url()
        self.assertGET200(url)

        name = name.title()
        subject = subject.title()
        body += ' edited'
        body_html = '<p>blablabla</p>'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':        user.pk,
                'name':        name,
                'subject':     subject,
                'body':        body,
                'body_html':   body_html,
                'attachments': self.formfield_value_multi_creator_entity(doc),
            },
        )
        self.assertNoFormError(response)

        template = self.refresh(template)
        self.assertEqual(name,      template.name)
        self.assertEqual(subject,   template.subject)
        self.assertEqual(body,      template.body)
        self.assertEqual(body_html, template.body_html)
        self.assertListEqual([doc], [*template.attachments.all()])

    def test_editview02(self):
        "Validation errors."
        # user = self.login()
        user = self.login_as_root_and_get()

        template = EmailTemplate.objects.create(
            user=user, name='My template', subject='Hello', body='Complete me',
        )
        response = self.client.post(
            template.get_edit_absolute_url(),
            follow=True,
            data={
                'user':      user.pk,
                'name':      template.name,
                'subject':   template.subject,
                'body':      'blablabla {{unexisting_var}}',
                'body_html': '<p>blablabla</p> {{foobar_var}}',
            },
        )
        form = response.context['form']
        error_msg = _('The following variables are invalid: %(vars)s')
        self.assertFormError(
            form, field='body', errors=error_msg % {'vars': 'unexisting_var'},
        )
        self.assertFormError(
            form, field='body_html', errors=error_msg % {'vars': 'foobar_var'},
        )

    def test_listview(self):
        # self.login()
        self.login_as_root()
        response = self.assertGET200(EmailTemplate.get_lv_absolute_url())

        with self.assertNoException():
            response.context['page_obj']  # NOQA

    @skipIfCustomDocument
    def test_add_attachments01(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        template = EmailTemplate.objects.create(
            user=user, name='My template',
            subject='Insert a joke *here*', body='blablabla',
        )

        file_obj1 = self.build_filedata('Content #1')
        doc1 = self._create_doc(user=user, title='My doc #1', file_obj=file_obj1)

        file_obj2 = self.build_filedata('Content #2')
        doc2 = self._create_doc(user=user, title='My doc #2', file_obj=file_obj2)

        url = reverse('emails__add_attachments_to_template', args=(template.id,))

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('New attachments for «{entity}»').format(entity=template),
            context.get('title')
        )
        self.assertEqual(_('Add the attachments'), context.get('submit_label'))

        response = self.client.post(
            url,
            data={'attachments': self.formfield_value_multi_creator_entity(doc1, doc2)},
        )
        self.assertNoFormError(response)
        self.assertCountEqual([doc1, doc2], template.attachments.all())

    def test_add_attachments02(self):
        # user = self.login()
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')
        self.assertGET404(reverse('emails__add_attachments_to_template', args=(orga.id,)))

    @skipIfCustomDocument
    def test_delete_attachments01(self):
        # user = self.login(
        user = self.login_as_emails_user(
            # is_superuser=False,
            allowed_apps=['documents'],
            creatable_models=[Document],
        )
        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        file_obj1 = self.build_filedata('Content #1')
        doc1 = self._create_doc('My doc #1', file_obj=file_obj1, user=user)

        file_obj2 = self.build_filedata('Content #2')
        doc2 = self._create_doc('My doc #2', file_obj=file_obj2, user=user)

        template = EmailTemplate.objects.create(
            user=user, name='My template',
            subject='Insert a joke *here*', body='blablabla',
        )
        template.attachments.set([doc1, doc2])

        url = self._build_rm_attachment_url(template)
        data = {'id': doc1.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data, follow=True)
        self.assertEqual([doc2], [*template.attachments.all()])

    @skipIfCustomDocument
    def test_delete_attachments02(self):
        "Not allowed to change the template."
        # user = self.login(
        user = self.login_as_emails_user(
            # is_superuser=False,
            allowed_apps=['documents'],
            creatable_models=[Document],
        )
        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,  # Not CHANGE
            set_type=SetCredentials.ESET_ALL,
        )

        file_obj = self.build_filedata('Content #1')
        doc = self._create_doc('My doc #1', file_obj=file_obj, user=user)

        template = EmailTemplate.objects.create(
            user=user, name='My template',
            subject='Insert a joke *here*', body='blablabla',
        )
        template.attachments.add(doc)

        self.assertPOST403(
            self._build_rm_attachment_url(template), data={'id': doc.id},
        )
