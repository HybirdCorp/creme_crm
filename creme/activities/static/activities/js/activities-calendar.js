/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2023  Hybird

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

function momentFormatter(format, dayFormat) {
    format = format || 'h[h]mm';

    return function(info) {
        var locale = info.localeCodes[0];
        var start = convertToMoment(info.start, info.timeZone, locale);
        var end = info.end ? convertToMoment(info.end, info.timeZone, locale) : null;
        var output;

        if (end !== null) {
            var rangeFormat = format;

            if (dayFormat) {
                if (start.format('MMD') !== end.format('MMD')) {
                    rangeFormat = dayFormat;
                }
            }

            output = [
                start.format(rangeFormat),
                end.format(rangeFormat)
            ].join(info.defaultSeparator);
        } else {
            output = start.format(format);
        }

        return output;
    };
};

/*
function labelInitials(label) {
    return label.split(/[-,\s]/i).map(function(word) {
        return word.charAt(0).toUpperCase();
    }).join('.') + '.';
}
*/

var FULLCALENDAR_SETTINGS = {
    // plugins: [ 'interaction', 'timeGrid', 'dayGrid', 'moment' ],
    locales: [{
        code: "fr",
        buttonText: {
            // prev:     '◄',  // left triangle
            // next:     '►',  // right triangle
            today: gettext("Today"),
            year:  gettext("Year"),
            month: gettext("Month"),
            week:  gettext("Week"),
            day:   gettext("Day"),
            list:  gettext("Calendar")
        },
        weekText: gettext("Week"),
        allDayContent: gettext("All day"),
        moreLinkContent: gettext("More"),
        noEventsContent: gettext("No event to display")
    }],
    locale: 'fr',
    eventTimeFormat: momentFormatter('H[h]mm', 'D/MM h[h]mm'),

    headerToolbar: {
        left:   'title',
        center: 'today,prev,next',
        right:  'week,month'
    },
    initialView: 'month',
    views: {
        month: {
            type: 'dayGridMonth',
            titleFormat: { year: 'numeric', month: 'long' },
            dayHeaderFormat: { weekday: 'long' }
        },
        week: {
            type: 'timeGridWeek',
            titleFormat: { year: 'numeric', month: 'long', day: 'numeric' },
            titleRangeSeparator: ' − ',
            dayHeaderFormat: { weekday: 'long', day: 'numeric', month: 'long' },
            weekNumbers: false
        },
        day: {
            type: 'timeGridDay',
            titleFormat: { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' },
            dayHeaderFormat: { weekday: 'long', day: 'numeric', month: 'long' }
        }
    },

    /* day settings */
    timeZone: 'UTC',
    slotMinTime: '00:00:00',
    slotMaxTime: '24:00:00',
    scrollTime: '08:00:00',
    defaultTimedEventDuration: '01:00:00',

    businessHours: {
        daysOfWeek: [ 1, 2, 3, 4, 5, 6 ], // Monday - Saturday
        startTime: '8:00', // a start time
        endTime: '18:00' // an end time
    },

    /* slots */
    allDaySlot: true,
    allDayContent: gettext("All day"),
    slotLabelFormat: momentFormatter("H[h]mm"),
    slotLabelInterval: '01:00:00',
    slotDuration: '00:15:00',
    defaultRangeSeparator: ' − ',

    /* week settings */
    weekends: true,
    firstDay: 1,    // monday
    fixedWeekCount: true,

    /* ui settings */
    themeSystem: 'standard',
    aspectRatio: 2,
    expandRows: true,

    editable: true,
    selectable: true,
    dayMaxEventRows: 4,
    dayMaxEvents: true,
    stickyHeaderDates: true,
    selectMirror: true,

    droppable: true,
    dropAccept: '.floating-event',

    /* ui plugins */
    nowIndicator: true
};

function convertToMoment(input, timeZone, locale) {
    if (input === null || moment.isMoment(input)) {
        return input;
    } else {
        return moment.utc(input);
    }
}

function toISO8601(value, allDay) {
    return allDay ? value.format('YYYY-MM-DD') : value.utc().toISOString(true);
}

creme.ActivityCalendarEventRange = creme.component.Component.sub({
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
                this.end.set({hours: 23, minutes: 59, seconds: 0});
            } else {
                this.end.add(moment.duration(this.duration));
            }
        } else if (this.allDay) {
            this.end.set({hours: 0, minutes: 0, seconds: 0}).subtract(1, 'minutes');
        }
    },

    isSmall: function() {
        return !this.allDay && (this.end.diff(this.start) < moment.duration('00:31:00').asMilliseconds());
    },

    toString: function() {
        return '${start} − ${end}${allday}'.template({
            start: this.start,
            end: this.end,
            allday: this.allDay ? '[ALLDAY]' : ''
        });
    }
});

