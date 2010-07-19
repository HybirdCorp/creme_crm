# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models.query_utils import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, get_list_or_404
from django.template.context import RequestContext
from django.utils.simplejson.encoder import JSONEncoder

from creme_core.forms.relation import RelationCreateForm, MultiEntitiesRelationCreateForm
from creme_core.models import Relation, RelationType, CremeEntity
from creme_core.registry import creme_registry
from creme_core.entities_access.permissions import user_has_read_permission_for_an_object
from creme_core.entities_access.filter_allowed_objects import filter_RUD_objects
from creme_core.entities_access.functions_for_permissions import read_object_or_die, edit_object_or_die, delete_object_or_die
from creme_core.views.generic import inner_popup, list_view_popup_from_widget
from creme_core.blocks import relations_block


#JSON_OPS = frozenset(('gt', 'lt', 'in'))

class JSONSelectError(Exception):
    def __init__(self, message, status):
        super(Exception, self).__init__(message)
        self.status = status

def __json_select(query, fields, range, sort_field=None, use_columns=False):
    try:
        start, end = range
        
        if not use_columns:
            result = []
            
            if sort_field:
                sorted_result = [(sort_field(entity), [getter(entity) for getter in fields]) for entity in query]
                sorted_result.sort(cmp=lambda a, b:cmp(a[0], b[0]))
                result = [e[1] for e in sorted_result[start:end]]
            else:
                for entity in query[start:end]:
                    result.append([getter(entity) for getter in fields])

        else:
            query = query.order_by(sort_field) if sort_field else query
            flat = len(fields) == 1
            result = list(query.values_list(flat=flat, *fields)[start:end])
        
        return JSONEncoder().encode(result)
    except Exception, err:
        raise JSONSelectError(unicode(err), 500)

# TODO (refs 293) : unused tool. remove it !
#def __json_parse_filter(filter, allowed_filters, allowed_ops):
#    field = str(filter[0])
#    size = len(filter)
#    
#    if field not in allowed_filters:
#        raise JSONSelectError("forbidden filter '%s'" % field, 403)
#    
#    if size == 2:
#        return (field, filter[1])
#
#    op = str(filter[-1])
#
#    if op not in allowed_ops:
#        raise JSONSelectError("forbidden op '%s'" % op, 403)
#
#    if size == 3:
#        return (field + '__' + op, filter[1])
#
#    return (field + '__' + op, [v for v in filter[1:-1]])
#
#def __json_parse_filters(filters, allowed_filters, allowed_ops):
#    filter_entries = (filter.split(',') for filter in filters if len(filter) > 1)
#    return dict(__json_parse_filter(entry, allowed_filters, allowed_ops) for entry in filter_entries)

def __json_parse_field(field, allowed_fields, use_columns=False):
    if field not in allowed_fields.keys():
        raise JSONSelectError("forbidden field '%s'" % field, 403)
    
    if use_columns:
        return field
    
    getter = allowed_fields.get(field)
        
    if not getter:
        raise JSONSelectError("forbidden fields '%s'" % field, 403)
    
    return getter
    
def __json_parse_fields(fields, allowed_fields, use_columns=False):
    if not fields:
        raise JSONSelectError("no such field", 400)
    
    return list(__json_parse_field(field, allowed_fields, use_columns) for field in fields)

# TODO (refs 293) : unused tool. remove it !
#def __json_parse_filtered_select_request(request, allowed_filters, allowed_ops, allowed_fields):
#    if not request:
#        raise JSONSelectError("not such parameter", 400)
#
#    use_columns = bool(request.get('value_list', 0))
#    range = [int(i) if i is not None else None for i in (request.get('start'), request.get('end'))]
#    
#    filters = __json_parse_filters(request.getlist('filters'), allowed_filters, allowed_ops)
#    fields = __json_parse_fields(request.getlist('fields'), allowed_fields, use_columns)
#    sort = request.get('sort')
#    sort = __json_parse_field(sort, allowed_fields, use_columns) if sort is not None else None
#
#    return (filters, fields, range, sort, use_columns)

def __json_parse_select_request(request, allowed_fields):
    if not request:
        raise JSONSelectError("not such parameter", 400)

    use_columns = bool(request.get('value_list', 0))
    range = [int(i) if i is not None else None for i in (request.get('start'), request.get('end'))]
    fields = __json_parse_fields(request.getlist('fields'), allowed_fields, use_columns)
    sort = request.get('sort')
    sort = __json_parse_field(sort, allowed_fields, use_columns) if sort is not None else None

    return (fields, range, sort, use_columns)

