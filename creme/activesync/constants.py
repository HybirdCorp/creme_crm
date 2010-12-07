# -*- coding: utf-8 -*-

################################################################################
# Folder sync / Provisionning

SYNC_NEED_CURRENT_POLICY = 142


################################################################################
#Provisionning
##remote wipe status
SYNC_PROVISION_RWSTATUS_NA      = 0
SYNC_PROVISION_RWSTATUS_OK      = 1
SYNC_PROVISION_RWSTATUS_PENDING = 2
SYNC_PROVISION_RWSTATUS_WIPED   = 3

##Command status
SYNC_PROVISION_STATUS_SUCCESS       = 1 # Success => Apply the policy.
SYNC_PROVISION_STATUS_PROTERROR     = 2 # Protocol error / Policy not defined. => Fix bug in client code./ Stop sending policy information. No policy is implemented.
SYNC_PROVISION_STATUS_SERVERERROR   = 3 # The policy type is unknown / An error occurred on the server => Issue a request by using MS-EAS-Provisioning-WBXML / Retry
SYNC_PROVISION_STATUS_DEVEXTMANAGED = 4 # Used ?
SYNC_PROVISION_STATUS_POLKEYMISM    = 5 # Policy key mismatch => Issue a new Provision request to obtain a valid policy key

################################################################################
#Folder sync
## Server return status
SYNC_FOLDER_STATUS_SUCCESS         = 1  # Success
SYNC_FOLDER_STATUS_SERVER_ERROR    = 6  # An error occurred on the server.
SYNC_FOLDER_STATUS_TIMEOUT         = 8  # The request timed out.
SYNC_FOLDER_STATUS_INVALID_SYNCKEY = 9  # Synchronization key mismatch or invalid synchronization key.
SYNC_FOLDER_STATUS_BAD_REQUEST     = 10 # Incorrectly formatted request
SYNC_FOLDER_STATUS_UNKNOW_ERROR    = 11 # An unknown error occurred.
SYNC_FOLDER_STATUS_ERROR           = 12 # Code unknown. 

## Folder Types
SYNC_FOLDER_TYPE_OTHER            = 1
SYNC_FOLDER_TYPE_INBOX            = 2
SYNC_FOLDER_TYPE_DRAFTS           = 3
SYNC_FOLDER_TYPE_WASTEBASKET      = 4
SYNC_FOLDER_TYPE_SENTMAIL         = 5
SYNC_FOLDER_TYPE_OUTBOX           = 6
SYNC_FOLDER_TYPE_TASK             = 7
SYNC_FOLDER_TYPE_APPOINTMENT      = 8
SYNC_FOLDER_TYPE_CONTACT          = 9
SYNC_FOLDER_TYPE_NOTE             = 10
SYNC_FOLDER_TYPE_JOURNAL          = 11
SYNC_FOLDER_TYPE_USER_MAIL        = 12
SYNC_FOLDER_TYPE_USER_APPOINTMENT = 13
SYNC_FOLDER_TYPE_USER_CONTACT     = 14
SYNC_FOLDER_TYPE_USER_TASK        = 15
SYNC_FOLDER_TYPE_USER_JOURNAL     = 16
SYNC_FOLDER_TYPE_USER_NOTE        = 17
SYNC_FOLDER_TYPE_UNKNOWN          = 18
SYNC_FOLDER_TYPE_RECIPIENT_CACHE  = 19
################################################################################