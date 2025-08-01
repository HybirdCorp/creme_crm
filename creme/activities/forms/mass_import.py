################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2025  Hybird
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
from collections import OrderedDict
from datetime import datetime, time
from functools import partial

from django.core.exceptions import ValidationError
from django.db.models.query_utils import Q
from django.forms import Field
from django.utils.timezone import make_aware
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from creme import persons
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.forms.mass_import import (
    BaseExtractorWidget,
    ImportForm4CremeEntity,
)
from creme.creme_core.forms.widgets import PrettySelect
from creme.creme_core.models import Relation, RelationType
from creme.creme_core.utils import as_int
from creme.creme_core.utils.chunktools import iter_as_chunk
from creme.persons.models import Civility

from .. import constants
from ..models import Calendar
from . import fields as act_fields
from .fields import ActivitySubTypeField

logger = logging.getLogger(__name__)
Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()

MODE_MULTICOLUMNS   = 1
MODE_SPLITTEDCOLUMN = 2

# Maximum of CremeEntities that can be retrieved in _one_ search for Participants/Subjects
# (more means that there is a big problem with the file, & no CremeEntity is created)
MAX_RELATIONSHIPS = 5


class RelatedExtractor:
    def __init__(self, create_if_unfound=False):
        self._create = create_if_unfound

    def extract_value(self, line, user):
        return (), ()

    def _searched_contact(self, first_name, last_name):
        return Contact(first_name=first_name, last_name=last_name)

    def _search_n_create_contacts(self, user, civility, first_name, last_name):
        extracted = ()
        err_msg = None
        query_dict = {'last_name__iexact': last_name}

        if first_name:
            query_dict['first_name__iexact'] = first_name

        # TODO: filter with link credentials too (because here we limit
        #       _before_ filtering not linkable...)
        contacts = EntityCredentials.filter(
            user, Contact.objects.filter(**query_dict),
        )[:MAX_RELATIONSHIPS + 1]

        if contacts:
            has_perm = user.has_perm_to_link
            contacts = [c for c in contacts if has_perm(c)]

            if contacts:
                length = len(contacts)

                if length > MAX_RELATIONSHIPS:
                    err_msg = _(
                        'Too many contacts were found for the search «{}»'
                    ).format(self._searched_contact(first_name, last_name))
                else:
                    if length > 1:
                        err_msg = _(
                            'Several contacts were found for the search «{}»'
                        ).format(self._searched_contact(first_name, last_name))

                    extracted = contacts
            else:
                err_msg = _(
                    'No linkable contact found for the search «{}»'
                ).format(self._searched_contact(first_name, last_name))
        elif self._create:
            extracted = [
                Contact.objects.create(
                    user=user,
                    first_name=first_name,
                    last_name=last_name,
                    civility=(
                        Civility.objects.filter(
                            Q(title=civility) | Q(shortcut=civility)
                        ).first()
                        if civility else
                        None
                    ),
                ),
            ]
        else:
            err_msg = _(
                'The participant «{}» cannot be found'
            ).format(self._searched_contact(first_name, last_name))

        return extracted, (err_msg,) if err_msg else ()


# Participants -----------------------------------------------------------------
def _contact_pattern(verbose_name):
    def _aux(fun):
        fun.verbose_name = verbose_name
        return fun

    return _aux


# NB: 'C' means Civility
#     'F' means First name
#     'L' means Last name
@_contact_pattern(gettext_lazy('Civility FirstName LastName'))
def _pattern_CFL(contact_as_str):
    names = contact_as_str.split(None, 2)
    last_name = names[-1].strip()
    length = len(names)

    if length > 1:
        civ        = names[0] if length > 2 else None
        first_name = names[-2]
    else:
        civ = first_name = None

    return civ, first_name, last_name


@_contact_pattern(gettext_lazy('Civility LastName FirstName'))
def _pattern_CLF(contact_as_str):
    names = contact_as_str.split()
    length = len(names)

    if length > 1:
        first_name = names[-1].strip()

        if length > 2:
            civ = names[0]
            last_name = ' '.join(names[1:-1])
        else:
            civ = None
            last_name = names[0]
    else:
        civ = first_name = None
        last_name = names[0]

    return civ, first_name, last_name


