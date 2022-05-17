# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from collections import defaultdict
from functools import partial

from django.core.exceptions import PermissionDenied
from django.db.models.query_utils import FilteredRelation, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_list_or_404, get_object_or_404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from .. import utils
from ..auth.decorators import login_required
from ..core.exceptions import ConflictError
from ..forms import relation as rel_forms
from ..models import CremeEntity, Relation, RelationType
from ..shortcuts import get_bulk_or_404
from ..utils.content_type import entity_ctypes
from .decorators import jsonify
from .generic import base
from .generic.delete import CremeModelDeletion
from .generic.listview import BaseEntitiesListPopup


def _fields_values(instances, getters, range, sort_getter=None, user=None):
    start, end = range
    result = []

    def values(i):
        return [getter(i, user) for getter in getters]

    if sort_getter:
        sorted_result = [
            (sort_getter(instance, user), values(instance))
            for instance in instances
        ]
        sorted_result.sort(key=lambda x: x[0])
        result.extend(e[1] for e in sorted_result[start:end])
    else:
        result.extend(values(instance) for instance in instances[start:end])

    return result


def _clean_getters_arg(field, allowed_fields):
    getter = allowed_fields.get(field)

    if not getter:
        raise PermissionDenied(f"Forbidden field '{field}'")

    return getter


def _clean_fields_values_args(data, allowed_fields):
    if not data:
        raise ValueError('Not such parameter')

    get = data.get
    range = [int(i) if i is not None else None for i in (get('start'), get('end'))]
    getters = [_clean_getters_arg(field, allowed_fields) for field in data.getlist('fields')]

    if not getters:
        raise ValueError(f'No such field (data={data})')

    sort_getter = get('sort')
    if sort_getter is not None:
        sort_getter = _clean_getters_arg(sort_getter, allowed_fields)

    return getters, range, sort_getter


JSON_ENTITY_FIELDS = {
    'unicode':     lambda e, user: e.allowed_str(user),
    'id':          lambda e, user: e.id,
    'entity_type': lambda e, user: e.entity_type_id,
    'summary':     lambda e, user: e.get_real_entity().get_entity_summary(user),
}


# TODO: move to entity.py (rename ?) & change also url
# TODO: factorise with entity.get_creme_entities_repr() ?
@login_required
@jsonify
def json_entity_get(request, entity_id):
    getters, range, sort = _clean_fields_values_args(request.GET, JSON_ENTITY_FIELDS)
    user = request.user
    instances = []
    entity = CremeEntity.objects.filter(pk=entity_id).first()

    if entity is not None and user.has_perm_to_view(entity):
        instances.append(entity)

    return _fields_values(instances, getters, (0, 1), sort, user)


JSON_CONTENT_TYPE_FIELDS = {
    'unicode': lambda e, user: str(e),
    'id':      lambda e, user: e.id
}


@login_required
@jsonify
def json_rtype_ctypes(request, rtype_id):
    content_types = get_object_or_404(RelationType, pk=rtype_id).object_ctypes.all()
    getters, range, sort = _clean_fields_values_args(request.GET, JSON_CONTENT_TYPE_FIELDS)

    if not content_types:
        content_types = [*entity_ctypes()]

    return _fields_values(content_types, getters, range, sort)


