# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from collections import defaultdict
from copy import deepcopy
from functools import partial
from json import loads as json_load
from typing import Optional, Type

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.validators import validate_email
from django.db.models.query import Q, QuerySet
from django.forms import ValidationError, fields
from django.forms import models as mforms
from django.forms import widgets
from django.urls import reverse
# from django.utils.encoding import smart_text
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ..auth.entity_credentials import EntityCredentials
from ..core import validators
from ..gui import quick_forms
from ..models import CremeEntity, EntityFilter, RelationType
from ..utils import find_first
from ..utils.collections import OrderedSet
from ..utils.content_type import ctype_choices, entity_ctypes
from ..utils.date_period import date_period_registry
from ..utils.date_range import date_range_registry
from ..utils.serializers import json_encode
from ..utils.unicode_collation import collator
from . import validators as f_validators
from . import widgets as core_widgets

__all__ = (
    'CremeUserChoiceField',
    'GenericEntityField', 'MultiGenericEntityField',
    'RelationEntityField', 'MultiRelationEntityField',
    'CreatorEntityField', 'MultiCreatorEntityField',
    'FilteredEntityTypeField',
    'OptionalField', 'OptionalChoiceField', 'OptionalModelChoiceField',
    'ListEditionField',
    # 'AjaxChoiceField', 'AjaxMultipleChoiceField',
    'AjaxModelChoiceField',
    'DatePeriodField', 'DateRangeField', 'ColorField', 'DurationField',
    'ChoiceOrCharField',
    'CTypeChoiceField', 'EntityCTypeChoiceField',
    'MultiCTypeChoiceField', 'MultiEntityCTypeChoiceField',
    'EnhancedMultipleChoiceField', 'EnhancedModelMultipleChoiceField',
    'ReadonlyMessageField',
)


# TODO: factorise with UserEnumerator ?
class CremeUserChoiceIterator(mforms.ModelChoiceIterator):
    """"Groups the teams & the inactive users in specific groups."""
    def __iter__(self):
        regular_choices = []
        if self.field.empty_label is not None:
            regular_choices.append(('', self.field.empty_label))

        sort_key = collator.sort_key

        def user_key(c):
            return sort_key(c[1])

        queryset = self.queryset
        choice = self.choice
        regular_choices.extend(
            choice(u) for u in queryset if u.is_active and not u.is_team
        )
        regular_choices.sort(key=user_key)

        yield '', regular_choices
        del regular_choices

        team_choices = [choice(u) for u in queryset if u.is_team]
        if team_choices:
            yield _('Teams'), team_choices
        del team_choices

        inactive_choices = [choice(u) for u in queryset if not u.is_active]
        if inactive_choices:
            inactive_choices.sort(key=user_key)
            yield _('Inactive users'), inactive_choices


class CremeUserChoiceField(mforms.ModelChoiceField):
    """Specialization of ModelChoiceField the User model.
    The user set by the form (see CremeForm/CremeModelForm) is used as initial
    choice by default.
    """
    iterator = CremeUserChoiceIterator

    def __init__(self, queryset=None, *, user=None, empty_label=None, **kwargs):
        super().__init__(
            queryset=get_user_model().objects.all() if queryset is None else queryset,
            empty_label=empty_label,  # NB: generally we avoid empty QuerySets.
            **kwargs
        )
        self.user = user

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        if self.initial is None:
            self.initial = None if user is None else user.id

    def label_from_instance(self, obj):
        # NB: we avoid the " (team)" suffix, because CremeUserChoiceIterator
        #     already creates an <optgroup> for teams.
        return str(obj) if not obj.is_team else obj.username


class JSONField(fields.CharField):
    default_error_messages = {
        'invalidformat':    _('Invalid format'),
        'invalidtype':      _('Invalid type'),
        'doesnotexist':     _('This entity does not exist.'),  # TODO: 'An entity ...' ?
        'isdeleted':        _('«%(entity)s» is in the trash.'),
        'isexcluded':       _('«%(entity)s» violates the constraints.'),

        # Used by child classes
        'entityrequired':   _('The entity is required.'),
        'ctyperequired':    _('The content type is required.'),
        'ctypenotallowed':  _('This content type is not allowed.'),
    }
    value_type: Optional[Type] = None  # Overload this: type of the value returned by the field.

    def __init__(self, *, user=None, **kwargs):
        super().__init__(**kwargs)
        self._user = user
        self.widget.from_python = self.from_python

    def __deepcopy__(self, memo):
        obj = super().__deepcopy__(memo)
        obj.widget.from_python = obj.from_python
        return obj

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user

    def _build_empty_value(self):
        "Value returned by not-required fields, when value is empty."
        if self.value_type is list:
            return []

        return None

    def _return_none_or_raise(self, required, error_key='required'):
        if required:
            raise ValidationError(self.error_messages[error_key])

        return None

    def _return_list_or_raise(self, required, error_key='required') -> list:
        if required:
            raise ValidationError(self.error_messages[error_key])

        return []

    def clean_value(self, data, name, type, required=True, required_error_key='required'):
        if not data:
            raise ValidationError(
                self.error_messages['invalidformat'],
                code='invalidformat',
            )

        if not isinstance(data, dict):
            raise ValidationError(
                self.error_messages['invalidformat'],
                code='invalidformat',
            )

        value = data.get(name)

        # 'value' can be "False" if a boolean value is expected.
        if value is None:
            return self._return_none_or_raise(required, required_error_key)

        if isinstance(value, type):
            return value

        if value == '' and not required:
            return None

        try:
            return type(value)
        except Exception as e:
            raise ValidationError(
                self.error_messages['invalidformat'],
                code='invalidformat',
            ) from e

    def clean_json(self, value, expected_type=None):
        if not value:
            return self._return_none_or_raise(self.required)

        try:
            data = json_load(value)
        except Exception as e:
            raise ValidationError(
                self.error_messages['invalidformat'],
                code='invalidformat',
            ) from e

        if expected_type is not None and data is not None and not isinstance(data, expected_type):
            raise ValidationError(
                self.error_messages['invalidtype'],
                code='invalidtype',
            )

        return data

    def format_json(self, value):
        return json_encode(value)

    # TODO: can we remove this hack with the new widget api (since django 1.2) ??
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, str):
            return value

        return self.format_json(self._value_to_jsonifiable(value))

    def clean(self, value):
        data = self.clean_json(value, expected_type=self.value_type)

        if not data:
            if self.required:
                raise ValidationError(
                    self.error_messages['required'],
                    code='required',
                )

            return self._build_empty_value()

        return self._value_from_unjsonfied(data)

    def _clean_entity(self, ctype, entity_pk):
        "@param ctype: ContentType instance or PK."
        if not isinstance(ctype, ContentType):
            try:
                ctype = ContentType.objects.get_for_id(ctype)
            except ContentType.DoesNotExist as e:
                raise ValidationError(
                    self.error_messages['doesnotexist'],
                    params={'ctype': ctype},
                    code='doesnotexist',
                ) from e

        entity = None

        if not entity_pk:
            if self.required:
                raise ValidationError(
                    self.error_messages['required'],
                    code='required',
                )
        else:
            model = ctype.model_class()
            assert issubclass(model, CremeEntity)

            try:
                # TODO: use filter(..).first() if we allow extra Q filter
                # entity = model.objects.get(is_deleted=False, pk=entity_pk)
                entity = model.objects.get(pk=entity_pk)
            except model.DoesNotExist as e:
                raise ValidationError(
                    self.error_messages['doesnotexist'],
                    params={
                        'ctype': ctype.pk,
                        'entity': entity_pk,
                    },
                    code='doesnotexist',
                ) from e
            else:
                if entity.is_deleted:
                    raise ValidationError(
                        self.error_messages['isdeleted'],
                        code='isdeleted',
                        params={'entity': entity.allowed_str(self._user)},
                    )

        return entity

    def _entity_queryset(self, model, qfilter=None):
        # query = model.objects.filter(is_deleted=False)
        query = model.objects.all()

        if qfilter is not None:
            query = query.filter(qfilter)

        return query

    def _clean_entity_from_model(self, model, entity_pk, qfilter=None):
        # try:
        #     return self._entity_queryset(model, qfilter).get(pk=entity_pk)
        # except model.DoesNotExist as e:
        #     if self.required:
        #         raise ValidationError(
        #             self.error_messages['doesnotexist'],
        #             code='doesnotexist',
        #         ) from e
        entity = self._entity_queryset(model, qfilter).filter(pk=entity_pk).first()
        if entity is None:
            if qfilter:
                entity = self._entity_queryset(model).filter(pk=entity_pk).first()
                if entity is not None:
                    raise ValidationError(
                        self.error_messages['isexcluded'],
                        code='isexcluded',
                        params={'entity': entity.allowed_str(self._user)},
                    )

            raise ValidationError(self.error_messages['doesnotexist'], code='doesnotexist')
        else:
            if entity.is_deleted:
                raise ValidationError(
                    self.error_messages['isdeleted'],
                    code='isdeleted',
                    params={'entity': entity.allowed_str(self._user)},
                )

            return entity

    def _value_from_unjsonfied(self, data):
        "Build the field value from deserialized data."
        return data

    def _value_to_jsonifiable(self, value):
        "Convert the python value to jsonifiable object."
        return value