#JSON_ENTITY_FILTERS = frozenset(('id', 'entity_type'))

JSON_ENTITY_FIELDS = {'unicode':unicode, 
                      'id':lambda e:e.id,
                      'entity_type':lambda e:e.entity_type_id}

# TODO (refs 293) : unused tool. remove it !
#@login_required
#def json_entity_select(request):
#    try:
#        filters, fields, range, sort, use_columns = __json_parse_filtered_select_request(request.GET, JSON_ENTITY_FILTERS, JSON_OPS, JSON_ENTITY_FIELDS)
#        query = filter_RUD_objects(request, CremeEntity.objects.filter(**filters))
#        return HttpResponse(__json_select(query, fields, range, sort, use_columns), mimetype="text/javascript")
#    except JSONSelectError, err:
#        return HttpResponse(err.message, mimetype="text/javascript", status=err.status)

@login_required
def json_entity_get(request, id):
    try:
        fields, range, sort, use_columns = __json_parse_select_request(request.GET, JSON_ENTITY_FIELDS)
        query = filter_RUD_objects(request, CremeEntity.objects.filter(pk=id))
        return HttpResponse(__json_select(query, fields, (0, 1), sort, use_columns), mimetype="text/javascript")
    except JSONSelectError, err:
        return HttpResponse(err.message, mimetype="text/javascript", status=err.status)

JSON_PREDICATE_FIELDS = {'unicode':unicode, 
                         'id':lambda e:e.id}

@login_required
def json_entity_predicates(request, id):
    try:
        predicates = __get_entity_predicates(request, id)
        parameters = __json_parse_select_request(request.GET, JSON_PREDICATE_FIELDS)
        return HttpResponse(__json_select(predicates, *parameters))
    except JSONSelectError, err:
        return HttpResponse(err.message, mimetype="text/javascript", status=err.status)
    except Http404, err:
        return HttpResponse(err, mimetype="text/javascript", status=404)
    except Exception, err:
        return HttpResponse(err, mimetype="text/javascript", status=500)

JSON_CONTENT_TYPE_FIELDS = {'unicode':unicode,
                            'name':lambda e:e.name, 
                            'id':lambda e:e.id}

@login_required
def json_predicate_content_types(request, id):
    try:
        #content_type_ids = get_object_or_404(RelationType, pk=id).object_range_ctype.all()
        content_types = get_object_or_404(RelationType, pk=id).object_ctypes.all()

        fields, range, sort, use_columns = __json_parse_select_request(request.GET, JSON_CONTENT_TYPE_FIELDS)
        
        #if not content_type_ids:
        if not content_types:
            content_type_from_model = ContentType.objects.get_for_model
            content_types = [content_type_from_model(model) for model in creme_registry.iter_entity_models()]
            return HttpResponse(__json_select(content_types, fields, range, sort))
    
        #return HttpResponse(__json_select(ContentType.objects.filter(pk__in=content_type_ids), fields, range, sort, use_columns))
        return HttpResponse(__json_select(content_types, fields, range, sort, use_columns))
    except JSONSelectError, err:
        return HttpResponse(err.message, mimetype="text/javascript", status=err.status)
    except Http404, err:
        return HttpResponse(err, mimetype="text/javascript", status=404)
    except Exception, err:
        return HttpResponse(err, mimetype="text/javascript", status=500)
        
def __get_entity_predicates(request, id):
    entity = get_object_or_404(CremeEntity, pk=id).get_real_entity()

    # TODO : unable to test it !
    die_status = read_object_or_die(request, entity)
    
    if die_status:
        return die_status
    
    predicates = RelationType.objects.filter(can_be_create_with_popup=True).order_by('predicate')
    predicates = predicates.filter(Q(subject_ctypes=entity.entity_type)|Q(subject_ctypes__isnull=True)).distinct()
    return predicates

def add_relations(request, subject_id):
    subject = get_object_or_404(CremeEntity, pk=subject_id)

    die_status = edit_object_or_die(request, subject)
    if die_status:
        return die_status

    POST = request.POST

    if POST:
        form = RelationCreateForm(subject, request.user.id, POST)

        if form.is_valid():
            form.save()
    else:
        form = RelationCreateForm(subject=subject, user_id=request.user.id)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':  form,
                        'title': u'Relations pour <%s>' % subject,
                       },
                       is_valid=form.is_valid(),
                       reload = False,
                       delegate_reload = True,
                       context_instance=RequestContext(request))

