# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2021  Hybird
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

from django import forms
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellRegularField,
)
from creme.creme_core.forms import CremeModelForm, FieldBlockManager
from creme.creme_core.forms import header_filter as hf_forms
from creme.creme_core.gui.custom_form import (
    CustomFormDescriptor,
    EntityCellCustomFormExtra,
    EntityCellCustomFormSpecial,
    ExtraFieldGroup,
    FieldGroup,
    FieldGroupList,
    base_cell_registry,
)
from creme.creme_core.models import CustomFormConfigItem, UserRole


class FieldIgnoringBase:
    def __init__(self):
        self._ignored_cells = []

    @property
    def ignored_cells(self):
        yield from self._ignored_cells

    @ignored_cells.setter
    def ignored_cells(self, cells):
        self._ignored_cells[:] = cells


# Regular & custom fields ------------------------------------------------------
class CFormCellRegularFieldsField(FieldIgnoringBase,
                                  hf_forms.EntityCellRegularFieldsField):
    fields_depth = 0

    def __init__(self, *args, **kwargs):
        FieldIgnoringBase.__init__(self)
        hf_forms.EntityCellRegularFieldsField.__init__(self, *args, **kwargs)

    def _regular_fields_enum(self, model):
        ignored_fnames = {
            cell.value
            for cell in self._ignored_cells
            if isinstance(cell, EntityCellRegularField)
        }

        return super()._regular_fields_enum(model=model).exclude(
            # lambda field, deep: field.name in ignored_fnames
            lambda model, field, depth: field.name in ignored_fnames
        ).exclude(
            editable=False,
        )


class CFormCellCustomFieldsField(FieldIgnoringBase,
                                 hf_forms.EntityCellCustomFieldsField):
    def __init__(self, *args, **kwargs):
        FieldIgnoringBase.__init__(self)
        hf_forms.EntityCellCustomFieldsField.__init__(self, *args, **kwargs)

    def _custom_fields(self):
        ignored_cfield_ids = {
            cell.custom_field.id
            for cell in self._ignored_cells
            if isinstance(cell, EntityCellCustomField)
        }

        for cfield in super()._custom_fields():
            if cfield.id not in ignored_cfield_ids:
                yield cfield


# Special cells ----------------------------------------------------------------

class CFormCellSpecialFieldsWidget(hf_forms.UniformEntityCellsWidget):
    template_name = 'creme_config/forms/widgets/cform-cells/special-fields.html'
    type_id = EntityCellCustomFormSpecial.type_id


class CFormCellSpecialFieldsField(FieldIgnoringBase,
                                  hf_forms.UniformEntityCellsField):
    widget = CFormCellSpecialFieldsWidget
    cell_class = EntityCellCustomFormSpecial

    def __init__(self, *args, **kwargs):
        FieldIgnoringBase.__init__(self)
        hf_forms.UniformEntityCellsField.__init__(self, *args, **kwargs)

    def _get_options(self):
        ignored_names = {
            cell.value
            for cell in self._ignored_cells
            if isinstance(cell, EntityCellCustomFormSpecial)
        }

        for name in EntityCellCustomFormSpecial.ALLOWED:
            if name not in ignored_names:
                cell = EntityCellCustomFormSpecial(model=self.model, name=name)
                yield cell.key, cell


# Extra Cells ------------------------------------------------------------------

class CFormCellExtraFieldsWidget(hf_forms.UniformEntityCellsWidget):
    template_name = 'creme_config/forms/widgets/cform-cells/extra-fields.html'
    type_id = EntityCellCustomFormExtra.type_id


class CFormCellExtraFieldsField(FieldIgnoringBase,
                                hf_forms.UniformEntityCellsField):
    widget = CFormCellExtraFieldsWidget
    cell_class = EntityCellCustomFormExtra

    def __init__(self, *args, **kwargs):
        FieldIgnoringBase.__init__(self)
        hf_forms.UniformEntityCellsField.__init__(self, *args, **kwargs)

    def _get_options(self):
        model = self.model
        cell_class = self.cell_class
        ignored_sub_type_ids = {
            cell.sub_cell.sub_type_id
            for cell in self._ignored_cells
            if isinstance(cell, EntityCellCustomFormExtra)
        }

        for sub_cell_class in self.cell_class.allowed_sub_cell_classes:
            if sub_cell_class.sub_type_id not in ignored_sub_type_ids:
                cell = cell_class(sub_cell_class(model))

                yield cell.key, cell


