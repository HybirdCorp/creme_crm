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

from collections import defaultdict

from django.core.exceptions import PermissionDenied
from django.db.models.query_utils import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, get_list_or_404, redirect
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from ..core.exceptions import ConflictError
from ..forms.relation import RelationCreateForm, MultiEntitiesRelationCreateForm
from ..models import Relation, RelationType, CremeEntity, EntityCredentials
from ..utils import get_from_POST_or_404, get_ct_or_404, creme_entity_content_types, jsonify
from .generic import inner_popup, list_view_popup_from_widget


def _fields_values(instances, getters, range, sort_getter=None, user=None):
    start, end = range
    result = []

    def values(i):
        return [getter(i, user) for getter in getters]

    if sort_getter:
        sorted_result = [(sort_getter(instance), values(instance)) for instance in instances]
        sorted_result.sort(key=lambda x: x[0])
        result.extend(e[1] for e in sorted_result[start:end])
    else:
        result.extend(values(instance) for instance in instances[start:end])

    return result

def _clean_getters_arg(field, allowed_fields):
    getter = allowed_fields.get(field)

    if not getter:
        raise PermissionDenied("Forbidden field '%s'" % field)

    return getter

def _clean_fields_values_args(data, allowed_fields):
    if not data:
        raise ValueError('Not such parameter')

    get = data.get
    range = [int(i) if i is not None else None for i in (get('start'), get('end'))]
    getters = [_clean_getters_arg(field, allowed_fields) for field in data.getlist('fields')]

    if not getters:
        raise ValueError('No such field')

    sort_getter = get('sort')
    if sort_getter is not None:
        sort_getter = _clean_getters_arg(sort_getter, allowed_fields)

    return getters, range, sort_getter

JSON_ENTITY_FIELDS = {'unicode':     lambda e, user: e.allowed_unicode(user),
                      'id':          lambda e, user: e.id,
                      'entity_type': lambda e, user: e.entity_type_id,
                      'summary':     lambda e, user: e.get_real_entity().get_entity_summary(user),
                     }

#TODO: move to entity.py, (rename ?) & change also url
@login_required
@jsonify
def json_entity_get(request, entity_id):
    getters, range, sort = _clean_fields_values_args(request.GET, JSON_ENTITY_FIELDS)
    query = EntityCredentials.filter(request.user, CremeEntity.objects.filter(pk=entity_id))

    return _fields_values(query, getters, (0, 1), sort, request.user)

JSON_PREDICATE_FIELDS = {'unicode': lambda e, user: unicode(e),
                         'id':      lambda e, user: e.id
                        }

@login_required
@jsonify
def json_entity_rtypes(request, entity_id): #TODO: seems unused
    entity = get_object_or_404(CremeEntity, pk=entity_id)
    request.user.has_perm_to_view_or_die(entity)

    #TODO: use CremePropertyType constraints too
    rtypes = RelationType.objects.filter(is_internal=False) \
                                 .filter(Q(subject_ctypes=entity.entity_type) |
                                         Q(subject_ctypes__isnull=True)
                                        ) \
                                 .order_by('predicate') \
                                 .distinct() #TODO: distinct useful ??

    #TODO: use unicode collation ?

    return _fields_values(rtypes, *_clean_fields_values_args(request.GET, JSON_PREDICATE_FIELDS))


JSON_CONTENT_TYPE_FIELDS = {'unicode':  lambda e, user: unicode(e),
                            #'name':     lambda e: e.name, #deprecated field
                            'id':       lambda e, user: e.id
                           }

@login_required
@jsonify
def json_rtype_ctypes(request, rtype_id):
    content_types = get_object_or_404(RelationType, pk=rtype_id).object_ctypes.all()
    getters, range, sort = _clean_fields_values_args(request.GET, JSON_CONTENT_TYPE_FIELDS)

    if not content_types:
        content_types = list(creme_entity_content_types())

    return _fields_values(content_types, getters, range, sort)

