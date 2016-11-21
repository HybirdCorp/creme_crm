# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

import warnings

from django.db.transaction import atomic
from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext

from formtools.wizard.views import SessionWizardView

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.gui import block_registry
# from creme.creme_core.gui.block import SpecificRelationsBlock
from creme.creme_core.models.block import (CremeEntity, UserRole,
        BlockDetailviewLocation, BlockPortalLocation, BlockMypageLocation,
        RelationBlockItem, InstanceBlockConfigItem, CustomBlockConfigItem)
from creme.creme_core.registry import creme_registry, NotRegistered
from creme.creme_core.utils import get_from_POST_or_404, get_ct_or_404
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.generic import add_model_with_popup, edit_model_with_popup, inner_popup
from creme.creme_core.views.generic.wizard import PopupWizardMixin

from ..forms import blocks


def _get_configurable_ctype(ctype_id):
    ctype = get_ct_or_404(ctype_id)
    model = ctype.model_class()

    if not issubclass(model, CremeEntity):
        raise Http404('This model is not a CremeEntity.')

    if block_registry.is_model_invalid(model):
        raise Http404('This model cannot have a detail-view configuration.')

    return ctype


@login_required
@permission_required('creme_core.can_admin')
def add_detailview(request, ct_id):
    ctype = _get_configurable_ctype(ct_id)

    return add_model_with_popup(request, blocks.BlockDetailviewLocationsAddForm,
                                title=ugettext(u'New block configuration for «%s»') % ctype,
                                submit_label=_('Save the configuration'),
                                initial={'content_type': ctype},
                               )


@login_required
@permission_required('creme_core.can_admin')
def add_portal(request):
    warnings.warn("creme_config/blocks/portal/add is now deprecated. "
                  "Use creme_config/blocks/portal/wizard view instead.",
                  DeprecationWarning
                 )

    return add_model_with_popup(request, blocks.BlockPortalLocationsAddForm,
                                _(u'New blocks configuration'),
                                submit_label=_('Save the configuration'),
                               )  # TODO: title portal ???


class PortalBlockWizard(PopupWizardMixin, SessionWizardView):
    class _RelationStep(blocks.BlockPortalLocationsAddForm):
        step_submit_label = _('Select')

    class _ConfigStep(blocks.BlockPortalLocationsEditForm):
        step_prev_label = _('Previous step')
        step_submit_label = _('Save the configuration')

    form_list = (_RelationStep, _ConfigStep)
    wizard_title = _('New blocks configuration')
    template_name = 'creme_core/generics/blockform/add_wizard_popup.html'
    permission = 'creme_core.can_admin'

    def done(self, form_list, **kwargs):
        conf_step = form_list[1]

        # with atomic():
        conf_step.save()

        return HttpResponse(content_type='text/javascript')

    def get_form_kwargs(self, step):
        kwargs = super(PortalBlockWizard, self).get_form_kwargs(step)

        if step == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            kwargs['app_name'] = cleaned_data['app_name']
            kwargs['block_locations'] = ()

        return kwargs


@login_required
@permission_required('creme_core.can_admin')
def add_relation_block(request):
    # warnings.warn("creme_config/blocks/relation_block/add is now deprecated. "
    #               "Use creme_config/blocks/relation_block/wizard view instead.",
    #               DeprecationWarning
    #              )

    return add_model_with_popup(request, blocks.RelationBlockAddForm,
                                _(u'New type of block'),
                                submit_label=_('Save the block'),
                               )


# class RelationBlockWizard(PopupWizardMixin, SessionWizardView):
#     class _RelationStep(RelationBlockAddForm):
#         step_submit_label = _('Select')
#
#     class _ContentTypeStep(RelationBlockItemAddCtypesForm):
#         step_prev_label = _('Previous step')
#         step_submit_label = _('Save the block')
#
#     form_list = (_RelationStep, _ContentTypeStep)
#     wizard_title = _('New type of block')
#     template_name = 'creme_core/generics/blockform/add_wizard_popup.html'
#     permission = 'creme_core.can_admin'
#
#     def done(self, form_list, **kwargs):
#         ctype_step = form_list[1]
#
#         # with atomic():
#         ctype_step.save()
#
#         return HttpResponse(content_type='text/javascript')
#
#     def get_form_instance(self, step):
#         if step == '1':
#             cleaned_data = self.get_cleaned_data_for_step('0')
#             relation_type = cleaned_data['relation_type']
#
#             block_id = SpecificRelationsBlock.generate_id('creme_config', relation_type.id)
#             return RelationBlockItem(block_id=block_id, relation_type=relation_type)


@login_required
@permission_required('creme_core.can_admin')
def add_custom_block(request):
    warnings.warn("creme_config/blocks/custom/add is now deprecated. "
                  "Use creme_config/blocks/custom/wizard view instead.",
                  DeprecationWarning
                 )

    return add_model_with_popup(request, blocks.CustomBlockConfigItemCreateForm,
                                _(u'New custom block'),
                                submit_label=_('Save the block'),
                               )


