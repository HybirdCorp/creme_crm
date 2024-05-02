/* globals FunctionFaker */

(function($) {

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

QUnit.module("creme.ActivityCalendar", new QUnitMixin(QUnitEventMixin,
                                                      QUnitAjaxMixin,
                                                      QUnitDialogMixin,
                                                      QUnitMouseMixin, {
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

    createCalendarHtml: function(options) {
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

    createDefaultCalendarHtml: function(options) {
        return this.createCalendarHtml($.extend({
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

    createDefaultCalendar: function(options) {
        options = options || {};

        var html = this.createDefaultCalendarHtml(options.html);
        var element = $(html).appendTo(this.qunitFixture());

        var controller = new creme.ActivityCalendar(element, $.extend({
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
}));

QUnit.test('creme.ActivityCalendar (empty)', function(assert) {
    var element = $(this.createCalendarHtml()).appendTo(this.qunitFixture());

    equal(0, element.find('.calendar .fc-header').length);

    var controller = new creme.ActivityCalendar(element);

    equal(1, element.find('.calendar .fc-header-toolbar').length, 'calendar header');

    equal('', controller.owner());
    equal('', controller.eventSelectUrl());
    equal('', controller.eventUpdateUrl());
    equal('', controller.eventCreateUrl());
    equal('', controller.eventFetchUrl());

    deepEqual([], controller.visibleCalendarIds());
    ok(controller.fullCalendar() instanceof FullCalendar.Calendar);
    equal(element, controller.element());
});

QUnit.test('creme.ActivityCalendar (options)', function(assert) {
    var element = $(this.createCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
        owner: 'myuser',
        eventSelectUrl: 'mock/calendar/select',
        eventUpdateUrl: 'mock/calendar/event/update',
        eventCreateUrl: 'mock/calendar/event/create',
        eventFetchUrl: 'mock/calendar/events'
    });

    equal('myuser', controller.owner());
    equal('mock/calendar/select', controller.eventSelectUrl());
    equal('mock/calendar/event/update', controller.eventUpdateUrl());
    equal('mock/calendar/event/create', controller.eventCreateUrl());
    equal('mock/calendar/events', controller.eventFetchUrl());

    deepEqual([], controller.visibleCalendarIds());
    ok(controller.fullCalendar() instanceof FullCalendar.Calendar);
    equal(element, controller.element());
});

QUnit.test('creme.ActivityCalendar (already bound)', function(assert) {
    var element = $(this.createCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element);  // eslint-disable-line

    this.assertRaises(function() {
        return new creme.ActivityCalendar(element);
    }, Error, 'Error: CalendarController is already bound');
});

QUnit.test('creme.ActivityCalendar (no history)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element);

    equal(false, controller.keepState());

    deepEqual([], this.mockHistoryChanges());

    controller.goToDate('2023-03-20');

    deepEqual([], this.mockHistoryChanges());
});

QUnit.test('creme.ActivityCalendar (history)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
        keepState: true
    });

    var view = controller.fullCalendar().view;
    var initialStart = toISO8601(view.activeStart, true);

    equal(true, controller.keepState());

    deepEqual([
        ['push', '#view=month&date=' + initialStart, undefined]
    ], this.mockHistoryChanges());

    controller.goToDate('2023-03-20');

    deepEqual([
        ['push', '#view=month&date=' + initialStart, undefined],
        ['push', '#view=month&date=' + '2023-02-27', undefined]
    ], this.mockHistoryChanges());
});

QUnit.test('creme.ActivityCalendar (fetch, empty url)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element);

    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.visibleCalendarIds().sort());
    deepEqual([], this.mockBackendUrlCalls());
});

QUnit.test('creme.ActivityCalendar (fetch, empty data)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events/empty'
                     });
    var view = controller.fullCalendar().view;

    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.visibleCalendarIds().sort());
    deepEqual([[
        'mock/calendar/events/empty', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }
    ]], this.mockBackendUrlCalls());
    this.assertCalendarEvents(controller, []);

    this.assertClosedDialog();
});

QUnit.test('creme.ActivityCalendar (fetch, invalid data)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events/fail'
                     });
    var view = controller.fullCalendar().view;

    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.visibleCalendarIds().sort());
    deepEqual([[
        'mock/calendar/events/fail', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }
    ]], this.mockBackendUrlCalls());
    this.assertCalendarEvents(controller, []);

    this.assertClosedDialog();
});

