# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

# import warnings

# from django.apps import apps
from django.db.transaction import atomic
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from formtools.wizard.views import SessionWizardView

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.bricks import brick_registry
from creme.creme_core.models import (UserRole,  # CremeEntity
        BrickDetailviewLocation, BrickHomeLocation, BrickMypageLocation,
        RelationBrickItem, InstanceBrickConfigItem, CustomBrickConfigItem)
from creme.creme_core.utils import get_from_POST_or_404, get_ct_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.generic.wizard import PopupWizardMixin

from ..forms import bricks

from .base import BaseConfigCreation
from .portal import _config_portal


# def _get_configurable_ctype(ctype_id):
#     ctype = get_ct_or_404(ctype_id)
#     model = ctype.model_class()
#
#     if not issubclass(model, CremeEntity):
#         raise Http404('This model is not a CremeEntity.')
#
#     if brick_registry.is_model_invalid(model):
#         raise Http404('This model cannot have a detail-view configuration.')
#
#     return ctype


@login_required
def portal(request):
    return _config_portal(request, 'creme_config/bricks_portal.html')


# @login_required
# @permission_required('creme_core.can_admin')
# def add_detailview(request, ct_id):
#     ctype = _get_configurable_ctype(ct_id)
#
#     return generic.add_model_with_popup(
#         request, bricks.BrickDetailviewLocationsAddForm,
#         title=ugettext('New block configuration for «{model}»').format(model=ctype),
#         submit_label=_('Save the configuration'),
#         initial={'content_type': ctype},
#     )
class BrickDetailviewLocationsCreation(generic.base.EntityCTypeRelatedMixin,
                                       BaseConfigCreation,
                                      ):
    # model = BrickDetailviewLocation
    form_class = bricks.BrickDetailviewLocationsAddForm
    submit_label = _('Save the configuration')

    def check_related_ctype(self, ctype):
        super().check_related_ctype(ctype)

        if brick_registry.is_model_invalid(ctype.model_class()):
            raise ConflictError('This model cannot have a detail-view configuration.')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ctype'] = self.get_ctype()

        return kwargs

    def get_title(self):
        return ugettext('New block configuration for «{model}»').format(
            model=self.get_ctype(),
        )


# class PortalBricksWizard(PopupWizardMixin, SessionWizardView):
#     class _RelationStep(bricks.BlockPortalLocationsAddForm):
#         step_submit_label = pgettext_lazy('creme_config-verb', u'Select')
#
#     class _ConfigStep(bricks.BlockPortalLocationsEditForm):
#         step_prev_label = _(u'Previous step')
#         step_submit_label = _(u'Save the configuration')
#
#     form_list = (_RelationStep, _ConfigStep)
#     wizard_title = _(u'New blocks configuration')
#     template_name = 'creme_core/generics/blockform/add_wizard_popup.html'
#     permission = 'creme_core.can_admin'
#
#     def dispatch(self, *args, **kwargs):
#         warnings.warn('creme_config.views.bricks.PortalBricksWizard() is deprecated.', DeprecationWarning)
#
#         return super(PortalBricksWizard, self).dispatch(*args, **kwargs)
#
#     def done(self, form_list, **kwargs):
#         form_list[1].save()
#
#         # return HttpResponse(content_type='text/javascript')
#         return HttpResponse()
#
#     def get_form_kwargs(self, step):
#         kwargs = super(PortalBricksWizard, self).get_form_kwargs(step)
#
#         if step == '1':
#             cleaned_data = self.get_cleaned_data_for_step('0')
#             kwargs['app_name'] = cleaned_data['app_name']
#             kwargs['block_locations'] = ()
#
#         return kwargs


# @login_required
# @permission_required('creme_core.can_admin')
# def create_rtype_brick(request):
#     return generic.add_model_with_popup(request, bricks.RTypeBrickAddForm,
#                                         title=_('New type of block'),
#                                         submit_label=_('Save the block'),
#                                        )
class RelationTypeBrickCreation(BaseConfigCreation):
    model = RelationBrickItem
    form_class = bricks.RTypeBrickAddForm


