from django.urls import re_path

from . import views

urlpatterns = [
    re_path(
        r'^calendar/user[/]?$',
        views.ConfiguredCalendarView.as_view(),
        name='activities__calendar',
    ),

    re_path(
        r'^calendar_config/settings/edit/(?P<item_id>\d+)[/]?$',
        views.CalendarConfigItemEdition.as_view(),
        name='calendar_config__edit_calendar_settings',
    ),
    re_path(
        r'^calendar_config/settings/add[/]?$',
        views.CalendarConfigItemCreation.as_view(),
        name='calendar_config__add_calendar_settings',
    ),
    re_path(
        r'^calendar_config/settings/delete[/]?$',
        views.CalendarConfigItemDeletion.as_view(),
        name='calendar_config__delete_calendar_settings',
    )
]
