from datetime import datetime, timedelta
from functools import partial

from django.conf import settings
from django.urls import reverse
from django.utils.timezone import localtime, now
from django.utils.translation import gettext as _

from creme.activities.constants import (
    UUID_STATUS_CANCELLED,
    UUID_STATUS_DONE,
    UUID_STATUS_IN_PROGRESS,
    UUID_STATUS_PLANNED,
)
from creme.activities.models import Status
from creme.activities.tests.base import skipIfCustomActivity
from creme.creme_core.models import UserRole

from .base import Activity, Contact, MobileBaseTestCase


class MobileAppTestCase(MobileBaseTestCase):
    def test_core_populate(self):
        role = self.get_object_or_fail(UserRole, name=_('Regular user'))
        self.assertNotIn('mobile', role.allowed_apps)

    def test_login(self):
        url = reverse('mobile__login')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'mobile/login.html')
        self.assertEqual('next', response.context.get('REDIRECT_FIELD_NAME'))

        password = 'passwd'
        user = self.create_user(password=password)
        response = self.assertPOST200(
            url, follow=True,
            data={
                'username': user.username,
                'password': password,
                'next':     self.PORTAL_URL,
            },
        )
        self.assertRedirects(response, self.PORTAL_URL)

    def test_logout(self):
        self.login_as_root()
        response = self.assertPOST200(reverse('mobile__logout'), follow=True)
        self.assertRedirects(response, reverse(settings.LOGIN_URL))

    @skipIfCustomActivity
    def test_portal(self):
        user = self.login_as_root_and_get()
        contact = user.linked_contact
        now_val = localtime(now())

        def today(hour=14, minute=0, second=0):
            return datetime(
                year=now_val.year, month=now_val.month, day=now_val.day,
                hour=hour, minute=minute, second=second,
                tzinfo=now_val.tzinfo,
            )

        past_midnight = today(0)

        def today_in_the_past(near):
            return now_val - (now_val - past_midnight) / near

        def today_in_the_future(near):
            return now_val + (today(23, 59, 59) - now_val) / near

        create_m = partial(self._create_meeting, user=user, participant=contact)
        m1 = create_m(title='Meeting: Manga', start=today_in_the_past(3))
        m2 = create_m(
            title='Meeting: Anime',
            start=today_in_the_past(2),
            status=self.get_object_or_fail(Status, uuid=UUID_STATUS_PLANNED),
        )
        m3 = create_m(
            title='Meeting: Manga #2',
            start=past_midnight,
            floating_type=Activity.FloatingType.FLOATING_TIME,
        )
        m4 = create_m(
            title='Meeting: Figures',
            start=today_in_the_future(3),
            status=self.get_object_or_fail(Status, uuid=UUID_STATUS_IN_PROGRESS),
        )
        m5 = create_m(
            title='Meeting: Figures #3',
            start=today_in_the_future(2),
        )  # Should be after m6
        m6 = create_m(title='Meeting: Figures #2', start=today_in_the_future(3))

        oneday = timedelta(days=1)
        create_m(
            title='Meeting: Tezuka manga',
            start=today(9),
            participant=Contact.objects.create(user=user, first_name='Gally', last_name='Alita'),
        )  # I do not participate
        create_m(
            title='Meeting: Comics',
            start=today(7),
            status=self.get_object_or_fail(Status, uuid=UUID_STATUS_DONE),
        )  # Done are excluded
        create_m(
            title='Meeting: Manhua',
            start=today(10),
            status=self.get_object_or_fail(Status, uuid=UUID_STATUS_CANCELLED),
        )  # Cancelled are excluded
        create_m(title='Meeting: Manga again',  start=now_val - oneday)  # Yesterday
        create_m(title='Meeting: Manga ter.',   start=now_val + oneday)  # Tomorrow

        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'mobile/index.html')

        with self.assertNoException():
            context = response.context
            hot_activities   = [*context['hot_activities']]
            today_activities = [*context['today_activities']]

        self.assertListEqual([m2, m1, m4], hot_activities)
        self.assertListEqual([m3, m6, m5], today_activities)
        self.assertContains(response, m1.title)
        self.assertContains(response, m3.title)

    @skipIfCustomActivity
    def test_portal__is_staff(self):
        self.login_as_super(is_staff=True)

        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'mobile/index.html')

        with self.assertNoException():
            context = response.context
            hot_activities   = [*context['hot_activities']]
            today_activities = [*context['today_activities']]

        self.assertFalse(hot_activities)
        self.assertFalse(today_activities)