QUnit.test('creme.ActivityCalendar (fetch)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events',
                         initialDate: '2023-03-20'
                     });
    controller.fullCalendar();

    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.visibleCalendarIds().sort());
    deepEqual([[
        'mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            // 6 weeks from the one containing march 1st 2023
            start: '2023-02-27',
            end: '2023-04-10'
        }
    ]], this.mockBackendUrlCalls());
    this.assertCalendarEvents(controller, [{
            allDay: false,
            start: toISO8601(moment.utc('2023-03-25T08:00:00')),
            end: toISO8601(moment.utc('2023-03-25T09:00:00')),
            title: "Event #1",
            props: {
                user: undefined,
                calendar: '1',
                type: 'Call'
            },
            backgroundColor: "#fcfcfc",
            textColor: new RGBColor("#fcfcfc").foreground().toString(),
            id: '1'
        }, {
            allDay: false,
            start: toISO8601(moment.utc('2023-03-25T09:00:00')),
            end: toISO8601(moment.utc('2023-03-25T10:00:00')),
            title: "Event #2",
            props: {
                user: undefined,
                calendar: '1',
                type: 'Call'
            },
            backgroundColor: "#fcfcfc",
            textColor: new RGBColor("#fcfcfc").foreground().toString(),
            id: '2'
        }, {
            allDay: false,
            start: toISO8601(moment.utc('2023-03-25T10:30:00')),
            end: toISO8601(moment.utc('2023-03-25T12:00:00')),
            title: "Event #10-1",
            props: {
                user: undefined,
                calendar: '10',
                type: 'Meeting'
            },
            backgroundColor: "#fc00fc",
            textColor: new RGBColor("#fc00fc").foreground().toString(),
            id: '3'
        }, {
            allDay: false,
            start: toISO8601(moment.utc('2023-03-26T14:30:00')),
            end: toISO8601(moment.utc('2023-03-26T14:45:00')),
            title: "Event #20-1 (small)",
            props: {
                user: undefined,
                calendar: '20',
                type: 'Meeting'
            },
            backgroundColor: "#fc0000",
            textColor: new RGBColor("#fc0000").foreground().toString(),
            id: '4'
        }, {
            allDay: false,
            start: toISO8601(moment.utc('2023-03-26T16:30:00')),
            end: toISO8601(moment.utc('2023-03-26T18:00:00')),
            title: "Event #20-2",
            props: {
                user: undefined,
                calendar: '20',
                type: 'Meeting'
            },
            backgroundColor: "#fc0000",
            textColor: new RGBColor("#fc0000").foreground().toString(),
            id: '5'
        }, {
            allDay: true,
            start: '2023-03-23',
            end: null,
            title: "Event #20-3 (all day)",
            props: {
                user: undefined,
                calendar: '20',
                type: 'Meeting'
            },
            backgroundColor: "#fc0000",
            textColor: new RGBColor("#fc0000").foreground().toString(),
            id: '6'
        }
    ]);
});

