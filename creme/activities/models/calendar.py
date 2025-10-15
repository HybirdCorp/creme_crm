################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from __future__ import annotations

import uuid
from collections import defaultdict

from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

import creme.creme_core.models.fields as core_fields
from creme.creme_core.models import CremeModel


class CalendarManager(models.Manager):
    def create_default_calendar(self,
                                user, *,
                                name: str | None = None,
                                color: str | None = None,
                                is_public: bool = False,
                                check_for_default: bool = False
                                ) -> Calendar:
        """Creates a default Calendar for a given user.

        @param user: 'django.contrib.auth.get_user_model()' instance.
        @param name: Name of the new calendar;
               <None> means a default one will be generated.
        @param color: HTML color string (without the "#" prefix);
               <None> means a random one will be picked.
        @param is_public: If 'True' the Activities on this calendar are visible by all users.
        @param check_for_default: Boolean ;
               - <True> means than a query is performed to search if another
               default Calendar exists (it is set to <is_default=False> if needed).
               - <False> by default ; so you SHOULD check if there is already
               another default Calendar.
        @return: A 'Calendar' instance.
        """
        kwargs = {} if not color else {'color': color}
        cal = self.model(
            name=name or gettext("{user}'s calendar").format(user=user),
            user=user, is_default=True, is_custom=False,
            is_public=is_public,
            **kwargs
        )
        cal._enable_default_checking = check_for_default
        cal.save()

        return cal

    create_default_calendar.alters_data = True

    def get_by_portable_key(self, key: str) -> Calendar:
        return self.get(uuid=key)

    def get_default_calendar(self, user) -> Calendar:
        """Get the user's default Calendar ; creates it if necessary.

        @param user: 'django.contrib.auth.get_user_model()' instance.
        @return: A 'Calendar' instance.
        """
        calendars = self.filter(user=user).order_by('-is_default')[:2]

        if not calendars:
            cal = self.create_default_calendar(user)
        else:
            defaults = [c for c in calendars if c.is_default]

            if not defaults:
                cal = calendars[0]
                cal.is_default = True
                self.filter(id=cal.id).update(is_default=True)
            else:
                cal = defaults[0]

                if len(defaults) > 1:
                    self.filter(user=user).exclude(id=cal.id).update(is_default=False)

        return cal

    def get_default_calendars(self, users) -> dict[int, Calendar]:
        """Get the default Calendars of several users at once efficiently.

        @param users: Iterable of 'django.contrib.auth.get_user_model()' instances.
        @return: Dictionary with users' IDs as keys & 'Calendar' instances as values.
        """
        default_calendars: dict[int, Calendar] = {}  # int is User ID
        calendar_ids_to_set: list[int]  = []
        calendar_ids_to_unset: list[int] = []
        users_per_id = {user.id: user for user in users}

        calendars_per_users = defaultdict(list)
        # NB: on order_by:
        #   '-is_default': to get default calendars as first element in list.
        #   '-is_public': to pass as default a public calendar if there is one.
        #   'id': to get stable ordering (to avoid race conditions).
        for cal in self.filter(user__in=users_per_id.keys()).order_by(
            '-is_default', '-is_public', 'id',
        ):
            calendars_per_users[cal.user_id].append(cal)

        for user_id, user_calendars in calendars_per_users.items():
            calendar = user_calendars[0]
            default_calendars[user_id] = calendar

            if not calendar.is_default:
                calendar_ids_to_set.append(calendar.id)

            calendar_ids_to_unset.extend(
                cal.id for cal in user_calendars[1:] if cal.is_default
            )

        self.filter(id__in=calendar_ids_to_set).update(is_default=True)
        self.filter(id__in=calendar_ids_to_unset).update(is_default=False)

        for user_id, user in users_per_id.items():
            if user_id not in calendars_per_users:
                default_calendars[user_id] = self.create_default_calendar(user)

        return default_calendars


class Calendar(CremeModel):
    uuid = models.UUIDField(
        unique=True, editable=False, default=uuid.uuid4,
    ).set_tags(viewable=False)

    # Not viewable by users, For administrators currently.
    created = core_fields.CreationDateTimeField().set_tags(viewable=False)
    modified = core_fields.ModificationDateTimeField().set_tags(viewable=False)

    user = core_fields.CremeUserForeignKey(verbose_name=_('Calendar owner'))
    name = models.CharField(_('Name'), max_length=100)
    is_default = models.BooleanField(
        _('Is default?'),
        default=False,
        help_text=_(
            "When a user is set as an Activity's participant, this Activity is "
            "added to its default calendar."
        ),
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name=_('Is public?'),
        help_text=_('Public calendars can be seen by other users on the calendar view.'),
    )
    color = core_fields.ColorField(
        # _('Color'),
        help_text=_('It is used on the calendar view to colorize Activities.'),
        default=core_fields.ColorField.random,
    )

    # Used by creme_config
    is_custom  = models.BooleanField(default=True, editable=False).set_tags(viewable=False)

    objects = CalendarManager()

    _enable_default_checking = True

    creation_label = _('Create a calendar')
    save_label     = _('Save the calendar')

    class Meta:
        app_label = 'activities'
        verbose_name = _('Calendar')
        verbose_name_plural = _('Calendars')
        ordering = ['name']

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

        if self.is_default:
            # Sadly we cannot update() on a slice...
            for def_cal in Calendar.objects.filter(user=self.user).order_by('id')[:1]:
                def_cal.is_default = True
                def_cal._enable_default_checking = False
                def_cal.save()

    def portable_key(self) -> str:
        """See CremeEntity.portable_key()."""
        return str(self.uuid)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        mngr = type(self).objects
        check = self._enable_default_checking

        if (
            check
            and not self.is_default
            and not mngr.filter(user=self.user, is_default=True).exists()
        ):
            self.is_default = True
            if update_fields is not None:
                update_fields = {'is_default', *update_fields}

        # TODO: help text to explain this behaviour?
        if self.user.is_team:
            self.is_public = True

        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

        if check and self.is_default:
            mngr.filter(user=self.user, is_default=True) \
                .exclude(id=self.id) \
                .update(is_default=False)
