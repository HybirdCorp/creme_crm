/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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

function isStartOfDay(value) {
    return value.toArray().slice(3, 6).join('') === '000';
}

function eventMomentFormatter(options) {
    options = options || {};
    var timeFormat = options.time || 'H[h]mm';
    var dayFormat = options.datetime || timeFormat;
    var dateFormat = options.date || 'D/MM';  // TODO

    return function(info) {
        var locale = info.localeCodes[0];
        var start = convertToMoment(info.start, info.timeZone, locale);
        var end = info.end ? convertToMoment(info.end, info.timeZone, locale) : null;
        var output;

        if (end === null) {
            // Without end, it can be either an allDay event (starts at 0h00) or monthview event.
            // fullcalendar does not give any clue...
            output = isStartOfDay(start) ? start.format(dateFormat) : start.format(timeFormat);
        } else if (start.isSame(end, 'day')) {
            output = [
                start.format(timeFormat),
                end.format(timeFormat)
            ].join(info.defaultSeparator);
        } else if (isStartOfDay(start) && isStartOfDay(end)) {
            var days = end ? end.diff(start, 'days') : 0;

            // if both start & end are at 00:00:00 there is a good chance that is an allDay event.
            if (days > 1) {
                output = [
                    start.format(dateFormat),
                    end.clone().add(-1, 'day').format(dateFormat)
                ].join(info.defaultSeparator);
            } else {
                output = start.format(dateFormat);
            }
        } else {
            output = [
                start.format(dayFormat),
                end.format(dayFormat)
            ].join(info.defaultSeparator);
        }

        return output;
    };
}

function slotMomentFormatter(format) {
    return function(info) {
        var locale = info.localeCodes[0];
        var start = convertToMoment(info.start, info.timeZone, locale);

        return start.format(format);
    };
}

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
    eventTimeFormat: eventMomentFormatter({
        time: 'H[h]mm',
        datetime: 'D/MM H[h]mm',
        date: 'D/MM'
    }),

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
        startTime: '08:00:00', // a start time
        endTime: '18:00:00' // an end time
    },

    /* slots */
    allDaySlot: true,
    allDayContent: gettext("All day"),
    slotLabelFormat: slotMomentFormatter("H[h]mm"),
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

creme.availableFullCalendarViewNames = function(options) {
    options = options || {};
    var views = Object.assign(FULLCALENDAR_SETTINGS, (options.fullCalendarOptions || options)).views || {};
    return _.keys(views);
};

