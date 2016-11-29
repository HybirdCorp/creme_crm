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

from itertools import chain
import warnings

from django.contrib.contenttypes.models import ContentType
from django.db.models import URLField, EmailField, ManyToManyField, ForeignKey
from django.forms import MultipleChoiceField, ChoiceField, ModelChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.apps import creme_app_configs
from creme.creme_core.constants import MODELBLOCK_ID
from creme.creme_core.core.entity_cell import EntityCellRegularField, EntityCellRelation
from creme.creme_core.forms import CremeForm, CremeModelForm, FieldBlockManager
from creme.creme_core.forms.fields import EntityCTypeChoiceField, MultiEntityCTypeChoiceField
from creme.creme_core.forms.header_filter import EntityCellsField
from creme.creme_core.forms.widgets import OrderedMultipleChoiceWidget, DynamicSelect
from creme.creme_core.gui.block import block_registry, SpecificRelationsBlock
from creme.creme_core.models import (RelationType, CremeEntity, UserRole,
        BlockDetailviewLocation, BlockPortalLocation, BlockMypageLocation,
        RelationBlockItem, CustomBlockConfigItem)
from creme.creme_core.registry import creme_registry
from creme.creme_core.utils.id_generator import generate_string_id_and_save
from creme.creme_core.utils.unicode_collation import collator


__all__ = ('BlockDetailviewLocationsAddForm', 'BlockDetailviewLocationsEditForm',
           'BlockPortalLocationsAddForm', 'BlockPortalLocationsEditForm',
           'BlockMypageLocationsForm',
           'RelationBlockAddForm',
           'RelationBlockItemAddCtypesForm', 'RelationBlockItemAddCtypeForm',
           'RelationBlockItemEditCtypeForm',
           'CustomBlockConfigItemCreateForm', 'CustomBlockConfigItemEditForm',
          )


class BlockLocationsField(MultipleChoiceField):
    def __init__(self, required=False, choices=(), widget=OrderedMultipleChoiceWidget, *args, **kwargs):
        super(BlockLocationsField, self).__init__(required=required, choices=choices,
                                                  widget=widget, *args, **kwargs
                                                 )


class _BlockLocationsForm(CremeForm):
    def _build_portal_locations_field(self, app_name, field_name, block_locations):
        blocks = self.fields[field_name]
        choices = [(block.id_, unicode(block.verbose_name))
                        for block in block_registry.get_compatible_portal_blocks(app_name)
                  ]
        sort_key = collator.sort_key
        choices.sort(key=lambda c: sort_key(c[1]))

        blocks.choices = choices
        blocks.initial = [bl.block_id for bl in block_locations]

    def _save_locations(self, location_model, location_builder, blocks_partitions,
                        old_locations=(), role=None, superuser=False,
                       ):
        # At least 1 block per zone (even if it can be fake block)
        needed = sum(len(block_ids) or 1 for block_ids in blocks_partitions.itervalues())
        lendiff = needed - len(old_locations)

        if lendiff < 0:
            locations_store = old_locations[:needed]
            location_model.objects.filter(pk__in=[loc.id for loc in old_locations[needed:]]).delete()
        else:
            locations_store = list(old_locations)

            if lendiff > 0:
                locations_store.extend(location_builder() for __ in xrange(lendiff))

        store_it = iter(locations_store)

        for zone, block_ids in blocks_partitions.iteritems():
            if not block_ids:  # No block for this zone -> fake block_id
                block_ids = ('',)

            for order, block_id in enumerate(block_ids, start=1):
                location = store_it.next()
                location.block_id = block_id
                location.order    = order
                location.zone     = zone  # NB: BlockPortalLocation has not 'zone' attr, but we do not care ! :)
                location.role     = role  # NB: idem with 'role'
                location.superuser = superuser  # NB: idem with 'superuser'

                location.save()