class EntityCredsJSONField(JSONField):
    "Base field which checks the permission for the retrieved entities"
    CREDS_VALIDATORS = [
        (
            EntityCredentials.VIEW,
            f_validators.validate_viewable_entity,
            f_validators.validate_viewable_entities,
        ), (
            EntityCredentials.CHANGE,
            f_validators.validate_editable_entity,
            f_validators.validate_editable_entities,
        ), (
            EntityCredentials.LINK,
            f_validators.validate_linkable_entity,
            f_validators.validate_linkable_entities,
        ),
    ]

    def __init__(self, *,
                 credentials=EntityCredentials.LINK,
                 quickforms_registry=None,
                 **kwargs):
        """Constructor.
        @param credentials: Binary combination of EntityCredentials.{VIEW, CHANGE, LINK}.
                            Default value is EntityCredentials.LINK.
        """
        super().__init__(**kwargs)
        self._credentials = credentials
        self.quickforms_registry = quickforms_registry or quick_forms.quickforms_registry

    def _check_entity_perms(self, entity, *args):
        user = self._user
        credentials = args[0] if args else self._credentials

        # We do not check permission if the initial related entity has not changed
        # (in order to allow the edition of an instance even if we do not have
        # the permissions for the already set related entity).
        initial = self.initial

        def get_initial_id():
            return initial.id if isinstance(initial, CremeEntity) else initial

        # NB: we compare ID to avoid problem with real/not real entities.
        if entity is not None and (not initial or (get_initial_id() != entity.id)):
            for cred, validator, _validator_multi in self.CREDS_VALIDATORS:
                if credentials & cred:
                    validator(entity, user)

        return entity

    def _check_entities_perms(self, entities, *args):
        user = self._user

        credentials = args[0] if args else self._credentials

        for cred, validator, validator_multi in self.CREDS_VALIDATORS:
            if credentials & cred:
                validator_multi(entities, user)

        return entities

    def _has_quickform(self, model):
        return self.quickforms_registry.get_form_class(model) is not None


class GenericEntityField(EntityCredsJSONField):
    widget: Type[widgets.TextInput] = core_widgets.CTEntitySelector
    value_type: Type = dict

    def __init__(self, *, models=(), autocomplete=False, creator=True, user=None, **kwargs):
        super().__init__(**kwargs)
        self.creator = creator
        self.autocomplete = autocomplete
        self._user = user
        self.allowed_models = models

    @property
    def allowed_models(self):
        return self._allowed_models

    @allowed_models.setter
    def allowed_models(self, allowed):
        """@param allowed: An iterable of models (ie: classes inheriting django.db.Model)."""
        self._allowed_models = [*allowed]
        self._update_widget_choices()

    @EntityCredsJSONField.user.setter
    def user(self, user):
        self._user = user
        self._update_widget_choices()

    @property
    def autocomplete(self):
        return self._autocomplete

    @autocomplete.setter
    def autocomplete(self, autocomplete):
        self._autocomplete = autocomplete
        self.widget.autocomplete = autocomplete

    @property
    def creator(self):
        return self._creator

    @creator.setter
    def creator(self, creator):
        self._creator = creator
        self.widget.creator = creator

    def widget_attrs(self, widget):
        return {'reset': False}

    def _update_widget_choices(self):
        self.widget.content_types = fields.CallableChoiceIterator(self._get_ctypes_options)

    def _create_url(self, user, ctype):
        model = ctype.model_class()

        if self._has_quickform(model) and user is not None and user.has_perm_to_create(model):
            return reverse('creme_core__quick_form', args=(ctype.pk,))

        return ''

    def _value_to_jsonifiable(self, value):
        if isinstance(value, CremeEntity):
            ctype = value.entity_type
            pk = value.id
        elif isinstance(value, int):
            ctype_id = CremeEntity.objects.values_list(
                'entity_type_id', flat=True,
            ).filter(id=value).first()
            if ctype_id is None:
                raise ValueError(f'No such entity with id={value}.')

            ctype = ContentType.objects.get_for_id(ctype_id)
            pk = value
        else:
            return value

        ctype_create_url = self._create_url(self.user, ctype)

        return {
            'ctype': {
                'id': ctype.id,
                'create': ctype_create_url,
                'create_label': str(ctype.model_class().creation_label),
            },
            'entity': pk
        }

    def _value_from_unjsonfied(self, data):
        clean_value = self.clean_value
        required = self.required

        # Compatibility with older format.
        if data and isinstance(data.get('ctype'), dict):
            ctype_choice = clean_value(data, 'ctype', dict, required, 'ctyperequired')
            ctype_pk = clean_value(ctype_choice, 'id', int, required, 'ctyperequired')
        else:
            warnings.warn(
                'GenericEntityField: old format "ctype": id entry is deprecated.',
                DeprecationWarning
            )
            ctype_pk = clean_value(data, 'ctype', int, required, 'ctyperequired')

        entity_pk = clean_value(data, 'entity', int, required, 'entityrequired')
        entity = self._clean_entity(self._clean_ctype(ctype_pk), entity_pk)

        return self._check_entity_perms(entity)

    def _clean_ctype(self, ctype_pk):
        # Check ctype in allowed ones
        for ct in self.get_ctypes():
            if ct.pk == ctype_pk:
                return ct

        raise ValidationError(self.error_messages['ctypenotallowed'], code='ctypenotallowed')

    def _get_ctypes_options(self):
        create_url = partial(self._create_url, self._user)
        choices = [
            (
                json_encode({
                    'id': ctype.pk,
                    'create': create_url(ctype),
                    'create_label': str(ctype.model_class().creation_label),
                }),
                str(ctype)
            ) for ctype in self.get_ctypes()
        ]

        sort_key = collator.sort_key
        choices.sort(key=lambda k: sort_key(k[1]))

        return choices

    def get_ctypes(self):
        models = self._allowed_models

        if models:
            get_ct = ContentType.objects.get_for_model

            return [get_ct(model) for model in models]

        return [*entity_ctypes()]


