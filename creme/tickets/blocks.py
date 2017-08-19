import warnings

from creme.creme_core.gui.block import SimpleBlock

warnings.warn('tickets.blocks is deprecated ; use tickets.bricks instead.', DeprecationWarning)


class TicketBlock(SimpleBlock):
    template_name = 'tickets/templatetags/block_ticket.html'