QUnit.parameterize('creme.ActivityCalendar.rendering (month view)', [
    true, false
], function(allowEventMove, assert) {
    var element = $(this.createDefaultCalendarHtml({
        options: {debounceDelay: 0}
    })).appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events',
                         initialDate: '2023-03-20',
                         allowEventMove: allowEventMove
                     });
    var view = controller.fullCalendar().view;
    var hex2rgb = function(color) {
        return $('<div style="color:${color};"></div>'.template({color: color})).css('color');
    };

    equal(view.type, 'month');

    deepEqual([{
            timestamp: '',
            title: "Event #20-3 (all day)",
            typename: '<div class="fc-event-type">Meeting</div>',
            color: hex2rgb('#fc0000'),
            isSmall: false,
            isEditable: allowEventMove
        }, {
            timestamp: '8h00',
            title: "Event #1",
            typename: '<div class="fc-event-type">Call</div>',
            color: hex2rgb('#fcfcfc'),
            isSmall: false,
            isEditable: allowEventMove
        }, {
            timestamp: '9h00',
            title: "Event #2",
            typename: '<div class="fc-event-type">Call</div>',
            color: hex2rgb('#fcfcfc'),
            isSmall: false,
            isEditable: allowEventMove
        }, {
            timestamp: '10h30',
            title: "Event #10-1",
            typename: '<div class="fc-event-type">Meeting</div>',
            color: hex2rgb('#fc00fc'),
            isSmall: false,
            isEditable: allowEventMove
        }, {
            timestamp: '14h30',
            title: "Event #20-1 (small)",
            typename: '<div class="fc-event-type">Meeting</div>',
            color: hex2rgb('#fc0000'),
            isSmall: false,
            isEditable: allowEventMove
        }, {
            timestamp: '16h30',
            title: "Event #20-2",
            typename: '<div class="fc-event-type">Meeting</div>',
            color: hex2rgb('#fc0000'),
            isSmall: false,
            isEditable: allowEventMove
        }
    ], element.find('.calendar .fc-event').map(function() {
        return {
            timestamp: $(this).find('.fc-event-time').text(),
            title: $(this).find('.fc-event-title').text(),
            typename: $(this).find('.fc-event-type').prop('outerHTML'),
            color: $(this).is('.fc-daygrid-dot-event') ? $(this).find('.fc-daygrid-event-dot').css('border-color') : $(this).css('background-color'),
            isSmall: $(this).find('.fc-small').length > 0,
            isEditable: $(this).is('.fc-event-draggable')
        };
    }).get());
});


QUnit.parameterize('creme.ActivityCalendar.timezoneOffset', [
    0, 120, -120
], function(offset, assert) {
    var element = $(this.createDefaultCalendarHtml({
        options: {debounceDelay: 0}
    })).appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events',
                         initialDate: '2023-03-20',
                         timezoneOffset: offset
                     });
    var view = controller.fullCalendar().view;

    equal(view.type, 'month');
    equal(controller.timezoneOffset(), offset);

    var now = controller.fullCalendar().getOption('now')();
    var expected = moment.utc().add(offset, 'm').milliseconds(0);

    equal(now, expected.toISOString(true));
});

// SWITCHING TO 'week' DO NOT WORK WITH FULLCALENDAR 5.x
// TODO : Find why !
/*
QUnit.test('creme.ActivityCalendar.rendering (week view)', function(assert) {
    var element = $(this.createDefaultCalendarHtml({
        options: {debounceDelay: 0}
    })).appendTo(this.qunitFixture());

    var controller = new creme.ActivityCalendar(element, {
                             eventFetchUrl: 'mock/calendar/events',
                         });

    controller.fullCalendarView('week', {
        start: '2023-03-20'
    });

    var view = controller.fullCalendar().view;
    var hex2rgb = function(color) {
        return $('<div style="color:${color};"></div>'.template({color: color})).css('color');
    };

    equal(view.type, 'week');
    equal('${week} ${num}'.template({week: gettext('Week'), num: todayAt().format('W')}),
          element.find('.fc-header-week').text());

    deepEqual([{
            timestamp: '',
            title: "Event #20-3 (all day)",
            typename: '<div class="fc-event-type">Meeting</div>',
            color: hex2rgb('#fc0000'),
            isSmall: false
        }, {
            timestamp: [todayAt({hours: 8}).format('H[h]mm'), todayAt({hours: 9}).format('H[h]mm')].join(' − '),
            title: "Event #1",
            typename: '<div class="fc-event-type">Call</div>',
            color: hex2rgb('#fcfcfc'),
            isSmall: false
        }, {
            timestamp: [todayAt({hours: 9}).format('H[h]mm'), todayAt({hours: 10}).format('H[h]mm')].join(' − '),
            title: "Event #2",
            typename: '<div class="fc-event-type">Call</div>',
            color: hex2rgb('#fcfcfc'),
            isSmall: false
        }, {
            timestamp: [todayAt({hours: 10, minutes: 30}).format('H[h]mm'), todayAt({hours: 12}).format('H[h]mm')].join(' − '),
            title: "Event #10-1",
            typename: '<div class="fc-event-type">Meeting</div>',
            color: hex2rgb('#fc00fc'),
            isSmall: false
        }, {
            timestamp: [todayAt({hours: 14, minutes: 30}).format('H[h]mm'), todayAt({hours: 14, minutes: 45}).format('H[h]mm')].join(' − '),
            title: "Event #20-1 (small)",
            typename: '<div class="fc-event-type">M.</div>',
            color: hex2rgb('#fc0000'),
            isSmall: true
        }, {
            timestamp: [todayAt({hours: 16, minutes: 30}).format('H[h]mm'), todayAt({hours: 18}).format('H[h]mm')].join(' − '),
            title: "Event #20-2",
            typename: '<div class="fc-event-type">Meeting</div>',
            color: hex2rgb('#fc0000'),
            isSmall: false
        }
    ], element.find('.calendar .fc-event').map(function() {
        return {
            timestamp: $(this).find('.fc-event-time').text(),
            title: $(this).find('.fc-event-title').text(),
            typename: $(this).find('.fc-event-type').prop('outerHTML'),
            color: $(this).is('.fc-daygrid-dot-event') ? $(this).find('.fc-daygrid-event-dot').css('border-color') : $(this).css('background-color'),
            isSmall: $(this).find('.fc-small').length > 0
        };
    }).get());
});
*/
/*
 * THIS FEATURE DO NOT WORK WITH FULLCALENDAR v4.x !!
 * TODO : see if we can reimplement it with rending hooks in v5+
 */