class CustomBrickWizard(PopupWizardMixin, SessionWizardView):
    class _ResourceStep(bricks.CustomBrickConfigItemCreateForm):
        step_submit_label = pgettext_lazy('creme_config-verb', 'Select')

    class _ConfigStep(bricks.CustomBrickConfigItemEditForm):
        class Meta(bricks.CustomBrickConfigItemEditForm.Meta):
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

        return HttpResponse()

    def get_form_instance(self, step):
        if step == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            return CustomBrickConfigItem(name=cleaned_data['name'],
                                         content_type=cleaned_data['ctype'],
                                        )


# @login_required
# @permission_required('creme_core.can_admin')
# def edit_detailview(request, ct_id, role):
#     if role == 'default':
#         role_obj = None
#         superuser = False
#     elif role == 'superuser':
#         role_obj = None
#         superuser = True
#     else:
#         try:
#             role_id = int(role)
#         except ValueError:
#             raise Http404('Role must be "default", "superuser" or an integer')
#
#         role_obj = get_object_or_404(UserRole, id=role_id)
#         superuser = False
#
#     ct_id = int(ct_id)
#
#     if ct_id:
#         ct = _get_configurable_ctype(ct_id)
#
#         if superuser:
#             title = ugettext('Edit configuration of super-users for «{model}»').format(model=ct)
#         elif role_obj:
#             title = ugettext('Edit configuration of «{role}» for «{model}»').format(
#                             role=role_obj,
#                             model=ct,
#             )
#         else:
#             title = ugettext('Edit default configuration for «{model}»').format(model=ct)
#     else:  # ct_id == 0
#         if role != 'default':
#             raise Http404('You can only edit "default" role with default config')
#
#         ct = None
#         title = _('Edit default configuration')
#
#     return generic.add_model_with_popup(
#         request, bricks.BrickDetailviewLocationsEditForm,
#         initial={'content_type': ct,
#                  'role': role_obj, 'superuser': superuser,
#                 },
#         title=title,
#         template='creme_core/generics/blockform/edit_popup.html',
#         submit_label=_('Save the configuration'),
#     )
class BrickDetailviewLocationsEdition(generic.base.EntityCTypeRelatedMixin,
                                      BaseConfigCreation,
                                     ):
    # model = BrickDetailviewLocation
    form_class = bricks.BrickDetailviewLocationsEditForm
    template_name = 'creme_core/generics/blockform/edit_popup.html'
    submit_label = _('Save the configuration')
    ct_id_0_accepted = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_info = None

    # TODO: factorise + remove _get_configurable_ctype()
    def check_related_ctype(self, ctype):
        super().check_related_ctype(ctype)

        if brick_registry.is_model_invalid(ctype.model_class()):
            raise ConflictError('This model cannot have a detail-view configuration.')

    def get_role_info(self):
        role_info = self.role_info

        if role_info is None:
            role = self.kwargs['role']

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

            if self.get_ctype() is None and role != 'default':
                raise Http404('You can only edit "default" role with default config')

            self.role_info = role_info = (role_obj, superuser)

        return role_info

    # TODO: factorise ?
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ctype'] = self.get_ctype()
        kwargs['role'], kwargs['superuser'] = self.get_role_info()

        return kwargs

    def get_title(self):
        ct = self.get_ctype()
        role, superuser = self.get_role_info()

        if ct is not None:
            if superuser:
                title = ugettext('Edit configuration of super-users for «{model}»').format(model=ct)
            elif role is not None:
                title = ugettext('Edit configuration of «{role}» for «{model}»').format(
                    role=role,
                    model=ct,
                )
            else:
                title = ugettext('Edit default configuration for «{model}»').format(model=ct)
        else:
            title = _('Edit default configuration')

        return title