@_contact_pattern(gettext_lazy('FirstName LastName'))
def _pattern_FL(contact_as_str):
    names = contact_as_str.split(None, 1)
    last_name  = names[-1].strip()
    first_name = names[0] if len(names) > 1 else None

    return None, first_name, last_name


@_contact_pattern(gettext_lazy('LastName FirstName'))
def _pattern_LF(contact_as_str):
    names = contact_as_str.rsplit(None, 1)
    last_name  = names[0].strip()
    first_name = names[1] if len(names) == 2 else None

    return None, first_name, last_name


_PATTERNS = OrderedDict([
    ('1', _pattern_CFL),
    ('2', _pattern_CLF),
    ('3', _pattern_FL),
    ('4', _pattern_LF),
])


class MultiColumnsParticipantsExtractor(RelatedExtractor):
    def __init__(self, first_name_index, last_name_index, create_if_unfound=False):
        super().__init__(create_if_unfound)
        self._first_name_index = first_name_index - 1 if first_name_index else None
        self._last_name_index = last_name_index - 1

    def extract_value(self, line, user):
        first_name = None
        last_name = line[self._last_name_index]
        first_name_index = self._first_name_index

        if first_name_index is not None:  # None -> not in CSV
            first_name = line[first_name_index]

        return self._search_n_create_contacts(user, None, first_name, last_name)


class SplitColumnParticipantsExtractor(RelatedExtractor):
    def __init__(self, column_index, separator, pattern_func, create_if_unfound=False):
        super().__init__(create_if_unfound)
        self._column_index = column_index - 1
        self._separator = separator
        self._pattern_func = pattern_func

    def extract_value(self, line, user):
        extracted = []
        global_err_msg = []
        search = partial(self._search_n_create_contacts, user)
        func = self._pattern_func

        for contact_as_str in line[self._column_index].split(self._separator):
            if contact_as_str:
                contacts, err_msg = search(*func(contact_as_str))

                extracted.extend(contacts)
                global_err_msg.extend(err_msg)

        return extracted, global_err_msg


class ParticipantsExtractorWidget(BaseExtractorWidget):
    template_name = 'activities/forms/widgets/mass-import/participants-extractor.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.propose_creation = False

    def get_context(self, name, value, attrs):
        value = value or {}
        context = super().get_context(name=name, value=value, attrs=attrs)

        widget_cxt = context['widget']
        widget_cxt['MULTICOLUMNS']   = MODE_MULTICOLUMNS
        widget_cxt['SPLITTEDCOLUMN'] = MODE_SPLITTEDCOLUMN
        widget_cxt['create']    = value.get('create', False)
        widget_cxt['separator'] = value.get('separator', '/')
        widget_cxt['mode']      = value.get('mode', 0)
        widget_cxt['propose_creation'] = self.propose_creation

        id_attr = widget_cxt['attrs']['id']

        def column_select_context(name_fmt, selected_key):
            return self.column_select.get_context(
                name=name_fmt.format(name),
                value=value.get(selected_key),
                attrs={
                    'id': name_fmt.format(id_attr),
                    'class': 'csv_col_select',
                },
            )['widget']

        # Mode MULTICOLUMNS
        widget_cxt['firstname_column_select'] = column_select_context(
            name_fmt='{}_first_name_colselect', selected_key='first_name_column_index',
        )
        widget_cxt['lastname_column_select'] = column_select_context(
            name_fmt='{}_last_name_colselect', selected_key='last_name_column_index',
        )

        # Mode SPLITTEDCOLUMN
        widget_cxt['pattern_column_select'] = column_select_context(
            name_fmt='{}_pattern_colselect', selected_key='pattern_column_index',
        )

        widget_cxt['pattern_select'] = PrettySelect(
            choices=[
                (pattern_id, str(pattern.verbose_name))
                for pattern_id, pattern in _PATTERNS.items()
            ],
        ).get_context(
            name=f'{name}_pattern',
            value=value.get('pattern_id'),
            attrs={
                'id': f'{id_attr}_pattern',
                'class': 'csv_pattern_select',
            },
        )['widget']

        return context

    def value_from_datadict(self, data, files, name):
        get = data.get

        return {
            'mode': as_int(get(f'{name}_mode'), 1),

            'first_name_column_index': as_int(get(f'{name}_first_name_colselect')),
            'last_name_column_index':  as_int(get(f'{name}_last_name_colselect')),

            'pattern_column_index': as_int(get(f'{name}_pattern_colselect')),
            'separator':    get(f'{name}_separator', '/'),
            'pattern_id':   get(f'{name}_pattern'),
            'create':       get(f'{name}_create', False),
        }


