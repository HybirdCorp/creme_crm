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

from django.http import Http404, HttpResponse # HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType

from creme.creme_core.registry import creme_registry, NotRegistered
from creme.creme_core.models.block import (BlockDetailviewLocation, BlockPortalLocation, BlockMypageLocation,
        RelationBlockItem, InstanceBlockConfigItem, CustomBlockConfigItem)
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.generic import add_model_with_popup, edit_model_with_popup, inner_popup
from creme.creme_core.utils import get_from_POST_or_404, get_ct_or_404

from ..forms.blocks import (BlockDetailviewLocationsAddForm, BlockDetailviewLocationsEditForm,
        BlockPortalLocationsAddForm, BlockPortalLocationsEditForm,
        BlockMypageLocationsForm,
        RelationBlockAddForm, RelationBlockItemAddCtypesForm, RelationBlockItemEditCtypeForm,
        CustomBlockConfigItemCreateForm, CustomBlockConfigItemEditForm)


@login_required
@permission_required('creme_config.can_admin')
def add_detailview(request):
    return add_model_with_popup(request, BlockDetailviewLocationsAddForm, _(u'New blocks configuration')) #TODO: title detail view ???

@login_required
@permission_required('creme_config.can_admin')
def add_portal(request):
    return add_model_with_popup(request, BlockPortalLocationsAddForm, _(u'New blocks configuration')) #TODO: title portal ???

@login_required
@permission_required('creme_config.can_admin')
def add_relation_block(request):
    return add_model_with_popup(request, RelationBlockAddForm, _(u'New type of block'))

@login_required
@permission_required('creme_config.can_admin')
def add_custom_block(request):
    return add_model_with_popup(request, CustomBlockConfigItemCreateForm, _(u'New custom block'))

@login_required
@permission_required('creme_config')
def portal(request):
    return render(request, 'creme_config/blocks_portal.html')

