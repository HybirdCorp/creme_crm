# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from logging import debug
from datetime import datetime

from django.db.models import CharField, IntegerField, TimeField, DateTimeField, TextField, ForeignKey, BooleanField, PositiveIntegerField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, CremeModel, Relation

from activities.constants import *
from activities.utils import get_ical_date


class ActivityType(CremeModel):
    id                    = CharField(primary_key=True, max_length=100)
    name                  = CharField(_(u'Name'), max_length=100)
    color                 = CharField(_(u'Color'), max_length=100, blank=True , null=True)
    default_day_duration  = IntegerField(_(u'Default day duration'))
    default_hour_duration = TimeField(_(u'Default hour duration'))

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'activities'
        verbose_name = _(u"Activity type")
        verbose_name_plural = _(u"Activity types")


class Activity(CremeEntity):
    """Activity : event or task"""
    title       = CharField(_(u'Title'), max_length=100)
    start       = DateTimeField(_(u'Start'), blank=True, null=True)
    end         = DateTimeField(_(u'End'), blank=True, null=True)
    description = TextField(_(u'Description'), blank=True, null=True)
    type        = ForeignKey(ActivityType, verbose_name=_(u"Activity type"))
    is_all_day  = BooleanField(_(u'All day ?'), blank=True, default=False)

    research_fields = CremeEntity.research_fields + ['title', 'type__name']
    excluded_fields_in_html_output = CremeEntity.excluded_fields_in_html_output + ['type', 'activity_ptr']

    class Meta:
        app_label = 'activities'
        verbose_name = _(u'Activity')
        verbose_name_plural = _(u'Activities')

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
        type_name = self.type.name

        #TODO: beuark (use a registry instead ??)

        if type_name == 'Formation':
            return self.trainingdate.get_title_for_calendar()

        if type_name == 'Indisponible':
            return  'Indisponible %s  %s' % (self.title, self.user.username)

        return  '%s  %s' % (self.title, self.user.username)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return "/activities/activity/%s" % self.id

    def get_edit_absolute_url(self):
        return "/activities/activity/edit/%s" % self.id

    def get_delete_absolute_url(self):
        return "/activities/activity/delete/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/activities/activities"

    def get_participant_relations(self):
        return Relation.objects.filter(object_entity=self, type=REL_SUB_PART_2_ACTIVITY)

    def get_subject_relations(self):
        return Relation.objects.filter(object_entity=self, type=REL_SUB_ACTIVITY_SUBJECT)

    def get_linkedto_relations(self):
        return Relation.objects.filter(object_entity=self, type=REL_SUB_LINKED_2_ACTIVITY)

    @staticmethod
    def _get_linked_aux(entity):
        types = (REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT, REL_OBJ_LINKED_2_ACTIVITY)
        return Activity.objects.filter(relations__object_entity=entity, relations__type__in=types)

    @staticmethod
    def get_future_linked(entity, today):
        return Activity._get_linked_aux(entity).filter(end__gt=today)

    @staticmethod
    def get_past_linked(entity, today):
        return Activity._get_linked_aux(entity).filter(end__lte=today)

    def handle_all_day(self):
        if self.is_all_day:
            self.start = self.start.replace(hour=0, minute=0)
            self.end   = self.end.replace(hour=23, minute=59)


class Meeting(Activity):
    place = CharField(_(u'Meeting place'), max_length=100, blank=True, null=True)

    def __init__(self, *args, **kwargs):
        super(Meeting, self).__init__(*args, **kwargs)
        self.type_id = ACTIVITYTYPE_MEETING

    class Meta:
        app_label = 'activities'
        verbose_name = _('Meeting')
        verbose_name_plural = _(u'Meetings')


class TaskStatus(CremeModel):
    name        = CharField(_(u'Name'), max_length=100)
    description = TextField(_(u'Description'))

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'activities'
        verbose_name = _(u'Task status')
        verbose_name_plural = _(u'Task status') #arf plural....


class Task(Activity):
    duration = PositiveIntegerField(_(u'Duration (in hour)'), blank=True, null=True)
    status   = ForeignKey(TaskStatus, verbose_name=_(u'Status'))

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

    def __init__(self, *args, **kwargs):
        super(PhoneCall, self).__init__(*args, **kwargs)
        self.type_id = ACTIVITYTYPE_PHONECALL

    class Meta:
        app_label = 'activities'
        verbose_name = _(u'Phone call')
        verbose_name_plural = _(u'Phone calls')