class CustomBlockWizard(PopupWizardMixin, SessionWizardView):
    class _ResourceStep(blocks.CustomBlockConfigItemCreateForm):
        step_submit_label = _('Select')

    class _ConfigStep(blocks.CustomBlockConfigItemEditForm):
        class Meta(blocks.CustomBlockConfigItemEditForm.Meta):
            exclude = ('name',)

        step_prev_label = _('Previous step')
        step_submit_label = _('Save the block')

    form_list = (_ResourceStep, _ConfigStep)
    wizard_title = _('New custom block')
    template_name = 'creme_core/generics/blockform/add_wizard_popup.html'
    permission = 'creme_core.can_admin'

    def done(self, form_list, **kwargs):
        resource_step, conf_step = form_list

        with atomic():  # TODO: improve to do not save() twice
            conf_step.instance = resource_step.save()
            conf_step.save()

        return HttpResponse(content_type='text/javascript')

    def get_form_instance(self, step):
        if step == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            return CustomBlockConfigItem(name=cleaned_data['name'],
                                         content_type=cleaned_data['ctype'],
                                        )


@login_required
def portal(request):
    return render(request, 'creme_config/blocks_portal.html')


@login_required
@permission_required('creme_core.can_admin')
def edit_detailview(request, ct_id, role):
    if role == 'default':
        role_obj = None
        superuser = False
    elif role == 'superuser':
        role_obj = None
        superuser = True
    else:
        try:
            role_id = int(role)
        except ValueError:
            raise Http404('Role must be "default", "superuser" or an integer')

        role_obj = get_object_or_404(UserRole, id=role_id)
        superuser = False

    ct_id = int(ct_id)

    if ct_id:
        ct = _get_configurable_ctype(ct_id)

        if superuser:
            title = ugettext(u'Edit configuration of super-users for «%s»') % ct
        elif role_obj:
            title = ugettext(u'Edit configuration of «%(role)s» for «%(type)s»') % {
                            'role': role_obj,
                            'type': ct,
                        }
        else:
            title = ugettext(u'Edit default configuration for «%s»') % ct
    else:  # ct_id == 0
        if role != 'default':
            raise Http404('You can only edit "default" role with default config')

        ct = None
        title = _(u'Edit default configuration')

    return add_model_with_popup(request, blocks.BlockDetailviewLocationsEditForm,
                                initial={'content_type': ct,
                                         'role': role_obj, 'superuser': superuser,
                                        },
                                title=title,
                                template='creme_core/generics/blockform/edit_popup.html',
                                submit_label=_('Save the configuration'),
                               )


