# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from datetime import datetime, time, timedelta
from functools import partial
import logging

from django.forms import IntegerField, BooleanField, ModelChoiceField, ModelMultipleChoiceField
from django.forms.fields import ChoiceField # DateTimeField
from django.forms.util import ValidationError, ErrorList
from django.utils.timezone import localtime
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User

from creme.creme_core.models import RelationType, Relation
from creme.creme_core.forms import CremeEntityForm
#from creme.creme_core.forms.base import FieldBlockManager
from creme.creme_core.forms.fields import (CremeDateTimeField, CremeTimeField,
        MultiCreatorEntityField, MultiGenericEntityField)
from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme.creme_core.forms.validators import validate_linkable_entities, validate_linkable_entity
from creme.creme_core.utils.dates import make_aware_dt

#from creme.creme_config.forms.fields import CreatorModelChoiceField TODO

from creme.persons.models import Contact

from creme.assistants.models import Alert

from ..models import ActivityType, Activity, Calendar, ActivitySubType
from ..constants import *
from ..utils import check_activity_collisions
from .activity_type import ActivityTypeField


logger = logging.getLogger(__name__)


class _ActivityForm(CremeEntityForm):
    type_selector = ActivityTypeField(label=_(u'Type'), types=ActivityType.objects.exclude(pk=ACTIVITYTYPE_INDISPO))

    start      = CremeDateTimeField(label=_(u'Start'), required=False)
    start_time = CremeTimeField(label=_(u'Start time'), required=False)
    end        = CremeDateTimeField(label=_(u'End'), required=False,
                                    help_text=_(u'Default duration of the type will be used if you leave blank.'),
                                   )
    end_time   = CremeTimeField(label=_(u'End time'), required=False)

    class Meta(CremeEntityForm.Meta):
        model = Activity
        exclude = CremeEntityForm.Meta.exclude + ('sub_type',)

    def __init__(self, *args, **kwargs):
        super(_ActivityForm, self).__init__(*args, **kwargs)
        self.participants = [] #all Contacts who participate: me, other users, other contacts

        duration_field = self.fields.get('duration')
        if duration_field:
            duration_field.help_text = _('It is only informative '
                                         'and is not used to compute the end time.'
                                        )

    def clean(self):
        cdata = super(_ActivityForm, self).clean()

        if not self._errors:
            self.floating_type = self._clean_interval(self._get_activity_type_n_subtype()[0])

            start = cdata['start']
            if start:
                collisions = check_activity_collisions(start, cdata['end'],
                                                       self._get_participants_2_check(),
                                                       busy=cdata['busy'],
                                                       exclude_activity_id=self.instance.pk,
                                                      )
                if collisions:
                    raise ValidationError(collisions)

        return cdata

    def _clean_interval(self, atype):
        cdata = self.cleaned_data
        start = cdata['start']
        end   = cdata['end']

        if not start and not end:
            return FLOATING

        floating_type = NARROW

        get = cdata.get
        is_all_day = get('is_all_day', False)
        start_time = get('start_time')
        end_time   = get('end_time')

        #TODO not start, not end, start time, end time => floating activity with time set but lost in the process

        if start_time is None and end_time is None:
            if not is_all_day:
                if get('busy', False):
                    raise ValidationError(ugettext(u"A floating on the day activity can't busy its participants"))

                floating_type = FLOATING_TIME

        if not start and end:
            raise ValidationError(ugettext(u"You can't set the end of your activity without setting its start"))

        if start and start_time:
            #start = datetime.combine(start, start_time)
            start = make_aware_dt(datetime.combine(start, start_time))

        if end and end_time:
            #end = datetime.combine(end, end_time)
            end = make_aware_dt(datetime.combine(end, end_time))

        if start and not end:
            if end_time is not None:
                #end = datetime.combine(start, end_time)
                end = make_aware_dt(datetime.combine(start, end_time))
            else:
                #end = start + atype.as_timedelta()
                tdelta = atype.as_timedelta()

                if (is_all_day or floating_type == FLOATING_TIME) and tdelta.days:
                    # in 'all day' mode, we round the number of day
                    days = tdelta.days - 1 #activity already takes 1 day (we do not want it takes 2)

                    if tdelta.seconds:
                        days += 1

                    tdelta = timedelta(days=days)

                end = start + tdelta

        if is_all_day or floating_type == FLOATING_TIME:
            start = make_aware_dt(datetime.combine(start, time(hour=0, minute=0)))
            end   = make_aware_dt(datetime.combine(end, time(hour=23, minute=59)))

        if start > end:
            raise ValidationError(ugettext(u'End time is before start time'))

        cdata['start'] = start
        cdata['end'] = end

        return floating_type

    def _get_activity_type_n_subtype(self):
        #raise NotImplementedError
        return self.cleaned_data['type_selector']

    def _get_participants_2_check(self):
        return self.participants

    def save(self, *args, **kwargs):
        instance = self.instance
        instance.floating_type = self.floating_type
        instance.type, instance.sub_type = self._get_activity_type_n_subtype()

        super(_ActivityForm, self).save(*args, **kwargs)

        create_relation = partial(Relation.objects.create, object_entity=instance,
                                  type_id=REL_SUB_PART_2_ACTIVITY, user=instance.user,
                                 )

        for participant in self.participants:
            create_relation(subject_entity=participant)

        return instance