class _BlockDetailviewLocationsForm(_BlockLocationsForm):
    top    = BlockLocationsField(label=_(u'Blocks to display on top'))
    left   = BlockLocationsField(label=_(u'Blocks to display on left side'))
    right  = BlockLocationsField(label=_(u'Blocks to display on right side'))
    bottom = BlockLocationsField(label=_(u'Blocks to display on bottom'))

    error_messages = {
        'duplicated_block': _(u'The following block should be displayed only once: «%(block)s»'),
        'empty_config':     _(u'Your configuration is empty !'),
    }

    _ZONES = (('top',    BlockDetailviewLocation.TOP),
              ('left',   BlockDetailviewLocation.LEFT),
              ('right',  BlockDetailviewLocation.RIGHT),
              ('bottom', BlockDetailviewLocation.BOTTOM)
             )

    def __init__(self, *args, **kwargs):
        super(_BlockDetailviewLocationsForm, self).__init__(*args, **kwargs)
        self.ct   = ct = self.initial['content_type']
        self.role = None
        self.superuser = False
        self.locations = ()

        self.modelblock_vname = modelblock_vname = ugettext('Information on the entity')
        choices = [(MODELBLOCK_ID, modelblock_vname)]
        choices.extend((block.id_, unicode(block.verbose_name))
                           for block in block_registry.get_compatible_blocks(model=ct.model_class() if ct else None)
                      )

        sort_key = collator.sort_key
        choices.sort(key=lambda c: sort_key(c[1]))

        fields = self.fields

        for fname, zone in self._ZONES:
            fields[fname].choices = choices

    def clean(self):
        cdata = super(_BlockDetailviewLocationsForm, self).clean()
        all_block_ids = set()

        for block_id in chain(cdata['top'], cdata['left'], cdata['right'], cdata['bottom']):
            if block_id in all_block_ids:
                raise ValidationError(self.error_messages['duplicated_block'],
                                      params={'block': self.modelblock_vname
                                                       if block_id == MODELBLOCK_ID else
                                                       block_registry[block_id].verbose_name,
                                             },
                                      code='duplicated_block',
                                     )

            all_block_ids.add(block_id)

        if not all_block_ids:
            raise ValidationError(self.error_messages['empty_config'],
                                  code='empty_config',
                                 )

        return cdata

    def save(self, *args, **kwargs):
        cdata = self.cleaned_data

        self._save_locations(BlockDetailviewLocation,
                             lambda: BlockDetailviewLocation(content_type=self.ct),
                             {BlockDetailviewLocation.TOP:    cdata['top'],
                              BlockDetailviewLocation.LEFT:   cdata['left'],
                              BlockDetailviewLocation.RIGHT:  cdata['right'],
                              BlockDetailviewLocation.BOTTOM: cdata['bottom'],
                             },
                             old_locations=self.locations,
                             role=self.role, superuser=self.superuser,
                            )


class BlockDetailviewLocationsAddForm(_BlockDetailviewLocationsForm):
    role = ModelChoiceField(label=_(u'Role'), queryset=UserRole.objects.none(),
                            empty_label=None, required=False,
                           )

    # TODO: manage Meta.fields in '*'
    blocks = FieldBlockManager(('general', _(u'Configuration'), ('role', 'top', 'left', 'right', 'bottom')))

    def __init__(self, *args, **kwargs):
        super(BlockDetailviewLocationsAddForm, self).__init__(*args, **kwargs)

        role_f = self.fields['role']
        used_role_ids = set(BlockDetailviewLocation.objects.filter(content_type=self.ct)
                                                   .exclude(role__isnull=True, superuser=False)
                                                   .values_list('role', flat=True)
                           )

        try:
            used_role_ids.remove(None)
        except KeyError:
            role_f.empty_label = u'*%s*' % ugettext(u'Superuser')  # NB: browser can ignore <em> tag in <option>...

        role_f.queryset = UserRole.objects.exclude(pk__in=used_role_ids)

    def save(self, *args, **kwargs):
        self.role      = role = self.cleaned_data['role']
        self.superuser = (role is None)
        super(BlockDetailviewLocationsAddForm, self).save(*args, **kwargs)


class BlockDetailviewLocationsEditForm(_BlockDetailviewLocationsForm):
    def __init__(self, *args, **kwargs):
        super(BlockDetailviewLocationsEditForm, self).__init__(*args, **kwargs)
        initial = self.initial
        self.role      = role      = initial['role']
        self.superuser = superuser = initial['superuser']

        self.locations = locations = \
            BlockDetailviewLocation.objects.filter(content_type=self.ct,
                                                   role=role, superuser=superuser,
                                                  ) \
                                           .order_by('order')

        fields = self.fields

        for fname, zone in self._ZONES:
            fields[fname].initial = [bl.block_id for bl in locations if bl.zone == zone]


