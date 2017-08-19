import warnings

from .bricks import (
    _RelatedEntitesBrick as _RelatedEntitesBlock,
    MessagingListsBlock as MessagingListsBlock,
    RecipientsBrick as RecipientsBlock,
    ContactsBrick as ContactsBlock,
    MessagesBrick as MessagesBlock,
    SendingsBrick as SendingsBlock,
)

warnings.warn('sms.blocks is deprecated ; use sms.bricks instead.', DeprecationWarning)

messaging_lists_block = MessagingListsBlock()
recipients_block      = RecipientsBlock()
contacts_block        = ContactsBlock()
messages_block        = MessagesBlock()
sendings_block        = SendingsBlock()