@login_required
def add_relations(request, subject_id, rtype_id=None):
    """
        NB: In case of rtype_id=None is internal relation type is verified in RelationCreateForm clean
    """
    subject = get_object_or_404(CremeEntity, pk=subject_id)
    request.user.has_perm_to_link_or_die(subject)

    relations_types = None

    if rtype_id:
        get_object_or_404(RelationType, pk=rtype_id).is_not_internal_or_die()
        relations_types = [rtype_id]

    if request.method == 'POST':
        form = RelationCreateForm(subject=subject, user=request.user,
                                  relations_types=relations_types,
                                  data=request.POST,
                                 )

        if form.is_valid():
            form.save()
    else:
        form = RelationCreateForm(subject=subject, user=request.user,
                                  relations_types=relations_types,
                                 )

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':  form,
                        'title': _(u'Relationships for <%s>') % subject,
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
def add_relations_bulk(request, model_ct_id, relations_types=None):#TODO: Factorise with add_properties_bulk and bulk_update?
    user = request.user
    model    = get_ct_or_404(model_ct_id).model_class()
    entities = get_list_or_404(model, pk__in=request.REQUEST.getlist('ids'))

    CremeEntity.populate_real_entities(entities)
    #CremeEntity.populate_credentials(entities, user)

    filtered = {True: [], False: []}
    has_perm_to_link = user.has_perm_to_link
    for entity in entities:
        filtered[has_perm_to_link(entity)].append(entity)

    if relations_types is not None:
        relations_types = [rt for rt in relations_types.split(',') if rt]

    if request.method == 'POST':
        form = MultiEntitiesRelationCreateForm(subjects=filtered[True],
                                               forbidden_subjects=filtered[False],
                                               user=request.user,
                                               data=request.POST,
                                               relations_types=relations_types,
                                              )

        if form.is_valid():
            form.save()
    else:
        form = MultiEntitiesRelationCreateForm(subjects=filtered[True],
                                               forbidden_subjects=filtered[False],
                                               user=request.user,
                                               relations_types=relations_types,
                                              )

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':  form,
                        'title': _(u'Multiple adding of relationships'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
def delete(request):
    relation = get_object_or_404(Relation, pk=get_from_POST_or_404(request.POST, 'id'))
    subject  = relation.subject_entity
    user = request.user

    has_perm = user.has_perm_to_unlink_or_die
    has_perm(subject)
    has_perm(relation.object_entity)
    relation.type.is_not_internal_or_die()

    relation.get_real_entity().delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return redirect(subject.get_real_entity())

@login_required
def delete_similar(request):
    "Delete relations with the same type between 2 entities"
    POST = request.POST
    subject_id = get_from_POST_or_404(POST, 'subject_id')
    rtype_id   = get_from_POST_or_404(POST, 'type')
    object_id  = get_from_POST_or_404(POST, 'object_id')

    user = request.user
    subject = get_object_or_404(CremeEntity, pk=subject_id)

    has_perm = user.has_perm_to_unlink_or_die
    has_perm(subject)
    has_perm(get_object_or_404(CremeEntity, pk=object_id))

    rtype = get_object_or_404(RelationType, pk=rtype_id)
    rtype.is_not_internal_or_die()

    for relation in Relation.objects.filter(subject_entity=subject.id, type=rtype, object_entity=object_id):
        relation.get_real_entity().delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return redirect(subject.get_real_entity())

@login_required
def delete_all(request):
    subject_id = get_from_POST_or_404(request.POST, 'subject_id')
    user = request.user
    subject = get_object_or_404(CremeEntity, pk=subject_id)
    user.has_perm_to_unlink_or_die(subject)

    errors = defaultdict(list)

    for relation in Relation.objects.filter(type__is_internal=False, subject_entity=subject_id):
        relation = relation.get_real_entity()
        if user.has_perm_to_unlink(relation.object_entity):
            relation.delete()
        else:
            errors[403].append(_(u'%s : <b>Permission denied</b>,') % relation)

    if not errors:
        status = 200
        message = _(u"Operation successfully completed")
    else:
        status = min(errors.iterkeys())
        message = ",".join(msg for error_messages in errors.itervalues() for msg in error_messages)

    return HttpResponse(message, mimetype="text/javascript", status=status)

@login_required
def objects_to_link_selection(request, rtype_id, subject_id, object_ct_id, o2m=False, *args, **kwargs):
    """Display an inner popup to select entities to link as relations' objects.
    @param rtype_id RelationType id of the future relations.
    @param subject_id Id of the entity used as subject for relations.
    @param object_ct_id Id of the ContentType of the future relations' objects.
    @param o2m One-To-Many ; if false, it seems Manay-To-Many => multi selection.
    Tip: see the js function creme.relations.handleAddFromPredicateEntity()
    """
    subject = get_object_or_404(CremeEntity, pk=subject_id)
    request.user.has_perm_to_link_or_die(subject)

    rtype = get_object_or_404(RelationType, pk=rtype_id)
    rtype.is_not_internal_or_die()

    #TODO: filter with relation creds too
    #extra_q = ~Q(relations__type=rtype.symmetric_type_id, relations__object_entity=subject_id) #It seems that way causes some entities linked with another reelation type to be skipped...
    extra_q = ~Q(pk__in=CremeEntity.objects.filter(relations__type=rtype.symmetric_type_id,
                                                   relations__object_entity=subject_id,
                                                  )
                                           .values_list('id', flat=True)
                )

    prop_types = list(rtype.object_properties.all())
    if prop_types:
        extra_q &= Q(properties__type__in=prop_types)

    extra_q_kw = kwargs.get('extra_q')
    if extra_q_kw is not None:
        extra_q &= extra_q_kw

    return list_view_popup_from_widget(request, object_ct_id, o2m, extra_q=extra_q)

#TODO: factorise code (with RelatedEntitiesField for example) ?  With a smart static method method in RelationType ?
@login_required
def add_relations_with_same_type(request):
    """Allow to create from a POST request several relations with the same
    relation type, between a subject and several other entities.
    Tip: see the js function creme.relations.handleAddFromPredicateEntity()
    """
    user = request.user
    POST = request.POST
    subject_id = get_from_POST_or_404(POST, 'subject_id', int)
    rtype_id   = get_from_POST_or_404(POST, 'predicate_id') #TODO: rename POST arg
    entity_ids = POST.getlist('entities')

    if not entity_ids:
        raise Http404('Void "entities" parameter.')

    rtype = get_object_or_404(RelationType, pk=rtype_id)
    rtype.is_not_internal_or_die()

    entity_ids.append(subject_id) #NB: so we can do only one query
    entities = list(CremeEntity.objects.filter(pk__in=entity_ids))

    #CremeEntity.populate_credentials(entities, user)

    subject_properties = frozenset(rtype.subject_properties.values_list('id', flat=True))
    object_properties  = frozenset(rtype.object_properties.values_list('id', flat=True))

    if subject_properties or object_properties:
        CremeEntity.populate_properties(entities) #Optimise the get_properties() (but it retrieves CremePropertyType objects too)

    for i, entity in enumerate(entities):
        if entity.id == subject_id:
            subject = entity
            entities.pop(i)
            break
    else:
        raise Http404('Can not find entity with id=%s' % subject_id)

    user.has_perm_to_link_or_die(subject)

    errors = defaultdict(list)
    len_diff = len(entity_ids) - len(entities)

    if len_diff != 1: #'subject' has been poped from entities, but not subject_id from entity_ids, so 1 and not 0
        errors[404].append(_(u"%s entities doesn't exist / doesn't exist any more") % len_diff)

    #TODO: move in a RelationType method ??
    subject_ctypes = frozenset(int(ct_id) for ct_id in rtype.subject_ctypes.values_list('id', flat=True))
    if subject_ctypes and subject.entity_type_id not in subject_ctypes:
        raise ConflictError('Incompatible type for subject')

    if subject_properties and not any(p.type_id in subject_properties for p in subject.get_properties()):
        raise ConflictError('Missing compatible property for subject')

    #TODO: move in a RelationType method ??
    object_ctypes = frozenset(int(ct_id) for ct_id in rtype.object_ctypes.values_list('id', flat=True))
    check_ctype = (lambda e: e.entity_type_id in object_ctypes) if object_ctypes else \
                  lambda e: True

    check_properties = (lambda e: any(p.type_id in object_properties for p in e.get_properties())) if object_properties else \
                       lambda e: True

    create_relation = Relation.objects.create
    for entity in entities:
        if not check_ctype(entity):
            errors[409].append(_(u"Incompatible type for object entity with id=%s") % entity.id)
        elif not check_properties(entity):
            errors[409].append(_(u"Missing compatible property for object entity with id=%s") % entity.id)
        elif not user.has_perm_to_link(entity):
            errors[403].append(_("Permission denied to entity with id=%s") % entity.id)
        else:
            create_relation(subject_entity=subject, type=rtype, object_entity=entity, user=user)

    if not errors:
        status = 200
        message = _(u"Operation successfully completed")
    else:
        status = min(errors.iterkeys())
        message = ",".join(msg for error_messages in errors.itervalues() for msg in error_messages)

    return HttpResponse(message, status=status)