class ActivityEditForm(_ActivityForm):
    #sub_type = ModelChoiceField(label=_('Activity type'), required=False,
                                #queryset=ActivitySubType.objects.none(),
                               #) #todo: CreatorModelChoiceField

    blocks = _ActivityForm.blocks.new(
        ('datetime', _(u'When'), ['is_all_day', 'start', 'start_time', 'end', 'end_time']),
    )

    #def _get_activity_type_n_subtype(self):
        #instance = self.instance
        #return instance.type, instance.sub_type

    def _localize(self, dt):
        return localtime(dt) if dt else dt

    def __init__(self, *args, **kwargs):
        super(ActivityEditForm, self).__init__(*args, **kwargs)
        fields = self.fields
        instance = self.instance

        #fields['sub_type'].queryset = ActivitySubType.objects.filter(type=instance.type)
        type_f = fields['type_selector']
        type_f.types = ActivityType.objects.filter(pk=instance.type_id)
        type_f.initial = (instance.type_id, instance.sub_type_id)

        if instance.floating_type == NARROW:
            start = self._localize(instance.start)
            if start:
                fields['start_time'].initial = start.time()

            end = self._localize(instance.end)
            if end:
                fields['end_time'].initial = end.time()

    def _get_participants_2_check(self):
        return self.instance.get_related_entities(REL_OBJ_PART_2_ACTIVITY)


class _ActivityCreateForm(_ActivityForm):
    participating_users = ModelMultipleChoiceField(label=_(u'Other participating users'),
                                                   queryset=User.objects.filter(is_staff=False),
                                                   required=False, widget=UnorderedMultipleChoiceWidget,
                                                  )

    def clean_participating_users(self):
        users = self.cleaned_data['participating_users']
        self.participants.extend(validate_linkable_entities(Contact.objects.filter(is_user__in=users), self.user))
        return users

    def save(self, *args, **kwargs):
        instance = super(_ActivityCreateForm, self).save(*args, **kwargs)

        for part_user in self.cleaned_data['participating_users']:
            #TODO: regroup queries ??
            instance.calendars.add(Calendar.get_user_default_calendar(part_user))

        return instance


MINUTES = 'minutes'

