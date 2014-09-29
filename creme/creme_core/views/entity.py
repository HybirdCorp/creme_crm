# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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
import logging

from django.core.exceptions import PermissionDenied
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, FieldDoesNotExist, ProtectedError
from django.forms.models import modelform_factory
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, get_list_or_404, render, redirect
#from django.core import serializers
#from django.utils.encoding import smart_unicode
#from django.utils.formats import date_format
#from django.utils.simplejson import JSONEncoder
#from django.utils.timezone import localtime
from django.utils.translation import ugettext as _

from ..auth.decorators import login_required
from ..core.exceptions import ConflictError
from ..forms import CremeEntityForm
from ..forms.bulk import BulkDefaultEditForm, BulkForm
from ..forms.merge import form_factory as merge_form_factory, MergeEntitiesBaseForm
from ..gui.bulk_update import bulk_update_registry
from ..models import CremeEntity, EntityCredentials #CustomField
from ..utils import get_ct_or_404, get_from_POST_or_404, get_from_GET_or_404, jsonify
from ..utils.meta import ModelFieldEnumerator
from ..views.generic import inner_popup, list_view_popup_from_widget
from ..views.decorators import POST_only

logger = logging.getLogger(__name__)

@login_required
@jsonify
def get_creme_entities_repr(request, entities_ids):
    entities = CremeEntity.objects.filter(pk__in=[id for id in entities_ids.split(',') if id])
    user = request.user
    has_perm = user.has_perm_to_view

    CremeEntity.populate_real_entities(entities)

    return [{'id': entity.id,
             'text': entity.get_real_entity().get_entity_summary(user) if has_perm(entity) else
                     _(u'Entity #%s (not viewable)') % entity.id
            } for entity in entities
           ]


#TODO: bake the result in HTML instead of ajax view ??
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

    kwargs = {}
    if len(required_fields) == 1:
        required_field = required_fields[0]
        kwargs['printer'] = lambda field: unicode(field.verbose_name) \
                                            if field.name != required_field else \
                                          _(u'%s [CREATION]') % field.verbose_name

    return ModelFieldEnumerator(model).filter(viewable=True).choices(**kwargs)


@login_required
# def bulk_update(request, ct_id):#TODO: Factorise with add_properties_bulk and add_relations_bulk?
#     user = request.user
#     model    = get_ct_or_404(ct_id).model_class()
#     entities = get_list_or_404(model, pk__in=request.REQUEST.getlist('ids'))
# 
#     CremeEntity.populate_real_entities(entities)
#     entities = [entity.get_real_entity() for entity in entities]
# 
#     filtered = {True: [], False: []}
#     has_perm = user.has_perm_to_change
# 
#     for entity in entities:
#         filtered[has_perm(entity)].append(entity)
# 
#     if request.method == 'POST':
#         form = EntitiesBulkUpdateForm(model=model,
#                                       subjects=filtered[True],
#                                       forbidden_subjects=filtered[False],
#                                       user=user,
#                                       data=request.POST,
#                                      )
# 
#         if form.is_valid():
#             form.save()
#     else:
#         form = EntitiesBulkUpdateForm(model=model,
#                                       subjects=filtered[True],
#                                       forbidden_subjects=filtered[False],
#                                       user=user,
#                                      )
# 
#     return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
#                        {'form':  form,
#                         'title': _(u'Multiple update'),
#                        },
#                        is_valid=form.is_valid(),
#                        reload=False,
#                        delegate_reload=True,
#                       )

#Commented on 25/01/2014
#todo: use jsonify (and remove Exception handling)
#todo: why POST ???
#@login_required
#def get_fields(request):
    #"""@return Fields for a model [('field1', 'field1_verbose_name'),...]"""
    #POST = request.POST

    #try:
        #model = get_ct_or_404(int(get_from_POST_or_404(POST, 'ct_id'))).model_class()
        #deep  = int(POST.get('deep', 1))
    #except ValueError as e:
        #msg    = str(e)
        #status = 400
    #except Http404 as e:
        #msg    = str(e)
        #status = 404
    #else:
        ##msg    = JSONEncoder().encode(get_flds_with_fk_flds_str(model, deep))
        #msg = JSONEncoder().encode(ModelFieldEnumerator(model, deep=1, only_leafs=True) #todo: use deep ??
                                       #.filter(viewable=True)
                                       #.choices()
                                  #)
        #status = 200

    #return HttpResponse(msg, mimetype="text/javascript", status=status)

