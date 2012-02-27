# -*- coding: utf-8 -*-

from activesync.blocks import mobile_sync_config_block, user_mobile_sync_config_block

to_register = ()

blocks_to_register = (('activesync', mobile_sync_config_block),
                     )

userblocks_to_register = (user_mobile_sync_config_block,)
