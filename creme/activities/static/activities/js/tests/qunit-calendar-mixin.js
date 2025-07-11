(function($) {
"use strict";

var _CalEventInfo = function(options) {
    Object.assign(this, options);
};

_CalEventInfo.prototype = {
    setEnd: function(date) {
        this.end = date;
    }
};

window.QUnitCalendarMixin = {
    todayAt: function(options) {
        options = $.extend({hours: 0, minutes: 0, seconds: 0}, options || {});
        return moment(options);
    },

    toISO8601: function(value, allDay) {
        if (Object.isNone(value)) {
            return null;
        }

        return allDay ? moment(value).format('YYYY-MM-DD') : moment(value).utc().toISOString(true);
    },

    defaultCalendarFetchData: function() {
        return [{
                id: '1',
                title: 'Event #1',
                color: '#fcfcfc',
                start: '2023-03-25T08:00:00',
                end: '2023-03-25T09:00:00',
                calendar: '1',
                allDay: false,
                editable: true,
                url: 'mock/calendar/event/show?id=1',
                type: 'Call'
            }, {
                id: '2',
                title: 'Event #2',
                color: '#fcfcfc',
                start: '2023-03-25T09:00:00',
                end: '2023-03-25T10:00:00',
                calendar: '1',
                allDay: false,
                editable: true,
                url: 'mock/calendar/event/show?id=2',
                type: 'Call',
                busy: true
            }, {
                id: '3',
                title: 'Event #10-1',
                color: '#fc00fc',
                start: '2023-03-25T10:30:00',
                end: '2023-03-25T12:00:00',
                calendar: '10',
                allDay: false,
                editable: true,
                url: 'mock/calendar/event/show?id=3',
                type: 'Meeting'
            }, {
                id: '4',
                title: 'Event #20-1 (small)',
                color: '#fc0000',
                start: '2023-03-26T14:30:00',
                end: '2023-03-26T14:45:00',
                calendar: '20',
                allDay: false,
                editable: true,
                url: 'mock/calendar/event/show?id=4',
                type: 'Meeting'
            }, {
                id: '5',
                title: 'Event #20-2',
                color: '#fc0000',
                start: '2023-03-26T16:30:00',
                end: '2023-03-26T18:00:00',
                calendar: '20',
                allDay: false,
                editable: true,
                url: 'mock/calendar/event/show?id=5',
                type: 'Meeting'
            }, {
                id: '6',
                title: 'Event #20-3 (all day)',
                color: '#fc0000',
                start: '2023-03-23',
                calendar: '20',
                allDay: true,
                editable: true,
                url: 'mock/calendar/event/show?id=6',
                type: 'Meeting'
            }
        ];
    },

    createDefaultCalendar: function(options) {
        options = options || {};

        var html = '<div class="calendar"></div>';
        var element = $(html).appendTo(this.qunitFixture());

        var controller = new creme.ActivityCalendar(element, $.extend({
            owner: 'myuser',
            eventSelectUrl: 'mock/calendar/select',
            eventUpdateUrl: 'mock/calendar/event/update',
            eventCreateUrl: 'mock/calendar/event/create',
            eventFetchUrl: 'mock/calendar/events'
        }, options || {}));

        return controller;
    },

    assertCalendarEvents: function(controller, expected) {
        var toISO8601 = this.toISO8601;

        function sorted(a, b) {
            return a.id > b.id ? 1 : (a.id < b.id) ? -1 : 0;
        }

        this.assert.deepEqual(
            expected.sort(sorted),
            controller.fullCalendarEvents().map(function(event) {
                return {
                    allDay: event.allDay,
                    start: toISO8601(event.start, event.allDay),
                    end: toISO8601(event.end, event.allDay),
                    title: event.title,
                    props: {
                        calendar: event.extendedProps.calendar,
                        user: event.extendedProps.user,
                        type: event.extendedProps.type
                    },
                    backgroundColor: event.backgroundColor,
                    textColor: event.textColor,
                    id: event.id
                };
            }).sort(sorted)
        );
    },

    getItemByTitle: function(element, title) {
        return element.find('.fc-event').filter(function() {
            return $(this).find('.fc-event-title').text() === title;
        });
    },

    getItemByUrl: function(element, url) {
        return element.find('.fc-event').filter(function() {
            return $(this).attr('href') === url;
        });
    },

    simulateCalendarDrop: function(controller, options) {
        options = options || {};

        var calendar = controller.fullCalendar();
        var view = calendar.view;

        calendar.getCurrentData().emitter.trigger('drop', {
            id: options.id,
            draggedEl: options.source.get(0),
            date: options.date,
            allDay: options.allDay,
            jsEvent: $.Event('mouseup'),
            revert: options.revert || _.noop,
            view: view
        });
    },

    simulateCalendarEventDrop: function(controller, options) {
        options = options || {};

        var calendar = controller.fullCalendar();
        var view = calendar.view;
        var calEvent = calendar.getEventById(options.id);
        var item = this.getItemByTitle(controller.element(), calEvent.title);

        calendar.getCurrentData().emitter.trigger('eventDrop', {
            el: item.get(0),
            event: new _CalEventInfo({
                id: options.id,
                start: options.start,
                end: options.end,
                allDay: options.allDay,
                extendedProps: calEvent.extendedProps || {}
            }),
            jsEvent: $.Event('mouseup'),
            revert: options.revert || _.noop,
            view: view
        });
    },

    simulateCalendarEventResize: function(controller, options) {
        options = options || {};

        var calendar = controller.fullCalendar();
        var view = calendar.view;
        var calEvent = calendar.getEventById(options.id);
        var item = this.getItemByTitle(controller.element(), calEvent.title);

        calendar.getCurrentData().emitter.trigger('eventResize', {
            el: item.get(0),
            event: new _CalEventInfo({
                id: options.id,
                start: options.start,
                end: options.end,
                allDay: options.allDay,
                extendedProps: calEvent.extendedProps || {}
            }),
            jsEvent: $.Event('mouseup'),
            revert: options.revert || _.noop,
            view: view
        });
    },

    simulateCalendarEventOverlap: function(controller, options) {
        options = options || {};

        var calendar = controller.fullCalendar();
        var still = options.still || {};
        var moving = options.moving || {};

        var stillCalEvent = calendar.getEventById(still.id);
        var movingCalEvent = calendar.getEventById(moving.id);

        return calendar.getCurrentData().options['eventOverlap'](new _CalEventInfo({
            id: still.id,
            start: still.start,
            end: still.end,
            allDay: still.allDay,
            extendedProps: stillCalEvent.extendedProps || {}
        }), new _CalEventInfo({
            id: moving.id,
            start: moving.start,
            end: moving.end,
            allDay: moving.allDay,
            extendedProps: movingCalEvent.extendedProps || {}
        }));
    }
};

}(jQuery));