#Commented on 25/01/2014
#todo: use jsonify (and remove Exception handling)
#@login_required
#def _get_ct_info(request, generator):
    #try:
        #ct = get_ct_or_404(int(get_from_POST_or_404(request.POST, 'ct_id')))
    #except ValueError as e:
        #status = 400
        #msg    = str(e)
    #except Http404 as e:
        #status = 404
        #msg    = str(e)
    #else:
        #status = 200
        #msg    = JSONEncoder().encode(generator(ct))

    #return HttpResponse(msg, mimetype="text/javascript", status=status)

#Commented on 25/01/2014
#@login_required
#def get_custom_fields(request):
    #"@return Custom fields for a model [('cfield1_id', 'cfield1_name'), ...]"
    #return _get_ct_info(request,
                        #lambda ct: list(CustomField.objects.filter(content_type=ct)
                                                           #.values_list('id', 'name')
                                       #)
                       #)

#Commented on 25/01/2014
#@login_required
#def get_function_fields(request):
    #"""@return functions fields for a model [('func_name', 'func_verbose_name'), ...]"""
    #return _get_ct_info(request,
                        #lambda ct: [(f_field.name, unicode(f_field.verbose_name)) 
                                        #for f_field in ct.model_class().function_fields
                                   #]
                       #)

# @login_required
# @jsonify
# def get_widget(request, ct_id):
#     model      = get_ct_or_404(ct_id).model_class()
#     GET        = request.GET
#     field_name = get_from_GET_or_404(GET, 'field_name')
#     entity_id  = GET.get('object_id')
# 
#     model_field, is_custom = EntitiesBulkUpdateForm.get_field(model, field_name)
# 
#     if model_field is None:
#         raise Http404(u"The field %s.%s doesn't exist" % (model._meta.verbose_name, field_name))
# 
#     instance = get_object_or_404(model, pk=entity_id) if entity_id else None
# 
#     if instance:
#         #TODO: factorise this credentials test ?
#         owner = instance.get_related_entity() if hasattr(instance, 'get_related_entity') else instance
#         request.user.has_perm_to_change_or_die(owner)
# 
#         is_updatable = bulk_update_registry.is_updatable(model, field_name, exclude_unique=False)
#     else: # Bulk edition
#         is_updatable = bulk_update_registry.is_updatable(model, field_name)
# 
#     # Prepare form field with custom widget if needed and initial value according to edit type
#     if is_custom:
#         form_field = EntitiesBulkUpdateForm.get_custom_formfield(model_field, instance)
#     else:
#         if not is_updatable:
#             raise Http404(u'The field %s.%s is not editable' % (model._meta.verbose_name, field_name))
# 
#         form_field = EntitiesBulkUpdateForm.get_updatable_formfield(model_field, request.user, instance)
# 
#     return {'rendered': form_field.widget.render(name='field_value',
#                                                  value=form_field.initial,
#                                                  attrs={'id': 'id_field_value'},
#                                                 ),
#            }

@login_required
def clone(request):
    #TODO: Improve credentials ?
    entity_id = get_from_POST_or_404(request.POST, 'id')
    entity    = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

    user = request.user
    user.has_perm_to_create_or_die(entity)
    user.has_perm_to_view_or_die(entity)

    new_entity = entity.clone()

    return redirect(new_entity)

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
            raise PermissionDenied(_(u"You are not allowed to access to this app"))

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
                return redirect(found[0])

    raise Http404(_(u'No entity corresponding to your search was found.'))

def _bulk_has_perm(entity, user):
    owner = entity.get_related_entity() if hasattr(entity, 'get_related_entity') else entity
    return user.has_perm_to_change(owner)

@login_required
def inner_edit_field(request, ct_id, id, field_name):
    user   = request.user
    model  = get_ct_or_404(ct_id).model_class()
    entity = get_object_or_404(model, pk=id)

    if not _bulk_has_perm(entity, user):
        raise PermissionDenied(_(u'You are not allowed to edit this entity'))

    bulk_status = bulk_update_registry.status(model)

    field_name = field_name if field_name is not None else bulk_status.updatables().next().name
    form_class = bulk_status.innerforms.get(field_name, BulkDefaultEditForm)

    try:
        if request.method == 'POST':
            form = form_class(model=model,
                              field_name=field_name,
                              entities=[entity],
                              user=user,
                              data=request.POST,
                             )

            if form.is_valid():
                form.save()
        else:
            form = form_class(model=model,
                              field_name=field_name,
                              entities=[entity],
                              user=user,
                             )
    except BulkForm.FieldDoesNotExist as e:
        raise Http404(e)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {'form':  form,
                        'title': _(u'Edit «%s»') % unicode(entity),
                       },
                       is_valid=form.is_valid(),
                       reload=False, delegate_reload=True,
                      )

