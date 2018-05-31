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

from itertools import chain
# import warnings

from django.contrib.contenttypes.models import ContentType
from django.db.models import URLField, EmailField, ManyToManyField, ForeignKey
from django.forms import MultipleChoiceField, ChoiceField, ModelChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext

# from creme.creme_core.apps import creme_app_configs
from creme.creme_core.core.entity_cell import EntityCellRegularField, EntityCellRelation
from creme.creme_core.forms import CremeForm, CremeModelForm, FieldBlockManager
from creme.creme_core.forms.fields import EntityCTypeChoiceField
from creme.creme_core.forms.header_filter import EntityCellsField
from creme.creme_core.forms.widgets import OrderedMultipleChoiceWidget, DynamicSelect, CremeRadioSelect
from creme.creme_core.gui import bricks as gui_bricks
from creme.creme_core.models import (RelationType, CremeEntity, UserRole,
        BrickDetailviewLocation, BrickHomeLocation, BrickMypageLocation,
        RelationBrickItem, CustomBrickConfigItem)
from creme.creme_core.registry import creme_registry
from creme.creme_core.utils.id_generator import generate_string_id_and_save
from creme.creme_core.utils.unicode_collation import collator


__all__ = ('BrickDetailviewLocationsAddForm', 'BrickDetailviewLocationsEditForm',
           # 'BlockPortalLocationsAddForm', 'BlockPortalLocationsEditForm',
           'BrickMypageLocationsForm',
           'RTypeBrickAddForm', 'RTypeBrickItemAddCtypeForm', 'RTypeBrickItemEditCtypeForm',
           'CustomBrickConfigItemCreateForm', 'CustomBrickConfigItemEditForm',
          )


class BrickLocationsField(MultipleChoiceField):
    def __init__(self, required=False, choices=(), widget=OrderedMultipleChoiceWidget, *args, **kwargs):
        super(BrickLocationsField, self).__init__(required=required, choices=choices,
                                                  widget=widget, *args, **kwargs
                                                 )


class _BrickLocationsForm(CremeForm):
    # def _build_portal_locations_field(self, app_name, field_name, block_locations):
    #     warnings.warn('creme_config.forms.bricks._BrickLocationsForm._build_portal_locations_field() is deprecated.',
    #                   DeprecationWarning
    #                  )
    #     bricks = self.fields[field_name]
    #     choices = [(brick.id_, unicode(brick.verbose_name))
    #                     for brick in gui_bricks.brick_registry.get_compatible_portal_blocks(app_name)
    #               ]
    #     sort_key = collator.sort_key
    #     choices.sort(key=lambda c: sort_key(c[1]))
    #
    #     bricks.choices = choices
    #     bricks.initial = [bl.brick_id for bl in block_locations]

    def _build_home_locations_field(self, field_name, brick_locations):
        bricks = self.fields[field_name]
        choices = [(brick.id_, unicode(brick.verbose_name))
                        for brick in gui_bricks.brick_registry.get_compatible_home_bricks()
                  ]
        sort_key = collator.sort_key
        choices.sort(key=lambda c: sort_key(c[1]))

        bricks.choices = choices
        bricks.initial = [bl.brick_id for bl in brick_locations]

    def _save_locations(self, location_model, location_builder,
                        bricks_partitions,
                        old_locations=(), role=None, superuser=False,
                       ):
        # At least 1 block per zone (even if it can be fake block)
        needed = sum(len(brick_ids) or 1 for brick_ids in bricks_partitions.itervalues())
        lendiff = needed - len(old_locations)

        if lendiff < 0:
            locations_store = old_locations[:needed]
            location_model.objects.filter(pk__in=[loc.id for loc in old_locations[needed:]]).delete()
        else:
            locations_store = list(old_locations)

            if lendiff > 0:
                locations_store.extend(location_builder() for __ in xrange(lendiff))

        store_it = iter(locations_store)

        for zone, brick_ids in bricks_partitions.iteritems():
            if not brick_ids:  # No brick for this zone -> fake brick_id
                brick_ids = ('',)

            for order, brick_id in enumerate(brick_ids, start=1):
                location = store_it.next()
                location.brick_id = brick_id
                location.order = order
                location.zone  = zone  # NB: BlockPortalLocation has not 'zone' attr, but we do not care ! :)
                location.role  = role  # NB: idem with 'role'
                location.superuser = superuser  # NB: idem with 'superuser'

                location.save()


