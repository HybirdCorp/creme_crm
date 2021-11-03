# -*- coding: utf-8 -*-

from django.template import Context, Template

from creme.creme_core.tests.base import CremeTestCase


class SMSTagsTestCase(CremeTestCase):
    def test_phonenumber(self):
        with self.assertNoException():
            render = Template(
                r'{% load sms_tags %}'
                r'{{"123"|sms_phonenumber}}'
                r'#{{"AAA-456"|sms_phonenumber}}'
            ).render(Context({}))

        self.assertEqual('123#456', render.strip())

    def test_formatphone(self):
        with self.assertNoException():
            render = Template(
                r'{% load sms_tags %}'
                r'#{{""|sms_formatphone}}'
                r'#{{"12345"|sms_formatphone}}'
                r'#{{"67891011"|sms_formatphone}}'
                r'#{{"678910111"|sms_formatphone}}'
                r'#'
            ).render(Context({}))

        self.assertEqual('##12345#67 89 10 11#678 91 01 11#', render.strip())
