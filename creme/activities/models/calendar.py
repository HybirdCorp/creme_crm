# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

import warnings

from django.db import models
from django.utils.translation import gettext_lazy as _, gettext

from creme.creme_core.models import CremeModel, fields as core_fields

from ..constants import COLOR_POOL, DEFAULT_CALENDAR_COLOR


class CalendarManager(models.Manager):
    def new_color(self):
        return COLOR_POOL[self.count() % len(COLOR_POOL)]

    def create_default_calendar(self, user, *, name=None, color=None, is_public=False, check_for_default=False):
        """Creates a default Calendar for a given user.

        @param user: 'django.contrib.auth.get_user_model()' instance.
        @param name: Name of the new calendar ; <None> means a default one will be generated.
        @param color: HTML color string ; <None> means a default one will be picked.
        @param is_public: Boolean.
        @param check_for_default: Boolean ; <True> means than a query is performed to search
               if another default Calendar exists (it is set to is_default=false if needed).
               <False> by default ; so you SHOULD check if there is already another default Calendar.
        @return: A Calendar instance.
        """
        cal = self.model(
            name=name or gettext("{user}'s calendar").format(user=user),
            user=user, is_default=True, is_custom=False,
            is_public=is_public,
            color=color or self.new_color(),
        )
        cal._enable_default_checking = check_for_default
        cal.save()

        return cal

    def get_default_calendar(self, user):
        """Get the user's default Calendar ; creates it if necessary.

        @param user: 'django.contrib.auth.get_user_model()' instance.
        @return: A Calendar instance.
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


class Calendar(CremeModel):
    name       = models.CharField(_('Name'), max_length=100)
    is_default = models.BooleanField(_('Is default?'), default=False)
    is_custom  = models.BooleanField(default=True, editable=False).set_tags(viewable=False)  # Used by creme_config
    is_public  = models.BooleanField(default=False, verbose_name=_('Is public?'))
    user       = core_fields.CremeUserForeignKey(verbose_name=_('Calendar owner'))
    color      = core_fields.ColorField(_('Color'))

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

    @property
    def get_color(self):  # TODO: rename (safe_color ?)
        "Color can be null, so in this case a default color is used in templates."
        return self.color or DEFAULT_CALENDAR_COLOR

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

        if self.is_default:
            # Sadly we cannot update() on a slice...
            for def_cal in Calendar.objects.filter(user=self.user).order_by('id')[:1]:
                def_cal.is_default = True
                def_cal._enable_default_checking = False
                def_cal.save()

    @classmethod
    def new_color(cls):
        warnings.warn('Calendar.new_color() is deprecated ; '
                      'use Calendar.objects.new_color() instead.',
                      DeprecationWarning
                     )
        return COLOR_POOL[cls.objects.count() % len(COLOR_POOL)]

    @classmethod
    def _create_default_calendar(cls, user, *, is_public=False):
        warnings.warn('Calendar._create_default_calendar() is deprecated ; '
                      'use Calendar.objects.create_default_calendar() instead.',
                      DeprecationWarning
                     )

        cal = Calendar(name=gettext("{user}'s calendar").format(user=user),
                       user=user, is_default=True, is_custom=False,
                       is_public=is_public,
                       color=cls.new_color(),
                      )
        cal._enable_default_checking = False
        cal.save()

        return cal

    @staticmethod
    def get_user_calendars(user):
        warnings.warn('Calendar.get_user_calendars() is deprecated.', DeprecationWarning)

        calendars = list(Calendar.objects.filter(user=user))

        if not calendars:
            calendars.append(Calendar._create_default_calendar(user))

        return calendars

    @classmethod
    def get_user_default_calendar(cls, user):
        "Returns the default user calendar ; creates it if necessary."
        warnings.warn('Calendar.get_user_default_calendar() is deprecated ; '
                      'use Calendar.objects.get_default_calendar() instead.',
                      DeprecationWarning
                     )

        calendars = cls.objects.filter(user=user)

        if not calendars:
            cal = cls._create_default_calendar(user)
        else:
            defaults = [c for c in calendars if c.is_default]

            if not defaults:
                cal = calendars[0]
                cal.is_default = True
                cal._enable_default_checking = False
                cal.save()  # TODO: update_fields=['is_default']
            else:
                cal = defaults[0]

                if len(defaults) > 1:
                    cls.objects.filter(user=user).exclude(id=cal.id).update(is_default=False)

        return cal

    def save(self, *args, **kwargs):
        mngr = type(self).objects

        if not self.color:
            # self.color = self.new_color()
            self.color = mngr.new_color()

        check = self._enable_default_checking

        if check and not self.is_default and \
           not mngr.filter(user=self.user, is_default=True).exists():
            self.is_default = True

        super().save(*args, **kwargs)

        if check and self.is_default:
            mngr.filter(user=self.user, is_default=True) \
                .exclude(id=self.id) \
                .update(is_default=False)
