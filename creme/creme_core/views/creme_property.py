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

#from django.db.models import Q
#from django.http import HttpResponse
from django.shortcuts import get_list_or_404 #get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from ..models import CremeEntity #CremePropertyType
from ..forms.creme_property import AddPropertiesForm, AddPropertiesBulkForm
from ..utils import get_ct_or_404 #, get_from_POST_or_404
from .generic import inner_popup, add_to_entity as generic_add_to_entity


@login_required
def add_properties_bulk(request, ct_id):#TODO: Factorise with add_relations_bulk and bulk_update?
    user     = request.user
    model    = get_ct_or_404(ct_id).model_class()
    entities = get_list_or_404(model, pk__in=request.REQUEST.getlist('ids'))

    CremeEntity.populate_real_entities(entities)
    #CremeEntity.populate_credentials(entities, user)

    filtered = {True: [], False: []}
    for entity in entities:
        filtered[entity.can_change(user)].append(entity)

    if request.method == 'POST':
        form = AddPropertiesBulkForm(model=model,
                                     entities=filtered[True],
                                     forbidden_entities=filtered[False],
                                     user=request.user,
                                     data=request.POST
                                    )

        if form.is_valid():
            form.save()
    else:
        form = AddPropertiesBulkForm(model=model,
                                     entities=filtered[True],
                                     forbidden_entities=filtered[False],
                                     user=request.user
                                    )

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':  form,
                        'title': _(u'Multiple adding of properties'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

#Commented on 21 february 2012
#@login_required
#def get_property_types_for_ct(request):
    #ct = get_ct_or_404(get_from_POST_or_404(request.POST, 'ct_id'))
    #property_types = CremePropertyType.objects.filter(Q(subject_ctypes=ct) | Q(subject_ctypes__isnull=True)) #todo: in a CremeProperty method ??

    #from django.core import serializers
    #data = serializers.serialize('json', property_types, fields=('text',))

    #return HttpResponse(data, mimetype='text/javascript')

@login_required
def add_to_entity(request, entity_id):
    return generic_add_to_entity(request, entity_id, AddPropertiesForm, _('New properties for <%s>'))