/*
QUnit.test('creme.ActivityCalendar.rendering (hilight, week view)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events'
                     });

    controller.fullCalendar().changeView('week');

    var timeFormat = "H[h]mm";

    var start = todayAt({hours: 8});
    var end = todayAt({hours: 9, minutes: 45});

    deepEqual([], element.find('.calendar .fc-highlight').get());

    controller.fullCalendar().select(start.toDate(), end.toDate());

    deepEqual([{
        content: '${start} − ${end}'.template({
            start: start.format(timeFormat),
            end: end.format(timeFormat)
        })
    }], element.find('.calendar .fc-highlight .fc-event-time').map(function() {
        return {
            content: $(this).text()
        };
    }).get());
});
*/

QUnit.test('creme.ActivityCalendar.visibleCalendarIds (selection)', function(assert) {
    var controller = this.createDefaultCalendar();
    var element = controller.element();
    var view = controller.fullCalendar().view;

    this.resetMockBackendCalls();

    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.visibleCalendarIds().sort());
    deepEqual([], this.mockBackendUrlCalls());

    // uncheck all => call update selection url
    element.find('.calendar-menu-item input').prop('checked', false).trigger('change');
    deepEqual([], controller.visibleCalendarIds().sort());
    deepEqual([
        ['mock/calendar/select', 'POST', {remove: '1'}],
        ['mock/calendar/select', 'POST', {remove: '2'}],
        ['mock/calendar/select', 'POST', {remove: '10'}],
        ['mock/calendar/select', 'POST', {remove: '11'}],
        ['mock/calendar/select', 'POST', {remove: '20'}]
    ], this.mockBackendUrlCalls());
    this.assertCalendarEvents(controller, []);

    this.resetMockBackendCalls();

    // check '10' => call update selection url
    element.find('.calendar-menu-item input[value="10"]').prop('checked', true).trigger('change');
    deepEqual(['10'], controller.visibleCalendarIds().sort());
    deepEqual([[
        'mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }
    ]], this.mockBackendUrlCalls());
    this.assertCalendarEvents(controller, [{
        allDay: false,
        start: toISO8601(moment.utc('2023-03-25T10:30:00')),
        end: toISO8601(moment.utc('2023-03-25T12:00:00')),
        props: {
            user: undefined,
            calendar: '10',
            type: 'Meeting'
        },
        backgroundColor: "#fc00fc",
        textColor: new RGBColor("#fc00fc").foreground().toString(),
        title: "Event #10-1",
        id: '3'
    }]);

    this.resetMockBackendCalls();

    // check '1' => call update selection url
    element.find('.calendar-menu-item input[value="1"]').prop('checked', true).trigger('change');
    deepEqual(['1', '10'].sort(), controller.visibleCalendarIds().sort());
    deepEqual([[
        'mock/calendar/events', 'GET', {
            calendar_id: ['1', '10'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }
    ]], this.mockBackendUrlCalls());

    this.assertCalendarEvents(controller, [{
        allDay: false,
        start: toISO8601(moment.utc('2023-03-25T08:00:00')),
        end: toISO8601(moment.utc('2023-03-25T09:00:00')),
        title: "Event #1",
        props: {
            user: undefined,
            calendar: '1',
            type: 'Call'
        },
        backgroundColor: "#fcfcfc",
        textColor: new RGBColor("#fcfcfc").foreground().toString(),
        id: '1'
    }, {
        allDay: false,
        start: toISO8601(moment.utc('2023-03-25T09:00:00')),
        end: toISO8601(moment.utc('2023-03-25T10:00:00')),
        title: "Event #2",
        props: {
            user: undefined,
            calendar: '1',
            type: 'Call'
        },
        backgroundColor: "#fcfcfc",
        textColor: new RGBColor("#fcfcfc").foreground().toString(),
        id: '2'
    }, {
        allDay: false,
        start: toISO8601(moment.utc('2023-03-25T10:30:00')),
        end: toISO8601(moment.utc('2023-03-25T12:00:00')),
        title: "Event #10-1",
        props: {
            user: undefined,
            calendar: '10',
            type: 'Meeting'
        },
        backgroundColor: "#fc00fc",
        textColor: new RGBColor("#fc00fc").foreground().toString(),
        id: '3'
    }]);
});

