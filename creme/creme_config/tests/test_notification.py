from functools import partial

from django.conf import settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext, pgettext

from creme.creme_core.constants import UUID_CHANNEL_SYSTEM
from creme.creme_core.core.notification import (
    OUTPUT_EMAIL,
    OUTPUT_WEB,
    SimpleNotifContent,
)
from creme.creme_core.models import (
    Notification,
    NotificationChannel,
    NotificationChannelConfigItem,
)
from creme.creme_core.notification import (
    AdministrationChannelType,
    SystemChannelType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from .. import bricks


class NotificationChannelTestCase(BrickTestCaseMixin, CremeTestCase):
    def _build_required_url(self, channel):
        return reverse('creme_config__set_notif_channel_required', args=(channel.id,))

    def test_portal(self):
        self.login_as_root()

        custom_chan = NotificationChannel.objects.create(
            name='My Channel', description='messages about stuffs',
            default_outputs=[OUTPUT_WEB],
        )

        response = self.assertGET200(reverse('creme_config__notification'))
        self.assertTemplateUsed(response, 'creme_config/portals/notification.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=bricks.NotificationChannelsBrick,
        )
        names = {tr.find('.//td').text for tr in self.get_brick_table_rows(brick_node)}
        self.assertIn(SystemChannelType.verbose_name,         names)
        self.assertIn(AdministrationChannelType.verbose_name, names)
        self.assertIn(custom_chan.name,                       names)

    def test_create_channel(self):
        self.login_as_root()

        url = reverse('creme_config__create_notif_channel')
        context1 = self.assertGET200(url).context
        self.assertEqual(NotificationChannel.creation_label, context1.get('title'))
        self.assertEqual(NotificationChannel.save_label,     context1.get('submit_label'))

        with self.assertNoException():
            fields = context1['form'].fields

        self.assertIn('name',            fields)
        self.assertIn('description',     fields)
        self.assertIn('required',        fields)
        self.assertIn('default_outputs', fields)
        self.assertNotIn('uuid',    fields)
        self.assertNotIn('type_id', fields)
        self.assertNotIn('deleted', fields)

        # ---
        name = 'My channel'
        description = 'For important things'
        self.assertNoFormError(
            self.client.post(
                url,
                data={
                    'name': name,
                    'description': description,
                    'required': 'on',
                    'default_outputs': ['web'],
                },
            ),
        )

        chan = self.get_object_or_fail(NotificationChannel, name=name)
        self.assertEqual(description, chan.description)
        self.assertTrue(chan.required)
        self.assertFalse(chan.type_id)
        self.assertFalse(chan.deleted)
        self.assertTrue(chan.uuid)
        self.assertListEqual([OUTPUT_WEB], chan.default_outputs)

    def test_create_channel_error(self):
        self.login_as_standard(admin_4_apps=['creme_core'])
        self.assertGET403(reverse('creme_config__create_notif_channel'))

    def test_edit_channel01(self):
        self.login_as_root()

        chan = NotificationChannel.objects.create(
            name='My new channel', required=True, default_outputs=[OUTPUT_WEB],
        )
        url = reverse('creme_config__edit_notif_channel', args=(chan.id,))
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Edit the channel «{object}»').format(object=chan.name),
            context1.get('title'),
        )
        self.assertEqual(_('Save the modifications'), context1.get('submit_label'))

        with self.assertNoException():
            fields = context1['form'].fields
            output_f = fields['default_outputs']
            output_choices = output_f.choices

        self.assertIn('name',        fields)
        self.assertIn('description', fields)
        self.assertNotIn('required', fields)
        self.assertInChoices(
            value='web', label=_('Web browser'), choices=output_choices,
        )
        self.assertInChoices(
            value='email', label=pgettext('creme_core', 'Email'), choices=output_choices,
        )
        self.assertEqual(['web'], output_f.initial)

        # ---
        name = 'My important channel'
        description = 'For important stuffs'
        self.assertNoFormError(
            self.client.post(
                url,
                data={
                    'name': name,
                    'description': description,
                    # 'required': '',
                    'default_outputs': ['email'],
                },
            ),
        )

        chan = self.refresh(chan)
        self.assertEqual(name, chan.name)
        self.assertEqual(description, chan.description)
        self.assertListEqual([OUTPUT_EMAIL], chan.default_outputs)
        self.assertTrue(chan.required)
        self.assertFalse(chan.type_id)
        self.assertFalse(chan.deleted)
        self.assertTrue(chan.uuid)

    def test_edit_channel02(self):
        "Not custom + default outputs."
        self.login_as_root()

        chan = self.get_object_or_fail(NotificationChannel, uuid=UUID_CHANNEL_SYSTEM)
        self.assertTrue(chan.required)
        self.assertListEqual([OUTPUT_WEB], chan.default_outputs)

        url = reverse('creme_config__edit_notif_channel', args=(chan.id,))
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields

        self.assertIn('default_outputs', fields)
        self.assertNotIn('name',        fields)
        self.assertNotIn('description', fields)
        self.assertNotIn('required',    fields)

        # ---
        self.assertNoFormError(
            self.client.post(url, data={'default_outputs': [OUTPUT_EMAIL]}),
        )
        chan = self.refresh(chan)
        self.assertListEqual([OUTPUT_EMAIL], chan.default_outputs)
        self.assertTrue(chan.required)

    def test_edit_channel_error01(self):
        "Not super_user."
        self.login_as_standard(admin_4_apps=['creme_core'])

        chan = NotificationChannel.objects.create(
            name='My new channel', default_outputs=[OUTPUT_WEB],
        )
        self.assertGET403(reverse('creme_config__edit_notif_channel', args=(chan.id,)))

    def test_edit_channel_error02(self):
        "Deleted channel."
        self.login_as_root()

        chan = NotificationChannel.objects.create(
            name='My new channel', default_outputs=[OUTPUT_WEB], deleted=now(),
        )
        self.assertGET404(reverse('creme_config__edit_notif_channel', args=(chan.id,)))

    def test_edit_set_required01(self):
        "Custom; True => False."
        user = self.login_as_root_and_get()

        create_chan = partial(
            NotificationChannel.objects.create,
            default_outputs=[OUTPUT_WEB], required=True,
        )
        chan1 = create_chan(name='My channel #1')
        chan2 = create_chan(name='My channel #2')
        item = NotificationChannelConfigItem.objects.create(channel=chan1, user=user)

        url = self._build_required_url(chan1)
        context1 = self.assertGET200(url).context

        self.assertEqual(
            _('Is the channel «{object}» required?').format(object=chan1.name),
            context1.get('title'),
        )
        self.assertEqual(_('Save the modifications'), context1.get('submit_label'))

        with self.assertNoException():
            fields = context1['form'].fields
            required_f = fields['required']

        self.assertEqual(1, len(fields))
        self.assertTrue(required_f.initial)
        self.assertEqual(
            _(
                'If the channel is not required anymore, '
                'users could configure it to receive no notification'
            ),
            required_f.help_text,
        )

        # ---
        self.assertNoFormError(self.client.post(url, data={'required': ''}))
        self.assertFalse(self.refresh(chan1).required)
        self.assertTrue(self.refresh(chan2).required)  # Not edited of course
        self.assertListEqual([], self.refresh(item).outputs)

    def test_edit_set_required02(self):
        "Custom; False => True (one user's configuration must be updated)."
        user1 = self.login_as_root_and_get()
        user2 = self.create_user()

        create_chan = partial(
            NotificationChannel.objects.create,
            default_outputs=[OUTPUT_WEB], required=False,
        )
        chan1 = create_chan(name='My channel #1')
        chan2 = create_chan(name='My channel #2')

        create_item = NotificationChannelConfigItem.objects.create
        item11 = create_item(channel=chan1, user=user1)
        item12 = create_item(channel=chan1, user=user2, outputs=[OUTPUT_EMAIL])
        item21 = create_item(channel=chan2, user=user1)

        url = self._build_required_url(chan1)
        context1 = self.assertGET200(url).context

        with self.assertNoException():
            form = context1['form']
            fields = form.fields
            required_f = fields['required']

        self.assertEqual(1, len(fields))
        self.assertIs(form.initial.get('required'), False)
        self.assertEqual(
            ngettext(
                'If the channel is set as required, the configuration of '
                '{count} user will be updated to use the default configuration',
                'If the channel is set as required, the configuration of '
                '{count} users will be updated to use the default configuration',
                1
            ).format(count=1),
            required_f.help_text,
        )

        # ---
        self.assertNoFormError(self.client.post(url, data={'required': 'on'}))
        self.assertTrue(self.refresh(chan1).required)
        self.assertFalse(self.refresh(chan2).required)  # Not edited of course

        self.assertListEqual([OUTPUT_WEB], self.refresh(item11).outputs)  # Updated
        # Not updated
        self.assertListEqual([OUTPUT_EMAIL], self.refresh(item12).outputs)
        self.assertListEqual([],             self.refresh(item21).outputs)

    def test_edit_set_required03(self):
        "Custom; False => True (2 users' configuration must be updated)."
        user1 = self.login_as_root_and_get()
        user2 = self.create_user()

        chan = NotificationChannel.objects.create(
            name='My channel', default_outputs=[OUTPUT_WEB], required=False,
        )

        create_item = partial(NotificationChannelConfigItem.objects.create, channel=chan)
        create_item(user=user1)
        create_item(user=user2)

        context1 = self.assertGET200(self._build_required_url(chan)).context

        with self.assertNoException():
            required_f = context1['form'].fields['required']

        self.assertEqual(
            ngettext(
                'If the channel is set as required, the configuration of '
                '{count} user will be updated to use the default configuration',
                'If the channel is set as required, the configuration of '
                '{count} users will be updated to use the default configuration',
                2
            ).format(count=2),
            required_f.help_text,
        )

    def test_edit_set_required04(self):
        "Not custom (is_staff=True)."
        self.login_as_super(is_staff=True)
        chan = self.get_object_or_fail(NotificationChannel, uuid=UUID_CHANNEL_SYSTEM)
        self.assertGET200(self._build_required_url(chan))

    def test_edit_set_required_error01(self):
        "Not super_user."
        self.login_as_standard(admin_4_apps=['creme_core'])

        chan = NotificationChannel.objects.create(
            name='My new channel', default_outputs=[OUTPUT_WEB],
        )
        self.assertGET403(self._build_required_url(chan))

    def test_edit_set_required_error02(self):
        "Deleted channel."
        self.login_as_root()

        chan = NotificationChannel.objects.create(
            name='My new channel', default_outputs=[OUTPUT_WEB],
            deleted=now(),
        )
        self.assertGET404(self._build_required_url(chan))

    def test_edit_set_required_error03(self):
        "Not custom (is_staff=False)."
        self.login_as_root()
        chan = self.get_object_or_fail(NotificationChannel, uuid=UUID_CHANNEL_SYSTEM)
        self.assertGET403(self._build_required_url(chan))

    def test_delete_channel01(self):
        "No linked notification."
        self.login_as_root()

        chan = NotificationChannel.objects.create(
            name='My channel', default_outputs=[OUTPUT_WEB],
        )
        url = reverse('creme_config__delete_notif_channel')
        data = {'id': chan.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)
        chan = self.assertStillExists(chan)
        deleted = chan.deleted
        self.assertIsNotNone(deleted)
        self.assertDatetimesAlmostEqual(now(), deleted)

        # ---
        self.assertPOST200(url, data=data)
        self.assertDoesNotExist(chan)

    def test_delete_channel02(self):
        "With one linked notification."
        user = self.login_as_root_and_get()

        chan = NotificationChannel.objects.create(
            name='My channel', default_outputs=[OUTPUT_WEB],
        )
        notif = Notification.objects.create(
            channel=chan, user=user,
            content=SimpleNotifContent(subject='Hi', body='How R U?'),
        )

        url = reverse('creme_config__delete_notif_channel')
        data = {'id': chan.id}
        self.assertPOST200(url, data=data)
        chan = self.assertStillExists(chan)
        self.assertIsNotNone(chan.deleted)

        # ---
        self.assertContains(
            self.client.post(url, data=data),
            ngettext(
                'This channel is still used by {count} notification, so it cannot be deleted.',
                'This channel is still used by {count} notifications, so it cannot be deleted.',
                1
            ).format(count=1),
            status_code=409,
        )

        self.assertStillExists(chan)
        self.assertStillExists(notif)

    def test_delete_channel03(self):
        "With 2 linked notifications."
        user = self.login_as_root_and_get()

        chan = NotificationChannel.objects.create(
            name='My channel', default_outputs=[OUTPUT_WEB], deleted=now(),
        )

        create_notif = partial(Notification.objects.create, channel=chan, user=user)
        create_notif(content=SimpleNotifContent(subject='*Subject #1*', body='*Body #1*'))
        create_notif(content=SimpleNotifContent(subject='*Subject #2*', body='*Body #2*'))

        self.assertContains(
            self.client.post(reverse('creme_config__delete_notif_channel'), data={'id': chan.id}),
            ngettext(
                'This channel is still used by {count} notification, so it cannot be deleted.',
                'This channel is still used by {count} notifications, so it cannot be deleted.',
                2
            ).format(count=2),
            status_code=409,
        )

    def test_delete_channel_error01(self):
        "No custom channel."
        self.login_as_root()

        chan = NotificationChannel.objects.create(
            name='My channel', default_outputs=[OUTPUT_WEB],
            type=SystemChannelType,  # <==
        )
        self.assertPOST409(reverse('creme_config__delete_notif_channel'), data={'id': chan.id})

    def test_delete_channel_error02(self):
        "No super-user."
        self.login_as_standard(admin_4_apps=['creme_core'])

        chan = NotificationChannel.objects.create(
            name='My channel', default_outputs=[OUTPUT_WEB],
        )
        self.assertPOST403(reverse('creme_config__delete_notif_channel'), data={'id': chan.id})


