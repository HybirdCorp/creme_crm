# -*- coding: utf-8 -*-
#TODO: factorise with ActivityCreateForm ??
#TODO: for the moment the calendars info on detailview is not reload because it is not a true Block.
class ParticipantCreateForm(CremeForm):
    participating_users = ModelMultipleChoiceField(label=_(u'Participating users'), queryset=User.objects.all(),
                                                   required=False, widget=UnorderedMultipleChoiceWidget
                                                  )
    other_participants  = MultiCremeEntityField(label=_(u'Other participants'), model=Contact, required=False)

    def __init__(self, activity, *args, **kwargs):
        super(ParticipantCreateForm, self).__init__(*args, **kwargs)
        self.activity = activity
        self.participants = []

        existing = Contact.objects.filter(relations__type=REL_SUB_PART_2_ACTIVITY, relations__object_entity=activity.id)
        user_ids = [contact.is_user_id for contact in existing if contact.is_user_id]

        fields = self.fields
        fields['participating_users'].queryset = User.objects.exclude(pk__in=user_ids)
        fields['other_participants'].q_filter = {'~pk__in': [c.id for c in existing], 'is_user__isnull': True}

    def clean(self):
        cleaned_data = self.cleaned_data

        if not self._errors:
            activity = self.activity
            participants = self.participants

            participants.extend(Contact.objects.filter(is_user__in=cleaned_data['participating_users']))
            participants += cleaned_data['other_participants']

            if activity.busy:
                _check_activity_collisions(activity.start, activity.end, participants)

        return cleaned_data

    def save(self):
        activity = self.activity

        create_link = CalendarActivityLink.objects.get_or_create
        for part_user in self.cleaned_data['participating_users']:
            #TODO: regroup queries ??
            create_link(calendar=Calendar.get_user_default_calendar(part_user), activity=activity)

        create_relation = partial(Relation.objects.create, object_entity=activity,
                                  type_id=REL_SUB_PART_2_ACTIVITY, user=activity.user)
        for participant in self.participants:
            create_relation(subject_entity=participant)