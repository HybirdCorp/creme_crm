# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
# import warnings

from django.core.exceptions import PermissionDenied
from django.db.models.query_utils import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, get_list_or_404, redirect
from django.utils.translation import ugettext as _, ungettext

from .. import utils
from ..auth.decorators import login_required
from ..core.exceptions import ConflictError
from ..forms.relation import RelationCreateForm, MultiEntitiesRelationCreateForm
from ..models import Relation, RelationType, CremeEntity

from .generic import inner_popup, listview


def _fields_values(instances, getters, range, sort_getter=None, user=None):
    start, end = range
    result = []

    def values(i):
        return [getter(i, user) for getter in getters]

    if sort_getter:
        sorted_result = [(sort_getter(instance, user), values(instance)) for instance in instances]
        sorted_result.sort(key=lambda x: x[0])
        result.extend(e[1] for e in sorted_result[start:end])
    else:
        result.extend(values(instance) for instance in instances[start:end])

    return result


def _clean_getters_arg(field, allowed_fields):
    getter = allowed_fields.get(field)

    if not getter:
        raise PermissionDenied("Forbidden field '{}'".format(field))

    return getter


def _clean_fields_values_args(data, allowed_fields):
    if not data:
        raise ValueError('Not such parameter')

    get = data.get
    range = [int(i) if i is not None else None for i in (get('start'), get('end'))]
    getters = [_clean_getters_arg(field, allowed_fields) for field in data.getlist('fields')]

    if not getters:
        raise ValueError(u'No such field (data={})'.format(data))

    sort_getter = get('sort')
    if sort_getter is not None:
        sort_getter = _clean_getters_arg(sort_getter, allowed_fields)

    return getters, range, sort_getter


JSON_ENTITY_FIELDS = {
    'unicode':     lambda e, user: e.allowed_unicode(user),
    'id':          lambda e, user: e.id,
    'entity_type': lambda e, user: e.entity_type_id,
    'summary':     lambda e, user: e.get_real_entity().get_entity_summary(user),
}


# TODO: move to entity.py (rename ?) & change also url
# TODO: factorise with entity.get_creme_entities_repr() ?
@login_required
@utils.jsonify
def json_entity_get(request, entity_id):
    getters, range, sort = _clean_fields_values_args(request.GET, JSON_ENTITY_FIELDS)
    user = request.user
    instances = []
    entity = CremeEntity.objects.filter(pk=entity_id).first()

    if entity is not None and user.has_perm_to_view(entity):
        instances.append(entity)

    return _fields_values(instances, getters, (0, 1), sort, user)


JSON_PREDICATE_FIELDS = {
    'unicode': lambda e, user: str(e),
    'id':      lambda e, user: e.id,
}


@login_required
@utils.jsonify
def json_entity_rtypes(request, entity_id):  # TODO: seems unused
    entity = get_object_or_404(CremeEntity, pk=entity_id)
    request.user.has_perm_to_view_or_die(entity)

    # TODO: use CremePropertyType constraints too
    rtypes = RelationType.objects.filter(is_internal=False) \
                                 .filter(Q(subject_ctypes=entity.entity_type) |
                                         Q(subject_ctypes__isnull=True)
                                        ) \
                                 .order_by('predicate') \
                                 .distinct()  # TODO: distinct useful ??

    # TODO: use unicode collation ?

    return _fields_values(rtypes, *_clean_fields_values_args(request.GET, JSON_PREDICATE_FIELDS))


JSON_CONTENT_TYPE_FIELDS = {
    'unicode': lambda e, user: str(e),
    'id':      lambda e, user: e.id
}


@login_required
@utils.jsonify
def json_rtype_ctypes(request, rtype_id):
    content_types = get_object_or_404(RelationType, pk=rtype_id).object_ctypes.all()
    getters, range, sort = _clean_fields_values_args(request.GET, JSON_CONTENT_TYPE_FIELDS)

    if not content_types:
        content_types = list(utils.creme_entity_content_types())

    return _fields_values(content_types, getters, range, sort)