# NOTE : filter_RUD_objects <= filter allowed entities for this user 

@login_required
def add_relations_bulk(request, model_ct_id, ids):
    POST = request.POST

    model    = get_object_or_404(ContentType, pk=model_ct_id).model_class()
    entities = get_list_or_404(model, pk__in=ids.split(','))

    die_statuses = set([edit_object_or_die(request, entity) for entity in entities])

    if die_statuses ^ set([None]):
        die_status = die_statuses.pop()
        while die_status is None and die_statuses:
            die_status = die_statuses.pop()
        return die_status

    if POST:
        form = MultiEntitiesRelationCreateForm(entities, request.user.id, POST)

        if form.is_valid():
            form.save()
    else:
        form = MultiEntitiesRelationCreateForm(subjects=entities, user_id=request.user.id)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':  form,
#                        'title': u'Relations pour <%s>' % subject,
                        'title': u'Ajout multiple de relation(s)',
                       },
                       is_valid=form.is_valid(),
                       reload = False,
                       delegate_reload = True,
                       context_instance=RequestContext(request))
    

@login_required
def delete(request):
    """
        @Permissions : Delete on relation's subject entity
    """
    post_get = request.POST.get
    relation = get_object_or_404(Relation, pk=post_get('id'))
    entity   = get_object_or_404(CremeEntity, pk=post_get('object_id')).get_real_entity()

    die_status = delete_object_or_die(request, entity) #delete credental on 'entity' ?? only one ???
    if die_status:
        return die_status

    relation.get_real_entity().delete()

#    return HttpResponseRedirect(entity.get_absolute_url())
    return HttpResponse("")

@login_required
def delete_similar(request):
    """Delete relations with the same type between 2 entities
        @Permissions : Delete on relation's subject entity
    """
    post_get = request.POST.get
    subject = get_object_or_404(CremeEntity, pk=post_get('subject_id')).get_real_entity()

    die_status = delete_object_or_die(request, subject) #delete credental on 'subject' ?? not relation's object ???
    if die_status:
        return die_status

    for relation in Relation.objects.filter(subject_entity=subject, type=post_get('type'), object_entity__id=post_get('object_id')):
        relation.get_real_entity().delete()

    return HttpResponse("")

@login_required
def add_relation_from_predicate_n_entity(request, predicate_id, subject_id, object_ct_id, o2m=False):
    template_dict = {
        'predicate_id': predicate_id,
        'subject_id':   subject_id,
        'o2m':          o2m
    }

    #TODo: only one query ??
    pklist = Relation.objects.filter(type__id=predicate_id, subject_entity__id=subject_id).values_list('object_entity_id')
    extra_q = ~Q(pk__in=pklist)

    return list_view_popup_from_widget(request, object_ct_id, o2m, extra_dict=template_dict, extra_q=extra_q)

@login_required
def handle_relation_from_predicate_n_entity(request):
    """
        @Permissions : Read on subject entity & Read on object entities
    """
    post = request.POST
    entities     = post.getlist('entities')
    subject_id   = post.get('subject_id')
    predicate_id = post.get('predicate_id')

    subject = get_object_or_404(CremeEntity, pk=subject_id).get_real_entity()

    return_msg = []
    status = 200

    die_status = read_object_or_die(request, subject)
    if die_status:
        return die_status
#        return_msg = "Fiche non accessible. Permissions non accordée."
#        status = 403

    is_there_already_err = False

    if entities and predicate_id:
        centity_get = CremeEntity.objects.get
        for entity_id in entities:
            try: #TODO: group SQL queries ??? (group by class)
                entity = centity_get(pk=entity_id).get_real_entity()
                if not user_has_read_permission_for_an_object(request, entity):
                    return_msg.append("permission d'accès à : %s refusée" % entity)
                    status = 403
                    continue
            except CremeEntity.DoesNotExist:
                if not is_there_already_err:
                    return_msg.append("Certaines des entités n'existent pas ou plus")
                    is_there_already_err = True
                    status = 404
                continue

            Relation.create(subject, predicate_id, entity)

    if status == 200:
        return_msg.append("Opération déroulée avec succès")

    return HttpResponse(",".join(return_msg), status=status)

@login_required
def reload_block(request, entity_id):
    return relations_block.detailview_ajax(request, entity_id)
