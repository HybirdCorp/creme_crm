# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import EmailField, ForeignKey, ManyToManyField, URLField
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_cell import (
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.forms import base
from creme.creme_core.forms import widgets as core_widgets
from creme.creme_core.forms.fields import EntityCTypeChoiceField
from creme.creme_core.forms.header_filter import EntityCellsField
from creme.creme_core.gui import bricks as gui_bricks
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickMypageLocation,
    CremeEntity,
    CustomBrickConfigItem,
    RelationBrickItem,
    RelationType,
    UserRole,
)
from creme.creme_core.registry import creme_registry
from creme.creme_core.utils.id_generator import generate_string_id_and_save
from creme.creme_core.utils.unicode_collation import collator

from .fields import BricksConfigField

__all__ = (
    'BrickDetailviewLocationsAddForm', 'BrickDetailviewLocationsEditForm',
    'BrickHomeLocationsAddingForm', 'BrickHomeLocationsEditionForm',
    'BrickMypageLocationsForm',
    'RTypeBrickAddForm', 'RTypeBrickItemAddCtypeForm', 'RTypeBrickItemEditCtypeForm',
    'CustomBrickConfigItemCreateForm', 'CustomBrickConfigItemEditForm',
)


class BrickLocationsField(forms.MultipleChoiceField):
    def __init__(self, *, required=False, choices=(),
                 widget=core_widgets.OrderedMultipleChoiceWidget,
                 **kwargs):
        super().__init__(
            required=required, choices=choices, widget=widget,
            **kwargs
        )


class _BrickLocationsForm(base.CremeForm):
    def _build_home_locations_field(self, field_name, brick_locations):
        bricks = self.fields[field_name]
        choices = [
            (brick.id_, str(brick.verbose_name))
            for brick in gui_bricks.brick_registry.get_compatible_home_bricks()
        ]
        sort_key = collator.sort_key
        choices.sort(key=lambda c: sort_key(c[1]))

        bricks.choices = choices
        bricks.initial = [bl.brick_id for bl in brick_locations]

    def _save_locations(self,
                        location_model,
                        location_builder,
                        bricks_partitions,
                        old_locations=(),
                        role=None,
                        superuser=False,
                        ):
        # At least 1 block per zone (even if it can be fake block)
        needed = sum(len(brick_ids) or 1 for brick_ids in bricks_partitions.values())
        lendiff = needed - len(old_locations)

        # Reserve the number of BrickLocation database rows we need for the
        # process. Remove the surplus, build the missing.
        if lendiff < 0:
            locations_store = old_locations[:needed]
            location_model.objects.filter(
                pk__in=[loc.id for loc in old_locations[needed:]],
            ).delete()
        else:
            locations_store = [*old_locations]

            if lendiff > 0:
                locations_store.extend(location_builder() for __ in range(lendiff))

        store_it = iter(locations_store)

        for zone, brick_ids in bricks_partitions.items():
            if not brick_ids:  # No brick for this zone -> fake brick_id
                brick_ids = ('',)

            for order, brick_id in enumerate(brick_ids, start=1):
                location = next(store_it)
                location.brick_id = brick_id
                location.order = order
                # NB: BrickHomeLocation has not 'zone' attr, but we do not care ! :)
                location.zone = zone
                # NB: idem with 'role'
                location.role = role
                # NB: idem with 'superuser'
                location.superuser = superuser

                location.save()


