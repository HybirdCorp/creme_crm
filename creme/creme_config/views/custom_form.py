################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2025  Hybird
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

from abc import ABC
from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms.base import LAYOUTS
from creme.creme_core.gui.custom_form import (
    ExtraFieldGroup,
    FieldGroup,
    FieldGroupList,
    customform_descriptor_registry,
)
from creme.creme_core.models import CustomEntityType, CustomFormConfigItem
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.bricks import BrickStateExtraDataSetting
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin

from ..bricks import CustomFormsBrick
from ..constants import BRICK_STATE_SHOW_CFORMS_DETAILS
from ..forms import custom_form as forms
from . import base


class Portal(base.ConfigPortal):
    template_name = 'creme_config/portals/custom-form.html'
    brick_classes = [CustomFormsBrick]


class CustomFormMixin:
    cform_registry = customform_descriptor_registry
    group_id_url_kwarg = 'group_id'
    cfci_pk_url_kwarg = 'item_id'

    def get_customform_descriptor_from_id(self, descriptor_id):
        desc = self.cform_registry.get(descriptor_id)

        if desc is None:
            raise ConflictError(f'The custom form "{descriptor_id}" is invalid.')

        ce_type = CustomEntityType.objects.get_for_model(desc.model)
        if ce_type and not ce_type.enabled:
            raise ConflictError(
                f'The custom form "{descriptor_id}" is related to a disabled custom type.'
            )

        return desc

    def get_customform_descriptor(self):
        try:
            desc = self.descriptor  # NOQA
        except AttributeError:
            self.descriptor = desc = self.get_customform_descriptor_from_id(
                self.object.descriptor_id,
            )

        return desc

    def get_groups(self):
        try:
            groups = self.groups  # NOQA
        except AttributeError:
            self.groups = groups = self.get_customform_descriptor().groups(item=self.object)

        return groups

    def get_group_id(self):
        group_id = int(self.kwargs[self.group_id_url_kwarg])

        if group_id >= len(self.get_groups()):
            raise ConflictError(f'The group ID "{group_id}" is invalid.')

        return group_id

    def get_cfci_for_update(self):
        return get_object_or_404(
            CustomFormConfigItem.objects.select_for_update(),
            id=self.kwargs[self.cfci_pk_url_kwarg],
        )


class CustomFormCreation(base.ConfigModelCreation):
    model = CustomFormConfigItem
    form_class = forms.CustomFormCreationForm
    desc_id_url_kwarg = 'desc_id'
    title = _('Add a configuration to «{descriptor.verbose_name}» for a role')
    cform_registry = customform_descriptor_registry

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.descriptor = None

    def get_customform_descriptor(self):
        desc = self.descriptor
        if desc is None:
            descriptor_id = self.kwargs[self.desc_id_url_kwarg]
            desc = self.cform_registry.get(descriptor_id)

            if desc is None:
                raise ConflictError(f'The custom form "{descriptor_id}" is invalid.')

            ce_type = CustomEntityType.objects.get_for_model(desc.model)
            if ce_type and not ce_type.enabled:
                raise ConflictError(
                    f'The custom form "{descriptor_id}" is related to a disabled custom type.'
                )

            self.descriptor = desc

        return desc

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['descriptor'] = self.get_customform_descriptor()

        return kwargs

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['descriptor'] = self.get_customform_descriptor()

        return data


class CustomFormDeletion(base.ConfigDeletion):
    id_arg = 'id'
    model = CustomFormConfigItem

    def perform_deletion(self, request):
        cfci = get_object_or_404(
            self.model,
            pk=get_from_POST_or_404(request.POST, self.id_arg),
        )

        if not cfci.superuser and not cfci.role_id:
            raise ConflictError('Cannot delete a default form')

        cfci.delete()