creme.CalendarEventRange = creme.component.Component.sub({
    _init_: function(options) {
        options = Object.assign({
            start: moment(),
            duration: '01:00:00',
            allDay: false
        }, options || {});

        this.start = options.start;
        this.end = options.end;
        this.allDay = options.allDay;

        if (Object.isNone(this.end)) {
            this.end = this.start.clone();

            if (this.allDay) {
                this.end.set({hours: 23, minutes: 59, seconds: 0});
            } else {
                this.end.add(moment.duration(options.duration));
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
        options = Object.assign({
            allowEventCreate: true,
            allowEventMove: true,
            allowEventOverlaps: true,
            defaultView: 'month',
            externalEventData: _.noop,
            eventUpdateUrl: '',
            eventCreateUrl: '',
            eventFetchUrl: '',
            fullCalendarOptions: {},
            headlessMode: false,
            owner: '',
            selectedSourceIds: [],
            showWeekNumber: true,
            showTimezoneInfo: false,
            timezoneOffset: 0,
            rendererDelay: 100
        }, options || {});

        this._element = element;
        this._events = new creme.component.EventHandler();

        this.selectedSourceIds(options.selectedSourceIds || []);
        this.props(_.omit(options, 'selectedSourceIds'));

        Assert.not(element.is('.fc-creme'), 'creme.ActivityCalendar is already bound');

        this._setupCalendarUi(element, options);
        this._setupCalendarExternalEvents(element);
    },

    props: function(props) {
        if (props === undefined) {
            return Object.assign({}, this._props);
        }

        this._props = Object.assign(this._props || {}, props);
        return this;
    },

    prop: function(name, value) {
        if (value === undefined) {
            return this._props[name];
        } else {
            this._props[name] = value;
            return this;
        }
    },

    trigger: function(event) {
        var data = Array.from(arguments).slice(1);

        if (!Object.isNone(this._element)) {
            this._element.trigger('cal-' + event, [this].concat(data || []));
        }

        this._events.trigger(event, data, this);
        return this;
    },

    one: function(event, listener, decorator) {
        this._events.one(event, listener, decorator);
        return this;
    },

    on: function(event, listener, decorator) {
        this._events.on(event, listener, decorator);
        return this;
    },

    off: function(event, listener) {
        this._events.off(event, listener);
        return this;
    },

    allowEventCreate: function(state) {
        return this.prop('allowEventCreate', state);
    },

    allowEventMove: function(state) {
        return this.prop('allowEventMove', state);
    },

    allowEventOverlaps: function(state) {
        return this.prop('allowEventOverlaps', state);
    },

    defaultView: function(view) {
        return this.prop('defaultView', view);
    },

    element: function() {
        return this._element;
    },

    eventUpdateUrl: function(url) {
        return this.prop('eventUpdateUrl', url);
    },

    eventCreateUrl: function(url) {
        return this.prop('eventCreateUrl', url);
    },

    eventFetchUrl: function(url) {
        return this.prop('eventFetchUrl', url);
    },

    fullCalendar: function() {
        return this._calendar;
    },

    fullCalendarEvents: function() {
        return this._calendar.getEvents();
    },

    fullCalendarOptions: function(options) {
        return this.prop('fullCalendarOptions', options);
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

    headlessMode: function(flag) {
        return this.prop('headlessMode', flag);
    },

    owner: function(owner) {
        return this.prop('owner', owner);
    },

    showWeekNumber: function(state) {
        return this.prop('showWeekNumber', state);
    },

    showTimezoneInfo: function(state) {
        return this.prop('showTimezoneInfo', state);
    },

    timezoneOffset: function(offset) {
        return this.prop('timezoneOffset', offset);
    },

    selectedSourceIds: function(ids) {
        if (ids === undefined) {
            return Array.from(this._selectedSourceIds || []);
        }

        // NB: creating new event source is a bad idea, because these new sources
        // have to be removed, in order to avoid :
        //    - duplicated Activities when we go to a page we a newly checked calendar.
        //    - accumulating event sources.
        // so we just force a new fetch.

        var next = new Set(ids || []);
        var prev = new Set(this._selectedSourceIds || []);

        var added = _.reject(Array.from(next), function(id) { return prev.has(id); });
        var removed = _.reject(Array.from(prev), function(id) { return next.has(id); });
        var calendar = this._calendar;

        this._selectedSourceIds = ids;

        if (!added.length && removed.length > 0) {
            // Just remove fullcalendar events when sources are only removed : no query + full redraw
            if (calendar) {
                var removedEvents = calendar.getEvents().filter(function(event) {
                    return !next.has(String(event.extendedProps.calendar));
                });

                calendar.batchRendering(function() {
                    removedEvents.forEach(function(event) {
                        event.remove();
                    });
                });
            }
        } else if (next.size) {
            // TODO: find a way to only retrieve new events + cache
            this.refetchEvents();
        }

        return this;
    },

    redraw: function() {
        if (this._calendar) {
            this._calendar.render();
        }

        return this;
    },

    refetchEvents: function() {
        if (this._calendar) {
            this._calendar.refetchEvents();
        }

        return this;
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
                              .onComplete(function(event) {
                                  self.trigger('query-complete', {
                                      activityCalendar: self,
                                      options: options,
                                      data: data,
                                      ok: event === 'done'
                                  });
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

    _toMoment: function(input) {
        var dateEnv = this.fullCalendar().getCurrentData().dateEnv;
        var timeZone = dateEnv.timeZone;
        var locale = dateEnv.locale.codes[0];

        return convertToMoment(input, timeZone, locale);
    },

    _setupCalendarExternalEvents: function(element) {
        var self = this;
        var props = this._props;
        var container = $(props.externalEventContainer);

        if (container.length > 0) {
            this._draggable = new FullCalendar.Draggable(container.get(0), {
                 itemSelector: props.externalEventItemSelector,
                 eventData: function(el) {
                    return self._props.externalEventData($(el), this);
                 }
            });
        }
    },

    _onCalendarExternalEventUpdate: function(calendar, info) {
        var self = this;
        var item = $(info.draggedEl);
        var range = new creme.CalendarEventRange({
            start: this._toMoment(info.date),
            duration: calendar.getOption('defaultTimedEventDuration'),
            allDay: info.allDay
        });

        var nextEvent = Object.assign({}, this._props.externalEventData(item, this), {
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

                 self.trigger('event-new', {
                     activityCalendar: self,
                     activityRange: range,
                     calEvent: nextEvent,
                     item: item,
                     external: true
                 });
             })
            .onFail(function() {
                info.revert();
             })
            .start();
    },

    _onCalendarEventUpdate: function(calendar, info) {
        var self = this;
        var range = new creme.CalendarEventRange({
            start: this._toMoment(info.event.start),
            end: this._toMoment(info.event.end),
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
            .onDone(function() {
                self.trigger('event-update', {
                    activityCalendar: self,
                    activityRange: range
                });
            })
            .start();
    },

    _onCalendarEventFetch: function(calendar, info, successCb, failureCb) {
        var self = this;
        var range = new creme.CalendarEventRange({
            start: this._toMoment(info.start),
            end: this._toMoment(info.end)
        });

        var isEditable = this.allowEventMove();

        this._query({
                url: this.eventFetchUrl(),
                backend: {dataType: 'json'}
             }, {
                calendar_id: this.selectedSourceIds(),
                start: range.start.format('YYYY-MM-DD'),
                end: range.end.format('YYYY-MM-DD')
             })
            .onDone(function(event, data) {
                var items = data.map(function(item) {
                    item.textColor = new RGBColor(item.color).foreground().toString();
                    item.editable = item.editable && isEditable;
                    return item;
                });

                self.trigger('event-fetch', {
                    activityCalendar: self,
                    activityRange: range,
                    items: items,
                    ok: true
                });

                successCb(items);
             })
            .onFail(function(event, err) {
                self.trigger('event-fetch', {
                    activityCalendar: self,
                    activityRange: range,
                    items: [],
                    error: err,
                    ok: false
                });

                failureCb(err);
            })
            .start();
    },

    _onCalendarEventCreate: function(calendar, info) {
        var self = this;

        var range = new creme.CalendarEventRange({
            start: this._toMoment(info.start),
            end: this._toMoment(info.end),
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
                         self.trigger('event-new', {
                             activityCalendar: self,
                             activityRange: range,
                             calEvent: info,
                             external: false,
                             redirectUrl: response.content
                         });
                      })
                     .open({width: '80%'});
    },

    _onCalendarEventShow: function(calendar, info) {
        var self = this;

        creme.dialogs.url(info.event.url)
                     .onClose(function() {
                         self.refetchEvents();
                         self.trigger('event-shown', {
                             activityCalendar: self,
                             calEvent: info
                         });
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
        if (event.end) {
            var start = this._toMoment(event.start);
            var end = this._toMoment(event.end);
            var eventDuration = start ? end.diff(start) : 0;
            var slotDuration = moment.duration(calendar.getOption('slotDuration')).asMilliseconds();
            return Math.round(eventDuration / slotDuration);
        }
    },

    _renderWeekEventContent: function(calendar, info, createElement) {
        var event = info.event;
        var view = info.view;
        var text = info.timeText;
        var formatter = FullCalendar.Internal.createFormatter(calendar.getOption('eventTimeFormat'));
        var slotCount = this._eventTimeSlotCount(event, calendar);
        var typeTag = event.extendedProps.type || '';

        if (event.allDay) {
            return createElement('div', {className: 'fc-event-main-frame'},
                createElement('div', {className: 'fc-event-title'}, event.title),
                typeTag && (createElement('div', {className: 'fc-event-type'}, typeTag))
            );
        } else if (slotCount < 2) {
            text = view.dateEnv.format(event.start, formatter);

            return createElement('div', {className: 'fc-event-main-frame fc-smaller'},
                text && (createElement("div", { className: "fc-event-time" }, text)),
                createElement('div', {className: 'fc-event-title'}, event.title),
                typeTag && (createElement('div', {className: 'fc-event-type'}, typeTag))
            );
        } else if (slotCount < 3) {
            text = view.dateEnv.format(event.start, formatter);

            return createElement('div', {className: 'fc-event-main-frame fc-small'},
                text && (createElement("div", { className: "fc-event-time" }, text)),
                typeTag && (createElement('div', {className: 'fc-event-type'}, typeTag)),
                createElement('div', {className: 'fc-event-title'}, event.title)
            );
        } else {
            text = event.end ? this._formatEventTime(info, formatter) : text;

            return createElement('div', {className: 'fc-event-main-frame'},
                typeTag && (createElement('div', {className: 'fc-event-type fc-sticky'}, typeTag)),
                createElement('div', {className: 'fc-event-header'},
                    text && (createElement("div", {className: "fc-event-time"}, text))
                ),
                createElement('div', {className: 'fc-event-title-container'},
                    createElement('div', {className: 'fc-event-title fc-sticky'}, event.title)
                )
            );
        }
    },

    _renderMonthEventContent: function(calendar, info, createElement) {
        var event = info.event;
        var view = info.view;
        var typeTag = event.extendedProps.type || '';
        var dotColor = info.borderColor || info.backgroundColor;
        var text = info.timeText;
        var start = this._toMoment(event.start);
        var end = this._toMoment(event.end);
        var isMultiDay = end && start.format('MMD') !== end.format('MMD');
        var formatter = FullCalendar.Internal.createFormatter(calendar.getOption('eventTimeFormat'));

        if (event.allDay || isMultiDay) {
            return createElement('div', {className: 'fc-event-main-frame'},
                createElement('div', {className: 'fc-event-title'}, event.title),
                typeTag && (createElement('div', {className: 'fc-event-type'}, typeTag))
            );
        } else {
            text = view.dateEnv.format(event.start, formatter);

            return createElement('div', {className: 'fc-event-empty-frame'},
                createElement('div', {className: 'fc-daygrid-event-dot', style: {borderColor: dotColor}}),
                text && (createElement("div", { className: "fc-event-time" }, text)),
                createElement('div', {className: 'fc-event-title'}, event.title),
                typeTag && (createElement('div', {className: 'fc-event-type'}, typeTag))
            );
        }
    },

    _renderCalendarEventContent: function(calendar, info, createElement) {
        if (info.view.type === 'week') {
            return this._renderWeekEventContent(calendar, info, createElement);
        } else {
            return this._renderMonthEventContent(calendar, info, createElement);
        }
    },

    _postRenderCalendarEvent: function(calendar, info) {
        var formatter = FullCalendar.Internal.createFormatter(calendar.getOption('eventTimeFormat'));
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
            var title = this._element.find('.fc-header-toolbar .fc-toolbar-title');
            var start = this._toMoment(view.activeStart);
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
        return this._toMoment(info.date).format('[S] W');
    },

    _onCalendarEventOverlap: function(calendar, still, moving) {
        var overlaps = this._props.allowEventOverlaps;

        if (Object.isFunc(overlaps)) {
            var stillRange = new creme.CalendarEventRange({
                start: this._toMoment(still.start),
                end: this._toMoment(still.end),
                duration: calendar.getOption('defaultTimedEventDuration'),
                allDay: still.allDay
            });

            var movingRange = new creme.CalendarEventRange({
                start: this._toMoment(moving.start),
                end: this._toMoment(moving.end),
                duration: calendar.getOption('defaultTimedEventDuration'),
                allDay: moving.allDay
            });

            return overlaps({
                still: still,
                stillRange: stillRange,
                moving: moving,
                movingRange: movingRange,
                activityCalendar: this
            });
        } else {
            return overlaps || false;
        }
    },

    _setupCalendarHandlers: function(calendar) {
        var self = this;

        calendar.on('select', function(info) {
            if (self.allowEventCreate()) {
                self._onCalendarEventCreate(calendar, info);
            }
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

            self.trigger('range-select', {
                activityCalendar: self,
                view: info.view.type,
                start: self._toMoment(info.view.activeStart),
                end: self._toMoment(info.view.activeEnd),
                calEvent: info
            });
        });
        calendar.on('drop', function(info) {
            self._onCalendarExternalEventUpdate(calendar, info);
        });
        calendar.on('eventDrop', function(info) {
            self._onCalendarEventUpdate(calendar, info);
            self._postRenderCalendarEvent(calendar, info);
        });
    },

    _setupCalendarUi: function(element, options) {
        var self = this;
        var initialDate = options.initialDate ? moment(options.initialDate) : moment();
        var initialView = options.initialView || this.defaultView();

        var fullCalendarSettings = this._fullCalendarSettings = Object.assign(
            {}, FULLCALENDAR_SETTINGS, options.fullCalendarOptions || {}, {
                initialDate: initialDate.format('YYYY-MM-DD'),
                initialView: initialView,
                weekNumbers: options.showWeekNumber
            }
        );

        if (options.rendererDelay > 0) {
            /*
             * Improve rendering performance by limiting the rendering events
             * see https://github.com/fullcalendar/fullcalendar/issues/3003#issuecomment-2260733884
             */
            fullCalendarSettings.rerenderDelay = options.rendererDelay;
        }

        if (options.headlessMode) {
            fullCalendarSettings.header = false;
        }

        element.addClass('fc-creme');

        var calendar = this._calendar = new FullCalendar.Calendar(
            element.get(0),
            Object.assign({}, fullCalendarSettings, {
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

                    return true;
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

        element.data('fc-creme', calendar);

        calendar.addEventSource(function(info, successCb, failureCb) {
            self._onCalendarEventFetch(calendar, info, successCb, failureCb);
        });

        this._setupCalendarHandlers(calendar);

        calendar.render();
    }
});

}(jQuery));
