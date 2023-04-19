BRICK_STATE_HIDE_INACTIVE_USERS  = 'creme_config-hide_inactive_users'
BRICK_STATE_HIDE_DELETED_CFIELDS = 'creme_config-hide_deleted_customfields'
BRICK_STATE_SHOW_CFORMS_DETAILS  = 'creme_config-show_customforms_details'

# Transfer ---------------------------------------------------------------------
# 1.0 (Creme 2.2)
# 1.1/1.2 (Creme 2.3) The models for search & custom-forms have changed.
# 1.3 (Creme 2.4) RelationBrickItem.brick_id has been removed (use 'id' now).
# 1.4 (Creme 2.5) InstanceBrickConfigItems are exported and imported if possible.
# 1.5 (Creme 2.6)
#    - Use UUID instead of ID with:
#       - CremePropertyType
#       - RelationBrickItem
#       - InstanceBrickConfigItem
#       - CustomBrickConfigItem
#    - Changes in the data for EntityFilterCondition of Relation
#      (CT uses natural-key, the key "entity_uuid" became just "entity").
#    - Notification channels added
#    - Use UUID instead of name with UserRole.
#    - "extra_data" in EntityFilter/HeaderFilter.
#    - UUID given for CustomFieldEnumValue.
# 1.6 (Creme 2.7)
#    - The cells for RelationBrickItem are now stored as a dictionary.
#    - Fields "role" & "superuser" for ButtonMenuItem.
FILE_VERSION = '1.6'

ID_VERSION = 'version'

ID_ROLES           = 'roles'
ID_MENU            = 'menu'
ID_BUTTONS         = 'buttons'
ID_SEARCH          = 'search'
ID_PROPERTY_TYPES  = 'property_types'
ID_RELATION_TYPES  = 'relation_types'
ID_FIELDS_CONFIG   = 'fields_config'
ID_CUSTOM_FIELDS   = 'custom_fields'
ID_HEADER_FILTERS  = 'header_filters'
ID_ENTITY_FILTERS  = 'entity_filters'
ID_CUSTOM_FORMS    = 'custom_forms'
ID_RTYPE_BRICKS    = 'rtype_bricks'
ID_INSTANCE_BRICKS = 'instance_bricks'
ID_CUSTOM_BRICKS   = 'custom_bricks'
ID_DETAIL_BRICKS   = 'detail_bricks'
ID_HOME_BRICKS     = 'home_bricks'
ID_MYPAGE_BRICKS   = 'mypage_bricks'
ID_CHANNELS        = 'channels'
