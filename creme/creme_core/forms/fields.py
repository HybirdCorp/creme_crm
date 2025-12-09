################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

import itertools
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Iterator, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from json import loads as json_load
from typing import Any

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.validators import validate_email
from django.db.models.query import Q, QuerySet, prefetch_related_objects
from django.forms import ValidationError, fields
from django.forms import models as mforms
from django.forms import widgets
from django.urls import reverse
from django.utils.choices import CallableChoiceIterator
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ..auth.entity_credentials import EntityCredentials
from ..core import validators
from ..core.entity_filter import EF_REGULAR
from ..gui import quick_forms
from ..models import (
    CremeEntity,
    CremePropertyType,
    CremeUser,
    EntityFilter,
    Relation,
    RelationType,
)
from ..utils.collections import OrderedSet
from ..utils.content_type import ctype_choices, entity_ctypes
from ..utils.date_period import DatePeriod, date_period_registry
from ..utils.date_range import date_range_registry
from ..utils.serializers import json_encode
from ..utils.unicode_collation import collator
from . import enumerable as enum_fields
from . import validators as f_validators
from . import widgets as core_widgets

__all__ = (
    'GenericEntityField', 'MultiGenericEntityField',
    'RelationEntityField', 'MultiRelationEntityField',
    'CreatorEntityField', 'MultiCreatorEntityField',
    'FilteredEntityTypeField',
    'OptionalField', 'OptionalChoiceField', 'OptionalModelChoiceField',
    'ListEditionField',
    'DatePeriodField', 'DateRangeField',
    'IntegerPercentField', 'ColorField', 'DurationField',
    'ChoiceOrCharField',
    'CTypeChoiceField', 'EntityCTypeChoiceField',
    'MultiCTypeChoiceField', 'MultiEntityCTypeChoiceField',
    'EnhancedMultipleChoiceField', 'EnhancedModelMultipleChoiceField',
    'ReadonlyMessageField',
)


class CremeUserEnumerableField(enum_fields.EnumerableModelChoiceField):
    """Specialization of EnumerableModelChoiceField the User model.
    The user set by the form (see CremeForm/CremeModelForm) is used as initial
    choice by default.
    """
    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        if self.initial is None:
            self.initial = None if user is None else user.id


class JSONField(fields.CharField):
    default_error_messages = {
        'invalidformat':    _('Invalid format'),
        'invalidtype':      _('Invalid type'),
        'doesnotexist':     _('This entity does not exist.'),  # TODO: 'An entity ...' ?
        'isdeleted':        _('«%(entity)s» is in the trash.'),
        'isexcluded':       _('«%(entity)s» violates the constraints.'),

        'ctypedoesnotexist': _('This content type does not exist.'),
        'ctyperequired': _('The content type is required.'),

        # Used by child classes
        'entityrequired':   _('The entity is required.'),
        'ctypenotallowed':  _('This content type is not allowed.'),
    }
    value_type: type | None = None  # Overload this: type of the value returned by the field.

    def __init__(self, *, user: CremeUser | None = None, **kwargs):
        super().__init__(**kwargs)
        self._user = user
        self.widget.from_python = self.from_python

    def __deepcopy__(self, memo):
        obj = super().__deepcopy__(memo)
        obj.widget.from_python = obj.from_python
        return obj

    @property
    def user(self) -> CremeUser | None:
        return self._user

    @user.setter
    def user(self, user: CremeUser | None) -> None:
        self._user = user

    def _build_empty_value(self):
        "Value returned by not-required fields, when value is empty."
        if self.value_type is list:
            return []

        return None

    def _return_none_or_raise(self, required, error_key='required'):
        if required:
            raise ValidationError(self.error_messages[error_key], code=error_key)

        return None

    def _return_list_or_raise(self, required, error_key='required') -> list:
        if required:
            raise ValidationError(self.error_messages[error_key], code=error_key)

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

    def _clean_ctype(self, ctype_id: int) -> ContentType | None:
        # TODO: validate integer (avoid putting strings in the ContentType's cache?)?
        if not ctype_id:
            if self.required:
                raise ValidationError(
                    self.error_messages['ctyperequired'],
                    code='ctyperequired',
                )

            return None

        try:
            ctype = ContentType.objects.get_for_id(ctype_id)
        except ContentType.DoesNotExist as e:
            raise ValidationError(
                self.error_messages['ctypedoesnotexist'],
                code='ctypedoesnotexist',
            ) from e

        return ctype

    def _clean_entity(self,
                      ctype: ContentType | int,
                      entity_pk: int | str,
                      ) -> CremeEntity | None:
        """Clean a CremeEntity from its model & its PK.
        @param ctype: ContentType instance, or ContentType's PK.
        @param entity_pk: ID of CremeEntity instance.
        @raise: ValidationError.
        """
        if not isinstance(ctype, ContentType):
            ctype = self._clean_ctype(ctype)

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

    def _entity_queryset(self, model: type[CremeEntity], qfilter: Q | None = None) -> QuerySet:
        query = model.objects.all()

        if qfilter is not None:
            query = query.filter(qfilter)

        return query

    def _clean_entity_from_model(self,
                                 model: type[CremeEntity],
                                 entity_pk: int,
                                 qfilter: Q | None = None,
                                 ) -> CremeEntity:
        """@raise: ValidationError"""
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
                 credentials: int = EntityCredentials.LINK,
                 quickforms_registry=None,
                 **kwargs):
        """Constructor.
        @param credentials: Binary combination of EntityCredentials.{VIEW, CHANGE, LINK}.
                            Default value is EntityCredentials.LINK.
        """
        super().__init__(**kwargs)
        self._credentials = credentials
        # self.quickforms_registry = quickforms_registry or quick_forms.quickform_registry
        self.quickform_registry = quickforms_registry or quick_forms.quickform_registry

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
        # return self.quickforms_registry.get_form_class(model) is not None
        return self.quickform_registry.get_form_class(model) is not None