@login_required
def add_relations(request, subject_id, rtype_id=None):
    """
        NB: In case of rtype_id=None is internal relation type is verified in RelationCreateForm clean
    """
    subject = get_object_or_404(CremeEntity, pk=subject_id)

    user = request.user
    user.has_perm_to_link_or_die(subject)

    relations_types = None

    if rtype_id:
        get_object_or_404(RelationType, pk=rtype_id).is_not_internal_or_die()
        relations_types = [rtype_id]

    if request.method == 'POST':
        form = RelationCreateForm(subject=subject, user=user,
                                  relations_types=relations_types,
                                  data=request.POST,
                                 )

        if form.is_valid():
            form.save()
    else:  # GET
        if rtype_id is None:
            excluded_rtype_ids = request.GET.getlist('exclude')
            if excluded_rtype_ids:
                # Theses type are excluded to provide a better GUI, but they cannot cause business conflict
                # (internal rtypes are always excluded), so it's not a problem to only excluded them only in GET part.
                relations_types = RelationType.get_compatible_ones(subject.entity_type) \
                                              .exclude(id__in=excluded_rtype_ids)

        form = RelationCreateForm(subject=subject, user=user,
                                  relations_types=relations_types,
                                 )

    return inner_popup(request,
                       'creme_core/generics/blockform/link_popup.html',
                       {'form':  form,
                        'title': _(u'Relationships for «{entity}»').format(entity=subject),
                        'submit_label': _(u'Save the relationships'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


# TODO: Factorise with add_properties_bulk and bulk_update?
@login_required
def add_relations_bulk(request, model_ct_id):
    rtype_ids = None

    if request.method == 'GET':
        rtype_ids = request.GET.getlist('rtype') or None

    user = request.user
    model = utils.get_ct_or_404(model_ct_id).model_class()

    # TODO: rename 'ids' -> 'entity/id' ?
    entities = get_list_or_404(model,
                               pk__in=request.POST.getlist('ids') if request.method == 'POST' else
                                      request.GET.getlist('ids'),
                              )

    CremeEntity.populate_real_entities(entities)

    filtered = {True: [], False: []}
    has_perm_to_link = user.has_perm_to_link
    for entity in entities:
        filtered[has_perm_to_link(entity)].append(entity)

    if request.method == 'POST':
        form = MultiEntitiesRelationCreateForm(subjects=filtered[True],
                                               forbidden_subjects=filtered[False],
                                               user=user,
                                               data=request.POST,
                                               relations_types=rtype_ids,
                                              )

        if form.is_valid():
            form.save()
    else:
        form = MultiEntitiesRelationCreateForm(subjects=filtered[True],
                                               forbidden_subjects=filtered[False],
                                               user=user,
                                               relations_types=rtype_ids,
                                              )

    return inner_popup(request, 'creme_core/generics/blockform/add_popup.html',
                       {'form':  form,
                        'title': _(u'Multiple adding of relationships'),
                        'submit_label': _(u'Save the relationships'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


@login_required
def delete(request):
    relation = get_object_or_404(Relation, pk=utils.get_from_POST_or_404(request.POST, 'id'))
    subject = relation.subject_entity
    user = request.user

    has_perm = user.has_perm_to_unlink_or_die
    has_perm(subject)
    has_perm(relation.object_entity)
    relation.type.is_not_internal_or_die()

    # relation.get_real_entity().delete()
    relation.delete()

    if request.is_ajax():
        # return HttpResponse(content_type='text/javascript')
        return HttpResponse()

    return redirect(subject.get_real_entity())


@login_required
def delete_similar(request):
    "Delete relations with the same type between 2 entities"
    get = partial(utils.get_from_POST_or_404, request.POST)
    subject_id = get('subject_id', int)
    rtype_id   = get('type')
    object_id  = get('object_id', int)

    user = request.user
    subject = get_object_or_404(CremeEntity, pk=subject_id)

    has_perm = user.has_perm_to_unlink_or_die
    has_perm(subject)
    has_perm(get_object_or_404(CremeEntity, pk=object_id))

    rtype = get_object_or_404(RelationType, pk=rtype_id)
    rtype.is_not_internal_or_die()

    for relation in Relation.objects.filter(subject_entity=subject.id, type=rtype, object_entity=object_id):
        # relation.get_real_entity().delete()
        relation.delete()

    if request.is_ajax():
        # return HttpResponse(content_type='text/javascript')
        return HttpResponse()

    return redirect(subject.get_real_entity())


@login_required
def delete_all(request):  # TODO: deprecate ?
    subject_id = utils.get_from_POST_or_404(request.POST, 'subject_id')
    user = request.user
    subject = get_object_or_404(CremeEntity, pk=subject_id)
    user.has_perm_to_unlink_or_die(subject)

    errors = defaultdict(list)

    for relation in Relation.objects.filter(type__is_internal=False, subject_entity=subject_id):
        # relation = relation.get_real_entity()
        if user.has_perm_to_unlink(relation.object_entity):
            relation.delete()
        else:
            errors[403].append(_(u'{entity} : <b>Permission denied</b>').format(entity=relation.object_entity))

    if not errors:
        status = 200
        message = _(u'Operation successfully completed')
    else:
        status = min(errors)
        message = ",".join(msg for error_messages in errors.values() for msg in error_messages)

    # return HttpResponse(message, content_type='text/javascript', status=status)
    return HttpResponse(message, status=status)


@login_required
def select_relations_objects(request):
    """Display an inner popup to select entities to link as relations' objects for a given subject entity.

    GET parameters:
     - rtype_id: RelationType ID of the future relations. Required.
     - subject_id: ID of the entity used as subject for relations. Integer. Required.
     - object_ct_id: ID of the ContentType of the future relations' objects. Integer. Required.
     - selection: 'single'/'multiple'. Optional. Default to 'single'.

    Tip: use the JS function creme.relations.addRelationTo().
    """
    get = partial(utils.get_from_GET_or_404, request.GET)
    subject_id    = get('subject_id', int)
    rtype_id      = get('rtype_id')
    objects_ct_id = get('objects_ct_id', int)
    mode          = get('selection', cast=listview.str_to_mode, default='single')

    objects_ct = utils.get_ct_or_404(objects_ct_id)

    subject = get_object_or_404(CremeEntity, pk=subject_id)
    request.user.has_perm_to_link_or_die(subject)

    rtype = get_object_or_404(RelationType, pk=rtype_id)
    rtype.is_not_internal_or_die()

    # TODO: filter with relation creds too ?
    # NB: list() because the serialization of sub-QuerySet does not work with the JSON session
    extra_q = ~Q(pk__in=list(CremeEntity.objects
                                        .filter(relations__type=rtype.symmetric_type_id,
                                                relations__object_entity=subject_id,
                                               )
                                        .values_list('id', flat=True)
                            )
                )

    prop_types = list(rtype.object_properties.all())
    if prop_types:
        extra_q &= Q(properties__type__in=prop_types)

    return listview.list_view_popup(request,
                                    model=objects_ct.model_class(),
                                    mode=mode,
                                    extra_q=extra_q,
                                   )


# TODO: factorise code (with RelatedEntitiesField for example) ?  With a smart static method method in RelationType ?
@login_required
def add_relations_with_same_type(request):
    """Allow to create from a POST request several relations with the same
    relation type, between a subject and several other entities.
    Tip: see the JS function creme.relations.addRelationTo()
    """
    user = request.user
    POST = request.POST
    subject_id = utils.get_from_POST_or_404(POST, 'subject_id', int)
    rtype_id   = utils.get_from_POST_or_404(POST, 'predicate_id')  # TODO: rename POST arg
    entity_ids = POST.getlist('entities')  # TODO: rename 'entity' ?

    if not entity_ids:
        raise Http404('Void "entities" parameter.')

    rtype = get_object_or_404(RelationType, pk=rtype_id)
    rtype.is_not_internal_or_die()

    entity_ids.append(subject_id)  # NB: so we can do only one query
    entities = list(CremeEntity.objects.filter(pk__in=entity_ids))

    subject_properties = frozenset(rtype.subject_properties.values_list('id', flat=True))
    object_properties  = frozenset(rtype.object_properties.values_list('id', flat=True))

    if subject_properties or object_properties:
        # Optimise the get_properties() (but it retrieves CremePropertyType objects too)
        CremeEntity.populate_properties(entities)

    for i, entity in enumerate(entities):
        if entity.id == subject_id:
            subject = entity
            entities.pop(i)
            break
    else:
        raise Http404('Can not find entity with id={}'.format(subject_id))

    user.has_perm_to_link_or_die(subject)

    errors = defaultdict(list)
    len_diff = len(entity_ids) - len(entities)

    if len_diff != 1:  # 'subject' has been pop from entities, but not subject_id from entity_ids, so 1 and not 0
        errors[404].append(ungettext(u"{count} entity doesn't exist or has been removed.",
                                     u"{count} entities don't exist or have been removed.",
                                     len_diff
                                    ).format(count=len_diff)
                          )

    # TODO: move in a RelationType method ??
    subject_ctypes = frozenset(int(ct_id) for ct_id in rtype.subject_ctypes.values_list('id', flat=True))
    if subject_ctypes and subject.entity_type_id not in subject_ctypes:
        raise ConflictError('Incompatible type for subject')

    if subject_properties and not any(p.type_id in subject_properties for p in subject.get_properties()):
        raise ConflictError('Missing compatible property for subject')

    # TODO: move in a RelationType method ??
    object_ctypes = frozenset(int(ct_id) for ct_id in rtype.object_ctypes.values_list('id', flat=True))
    check_ctype = (lambda e: e.entity_type_id in object_ctypes) if object_ctypes else \
                  lambda e: True

    check_properties = (lambda e: any(p.type_id in object_properties for p in e.get_properties())) \
                       if object_properties else \
                       lambda e: True

    create_relation = Relation.objects.create
    for entity in entities:
        if not check_ctype(entity):
            errors[409].append(_(u'Incompatible type for object entity with id={}').format(entity.id))
        elif not check_properties(entity):
            errors[409].append(_(u'Missing compatible property for object entity with id={}').format(entity.id))
        elif not user.has_perm_to_link(entity):
            errors[403].append(_(u'Permission denied to entity with id={}').format(entity.id))
        else:
            create_relation(subject_entity=subject, type=rtype, object_entity=entity, user=user)

    if not errors:
        status = 200
        message = _(u'Operation successfully completed')
    else:
        status = min(errors)
        message = ','.join(msg for error_messages in errors.values() for msg in error_messages)

    return HttpResponse(message, status=status)