class ActivityCreateForm(_ActivityCreateForm):
    #type_selector = ActivityTypeField(label=_(u'Type'), types=ActivityType.objects.exclude(pk=ACTIVITYTYPE_INDISPO))

    my_participation    = BooleanField(required=False, label=_(u'Do I participate to this activity?'), initial=True)
    my_calendar         = ModelChoiceField(queryset=Calendar.objects.none(), required=False,
                                           label=_(u'On which of my calendar this activity will appears?'),
                                           empty_label=None,
                                          )
    other_participants  = MultiCreatorEntityField(label=_(u'Other participants'), model=Contact, required=False)
    subjects            = MultiGenericEntityField(label=_(u'Subjects'), required=False)
    linked_entities     = MultiGenericEntityField(label=_(u'Entities linked to this activity'), required=False)

    alert_day            = CremeDateTimeField(label=_(u'Alert day'), required=False)
    alert_start_time     = CremeTimeField(label=_(u"Alert time"), required=False)
    alert_trigger_number = IntegerField(label=_(u'Value'), required=False,
                                        help_text=_(u'Your alert will be raised X units (X = Value) before the start of the activity'),
                                       )
    alert_trigger_unit   = ChoiceField(label=_(u'Unit'), required=False,
                                       choices=[(MINUTES, _(u'Minute')),
                                                ('hours', _(u'Hour')),
                                                ('days',  _(u'Day',)),
                                                ('weeks', _(u'Week')),
                                               ],
                                      )

    #class Meta(_ActivityForm.Meta):
        #exclude = _ActivityForm.Meta.exclude + ('sub_type',)

    blocks = _ActivityForm.blocks.new(
        ('datetime',       _(u'When'),         ['start', 'start_time', 'end', 'end_time', 'is_all_day']),
        ('participants',   _(u'Participants'), ['my_participation', 'my_calendar', 'participating_users',
                                                'other_participants', 'subjects', 'linked_entities']),
        ('alert_datetime', _(u'Generate an alert on a specific date'), ['alert_day', 'alert_start_time']),
        ('alert_period',   _(u'Generate an alert in a while'),         ['alert_trigger_number', 'alert_trigger_unit']),
    )

    def __init__(self, activity_type_id=None, *args, **kwargs):
        super(ActivityCreateForm, self).__init__(*args, **kwargs)
        user   = self.user
        fields = self.fields

        if activity_type_id:
            #TODO: improve help_text of end (we know the type default duration)
            fields['type_selector'].types = ActivityType.objects.filter(pk=activity_type_id)

        my_calendar_field = fields['my_calendar']
        my_calendar_field.queryset = Calendar.objects.filter(user=user)
        my_calendar_field.initial  = Calendar.get_user_default_calendar(user)

        #TODO: refactor this with a smart widget that manages dependencies
        fields['my_participation'].widget.attrs['onclick'] = \
            "if($(this).is(':checked')){$('#id_my_calendar').removeAttr('disabled');}else{$('#id_my_calendar').attr('disabled', 'disabled');}"

        fields['subjects'].allowed_models = [ct.model_class() 
                                                for ct in RelationType.objects
                                                                      .get(pk=REL_SUB_ACTIVITY_SUBJECT)
                                                                      .subject_ctypes.all()
                                            ]
        fields['participating_users'].queryset = User.objects.filter(is_staff=False).exclude(pk=user.id)
        fields['other_participants'].q_filter = {'is_user__isnull': True}

    def clean_my_participation(self):
        my_participation = self.cleaned_data.get('my_participation', False)

        if my_participation:
            user = self.user

            #try:
                #user_contact = Contact.objects.get(is_user=user)
            #except Contact.DoesNotExist:
                #logger.warn('No Contact linked to this user: %s', user)
            #else:
                #self.participants.append(validate_linkable_entity(user_contact, user))
            self.participants.append(validate_linkable_entity(user.linked_contact, user))

        return my_participation

    def clean_other_participants(self):
        participants = self.cleaned_data['other_participants']
        self.participants.extend(validate_linkable_entities(participants, self.user))
        return participants

    def clean_subjects(self):
        return validate_linkable_entities(self.cleaned_data['subjects'], self.user)

    def clean_linked_entities(self):
        return validate_linkable_entities(self.cleaned_data['linked_entities'], self.user)

    def clean(self):
        if not self._errors:
            cdata = self.cleaned_data
            my_participation = cdata['my_participation']
            if my_participation and not cdata.get('my_calendar'):
                self.errors['my_calendar'] = ErrorList([ugettext(u'If you participate, you have to choose one of your calendars.')])

            if not my_participation and not cdata['participating_users']:
                raise ValidationError(ugettext('No participant'))

            if cdata.get('alert_day') and cdata.get('alert_start_time') is None:
                raise ValidationError(ugettext('If you want this alert you must specify date and time')) #TODO: not global error

        return super(ActivityCreateForm, self).clean()

    #def _get_activity_type_n_subtype(self):
        #return self.cleaned_data['type_selector']

    def save(self, *args, **kwargs):
        instance = super(ActivityCreateForm, self).save(*args, **kwargs)

        self._generate_alerts()

        cdata = self.cleaned_data

        if cdata['my_participation']:
            instance.calendars.add(cdata['my_calendar'])

        create_relation = partial(Relation.objects.create, object_entity=instance, user=instance.user)

        for entities, rtype_id in ((cdata['subjects'],        REL_SUB_ACTIVITY_SUBJECT),
                                   (cdata['linked_entities'], REL_SUB_LINKED_2_ACTIVITY),
                                  ):
            for entity in entities:
                create_relation(subject_entity=entity, type_id=rtype_id)

        return instance

    def _create_alert(self, activity, trigger_date):
        Alert.objects.create(user=activity.user,
                             trigger_date=trigger_date,
                             creme_entity=activity,
                             title=ugettext('Alert of activity'),
                             description=ugettext(u'Alert related to %s') % activity,
                            )

    def _generate_alerts(self):
        get = self.cleaned_data.get
        activity = self.instance
        specific_date_alert = get('alert_day')

        if specific_date_alert:
            start_time = get('alert_start_time')
            self._create_alert(activity,
                               specific_date_alert.replace(hour=start_time.hour,
                                                           minute=start_time.minute,
                                                          )
                              )

        amount = get('alert_trigger_number')

        if amount:
            self._create_alert(activity,
                               activity.start - timedelta(**{get('alert_trigger_unit') or MINUTES: amount})
                              )


