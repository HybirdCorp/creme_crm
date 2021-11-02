# -*- coding: utf-8 -*-

from django.template import Context, Template

from ..base import CremeTestCase


class CremeLatexTagsTestCase(CremeTestCase):
    def test_latex_newline(self):
        with self.assertNoException():
            render = Template(
                r'{% load creme_latex %}'
                r'{{text|latex_newline}}'
            ).render(Context({'text': 'Hello world!\nHow are you?'}))

        self.assertEqual(r'Hello world!\newline How are you?', render.strip())

    def test_latex_escape(self):
        with self.assertNoException():
            render = Template(
                r'{% load creme_latex %}'
                r'{{text|latex_escape}}'
            ).render(Context({'text': r'Opportunities ($) > Portal'}))

        self.assertEqual(r'Opportunities (\$) \textgreater Portal', render.strip())