class GenericEntityField(EntityCredsJSONField):
    """Select a CremeEntity which types is among a limited list of possibilities.

    Example:
        field = GenericEntityField(
            label='Friend entity',
            models=[Organisation, Contact, Document],
        )

        # Initial value possibilities
        # The instance 'my_contact' is pre-selected
        field.initial = my_contact
        field.initial = my_contact.id

        # Only the model is pre-selected
        field.initial = ContentType.objects.get_for_model(Contact)
    """
    widget: type[widgets.TextInput] = core_widgets.CTEntitySelector
    value_type: type = dict

    def __init__(self, *,
                 models: Iterable[type[CremeEntity]] = (),
                 autocomplete=True, creator=True, user=None,
                 **kwargs):
        """Constructor.
        @param models: types of CremeEntity which are available.
        @param autocomplete: autocompletion for the selector of models?
        @param creator: True means a button to create instance is displayed;
               Notice the model must have a registered quick-form too.
        @param user: logged user.
        """
        super().__init__(**kwargs)
        self.creator = creator
        self.autocomplete = autocomplete
        self._user = user
        self.allowed_models = models

    @property
    def allowed_models(self) -> list[type[CremeEntity]]:
        """Types of CremeEntity which are available."""
        return self._allowed_models

    @allowed_models.setter
    def allowed_models(self, allowed: Iterable[type[CremeEntity]]) -> None:
        self._allowed_models = [*allowed]
        self._update_widget_choices()

    @EntityCredsJSONField.user.setter
    def user(self, user):
        self._user = user
        self._update_widget_choices()

    @property
    def autocomplete(self):
        """Autocompletion for the selector of models?"""
        return self._autocomplete

    @autocomplete.setter
    def autocomplete(self, autocomplete):
        self._autocomplete = autocomplete
        self.widget.autocomplete = autocomplete

    @property
    def creator(self):
        """Display a button to create instance?"""
        return self._creator

    @creator.setter
    def creator(self, creator):
        self._creator = creator
        self.widget.creator = creator

    def widget_attrs(self, widget):
        return {'reset': False}

    def _update_widget_choices(self):
        self.widget.content_types = CallableChoiceIterator(self._get_ctypes_options)

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
        elif isinstance(value, ContentType):
            ctype = value
            pk = None
        else:
            return value

        ctype_create_url = self._create_url(self.user, ctype)

        return {
            'ctype': {
                'id': ctype.id,
                'create': ctype_create_url,
                'create_label': str(ctype.model_class().creation_label),
            },
            'entity': pk,
        }

    def _value_from_unjsonfied(self, data):
        clean_value = self.clean_value
        required = self.required

        ctype_choice = clean_value(data, 'ctype', dict, required, 'ctyperequired')
        ctype_pk = clean_value(ctype_choice, 'id', int, required, 'ctyperequired')

        entity_pk = clean_value(data, 'entity', int, required, 'entityrequired')
        ctype = self._clean_ctype(ctype_pk)

        return self._check_entity_perms(
            entity=self._clean_entity(ctype=ctype, entity_pk=entity_pk),
        ) if ctype else None

    def _clean_ctype(self, ctype_pk):
        ctype = super()._clean_ctype(ctype_pk)

        if ctype and not any(
            ctype == allowed_ct for allowed_ct in self.get_ctypes()
        ):
            raise ValidationError(
                self.error_messages['ctypenotallowed'], code='ctypenotallowed',
            )

        return ctype

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

    def get_ctypes(self) -> list[ContentType]:
        """Available models as a list of ContentTypes."""
        models = self._allowed_models

        if models:
            get_ct = ContentType.objects.get_for_model

            return [get_ct(model) for model in models]

        return [*entity_ctypes()]


