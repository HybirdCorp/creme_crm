/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2014  Hybird

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*******************************************************************************/

creme.activities = {};

creme.activities.exportAsICal = function(list) {
    var selection = $(list).list_view('getSelectedEntities').trim();

    if (!selection) {
        creme.dialogs.warning(gettext('Please select at least a line in order to export.')).open();
        return false;
    }

    document.location.href = '/activities/activities/%s/ical'.format(selection);
}

// creme.activities.ajax = {};

creme.activities.calendar = {};

// creme.activities.calendar.loading = function(bool) {
//     if (bool) {
//         $('#loading_col').remove();
//     } else {
//         $('.fc-header-left').find('tr').append($('<td id="loading_col"><img src="' + creme_media_url("images/wait.gif") + '"/>' + gettext("Loading...") + '</td>'));
//     }
// }

/*
creme.activities.calendar.loading = function(bool) {
    if (bool) {
        $('#loading_col').remove();
    } else {
      var loadingImage = $('<img>').attr ('src', creme_media_url ('images/wait.gif'));
      $('<td id="loading_col">').append (loadingImage, '<span>' + gettext ("Loading...") + '</span>')
                                .appendTo ('.fc-header-left tr');
    }
}
*/

creme.activities.calendar.loading = function(loading_done) {
  $('.calendar .loading-indicator').css('visibility', loading_done ? 'hidden' : 'visible');
}

creme.activities.calendar.filterEvents = function(widget, calendar, events) {
    widget.fullCalendar('removeEvents', function(event) {return calendar == event.calendar;});

    if (events) {
        $.each(events, function(index, event) {
            if (calendar == event.calendar) {
                widget.fullCalendar('renderEvent', event);
            }
        })
    }

    creme.activities.calendar.resizeSidebar();
}

creme.activities.calendar.addFilteringInput = function(input, filter_callable) {
    input.data('oldVal', input.val());
    input.bind('propertychange input paste', function() {
        var val = input.val();

        if (input.data('oldVal') == val) {
            return;
        }

        input.data ('oldVal', val);

        filter_callable(val.toUpperCase());
    });
}

creme.activities.calendar.loadCalendarEventListeners = function(user, creme_calendars_by_user) {
    creme.activities.calendar.floatingEventFilter = function(input_value) {
        $('.floating_event').each(function(index, element) {
            var event = $(element);
            event.toggleClass('hidden', event.text().toUpperCase().indexOf (input_value) == -1);
        });

    }

    creme.activities.calendar.othersCalendarsFilter = function(input_value){
        for (var calendar_user in creme_calendars_by_user) {
            var calendars = creme_calendars_by_user [calendar_user];
            var username_match = calendar_user.toUpperCase().indexOf(input_value) != -1;
            var match_count = 0;

            for (var i = 0, size = calendars.length; i < size; ++i) {
                var calendar = calendars[i];
                var calendar_name = calendar.name.toUpperCase();
                var match = (calendar_name.indexOf(input_value) != -1) || username_match;

                if (match) {match_count++;}
                $('.calendar_label_container[data-calendar=' + calendar.id + ']').toggleClass('hidden', !match);
            }

            $('.calendar_label_owner[data-user="' + calendar_user + '"]').toggleClass ('hidden', match_count == 0);
        }
    }

    $('input[type="checkbox"]').change(function(event) {
        var widget = $('.calendar');
        var chk_box = $(this);
        var calendar_id = chk_box.val();
        var events_url = '/activities/calendar/users_activities/';
        var calendar_view = widget.fullCalendar('getView');

        if (chk_box.is(':checked')) {
            $.ajax({
                type: "GET",
                dataType:'json',
                data: {
                    start: Math.round(calendar_view.visStart.getTime() / 1000),
                    end: Math.round(calendar_view.visEnd.getTime() / 1000)
                },
                url: events_url + calendar_id,
                error: function(request, textStatus, errorThrown) {
                    chk_box.attr('checked', false);
                },
                beforeSend: function(request) {
                    creme.activities.calendar.loading(false);
                },
                complete: function(request, txtStatus) {
                    creme.activities.calendar.loading(true);
                },
                success: function(returnedData, status) {
                    creme.activities.calendar.filterEvents(widget, calendar_id, returnedData);
                }
            });
        } else {
            creme.activities.calendar.filterEvents(widget, calendar_id);
        }
    });

    $('.floating_event_filter input').each(function() {
        creme.activities.calendar.addFilteringInput($(this), creme.activities.calendar.floatingEventFilter);
    });

    $('.calendar_filter input').each(function() {
        creme.activities.calendar.addFilteringInput($(this), creme.activities.calendar.othersCalendarsFilter);
    });

    $('.floating_event').each(function () {
        var element = $(this);
        var calendar = element.attr('data-calendar');
        var type = element.attr('data-type');
        var event_id = element.attr('data-id');
        var color = element.attr('data-color');
        var event = {
            id: event_id,
            title: $.trim(element.text()),
            type: type,
            user: user,
            calendar: calendar,
            className: 'event event-' + calendar,
            url: "/activities/activity/%s/popup".replace("%s", event_id),
            calendar_color: color
        };

        element.data('eventObject', event);
        element.draggable({
            zIndex: 999,
            revert: true,
            revertDuration: 0,
            appendTo: 'body',
            containment: 'window',
            scroll: false,
            helper: 'clone'
        });
    });

}

