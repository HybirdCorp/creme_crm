# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.core.exceptions import PermissionDenied
from django.db.models import Q, FieldDoesNotExist, ForeignKey, ManyToManyField
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, get_list_or_404, render
from django.core import serializers
from django.forms.models import modelform_factory
from django.utils.translation import ugettext as _
from django.utils.simplejson import JSONEncoder
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.models import CremeEntity, CustomField, EntityCredentials
from creme_core.forms import CremeEntityForm
from creme_core.forms.bulk import _get_choices, EntitiesBulkUpdateForm, _FIELDS_WIDGETS, EntityInnerEditForm
from creme_core.forms.merge import form_factory as merge_form_factory, MergeEntitiesBaseForm
from creme_core.views.generic import inner_popup, list_view_popup_from_widget
from creme_core.utils import get_ct_or_404, get_from_POST_or_404, get_from_GET_or_404, jsonify
from creme_core.utils.meta import get_flds_with_fk_flds_str


@login_required
@jsonify
def get_creme_entities_repr(request, entities_ids):
    entities = CremeEntity.objects.filter(pk__in=[id for id in entities_ids.split(',') if id])
    user = request.user

    #TODO: populate real entities and credentials....

    return [{'id': entity.id,
             'text': entity.get_real_entity().get_entity_summary(user) if entity.can_view(user) else \
                     ugettext(u'Entity #%s (not viewable)') % entity.id
            } for entity in entities
           ]

@login_required
def get_creme_entity_as_json(request):
    POST   = request.POST
    pk     = POST.get('pk')
    fields = POST.getlist('fields') or None

    data   = []
    status = 404

    if pk:
        try:
            entity = CremeEntity.objects.get(pk=pk).get_real_entity()
        except CremeEntity.DoesNotExist:
            pass
        else:
            if entity.can_view(request.user):
                data = [entity]
                status = 200

    return HttpResponse(serializers.serialize('json', data, fields=fields), mimetype="text/javascript", status=status)


EXCLUDED_FIELDS = frozenset(('id', 'entity_type', 'is_deleted', 'is_actived', 'cremeentity_ptr', 'header_filter_search_field'))

@jsonify
@login_required
def get_info_fields(request, ct_id):
    ct = get_ct_or_404(ct_id)
    model = ct.model_class()

    if not issubclass(model, CremeEntity):
        raise Http404('No a CremeEntity subclass: %s' % model)

    #TODO: use django.forms.models.fields_for_model ?
    form = modelform_factory(model, CremeEntityForm)(user=request.user)
    required_fields = [name for name, field in form.fields.iteritems() if field.required and name != 'user']

    if len(required_fields) == 1:
        required_field = required_fields[0]
        format  = _(u'%s [CREATION]')
        printer = lambda field: unicode(field.verbose_name) if field.name != required_field else \
                                format % field.verbose_name
    else:
        printer = lambda field: unicode(field.verbose_name)

    return [(field.name, printer(field)) for field in model._meta.fields if field.name not in EXCLUDED_FIELDS and not isinstance(field, ForeignKey)]

