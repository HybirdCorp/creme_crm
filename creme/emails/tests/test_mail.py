from datetime import timedelta
from functools import partial
from os.path import basename
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend
from django.forms import IntegerField
from django.urls import reverse
from django.utils.html import escape
from django.utils.timezone import now
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core import workflows
from creme.creme_core.core.entity_filter import condition_handler
# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.core.workflow import WorkflowConditions, WorkflowEngine
from creme.creme_core.forms.widgets import Label
from creme.creme_core.gui import actions
from creme.creme_core.models import (
    CremePropertyType,
    CustomField,
    FakeInvoice,
    FieldsConfig,
    Job,
    RelationType,
    Workflow,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.documents.models import FolderCategory
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .. import bricks
from ..actions import BulkEntityEmailResendAction, EntityEmailResendAction
from ..constants import (
    REL_OBJ_MAIL_RECEIVED,
    REL_OBJ_MAIL_SENT,
    REL_OBJ_RELATED_TO,
    REL_SUB_MAIL_RECEIVED,
    REL_SUB_MAIL_SENT,
    REL_SUB_RELATED_TO,
)
from ..creme_jobs import entity_emails_send_type
from ..models import EmailSignature
from .base import (
    Contact,
    Document,
    EmailTemplate,
    EntityEmail,
    Folder,
    MailingList,
    Organisation,
    _EmailsTestCase,
    skipIfCustomEmailTemplate,
    skipIfCustomEntityEmail,
)


@skipIfCustomEntityEmail
class EntityEmailTestCase(BrickTestCaseMixin, _EmailsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original_send_messages = EmailBackend.send_messages

    def tearDown(self):
        super().tearDown()
        EmailBackend.send_messages = self.original_send_messages

    def login_as_emails_user(self, *,
                             allowed_apps=('persons', 'emails'),
                             creatable_models=(Contact, Organisation, EntityEmail),
                             **kwargs):
        return super().login_as_standard(
            allowed_apps=allowed_apps,
            creatable_models=creatable_models,
            **kwargs,
        )

    @staticmethod
    def _build_send_from_template_url(entity):
        return reverse('emails__create_email_from_template', args=(entity.id,))

    @staticmethod
    def _build_link_emails_url(entity):
        return reverse('emails__link_emails', args=(entity.id,))

    def _get_job(self):
        return self.get_object_or_fail(Job, type_id=entity_emails_send_type.id)

    def _send_mails(self, job=None):
        # Empty the Queue to avoid log messages
        WorkflowEngine.get_current()._queue.pickup()

        entity_emails_send_type.execute(job or self._get_job())

    @skipIfCustomContact
    def test_createview(self):
        user = self.login_as_root_and_get()

        queue = get_queue()
        queue.clear()

        recipient = 'vincent.law@immigrates.rmd'
        contact = Contact.objects.create(
            user=user,
            first_name='Vincent', last_name='Law',
            email=recipient,
        )
        url = self._build_create_entitymail_url(contact)

        context = self.assertGET200(url).context
        self.assertEqual(
            _('Sending an email to «{entity}»').format(entity=contact),
            context.get('title'),
        )
        self.assertEqual(EntityEmail.sending_label, context.get('submit_label'))

        with self.assertNoException():
            c_recipients = context['form'].fields['c_recipients']

        self.assertListEqual([contact.id], c_recipients.initial)

        # ---
        sender = user.linked_contact.email
        body = 'Freeze !'
        body_html = '<p>Freeze !</p>'
        subject = 'Under arrest'
        response2 = self.client.post(
            url,
            data={
                'user':         user.id,
                'sender':       sender,
                'c_recipients': self.formfield_value_multi_creator_entity(contact),
                'subject':      subject,
                'body':         body,
                'body_html':    body_html,
            },
        )
        self.assertNoFormError(response2)

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=recipient)
        self.assertEqual(user,             email.user)
        self.assertEqual(subject,          email.subject)
        self.assertEqual(body,             email.body)
        self.assertEqual(body_html,        email.body_html)
        self.assertEqual(EntityEmail.Status.SENT, email.status)
        self.assertIs(email.synchronised, False)

        self.assertHaveRelation(subject=email, type=REL_SUB_MAIL_SENT, object=user.linked_contact)
        self.assertHaveRelation(subject=email, type=REL_SUB_MAIL_RECEIVED, object=contact)
        self.assertHaveNoRelation(subject=email, type=REL_SUB_RELATED_TO, object=contact)

        # ---
        response3 = self.assertGET200(reverse('emails__view_email', args=(email.id,)))
        self.assertTemplateUsed(response3, 'emails/view_entity_mail.html')

        body_brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=bricks.EmailHTMLBodyBrick,
        )
        iframe_node1 = body_brick_node.find('.//iframe')
        self.assertIsNotNone(iframe_node1)
        self.assertEqual(
            reverse('creme_core__sanitized_html_field', args=(email.id, 'body_html')),
            iframe_node1.attrib.get('src'),
        )

        # ---
        response4 = self.assertGET200(reverse('emails__view_email_popup', args=(email.id,)))
        self.assertTemplateUsed(response4, 'creme_core/generics/detail-popup.html')

        popup_brick_node = self.get_brick_node(
            self.get_html_tree(response4.content), brick=bricks.MailPopupBrick,
        )
        iframe_node2 = popup_brick_node.find('.//iframe')
        self.assertIsNotNone(iframe_node2)
        self.assertEqual(
            reverse('creme_core__sanitized_html_field', args=(email.id, 'body_html')),
            iframe_node2.attrib.get('src'),
        )

        # ---
        message = self.get_alone_element(mail.outbox)
        self.assertEqual(subject,     message.subject)
        self.assertEqual('',          message.body)
        self.assertEqual([recipient], message.recipients())
        self.assertEqual(sender,      message.from_email)
        # TODO: test better
        self.assertIn('Message-ID', message.extra_headers)

        self.assertBodiesEqual(message, body=body, body_html=body_html)
        self.assertEqual(1, len(message.attachments))

        self.assertEqual([], queue.refreshed_jobs)

    @skipIfCustomContact
    def test_createview__related_entity(self):
        "Entity is not used as recipient => linked with RelationType REL_SUB_RELATED_TO."
        user = self.login_as_root_and_get()
        entity = MailingList.objects.create(user=user, name='ML1')
        contact = Contact.objects.create(
            user=user, first_name='Vincent', last_name='Law', email='vlaw@immigrates.rmd',
        )

        sender = user.linked_contact.email
        self.assertNoFormError(self.client.post(
            self._build_create_entitymail_url(entity),
            data={
                'user':         user.id,
                'sender':       sender,
                'c_recipients': self.formfield_value_multi_creator_entity(contact),
                'subject':      'Ola',
                'body':         'Freeze!',
            },
        ))

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=contact.email)
        self.assertHaveRelation(subject=email, type=REL_SUB_MAIL_SENT, object=user.linked_contact)
        self.assertHaveRelation(subject=email, type=REL_SUB_MAIL_RECEIVED, object=contact)
        self.assertHaveRelation(subject=email, type=REL_SUB_RELATED_TO, object=entity)

    @skipIfCustomOrganisation
    def test_createview__attachments(self):
        user = self.login_as_root_and_get()

        recipient = 'contact@venusgate.jp'
        orga = Organisation.objects.create(user=user, name='Venus gate', email=recipient)
        url = self._build_create_entitymail_url(orga)

        response = self.assertGET200(url)

        with self.assertNoException():
            o_recipients = response.context['form'].fields['o_recipients']

        self.assertEqual([orga.id], o_recipients.initial)

        folder = Folder.objects.create(
            user=user, title='Test folder', parent_folder=None,
            category=FolderCategory.objects.create(name='Test category'),
        )

        def create_doc(title, content):
            tmpfile = NamedTemporaryFile(suffix=".txt")
            tmpfile.write(content)
            tmpfile.flush()
            tmpfile.file.seek(0)

            response = self.client.post(
                reverse('documents__create_document'), follow=True,
                data={
                    'user':          user.id,
                    'title':         title,
                    'description':   'Attachment file',
                    'filedata':      tmpfile,
                    'linked_folder': folder.id,
                },
            )
            self.assertNoFormError(response)

            return self.get_object_or_fail(Document, title=title)

        content1 = b"Hey I'm the content"
        content2 = b'Another content'
        doc1 = create_doc('Doc01', content1)
        doc2 = create_doc('Doc02', content2)

        sender = 're-l.mayer@rpd.rmd'
        signature = EmailSignature.objects.create(
            user=user,
            name="Re-l's signature",
            body='I love you... not',
        )
        response = self.client.post(
            url,
            data={
                'user':         user.id,
                'sender':       sender,
                'o_recipients': self.formfield_value_multi_creator_entity(orga),
                'subject':      'Cryogenisation',
                'body':         'I want to be freezed !',
                'body_html':    '<p>I want to be freezed !</p>',
                'signature':    signature.id,
                'attachments':  self.formfield_value_multi_creator_entity(doc1, doc2),
                'send_me':      True,
            },
        )
        self.assertNoFormError(response)

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=recipient)
        self.assertEqual(signature, email.signature)

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=sender)
        self.assertEqual(signature, email.signature)

        messages = mail.outbox
        self.assertEqual(2, len(messages))
        self.assertEqual([sender], messages[0].recipients())

        message = messages[1]
        self.assertListEqual([recipient], message.recipients())
        self.assertListEqual(
            [
                (basename(doc1.filedata.name), content1.decode(), 'text/plain'),
                (basename(doc2.filedata.name), content2.decode(), 'text/plain'),
            ],
            message.attachments[1:],  # 0 is for bodies
        )

    @skipIfCustomContact
    def test_createview__required_customfield(self):
        user = self.login_as_root_and_get()

        create_cf = partial(CustomField.objects.create, content_type=EntityEmail)
        cf1 = create_cf(field_type=CustomField.STR, name='Comment')
        cf2 = create_cf(field_type=CustomField.INT, name='Business ID', is_required=True)

        recipient = 'vincent.law@immigrates.rmd'
        contact = Contact.objects.create(
            user=user,
            first_name='Vincent', last_name='Law',
            email=recipient,
        )
        response = self.assertGET200(self._build_create_entitymail_url(contact))

        fields = response.context['form'].fields
        self.assertNotIn(f'custom_field-{cf1.id}', fields)

        cf2_f = fields.get(f'custom_field-{cf2.id}')
        self.assertIsInstance(cf2_f, IntegerField)
        self.assertTrue(cf2_f.required)

    @skipIfCustomContact
    def test_createview__empty_body01(self):
        "HTML body is empty => automatically filled from body."
        user = self.login_as_root_and_get()

        recipient = 'vincent.law@immigrates.rmd'
        contact = Contact.objects.create(
            user=user,
            first_name='Vincent', last_name='Law',
            email=recipient,
        )
        url = self._build_create_entitymail_url(contact)
        response1 = self.assertGET200(url)
        with self.assertNoException():
            fields = response1.context['form'].fields
            subject_f = fields['subject']
            body_f = fields['body']
            html_f = fields['body_html']

        self.assertTrue(subject_f.required)
        self.assertFalse(body_f.required)
        self.assertFalse(html_f.required)

        sender = user.linked_contact.email
        body = 'Fresh & tasty!\nTry it now!'
        response2 = self.client.post(
            url,
            data={
                'user':         user.id,
                'sender':       sender,
                'c_recipients': self.formfield_value_multi_creator_entity(contact),
                'subject':      'New product',
                'body':         body,
                'body_html':    '    ',  # Considered as empty once stripped
            },
        )
        self.assertNoFormError(response2)

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=recipient)
        self.assertEqual(body, email.body)
        self.assertEqual(
            '<html><body><code><p>Fresh &amp; tasty!<br>Try it now!</p></code></body></html>',
            email.body_html,
        )

    @skipIfCustomContact
    def test_createview__empty_body02(self):
        "Body is empty => automatically filled from HTML body."
        user = self.login_as_root_and_get()

        recipient = 'vincent.law@immigrates.rmd'
        contact = Contact.objects.create(
            user=user,
            first_name='Vincent', last_name='Law',
            email=recipient,
        )
        sender = user.linked_contact.email
        response = self.client.post(
            self._build_create_entitymail_url(contact),
            data={
                'user':         user.id,
                'sender':       sender,
                'c_recipients': self.formfield_value_multi_creator_entity(contact),
                'subject':      'New slurm',
                'body':         '    ',  # Considered as empty once stripped
                'body_html': '''
<html>
<head></head>
<body style="margin:0px; padding:0px;">
<table width="640" cellpadding="0" cellspacing="0" border="0">
<tbody>
<tr>
<td valign="top" align="center"></td>
<td width="320"><p style="text-align: justify;">
Taste our <span style="text-decoration:underline;">new recipe</span> which is 72%
better &amp; lighter than the previous one.
</p></td>
<td valign="top" align="center">Visit our <a href="https://slurm.com">site</a> !</td>
</body>
</html>
'''
            },
        )
        self.assertNoFormError(response)

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=recipient)
        self.assertEqual(
            'Taste our new recipe which is 72%\n'
            'better & lighter than the previous one.\n'
            '\n'
            'Visit our site !',
            # 'Visit our site (https://slurm.com) !',  TODO ??
            email.body,
        )

    @skipIfCustomContact
    def test_createview__empty_body03(self):
        "Both bodies are empty => error."
        user = self.login_as_root_and_get()

        recipient = 'vincent.law@immigrates.rmd'
        contact = Contact.objects.create(
            user=user,
            first_name='Vincent', last_name='Law',
            email=recipient,
        )
        response = self.assertPOST200(
            self._build_create_entitymail_url(contact),
            data={
                'user':         user.id,
                'sender':       user.linked_contact.email,
                'c_recipients': self.formfield_value_multi_creator_entity(contact),

                'subject': 'New slurm',

                'body':      '  ',
                'body_html': '    ',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_('Both bodies cannot be empty at the same time.'),
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_createview__error_invalid_address(self):
        "Invalid email address."
        user = self.login_as_root_and_get()

        create_contact = partial(Contact.objects.create, user=user)
        contact01 = create_contact(
            first_name='Vincent', last_name='Law',
            email='vincent.law@immigrates',  # Invalid
        )
        contact02 = create_contact(
            first_name='Pino', last_name='AutoReiv',
            email='pino@autoreivs.rmd',  # OK
        )

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='Venus gate', email='contact/venusgate.jp')  # Invalid
        orga02 = create_orga(name='Nerv',       email='contact@nerv.jp')  # Ok

        response = self.assertPOST200(
            self._build_create_entitymail_url(contact01),
            data={
                'user':         user.id,
                'sender':       user.linked_contact.email,
                'c_recipients': self.formfield_value_multi_creator_entity(contact01, contact02),
                'o_recipients': self.formfield_value_multi_creator_entity(orga01, orga02),
                'subject':      'Under arrest',
                'body':         'Freeze !',
                'body_html':    '<p>Freeze !</p>',
            },
        )
        form = self.get_form_or_fail(response)
        self.assertFormError(
            form,
            field='c_recipients',
            errors=_('The email address for {} is invalid').format(contact01),
        )
        self.assertFormError(
            form,
            field='o_recipients',
            errors=_('The email address for {} is invalid').format(orga01),
        )

    @skipIfCustomContact
    def test_createview__no_address01(self):
        "Related contact has no emails address."
        user = self.login_as_root_and_get()

        contact = Contact.objects.create(user=user, first_name='Vincent', last_name='Law')
        response = self.assertGET200(self._build_create_entitymail_url(contact))

        with self.assertNoException():
            c_recipients = response.context['form'].fields['c_recipients']

        self.assertIsNone(c_recipients.initial)
        self.assertEqual(
            _('Beware: the contact «{}» has no email address!').format(contact),
            c_recipients.help_text,
        )

    @skipIfCustomOrganisation
    def test_createview__no_address02(self):
        "Related organisation has no email address."
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='Venus gate')
        response = self.assertGET200(self._build_create_entitymail_url(orga))

        with self.assertNoException():
            o_recipients = response.context['form'].fields['o_recipients']

        self.assertIsNone(o_recipients.initial)
        self.assertEqual(
            _('Beware: the organisation «{}» has no email address!').format(orga),
            o_recipients.help_text,
        )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_createview__no_link_perm(self):
        "Credentials problem."
        user = self.login_as_emails_user()
        other_user = self.get_root_user()
        self.add_credentials(user.role, all='!LINK', own='*')

        create_contact = Contact.objects.create
        contact01 = create_contact(
            user=other_user,
            first_name='Vincent',
            last_name='Law',
            email='vincent.law@immigrates.rmd',
        )
        contact02 = create_contact(
            user=user,
            first_name='Pino',
            last_name='AutoReiv',
            email='pino@autoreivs.rmd',
        )

        create_orga = Organisation.objects.create
        orga01 = create_orga(
            user=other_user, name='Venus gate', email='contact@venusgate.jp',
        )
        orga02 = create_orga(user=user, name='Nerv', email='contact@nerv.jp')

        self.assertTrue(user.has_perm_to_view(contact01))
        self.assertFalse(user.has_perm_to_link(contact01))
        self.assertTrue(user.has_perm_to_view(contact02))
        self.assertTrue(user.has_perm_to_link(contact02))

        def post(contact):
            return self.client.post(
                self._build_create_entitymail_url(contact),
                data={
                    'user': user.id,
                    'sender': user.linked_contact.email,

                    'c_recipients': self.formfield_value_multi_creator_entity(
                        contact01, contact02,
                    ),
                    'o_recipients': self.formfield_value_multi_creator_entity(
                        orga01, orga02,
                    ),
                    'subject': 'Under arrest',
                    'body': 'Freeze !',
                    'body_html': '<p>Freeze !</p>',
                },
            )

        self.assertEqual(403, post(contact01).status_code)

        response2 = post(contact02)
        self.assertEqual(200, response2.status_code)

        form2 = response2.context['form']
        self.assertFormError(
            form2,
            field='c_recipients',
            errors=_('Some entities are not linkable: {}').format(contact01),
        )
        self.assertFormError(
            form2,
            field='o_recipients',
            errors=_('Some entities are not linkable: {}').format(orga01),
        )

    def test_createview__no_recipient(self):
        user = self.login_as_root_and_get()
        c = Contact.objects.create(user=user, first_name='Vincent', last_name='Law')
        response = self.assertPOST200(
            self._build_create_entitymail_url(c),
            data={
                'user':         user.id,
                'sender':       user.linked_contact.email,
                'c_recipients': '[]',
                'o_recipients': '[]',
                'subject':      'Under arrest',
                'body':         'Freeze !',
                'body_html':    '<p>Freeze !</p>',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_('Select at least a Contact or an Organisation'),
        )

    @skipIfCustomContact
    def test_createview__fieldsconfig01(self):
        "FieldsConfig: Contact.email is hidden."
        user = self.login_as_root_and_get()
        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )

        c = Contact.objects.create(user=user, first_name='Vincent', last_name='Law')

        url = self._build_create_entitymail_url(c)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            recip_field = response1.context['form'].fields['c_recipients']

        self.assertIsInstance(recip_field.widget, Label)
        self.assertEqual(
            _(
                'Beware: the field «Email address» is hidden; '
                'please contact your administrator.'
            ),
            recip_field.initial,
        )

        # POSt ---
        response2 = self.assertPOST200(
            url,
            data={
                'user':         user.id,
                'sender':       user.linked_contact.email,
                # Should not be used
                'c_recipients': self.formfield_value_multi_creator_entity(c),
                'subject':      'Under arrest',
                'body':         'Freeze !',
                'body_html':    '<p>Freeze !</p>',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response2),
            field=None,
            errors=_('Select at least a Contact or an Organisation'),
        )

    @skipIfCustomOrganisation
    def test_createview__fieldsconfig02(self):
        "FieldsConfig: Organisation.email is hidden."
        user = self.login_as_root_and_get()
        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )

        orga = Organisation.objects.create(user=user, name='Venus gate')

        url = self._build_create_entitymail_url(orga)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            recip_field = response1.context['form'].fields['o_recipients']

        self.assertIsInstance(recip_field.widget, Label)
        self.assertEqual(
            _(
                'Beware: the field «Email address» is hidden; '
                'please contact your administrator.'
            ),
            recip_field.initial,
        )

        # POST ---
        response2 = self.assertPOST200(
            url,
            data={
                'user':         user.id,
                'sender':       user.linked_contact.email,
                # Should not be used
                'o_recipients': self.formfield_value_multi_creator_entity(orga),
                'subject':      'Under arrest',
                'body':         'Freeze !',
                'body_html':    '<p>Freeze !</p>',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response2),
            field=None,
            errors=_('Select at least a Contact or an Organisation'),
        )

    @skipIfCustomContact
    def test_createview__sending_error(self):
        "Mail sending error."
        user = self.login_as_root_and_get()

        queue = get_queue()
        queue.clear()

        self.send_messages_called = False

        def send_messages(this, messages):
            self.send_messages_called = True
            raise Exception('Sent error')

        EmailBackend.send_messages = send_messages

        recipient = 'vincent.law@immigrates.rmd'
        contact = Contact.objects.create(
            user=user, first_name='Vincent', last_name='Law', email=recipient,
        )

        sender = user.linked_contact.email
        response = self.client.post(
            self._build_create_entitymail_url(contact),
            data={
                'user':         user.id,
                'sender':       sender,
                'c_recipients': self.formfield_value_multi_creator_entity(contact),
                'subject':      'Under arrest',
                'body':         'Freeze !',
                'body_html':    '<p>Freeze !</p>',
            },
        )
        self.assertNoFormError(response)

        email = self.get_object_or_fail(EntityEmail, sender=sender, recipient=recipient)
        self.assertEqual(EntityEmail.Status.SENDING_ERROR, email.status)

        self.assertTrue(queue.refreshed_jobs)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_createview__no_creation_perm(self):
        "No creation credentials."
        user = self.login_as_emails_user(
            creatable_models=(Contact, Organisation)  # No EntityEmail
        )
        self.add_credentials(user.role, all='*')

        contact02 = Contact.objects.create(user=user, first_name='Pino', last_name='AutoReiv')
        self.assertGET403(self._build_create_entitymail_url(contact02))

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_createview__empty_email(self):
        "Empty email address."
        user = self.login_as_root_and_get()

        create_contact = partial(Contact.objects.create, user=user)
        contact01 = create_contact(first_name='Vincent', last_name='Law', email='')
        contact02 = create_contact(
            first_name='Pino', last_name='AutoReiv', email='pino@autoreivs.rmd',
        )

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='Venus gate', email='')
        orga02 = create_orga(name='Nerv',       email='contact@nerv.jp')  # Ok

        response = self.assertPOST200(
            self._build_create_entitymail_url(contact01),
            data={
                'user':         user.id,
                'sender':       user.linked_contact.email,
                'c_recipients': self.formfield_value_multi_creator_entity(contact01, contact02),
                'o_recipients': self.formfield_value_multi_creator_entity(orga01, orga02),
                'subject':      'Under arrest',
                'body':         'Freeze !',
                'body_html':    '<p>Freeze !</p>',
            },
        )
        form = self.get_form_or_fail(response)
        msg = _('«%(entity)s» violates the constraints.')
        self.assertFormError(
            form, field='c_recipients', errors=msg % {'entity': contact01},
        )
        self.assertFormError(
            form, field='o_recipients', errors=msg % {'entity': orga01},
        )

    @parameterized.expand([REL_SUB_MAIL_SENT, REL_SUB_MAIL_RECEIVED, REL_SUB_RELATED_TO])
    @skipIfCustomContact
    def test_createview__disabled_rtype(self, rtype_id):
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(
            user=user,
            first_name='Vincent', last_name='Law',
            email='vincent.law@immigrates.rmd',
        )

        rtype = self.get_object_or_fail(RelationType, id=rtype_id)
        rtype.enabled = False
        rtype.save()

        try:
            self.assertGET409(self._build_create_entitymail_url(contact))
        finally:
            rtype.enabled = True
            rtype.save()

    def test_createview__is_staff(self):
        self.login_as_super(is_staff=True)
        contact = Contact.objects.create(
            user=self.get_root_user(),
            first_name='Vincent', last_name='Law',
            email='vincent.law@immigrates.rmd',
        )

        self.assertGET409(self._build_create_entitymail_url(contact))

    @skipIfCustomEmailTemplate
    @skipIfCustomContact
    def test_create_from_template01(self):
        user = self.login_as_root_and_get()

        body_format      = 'Hi {} {}, nice to meet you !'.format
        body_html_format = 'Hi <strong>{} {}</strong>, nice to meet you !'.format

        subject = 'I am da subject'
        signature = EmailSignature.objects.create(
            user=user, name="Re-l's signature", body='I love you... not',
        )
        template = EmailTemplate.objects.create(
            user=user, name='My template', subject=subject,
            body=body_format('{{first_name}}', '{{last_name}}'),
            body_html=body_html_format('{{first_name}}', '{{last_name}}'),
            signature=signature,
        )

        recipient = 'vincent.law@city.mosk'
        first_name = 'Vincent'
        last_name = 'Law'
        contact = Contact.objects.create(
            user=user, first_name=first_name, last_name=last_name, email=recipient,
        )

        url = self._build_send_from_template_url(contact)
        response = self.assertGET200(url)
        self.assertTemplateUsed(
            response,
            'creme_core/generics/blockform/add-wizard-popup.html',
        )

        context = response.context
        title = _('Sending an email to «{entity}»').format(entity=contact)
        self.assertEqual(
            title,
            context.get('title')
        )
        self.assertEqual(_('Select this template'), context.get('submit_label'))

        # ---
        step_key = 'entity_email_wizard-current_step'
        response = self.client.post(
            url,
            data={
                step_key: '0',
                '0-template': template.id,
            },
        )
        self.assertNoFormError(response)

        context = response.context
        self.assertEqual(title, context.get('title'))
        self.assertEqual(_('Send the email'), context.get('submit_label'))

        with self.assertNoException():
            form = context['form']
            fields = form.fields
            fields['subject']  # NOQA
            fields['body']  # NOQA
            fields['body_html']  # NOQA
            fields['signature']  # NOQA
            fields['attachments']  # NOQA

        ini_get = form.initial.get
        self.assertEqual(subject, ini_get('subject'))
        self.assertEqual(
            body_format(contact.first_name, contact.last_name),
            ini_get('body'),
        )
        self.assertEqual(
            body_html_format(contact.first_name, contact.last_name),
            ini_get('body_html'),
        )
        self.assertEqual(signature.id, ini_get('signature'))
        # self.assertEqual(attachments,  ini_get('attachments')) #TODO

        response = self.client.post(
            url,
            data={
                step_key: '1',
                '1-step': 2,
                '1-user': user.id,
                '1-sender': user.linked_contact.email,
                '1-c_recipients': self.formfield_value_multi_creator_entity(contact),
                '1-subject': subject,
                '1-body': ini_get('body'),
                '1-body_html': ini_get('body_html'),
                '1-signature': signature.id,
            },
        )
        self.assertNoFormError(response)
        email = self.get_object_or_fail(EntityEmail, recipient=recipient)
        self.assertEqual(user.linked_contact.email, email.sender)
        self.assertEqual(ini_get('body'),           email.body)

    @skipIfCustomContact
    def test_create_from_template02(self):
        "Not super-user."
        user = self.login_as_emails_user()
        self.add_credentials(user.role, all=['VIEW', 'LINK'])

        contact = Contact.objects.create(
            user=user, first_name='Vincent', last_name='Law',
            email='vincent.law@city.mosk',
        )
        self.assertGET200(self._build_send_from_template_url(contact))

    @skipIfCustomContact
    def test_create_from_template03(self):
        "Creation permission needed."
        user = self.login_as_emails_user(creatable_models=[])
        self.add_credentials(user.role, all=['VIEW', 'LINK'])

        contact = Contact.objects.create(
            user=user, first_name='Vincent', last_name='Law',
            email='vincent.law@city.mosk',
        )
        self.assertGET403(self._build_send_from_template_url(contact))

    @skipIfCustomContact
    def test_create_from_template04(self):
        "LINK permission needed."
        user = self.login_as_emails_user()
        self.add_credentials(user.role, all=['VIEW'])  # 'LINK'

        contact = Contact.objects.create(
            user=user, first_name='Vincent', last_name='Law',
            email='vincent.law@city.mosk',
        )
        self.assertGET403(self._build_send_from_template_url(contact))

    @parameterized.expand([REL_SUB_MAIL_SENT, REL_SUB_MAIL_RECEIVED])
    @skipIfCustomContact
    def test_create_from_template_disabled_rtype(self, rtype_id):
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(
            user=user,
            first_name='Vincent', last_name='Law',
            email='vincent.law@immigrates.rmd',
        )

        rtype = self.get_object_or_fail(RelationType, id=rtype_id)
        rtype.enabled = False
        rtype.save()

        try:
            self.assertGET409(self._build_send_from_template_url(contact))
        finally:
            rtype.enabled = True
            rtype.save()

    def test_link_to_emails01(self):
        "Contact."
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(user=user, first_name='Vincent', last_name='Law')
        email1 = self._create_email(user=user)
        email2 = self._create_email(user=user)

        url = self._build_link_emails_url(contact)
        response1 = self.assertGET200(url)

        context = response1.context
        self.assertEqual(
            _('Link «{entity}» to emails').format(entity=contact),
            context.get('title'),
        )
        self.assertEqual(_('Save the relationships'), context.get('submit_label'))

        with self.assertNoException():
            allowed_rtypes = context['form'].fields['relations'].allowed_rtypes

        self.assertSetEqual(
            {REL_OBJ_MAIL_SENT, REL_OBJ_MAIL_RECEIVED, REL_OBJ_RELATED_TO},
            {rtype.id for rtype in allowed_rtypes},
        )

        # ---
        response2 = self.client.post(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (REL_OBJ_MAIL_RECEIVED, email1),
                    (REL_OBJ_RELATED_TO,    email2),
                ),
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(2, contact.relations.count())
        self.assertHaveRelation(subject=contact, type=REL_OBJ_MAIL_RECEIVED, object=email1)
        self.assertHaveRelation(subject=contact, type=REL_OBJ_RELATED_TO,    object=email2)

    def test_link_to_emails02(self):
        "Invoice => only one relation type proposed."
        user = self.login_as_root_and_get()
        invoice = FakeInvoice.objects.create(user=user, name='Swords & shields')
        response = self.assertGET200(self._build_link_emails_url(invoice))

        with self.assertNoException():
            allowed_rtypes = response.context['form'].fields['relations'].allowed_rtypes

        self.assertListEqual(
            [REL_OBJ_RELATED_TO],
            [rtype.id for rtype in allowed_rtypes],
        )

    def test_link_to_emails03(self):
        "Disabled relation types."
        user = self.login_as_root_and_get()

        url = self._build_link_emails_url(
            Contact.objects.create(user=user, first_name='Vincent', last_name='Law')
        )
        disabled_rtypes = []

        def disable(rtype_id):
            rtype = self.get_object_or_fail(RelationType, id=rtype_id)
            rtype.enabled = False
            rtype.save()
            disabled_rtypes.append(rtype)

        try:
            self.assertGET200(url)

            disable(REL_OBJ_MAIL_SENT)
            self.assertGET200(url)

            disable(REL_OBJ_MAIL_RECEIVED)
            self.assertGET200(url)

            disable(REL_OBJ_RELATED_TO)
            self.assertGET409(url)
        finally:
            for rtype in disabled_rtypes:
                rtype.enabled = True
                rtype.save()

    def test_link_to_emails04(self):
        "Incompatible relation types (property types constraints)."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is important')

        url = self._build_link_emails_url(
            Contact.objects.create(user=user, first_name='John', last_name='Doe')
        )
        modified_rtypes = []

        def add_constraint(rtype_id):
            rtype = self.get_object_or_fail(RelationType, id=rtype_id)
            rtype.subject_properties.add(ptype)
            modified_rtypes.append(rtype)

        try:
            self.assertGET200(url)

            add_constraint(REL_OBJ_MAIL_SENT)
            self.assertGET200(url)

            add_constraint(REL_OBJ_MAIL_RECEIVED)
            self.assertGET200(url)

            add_constraint(REL_OBJ_RELATED_TO)
            error_response = self.assertGET409(url)
        finally:
            for rtype in modified_rtypes:
                rtype.subject_properties.remove(ptype)

        self.assertIn(
            escape(_('No type of relationship is compatible.')),
            error_response.text,
        )

    def test_brick(self):
        user = self.login_as_root_and_get()

        contact = Contact.objects.create(
            user=user,
            first_name='Vincent', last_name='Law',
            email='vincent.law@immigrates.rmd',
        )

        subject = 'Under arrest'
        self.assertNoFormError(self.client.post(
            self._build_create_entitymail_url(contact),
            data={
                'user':         user.id,
                'sender':       user.linked_contact.email,
                'c_recipients': self.formfield_value_multi_creator_entity(contact),
                'subject':      subject,
                'body':         'Freeze !',
                # 'body_html':    '<p>Freeze !</p>',
            },
        ))
        email = self.get_object_or_fail(EntityEmail, subject=subject)

        response = self.assertGET200(contact.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=bricks.MailsHistoryBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Email in the history',
            plural_title='{count} Emails in the history',
        )

        subject_td = brick_node.find('.//td[@class="email-subject"]')
        self.assertIsNotNone(subject_td)
        self.assertEqual(email.subject, subject_td.text)

    def test_listview01(self):
        user = self.login_as_root_and_get()
        self._create_emails(user=user)

        response = self.assertGET200(reverse('emails__list_emails'))

        with self.assertNoException():
            emails = response.context['page_obj']

        self.assertEqual(4, emails.object_list.count())

    def test_listview_instance_actions(self):
        user = self.login_as_root_and_get()
        email = self._create_email(user=user)

        resend_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=email)
            if isinstance(action, EntityEmailResendAction)
        )
        self.assertEqual('email-resend', resend_action.type)
        self.assertEqual(reverse('emails__resend_emails'), resend_action.url)
        self.assertDictEqual(
            {
                'data': {},
                'options': {'selection': [email.id]},
            },
            resend_action.action_data,
        )
        self.assertTrue(resend_action.is_enabled)
        self.assertTrue(resend_action.is_visible)

    def test_listview_bulk_actions(self):
        user = self.login_as_root_and_get()
        resend_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .bulk_actions(user=user, model=EntityEmail)
            if isinstance(action, BulkEntityEmailResendAction)
        )
        self.assertEqual('email-resend-selection', resend_action.type)
        self.assertEqual(reverse('emails__resend_emails'), resend_action.url)
        self.assertIsNone(resend_action.action_data)
        self.assertTrue(resend_action.is_enabled)
        self.assertTrue(resend_action.is_visible)

    def test_get_sanitized_html_field01(self):
        "Empty body."
        user = self.login_as_root_and_get()
        email = self._create_email(user=user, body_html='')
        # Not an UnsafeHTMLField
        self.assertGET409(reverse('creme_core__sanitized_html_field', args=(email.id, 'sender')))

        response = self.assertGET200(
            reverse('creme_core__sanitized_html_field', args=(email.id, 'body_html'))
        )
        self.assertEqual('', response.text)
        self.assertEqual('SAMEORIGIN', response.get('X-Frame-Options'))

    def test_get_sanitized_html_field02(self):
        user = self.login_as_root_and_get()
        email = self._create_email(
            user=user,
            body_html=(
                '<p>hi</p>'
                '<img alt="Totoro" src="http://external/images/totoro.jpg" />'
                '<img alt="Nekobus" src="{}nekobus.jpg" />'.format(settings.MEDIA_URL)
            ),
        )

        url = reverse('creme_core__sanitized_html_field', args=(email.id, 'body_html'))
        response = self.assertGET200(url)
        self.assertEqual(
            '<p>hi</p>'
            '<img alt="Totoro">'
            '<img alt="Nekobus" src="{}nekobus.jpg">'.format(settings.MEDIA_URL),
            response.text,
        )

        response = self.assertGET200(url + '?external_img=on')
        self.assertEqual(
            '<p>hi</p>'
            '<img alt="Totoro" src="http://external/images/totoro.jpg">'
            '<img alt="Nekobus" src="{}nekobus.jpg">'.format(settings.MEDIA_URL),
            response.text,
        )
        # TODO: improve sanitization test (other tags, css...)

    def test_resend01(self):
        user = self.login_as_root_and_get()
        NOT_SENT = EntityEmail.Status.NOT_SENT
        email1 = self._create_email(user=user, status=NOT_SENT)
        email2 = self._create_email(user=user, status=NOT_SENT)

        url = reverse('emails__resend_emails')
        data = {'ids': f'{email1.id},{email2.id}, '}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)

        messages = mail.outbox
        self.assertEqual(2, len(messages))

        message = messages[0]
        self.assertEqual(email1.subject, message.subject)
        self.assertBodiesEqual(message, body=email1.body, body_html=email1.body_html)

        SENT = EntityEmail.Status.SENT
        self.assertEqual(SENT, self.refresh(email1).status)
        self.assertEqual(SENT, self.refresh(email2).status)

    def test_resend02(self):
        self.login_as_root()

        url = reverse('emails__resend_emails')
        self.assertPOST409(url, data={'ids': 'notanint'})
        self.assertPOST404(url, data={'ids': str(self.UNUSED_PK)})

    def test_job(self):
        user = self.login_as_root_and_get()
        now_value = now()

        ptype = CremePropertyType.objects.create(text='Sent this year')
        source = workflows.EditedEntitySource(model=EntityEmail)
        Workflow.objects.create(
            title='WF for EntityEmail',
            content_type=EntityEmail,
            trigger=workflows.EntityEditionTrigger(model=EntityEmail),
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[
                    condition_handler.DateRegularFieldConditionHandler.build_condition(
                        model=EntityEmail,
                        field_name='sending_date',
                        date_range='current_year',
                    ),
                ],
            ),
            actions=[workflows.PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        job = self._get_job()
        self.assertIsNone(job.user)
        self.assertIsNone(job.type.next_wakeup(job, now_value))

        email = self._create_email(user=user, status=EntityEmail.Status.NOT_SENT)
        self.clear_global_info()  # Clear the event queue to allow edition event

        self.assertIs(job.type.next_wakeup(job, now_value), now_value)
        self.assertIsNone(email.sending_date)

        self._send_mails(job)

        message = self.get_alone_element(mail.outbox)
        self.assertEqual(email.subject, message.subject)
        self.assertBodiesEqual(message, body=email.body, body_html=email.body_html)

        email = self.refresh(email)
        self.assertDatetimesAlmostEqual(now(), email.sending_date)
        self.assertHasProperty(entity=email, ptype=ptype)

    def test_job__error_n_retry(self):
        from ..creme_jobs.entity_emails_send import ENTITY_EMAILS_RETRY

        user = self.login_as_root_and_get()
        email = self._create_email(user=user, status=EntityEmail.Status.SENDING_ERROR)

        job = self._get_job()
        now_value = now()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsNotNone(wakeup)
        self.assertDatetimesAlmostEqual(
            now_value + timedelta(minutes=ENTITY_EMAILS_RETRY),
            wakeup,
        )

        self._send_mails(job)

        message = self.get_alone_element(mail.outbox)
        self.assertEqual(email.subject, message.subject)
        self.assertBodiesEqual(message, body=email.body, body_html=email.body_html)

    def test_job__already_sent(self):
        user = self.login_as_root_and_get()
        self._create_email(user=user, status=EntityEmail.Status.SENT)
        self._send_mails()

        self.assertFalse(mail.outbox)

    def test_job__deleted_email(self):
        "Email is in the trash."
        user = self.login_as_root_and_get()
        email = self._create_email(user=user, status=EntityEmail.Status.SENDING_ERROR)
        email.trash()

        job = self._get_job()
        self.assertIsNone(job.type.next_wakeup(job, now()))

        self._send_mails(job)
        self.assertFalse(mail.outbox)

    def test_refresh_job01(self):
        "Mail is restored + have to be sent => refresh the job."
        user = self.login_as_root_and_get()
        job = self._get_job()

        email = self._create_email(user=user, status=EntityEmail.Status.SENDING_ERROR)
        email.trash()

        queue = get_queue()
        queue.clear()

        email.restore()
        self.assertFalse(self.refresh(email).is_deleted)

        jobs = queue.refreshed_jobs
        self.assertEqual(1, len(jobs))
        self.assertEqual(job, jobs[0][0])

    def test_refresh_job02(self):
        "Mail is restored + do not have to be sent => do not refresh the job."
        user = self.login_as_root_and_get()

        email = self._create_email(user=user, status=EntityEmail.Status.SENDING_ERROR)
        email.status = EntityEmail.Status.SENT
        email.is_deleted = True
        email.save()

        email = self.refresh(email)

        queue = get_queue()
        queue.clear()

        email.restore()
        self.assertFalse(queue.refreshed_jobs)
