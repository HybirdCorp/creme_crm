# -*- coding: utf-8 -*-

import warnings

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.fields import MultiEntityCTypeChoiceField
from creme.creme_core.models import RelationBlockItem

from . import bricks
from .bricks import _BlockPortalLocationsForm, BlockPortalLocationsAddForm, BlockPortalLocationsEditForm

warnings.warn('creme_config.forms.blocks is deprecated ; use creme_config.forms.bricks instead.', DeprecationWarning)


class BlockLocationsField(bricks.BrickLocationsField):
    def __init__(self, *args, **kwargs):
        warnings.warn('blocks.BlockLocationsField is deprecated ; use bricks.BrickLocationsField instead.',
                      DeprecationWarning
                     )

        super(BlockLocationsField, self).__init__(*args, **kwargs)


class _BlockLocationsForm(bricks._BrickLocationsForm):
    def __init__(self, *args, **kwargs):
        warnings.warn('blocks._BlockLocationsForm is deprecated ; use bricks._BrickLocationsForm instead.',
                      DeprecationWarning
                     )

        super(_BlockLocationsForm, self).__init__(*args, **kwargs)


class _BlockDetailviewLocationsForm(bricks._BrickDetailviewLocationsForm):
    def __init__(self, *args, **kwargs):
        warnings.warn('blocks._BlockDetailviewLocationsForm is deprecated ; '
                      'use bricks._BrickDetailviewLocationsForm instead.',
                      DeprecationWarning
                     )

        super(_BlockDetailviewLocationsForm, self).__init__(*args, **kwargs)


class BlockDetailviewLocationsAddForm(bricks.BrickDetailviewLocationsAddForm):
    def __init__(self, *args, **kwargs):
        warnings.warn('blocks.BlockDetailviewLocationsAddForm is deprecated ; '
                      'use bricks.BrickDetailviewLocationsAddForm instead.',
                      DeprecationWarning
                     )

        super(BlockDetailviewLocationsAddForm, self).__init__(*args, **kwargs)


class BlockDetailviewLocationsEditForm(bricks.BrickDetailviewLocationsEditForm):
    def __init__(self, *args, **kwargs):
        warnings.warn('blocks.BlockDetailviewLocationsEditForm is deprecated ; '
                      'use bricks.BrickDetailviewLocationsEditForm instead.',
                      DeprecationWarning
                     )

        super(BlockDetailviewLocationsEditForm, self).__init__(*args, **kwargs)


class BlockMypageLocationsForm(bricks.BrickMypageLocationsForm):
    def __init__(self, *args, **kwargs):
        warnings.warn('blocks.BlockMypageLocationsForm is deprecated ; use bricks.BrickMypageLocationsForm instead.',
                      DeprecationWarning
                     )

        super(BlockMypageLocationsForm, self).__init__(*args, **kwargs)


class RelationBlockAddForm(bricks.RTypeBrickAddForm):
    def __init__(self, *args, **kwargs):
        warnings.warn('blocks.RelationBlockAddForm is deprecated ; use bricks.RTypeBrickAddForm instead.',
                      DeprecationWarning
                     )

        super(RelationBlockAddForm, self).__init__(*args, **kwargs)


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


class RelationBlockItemEditCtypeForm(bricks.RTypeBrickItemEditCtypeForm):
    def __init__(self, *args, **kwargs):
        warnings.warn('blocks.RelationBlockItemEditCtypeForm is deprecated ; '
                      'use bricks.RTypeBrickItemEditCtypeForm instead.',
                      DeprecationWarning
                     )

        super(RelationBlockItemEditCtypeForm, self).__init__(*args, **kwargs)


class CustomBlockConfigItemCreateForm(bricks.CustomBrickConfigItemCreateForm):
    def __init__(self, *args, **kwargs):
        warnings.warn('blocks.CustomBlockConfigItemCreateForm is deprecated ; '
                      'use bricks.CustomBrickConfigItemCreateForm instead.',
                      DeprecationWarning
                     )

        super(CustomBlockConfigItemCreateForm, self).__init__(*args, **kwargs)


class CustomBlockConfigItemEditForm(bricks.CustomBrickConfigItemEditForm):
    def __init__(self, *args, **kwargs):
        warnings.warn('blocks.CustomBlockConfigItemEditForm is deprecated ; '
                      'use bricks.CustomBrickConfigItemEditForm instead.',
                      DeprecationWarning
                     )

        super(CustomBlockConfigItemEditForm, self).__init__(*args, **kwargs)
