from creme.documents.tests.base import (
    DocumentsTestCaseMixin,
    skipIfCustomDocument,
)

from ..base import EmailTemplate, _EmailsTestCase, skipIfCustomEmailTemplate


@skipIfCustomEmailTemplate
class EmailTemplateTestCase(DocumentsTestCaseMixin, _EmailsTestCase):
    @skipIfCustomDocument
    def test_clone(self):
        user = self.login_as_root_and_get()

        file_obj = self.build_filedata('Content #1')
        doc = self._create_doc('My doc #1', file_obj=file_obj, user=user)

        template = EmailTemplate.objects.create(
            user=user, name='My template',
            subject='Insert a joke *here*', body='blablabla',
            body_html='<p>blablabla</p>',
        )
        template.attachments.add(doc)

        cloned_template = self.clone(template)
        self.assertIsInstance(cloned_template, EmailTemplate)
        self.assertNotEqual(template.pk, cloned_template.pk)
        self.assertEqual(template.name,      cloned_template.name)
        self.assertEqual(template.subject,   cloned_template.subject)
        self.assertEqual(template.body,      cloned_template.body)
        self.assertEqual(template.body_html, cloned_template.body_html)
        self.assertCountEqual([doc], cloned_template.attachments.all())

    # @skipIfCustomDocument
    # def test_clone__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     file_obj = self.build_filedata('Content #1')
    #     doc = self._create_doc('My doc #1', file_obj=file_obj, user=user)
    #
    #     template = EmailTemplate.objects.create(
    #         user=user, name='My template',
    #         subject='Insert a joke *here*', body='blablabla',
    #         body_html='<p>blablabla</p>',
    #     )
    #     template.attachments.add(doc)
    #
    #     cloned_template = template.clone()
    #     self.assertIsInstance(cloned_template, EmailTemplate)
    #     self.assertNotEqual(template.pk, cloned_template.pk)
    #     self.assertEqual(template.name,      cloned_template.name)
    #     self.assertEqual(template.subject,   cloned_template.subject)
    #     self.assertEqual(template.body,      cloned_template.body)
    #     self.assertEqual(template.body_html, cloned_template.body_html)
    #     self.assertCountEqual([doc], cloned_template.attachments.all())
