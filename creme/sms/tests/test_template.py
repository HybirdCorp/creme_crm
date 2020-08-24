# -*- coding: utf-8 -*-

from django.urls import reverse
from django.utils.lorem_ipsum import COMMON_P
from django.utils.translation import gettext as _

from creme.creme_core.tests.base import CremeTestCase

from .base import MessageTemplate, skipIfCustomMessageTemplate


@skipIfCustomMessageTemplate
class MessageTemplateTestCase(CremeTestCase):
    def test_createview01(self):
        user = self.login()

        url = reverse('sms__create_template')
        self.assertGET200(url)

        name = 'My template #1'
        subject = 'Our new release is available!'
        body = 'The version 3.0 contains 25120 new awesome features.'
        response = self.client.post(
            url, follow=True,
            data={
                'user': user.pk,
                'name': name,
                'subject': subject,
                'body': body,
            },
        )
        self.assertNoFormError(response)

        msg_template = self.get_object_or_fail(MessageTemplate, name=name)
        self.assertEqual(user,    msg_template.user)
        self.assertEqual(subject, msg_template.subject)
        self.assertEqual(body,    msg_template.body)

        # ----
        response = self.assertGET200(msg_template.get_absolute_url())
        self.assertTemplateUsed(response, 'sms/view_template.html')

    def test_createview02(self):
        "Message too long."
        user = self.login()

        url = reverse('sms__create_template')
        error_msg = _('Message is too long (%(length)s > %(max_length)s)')

        def post(subject, body, error, special_chars_count=0):
            response = self.assertPOST200(
                url, follow=True,
                data={
                    'user': user.pk,
                    'name': 'My template',
                    'subject': subject,
                    'body': body,
                },
            )
            if error:
                self.assertFormError(
                    response, 'form', None,
                    error_msg % {
                        'length': len(subject) + len(body) + 3 + special_chars_count,
                        'max_length': 160,
                    }
                )
            else:
                self.assertNoFormError(response)

        def build_body(prefix, length):
            return prefix + COMMON_P[:length - len(prefix)]

        post(
            subject='Subject with 26 characters',
            body=build_body(
                # NB: 3 is for ' : '
                'Body with 160 - 26 - 3 = 131 characters in order to use the '
                'maximum allowed length.',
                length=131,
            ),
            error=False,
        )
        post(
            subject='Subject with 26 characters',
            body=build_body(
                # NB: 3 is for ' : '
                'Body with 160 - 26 - 3 + 1 = 132 characters in order to exceed '
                'the maximum allowed length.',
                length=132,
            ),
            error=True,
        )
        post(
            subject='Subject with 26 characters',
            body=build_body(
                # NB: 3 is for ' : '
                'Body with 160 - 26 - 3 = 131 characters, '
                'but with the character € which count for 2, '
                'in order to exceed the maximum allowed length.',
                length=130,
            ),
            error=True,
            special_chars_count=1,
        )

    def test_editview(self):
        user = self.login()

        template = MessageTemplate.objects.create(
            user=user,
            name='my first template',
            subject='Insert a joke *here*',
            body='blablabla',
        )

        url = template.get_edit_absolute_url()
        self.assertGET200(url)

        name    = template.name.title()
        subject = template.subject.title()
        body    = f'{template.body} edited'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':    user.pk,
                'name':    name,
                'subject': subject,
                'body':    body,
            },
        )
        self.assertNoFormError(response)

        template = self.refresh(template)
        self.assertEqual(name,    template.name)
        self.assertEqual(subject, template.subject)
        self.assertEqual(body,    template.body)

    def test_listview(self):
        user = self.login()
        template1 = MessageTemplate.objects.create(
            user=user,
            name='My first template',
            subject='Insert a joke *here*',
            body='blablabla',
        )
        template2 = MessageTemplate.objects.create(
            user=user,
            name='My second template',
            subject='Insert another joke *here*',
            body='blablabla',
        )

        response = self.assertGET200(MessageTemplate.get_lv_absolute_url())

        with self.assertNoException():
            tplt_page = response.context['page_obj']

        self.assertEqual(2, tplt_page.paginator.count)
        self.assertSetEqual({template1, template2}, {*tplt_page.object_list})
