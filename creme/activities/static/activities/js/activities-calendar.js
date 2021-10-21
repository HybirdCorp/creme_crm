/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2021  Hybird

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

(function($) {
"use strict";

var FULLCALENDAR_SETTINGS = {
    header: {
        left:   'title',
        center: 'today, prev,next',
        right:  'agendaWeek,month,day'
    },

    /* views settings */
    defaultView: 'month', // 'agendaWeek'
    views: {
        month: {
            titleFormat: 'MMMM YYYY',
            columnFormat: 'dddd'
        },
        week: {
            titleFormat: 'D MMMM YYYY',
            titleRangeSeparator: ' − ',
            columnFormat: 'dddd D MMMM',
            selectHelper: true
        },
        day: {
            titleFormat: 'dddd d MMMM YYYY',
            columnFormat: 'dddd d MMMM'
        }
    },

    /* day settings */
    timezone: 'local',
    minTime: '00:00:00',
    maxTime: '24:00:00',
    scrollTime: '06:00:00',
    timeFormat: "H[h]mm", // TODO: use l110n time format
    defaultTimedEventDuration: '01:00:00',

    /* slots */
    allDaySlot: true,
    allDayText: gettext("All day"),
    slotLabelFormat: "H[h]mm",
    slotLabelInterval: '01:00:00',
    slotDuration: '00:15:00',

    /* week settings */
    weekends: true,
    firstDay: 1,    // monday
    fixedWeekCount: true,

    /* ui settings */
    themeSystem: 'standard',
    aspectRatio: 2,

    editable: true,
    selectable: true,

    droppable: true,
    dropAccept: '.floating-event',

    buttonText: {
        prev:     '◄',  // left triangle
        next:     '►',  // right triangle
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
        gettext("Wednesday"),
        gettext("Thursday"),
        gettext("Friday"),
        gettext("Saturday")
    ],

    /* ui plugins */
    nowIndicator: true
};

var CalendarEventRange = creme.component.Component.sub({
    _init_: function(event) {
        event = $.extend({
            start: moment(),
            duration: '01:00:00',
            allDay: false
        }, event || {});

        $.extend(this, event);

        if (Object.isNone(this.end)) {
            this.end = this.start.clone();

            if (this.allDay) {
                this.end.set({hours: 0, minutes: 0, seconds: 0});
            } else {
                this.end.add(moment.duration(this.duration));
            }
        } else if (this.allDay) {
            this.end.subtract(1, 'days');
        }
    },

    toString: function() {
        return '${start} − ${end}${allday}'.template({
            start: this.start,
            end: this.end,
            allday: this.allDay ? '[ALLDAY]' : ''
        });
    }
});

creme.activities = creme.activities || {};

creme.activities.CalendarController = creme.component.Component.sub({
    _init_: function(options) {
        options = $.extend({
            debounceDelay: 200
        }, options || {});

        this.debounceDelay(options.debounceDelay);
        this.owner(options.owner || '');
        this.eventSelectUrl(options.eventSelectUrl || '');
        this.eventUpdateUrl(options.eventUpdateUrl || '');
        this.eventCreateUrl(options.eventCreateUrl || '');
        this.eventFetchUrl(options.eventFetchUrl || '');
    },

    owner: function(owner) {
        return Object.property(this, '_owner', owner);
    },

    eventSelectUrl: function(url) {
        return Object.property(this, '_eventSelectUrl', url);
    },

    eventUpdateUrl: function(url) {
        return Object.property(this, '_eventUpdateUrl', url);
    },

    eventCreateUrl: function(url) {
        return Object.property(this, '_eventCreateUrl', url);
    },

    eventFetchUrl: function(url) {
        return Object.property(this, '_eventFetchUrl', url);
    },

    debounceDelay: function(delay) {
        return Object.property(this, '_debounceDelay', delay);
    },

    calendar: function() {
        return this._element.find('.calendar');
    },

    fullCalendar: function() {
        if (this.isBound()) {
            if (arguments.length > 0) {
                this.calendar().fullCalendar.apply(this.calendar(), Array.copy(arguments));
                return this;
            } else {
                return this.calendar().fullCalendar('getCalendar');
            }
        } else {
            return arguments.length > 0 ? this : undefined;
        }
    },

    calendarView: function() {
        if (this.isBound()) {
            return this.calendar().fullCalendar('getCalendar').view;
        }
    },

    _queryErrorMessage: function(data, error) {
        if (error.status === 403) {
            return gettext("You do not have permission, the change will not be saved.");
        } else if (error.status === 409) {
            return unescape(data);
        } else {
            return gettext("Error, please reload the page.");
        }
    },

    _query: function(options, data) {
        var self = this;

        var query = creme.ajax.query(options.url, options, data)
                              .onStart(function() { self.isLoading(true); })
                              .onComplete(function() {
                                  self.isLoading(false);
                                  self._resizeSidebar();
                              });

        if (options.warnOnFail) {
            return new creme.component.Action(function() {
                var action = this;

                query.onFail(function(event, data, error) {
                          var message = self._queryErrorMessage(data, error);
                          var dialog = creme.dialogs.warning(message);

                          dialog.onClose(function() {
                                     action.fail(data, error);
                                 })
                                .open();
                      })
                     .onDone(function(event, data) {
                         action.done(data);
                      })
                     .start();
            });
        } else {
            return query;
        }
    },

    isLoading: function(state) {
        if (!this.isBound()) {
            return false;
        }

        var indicator = this._element.find('.calendar .loading-indicator');

        if (state === undefined) {
            return indicator.is('.is-loading');
        }

        indicator.toggleClass('is-loading', state);
        return this;
    },

    isBound: function() {
        return Object.isNone(this._element) === false;
    },

    bind: function(element) {
        if (this.isBound()) {
            throw new Error('CalendarController is already bound');
        }

        this._element = element;
        this._bindFilterInputs(element, '.floating-event-filter input', this._filterCalendarEvents.bind(this));
        this._bindFilterInputs(element, '.calendar-menu-filter input', this._filterCalendars.bind(this));
        this._bindToggleCalendar(element);

        this._setupCalendarUi(element);
        this._setupCalendarExternalEvents(element);

        // move 'loading...' indicator
        element.find('.loading-indicator').insertBefore(element.find('.fc-view-container'));

        return this;
    },

    element: function() {
        return this._element;
    },

    visibleCalendarIds: function(ids) {
        if (this.isBound()) {
            var checkboxes = this._element.find('input[type="checkbox"][name="calendar_id"]:checked');

            if (ids === undefined) {
                return checkboxes.map(function() {
                    return $(this).val();
                }).get();
            }

            checkboxes.each(function() {
                $(this).prop('checked', ids.indexOf($(this).val()) !== -1);
            });

            this._element.find('.calendar').fullCalendar('refetchEvents');
            return this;
        } else {
            return ids === undefined ? [] : this;
        }
    },

    _addAllCalendarEvents: function(id) {
        // NB: creating new event source is a bad idea, because these new sources
        // have to be removed, in order to avoid :
        //    - duplicated Activities when we go to a page we a newly checked calendar.
        //    - accumulating event sources.
        // so we just force a new fetch.  TODO: find a way to only retrieve new events + cache
        this._element.find('.calendar').fullCalendar('refetchEvents');
    },

    _removeAllCalendarEvents: function(id) {
        var calendar = this._element.find('.calendar');
        var query = this._query({
                            url: this.eventSelectUrl(),
                            action: 'POST'
                        }, {
                            remove: id
                        });

        query.onDone(function() {
            calendar.fullCalendar('removeEvents', function(event) {
                return String(id) === String(event.calendar);
            });
        }).start();

        return this;
    },

    _debounce: function(handler) {
        var delay = this.debounceDelay();

        if (delay > 0) {
            return creme.utils.debounce(handler, delay);
        } else {
            return handler;
        }
    },

    _resizeSidebar: function() {
        var calendar = this._element.find('.calendar');
        var calendarHeight = calendar.height();

        var sidebar = this._element.find('.calendar-menu');
        var sidebarMargin = parseInt(sidebar.css('margin-top'));

        sidebar.css('height', (calendarHeight - sidebarMargin) + 'px');
    },

    _filterCalendars: function(element, search) {
        element.find('.other-calendars .calendar-menu-usergroup').each(function() {
            var username = $(this).attr('data-user');
            var calendars = $(this).find('.calendar-menu-item');
            var title = $(this).find('.calendar-menu-usergroup-label');

            var isOwnerMatches = (
               username.toUpperCase().indexOf(search) !== -1 ||
               title.text().toUpperCase().indexOf(search) !== -1
            );

            if (isOwnerMatches) {
                title.removeClass('hidden');
                calendars.removeClass('hidden');
            } else {
                var anyCalendarMatch = false;

                calendars.each(function() {
                    var match = $(this).find('label').text().toUpperCase().indexOf(search) !== -1;
                    $(this).toggleClass('hidden', !match);
                    anyCalendarMatch |= match;
                });

                title.toggleClass('hidden', !anyCalendarMatch);
            }
        });
    },

    _filterCalendarEvents: function(element, search) {
        element.find('.floating-event').each(function() {
            $(this).toggleClass('hidden', $(this).text().toUpperCase().indexOf(search) === -1);
        });
    },

    _bindFilterInputs: function(element, query, callback) {
        element.on('propertychange keyup input paste', query, this._debounce(function(e) {
            callback(element, $(this).val().toUpperCase());
        }));
    },

    _bindToggleCalendar: function(element) {
        var self = this;

        element.on('change', '.calendar-menu-item input[type="checkbox"]', function(event) {
            if ($(this).prop('checked')) {
                self._addAllCalendarEvents($(this).val());
            } else {
                self._removeAllCalendarEvents($(this).val());
            }
        });
    },

    _setupCalendarExternalEvents: function(element) {
        element.find('.floating-event').draggable({
            zIndex: 999,
            revert: true,
            revertDuration: 0,
            appendTo: 'body',
            containment: 'window',
            scroll: false,
            helper: 'clone'
        });
    },

    _getFloatingEventMeta: function(item) {
        return {
            id: item.attr('data-id'),
            title: (item.text() || '').trim(),
            type: item.attr('data-type'),
            user: this.owner(),
            calendar: item.attr('data-calendar'),
            className: [],
            url: item.attr('data-popup_url'),
            editable: true,
            color: item.attr('data-color')
        };
    },

    _onCalendarExternalEventUpdate: function(calendar, item, event) {
        var newEvent = $.extend({}, this._getFloatingEventMeta(item), {
            start: event.start,
            end: event.end,
            allDay: event.allDay
        });

        this._query({
                 url: this.eventUpdateUrl(),
                 action: 'POST',
                 warnOnFail: true
             }, {
                 id: newEvent.id,
                 start: newEvent.start.valueOf(),  // timestamp in MILLISECOND
                 end: newEvent.end.valueOf(),      // timestamp in MILLISECOND
                 allDay: newEvent.allDay
             })
            .onDone(function() {
                 calendar.fullCalendar('renderEvent', newEvent);

//                 var group = item.parents('.menu-group:first');
                 var group = item.parents('.menu-group').first();
                 item.detach();

                 group.toggleClass('is-empty-group', group.find('.floating-event').length === 0);
             })
            .start();
    },

    _onCalendarEventUpdate: function(calendar, item, event, revertCallback) {
        this._query({
                 url: this.eventUpdateUrl(),
                 action: 'POST',
                 warnOnFail: true
             }, {
                 id: event.id,
                 start: event.start.valueOf(),  // timestamp in MILLISECOND
                 end: event.end.valueOf(),      // timestamp in MILLISECOND
                 allDay: event.allDay
             })
            .onFail(function(event, err) {
                revertCallback();
             })
            .start();
    },

    _onCalendarEventFetch: function(calendar, range, callback) {
        this._query({
                url: this.eventFetchUrl(),
                backend: {dataType: 'json'}
             }, {
                calendar_id: this.visibleCalendarIds(),
                start: range.start.unix(),  // timestamp in SECOND
                end: range.end.unix()       // timestamp in SECOND
             })
            .onDone(function(event, data) {
                callback(data);
             })
            .start();
    },

    _onCalendarEventCreate: function(calendar, event) {
        var data = {
            start: event.start.format(),
            end: event.end.format(),
            allDay: event.allDay ? 1 : 0
        };

        creme.dialogs.form(this.eventCreateUrl(), {}, data)
                     .onFormSuccess(function() {
                         calendar.fullCalendar('refetchEvents');
                      })
                     .open({width: '80%'});
    },

    _onCalendarEventShow: function(calendar, event) {
        creme.dialogs.url(event.url).open({width: '80%'});
    },

    _renderCalendarEvent: function(calendar, event, item, view) {
        if (event.type) {
            var eventTypeLabel = $('<span class="fc-type">${type}</span>'.template(event));
            eventTypeLabel.insertAfter(item.find('.fc-content .fc-title'));
        }

        if (view.name === 'agendaWeek' && !Object.isNone(event.end)) {
            var isSmall = (event.end.diff(event.start) < moment.duration('00:31:00').asMilliseconds());
            item.toggleClass('fc-small', isSmall);
        }

        var foreground = new RGBColor(event.color).foreground().toString();

        item.css('background-color', event.color);
        item.css('color', foreground);
    },

    _renderCalendarSelection: function(calendar, event, item, view) {
        item.html('${start} − ${end}'.template({
            start: event.start.format(view.options.timeFormat),
            end: event.end.format(view.options.timeFormat)
        }));
        item.addClass('fc-event-highlight');
    },

    _renderCalendarView: function(calendar, view) {
        if (view.name === 'agendaWeek') {
            calendar.find('.fc-header-toolbar .fc-left h2')
                    .append($(
                        '<span class="fc-header-week">${label} ${num}</span>'.template({
                            label: gettext("Week"),
                            num: view.start.format('W')
                        })
                    ));
        }
    },

    /* TODO : handle overlap validation for events from same calendar ?
    _checkCalendarEventOverlap: function(still, moving) {
        return true;
    },
    */

    _setupCalendarUi: function(element) {
        var self = this;
        var calendar = element.find('.calendar');

        calendar.fullCalendar($.extend({}, FULLCALENDAR_SETTINGS, {
            events: function(start, end, timezone, callback) {
                self._onCalendarEventFetch(calendar, {start: start, end: end}, callback);
            },
            loading: function(isLoading, view) {
                self.isLoading(isLoading);
            },
            select: function(start, end, jsEvent, view) {
                var allDay = start.hasTime() === false;

                self._onCalendarEventCreate(calendar, new CalendarEventRange({
                    start: start,
                    end: end,
                    duration: FULLCALENDAR_SETTINGS.defaultTimedEventDuration,
                    allDay: allDay
                }));
            },
            viewRender: function(view) {
                self._renderCalendarView(calendar, view);
            },
            eventRender: function(event, item, view) {
                if (event._id) {
                    self._renderCalendarEvent(calendar, event, item, view);
                } else {
                    self._renderCalendarSelection(calendar, event, item, view);
                }
            },
            // eventDragStart: function(calEvent, domEvent, ui, view) {},
            // see https://fullcalendar.io/docs/drop
            drop: function(date) {
                var allDay = self.calendarView().name === 'month';
                var event = new CalendarEventRange({
                    start: date,
                    duration: FULLCALENDAR_SETTINGS.defaultTimedEventDuration,
                    allDay: allDay
                });
                self._onCalendarExternalEventUpdate(calendar, $(this), event);
            },
            // see https://fullcalendar.io/docs/eventDrop
            eventDrop: function(event, delta, revertFunc) {
                event = new CalendarEventRange(event);
                self._onCalendarEventUpdate(calendar, $(this), event, revertFunc);
            },
            eventResize: function(event, delta, revertFunc) {
                event = new CalendarEventRange(event);
                self._onCalendarEventUpdate(calendar, $(this), event, revertFunc);
            },
            eventClick: function(event, item, jsEvent) {
                self._onCalendarEventShow(calendar, event, item);
                return false;
            }
            /* TODO : handle overlap validation for events from same calendar ?
            eventOverlap: function(still, moving) {
                return self._checkCalendarEventOverlap(still, moving);
            }
            */
        }));
    }
});

}(jQuery));