class _BrickDetailviewLocationsForm(_BrickLocationsForm):
    hat = forms.ChoiceField(label=_('Header block'), widget=core_widgets.CremeRadioSelect)
    locations = BricksConfigField(label=_("Blocks"), required=True)

    locations_map = {
        BrickDetailviewLocation.TOP: BricksConfigField.zones.TOP,
        BrickDetailviewLocation.LEFT: BricksConfigField.zones.LEFT,
        BrickDetailviewLocation.RIGHT: BricksConfigField.zones.RIGHT,
        BrickDetailviewLocation.BOTTOM: BricksConfigField.zones.BOTTOM,
    }

    def __init__(self, ctype=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ct = ctype

        self.role = None
        self.superuser = False
        self.locations = ()
        model = ctype.model_class() if ctype else None

        self.choices = choices = [
            (brick.id_, brick)
            for brick in gui_bricks.brick_registry.get_compatible_bricks(model=model)
        ]
        sort_key = collator.sort_key
        choices.sort(key=lambda c: sort_key(c[1].verbose_name))

        self.fields['locations'].choices = self.choices

        hat_bricks = []
        if model:
            hat_bricks.extend(gui_bricks.brick_registry.get_compatible_hat_bricks(model))

        if len(hat_bricks) > 1:
            hat_f = self.fields['hat']
            hat_f.choices = [(brick.id_, brick.verbose_name) for brick in hat_bricks]
        else:
            del self.fields['hat']

    def save(self, *args, **kwargs):
        cdata = self.cleaned_data
        hat_brick_id = cdata.get('hat')
        locations = cdata["locations"]
        self._save_locations(
            BrickDetailviewLocation,
            lambda: BrickDetailviewLocation(content_type=self.ct),
            bricks_partitions={
                BrickDetailviewLocation.HAT:    [hat_brick_id] if hat_brick_id else [],
                BrickDetailviewLocation.TOP:    locations['top'],
                BrickDetailviewLocation.LEFT:   locations['left'],
                BrickDetailviewLocation.RIGHT:  locations['right'],
                BrickDetailviewLocation.BOTTOM: locations['bottom'],
            },
            old_locations=self.locations,
            role=self.role, superuser=self.superuser,
        )


class BrickDetailviewLocationsAddForm(_BrickDetailviewLocationsForm):
    role = forms.ModelChoiceField(
        label=_('Role'), queryset=UserRole.objects.none(),
        empty_label=None, required=False,
    )

    # TODO: manage Meta.fields in '*'
    blocks = base.FieldBlockManager({
        'id': 'general',
        'label': _('Configuration'),
        'fields': ('role', 'hat', 'locations'),
    })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields

        role_f = fields['role']
        used_role_ids = {
            *BrickDetailviewLocation.objects
                                    .filter(content_type=self.ct)
                                    .exclude(role__isnull=True, superuser=False)
                                    .values_list('role', flat=True),
        }

        try:
            used_role_ids.remove(None)
        except KeyError:
            # NB: browser can ignore <em> tag in <option>...
            role_f.empty_label = '*{}*'.format(gettext('Superuser'))

        role_f.queryset = UserRole.objects.exclude(pk__in=used_role_ids)

        hat_f = fields.get('hat')
        if hat_f:
            hat_f.initial = hat_f.choices[0][0]

    def save(self, *args, **kwargs):
        self.role = role = self.cleaned_data['role']
        self.superuser = (role is None)
        super().save(*args, **kwargs)


class BrickDetailviewLocationsEditForm(_BrickDetailviewLocationsForm):
    def __init__(self, role, superuser, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        self.superuser = superuser

        self.locations = locations = BrickDetailviewLocation.objects.filter(
            content_type=self.ct,
            role=role, superuser=superuser,
        ).order_by('order')

        fields = self.fields

        initial_locations = {zone.value: [] for zone in self.locations_map.values()}
        for bl in locations:
            zone_name = self.locations_map.get(bl.zone)
            if bl.brick_id and zone_name is not None:
                initial_locations[zone_name.value].append(bl.brick_id)
        fields['locations'].initial = initial_locations

        hat_f = fields.get('hat')
        if hat_f:
            HEADER = BrickDetailviewLocation.HAT
            selected = [bl.brick_id for bl in locations if bl.zone == HEADER]
            hat_f.initial = selected[0] if selected else hat_f.choices[0][0]


class BrickHomeLocationsAddingForm(_BrickLocationsForm):
    role = forms.ModelChoiceField(
        label=_('Role'),
        queryset=UserRole.objects.none(),
        empty_label=None, required=False,
    )
    bricks = BrickLocationsField(label=_('Blocks to display on the home'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._build_home_locations_field(field_name='bricks', brick_locations=())

        role_f = self.fields['role']
        used_role_ids = {
            *BrickHomeLocation.objects
                              .exclude(role__isnull=True, superuser=False)
                              .values_list('role', flat=True),
        }

        # TODO: factorise ?
        try:
            used_role_ids.remove(None)
        except KeyError:
            # NB: browser can ignore <em> tag in <option>...
            role_f.empty_label = '*{}*'.format(gettext('Superuser'))

        role_f.queryset = UserRole.objects.exclude(pk__in=used_role_ids)

    def save(self, *args, **kwargs):
        role = self.cleaned_data['role']

        self._save_locations(
            location_model=BrickHomeLocation,
            location_builder=lambda: BrickHomeLocation(),
            bricks_partitions={1: self.cleaned_data['bricks']},  # 1 is a "nameless" zone
            role=role,
            superuser=(role is None),
        )


class BrickHomeLocationsEditionForm(_BrickLocationsForm):
    bricks = BrickLocationsField(label=_('Blocks to display on the home'))

    def __init__(self, role, superuser, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        self.superuser = superuser

        self.locations = locations = BrickHomeLocation.objects.filter(
            role=role, superuser=superuser,
        )

        self._build_home_locations_field(field_name='bricks', brick_locations=locations)

    def save(self, *args, **kwargs):
        self._save_locations(
            location_model=BrickHomeLocation,
            location_builder=lambda: BrickHomeLocation(),
            bricks_partitions={1: self.cleaned_data['bricks']},  # 1 is a "nameless" zone
            old_locations=self.locations,
            role=self.role, superuser=self.superuser,
        )


class BrickMypageLocationsForm(_BrickLocationsForm):
    bricks = BrickLocationsField(
        label=_('Blocks to display on the «My Page» of the users'),
    )

    def __init__(self, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.locations = locations = BrickMypageLocation.objects.filter(user=owner)

        self._build_home_locations_field(field_name='bricks', brick_locations=locations)

    def save(self, *args, **kwargs):
        self._save_locations(
            BrickMypageLocation,
            lambda: BrickMypageLocation(user=self.owner),
            {1: self.cleaned_data['bricks']},  # 1 is a "nameless" zone
            self.locations,
        )


class RTypeBrickAddForm(base.CremeModelForm):
    relation_type = forms.ModelChoiceField(
        RelationType.objects.none(), empty_label=None,
        widget=core_widgets.DynamicSelect(attrs={'autocomplete': True}),
    )

    class Meta(base.CremeModelForm.Meta):
        model = RelationBrickItem

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        existing_type_ids = RelationBrickItem.objects.values_list('relation_type_id', flat=True)

        self.fields['relation_type'].queryset = RelationType.objects.exclude(
            pk__in=existing_type_ids,
        )

    def save(self, *args, **kwargs):
        self.instance.brick_id = gui_bricks.SpecificRelationsBrick.generate_id(
            'creme_config',
            self.cleaned_data['relation_type'].id,
        )
        return super().save(*args, **kwargs)


class RTypeBrickItemAddCtypeForm(base.CremeModelForm):
    ctype = EntityCTypeChoiceField(
        label=_('Customised resource'),
        widget=core_widgets.DynamicSelect({'autocomplete': True}),
    )

    class Meta:
        model = RelationBrickItem
        exclude = ('relation_type',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        ct_field = self.fields['ctype']
        compatible_ctypes = instance.relation_type.object_ctypes.all()

        if compatible_ctypes:
            ct_field.ctypes = compatible_ctypes

        # TODO: iter_ctypes() ??
        used_ct_ids = frozenset(ct.id for ct, cells in instance.iter_cells())
        ct_field.ctypes = (ct for ct in ct_field.ctypes if ct.id not in used_ct_ids)

    def save(self, *args, **kwargs):
        # NB: we should set this in clean(), but it interfere when we re-using
        #     the same instance (see __init__)
        self.instance.set_cells(self.cleaned_data['ctype'], ())

        return super().save(*args, **kwargs)


class RTypeBrickItemEditCtypeForm(base.CremeModelForm):
    cells = EntityCellsField(label=_('Columns'))

    class Meta:
        model = RelationBrickItem
        exclude = ('relation_type',)

    error_messages = {
        'invalid_first': _('This type of field can not be the first column.'),
    }

    def __init__(self, ctype, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctype = ctype

        cells_f = self.fields['cells']
        cells = self.instance.get_cells(ctype)
        cells_f.non_hiddable_cells = cells or ()
        cells_f.model = ctype.model_class()
        cells_f.initial = cells

    def _is_valid_first_column(self, cell):
        if isinstance(cell, EntityCellRegularField):
            field = cell.field_info[0]

            # These fields are already rendered with <a> tag ; it would be better to
            # have a higher semantic (ask to the fields printer how it renders theme ???)
            if (
                isinstance(field, (URLField, EmailField, ManyToManyField))
                or (
                    isinstance(field, ForeignKey)
                    and issubclass(field.remote_field.model, CremeEntity)
                )
            ):
                return False
        elif isinstance(cell, EntityCellRelation):
            return False

        return True

    def clean_cells(self):
        cells = self.cleaned_data['cells']

        if not self._errors and not self._is_valid_first_column(cells[0]):
            raise ValidationError(
                self.error_messages['invalid_first'],
                code='invalid_first',
            )

        return cells

    def save(self, *args, **kwargs):
        self.instance.set_cells(self.ctype, self.cleaned_data['cells'])

        return super().save(*args, **kwargs)


class _CustomBrickConfigItemBaseForm(base.CremeModelForm):
    class Meta(base.CremeModelForm.Meta):
        model = CustomBrickConfigItem

    def save(self, commit=True, *args, **kwargs):
        instance = self.instance

        if instance.pk:
            super().save(*args, **kwargs)
        else:
            super().save(commit=False)

            if commit:
                ct = instance.content_type
                generate_string_id_and_save(
                    CustomBrickConfigItem, [instance],
                    f'creme_core-user_customblock_{ct.app_label}-{ct.model}',
                )

        return instance


class CustomBrickConfigItemCreateForm(_CustomBrickConfigItemBaseForm):
    ctype = EntityCTypeChoiceField(
        label=_('Related resource'),
        widget=core_widgets.DynamicSelect(attrs={'autocomplete': True}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        get_for_model = ContentType.objects.get_for_model
        is_invalid = gui_bricks.brick_registry.is_model_invalid
        self.fields['ctype'].ctypes = (
            get_for_model(model)
            for model in creme_registry.iter_entity_models()
            if not is_invalid(model)
        )

    def clean(self, *args, **kwargs):
        cdata = super().clean(*args, **kwargs)

        if not self._errors:
            self.instance.content_type = self.cleaned_data['ctype']

        return cdata


class CustomBrickConfigItemEditForm(_CustomBrickConfigItemBaseForm):
    cells = EntityCellsField(label=_('Lines'))

    blocks = base.CremeModelForm.blocks.new({
        'id': 'cells', 'label': 'Columns', 'fields': ['cells'],
    })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = self.instance
        cells_f = self.fields['cells']
        cells = instance.cells
        cells_f.non_hiddable_cells = cells
        cells_f.model = instance.content_type.model_class()
        cells_f.initial = cells

    def clean(self, *args, **kwargs):
        cdata = super().clean(*args, **kwargs)

        if not self._errors:
            self.instance.cells = self.cleaned_data['cells']

        return cdata