# @login_required
# @permission_required('creme_core.can_admin')
# def edit_portal(request, app_name):
#     warnings.warn('creme_config.views.bricks.edit_portal() is deprecated.', DeprecationWarning)
#
#     if app_name == 'default':
#         app_name = ''
#         title = _(u'Edit default portal configuration')
#     elif app_name == 'creme_core':
#         title = _(u'Edit home configuration')
#     else:
#         try:
#             app_config = apps.get_app_config(app_name)
#         except LookupError as e:
#             raise Http404(str(e))
#
#         title = ugettext(u'Edit portal configuration for «%s»') % app_config.verbose_name
#
#     b_locs = BlockPortalLocation.objects.filter(app_name=app_name).order_by('order')
#
#     if not b_locs:  # todo: a default config must exist (it works for now because there is always 'assistants' app)
#         raise Http404('This configuration does not exist (any more ?)')
#
#     if request.method == 'POST':
#         locs_form = bricks.BlockPortalLocationsEditForm(app_name=app_name, block_locations=b_locs, user=request.user,
#                                                         data=request.POST,
#                                                         )
#
#         if locs_form.is_valid():
#             locs_form.save()
#     else:
#         locs_form = bricks.BlockPortalLocationsEditForm(app_name=app_name, block_locations=b_locs, user=request.user)
#
#     return inner_popup(request,
#                        'creme_core/generics/blockform/edit_popup.html',
#                        {'form':  locs_form,
#                         'title': title,
#                         'submit_label': _(u'Save the modifications'),
#                        },
#                        is_valid=locs_form.is_valid(),
#                        reload=False,
#                        delegate_reload=True,
#                       )


@login_required
@permission_required('creme_core.can_admin')
def edit_home(request):
    if request.method == 'POST':
        locs_form = bricks.BrickHomeLocationsForm(user=request.user, data=request.POST)

        if locs_form.is_valid():
            locs_form.save()
    else:
        locs_form = bricks.BrickHomeLocationsForm(user=request.user)

    return generic.inner_popup(
        request,
        'creme_core/generics/blockform/edit_popup.html',
        {'form':  locs_form,
         'title': _('Edit home configuration'),
         'submit_label': _('Save the modifications'),
        },
        is_valid=locs_form.is_valid(),
        reload=False,
        delegate_reload=True,
    )


