# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.db.models import (PositiveIntegerField, DateTimeField, CharField, TextField,
                              BooleanField, ManyToManyField, ForeignKey, PROTECT, SET_NULL)
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeEntity, Relation

from creme.creme_config.models import SettingValue

from ..constants import *
from .calendar import Calendar
from .other_models import ActivityType, ActivitySubType, Status


class Activity(CremeEntity):
    "Activity : task, meeting, phone call, indisponibility, ..."
    title         = CharField(_(u'Title'), max_length=100)
    start         = DateTimeField(_(u'Start'), blank=True, null=True)
    end           = DateTimeField(_(u'End'), blank=True, null=True)
    description   = TextField(_(u'Description'), blank=True, null=True)
    minutes       = TextField(_(u'Minutes'), blank=True, null=True)
    place         = CharField(_(u'Activity place'), max_length=100, blank=True, null=True)
    duration      = PositiveIntegerField(_(u'Duration (in hour)'), blank=True, null=True)
    type          = ForeignKey(ActivityType, verbose_name=_(u'Activity type'),
                               on_delete=PROTECT, editable=False,
                              )
    sub_type      = ForeignKey(ActivitySubType, verbose_name=_(u'Activity sub-type'),
                               blank=True, null=True, on_delete=SET_NULL,
                              )
    status        = ForeignKey(Status, verbose_name=_(u'Status'), blank=True, null=True)
    calendars     = ManyToManyField(Calendar, verbose_name=_(u'Calendars'),
                                    blank=True, null=True, editable=False,
                                   )
    is_all_day    = BooleanField(_(u'All day?'), blank=True, default=False)
    busy          = BooleanField(_(u'Busy?'), default=False)
    #TODO: use choices ; to be improved with choices: listview search/field printers/history
    floating_type = PositiveIntegerField(_(u'Floating type'), default=NARROW,
                                         editable=False,
                                        ).set_tags(viewable=False)


    creation_label = _('Add an activity')
    #research_fields = CremeEntity.research_fields + ['title', 'type__name']
    #excluded_fields_in_html_output = CremeEntity.excluded_fields_in_html_output + ['activity_ptr', 'floating_type']

    class Meta:
        app_label = 'activities'
        verbose_name = _(u'Activity')
        verbose_name_plural = _(u'Activities')
        ordering = ('-start',)

    def as_ical_event(self):
        """Return a normalized iCalendar event string
            /!\ Each parameter has to be separated by \n ONLY no spaces allowed!
            Example : BEGIN:VEVENT\nUID:http://cremecrm.com"""
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
        return u'%s - %s' % (self.title, self.user)

    @classmethod
    def get_creation_title(cls, type_id):
        return CREATION_LABELS.get(type_id, cls.creation_label)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return "/activities/activity/%s" % self.id

    def get_edit_absolute_url(self):
        return "/activities/activity/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
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
    def get_future_linked(entity, today): #TODO end greater than today or floating type equal to floating
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


#class Meeting(Activity):
    #place = CharField(_(u'Meeting place'), max_length=100, blank=True, null=True)

    #def __init__(self, *args, **kwargs):
        #super(Meeting, self).__init__(*args, **kwargs)
        #self.type_id = ACTIVITYTYPE_MEETING

    #class Meta:
        #app_label = 'activities'


#class Task(Activity):
    #duration = PositiveIntegerField(_(u'Duration (in hour)'), blank=True, null=True)

    #def __init__ (self, *args , **kwargs):
        #super(Task, self).__init__(*args, **kwargs)
        #self.type_id = ACTIVITYTYPE_TASK

    #class Meta:
        #app_label = 'activities'


#class PhoneCallType(CremeModel):
    #name        = CharField(_(u"Call type"), max_length=100, blank=True, null=True)
    #description = TextField(_(u'Description'))

    #def __unicode__(self):
        #return self.name

    #class Meta:
        #app_label = 'activities'


#class PhoneCall(Activity):
    #call_type = ForeignKey(PhoneCallType, verbose_name=_(u"Phonecall type"), blank=True, null=True)

    #def __init__(self, *args, **kwargs):
        #super(PhoneCall, self).__init__(*args, **kwargs)
        #self.type_id = ACTIVITYTYPE_PHONECALL

    #class Meta:
        #app_label = 'activities'


@receiver(post_delete, sender=Relation)
def _set_null_calendar_on_delete_participant(sender, instance, **kwargs):
    type_id = instance.type_id

    if type_id == REL_SUB_PART_2_ACTIVITY:
        contact  = instance.subject_entity.get_real_entity()
        activity = instance.object_entity.get_real_entity()
    elif type_id == REL_OBJ_PART_2_ACTIVITY:
        contact  = instance.object_entity.get_real_entity()
        activity = instance.subject_entity.get_real_entity()
    else:
        return

    if contact.is_user:
        activity.calendars.remove(Calendar.get_user_default_calendar(contact.is_user))
