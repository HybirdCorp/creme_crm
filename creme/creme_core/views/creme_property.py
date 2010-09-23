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

from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, CremePropertyType, CremeProperty
from creme_core.entities_access.functions_for_permissions import edit_object_or_die
from creme_core.entities_access.permissions import user_has_edit_permission_for_an_object
from creme_core.views.generic import inner_popup
from creme_core.forms.creme_property import AddPropertiesForm


@login_required
def add_to_entities(request):
    POST = request.POST

    #TODO: a method get_or_404(POST, 'ids') ???
    try:
        entities_ids  = POST['ids']
        prop_type_id  = POST['type_id']
    except KeyError, e:
        raise Http404(str(e))

    property_type = get_object_or_404(CremePropertyType, pk=prop_type_id)

    return_str = ""
    get = CremeEntity.objects.get
    property_get = CremeProperty.objects.get

    #TODO: regroup queries ???
    for id in entities_ids.split(','):
        try:
            entity = get(pk=id)
        except CremeEntity.DoesNotExist:
            continue

        if not id.isdigit():
            debug('not digit ?!')
            continue

        if not user_has_edit_permission_for_an_object(request, entity):
            return_str += _(u'%s : <b>Permission denied</b>,') % entity
            continue

        try:
            property = property_get(type=property_type, creme_entity=entity)
        except CremeProperty.DoesNotExist:
            CremeProperty(type=property_type, creme_entity=entity).save()
        else:
            return_str += _(u'%(entity)s has already the property %(property)s,') % {'entity': entity, 'property': property}

    return_status = 200 if not return_str else 400
    return_str    = "%s" % return_str

    return HttpResponse(return_str, mimetype="text/javascript", status=return_status)

@login_required
def get_property_types_for_ct(request):
    ct = get_object_or_404(ContentType, pk=request.POST.get('ct_id')) #TODO: get ct_id or 404
    property_types = CremePropertyType.objects.filter(Q(subject_ctypes=ct) | Q(subject_ctypes__isnull=True))

    from django.core import serializers
    data = serializers.serialize('json', property_types, fields=('text',))

    return HttpResponse(data, mimetype='text/javascript')


#TODO: factorise in a generic add_to_entity_by_ipopup() view (see assistants etc...)
@login_required
def add_to_entity(request, entity_id):
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

    die_status = edit_object_or_die(request, entity)
    if die_status:
        return die_status

    if request.POST:
        prop_form = AddPropertiesForm(entity, request.POST)

        if prop_form.is_valid():
            prop_form.save()
    else:
        prop_form = AddPropertiesForm(entity=entity)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   prop_form,
                        'title':  _('New properties for <%s>') % entity,
                       },
                       is_valid=prop_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
def delete(request):
    """
        @Permissions : Edit on property's linked object
    """
    POST = request.POST

    try:
        entity_id   = POST['object_id']
        property_id = POST['id']
    except KeyError, e:
        raise Http404(str(e))

    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

    die_status = edit_object_or_die(request, entity)
    if die_status:
        return die_status

    property_ = get_object_or_404(CremeProperty, pk=property_id)
    property_.delete()

    return HttpResponse("")