QUnit.test('creme.ActivityCalendar.filter (sidebar)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var element = controller.element();
    var input = element.find('.calendar-menu-filter input');
    var getval = function() { return $(this).val(); };
    var getlabel = function() { return $(this).text(); };

    equal('', input.val());
    deepEqual(
        ['1', '2', '10', '11', '20'].sort(),
        element.find('.calendar-menu-item:not(.hidden) input').map(getval).get().sort()
    );
    deepEqual(
        ['Jon Snow', 'Ramsey Snow'],
        element.find('.calendar-menu-usergroup-label:not(.hidden)').map(getlabel).get().sort()
    );

    // Matches "Jon Snow" group only
    input.val('jon').trigger($.Event("keyup", {keyCode: 13}));
    deepEqual(
        ['1', '2', '10', '11'].sort(),
        element.find('.calendar-menu-item:not(.hidden) input').map(getval).get().sort()
    );
    deepEqual(
        ['Jon Snow'],
        element.find('.calendar-menu-usergroup-label:not(.hidden)').map(getlabel).get().sort()
    );

    // Matches both "Jon Snow" & "Ramsey Snow" groups
    input.val('Snow').trigger($.Event("keyup", {keyCode: 13}));
    deepEqual(
        ['1', '2', '10', '11', '20'].sort(),
        element.find('.calendar-menu-item:not(.hidden) input').map(getval).get().sort()
    );
    deepEqual(
        ['Jon Snow', 'Ramsey Snow'],
        element.find('.calendar-menu-usergroup-label:not(.hidden)').map(getlabel).get().sort()
    );

    // Matches "A Calendar #10"
    input.val('#10').trigger($.Event("keyup", {keyCode: 13}));
    deepEqual(
        ['1', '2', '10'].sort(),
        element.find('.calendar-menu-item:not(.hidden) input').map(getval).get().sort()
    );
    deepEqual(
        ['Jon Snow'],
        element.find('.calendar-menu-usergroup-label:not(.hidden)').map(getlabel).get().sort()
    );

     // Matches "B Calendar #20"
    input.val('#20').trigger($.Event("keyup", {keyCode: 13}));
    deepEqual(
        ['1', '2', '20'].sort(),
        element.find('.calendar-menu-item:not(.hidden) input').map(getval).get().sort()
    );
    deepEqual(
        ['Ramsey Snow'],
        element.find('.calendar-menu-usergroup-label:not(.hidden)').map(getlabel).get().sort()
    );
});

QUnit.test('creme.ActivityCalendar.filter (floating events)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var element = controller.element();
    var input = element.find('.floating-event-filter input');
    var getid = function() { return $(this).attr('data-id'); };

    equal('', input.val());
    deepEqual(
        ['51', '52', '53'].sort(),
        element.find('.floating-event:not(.hidden)').map(getid).get().sort()
    );

    input.val('call').trigger($.Event("keyup", {keyCode: 13}));
    deepEqual(
        ['52'],
        element.find('.floating-event:not(.hidden)').map(getid).get()
    );

    input.val('event').trigger($.Event("keyup", {keyCode: 13}));
    deepEqual(
        ['51', '53'].sort(),
        element.find('.floating-event:not(.hidden)').map(getid).get().sort()
    );
});