class _BlockPortalLocationsForm(_BlockLocationsForm):
    def _save_portal_locations(self, app_name, old_locations=(), block_ids=()):
        self._save_locations(BlockPortalLocation,
                             lambda: BlockPortalLocation(app_name=app_name),
                             {1: block_ids},  # 1 is a "nameless" zone
                             old_locations,
                            )


class BlockPortalLocationsAddForm(_BlockPortalLocationsForm):
    app_name = ChoiceField(label=_(u'Related application'), choices=(),
                           widget=DynamicSelect(attrs={'autocomplete': True}),
                          )

    def __init__(self, *args, **kwargs):
        super(BlockPortalLocationsAddForm, self).__init__(*args, **kwargs)

        excluded_apps = set(BlockPortalLocation.objects.values_list('app_name', flat=True))
        excluded_apps.add('creme_core')
        excluded_apps.add('creme_config')

        # self.fields['app_name'].choices = [(app.name, app.verbose_name)
        #                                        for app in creme_registry.iter_apps()
        #                                            if not app.name in excluded_apps
        #                                   ]
        self.fields['app_name'].choices = [(app_config.label, app_config.verbose_name)
                                               for app_config in creme_app_configs()
                                                   if not app_config.label in excluded_apps
                                          ]

    def save(self, *args, **kwargs):
        self._save_portal_locations(self.cleaned_data['app_name'])


class BlockPortalLocationsEditForm(_BlockPortalLocationsForm):
    blocks = BlockLocationsField(label=_(u'Blocks to display on the portal'))

    def __init__(self, app_name, block_locations, *args, **kwargs):
        super(BlockPortalLocationsEditForm, self).__init__(*args, **kwargs)
        self.app_name = app_name
        self.locations = block_locations

        self._build_portal_locations_field(app_name=app_name, field_name='blocks',
                                           block_locations=block_locations,
                                          )

    def save(self, *args, **kwargs):
        self._save_portal_locations(self.app_name, self.locations, self.cleaned_data['blocks'])


class BlockMypageLocationsForm(_BlockLocationsForm):
    blocks = BlockLocationsField(label=_(u"""Blocks to display on the "My Page" of the users"""))

    def __init__(self, owner, *args, **kwargs):
        super(BlockMypageLocationsForm, self).__init__(*args, **kwargs)
        self.owner = owner
        self.locations = locations = BlockMypageLocation.objects.filter(user=owner)

        self._build_portal_locations_field(app_name='creme_core', field_name='blocks',
                                           block_locations=locations,
                                          )

    def save(self, *args, **kwargs):
        self._save_locations(BlockMypageLocation,
                             lambda: BlockMypageLocation(user=self.owner),
                             {1: self.cleaned_data['blocks']},  # 1 is a "nameless" zone
                             self.locations,
                            )


class RelationBlockAddForm(CremeModelForm):
    relation_type = ModelChoiceField(RelationType.objects, empty_label=None,
                                     widget=DynamicSelect(attrs={'autocomplete': True}),
                                    )

    class Meta(CremeModelForm.Meta):
        model = RelationBlockItem

    def __init__(self, *args, **kwargs):
        super(RelationBlockAddForm, self).__init__(*args, **kwargs)

        existing_type_ids = RelationBlockItem.objects.values_list('relation_type_id', flat=True)

        relation_type = self.fields['relation_type']
        relation_type.queryset = RelationType.objects.exclude(pk__in=existing_type_ids)

    def save(self, *args, **kwargs):
        self.instance.block_id = SpecificRelationsBlock.generate_id(
                                        'creme_config',
                                        self.cleaned_data['relation_type'].id,
                                    )
        return super(RelationBlockAddForm, self).save(*args, **kwargs)


class RelationBlockItemAddCtypesForm(CremeModelForm):
    ctypes = MultiEntityCTypeChoiceField(label=_(u'Customised resource'))

    class Meta:
        model = RelationBlockItem
        exclude = ('relation_type',)

    def __init__(self, *args, **kwargs):
        warnings.warn('RelationBlockItemAddCtypesForm is now deprecated.', DeprecationWarning)

        super(RelationBlockItemAddCtypesForm, self).__init__(*args, **kwargs)
        instance = self.instance
        ct_field = self.fields['ctypes']
        compatible_ctypes = instance.relation_type.object_ctypes.all()

        if compatible_ctypes:
            ct_field.ctypes = compatible_ctypes

        used_ct_ids = frozenset(ct.id for ct, cells in instance.iter_cells())  # TODO: iter_ctypes() ??
        ct_field.ctypes = (ct for ct in ct_field.ctypes if ct.id not in used_ct_ids)

    def save(self, *args, **kwargs):
        instance = self.instance

        for ctype in self.cleaned_data['ctypes']:
            instance.set_cells(ctype, ())

        return super(RelationBlockItemAddCtypesForm, self).save(*args, **kwargs)