class _BrickDetailviewLocationsForm(_BrickLocationsForm):
    hat    = ChoiceField(label=_(u'Header block'), widget=CremeRadioSelect)
    top    = BrickLocationsField(label=_(u'Blocks to display on top'))
    left   = BrickLocationsField(label=_(u'Blocks to display on left side'))
    right  = BrickLocationsField(label=_(u'Blocks to display on right side'))
    bottom = BrickLocationsField(label=_(u'Blocks to display on bottom'))

    error_messages = {
        'duplicated_block': _(u'The following block should be displayed only once: «%(block)s»'),
        'empty_config':     _(u'Your configuration is empty !'),
    }

    _ZONES = (('top',    BrickDetailviewLocation.TOP),
              ('left',   BrickDetailviewLocation.LEFT),
              ('right',  BrickDetailviewLocation.RIGHT),
              ('bottom', BrickDetailviewLocation.BOTTOM)
             )

    def __init__(self, *args, **kwargs):
        super(_BrickDetailviewLocationsForm, self).__init__(*args, **kwargs)
        self.ct = ct = self.initial['content_type']
        self.role = None
        self.superuser = False
        self.locations = ()
        model = ct.model_class() if ct else None

        self.choices = choices = [
            (brick.id_, unicode(brick.verbose_name))
               for brick in gui_bricks.brick_registry.get_compatible_bricks(model=model)
        ]

        sort_key = collator.sort_key
        choices.sort(key=lambda c: sort_key(c[1]))

        fields = self.fields

        for fname, zone in self._ZONES:
            fields[fname].choices = choices

        hat_bricks = []
        if model:
            hat_bricks.extend(gui_bricks.brick_registry.get_compatible_hat_bricks(model))

        if len(hat_bricks) > 1:
            hat_f = fields['hat']
            hat_f.choices = [(brick.id_, brick.verbose_name) for brick in hat_bricks]
        else:
            del fields['hat']

    def clean(self):
        cdata = super(_BrickDetailviewLocationsForm, self).clean()
        all_brick_ids = set()

        for brick_id in chain(cdata['top'], cdata['left'], cdata['right'], cdata['bottom']):
            if brick_id in all_brick_ids:
                verbose_name = '??'
                for b_id, b_vname in self.choices:
                    if b_id == brick_id:
                        verbose_name = b_vname
                        break

                raise ValidationError(self.error_messages['duplicated_block'],
                                      params={'block': verbose_name},
                                      code='duplicated_block',
                                     )

            all_brick_ids.add(brick_id)

        if not all_brick_ids:
            raise ValidationError(self.error_messages['empty_config'],
                                  code='empty_config',
                                 )

        return cdata

    def save(self, *args, **kwargs):
        cdata = self.cleaned_data
        hat_brick_id = cdata.get('hat')

        self._save_locations(BrickDetailviewLocation,
                             lambda: BrickDetailviewLocation(content_type=self.ct),
                             bricks_partitions={
                                 BrickDetailviewLocation.HAT:    [hat_brick_id] if hat_brick_id else [],
                                 BrickDetailviewLocation.TOP:    cdata['top'],
                                 BrickDetailviewLocation.LEFT:   cdata['left'],
                                 BrickDetailviewLocation.RIGHT:  cdata['right'],
                                 BrickDetailviewLocation.BOTTOM: cdata['bottom'],
                             },
                             old_locations=self.locations,
                             role=self.role, superuser=self.superuser,
                            )