# TODO: Add a q_filter, see utilization in EntityEmailForm
# TODO: propose to allow duplicates ???
class MultiGenericEntityField(GenericEntityField):
    widget = core_widgets.MultiCTEntitySelector
    value_type: Type = list

    def __init__(self, *, models=(), autocomplete=False, unique=True,
                 creator=True, user=None, **kwargs):
        super().__init__(
            models=models, autocomplete=autocomplete, creator=creator, user=user,
            **kwargs
        )
        self.unique = unique

    def widget_attrs(self, widget):
        return {}

    def _value_to_jsonifiable(self, value):
        return [*map(super()._value_to_jsonifiable, value)]

    def _value_from_unjsonfied(self, data):
        # We want to to keep the global order (left by defaultdict)
        if self.unique:
            entities_pks = OrderedSet()
            entities_pks_append = entities_pks.add
        else:
            entities_pks = []
            entities_pks_append = entities_pks.append

        entities_by_ctype = defaultdict(list)
        clean_value = self.clean_value

        # Group entity PKs by ctype, in order to make efficient queries
        for entry in data:
            # Compatibility with older format.
            if data and isinstance(entry.get('ctype'), dict):
                ctype_choice = clean_value(entry, 'ctype', dict, required=False)
                ctype_pk = clean_value(ctype_choice, 'id', int, required=False)
            else:
                warnings.warn(
                    'MultiGenericEntityField: old format "ctype": id entry is deprecated.',
                    DeprecationWarning
                )
                ctype_pk = clean_value(entry, 'ctype', int, required=False)

            if not ctype_pk:
                continue

            entity_pk = clean_value(entry, 'entity', int, required=False)
            if not entity_pk:
                continue

            entities_pks_append(entity_pk)
            entities_by_ctype[ctype_pk].append(entity_pk)

        entities_map = {}

        # Build the list of entities (ignore invalid entries)
        for ct_id, ctype_entity_pks in entities_by_ctype.items():
            # ctype_entities = self._clean_ctype(ct_id).model_class() \
            #                                          .objects \
            #                                          .filter(is_deleted=False) \
            #                                          .in_bulk(ctype_entity_pks)
            ctype_entities = self._clean_ctype(ct_id) \
                                 .get_all_objects_for_this_type() \
                                 .in_bulk(ctype_entity_pks)

            if not all(pk in ctype_entities for pk in ctype_entity_pks):
                raise ValidationError(
                    self.error_messages['doesnotexist'],
                    code='doesnotexist',
                )

            # TODO: factorise
            for entity in ctype_entities.values():
                if entity.is_deleted:
                    raise ValidationError(
                        self.error_messages['isdeleted'],
                        code='isdeleted',
                        params={'entity': entity.allowed_str(self._user)},
                    )

            entities_map.update(ctype_entities)

        if not entities_map:
            return self._return_list_or_raise(self.required)

        return self._check_entities_perms([entities_map[pk] for pk in entities_pks])


class ChoiceModelIterator:
    def __init__(self, queryset, render_value=None, render_label=None):
        self.queryset = queryset.all()
        self.render_value = render_value or (lambda v: v.pk)
        self.render_label = render_label or (lambda v: str(v))

    def __iter__(self):
        for model in self.queryset:
            yield self.render_value(model), self.render_label(model)

    def __len__(self):
        return len(self.queryset)


class RelationEntityField(EntityCredsJSONField):
    widget = core_widgets.RelationSelector
    default_error_messages = {
        'rtypedoesnotexist': _(
            'This type of relationship does not exist (id=%(rtype_id)s).'
        ),
        'rtypenotallowed': _(
            'This type of relationship causes a constraint error '
            '(id="%(rtype_id)s").'
        ),
        'ctypenotallowed': _(
            'This content type cause constraint error with the type of relationship '
            '(id="%(ctype_id)s").'
        ),
        'nopropertymatch': _(
            'This entity has no property that matches the constraints of the type of relationship.'
        ),
    }
    value_type: Type = dict

    def __init__(
            self, *,
            allowed_rtypes=RelationType.objects.none(),
            autocomplete=False,
            **kwargs):
        super().__init__(**kwargs)
        self.autocomplete = autocomplete
        self.allowed_rtypes = allowed_rtypes

    @property
    def allowed_rtypes(self):
        return self._allowed_rtypes

    @allowed_rtypes.setter
    def allowed_rtypes(self, allowed):
        rtypes = (
            allowed if isinstance(allowed, QuerySet) else
            RelationType.objects.filter(id__in=allowed)
        )
        rtypes = rtypes.order_by('predicate')  # TODO: in RelationType._meta.ordering ??

        self._allowed_rtypes = rtypes
        self.widget.relation_types = self._get_options()

    @property
    def autocomplete(self):
        return self._autocomplete

    @autocomplete.setter
    def autocomplete(self, autocomplete):
        self._autocomplete = autocomplete
        self.widget.autocomplete = autocomplete

    def _value_to_jsonifiable(self, value):
        rtype, entity = value

        return {
            'rtype': rtype.pk, 'ctype': entity.entity_type_id, 'entity': entity.pk,
        } if entity else {
            'rtype': rtype.pk, 'ctype': None,                  'entity': None,
        }

    def _value_from_unjsonfied(self, data):
        clean_value = self.clean_value
        rtype_pk = clean_value(data, 'rtype',  str)

        ctype_pk = clean_value(data, 'ctype',  int, required=False)
        if not ctype_pk:
            return self._return_none_or_raise(self.required, 'ctyperequired')

        entity_pk = clean_value(data, 'entity', int, required=False)
        if not entity_pk:
            return self._return_none_or_raise(self.required, 'entityrequired')

        rtype = self._clean_rtype(rtype_pk)
        self._validate_ctype_constraints(rtype, ctype_pk)

        entity = self._clean_entity(ctype_pk, entity_pk)
        self._check_entity_perms(entity)
        self._validate_properties_constraints(rtype, entity)

        return rtype, entity

    def _validate_ctype_constraints(self, rtype, ctype_pk):
        ctype_ids = rtype.object_ctypes.values_list('pk', flat=True)

        # Is relation type accepts content type
        if ctype_ids and ctype_pk not in ctype_ids:
            raise ValidationError(
                self.error_messages['ctypenotallowed'],
                params={'ctype_id': ctype_pk},
                code='ctypenotallowed',
            )

    def _validate_properties_constraints(self, rtype, entity):
        needed_ptype_ids = [*rtype.object_properties.values_list('id', flat=True)]

        if needed_ptype_ids:
            ptype_ids = {p.type_id for p in entity.get_properties()}

            if any(
                needed_ptype_id not in ptype_ids
                for needed_ptype_id in needed_ptype_ids
            ):
                raise ValidationError(
                    self.error_messages['nopropertymatch'],
                    code='nopropertymatch',
                )

    def _clean_rtype(self, rtype_pk):
        # Is relation type allowed
        if rtype_pk not in self._get_allowed_rtypes_ids():
            raise ValidationError(
                self.error_messages['rtypenotallowed'],
                params={'rtype_id': rtype_pk}, code='rtypenotallowed',
            )

        # NB: we are sure the RelationType exists here
        return RelationType.objects.get(pk=rtype_pk)

    def _get_options(self):  # TODO: inline
        return ChoiceModelIterator(self._allowed_rtypes)

    def _get_allowed_rtypes_objects(self):
        return self._allowed_rtypes.all()

    def _get_allowed_rtypes_ids(self):
        return self._allowed_rtypes.values_list('id', flat=True)


