import warnings

from .bricks import (
    UserMobileSyncConfigBrick as UserMobileSyncConfigBlock,
    MobileSyncConfigBrick as MobileSyncConfigBlock,
    UserSynchronizationHistoryBrick as UserSynchronizationHistoryBlock,
)

warnings.warn('activesync.blocks is deprecated ; use activesync.bricks instead.', DeprecationWarning)


user_mobile_sync_config_block      = UserMobileSyncConfigBlock()
mobile_sync_config_block           = MobileSyncConfigBlock()
user_synchronization_history_block = UserSynchronizationHistoryBlock()
