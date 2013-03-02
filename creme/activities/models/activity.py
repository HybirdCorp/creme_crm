# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from datetime import datetime

from django.db.models import (CharField, IntegerField, DateTimeField, TextField,
                              ForeignKey, BooleanField, PositiveIntegerField, PROTECT)
from django.db.models.fields.related import ManyToManyField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, CremeModel
from creme_core.models.fields import DurationField, CremeUserForeignKey

from creme_config.models.setting import SettingValue

from activities.constants import *
from activities.utils import get_ical_date


class Calendar(CremeModel):
    name        = CharField(_(u'Name'), max_length=100, unique=True)
    is_default  = BooleanField(_(u'Default ?'), default=False)
    is_custom   = BooleanField(default=True, editable=False) #used by creme_config
    is_public   = BooleanField(default=False, verbose_name=_(u"Is public ?"))
    user        = CremeUserForeignKey(verbose_name=_(u"Calendar owner"))

    class Meta:
        app_label = 'activities'
        verbose_name = _(u"Calendar")
        verbose_name_plural = _(u"Calendars")
        ordering = ['name']

    def __unicode__(self):
        return self.name

    @staticmethod
    def get_user_calendars(user, get_default_if_none=True):
        calendars = Calendar.objects.filter(user=user)
        if not calendars and get_default_if_none:
            calendars = [Calendar.get_user_default_calendar(user)]
        return calendars

    @staticmethod
    def get_user_default_calendar(user):
        """ Returns the default user calendar and creating it if necessary"""
        try:
            return Calendar.objects.get(user=user, is_default=True)
        except Calendar.DoesNotExist:
            try:
                c = Calendar.objects.filter(user=user)[0]
                c.is_default = True
                c.save()
                return c
            except IndexError:
                return Calendar.objects.create(name=_(u"Default %(user)s's calendar") % {'user': user},
                                               user=user,
                                               is_default=True,
                                               is_custom=False)
        except Calendar.MultipleObjectsReturned:
            calendars = Calendar.objects.filter(user=user)
            calendars.update(is_default=False)
            c = calendars[0]
            c.is_default = True
            c.save()
            return c



class ActivityType(CremeModel):
    id                    = CharField(primary_key=True, max_length=100)
    name                  = CharField(_(u'Name'), max_length=100)
    color                 = CharField(_(u'Color'), max_length=100, blank=True, null=True)
    default_day_duration  = IntegerField(_(u'Default day duration'))
    default_hour_duration = DurationField(_(u'Default hour duration'), max_length=15)
    is_custom             = BooleanField(default=True) #used by creme_config

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'activities'
        verbose_name = _(u"Activity type")
        verbose_name_plural = _(u"Activity types")


class Status(CremeModel):
    name        = CharField(_(u'Name'), max_length=100)
    description = TextField(_(u'Description'))

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'activities'
        verbose_name = _(u'Status')
        verbose_name_plural = _(u'Status') #arf plural....