class MultiRelationEntityField(RelationEntityField):
    widget: Type[widgets.TextInput] = core_widgets.MultiRelationSelector
    value_type: Type = list

    def _value_to_jsonifiable(self, value):
        return [*map(super()._value_to_jsonifiable, value)]

    def _build_rtype_cache(self, rtype_pk):
        try:
            rtype = RelationType.objects.get(pk=rtype_pk)
        except RelationType.DoesNotExist as e:
            raise ValidationError(
                self.error_messages['rtypedoesnotexist'],
                params={'rtype_id': rtype_pk},
                code='rtypedoesnotexist',
            ) from e

        allowed_ctype_ids = frozenset(ct.pk for ct in rtype.object_ctypes.all())
        needed_ptype_ids = [*rtype.object_properties.values_list('id', flat=True)]

        return rtype, allowed_ctype_ids, needed_ptype_ids

    def _build_ctype_cache(self, ctype_pk):
        try:
            ctype = ContentType.objects.get_for_id(ctype_pk)
        except ContentType.DoesNotExist as e:
            raise ValidationError(
                # self.error_messages['ctypedoesnotexist'],
                # code='ctypedoesnotexist',
                str(e)
            ) from e

        return ctype, []

    def _get_cache(self, entries, key, build_func):
        cache = entries.get(key)

        if not cache:
            cache = build_func(key)
            entries[key] = cache

        return cache

    def _value_from_unjsonfied(self, data):
        clean_value = self.clean_value
        cleaned_entries = []

        for entry in data:
            rtype_pk = clean_value(entry, 'rtype', str)

            ctype_pk = clean_value(entry, 'ctype', int, required=False)
            if not ctype_pk:
                continue

            entity_pk = clean_value(entry, 'entity', int, required=False)
            if not entity_pk:
                continue

            cleaned_entries.append((rtype_pk, ctype_pk, entity_pk))

        rtypes_cache = {}
        ctypes_cache = {}
        allowed_rtypes_ids = frozenset(self._get_allowed_rtypes_ids())

        need_property_validation = False

        for rtype_pk, ctype_pk, entity_pk in cleaned_entries:
            # Check if relation type is allowed
            if rtype_pk not in allowed_rtypes_ids:
                raise ValidationError(
                    self.error_messages['rtypenotallowed'],
                    params={'rtype_id': rtype_pk},
                    code='rtypenotallowed',
                )

            rtype, allowed_ctype_ids, needed_ptype_ids = self._get_cache(
                rtypes_cache, rtype_pk, self._build_rtype_cache,
            )

            if needed_ptype_ids:
                need_property_validation = True

            # Check if content type is allowed by relation type
            if allowed_ctype_ids and ctype_pk not in allowed_ctype_ids:
                raise ValidationError(
                    self.error_messages['ctypenotallowed'],
                    # params={'ctype': ctype_pk},
                    params={'ctype_id': ctype_pk},
                    code='ctypenotallowed',
                )

            ctype, ctype_entity_pks = self._get_cache(
                ctypes_cache, ctype_pk,
                self._build_ctype_cache,
            )
            ctype_entity_pks.append(entity_pk)

        entities_cache = {}

        # Build real entity cache and check both entity id exists and in correct content type
        for ctype, entity_pks in ctypes_cache.values():
            ctype_entities = {
                entity.pk: entity
                # for entity in ctype.model_class()
                #                    .objects
                #                    .filter(is_deleted=False, pk__in=entity_pks)
                for entity in ctype.get_all_objects_for_this_type(pk__in=entity_pks)
            }

            if not all(entity_pk in ctype_entities for entity_pk in entity_pks):
                raise ValidationError(
                    self.error_messages['doesnotexist'],
                    code='doesnotexist',
                    # TODO: params={'entity_id': ...} ?
                )

            for entity in ctype_entities.values():
                if entity.is_deleted:
                    raise ValidationError(
                        self.error_messages['isdeleted'],
                        code='isdeleted',
                        params={'entity': entity.allowed_str(self._user)},
                    )

            entities_cache.update(ctype_entities)

        self._check_entities_perms(entities_cache.values())

        relations = []

        # Build cache for validation of properties constraint between relationtypes and entities
        if need_property_validation:
            CremeEntity.populate_properties(entities_cache.values())

        for rtype_pk, ctype_pk, entity_pk in cleaned_entries:
            rtype, allowed_ctype_ids, needed_ptype_ids = rtypes_cache.get(rtype_pk)
            entity = entities_cache.get(entity_pk)

            if needed_ptype_ids:
                ptype_ids = {p.type_id for p in entity.get_properties()}

                if any(needed_ptype_id not in ptype_ids for needed_ptype_id in needed_ptype_ids):
                    raise ValidationError(
                        self.error_messages['nopropertymatch'],
                        code='nopropertymatch',
                    )

            relations.append((rtype, entity))

        if not relations:
            return self._return_list_or_raise(self.required)

        return relations


