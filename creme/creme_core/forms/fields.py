# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from future_builtins import map

from collections import defaultdict
from copy import deepcopy
from functools import partial
from itertools import chain
from json import loads as json_load, dumps as json_dump
# from re import compile as compile_re
import warnings

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.core.validators import validate_email
from django.db.models.query import QuerySet, Q
from django.forms import fields, widgets, ValidationError, ModelChoiceField
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from ..auth.entity_credentials import EntityCredentials
from ..constants import REL_SUB_HAS
from ..core import validators
from ..models import RelationType, CremeEntity, EntityFilter
from ..utils import creme_entity_content_types, build_ct_choices, find_first
from ..utils.collections import OrderedSet
from ..utils.date_period import date_period_registry
from ..utils.date_range import date_range_registry
from ..utils.queries import get_q_from_dict
# from .widgets import UnorderedMultipleChoiceWidget
from . import validators as f_validators
from . import widgets as core_widgets


__all__ = ('GenericEntityField', 'MultiGenericEntityField',
           'RelationEntityField', 'MultiRelationEntityField',
           'CreatorEntityField', 'MultiCreatorEntityField',
           'FilteredEntityTypeField',
           'OptionalField', 'OptionalChoiceField', 'OptionalModelChoiceField',
           'ListEditionField',
           'AjaxChoiceField', 'AjaxMultipleChoiceField', 'AjaxModelChoiceField',
           'CremeTimeField', 'CremeDateField', 'CremeDateTimeField',
           'DatePeriodField', 'DateRangeField', 'ColorField', 'DurationField',
           'ChoiceOrCharField',
           'CTypeChoiceField', 'EntityCTypeChoiceField',
           'MultiCTypeChoiceField', 'MultiEntityCTypeChoiceField',
          )


