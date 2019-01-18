/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2018  Hybird

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

/* global creme_media_url */
(function($) {
"use strict";

creme.activities = creme.activities || {};

creme.activities.ExportAsICalAction = creme.component.Action.sub({
    _init_: function(list, options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
        this._list = list;
    },

    _run: function(options) {
        options = $.extend({}, this.options(), options || {});

        var self = this;
        var selection = creme.lv_widget.selectedLines(this._list);

        if (selection.length < 1) {
            creme.dialogs.warning(gettext('Please select at least a line in order to export.'))
                         .onClose(function() {
                             self.cancel();
                          })
                         .open();
        } else {
            self.done();
            creme.utils.goTo(options.url, {id: selection});
        }
    }
});

/*
creme.activities.exportAsICal = function(list, url) {
    console.warn('creme.activities.exportAsICal is deprecated. Use ExportAsICalAction instead.');
    var action = new creme.activities.ExportAsICalAction(list, {url: url});
    action.start();
};
*/

$(document).on('listview-setup-actions', '.ui-creme-listview', function(e, actions) {
    actions.register('activities-export-ical', function(url, options, data, e) {
        return new creme.activities.ExportAsICalAction(this._list, {url: url});
    });
});

creme.activities.calendar = {};

creme.activities.calendar.loading = function(state) {
  $('.calendar .loading-indicator').toggleClass('is-loading', state);
};

creme.activities.calendar.addFilteringInput = function(input, filter_callable) {
    input.data('oldVal', input.val());
    input.bind('propertychange input paste', function() {
        var val = input.val();

        if (input.data('oldVal') === val) {
            return;
        }

        input.data('oldVal', val);

        filter_callable(val.toUpperCase());
    });
};

creme.activities.calendar.loadCalendarEventListeners = function(user, creme_calendars_by_user) {
    var floatingEventFilter = function(input_value) {
        $('.floating_event').each(function(index, element) {
            var event = $(element);
            event.toggleClass('hidden', event.text().toUpperCase().indexOf(input_value) === -1);
        });
    };

    var othersCalendarsFilter = function(input_value) {
        for (var calendar_user in creme_calendars_by_user) {
            var calendars = creme_calendars_by_user[calendar_user];
            var username_match = calendar_user.toUpperCase().indexOf(input_value) !== -1;
            var match_count = 0;

            for (var i = 0, size = calendars.length; i < size; ++i) {
                var calendar = calendars[i];
                var calendar_name = calendar.name.toUpperCase();
                var match = (calendar_name.indexOf(input_value) !== -1) || username_match;

                if (match) {
                    match_count++;
                }

                $('.calendar_label_container[data-calendar=' + calendar.id + ']').toggleClass('hidden', !match);
            }

            $('.calendar_label_owner[data-user="' + calendar_user + '"]').toggleClass('hidden', match_count === 0);
        }
    };

    $('input[type="checkbox"]').change(function(event) {
        var widget = $('.calendar');
        var chk_box = $(this);
        var calendar_id = chk_box.val();

        if (chk_box.is(':checked')) {
            // NB: creating new event source is a bad idea, because these new sources
            // have to be removed, in order to avoid :
            //    - duplicated Activities when we go to a page we a newly checked calendar.
            //    - accumulating event sources.
            // so we just force a new fetch.  TODO: find a way to only retrieve new events + cache
            widget.fullCalendar('refetchEvents');
        } else {
            widget.fullCalendar('removeEvents', function(event) {
                return calendar_id === event.calendar;
            });
        }
    });

    $('.floating_event_filter input').each(function() {
        creme.activities.calendar.addFilteringInput($(this), floatingEventFilter);
    });

    $('.calendar_filter input').each(function() {
        creme.activities.calendar.addFilteringInput($(this), othersCalendarsFilter);
    });

    $('.floating_event').each(function () {
        var element = $(this);
        var calendar = element.attr('data-calendar');
        var type = element.attr('data-type');
        var color = element.attr('data-color');
        var event = {
            id: element.attr('data-id'),
            title: $.trim(element.text()),
            type: type,
            user: user,
            calendar: calendar,
            className: 'event event-' + calendar,
            url: element.attr('data-popup_url'),
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

};

creme.activities.calendar.chooseForeground = function(target, bgColor) {
    var rgb = creme.color.HEXtoRGB(bgColor);
    target.css('color', creme.color.maxContrastingColor(rgb.r, rgb.g, rgb.b));
};

creme.activities.calendar.updater = function(update_url, event, dayDelta, minuteDelta, allDay, revertFunc, jsEvent, ui, view) {
    creme.ajax.query(update_url, {action: 'POST'},
                     {id: event.id,
                      start: event.start.getTime(),
                      end: event.end.getTime(),
                      allDay: allDay
                     })
              .onFail(function(event, data, error) {
                  if (error.status === 403) {
                      creme.dialogs.warning(gettext("You do not have permission, the change will not be saved.")).open();
                  } else if (error.status === 409) {
                      creme.dialogs.warning(unescape(data)).open();
                  } else if (error.status >= 300 || error.status === 0) {
                      creme.dialogs.warning(gettext("Error, please reload the page.")).open();
                  }
                  revertFunc();
               })
              .onStart(function() {
                  creme.activities.calendar.loading(true);
               })
              .onComplete(function() {
                  creme.activities.calendar.loading(false);
                  creme.activities.calendar.resizeSidebar();
               }).start();
};

creme.activities.calendar.resizeSidebar = function() {
    var calendar = $('.calendar');
    var calendarHeight = calendar.height();

    var sidebar = $('.menu_calendar');
    var sidebarMargin = parseInt(sidebar.css('margin-top'));

    sidebar.css('height', (calendarHeight - sidebarMargin) + 'px');
};

creme.activities.calendar.fullCalendar = function(events_url, creation_url, update_url) {
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
        defaultView: 'month', // 'agendaWeek',
        allDaySlot: true,
        allDayText: gettext("All day"),
        axisFormat: "H'h'mm",
        slotMinutes: 15,
        defaultEventMinutes: 60,
        firstHour: new Date().toString("HH"),
        minTime: 0,
        maxTime: 24,
        timeFormat: "H'h'mm", // TODO: use l110n time format
        columnFormat: {
            "month": "dddd",
            "agendaWeek": "dddd d MMMM",
            "agendaDay": "dddd d MMMM"
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
            var chk_boxes_q = 'input[type="checkbox"][name="selected_calendars"]';

            var cal_ids = $(chk_boxes_q + ':checked').map(function() {
                return $(this).val();
            });

            $(chk_boxes_q).enable(false);

            $.ajax({
                url: events_url,
                dataType: 'json',
                data: {
                    calendar_id: cal_ids.get(),
                    start: Math.round(start.getTime() / 1000),
                    end: Math.round(end.getTime() / 1000)
                },
                success: function(events) {
                    callback(events);
                    creme.activities.calendar.resizeSidebar();
                    $(chk_boxes_q).enable(true);
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

            var cancel_drop = function() {
                elem.show();
                $('.calendar').fullCalendar('removeEvents', event.id);
            };

            creme.activities.calendar.updater(update_url, event, null, null, allDay, cancel_drop);
        },
        loading: function(isLoading, view) {
            creme.activities.calendar.loading(isLoading);
        },
        dayClick: function(date, allDay, jsEvent, view) {
            var data = {
                'year':   date.getFullYear(),
                'month':  date.getMonth() + 1,
                'day':    date.getDate(),
                'hour':   date.getHours(),
                'minute': date.getMinutes()
            };

            creme.dialogs.form(creation_url, {}, data)
                         .onFormSuccess(function() {
                             $('.calendar').fullCalendar('refetchEvents');
                          })
                         .open({width: '80%'});
        },
        eventRender: function(event, element, view) {
            if (event.type) {
                var eventType = $('<span>').addClass('fc-event-type').text(event.type);
                var eventTime = element.find('.fc-event-time');

                if (eventTime.length > 0) {
                    if (view.name === 'month') {
                        eventType.text(' – ' + eventType.text());
                    }

                    eventType.insertAfter(eventTime);
                } else {
                    element.find('.fc-event-inner').prepend(eventType);
                }
            }

            element.css('background-color', event.calendar_color);
            creme.activities.calendar.chooseForeground(element, event.calendar_color);
        },
        eventDragStart: function(calEvent, domEvent, ui, view) {},
        eventDrop: function(event, dayDelta, minuteDelta, allDay, revertFunc, jsEvent, ui, view) {
            creme.activities.calendar.updater(update_url, event, dayDelta, minuteDelta, allDay, revertFunc, jsEvent, ui, view);
        },
        eventClick: function(event) {
            creme.dialogs.url(event.url).open({width: '80%'});
            return false;
        },
        eventResize: function(event, dayDelta, minuteDelta, revertFunc, jsEvent, ui, view) {
            creme.activities.calendar.updater(update_url, event, dayDelta, minuteDelta, null, revertFunc, jsEvent, ui, view);
        }
    });

    // insert 'loading...' indicator
    var loadingImage = $('<img>').attr('src', creme_media_url('images/wait.gif'));
    $('<div class="loading-indicator">').append(loadingImage, '<div class="loading-label">' + gettext("Loading...") + '</div>')
                                        .insertBefore('.fc-content');
};

}(jQuery));