class RelationBlockItemAddCtypeForm(CremeModelForm):
    ctype = EntityCTypeChoiceField(label=_(u'Customised resource'),
                                   widget=DynamicSelect({'autocomplete': True}),
                                  )

    class Meta:
        model = RelationBlockItem
        exclude = ('relation_type',)

    def __init__(self, *args, **kwargs):
        super(RelationBlockItemAddCtypeForm, self).__init__(*args, **kwargs)
        instance = self.instance
        ct_field = self.fields['ctype']
        compatible_ctypes = instance.relation_type.object_ctypes.all()

        if compatible_ctypes:
            ct_field.ctypes = compatible_ctypes

        used_ct_ids = frozenset(ct.id for ct, cells in instance.iter_cells())  # TODO: iter_ctypes() ??
        ct_field.ctypes = (ct for ct in ct_field.ctypes if ct.id not in used_ct_ids)

    def save(self, *args, **kwargs):
        self.instance.set_cells(self.cleaned_data['ctype'], ())

        return super(RelationBlockItemAddCtypeForm, self).save(*args, **kwargs)


class RelationBlockItemEditCtypeForm(CremeModelForm):
    cells = EntityCellsField(label=_(u'Columns'))

    class Meta:
        model = RelationBlockItem
        exclude = ('relation_type',)

    error_messages = {
        'invalid_first': _('This type of field can not be the first column.'),
    }

    def __init__(self, ctype, *args, **kwargs):
        super(RelationBlockItemEditCtypeForm, self).__init__(*args, **kwargs)
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
               (isinstance(field, ForeignKey) and issubclass(field.rel.to, CremeEntity)):
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

        return super(RelationBlockItemEditCtypeForm, self).save(*args, **kwargs)


class CustomBlockConfigItemCreateForm(CremeModelForm):
    ctype = EntityCTypeChoiceField(label=_(u'Related resource'),
                                   widget=DynamicSelect(attrs={'autocomplete': True}),
                                  )

    class Meta(CremeModelForm.Meta):
        model = CustomBlockConfigItem

    def __init__(self, *args, **kwargs):
        super(CustomBlockConfigItemCreateForm, self).__init__(*args, **kwargs)
        # TODO: add an 'exclude' argument in creme_entity_content_types() ??
        get_for_model = ContentType.objects.get_for_model
        is_invalid = block_registry.is_model_invalid
        self.fields['ctype'].ctypes = (get_for_model(model)
                                           for model in creme_registry.iter_entity_models()
                                              if not is_invalid(model)
                                      )

    def save(self, *args, **kwargs):
        instance = self.instance
        ct = self.cleaned_data['ctype']
        instance.content_type = ct

        super(CustomBlockConfigItemCreateForm, self).save(commit=False)
        generate_string_id_and_save(CustomBlockConfigItem, [instance],
                                    'creme_core-user_customblock_%s-%s' % (ct.app_label, ct.model)
                                   )

        return instance


class CustomBlockConfigItemEditForm(CremeModelForm):
    cells = EntityCellsField(label=_(u'Lines'))

    blocks = CremeModelForm.blocks.new(('cells', 'Columns', ['cells']))

    class Meta(CremeModelForm.Meta):
        model = CustomBlockConfigItem

    def __init__(self, *args, **kwargs):
        super(CustomBlockConfigItemEditForm, self).__init__(*args, **kwargs)

        instance = self.instance
        cells_f = self.fields['cells']
        cells = instance.cells
        cells_f.non_hiddable_cells = cells
        cells_f.content_type = instance.content_type
        cells_f.initial = cells

    def save(self, *args, **kwargs):
        self.instance.cells = self.cleaned_data['cells']

        return super(CustomBlockConfigItemEditForm, self).save(*args, **kwargs)
