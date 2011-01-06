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

from django.db.models.query_utils import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, get_list_or_404
from django.template.context import RequestContext
from django.utils.simplejson.encoder import JSONEncoder
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.forms.relation import RelationCreateForm, MultiEntitiesRelationCreateForm
from creme_core.models import Relation, RelationType, CremeEntity, EntityCredentials
from creme_core.registry import creme_registry
from creme_core.views.generic import inner_popup, list_view_popup_from_widget
from creme_core.utils import get_ct_or_404, get_from_POST_or_404

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
                sorted_result.sort(cmp=lambda a, b:cmp(a[0], b[0])) #TODO: use 'key' param instead
                result = [e[1] for e in sorted_result[start:end]]
            else:
                for entity in query[start:end]:
                    result.append([getter(entity) for getter in fields]) #TODO: use extend + genexpr ?

        else:
            query = query.order_by(sort_field) if sort_field else query
            flat = len(fields) == 1
            result = list(query.values_list(flat=flat, *fields)[start:end])

        return JSONEncoder().encode(result) #TODO: move out tre 'try' block
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

JSON_ENTITY_FIELDS = {
                        'unicode':     unicode,
                        'id':          lambda e: e.id,
                        'entity_type': lambda e: e.entity_type_id
                     }

#TODO: unused tool. remove it !
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
        #query = filter_RUD_objects(request, CremeEntity.objects.filter(pk=id))
        query = EntityCredentials.filter(request.user, CremeEntity.objects.filter(pk=id))
        return HttpResponse(__json_select(query, fields, (0, 1), sort, use_columns), mimetype="text/javascript") #TODO: move out the 'try' block
    except JSONSelectError, err:
        return HttpResponse(err.message, mimetype="text/javascript", status=err.status)

JSON_PREDICATE_FIELDS = {
                            'unicode': unicode,
                            'id':      lambda e: e.id
                        }

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

JSON_CONTENT_TYPE_FIELDS = {
                            'unicode':  unicode,
                            'name':     lambda e: e.name,
                            'id':       lambda e: e.id
                           }

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

    entity.can_view_or_die(request.user)

    predicates = RelationType.objects.filter(can_be_create_with_popup=True).order_by('predicate')

    return predicates.filter(Q(subject_ctypes=entity.entity_type)|Q(subject_ctypes__isnull=True)).distinct()

def add_relations(request, subject_id, relation_type_id=None):
    subject = get_object_or_404(CremeEntity, pk=subject_id)
    subject.can_change_or_die(request.user)

    relations_types = [relation_type_id] if relation_type_id else None
    POST = request.POST

    if POST:
        form = RelationCreateForm(subject, request.user.id, relations_types, POST)

        if form.is_valid():
            form.save()
    else:
        form = RelationCreateForm(subject=subject, user_id=request.user.id, relations_types=relations_types)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':  form,
                        'title': _(u'Relations for <%s>') % subject,
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

#TODO: use EntityCredentials.filter to filter allowed entities for this user
@login_required
def add_relations_bulk(request, model_ct_id, ids):
    POST = request.POST

    model    = get_object_or_404(ContentType, pk=model_ct_id).model_class()
    entities = get_list_or_404(model, pk__in=[id for id in ids.split(',') if id])

    #TODO: improve by regrouping queries
    for entity in entities:
        entity.can_change_or_die(request.user) #TODO: edit credentials ??? only on subject ??

    if POST:
        form = MultiEntitiesRelationCreateForm(entities, request.user.id, None, POST)

        if form.is_valid():
            form.save()
    else:
        form = MultiEntitiesRelationCreateForm(subjects=entities, user_id=request.user.id)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':  form,
                        'title': _(u'Multiple adding of relations'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

#TODO: deeply think about the relation credentials...
@login_required
def delete(request):
    relation = get_object_or_404(Relation, pk=get_from_POST_or_404(request.POST, 'id'))
    subject  = relation.subject_entity

    subject.can_delete_or_die(request.user) #TODO: delete credentials on 'subject_entity' ?? only one ???
    relation.get_real_entity().delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(subject.get_absolute_url())


@login_required
def delete_similar(request):
    """Delete relations with the same type between 2 entities
        @Permissions : Delete on relation's subject entity
    """
    POST = request.POST
    subject_id = get_from_POST_or_404(POST, 'subject_id')
    rtype_id   = get_from_POST_or_404(POST, 'type')
    object_id  = get_from_POST_or_404(POST, 'object_id')

    subject = get_object_or_404(CremeEntity, pk=subject_id).get_real_entity()

    subject.can_delete_or_die(request.user) #TODO: delete credentials on 'subject' ?? only it ???

    for relation in Relation.objects.filter(subject_entity=subject, type=rtype_id, object_entity=object_id):
        relation.get_real_entity().delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(subject.get_absolute_url())

@login_required
def objects_to_link_selection(request, rtype_id, subject_id, object_ct_id, o2m=False):
    template_dict = {
        'predicate_id': rtype_id,   #TODO: useful ??
        'subject_id':   subject_id, #TODO: useful ??
        'o2m':          o2m
    }

    #extra_q = ~Q(pk__in=Relation.objects.filter(type=rtype_id, subject_entity=subject_id).values_list('object_entity_id'))
    rtype   = get_object_or_404(RelationType, pk=rtype_id)
    extra_q = ~Q(relations__type=rtype.symmetric_type_id, relations__object_entity=subject_id)

    return list_view_popup_from_widget(request, object_ct_id, o2m, extra_dict=template_dict, extra_q=extra_q)


#TODO: refactor (add unit tests too)
#TODO: rework credentials (for now: Read on subject & object entities)
@login_required
def add_relations_with_same_type(request):
    """Allow to create from a POST request several relations with the same
    relation type, between a subject and several other entities.
    """
    post = request.POST
    entities     = post.getlist('entities')
    subject_id   = post.get('subject_id')
    predicate_id = post.get('predicate_id')

    subject = get_object_or_404(CremeEntity, pk=subject_id).get_real_entity()

    return_msg = []
    status = 200

    subject.can_view_or_die(request.user)

    is_there_already_err = False

    if entities and predicate_id:
        centity_get = CremeEntity.objects.get
        for entity_id in entities:
            try: #TODO: group SQL queries ??? (group by class)
                entity = centity_get(pk=entity_id).get_real_entity()
                #if not user_has_read_permission_for_an_object(request, entity):
                if not request.user.has_perm('creme_core.view_entity', entity):
                    return_msg.append(_(u"access permission denied : %s denied") % entity)
                    status = 403
                    continue
            except CremeEntity.DoesNotExist:
                if not is_there_already_err:
                    return_msg.append(_(u"Some entities doesn't exist / doesn't exist any more"))
                    is_there_already_err = True
                    status = 404
                continue

            Relation.create(subject, predicate_id, entity)

    if status == 200:
        return_msg.append(_(u"Operation successfully completed"))

    return HttpResponse(",".join(return_msg), status=status)

#TODO: use jsonify
@login_required
def get_predicates_choices_4_ct(request):
    ct = get_ct_or_404(get_from_POST_or_404(request.POST, 'ct_id'))
    predicates = [(rtype.id, rtype.predicate) for rtype in RelationType.get_compatible_ones(ct).order_by('predicate')]

    return HttpResponse(JSONEncoder().encode(predicates), mimetype="text/javascript")