class BrickDetailviewLocationsAddForm(_BrickDetailviewLocationsForm):
    role = ModelChoiceField(label=_(u'Role'), queryset=UserRole.objects.none(),
                            empty_label=None, required=False,
                           )

    # TODO: manage Meta.fields in '*'
    blocks = FieldBlockManager(('general', _(u'Configuration'), ('role', 'hat', 'top', 'left', 'right', 'bottom')))

    def __init__(self, *args, **kwargs):
        super(BrickDetailviewLocationsAddForm, self).__init__(*args, **kwargs)
        fields = self.fields

        role_f = fields['role']
        used_role_ids = set(BrickDetailviewLocation.objects
                                                   .filter(content_type=self.ct)
                                                   .exclude(role__isnull=True, superuser=False)
                                                   .values_list('role', flat=True)
                           )

        try:
            used_role_ids.remove(None)
        except KeyError:
            role_f.empty_label = u'*%s*' % ugettext(u'Superuser')  # NB: browser can ignore <em> tag in <option>...

        role_f.queryset = UserRole.objects.exclude(pk__in=used_role_ids)

        hat_f = fields.get('hat')
        if hat_f:
            hat_f.initial = hat_f.choices[0][0]

    def save(self, *args, **kwargs):
        self.role      = role = self.cleaned_data['role']
        self.superuser = (role is None)
        super(BrickDetailviewLocationsAddForm, self).save(*args, **kwargs)


class BrickDetailviewLocationsEditForm(_BrickDetailviewLocationsForm):
    def __init__(self, *args, **kwargs):
        super(BrickDetailviewLocationsEditForm, self).__init__(*args, **kwargs)
        initial = self.initial
        self.role      = role      = initial['role']
        self.superuser = superuser = initial['superuser']

        self.locations = locations = \
            BrickDetailviewLocation.objects.filter(content_type=self.ct,
                                                   role=role, superuser=superuser,
                                                  ) \
                                           .order_by('order')

        fields = self.fields

        for fname, zone in self._ZONES:
            fields[fname].initial = [bl.brick_id for bl in locations if bl.zone == zone]

        hat_f = fields.get('hat')
        if hat_f:
            HEADER = BrickDetailviewLocation.HAT
            selected = [bl.brick_id for bl in locations if bl.zone == HEADER]
            hat_f.initial = selected[0] if selected else hat_f.choices[0][0]


# class _BlockPortalLocationsForm(_BrickLocationsForm):
#     def __init__(self, *args, **kwargs):
#         warnings.warn('creme_config.forms.bricks._BlockPortalLocationsForm is deprecated.', DeprecationWarning)
#         super(_BlockPortalLocationsForm, self).__init__(*args, **kwargs)
#
#     def _save_portal_locations(self, app_name, old_locations=(), block_ids=()):
#         self._save_locations(BlockPortalLocation,
#                              lambda: BlockPortalLocation(app_name=app_name),
#                              {1: block_ids},  # 1 is a "nameless" zone
#                              old_locations,
#                             )


# class BlockPortalLocationsAddForm(_BlockPortalLocationsForm):
#     app_name = ChoiceField(label=_(u'Related application'), choices=(),
#                            widget=DynamicSelect(attrs={'autocomplete': True}),
#                           )
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('creme_config.forms.bricks.BlockPortalLocationsAddForm is deprecated.', DeprecationWarning)
#         super(BlockPortalLocationsAddForm, self).__init__(*args, **kwargs)
#
#         excluded_apps = set(BlockPortalLocation.objects.values_list('app_name', flat=True))
#         excluded_apps.add('creme_core')
#         excluded_apps.add('creme_config')
#
#         self.fields['app_name'].choices = [(app_config.label, app_config.verbose_name)
#                                                for app_config in creme_app_configs()
#                                                    if not app_config.label in excluded_apps
#                                           ]
#
#     def save(self, *args, **kwargs):
#         self._save_portal_locations(self.cleaned_data['app_name'])