class CreatorEntityField(EntityCredsJSONField):
    # The following attributes are set: model, q_filter, creation_url, creation_allowed
    widget = core_widgets.EntityCreatorWidget

    value_type: Type = int

    def __init__(self, *,
                 model=None,
                 q_filter=None,
                 create_action_url='',
                 create_action_label=None,
                 user=None,
                 force_creation=False,
                 **kwargs):
        super().__init__(**kwargs)
        widget = self.widget
        self._model = widget.model = model
        self._q_filter = widget.q_filter = q_filter
        self._create_action_url = widget.creation_url = create_action_url
        self.create_action_label = create_action_label
        self._force_creation = force_creation
        self.user = user

    @property
    def force_creation(self):
        return self._force_creation

    @force_creation.setter
    def force_creation(self, force_creation):
        self._force_creation = force_creation
        self._update_creation_info()

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model=None):
        self._model = model
        self.widget.model = model
        self._update_creation_info()

    @property
    def q_filter(self):
        return self._q_filter

    @q_filter.setter
    def q_filter(self, q_filter):
        """
        @param q_filter: Allows to filter the selection. Same meaning than Model.limit_choices_to ;
               so it can be dictionary (eg: {'user__is_staff': False}),
               a <django.db.models.query.Q instance>,
               or a callable which returns dictionary/Q.
               <None> means not filtering.
        """
        self.widget.q_filter = self._q_filter = q_filter
        self._update_creation_info()

    @property
    def q_filter_query(self):
        q_filter = self._q_filter
        q = None

        if q_filter is not None:
            if callable(q_filter):
                q_filter = q_filter()

            if isinstance(q_filter, dict):
                q = Q(**q_filter)
            elif isinstance(q_filter, Q):
                q = q_filter
            else:
                raise ValueError(
                    f'Invalid type for q_filter (needs dict or Q): {q_filter}'
                )

        return q

    @property
    def create_action_label(self):
        return self._create_action_label

    @create_action_label.setter
    def create_action_label(self, label):
        self._create_action_label = self.widget.creation_label = label

    @property
    def create_action_url(self):
        if self._create_action_url:
            return self._create_action_url

        model = self._model

        if model is not None and self._has_quickform(model):
            return reverse(
                'creme_core__quick_form',
                args=(ContentType.objects.get_for_model(model).id,),
            )

        return ''

    @create_action_url.setter
    def create_action_url(self, url):
        self._create_action_url = url

        self._update_creation_info()

    @EntityCredsJSONField.user.setter
    def user(self, user):
        self._user = user
        self._update_creation_info()

    def _update_creation_info(self):
        user = self._user
        model = self._model
        widget = self.widget

        if user and model:
            widget.creation_allowed = user.has_perm_to_create(model)
            widget.creation_url = (
                self.create_action_url
                if not self._q_filter or self._force_creation
                else ''
            )
        else:
            widget.creation_allowed = False
            widget.creation_url = ''

    def _value_to_jsonifiable(self, value):
        if isinstance(value, int):
            if not self._entity_queryset(
                self.model,
                # self.q_filter_query,
            ).filter(pk=value).exists():
                raise ValueError(f'No such entity with id={value}.')

            return value

        assert isinstance(value, CremeEntity)
        return value.id

    def _value_from_unjsonfied(self, data):
        model = self.model

        if model is None:
            if self.required:
                raise ValidationError(self.error_messages['required'], code='required')

            return None

        entity = self._clean_entity_from_model(model, data, self.q_filter_query)

        return self._check_entity_perms(entity)


class MultiCreatorEntityField(CreatorEntityField):
    widget = core_widgets.MultiEntityCreatorWidget  # See CreatorEntityField.widget comment
    value_type: Type = list

    def _value_to_jsonifiable(self, value):
        if not value:
            return []

        if value and isinstance(value[0], int):
            if self._entity_queryset(
                self.model, self.q_filter_query,
            ).filter(pk__in=value).count() < len(value):
                raise ValueError(
                    "The entities with ids [{}] don't exist.".format(
                        ', '.join(str(v) for v in value),
                    )
                )

            return value

        return [*map(super()._value_to_jsonifiable, value)]

    def _value_from_unjsonfied(self, data):
        entities = []
        model = self.model

        if model is not None:
            clean_entity = partial(
                self._clean_entity_from_model,
                model=model, qfilter=self.q_filter_query,
            )

            for entry in data:
                if not isinstance(entry, int):
                    raise ValidationError(
                        self.error_messages['invalidtype'],
                        code='invalidtype',
                    )

                entity = clean_entity(entity_pk=entry)

                if entity is None:
                    raise ValidationError(
                        self.error_messages['doesnotexist'],
                        code='doesnotexist',
                    )

                entities.append(entity)
        elif self.required:
            raise ValidationError(
                self.error_messages['required'],
                code='required',
            )

        return self._check_entities_perms(entities)


class FilteredEntityTypeField(JSONField):
    widget = core_widgets.FilteredEntityTypeWidget
    default_error_messages = {
        'invalidefilter': _('This filter is invalid.'),
    }
    value_type = dict

    def __init__(self, *, ctypes=entity_ctypes, empty_label=None, **kwargs):
        """Constructor.
        @param ctypes: Allowed content types.
               - A callable which returns an iterable of ContentType IDs / instances.
               - Sequence of ContentType IDs / instances.
        """
        super().__init__(**kwargs)
        self._empty_label = empty_label
        self.ctypes = ctypes

    def _build_empty_value(self):
        return None, None

    def _clean_ctype(self, ctype_pk):
        for ct in self.ctypes:
            if ctype_pk == ct.id:
                return ct

    @property
    def ctypes(self):
        get_ct = ContentType.objects.get_for_id
        return [
            ct_or_ctid if isinstance(ct_or_ctid, ContentType) else get_ct(ct_or_ctid)
            for ct_or_ctid in self._ctypes()
        ]

    @ctypes.setter
    def ctypes(self, ctypes):
        "See constructor."
        if not callable(ctypes):
            ctypes_list = [*ctypes]  # We copy the sequence to avoid external modifications

            def ctypes():
                return ctypes_list

        self._ctypes = ctypes
        self.widget.content_types = fields.CallableChoiceIterator(self._get_choices)

    def _get_choices(self):
        choices = []

        if self._empty_label is not None:
            # TODO: improve widget to do not make a request for '0' (same comment in widget)
            choices.append((0, str(self._empty_label)))

        choices.extend(ctype_choices(self.ctypes))

        return choices

    def _value_from_unjsonfied(self, data):
        clean_value = self.clean_value
        ctype_pk = clean_value(data, 'ctype', int, required=False)

        if not ctype_pk:
            if self.required:
                raise ValidationError(
                    self.error_messages['ctyperequired'],
                    code='ctyperequired',
                )

            return self._build_empty_value()

        ct = self._clean_ctype(ctype_pk)
        if ct is None:
            raise ValidationError(
                self.error_messages['ctypenotallowed'],
                code='ctypenotallowed',
            )

        efilter_pk = clean_value(data, 'efilter',  str, required=False)
        if not efilter_pk:  # TODO: self.filter_required ???
            efilter = None
        else:
            try:
                efilter = EntityFilter.objects.filter_by_user(self._user)\
                                              .filter(entity_type=ct)\
                                              .get(pk=efilter_pk)
            except EntityFilter.DoesNotExist:
                raise ValidationError(
                    self.error_messages['invalidefilter'],
                    code='invalidefilter',
                )

        return ct, efilter

    def _value_to_jsonifiable(self, value):
        return {'ctype': value[0], 'efilter': value[1]}


