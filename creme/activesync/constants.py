# -*- coding: utf-8 -*-

################################################################################
# Folder sync / Provisionning

SYNC_REMOTE_WIPE_REQUESTED = 140
SYNC_NEED_CURRENT_POLICY   = 142

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
#Conflicts helpers
CONFLICT_CLIENT_MASTER = 0 #Client object replaces server object
CONFLICT_SERVER_MASTER = 1 #Server object replaces client object

################################################################################
#Sync (AirSync)
##Sync statuses
SYNC_AIRSYNC_STATUS_SUCCESS              = 1
SYNC_AIRSYNC_STATUS_INVALID_SYNCKEY      = 3  # Invalid or mismatched synchronization key. OR Synchronization state corrupted on server.
SYNC_AIRSYNC_STATUS_PROTOCOL_ERR         = 4  # There was a semantic error in the synchronization request.
SYNC_AIRSYNC_STATUS_SERVER_ERR           = 5  # Server misconfiguration, temporary system issue, or bad item. This is frequently a transient condition.
SYNC_AIRSYNC_STATUS_CLIENT_SERV_CONV_ERR = 6  # The client has sent a malformed or invalid item.
SYNC_AIRSYNC_STATUS_MATCHING_CONFLICT    = 7  # The client has changed an item for which the conflict policy indicates that the server's changes take precedence.
SYNC_AIRSYNC_STATUS_OBJ_NOT_FOUND        = 8  # The client issued a <Fetch> or <Change> operation that has an ItemID value that is no longer valid on the server (for example, the item was deleted).
SYNC_AIRSYNC_STATUS_CANT_BE_COMPLETED    = 9  # User account could be out of disk space.
SYNC_AIRSYNC_STATUS_FOLDERS_CHANGED      = 12 # The folder hierarchy has changed. Mailbox folders are not synchronized.
SYNC_AIRSYNC_STATUS_SYNC_UNCOMPLETE      = 13 # The Sync command request is not complete. An empty or partial Sync command request is received and the cached set of notify- able collections is missing
SYNC_AIRSYNC_STATUS_INVALID_TIME_OPTIONS = 14 # The Sync request was processed successfully but the <Wait> or <HeartbeatInterval> interval that is specified by the client is outside the range set by the server administrator. If the <HeartbeatInterval> or <Wait> value included in the Sync request is larger than the maximum allowable value, the response contains a <Limit> element that specifies the maximum allowed value. If the <HeartbeatInterval> or <Wait> value included in the Sync request is smaller than the minimum allowable value, the response contains a <Limit> element that specifies the minimum allowed value.
SYNC_AIRSYNC_STATUS_INVALID_SYNC_CMD     = 15 # Too many collections are included in the Sync request.
SYNC_AIRSYNC_STATUS_RETRY                = 16 # Something on the server caused a retriable error

################################################################################