class RelationsAdding(base.RelatedToEntityFormPopup):
    form_class = rel_forms.RelationCreateForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title = _('Relationships for «{entity}»')
    submit_label = _('Save the relationships')
    entity_id_url_kwarg = 'subject_id'
    entity_form_kwarg = 'subject'
    rtype_id_url_kwarg = 'rtype_id'

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['relations_types'] = self.get_relation_types()

        return kwargs

    def get_relation_types(self):
        subject = self.get_related_entity()
        subject_ctype = subject.entity_type
        rtypes = None
        rtype_id = self.kwargs.get(self.rtype_id_url_kwarg)

        if rtype_id:
            rtype = get_object_or_404(RelationType, pk=rtype_id)
            rtype.is_not_internal_or_die()

            if not rtype.is_compatible(subject_ctype):
                raise ConflictError(
                    gettext(
                        'This type of relationship is not compatible with «{model}».'
                    ).format(model=subject_ctype)
                )

            # TODO: make a method in RelationType (improve is_compatible() ?)
            needed_property_types = [*rtype.subject_properties.all()]
            if needed_property_types:
                subjects_prop_ids = {*subject.properties.values_list('type', flat=True)}
                missing_ptypes = [
                    needed_ptype
                    for needed_ptype in needed_property_types
                    if needed_ptype.id not in subjects_prop_ids
                ]

                if missing_ptypes:
                    raise ConflictError(
                        ngettext(
                            'This type of relationship needs an entity with '
                            'this property: {properties}.',
                            'This type of relationship needs an entity with '
                            'these properties: {properties}.',
                            number=len(missing_ptypes)
                        ).format(
                            properties=', '.join(str(ptype) for ptype in missing_ptypes),
                        )
                    )

            rtypes = [rtype_id]

        request = self.request

        if request.method == 'GET' and rtype_id is None:
            excluded_rtype_ids = request.GET.getlist('exclude')

            if excluded_rtype_ids:
                # Theses type are excluded to provide a better GUI, but they
                # cannot cause business conflict (internal rtypes are always excluded),
                # so it's not a problem to only excluded them only in GET part.
                rtypes = RelationType.objects\
                                     .compatible(subject_ctype) \
                                     .exclude(id__in=excluded_rtype_ids)

        return rtypes


# TODO: Factorise with add_properties_bulk and bulk_update?
class RelationsBulkAdding(base.EntityCTypeRelatedMixin, base.CremeFormPopup):
    template_name = 'creme_core/generics/blockform/link-popup.html'
    form_class = rel_forms.MultiEntitiesRelationCreateForm
    title = _('Multiple adding of relationships')
    submit_label = _('Save the relationships')

    def filter_entities(self, entities):
        filtered = {True: [], False: []}
        has_perm = self.request.user.has_perm_to_link

        for entity in entities:
            filtered[has_perm(entity)].append(entity)

        return filtered

    def get_entities(self, model):
        request = self.request
        # TODO: rename 'ids' -> 'entity/id' ?
        entities = get_list_or_404(
            model,
            pk__in=(
                request.POST.getlist('ids')
                if request.method == 'POST' else
                request.GET.getlist('ids')
            ),
        )

        CremeEntity.populate_real_entities(entities)

        return entities

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        filtered = self.filter_entities(self.get_entities(model=self.get_ctype().model_class()))
        kwargs['subjects'] = filtered[True]
        kwargs['forbidden_subjects'] = filtered[False]

        request = self.request
        kwargs['relations_types'] = (
            request.GET.getlist('rtype') if request.method == 'GET' else None
        )

        return kwargs


class RelationDeletion(CremeModelDeletion):
    model = Relation

    def check_instance_permissions(self, instance, user):
        subject = instance.subject_entity

        has_perm = user.has_perm_to_unlink_or_die
        has_perm(subject)
        has_perm(instance.object_entity)
        instance.type.is_not_internal_or_die()

    def get_success_url(self):
        # TODO: callback_url?
        return self.object.subject_entity.get_real_entity().get_absolute_url()


