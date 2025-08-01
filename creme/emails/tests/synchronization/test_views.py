from functools import partial
from os.path import basename, exists, join

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext, pgettext

from creme.creme_core.models import FileRef
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.file_handling import FileCreator
from creme.documents import get_document_model
from creme.documents.models import FolderCategory
from creme.emails import bricks
from creme.emails.constants import (
    REL_SUB_MAIL_RECEIVED,
    REL_SUB_MAIL_SENT,
    UUID_FOLDER_CAT_EMAILS,
)
from creme.emails.models import (
    EmailSyncConfigItem,
    EmailToSync,
    EmailToSyncPerson,
)
from creme.emails.tests.base import (
    Contact,
    EntityEmail,
    Folder,
    Organisation,
    _EmailsTestCase,
)
from creme.persons.tests.base import skipIfCustomContact

Document = get_document_model()


class SynchronizationViewsTestCase(BrickTestCaseMixin, _EmailsTestCase):
    DEL_CONF_URL = reverse('emails__delete_sync_config_item')
    ACCEPT_EMAIL_URL = reverse('emails__accept_email_to_sync')
    DEL_EMAIL_URL = reverse('emails__delete_email_to_sync')

    # TODO: factorise
    @staticmethod
    def _create_file_for_document(name):
        rel_media_dir_path = Document._meta.get_field('filedata').upload_to

        abs_path = FileCreator(
            dir_path=join(settings.MEDIA_ROOT, rel_media_dir_path),
            name=name,
        ).create()

        with open(abs_path, 'w') as f:
            f.write('I am the content')

        return join(rel_media_dir_path, basename(abs_path))

    def test_creme_config_portal(self):
        self.login_as_root()

        EmailSyncConfigItem.objects.create(
            host='pop.mydomain.org',
            username='spike',
            password='c0w|3OY B3b0P',
            port=112,
            use_ssl=False,
        )
        response = self.assertGET200(reverse('creme_config__app_portal', args=('emails',)))

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=bricks.EmailSyncConfigItemsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Configured server for synchronization',
            plural_title='{count} Configured servers for synchronization',
        )

    def test_server_config_creation01(self):
        "POP, SSL, no attachments."
        self.login_as_emails_admin()

        url = reverse('emails__create_sync_config_item')
        context1 = self.assertGET200(url).context

        with self.assertNoException():
            password_f = context1['form'].fields['password']

        self.assertTrue(password_f.required)
        self.assertFalse(password_f.help_text)
        self.assertEqual(
            pgettext('emails', 'Create a server configuration'),
            context1.get('title'),
        )
        self.assertEqual(
            _('Save the configuration'),
            context1.get('submit_label'),
        )

        # ---
        box_type = EmailSyncConfigItem.Type.POP
        pop_host = 'pop.mydomain.org'
        username = 'spike'
        password = 'c0w|3OY B3b0P'
        port = 1024
        response2 = self.client.post(
            url,
            data={
                'type': box_type,
                'host': pop_host,
                'username': username,
                'password': password,
                'port': port,
                'use_ssl': 'on',

                'keep_attachments': '',
            },
        )
        self.assertNoFormError(response2)

        item = self.get_object_or_fail(EmailSyncConfigItem, host=pop_host)
        self.assertEqual(box_type, item.type)
        self.assertEqual(username, item.username)
        self.assertEqual(password, item.password)
        self.assertEqual(port,     item.port)
        self.assertIs(item.use_ssl,          True)
        self.assertIs(item.keep_attachments, False)

    def test_server_config_creation02(self):
        "No admin credentials."
        self.login_as_emails_user()
        self.assertGET403(reverse('emails__create_sync_config_item'))

    def test_server_config_edition01(self):
        "IMAP, no SSL, default port, keep attachments."
        self.login_as_emails_admin()

        item = EmailSyncConfigItem.objects.create(
            type=EmailSyncConfigItem.Type.POP,
            host='pop.mydomain.org',
            username='spike',
            password='c0w|3OY B3b0P',
            port=112,
            use_ssl=False,
            keep_attachments=False,
        )

        url = item.get_edit_absolute_url()
        context1 = self.assertGET200(url).context

        with self.assertNoException():
            password_f = context1['form'].fields['password']

        self.assertFalse(password_f.required)
        self.assertEqual(
            _('Leave empty to keep the recorded password'),
            password_f.help_text,
        )

        self.assertEqual(
            pgettext('emails', 'Edit the server configuration'),
            context1.get('title'),
        )
        self.assertEqual(
            _('Save the configuration'),
            context1.get('submit_label'),
        )

        # ---
        box_type = EmailSyncConfigItem.Type.IMAP
        imap_host = 'imap.mydomain.org'
        username = 'spiegel'
        password = 's33 y4 $p4c3 c0xBoY'
        # port = 1024
        response2 = self.client.post(
            url,
            data={
                'type': box_type,
                'host': imap_host,
                'username': username,
                'password': password,
                # 'port': port,
                'use_ssl': '',
                'keep_attachments': 'on',
            },
        )
        self.assertNoFormError(response2)

        item = self.refresh(item)
        self.assertEqual(box_type,  item.type)
        self.assertEqual(imap_host, item.host)
        self.assertEqual(username,  item.username)
        self.assertEqual(password,  item.password)
        self.assertIsNone(item.port)
        self.assertFalse(item.use_ssl)
        self.assertTrue(item.keep_attachments)

    def test_server_config_edition02(self):
        "Port is set, password is kept."
        self.login_as_emails_admin()

        password = 'c0w|3OY B3b0P'
        item = EmailSyncConfigItem.objects.create(
            type=EmailSyncConfigItem.Type.IMAP,
            host='imap.mydomain.org',
            username='spiegel',
            password=password,
            # port=...,
            use_ssl=False,
            keep_attachments=True,
        )

        box_type = EmailSyncConfigItem.Type.POP
        imap_host = 'pop.mydomain.org'
        username = 'spike'
        port = 1024
        response = self.client.post(
            item.get_edit_absolute_url(),
            data={
                'type': box_type,
                'host': imap_host,
                'username': username,
                'password': '',  # <== empty
                'port': port,
                'use_ssl': '',
                'keep_attachments': '',
            },
        )
        self.assertNoFormError(response)

        item = self.refresh(item)
        self.assertEqual(box_type,  item.type)
        self.assertEqual(imap_host, item.host)
        self.assertEqual(username,  item.username)
        self.assertEqual(password,  item.password)
        self.assertEqual(port,      item.port)
        self.assertFalse(item.use_ssl)
        self.assertFalse(item.keep_attachments)

    def test_server_config_edition03(self):
        "No admin credentials."
        self.login_as_emails_user()

        item = EmailSyncConfigItem.objects.create(
            host='pop.mydomain.org',
            username='spike',
            password='c0w|3OY B3b0P',
            port=112,
            use_ssl=False,
        )
        self.assertGET403(item.get_edit_absolute_url())

    def test_server_config_deletion01(self):
        self.login_as_emails_admin()

        item = EmailSyncConfigItem.objects.create(
            host='pop.mydomain.org',
            username='spike',
            password='c0w|3OY B3b0P',
            port=112,
            use_ssl=False,
        )

        url = self.DEL_CONF_URL
        data = {'id': item.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertDoesNotExist(item)

    def test_server_config_deletion02(self):
        "No admin credentials."
        self.login_as_emails_user()

        item = EmailSyncConfigItem.objects.create(
            host='pop.mydomain.org',
            username='spike',
            password='c0w|3OY B3b0P',
            # port=112,
            # use_ssl=False,
        )
        self.assertPOST403(self.DEL_CONF_URL, data={'id': item.id})
        self.assertStillExists(item)

    def test_sync_portal__allowed_user(self):
        user = self.login_as_emails_user()

        create_e2s = EmailToSync.objects.create
        create_e2s(user=user,                 subject='I want a swordfish II')
        create_e2s(user=self.get_root_user(), subject='I want a swordfish III')

        response = self.assertGET200(reverse('emails__sync_portal'))

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=bricks.EmailsToSyncBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Email to synchronise',
            plural_title='{count} Emails to synchronise',
        )

    def test_sync_portal__forbidden_user(self):
        self.login_as_standard(allowed_apps=['documents'])
        self.assertGET403(reverse('emails__sync_portal'))

    def test_sync_portal__staff(self):
        self.login_as_super(is_staff=True)

        EmailToSync.objects.create(user=self.get_root_user(), subject='I want a swordfish')

        response = self.assertGET200(reverse('emails__sync_portal'))
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=bricks.EmailsToSyncBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Email to synchronise',
            plural_title='{count} Emails to synchronise',
        )

    def test_sync_portal__team(self):
        user = self.login_as_emails_user()
        team1 = self.create_team('Team OK', user)
        team2 = self.create_team('Team KO', self.get_root_user())

        create_e2s = EmailToSync.objects.create
        create_e2s(user=team1, subject='I want a swordfish II')
        create_e2s(user=team2, subject='I want a swordfish III')

        response = self.assertGET200(reverse('emails__sync_portal'))

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=bricks.EmailsToSyncBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Email to synchronise',
            plural_title='{count} Emails to synchronise',
        )

    def test_delete_email_to_sync01(self):
        user = self.login_as_emails_user()

        create_e2s = partial(EmailToSync.objects.create, user=user)
        e2s1 = create_e2s(subject='I want a swordfish I')
        e2s2 = create_e2s(subject='I want a swordfish II')

        create_person = partial(EmailToSyncPerson.objects.create, email_to_sync=e2s1)
        person1 = create_person(type=EmailToSyncPerson.Type.SENDER, email='spiegel@bebop.mrs')
        person2 = create_person(type=EmailToSyncPerson.Type.RECIPIENT, email='valentine@bebop.mrs')

        attached_file = FileRef.objects.create(
            user=user,
            filedata=self._create_file_for_document('test_delete_email_to_sync01.txt'),
            temporary=False,
        )
        e2s1.attachments.add(attached_file)

        url = self.DEL_EMAIL_URL
        data = {'ids': f'{e2s1.id},{e2s2.id},'}
        self.assertGET405(url, data=data)

        response = self.assertPOST200(url, data=data)
        self.assertEqual(_('Operation successfully completed'), response.text)

        self.assertDoesNotExist(e2s1)
        self.assertDoesNotExist(e2s2)

        self.assertDoesNotExist(person1)
        self.assertDoesNotExist(person2)

        self.assertTrue(self.refresh(attached_file).temporary)

    def test_delete_email_to_sync02(self):
        "No emails credentials."
        user = self.login_as_standard(
            allowed_apps=['persons'],  # <====
        )
        e2s = EmailToSync.objects.create(user=user, subject='I want a swordfish II')

        self.assertPOST403(self.DEL_EMAIL_URL, data={'ids': e2s.id})
        self.assertStillExists(e2s)

    def test_delete_email_to_sync03(self):
        "Not owner."
        self.login_as_emails_user()
        e2s = EmailToSync.objects.create(
            user=self.get_root_user(),  # <====
            subject='I want a swordfish II',
        )

        self.assertPOST403(self.DEL_EMAIL_URL, data={'ids': e2s.id})
        self.assertStillExists(e2s)

    def test_delete_email_to_sync04(self):
        "Not owner but staff."
        self.login_as_super(is_staff=True)
        e2s = EmailToSync.objects.create(
            user=self.get_root_user(), subject='I want a swordfish II',
        )

        self.assertPOST200(self.DEL_EMAIL_URL, data={'ids': e2s.id})
        self.assertDoesNotExist(e2s)

    def test_delete_email_to_sync_error01(self):
        "issues with ID list."
        self.login_as_root()
        self.assertPOST404(self.DEL_EMAIL_URL, data={})
        self.assertPOST(400, self.DEL_EMAIL_URL, data={'ids': '1,notint'})
        self.assertPOST(400, self.DEL_EMAIL_URL, data={'ids': ''})

    def test_delete_email_to_sync_error02(self):
        "Error mix."
        user = self.login_as_root_and_get()

        create_e2s = EmailToSync.objects.create
        e2s1 = create_e2s(user=user,               subject='I want a swordfish I')
        e2s2 = create_e2s(user=self.create_user(), subject='I want a swordfish II')

        response = self.assertPOST403(
            self.DEL_EMAIL_URL,
            data={'ids': f'{e2s1.id},{e2s2.id},123654'},
        )
        self.assertDoesNotExist(e2s1)

        self.assertDictEqual(
            {
                'count': 3,
                'errors': [
                    ngettext(
                        "{count} email doesn't exist or has been removed.",
                        "{count} emails don't exist or have been removed.",
                        1
                    ).format(count=1),
                    _('You cannot edit or delete this email (not yours)'),
                ],
            },
            response.json(),
        )

    @skipIfCustomContact
    def test_edit_person01(self):
        user = self.login_as_emails_user(allowed_apps=['persons'])
        self.add_credentials(user.role, own=['VIEW', 'CHANGE', 'LINK'])

        e2s = EmailToSync.objects.create(user=user, subject='I want a swordfish II')

        addr = 'spike@bebop.mrs'
        recipient = EmailToSyncPerson.objects.create(
            email_to_sync=e2s, type=EmailToSyncPerson.Type.RECIPIENT, email=addr,
        )

        url = recipient.get_edit_absolute_url()
        context1 = self.assertGET200(url).context
        self.assertEqual(
            # _('Edit the recipient «{object}»').format(object=recipient.email), TODO?
            _('Edit «{object}»').format(object=addr),
            context1.get('title'),
        )

        with self.assertNoException():
            person_f1 = context1['form'].fields['person']
        self.assertIsNone(person_f1.initial)

        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
        )

        self.assertNoFormError(self.client.post(
            url, data={'person': self.formfield_value_generic_entity(contact)},
        ))

        recipient = self.refresh(recipient)
        self.assertEqual(addr,    recipient.email)  # No change
        self.assertEqual(contact, recipient.entity.get_real_entity())
        self.assertEqual(Contact, recipient.entity_ctype.model_class())
        self.assertEqual(contact, recipient.person)

        self.assertEqual(addr, self.refresh(contact).email)

        # Set an Organisation ---
        orga = Organisation.objects.create(user=user, name='Bebop')

        self.assertNoFormError(self.client.post(
            url, data={'person': self.formfield_value_generic_entity(orga)},
        ))

        self.assertEqual(orga, self.refresh(recipient).person)
        self.assertEqual(addr, self.refresh(orga).email)

        # ---
        response4 = self.assertGET200(url)

        with self.assertNoException():
            person_f2 = response4.context['form'].fields['person']
        self.assertEqual(orga, person_f2.initial)

    def test_edit_person02(self):
        "No emails credentials."
        user = self.login_as_standard(
            allowed_apps=['persons'],  # <====
        )

        recipient = EmailToSyncPerson.objects.create(
            email_to_sync=EmailToSync.objects.create(
                user=user, subject='I want a swordfish II',
            ),
            type=EmailToSyncPerson.Type.RECIPIENT, email='spike@bebop.mrs',
        )
        self.assertGET403(recipient.get_edit_absolute_url())

    @skipIfCustomContact
    def test_edit_person03(self):
        "LINK credentials."
        user = self.login_as_emails_user(allowed_apps=['persons'])
        self.add_credentials(user.role, own=['VIEW', 'CHANGE'])  # Not 'LINK'

        e2s = EmailToSync.objects.create(user=user, subject='I want a swordfish II')
        recipient = EmailToSyncPerson.objects.create(
            email_to_sync=e2s, type=EmailToSyncPerson.Type.RECIPIENT, email='spike@bebop.mrs',
        )
        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
        )
        response = self.assertPOST200(
            recipient.get_edit_absolute_url(),
            data={'person': self.formfield_value_generic_entity(contact)},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='person',
            errors=_('You are not allowed to link this entity: {}').format(contact),
        )

    @skipIfCustomContact
    def test_edit_person04(self):
        "CHANGE credentials if email must be set."
        user = self.login_as_emails_user(allowed_apps=['persons'])
        self.add_credentials(user.role, own=['VIEW', 'LINK'])  # Not 'CHANGE'

        e2s = EmailToSync.objects.create(user=user, subject='I want a swordfish II')
        recipient = EmailToSyncPerson.objects.create(
            email_to_sync=e2s, type=EmailToSyncPerson.Type.RECIPIENT, email='spike@bebop.mrs',
        )

        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
        )

        url = recipient.get_edit_absolute_url()
        data = {'person': self.formfield_value_generic_entity(contact)}
        response1 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response1.context['form'],
            field='person',
            errors=_(
                'You are not allowed to edit «{}», so the email address cannot be updated'
            ).format(contact),
        )

        # Email has not to be edited ---
        contact.email = recipient.email
        contact.save()

        self.assertNoFormError(self.client.post(url, data=data))
        self.assertEqual(contact, self.refresh(recipient).person)

    def test_mark_recipient(self):
        user = self.login_as_emails_user(allowed_apps=['persons'])

        create_e2s = partial(EmailToSync.objects.create, user=user)
        e2s_1 = create_e2s(subject='I want a swordfish II')
        e2s_2 = create_e2s(subject='I want a hammerhead')

        create_person = partial(
            EmailToSyncPerson.objects.create, type=EmailToSyncPerson.Type.RECIPIENT,
        )
        recipient11 = create_person(
            email_to_sync=e2s_1, email='spike@bebop.mrs', is_main=True,
        )
        recipient12 = create_person(
            email_to_sync=e2s_1, email='jet@bebop.mrs',
        )
        recipient21 = create_person(
            email_to_sync=e2s_2, email='spike@bebop.mrs', is_main=True,
        )
        recipient22 = create_person(
            email_to_sync=e2s_2, email='spike@bebop.mrs',
        )

        url = reverse('emails__mark_email_to_sync_recipient', args=(e2s_1.id,))
        data = {'id': recipient12.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertTrue(self.refresh(recipient12).is_main)
        self.assertFalse(self.refresh(recipient11).is_main)
        self.assertTrue(self.refresh(recipient21).is_main)
        self.assertFalse(self.refresh(recipient22).is_main)

        # ---
        self.assertPOST404(url, data={'id': recipient22.id})
        self.assertTrue(self.refresh(recipient12).is_main)
        self.assertFalse(self.refresh(recipient11).is_main)
        self.assertTrue(self.refresh(recipient21).is_main)
        self.assertFalse(self.refresh(recipient22).is_main)

    def test_mark_recipient__sender(self):
        "Cannot mark senders."
        user = self.login_as_emails_user(allowed_apps=['persons'])
        e2s = EmailToSync.objects.create(user=user, subject='I want a swordfish II')
        sender = EmailToSyncPerson.objects.create(
            email_to_sync=e2s, email='spike@bebop.mrs',
            type=EmailToSyncPerson.Type.SENDER,
        )
        self.assertPOST404(
            reverse('emails__mark_email_to_sync_recipient', args=(e2s.id,)),
            data={'id': sender.id},
        )

    def test_mark_recipient__no_emails_creds(self):
        "No emails credentials."
        user = self.login_as_standard(
            allowed_apps=['persons'],  # <===
        )
        e2s = EmailToSync.objects.create(user=user, subject='I want a swordfish II')
        recipient = EmailToSyncPerson.objects.create(
            email_to_sync=e2s, email='spike@bebop.mrs',
            type=EmailToSyncPerson.Type.RECIPIENT,
        )
        self.assertPOST403(
            reverse('emails__mark_email_to_sync_recipient', args=(e2s.id,)),
            data={'id': recipient.id},
        )

    def test_mark_recipient__not_owner(self):
        "Not owner."
        self.login_as_emails_user()
        e2s = EmailToSync.objects.create(
            user=self.get_root_user(),  # <===
            subject='I want a swordfish II',
        )
        recipient = EmailToSyncPerson.objects.create(
            email_to_sync=e2s, email='spike@bebop.mrs',
            type=EmailToSyncPerson.Type.RECIPIENT,
        )
        self.assertPOST403(
            reverse('emails__mark_email_to_sync_recipient', args=(e2s.id,)),
            data={'id': recipient.id},
        )

    def test_mark_recipient__in_team_owner(self):
        user = self.login_as_emails_user(allowed_apps=['persons'])
        team = self.create_team('Default owner', user)
        e2s = EmailToSync.objects.create(subject='I want a swordfish II', user=team)

        create_person = partial(
            EmailToSyncPerson.objects.create, type=EmailToSyncPerson.Type.RECIPIENT,
        )
        recipient1 = create_person(email_to_sync=e2s, email='spike@bebop.mrs', is_main=True)
        recipient2 = create_person(email_to_sync=e2s, email='jet@bebop.mrs')

        self.assertPOST200(
            reverse('emails__mark_email_to_sync_recipient', args=(e2s.id,)),
            data={'id': recipient2.id},
        )
        self.assertTrue(self.refresh(recipient2).is_main)
        self.assertFalse(self.refresh(recipient1).is_main)

    def test_mark_recipient__not_in_team_owner(self):
        self.login_as_emails_user(allowed_apps=['persons'])
        team = self.create_team('Default owner', self.get_root_user())
        e2s = EmailToSync.objects.create(subject='I want a swordfish II', user=team)

        create_person = partial(
            EmailToSyncPerson.objects.create, type=EmailToSyncPerson.Type.RECIPIENT,
        )
        create_person(email_to_sync=e2s, email='spike@bebop.mrs', is_main=True)
        recipient2 = create_person(email_to_sync=e2s, email='jet@bebop.mrs')

        self.assertPOST403(
            reverse('emails__mark_email_to_sync_recipient', args=(e2s.id,)),
            data={'id': recipient2.id},
        )

    def test_delete_recipient01(self):
        user = self.login_as_emails_user()
        e2s = EmailToSync.objects.create(user=user, subject='I want a swordfish II')

        create_person = partial(EmailToSyncPerson.objects.create, email_to_sync=e2s)
        sender = create_person(
            type=EmailToSyncPerson.Type.SENDER,
            email='spike@bebop.mrs',
        )
        recipient1 = create_person(
            type=EmailToSyncPerson.Type.RECIPIENT,
            email='spike@bebop.mrs',
        )
        recipient2 = create_person(
            type=EmailToSyncPerson.Type.RECIPIENT,
            email='jet@bebop.mrs',
        )

        url = reverse('emails__delete_email_to_sync_recipient', args=(e2s.id, ))

        # Cannot delete a sender
        data1 = {'id': sender.id}
        self.assertGET405(url, data=data1)
        self.assertPOST404(url, data=data1)

        # Delete not last recipient
        self.assertPOST200(url, data={'id': recipient1.id})
        self.assertDoesNotExist(recipient1)
        self.assertStillExists(e2s)

        # Cannot delete the last recipient
        self.assertPOST409(url, data={'id': recipient2.id})
        self.assertStillExists(recipient2)

    def test_delete_recipient02(self):
        "No emails credentials."
        user = self.login_as_standard(
            allowed_apps=['persons'],  # <====
        )
        e2s = EmailToSync.objects.create(user=user, subject='I want a swordfish II')
        recipient = EmailToSyncPerson.objects.create(
            email_to_sync=e2s,
            type=EmailToSyncPerson.Type.RECIPIENT,
            email='spike@bebop.mrs',
        )
        self.assertPOST403(
            reverse('emails__delete_email_to_sync_recipient', args=(e2s.id,)),
            data={'id': recipient.id},
        )

    def test_delete_recipient03(self):
        "Not owner."
        self.login_as_emails_user()

        e2s = EmailToSync.objects.create(
            user=self.get_root_user(),   # <====
            subject='I want a swordfish II',
        )
        recipient = EmailToSyncPerson.objects.create(
            email_to_sync=e2s,
            type=EmailToSyncPerson.Type.RECIPIENT,
            email='spike@bebop.mrs',
        )
        self.assertPOST403(
            reverse('emails__delete_email_to_sync_recipient', args=(e2s.id,)),
            data={'id': recipient.id},
        )

    def test_delete_attachment01(self):
        user = self.login_as_emails_user()
        e2s = EmailToSync.objects.create(user=user, subject='I want a swordfish II')

        create_fileref = partial(FileRef.objects.create, user=user, temporary=False)
        attached_file1 = create_fileref(
            filedata=self._create_file_for_document('test_delete_attachment01_1.txt'),
        )
        attached_file2 = create_fileref(
            filedata=self._create_file_for_document('test_delete_attachment01_2.txt'),
        )
        e2s.attachments.set([attached_file1, attached_file2])

        url = reverse('emails__delete_email_to_sync_attachment', args=(e2s.id,))
        data = {'id': attached_file1.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertTrue(self.refresh(attached_file1).temporary)
        self.assertListEqual([attached_file2], [*e2s.attachments.all()])

    def test_delete_attachment02(self):
        "No emails credentials."
        user = self.login_as_standard(
            allowed_apps=['persons'],  # <===
        )
        e2s = EmailToSync.objects.create(user=user, subject='I want a swordfish II')

        attached_file = FileRef.objects.create(
            user=user,
            filedata=self._create_file_for_document('test_delete_attachment02.txt'),
            temporary=False,
        )
        e2s.attachments.add(attached_file)

        self.assertPOST403(
            reverse('emails__delete_email_to_sync_attachment', args=(e2s.id,)),
            data={'id': attached_file.id},
        )

    def test_delete_attachment03(self):
        "Not owner."
        self.login_as_emails_user()
        other_user = self.get_root_user()
        e2s = EmailToSync.objects.create(user=other_user, subject='I want a swordfish II')

        attached_file = FileRef.objects.create(
            user=other_user,
            filedata=self._create_file_for_document('test_delete_attachment03.txt'),
            temporary=False,
        )
        e2s.attachments.add(attached_file)

        self.assertPOST403(
            reverse('emails__delete_email_to_sync_attachment', args=(e2s.id,)),
            data={'id': attached_file.id},
        )

    def test_fix_email_to_sync01(self):
        user = self.login_as_emails_user(allowed_apps=['persons'])
        self.add_credentials(user.role, all=['VIEW', 'LINK'])

        linked_contact = user.linked_contact
        subject = 'I want a swordfish'
        received_subject = f'Fw: {subject}'
        e2s = EmailToSync.objects.create(user=user, subject=received_subject)
        EmailToSyncPerson.objects.create(
            email_to_sync=e2s,
            type=EmailToSyncPerson.Type.SENDER,
            email=linked_contact.email,
            person=linked_contact,
        )

        url = reverse('emails__fix_email_to_sync', args=(e2s.id,))
        response1 = self.assertGET200(url)

        with self.assertNoException():
            form = response1.context['form']
            fields = form.fields
            sender_f = fields['sender']
            recipient_f = fields['recipient']

        self.assertEqual(received_subject, form.initial.get('subject'))
        self.assertEqual(linked_contact, recipient_f.initial)
        self.assertIsNone(sender_f.initial)

        # ---
        sender_contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel', email='spiegel@bebop.spc',
        )
        response2 = self.client.post(
            url,
            data={
                'subject':   subject,
                'sender':    self.formfield_value_generic_entity(sender_contact),
                'recipient': self.formfield_value_generic_entity(linked_contact),
            },
        )
        self.assertNoFormError(response2)

        e2s = self.refresh(e2s)
        self.assertEqual(subject, e2s.subject)

        related_persons = [*e2s.related_persons.order_by('type')]
        self.assertEqual(2, len(related_persons))

        related1 = related_persons[0]
        self.assertEqual(EmailToSyncPerson.Type.SENDER, related1.type)
        self.assertEqual(sender_contact.email,          related1.email)
        self.assertEqual(sender_contact,                related1.person)

        related2 = related_persons[1]
        self.assertEqual(EmailToSyncPerson.Type.RECIPIENT, related2.type)
        self.assertEqual(linked_contact.email,             related2.email)
        self.assertEqual(linked_contact,                   related2.person)

    def test_fix_email_to_sync02(self):
        "No emails credentials."
        user = self.login_as_standard(
            allowed_apps=['persons'],  # <===
        )

        e2s = EmailToSync.objects.create(user=user, subject='Fw: I want a swordfish')

        linked_contact = user.linked_contact
        EmailToSyncPerson.objects.create(
            email_to_sync=e2s,
            type=EmailToSyncPerson.Type.SENDER,
            email=linked_contact.email,
            person=linked_contact,
        )

        self.assertGET403(reverse('emails__fix_email_to_sync', args=(e2s.id,)))

    def test_fix_email_to_sync03(self):
        "No emails credentials."
        user = self.login_as_root_and_get()
        e2s = EmailToSync.objects.create(user=user, subject='Fw: I want a swordfish')

        contact1 = user.linked_contact
        contact2 = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel', email='spiegel@bebop.spc',
        )

        create_person = partial(EmailToSyncPerson.objects.create, email_to_sync=e2s)
        create_person(
            type=EmailToSyncPerson.Type.SENDER,
            email=contact1.email,
            person=contact1,
        )
        create_person(
            type=EmailToSyncPerson.Type.RECIPIENT,
            email=contact2.email,
            person=contact2,
        )

        self.assertGET409(reverse('emails__fix_email_to_sync', args=(e2s.id,)))

    def test_fix_email_to_sync04(self):
        "Sender/recipient must have an email address."
        user = self.login_as_root_and_get()

        e2s = EmailToSync.objects.create(user=user, subject='Fw: I want a swordfish')

        contact1 = user.linked_contact
        EmailToSyncPerson.objects.create(
            email_to_sync=e2s,
            type=EmailToSyncPerson.Type.SENDER,
            email=contact1.email,
            person=contact1,
        )

        contact2 = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
            # email='...',
        )
        url = reverse('emails__fix_email_to_sync', args=(e2s.id,))
        response1 = self.assertPOST200(
            url,
            data={
                'subject':   e2s.subject,
                'sender':    self.formfield_value_generic_entity(contact2),
                'recipient': self.formfield_value_generic_entity(contact1),
            },
        )
        msg = _('This entity has no email address.')
        self.assertFormError(response1.context['form'], field='sender', errors=msg)

        # ---
        response2 = self.assertPOST200(
            url,
            data={
                'subject':   e2s.subject,
                'sender':    self.formfield_value_generic_entity(contact1),
                'recipient': self.formfield_value_generic_entity(contact2),
            },
        )
        self.assertFormError(response2.context['form'], field='recipient', errors=msg)

    @skipIfCustomContact
    def test_accept_email_to_sync01(self):
        user = self.login_as_emails_user()

        create_e2s = partial(EmailToSync.objects.create, user=user)
        e2s1 = create_e2s(
            subject='I want a swordfish I',
            body="Hello,\nI'd prefer a blue one.\n Have a good day.",
            body_html="Hello,\nI'd prefer a <b>blue</b> one.\nHave a nice day.",
        )
        e2s2 = create_e2s(
            subject='I want a swordfish II',
            body="Hello,\nI'd prefer a green one.\n Thx.",
        )

        sender_contact = user.linked_contact

        create_contact = partial(Contact.objects.create, user=user)
        contact1 = create_contact(
            first_name='Spike', last_name='Spiegel', email='spiegel@bebop.spc',
        )
        contact2 = create_contact(
            first_name='Jet', last_name='Black', email='black@bebop.spc',
        )

        create_person = EmailToSyncPerson.objects.create
        sender1 = create_person(
            email_to_sync=e2s1,
            type=EmailToSyncPerson.Type.SENDER,
            email=sender_contact.email,
            person=sender_contact,
        )
        recipient11 = create_person(
            email_to_sync=e2s1,
            type=EmailToSyncPerson.Type.RECIPIENT,
            email=contact1.email,
            person=contact1,
        )
        recipient12 = create_person(
            email_to_sync=e2s1,
            type=EmailToSyncPerson.Type.RECIPIENT,
            email=contact2.email,
            person=contact2,
            is_main=True,
        )

        sender2 = create_person(
            email_to_sync=e2s2,
            type=EmailToSyncPerson.Type.SENDER,
            email=sender_contact.email,
            person=sender_contact,
        )
        recipient2 = create_person(
            email_to_sync=e2s2,
            type=EmailToSyncPerson.Type.RECIPIENT,
            email=contact1.email,
            person=contact1,
            is_main=True,
        )

        file_name = 'test_accept_email_to_sync01.txt'
        attached_file = FileRef.objects.create(
            user=user,
            filedata=self._create_file_for_document(file_name),
            temporary=False,
        )
        e2s1.attachments.add(attached_file)

        url = self.ACCEPT_EMAIL_URL
        data = {'ids': f'{e2s1.id},{e2s2.id}'}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)

        # ---
        email1 = self.get_object_or_fail(EntityEmail, subject=e2s1.subject)
        self.assertEqual(EntityEmail.Status.SYNCHRONIZED, email1.status)
        self.assertEqual(e2s1.body,                       email1.body)
        self.assertEqual(e2s1.body_html,                  email1.body_html)
        self.assertEqual(sender_contact.email,            email1.sender)
        self.assertEqual(recipient12.email,               email1.recipient)
        self.assertIsNone(email1.sending_date)
        self.assertIsNone(email1.reception_date)
        self.assertIs(email1.synchronised, True)

        self.assertHaveRelation(email1, type=REL_SUB_MAIL_SENT,     object=sender_contact)
        self.assertHaveNoRelation(email1, type=REL_SUB_MAIL_RECEIVED, object=sender_contact)

        self.assertHaveRelation(email1, type=REL_SUB_MAIL_RECEIVED, object=contact1)
        self.assertHaveNoRelation(email1, type=REL_SUB_MAIL_SENT,     object=contact1)
        self.assertHaveRelation(email1, type=REL_SUB_MAIL_RECEIVED, object=contact2)

        attachment = self.get_alone_element(email1.attachments.all())
        self.assertEqual(file_name, attachment.title)

        path = attachment.filedata.path
        self.assertEqual(attached_file.filedata.path, path)
        self.assertTrue(exists(path))

        folder = attachment.linked_folder
        self.assertUUIDEqual(UUID_FOLDER_CAT_EMAILS, folder.category.uuid)
        self.assertEqual(
            _("{username}'s files received by email").format(
                username=user.username,
            ),
            folder.title,
        )
        self.assertIsNone(folder.parent_folder)

        self.assertDoesNotExist(attached_file)
        self.assertDoesNotExist(sender1)
        self.assertDoesNotExist(recipient11)
        self.assertDoesNotExist(recipient12)
        self.assertDoesNotExist(e2s1)

        # ---
        email2 = self.get_object_or_fail(EntityEmail, subject=e2s2.subject)
        self.assertEqual(e2s2.body, email2.body)
        self.assertFalse(email2.body_html)
        self.assertEqual(sender2.email,    email2.sender)
        self.assertEqual(recipient2.email, email2.recipient)

    def test_accept_email_to_sync02(self):
        "Reception date + only one recipient."
        user = self.login_as_root_and_get()

        reception_date = self.create_datetime(
            year=2022, month=1, day=11, hour=16, minute=25,
        )
        e2s = EmailToSync.objects.create(
            user=user,
            subject='I want a swordfish II',
            body="Hello,\nI'd prefer a blue one.\n Have a good day.",
            date=reception_date,
        )

        sender_contact = user.linked_contact
        recipient_contact = Contact.objects.create(
            user=user, first_name='Jet', last_name='Black',
        )

        create_person = partial(EmailToSyncPerson.objects.create, email_to_sync=e2s)
        create_person(
            type=EmailToSyncPerson.Type.SENDER,
            email=sender_contact.email,
            person=sender_contact,
        )
        create_person(
            type=EmailToSyncPerson.Type.RECIPIENT,
            email=recipient_contact.email,
            person=recipient_contact,
            # is_main=True, => not needed
        )

        self.assertPOST200(self.ACCEPT_EMAIL_URL, data={'ids': e2s.id})

        email = self.get_object_or_fail(EntityEmail, subject=e2s.subject)
        self.assertIsNone(email.sending_date)
        self.assertEqual(reception_date, email.reception_date)

    @skipIfCustomContact
    def test_accept_email_to_sync03(self):
        "Folder already exists."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        create_folder = partial(
            Folder.objects.create,
            category=FolderCategory.objects.get(uuid=UUID_FOLDER_CAT_EMAILS),
        )
        create_folder(user=other_user, title='Not mine')
        folder = create_folder(user=user, title='Mine')
        create_folder(user=user, title='Mine too')

        e2s = EmailToSync.objects.create(
            user=user,
            subject='I want a swordfish II',
            body="Hello,\nI'd prefer a blue one.\n Have a good day.",
        )

        sender_contact = user.linked_contact
        recipient_contact = other_user.linked_contact

        create_person = partial(EmailToSyncPerson.objects.create, email_to_sync=e2s)
        create_person(
            type=EmailToSyncPerson.Type.SENDER,
            email=sender_contact.email,
            person=sender_contact,
        )
        create_person(
            type=EmailToSyncPerson.Type.RECIPIENT,
            email=recipient_contact.email,
            person=recipient_contact,
            is_main=True,
        )

        file_name = 'test_accept_email_to_sync02.txt'
        attached_file = FileRef.objects.create(
            user=user,
            filedata=self._create_file_for_document(file_name),
            temporary=False,
        )
        e2s.attachments.add(attached_file)

        self.assertPOST200(self.ACCEPT_EMAIL_URL, data={'ids': e2s.id})
        email = self.get_object_or_fail(EntityEmail, subject=e2s.subject)

        attachment = self.get_alone_element(email.attachments.all())
        self.assertEqual(folder, attachment.linked_folder)

    def test_accept_email_to_sync_perm01(self):
        "No emails credentials."
        user = self.login_as_standard(
            allowed_apps=['persons'],  # <====
        )

        e2s = EmailToSync.objects.create(
            user=user,
            subject='I want a swordfish II',
            body="Hello,\nI'd prefer a blue one.\n Have a good day.",
        )
        self.assertPOST403(self.ACCEPT_EMAIL_URL, data={'ids': e2s.id})

    def test_accept_email_to_sync_perm02(self):
        "Not owner."
        self.login_as_emails_user()

        e2s = EmailToSync.objects.create(
            user=self.get_root_user(),  # <====
            subject='I want a swordfish II',
            body="Hello,\nI'd prefer a blue one.\n Have a good day.",
        )
        self.assertPOST403(self.ACCEPT_EMAIL_URL, data={'ids': e2s.id})

    def test_accept_email_to_sync_perm03(self):
        "Not owner but staff."
        self.login_as_super(is_staff=True)

        other_user = self.get_root_user()
        e2s = EmailToSync.objects.create(
            user=other_user,
            subject='I want a swordfish II',
            body="Hello,\nI'd prefer a blue one.\n Have a good day.",
        )

        sender_contact = Contact.objects.create(
            user=other_user, first_name='Akane', last_name='Tendô',
        )
        recipient_contact = other_user.linked_contact

        create_person = partial(EmailToSyncPerson.objects.create, email_to_sync=e2s)
        create_person(
            type=EmailToSyncPerson.Type.SENDER,
            email=sender_contact.email,
            person=sender_contact,
        )
        create_person(
            type=EmailToSyncPerson.Type.RECIPIENT,
            email=recipient_contact.email,
            person=recipient_contact,
            is_main=True,
        )

        self.assertPOST200(self.ACCEPT_EMAIL_URL, data={'ids': e2s.id})

    @skipIfCustomContact
    def test_accept_email_to_sync_error01(self):
        "No sender, 2 senders (should not happen)."
        user = self.login_as_root_and_get()

        e2s = EmailToSync.objects.create(
            user=user,
            subject='I want a swordfish II',
            body="Hello,\nI'd prefer a blue one.\n Have a good day.",
        )

        recipient_contact = Contact.objects.create(user=user, first_name='Jet', last_name='Black')

        create_person = partial(EmailToSyncPerson.objects.create, email_to_sync=e2s)
        create_person(
            type=EmailToSyncPerson.Type.RECIPIENT,
            email=recipient_contact.email,
            person=recipient_contact,
            is_main=True,
        )

        url = self.ACCEPT_EMAIL_URL
        data = {'ids': e2s.id}
        msg = 'There must be one & only one sender'
        response1 = self.assertPOST409(url, data=data)
        self.assertDictEqual(
            {
                'count': 1,
                'errors': [msg],
            },
            response1.json(),
        )

        # ---
        for sender_contact in (
            user.linked_contact,
            Contact.objects.create(user=user, first_name='Jet', last_name='Black'),
        ):
            create_person(
                type=EmailToSyncPerson.Type.SENDER,
                email=sender_contact.email,
                person=sender_contact,
            )

        response2 = self.assertPOST409(url, data=data)
        self.assertDictEqual(
            {
                'count': 1,
                'errors': [msg],
            },
            response2.json(),
        )

    def test_accept_email_to_sync_error02(self):
        "No main recipient."
        user = self.login_as_root_and_get()

        e2s = EmailToSync.objects.create(
            user=user,
            subject='I want a swordfish II',
            body="Hello,\nI'd prefer a blue one.\n Have a good day.",
        )

        sender_contact = user.linked_contact
        recipient_contact1 = self.create_user(0).linked_contact
        recipient_contact2 = self.create_user(1).linked_contact

        create_person = partial(EmailToSyncPerson.objects.create, email_to_sync=e2s)
        create_person(
            type=EmailToSyncPerson.Type.SENDER,
            email=sender_contact.email,
            person=sender_contact,
        )
        for recipient_contact in (recipient_contact1, recipient_contact2):
            create_person(
                type=EmailToSyncPerson.Type.RECIPIENT,
                email=recipient_contact.email,
                person=recipient_contact,
                is_main=False,
            )

        response = self.assertPOST409(self.ACCEPT_EMAIL_URL, data={'ids': e2s.id})
        self.assertDictEqual(
            {
                'count': 1,
                'errors': [_('There is no recipient marked as main')],
            },
            response.json(),
        )

    def test_accept_email_to_sync_error03(self):
        "Sender is not complete (no related person)."
        user = self.login_as_root_and_get()

        e2s = EmailToSync.objects.create(
            user=user,
            subject='I want a swordfish II',
            body="Hello,\nI'd prefer a blue one.\nHave a good day.",
        )

        recipient_contact = self.create_user().linked_contact

        create_person = partial(EmailToSyncPerson.objects.create, email_to_sync=e2s)
        create_person(
            type=EmailToSyncPerson.Type.SENDER,
            email='spike@bebop.spc',
            # person=...,
        )
        create_person(
            type=EmailToSyncPerson.Type.RECIPIENT,
            email=recipient_contact.email,
            person=recipient_contact,
            is_main=False,
        )

        response = self.assertPOST409(self.ACCEPT_EMAIL_URL, data={'ids': e2s.id})
        self.assertDictEqual(
            {
                'count': 1,
                'errors': [_('The sender is not associated to a Contact/Organisation')],
            },
            response.json(),
        )

    def test_accept_email_to_sync_error04(self):
        "Recipient is not complete (no related person)."
        user = self.login_as_root_and_get()

        e2s = EmailToSync.objects.create(
            user=user,
            subject='I want a swordfish II',
            body="Hello,\nI'd prefer a blue one.\nHave a good day.",
        )

        sender_contact = self.create_user().linked_contact

        create_person = partial(EmailToSyncPerson.objects.create, email_to_sync=e2s)
        create_person(
            type=EmailToSyncPerson.Type.SENDER,
            email=sender_contact.email,
            person=sender_contact,

        )
        recipient = create_person(
            type=EmailToSyncPerson.Type.RECIPIENT,
            email='spike@bebop.spc',
            # person=...,
            is_main=True,
        )

        response = self.assertPOST409(self.ACCEPT_EMAIL_URL, data={'ids': e2s.id})
        self.assertDictEqual(
            {
                'count': 1,
                'errors': [
                    _(
                        'The recipient «{email}» is not associated to a Contact/Organisation'
                    ).format(email=recipient.email),
                ],
            },
            response.json(),
        )