class Activity(CremeEntity):
    """Activity : event or task"""
    title       = CharField(_(u'Title'), max_length=100)
    start       = DateTimeField(_(u'Start'), blank=True, null=True)
    end         = DateTimeField(_(u'End'), blank=True, null=True)
    description = TextField(_(u'Description'), blank=True, null=True)
    minutes     = TextField(_(u'Minutes'), blank=True, null=True)
    type        = ForeignKey(ActivityType, verbose_name=_(u"Activity type"), on_delete=PROTECT)
    calendars   = ManyToManyField(Calendar, verbose_name=_(u"Calendars"), blank=True, null=True)
    is_all_day  = BooleanField(_(u'All day ?'), blank=True, default=False)
    status      = ForeignKey(Status, verbose_name=_(u'Status'), blank=True, null=True)
    busy        = BooleanField(_(u'Busy ?'), default=False)

    creation_label = _('Add an activity')
    #research_fields = CremeEntity.research_fields + ['title', 'type__name']
    #excluded_fields_in_html_output = CremeEntity.excluded_fields_in_html_output + ['activity_ptr', ]

    class Meta:
        app_label = 'activities'
        verbose_name = _(u'Activity')
        verbose_name_plural = _(u'Activities')
        ordering =('-start',)

    def as_ical_event(self):
        """Return a normalized iCalendar event string
            /!\ Each parameter has to be separated by \n ONLY no spaces allowed!
            Example : BEGIN:VEVENT\nUID:http://cremecrm.com"""
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
""" % {
                    'dtstamp'    : get_ical_date(datetime.now()),
                    'summary'    : self.title,
                    'dtstart'    : get_ical_date(self.start),
                    'dtend'      : get_ical_date(self.end),
                    'location'   : "",
                    'categories' : self.type.name,
                    'status'     : ""
                }

    def get_title_for_calendar(self):
        return  '%s  %s' % (self.title, self.user.username)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return "/activities/activity/%s" % self.id

    def get_edit_absolute_url(self):
        return "/activities/activity/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/activities/activities"

    def get_participant_relations(self):
        return self.get_relations(REL_OBJ_PART_2_ACTIVITY, real_obj_entities=True)

    def get_subject_relations(self):
        return self.get_relations(REL_OBJ_ACTIVITY_SUBJECT, real_obj_entities=True)

    def get_linkedto_relations(self):
        return self.get_relations(REL_OBJ_LINKED_2_ACTIVITY, real_obj_entities=True)

    #TODO: test
    @staticmethod
    def _get_linked_aux(entity):
        types = (REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)
        return Activity.objects.filter(is_deleted=False,
                                       relations__object_entity=entity,
                                       relations__type__in=types,
                                      ) \
                               .distinct()

    #TODO: test
    @staticmethod
    def _get_linked_for_ctypes_aux(ct_ids):
        types = (REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)
        return Activity.objects.filter(is_deleted=False,
                                       relations__object_entity__entity_type__in=ct_ids,
                                       relations__type__in=types,
                                      ) \
                               .distinct()

    #TODO: test
    @staticmethod
    def _get_linked_for_orga(orga):
        types = (REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)
        entities = [orga]
        entities.extend(orga.get_managers().values_list('id', flat=True))
        entities.extend(orga.get_employees().values_list('id', flat=True))
        return Activity.objects.filter(is_deleted=False,
                                       relations__object_entity__in=entities,
                                       relations__type__in=types,
                                      ) \
                               .distinct()

    @staticmethod
    def get_future_linked(entity, today):
        return Activity._get_linked_aux(entity).filter(end__gt=today).order_by('start')

    @staticmethod
    def get_future_linked_for_ctypes(ct_ids, today):
        return Activity._get_linked_for_ctypes_aux(ct_ids).filter(end__gt=today).order_by('start')

    @staticmethod
    def get_future_linked_for_orga(orga, today):
        return Activity._get_linked_for_orga(orga).filter(end__gt=today).order_by('start')

    @staticmethod
    def get_past_linked(entity, today):
        return Activity._get_linked_aux(entity).filter(end__lte=today).order_by('-start')

    @staticmethod
    def get_past_linked_for_ctypes(ct_ids, today):
        return Activity._get_linked_for_ctypes_aux(ct_ids).filter(end__lte=today).order_by('-start')

    @staticmethod
    def get_past_linked_for_orga(orga, today):
        return Activity._get_linked_for_orga(orga).filter(end__lte=today).order_by('-start')

    def handle_all_day(self):
        if self.is_all_day:
            self.start = self.start.replace(hour=0, minute=0)
            self.end   = self.end.replace(hour=23, minute=59)

    def _pre_save_clone(self, source):
        #TODO: Explicit this into description ? Move the activity to another time-slot ?
        if source.busy:
            self.busy = False

    @staticmethod
    def display_review():
        return SettingValue.objects.get(key=DISPLAY_REVIEW_ACTIVITIES_BLOCKS).value

    def count_lines_display_block(self):
        total=1
        if self.get_subject_relations():
            total += 1
        if self.get_participant_relations():
            total += 1
        if self.get_linkedto_relations():
            total += 1
        if Activity.display_review() and self.minutes:
            total += 1
        return total

    def _copy_relations(self, source):
        super(Activity, self)._copy_relations(source, allowed_internal=[REL_OBJ_PART_2_ACTIVITY])


class Meeting(Activity):
    place = CharField(_(u'Meeting place'), max_length=100, blank=True, null=True)

    #excluded_fields_in_html_output = Activity.excluded_fields_in_html_output + ['type']

    def __init__(self, *args, **kwargs):
        super(Meeting, self).__init__(*args, **kwargs)
        self.type_id = ACTIVITYTYPE_MEETING

    class Meta:
        app_label = 'activities'
        verbose_name = _('Meeting')
        verbose_name_plural = _(u'Meetings')


class Task(Activity):
    duration = PositiveIntegerField(_(u'Duration (in hour)'), blank=True, null=True)

    #excluded_fields_in_html_output = Activity.excluded_fields_in_html_output + ['type']

    def __init__ (self, *args , **kwargs):
        super(Task, self).__init__(*args, **kwargs)
        self.type_id = ACTIVITYTYPE_TASK

    class Meta:
        app_label = 'activities'
        verbose_name = _(u'Task')
        verbose_name_plural = _(u'Tasks')


class PhoneCallType(CremeModel):
    name        = CharField(_(u"Call type"), max_length=100, blank=True, null=True)
    description = TextField(_(u'Description'))

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'activities'
        verbose_name = _("Phonecall type")
        verbose_name_plural = _(u"Phonecall types")


class PhoneCall(Activity):
    call_type = ForeignKey(PhoneCallType, verbose_name=_(u"Phonecall type"), blank=True, null=True)

    #excluded_fields_in_html_output = Activity.excluded_fields_in_html_output + ['type']

    def __init__(self, *args, **kwargs):
        super(PhoneCall, self).__init__(*args, **kwargs)
        self.type_id = ACTIVITYTYPE_PHONECALL

    class Meta:
        app_label = 'activities'
        verbose_name = _(u'Phone call')
        verbose_name_plural = _(u'Phone calls')

