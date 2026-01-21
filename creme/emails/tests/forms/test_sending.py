from copy import deepcopy

from django import forms
from django.core.validators import EmailValidator
from django.utils.translation import gettext as _

from creme.creme_core.tests.base import CremeTestCase
from creme.emails.forms.sending import SendingConfigField
from creme.emails.models import EmailSendingConfigItem


class SendingConfigFieldTestCase(CremeTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_config = EmailSendingConfigItem.objects.create
        cls.item1 = create_config(
            name='Config #1',
            host='smail.mydomain.org',
            username='jet',
            password='c0w|3OY B3b0P',
            default_sender='jet@mydomain.org',
        )
        cls.item2 = create_config(
            name='Config #2',
            host='smtp.mydomain.org',
            username='spike',
            password='sp4c3 c0w|3OY',
        )

    def test_configuration_class(self):
        email1 = 'jet@mydomain.org'
        conf1 = SendingConfigField.Configuration(item=self.item1, sender=email1)
        self.assertEqual(self.item1, conf1.item)
        self.assertEqual(email1,     conf1.sender)

        email2 = 'spike@mydomain.org'
        conf2 = SendingConfigField.Configuration(item=self.item2, sender=email2)
        self.assertEqual(self.item2, conf2.item)
        self.assertEqual(email2,     conf2.sender)

        self.assertTrue(bool(conf1))
        self.assertNotEqual(conf1, None)
        self.assertNotEqual(conf1, conf2)
        self.assertEqual(
            SendingConfigField.Configuration(item=self.item1, sender=email1),
            conf1,
        )
        self.assertNotEqual(
            SendingConfigField.Configuration(item=self.item2, sender=email1),
            conf1,
        )
        self.assertNotEqual(
            SendingConfigField.Configuration(item=self.item1, sender=email2),
            conf1,
        )

    def test_ok(self):
        item1 = self.item1
        item2 = self.item2
        field = SendingConfigField()

        self.assertListEqual(
            [
                (str(item1.id), item1.name, {'default_sender': item1.default_sender}),
                (str(item2.id), item2.name, {'default_sender': ''}),
            ],
            [*field.widget.choices],
        )

        sender = 'jet@mydomain.org'
        self.assertEqual(
            SendingConfigField.Configuration(item=item1, sender=sender),
            field.clean([item1.id, sender]),
        )

    def test_ok__init(self):
        sender = 'spike@mydomain.org'
        item = self.item2
        self.assertEqual(
            SendingConfigField.Configuration(item=item, sender=sender),
            SendingConfigField().clean([item.id, sender]),
        )

    def test_required(self):
        field = SendingConfigField()
        msg = _('This field is required.')
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=['', ''],
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=None,
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=[self.item1.id, ''],
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=['', 'spike@mydomain.org'],
        )

    def test_not_required(self):
        clean = SendingConfigField(required=False).clean
        self.assertIsNone(clean(['', '']))
        self.assertIsNone(clean(['']))
        self.assertIsNone(clean([]))
        self.assertIsNone(clean(None))
        self.assertIsNone(clean([self.item1.id, '']))
        self.assertIsNone(clean(['', 'spike@mydomain.org']))

    def test_invalid_pk(self):
        self.assertFormfieldError(
            field=SendingConfigField(),
            value=[self.UNUSED_PK, 'spike@mydomain.org'],
            messages=forms.ModelChoiceField.default_error_messages['invalid_choice'],
            codes='invalid_choice',
        )

    def test_invalid_email(self):
        self.assertFormfieldError(
            field=SendingConfigField(),
            value=[self.item1.id, 'not an email'],
            messages=EmailValidator.message,
            codes='invalid',
        )

    def test_widget(self):
        field1 = SendingConfigField()
        item1 = self.item1
        item2 = self.item2
        expected = [
            (str(item1.id), item1.name, {'default_sender': item1.default_sender}),
            (str(item2.id), item2.name, {'default_sender': item2.default_sender}),
        ]
        self.assertListEqual(expected, [*field1.widget.choices])
        self.assertEqual(2, len(field1.queryset))  # We force the evaluation of the queryset

        field2 = deepcopy(field1)
        item3 = EmailSendingConfigItem.objects.create(
            name='Config #3',
            host='smtp2.mydomain.org',
            username='faye',
            password='c0w|3OY B3b0P',
            default_sender='faye@mydomain.org',
        )
        self.assertEqual(3, len(field2.queryset))
        self.assertListEqual(
            [
                *expected,
                (str(item3.id), item3.name, {'default_sender': item3.default_sender}),
            ],
            [*field2.widget.choices],
        )
