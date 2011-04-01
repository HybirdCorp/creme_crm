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

from logging import debug

from django.forms import IntegerField, MultipleChoiceField, ChoiceField
from django.forms.widgets import HiddenInput
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, BlockConfigItem, RelationBlockItem, InstanceBlockConfigItem
from creme_core.forms import CremeForm, CremeModelForm
from creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme_core.gui.block import block_registry, SpecificRelationsBlock
from creme_core.utils import creme_entity_content_types
from creme_core.utils.id_generator import generate_string_id_and_save


class _DetailviewBlocksForm(CremeForm):
    ct_id     = ChoiceField(label=_(u'Related resource'), choices=(), required=True)
    block_ids = MultipleChoiceField(label=_(u'Block to display'), required=False,
                                    choices=(),
                                    widget=OrderedMultipleChoiceWidget)

    _configured_model = None

    def __init__(self, *args, **kwargs):
        super(_DetailviewBlocksForm, self).__init__(*args, **kwargs)

        choices = [(block.id_, block.verbose_name)
                        for block in block_registry.get_compatible_blocks(model=self._configured_model)
                  ]
        choices.extend((rbi.block_id, ugettext(u'Relation block: %s') % rbi.relation_type.predicate)
                            for rbi in RelationBlockItem.objects.all()
                      ) #TODO: filter compatible relation types
        choices.extend((ibi.block_id, ugettext(u"Instance's block: %s") % ibi)
                            for ibi in InstanceBlockConfigItem.objects.all()
                      )

        self.fields['block_ids'].choices = choices

    def save(self):
        cleaned_data  = self.cleaned_data
        block_ids     = cleaned_data['block_ids']
        ct_id         = cleaned_data['ct_id']
        BCI_filter    = BlockConfigItem.objects.filter
        ct            = ContentType.objects.get_for_id(ct_id) if ct_id else None  #can't filter correctly with ct_id = 0/None -> use ContentType object
        blocks_2_save = []

        #No block for this content type -> fake block_id
        if not block_ids:
            #No pk to BCI objects --> can delete() on queryset directly
            BCI_filter(content_type=ct).delete()
            blocks_2_save.append(BlockConfigItem(content_type=ct, block_id='', order=1, on_portal=False))
        else:
            old_ids = set(BCI_filter(content_type=ct).values_list('block_id', flat=True))
            new_ids = set(block_ids)
            blocks_to_del = old_ids - new_ids
            blocks_to_add = new_ids - old_ids

            #No pk to BCI objects --> can delete() on queryset directly
            BCI_filter(content_type=ct, block_id__in=blocks_to_del).delete()

            for i, block_id in enumerate(block_ids):
                order = i + 1 #TODO: use 'start' arg in enumerate with Python 2.6

                if block_id in blocks_to_add:
                    blocks_2_save.append(BlockConfigItem(content_type=ct, block_id=block_id, order=order, on_portal=False))
                else:
                    bci = BlockConfigItem.objects.get(content_type=ct, block_id=block_id) #TODO: queries could be regrouped...

                    if bci.order != order:
                        bci.order = order
                        bci.save()

        generate_string_id_and_save(BlockConfigItem, blocks_2_save, 'creme_config-userbci')


class BlocksEditForm(_DetailviewBlocksForm):
    ct_id = IntegerField(widget=HiddenInput())

    def __init__(self, ct_id, block_config_items, *args, **kwargs):
        #NB: before super's __init__ (used for block_registry.get_compatible_blocks())
        if ct_id:
            self._configured_model = ContentType.objects.get_for_id(ct_id).model_class()

        super(BlocksEditForm, self).__init__(*args, **kwargs)

        fields = self.fields
        fields['ct_id'].initial = ct_id
        fields['block_ids'].initial = [bci.block_id for bci in block_config_items]


class BlocksAddForm(_DetailviewBlocksForm):
    def __init__(self, *args, **kwargs):
        super(BlocksAddForm, self).__init__(*args, **kwargs)

        entity_ct_ids = set(ct.id for ct in creme_entity_content_types())
        used_ct_ids   = set(BlockConfigItem.objects.exclude(content_type=None).distinct().values_list('content_type_id', flat=True))
        self.fields['ct_id'].choices = [(ct.id, ct) for ct in ContentType.objects.filter(pk__in=entity_ct_ids - used_ct_ids)]


class BlocksPortalEditForm(CremeForm):
    ct_id     = IntegerField(widget=HiddenInput())
    block_ids = MultipleChoiceField(label=_(u'Blocks to display on the portal'), required=False,
                                    choices=(), widget=OrderedMultipleChoiceWidget)

    def __init__(self, ct_id, block_config_items, *args, **kwargs):
        super(BlocksPortalEditForm, self).__init__(*args, **kwargs)
        self._block_config_items = block_config_items

        fields = self.fields
        fields['ct_id'].initial = ct_id

        get_block = block_registry.get_block
        choices   = []

        for bci in block_config_items:
            id_   = bci.block_id
            block = get_block(id_)

            if hasattr(block, 'portal_display'):
                choices.append((id_, block.verbose_name))

        block_ids = fields['block_ids']
        block_ids.choices = choices
        block_ids.initial = [bci.block_id for bci in block_config_items if bci.on_portal]

    def save(self):
        on_portal_ids = set(self.cleaned_data['block_ids'])

        for bci in self._block_config_items:
            on_portal = (bci.block_id in on_portal_ids)

            if bci.on_portal != on_portal:
                bci.on_portal = on_portal
                bci.save()


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