# ------------------------------------------------------------------------------
class CustomFormCellsWidget(hf_forms.EntityCellsWidget):
    template_name = 'creme_config/forms/widgets/cform-cells/widget.html'


class CustomFormCellsField(hf_forms.EntityCellsField):
    widget = CustomFormCellsWidget
    field_classes = {
        CFormCellRegularFieldsField,
        CFormCellCustomFieldsField,
        CFormCellSpecialFieldsField,
        # CFormCellExtraFieldsField,  # NB: add dynamic class
    }

    def __init__(self, *, cell_registry=None, **kwargs):
        super().__init__(
            cell_registry=cell_registry or base_cell_registry,
            **kwargs
        )
        self._ignored_cells = []

    @property
    def ignored_cells(self):
        yield from self._ignored_cells

    @ignored_cells.setter
    def ignored_cells(self, cells):
        self._ignored_cells[:] = cells
        for sub_field in self._sub_fields:
            sub_field.ignored_cells = cells


class CustomFormGroupForm(CremeModelForm):
    name = forms.CharField(label=_('Name'), max_length=100)
    cells = CustomFormCellsField(label=_('Fields'))

    blocks = FieldBlockManager(
        {
            'id': 'name',
            'label': 'Name',
            'fields': ('name',),
        }, {
            'id': 'cells',
            'label': 'Fields',
            'fields': ('cells',),
        },
    )

    class Meta:
        model = CustomFormConfigItem
        fields = ()

    def __init__(self, descriptor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.descriptor = descriptor
        registry = descriptor.build_cell_registry()

        class FinalCellExtraFieldsField(CFormCellExtraFieldsField):
            cell_class = registry[EntityCellCustomFormExtra.type_id]

        cells_f = self.fields['cells']
        cells_f.field_classes = {
            *cells_f.field_classes,
            FinalCellExtraFieldsField,
        }
        cells_f.cell_registry = registry


class CustomFormGroupCreationForm(CustomFormGroupForm):
    def __init__(self, descriptor, groups, *args, **kwargs):
        super().__init__(descriptor=descriptor, *args, **kwargs)
        cells_f = self.fields['cells']
        cells_f.model = model = descriptor.model
        cells_f.required = False

        ignored_cells = [
            *(
                cell
                for i, group in enumerate(groups)
                for cell in getattr(group, 'cells', ())  # extra group has no <cells>
            ),
            *(
                EntityCellRegularField.build(model=model, name=field_name)
                for field_name in descriptor.excluded_fields
            ),
        ]
        # TODO: move semantic to EntityCellCustomFormSpecial ??
        if descriptor.form_type == CustomFormDescriptor.EDITION_FORM:
            ignored_cells.extend(
                EntityCellCustomFormSpecial(model=model, name=name)
                for name in (
                    EntityCellCustomFormSpecial.CREME_PROPERTIES,
                    EntityCellCustomFormSpecial.RELATIONS,
                )
            )
        cells_f.ignored_cells = ignored_cells

    def save(self, *args, **kwargs):
        cdata = self.cleaned_data
        instance = self.instance
        desc = self.descriptor
        model = desc.model
        cell_registry = desc.build_cell_registry()

        instance.store_groups(FieldGroupList(
            model=model,
            cell_registry=cell_registry,
            groups=[
                *FieldGroupList.from_dicts(
                    model=model,
                    data=instance.groups_as_dicts(),
                    cell_registry=cell_registry,
                ),
                FieldGroup(name=cdata['name'], cells=cdata['cells']),
            ],
        ))

        return super().save(*args, **kwargs)


class CustomFormExtraGroupCreationForm(CremeModelForm):
    group = forms.ChoiceField(label=_('Group'))

    class Meta:
        model = CustomFormConfigItem
        fields = ()

    def __init__(self, descriptor, groups, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.descriptor = descriptor
        used_group_ids = {
            group.extra_group_id
            for group in groups
            if isinstance(group, ExtraFieldGroup)
        }
        choices = [
            (group_class.extra_group_id, group_class.name)
            for group_class in descriptor.extra_group_classes
            if group_class.extra_group_id not in used_group_ids
        ]

        if choices:
            self.fields['group'].choices = choices
        else:
            self.fields['group'].help_text = _(
                'Sorry no extra group is available any more.'
            )

    # TODO: factorise ?
    def save(self, *args, **kwargs):
        instance = self.instance
        desc = self.descriptor
        model = desc.model
        cell_registry = desc.build_cell_registry()

        group_id = self.cleaned_data['group']
        extra_group_class = next(
            group_class
            for group_class in desc.extra_group_classes
            if group_class.extra_group_id == group_id
        )

        instance.store_groups(FieldGroupList(
            model=model,
            cell_registry=cell_registry,
            groups=[
                *FieldGroupList.from_dicts(
                    model=model,
                    data=instance.groups_as_dicts(),
                    cell_registry=cell_registry,
                ),
                extra_group_class(model=model),
            ],
        ))

        return super().save(*args, **kwargs)


class CustomFormConfigItemChoiceField(forms.ModelChoiceField):
    def __init__(self, queryset=CustomFormConfigItem.objects.none(), **kwargs):
        super().__init__(queryset=queryset, **kwargs)

    def label_from_instance(self, obj):
        if obj.superuser:
            return _('Form for super-user')

        if obj.role:
            return gettext('Form for role «{role}»').format(role=obj.role)

        return _('Default form')


class CustomFormCreationForm(CremeModelForm):
    role = forms.ModelChoiceField(
        label=_('Role'),
        queryset=UserRole.objects.none(),
        empty_label=None, required=False,
    )
    instance_to_copy = CustomFormConfigItemChoiceField(
        label=_('Form to copy'),
        help_text=_(
            'You can copy an existing form in order to avoid creating your new form from scratch.'
        ),
        required=False,
    )

    class Meta:
        model = CustomFormConfigItem
        fields = ('role',)

    def __init__(self, descriptor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        instance.descriptor_id = descriptor.id
        instance.content_type = descriptor.model
        instance.store_groups([])  # TODO: remove when JSONField with default

        fields = self.fields
        item_model = type(instance)

        # ---
        role_f = fields['role']
        used_role_ids = {
            *item_model.objects
                       .filter(descriptor_id=instance.descriptor_id)
                       .exclude(role__isnull=True, superuser=False)
                       .values_list('role', flat=True),
        }

        try:
            used_role_ids.remove(None)
        except KeyError:
            # NB: browser can ignore <em> tag in <option>...
            role_f.empty_label = '*{}*'.format(gettext('Superuser'))

        role_f.queryset = UserRole.objects.exclude(pk__in=used_role_ids)

        # ---
        # TODO: do only one query (see used_role_ids) (convert ModelChoiceField to ChoiceField?)
        fields['instance_to_copy'].queryset = item_model.objects.filter(
            descriptor_id=instance.descriptor_id,
        ).select_related('role')

    def save(self, *args, **kwargs):
        c_data = self.cleaned_data
        instance = self.instance

        instance.superuser = (c_data['role'] is None)

        instance_to_copy = c_data.get('instance_to_copy')
        if instance_to_copy is not None:
            instance.json_groups = instance_to_copy.json_groups

        return super().save(*args, **kwargs)


# TODO: factorise
class CustomFormGroupEditionForm(CustomFormGroupForm):
    def __init__(self, descriptor, groups, group_id, *args, **kwargs):
        super().__init__(descriptor=descriptor, *args, **kwargs)
        self.groups = groups
        self.group_id = group_id

        group = groups[group_id]
        fields = self.fields
        model = descriptor.model

        fields['name'].initial = group.name

        cells_f = fields['cells']
        cells = [*group.cells]
        cells_f.non_hiddable_cells = cells
        cells_f.model = model
        cells_f.initial = cells

        ignored_cells = [
            *(
                cell
                for i, group in enumerate(groups)
                if i != group_id
                for cell in getattr(group, 'cells', ())
            ),
            *(
                EntityCellRegularField.build(model=model, name=field_name)
                for field_name in descriptor.excluded_fields
            ),
        ]
        if descriptor.form_type == CustomFormDescriptor.EDITION_FORM:
            ignored_cells.extend(
                EntityCellCustomFormSpecial(model=model, name=name)
                for name in (
                    EntityCellCustomFormSpecial.CREME_PROPERTIES,
                    EntityCellCustomFormSpecial.RELATIONS,
                )
            )
        cells_f.ignored_cells = ignored_cells

    def save(self, *args, **kwargs):
        cdata = self.cleaned_data
        groups = [*self.groups]
        layout = groups[self.group_id].layout
        groups[self.group_id] = FieldGroup(
            name=cdata['name'], cells=cdata['cells'], layout=layout,
        )

        self.instance.store_groups(FieldGroupList(
            model=self.descriptor.model, groups=groups,
            cell_registry=self.descriptor.build_cell_registry(),
        ))

        return super().save(*args, **kwargs)
