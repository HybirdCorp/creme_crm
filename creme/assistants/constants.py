# import warnings

UUID_CHANNEL_USERMESSAGES = '395ca7a2-24f3-4348-a0d3-55887e956e61'

UUID_PRIORITY_IMPORTANT      = 'd9dba2d3-18cf-4166-9bd7-6a9fa299e9e1'
UUID_PRIORITY_VERY_IMPORTANT = '16445980-4abe-409c-8c45-f2f4f9bfc945'
UUID_PRIORITY_NOT_IMPORTANT  = '2e4eb53f-e686-42e5-8352-4d3c0ef6c19e'

BRICK_STATE_HIDE_VALIDATED_ALERTS = 'assistants-hide_validated_alerts'
BRICK_STATE_HIDE_VALIDATED_TODOS  = 'assistants-hide_validated_todos'


# def __getattr__(name):
#     if name == 'MIN_HOUR_4_TODO_REMINDER':
#         warnings.warn(
#             '"MIN_HOUR_4_TODO_REMINDER" is deprecated; '
#             'use assistants.setting_keys.todo_reminder_key.id instead.',
#             DeprecationWarning,
#         )
#         return 'assistants-min_hour_4_todo_reminder'
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
