# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.db.models import CharField, BooleanField
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import CremeUserForeignKey, ColorField

from ..constants import COLOR_POOL, DEFAULT_CALENDAR_COLOR


class Calendar(CremeModel):
    name        = CharField(_('Name'), max_length=100)
    is_default  = BooleanField(_('Is default?'), default=False)
    is_custom   = BooleanField(default=True, editable=False).set_tags(viewable=False)  # Used by creme_config
    is_public   = BooleanField(default=False, verbose_name=_('Is public?'))
    user        = CremeUserForeignKey(verbose_name=_('Calendar owner'))
    color       = ColorField(_('Color'))

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
        "color can be null, so in this case a default color is used in templates"
        return self.color or DEFAULT_CALENDAR_COLOR

    def delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

        if self.is_default:
            # Sadly we cannot update() on a slice...
            for def_cal in Calendar.objects.filter(user=self.user).order_by('id')[:1]:
                def_cal.is_default = True
                def_cal._enable_default_checking = False
                def_cal.save()

    @staticmethod
    def new_color():
        return COLOR_POOL[Calendar.objects.count() % len(COLOR_POOL)]

    @staticmethod
    def _create_default_calendar(user):
        cal = Calendar(name=ugettext("{user}'s calendar").format(user=user),
                       user=user, is_default=True, is_custom=False,
                       color=Calendar.new_color(),
                      )
        cal._enable_default_checking = False
        cal.save()

        return cal

    @staticmethod
    def get_user_calendars(user):
        calendars = list(Calendar.objects.filter(user=user))

        if not calendars:
            calendars.append(Calendar._create_default_calendar(user))

        return calendars

    @staticmethod
    def get_user_default_calendar(user):
        "Returns the default user calendar ; creates it if necessary."
        calendars = Calendar.objects.filter(user=user)

        if not calendars:
            cal = Calendar._create_default_calendar(user)
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
                    Calendar.objects.filter(user=user).exclude(id=cal.id).update(is_default=False)

        return cal

    def save(self, *args, **kwargs):
        if not self.color:
            self.color = self.new_color()

        check = self._enable_default_checking

        if check and not self.is_default and \
           not Calendar.objects.filter(user=self.user, is_default=True).exists():
            self.is_default = True

        super().save(*args, **kwargs)

        if check and self.is_default:
            Calendar.objects.filter(user=self.user, is_default=True) \
                            .exclude(id=self.id) \
                            .update(is_default=False)
