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

from itertools import chain

from django.forms import MultipleChoiceField, ChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType

from creme.creme_core.registry import creme_registry
from creme.creme_core.models import (RelationType, BlockDetailviewLocation, BlockPortalLocation,
                               BlockMypageLocation, RelationBlockItem)
from creme.creme_core.forms import CremeForm, CremeModelForm
from creme.creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme.creme_core.gui.block import block_registry, SpecificRelationsBlock
from creme.creme_core.utils import creme_entity_content_types
from creme.creme_core.constants import MODELBLOCK_ID


__all__ = ('BlockDetailviewLocationsAddForm', 'BlockDetailviewLocationsEditForm',
           'BlockPortalLocationsAddForm', 'BlockPortalLocationsEditForm',
           'BlockMypageLocationsForm',
           'RelationBlockAddForm',
          )


class BlockLocationsField(MultipleChoiceField):
    def __init__(self, required=False, choices=(), widget=OrderedMultipleChoiceWidget, *args, **kwargs):
        super(BlockLocationsField, self).__init__(required=required, choices=choices, widget=widget, *args, **kwargs)


class _BlockLocationsForm(CremeForm):
    def _build_portal_locations_field(self, app_name, field_name, block_locations):
        blocks = self.fields[field_name]
        blocks.choices = [(block.id_, block.verbose_name)
                            for block in block_registry.get_compatible_portal_blocks(app_name)
                         ]
        blocks.initial = [bl.block_id for bl in block_locations]

    #TODO: use transaction ???
    def _save_locations(self, location_model, location_builder, blocks_partitions, old_locations=()):
        needed = sum(len(block_ids) or 1 for block_ids in blocks_partitions.itervalues()) #at least 1 block per zone (even if it can be fake block)
        lendiff = needed - len(old_locations)

        if lendiff < 0:
            locations_store = old_locations[:needed]
            location_model.objects.filter(pk__in=[loc.id for loc in old_locations[needed:]]).delete()
        else:
            locations_store = list(old_locations)

            if lendiff > 0:
               locations_store.extend(location_builder() for i in xrange(lendiff))

        store_it = iter(locations_store)

        for zone, block_ids in blocks_partitions.iteritems():
            if not block_ids: #No block for this zone -> fake block_id
                block_ids = ('',)

            for order, block_id in enumerate(block_ids, start=1):
                location = store_it.next()
                location.block_id = block_id
                location.order    = order
                location.zone     = zone #NB: BlockPortalLocation has not 'zone' attr, but we do not care ! :)

                location.save()


class _BlockDetailviewLocationsForm(_BlockLocationsForm):
    def _save_detail_locations(self, ct, old_locations=(), top=(), left=(), right=(), bottom=()):
        self._save_locations(BlockDetailviewLocation,
                             lambda: BlockDetailviewLocation(content_type=ct),
                             {BlockDetailviewLocation.TOP:    top,
                              BlockDetailviewLocation.LEFT:   left,
                              BlockDetailviewLocation.RIGHT:  right,
                              BlockDetailviewLocation.BOTTOM: bottom,
                             },
                             old_locations
                            )


class BlockDetailviewLocationsAddForm(_BlockDetailviewLocationsForm):
    ct_id = ChoiceField(label=_(u'Related resource'), choices=(), required=True)

    def __init__(self, *args, **kwargs):
        super(BlockDetailviewLocationsAddForm, self).__init__(*args, **kwargs)

        entity_ct_ids = set(ct.id for ct in creme_entity_content_types())
        used_ct_ids   = set(BlockDetailviewLocation.objects.exclude(content_type=None)
                                                           .distinct()
                                                           .values_list('content_type_id', flat=True)
                           )
        self.fields['ct_id'].choices = [(ct.id, ct) for ct in ContentType.objects.filter(pk__in=entity_ct_ids - used_ct_ids)]

    def save(self, *args, **kwargs):
        self._save_detail_locations(ContentType.objects.get_for_id(self.cleaned_data['ct_id']))