class OptionalField(fields.MultiValueField):
    """Base class for fields combining a BooleanField & another field, the first
    one controlling the inhibition of the second one: when the value of the
    BooleanField is <False>, the value of the second field is ignored.

    Hint: in the child classes, you should probably use a widget inheriting
          'OptionalWidget'.
    """
    sub_field = fields.Field
    widget: Type[core_widgets.OptionalWidget] = core_widgets.OptionalWidget

    default_error_messages = {
        'subfield_required': _('Enter a value if you check the box.'),
    }

    def __init__(
            self,
            *,
            widget=None,
            label=None,
            initial=None,
            help_text='',
            sub_label='',
            disabled=False,
            **kwargs):
        super().__init__(
            fields=(
                fields.BooleanField(required=False),
                self._build_subfield(**kwargs),
            ),
            required=False,
            require_all_fields=False,
            widget=widget, label=label, initial=initial, help_text=help_text,
            disabled=disabled,
        )
        self.widget.sub_label = sub_label

    def _build_subfield(self, *args, **kwargs):
        return self.sub_field(*args, **kwargs)

    def compress(self, data_list):
        return (data_list[0], data_list[1]) if data_list else (False, None)

    def clean(self, value):
        sub_field = self.fields[1]
        sub_required = sub_field.required
        if sub_required:
            sub_field.required = False

        use_value, sub_value = super().clean(value)

        if sub_required:
            sub_field.required = True

            if use_value:
                try:
                    sub_field_value = value[1]
                except IndexError:
                    sub_field_value = None

                if sub_field_value in self.empty_values:
                    raise ValidationError(
                        self.error_messages['subfield_required'],
                        code='subfield_required',
                    )

        if not use_value:
            sub_value = None

        return use_value, sub_value

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, value):
        self._disabled = value

        for field in getattr(self, 'fields', ()):
            field.disabled = value


class OptionalChoiceField(OptionalField):
    sub_field = fields.ChoiceField
    widget = core_widgets.OptionalSelect


class OptionalModelChoiceField(OptionalChoiceField):
    sub_field = mforms.ModelChoiceField


class ListEditionField(fields.Field):
    """A field to allow the user to edit/delete a list of strings.
    It returns a list with the same order:
    * deleted elements are replaced by None.
    * modified elements are replaced by the new value.
    """
    widget = core_widgets.ListEditionWidget

    def __init__(self, *, content=(), only_delete=False, **kwargs):
        """Constructor.
        @param content: Sequence of strings
        @param only_delete: Can only delete elements, not edit them.
        """
        super().__init__(**kwargs)
        self.content = content
        self.only_delete = only_delete

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, content):
        self._content = content
        self.widget.content = content

    @property
    def only_delete(self):
        return self._only_delete

    @only_delete.setter
    def only_delete(self, only_delete):
        self._only_delete = only_delete
        self.widget.only_delete = only_delete