# TODO: Add a q_filter, see utilization in EntityEmailForm
# TODO: propose to allow duplicates ???
class MultiGenericEntityField(GenericEntityField):
    widget = core_widgets.MultiCTEntitySelector
    value_type: type = list

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
        # We want to keep the global order (left by defaultdict)
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
            ctype_choice = clean_value(entry, 'ctype', dict, required=False)
            ctype_pk = clean_value(ctype_choice, 'id', int, required=False)

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
        'rtypenotallowed': _(
            'This type of relationship causes a constraint error '
            '(id="%(rtype_id)s").'
        ),
    }
    value_type: type = dict

    def __init__(self, *,
                 allowed_rtypes=RelationType.objects.none(),
                 autocomplete=False,
                 **kwargs):
        super().__init__(**kwargs)
        self.autocomplete = autocomplete
        self.allowed_rtypes = allowed_rtypes

    @property
    def allowed_rtypes(self):
        # TODO: .all()?
        return self._allowed_rtypes

    @allowed_rtypes.setter
    def allowed_rtypes(self, allowed):
        self._allowed_rtypes = (
            allowed if isinstance(allowed, QuerySet) else
            RelationType.objects.filter(id__in=allowed)
        )
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
        entity = self._clean_entity(ctype_pk, entity_pk)
        self._check_entity_perms(entity)

        Relation(
            # user=self.user
            subject_entity=entity,
            type=rtype.symmetric_type,
        ).clean_subject_entity()

        # TODO: return Relation?
        return rtype, entity

    def _clean_rtype(self, rtype_pk):
        rtypes = self._allowed_rtypes

        try:
            rtype = rtypes.select_related('symmetric_type').get(pk=rtype_pk)
        except rtypes.model.DoesNotExist as e:
            raise ValidationError(
                self.error_messages['rtypenotallowed'],
                code='rtypenotallowed',
                params={'rtype_id': rtype_pk},
            ) from e

        return rtype

    def _get_options(self):  # TODO: inline
        return ChoiceModelIterator(self._allowed_rtypes)


class MultiRelationEntityField(RelationEntityField):
    widget: type[widgets.TextInput] = core_widgets.MultiRelationSelector
    value_type: type = list

    def _value_to_jsonifiable(self, value):
        return [*map(super()._value_to_jsonifiable, value)]

    def _clean_ctype(self, ctype_id: int) -> ContentType:
        try:
            ctype = ContentType.objects.get_for_id(ctype_id)
        except ContentType.DoesNotExist as e:
            raise ValidationError(str(e)) from e

        return ctype

    def _clean_entities(self,
                        ctype: ContentType,
                        entity_ids: Sequence[int],
                        ) -> dict[int, CremeEntity]:
        entities = {
            entity.id: entity
            for entity in ctype.get_all_objects_for_this_type(pk__in=entity_ids)
        }

        if any(entity_id not in entities for entity_id in entity_ids):
            raise ValidationError(
                self.error_messages['doesnotexist'],
                code='doesnotexist',
                # TODO: params={'entity_id': ...} ?
            )

        for entity in entities.values():
            if entity.is_deleted:
                raise ValidationError(
                    self.error_messages['isdeleted'],
                    code='isdeleted',
                    params={'entity': entity.allowed_str(self._user)},
                )

        return entities

    def _clean_rtypes(self, rtype_ids: Collection[str]) -> dict[str, RelationType]:
        rtypes_by_ids = self._allowed_rtypes.select_related('symmetric_type').in_bulk(rtype_ids)

        for rtype_id in rtype_ids:
            if rtype_id not in rtypes_by_ids:
                raise ValidationError(
                    self.error_messages['rtypenotallowed'],
                    params={'rtype_id': rtype_id},
                    code='rtypenotallowed',
                )

        return rtypes_by_ids

    def _value_from_unjsonfied(self, data):
        clean_value = self.clean_value
        cleaned_entries = []
        rtype_ids = set()
        entity_ids_by_ct_id = defaultdict(list)

        for entry in data:
            rtype_id = clean_value(entry, 'rtype', str)

            ctype_id = clean_value(entry, 'ctype', int, required=False)
            if not ctype_id:
                continue

            entity_id = clean_value(entry, 'entity', int, required=False)
            if not entity_id:
                continue

            rtype_ids.add(rtype_id)
            entity_ids_by_ct_id[ctype_id].append(entity_id)
            cleaned_entries.append((rtype_id, entity_id))

        rtypes_by_id = self._clean_rtypes(rtype_ids)

        entities_by_id = {}
        for ctype_id, entity_ids in entity_ids_by_ct_id.items():
            entities_by_id.update(self._clean_entities(
                ctype=self._clean_ctype(ctype_id),
                entity_ids=entity_ids,
            ))

        self._check_entities_perms(entities_by_id.values())

        # Prefetching
        prefetch_related_objects(
            [
                single_rtype
                for rtype in rtypes_by_id.values()
                for single_rtype in (rtype, rtype.symmetric_type)
            ],
            'subject_ctypes',
            'subject_properties',
            'subject_forbidden_properties',
        )
        CremeEntity.populate_properties(entities_by_id.values())

        relations = []

        for rtype_id, entity_id in cleaned_entries:
            rtype = rtypes_by_id[rtype_id]
            entity = entities_by_id[entity_id]

            Relation(
                # user=self.user
                subject_entity=entity,
                type=rtype.symmetric_type,
            ).clean_subject_entity()

            # TODO: return Relations?
            relations.append((rtype, entity))

        if not relations:
            return self._return_list_or_raise(self.required)

        return relations


