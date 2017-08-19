import warnings

from .bricks import (
    PollFormLinesBrick as PollFormLinesBlock,
    PollReplyLinesBrick as PollReplyLinesBlock,
    PollRepliesBrick as PollRepliesBlock,
    _RelatedRepliesBrick as _RelatedRepliesBlock,
    PersonPollRepliesBrick as PersonPollRepliesBlock,
    PollCampaignRepliesBrick as PollCampaignRepliesBlock,
)

warnings.warn('polls.blocks is deprecated ; use polls.bricks instead.', DeprecationWarning)

pform_lines_block       = PollFormLinesBlock()
preply_lines_block      = PollReplyLinesBlock()
preplies_block          = PollRepliesBlock()
related_preplies_block  = PersonPollRepliesBlock()
pcampaign_replies_block = PollCampaignRepliesBlock()

block_list = (
    pform_lines_block,
    preply_lines_block,
    preplies_block,
    related_preplies_block,
    pcampaign_replies_block,
)
