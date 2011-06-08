# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from django.shortcuts import get_object_or_404, get_list_or_404
from django.core import serializers
from django.forms.models import modelform_factory
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.utils.simplejson import JSONEncoder
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.models import CremeEntity, CustomField, EntityCredentials
from creme_core.forms import CremeEntityForm
from creme_core.forms.bulk import _get_choices, EntitiesBulkUpdateForm, _FIELDS_WIDGETS
from creme_core.views.generic.popup import inner_popup
from creme_core.utils import get_ct_or_404, get_from_POST_or_404, get_from_GET_or_404, jsonify
from creme_core.utils.meta import get_flds_with_fk_flds_str

#Commented 19 may 2011 (its url too)
#@login_required
#def get_creme_entity_repr(request, entity_id):
#    entity = get_object_or_404(CremeEntity, pk=entity_id)
#    entity.can_view_or_die(request.user)
#
#    return HttpResponse(entity.get_real_entity().get_entity_summary(), mimetype="text/javascript")

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
def bulk_update(request, ct_id, ids):
    user = request.user
    model    = get_object_or_404(ContentType, pk=ct_id).model_class()
    entities = get_list_or_404(model, pk__in=[id for id in ids.split(',') if id])

    CremeEntity.populate_real_entities(entities)
    CremeEntity.populate_credentials(entities, user)

    filtered = {True: [], False: []}
    for entity in entities:
        filtered[entity.can_change(user)].append(entity)


    if request.method == 'POST':
        form = EntitiesBulkUpdateForm(model=model,
                                      subjects=filtered[True],
                                      forbidden_subjects=filtered[False],
                                      user=request.user,
                                      data=request.POST)

        if form.is_valid():
            form.save()
    else:
        form = EntitiesBulkUpdateForm(model=model,
                                      subjects=filtered[True],
                                      forbidden_subjects=filtered[False],
                                      user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {
                        'form':  form,
                        'title': _(u'Multiple update'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))


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
    field_name        = get_from_POST_or_404(request.POST, 'field_name')
    field_value_name  = get_from_POST_or_404(request.POST, 'field_value_name')

    if EntitiesBulkUpdateForm.is_custom_field(field_name):
        model_field = CustomField.objects.get(pk=EntitiesBulkUpdateForm.get_custom_field_id(field_name))
        form_field  = model_field.get_formfield(None)
        form_field.choices = form_field.choices if hasattr(form_field, 'choices') else ()
        widget = _FIELDS_WIDGETS.get(model_field.get_value_class())
    else:
        model_field = model._meta.get_field(field_name)
        form_field = model_field.formfield()
        form_field.choices = _get_choices(model_field, request.user)
        widget = _FIELDS_WIDGETS.get(model_field.__class__)

    rendered = None

    if widget is None:
        rendered = form_field.widget.render(name=field_value_name, value=None, attrs={'id': 'id_%s' % field_value_name})

    else:
        rendered=widget(field_value_name, form_field.choices)

    return {
        'rendered': rendered
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
            except FieldDoesNotExist, e:
                pass
            else:
                query |= Q(**{str(field): value})

        if query: #avoid useless query
            found = EntityCredentials.filter(user, model.objects.filter(query))[:1]

            if found:
                return HttpResponseRedirect(found[0].get_absolute_url())

    raise Http404(_(u'No entity corresponding to your search was found.'))