class CreatorEntityField(EntityCredsJSONField):
    # The following attributes are set: model, q_filter, creation_url, creation_allowed
    widget = core_widgets.EntityCreatorWidget

    value_type: type = int

    def __init__(self, *,
                 model: type[CremeEntity] | None = None,
                 q_filter: dict | Q | Callable | None = None,
                 create_action_url='',
                 create_action_label=None,  # TODO: empty string instead?
                 user: CremeUser | None = None,
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
    def force_creation(self) -> bool:
        return self._force_creation

    @force_creation.setter
    def force_creation(self, force_creation: bool) -> None:
        self._force_creation = force_creation
        self._update_creation_info()

    @property
    def model(self) -> type[CremeEntity] | None:
        return self._model

    @model.setter
    def model(self, model: type[CremeEntity] | None):
        self._model = model
        self.widget.model = model
        self._update_creation_info()

    @property
    def q_filter(self) -> dict | Q | Callable:
        return self._q_filter

    @q_filter.setter
    def q_filter(self, q_filter: dict | Q | Callable | None) -> None:
        """
        @param q_filter: Allows to filter the selection. Same meaning than Model.limit_choices_to ;
               so it can be dictionary (e.g. {'user__is_staff': False}),
               a <django.db.models.query.Q instance>,
               or a callable which returns dictionary/Q.
               <None> means not filtering.
        """
        self.widget.q_filter = self._q_filter = q_filter
        self._update_creation_info()

    @property
    def q_filter_query(self) -> Q | None:
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
    def create_action_label(self) -> str | None:
        return self._create_action_label

    @create_action_label.setter
    def create_action_label(self, label: str | None) -> None:
        self._create_action_label = self.widget.creation_label = label

    @property
    def create_action_url(self) -> str:
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
    def create_action_url(self, url: str) -> None:
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
    value_type: type = list

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

    def __init__(self, *,
                 ctypes: Callable | Sequence[int | ContentType] = entity_ctypes,
                 filter_types=(EF_REGULAR,),
                 empty_label=None,
                 **kwargs):
        """Constructor.
        @param ctypes: Allowed content types.
               - A callable which returns an iterable of ContentType IDs / instances.
               - Sequence of ContentType IDs / instances.
        @param filter_types: Allowed types of filter.
        """
        super().__init__(**kwargs)
        self._empty_label = empty_label
        self.ctypes = ctypes
        self.filter_types = filter_types

    def _build_empty_value(self):
        return None, None

    def _clean_ctype(self, ctype_pk):
        for ct in self.ctypes:
            if ctype_pk == ct.id:
                return ct

    @property
    def ctypes(self) -> list[ContentType]:
        get_ct = ContentType.objects.get_for_id
        return [
            ct_or_ctid if isinstance(ct_or_ctid, ContentType) else get_ct(ct_or_ctid)
            for ct_or_ctid in self._ctypes()
        ]

    @ctypes.setter
    def ctypes(self, ctypes: Callable | Sequence[int | ContentType]) -> None:
        "See constructor."
        if not callable(ctypes):
            ctypes_list = [*ctypes]  # We copy the sequence to avoid external modifications

            def ctypes():
                return ctypes_list

        self._ctypes = ctypes
        self.widget.content_types = CallableChoiceIterator(self._get_choices)

    @property
    def filter_types(self) -> Iterator[str]:
        yield from self._filter_types

    @filter_types.setter
    def filter_types(self, value: Iterable[str]):
        self._filter_types = self.widget.efilter_types = [*value]

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
                efilter = EntityFilter.objects.filter_by_user(
                    self._user, types=self.filter_types,
                ).filter(entity_type=ct).get(pk=efilter_pk)
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
    widget: type[core_widgets.OptionalWidget] = core_widgets.OptionalWidget

    default_error_messages = {
        'subfield_required': _('Enter a value if you check the box.'),
    }

    @dataclass(frozen=True)
    class Option:
        is_set: bool = False
        data: Any = None

        def __post_init__(self):
            if not self.is_set and self.data is not None:
                raise ValueError('Option: data cannot be set')

    def __init__(self,
                 *,
                 required=True,  # Not used because it does not mean anything here
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
                self._build_subfield(required=False, **kwargs),
            ),
            required=False,
            require_all_fields=False,
            widget=widget, label=label, initial=initial, help_text=help_text,
            disabled=disabled,
        )
        self.widget.sub_label = sub_label

    def _build_subfield(self, **kwargs):
        return self.sub_field(**kwargs)

    def compress(self, data_list):
        if data_list:
            is_set = data_list[0] if data_list else False
            data = data_list[1] if (is_set and len(data_list) > 1) else None
        else:
            is_set = False
            data = None

        return self.Option(is_set=is_set, data=data)

    def validate(self, value):
        if value.is_set and value.data in self.empty_values:
            raise ValidationError(
                self.error_messages['subfield_required'],
                code='subfield_required',
            )

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