# class AjaxChoiceField(fields.ChoiceField):
#     """
#         Same as ChoiceField but bypass the choices validation due to the ajax filling
#     """
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         warnings.warn('creme_core.forms.fields.AjaxChoiceField is deprecated',
#                       DeprecationWarning
#                      )
#
#     def clean(self, value):
#         if value in self.empty_values:
#             if self.required:
#                 raise ValidationError(self.error_messages['required'], code='required')
#
#             value = ''
#
#         return smart_text(value)


# class AjaxMultipleChoiceField(fields.MultipleChoiceField):
#     """
#         Same as MultipleChoiceField but bypass the choices validation due to the ajax filling
#     """
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         warnings.warn('creme_core.forms.fields.AjaxMultipleChoiceField is deprecated',
#                       DeprecationWarning
#                      )
#
#     def clean(self, value):
#         """
#         Validates that the input is a list or tuple.
#         """
#         not_value = not value
#         if self.required and not_value:
#             raise ValidationError(self.error_messages['required'], code='required')
#         elif not self.required and not_value:
#             return []
#
#         if not isinstance(value, (list, tuple)):
#             raise ValidationError(self.error_messages['invalid_list'],
#                                   code='invalid_list',
#                                  )
#
#         return [smart_text(val) for val in value]


class AjaxModelChoiceField(mforms.ModelChoiceField):
    """
        Same as ModelChoiceField but bypass the choices validation due to the ajax filling
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        warnings.warn(
            'creme_core.forms.fields.AjaxModelChoiceField is deprecated',
            DeprecationWarning,
        )

    def clean(self, value):
        # Field.clean(self, value)

        if value in self.empty_values:
            return None

        try:
            key = self.to_field_name or 'pk'
            value = self.queryset.model._default_manager.get(**{key: value})
        except self.queryset.model.DoesNotExist:
            raise ValidationError(
                self.error_messages['invalid_choice'],
                code='invalid_choice',
            )

        return value


class MultiEmailField(fields.Field):
    # Original code at
    #   http://docs.djangoproject.com/en/1.3/ref/forms/validation/#form-field-default-cleaning
    widget = widgets.Textarea

    def __init__(self, *, sep='\n', **kwargs):
        super().__init__(**kwargs)
        self.sep = sep

    def to_python(self, value):
        "Normalize data to a list of strings."

        # Return an empty list if no input was given.
        if not value:
            return []

        # Remove empty values but the validation is more flexible
        return [v for v in value.split(self.sep) if v]

    def validate(self, value):
        "Check if value consists only of valid emails."
        # Use the parent's handling of required fields, etc.
        super().validate(value)

        for email in value:
            validate_email(email)


class DatePeriodField(fields.MultiValueField):
    widget = core_widgets.DatePeriodWidget

    def __init__(self, *, period_registry=date_period_registry, period_names=None, **kwargs):
        """Constructor.
        @param period_registry: see property 'period_registry'.
        @param period_names: see property 'period_names'.
        """
        super().__init__(
            (fields.ChoiceField(), fields.IntegerField(min_value=1)),
            **kwargs
        )

        self._period_registry = period_registry
        self.period_names = period_names

    def _update_choices(self):
        self.fields[0].choices = self.widget.choices = [
            *self._period_registry.choices(choices=self._period_names)
        ]

    @property
    def choices(self):
        return self.fields[0].choices

    @property
    def period_names(self):
        return self._period_names

    @period_names.setter
    def period_names(self, period_names):
        """Set the periods which are valid (they must be registered in the related registry too).
        @param period_names: Sequence of strings (see DatePeriod.name for valid values),
                             or None (== all available periods in the registry are used.
        """
        self._period_names = period_names
        self._update_choices()

    @property
    def period_registry(self):
        return self._period_registry

    @period_registry.setter
    def period_registry(self, period_registry):
        "@param period_registry: DatePeriodRegistry instance."
        self._period_registry = period_registry
        self._update_choices()

    def compress(self, data_list):
        return (data_list[0], data_list[1]) if data_list else ('', '')

    def clean(self, value):
        period_name, period_value = super().clean(value)

        if not period_value:
            return None

        return date_period_registry.get_period(period_name, period_value)


class DateRangeField(fields.MultiValueField):
    """A field which returns a creme_core.utils.DateRange.
    Commonly used with a DateRangeWidget.
    eg:
        # Use DateRangeWidget with defaults params
        DateRangeField(label=_('Date range'))

        # Render DateRangeWidget as ul/li
        DateRangeField(label=_('Date range'), widget=DateRangeWidget(attrs={'render_as': 'ul'}))

        # Render DateRangeWidget as a table
        DateRangeField(label=_('Date range'), widget=DateRangeWidget(attrs={'render_as': 'table'}))
    """
    widget = core_widgets.DateRangeWidget
    default_error_messages = {
        'customized_empty': _(
            'If you select «customized» you have to specify a start date and/or an end date.'
        ),
        'customized_invalid': _('Start date has to be before end date.'),
    }

    def __init__(self, *, render_as='table', **kwargs):
        # TODO: are these attributes useful ??
        self.ranges = ranges = fields.ChoiceField(
            required=False,
            choices=lambda: [
                ('', pgettext_lazy('creme_core-date_range', 'Customized')),
                *date_range_registry.choices(),
            ],
        )
        self.start_date = fields.DateField(required=False)
        self.end_date   = fields.DateField(required=False)
        self.render_as = render_as

        super().__init__(
            fields=(
                ranges,
                self.start_date,
                self.end_date,
            ),
            require_all_fields=False,
            **kwargs
        )

        self.widget.choices = ranges.widget.choices  # Get the CallableChoiceIterator

    def compress(self, data_list):
        return (data_list[0], data_list[1], data_list[2]) if data_list else ('', '', '')

    def clean(self, value):
        range_name, start, end = super().clean(value)

        if range_name == '':
            if not start and not end and self.required:
                raise ValidationError(
                    self.error_messages['customized_empty'],
                    code='customized_empty',
                )

            if start and end and start > end:
                raise ValidationError(
                    self.error_messages['customized_invalid'],
                    code='customized_invalid',
                )

        return date_range_registry.get_range(range_name, start, end)

    def widget_attrs(self, widget):
        return {'render_as': self.render_as}


class ColorField(fields.CharField):
    """A Field which handles HTML colors (e.g: #F2FAB3) without '#' """
    default_validators = [validators.validate_color]
    widget = core_widgets.ColorPickerWidget
    default_error_messages = {
        'invalid': _('Enter a valid value (eg: DF8177).'),
    }

    def __init__(self, *, max_length=6, min_length=6, **kwargs):
        super().__init__(max_length=max_length, min_length=min_length, **kwargs)

    def clean(self, value):
        return super().clean(value).upper()


class DurationField(fields.MultiValueField):
    widget = core_widgets.DurationWidget
    default_error_messages = {
        'invalid': _('Enter a whole number.'),
        'min_value': _('Ensure this value is greater than or equal to %(limit_value)s.'),
    }

    def __init__(self, **kwargs):
        IntegerField = fields.IntegerField
        self.hours   = IntegerField(min_value=0)
        self.minutes = IntegerField(min_value=0)
        self.seconds = IntegerField(min_value=0)

        super().__init__(fields=(self.hours, self.minutes, self.seconds), **kwargs)

    def compress(self, data_list):
        return (
            data_list[0], data_list[1], data_list[2]
        ) if data_list else ('', '', '')

    def clean(self, value):
        hours, minutes, seconds = super().clean(value)
        return ':'.join([
            str(hours or 0), str(minutes or 0), str(seconds or 0)
        ])


class ChoiceOrCharField(fields.MultiValueField):
    """Field which combines a ChoiceField & a CharField ; the user can fill the
    second one if no choice is satisfying.
    """
    widget = core_widgets.ChoiceOrCharWidget

    default_error_messages = {
        'invalid_other': _('Enter a value for "Other" choice.'),
    }

    def __init__(self, *, choices=(), **kwargs):
        """@param choices Sequence of tuples (id, value).
                          BEWARE: id should not be a null value (like '', 0, etc..).
        """
        self.choice_field = choice_field = fields.ChoiceField()
        super().__init__(
            fields=(choice_field, fields.CharField(required=False)),
            require_all_fields=False,
            **kwargs
        )
        self.choices = choices

    @property
    def choices(self):
        return self._choices

    @choices.setter
    def choices(self, value):
        """See ChoiceField._set_choices()."""
        self._choices = self.choice_field.choices = self.widget.choices = [
            (0, _('Other')),
            *value,
        ]

    def compress(self, data_list):
        index = None
        strval = None

        if data_list:
            index = data_list[0]

            if index == '0':
                index = 0
                strval = data_list[1]
            elif index:
                index, strval = find_first(self.choices, lambda item: str(item[0]) == index)

        return index, strval

    def clean(self, value):
        value = super().clean(value)

        if value[0] == 0 and not value[1]:
            raise ValidationError(
                self.error_messages['invalid_other'],
                code='invalid_other',
            )

        return value


class CTypeChoiceField(fields.Field):
    "A ChoiceField whose choices are a ContentType instances."
    widget = widgets.Select
    default_error_messages = {
        'invalid_choice': _(
            'Select a valid choice. That choice is not one of the available choices.'
        ),
    }

    # TODO: ctypes_or_models ??
    def __init__(self, *, ctypes=(), empty_label='---------',
                 required=True, widget=None, label=None, initial=None,
                 help_text='',
                 to_field_name=None, limit_choices_to=None,  # TODO: manage ?
                 **kwargs):
        "@param ctypes: A sequence of ContentTypes or a callable which returns one."
        super().__init__(
            required=required, widget=widget, label=label,
            initial=initial, help_text=help_text,
            **kwargs
        )
        self.empty_label = empty_label
        self.ctypes = ctypes

    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)
        result._ctypes = deepcopy(self._ctypes, memo)
        return result

    @property
    def ctypes(self):
        return self._ctypes()

    @ctypes.setter
    def ctypes(self, ctypes):
        if not callable(ctypes):
            ctypes_list = [*ctypes]

            def ctypes():
                return ctypes_list

        self._ctypes = ctypes
        self.widget.choices = fields.CallableChoiceIterator(
            lambda: self._build_empty_choice(self._build_ctype_choices(self.ctypes))
        )

    def _build_empty_choice(self, choices):
        return choices if self.required else [('', self.empty_label), *choices]

    def _build_ctype_choices(self, ctypes):
        return ctype_choices(ctypes)

    def prepare_value(self, value):
        return value.id if isinstance(value, ContentType) else super().prepare_value(value)

    def to_python(self, value):
        if value in self.empty_values:
            return None

        try:
            ct_id = int(value)

            for ctype in self.ctypes:
                if ctype.id == ct_id:
                    return ctype
        except ValueError:
            pass

        raise ValidationError(
            self.error_messages['invalid_choice'],
            code='invalid_choice',
        )


class MultiCTypeChoiceField(CTypeChoiceField):
    """Multiple version of CTypeChoiceField."""
    widget = core_widgets.UnorderedMultipleChoiceWidget  # Beware: use Choice inner class

    def _build_ctype_choices(self, ctypes):
        Choice = self.widget.Choice
        get_app_conf = apps.get_app_config

        choices = [
            (
                Choice(ct.id, help=get_app_conf(ct.app_label).verbose_name),
                str(ct),
            ) for ct in ctypes
        ]
        sort_key = collator.sort_key
        choices.sort(key=lambda k: sort_key(k[1]))

        return choices

    def _build_empty_choice(self, choices):
        return choices

    def prepare_value(self, value):
        prepare_value = super().prepare_value

        return (
            [prepare_value(v) for v in value]
            if hasattr(value, '__iter__') else
            prepare_value(value)
        )

    def to_python(self, value):
        ctypes = []

        if value not in self.empty_values:
            to_python = super().to_python
            ctypes.extend(to_python(ct_id) for ct_id in value)

        return ctypes


class EntityCTypeChoiceField(CTypeChoiceField):
    """Version of CTypeChoiceField where all ContentTypes correspond to classes
    inheriting CremeEntity.
    """
    def __init__(self, *, ctypes=None, **kwargs):
        ctypes = ctypes or entity_ctypes
        super().__init__(ctypes=ctypes, **kwargs)


class MultiEntityCTypeChoiceField(MultiCTypeChoiceField):
    """Multiple version of EntityCTypeChoiceField."""
    def __init__(self, *, ctypes=None, **kwargs):
        ctypes = ctypes or entity_ctypes
        super().__init__(ctypes=ctypes, **kwargs)


class EnhancedChoiceIterator:
    def __init__(self, field, choices):
        self.field = field
        self.choices = choices
        self.forced_values = field.forced_values
        self.choice_cls = field.widget.Choice

    def __iter__(self):
        choices = self.choices
        forced_values = self.forced_values

        # for x in (choices() if callable(choices) else choices):
        #     if isinstance(x, dict):
        #         value = x['value']
        #         label = x['label']
        #         help_txt = x.get('help', '')
        #     else:
        #         value, label = x
        #         help_txt = ''
        #
        #     yield (
        #         self.choice_cls(
        #             value=value,
        #             readonly=(value in forced_values),
        #             help=help_txt,
        #         ),
        #         label,
        #     )
        for choice in (choices() if callable(choices) else choices):
            if isinstance(choice, dict):
                choice_kwargs = {**choice}
                value = choice_kwargs['value']
                label = choice_kwargs.pop('label')
            else:
                value, label = choice
                choice_kwargs = {'value': value}

            choice_kwargs['readonly'] = (value in forced_values)

            yield (self.choice_cls(**choice_kwargs), label)


class EnhancedMultipleChoiceField(fields.MultipleChoiceField):
    """Specialization of MultipleChoiceField with some improvements.
    It allows:
     - to force some choices. The forced choices cannot be un-selected.
       It's useful to show to the user the choices which will be automatically
       applied (instead of hiding them).
     - to display a help text for each choice (you have to use the <dict>
       format for choice).

    Format for <choices> (constructor argument & property setter):
        - Classical list of 2-tuples (value, label).
        - List of dict {'value': value, 'label': label}
          A key "help" is also available for the help text.
        - A callable without argument which return one the the previous format.
    """
    widget = core_widgets.UnorderedMultipleChoiceWidget
    iterator = EnhancedChoiceIterator

    def __init__(self, *, forced_values=(), iterator=None, **kwargs):
        """Constructor.

        @param forced_values: Iterable of values (ie: the "value" part of choices).
        @param iterator: Class with the interface of <EnhancedChoiceIterator>.
        @param kwargs: See <MultipleChoiceField>.
        """
        self._raw_choices = None  # Backup of the choices, in order to build iterator.
        self._initial = None
        self._forced_values = frozenset(forced_values)

        if iterator is not None:
            self.iterator = iterator

        super().__init__(**kwargs)

    @fields.MultipleChoiceField.choices.setter
    def choices(self, value):
        self._raw_choices = value
        self._choices = self.widget.choices = self.iterator(field=self, choices=value)

    def clean(self, value):
        value = super().clean(value)

        for fv in self._forced_values:
            v = str(fv)
            if v not in value:
                value.append(v)

        return value

    @property
    def forced_values(self):
        """@return: A frozenset of values."""
        return self._forced_values

    @forced_values.setter
    def forced_values(self, values):
        """@param values: Iterable of values (ie: the "value" part of choices)."""
        self._forced_values = frozenset(values or ())
        self.choices = self._raw_choices

    @property
    def initial(self):
        result = set()

        initial = self._initial
        if initial is not None:
            result.update(initial)

        result.update(self._forced_values)

        return result

    @initial.setter
    def initial(self, value):
        self._initial = value


class EnhancedModelChoiceIterator(mforms.ModelChoiceIterator):
    def __init__(self, field):
        super().__init__(field=field)
        self.forced_values = field.forced_values
        self.choice_cls = field.widget.Choice

    def help(self, obj):
        """Builds a help text for a choice.

        Override this method to create not-empty messages.

        @param obj: Instance of <django.db.models.Model>.
        @return: A string.
        """
        return ''

    def choice(self, obj):
        # pk, label = super().choice(obj)
        value, label = super().choice(obj)
        pk = value.value

        # NB: django's ModelChoiceIteratorValue stores the instance (obj)
        # => TODO: do the same thing ?
        return (
            self.choice_cls(
                value=pk,
                readonly=(pk in self.forced_values),
                help=self.help(obj),
            ),
            label,
        )


class EnhancedModelMultipleChoiceField(mforms.ModelMultipleChoiceField):
    """Specialization of ModelMultipleChoiceField with some improvements.
    It allows:
     - to force some choices. The forced choices cannot be un-selected.
       It's useful to show to the user the choices which will be automatically
       applied (instead of hiding them).
     - to display a help text for each choice (you have to use a customised
       choice iterator class).
    """
    widget = core_widgets.UnorderedMultipleChoiceWidget
    iterator = EnhancedModelChoiceIterator

    def __init__(self, *, forced_values=(), iterator=None, **kwargs):
        """Constructor.

        @param forced_values: Iterable of PKs (or values of the attribute
               corresponding to "to_field_name").
        @param iterator: Class with the interface of <EnhancedModelChoiceIterator>.
        @param kwargs: See <ModelMultipleChoiceField>.
        """
        self._initial = None
        self._forced_values = frozenset(forced_values)

        if iterator is not None:
            self.iterator = iterator

        super().__init__(**kwargs)

    def prepare_value(self, value):
        prepared_value = super().prepare_value(value)

        if self._forced_values and isinstance(prepared_value, list):
            prepared_value.extend(self._forced_values)

        return prepared_value

    @property
    def forced_values(self):
        """@return A frozenset of PKs."""
        return self._forced_values

    @forced_values.setter
    def forced_values(self, values):
        """@param values: Iterable of PKs."""
        self._forced_values = frozenset(values or ())
        self.widget.choices = self.choices

    @property
    def initial(self):
        result = set()
        initial = self._initial
        if initial is not None:
            result.update(initial)

        result.update(self._forced_values)

        return result

    @initial.setter
    def initial(self, value):
        self._initial = value


class ReadonlyMessageField(fields.CharField):
    """Field made to display a message to the user.
    POSTed value is ignored, the given default value is always returned.
    """
    widget = core_widgets.Label

    def __init__(self, *, label, initial='', widget=None, return_value=None):
        super().__init__(
            label=label,
            widget=widget,
            initial=initial,
            required=False,
        )
        self.return_value = return_value

    def clean(self, value):
        return self.return_value