creme.ActivityCalendar = creme.component.Component.sub({
    _init_: function(element, options) {
        options = $.extend({
            debounceDelay: 200,
            defaultView: 'month',
            keepState: false,
            showWeekNumber: true,
            showTimezoneInfo: false,
            allowEventMove: true,
            fullCalendarOptions: {}
        }, options || {});

        this._element = element;

        Assert.not(this.calendarElement().is('.fc-creme'), 'CalendarController is already bound');

        this.debounceDelay(options.debounceDelay);
        this.defaultView(options.defaultView);
        this.owner(options.owner || '');
        this.eventSelectUrl(options.eventSelectUrl || '');
        this.eventUpdateUrl(options.eventUpdateUrl || '');
        this.eventCreateUrl(options.eventCreateUrl || '');
        this.eventFetchUrl(options.eventFetchUrl || '');
        this.keepState(options.keepState);
        this.showWeekNumber(options.showWeekNumber);
        this.showTimezoneInfo(options.showTimezoneInfo);
        this.allowEventMove(options.allowEventMove);
        this.timezoneOffset(options.timezoneOffset);

        this._bindFilterInputs(element, '.floating-event-filter input', this._filterCalendarEvents.bind(this));
        this._bindFilterInputs(element, '.calendar-menu-filter input', this._filterCalendars.bind(this));
        this._bindToggleCalendar(element);

        this._setupCalendarUi(element, options);
        this._setupCalendarExternalEvents(element);
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

    allowEventMove: function(state) {
        return Object.property(this, '_allowEventMove', state);
    },

    timezoneOffset: function(offset) {
        return Object.property(this, '_timezoneOffset', offset);
    },

    defaultView: function(view) {
        return Object.property(this, '_defaultView', view);
    },

    debounceDelay: function(delay) {
        return Object.property(this, '_debounceDelay', delay);
    },

    keepState: function(keep) {
        return Object.property(this, '_keepState', keep);
    },

    showWeekNumber: function(state) {
        return Object.property(this, '_showWeekNumber', state);
    },

    showTimezoneInfo: function(state) {
        return Object.property(this, '_showTimezoneInfo', state);
    },

    calendarElement: function() {
        return this._element.find('.calendar');
    },

    fullCalendar: function() {
        return this._calendar;
    },

    fullCalendarView: function(view, options) {
        if (view === undefined) {
            return this._calendar.view;
        }

        var calendar = this._calendar;

        calendar.batchRendering(function() {
            calendar.changeView(view, options);
        });
    },

    goToDate: function(date) {
        this._calendar.gotoDate(date);
    },

    fullCalendarEvents: function() {
        return this._calendar.getEvents();
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
                              .onComplete(function() {
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

    element: function() {
        return this._element;
    },

    visibleCalendarIds: function(ids) {
        var checkboxes = this._element.find('input[type="checkbox"][name="calendar_id"]:checked');

        if (ids === undefined) {
            return checkboxes.map(function() {
                return $(this).val();
            }).get();
        }

        checkboxes.each(function() {
            $(this).prop('checked', ids.indexOf($(this).val()) !== -1);
        });

        this.fullCalendar().refetchEvents();
        return this;
    },

    toMoment: function(input) {
        var dateEnv = this.fullCalendar().getCurrentData().dateEnv;
        var timeZone = dateEnv.timeZone;
        var locale = dateEnv.locale.codes[0];

        return convertToMoment(input, timeZone, locale);
    },

    _loadStateFromUrl: function(url) {
        var hash = creme.ajax.parseUrl(url || window.location.href).hash || '';
        var data = creme.ajax.decodeSearchData(hash.slice(1));
        var view = data.view && (data.view in FULLCALENDAR_SETTINGS.views) ? data.view : this.defaultView();
        var date = data.date ? moment(data.date) : undefined;
        date = date && date.isValid() ? date : undefined;

        return {view: view, date: date};
    },

    _storeStateInUrl: function(state) {
        creme.history.push('#' + creme.ajax.param({
            view: state.view,
            date: state.date.format('YYYY-MM-DD')
        }));
    },

    _updateState: function(info) {
        var previous = (this._loadStateFromUrl() || {});
        var prevDateISO = previous.date ? toISO8601(previous.date, true) : null;

        if (info.view === previous.view && toISO8601(info.start, true) === prevDateISO) {
            return;
        }

        /*
         * In month view the activeStart & activeEnd are enclosing the stored date.
         * Do not change the state if the date is still within view range.
         */
        if (info.view === 'month' && previous.date && previous.date.isBetween(info.start, info.end)) {
            return;
        }

        this._storeStateInUrl({
            view: info.view, date: info.start
        });
    },

    _addAllCalendarEvents: function(id) {
        // NB: creating new event source is a bad idea, because these new sources
        // have to be removed, in order to avoid :
        //    - duplicated Activities when we go to a page we a newly checked calendar.
        //    - accumulating event sources.
        // so we just force a new fetch.  TODO: find a way to only retrieve new events + cache
        this.fullCalendar().refetchEvents();
    },

    _removeAllCalendarEvents: function(calendarId) {
        var calendar = this.fullCalendar();
        var query = this._query({
                            url: this.eventSelectUrl(),
                            action: 'POST'
                        }, {
                            remove: calendarId
                        });

        query.onDone(function() {
            var events = calendar.getEvents().filter(function(event) {
                return String(calendarId) === String(event.extendedProps.calendar);
            });

            calendar.batchRendering(function() {
                events.forEach(function(event) {
                    event.remove();
                });
            });
        }).start();

        return this;
    },

    _debounce: function(handler) {
        var delay = this.debounceDelay();

        if (delay > 0) {
            return _.debounce(handler, delay);
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
        var self = this;
        var floatingEls = element.find('.floating-activities');

        if (floatingEls.length > 0) {
            this._draggable = new FullCalendar.Draggable(floatingEls.get(0), {
                 itemSelector: '.floating-event',
                 eventData: function(el) {
                    return self._getFloatingEventData($(el));
                 }
            });
        }
    },

    _getFloatingEventData: function(item) {
        var color = item.data('color');

        return {
            id: item.data('id'),
            title: (item.text() || '').trim(),
            extendedProps: {
                type: item.data('type'),
                user: this.owner(),
                calendar: item.data('calendar'),
                busy: Boolean(item.data('busy'))
            },
            className: [],
            url: item.data('popup_url'),
            editable: true,
            create: false,
            backgroundColor: color,
            textColor: new RGBColor(color).foreground().toString()
        };
    },

    _onCalendarExternalEventUpdate: function(calendar, info) {
        var item = $(info.draggedEl);
        var range = new creme.ActivityCalendarEventRange({
            start: this.toMoment(info.date, calendar),
            duration: calendar.getOption('defaultTimedEventDuration'),
            allDay: info.allDay
        });

        var nextEvent = $.extend({}, this._getFloatingEventData(item), {
            start: range.start.toDate(),
            end: range.end.toDate(),
            allDay: range.allDay
        });

        this._query({
                 url: this.eventUpdateUrl(),
                 action: 'POST',
                 warnOnFail: true
             }, {
                 id: nextEvent.id,
                 start: toISO8601(range.start, range.allDay),
                 end: toISO8601(range.end, range.allDay),
                 allDay: range.allDay
             })
            .onDone(function() {
                 calendar.addEvent(nextEvent);

                 var group = item.parents('.menu-group').first();
                 item.detach();

                 group.toggleClass('is-empty-group', group.find('.floating-event').length === 0);
             })
            .start();
    },

    _onCalendarEventUpdate: function(calendar, info) {
        var range = new creme.ActivityCalendarEventRange({
            start: this.toMoment(info.event.start, calendar),
            end: this.toMoment(info.event.end, calendar),
            duration: calendar.getOption('defaultTimedEventDuration'),
            allDay: info.event.allDay
        });

        /*
         * Drag-n-drop from AllDay to a slot will not fill the 'end' attribute.
         * So do it ourselves.
         */
        if (!info.event.allDay && info.event.end === null) {
            info.event.setEnd(range.end.toDate());
        }

        this._query({
                 url: this.eventUpdateUrl(),
                 action: 'POST',
                 warnOnFail: true
             }, {
                 id: info.event.id,
                 start: toISO8601(range.start, range.allDay),
                 end: toISO8601(range.end, range.allDay),
                 allDay: range.allDay
             })
            .onFail(function() {
                info.revert();
             })
            .start();
    },

    _onCalendarEventFetch: function(calendar, info, successCb, failureCb) {
        var range = new creme.ActivityCalendarEventRange({
            start: this.toMoment(info.start, calendar),
            end: this.toMoment(info.end, calendar)
        });

        var isEditable = this.allowEventMove();

        this._query({
                url: this.eventFetchUrl(),
                backend: {dataType: 'json'}
             }, {
                calendar_id: this.visibleCalendarIds(),
                start: range.start.format('YYYY-MM-DD'),
                end: range.end.format('YYYY-MM-DD')
             })
            .onDone(function(event, data) {
                successCb(data.map(function(item) {
                    item.textColor = new RGBColor(item.color).foreground().toString();
                    item.editable = item.editable && isEditable;
                    return item;
                }));
             })
            .onFail(function(event, err) {
                failureCb(err);
            })
            .start();
    },

    _onCalendarEventCreate: function(calendar, info) {
        var range = new creme.ActivityCalendarEventRange({
            start: this.toMoment(info.start, calendar),
            end: this.toMoment(info.end, calendar),
            duration: calendar.getOption('defaultTimedEventDuration'),
            allDay: info.allDay
        });

        var data = {
            start: toISO8601(range.start, range.allDay),
            end: toISO8601(range.end, range.allDay),
            allDay: range.allDay ? 1 : 0
        };

        creme.dialogs.form(this.eventCreateUrl(), {}, data)
                     .onFormSuccess(function(event, response) {
                         var redirect = response.content;

                         if (redirect) {
                            /* TODO: unit test this case */
                            creme.utils.goTo(redirect);
                         } else {
                            calendar.refetchEvents();
                         }
                      })
                     .open({width: '80%'});
    },

    _onCalendarEventShow: function(calendar, info) {
        creme.dialogs.url(info.event.url)
                     .onClose(function() {
                         calendar.refetchEvents();
                     }).open({width: '80%'});
    },

    _formatEventTime: function(info, formatter) {
        var view = info.view;
        var event = info.event;

        if (info.event.end !== null) {
            return view.dateEnv.formatRange(event.start, event.end, formatter);
        } else {
            return view.dateEnv.format(event.start, formatter);
        }
    },

    _eventTimeSlotCount: function(event, calendar) {
        var eventDuration = this.toMoment(event.end, calendar).diff(this.toMoment(event.start, calendar));
        var slotDuration = moment.duration(calendar.getOption('slotDuration')).asMilliseconds();
        return event.end && Math.round(eventDuration / slotDuration);
    },

    _renderWeekEventContent: function(calendar, info, createElement) {
        var event = info.event;
        var view = info.view;
        var items = [];
        var text = info.timeText;
        var formatter = FullCalendar.createFormatter(calendar.getOption('eventTimeFormat'));
        var slotCount = this._eventTimeSlotCount(event, calendar);
        var typeTag = event.extendedProps.type || '';

        if (event.allDay) {
            items = [
                createElement('div', {className: 'fc-event-main-frame'},
                    createElement('div', {className: 'fc-event-title'}, event.title),
                    typeTag && (createElement('div', {className: 'fc-event-type'}, typeTag))
                )
            ];
        } else if (slotCount < 2) {
            text = view.dateEnv.format(event.start, formatter);

            items = [
                createElement('div', {className: 'fc-event-main-frame fc-smaller'},
                    text && (createElement("div", { className: "fc-event-time" }, text)),
                    createElement('div', {className: 'fc-event-title'}, event.title),
                    typeTag && (createElement('div', {className: 'fc-event-type'}, typeTag))
                )
            ];
        } else if (slotCount < 3) {
            text = view.dateEnv.format(event.start, formatter);

            items = [
                createElement('div', {className: 'fc-event-main-frame fc-small'},
                    text && (createElement("div", { className: "fc-event-time" }, text)),
                    typeTag && (createElement('div', {className: 'fc-event-type'}, typeTag)),
                    createElement('div', {className: 'fc-event-title'}, event.title)
                )
            ];
        } else {
            text = event.end ? this._formatEventTime(info, formatter) : text;

            items = [
                createElement('div', {className: 'fc-event-main-frame'},
                    typeTag && (createElement('div', {className: 'fc-event-type fc-sticky'}, typeTag)),
                    createElement('div', {className: 'fc-event-header'},
                        text && (createElement("div", {className: "fc-event-time"}, text))
                    ),
                    createElement('div', {className: 'fc-event-title-container'},
                        createElement('div', {className: 'fc-event-title fc-sticky'}, event.title)
                    )
                )
            ];
        }

        return items;
    },

    _renderMonthEventContent: function(calendar, info, createElement) {
        var event = info.event;
        var typeTag = event.extendedProps.type || '';
        var dotColor = info.borderColor || info.backgroundColor;
        var items = [];
        var text = info.timeText;
        var start = this.toMoment(event.start, calendar);
        var end = this.toMoment(event.end, calendar);
        var isMultiDay = end && start.format('MMD') !== end.format('MMD');

        if (event.allDay || isMultiDay) {
            items = [
                createElement('div', {className: 'fc-event-main-frame'},
                    createElement('div', {className: 'fc-event-title'}, event.title),
                    typeTag && (createElement('div', {className: 'fc-event-type'}, typeTag))
                )
            ];
        } else {
            items = [
                createElement('div', {className: 'fc-daygrid-event-dot', style: {borderColor: dotColor}}),
                text && (createElement("div", { className: "fc-event-time" }, text)),
                createElement('div', {className: 'fc-event-title'}, event.title),
                typeTag && (createElement('div', {className: 'fc-event-type'}, typeTag))
            ];
        }

        return items;
    },

    _renderCalendarEventContent: function(calendar, info, createElement) {
        if (info.view.type === 'week') {
            return this._renderWeekEventContent(calendar, info, createElement);
        } else {
            return this._renderMonthEventContent(calendar, info, createElement);
        }
    },

    _postRenderCalendarEvent: function(calendar, info) {
        var formatter = FullCalendar.createFormatter(calendar.getOption('eventTimeFormat'));
        var title = "${range}\n${tag}${title}".template({
            range: this._formatEventTime(info, formatter),
            tag: info.event.extendedProps.type ? info.event.extendedProps.type + '\n' : '',
            title: info.event.title
        });

        info.el.setAttribute('alt', title);
        info.el.setAttribute('title', title);

        if (info.event.extendedProps.busy) {
            info.el.classList.add('fc-busy');
        }
    },

    _postRenderCalendarView: function(calendar, info) {
        var view = info.view;

        if (this.showWeekNumber()) {
            var title = this.calendarElement().find('.fc-header-toolbar .fc-toolbar-title');
            var start = this.toMoment(view.activeStart, calendar);
            var week = title.find('.fc-header-week');
            var isWeekView = (view.type === 'week');

            if (isWeekView) {
                if (week.length === 0) {
                    week = $('<span class="fc-header-week">').appendTo(title);
                }

                week.text('${label} ${num}'.template({
                    label: gettext("Week"),
                    num: start.format('W')
                }));
            }

            week.toggleClass('hidden', !isWeekView);
        }
    },

    _renderWeekNumber: function(calendar, info) {
        return this.toMoment(info.date, calendar).format('[S] W');
    },

    _onCalendarEventOverlap: function(calendar, still, moving) {
        return true;
        // return still.extendedProps.calendar !== moving.extendedProps.calendar;
    },

    _setupCalendarHandlers: function(calendar) {
        var self = this;

        calendar.on('select', function(info) {
            self._onCalendarEventCreate(calendar, info);
        });
        calendar.on('eventClick', function(info) {
            info.jsEvent.preventDefault();
            self._onCalendarEventShow(calendar, info);
            return false;
        });
        calendar.on('eventResize', function(info) {
            self._onCalendarEventUpdate(calendar, info);
            self._postRenderCalendarEvent(calendar, info);
        });
        calendar.on('datesSet', function(info) {
            self._postRenderCalendarView(calendar, info);

            if (self.keepState()) {
                self._updateState({
                    view: info.view.type,
                    start: self.toMoment(info.view.activeStart, calendar),
                    end: self.toMoment(info.view.activeEnd, calendar)
                });
            }
        });
        calendar.on('drop', function(info) {
            self._onCalendarExternalEventUpdate(calendar, info);
        });
        calendar.on('eventDrop', function(info) {
            self._onCalendarEventUpdate(calendar, info);
        });
    },

    _setupCalendarUi: function(element, options) {
        var self = this;
        var calendarElement = this.calendarElement().addClass('fc-creme');
        var initialState = $.extend({
            date: options.initialDate ? moment(options.initialDate) : moment(),
            view: options.initialView
        }, this._loadStateFromUrl());

        var calendar = this._calendar = new FullCalendar.Calendar(
            calendarElement.get(0),
            $.extend({}, FULLCALENDAR_SETTINGS, options.fullCalendarOptions || {}, {
                initialView: initialState.view,
                initialDate: initialState.date.format('YYYY-MM-DD'),
                weekNumbers: options.showWeekNumber,
                weekNumberContent: function(info) {
                    return self._renderWeekNumber(calendar, info);
                },
                eventContent: function(info, createElement) {
                    return self._renderCalendarEventContent(calendar, info, createElement);
                },
                eventDidMount: function(info) {
                    return self._postRenderCalendarEvent(calendar, info);
                },
                eventOverlap: function(still, moving) {
                    return self._onCalendarEventOverlap(calendar, still, moving);
                },
                nowIndicatorContent: function(info, createElement) {
                    if (self.showTimezoneInfo()) {
                        var text = moment.utc().utcOffset(self.timezoneOffset()).format('Z');
                        return createElement('div', {className: 'fc-timegrid-now-timezone'}, 'UTC' + text);
                    }
                },
                now: function() {
                    var now = moment().milliseconds(0);
                    var offset = self.timezoneOffset();

                    offset = isNaN(offset) ? now.utcOffset() : offset;
                    now = now.utc().add(offset, 'm');

                    return now.toISOString(true);
                }
            })
        );

        calendarElement.data('fc-creme', calendar);

        calendar.addEventSource(function(info, successCb, failureCb) {
            self._onCalendarEventFetch(calendar, info, successCb, failureCb);
        });

        this._setupCalendarHandlers(calendar);

        calendar.render();

        $(window).on('hashchange', function() {
            if (self.keepState()) {
                var state = self._loadStateFromUrl();

                if (state.view) {
                    calendar.changeView(
                        state.view,
                        state.date ? state.date.format('YYYY-MM-DD') : undefined
                    );
                }
            }
        });
    }
});

}(jQuery));