class UnionField(fields.Field):
    """Base class for fields which are a union of other subfields, ie the user
    has to pick one subfield among several ones (of potentially different types).

    It's particularly useful when the subfields are complex ; you can use simpler
    & more specific field/widget in other cases (see 'ChoiceOrCharField').
    """
    widget = core_widgets.UnionWidget
    default_error_messages = {
        'invalid': 'No sub-data related to your choice.',
    }

    def __init__(self, fields_choices=(), empty_label=_('Empty'), **kwargs):
        """Constructor.
        @param fields_choices: A sequence of tuples (field_id, field).
               Each 'field_id' must be unique (strings & integers are good choices).
               'field' is an instance of <django.forms.Field>.
        @param empty_label: Label used when the field is not required to propose
               an additional empty choice.
        """
        self._fields_choices = []
        super().__init__(**kwargs)
        self.empty_label = empty_label
        self.fields_choices = fields_choices

    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)

        # Need to force a new CallableChoiceIterator to be created.
        result.fields_choices = result.fields_choices

        return result

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, value):
        self._disabled = value

        for choice in self._fields_choices:
            choice[1].disabled = value

    @property
    def fields_choices(self):
        # TODO: copy?
        return self._fields_choices

    @fields_choices.setter
    def fields_choices(self, value):
        "See constructor."
        choices = self._fields_choices
        choices[:] = value

        disabled = self.disabled
        for choice in choices:
            choice[1].disabled = disabled

        def _widget_choices():
            w_choices = []
            if not self.required:
                w_choices.append(('', self.empty_label, widgets.HiddenInput()))

            for name, field in choices:
                w_choices.append((name, field.label, field.widget))

            return w_choices

        self.widget.widgets_choices = CallableChoiceIterator(_widget_choices)

    def validate(self, value):
        super().validate(value=value)
        if value:
            kind, sub_value = value

            if sub_value in self.empty_values and self.required:
                raise ValidationError(self.error_messages['required'], code='required')

    def to_python(self, value):
        # TODO: use 'disabled' attribute?
        if value:
            choice, sub_values = value

            for field_id, field in self._fields_choices:
                if choice == field_id:
                    try:
                        sub_value = sub_values[field_id]
                    except KeyError:
                        raise ValidationError(
                            self.error_messages['invalid'], code='invalid',
                        )

                    return (field_id, field.clean(sub_value))