class ParticipantsExtractorField(Field):
    def __init__(self, *, choices, **kwargs):
        super().__init__(widget=ParticipantsExtractorWidget, **kwargs)
        self._user = None
        self._can_create = False
        self._allowed_indexes = {c[0] for c in choices}

        self.widget.choices = choices

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self.widget.propose_creation = self._can_create = user.has_perm_to_create(Contact)

    def _clean_index(self, value, key):
        try:
            index = int(value[key])
        except TypeError as e:
            raise ValidationError(f'Invalid value for index "{key}"') from e

        if index not in self._allowed_indexes:
            raise ValidationError('Invalid index')

        return index

    def _clean_mode(self, value):  # TODO: factorise
        try:
            mode = int(value['mode'])
        except TypeError as e:
            raise ValidationError('Invalid value for mode') from e

        return mode

    def _manage_empty(self):
        if self.required:
            raise ValidationError(self.error_messages['required'])

        return RelatedExtractor()  # Empty extractor

    def clean(self, value):
        mode = self._clean_mode(value)
        clean_index = partial(self._clean_index, value)
        create_if_unfound = value['create'] and self._can_create

        if mode == MODE_MULTICOLUMNS:
            first_name_index = clean_index('first_name_column_index')
            last_name_index  = clean_index('last_name_column_index')

            if not last_name_index:
                return self._manage_empty()

            return MultiColumnsParticipantsExtractor(
                first_name_index, last_name_index, create_if_unfound,
            )
        elif mode == MODE_SPLITTEDCOLUMN:
            index = clean_index('pattern_column_index')

            if not index:  # TODO test
                return self._manage_empty()

            pattern_func = _PATTERNS.get(value['pattern_id'])
            if not pattern_func:
                raise ValidationError('Invalid pattern')

            return SplitColumnParticipantsExtractor(
                index, value['separator'], pattern_func, create_if_unfound,
            )
        else:
            raise ValidationError('Invalid mode')


# Subjects ---------------------------------------------------------------------

class SubjectsExtractor(RelatedExtractor):
    def __init__(self, column_index, separator, create_if_unfound=False):
        super().__init__(create_if_unfound)
        self._column_index = column_index - 1
        self._separator = separator
        self._models = [
            *RelationType.objects
                         .get(pk=constants.REL_SUB_ACTIVITY_SUBJECT)
                         .subject_models,
        ]

    def extract_value(self, line, user):
        extracted = []
        err_msg   = []

        for search in line[self._column_index].split(self._separator):
            search = search.strip()

            if not search:
                continue

            # TODO: it seems this code does not work ; but it would be cool to make less queries...
            #     EntityCredentials.filter(
            #         user,
            #         CremeEntity.objects.filter(header_filter_search_field__icontains=search),
            #     )

            has_perm = user.has_perm_to_link
            unlinkable_found = False

            for model in self._models:
                # TODO: filter with link credentials too
                #       (because here we limit _before_ filtering not linkable...)
                instances = EntityCredentials.filter(
                    user,
                    model.objects.filter(header_filter_search_field__icontains=search),
                )[:MAX_RELATIONSHIPS + 1]
                linkable_extracted = [e for e in instances if has_perm(e)]

                if linkable_extracted:
                    length = len(linkable_extracted)

                    if length > MAX_RELATIONSHIPS:
                        err_msg.append(
                            _(
                                'Too many «{models}» were found for the search «{search}»'
                            ).format(
                                models=model._meta.verbose_name_plural,
                                search=search,
                            )
                        )
                    else:
                        if length > 1:
                            err_msg.append(
                                _(
                                    'Several «{models}» were found for the search «{search}»'
                                ).format(
                                    models=model._meta.verbose_name_plural,
                                    search=search,
                                )
                            )

                        extracted.extend(linkable_extracted)

                    break

                if instances:
                    unlinkable_found = True
            else:
                if self._create:
                    extracted.append(Organisation.objects.create(user=user, name=search))
                elif unlinkable_found:
                    err_msg.append(
                        _('No linkable entity found for the search «{}»').format(search)
                    )
                else:
                    err_msg.append(_('The subject «{}» cannot be found').format(search))

        return extracted, err_msg


