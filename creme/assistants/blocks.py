import warnings

from .bricks import (
    _AssistantsBrick as _AssistantsBlock,
    TodosBrick as TodosBlock,
    MemosBrick as MemosBlock,
    AlertsBrick as AlertsBlock,
    ActionsOnTimeBrick as ActionsITBlock,
    ActionsNotOnTimeBrick as ActionsNITBlock,
    UserMessagesBrick as UserMessagesBlock,
)

warnings.warn('assistants.blocks is deprecated ; use assistants.bricks instead.', DeprecationWarning)

alerts_block      = AlertsBlock()
actions_it_block  = ActionsITBlock()
actions_nit_block = ActionsNITBlock()
memos_block       = MemosBlock()
todos_block       = TodosBlock()
messages_block    = UserMessagesBlock()
