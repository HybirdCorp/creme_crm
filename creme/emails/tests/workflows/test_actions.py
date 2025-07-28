from uuid import uuid4

from django.test.utils import override_settings
from django.utils.html import escape
from django.utils.translation import gettext as _

from creme.creme_core.core.workflow import (
    WorkflowBrokenData,
    workflow_registry,
)
from creme.creme_core.workflows import CreatedEntitySource, EditedEntitySource
from creme.documents.tests.base import DocumentsTestCaseMixin
from creme.emails.constants import REL_SUB_MAIL_RECEIVED
from creme.emails.forms.workflows import (
    EmailSendingActionForm,
    TemplateSendingActionForm,
)
from creme.emails.models import EmailSignature, WorkflowEmail
from creme.emails.workflows import (
    EmailSendingAction,
    FixedUserRecipient,
    LiteralRecipient,
    RegularEmailFieldRecipient,
    TemplateSendingAction,
    UserFKRecipient,
)

from ..base import (
    Contact,
    EmailTemplate,
    EntityEmail,
    Organisation,
    _EmailsTestCase,
)

test_sender = 'creme@mydomain.org'


@override_settings(EMAIL_SENDER=test_sender)
class EmailSendingActionTestCase(_EmailsTestCase):
    def test_simple(self):
        "Literal sender, no template for subject/body."
        user = self.get_root_user()
        type_id = 'emails-email_sending'
        self.assertEqual(type_id, EmailSendingAction.type_id)
        self.assertEqual(_('Sending an email'), EmailSendingAction.verbose_name)

        # Instance ---
        address = 'spike.spiegel@bebop.mrs'
        recipient = LiteralRecipient(email_address=address)
        subject = 'This is important'
        body = 'A Contact has been created.'
        source = CreatedEntitySource(model=Contact)
        action = EmailSendingAction(
            recipient=recipient, entity_source=source, subject=subject, body=body,
        )
        self.assertEqual(recipient, action.recipient)
        self.assertEqual(subject,   action.subject)
        self.assertEqual(body,      action.body)
        self.assertEqual(source,    action.entity_source)

        serialized = {
            'type': type_id,
            'recipient': recipient.to_dict(),
            'entity': source.to_dict(),
            'subject': subject,
            'body': body,
        }
        self.assertDictEqual(serialized, action.to_dict())
        self.assertHTMLEqual(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{recipient}</li>'
            '  <li>{subject}</li>'
            '  <li>{body_label}<br><p>{body}</p></li>'
            ' </ul>'
            '</div>'.format(
                label=_('Sending an email:'),
                recipient=recipient.render(user=user),
                subject=_('Subject: {subject}').format(subject=subject),
                body_label=_('Body:'),
                body=body,
            ),
            action.render(user=user),
        )

        # De-serialisation ---
        deserialized = EmailSendingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, EmailSendingAction)
        self.assertEqual(recipient, deserialized.recipient)
        self.assertEqual(source,    deserialized.entity_source)
        self.assertEqual(subject,   deserialized.subject)
        self.assertEqual(body,      deserialized.body)

        # Execution ---
        wf_email_count = WorkflowEmail.objects.count()
        deserialized.execute(context={
            CreatedEntitySource.type_id: Contact.objects.create(user=user, last_name='Spiegel'),
        })
        self.assertEqual(wf_email_count + 1, WorkflowEmail.objects.count())

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(test_sender, wf_email.sender)
        self.assertEqual(address,     wf_email.recipient)
        self.assertEqual(subject,     wf_email.subject)
        self.assertEqual(body,        wf_email.body)

        # Configuration ---
        self.assertEqual(
            EmailSendingAction.config_form_class(), EmailSendingActionForm,
        )

    def test_fixed_user(self):
        user = self.get_root_user()

        # Instance ---
        recipient = FixedUserRecipient(user=user)
        source = CreatedEntitySource(model=Organisation)
        subject = 'This is very important'
        body = 'An Organisation has been created.'
        action = EmailSendingAction(
            recipient=recipient, subject=subject, body=body, entity_source=source,
        )
        self.assertEqual(recipient, action.recipient)
        self.assertEqual(subject,   action.subject)
        self.assertEqual(body,      action.body)

        serialized = {
            'type': EmailSendingAction.type_id,
            'recipient': recipient.to_dict(),
            'entity': source.to_dict(),
            'subject': subject,
            'body': body,
        }
        self.assertDictEqual(serialized, action.to_dict())

        # De-serialisation ---
        deserialized = EmailSendingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, EmailSendingAction)
        self.assertEqual(recipient, deserialized.recipient)

        # Execution ---
        wf_email_count = WorkflowEmail.objects.count()
        deserialized.execute(context={
            CreatedEntitySource.type_id: Organisation.objects.create(user=user, name='Bebop'),
        })
        self.assertEqual(wf_email_count + 1, WorkflowEmail.objects.count())

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(test_sender, wf_email.sender)
        self.assertEqual(user.email,  wf_email.recipient)

        self.assertFalse(EntityEmail.objects.all())

    @override_settings(SITE_DOMAIN='https://creme.mydomain')
    def test_user_fk(self):
        user = self.get_root_user()
        contact = user.linked_contact
        recipient = UserFKRecipient(
            entity_source=EditedEntitySource(model=Contact),
            field_name='is_user',
        )
        action = EmailSendingAction(
            recipient=recipient,
            entity_source=EditedEntitySource(model=Contact),
            subject='Modification!!',
            body='A Contact has been modified: {{entity}}',
        )
        action.execute(context={EditedEntitySource.type_id: contact})

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(user.email, wf_email.recipient)
        self.assertEqual(
            f'A Contact has been modified: {contact}',
            wf_email.body,
        )
        self.assertEqual(
            f'A Contact has been modified: {contact}',
            wf_email.body,
        )
        self.maxDiff = None
        self.assertHTMLEqual(
            f'<!DOCTYPE html>'
            f'<html>'
            f' <head>'
            f'  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'
            f'  <meta name="viewport" content="width=device-width, initial-scale=1.0">'
            f'  <title>Creme Workflow</title>'
            f' </head>'
            f' <body style="margin:0;padding-top:0;padding-bottom:0;padding-right:0;'
            f'padding-left:0;min-width:100%;background-color:#f0f0f0;">'
            f'  <p style="margin: 10px;background-color: #d2e3f2;padding: 10px;'
            f'color: #21323c;border-radius: 5px;width: fit-content;">'
            f'A Contact has been modified: '
            f'   <a href="https://creme.mydomain{contact.get_absolute_url()}">{contact}</a>'
            f'  </p>'
            f' </body>'
            f'</html>',
            wf_email.body_html,
        )

    def test_no_recipient(self):
        user = self.get_root_user()

        recipient = UserFKRecipient(
            entity_source=EditedEntitySource(model=Contact),
            field_name='is_user',
        )
        action = EmailSendingAction(
            recipient=recipient,
            entity_source=EditedEntitySource(model=Contact),
            subject='Modification!!',
            body='A Contact has been modified.',
        )

        # <is_user==None> => No email sent
        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
        )
        action.execute(context={EditedEntitySource.type_id: contact})
        self.assertFalse(WorkflowEmail.objects.all())

    def test_empty_source(self):
        action = EmailSendingAction(
            recipient=FixedUserRecipient(user=self.get_root_user()),
            entity_source=EditedEntitySource(model=Contact),
            subject='Modification!!',
            body='A Contact has been modified.',
        )

        action.execute(context={EditedEntitySource.type_id: None})
        self.assertFalse(WorkflowEmail.objects.all())

    @override_settings(SITE_DOMAIN='https://crm.domain')
    def test_regular_field(self):
        user1 = self.get_root_user()
        user2 = self.create_user()

        recipient = RegularEmailFieldRecipient(
            entity_source=CreatedEntitySource(model=Contact),
            field_name='email',
        )
        subject = 'A New Contact is here!'
        body = 'Go & see it!!\nHere: {{entity}}'
        action = EmailSendingAction(
            recipient=recipient, subject=subject, body=body,
            entity_source=CreatedEntitySource(model=Contact),
        )
        self.assertEqual(recipient, action.recipient)
        self.assertEqual(subject,   action.subject)
        self.assertEqual(body,      action.body)

        # Execution ---
        e_email_count = EntityEmail.objects.count()
        contact = Contact.objects.create(
            user=user1, first_name='Spike', last_name='Spiegel',
            email='spike.spiegel@bebop.mrs',
        )
        action.execute(context={CreatedEntitySource.type_id: contact}, user=user2)
        self.assertFalse(WorkflowEmail.objects.all())
        self.assertEqual(e_email_count + 1, EntityEmail.objects.count())

        e_email = EntityEmail.objects.order_by('-id')[0]
        self.assertEqual(user2, e_email.user)
        self.assertEqual(_('Created by a Workflow'), e_email.description)
        self.assertEqual(test_sender,   e_email.sender)
        self.assertEqual(contact.email, e_email.recipient)
        self.assertEqual(subject,       e_email.subject)
        self.assertEqual(f'Go & see it!!\nHere: {contact}', e_email.body)
        self.assertEqual(EntityEmail.Status.NOT_SENT, e_email.status)
        self.assertHaveRelation(
            subject=e_email, type=REL_SUB_MAIL_RECEIVED, object=contact,
        )
        self.maxDiff = None
        self.assertHTMLEqual(
            f'<!DOCTYPE html>'
            f'<html>'
            f' <head>'
            f'  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'
            f'  <meta name="viewport" content="width=device-width, initial-scale=1.0">'
            f'  <title>Creme Workflow</title>'
            f' </head>'
            f' <body style="margin:0;padding-top:0;padding-bottom:0;padding-right:0;'
            f'padding-left:0;min-width:100%;background-color:#f0f0f0;">'
            f'  <p style="margin: 10px;background-color: #d2e3f2;padding: 10px;'
            f'color: #21323c;border-radius: 5px;width: fit-content;">'
            f'Go & see it!!<br>Here: <a href="https://crm.domain{contact.get_absolute_url()}">'
            f'{contact}</a>'
            f'  </p>'
            f' </body>'
            f'</html>',
            e_email.body_html,
        )

    def test_regular_field__user_not_given(self):
        user = self.get_root_user()
        action = EmailSendingAction(
            recipient=RegularEmailFieldRecipient(
                entity_source=CreatedEntitySource(model=Contact),
                field_name='email',
            ),
            subject='A New Contact is here!',
            body='Here: {{entity}}',
            entity_source=CreatedEntitySource(model=Contact),
        )
        e_email_count = EntityEmail.objects.count()
        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
            email='spike.spiegel@bebop.mrs',
        )

        action.execute(context={CreatedEntitySource.type_id: contact})
        self.assertEqual(e_email_count + 1, EntityEmail.objects.count())

        e_email = EntityEmail.objects.order_by('-id')[0]
        self.assertEqual(user, e_email.user)

    def test_registry__global(self):
        self.assertIn(EmailSendingAction, workflow_registry.action_classes)