# class BlockPortalLocationsEditForm(_BlockPortalLocationsForm):
#     blocks = BrickLocationsField(label=_(u'Blocks to display on the portal'))
#
#     def __init__(self, app_name, block_locations, *args, **kwargs):
#         warnings.warn('creme_config.forms.bricks.BlockPortalLocationsEditForm is deprecated.', DeprecationWarning)
#         super(BlockPortalLocationsEditForm, self).__init__(*args, **kwargs)
#         self.app_name = app_name
#         self.locations = block_locations
#
#         self._build_portal_locations_field(app_name=app_name, field_name='blocks',
#                                            block_locations=block_locations,
#                                           )
#
#     def save(self, *args, **kwargs):
#         self._save_portal_locations(self.app_name, self.locations, self.cleaned_data['blocks'])


class BrickHomeLocationsForm(_BrickLocationsForm):
    bricks = BrickLocationsField(label=_(u'Blocks to display on the home'))

    def __init__(self, *args, **kwargs):
        super(BrickHomeLocationsForm, self).__init__(*args, **kwargs)
        # self.locations = locations = BlockPortalLocation.objects.filter(app_name='creme_core')
        self.locations = locations = BrickHomeLocation.objects.all()

        self._build_home_locations_field(field_name='bricks', brick_locations=locations)

    def save(self, *args, **kwargs):
        self._save_locations(location_model=BrickHomeLocation,
                             # location_builder=lambda: BlockPortalLocation(app_name='creme_core'),
                             location_builder=lambda: BrickHomeLocation(),
                             bricks_partitions={1: self.cleaned_data['bricks']},  # 1 is a "nameless" zone
                             old_locations=self.locations,
                            )


class BrickMypageLocationsForm(_BrickLocationsForm):
    # blocks = BrickLocationsField(label=_(u'Blocks to display on the "My Page" of the users'))
    bricks = BrickLocationsField(label=_(u'Blocks to display on the «My Page» of the users'))

    def __init__(self, owner, *args, **kwargs):
        super(BrickMypageLocationsForm, self).__init__(*args, **kwargs)
        self.owner = owner
        self.locations = locations = BrickMypageLocation.objects.filter(user=owner)

        # self._build_home_locations_field(field_name='blocks', brick_locations=locations)
        self._build_home_locations_field(field_name='bricks', brick_locations=locations)

    def save(self, *args, **kwargs):
        self._save_locations(BrickMypageLocation,
                             lambda: BrickMypageLocation(user=self.owner),
                             # {1: self.cleaned_data['blocks']},  # 1 is a "nameless" zone
                             {1: self.cleaned_data['bricks']},  # 1 is a "nameless" zone
                             self.locations,
                            )


class RTypeBrickAddForm(CremeModelForm):
    relation_type = ModelChoiceField(RelationType.objects, empty_label=None,
                                     widget=DynamicSelect(attrs={'autocomplete': True}),
                                    )

    class Meta(CremeModelForm.Meta):
        model = RelationBrickItem

    def __init__(self, *args, **kwargs):
        super(RTypeBrickAddForm, self).__init__(*args, **kwargs)

        existing_type_ids = RelationBrickItem.objects.values_list('relation_type_id', flat=True)

        relation_type = self.fields['relation_type']
        relation_type.queryset = RelationType.objects.exclude(pk__in=existing_type_ids)

    def save(self, *args, **kwargs):
        self.instance.brick_id = gui_bricks.SpecificRelationsBrick.generate_id(
                                        'creme_config',
                                        self.cleaned_data['relation_type'].id,
                                    )
        return super(RTypeBrickAddForm, self).save(*args, **kwargs)


class RTypeBrickItemAddCtypeForm(CremeModelForm):
    ctype = EntityCTypeChoiceField(label=_(u'Customised resource'),
                                   widget=DynamicSelect({'autocomplete': True}),
                                  )

    class Meta:
        model = RelationBrickItem
        exclude = ('relation_type',)

    def __init__(self, *args, **kwargs):
        super(RTypeBrickItemAddCtypeForm, self).__init__(*args, **kwargs)
        instance = self.instance
        ct_field = self.fields['ctype']
        compatible_ctypes = instance.relation_type.object_ctypes.all()

        if compatible_ctypes:
            ct_field.ctypes = compatible_ctypes

        used_ct_ids = frozenset(ct.id for ct, cells in instance.iter_cells())  # TODO: iter_ctypes() ??
        ct_field.ctypes = (ct for ct in ct_field.ctypes if ct.id not in used_ct_ids)

    def save(self, *args, **kwargs):
        self.instance.set_cells(self.cleaned_data['ctype'], ())

        return super(RTypeBrickItemAddCtypeForm, self).save(*args, **kwargs)