@login_required
def bulk_edit_field(request, ct_id, id, field_name):
    user   = request.user
    model  = get_ct_or_404(ct_id).model_class()
    entities = get_list_or_404(model, pk__in=id.split(','))

    filtered = [e for e in entities if _bulk_has_perm(e, user)]

    if not filtered:
        raise PermissionDenied(_(u'You are not allowed to edit these entities'))

    bulk_status = bulk_update_registry.status(model)

    field_name = field_name if field_name is not None else bulk_status.updatables().next().name
    form_class = bulk_status.innerforms.get(field_name, BulkDefaultEditForm)

    try:
        if request.method == 'POST':
            form = form_class(model=model,
                              field_name=field_name,
                              entities=filtered,
                              user=user,
                              data=request.POST,
                              is_bulk=True,
                             )

            if form.is_valid():
                form.save()
                return render(request, 'creme_core/frags/bulk_process_report.html',
                              {'form':  form,
                               'title': _(u'Multiple update'),
                              },)
        else:
            form = form_class(model=model,
                              field_name=field_name,
                              entities=filtered,
                              user=user,
                              is_bulk=True,
                             )
    except BulkForm.FieldDoesNotExist as e:
        raise Http404(e)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {'form':  form,
                        'title': _(u'Multiple update')
                       },
                       is_valid=form.is_valid(),
                       reload=False, delegate_reload=True,
                      )

@login_required
def select_entity_for_merge(request, entity1_id):
    entity1 = get_object_or_404(CremeEntity, pk=entity1_id)

    user = request.user
    user.has_perm_to_view_or_die(entity1); user.has_perm_to_change_or_die(entity1)

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
        #raise Http404('You can not merge entities of different types.')
        raise ConflictError('You can not merge entities of different types.')

    user = request.user
    can_view = user.has_perm_to_view_or_die
    can_view(entity1); user.has_perm_to_change_or_die(entity1)
    can_view(entity2); user.has_perm_to_delete_or_die(entity2)

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

            return redirect(entity1)
    else:
        try:
            merge_form = EntitiesMergeForm(user=request.user, entity1=entity1, entity2=entity2)
        except MergeEntitiesBaseForm.CanNotMergeError as e:
            #raise Http404(e)
            raise ConflictError(e)

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

@login_required
def trash(request):
    return render(request, 'creme_core/trash.html')

@login_required
@POST_only
def empty_trash(request):

    user = request.user
    errors = []

    #NB: we do not use delete() method of queryset in order to send signals
    for entity in EntityCredentials.filter(user,
                                           #CremeEntity.objects.only_deleted(),
                                           CremeEntity.objects.filter(is_deleted=True),
                                           EntityCredentials.DELETE
                                          ):
        #TODO:
        #if entity.get_delete_absolute_url() != CremeEntity.get_delete_absolute_url(entity):
            #errors[404].append(_('%s does not use the generic deletion view.') % entity.allowed_unicode(user))

        try:
            entity.delete()
        except ProtectedError:
            errors.append(_(u'"%s" can not be deleted because of its dependencies.') %
                            entity.allowed_unicode(user)
                         )

    #TODO: factorise ??
    if not errors:
        status = 200
        message = _('Operation successfully completed')
    else:
        status = 409
        message = _('The following entities cannot be deleted') + '<ul>' + '\n'.join('<li>' + msg + '</li>' for msg in errors) + '</ul>'

    return HttpResponse(message, mimetype='text/javascript', status=status)

@login_required
@POST_only
def restore_entity(request, entity_id):
    entity = get_object_or_404(CremeEntity.objects.filter(is_deleted=True), pk=entity_id) \
                                                  .get_real_entity()

    if entity.get_delete_absolute_url() != CremeEntity.get_delete_absolute_url(entity):
        raise Http404(_(u'This model does not use the generic deletion view.'))

    if hasattr(entity, 'get_related_entity'):
        raise Http404('Can not restore an auxiliary entity') #see trash_entity()

    request.user.has_perm_to_delete_or_die(entity)
    entity.restore()

    if request.is_ajax():
        return HttpResponse(mimetype='text/javascript')

    return redirect(entity)


