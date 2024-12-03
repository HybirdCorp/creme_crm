from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.core.notification import (
    OUTPUT_EMAIL,
    OUTPUT_WEB,
    NotificationChannelType,
    NotificationContent,
    NotificationRegistry,
    Output,
    RelatedToModelBaseContent,
    SimpleNotifContent,
    notification_registry,
)
from creme.creme_core.models import CremeEntity, FakeOrganisation, FakeSector
from creme.creme_core.tests.base import CremeTestCase

TEST_OUTPUT_SMTP = Output('smtp')
TEST_OUTPUT_HTTP = Output('http')
TEST_OUTPUT_XMPP = Output('xmpp')


class DummyChannelType1(NotificationChannelType):
    id = NotificationChannelType.generate_id('creme_core', 'dummy1')


class DummyChannelType2(NotificationChannelType):
    id = NotificationChannelType.generate_id('creme_core', 'dummy2')


class DummyContent(NotificationContent):
    id = NotificationContent.generate_id('creme_core', 'dummy')


class DummyWebContent(DummyContent):
    pass


class DummyEmailContent(DummyContent):
    pass


class NotificationTestCase(CremeTestCase):
    def test_content_simple01(self):
        user = self.get_root_user()
        subject = 'Alert!'
        body = 'Your meeting is about to start.'
        snc = SimpleNotifContent(subject=subject, body=body)
        self.assertEqual('creme_core-simple', snc.id)
        self.assertEqual(subject,   snc.get_subject(user))
        self.assertEqual(body,      snc.get_body(user))
        self.assertEqual('',        snc.get_html_body(user))
        self.assertDictEqual({'subject': subject, 'body': body}, snc.as_dict())

    def test_content_simple02(self):
        user = self.get_root_user()
        subject = 'Alert!'
        body = 'Your meeting is about to start.'
        html_body = 'Your meeting is <strong>about to start</strong>.'
        snc = SimpleNotifContent(subject=subject, body=body, html_body=html_body)
        self.assertEqual('creme_core-simple', snc.id)
        self.assertEqual(subject,   snc.get_subject(user))
        self.assertEqual(body,      snc.get_body(user))
        self.assertEqual(html_body, snc.get_html_body(user))
        self.assertDictEqual(
            {'subject': subject, 'body': body, 'html_body': html_body},
            snc.as_dict(),
        )

    def test_content_eq(self):
        subject = 'Beware!'
        body = 'The invoice has not been paid!'
        simple = SimpleNotifContent(subject=subject, body=body)
        self.assertEqual(simple, SimpleNotifContent(subject=subject, body=body))
        self.assertNotEqual(simple, SimpleNotifContent(subject='Other', body=body))
        self.assertNotEqual(simple, SimpleNotifContent(subject=subject, body='Other'))

        class DummyContent(SimpleNotifContent):
            id = SimpleNotifContent.generate_id('creme_core', 'dummy')

        self.assertNotEqual(simple, DummyContent(subject=subject, body=body))
        self.assertNotEqual(simple, 'a string')

    def test_registry01(self):
        registry = NotificationRegistry()
        self.assertListEqual([], [*registry.output_choices])

        registry.register_output(
            value=TEST_OUTPUT_HTTP, label='Web',
        ).register_output(
            value=TEST_OUTPUT_SMTP, label='Mail',
        ).register_output(
            value=TEST_OUTPUT_XMPP, label='XMPP',
        )
        self.assertListEqual(
            [('http', 'Web'), ('smtp', 'Mail'), ('xmpp', 'XMPP')],
            [*registry.output_choices],
        )

        # ---
        self.assertIsNone(registry.get_channel_type(DummyChannelType1.id))
        self.assertIsNone(registry.get_channel_type(DummyChannelType2.id))

        registry.register_channel_types(DummyChannelType1)
        self.assertIsInstance(
            registry.get_channel_type(DummyChannelType1.id),
            DummyChannelType1,
        )
        self.assertIsNone(registry.get_channel_type(DummyChannelType2.id))

        # ---
        get_ct_cls = registry.get_content_class

        # First registered => default
        registry.register_content(
            content_cls=DummyWebContent, output=TEST_OUTPUT_HTTP,
        ).register_content(
            content_cls=DummyEmailContent, output=TEST_OUTPUT_SMTP,
        )
        self.assertIs(
            DummyWebContent,
            get_ct_cls(output=TEST_OUTPUT_HTTP, content_id=DummyContent.id),
        )
        self.assertIs(
            DummyEmailContent,
            get_ct_cls(output=TEST_OUTPUT_SMTP, content_id=DummyContent.id),
        )

    def test_registry_output_errors(self):
        registry = NotificationRegistry().register_output(
            value=TEST_OUTPUT_HTTP, label='Web',
        )

        with self.assertRaises(registry.RegistrationError):
            registry.register_output(value=Output(''), label='Void')

        with self.assertRaises(registry.RegistrationError):
            registry.register_output(value=Output(TEST_OUTPUT_HTTP), label='Http')

    def test_registry_channel_type(self):
        "Multi register."
        registry = NotificationRegistry().register_channel_types(
            DummyChannelType1,
            DummyChannelType2,
        )
        self.assertIsInstance(
            registry.get_channel_type(DummyChannelType1.id),
            DummyChannelType1,
        )
        self.assertIsInstance(
            registry.get_channel_type(DummyChannelType2.id),
            DummyChannelType2,
        )

    def test_registry_channel_type_errors(self):
        registry = NotificationRegistry()

        with self.assertLogs(level='WARNING') as logs_manager:
            registry.get_channel_type('unknown')
        self.assertListEqual(
            logs_manager.output,
            [
                'WARNING:'
                'creme.creme_core.core.notification:'
                'The channel type "unknown" is invalid.'
            ],
        )

        # --
        class InvalidChanType(NotificationChannelType):
            pass

        with self.assertRaises(registry.RegistrationError):
            registry.register_channel_types(InvalidChanType)

        # ---
        class DupChanType(NotificationChannelType):
            id = DummyChannelType1.id

        with self.assertRaises(registry.RegistrationError):
            registry.register_channel_types(DummyChannelType1, DupChanType)

    def test_registry_content_default01(self):
        registry = NotificationRegistry().register_output(
            value=TEST_OUTPUT_HTTP, label='Web',
        ).register_output(
            value=TEST_OUTPUT_SMTP, label='Mail',
        ).register_content(
            content_cls=DummyContent,
        )
        self.assertIs(
            DummyContent,
            registry.get_content_class(
                output=str(TEST_OUTPUT_HTTP), content_id=DummyContent.id,
            ),
        )
        self.assertIs(
            DummyContent,
            registry.get_content_class(
                output=str(TEST_OUTPUT_SMTP), content_id=DummyContent.id,
            ),
        )

        # Specialisation => no error
        class SMTPDummyContent(DummyContent):
            pass

        registry.register_content(
            content_cls=SMTPDummyContent, output=TEST_OUTPUT_SMTP,
        )

    def test_registry_content_default02(self):
        registry = NotificationRegistry().register_output(
            value=TEST_OUTPUT_HTTP, label='Web',
        ).register_output(
            value=TEST_OUTPUT_SMTP, label='Mail',
        ).register_content(
            content_cls=DummyWebContent, output=TEST_OUTPUT_HTTP,  # first => default
        )
        self.assertIs(
            DummyWebContent,
            registry.get_content_class(output=TEST_OUTPUT_HTTP, content_id=DummyContent.id),
        )
        self.assertIs(
            DummyWebContent,
            registry.get_content_class(output=TEST_OUTPUT_SMTP, content_id=DummyContent.id),
        )

    def test_registry_content_errors01(self):
        registry = NotificationRegistry().register_output(
            value=TEST_OUTPUT_HTTP, label='Web',
        ).register_content(
            content_cls=DummyWebContent, output=TEST_OUTPUT_HTTP,
        )

        class InvalidContent(NotificationContent):
            pass

        with self.assertRaises(registry.RegistrationError):
            registry.register_content(content_cls=InvalidContent)  # output=TEST_OUTPUT_HTTP

        # ---
        with self.assertRaises(registry.RegistrationError):
            registry.register_content(
                content_cls=DummyWebContent,
                output=TEST_OUTPUT_SMTP,  # <==
            )

        # ---
        class DupContent(NotificationContent):
            id = DummyWebContent.id

        with self.assertRaises(registry.RegistrationError):
            registry.register_content(content_cls=DupContent, output=TEST_OUTPUT_HTTP)

    def test_registry_content_errors02(self):
        registry = NotificationRegistry().register_output(
            value=TEST_OUTPUT_HTTP, label='Web',
        ).register_content(
            content_cls=DummyWebContent, output=TEST_OUTPUT_HTTP,
        )

        with self.assertRaises(KeyError):
            registry.get_content_class(
                output=TEST_OUTPUT_SMTP, content_id=DummyWebContent.id,
            )

    def test_registry_content_fallback(self):
        registry = NotificationRegistry().register_output(
            value=TEST_OUTPUT_HTTP, label='Web',
        )

        with self.assertLogs(level='CRITICAL') as logs_manager:
            with self.assertNoException():
                content_cls = registry.get_content_class(
                    output=TEST_OUTPUT_HTTP,
                    content_id=DummyWebContent.id,  # <= not registered
                )

        self.assertIs(content_cls, registry.FallbackContent)
        self.assertListEqual(
            logs_manager.output,
            [
                'CRITICAL:'
                'creme.creme_core.core.notification:the notification content ID '
                '"creme_core-dummy" is invalid (have you deleted the content '
                'class without cleaning the data base?)'
            ],
        )

        content = content_cls.from_dict({'some': 'unused data'})
        user = self.get_root_user()
        self.assertEqual(
            _('Notification (type cannot be determined)'),
            content.get_subject(user=user),
        )
        msg = _('Please contact your administrator')
        self.assertEqual(msg, content.get_body(user=user))
        self.assertEqual(msg, content.get_html_body(user=user))

    def test_global_registry(self):
        self.assertIs(
            SimpleNotifContent,
            notification_registry.get_content_class(
                output=OUTPUT_WEB, content_id=SimpleNotifContent.id,
            ),
        )
        self.assertIs(
            SimpleNotifContent,
            notification_registry.get_content_class(
                output=OUTPUT_EMAIL, content_id=SimpleNotifContent.id,
            ),
        )

    def test_related_to_model_content01(self):
        "CremeEntity."
        class RelatedToOrganisation(RelatedToModelBaseContent):
            model = CremeEntity

        ContentType.objects.get_for_model(CremeEntity)  # NB: fill cache

        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')

        content1 = RelatedToOrganisation(instance=orga)
        data = content1.as_dict()
        self.assertDictEqual({'instance': orga.id}, data)

        with self.assertNumQueries(0):
            self.assertEqual(f'Related to «{orga}»', content1.get_body(user))

        with self.assertNumQueries(0):
            self.assertEqual(str(orga), content1.get_subject(user))

        with self.assertNumQueries(0):
            self.assertHTMLEqual(
                f'Related to:<a href={orga.get_absolute_url()} target="_self">{orga}</a>',
                content1.get_html_body(user),
            )

        # ---
        content2 = RelatedToOrganisation.from_dict(data)
        self.assertIsInstance(content2, RelatedToOrganisation)

        with self.assertNumQueries(0):
            self.assertDictEqual({'instance': orga.id}, content2.as_dict())

        with self.assertNumQueries(2):
            self.assertEqual(f'Related to «{orga}»', content2.get_body(user))

        with self.assertNumQueries(0):
            content2.get_body(user)

    def test_related_to_model_content02(self):
        "Specific CremeEntity model."
        class RelatedToOrganisation(RelatedToModelBaseContent):
            model = FakeOrganisation

        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')

        content1 = RelatedToOrganisation(instance=orga)
        data = content1.as_dict()
        self.assertDictEqual({'instance': orga.id}, data)

        with self.assertNumQueries(0):
            self.assertEqual(f'Related to «{orga}»', content1.get_body(user))

        # ---
        content2 = RelatedToOrganisation.from_dict(data)
        self.assertIsInstance(content2, RelatedToOrganisation)

        with self.assertNumQueries(0):
            self.assertDictEqual({'instance': orga.id}, content2.as_dict())

        with self.assertNumQueries(1):  # <= only one here
            self.assertEqual(f'Related to «{orga}»', content2.get_body(user))

    def test_related_to_model_content03(self):
        "Not CremeEntity."
        class RelatedToSector(RelatedToModelBaseContent):
            model = FakeSector

        user = self.get_root_user()
        sector = FakeSector.objects.first()
        content = RelatedToSector(instance=sector)

        self.assertEqual(f'Related to «{sector}»', content.get_body(user))
        self.assertEqual(str(sector),              content.get_subject(user))
        self.assertHTMLEqual(f'Related to: {sector}', content.get_html_body(user))

    def test_related_to_model_content_error(self):
        class RelatedToOrganisation(RelatedToModelBaseContent):
            model = FakeOrganisation

        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        pk = orga.pk
        orga.delete()

        content2 = RelatedToOrganisation.from_dict({'instance': pk})
        self.assertIsInstance(content2, RelatedToOrganisation)

        user = self.get_root_user()

        with self.assertNumQueries(1):
            self.assertEqual('Related to a removed instance', content2.get_body(user))

        with self.assertNumQueries(0):
            self.assertHTMLEqual('Related to a removed instance', content2.get_html_body(user))

        with self.assertNumQueries(0):
            self.assertEqual('??', content2.get_subject(user))