class ListEditionField(fields.Field):
    """A field to allow the user to edit/delete a list of strings.
    It returns a list with the same order:
    * deleted elements are replaced by None.
    * modified elements are replaced by the new value.
    """
    widget = core_widgets.ListEditionWidget

    def __init__(self, *, content: Sequence[str] = (), only_delete=False, **kwargs):
        """Constructor.
        @param content: Sequence of strings
        @param only_delete: Can only delete elements, not edit them.
        """
        super().__init__(**kwargs)
        self.content = content  # TODO: get an Iterable & build a list?
        self.only_delete = only_delete

    @property
    def content(self) -> Sequence[str]:
        return self._content

    @content.setter
    def content(self, content: Sequence[str]):
        self._content = content
        self.widget.content = content

    @property
    def only_delete(self) -> bool:
        return self._only_delete

    @only_delete.setter
    def only_delete(self, only_delete: bool) -> None:
        self._only_delete = only_delete
        self.widget.only_delete = only_delete


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
    """Field to choose a date period (e.g. "3 weeks").
    This period is modeled with an instance of 'creme_core.utils.date_period.DatePeriod'.

    The field generates an instance of DatePeriod, but you can initialize it
    with a dictionary too (see 'DatePeriod.as_dict()' for the correct keys/values):

        [...]
        from creme.creme_core.utils.date_period import date_period_registry

        class MyForm(forms.Form):
            periodicity = DatePeriodField(label=_('Periodicity'))

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self.fields['periodicity'].initial = date_period_registry.get_period('days', 1)
                # OR
                self.fields['periodicity'].initial = {'type': 'days', 'value': 1}

            def save(self, *args, **kwargs):
                period = self.cleaned_data['periodicity']  # It's a DatePeriod instance.
                [...]
    """
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
    def choices(self):  # TODO: rename "period_choices"?
        return self.fields[0].choices

    @property
    def period_names(self):
        return self._period_names

    @period_names.setter
    def period_names(self, period_names):
        """Set the periods which are valid (they must be registered in the related registry too).
        @param period_names: Sequence of strings (see DatePeriod.name for valid values),
               or None (== all available periods in the registry are used).
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
        # NB: data_list = (period_name, period_value)
        return date_period_registry.get_period(
            *data_list
        ) if data_list and all(data_list) else None


class RelativeDatePeriodField(fields.MultiValueField):
    """Field to choose a relative date period (e.g. "3 weeks before", "1 day after").
    Hint: see DatePeriodField too.
    """
    widget = core_widgets.RelativeDatePeriodWidget

    # TODO: move to 'utils.date_period'?
    class RelativeDatePeriod:
        BEFORE = -1
        AFTER  = 1

        def __init__(self, sign: int, period: DatePeriod):
            if sign not in (self.BEFORE, self.AFTER):
                raise ValueError(f'sign must be in {(self.BEFORE, self.AFTER)}')

            self.sign = sign
            self.period = period

        def __str__(self):
            # TODO: localize?
            return f'{"after" if self.sign == 1 else "before"} {self.period}'

        def __eq__(self, other):
            return (
                isinstance(other, type(self))
                and (self.sign == other.sign)
                and (self.period == other.period)
            )

        def as_dict(self) -> dict:
            "As a jsonifiable dictionary."
            return {
                'sign': self.sign,
                **self.period.as_dict(),
            }

        @classmethod
        def choices(cls):
            return [
                (cls.BEFORE, pgettext_lazy('creme_core-date_period', 'Before')),
                (cls.AFTER,  pgettext_lazy('creme_core-date_period', 'After')),
            ]

    def __init__(self, *, period_registry=date_period_registry, period_names=None, **kwargs):
        """Constructor.
        @param period_registry: See DatePeriodField.
        @param period_names: See DatePeriodField.
        """
        super().__init__(
            (
                fields.TypedChoiceField(
                    coerce=int,
                    # Hint: use the second value to test emptiness
                    empty_value=self.RelativeDatePeriod.AFTER,
                ),
                DatePeriodField(period_registry=period_registry),
            ),
            **kwargs
        )

        self.period_names = period_names
        self.relative_choices = self.RelativeDatePeriod.choices()

    @property
    def period_choices(self):
        return self.fields[1].choices

    @property
    def period_names(self):
        return self.fields[1].period_names

    @period_names.setter
    def period_names(self, period_names):
        """Set the periods which are valid (they must be registered in the related registry too).
        @param period_names: Sequence of strings (see DatePeriod.name for valid values),
               or None (== all available periods in the registry are used).
        """
        period_f = self.fields[1]
        period_f.period_names = period_names
        self.widget.period_choices = period_f.choices

    @property
    def period_registry(self):
        return self.fields[1].period_registry

    @period_registry.setter
    def period_registry(self, period_registry):
        self.fields[1].period_registry = period_registry

    @property
    def relative_choices(self):
        return self.fields[0].choices

    @relative_choices.setter
    def relative_choices(self, choices):
        self.fields[0].choices = self.widget.relative_choices = choices

    def compress(self, data_list):
        return self.RelativeDatePeriod(
            sign=data_list[0], period=data_list[1],
        ) if data_list and all(data_list) else None

    def validate(self, value):
        if self.required and value is None:
            raise ValidationError(self.error_messages['required'], code='required')


class DateRangeField(fields.MultiValueField):
    """A field which returns a creme_core.utils.DateRange.
    Commonly used with a DateRangeWidget.
    For example:
        # Use DateRangeWidget with defaults params
        DateRangeField(label=_('Date range'))

        # Render DateRangeWidget as ul/li
        DateRangeField(label=_('Date range'), widget=DateRangeWidget(attrs={'render_as': 'ul'}))

        # Render DateRangeWidget as a table
        DateRangeField(label=_('Date range'), widget=DateRangeWidget(attrs={'render_as': 'table'}))
    """
    widget = core_widgets.DateRangeWidget
    default_error_messages = {
        # TODO?
        # 'customized_empty': _(
        #     'If you select «customized» you have to specify a start date and/or an end date.'
        # ),
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
        it = itertools.chain(data_list, itertools.repeat(None))
        return date_range_registry.get_range(name=next(it), start=next(it), end=next(it))

    def validate(self, value):
        if not value.name:
            start, end = value.get_dates(now=None)

            if start and end and start > end:
                raise ValidationError(
                    self.error_messages['customized_invalid'],
                    code='customized_invalid',
                )

    def widget_attrs(self, widget):
        return {'render_as': self.render_as}


class IntegerPercentField(fields.IntegerField):
    widget = core_widgets.PercentInput


class DecimalPercentField(fields.DecimalField):
    widget = core_widgets.PercentInput


class YearField(fields.IntegerField):
    widget = core_widgets.YearInput


class ColorField(fields.CharField):
    """A Field which handles HTML colors (e.g: #F2FAB3) without '#'."""
    default_validators = [validators.validate_color]
    widget = widgets.ColorInput
    default_error_messages = {
        'invalid': _('Enter a valid value (e.g. DF8177).'),
    }

    def to_python(self, value):
        return value[1:] if value and value.startswith('#') else value

    def prepare_value(self, value):
        return f'#{value}' if value else ''

    def clean(self, value):
        return super().clean(value).upper()


class DurationField(fields.MultiValueField):
    widget = core_widgets.DurationWidget

    def __init__(self, **kwargs):
        IntegerField = fields.IntegerField
        # TODO: max value?
        # TODO: pass limits to widget
        self.hours   = IntegerField(min_value=0)
        self.minutes = IntegerField(min_value=0)
        self.seconds = IntegerField(min_value=0)

        super().__init__(fields=(self.hours, self.minutes, self.seconds), **kwargs)

    def compress(self, data_list):
        it = itertools.chain(data_list, itertools.repeat(0))

        return timedelta(hours=next(it), minutes=next(it), seconds=next(it))


class ChoiceOrCharField(fields.MultiValueField):
    """Field which combines a ChoiceField & a CharField ; the user can fill the
    second one if no choice is satisfying.
    """
    widget = core_widgets.ChoiceOrCharWidget

    default_error_messages = {
        'invalid_other': _('Enter a value for "Other" choice.'),
    }

    def __init__(self, *, choices: Iterable[tuple] = (), **kwargs):
        """@param choices Sequence of tuples (id, value).
                  BEWARE: "id" should not be a null value (like '', 0, etc...).
        """
        self.choice_field = choice_field = fields.ChoiceField()
        super().__init__(
            fields=(choice_field, fields.CharField(required=False)),
            require_all_fields=False,
            **kwargs
        )
        self.choices = choices

    @property
    def choices(self) -> list[tuple]:
        return self._choices

    @choices.setter
    def choices(self, value) -> None:
        """See ChoiceField._set_choices()."""
        self._choices = self.choice_field.choices = self.widget.choices = [
            (0, _('Other')),
            *value,
        ]

    def compress(self, data_list):
        index = None
        strval = None

        if data_list:
            str_index = data_list[0]

            if str_index == '0':
                index = 0
                strval = data_list[1]
            elif str_index:
                index, strval = next(item for item in self.choices if str(item[0]) == str_index)

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
    def __init__(self, *,
                 ctypes: Iterable[ContentType] | Callable = (),
                 empty_label='---------',
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
    def ctypes(self) -> list[ContentType]:
        return self._ctypes()

    @ctypes.setter
    def ctypes(self, ctypes: Iterable[ContentType] | Callable) -> None:
        if not callable(ctypes):
            ctypes_list = [*ctypes]

            def ctypes():
                return ctypes_list

        self._ctypes = ctypes
        self.widget.choices = CallableChoiceIterator(
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
    # TODO <def __init__(self, *, ctypes=entity_ctypes, **kwargs):> ??
    def __init__(self, *, ctypes=None, **kwargs):
        ctypes = ctypes or entity_ctypes
        super().__init__(ctypes=ctypes, **kwargs)


class MultiEntityCTypeChoiceField(MultiCTypeChoiceField):
    """Multiple version of EntityCTypeChoiceField."""
    # TODO: see above
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
        - A callable without argument which returns one of the previous format.
    """
    widget = core_widgets.UnorderedMultipleChoiceWidget
    iterator = EnhancedChoiceIterator

    def __init__(self, *, forced_values=(), iterator=None, **kwargs):
        """Constructor.

        @param forced_values: Iterable of values (i.e. the "value" part of choices).
        @param iterator: Class with the interface of <EnhancedChoiceIterator>.
        @param kwargs: See <MultipleChoiceField>.
        """
        self._raw_choices = None  # Backup of the choices, in order to build iterator.
        # self._initial = None
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
        """@param values: Iterable of values (i.e. the "value" part of choices)."""
        self._forced_values = frozenset(values or ())
        self.choices = self._raw_choices

    # @property
    # def initial(self):
    #     result = set()
    #
    #     initial = self._initial
    #     if initial is not None:
    #         result.update(initial)
    #
    #     result.update(self._forced_values)
    #
    #     return result
    #
    # @initial.setter
    # def initial(self, value):
    #     self._initial = value
    def prepare_value(self, value):
        prepared = {*value} if value else set()
        prepared.update(self._forced_values)

        return prepared


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
        # self._initial = None
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

    # @property
    # def initial(self):
    #     result = set()
    #     initial = self._initial
    #     if initial is not None:
    #         result.update(initial)
    #
    #     result.update(self._forced_values)
    #
    #     return result
    #
    # @initial.setter
    # def initial(self, value):
    #     self._initial = value


class PropertyTypeChoiceIterator(EnhancedModelChoiceIterator):
    def help(self, obj):
        return obj.description


class PropertyTypesChoiceField(EnhancedModelMultipleChoiceField):
    iterator = PropertyTypeChoiceIterator

    def __init__(self, *,
                 label=_('Properties'),
                 queryset=CremePropertyType.objects.none(),
                 **kwargs):
        super().__init__(label=label, queryset=queryset, **kwargs)


class OrderedChoiceIterator:
    """Generate the choices for OrderedMultipleChoiceField."""
    def __init__(self, field, choices):
        self.field = field
        self.choices = choices
        self.choice_cls = field.widget.Choice

    def __iter__(self):
        choices = self.choices
        choice_cls = self.choice_cls

        # TODO: manage callable choices?
        #       for choice in (choices() if callable(choices) else choices):
        for choice in choices:
            if isinstance(choice, list | tuple):
                value_or_group_name, label_or_sub_choices = choice

                if isinstance(label_or_sub_choices, list | tuple):
                    # TODO
                    # yield (choice_cls(group=True.....), value_or_group_name)
                    #
                    # for sub_choice in label_or_sub_choices:
                    #     if isinstance(sub_choice, dict):
                    #         choice_kwargs = {**sub_choice}
                    #         label = choice_kwargs.pop('label')
                    #         yield (choice_cls(**choice_kwargs), label)
                    #     else:
                    #         assert isinstance(sub_choice, list | tuple)
                    #         value, label = sub_choice
                    #         yield (choice_cls(value=value), label)
                    raise ValueError(
                        'groups are not managed yet. '
                        'Hint: you can use prefix for your labels, '
                        'and/or use disabled items for separators.'
                    )
                else:
                    yield (choice_cls(value=value_or_group_name), label_or_sub_choices)
            elif isinstance(choice, dict):
                choice_kwargs = {**choice}
                label = choice_kwargs.pop('label')

                yield (choice_cls(**choice_kwargs), label)
            else:
                raise ValueError(f'invalid choice format: {choice}')


class OrderedMultipleChoiceField(fields.MultipleChoiceField):
    """Version of MultipleChoiceField where the order of the selected items can
    be set by the user.

    Format of the choices:
        - Classical tuple: (item_id, item_label)
        - Dictionary: {'value': item_id, 'label': item_label}
          Optional keys:
            - "help": an help-text/description of the item
            - "disabled": a boolean ; <True> means that the state of the choice
               (i.e. selected or not selected) cannot be changed.
        - Note: groups are not managed yet. Currently, you can prefix the label
          of the items you want to group (with "my group: " for example) and/or
          use disabled item as group separators.
    """
    widget = core_widgets.OrderedMultipleChoiceWidget
    default_error_messages = {
        'missing_choice': _('The choice %(value)s is mandatory.'),
    }
    iterator = OrderedChoiceIterator

    def __init__(self, *, iterator=None, **kwargs):
        """Constructor.

        @param iterator: Class with the interface of <OrderedChoiceIterator>.
        @param kwargs: See <MultipleChoiceField>.
        """
        if iterator is not None:
            self.iterator = iterator

        super().__init__(**kwargs)

    @fields.MultipleChoiceField.choices.setter
    def choices(self, value):
        self._choices = self.widget.choices = self.iterator(field=self, choices=value)

    def valid_value(self, value):
        # NB: "Optimised" version of valid_value() (we know 'choice' is a Choice instance)
        #     We'll have to improve it if we manage groups.
        text_value = str(value)
        for choice, label in self.choices:
            if text_value == str(choice.value):
                return (
                    any(text_value == str(i) for i in self.initial or ())
                    if choice.disabled
                    else True
                )

        return False

    def validate(self, value):
        super().validate(value)

        if self.initial:
            initial = {str(i) for i in self.initial}

            for choice, _label in self.choices:
                if choice.disabled:
                    str_choice = str(choice.value)

                    if (
                        str_choice in initial
                        and not any(str(val) == str_choice for val in value)
                    ):
                        raise ValidationError(
                            self.error_messages['missing_choice'],
                            code='missing_choice',
                            params={'value': str_choice},
                        )


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