class BlockDetailviewLocationsEditForm(_BlockDetailviewLocationsForm):
    top    = BlockLocationsField(label=_(u'Blocks to display on top'))
    left   = BlockLocationsField(label=_(u'Blocks to display on left side'))
    right  = BlockLocationsField(label=_(u'Blocks to display on right side'))
    bottom = BlockLocationsField(label=_(u'Blocks to display on bottom'))

    _ZONES = (('top',    BlockDetailviewLocation.TOP),
              ('left',   BlockDetailviewLocation.LEFT),
              ('right',  BlockDetailviewLocation.RIGHT),
              ('bottom', BlockDetailviewLocation.BOTTOM)
             )

    def __init__(self, ct, block_locations, *args, **kwargs):
        super(BlockDetailviewLocationsEditForm, self).__init__(*args, **kwargs)
        self.ct = ct
        self.locations = block_locations

        choices = [(MODELBLOCK_ID, ugettext('Information on the entity'))]
        choices.extend((block.id_, block.verbose_name)
                           for block in block_registry.get_compatible_blocks(model=ct.model_class() if ct else None)
                      )

        fields = self.fields

        for fname, zone in self._ZONES:
            block_ids = fields[fname]
            block_ids.initial = [bl.block_id for bl in block_locations if bl.zone == zone]
            block_ids.choices = choices

    def clean(self):
        cdata = self.cleaned_data
        all_block_ids = set()

        for block_id in chain(cdata['top'], cdata['left'], cdata['right'], cdata['bottom']):
            if block_id in all_block_ids:
                raise ValidationError(ugettext(u'The following block should be displayed only once: <%s>') % \
                                        block_registry[block_id].verbose_name
                                     )

            all_block_ids.add(block_id)

        return cdata

    def save(self, *args, **kwargs):
        cdata = self.cleaned_data
        self._save_detail_locations(self.ct, self.locations,
                                    cdata['top'], cdata['left'], cdata['right'], cdata['bottom']
                                   )


class _BlockPortalLocationsForm(_BlockLocationsForm):
    def _save_portal_locations(self, app_name, old_locations=(), block_ids=()):
        self._save_locations(BlockPortalLocation,
                             lambda: BlockPortalLocation(app_name=app_name),
                             {1: block_ids}, #1 is a "nameless" zone
                             old_locations,
                            )


class BlockPortalLocationsAddForm(_BlockPortalLocationsForm):
    app_name = ChoiceField(label=_(u'Related application'), choices=(), required=True)

    def __init__(self, *args, **kwargs):
        super(BlockPortalLocationsAddForm, self).__init__(*args, **kwargs)

        excluded_apps = set(BlockPortalLocation.objects.values_list('app_name', flat=True))
        excluded_apps.add('creme_core')
        excluded_apps.add('creme_config')
        self.fields['app_name'].choices = [(app.name, app.verbose_name)
                                               for app in creme_registry.iter_apps()
                                                   if not app.name in excluded_apps
                                          ]

    def save(self, *args, **kwargs):
        self._save_portal_locations(self.cleaned_data['app_name'])


class BlockPortalLocationsEditForm(_BlockPortalLocationsForm):
    blocks = BlockLocationsField(label=_(u'Blocks to display on the portal'))

    def __init__(self, app_name, block_locations, *args, **kwargs):
        super(BlockPortalLocationsEditForm, self).__init__(*args, **kwargs)
        self.app_name = app_name
        self.locations = block_locations

        self._build_portal_locations_field(app_name=app_name, field_name='blocks', block_locations=block_locations)

    def save(self, *args, **kwargs):
        self._save_portal_locations(self.app_name, self.locations, self.cleaned_data['blocks'])


class BlockMypageLocationsForm(_BlockLocationsForm):
    blocks = BlockLocationsField(label=_(u"""Blocks to display on the "My Page" of the users"""))

    def __init__(self, owner, *args, **kwargs):
        super(BlockMypageLocationsForm, self).__init__(*args, **kwargs)
        self.owner = owner
        self.locations = locations = BlockMypageLocation.objects.filter(user=owner)

        self._build_portal_locations_field(app_name='creme_core', field_name='blocks', block_locations=locations)

    def save(self, *args, **kwargs):
        self._save_locations(BlockMypageLocation,
                             lambda: BlockMypageLocation(user=self.owner),
                             {1: self.cleaned_data['blocks']}, #1 is a "nameless" zone
                             self.locations
                            )


class RelationBlockAddForm(CremeModelForm):
    class Meta:
        model = RelationBlockItem
        exclude = ('block_id',)

    def __init__(self, *args, **kwargs):
        super(RelationBlockAddForm, self).__init__(*args, **kwargs)

        existing_type_ids = RelationBlockItem.objects.values_list('relation_type_id', flat=True)
        self.fields['relation_type'].queryset = RelationType.objects.exclude(pk__in=existing_type_ids)

    def save(self):
        self.instance.block_id = SpecificRelationsBlock.generate_id('creme_config', self.cleaned_data['relation_type'].id)
        super(RelationBlockAddForm, self).save()