@override_settings(EMAIL_SENDER=test_sender)
class TemplateSendingActionTestCase(DocumentsTestCaseMixin, _EmailsTestCase):
    def test_simple(self):
        "Literal sender, no template variable."
        user = self.get_root_user()
        type_id = 'emails-template_sending'
        self.assertEqual(type_id, TemplateSendingAction.type_id)
        self.assertEqual(
            _('Sending an email (from a template)'),
            TemplateSendingAction.verbose_name,
        )

        # Instance ---
        signature = EmailSignature.objects.create(
            user=user,
            name='Main signature',
            body='Client relation team',
        )
        template = EmailTemplate.objects.create(
            user=user, name='Template for WF',
            subject='This is important',
            body='A Contact has been created.',
            body_html='A <i>Contact</i> has been created.',
            signature=signature,
        )

        address = 'spike.spiegel@bebop.mrs'
        recipient = LiteralRecipient(email_address=address)
        source = CreatedEntitySource(model=Contact)
        action = TemplateSendingAction(
            recipient=recipient, entity_source=source, template=template,
        )
        self.assertEqual(recipient, action.recipient)
        self.assertEqual(source,    action.entity_source)
        self.assertEqual(template,  action.template)

        serialized = {
            'type': type_id,
            'recipient': recipient.to_dict(),
            'entity': source.to_dict(),
            'template': str(template.uuid),
        }
        self.assertDictEqual(serialized, action.to_dict())
        self.assertHTMLEqual(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{recipient}</li>'
            '  <li>{template_label}<a href="{template_url}" target="_self">{template}</a></li>'
            ' </ul>'
            '</div>'.format(
                label=_('Sending an email:'),
                recipient=recipient.render(user=user),
                template_label=_('Use template:'),
                template_url=template.get_absolute_url(),
                template=template.name,
            ),
            action.render(user=user),
        )

        # De-serialisation ---
        deserialized = TemplateSendingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, TemplateSendingAction)
        self.assertEqual(recipient, deserialized.recipient)
        self.assertEqual(template,  deserialized.template)

        # Execution ---
        wf_email_count = WorkflowEmail.objects.count()
        contact = Contact.objects.create(user=user, first_name='Ed', last_name='Wong')
        deserialized.execute(context={source.type_id: contact})
        self.assertEqual(wf_email_count + 1, WorkflowEmail.objects.count())

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(test_sender, wf_email.sender)
        self.assertEqual(address,     wf_email.recipient)
        self.assertEqual(template.subject,   wf_email.subject)
        self.assertEqual(template.body,      wf_email.body)
        self.assertEqual(template.body_html, wf_email.body_html)
        self.assertEqual(signature, wf_email.signature)

        self.assertFalse(EntityEmail.objects.all())

        # Configuration ---
        self.assertEqual(
            TemplateSendingAction.config_form_class(), TemplateSendingActionForm,
        )

    def test_fixed_user(self):
        user = self.login_as_root_and_get()
        doc = self._create_doc(title='Attachment #1', user=user)

        # Instance ---
        recipient = FixedUserRecipient(user=user)

        source = CreatedEntitySource(model=Contact)
        subject = 'This is very important'
        template = EmailTemplate.objects.create(
            user=user, name='Template for WF', subject=subject,
            body='A Contact has been created: {{last_name}}, {{first_name}}',
            body_html='A Contact has been <b>created</b>: {{last_name}}, {{first_name}}',
        )
        template.attachments.set([doc])

        action = TemplateSendingAction(
            recipient=recipient, template=str(template.uuid), entity_source=source,
        )

        serialized = {
            'type': TemplateSendingAction.type_id,
            'recipient': recipient.to_dict(),
            'entity': source.to_dict(),
            'template': str(template.uuid),
        }
        self.assertDictEqual(serialized, action.to_dict())

        # De-serialisation ---
        deserialized = TemplateSendingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, TemplateSendingAction)
        self.assertEqual(recipient, deserialized.recipient)

        self.assertHTMLEqual(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{recipient}</li>'
            '  <li>{template_label}<a href="{template_url}" target="_self">{template}</a></li>'
            ' </ul>'
            '</div>'.format(
                label=_('Sending an email:'),
                recipient=escape(recipient.render(user=user)),
                template_label=_('Use template:'),
                template_url=template.get_absolute_url(),
                template=template.name,
            ),
            deserialized.render(user=user),
        )

        # Execution ---
        wf_email_count = WorkflowEmail.objects.count()
        contact = Contact.objects.create(user=user, first_name='Ed', last_name='Wong')
        deserialized.execute(context={source.type_id: contact})
        self.assertEqual(wf_email_count + 1, WorkflowEmail.objects.count())

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(test_sender, wf_email.sender)
        self.assertEqual(user.email,  wf_email.recipient)
        self.assertEqual(
            f'A Contact has been created: {contact.last_name}, {contact.first_name}',
            wf_email.body,
        )
        self.assertEqual(
            f'A Contact has been <b>created</b>: {contact.last_name}, {contact.first_name}',
            wf_email.body_html,
        )
        self.assertListEqual([doc], [*wf_email.attachments.all()])

    def test_no_recipient(self):
        user1 = self.get_root_user()

        source = EditedEntitySource(model=Contact)
        action = TemplateSendingAction(
            recipient=UserFKRecipient(
                entity_source=source, field_name='is_user',
            ),
            entity_source=source,
            template=EmailTemplate.objects.create(
                user=user1,
                subject='Modification!!',
                body='A Contact has been modified.',
            ),
        )
        contact = Contact.objects.create(
            user=user1, first_name='Spike', last_name='Spiegel',
            # is_user=..., => No email sent
        )
        action.execute(context={source.type_id: contact})
        self.assertFalse(WorkflowEmail.objects.all())

    def test_empty_source(self):
        user = self.get_root_user()
        source = CreatedEntitySource(model=Contact)
        action = TemplateSendingAction(
            recipient=FixedUserRecipient(user=user),
            entity_source=source,
            template=EmailTemplate.objects.create(
                user=user,
                subject='Modification!!',
                body='A Contact has been modified.',
            ),
        )

        action.execute(context={source.type_id: None})
        self.assertFalse(WorkflowEmail.objects.all())

    def test_regular_field(self):
        user1 = self.login_as_root_and_get()
        user2 = self.create_user()

        doc = self._create_doc(title='Attachment #1', user=user1)

        source = CreatedEntitySource(model=Contact)
        recipient = RegularEmailFieldRecipient(
            entity_source=source, field_name='email',
        )
        signature = EmailSignature.objects.create(
            user=user1,
            name='Main signature',
            body='Client relation team',
        )
        template = EmailTemplate.objects.create(
            user=user1, subject='A New Contact is here!',
            body='This is {{first_name}} {{last_name}}',
            body_html='This is {{first_name}} <b>{{last_name}}</b>',
            signature=signature,
        )
        template.attachments.set([doc])
        action = TemplateSendingAction(
            recipient=recipient, entity_source=source, template=template,
        )

        # Execution ---
        e_email_count = EntityEmail.objects.count()
        contact = Contact.objects.create(
            user=user1, first_name='Spike', last_name='Spiegel',
            email='spike.spiegel@bebop.mrs',
        )
        action.execute(context={source.type_id: contact}, user=user2)
        self.assertFalse(WorkflowEmail.objects.all())
        self.assertEqual(e_email_count + 1, EntityEmail.objects.count())

        e_email = EntityEmail.objects.order_by('-id')[0]
        self.assertEqual(user2, e_email.user)
        self.assertEqual(_('Created by a Workflow'), e_email.description)
        self.assertEqual(test_sender,      e_email.sender)
        self.assertEqual(contact.email,    e_email.recipient)
        self.assertEqual(template.subject, e_email.subject)
        self.assertEqual(signature,        e_email.signature)
        self.assertEqual(
            f'This is {contact.first_name} {contact.last_name}',
            e_email.body,
        )
        self.assertEqual(
            f'This is {contact.first_name} <b>{contact.last_name}</b>',
            e_email.body_html,
        )
        self.assertEqual(EntityEmail.Status.NOT_SENT, e_email.status)
        self.assertListEqual([doc], [*e_email.attachments.all()])
        self.assertHaveRelation(
            subject=e_email, type=REL_SUB_MAIL_RECEIVED, object=contact,
        )

    def test_regular_field__no_given_user(self):
        user = self.login_as_root_and_get()

        source = CreatedEntitySource(model=Contact)
        template = EmailTemplate.objects.create(
            user=user, subject='A New Contact!',
            body='This is {{last_name}}',
            body_html='This is <b>{{last_name}}</b>',
        )
        action = TemplateSendingAction(
            recipient=RegularEmailFieldRecipient(
                entity_source=source, field_name='email',
            ),
            entity_source=source, template=template,
        )

        e_email_count = EntityEmail.objects.count()
        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
            email='spike.spiegel@bebop.mrs',
        )
        action.execute(context={source.type_id: contact})
        self.assertEqual(e_email_count + 1, EntityEmail.objects.count())

        e_email = EntityEmail.objects.order_by('-id')[0]
        self.assertEqual(user, e_email.user)

    def test_broken_template(self):
        user = self.get_root_user()
        e_email_count = EntityEmail.objects.count()
        action = TemplateSendingAction.from_dict(
            data={
                'type': TemplateSendingAction.type_id,
                'recipient': {
                    'type': FixedUserRecipient.type_id,
                    'user': str(user.uuid),
                },
                'entity': {
                    'type': CreatedEntitySource.type_id,
                    'model': 'persons.organisation',
                },
                'template': str(uuid4()),
            },
            registry=workflow_registry,
        )

        with self.assertNumQueries(1):
            with self.assertRaises(WorkflowBrokenData) as cm:
                action.template  # NOQA
        self.assertEqual(
            _('The template does not exist anymore'), str(cm.exception),
        )

        with self.assertNumQueries(0):
            with self.assertRaises(WorkflowBrokenData):
                action.template  # NOQA

        # Render ---
        self.assertHTMLEqual(
            '{label}<p class="errorlist">{error}</p>'.format(
                label=_('Sending an email'),
                error=_('The template does not exist anymore'),
            ),
            action.render(user=user),
        )

        # Execute ---
        with self.assertLogs(level='WARNING') as log_cm:
            with self.assertNoException():
                action.execute(context={
                    CreatedEntitySource.type_id:
                        Organisation.objects.create(user=user, name='Acme'),
                })
        self.assertIn(
            _('The template does not exist anymore'),
            self.get_alone_element(log_cm.output),
        )
        self.assertEqual(e_email_count, EntityEmail.objects.count())

    def test_registry__global(self):
        self.assertIn(TemplateSendingAction, workflow_registry.action_classes)