class CustomFormResetting(CustomFormMixin, base.ConfigDeletion):
    id_arg = 'id'
    model = CustomFormConfigItem

    @atomic
    def perform_deletion(self, request):
        cfci = get_object_or_404(
            self.model.objects.select_for_update(),
            pk=get_from_POST_or_404(request.POST, self.id_arg),
        )
        descriptor = self.get_customform_descriptor_from_id(cfci.descriptor_id)
        # TODO: factorise with CustomFormConfigItemManager.create_if_needed()
        cfci.store_groups(FieldGroupList.from_cells(
            model=descriptor.model,
            data=descriptor.default_groups_desc,
            cell_registry=descriptor.build_cell_registry(),
            allowed_extra_group_classes=(*descriptor.extra_group_classes,),
        ))
        cfci.save()


class _BaseCustomFormGroupCreation(CustomFormMixin, base.ConfigModelEdition):
    model = CustomFormConfigItem
    pk_url_kwarg = 'item_id'
    submit_label = _('Save the configuration')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['descriptor'] = self.get_customform_descriptor()
        kwargs['groups'] = self.get_groups()

        return kwargs

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['form'] = self.get_customform_descriptor()

        return data


class CustomFormGroupCreation(_BaseCustomFormGroupCreation):
    form_class = forms.CustomFormGroupCreationForm
    title = _('Add a group to «{form}»')


class CustomFormExtraGroupCreation(_BaseCustomFormGroupCreation):
    form_class = forms.CustomFormExtraGroupCreationForm
    title = _('Add an extra group to «{form}»')

    def get_customform_descriptor(self):
        desc = super().get_customform_descriptor()

        if not next(desc.extra_group_classes, None):
            raise ConflictError('This custom-form does not propose extra group.')

        return desc


class CustomFormGroupEdition(CustomFormMixin, base.ConfigModelEdition):
    model = CustomFormConfigItem
    form_class = forms.CustomFormGroupEditionForm
    pk_url_kwarg = 'item_id'
    title = _('Edit the group «{group}»')
    submit_label = _('Save the configuration')

    def get_group(self):
        group = self.get_groups()[self.get_group_id()]

        if isinstance(group, ExtraFieldGroup):
            raise ConflictError('An extra group cannot be edited.')

        return group

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs['descriptor'] = self.get_customform_descriptor()
        kwargs['groups'] = self.get_groups()
        kwargs['group_id'] = self.get_group_id()

        self.get_group()  # Check group

        return kwargs

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['group'] = self.get_group().name

        return data


class CustomFormGroupLayoutSetting(CustomFormMixin, generic.CheckedView):
    permissions = 'creme_core.can_admin'
    layout_arg = 'layout'

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self.object = None

    @atomic
    def post(self, request, *args, **kwargs):
        layout = get_from_POST_or_404(request.POST, self.layout_arg)
        if layout not in LAYOUTS:
            raise ConflictError(f'The layout "{layout}" is invalid.')

        self.object = cfci = self.get_cfci_for_update()
        desc = self.get_customform_descriptor()
        group_id = self.get_group_id()

        groups = [*self.get_groups()]
        groups[group_id]._layout = layout

        cfci.store_groups(FieldGroupList(
            model=desc.model, groups=groups, cell_registry=desc.build_cell_registry(),
        ))
        cfci.save()  # TODO: only if changed ?

        return HttpResponse()


class BaseCustomFormDeletion(CustomFormMixin, ABC, base.ConfigDeletion):
    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self.object = None


class CustomFormGroupDeletion(BaseCustomFormDeletion):
    group_id_arg = 'group_id'

    @atomic
    def perform_deletion(self, request):
        group_id = get_from_POST_or_404(request.POST, self.group_id_arg, cast=int)
        self.object = cfci = self.get_cfci_for_update()
        desc = self.get_customform_descriptor()

        groups = [*self.get_groups()]
        try:
            del groups[group_id]
        except IndexError:
            raise ConflictError(f'The group ID "{group_id}" is invalid.')

        cfci.store_groups(FieldGroupList(
            model=desc.model, groups=groups, cell_registry=desc.build_cell_registry(),
        ))
        cfci.save()


