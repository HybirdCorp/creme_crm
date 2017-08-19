import warnings

from django.utils.translation import ugettext_lazy as _

from .bricks import (
    PropertiesBrick as PropertiesBlock,
    RelationsBrick as RelationsBlock,
    HistoryBrick as HistoryBlock,
    TrashBrick as TrashBlock,
)
from .gui.block import SimpleBlock

warnings.warn('creme_core.blocks is deprecated ; use creme_core.bricks instead.', DeprecationWarning)


class CustomFieldsBlock(SimpleBlock):
    id_           = SimpleBlock.generate_id('creme_core', 'customfields')
    verbose_name  = _(u'Custom fields')
    template_name = 'creme_core/templatetags/block_customfields.html'


properties_block   = PropertiesBlock()
relations_block    = RelationsBlock()
customfields_block = CustomFieldsBlock()
history_block      = HistoryBlock()
trash_block        = TrashBlock()
