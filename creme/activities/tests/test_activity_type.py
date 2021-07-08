# -*- coding: utf-8 -*-

from django.urls import reverse

from ..models import ActivitySubType, ActivityType
from .base import _ActivitiesTestCase


class ActivityTypeTestCase(_ActivitiesTestCase):
    def test_create_type(self):
        self.login()
        self.assertGET200(reverse('creme_config__app_portal', args=('activities',)))
        self.assertGET200(reverse(
            'creme_config__model_portal',
            args=('activities', 'activity_type'),
        ))

        url = reverse('creme_config__create_instance', args=('activities', 'activity_type'))
        self.assertGET200(url)

        name = 'Awesome show'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name': name,
                'default_day_duration': '0',

                'default_hour_duration_0': '0',
                'default_hour_duration_1': '15',
                'default_hour_duration_2': '0',
            },
        ))

        atype = self.get_object_or_fail(ActivityType, name=name)
        self.assertEqual(0,        atype.default_day_duration)
        self.assertEqual('0:15:0', atype.default_hour_duration)

    def test_edit_type(self):
        self.login()

        type_id = 'test-activity_awsesome'
        atype = ActivityType.objects.create(
            pk=type_id,
            name='karate session',
            default_day_duration=0,
            default_hour_duration='00:15:00',
            is_custom=True,
        )

        url = reverse(
            'creme_config__edit_instance',
            args=('activities', 'activity_type', atype.id),
        )
        self.assertGET200(url)

        name = atype.name.title()
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name': name,
                'default_day_duration': '1',

                'default_hour_duration_0': '1',
                'default_hour_duration_1': '0',
                'default_hour_duration_2': '0',
            },
        ))

        atype = self.refresh(atype)
        self.assertEqual(name, atype.name)
        self.assertEqual(1,       atype.default_day_duration)
        self.assertEqual('1:0:0', atype.default_hour_duration)

    def test_create_subtype(self):
        self.login()
        self.assertGET200(reverse(
            'creme_config__model_portal',
            args=('activities', 'activity_sub_type')
        ))

        atype = ActivityType.objects.create(
            pk='test-activity_karate',
            name='Karate session',
            default_day_duration=0,
            default_hour_duration='00:15:00',
            is_custom=True,
        )

        url = reverse(
            'creme_config__create_instance', args=('activities', 'activity_sub_type'),
        )
        self.assertGET200(url)

        name = 'Fight'
        self.assertNoFormError(
            self.client.post(url, data={'type': atype.id, 'name': name})
        )

        self.get_object_or_fail(ActivitySubType, name=name, type=atype)

    def test_edit_subtype(self):
        self.login()

        atype = ActivityType.objects.create(
            pk='test-activity_karate',
            name='karate session',
            default_day_duration=0,
            default_hour_duration='00:15:00',
            is_custom=True,
        )
        satype = ActivitySubType.objects.create(
            pk='test-activity_fight', type=atype, name='Figtho',
        )

        url = reverse(
            'creme_config__edit_instance',
            args=('activities', 'activity_sub_type', satype.id),
        )
        self.assertGET200(url)

        name = 'Figtho'
        self.assertNoFormError(
            self.client.post(url, data={'type': atype.id, 'name': name})
        )
        self.assertEqual(name, self.refresh(satype).name)