class RelationFromFieldsDeletion(CremeModelDeletion):
    "Delete a Relation which we retrieve from the subject/object/type."
    model = Relation

    subject_id_arg = 'subject_id'
    object_id_arg = 'object_id'
    rtype_id_arg = 'type'

    def check_subject_permissions(self, subject, user):
        user.has_perm_to_unlink_or_die(subject)

    def check_object_permissions(self, object, user):
        user.has_perm_to_unlink_or_die(object)

    def check_rtype_permissions(self, rtype, user):
        rtype.is_not_internal_or_die()

    def get_entities(self):
        request = self.request
        get = partial(utils.get_from_POST_or_404, request.POST, cast=int)
        subject_id = get(self.subject_id_arg)
        object_id  = get(self.object_id_arg)
        entities_per_id = get_bulk_or_404(CremeEntity, [subject_id, object_id])
        user = request.user

        subject = entities_per_id[subject_id]
        self.check_subject_permissions(subject=subject, user=user)

        object = entities_per_id[object_id]
        self.check_object_permissions(object=object, user=user)

        return {
            'subject_entity': subject,
            'object_entity': object,
        }

    def get_rtype(self):
        rtype = get_object_or_404(
            RelationType,
            id=utils.get_from_POST_or_404(self.request.POST, self.rtype_id_arg),
        )
        self.check_rtype_permissions(rtype=rtype, user=self.request.user)

        return rtype

    def get_query_kwargs(self):
        kwargs = self.get_entities()
        kwargs['type'] = self.get_rtype()

        return kwargs

    # TODO ?
    # def get_success_url(self):
    #     return self.object.subject_entity.get_real_entity().get_absolute_url()


class RelationsObjectsSelectionPopup(base.EntityRelatedMixin,
                                     base.EntityCTypeRelatedMixin,
                                     BaseEntitiesListPopup):
    """Display an inner popup to select entities to link as relations' objects
    for a given subject entity.

    New GET parameters:
     - 'rtype_id':     RelationType ID of the future relations. Required.
     - 'subject_id':   ID of the entity used as subject for relations. Integer. Required.
     - 'object_ct_id': ID of the ContentType of the future relations' objects. Integer. Required.

    Tip: use the JS function creme.relations.AddRelationToAction().
    """
    subject_id_arg    = 'subject_id'
    rtype_id_arg      = 'rtype_id'
    objects_ct_id_arg = 'objects_ct_id'

    def get_ctype_id(self):
        return utils.get_from_GET_or_404(self.request.GET, self.objects_ct_id_arg)

    @property
    def model(self):
        return self.get_ctype().model_class()

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)

    def get_related_entity_id(self):
        return utils.get_from_GET_or_404(self.request.GET, self.subject_id_arg, cast=int)

    def get_rtype(self):
        rtype = get_object_or_404(
            RelationType,
            pk=utils.get_from_GET_or_404(self.request.GET, key=self.rtype_id_arg),
        )
        rtype.is_not_internal_or_die()

        return rtype

    def get_internal_q(self):
        rtype = self.get_rtype()

        # TODO: filter with relation creds too ?
        # NB: list() because the serialization of sub-QuerySet does not work with the JSON session
        # extra_q = ~Q(
        #     pk__in=list(CremeEntity.objects
        #                            .filter(relations__type=rtype.symmetric_type_id,
        #                                    relations__object_entity=self.get_related_entity().id,
        #                                   )
        #                            .values_list('id', flat=True)
        #                ),
        # )
        extra_q = ~Q(
            pk__in=[
                *CremeEntity.objects.annotate(
                    relations_w_entity=FilteredRelation(
                        'relations',
                        condition=Q(relations__object_entity=self.get_related_entity().id),
                    )
                ).filter(
                    relations_w_entity__type=rtype.symmetric_type_id,
                ).values_list('id', flat=True)
            ],
        )

        prop_types = [*rtype.object_properties.values_list('id', flat=True)]
        if prop_types:
            extra_q &= Q(properties__type__in=prop_types)

        return extra_q


