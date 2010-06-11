# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeForm
from creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme_core.gui.block import block_registry
from creme_core.models import BlockConfigItem
from creme_core.utils import creme_entity_content_types
from creme_core.utils.id_generator import generate_string_id_and_save


class DetailviewBlocksForm(CremeForm):
    ct_id     = ChoiceField(label=_(u'Resource associée'), choices=(), required=True)
    block_ids = MultipleChoiceField(label=_(u'Blocs à afficher'), required=False,
                                    choices=[(id_, block.verbose_name) for id_, block in block_registry],
                                    widget=OrderedMultipleChoiceWidget)

    def save(self):
        cleaned_data  = self.cleaned_data
        block_ids     = cleaned_data['block_ids']
        ct_id         = cleaned_data['ct_id']
        BCI_filter    = BlockConfigItem.objects.filter
        ct            = ContentType.objects.get(pk=ct_id) if ct_id else None  #can't filter correctly with ct_id = 0/None -> use ContentType object
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
                if block_id in blocks_to_add:
                    blocks_2_save.append(BlockConfigItem(content_type=ct, block_id=block_id, order=i + 1, on_portal=False))
                else:
                    bci = BlockConfigItem.objects.get(content_type=ct, block_id=block_id)

                    if bci.order != i + 1:
                        bci.order = i + 1
                        bci.save()

        generate_string_id_and_save(BlockConfigItem, blocks_2_save, 'creme_config-userbci')


class BlocksEditForm(DetailviewBlocksForm):
    ct_id = IntegerField(widget=HiddenInput())

    def __init__(self, block_config_items, *args, **kwargs):
        super(BlocksEditForm, self).__init__(*args, **kwargs)

        self.fields['block_ids'].initial = [bci.block_id for bci in block_config_items]


class BlocksAddForm(DetailviewBlocksForm):
    def __init__(self, *args, **kwargs):
        super(BlocksAddForm, self).__init__(*args, **kwargs)

        entity_ct_ids = set(ct.id for ct in creme_entity_content_types())
        used_ct_ids   = set(BlockConfigItem.objects.exclude(content_type=None).distinct().values_list('content_type_id', flat=True))
        self.fields['ct_id'].choices = [(ct.id, ct) for ct in ContentType.objects.filter(pk__in=entity_ct_ids - used_ct_ids)]


class BlocksPortalEditForm(CremeForm):
    ct_id     = IntegerField(widget=HiddenInput())
    block_ids = MultipleChoiceField(label=_(u'Blocs à afficher sur le portail'), required=False,
                                    choices=(), widget=OrderedMultipleChoiceWidget)

    def __init__(self, block_config_items, *args, **kwargs):
        super(BlocksPortalEditForm, self).__init__(*args, **kwargs)

        self._block_config_items = block_config_items

        block_ids = self.fields['block_ids']
        get_block = block_registry.get_block
        choices   = []

        for bci in block_config_items:
            id_   = bci.block_id
            block = get_block(id_)
            if hasattr(block, 'portal_display'):
                choices.append((id_, block.verbose_name))

        block_ids.choices = choices
        block_ids.initial = [bci.block_id for bci in block_config_items if bci.on_portal]

    def save(self):
        on_portal_ids = set(self.cleaned_data['block_ids'])

        for bci in self._block_config_items:
            on_portal = (bci.block_id in on_portal_ids)

            if bci.on_portal != on_portal:
                bci.on_portal = on_portal
                bci.save()
