from django.dispatch import Signal

# Signal sent when a CustomEntityType instance which is disabled; it means the
# type is available again to represent a new kind of entity, so we have to clean
# the DB to get a "clean" type.
# Provided arguments:
# - "sender" is the CustomEntityType instance.
# - "entity_ctype" is the ContentType instance corresponding to
#   <sender.entity_model> (it's a shortcut).
disable_custom_entity_type = Signal()