class SubjectsExtractorWidget(BaseExtractorWidget):
    template_name = 'activities/forms/widgets/mass-import/subjects-extractor.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.propose_creation = False

    def get_context(self, name, value, attrs):
        value = value or {}
        context = super().get_context(name=name, value=value, attrs=attrs)

        widget_cxt = context['widget']

        # TODO: factorise with ExtractorWidget
        final_attrs = widget_cxt['attrs']
        required = final_attrs.pop('required', False)

        # Column <select> ------
        try:
            selected_col = int(value.get('selected_column', -1))
        except TypeError:
            selected_col = 0

        widget_cxt['column_select'] = self.column_select.get_context(
            name=f'{name}_colselect',
            value=selected_col,
            attrs={
                'id': '{}_colselect'.format(final_attrs['id']),
                'class': 'csv_col_select',
                'required': required,
            },
        )['widget']

        # Other sub-widgets
        widget_cxt['propose_creation'] = self.propose_creation
        widget_cxt['create']    = value.get('create', False)
        widget_cxt['separator'] = value.get('separator', '/')

        return context

    def value_from_datadict(self, data, files, name):
        get = data.get

        return {
            'selected_column': as_int(get(f'{name}_colselect')),
            'create':          get(f'{name}_create', False),
            'separator':       get(f'{name}_separator', '/'),
        }


class SubjectsExtractorField(Field):
    def __init__(self, *, choices, **kwargs):
        super().__init__(widget=SubjectsExtractorWidget, **kwargs)
        self._user = None
        self._can_create = False
        self._allowed_indexes = {c[0] for c in choices}
        self.widget.choices = choices

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self.widget.propose_creation = self._can_create = user.has_perm_to_create(Organisation)

    # TODO: factorise (in ExtractorField) (need _allowed_indexes)
    def _clean_index(self, value, key):
        try:
            index = int(value[key])
        except TypeError as e:
            raise ValidationError(f'Invalid value for index "{key}"') from e

        if index not in self._allowed_indexes:
            raise ValidationError('Invalid index')

        return index

    def clean(self, value):
        index = self._clean_index(value, 'selected_column')

        if not index:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return RelatedExtractor()  # Empty extractor

        return SubjectsExtractor(
            index, value['separator'], value['create'] and self._can_create,
        )


