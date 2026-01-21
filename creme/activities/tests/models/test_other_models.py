from django.template import Context, Template
from django.urls import reverse
from django.utils.translation import gettext as _
from PIL.ImageColor import getrgb

from creme.activities.models import ActivitySubType, ActivityType, Status
from creme.creme_core.gui.view_tag import ViewTag

from ..base import Activity, _ActivitiesTestCase


class StatusTestCase(_ActivitiesTestCase):
    def test_color(self):
        status1 = Status(name='OK')
        color1 = status1.color
        self.assertIsInstance(color1, str)
        self.assertEqual(6, len(color1))

        with self.assertNoException():
            getrgb(f'#{color1}')

        # ---
        status2 = Status(name='KO')
        self.assertNotEqual(color1, status2.color)

    def test_render(self):
        user = self.get_root_user()
        status = Status.objects.create(name='OK', color='00FF00')
        ctxt = {
            'user': user,
            'activity': Activity(user=user, title='OK Ticket', status=status),
        }
        template = Template(
            r'{% load creme_core_tags %}'
            r'{% print_field object=activity field="status" tag=tag %}'
        )
        self.assertEqual(
            status.name,
            template.render(Context({**ctxt, 'tag': ViewTag.TEXT_PLAIN})).strip()
        )
        self.assertHTMLEqual(
            f'<div class="ui-creme-colored_status">'
            f' <div class="ui-creme-color_indicator" style="background-color:#{status.color};" />'
            f' <span>{status.name}</span>'
            f'</div>',
            template.render(Context({**ctxt, 'tag': ViewTag.HTML_DETAIL})),
        )


class ActivityTypeTestCase(_ActivitiesTestCase):
    def test_save(self):
        atype = ActivityType.objects.create(
            name='Martial arts', default_day_duration=0, default_hour_duration='00:15:00',
        )
        self.assertTrue(atype.is_custom)

        sub_type = ActivitySubType(name='Karate session', type=atype)
        self.assertTrue(sub_type.is_custom)

        with self.assertNoException():
            sub_type.save()

        # ---
        sub_type.is_custom = False

        with self.assertRaises(ValueError) as cm:
            sub_type.save()

        self.assertEqual(
            f'The ActivitySubType id="{sub_type.id}" is not custom, '
            f'so the related ActivityType cannot be custom.',
            str(cm.exception),
        )

        # ---
        atype.is_custom = False

        with self.assertNoException():
            sub_type.save()

    def test_create_type(self):
        self.login_as_root()
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
        self.assertEqual('0:15:00', atype.default_hour_duration)

    def test_edit_type(self):
        self.login_as_root()

        atype = ActivityType.objects.create(
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
        self.assertEqual('1:00:00', atype.default_hour_duration)

    def test_create_subtype(self):
        self.login_as_root()
        self.assertGET200(reverse(
            'creme_config__model_portal',
            args=('activities', 'activity_sub_type')
        ))

        atype = ActivityType.objects.create(
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
        self.login_as_root()

        atype = ActivityType.objects.create(
            name='karate session',
            default_day_duration=0,
            default_hour_duration='00:15:00',
            is_custom=True,
        )
        satype = ActivitySubType.objects.create(type=atype, name='Fightoo')

        url = reverse(
            'creme_config__edit_instance',
            args=('activities', 'activity_sub_type', satype.id),
        )
        self.assertGET200(url)

        name = 'Fight!!'
        self.assertNoFormError(
            self.client.post(url, data={'type': atype.id, 'name': name})
        )
        self.assertEqual(name, self.refresh(satype).name)

    def test_delete_type__not_used(self):
        self.login_as_root()

        atype = ActivityType.objects.create(
            name='Karate session',
            default_day_duration=0, default_hour_duration='00:15:00',
            is_custom=True,
        )
        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('activities', 'activity_type', atype.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(ActivityType).job
        job.type.execute(job)
        self.assertDoesNotExist(atype)

    def test_delete_type__used(self):
        user = self.login_as_root_and_get()

        atype = ActivityType.objects.create(
            name='Karate session',
            default_day_duration=0,
            default_hour_duration='00:15:00',
            is_custom=True,
        )
        sub_type = ActivitySubType.objects.create(
            type=atype,
            name='Kick session',
            is_custom=True,
        )

        Activity.objects.create(user=user, type=atype, sub_type=sub_type)

        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('activities', 'activity_type', atype.id),
        ))
        self.assertFormError(
            self.get_form_or_fail(response),
            field='replace_activities__activity_type',
            errors=_('Deletion is not possible.'),
        )