def _delete_entity(user, entity):
    if entity.get_delete_absolute_url() != CremeEntity.get_delete_absolute_url(entity):
        return 404, _('%s does not use the generic deletion view.') % entity.allowed_unicode(user)

    if hasattr(entity, 'get_related_entity'):
        related = entity.get_related_entity()

        if related is None:
            logger.critical('delete_entity(): an auxiliary entity seems orphan (id=%s)', entity.id)
            return 403, _(u'You are not allowed to delete this entity: %s') % entity.allowed_unicode(user)

        if not user.has_perm_to_change(related):
            return 403, _(u'%s : <b>Permission denied</b>,') % entity.allowed_unicode(user)

        entity.relations.exclude(type__is_internal=True).delete()
        #entity.properties.all().delete()
        trash = False
    else:
        if not user.has_perm_to_delete(entity):
            return 403, _(u'%s : <b>Permission denied</b>,') % entity.allowed_unicode(user)

        trash = not entity.is_deleted

    try:
        if trash:
            entity.trash()
        else:
            entity.delete()
    except ProtectedError as e:
        return (400,
                _(u'"%s" can not be deleted because of its dependencies.') %
                    entity.allowed_unicode(user),
                {'protected_objects': e.args[1]},
               )


@login_required
def delete_entities(request):
    "Delete several CremeEntities, with a Ajax call (POST method)."
    try:
        entity_ids = [int(e_id) for e_id in get_from_POST_or_404(request.POST, 'ids').split(',') if e_id]
    except ValueError:
        return HttpResponse('Bad POST argument', mimetype='text/javascript', status=400)

    if not entity_ids:
        return HttpResponse(_('No selected entities'), mimetype='text/javascript', status=400)

    logger.debug('delete_entities() -> ids: %s ', entity_ids)

    user     = request.user
    entities = list(CremeEntity.objects.filter(pk__in=entity_ids))
    errors   = defaultdict(list)

    len_diff = len(entity_ids) - len(entities)
    if len_diff:
        errors[404].append(_(u"%s entities doesn't exist / doesn't exist any more") % len_diff)

    CremeEntity.populate_real_entities(entities)

    for entity in entities:
        error = _delete_entity(user, entity.get_real_entity())
        if error:
            errors[error[0]].append(error[1]) #TODO: use error[2] if exists ??

    if not errors:
        status = 200
        message = _('Operation successfully completed')
    else:
        status = min(errors.iterkeys())
        message = ",".join(msg for error_messages in errors.itervalues() for msg in error_messages)

    return HttpResponse(message, mimetype='text/javascript', status=status)

@login_required
#TODO: @redirect_if_not_ajax
@POST_only
def delete_entity(request, entity_id):
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()
    error = _delete_entity(request.user, entity)

    if error:
        #code, msg = error #TODO: Python3 => code, msg, *args = error
        code, msg, args = error if len(error) == 3 else error + ({},)

        if code == 404: raise Http404(msg)
        #if code == 403: raise PermissionDenied(msg)

        #if request.is_ajax():
            #return HttpResponse(smart_unicode(msg), mimetype='text/javascript', status=code)

        raise PermissionDenied(msg, args)

    if request.is_ajax():
        return HttpResponse(mimetype='text/javascript')

    return HttpResponseRedirect(entity.get_lv_absolute_url())

@login_required
def delete_related_to_entity(request, ct_id):
    """Delete a model related to a CremeEntity.
    @param request Request with POST method ; POST data should contain an 'id'(=pk) value.
    @param model A django model class that implements the method get_related_entity().
    """
    model = get_ct_or_404(ct_id).model_class()
    if issubclass(model, CremeEntity):
        raise Http404('This view can not delete CremeEntities.')

    auxiliary = get_object_or_404(model, pk=get_from_POST_or_404(request.POST, 'id'))
    entity = auxiliary.get_related_entity()

    request.user.has_perm_to_change_or_die(entity)

    try:
        auxiliary.delete()
    except ProtectedError as e:
        #msg = e.args[0]

        #if request.is_ajax():
            #return HttpResponse(smart_unicode(msg), mimetype="text/javascript", status=400)

        #raise Http404(unicode(msg)) #todo enhance 404 rendering to use the message...
        raise PermissionDenied(e.args[0])

    if request.is_ajax():
        return HttpResponse(mimetype='text/javascript')

    return redirect(entity)
