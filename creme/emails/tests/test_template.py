# -*- coding: utf-8 -*-

try:
    # from json import dumps as json_dump

    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import FakeOrganisation

    from creme.documents.tests.base import _DocumentsTestCase, skipIfCustomDocument

    from .base import _EmailsTestCase, skipIfCustomEmailTemplate, EmailTemplate
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIfCustomEmailTemplate
class TemplatesTestCase(_DocumentsTestCase, _EmailsTestCase):
    def setUp(self):
        self.login()

    def test_createview01(self):  # TODO: test attachments
        url = reverse('emails__create_template')
        self.assertGET200(url)

        name      = 'my_template'
        subject   = 'Insert a joke *here*'
        body      = 'blablabla {{first_name}}'
        body_html = '<p>blablabla {{last_name}}</p>'
        response = self.client.post(url, follow=True,
                                    data={'user':      self.user.pk,
                                          'name':      name,
                                          'subject':   subject,
                                          'body':      body,
                                          'body_html': body_html,
                                         }
                                   )
        self.assertNoFormError(response)

        template = self.get_object_or_fail(EmailTemplate, name=name)
        self.assertEqual(subject,   template.subject)
        self.assertEqual(body,      template.body)
        self.assertEqual(body_html, template.body_html)

        # ----
        response = self.assertGET200(template.get_absolute_url())
        self.assertTemplateUsed(response, 'emails/view_template.html')

    def test_createview02(self):
        "Validation error"
        response = self.assertPOST200(reverse('emails__create_template'), follow=True,
                                      data={'user':      self.user.pk,
                                            'name':      'my_template',
                                            'subject':   'Insert a joke *here*',
                                            'body':      'blablabla {{unexisting_var}}',
                                            'body_html': '<p>blablabla</p> {{foobar_var}}',
                                           }
                                     )

        error_msg = _('The following variables are invalid: %(vars)s')
        self.assertFormError(response, 'form', 'body',
                             error_msg % {'vars': ['unexisting_var']}
                            )
        self.assertFormError(response, 'form', 'body_html',
                             error_msg % {'vars': ['foobar_var']}
                            )

    def test_editview01(self):
        name    = 'my template'
        subject = 'Insert a joke *here*'
        body    = 'blablabla'
        template = EmailTemplate.objects.create(user=self.user, name=name, subject=subject, body=body)

        url = template.get_edit_absolute_url()
        self.assertGET200(url)

        name    = name.title()
        subject = subject.title()
        body    += ' edited'
        response = self.client.post(url, follow=True,
                                    data={'user':    self.user.pk,
                                          'name':    name,
                                          'subject': subject,
                                          'body':    body,
                                         }
                                   )
        self.assertNoFormError(response)

        template = self.refresh(template)
        self.assertEqual(name,    template.name)
        self.assertEqual(subject, template.subject)
        self.assertEqual(body,    template.body)
        self.assertEqual('',      template.body_html)

    def test_listview(self):
        response = self.assertGET200(EmailTemplate.get_lv_absolute_url())

        with self.assertNoException():
            response.context['entities']

    @skipIfCustomDocument
    def test_add_attachments01(self):
        template = EmailTemplate.objects.create(user=self.user,
                                                name='My template',
                                                subject='Insert a joke *here*',
                                                body='blablabla',
                                               )

        file_obj1 = self._build_filedata('Content #1')
        doc1 = self._create_doc('My doc #1', file_obj1)

        file_obj2 = self._build_filedata('Content #2')
        doc2 = self._create_doc('My doc #2', file_obj2)

        url = reverse('emails__add_attachments_to_template', args=(template.id,))

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(_('New attachments for «{entity}»').format(entity=template),
                         context.get('title')
                        )
        self.assertEqual(_('Add the attachments'), context.get('submit_label'))

        response = self.client.post(url, data={'attachments': self.formfield_value_multi_creator_entity(doc1, doc2)})
        self.assertNoFormError(response)
        self.assertEqual({doc1, doc2}, set(template.attachments.all()))

    def test_add_attachments02(self):
        orga = FakeOrganisation.objects.create(user=self.user, name='Acme')
        self.assertGET404(reverse('emails__add_attachments_to_template', args=(orga.id,)))

    # TODO: test delete attachments