@login_required
@permission_required('creme_core.can_admin')
def edit_portal(request, app_name):
    if app_name == 'default':
        app_name = ''
        title = _(u'Edit default portal configuration')
    elif app_name == 'creme_core':
        title = _(u'Edit home configuration')
    else:
        try:
            app = creme_registry.get_app(app_name)
        except NotRegistered as e:
            raise Http404(str(e))

        title = ugettext(u'Edit portal configuration for «%s»') % app.verbose_name

    b_locs = BlockPortalLocation.objects.filter(app_name=app_name).order_by('order')

    if not b_locs:  # TODO: a default config must exist (it works for now because there is always 'assistants' app)
        raise Http404('This configuration does not exist (any more ?)')

    if request.method == 'POST':
        locs_form = blocks.BlockPortalLocationsEditForm(app_name=app_name, block_locations=b_locs, user=request.user,
                                                        data=request.POST,
                                                       )

        if locs_form.is_valid():
            locs_form.save()
    else:
        locs_form = blocks.BlockPortalLocationsEditForm(app_name=app_name, block_locations=b_locs, user=request.user)

    return inner_popup(request,
                       'creme_core/generics/blockform/edit_popup.html',
                       {'form':  locs_form,
                        'title': title,
                        'submit_label': _('Save the modifications'),
                       },
                       is_valid=locs_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


def _edit_mypage(request, title, user=None):
    if request.method == 'POST':
        locs_form = blocks.BlockMypageLocationsForm(owner=user, user=request.user, data=request.POST)

        if locs_form.is_valid():
            locs_form.save()
    else:
        locs_form = blocks.BlockMypageLocationsForm(owner=user, user=request.user)

    return inner_popup(request,
                       'creme_core/generics/blockform/edit_popup.html',
                       {'form':  locs_form,
                        'title': title,
                        'submit_label': _('Save the modifications'),
                       },
                       is_valid=locs_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


@login_required
@permission_required('creme_core.can_admin')
def edit_default_mypage(request):
    return _edit_mypage(request, _(u'Edit default "My page"'))


@login_required
def edit_mypage(request):
    return _edit_mypage(request, _(u'Edit "My page"'), user=request.user)


@login_required
@permission_required('creme_core.can_admin')
def add_ctypes_2_relation_block(request, rbi_id):
    warnings.warn("creme_config/blocks/relation_block/add_ctypes/{{rbi_id}} is now deprecated. "
                  "Use creme_config/blocks/relation_block/{{rbi_id}}/wizard view instead.",
                  DeprecationWarning
                 )

    return edit_model_with_popup(request, {'id': rbi_id}, RelationBlockItem,
                                 blocks.RelationBlockItemAddCtypesForm,
                                 ugettext(u'New customised types for «%s»'),
                                )


class RelationCTypeBlockWizard(PopupWizardMixin, SessionWizardView):
    class _ContentTypeStep(blocks.RelationBlockItemAddCtypeForm):
        step_submit_label = _('Select')

    class _FieldsStep(blocks.RelationBlockItemEditCtypeForm):
        step_prev_label = _('Previous step')
        step_submit_label = _('Save the configuration')

    form_list = (_ContentTypeStep, _FieldsStep)
    wizard_title = 'New customised type'  # Overridden by get_context_data()
    template_name = 'creme_core/generics/blockform/add_wizard_popup.html'
    permission = 'creme_core.can_admin'

    def done(self, form_list, **kwargs):
        form_list[1].save()

        return HttpResponse(content_type='text/javascript')

    def get_context_data(self, form, **kwargs):
        context = super(RelationCTypeBlockWizard, self).get_context_data(form, **kwargs)
        context['title'] = ugettext(u'New customised type for «%s»') % form.instance

        return context

    def get_form_instance(self, step):
        return get_object_or_404(RelationBlockItem, id=self.kwargs['rbi_id'])

    def get_form_kwargs(self, step):
        kwargs = super(RelationCTypeBlockWizard, self).get_form_kwargs(step)

        if step == '1':
            kwargs['ctype'] = self.get_cleaned_data_for_step('0')['ctype']

        return kwargs


@login_required
@permission_required('creme_core.can_admin')
def edit_ctype_of_relation_block(request, rbi_id, ct_id):
    ctype = get_ct_or_404(ct_id)
    rbi = get_object_or_404(RelationBlockItem, id=rbi_id)

    if rbi.get_cells(ctype) is None:
        raise Http404('This ContentType is not set in the RelationBlockItem')

    if request.method == 'POST':
        form = blocks.RelationBlockItemEditCtypeForm(user=request.user, data=request.POST,
                                                     instance=rbi, ctype=ctype,
                                                    )

        if form.is_valid():
            form.save()
    else:
        form = blocks.RelationBlockItemEditCtypeForm(user=request.user, instance=rbi, ctype=ctype)

    return inner_popup(request,
                       'creme_core/generics/blockform/edit_popup.html',
                       {'form':  form,
                        'title': ugettext(u'Edit «%s» configuration') % ctype,
                        'submit_label': _('Save the modifications'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


@POST_only
@login_required
@permission_required('creme_core.can_admin')
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
@permission_required('creme_core.can_admin')
def edit_custom_block(request, cbci_id):
    return edit_model_with_popup(request, {'id': cbci_id}, CustomBlockConfigItem,
                                 blocks.CustomBlockConfigItemEditForm,
                                 ugettext(u'Edit the block «%s»'),
                                )


@login_required
@permission_required('creme_core.can_admin')
def delete_detailview(request):
    POST = request.POST
    ct_id = get_from_POST_or_404(POST, 'id', int)

    if not ct_id:
        raise Http404('Default config can not be deleted')

    role_id = None
    superuser = False

    role = POST.get('role')
    if role:
        if role == 'superuser':
            superuser = True
        else:
            try:
                role_id = int(role)
            except ValueError:
                raise Http404('"role" argument must be "superuser" or an integer')

    BlockDetailviewLocation.objects.filter(content_type=ct_id,
                                           role=role_id, superuser=superuser,
                                          ).delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_portal(request):
    app_name = get_from_POST_or_404(request.POST, 'id')

    if app_name == 'creme_core':
        raise Http404('Home config can not be deleted')

    BlockPortalLocation.objects.filter(app_name=app_name).delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_default_mypage(request):
    get_object_or_404(BlockMypageLocation,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                      user=None,
                     ).delete()

    return HttpResponse()


@login_required
def delete_mypage(request):
    get_object_or_404(BlockMypageLocation,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                      user=request.user,
                     ).delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_relation_block(request):
    get_object_or_404(RelationBlockItem,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                     ).delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_instance_block(request):
    get_object_or_404(InstanceBlockConfigItem,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                     ).delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_custom_block(request):
    cbci_id = get_from_POST_or_404(request.POST, 'id')
    get_object_or_404(CustomBlockConfigItem, pk=cbci_id).delete()

    return HttpResponse()