@login_required
def bulk_update(request, ct_id):#TODO: Factorise with add_properties_bulk and add_relations_bulk?
    user = request.user
    model    = get_object_or_404(ContentType, pk=ct_id).model_class()
    entities = get_list_or_404(model, pk__in=request.REQUEST.getlist('ids'))

    CremeEntity.populate_real_entities(entities)
    entities = [entity.get_real_entity() for entity in entities]

    CremeEntity.populate_credentials(entities, user)

    filtered = {True: [], False: []}
    for entity in entities:
        filtered[entity.can_change(user)].append(entity)

    if request.method == 'POST':
        form = EntitiesBulkUpdateForm(model=model,
                                      subjects=filtered[True],
                                      forbidden_subjects=filtered[False],
                                      user=request.user,
                                      data=request.POST,
                                     )

        if form.is_valid():
            form.save()
    else:
        form = EntitiesBulkUpdateForm(model=model,
                                      subjects=filtered[True],
                                      forbidden_subjects=filtered[False],
                                      user=request.user,
                                     )

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {'form':  form,
                        'title': _(u'Multiple update'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


#TODO: use jsonify (and remove Exception handling)
#TODO: why POST ???
@login_required
def get_fields(request):
    """@return Fields for a model [('field1', 'field1_verbose_name'),...]"""
    POST = request.POST

    try:
        model = get_ct_or_404(int(get_from_POST_or_404(POST, 'ct_id'))).model_class()
        deep  = int(POST.get('deep', 1))
    except ValueError, e:
        msg    = str(e)
        status = 400
    except Http404, e:
        msg    = str(e)
        status = 404
    else:
        msg    = JSONEncoder().encode(get_flds_with_fk_flds_str(model, deep))
        status = 200

    return HttpResponse(msg, mimetype="text/javascript", status=status)

@login_required
def _get_ct_info(request, generator):
    try:
        ct = get_ct_or_404(int(get_from_POST_or_404(request.POST, 'ct_id')))
    except ValueError, e:
        status = 400
        msg    = str(e)
    except Http404, e:
        status = 404
        msg    = str(e)
    else:
        status = 200
        msg    = JSONEncoder().encode(generator(ct))

    return HttpResponse(msg, mimetype="text/javascript", status=status)


def get_custom_fields(request):
    """@return Custom fields for a model [('cfield1_name', 'cfield1_name'), ...]"""
    return _get_ct_info(request,
                        lambda ct: [(cf.name, cf.name) for cf in CustomField.objects.filter(content_type=ct)])

def get_function_fields(request):
    """@return functions fields for a model [('func_name', 'func_verbose_name'), ...]"""
    return _get_ct_info(request,
                        lambda ct: [(f_field.name, unicode(f_field.verbose_name)) for f_field in ct.model_class().function_fields])


@jsonify
def get_widget(request, ct_id):
    model             = get_ct_or_404(ct_id).model_class()
    POST = request.POST
    field_name        = get_from_POST_or_404(POST, 'field_name')
    field_value_name  = get_from_POST_or_404(POST, 'field_value_name')

    initial_value = None
    model_field, is_custom = EntitiesBulkUpdateForm.get_field(model, field_name)

    #TODO: manage invalid field ('model_field is None')
    #TODO: check if field is bulk_editable ?

    if is_custom:
        form_field  = model_field.get_formfield(None)
        form_field.choices = form_field.choices if hasattr(form_field, 'choices') else ()
        widget = _FIELDS_WIDGETS.get(model_field.get_value_class())

        object_id = POST.get('object_id')
        if object_id: # Inner edit case only in order to set current custom field value
            entity = CremeEntity.objects.get(pk=object_id)
            if entity.can_change(request.user):
                if model_field.field_type == CustomField.ENUM:
                    cf_values = model_field.get_value_class().objects.filter(custom_field=model_field.id, entity=entity.id)
                    initial_value = cf_values[0].value.id if cf_values else None
                elif model_field.field_type == CustomField.MULTI_ENUM:
                    cf_values = model_field.get_value_class().objects.filter(custom_field=model_field.id, entity=entity.id)
                    initial_value = cf_values[0].value.values_list('id', flat=True) if cf_values else None
                elif model_field.field_type == CustomField.BOOL:
                    cf_values = model_field.get_value_class().objects.filter(custom_field=model_field.id, entity=entity.id)
                    initial_value = cf_values[0].value if cf_values else None
                else:
                    initial_value = model_field.get_pretty_value(entity.id)
    else:
        form_field = model_field.formfield()
        form_field.choices = _get_choices(model_field, request.user)
        widget = _FIELDS_WIDGETS.get(model_field.__class__)

        object_id = POST.get('object_id')
        if object_id: # Inner edit case only in order to set current regular field value
            entity = CremeEntity.objects.get(pk=object_id)
            if entity.can_change(request.user):
                initial_value = getattr(entity.get_real_entity(), field_name)
                if isinstance(model._meta.get_field(field_name), ForeignKey) and initial_value is not None:
                    initial_value = initial_value.id
                elif isinstance(model._meta.get_field(field_name), ManyToManyField) and initial_value is not None:
                    initial_value = initial_value.all().values_list('id', flat=True)

    rendered = None

    if widget is None:
        rendered = form_field.widget.render(name=field_value_name, value=initial_value, attrs={'id': 'id_%s' % field_value_name})
    else:
        rendered = widget(field_value_name, form_field.choices, value=initial_value)

    return {'rendered': rendered}

@login_required
def clone(request):
    #TODO: Improve credentials ?
    entity_id = get_from_POST_or_404(request.POST, 'id')
    entity    = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

    user = request.user
    user.has_perm_to_create_or_die(entity)
    entity.can_view_or_die(user)

    new_entity = entity.clone()

    return HttpResponseRedirect(new_entity.get_absolute_url())

@login_required
def search_and_view(request):
    GET = request.GET
    model_ids = get_from_GET_or_404(GET, 'models').split(',')
    fields    = get_from_GET_or_404(GET, 'fields').split(',')
    value     = get_from_GET_or_404(GET, 'value')

    if not value: #avoid useless queries
        raise Http404(u'Void "value" arg')

    user = request.user
    has_perm = user.has_perm
    models = []

    for model_id in model_ids:
        try:
            ct = ContentType.objects.get_by_natural_key(*model_id.split('-'))
        except (ContentType.DoesNotExist, TypeError):
            raise Http404(u'These model does not exist: %s' % model_id)

        if not has_perm(ct.app_label):
            raise PermissionDenied(_(u"You are not allowed to acceed to this app"))

        model = ct.model_class()

        if issubclass(model, CremeEntity):
            models.append(model)

    if not models:
        raise Http404(u'No valid models')

    for model in models:
        query = Q()

        for field in fields:
            try:
                model._meta.get_field_by_name(field)
            except FieldDoesNotExist, e:
                pass
            else:
                query |= Q(**{str(field): value})

        if query: #avoid useless query
            found = EntityCredentials.filter(user, model.objects.filter(query))[:1]

            if found:
                return HttpResponseRedirect(found[0].get_absolute_url())

    raise Http404(_(u'No entity corresponding to your search was found.'))

_CUSTOM_NAME = 'custom_field_%s'

@login_required
def edit_field(request, id, field_str):
    user = request.user
    #entity = get_object_or_404(CremeEntity, pk=id)
    entity = get_object_or_404(CremeEntity, pk=id).get_real_entity()
    #model  = entity.entity_type.model_class()
    model  = entity.__class__

    field_name = _CUSTOM_NAME % int(field_str) if field_str.isdigit() else field_str

    #filtered = {True: [], False: []}
    #filtered[entity.can_change(user)].append(entity)
    entity.can_change_or_die(user)

    if request.method == 'POST':
        form = EntityInnerEditForm(model=model,
                                   field_name = field_name,
                                   #subjects=filtered[True],
                                   subject=entity,
                                   #forbidden_subjects=filtered[False],
                                   user=user,
                                   data=request.POST,
                                  )

        if form.is_valid():
            form.save()
    else:
        form = EntityInnerEditForm(model=model,
                                   field_name = field_name,
                                   #subjects=filtered[True],
                                   subject=entity,
                                   #forbidden_subjects=filtered[False],
                                   user=user,
                                  )

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {'form':  form,
                        'title': _(u'Inner update'),
                       },
                       is_valid=form.is_valid(),
                       reload=False, delegate_reload=True,
                      )

@login_required
def select_entity_for_merge(request, entity1_id):
    entity1 = get_object_or_404(CremeEntity, pk=entity1_id)

    user = request.user
    entity1.can_view_or_die(user); entity1.can_change_or_die(user)

    #TODO: filter viewable & deletable entities + (manage swapping ?)
    #TODO: change list_view_popup_from_widget code (o2m should be '1', but True works)
    return list_view_popup_from_widget(request, entity1.entity_type_id, o2m=True,
                                       extra_q=~Q(pk=entity1_id)
                                      )

@login_required
def merge(request, entity1_id, entity2_id):
    entity1 = get_object_or_404(CremeEntity, pk=entity1_id)
    entity2 = get_object_or_404(CremeEntity, pk=entity2_id)

    if entity1.entity_type_id != entity2.entity_type_id:
        raise Http404('You can not merge entities of different types.')

    user = request.user
    entity1.can_view_or_die(user); entity1.can_change_or_die(user)
    entity2.can_view_or_die(user); entity2.can_delete_or_die(user)

    #TODO: try to swap 1 & 2

    entity1 = entity1.get_real_entity()
    entity2 = entity2.get_real_entity()

    EntitiesMergeForm = merge_form_factory(entity1.__class__)

    if request.method == 'POST':
        merge_form = EntitiesMergeForm(user=request.user, data=request.POST,
                                       entity1=entity1, entity2=entity2
                                      )

        if merge_form.is_valid():
            merge_form.save()

            return HttpResponseRedirect(entity1.get_absolute_url())
    else:
        try:
            merge_form = EntitiesMergeForm(user=request.user, entity1=entity1, entity2=entity2)
        except MergeEntitiesBaseForm.CanNotMergeError as e:
            raise Http404(e)

    return render(request, 'creme_core/merge.html',
                  {'form':   merge_form,
                   'title': _('Merge <%(entity1)s> with <%(entity2)s>') % {
                                   'entity1': entity1,
                                   'entity2': entity2,
                                },
                    'help_message': _(u'You are going to merge two entities into a new one.\n'
                                      'Choose which information you want the old entities '
                                      'give to the new entity.\n'
                                      'The relationships, the properties and the other links '
                                      'with any of old entities will be automatically '
                                      'available in the new merged entity.'
                                     ),
                  }
                 )