def _edit_mypage(request, title, user=None):
    if request.method == 'POST':
        locs_form = bricks.BrickMypageLocationsForm(owner=user, user=request.user, data=request.POST)

        if locs_form.is_valid():
            locs_form.save()
    else:
        locs_form = bricks.BrickMypageLocationsForm(owner=user, user=request.user)

    return generic.inner_popup(
        request,
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
    return _edit_mypage(request, _('Edit default "My page"'))


@login_required
def edit_mypage(request):
    return _edit_mypage(request, _('Edit "My page"'), user=request.user)


class RelationCTypeBrickWizard(PopupWizardMixin, SessionWizardView):
    class _ContentTypeStep(bricks.RTypeBrickItemAddCtypeForm):
        step_submit_label = pgettext_lazy('creme_config-verb', 'Select')

    class _FieldsStep(bricks.RTypeBrickItemEditCtypeForm):
        step_prev_label = _('Previous step')
        step_submit_label = _('Save the configuration')

    form_list = (_ContentTypeStep, _FieldsStep)
    wizard_title = 'New customised type'  # Overridden by get_context_data()
    template_name = 'creme_core/generics/blockform/add_wizard_popup.html'
    permission = 'creme_core.can_admin'

    def done(self, form_list, **kwargs):
        # form_list[1].save()
        _ct_form, fields_form = form_list
        fields_form.save()

        return HttpResponse()

    def get_context_data(self, form, **kwargs):
        # context = super(RelationCTypeBrickWizard, self).get_context_data(form, **kwargs)
        context = super().get_context_data(form, **kwargs)
        context['title'] = ugettext('New customised type for «{predicate}»').format(predicate=form.instance)

        return context

    def get_form_instance(self, step):
        return get_object_or_404(RelationBrickItem, id=self.kwargs['rbi_id'])

    def get_form_kwargs(self, step):
        # kwargs = super(RelationCTypeBrickWizard, self).get_form_kwargs(step)
        kwargs = super().get_form_kwargs(step)

        if step == '1':
            kwargs['ctype'] = self.get_cleaned_data_for_step('0')['ctype']

        return kwargs


@login_required
@permission_required('creme_core.can_admin')
def edit_cells_of_rtype_brick(request, rbi_id, ct_id):
    ctype = get_ct_or_404(ct_id)
    rbi = get_object_or_404(RelationBrickItem, id=rbi_id)

    if rbi.get_cells(ctype) is None:
        raise Http404('This ContentType is not set in the RelationBlockItem')

    if request.method == 'POST':
        form = bricks.RTypeBrickItemEditCtypeForm(user=request.user, data=request.POST,
                                                  instance=rbi, ctype=ctype,
                                                 )

        if form.is_valid():
            form.save()
    else:
        form = bricks.RTypeBrickItemEditCtypeForm(user=request.user, instance=rbi, ctype=ctype)

    return generic.inner_popup(
        request,
        'creme_core/generics/blockform/edit_popup.html',
        {'form':  form,
         'title': ugettext('Edit «{model}» configuration').format(model=ctype),
         'submit_label': _('Save the modifications'),
        },
        is_valid=form.is_valid(),
        reload=False,
        delegate_reload=True,
    )


@POST_only
@login_required
@permission_required('creme_core.can_admin')
def delete_cells_of_rtype_brick(request, rbi_id):
    ctype = get_ct_or_404(get_from_POST_or_404(request.POST, 'id'))
    rbi = get_object_or_404(RelationBrickItem, id=rbi_id)

    try:
        rbi.delete_cells(ctype)
    except KeyError:
        raise Http404('This ContentType is not set in the RelationBlockItem')

    rbi.save()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def edit_custom_brick(request, cbci_id):
    return generic.edit_model_with_popup(
        request, {'id': cbci_id}, CustomBrickConfigItem,
        bricks.CustomBrickConfigItemEditForm,
        ugettext('Edit the block «%s»'),
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

    BrickDetailviewLocation.objects.filter(content_type=ct_id,
                                           role=role_id, superuser=superuser,
                                          ).delete()

    return HttpResponse()


# @login_required
# @permission_required('creme_core.can_admin')
# def delete_portal(request):
#     warnings.warn('creme_config.views.bricks.delete_portal() is deprecated.', DeprecationWarning)
#
#     app_label = get_from_POST_or_404(request.POST, 'id')
#
#     if app_label == 'creme_core':
#         raise Http404('Home config can not be deleted')
#
#     BlockPortalLocation.objects.filter(app_name=app_label).delete()
#
#     return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_home(request):
    get_object_or_404(BrickHomeLocation,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                      # app_name='creme_core',
                     ).delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_default_mypage(request):
    get_object_or_404(BrickMypageLocation,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                      user=None,
                     ).delete()

    return HttpResponse()


@login_required
def delete_mypage(request):
    get_object_or_404(BrickMypageLocation,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                      user=request.user,
                     ).delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_rtype_brick(request):
    get_object_or_404(RelationBrickItem,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                     ).delete()

    return HttpResponse()



@login_required
@permission_required('creme_core.can_admin')
def delete_instance_brick(request):
    get_object_or_404(InstanceBrickConfigItem,
                      pk=get_from_POST_or_404(request.POST, 'id'),
                     ).delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete_custom_brick(request):
    cbci_id = get_from_POST_or_404(request.POST, 'id')
    get_object_or_404(CustomBrickConfigItem, pk=cbci_id).delete()

    return HttpResponse()
