# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from functools import partial

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.timezone import localtime, now

from creme.activities.constants import (
    FLOATING_TIME,
    STATUS_CANCELLED,
    STATUS_DONE,
    STATUS_IN_PROGRESS,
    STATUS_PLANNED,
)
from creme.activities.tests.base import skipIfCustomActivity

from .base import MobileBaseTestCase


class MobileAppTestCase(MobileBaseTestCase):
    def test_login(self):
        url = reverse('mobile__login')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'mobile/login.html')
        self.assertEqual('next', response.context.get('REDIRECT_FIELD_NAME'))

        username = 'gally'
        password = 'passwd'
        get_user_model().objects.create_superuser(
            username,
            first_name='Gally',
            last_name='Alita',
            email='gally@zalem.org',
            password=password,
        )

        response = self.assertPOST200(
            url, follow=True,
            data={
                'username': username,
                'password': password,
                'next':     self.PORTAL_URL,
            },
        )
        self.assertRedirects(response, self.PORTAL_URL)

    def test_logout(self):
        self.login()
        response = self.assertGET200(reverse('mobile__logout'), follow=True)
        self.assertRedirects(response, reverse(settings.LOGIN_URL))

    @skipIfCustomActivity
    def test_portal(self):
        user = self.login()
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

        create_m = partial(self._create_meeting, participant=contact)
        m1 = create_m('Meeting: Manga', start=today_in_the_past(3))
        m2 = create_m(
            'Meeting: Anime',
            start=today_in_the_past(2),
            status_id=STATUS_PLANNED,
        )
        m3 = create_m(
            'Meeting: Manga #2',
            start=past_midnight,
            floating_type=FLOATING_TIME,
        )
        m4 = create_m(
            'Meeting: Figures',
            start=today_in_the_future(3),
            status_id=STATUS_IN_PROGRESS,
        )
        m5 = create_m(
            'Meeting: Figures #3',
            start=today_in_the_future(2),
        )  # Should be after m6
        m6 = create_m('Meeting: Figures #2', start=today_in_the_future(3))

        oneday = timedelta(days=1)
        create_m(
            'Meeting: Tezuka manga',
            start=today(9),
            participant=self.other_user.linked_contact,
        )  # I do not participate
        create_m(
            'Meeting: Comics',
            start=today(7),
            status_id=STATUS_DONE,
        )  # Done are excluded
        create_m(
            'Meeting: Manhua',
            start=today(10),
            status_id=STATUS_CANCELLED,
        )  # Cancelled are excluded
        create_m('Meeting: Manga again',  start=now_val - oneday)  # Yesterday
        create_m('Meeting: Manga ter.',   start=now_val + oneday)  # Tomorrow

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
