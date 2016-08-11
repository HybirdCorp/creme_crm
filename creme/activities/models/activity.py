# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

import logging

from django.core.urlresolvers import reverse
from django.db.models import (PositiveIntegerField, DateTimeField, CharField,
        TextField, BooleanField, ManyToManyField, ForeignKey, PROTECT, SET_NULL)
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeEntity, SettingValue

# from .. import get_activity_model
from ..constants import (NARROW, CREATION_LABELS, SETTING_AUTO_ORGA_SUBJECTS, DISPLAY_REVIEW_ACTIVITIES_BLOCKS,
        REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)
from .calendar import Calendar
from .other_models import ActivityType, ActivitySubType, Status


logger = logging.getLogger(__name__)


class AbstractActivity(CremeEntity):
    """Activity : task, meeting, phone call, unavailability ..."""
    title         = CharField(_(u'Title'), max_length=100)
    start         = DateTimeField(_(u'Start'), blank=True, null=True)
    end           = DateTimeField(_(u'End'), blank=True, null=True)
    description   = TextField(_(u'Description'), blank=True, null=True).set_tags(optional=True)
    minutes       = TextField(_(u'Minutes'), blank=True, null=True)
    place         = CharField(_(u'Activity place'), max_length=500, blank=True)\
                             .set_tags(optional=True)
    duration      = PositiveIntegerField(_(u'Duration (in hour)'), blank=True, null=True)
    type          = ForeignKey(ActivityType, verbose_name=_(u'Activity type'),
                               on_delete=PROTECT,
                              )
    sub_type      = ForeignKey(ActivitySubType, verbose_name=_(u'Activity sub-type'),
                               blank=True, null=True, on_delete=SET_NULL,
                              )
    status        = ForeignKey(Status, verbose_name=_(u'Status'),
                               blank=True, null=True, on_delete=SET_NULL,
                              )
    calendars     = ManyToManyField(Calendar, verbose_name=_(u'Calendars'),
                                    blank=True, editable=False,
                                   )
    is_all_day    = BooleanField(_(u'All day?'), blank=True, default=False)
    busy          = BooleanField(_(u'Busy?'), default=False)
    # TODO: use choices ; to be improved with choices: list-view search/field printers/history
    floating_type = PositiveIntegerField(_(u'Floating type'), default=NARROW,
                                         editable=False,
                                        ).set_tags(viewable=False)

    creation_label = _('Add an activity')

    class Meta:
        abstract = True
        app_label = 'activities'
        verbose_name = _(u'Activity')
        verbose_name_plural = _(u'Activities')
        ordering = ('-start',)

    def as_ical_event(self):
        """Return a normalized iCalendar event string
            /!\ Each parameter has to be separated by \n ONLY no spaces allowed!
            Example : BEGIN:VEVENT\nUID:http://cremecrm.com
        """
        from ..utils import get_ical_date
        return u"""BEGIN:VEVENT
UID:http://cremecrm.com
DTSTAMP:%(dtstamp)s
SUMMARY:%(summary)s
DTSTART:%(dtstart)s
DTEND:%(dtend)s
LOCATION:%(location)s
CATEGORIES:%(categories)s
STATUS:%(status)s
END:VEVENT
""" % {'dtstamp':    get_ical_date(now()),
       'summary':    self.title,
       'dtstart':    get_ical_date(self.start),
       'dtend':      get_ical_date(self.end),
       'location':   '',
       'categories': self.type.name,
       'status':     '',
       }

    def get_title_for_calendar(self):
        return self.title

    @classmethod
    def get_creation_title(cls, type_id):
        return CREATION_LABELS.get(type_id, cls.creation_label)

    def __unicode__(self):
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
        @param real_entities Retrieve (efficiently) the real entities which are related.
        """
        return self.get_relations(REL_OBJ_ACTIVITY_SUBJECT, real_obj_entities=real_entities)

    def get_linkedto_relations(self):
        return self.get_relations(REL_OBJ_LINKED_2_ACTIVITY, real_obj_entities=True)

    # TODO: move to manager the following methods
    # TODO: test
    # @staticmethod
    # def _get_linked_aux(entity):
    @classmethod
    def _get_linked_aux(cls, entity):
        types = (REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)
        # return get_activity_model().objects.filter(is_deleted=False,
        return cls.objects.filter(is_deleted=False,
                                  relations__object_entity=entity,
                                  relations__type__in=types,
                                 ) \
                          .distinct()

    # TODO: test
    # @staticmethod
    # def _get_linked_for_ctypes_aux(ct_ids):
    @classmethod
    def _get_linked_for_ctypes_aux(cls, ct_ids):
        types = (REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)
        # return get_activity_model().objects.filter(is_deleted=False,
        return cls.objects.filter(is_deleted=False,
                                  relations__object_entity__entity_type__in=ct_ids,
                                  relations__type__in=types,
                                 ) \
                          .distinct()

    # TODO: test
    # @staticmethod
    # def _get_linked_for_orga(orga):
    @classmethod
    def _get_linked_for_orga(cls, orga):
        types = (REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)
        entities = [orga]
        entities.extend(orga.get_managers().values_list('id', flat=True))
        entities.extend(orga.get_employees().values_list('id', flat=True))

        # return get_activity_model().objects.filter(is_deleted=False,
        return cls.objects.filter(is_deleted=False,
                                  relations__object_entity__in=entities,
                                  relations__type__in=types,
                                  ) \
                          .distinct()

    # @staticmethod
    # def get_future_linked(entity, today):
    #     return get_activity_model()._get_linked_aux(entity).filter(end__gt=today).order_by('start')
    @classmethod
    def get_future_linked(cls, entity, today):  # TODO end greater than today or floating type equal to floating
        return cls._get_linked_aux(entity).filter(end__gt=today).order_by('start')

    # @staticmethod
    # def get_future_linked_for_ctypes(ct_ids, today):
    #     return get_activity_model()._get_linked_for_ctypes_aux(ct_ids).filter(end__gt=today).order_by('start')
    @classmethod
    def get_future_linked_for_ctypes(cls, ct_ids, today):
        return cls._get_linked_for_ctypes_aux(ct_ids).filter(end__gt=today).order_by('start')

    # @staticmethod
    # def get_future_linked_for_orga(orga, today):
    #     return get_activity_model()._get_linked_for_orga(orga).filter(end__gt=today).order_by('start')
    @classmethod
    def get_future_linked_for_orga(cls, orga, today):
        return cls._get_linked_for_orga(orga).filter(end__gt=today).order_by('start')

    # @staticmethod
    # def get_past_linked(entity, today):
    #     return get_activity_model()._get_linked_aux(entity).filter(end__lte=today).order_by('-start')
    @classmethod
    def get_past_linked(cls, entity, today):
        return cls._get_linked_aux(entity).filter(end__lte=today).order_by('-start')

    # @staticmethod
    # def get_past_linked_for_ctypes(ct_ids, today):
    #     return get_activity_model()._get_linked_for_ctypes_aux(ct_ids).filter(end__lte=today).order_by('-start')
    @classmethod
    def get_past_linked_for_ctypes(cls, ct_ids, today):
        return cls._get_linked_for_ctypes_aux(ct_ids).filter(end__lte=today).order_by('-start')

    # @staticmethod
    # def get_past_linked_for_orga(orga, today):
    #     return get_activity_model()._get_linked_for_orga(orga).filter(end__lte=today).order_by('-start')
    @classmethod
    def get_past_linked_for_orga(cls, orga, today):
        return cls._get_linked_for_orga(orga).filter(end__lte=today).order_by('-start')

    def handle_all_day(self):
        if self.is_all_day:
            self.start = self.start.replace(hour=0, minute=0)
            self.end   = self.end.replace(hour=23, minute=59)

    def _pre_save_clone(self, source):
        # TODO: Explicit this into description ? Move the activity to another time-slot ?
        if source.busy:
            self.busy = False

    def is_auto_orga_subject_enabled(self):
        # TODO: better cache system for SettingValues...
        CACHE_NAME = '_auto_orga_subject_cache'
        enabled = getattr(self, CACHE_NAME, None)

        if enabled is None:
            try:
                sv = SettingValue.objects.get(key_id=SETTING_AUTO_ORGA_SUBJECTS)
            except SettingValue.DoesNotExist:
                logger.critical('SettingValue with key=%s cannot be found !'
                                ' ("creme_populate" command has not been run correctly)',
                                SETTING_AUTO_ORGA_SUBJECTS
                                )
                enabled = False
            else:
                enabled = sv.value

            setattr(self, CACHE_NAME, enabled)

        return enabled

    @staticmethod
    def display_review():
        return SettingValue.objects.get(key_id=DISPLAY_REVIEW_ACTIVITIES_BLOCKS).value

    def count_lines_display_block(self):
        total=1
        if self.get_subject_relations():
            total += 1
        if self.get_participant_relations():
            total += 1
        if self.get_linkedto_relations():
            total += 1
        if self.display_review() and self.minutes:
            total += 1

        return total

    def _copy_relations(self, source):
        super(AbstractActivity, self)._copy_relations(source, allowed_internal=[REL_OBJ_PART_2_ACTIVITY])

    def _pre_delete(self):
        for relation in self.relations.filter(type=REL_OBJ_PART_2_ACTIVITY):
            relation._delete_without_transaction()


class Activity(AbstractActivity):
    class Meta(AbstractActivity.Meta):
        swappable = 'ACTIVITIES_ACTIVITY_MODEL'