# Main -------------------------------------------------------------------------
def get_massimport_form_builder(header_dict, choices):
    class ActivityMassImportForm(ImportForm4CremeEntity):
        type_selector = ActivitySubTypeField(
            label=_('Type'), limit_choices_to=~Q(type__uuid=constants.UUID_TYPE_UNAVAILABILITY),
        )

        my_participation = act_fields.UserParticipationField(
            label=_('Do I participate in this activity?'), empty_label=None,
        )
        participating_users = act_fields.ParticipatingUsersField(
            label=_('Other participating users'),
            required=False,
        )
        participants = ParticipantsExtractorField(
            choices=choices, label=_('Participants'), required=False,
        )

        subjects = SubjectsExtractorField(
            choices=choices, label=_('Subjects (organisations only)'), required=False,
        )

        class Meta:
            exclude = ('type', 'sub_type', 'busy')

        blocks = ImportForm4CremeEntity.blocks.new({
            'id': 'participants',
            'label': _('Participants & subjects'),
            'fields': [
                'my_participation', 'participating_users', 'participants', 'subjects',
            ],
        })

        user_participants: set[Contact]
        calendars: list[Calendar]

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            user = self.user
            if user.linked_contact:
                self.fields['my_participation'].initial = (
                    True,
                    Calendar.objects.get_default_calendar(user).id,
                )

            self.user_participants = set()
            self.calendars = []

        def clean_my_participation(self):
            my_participation = self.cleaned_data['my_participation']

            if my_participation.is_set:
                self.user_participants.add(self.user.linked_contact)
                self.calendars.append(my_participation.data)

            return my_participation

        def clean_participating_users(self):
            participants_data = self.cleaned_data['participating_users']
            self.user_participants.update(participants_data['contacts'])
            self.calendars.extend(participants_data['calendars'])

            return participants_data

        def _pre_instance_save(self, instance, line):
            sub_type = self.cleaned_data['type_selector']
            instance.type, instance.sub_type = sub_type.type, sub_type

            instance.floating_type = instance.FloatingType.NARROW
            start = instance.start
            end = instance.end

            if start:
                null_time = time(0)

                if start.time() == null_time and (not end or end.time() == null_time):
                    instance.end = make_aware(datetime.combine(start, time(hour=23, minute=59)))
                    instance.floating_type = instance.FloatingType.FLOATING_TIME
                elif not end:
                    instance.end = start + instance.type.as_timedelta()
                elif start > instance.end:
                    instance.end = start + instance.type.as_timedelta()
                    self.append_error(_('End time is before start time'))
            else:
                instance.floating_type = instance.FloatingType.FLOATING

        def _post_instance_creation(self, instance, line, updated):
            super()._post_instance_creation(instance, line, updated)

            cdata = self.cleaned_data
            owner = instance.user
            participant_ids = set()

            if updated:
                # TODO: improve get_participant_relations() (not retrieve real entities)
                participant_ids.update(
                    Relation.objects.filter(
                        type=constants.REL_SUB_PART_2_ACTIVITY,
                        object_entity=instance.id,
                    ).values_list('subject_entity', flat=True)
                )

            def add_participant(participating_contact):
                if participating_contact.id not in participant_ids:
                    Relation.objects.safe_create(
                        subject_entity=participating_contact,
                        type_id=constants.REL_SUB_PART_2_ACTIVITY,
                        object_entity=instance, user=owner,
                    )
                    participant_ids.add(participating_contact.id)

            # We could create a cache in self (or even put a cache-per-request
            # in Calendar.get_user_default_calendar() but the import can take a
            # long time, & the default Calendar could change
            #  => TODO: use a time based cache ?
            default_calendars_cache = {}

            def add_to_default_calendar(participating_user):
                calendar = default_calendars_cache.get(participating_user.id)

                if calendar is None:
                    default_calendars_cache[participating_user.id] = calendar = \
                        Calendar.objects.get_default_calendar(participating_user)

                instance.calendars.add(calendar)

            for participant in self.user_participants:
                add_participant(participant)

            for calendars_chunk in iter_as_chunk(self.calendars, 256):
                # TODO: add to default_calendars_cache?
                instance.calendars.add(*calendars_chunk)

            dyn_participants, err_messages = cdata['participants'].extract_value(line, self.user)

            for err_msg in err_messages:
                self.append_error(err_msg)

            for participant in dyn_participants:
                add_participant(participant)

                part_user = participant.is_user
                if part_user is not None:
                    add_to_default_calendar(part_user)

            # Subjects ----
            subjects, err_messages = cdata['subjects'].extract_value(line, self.user)

            for err_msg in err_messages:
                self.append_error(err_msg)

            Relation.objects.safe_multi_save(
                Relation(
                    subject_entity=subject,
                    type_id=constants.REL_SUB_ACTIVITY_SUBJECT,
                    object_entity=instance,
                    user=owner,
                ) for subject in subjects
            )

    return ActivityMassImportForm