class RelatedActivityCreateForm(ActivityCreateForm):
    def __init__(self, related_entity, relation_type_id, *args, **kwargs):
        super(RelatedActivityCreateForm, self).__init__(*args, **kwargs)

        if relation_type_id == REL_SUB_PART_2_ACTIVITY:
            assert isinstance(related_entity, Contact)

            if related_entity.is_user:
                self.fields['participating_users'].initial = [related_entity.is_user]
            else:
                self.fields['other_participants'].initial = [related_entity]
        elif relation_type_id == REL_SUB_ACTIVITY_SUBJECT:
            self.fields['subjects'].initial = [related_entity]
        else:
            assert relation_type_id == REL_SUB_LINKED_2_ACTIVITY
            self.fields['linked_entities'].initial = [related_entity]


class CalendarActivityCreateForm(ActivityCreateForm):
    class Meta(ActivityCreateForm.Meta):
        exclude = ActivityCreateForm.Meta.exclude + ('minutes', )

    def __init__(self, start=None, *args, **kwargs):
        super(CalendarActivityCreateForm, self).__init__(*args, **kwargs)
        fields = self.fields
        fields['participating_users'].widget.attrs = {'reduced': 'true'}

        if start: #normally there's always a start_date for this kind of add
            fields['start'].initial = start
            hour = start.hour
            minute = start.minute

            if hour or minute: #in case start date is not a simple date (add from month view in the calendar)
                fields['start_time'].initial = time(hour=hour, minute=minute) #avoid 00h00 for start time in this case


class IndisponibilityCreateForm(_ActivityCreateForm):
    type_selector = ModelChoiceField(label=_('Indisponibility type'), required=False,
                                     queryset=ActivitySubType.objects.filter(type=ACTIVITYTYPE_INDISPO),
                                    ) #TODO: CreatorModelChoiceField

    class Meta(_ActivityCreateForm.Meta):
        exclude = _ActivityCreateForm.Meta.exclude + (
                        'place', 'description', 'minutes', 'busy', 'status',
                        'duration',
                    ) #'sub_type' #TODO: test

    blocks = _ActivityCreateForm.blocks.new(
        ('datetime',     _(u'When'),         ['is_all_day', 'start', 'start_time', 'end', 'end_time']),
        ('participants', _(u'Participants'), ['participating_users']),
    )

    def __init__(self, activity_type_id=None, *args, **kwargs):
        assert activity_type_id == ACTIVITYTYPE_INDISPO
        super(IndisponibilityCreateForm, self).__init__(*args, **kwargs)
        fields = self.fields

        fields['start'].required = True

        end_f = fields['end']
        end_f.required = True
        end_f.help_text = None

        p_users_field = fields['participating_users']
        p_users_field.label = _(u'Unavailable users')
        p_users_field.required = True


    def clean(self):
        self.cleaned_data['busy'] = True
        return super(IndisponibilityCreateForm, self).clean()

    def _get_activity_type_n_subtype(self):
        return (ActivityType.objects.get(pk=ACTIVITYTYPE_INDISPO),
                self.cleaned_data['type_selector'],
               )