creme.activities.calendar.chooseForeground = function(target, bgColor) {
    var rgb = creme.color.HEXtoRGB(bgColor);
    target.css('color', creme.color.maxContrastingColor(rgb.r, rgb.g, rgb.b));
}

creme.activities.calendar.updater = function(event, dayDelta, minuteDelta, allDay, revertFunc, jsEvent, ui, view) {
    $.ajax({
        type: "POST",
        url: "/activities/calendar/activity/update",
        data: {
            id: event.id,
            start: event.start.getTime(),
            end: event.end.getTime(),
            allDay: allDay
        },
        error: function(request, textStatus, errorThrown) {
            if (request.status == 403) {
                creme.dialogs.warning(gettext("You do not have permission, the change will not be saved."));
            } else if (request.status == 409) {
                creme.dialogs.warning(unescape(request.responseText));
            } else if (request.status >= 300 || request.status == 0) {
                creme.dialogs.warning(gettext("Error, please reload the page."));
            }
            revertFunc();
        },
        beforeSend: function(request) {
            creme.activities.calendar.loading(false);
        },
        complete: function(request, txtStatus) {
            creme.activities.calendar.loading(true);
            creme.activities.calendar.resizeSidebar();
        },
    });
}

creme.activities.calendar.resizeSidebar = function() {
    var calendar = $('.calendar');
    var calendarHeight = calendar.height();

    var sidebar = $('.menu_calendar');
    var sidebarMargin = parseInt(sidebar.css('margin-top'));

    sidebar.css('height', (calendarHeight - sidebarMargin) + 'px');
}

creme.activities.calendar.positionNavigationWidget = function() {
    var titleWidth = $('.fc-header-left').width();
    $('.fc-header-center table').css ('left', '-' + titleWidth + 'px');
}

