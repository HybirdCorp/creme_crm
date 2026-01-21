from django.conf import settings
from django.urls import reverse

# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.models import Job
from creme.emails.creme_jobs import entity_emails_send_type

from ..base import EntityEmail, _EmailsTestCase, skipIfCustomEntityEmail


@skipIfCustomEntityEmail
class EntityEmailTestCase(_EmailsTestCase):
    def test_get_sanitized_html_field__empty(self):
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

    def test_get_sanitized_html_field__filled(self):
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

    def test_refresh_job(self):
        "Mail is restored + have to be sent => refresh the job."
        user = self.login_as_root_and_get()
        job = self.get_object_or_fail(Job, type_id=entity_emails_send_type.id)

        email = self._create_email(user=user, status=EntityEmail.Status.SENDING_ERROR)
        email.trash()

        queue = get_queue()
        queue.clear()

        email.restore()
        self.assertFalse(self.refresh(email).is_deleted)

        jobs = queue.refreshed_jobs
        self.assertEqual(1, len(jobs))
        self.assertEqual(job, jobs[0][0])

    def test_refresh_job__useless(self):
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