class CustomFormCellDeletion(BaseCustomFormDeletion):
    cell_key_arg = 'cell_key'

    @atomic
    def perform_deletion(self, request):
        cell_key = get_from_POST_or_404(request.POST, self.cell_key_arg)
        self.object = cfci = self.get_cfci_for_update()
        desc = self.get_customform_descriptor()

        groups = []
        found = False
        for group in self.get_groups():
            cells = []

            # TODO: better API for group.cells ?
            for cell in getattr(group, 'cells', ()):
                if cell.key != cell_key:
                    cells.append(cell)
                else:
                    found = True

            groups.append(
                FieldGroup(name=group.name, cells=cells, layout=group.layout)
                if found else
                group
            )

        if not found:
            raise Http404(f'The cell with key="{cell_key}" has not been found.')

        cfci.store_groups(FieldGroupList(
            model=desc.model, groups=groups, cell_registry=desc.build_cell_registry()
        ))
        cfci.save()


class CustomFormGroupReordering(CustomFormMixin, generic.CheckedView):
    permissions = 'creme_core.can_admin'
    target_order_arg = 'target'

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self.object = None

    @atomic
    def post(self, request, *args, **kwargs):
        target = get_from_POST_or_404(request.POST, self.target_order_arg, cast=int)

        self.object = cfci = self.get_cfci_for_update()
        desc = self.get_customform_descriptor()
        group_id = self.get_group_id()

        groups = [*self.get_groups()]
        if target > len(groups):
            raise ConflictError(f'The target "{target}" is too big.')

        moved_group = groups.pop(group_id)
        groups.insert(target, moved_group)

        cfci.store_groups(FieldGroupList(
            model=desc.model, groups=groups, cell_registry=desc.build_cell_registry(),
        ))
        cfci.save()  # TODO: only if changed ?

        return HttpResponse()


class CustomFormShowDetails(EntityCTypeRelatedMixin,
                            CustomFormMixin,
                            BrickStateExtraDataSetting):
    ctype_id_arg = 'ct_id'
    item_id_arg = 'item_id'
    action_arg = 'action'
    brick_cls = CustomFormsBrick
    data_key = BRICK_STATE_SHOW_CFORMS_DETAILS

    # Actions
    HIDE = 'hide'
    SHOW = 'show'

    @dataclass
    class Action:
        show: bool
        ctype: ContentType
        item: CustomFormConfigItem | None

    def get_show(self) -> bool:
        match get_from_POST_or_404(self.request.POST, key=self.action_arg):
            case self.SHOW:
                return True
            case self.HIDE:
                return False
            case _:
                raise Http404(f'Invalid argument "action": "{self.action_arg}"')

    def get_ctype_id(self):
        return get_from_POST_or_404(self.request.POST, key=self.ctype_id_arg)

    def get_value(self):
        show = self.get_show()
        item_id = get_from_POST_or_404(
            self.request.POST, key=self.item_id_arg, cast=int, default=0,
        )

        if item_id:
            item = get_object_or_404(CustomFormConfigItem, id=item_id)
            desc = self.get_customform_descriptor_from_id(item.descriptor_id)
            ctype = ContentType.objects.get_for_model(desc.model)
        else:
            item = None
            ctype = self.get_ctype()

        return None if ctype is None else self.Action(show=show, ctype=ctype, item=item)

    def set_value(self, state, value):
        new_value = None  # By default, we hide the whole ContentType
        current_value = state.get_extra_data(self.data_key)
        ctype_id = value.ctype.id
        item = value.item

        if current_value is None:
            if not value.show:
                # Hide a ContentType/item but the config is already empty => do nothing
                return

            new_value = {'ctype': ctype_id}

            if item:
                new_value['items'] = [item.id]
        else:
            if value.show:
                new_value = {'ctype': ctype_id}

                if item:
                    # NB: we use a set to de-duplicate IDs
                    items = {item.id}
                    if current_value['ctype'] == ctype_id:
                        items.update(current_value.get('items', ()))

                    # NB: we sort to facilitate unit testing
                    new_value['items'] = sorted(items)
            else:  # Hide
                if current_value['ctype'] == ctype_id:
                    if item:
                        items = {*current_value.get('items', ())}
                        items.discard(item.id)

                        if items:
                            new_value = {'ctype': ctype_id, 'items': sorted(items)}
                else:
                    # Hide a ContentType not shown => do nothing
                    return

        super().set_value(state=state, value=new_value)
