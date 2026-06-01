from uuid import uuid4

from django.urls import reverse
from django.utils.html import escape
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.activities import constants
from creme.activities.menu import (
    MeetingsEntry,
    PhoneCallsEntry,
    _TypedActivitiesEntry,
)
from creme.activities.tests.base import _ActivitiesTestCase


# TODO: complete
class ActivitiesMenuTestCase(_ActivitiesTestCase):
    def test_PhoneCallsEntry(self):
        entry = PhoneCallsEntry()
        url = reverse('activities__list_phone_calls')
        self.assertEqual(url, entry.url)
        self.assertHTMLEqual(
            f'<a href="{url}">{_('Phone calls')}</a>',
            entry.render({'user': self.get_root_user()}),
        )

    def test_PhoneCallsEntry__forbidden(self):
        user = self.create_user(
            role=self.create_role(allowed_apps=['creme_core', 'persons']),
        )
        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden" title="{title}">'
            '{label}'
            '</span>'.format(
                title=_('You are not allowed to access to the app: {}').format(
                    _('Activities')
                ),
                label=_('Phone calls'),
            ),
            PhoneCallsEntry().render({'user': user}),
        )

    def test_PhoneCallsEntry__type_disabled(self):
        entry = PhoneCallsEntry()
        atype = self._get_type(constants.UUID_TYPE_PHONECALL)

        try:
            atype.disabled = now()
            atype.save()

            html = entry.render({'user': self.get_root_user()})
        finally:
            atype.disabled = None
            atype.save()

        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden" title="{title}">'
            '{label}'
            '</span>'.format(
                title=atype.message_for_disabled,
                label=_('Phone calls'),
            ),
            html,
        )

    def test_MeetingsEntry(self):
        entry = MeetingsEntry()
        url = reverse('activities__list_meetings')
        self.assertEqual(url, entry.url)
        self.assertHTMLEqual(
            f'<a href="{url}">{_('Meetings')}</a>',
            entry.render({'user': self.get_root_user()}),
        )

    def test_MeetingsEntry__forbidden(self):
        user = self.create_user(
            role=self.create_role(allowed_apps=['creme_core', 'persons']),
        )
        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden" title="{title}">'
            '{label}'
            '</span>'.format(
                title=_('You are not allowed to access to the app: {}').format(
                    _('Activities')
                ),
                label=_('Meetings'),
            ),
            MeetingsEntry().render({'user': user}),
        )

    def test_MeetingsEntry__type_disabled(self):
        entry = MeetingsEntry()
        atype = self._get_type(constants.UUID_TYPE_MEETING)

        try:
            atype.disabled = now()
            atype.save()

            html = entry.render({'user': self.get_root_user()})
        finally:
            atype.disabled = None
            atype.save()

        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden" title="{title}">'
            '{label}'
            '</span>'.format(
                title=atype.message_for_disabled,
                label=_('Meetings'),
            ),
            html,
        )

    def test_TypedActivitiesEntry__type_removed(self):
        class TestTypedActivitiesEntry(_TypedActivitiesEntry):
            id = 'activities-invalid'
            label = 'Invalid'
            url_name = 'activities__list_phone_calls'  # whatever
            type_uuid = str(uuid4())  # <===

        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden" title="{title}">'
            '{label}'
            '</span>'.format(
                title=escape(_(
                    'It seems the instance of model «{model}» with uuid "{uuid}" '
                    'has been deleted; please contact your administrator.'
                ).format(
                    model=_('Type of activity'),
                    uuid=TestTypedActivitiesEntry.type_uuid,
                )),
                label=TestTypedActivitiesEntry.label,
            ),
            TestTypedActivitiesEntry().render({'user': self.get_root_user()}),
        )