QUnit.test('creme.ActivityCalendar.create (canceled, allDay)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var view = controller.fullCalendar().view;
    var today = todayAt();

    this.assertClosedDialog();

    controller.fullCalendar().select(today.format('YYYY-MM-DD'));

    this.assertOpenedDialog();
    this.closeDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/create', 'GET', {
            start: today.format('YYYY-MM-DD'),
            end: today.format('YYYY-MM-DD'),
            allDay: 1
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.ActivityCalendar.create (ok, allDay)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var view = controller.fullCalendar().view;
    var today = todayAt();

    this.assertClosedDialog();

    controller.fullCalendar().select(today.format('YYYY-MM-DD'));

    this.assertOpenedDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/create', 'GET', {
            start: today.format('YYYY-MM-DD'),
            end: today.format('YYYY-MM-DD'),
            allDay: 1
        }]
    ], this.mockBackendUrlCalls());

    this.submitFormDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/create', 'GET', {
            start: today.format('YYYY-MM-DD'),
            end: today.format('YYYY-MM-DD'),
            allDay: 1
        }],
        ['mock/calendar/event/create', 'POST', {}],
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.ActivityCalendar.create (ok)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var view = controller.fullCalendar().view;
    var eventStart = todayAt({hours: 8});
    var eventEnd = eventStart.clone().add(controller.fullCalendar().defaultTimedEventDuration);

    this.assertClosedDialog();

    controller.fullCalendar().select(eventStart.format(), eventEnd.format());

    this.assertOpenedDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/create', 'GET', {
            start: toISO8601(eventStart),
            end: toISO8601(eventEnd),
            allDay: 0
        }]
    ], this.mockBackendUrlCalls());

    this.submitFormDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/create', 'GET', {
            start: toISO8601(eventStart),
            end: toISO8601(eventEnd),
            allDay: 0
        }],
        ['mock/calendar/event/create', 'POST', {}],
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.ActivityCalendar.show', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {
            debounceDelay: 0,
            initialDate: '2023-03-20'
        }
    });
    var view = controller.fullCalendar().view;
    var element = controller.element();

    this.assertClosedDialog();

    this.getItemByTitle(element, 'Event #10-1').find('.fc-event-title').trigger('click');

    this.assertOpenedDialog();
    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/show', 'GET', {
            id: '3'
        }]
    ], this.mockBackendUrlCalls());

    this.closeDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/show', 'GET', {
            id: '3'
        }],
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.ActivityCalendar.eventDrop (ok)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var view = controller.fullCalendar().view;
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    controller.visibleCalendarIds(['10']);

    var newEventStart = todayAt({hours: 15, minutes: 30}).add(1, 'days');
    var newEventEnd = todayAt({hours: 17}).add(1, 'days');

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());

    this.simulateCalendarEventDrop(controller, {
        id: '3',
        start: newEventStart.toDate(),
        end: newEventEnd.toDate(),
        allDay: false,
        revert: revertCb
    });

    this.assertClosedDialog();

    // update query sent
    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/update', 'POST', {
            id: '3',
            allDay: false,
            start: toISO8601(newEventStart),
            end: toISO8601(newEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    // revert not called, no pb
    equal(0, fakeRevert.count());
});

QUnit.test('creme.ActivityCalendar.eventDrop (fail)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {
            debounceDelay: 0,
            eventUpdateUrl: 'mock/calendar/event/update/400'
        }
    });
    var view = controller.fullCalendar().view;
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    controller.visibleCalendarIds(['10']);

    var newEventStart = todayAt({hours: 15, minutes: 30}).add(1, 'days');
    var newEventEnd = todayAt({hours: 17}).add(1, 'days');

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());

    this.simulateCalendarEventDrop(controller, {
        id: '3',
        start: newEventStart.toDate(),
        end: newEventEnd.toDate(),
        allDay: false,
        revert: revertCb
    });

    this.assertOpenedDialog(gettext('Error, please reload the page.'));
    this.closeDialog();

    // Invalid update, call revert
    equal(1, fakeRevert.count());

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/update/400', 'POST', {
            id: '3',
            allDay: false,
            start: toISO8601(newEventStart),
            end: toISO8601(newEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    controller.eventUpdateUrl('mock/calendar/event/update/403');

    this.simulateCalendarEventDrop(controller, {
        id: '3',
        start: newEventStart.toDate(),
        end: newEventEnd.toDate(),
        allDay: false,
        revert: revertCb
    });

    this.assertOpenedDialog(gettext('You do not have permission, the change will not be saved.'));
    this.closeDialog();

    equal(2, fakeRevert.count());

    controller.eventUpdateUrl('mock/calendar/event/update/409');

    this.simulateCalendarEventDrop(controller, {
        id: '3',
        start: newEventStart.toDate(),
        end: newEventEnd.toDate(),
        allDay: false,
        revert: revertCb
    });

    this.assertOpenedDialog('Unable to update calendar event');
    this.closeDialog();

    equal(3, fakeRevert.count());
});

