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
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity, CREME_REPLACE_NULL  # SettingValue
from creme.creme_core.models.manager import CremeEntityManager

from ..constants import (
    NARROW, CREATION_LABELS,
    REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY,
)
# from ..setting_keys import auto_subjects_key

from . import other_models
from .calendar import Calendar


class ActivityManager(CremeEntityManager):
    linked_rtype_ids = (
        REL_OBJ_PART_2_ACTIVITY,
        REL_OBJ_ACTIVITY_SUBJECT,
        REL_OBJ_LINKED_2_ACTIVITY,
    )

    def _linked(self, entity):
        return self.filter(
            is_deleted=False,
            relations__object_entity=entity,
            relations__type__in=self.linked_rtype_ids,
        ).distinct()

    def _linked_to_organisation(self, orga):
        return self.filter(
            is_deleted=False,
            relations__object_entity__in=[
                orga,
                *orga.get_managers().values_list('id', flat=True),
                *orga.get_employees().values_list('id', flat=True),
            ],
            relations__type__in=self.linked_rtype_ids,
        ).distinct()

    def future_linked(self, entity, today):
        # TODO: end greater than today or floating type equal to floating
        return self._linked(entity).filter(end__gt=today).order_by('start')

    def past_linked(self, entity, today):
        return self._linked(entity).filter(end__lte=today)

    def future_linked_to_organisation(self, orga, today):
        return self._linked_to_organisation(orga).filter(end__gt=today).order_by('start')

    def past_linked_to_organisation(self, orga, today):
        return self._linked_to_organisation(orga).filter(end__lte=today)