@login_required
def add_relations_with_same_type(request):
    """Allow to create from a POST request several relations with the same
    relation type, between a subject and several other entities.
    Tip: see the JS class 'creme.relations.AddRelationToAction()'.
    """
    user = request.user
    POST = request.POST
    subject_id = utils.get_from_POST_or_404(POST, 'subject_id', int)
    rtype_id   = utils.get_from_POST_or_404(POST, 'predicate_id')  # TODO: rename POST arg

    # TODO: rename 'object_ids' ?
    # entity_ids = POST.getlist('entities')
    try:
        entity_ids = {int(e_id) for e_id in POST.getlist('entities')}
    except ValueError:
        raise Http404('An ID in the argument "entities" is not an integer.')

    if not entity_ids:
        raise Http404('Void "entities" parameter.')

    if subject_id in entity_ids:
        # TODO: gettext ?
        raise ConflictError('You cannot link an entity with itself.')

    rtype = get_object_or_404(RelationType, pk=rtype_id)
    rtype.is_not_internal_or_die()

    # entity_ids.append(subject_id)
    entity_ids.add(subject_id)  # NB: so we can do only one query
    entities = [*CremeEntity.objects.filter(pk__in=entity_ids)]

    needed_subject_pt_ids = rtype.subject_properties.values_list('id', flat=True)
    needed_object_pt_ids  = rtype.object_properties.values_list('id', flat=True)

    if needed_subject_pt_ids or needed_object_pt_ids:
        # Optimise the get_properties() (but it retrieves CremePropertyType objects too)
        CremeEntity.populate_properties(entities)

    for i, entity in enumerate(entities):
        if entity.id == subject_id:
            subject = entity
            entities.pop(i)
            break
    else:
        raise Http404(f'Can not find entity with id={subject_id}')

    user.has_perm_to_link_or_die(subject)

    errors = defaultdict(list)
    len_diff = len(entity_ids) - len(entities)

    # 'subject' has been pop from entities, but not subject_id from entity_ids, so 1 and not 0
    if len_diff != 1:
        errors[404].append(
            ngettext(
                "{count} entity doesn't exist or has been removed.",
                "{count} entities don't exist or have been removed.",
                len_diff
            ).format(count=len_diff),
        )

    # TODO: improve RelationType.is_compatible()
    subject_ct_ids = rtype.subject_ctypes.values_list('id', flat=True)
    if subject_ct_ids and subject.entity_type_id not in subject_ct_ids:
        raise ConflictError('Incompatible type for subject')

    if needed_subject_pt_ids:
        subject_pt_ids = {p.type_id for p in subject.get_properties()}

        if any(
            needed_ptype_id not in subject_pt_ids
            for needed_ptype_id in needed_subject_pt_ids
        ):
            raise ConflictError('Missing compatible property for subject')

    # TODO: idem
    object_ct_ids = frozenset(rtype.object_ctypes.values_list('id', flat=True))
    check_ctype = (
        (lambda e: e.entity_type_id in object_ct_ids)
        if object_ct_ids else
        (lambda e: True)
    )

    def check_properties(entity):
        if not needed_object_pt_ids:
            return True

        object_pt_ids = {p.type_id for p in entity.get_properties()}

        return all(
            needed_ptype_id in object_pt_ids
            for needed_ptype_id in needed_object_pt_ids
        )

    create_relation = Relation.objects.safe_create
    for entity in entities:
        if not check_ctype(entity):
            errors[409].append(
                gettext(
                    'Incompatible type for object entity with id={}'
                ).format(entity.id)
            )
        elif not check_properties(entity):
            errors[409].append(
                gettext(
                    'Missing compatible property for object entity with id={}'
                ).format(entity.id)
            )
        elif not user.has_perm_to_link(entity):
            errors[403].append(
                gettext(
                    'Permission denied to entity with id={}'
                ).format(entity.id))
        else:
            create_relation(
                subject_entity=subject, type=rtype, object_entity=entity, user=user,
            )

    if not errors:
        status = 200
        message = gettext('Operation successfully completed')
    else:
        status = min(errors)
        message = ','.join(
            msg
            for error_messages in errors.values()
            for msg in error_messages
        )

    return HttpResponse(message, status=status)