QUnit.test('creme.ActivityCalendar.resize (ok)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var view = controller.fullCalendar().view;
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    controller.visibleCalendarIds(['10']);

    var eventStart = todayAt({hours: 10, minutes: 30});
    var newEventEnd = todayAt({hours: 17});

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());

    this.simulateCalendarEventResize(controller, {
        id: '3',
        start: eventStart.toDate(),
        end: newEventEnd.toDate(),
        allDay: false,
        revert: revertCb
    });

    this.assertClosedDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/update', 'POST', {
            id: '3',
            allDay: false,
            start: toISO8601(eventStart),
            end: toISO8601(newEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    equal(0, fakeRevert.count());
});

QUnit.test('creme.ActivityCalendar.resize (fail)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {
            debounceDelay: 0,
            eventUpdateUrl: 'mock/calendar/event/update/400'
        }
    });
    var view = controller.fullCalendar().view;
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    controller.visibleCalendarIds(['10']);

    var eventStart = todayAt({hours: 10, minutes: 30});
    var newEventEnd = todayAt({hours: 17});

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());

    this.simulateCalendarEventResize(controller, {
        id: '3',
        start: eventStart.toDate(),
        end: newEventEnd.toDate(),
        allDay: false,
        revert: revertCb
    });

    this.assertOpenedDialog(gettext('Error, please reload the page.'));
    this.closeDialog();

    // Invalid update, call revert
    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: toISO8601(view.activeStart, true),
            end: toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/update/400', 'POST', {
            id: '3',
            allDay: false,
            start: toISO8601(eventStart),
            end: toISO8601(newEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    equal(1, fakeRevert.count());
});

QUnit.test('creme.ActivityCalendar.external (ok, allDay)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });

    var element = controller.element();

    controller.visibleCalendarIds(['10']);

    this.resetMockBackendCalls();

    deepEqual([], this.mockBackendUrlCalls());

    equal(false, element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group'));
    equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var dropDate = todayAt().add(1, 'days').utc();

    this.simulateCalendarDrop(controller, {
        source: dragSource,
        date: dropDate.toDate(),
        allDay: true
    });

    deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: 52,
            allDay: true,
            start: toISO8601(dropDate, true),
            end: toISO8601(dropDate, true)
        }]
    ], this.mockBackendUrlCalls());

    // floating event has been removed from menu
    equal(0, element.find('.floating-event[data-id="52"]').length);
    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(2, element.find('.floating-event').length);
});

QUnit.test('creme.ActivityCalendar.external (fail, allDay)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {
            debounceDelay: 0,
            eventUpdateUrl: 'mock/calendar/event/update/400'
        }
    });
    var element = controller.element();

    controller.visibleCalendarIds(['10']);

    this.resetMockBackendCalls();

    deepEqual([], this.mockBackendUrlCalls());

    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var dropDate = todayAt().add(1, 'days').utc();

    this.simulateCalendarDrop(controller, {
        source: dragSource,
        date: dropDate.toDate(),
        allDay: true
    });

    this.assertOpenedDialog(gettext('Error, please reload the page.'));
    this.closeDialog();

    deepEqual([
        ['mock/calendar/event/update/400', 'POST', {
            id: 52,
            allDay: true,
            start: toISO8601(dropDate, true),
            end: toISO8601(dropDate, true)
        }]
    ], this.mockBackendUrlCalls());

    // floating event remains in menu
    equal(1, element.find('.floating-event[data-id="52"]').length);
    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(3, element.find('.floating-event').length);
});