class NotificationChannelConfigItemTestCase(BrickTestCaseMixin, CremeTestCase):
    def _build_edit_url(self, chan):
        return reverse('creme_config__edit_channel_config', args=(chan.id,))

    def test_portal(self):
        user = self.login_as_standard()
        root = self.get_root_user()
        self.assertFalse(NotificationChannelConfigItem.objects.filter(user=user))
        self.assertFalse(NotificationChannelConfigItem.objects.filter(user=root))

        create_chan = partial(NotificationChannel.objects.create, default_outputs=[OUTPUT_WEB])
        custom_chan = create_chan(name='My Channel')
        deleted_chan = create_chan(name='Deleted chan', deleted=now())

        channels = NotificationChannel.objects.filter(deleted=None)
        count = len(channels)
        bricks.NotificationChannelConfigItemsBrick.page_size = max(count, settings.BLOCK_SIZE)

        NotificationChannelConfigItem.objects.create(channel=channels[0], user=user)

        response = self.assertGET200(reverse('creme_config__user_settings'))
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=bricks.NotificationChannelConfigItemsBrick,
        )

        items = NotificationChannelConfigItem.objects.filter(
            user=user,
        ).values_list('channel', flat=True)
        self.assertEqual(count, len(items), items)

        self.assertBrickTitleEqual(
            brick_node,
            count=count,
            title='{count} Channel',
            plural_title='{count} Channels',
        )
        names = {tr.find('.//td').text for tr in self.get_brick_table_rows(brick_node)}
        self.assertIn(SystemChannelType.verbose_name,         names)
        self.assertIn(AdministrationChannelType.verbose_name, names)
        self.assertIn(custom_chan.name,                       names)
        self.assertNotIn(deleted_chan.name, names)

        self.assertFalse(NotificationChannelConfigItem.objects.filter(user=root))

    def test_edit01(self):
        "Item already exists."
        user = self.login_as_standard()
        custom_chan = NotificationChannel.objects.create(
            name='My Channel', default_outputs=[OUTPUT_WEB],
        )
        self.assertTrue(custom_chan.required)

        item = NotificationChannelConfigItem.objects.create(
            channel=custom_chan, user=user, outputs=[OUTPUT_WEB],
        )

        url = self._build_edit_url(custom_chan)
        response1 = self.assertGET200(url)
        self.assertEqual(
            _('Configure the channel «{object}»').format(object=custom_chan.name),
            response1.context.get('title'),
        )

        with self.assertNoException():
            fields = response1.context['form'].fields
            output_f = fields['outputs']
            output_choices = output_f.choices

        self.assertEqual(1, len(fields))
        self.assertInChoices(
            value='web', label=_('Web browser'), choices=output_choices,
        )
        self.assertInChoices(
            value='email', label=pgettext('creme_core', 'Email'), choices=output_choices,
        )
        self.assertEqual(['web'], output_f.initial)
        self.assertTrue(output_f.required)

        # ---
        self.assertNoFormError(self.client.post(
            url, data={'outputs': [OUTPUT_EMAIL]},
        ))
        self.assertListEqual([OUTPUT_EMAIL], self.refresh(item).outputs)

    def test_edit02(self):
        "Item does not exist (should not happen in real cases)."
        user = self.login_as_standard()
        custom_chan = NotificationChannel.objects.create(
            name='My Channel', default_outputs=[OUTPUT_WEB],
        )
        self.assertFalse(
            NotificationChannelConfigItem.objects.filter(channel=custom_chan, user=user)
        )

        self.assertGET200(self._build_edit_url(custom_chan))
        item = self.get_object_or_fail(
            NotificationChannelConfigItem, channel=custom_chan, user=user,
        )
        self.assertListEqual([OUTPUT_WEB], item.outputs)

    def test_edit03(self):
        "Required channel."
        user = self.login_as_standard()
        custom_chan = NotificationChannel.objects.create(
            name='My Channel', required=True, default_outputs=[OUTPUT_WEB],
        )
        NotificationChannelConfigItem.objects.create(
            channel=custom_chan, user=user, outputs=custom_chan.default_outputs,
        )

        response = self.assertGET200(self._build_edit_url(custom_chan))

        with self.assertNoException():
            output_f = response.context['form'].fields['outputs']

        self.assertTrue(output_f.required)

    def test_edit04(self):
        "Deleted channel."
        user = self.login_as_standard()
        custom_chan = NotificationChannel.objects.create(
            name='My Channel', default_outputs=[OUTPUT_WEB], deleted=now(),
        )
        NotificationChannelConfigItem.objects.create(
            channel=custom_chan, user=user, outputs=custom_chan.default_outputs,
        )

        self.assertGET409(self._build_edit_url(custom_chan))