@login_required
@permission_required('creme_config.can_admin')
def edit_detailview(request, ct_id):
    ct_id = int(ct_id)

    if ct_id:
        ct = ContentType.objects.get_for_id(ct_id)
        title = _(u'Edit configuration for %s') % ct
    else: #ct_id == 0
        ct = None
        title = _(u'Edit default configuration')

    b_locs = BlockDetailviewLocation.objects.filter(content_type=ct).order_by('order')

    if not b_locs: #TODO: a default config must exist (it works for now because there is always 'assistants' app)
        raise Http404('This configuration does not exist (any more ?)')

    if request.method == 'POST':
        locs_form = BlockDetailviewLocationsEditForm(ct=ct, block_locations=b_locs, user=request.user, data=request.POST)

        if locs_form.is_valid():
            locs_form.save()
    else:
        locs_form = BlockDetailviewLocationsEditForm(ct=ct, block_locations=b_locs, user=request.user)

    return inner_popup(request,
                       'creme_core/generics/blockform/edit_popup.html',
                       {'form':  locs_form,
                        'title': title,
                       },
                       is_valid=locs_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
@permission_required('creme_config.can_admin')
def edit_portal(request, app_name):
    if  app_name == 'default':
        app_name = ''
        title = _(u'Edit default portal configuration')
    elif app_name == 'creme_core':
        title = _(u'Edit home configuration')
    else:
        try:
            app = creme_registry.get_app(app_name)
        except NotRegistered as e:
            raise Http404(str(e))

        title = _(u'Edit portal configuration for <%s>') % app.verbose_name

    b_locs = BlockPortalLocation.objects.filter(app_name=app_name).order_by('order')

    if not b_locs: #TODO: a default config must exist (it works for now because there is always 'assistants' app)
        raise Http404('This configuration does not exist (any more ?)')

    if request.method == 'POST':
        locs_form = BlockPortalLocationsEditForm(app_name=app_name, block_locations=b_locs, user=request.user, data=request.POST)

        if locs_form.is_valid():
            locs_form.save()
    else:
        locs_form = BlockPortalLocationsEditForm(app_name=app_name, block_locations=b_locs, user=request.user)

    return inner_popup(request,
                       'creme_core/generics/blockform/edit_popup.html',
                       {'form':  locs_form,
                        'title': title,
                       },
                       is_valid=locs_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

def _edit_mypage(request, title, user=None):
    if request.method == 'POST':
        locs_form = BlockMypageLocationsForm(owner=user, user=request.user, data=request.POST)

        if locs_form.is_valid():
            locs_form.save()
    else:
        locs_form = BlockMypageLocationsForm(owner=user, user=request.user)

    return inner_popup(request,
                       'creme_core/generics/blockform/edit_popup.html',
                       {'form':  locs_form,
                        'title': title,
                       },
                       is_valid=locs_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
@permission_required('creme_config.can_admin')
def edit_default_mypage(request):
    return _edit_mypage(request, _(u'Edit default "My page"'))

@login_required
#@permission_required('my_page')
def edit_mypage(request):
    return _edit_mypage(request, _(u'Edit "My page"'), user=request.user)


@login_required
@permission_required('creme_config.can_admin')
def add_ctypes_2_relation_block(request, rbi_id):
    return edit_model_with_popup(request, {'id': rbi_id}, RelationBlockItem,
                                 RelationBlockItemAddCtypesForm,
                                 _(u'New customised types for <%s>'),
                                )

@login_required
@permission_required('creme_config.can_admin')
def edit_ctype_of_relation_block(request, rbi_id, ct_id):
    ctype = get_ct_or_404(ct_id)
    rbi = get_object_or_404(RelationBlockItem, id=rbi_id)

    if rbi.get_cells(ctype) is None:
        raise Http404('This ContentType is not set in the RelationBlockItem')

    if request.method == 'POST':
        form = RelationBlockItemEditCtypeForm(user=request.user, data=request.POST,
                                              instance=rbi, ctype=ctype,
                                             )

        if form.is_valid():
            form.save()
    else:
        form = RelationBlockItemEditCtypeForm(user=request.user, instance=rbi, ctype=ctype)

    return inner_popup(request,
                       'creme_core/generics/blockform/edit_popup.html',
                       {'form':  form,
                        'title': _(u'Edit <%s> configuration') % ctype,
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@POST_only
@login_required
@permission_required('creme_config.can_admin')
def delete_ctype_of_relation_block(request, rbi_id):
    ctype = get_ct_or_404(get_from_POST_or_404(request.POST, 'id'))
    rbi = get_object_or_404(RelationBlockItem, id=rbi_id)

    try:
        rbi.delete_cells(ctype)
    except KeyError:
        raise Http404('This ContentType is not set in the RelationBlockItem')

    rbi.save()

    return HttpResponse()

@login_required
@permission_required('creme_config.can_admin')
def edit_custom_block(request, cbci_id):
    return edit_model_with_popup(request, {'id': cbci_id}, CustomBlockConfigItem,
                                 CustomBlockConfigItemEditForm,
                                 _(u'Edit the block <%s>'),
                                )

    ##No popup version
    #cbci = get_object_or_404(CustomBlockConfigItem, id=cbci_id)

    #if request.method == 'POST':
        #POST = request.POST
        #cbci_form = CustomBlockConfigItemEditForm(user=request.user, data=POST, instance=cbci)

        #if cbci_form.is_valid():
            #cbci_form.save()

            #return HttpResponseRedirect('/creme_config/blocks/portal/')

        #cancel_url = POST.get('cancel_url')
    #else:
        #cbci_form = CustomBlockConfigItemEditForm(user=request.user, instance=cbci)
        #cancel_url = request.META.get('HTTP_REFERER')

    #return render(request, 'creme_core/generics/blockform/edit.html',
                  #{'form': cbci_form,
                   #'object': cbci,
                   #'cancel_url': cancel_url,
                   #'submit_label': _('Save the custom block'),
                  #}
                 #)

@login_required
@permission_required('creme_config.can_admin')
def delete_detailview(request):
    ct_id = get_from_POST_or_404(request.POST, 'id', int)

    if not ct_id:
        raise Http404('Default config can not be deleted')

    BlockDetailviewLocation.objects.filter(content_type=ct_id).delete()

    return HttpResponse()

@login_required
@permission_required('creme_config.can_admin')
def delete_portal(request):
    app_name = get_from_POST_or_404(request.POST, 'id')

    if app_name == 'creme_core':
        raise Http404('Home config can not be deleted')

    BlockPortalLocation.objects.filter(app_name=app_name).delete()

    return HttpResponse()

@login_required
@permission_required('creme_config.can_admin')
def delete_default_mypage(request):
    get_object_or_404(BlockMypageLocation, pk=get_from_POST_or_404(request.POST, 'id'), user=None).delete()

    return HttpResponse()

@login_required
def delete_mypage(request):
    get_object_or_404(BlockMypageLocation, pk=get_from_POST_or_404(request.POST, 'id'), user=request.user).delete()

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

    return HttpResponse()

@login_required
@permission_required('creme_config.can_admin')
def delete_custom_block(request):
    cbci_id = get_from_POST_or_404(request.POST, 'id')
    get_object_or_404(CustomBlockConfigItem, pk=cbci_id).delete()

    return HttpResponse()