class AbstractActivity(CremeEntity):
    """Activity : task, meeting, phone call, unavailability ..."""
    title = models.CharField(_('Title'), max_length=100)
    start = models.DateTimeField(_('Start'), blank=True, null=True)
    end   = models.DateTimeField(_('End'), blank=True, null=True)
    # description = models.TextField(_('Description'), blank=True).set_tags(optional=True)

    minutes  = models.TextField(_('Minutes'), blank=True)
    place    = models.CharField(_('Activity place'), max_length=500, blank=True)\
                               .set_tags(optional=True)
    duration = models.PositiveIntegerField(_('Duration (in hour)'),
                                           blank=True, null=True,
                                          )

    type     = models.ForeignKey(other_models.ActivityType,
                                 verbose_name=_('Activity type'),
                                 on_delete=models.PROTECT,
                                )
    sub_type = models.ForeignKey(other_models.ActivitySubType,
                                 verbose_name=_('Activity sub-type'),
                                 blank=True, null=True,
                                 on_delete=models.SET_NULL,
                                )
    status   = models.ForeignKey(other_models.Status, verbose_name=_('Status'),
                                 blank=True, null=True,
                                 # on_delete=models.SET_NULL,
                                 on_delete=CREME_REPLACE_NULL,
                                )

    calendars = models.ManyToManyField(Calendar, verbose_name=_('Calendars'),
                                       # blank=True,
                                       editable=False,
                                      )

    is_all_day    = models.BooleanField(_('All day?'), blank=True, default=False)
    busy          = models.BooleanField(_('Busy?'), default=False)
    # TODO: use choices ?
    floating_type = models.PositiveIntegerField(_('Floating type'), default=NARROW,
                                                editable=False,
                                               ).set_tags(viewable=False)

    objects = ActivityManager()

    creation_label = _('Create an activity')
    save_label = _('Save the activity')

    class Meta:
        abstract = True
        manager_inheritance_from_future = True
        app_label = 'activities'
        verbose_name = _('Activity')
        verbose_name_plural = _('Activities')
        ordering = ('-start',)

    def as_ical_event(self):
        r"""Return a normalized iCalendar event string
            /!\ Each parameter has to be separated by \n ONLY no spaces allowed!
            Example : BEGIN:VEVENT\nUID:http://cremecrm.com
        """
        from ..utils import get_ical_date
        return """BEGIN:VEVENT
UID:http://cremecrm.com
DTSTAMP:{dtstamp}
SUMMARY:{summary}
DTSTART:{dtstart}
DTEND:{dtend}
LOCATION:{location}
CATEGORIES:{categories}
STATUS:{status}
END:VEVENT
""".format(dtstamp=get_ical_date(now()),
           summary=self.title,
           dtstart=get_ical_date(self.start),
           dtend=get_ical_date(self.end),
           location='',
           categories=self.type.name,
           status='',
          )

    def get_title_for_calendar(self):
        warnings.warn("AbstractActivity.get_title_for_calendar() is deprecated ; "
                      "use the attribute 'title' instead.",
                      DeprecationWarning,
                     )
        return self.title

    @classmethod
    def get_creation_title(cls, type_id):
        return CREATION_LABELS.get(type_id, cls.creation_label)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('activities__view_activity', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('activities__create_activity')

    def get_edit_absolute_url(self):
        return reverse('activities__edit_activity', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('activities__list_activities')

    def get_participant_relations(self):
        return self.get_relations(REL_OBJ_PART_2_ACTIVITY, real_obj_entities=True)

    def get_subject_relations(self, real_entities=True):
        """Get the list of models.Relation instances which link the Activity
        with its subjects.
        @param real_entities: Retrieve (efficiently) the real entities which are related.
        """
        return self.get_relations(REL_OBJ_ACTIVITY_SUBJECT, real_obj_entities=real_entities)

    def get_linkedto_relations(self):
        return self.get_relations(REL_OBJ_LINKED_2_ACTIVITY, real_obj_entities=True)

    @classmethod
    def _get_linked_aux(cls, entity):
        warnings.warn('AbstractActivity._get_linked_aux() is deprecated.',
                      DeprecationWarning,
                     )

        types = (REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)
        return cls.objects.filter(is_deleted=False,
                                  relations__object_entity=entity,
                                  relations__type__in=types,
                                 ) \
                          .distinct()

    # @classmethod
    # def _get_linked_for_ctypes_aux(cls, ct_ids):
    #     warnings.warn('AbstractActivity._get_linked_for_ctypes_aux() is deprecated.',
    #                   DeprecationWarning
    #                  )
    #
    #     types = (REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)
    #     return cls.objects.filter(is_deleted=False,
    #                               relations__object_entity__entity_type__in=ct_ids,
    #                               relations__type__in=types,
    #                              ) \
    #                       .distinct()

    @classmethod
    def _get_linked_for_orga(cls, orga):
        warnings.warn('AbstractActivity._get_linked_for_orga() is deprecated.',
                      DeprecationWarning,
                     )

        types = (REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)
        entities = [orga,
                    *orga.get_managers().values_list('id', flat=True),
                    *orga.get_employees().values_list('id', flat=True),
                   ]

        return cls.objects.filter(is_deleted=False,
                                  relations__object_entity__in=entities,
                                  relations__type__in=types,
                                 ) \
                          .distinct()

    @classmethod
    def get_future_linked(cls, entity, today):
        warnings.warn('AbstractActivity.get_future_linked() is deprecated ; '
                      'use .objects.future_linked() instead.',
                      DeprecationWarning,
                     )

        return cls._get_linked_aux(entity).filter(end__gt=today).order_by('start')

    # @classmethod
    # def get_future_linked_for_ctypes(cls, ct_ids, today):
    #     warnings.warn('AbstractActivity.get_future_linked_for_ctypes() is deprecated.',
    #                   DeprecationWarning
    #                  )
    #     return cls._get_linked_for_ctypes_aux(ct_ids).filter(end__gt=today).order_by('start')

    @classmethod
    def get_future_linked_for_orga(cls, orga, today):
        warnings.warn('AbstractActivity.get_future_linked_for_orga() is deprecated ; '
                      'use .objects.future_linked_to_organisation() instead.',
                      DeprecationWarning,
                     )

        return cls._get_linked_for_orga(orga).filter(end__gt=today).order_by('start')

    @classmethod
    def get_past_linked(cls, entity, today):
        warnings.warn('AbstractActivity.get_past_linked() is deprecated ; '
                      'use .objects.past_linked() instead.',
                      DeprecationWarning,
                     )

        return cls._get_linked_aux(entity).filter(end__lte=today)  # .order_by('-start')

    # @classmethod
    # def get_past_linked_for_ctypes(cls, ct_ids, today):
    #     warnings.warn('AbstractActivity.get_past_linked_for_ctypes() is deprecated.',
    #                   DeprecationWarning
    #                  )
    #     return cls._get_linked_for_ctypes_aux(ct_ids).filter(end__lte=today).order_by('-start')

    @classmethod
    def get_past_linked_for_orga(cls, orga, today):
        warnings.warn('AbstractActivity.get_past_linked_for_orga() is deprecated ; '
                      'use .objects.past_linked_to_organisation() instead.',
                      DeprecationWarning,
                     )

        return cls._get_linked_for_orga(orga).filter(end__lte=today)  # .order_by('-start')

    def handle_all_day(self):
        if self.is_all_day:
            self.start = self.start.replace(hour=0, minute=0)
            self.end   = self.end.replace(hour=23, minute=59)

    def _pre_save_clone(self, source):
        # TODO: Explicit this into description ? Move the activity to another time-slot ?
        if source.busy:
            self.busy = False

    def is_auto_orga_subject_enabled(self):
        warnings.warn('AbstractActivity.is_auto_orga_subject_enabled() is deprecated ; '
                      'use activities.utils.is_auto_orga_subject_enabled() instead.',
                      DeprecationWarning
                     )
        from creme.activities.utils import is_auto_orga_subject_enabled

        return is_auto_orga_subject_enabled()

    # @staticmethod
    # def display_review():
    #     warnings.warn('AbstractActivity.display_review() is deprecated ; '
    #                   'use "SettingValue.objects.get_4_key(setting_keys.review_key).value" instead.',
    #                   DeprecationWarning
    #                  )
    #     from ..constants import SETTING_DISPLAY_REVIEW
    #
    #     return SettingValue.objects.get(key_id=SETTING_DISPLAY_REVIEW).value

    def _copy_relations(self, source):
        super()._copy_relations(source, allowed_internal=[REL_OBJ_PART_2_ACTIVITY])

    def _pre_delete(self):
        for relation in self.relations.filter(type=REL_OBJ_PART_2_ACTIVITY):
            relation._delete_without_transaction()


class Activity(AbstractActivity):
    class Meta(AbstractActivity.Meta):
        swappable = 'ACTIVITIES_ACTIVITY_MODEL'
