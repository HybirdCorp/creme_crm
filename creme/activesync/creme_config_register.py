# -*- coding: utf-8 -*-

from . import bricks


blocks_to_register = (('activesync', bricks.MobileSyncConfigBrick),
                     )

userblocks_to_register = (bricks.UserMobileSyncConfigBrick,)