class JSONField(fields.CharField):
    default_error_messages = {
        'invalidformat':    _(u'Invalid format'),
        'invalidtype':      _(u'Invalid type'),
        'doesnotexist':     _(u'This entity does not exist.'),

        # Used by child classes
        'entityrequired':   _(u'The entity is required.'),
        'ctyperequired':    _(u'The content type is required.'),
        'ctypenotallowed':  _(u'This content type is not allowed.'),
    }
    value_type = None  # Overload this: type of the value returned by the field.

    def __init__(self, user=None, *args, **kwargs):
        super(JSONField, self).__init__(*args, **kwargs)
        self._user = user
        self.widget.from_python = self.from_python

    def __deepcopy__(self, memo):
        obj = super(JSONField, self).__deepcopy__(memo)
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

    def _return_list_or_raise(self, required, error_key='required'):
        if required:
            raise ValidationError(self.error_messages[error_key])

        return []

    def clean_value(self, data, name, type, required=True, required_error_key='required'):
        if not data:
            raise ValidationError(self.error_messages['invalidformat'],
                                  code='invalidformat',
                                 )

        if not isinstance(data, dict):
            raise ValidationError(self.error_messages['invalidformat'],
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
        except:
            raise ValidationError(self.error_messages['invalidformat'],
                                  code='invalidformat',
                                 )

    def clean_json(self, value, expected_type=None):
        if not value:
            return self._return_none_or_raise(self.required)

        try:
            data = json_load(value)
        except Exception:
            raise ValidationError(self.error_messages['invalidformat'],
                                  code='invalidformat',
                                 )

        if expected_type is not None and data is not None and not isinstance(data, expected_type):
            raise ValidationError(self.error_messages['invalidtype'], code='invalidtype')

        return data

    def format_json(self, value):
        return json_dump(value)

    # TODO: can we remove this hack with the new widget api (since django 1.2) ??
    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        return self.format_json(self._value_to_jsonifiable(value))

    def clean(self, value):
        data = self.clean_json(value, expected_type=self.value_type)

        if not data:
            if self.required:
                raise ValidationError(self.error_messages['required'], code='required')

            return self._build_empty_value()

        return self._value_from_unjsonfied(data)

    def _clean_entity(self, ctype, entity_pk):
        "@param ctype ContentType instance or PK."
        if not isinstance(ctype, ContentType):
            try:
                ctype = ContentType.objects.get_for_id(ctype)
            except ContentType.DoesNotExist:
                raise ValidationError(self.error_messages['doesnotexist'],
                                      params={'ctype': ctype},
                                      code='doesnotexist',
                                     )

        entity = None

        if not entity_pk:
            if self.required:
                raise ValidationError(self.error_messages['required'], code='required')
        else:
            model = ctype.model_class()
            assert issubclass(model, CremeEntity)

            try:
                entity = model.objects.get(is_deleted=False, pk=entity_pk)
            except model.DoesNotExist:
                raise ValidationError(self.error_messages['doesnotexist'],
                                      params={'ctype': ctype.pk,
                                              'entity': entity_pk,
                                             },
                                      code='doesnotexist',
                                     )

        return entity

    def _entity_queryset(self, model, qfilter=None):
        query = model.objects.filter(is_deleted=False)

        if qfilter is not None:
            query = query.filter(qfilter)

        return query

    def _clean_entity_from_model(self, model, entity_pk, qfilter=None):
        try:
            return self._entity_queryset(model, qfilter).get(pk=entity_pk)
        except model.DoesNotExist:
            if self.required:
                raise ValidationError(self.error_messages['doesnotexist'],
                                      code='doesnotexist',
                                     )

    # def _create_widget(self):
    #     raise NotImplementedError
    #
    # def _build_widget(self):
    #     warnings.warn("JSONField._build_widget() is deprecated ; "
    #                   "set a 'widget' class attribute in your field instead.",
    #                   DeprecationWarning
    #                  )
    #     self.widget = self._create_widget()
    #     self.widget.from_python = lambda v: self.from_python(v)

    def _value_from_unjsonfied(self, data):
        "Build the field value from deserialized data."
        return data

    def _value_to_jsonifiable(self, value):
        "Convert the python value to jsonifiable object."
        return value


class EntityCredsJSONField(JSONField):
    "Base field which checks the permission for the retrieved entities"
    CREDS_VALIDATORS = [
        (EntityCredentials.VIEW,   f_validators.validate_viewable_entity, f_validators.validate_viewable_entities),
        (EntityCredentials.CHANGE, f_validators.validate_editable_entity, f_validators.validate_editable_entities),
        (EntityCredentials.LINK,   f_validators.validate_linkable_entity, f_validators.validate_linkable_entities),
    ]

    def __init__(self, credentials=EntityCredentials.LINK, *args, **kwargs):
        """Constructor.
        @param credentials: Binary combination of EntityCredentials.{VIEW, CHANGE, LINK}.
                            Default value is EntityCredentials.LINK.
        """
        super(EntityCredsJSONField, self).__init__(*args, **kwargs)
        self._credentials = credentials

    def _check_entity_perms(self, entity, *args):
        user = self._user
        assert user is not None

        credentials = args[0] if args else self._credentials

        # We do not check permission if the initial related entity has not changed
        # (in order to allow the edition of an instance even if we do not have
        # the permissions for the already set related entity).
        initial = self.initial

        def get_initial_id():
            return initial.id if isinstance(initial, CremeEntity) else initial

        # NB: we compare ID to avoid problem with real/not real entities.
        if entity is not None and (not initial or (get_initial_id() != entity.id)):
            for cred, validator, validator_multi in self.CREDS_VALIDATORS:
                if credentials & cred:
                    validator(entity, user)

        return entity

    def _check_entities_perms(self, entities, *args):
        user = self._user
        assert user is not None

        credentials = args[0] if args else self._credentials

        for cred, validator, validator_multi in self.CREDS_VALIDATORS:
            if credentials & cred:
                validator_multi(entities, user)

        return entities


# class GenericEntityField(JSONField):
class GenericEntityField(EntityCredsJSONField):
    widget = core_widgets.CTEntitySelector
    # default_error_messages = {
    #     'ctypenotallowed': _(u'This content type is not allowed.'),
    #     'ctyperequired':   _(u'The content type is required.'),
    #     'doesnotexist':    _(u'This entity does not exist.'),
    #     'entityrequired':  _(u'The entity is required.'),
    # }
    value_type = dict

    def __init__(self, models=(), autocomplete=False, creator=True, user=None, *args, **kwargs):
        super(GenericEntityField, self).__init__(*args, **kwargs)
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
        if not hasattr(allowed, '__iter__'):
            warnings.warn("GenericEntityField.allowed_models property should take an iterable.",
                          DeprecationWarning
                         )
            allowed = ()

        self._allowed_models = list(allowed)
        self._update_widget_choices()

    # @property
    # def user(self):
    #     return self._user

    # @user.setter
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

    # def _update_wigets_choices(self):
    def _update_widget_choices(self):
        self.widget.content_types = fields.CallableChoiceIterator(self._get_ctypes_options)

    def _has_quickform(self, model):
        from creme.creme_core.gui import quickforms_registry
        return quickforms_registry.get_form(model) is not None

    def _create_url(self, user, ctype):
        model = ctype.model_class()

        if self._has_quickform(model) and user is not None and user.has_perm_to_create(model):
            # # return '/creme_core/quickforms/from_widget/%s/add/1' % ctype.pk
            # return '/creme_core/quickforms/from_widget/%s/add/' % ctype.pk
            return reverse('creme_core__quick_form', args=(ctype.pk,))

        return ''

    def _value_to_jsonifiable(self, value):
        if isinstance(value, CremeEntity):
            ctype_id = value.entity_type_id
            ctype = value.entity_type
            pk = value.id
        else:
            return value

        ctype_create_url = self._create_url(self.user, ctype)

        return {'ctype': {
                    'id': ctype_id,
                    'create': ctype_create_url,
                    'create_label': unicode(ctype.model_class().creation_label),
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
            warnings.warn('GenericEntityField: old format "ctype": id entry is deprecated.')
            ctype_pk = clean_value(data, 'ctype', int, required, 'ctyperequired')

        entity_pk = clean_value(data, 'entity', int, required, 'entityrequired')

        # return self._clean_entity(self._clean_ctype(ctype_pk), entity_pk)
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
        return ((json_dump({'id': ctype.pk,
                            'create': create_url(ctype),
                            'create_label': unicode(ctype.model_class().creation_label),
                           }),
                 unicode(ctype)
                ) for ctype in self.get_ctypes())

    def get_ctypes(self):
        models = self._allowed_models

        if models:
            get_ct = ContentType.objects.get_for_model

            return [get_ct(model) for model in models]

        return list(creme_entity_content_types())


# TODO: Add a q_filter, see utilization in EntityEmailForm
# TODO: propose to allow duplicates ???
class MultiGenericEntityField(GenericEntityField):
    widget = core_widgets.MultiCTEntitySelector
    value_type = list

    def __init__(self, models=(), autocomplete=False, unique=True, creator=True, user=None, *args, **kwargs):
        super(MultiGenericEntityField, self).__init__(models=models, autocomplete=autocomplete,
                                                      creator=creator, user=user,
                                                      *args, **kwargs
                                                     )
        self.unique = unique

    def widget_attrs(self, widget):
        return {}

    def _value_to_jsonifiable(self, value):
        return list(map(super(MultiGenericEntityField, self)._value_to_jsonifiable, value))

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
                warnings.warn('MultiGenericEntityField: old format "ctype": id entry is deprecated.')
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
        for ct_id, ctype_entity_pks in entities_by_ctype.iteritems():
            ctype_entities = self._clean_ctype(ct_id).model_class() \
                                                     .objects \
                                                     .filter(is_deleted=False) \
                                                     .in_bulk(ctype_entity_pks)

            if not all(pk in ctype_entities for pk in ctype_entity_pks):
                raise ValidationError(self.error_messages['doesnotexist'],
                                      code='doesnotexist',
                                     )

            entities_map.update(ctype_entities)

        if not entities_map:
            return self._return_list_or_raise(self.required)

        # return [entities_map[pk] for pk in entities_pks]
        return self._check_entities_perms([entities_map[pk] for pk in entities_pks])


class ChoiceModelIterator(object):
    def __init__(self, queryset, render_value=None, render_label=None):
        self.queryset = queryset.all()
        self.render_value = render_value or (lambda v: v.pk)
        self.render_label = render_label or (lambda v: unicode(v))

    def __iter__(self):
        for model in self.queryset:
            yield (self.render_value(model), self.render_label(model))

    def __len__(self):
        return len(self.queryset)


# class RelationEntityField(JSONField):
class RelationEntityField(EntityCredsJSONField):
    widget = core_widgets.RelationSelector
    default_error_messages = {
        'rtypedoesnotexist': _(u'This type of relationship does not exist.'),
        'rtypenotallowed':   _(u'This type of relationship causes a constraint error.'),
        # 'ctyperequired':     _(u'The content type is required.'),
        'ctypenotallowed':   _(u'This content type cause constraint error with the type of relationship.'),
        # 'entityrequired':    _(u'The entity is required.'),
        # 'doesnotexist':      _(u"This entity doesn't exist."),
        'nopropertymatch':   _(u'This entity has no property that matches the constraints of the type of relationship.'),
    }
    value_type = dict

    def __init__(self, allowed_rtypes=(REL_SUB_HAS, ), autocomplete=False, *args, **kwargs):
        super(RelationEntityField, self).__init__(*args, **kwargs)
        self.autocomplete = autocomplete
        self.allowed_rtypes = allowed_rtypes

    @property
    def allowed_rtypes(self):
        return self._allowed_rtypes

    @allowed_rtypes.setter
    def allowed_rtypes(self, allowed):
        rtypes = allowed if isinstance(allowed, QuerySet) else \
                 RelationType.objects.filter(id__in=allowed)
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

        return {'rtype': rtype.pk, 'ctype': entity.entity_type_id, 'entity': entity.pk} if entity else \
               {'rtype': rtype.pk, 'ctype': None,                  'entity': None}

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
            raise ValidationError(self.error_messages['ctypenotallowed'],
                                  params={'ctype': ctype_pk}, code='ctypenotallowed',
                                 )

    def _validate_properties_constraints(self, rtype, entity):
        ptype_ids = frozenset(rtype.object_properties.values_list('id', flat=True))

        if ptype_ids and not any(p.type_id in ptype_ids for p in entity.get_properties()):
            raise ValidationError(self.error_messages['nopropertymatch'],
                                  code='nopropertymatch',
                                 )

    def _clean_rtype(self, rtype_pk):
        # Is relation type allowed
        if rtype_pk not in self._get_allowed_rtypes_ids():
            raise ValidationError(self.error_messages['rtypenotallowed'],
                                  params={'rtype': rtype_pk}, code='rtypenotallowed',
                                 )

        try:
            return RelationType.objects.get(pk=rtype_pk)
        except RelationType.DoesNotExist:
            raise ValidationError(self.error_messages['rtypedoesnotexist'],
                                  params={'rtype': rtype_pk}, code='rtypedoesnotexist',
                                 )

    def _get_options(self):  # TODO: inline
        return ChoiceModelIterator(self._allowed_rtypes)

    def _get_allowed_rtypes_objects(self):
        return self._allowed_rtypes.all()

    def _get_allowed_rtypes_ids(self):
        return self._allowed_rtypes.values_list('id', flat=True)


class MultiRelationEntityField(RelationEntityField):
    widget = core_widgets.MultiRelationSelector
    value_type = list

    def _value_to_jsonifiable(self, value):
        return list(map(super(MultiRelationEntityField, self)._value_to_jsonifiable, value))

    def _build_rtype_cache(self, rtype_pk):
        try:
            rtype = RelationType.objects.get(pk=rtype_pk)
        except RelationType.DoesNotExist:
            raise ValidationError(self.error_messages['rtypedoesnotexist'],
                                  params={'rtype': rtype_pk}, code='rtypedoesnotexist',
                                 )

        rtype_allowed_ctypes     = frozenset(ct.pk for ct in rtype.object_ctypes.all())
        rtype_allowed_properties = frozenset(rtype.object_properties.values_list('id', flat=True))

        return rtype, rtype_allowed_ctypes, rtype_allowed_properties

    def _build_ctype_cache(self, ctype_pk):
        try:
            ctype = ContentType.objects.get_for_id(ctype_pk)
        except ContentType.DoesNotExist:
            raise ValidationError(self.error_messages['ctypedoesnotexist'],
                                  params={'ctype': ctype_pk}, code='ctypedoesnotexist',
                                 )

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

            ctype_pk =  clean_value(entry, 'ctype', int, required=False)
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
                raise ValidationError(self.error_messages['rtypenotallowed'],
                                      params={'rtype': rtype_pk,
                                              'ctype': ctype_pk,
                                             },
                                      code='rtypenotallowed',
                                     )

            rtype, rtype_allowed_ctypes, rtype_allowed_properties = \
                self._get_cache(rtypes_cache, rtype_pk, self._build_rtype_cache)

            if rtype_allowed_properties:
                need_property_validation = True

            # Check if content type is allowed by relation type
            if rtype_allowed_ctypes and ctype_pk not in rtype_allowed_ctypes:
                raise ValidationError(self.error_messages['ctypenotallowed'],
                                      params={'ctype':ctype_pk}, code='ctypenotallowed',
                                     )

            ctype, ctype_entity_pks = self._get_cache(ctypes_cache, ctype_pk,
                                                      self._build_ctype_cache,
                                                     )
            ctype_entity_pks.append(entity_pk)

        entities_cache = {}

        # Build real entity cache and check both entity id exists and in correct content type
        for ctype, entity_pks in ctypes_cache.values():
            ctype_entities = {entity.pk: entity
                                for entity in ctype.model_class()
                                                   .objects
                                                   .filter(is_deleted=False, pk__in=entity_pks)
                             }

            if not all(entity_pk in ctype_entities for entity_pk in entity_pks):
                raise ValidationError(self.error_messages['doesnotexist'],
                                      code='doesnotexist',
                                     )

            entities_cache.update(ctype_entities)

        self._check_entities_perms(entities_cache.values())

        relations = []

        # Build cache for validation of properties constraint between relationtypes and entities
        if need_property_validation:
            CremeEntity.populate_properties(entities_cache.values())

        for rtype_pk, ctype_pk, entity_pk in cleaned_entries:
            rtype, rtype_allowed_ctypes, rtype_allowed_properties = rtypes_cache.get(rtype_pk)
            entity = entities_cache.get(entity_pk)

            if rtype_allowed_properties and \
               not any(p.type_id in rtype_allowed_properties for p in entity.get_properties()):
                raise ValidationError(self.error_messages['nopropertymatch'],
                                      code='nopropertymatch',
                                     )

            relations.append((rtype, entity))

        if not relations:
            return self._return_list_or_raise(self.required)

        return relations


# class CreatorEntityField(JSONField):
class CreatorEntityField(EntityCredsJSONField):
    widget = core_widgets.EntityCreatorWidget  # The following attributes are set:
                                               # model, q_filter, creation_url, creation_allowed
    # default_error_messages = {
    #     'doesnotexist':    _(u"This entity doesn't exist."),
    #     'entityrequired':  _(u"The entity is required."),
    # }
    value_type = int

    def __init__(self, model=None, q_filter=None,
                 # create_action_url=None,
                 create_action_url='',
                 user=None, force_creation=False, *args, **kwargs
                ):
        super(CreatorEntityField, self).__init__(*args, **kwargs)
        widget = self.widget
        self._model = widget.model = model

        self._check_qfilter(q_filter)
        self._q_filter = widget.q_filter = q_filter

        self._create_action_url = widget.creation_url = create_action_url
        self._force_creation = force_creation
        self.user = user

    def _check_qfilter(self, q_filter):
        if isinstance(q_filter, Q):
            raise TypeError('<%s>: "Q" instance for q_filter is not (yet) supported (notice that it '
                            'can be generated from the "limit_choices_to" in a field related '
                            'to CremeEntity of one of your models).\n'
                            ' -> Use a dict (or a callable which returns a dict)' %
                                self.__class__.__name__
                           )

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
        @param q_filter: Allow to filter the selection ; it's a dictionary (eg: {'user__is_staff': False})
                         or a callable which returns a dictionary. 'None' means not filtering.
        """
        self._check_qfilter(q_filter)

        self.widget.q_filter = self._q_filter = q_filter
        self._update_creation_info()

    @property
    def q_filter_query(self):
        q_filter = self._q_filter
        # try:
        #     return get_q_from_dict(q_filter) if q_filter is not None else None
        # except:
        #     raise ValueError('Invalid q_filter %s' % q_filter)
        q = None

        if q_filter is not None:
            if callable(q_filter):
                q_filter = q_filter()
                self._check_qfilter(q_filter)

            try:
                q = get_q_from_dict(q_filter)
            except:
                raise ValueError('Invalid q_filter %s' % q_filter)

        return q

    @property
    def create_action_url(self):
        # if self._create_action_url is not None:
        if self._create_action_url:
            return self._create_action_url

        model = self._model

        # return None if model is None else (
        #        # '/creme_core/quickforms/from_widget/%s/add/1' %
        #        '/creme_core/quickforms/from_widget/%s/add/' %
        #             ContentType.objects.get_for_model(model).id)
        if model is not None and self._has_quickform(model):
            # return '/creme_core/quickforms/from_widget/{}/add/'.format(
            #     ContentType.objects.get_for_model(model).id
            # )
            return reverse('creme_core__quick_form',
                           args=(ContentType.objects.get_for_model(model).id,),
                          )

        return ''

    @create_action_url.setter
    def create_action_url(self, url):
        self._create_action_url = url

        self._update_creation_info()

    # @property
    # def user(self):
    #     return self._user

    # @user.setter
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
            # widget.creation_url = self.create_action_url \
            #                       if self._has_quickform(model) and (
            #                           not self._q_filter or self._force_creation) \
            #                       else ''
            widget.creation_url = self.create_action_url \
                                  if not self._q_filter or self._force_creation \
                                  else ''
        else:
            widget.creation_allowed = False
            widget.creation_url = ''

    def _has_quickform(self, model):
        from creme.creme_core.gui import quickforms_registry
        return quickforms_registry.get_form(model) is not None

    def _value_to_jsonifiable(self, value):
        if isinstance(value, (int, long)):
            if not self._entity_queryset(self.model, self.q_filter_query).filter(pk=value).exists():
                raise ValueError('No such entity with id %d.' % value)

            return value

        assert isinstance(value, CremeEntity)
        return value.id

    def _value_from_unjsonfied(self, data):
        model = self.model

        if model is None:
            if self.required:
                raise ValidationError(self.error_messages['required'], code='required')

            return None

        # return self._clean_entity_from_model(model, data, self.q_filter_query)
        entity = self._clean_entity_from_model(model, data, self.q_filter_query)

        return self._check_entity_perms(entity)


class MultiCreatorEntityField(CreatorEntityField):
    widget = core_widgets.MultiEntityCreatorWidget  # See CreatorEntityField.widget comment
    value_type = list

    def _value_to_jsonifiable(self, value):
        if not value:
            return []

        if value and isinstance(value[0], (int, long)):
            if self._entity_queryset(self.model, self.q_filter_query).filter(pk__in=value).count() < len(value):
                raise ValueError("One or more entities with ids [%s] doesn't exists." %
                                    ', '.join(str(v) for v in value)
                                )

            return value

        return list(map(super(MultiCreatorEntityField, self)._value_to_jsonifiable, value))

    def _value_from_unjsonfied(self, data):
        entities = []
        model = self.model

        if model is not None:
            clean_entity = partial(self._clean_entity_from_model,
                                   model=model, qfilter=self.q_filter_query,
                                  )

            for entry in data:
                if not isinstance(entry, int):
                    raise ValidationError(self.error_messages['invalidtype'], code='invalidtype')

                entity = clean_entity(entity_pk=entry)

                if entity is None:
                    raise ValidationError(self.error_messages['doesnotexist'], code='doesnotexist')

                entities.append(entity)
        elif self.required:
            raise ValidationError(self.error_messages['required'], code='required')

        # return entities
        return self._check_entities_perms(entities)


class FilteredEntityTypeField(JSONField):
    widget = core_widgets.FilteredEntityTypeWidget
    default_error_messages = {
        # 'ctyperequired':   _(u'The content type is required.'),
        # 'ctypenotallowed': _(u'This content type is not allowed.'),
        'invalidefilter':  _(u'This filter is invalid.'),
    }
    value_type = dict

    # def __init__(self, ctypes=creme_entity_content_types, empty_label=None, user=None, *args, **kwargs):
    def __init__(self, ctypes=creme_entity_content_types, empty_label=None, *args, **kwargs):
        """Constructor.
        @param ctypes Allowed types.
                        - A callable which returns an iterable of ContentType IDs / instances.
                        - Sequence of ContentType IDs / instances.
        """
        # self.user = user
        super(FilteredEntityTypeField, self).__init__(*args, **kwargs)
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
        return [ct_or_ctid if isinstance(ct_or_ctid, ContentType) else get_ct(ct_or_ctid)
                    for ct_or_ctid in self._ctypes()
               ]

    @ctypes.setter
    def ctypes(self, ctypes):
        "See constructor."
        if not callable(ctypes):
            ctypes_list = list(ctypes)  # We copy the sequence to avoid external modifications
            ctypes = lambda: ctypes_list

        self._ctypes = ctypes
        self.widget.content_types = fields.CallableChoiceIterator(self._get_choices)

    def _get_choices(self):
        choices = []

        if self._empty_label is not None:
            # TODO: improve widget to do not make a request for '0' (same comment in widget)
            choices.append((0, unicode(self._empty_label)))

        choices.extend(build_ct_choices(self.ctypes))

        return choices

    def _value_from_unjsonfied(self, data):
        clean_value = self.clean_value
        ctype_pk = clean_value(data, 'ctype', int, required=False)

        if not ctype_pk:
            if self.required:
                raise ValidationError(self.error_messages['ctyperequired'],
                                      code='ctyperequired',
                                     )

            return self._build_empty_value()

        ct = self._clean_ctype(ctype_pk)
        if ct is None:
            raise ValidationError(self.error_messages['ctypenotallowed'],
                                  code='ctypenotallowed',
                                 )

        efilter_pk = clean_value(data, 'efilter',  str, required=False)
        if not efilter_pk:  # TODO: self.filter_required ???
            efilter = None
        else:
            try:
                # if self.user:
                #     efilter = EntityFilter.get_for_user(self.user, ct) \
                #                           .get(pk=efilter_pk)
                # else:
                #     warnings.warn("FilteredEntityTypeField.clean(): 'user' attribute has not been set (so privacy cannot be checked)",
                #                   DeprecationWarning
                #                  )
                #
                #     efilter = EntityFilter.objects.get(entity_type=ct, pk=efilter_pk)
                efilter = EntityFilter.get_for_user(self._user, ct).get(pk=efilter_pk)
            except EntityFilter.DoesNotExist:
                raise ValidationError(self.error_messages['invalidefilter'],
                                      code='invalidefilter',
                                     )

        return ct, efilter

    def _value_to_jsonifiable(self, value):
        return {'ctype': value[0], 'efilter': value[1]}


class OptionalField(fields.MultiValueField):
    sub_field = fields.Field
    widget = core_widgets.OptionalWidget

    default_error_messages = {
        'subfield_required': _(u'Enter a value if you check the box.'),
    }

    def __init__(self, widget=None, label=None, initial=None, help_text='', sub_label='', *args, **kwargs):
        super(OptionalField, self).__init__(fields=(fields.BooleanField(required=False),
                                                    self._build_subfield(*args, **kwargs),
                                                   ),
                                            required=False,
                                            require_all_fields=False,
                                            widget=widget, label=label, initial=initial, help_text=help_text,
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

        use_value, sub_value = super(OptionalField, self).clean(value)

        if sub_required:
            sub_field.required = True

            if use_value:
                try:
                    sub_field_value = value[1]
                except IndexError:
                    sub_field_value = None

                if sub_field_value in self.empty_values:
                    raise ValidationError(self.error_messages['subfield_required'], code='subfield_required')

        if not use_value:
            sub_value = None

        return use_value, sub_value


class OptionalChoiceField(OptionalField):
    sub_field = fields.ChoiceField
    widget = core_widgets.OptionalSelect


class OptionalModelChoiceField(OptionalChoiceField):
    sub_field = ModelChoiceField


class ListEditionField(fields.Field):
    """A field to allow the user to edit/delete a list of strings.
    It returns a list with the same order:
    * deleted elements are replaced by None.
    * modified elements are replaced by the new value.
    """
    widget = core_widgets.ListEditionWidget
    default_error_messages = {}

    def __init__(self, content=(), only_delete=False, *args, **kwargs):
        """
        @param content Sequence of strings
        @param only_delete Can only delete elements, not edit them.
        """
        super(ListEditionField, self).__init__(*args, **kwargs)
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


class AjaxChoiceField(fields.ChoiceField):
    """
        Same as ChoiceField but bypass the choices validation due to the ajax filling
    """
    def clean(self, value):
        """
        Validates that the input is in self.choices.
        """
#        value = super(ChoiceField, self).clean(value)
        if value in self.empty_values:
            if self.required:
                raise ValidationError(self.error_messages['required'], code='required')

            value = u''

        return smart_unicode(value)


class AjaxMultipleChoiceField(fields.MultipleChoiceField):
    """
        Same as MultipleChoiceField but bypass the choices validation due to the ajax filling
    """
    def clean(self, value):
        """
        Validates that the input is a list or tuple.
        """
        not_value = not value
        if self.required and not_value:
            raise ValidationError(self.error_messages['required'], code='required')
        elif not self.required and not_value:
            return []

        if not isinstance(value, (list, tuple)):
            raise ValidationError(self.error_messages['invalid_list'],
                                  code='invalid_list',
                                 )

        return [smart_unicode(val) for val in value]


class AjaxModelChoiceField(ModelChoiceField):
    """
        Same as ModelChoiceField but bypass the choices validation due to the ajax filling
    """
    def clean(self, value):
#        Field.clean(self, value)

        # if value in fields.EMPTY_VALUES:
        if value in self.empty_values:
            return None

        try:
            key   = self.to_field_name or 'pk'
            value = self.queryset.model._default_manager.get(**{key: value})
        except self.queryset.model.DoesNotExist:
            raise ValidationError(self.error_messages['invalid_choice'],
                                  code='invalid_choice',
                                 )

        return value


class CremeTimeField(fields.TimeField):
    widget = core_widgets.TimeWidget

    def __init__(self, *args, **kwargs):
        super(CremeTimeField, self).__init__(*args, **kwargs)
        warnings.warn("CremeTimeField is deprecated ; use django TimeField instead or nothing at all.",
                      DeprecationWarning
                     )


class CremeDateField(fields.DateField):
    widget = core_widgets.CalendarWidget

    def __init__(self, *args, **kwargs):
        super(CremeDateField, self).__init__(*args, **kwargs)
        warnings.warn("CremeDateField is deprecated ; use django DateField instead or nothing at all.",
                      DeprecationWarning
                     )


class CremeDateTimeField(fields.DateTimeField):
    widget = core_widgets.CalendarWidget

    def __init__(self, *args, **kwargs):
        super(CremeDateTimeField, self).__init__(*args, **kwargs)
        warnings.warn("CremeDateTimeField is deprecated ; use django DateTimeField instead or nothing at all.",
                      DeprecationWarning
                     )


class MultiEmailField(fields.Field):
    # Original code at http://docs.djangoproject.com/en/1.3/ref/forms/validation/#form-field-default-cleaning
    widget = widgets.Textarea

    def __init__(self, sep="\n", *args, **kwargs):
        super(MultiEmailField, self).__init__(*args, **kwargs)
        self.sep = sep

    def to_python(self, value):
        "Normalize data to a list of strings."

        # Return an empty list if no input was given.
        if not value:
            return []
        return [v for v in value.split(self.sep) if v]  # Remove empty values but the validation is more flexible

    def validate(self, value):
        "Check if value consists only of valid emails."

        # Use the parent's handling of required fields, etc.
        super(MultiEmailField, self).validate(value)

        for email in value:
            validate_email(email)


class DatePeriodField(fields.MultiValueField):
    widget = core_widgets.DatePeriodWidget

    # def __init__(self, *args, **kwargs):
    #     choices = kwargs.pop('choices', None)
    def __init__(self, period_registry=date_period_registry, period_names=None, *args, **kwargs):
        """Constructor.
        @param period_registry: see property 'period_registry'.
        @param period_names: see property 'period_names'.
        """
        try:
            period_names = kwargs.pop('choices')
        except KeyError:
            pass
        else:
            warnings.warn('DatePeriodField.__init__(): "choices" argument is deprecated ; '
                          'use "period_names"  instead (same type).',
                          DeprecationWarning
                         )

        super(DatePeriodField, self).__init__((fields.ChoiceField(), fields.IntegerField(min_value=1)),
                                              *args, **kwargs
                                             )

        # self.fields[0].choices = self.widget.choices = list(date_period_registry.choices(choices=choices))
        self._period_registry = period_registry
        self.period_names = period_names

    def _update_choices(self):
        self.fields[0].choices = self.widget.choices = list(self._period_registry.choices(choices=self._period_names))

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
        return (data_list[0], data_list[1]) if data_list else (u'', u'')

    def clean(self, value):
        period_name, period_value = super(DatePeriodField, self).clean(value)

        if not period_value:
            return None

        return date_period_registry.get_period(period_name, period_value)


class DateRangeField(fields.MultiValueField):
    """A field which returns a creme_core.utils.DateRange.
    Commonly used with a DateRangeWidget.
    eg:
        # Use DateRangeWidget with defaults params
        DateRangeField(label=_(u'Date range'))

        #Render DateRangeWidget as ul/li
        DateRangeField(label=_(u'Date range'), widget=DateRangeWidget(attrs={'render_as': 'ul'}))

        #Render DateRangeWidget as a table
        DateRangeField(label=_(u'Date range'), widget=DateRangeWidget(attrs={'render_as': 'table'}))
    """
    widget = core_widgets.DateRangeWidget
    default_error_messages = {
        'customized_empty': _(u'If you select «customized» you have to specify a start date and/or an end date.'),
        'customized_invalid': _(u'Start date has to be before end date.'),
    }

    def __init__(self, render_as="table", *args, **kwargs):
        # TODO: are these attributes useful ??
        self.ranges = ranges = fields.ChoiceField(
                required=False,
                choices=lambda: chain([(u'', pgettext_lazy('creme_core-date_range', u'Customized'))],
                                      date_range_registry.choices(),
                                     )
            )
        self.start_date = fields.DateField(required=False)
        self.end_date   = fields.DateField(required=False)
        self.render_as  = render_as

        super(DateRangeField, self).__init__(fields=(ranges,
                                                     self.start_date,
                                                     self.end_date,
                                                    ),
                                             require_all_fields=False, *args, **kwargs
                                            )

        self.widget.choices = ranges.widget.choices  # Get the CallableChoiceIterator

    def compress(self, data_list):
        return (data_list[0], data_list[1], data_list[2]) if data_list else (u'', u'', u'')

    def clean(self, value):
        range_name, start, end = super(DateRangeField, self).clean(value)

        if range_name == '':
            if not start and not end and self.required:
                raise ValidationError(self.error_messages['customized_empty'],
                                      code='customized_empty',
                                     )

            if start and end and start > end:
                raise ValidationError(self.error_messages['customized_invalid'],
                                      code='customized_invalid',
                                     )

        return date_range_registry.get_range(range_name, start, end)

    def widget_attrs(self, widget):
        return {'render_as': self.render_as}


# class ColorField(RegexField):
class ColorField(fields.CharField):
    """A Field which handles HTML colors (e.g: #F2FAB3) without '#' """
    # regex  = compile_re(r'^([0-9a-fA-F]){6}$')
    default_validators = [validators.validate_color]
    widget = core_widgets.ColorPickerWidget
    default_error_messages = {
        'invalid': _(u'Enter a valid value (eg: DF8177).'),
    }

    def __init__(self, *args, **kwargs):
        # super(ColorField, self).__init__(self.regex, max_length=6, min_length=6, *args, **kwargs)
        super(ColorField, self).__init__(max_length=6, min_length=6, *args, **kwargs)

    def clean(self, value):
        return super(ColorField, self).clean(value).upper()


class DurationField(fields.MultiValueField):
    widget = core_widgets.DurationWidget
    default_error_messages = {
        'invalid': _(u'Enter a whole number.'),
        'min_value': _(u'Ensure this value is greater than or equal to %(limit_value)s.'),
    }

    def __init__(self, *args, **kwargs):
        IntegerField = fields.IntegerField
        self.hours   = IntegerField(min_value=0)
        self.minutes = IntegerField(min_value=0)
        self.seconds = IntegerField(min_value=0)

        super(DurationField, self).__init__(fields=(self.hours, self.minutes, self.seconds), *args, **kwargs)

    def compress(self, data_list):
        return (data_list[0], data_list[1], data_list[2]) if data_list else (u'', u'', u'')

    def clean(self, value):
        hours, minutes, seconds = super(DurationField, self).clean(value)
        return ':'.join([str(hours or 0), str(minutes or 0), str(seconds or 0)])


class ChoiceOrCharField(fields.MultiValueField):
    widget = core_widgets.ChoiceOrCharWidget

    default_error_messages = {
        'invalid_other': _(u'Enter a value for "Other" choice.'),
    }

    def __init__(self, choices=(), *args, **kwargs):
        """@param choices Sequence of tuples (id, value).
                          BEWARE: id should not be a null value (like '', 0, etc..).
        """
        self.choice_field = choice_field = fields.ChoiceField()
        super(ChoiceOrCharField, self).__init__(fields=(choice_field, fields.CharField(required=False)),
                                                require_all_fields=False,
                                                *args, **kwargs
                                               )
        self.choices = choices

    @property
    def choices(self):
        return self._choices

    @choices.setter
    def choices(self, value):
        """See ChoiceField._set_choices()"""
        choices = [(0, _('Other'))]
        choices.extend(value)
        self._choices = self.choice_field.choices = self.widget.choices = choices

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
        value = super(ChoiceOrCharField, self).clean(value)

        if value[0] == 0 and not value[1]:
            raise ValidationError(self.error_messages['invalid_other'],
                                  code='invalid_other',
                                 )

        return value


class CTypeChoiceField(fields.Field):
    "A ChoiceField whose choices are a ContentType instances."
    widget = widgets.Select
    default_error_messages = {
        'invalid_choice': _(u'Select a valid choice. That choice is not one of'
                            u' the available choices.'),
    }

    # TODO: ctypes_or_models ??
    def __init__(self, ctypes=(), empty_label=u'---------',
                 required=True, widget=None, label=None, initial=None,
                 help_text=None,
                 to_field_name=None, limit_choices_to=None,  # TODO: manage ?
                 *args, **kwargs):
        "@param ctypes: A sequence of ContentTypes or a callable which returns one."
        super(CTypeChoiceField, self).__init__(required, widget, label, initial, help_text,
                                               *args, **kwargs
                                              )
        self.empty_label = empty_label
        self.ctypes = ctypes

    def __deepcopy__(self, memo):
        result = super(CTypeChoiceField, self).__deepcopy__(memo)
        result._ctypes = deepcopy(self._ctypes, memo)
        return result

    @property
    def ctypes(self):
        return self._ctypes()

    @ctypes.setter
    def ctypes(self, ctypes):
        if not callable(ctypes):
            ctypes_list = list(ctypes)
            ctypes = lambda: ctypes_list

        self._ctypes = ctypes
        self.widget.choices = fields.CallableChoiceIterator(
                lambda: self._build_empty_choice(self._build_ctype_choices(self.ctypes))
            )

    def _build_empty_choice(self, choices):
        if not self.required:
            return [('', self.empty_label)] + choices

        return choices

    def _build_ctype_choices(self, ctypes):
        return build_ct_choices(ctypes)

    def to_python(self, value):
        # if value in fields.EMPTY_VALUES:
        if value in self.empty_values:
            return None

        try:
            ct_id = int(value)

            for ctype in self.ctypes:
                if ctype.id == ct_id:
                    return ctype
        except ValueError:
            pass

        raise ValidationError(self.error_messages['invalid_choice'],
                              code='invalid_choice',
                             )


class MultiCTypeChoiceField(CTypeChoiceField):
    widget = core_widgets.UnorderedMultipleChoiceWidget  # Beware: use Choice inner class

    def _build_ctype_choices(self, ctypes):
        from ..utils.unicode_collation import collator
        # from ..registry import creme_registry

        Choice = self.widget.Choice
        # get_app = creme_registry.get_app
        get_app_conf = apps.get_app_config

        # choices = [(Choice(ct.id, help=_(get_app(ct.app_label).verbose_name)),
        choices = [(Choice(ct.id, help=get_app_conf(ct.app_label).verbose_name),
                    unicode(ct),
                   ) for ct in ctypes
                  ]
        sort_key = collator.sort_key
        choices.sort(key=lambda k: sort_key(k[1]))

        return choices

    def _build_empty_choice(self, choices):
        return choices

    def to_python(self, value):
        ctypes = []

        # if value not in fields.EMPTY_VALUES:
        if value not in self.empty_values:
            to_python = super(MultiCTypeChoiceField, self).to_python
            ctypes.extend(to_python(ct_id) for ct_id in value)

        return ctypes


class EntityCTypeChoiceField(CTypeChoiceField):
    def __init__(self, ctypes=None, *args, **kwargs):
        ctypes = ctypes or creme_entity_content_types
        super(EntityCTypeChoiceField, self).__init__(ctypes=ctypes, *args, **kwargs)


class MultiEntityCTypeChoiceField(MultiCTypeChoiceField):
    def __init__(self, ctypes=None, *args, **kwargs):
        ctypes = ctypes or creme_entity_content_types
        super(MultiEntityCTypeChoiceField, self).__init__(ctypes=ctypes, *args, **kwargs)