QUnit.test('creme.ActivityCalendar.external (ok, none remains, allDay)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0},
        html: {
            floating: [
                {id: '51', label: 'Floating event #1', typename: 'Call', calendar: '1', color: '#ccffcc'}
            ]
        }
    });
    var element = controller.element();

    controller.visibleCalendarIds(['10']);

    this.resetMockBackendCalls();

    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(1, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="51"]');
    var dropDate = todayAt().add(1, 'days').utc();

    this.simulateCalendarDrop(controller, {
        source: dragSource,
        date: dropDate.toDate(),
        allDay: true
    });

    deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: 51,
            allDay: true,
            start: toISO8601(dropDate, true),
            end: toISO8601(dropDate, true)
        }]
    ], this.mockBackendUrlCalls());

    // floating event has been removed from menu
    equal(0, element.find('.floating-event[data-id="51"]').length);
    equal(
        true,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(0, element.find('.floating-event').length);
});

// SWITCHING TO 'week' DO NOT WORK WITH FULLCALENDAR 5.x
// TODO : Find why !
/*
QUnit.test('creme.ActivityCalendar.external (ok, hour)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var element = controller.element();

    controller.visibleCalendarIds(['10']);
    controller.fullCalendar().changeView('week');

    this.resetMockBackendCalls();

    deepEqual([], this.mockBackendUrlCalls());

    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var dropEventStart = todayAt({hours: 8}).add(1, 'days');
    var dropEventEnd = dropEventStart.clone().add(moment.duration(
        controller.fullCalendar().getOption('defaultTimedEventDuration')
    ));

    this.simulateCalendarDrop(controller, {
        source: dragSource,
        date: dropEventStart.toDate(),
        allDay: false
    });

    deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: 52,
            allDay: false,
            start: dropEventStart.format(),
            end: dropEventEnd.format()
        }]
    ], this.mockBackendUrlCalls());

    // floating event has been removed from menu
    equal(0, element.find('.floating-event[data-id="52"]').length);
    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(2, element.find('.floating-event').length);
});

QUnit.test('creme.ActivityCalendar.external (fail, hour)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {
            debounceDelay: 0,
            eventUpdateUrl: 'mock/calendar/event/update/400'
        }
    });
    var element = controller.element();

    controller.visibleCalendarIds(['10']);
    controller.fullCalendar().changeView('week');

    this.resetMockBackendCalls();

    deepEqual([], this.mockBackendUrlCalls());

    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var dropEventStart = todayAt({hours: 8}).add(1, 'days');
    var dropEventEnd = dropEventStart.clone().add(moment.duration(
        controller.fullCalendar().getOption('defaultTimedEventDuration')
    ));

    this.simulateCalendarDrop(controller, {
        source: dragSource,
        date: dropEventStart.toDate(),
        allDay: false
    });

    this.assertOpenedDialog(gettext('Error, please reload the page.'));
    this.closeDialog();

    deepEqual([
        ['mock/calendar/event/update/400', 'POST', {
            id: 52,
            allDay: false,
            start: dropEventStart.format(),
            end: dropEventEnd.format()
        }]
    ], this.mockBackendUrlCalls());

    // floating event remains in menu
    equal(1, element.find('.floating-event[data-id="52"]').length);
    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(3, element.find('.floating-event').length);
});

QUnit.test('creme.ActivityCalendar.external (ok, none remains, hour)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0},
        html: {
            floating: [
                {id: '51', label: 'Floating event #1', typename: 'Call', calendar: '1', color: '#ccffcc'}
            ]
        }
    });
    var element = controller.element();

    controller.visibleCalendarIds(['10']);
    controller.fullCalendar().changeView('week');

    this.resetMockBackendCalls();

    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(1, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="51"]');
    var dropEventStart = todayAt({hours: 8}).add(1, 'days');
    var dropEventEnd = dropEventStart.clone().add(moment.duration(
        controller.fullCalendar().getOption('defaultTimedEventDuration')
    ));

    this.simulateCalendarDrop(controller, {
        source: dragSource,
        date: dropEventStart.toDate(),
        allDay: false
    });

    deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: 51,
            allDay: false,
            start: dropEventStart.format(),
            end: dropEventEnd.format()
        }]
    ], this.mockBackendUrlCalls());

    // floating event has been removed from menu
    equal(0, element.find('.floating-event[data-id="51"]').length);
    equal(
        true,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(0, element.find('.floating-event').length);
});
*/
}(jQuery));
