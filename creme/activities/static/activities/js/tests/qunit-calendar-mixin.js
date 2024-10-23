(function($) {
"use strict";

function todayAt(options) {
    options = $.extend({hours: 0, minutes: 0, seconds: 0}, options || {});
    return moment(options);
};

/*
function todayUTCAt(options) {
    options = $.extend({hours: 0, minutes: 0, seconds: 0}, options || {});
    return moment.utc(options);
};
*/

function toISO8601(value, allDay) {
    if (Object.isNone(value)) {
        return null;
    }

    return allDay ? moment(value).format('YYYY-MM-DD') : moment(value).utc().toISOString(true);
}

function _defaultCalendarData() {
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
            type: 'Call'
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
};

window.QUnitCalendarViewMixin = {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendGET({
            'mock/calendar/event/show': backend.response(200, ''),
            'mock/calendar/event/floating': backend.response(200, ''),
            'mock/calendar/event/create': backend.response(200, '<form></form>'),

            'mock/calendar/events/empty': backend.responseJSON(200, []),
            'mock/calendar/events/fail': backend.responseJSON(400, 'Invalid calendar fetch'),
            'mock/calendar/events': function(url, data, options) {
                 return backend.responseJSON(200, _defaultCalendarData().filter(function(item) {
                     var ids = data.calendar_id || [];
                     return ids.indexOf(item.calendar) !== -1;
                 }));
             }
        });

        this.setMockBackendPOST({
            'mock/calendar/select': backend.response(200, ''),
            'mock/calendar/event/update': backend.response(200, ''),
            'mock/calendar/event/update/400': backend.response(400, 'Unable to update calendar event'),
            'mock/calendar/event/update/403': backend.response(403, 'Unable to update calendar event'),
            'mock/calendar/event/update/409': backend.response(409, 'Unable to update calendar event'),
            'mock/calendar/event/create': backend.response(200, '')
        });
    },

    toISO8601: toISO8601,
    todayAt: todayAt,

    createFloatingEventMenuItemHtml: function(item) {
        item = $.extend({
            color: '#c1d9ec',
            id: '1',
            calendar: '1',
            typename: 'Event',
            url: 'mock/calendar/event/floating?id=${id}',
            label: 'Floating Event #1'
        }, item || {});

        return (
            '<div class="floating-event" data-id="${id}" data-calendar="${calendar}" data-type="${typename}" data-popup_url="${url}" data-color="${color}">' +
                '<div class="colored-square" style="background-color:${color};"></div>' +
                '<span>${label}</span>' +
            '</div>'
        ).template($.extend({}, item, {
            url: item.url.template(item)
        }));
    },

    createCalendarMenuItemHtml: function(item) {
        item = $.extend({
            color: '#c1d9ec',
            id: '1',
            label: 'Calendar #1'
        }, item || {});

        return (
            '<div class="calendar-menu-item">' +
                '<div class="colored-square" style="background-color:${color};"></div>' +
                '<input type="checkbox" value="${id}" id="id_calendar_${id}" name="calendar_id" checked/>' +
                '<label for="id_calendar_${id}">${label}</label>' +
            '</div>'
        ).template(item);
    },

    createCalendarMenuGroupHtml: function(group) {
        return (
            '<div class="calendar-menu-usergroup" data-user="${owner}">' +
                '<h5 class="calendar-menu-usergroup-label">${label}</h5>' +
                '${items}' +
            '</div>'
        ).template({
            owner: group.owner || '',
            label: group.label || '',
            items: (group.items || []).map(this.createCalendarMenuItemHtml.bind(this)).join('')
        });
    },

    createCalendarViewHtml: function(options) {
        options = $.extend({
            mine: [],
            others: [],
            floating: []
        }, options || {});

        return (
            '<div class="calendar-main">' +
                '<div class="calendar-menu toggle-target">' +
                    '<div class="ui-creme-widget ui-creme-toggle widget-auto toggle-collapsed menu-group" widget="ui-creme-toggle">' +
                        '<h4 class="toggle-trigger menu-group-title">' +
                            '<span class="menu-group-label">Floating activities</span>' +
                        '</h4>' +
                        '<div class="floating-event-filter toggle-target"><input type="search" placeholder="FILTER FLOATING ACTIVITIES" /></div>' +
                        '<div class="floating-activities menu-sublist toggle-target">' +
                            '${floating}' +
                        '</div>' +
                    '</div>' +
                    '<div class="ui-creme-widget ui-creme-toggle widget-auto menu-group" widget="ui-creme-toggle">' +
                        '<h4 class="toggle-trigger menu-group-title">' +
                            '<span class="menu-group-label">My calendars</span>' +
                        '</h4>' +
                        '<div class="my-calendars menu-sublist toggle-target">' +
                            '${mine}' +
                        '</div>' +
                        '<hr/>' +
                    '</div>' +
                    '<div class="ui-creme-widget ui-creme-toggle widget-auto toggle-collapsed menu-group" widget="ui-creme-toggle">' +
                        '<h4 class="toggle-trigger menu-group-title">' +
                            '<span class="menu-group-label">Calendars of other people</span>' +
                        '</h4>' +
                        '<div class="calendar-menu-filter toggle-target"><input type="search" placeholder="FILTER CALENDARS OR COLLABORATORS" /></div>' +
                        '<div class="other-calendars menu-sublist toggle-target">' +
                            '${others}' +
                        '</div>' +
                    '</div>' +
                '</div>' +
                '<div class="calendar with_menu"></div>' +
            '</div>'
        ).template({
            mine: (options.mine || []).map(this.createCalendarMenuItemHtml.bind(this)).join(''),
            others: (options.others || []).map(this.createCalendarMenuGroupHtml.bind(this)).join(''),
            floating: (options.floating || []).map(this.createFloatingEventMenuItemHtml.bind(this)).join('')
        });
    },

    createDefaultCalendarViewHtml: function(options) {
        return this.createCalendarViewHtml($.extend({
            mine: [
                {id: '1', label: 'My calendar #1'},
                {id: '2', label: 'My calendar #2', color: '#ff00000'}
            ],
            others: [{
                    owner: 'jsnow',
                    label: 'Jon Snow',
                    items: [
                        {id: '10', label: 'A calendar #10', color: '#00ff00'},
                        {id: '11', label: 'A calendar #11', color: '#00ffff'}
                    ]
                }, {
                    owner: 'rsnow',
                    label: 'Ramsey Snow',
                    items: [
                        {id: '20', label: 'B calendar #20', color: '#ffff00'}
                    ]
                }
            ],
            floating: [
                {id: '51', label: 'Floating event #1', typename: 'Call', calendar: '1', color: '#ccffcc'},
                {id: '52', label: 'Floating call #2', typename: 'Event', calendar: '10', color: '#ffcccc'},
                {id: '53', label: 'Floating metting event #3', typename: 'Meeting', calendar: '10', color: '#ccccff'}
            ]
        }, options || {}));
    },

    createDefaultCalendarView: function(options) {
        options = options || {};

        var html = this.createDefaultCalendarViewHtml(options.html);
        var element = $(html).appendTo(this.qunitFixture());

        var controller = new creme.FullActivityCalendar(element, $.extend({
            owner: 'myuser',
            eventSelectUrl: 'mock/calendar/select',
            eventUpdateUrl: 'mock/calendar/event/update',
            eventCreateUrl: 'mock/calendar/event/create',
            eventFetchUrl: 'mock/calendar/events'
        }, options.options || {}));

        return controller;
    },

    /*
    getCalendarEventItemFootprint: function(item) {
        return $(item).data().fcSeg.footprint;
    },

    findCalendarEventItem: function(element, id) {
        var self = this;

        return element.find('.calendar .fc-event').filter(function() {
            return self.getCalendarEventItemFootprint(this).eventInstance.def.id === id;
        });
    },

    getCalendarEvents: function(element) {
        var self = this;
        return element.find('.calendar .fc-event').map(function() {
            var footprint = self.getCalendarEventItemFootprint(this);
            var event = footprint.eventInstance;
            var isAllDay = footprint.componentFootprint.isAllDay;

            if (event) {
                return {
                    title: event.def.title,
                    id: event.def.id,
                    calendar: event.def.miscProps.calendar,
                    start: event.dateProfile.start.toString(),
                    end: isAllDay ? null : event.dateProfile.end.toString(),
                    allDay: isAllDay || false
                };
            }
        }).get().sort(function(a, b) {
            return a.id > b.id ? 1 : (a.id < b.id) ? -1 : 0;
        });
    },

    simulateCalendarResize: function(controller, item, range) {
        var view = controller.fullCalendar().view;
        var event = this.getCalendarEventItemFootprint(item).eventInstance;

        view.reportEventResize(
            event,
            FullCalendar.EventDefMutation.createFromRawProps(event, {
                id: event.def.id,
                start: range.activeStart,
                end: range.activeEnd,
                className: []
            }),
            item,
            $.Event('mouseup')
        );
    },

    simulateCalendarExternalDragNDrop: function(controller, item, range) {
        var view = controller.fullCalendar().view;
        var singleEvent = FullCalendar.SingleEventDef.parse(
            range, new FullCalendar.EventSource(view.calendar)
        );

        view.reportExternalDrop(
            singleEvent, false, false, item, $.Event('mouseup')
        );
    },

    simulateCalendarDragNDrop: function(controller, item, range) {
        var view = controller.fullCalendar().view;
        var event = this.getCalendarEventItemFootprint(item).eventInstance;

        view.reportEventDrop(
            event,
            FullCalendar.EventDefMutation.createFromRawProps(event, {
                id: event.def.id,
                start: range.start,
                end: range.end,
                className: []
            }),
            item,
            $.Event('mouseup')
        );
    }
    */

    assertCalendarEvents: function(controller, expected) {
        function sorted(a, b) {
            return a.id > b.id ? 1 : (a.id < b.id) ? -1 : 0;
        }

        deepEqual(
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
            view: view
        });
    },

    simulateCalendarEventDrop: function(controller, options) {
        options = options || {};

        var calendar = controller.fullCalendar();
        var view = calendar.view;
        var event = calendar.getEventById(options.id);
        var item = this.getItemByTitle(controller.element(), event.title);

        calendar.getCurrentData().emitter.trigger('eventDrop', {
            el: item.get(0),
            event: {
                id: options.id,
                start: options.start,
                end: options.end,
                allDay: options.allDay
            },
            jsEvent: $.Event('mouseup'),
            revert: options.revert,
            view: view
        });
    },

    simulateCalendarEventResize: function(controller, options) {
        options = options || {};

        var calendar = controller.fullCalendar();
        var view = calendar.view;
        var event = calendar.getEventById(options.id);
        var item = this.getItemByTitle(controller.element(), event.title);

        calendar.getCurrentData().emitter.trigger('eventDrop', {
            el: item.get(0),
            event: {
                id: options.id,
                start: options.start,
                end: options.end,
                allDay: options.allDay
            },
            jsEvent: $.Event('mouseup'),
            revert: options.revert,
            view: view
        });
    }
};

}(jQuery));