creme.activities.calendar.fullCalendar = function(events_url) {
    $('.calendar').fullCalendar({
        weekends: true,
        header: {
            left:   'title',
            center: 'today, prev,next',
            right:  'agendaWeek,month'
        },
        theme: false,
        firstDay: 1,
        weekMode: 'fixed',
        aspectRatio: 2,
        defaultView: 'month',//'agendaWeek',
        allDaySlot: true,
        allDayText: gettext("All day"),
        axisFormat: "H'h'mm",
        slotMinutes: 15,
        defaultEventMinutes: 60,
        firstHour: new Date().toString("HH"),
        minTime: 0,
        maxTime: 24,
        timeFormat: "H'h'mm", //TODO: use l110n time format
        columnFormat: {
            "month":"dddd",
            "agendaWeek":"dddd d MMMM",
            "agendaDay":"dddd d MMMM"
        },
        titleFormat: {
            month: 'MMMM yyyy',
            week: "d[ yyyy]{ '&#8212;' d MMMM yyyy}",
            day: 'dddd d MMMM yyyy'
        },
        buttonText: {
            prev:     '&nbsp;&#9668;&nbsp;',  // left triangle
            next:     '&nbsp;&#9658;&nbsp;',  // right triangle
            prevYear: '&nbsp;&lt;&lt;&nbsp;', // <<
            nextYear: '&nbsp;&gt;&gt;&nbsp;', // >>
            today:    gettext("Today"),
            month:    gettext("Month"),
            week:     gettext("Week"),
            day:      gettext("Day")
        },
        monthNames: [
            gettext("January"),
            gettext("February"),
            gettext("March"),
            gettext("April"),
            gettext("May"),
            gettext("June"),
            gettext("July"),
            gettext("August"),
            gettext("September"),
            gettext("October"),
            gettext("November"),
            gettext("December")
        ],
        dayNames: [
            gettext("Sunday"),
            gettext("Monday"),
            gettext("Tuesday"),
            gettext("Wesnesday"),
            gettext("Thursday"),
            gettext("Friday"),
            gettext("Saturday")
        ],
        events: function(start, end, callback) {
            var cal_ids = $('input[type="checkbox"][name="selected_calendars"]:checked').map(function() {
                return $(this).val();
            });

            $.ajax({
                url: events_url + cal_ids.get().join(','),
                dataType: 'json',
                data: {
                    start: Math.round(start.getTime() / 1000),
                    end: Math.round(end.getTime() / 1000)
                },
                success: function(events) {
                    callback(events);
                    creme.activities.calendar.resizeSidebar();
                    creme.activities.calendar.positionNavigationWidget();
                }
            });
        },
        editable: true,
        droppable: true,
        drop: function(date, allDay) {
            var elem = $(this);
            var eventPrototype = elem.data('eventObject');
            var event = $.extend({}, eventPrototype);

            event.start = date;
            event.allDay = allDay;

            var end_date = new Date(date);
            if (allDay) {
                end_date.setHours(23, 59, 59);
            } else {
                end_date.setHours(date.getHours() + 1);
            }

            event.end = end_date;

            $('.calendar').fullCalendar('renderEvent', event);
            elem.hide();

            cancel_drop = function() {
                elem.show();
                $('.calendar').fullCalendar('removeEvents', event.id);
            }

            creme.activities.calendar.updater(event, null, null, allDay, cancel_drop);
        },
        loading: function(isLoading, view) {
            creme.activities.calendar.loading(!isLoading);
        },
        dayClick: function(date, allDay, jsEvent, view) {
            var data = {
                'year':   date.getFullYear(),
                'month':  date.getMonth() + 1,
                'day':    date.getDate(),
                'hour':   date.getHours(),
                'minute': date.getMinutes()
            };

            creme.dialogs.form('/activities/activity/add_popup', {reloadOnSuccess: true}, data).open({width: '80%'});
        },
        eventRender: function(event, element, view) {
            var container = element.find('a');

            if (event.type) {
                var eventType = $('<span>').addClass('fc-event-type').text (event.type);
                var eventTime = element.find ('.fc-event-time');

                if (eventTime.length != 0) {
                    if (view.name == 'month') {
                        eventType.text (' – ' + eventType.text());
                    }

                    eventType.insertAfter(eventTime);
                } else {
                    container.prepend(eventType);
                }
            }

            container.css('background-color', event.calendar_color);
            creme.activities.calendar.chooseForeground(container, event.calendar_color);
        },
        eventDragStart: function(calEvent, domEvent, ui, view) {},
        eventDrop: function(event, dayDelta, minuteDelta, allDay, revertFunc, jsEvent, ui, view) {
            creme.activities.calendar.updater(event, dayDelta, minuteDelta, allDay, revertFunc, jsEvent, ui, view);
        },
        eventClick: function(event) {
            creme.dialogs.url(event.url).open({width:'80%'});

            return false;
        },
        eventResize: function(event, dayDelta, minuteDelta, revertFunc, jsEvent, ui, view) {
            creme.activities.calendar.updater(event, dayDelta, minuteDelta, null, revertFunc, jsEvent, ui, view);
        }
    });

    // insert 'loading...' indicator
    var loadingImage = $('<img>').attr ('src', creme_media_url('images/wait.gif'));
    $('<div class="loading-indicator">').append(loadingImage, '<div class="loading-label">' + gettext("Loading...") + '</div>')
                                        .insertBefore('.fc-content');
}
