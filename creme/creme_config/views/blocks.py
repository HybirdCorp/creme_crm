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

from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import BlockConfigItem, RelationBlockItem, InstanceBlockConfigItem, BlockState
from creme_core.views.generic import add_model_with_popup, inner_popup
from creme_core.utils import get_from_POST_or_404

from creme_config.forms.blocks import BlocksAddForm, BlocksEditForm, BlocksPortalEditForm, RelationBlockAddForm


@login_required
@permission_required('creme_config.can_admin')
def add(request):
    return add_model_with_popup(request, BlocksAddForm, _(u'New blocks configuration'))

@login_required
@permission_required('creme_config.can_admin')
def add_relation_block(request):
    return add_model_with_popup(request, RelationBlockAddForm, _(u'New type of block'))

@login_required
@permission_required('creme_config.can_admin')
def portal(request):
    return render_to_response('creme_config/blocks_portal.html', {},
                              context_instance=RequestContext(request)
                             )

@login_required
@permission_required('creme_config.can_admin')
def _edit(request, ct_id, form_class, portal):
    ct_id = int(ct_id)
    bci = BlockConfigItem.objects.filter(content_type=ct_id or None).order_by('order')

    if not bci: #TODO: a default config must exist (it works for now because there is always 'assistants' app)
        raise Http404('This configuration does not exist (any more ?)')

    if request.method == 'POST':
        blocks_form = form_class(ct_id=ct_id, block_config_items=bci, user=request.user, data=request.POST)

        if blocks_form.is_valid():
            blocks_form.save()
    else:
        blocks_form = form_class(ct_id=ct_id, block_config_items=bci, user=request.user)

    if ct_id:
        title = _(u'Edit portal configuration for %s') if portal else _(u'Edit configuration for %s')
        title = title % ContentType.objects.get_for_id(ct_id)
    else:
        title = _(u'Edit home configuration') if portal else _(u'Edit default configuration')

    return inner_popup(request,
                       'creme_core/generics/blockform/edit_popup.html',
                       {
                        'form':  blocks_form,
                        'title': title,
                       },
                       is_valid=blocks_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request)
                      )

def edit(request, ct_id):
    return _edit(request, ct_id, BlocksEditForm, portal=False)

def edit_portal(request, ct_id):
    return _edit(request, ct_id, BlocksPortalEditForm, portal=True)

@login_required
@permission_required('creme_config.can_admin')
def delete(request):
    ct_id = get_from_POST_or_404(request.POST, 'id', int)

    if not ct_id:
        raise Http404('Default config can not be deleted')

    BlockConfigItem.objects.filter(content_type=ct_id).delete()

    return HttpResponse()

@login_required
@permission_required('creme_config.can_admin')
def delete_relation_block(request):
    get_object_or_404(RelationBlockItem, pk=get_from_POST_or_404(request.POST, 'id')).delete()

    return HttpResponse()

@login_required
@permission_required('creme_config.can_admin')
def delete_instance_block(request):
    block_id = get_from_POST_or_404(request.POST, 'id')
    get_object_or_404(InstanceBlockConfigItem, pk=block_id).delete()
    BlockState.objects.filter(block_id=block_id).delete()

    return HttpResponse()
