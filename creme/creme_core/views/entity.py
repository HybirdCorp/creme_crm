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

from django.core.exceptions import PermissionDenied
from django.db.models import Q, FieldDoesNotExist, ForeignKey
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, get_list_or_404, render
from django.core import serializers
from django.forms.models import modelform_factory, model_to_dict
from django.utils.translation import ugettext as _
from django.utils.simplejson import JSONEncoder
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.models import CremeEntity, CustomField, EntityCredentials
from creme_core.gui.bulk_update import bulk_update_registry
from creme_core.forms import CremeEntityForm
from creme_core.forms.bulk import _get_choices, EntitiesBulkUpdateForm, _FIELDS_WIDGETS, EntityInnerEditForm
from creme_core.forms.merge import form_factory as merge_form_factory, MergeEntitiesBaseForm
from creme_core.views.generic import inner_popup, list_view_popup_from_widget
from creme_core.utils import get_ct_or_404, get_from_POST_or_404, get_from_GET_or_404, jsonify
from creme_core.utils.meta import ModelFieldEnumerator #get_flds_with_fk_flds_str


@login_required
@jsonify
def get_creme_entities_repr(request, entities_ids):
    entities = CremeEntity.objects.filter(pk__in=[id for id in entities_ids.split(',') if id])
    user = request.user

    #TODO: populate real entities....

    return [{'id': entity.id,
             'text': entity.get_real_entity().get_entity_summary(user) if entity.can_view(user) else \
                     _(u'Entity #%s (not viewable)') % entity.id
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

    return HttpResponse(serializers.serialize('json', data, fields=fields),
                        mimetype="text/javascript", status=status,
                       )


#TODO: use fields tags
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
    required_fields = [name for name, field in form.fields.iteritems()
                           if field.required and name != 'user'
                      ]

    if len(required_fields) == 1:
        required_field = required_fields[0]
        format  = _(u'%s [CREATION]')
        printer = lambda field: unicode(field.verbose_name) if field.name != required_field else \
                                format % field.verbose_name
    else:
        printer = lambda field: unicode(field.verbose_name)

    return [(field.name, printer(field))
                for field in model._meta.fields
                    if field.name not in EXCLUDED_FIELDS and not isinstance(field, ForeignKey)
           ]

@login_required
def bulk_update(request, ct_id):#TODO: Factorise with add_properties_bulk and add_relations_bulk?
    user = request.user
    model    = get_ct_or_404(ct_id).model_class()
    entities = get_list_or_404(model, pk__in=request.REQUEST.getlist('ids'))

    CremeEntity.populate_real_entities(entities)
    entities = [entity.get_real_entity() for entity in entities]

    #CremeEntity.populate_credentials(entities, user)

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
    except ValueError as e:
        msg    = str(e)
        status = 400
    except Http404 as e:
        msg    = str(e)
        status = 404
    else:
        #msg    = JSONEncoder().encode(get_flds_with_fk_flds_str(model, deep))
        msg = JSONEncoder().encode(ModelFieldEnumerator(model, deep=1, only_leafs=True) #TODO: use deep ??
                                       .filter(viewable=True)
                                       .choices()
                                  )
        status = 200

    return HttpResponse(msg, mimetype="text/javascript", status=status)

@login_required
def _get_ct_info(request, generator):
    try:
        ct = get_ct_or_404(int(get_from_POST_or_404(request.POST, 'ct_id')))
    except ValueError as e:
        status = 400
        msg    = str(e)
    except Http404 as e:
        status = 404
        msg    = str(e)
    else:
        status = 200
        msg    = JSONEncoder().encode(generator(ct))

    return HttpResponse(msg, mimetype="text/javascript", status=status)


def get_custom_fields(request):
    """@return Custom fields for a model [('cfield1_name', 'cfield1_name'), ...]"""
    return _get_ct_info(request,
                        lambda ct: [(cf.name, cf.name)
                                        for cf in CustomField.objects.filter(content_type=ct)
                                   ]
                       )

def get_function_fields(request):
    """@return functions fields for a model [('func_name', 'func_verbose_name'), ...]"""
    return _get_ct_info(request,
                        lambda ct: [(f_field.name, unicode(f_field.verbose_name)) 
                                        for f_field in ct.model_class().function_fields
                                   ]
                       )


@jsonify
def get_widget(request, ct_id):
    model               = get_ct_or_404(ct_id).model_class()
    POST                = request.POST
    field_name          = get_from_POST_or_404(POST, 'field_name')
    field_value_name    = get_from_POST_or_404(POST, 'field_value_name')
    inner_edit_obj_id   = POST.get('object_id')

    model_field, is_custom = EntitiesBulkUpdateForm.get_field(model, field_name)

    # Check if model field really exists
    if model_field is None:
        raise Http404(u'Unknown field')

    # Set up context and credentials for inner edit case
    if inner_edit_obj_id:
        object = model.objects.get(pk=inner_edit_obj_id)
        owner = object.get_related_entity() if hasattr(object, 'get_related_entity') else object
        owner.can_change_or_die(request.user)
        is_updatable = bulk_update_registry.is_bulk_updatable(model, field_name, exclude_unique=False)
    else:
        is_updatable = bulk_update_registry.is_bulk_updatable(model, field_name)

    # Prepare form field with custom widget if needed and initial value according to edit type
    if is_custom:
        if inner_edit_obj_id:
            #TODO why get_custom_value doesnt seem to work when populate custom values has not been called
            CremeEntity.populate_custom_values([object], [model_field])
            form_field = model_field.get_formfield(object.get_custom_value(model_field))
        else:
            form_field = model_field.get_formfield(None)
    elif is_updatable:
        form_field = model_field.formfield()
        form_field.choices = _get_choices(model_field, request.user)
        form_field.widget = _FIELDS_WIDGETS.get(model_field.__class__) or form_field.widget

        if inner_edit_obj_id:
            form_field.initial = model_to_dict(object, [field_name])[field_name]

    return {'rendered': form_field.widget.render(name=field_value_name,
                                                 value=form_field.initial,
                                                 attrs={'id': 'id_%s' % field_value_name},
                                                ),
           }

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
            except FieldDoesNotExist:
                pass
            else:
                query |= Q(**{str(field): value})

        if query: #avoid useless query
            found = EntityCredentials.filter(user, model.objects.filter(query))[:1]

            if found:
                return HttpResponseRedirect(found[0].get_absolute_url())

    raise Http404(_(u'No entity corresponding to your search was found.'))

@login_required
def edit_field(request, ct_id, id, field_str):
    user   = request.user
    model  = get_ct_or_404(ct_id).model_class()
    entity = get_object_or_404(model, pk=id)

    owner = entity.get_related_entity() if hasattr(entity, 'get_related_entity') else entity
    owner.can_change_or_die(user)

    try:
        if request.method == 'POST':
            form = EntityInnerEditForm(model=model,
                                       field_id=field_str,
                                       subject=entity,
                                       user=user,
                                       data=request.POST,
                                      )

            if form.is_valid():
                form.save()
        else:
            form = EntityInnerEditForm(model=model,
                                       field_id=field_str,
                                       subject=entity,
                                       user=user,
                                      )
    except EntityInnerEditForm.InvalidField as e:
        raise Http404(e)

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