class RTypeBrickItemEditCtypeForm(CremeModelForm):
    cells = EntityCellsField(label=_(u'Columns'))

    class Meta:
        model = RelationBrickItem
        exclude = ('relation_type',)

    error_messages = {
        'invalid_first': _(u'This type of field can not be the first column.'),
    }

    def __init__(self, ctype, *args, **kwargs):
        super(RTypeBrickItemEditCtypeForm, self).__init__(*args, **kwargs)
        self.ctype = ctype

        cells_f = self.fields['cells']
        cells = self.instance.get_cells(ctype)
        cells_f.non_hiddable_cells = cells or ()
        cells_f.content_type = ctype
        cells_f.initial = cells

    def _is_valid_first_column(self, cell):
        if isinstance(cell, EntityCellRegularField):
            field = cell.field_info[0]

            # These fields are already rendered with <a> tag ; it would be better to
            # have a higher semantic (ask to the fields printer how it renders theme ???)
            if isinstance(field, (URLField, EmailField, ManyToManyField)) or \
               (isinstance(field, ForeignKey) and issubclass(field.remote_field.model, CremeEntity)):
                return False
        elif isinstance(cell, EntityCellRelation):
            return False

        return True

    def clean_cells(self):
        cells = self.cleaned_data['cells']

        if not self._errors and not self._is_valid_first_column(cells[0]):
            raise ValidationError(self.error_messages['invalid_first'], code='invalid_first')

        return cells

    def save(self, *args, **kwargs):
        self.instance.set_cells(self.ctype, self.cleaned_data['cells'])

        return super(RTypeBrickItemEditCtypeForm, self).save(*args, **kwargs)


class CustomBrickConfigItemCreateForm(CremeModelForm):
    ctype = EntityCTypeChoiceField(label=_(u'Related resource'),
                                   widget=DynamicSelect(attrs={'autocomplete': True}),
                                  )

    class Meta(CremeModelForm.Meta):
        model = CustomBrickConfigItem

    def __init__(self, *args, **kwargs):
        super(CustomBrickConfigItemCreateForm, self).__init__(*args, **kwargs)
        # TODO: add an 'exclude' argument in creme_entity_content_types() ??
        get_for_model = ContentType.objects.get_for_model
        is_invalid = gui_bricks.brick_registry.is_model_invalid
        self.fields['ctype'].ctypes = (get_for_model(model)
                                           for model in creme_registry.iter_entity_models()
                                              if not is_invalid(model)
                                      )

    def save(self, *args, **kwargs):
        instance = self.instance
        ct = self.cleaned_data['ctype']
        instance.content_type = ct

        super(CustomBrickConfigItemCreateForm, self).save(commit=False)
        generate_string_id_and_save(CustomBrickConfigItem, [instance],
                                    'creme_core-user_customblock_%s-%s' % (ct.app_label, ct.model)
                                   )

        return instance


class CustomBrickConfigItemEditForm(CremeModelForm):
    cells = EntityCellsField(label=_(u'Lines'))

    blocks = CremeModelForm.blocks.new(('cells', 'Columns', ['cells']))

    class Meta(CremeModelForm.Meta):
        model = CustomBrickConfigItem

    def __init__(self, *args, **kwargs):
        super(CustomBrickConfigItemEditForm, self).__init__(*args, **kwargs)

        instance = self.instance
        cells_f = self.fields['cells']
        cells = instance.cells
        cells_f.non_hiddable_cells = cells
        cells_f.content_type = instance.content_type
        cells_f.initial = cells

    def save(self, *args, **kwargs):
        self.instance.cells = self.cleaned_data['cells']

        return super(CustomBrickConfigItemEditForm, self).save(*args, **kwargs)
