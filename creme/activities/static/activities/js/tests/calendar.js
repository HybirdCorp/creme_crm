/* globals FunctionFaker QUnitCalendarMixin */

(function($) {

QUnit.module("creme.ActivityCalendar", new QUnitMixin(QUnitEventMixin,
                                                      QUnitAjaxMixin,
                                                      QUnitDialogMixin,
                                                      QUnitMouseMixin,
                                                      QUnitCalendarMixin, {
    beforeEach: function() {
        var backend = this.backend;
        var fetchData = this.defaultCalendarFetchData();
        backend.options.enableUriSearch = true;

        this.setMockBackendGET({
            'mock/calendar/event/show': backend.response(200, ''),
            'mock/calendar/event/create': backend.response(200, '<form></form>'),

            'mock/calendar/events/empty': backend.responseJSON(200, []),
            'mock/calendar/events/fail': backend.responseJSON(400, 'Invalid calendar fetch'),
            'mock/calendar/events': function(url, data, options) {
                 return backend.responseJSON(200, fetchData.filter(function(item) {
                     var ids = data.calendar_id || [];
                     return ids.indexOf(item.calendar) !== -1;
                 }));
             }
        });

        this.setMockBackendPOST({
            'mock/calendar/event/update': backend.response(200, ''),
            'mock/calendar/event/update/400': backend.response(400, 'Unable to update calendar event'),
            'mock/calendar/event/update/403': backend.response(403, 'Unable to update calendar event'),
            'mock/calendar/event/update/409': backend.response(409, 'Unable to update calendar event'),
            'mock/calendar/event/create': backend.response(200, '')
        });
    }
}));

QUnit.test('creme.ActivityCalendar (empty)', function(assert) {
    var element = $('<div class="calendar"></div>').appendTo(this.qunitFixture());

    assert.equal(0, element.find('.fc-header').length);

    var controller = new creme.ActivityCalendar(element);

    assert.equal(1, element.find('.fc-header-toolbar').length, 'calendar header');

    assert.equal('', controller.owner());
    assert.equal('', controller.eventUpdateUrl());
    assert.equal('', controller.eventCreateUrl());
    assert.equal('', controller.eventFetchUrl());
    assert.equal(true, controller.allowEventOverlaps());
    assert.equal(true, controller.allowEventMove());
    assert.equal(true, controller.allowEventCreate());
    assert.equal(false, controller.headlessMode());
    assert.equal('month', controller.defaultView());
    assert.deepEqual({}, controller.fullCalendarOptions());

    assert.deepEqual([], controller.selectedSourceIds());
    assert.ok(controller.fullCalendar() instanceof FullCalendar.Calendar);
    assert.equal(element, controller.element());
    assert.equal(controller.fullCalendarView(), controller.fullCalendar().view);
});

QUnit.test('creme.ActivityCalendar (options)', function(assert) {
    var element = $('<div class="calendar"></div>').appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
        owner: 'myuser',
        allowEventOverlaps: false,
        allowEventMove: false,
        headlessMode: true,
        defaultView: 'week',
        eventUpdateUrl: 'mock/calendar/event/update',
        eventCreateUrl: 'mock/calendar/event/create',
        eventFetchUrl: 'mock/calendar/events',
        rendererDelay: 100,
        fullCalendarOptions: {
            slotDuration: '00:15:00'
        }
    });

    assert.equal('myuser', controller.owner());
    assert.equal('mock/calendar/event/update', controller.eventUpdateUrl());
    assert.equal('mock/calendar/event/create', controller.eventCreateUrl());
    assert.equal('mock/calendar/events', controller.eventFetchUrl());
    assert.equal(false, controller.allowEventOverlaps());
    assert.equal(false, controller.allowEventMove());
    assert.equal(true, controller.headlessMode());
    assert.equal('week', controller.defaultView());
    assert.deepEqual({
        slotDuration: '00:15:00'
    }, controller.fullCalendarOptions());

    assert.deepEqual([], controller.selectedSourceIds());
    assert.ok(controller.fullCalendar() instanceof FullCalendar.Calendar);
    assert.equal(element, controller.element());
    assert.equal(controller.fullCalendarView(), controller.fullCalendar().view);

    assert.deepEqual({
        owner: 'myuser',
        eventUpdateUrl: 'mock/calendar/event/update',
        eventCreateUrl: 'mock/calendar/event/create',
        eventFetchUrl: 'mock/calendar/events',
        allowEventOverlaps: false,
        allowEventMove: false,
        allowEventCreate: true,
        headlessMode: true,
        defaultView: 'week',
        externalEventData: _.noop,
        rendererDelay: 100,
        fullCalendarOptions: {
            slotDuration: '00:15:00'
        },
        showTimezoneInfo: false,
        showWeekNumber: true,
        timezoneOffset: 0
    }, controller.props());
});

QUnit.test('creme.ActivityCalendar (already bound)', function(assert) {
    var element = $('<div class="calendar"></div>').appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element);  // eslint-disable-line

    this.assertRaises(function() {
        return new creme.ActivityCalendar(element);
    }, Error, 'Error: creme.ActivityCalendar is already bound');
});

QUnit.test('creme.ActivityCalendar (fetch, empty url)', function(assert) {
    var element = $('<div class="calendar"></div>').appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
        selectedSourceIds: ['1', '2', '10', '11', '20']
    }).on('event-fetch', this.mockListener('event-fetch'));

    var view = controller.fullCalendar().view;

    assert.deepEqual(['1', '2', '10', '11', '20'].sort(), controller.selectedSourceIds().sort());
    assert.deepEqual([], this.mockBackendUrlCalls());
    assert.deepEqual([], this.mockListenerCalls('event-fetch'));

    controller.refetchEvents();

    assert.deepEqual([], this.mockBackendUrlCalls());
    assert.deepEqual([
        ['event-fetch', {
            activityCalendar: controller,
            activityRange: new creme.CalendarEventRange({
                start: controller._toMoment(view.activeStart),
                end: controller._toMoment(view.activeEnd)
            }),
            error: Error('Unable to send request with empty url'),
            items: [],
            ok: false
        }]
    ], this.mockListenerCalls('event-fetch'));
});

QUnit.test('creme.ActivityCalendar (fetch, empty data)', function(assert) {
    var element = $('<div class="calendar"></div>').appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
        eventFetchUrl: 'mock/calendar/events/empty',
        selectedSourceIds: ['1', '2', '10', '11', '20']
    }).on('event-fetch', this.mockListener('event-fetch'));

    var view = controller.fullCalendar().view;

    assert.deepEqual(['1', '2', '10', '11', '20'].sort(), controller.selectedSourceIds().sort());
    assert.deepEqual([[
        'mock/calendar/events/empty', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }
    ]], this.mockBackendUrlCalls());
    assert.deepEqual([], this.mockListenerCalls('event-fetch'));

    this.assertCalendarEvents(controller, []);
    this.assertClosedDialog();

    controller.refetchEvents();

    assert.deepEqual([
        ['event-fetch', {
            activityCalendar: controller,
            activityRange: new creme.CalendarEventRange({
                start: controller._toMoment(view.activeStart),
                end: controller._toMoment(view.activeEnd)
            }),
            items: [],
            ok: true
        }]
    ], this.mockListenerCalls('event-fetch'));
});

QUnit.test('creme.ActivityCalendar (fetch, invalid data)', function(assert) {
    var element = $('<div class="calendar"></div>').appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
        eventFetchUrl: 'mock/calendar/events/fail',
        selectedSourceIds: ['1', '2', '10', '11', '20']
    }).on('event-fetch', this.mockListener('event-fetch'));

    var view = controller.fullCalendar().view;

    assert.deepEqual(['1', '2', '10', '11', '20'].sort(), controller.selectedSourceIds().sort());
    assert.deepEqual([[
        'mock/calendar/events/fail', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }
    ]], this.mockBackendUrlCalls());

    this.assertCalendarEvents(controller, []);
    this.assertClosedDialog();

    controller.refetchEvents();

    assert.deepEqual([
        ['event-fetch', {
            activityCalendar: controller,
            activityRange: new creme.CalendarEventRange({
                start: controller._toMoment(view.activeStart),
                end: controller._toMoment(view.activeEnd)
            }),
            error: 'Invalid calendar fetch',
            items: [],
            ok: false
        }]
    ], this.mockListenerCalls('event-fetch'));
});

QUnit.parameterize('creme.ActivityCalendar (fetch)', [
    true, false
], function(allowEventMove, assert) {
    var element = $('<div class="calendar"></div>').appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
        eventFetchUrl: 'mock/calendar/events',
        initialDate: '2023-03-20',
        allowEventMove: allowEventMove,
        selectedSourceIds: ['1', '2', '10', '11', '20']
    }).on('event-fetch', this.mockListener('event-fetch'));

    var view = controller.fullCalendar().view;

    assert.deepEqual(['1', '2', '10', '11', '20'].sort(), controller.selectedSourceIds().sort());
    assert.deepEqual([[
        'mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            // 6 weeks from the one containing march 1st 2023
            start: '2023-02-27',
            end: '2023-04-10'
        }
    ]], this.mockBackendUrlCalls());
    this.assertCalendarEvents(controller, [{
            allDay: false,
            start: this.toISO8601(moment.utc('2023-03-25T08:00:00')),
            end: this.toISO8601(moment.utc('2023-03-25T09:00:00')),
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
            start: this.toISO8601(moment.utc('2023-03-25T09:00:00')),
            end: this.toISO8601(moment.utc('2023-03-25T10:00:00')),
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
            start: this.toISO8601(moment.utc('2023-03-25T10:30:00')),
            end: this.toISO8601(moment.utc('2023-03-25T12:00:00')),
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
            start: this.toISO8601(moment.utc('2023-03-26T14:30:00')),
            end: this.toISO8601(moment.utc('2023-03-26T14:45:00')),
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
            start: this.toISO8601(moment.utc('2023-03-26T16:30:00')),
            end: this.toISO8601(moment.utc('2023-03-26T18:00:00')),
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

    controller.refetchEvents();

    assert.deepEqual([
        ['event-fetch', {
            activityCalendar: controller,
            activityRange: new creme.CalendarEventRange({
                start: controller._toMoment(view.activeStart),
                end: controller._toMoment(view.activeEnd)
            }),
            items: this.defaultCalendarFetchData().map(function(item) {
                return Object.assign(item, {
                    textColor: new RGBColor(item.color).foreground().toString(),
                    editable: allowEventMove
                });
            }),
            ok: true
        }]
    ], this.mockListenerCalls('event-fetch'));

    // call rendering −> fetch again
    controller.redraw();

    assert.deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            // 6 weeks from the one containing march 1st 2023
            start: '2023-02-27',
            end: '2023-04-10'
        }],
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            // 6 weeks from the one containing march 1st 2023
            start: '2023-02-27',
            end: '2023-04-10'
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.ActivityCalendar.toggleSources', function(assert) {
    var controller = this.createDefaultCalendar({
        selectedSourceIds: []
    });
    var view = controller.fullCalendar().view;

    this.resetMockBackendCalls();

    controller.selectedSourceIds(['10']);

    assert.deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());

    controller.selectedSourceIds(['11', '10', '2']);

    assert.deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/events', 'GET', {
            calendar_id: ['11', '10', '2'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());

    controller.selectedSourceIds(['11']);

    // no query if only remove
    assert.deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/events', 'GET', {
            calendar_id: ['11', '10', '2'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());
});


QUnit.parameterize('creme.ActivityCalendar.rendering (month view)', [
    true, false
], function(allowEventMove, assert) {
    var element = $('<div class="calendar"></div>').appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events',
                         initialDate: '2023-03-20',
                         allowEventMove: allowEventMove,
                         selectedSourceIds: ['1', '2', '10', '11', '20']
                     });
    var view = controller.fullCalendar().view;
    var hex2rgb = function(color) {
        return $('<div style="color:${color};"></div>'.template({color: color})).css('color');
    };

    assert.equal(view.type, 'month');

    assert.deepEqual([{
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
    ], element.find('.fc-event').map(function() {
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
    var element = $('<div class="calendar"></div>').appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events',
                         initialDate: '2023-03-20',
                         timezoneOffset: offset,
                         selectedSourceIds: ['1', '2', '10', '11', '20']
                     });
    var view = controller.fullCalendar().view;

    assert.equal(view.type, 'month');
    assert.equal(controller.timezoneOffset(), offset);

    var now = controller.fullCalendar().getOption('now')();
    var expected = moment.utc().add(offset, 'm').milliseconds(0);

    assert.equal(now, expected.toISOString(true));
});

QUnit.parameterize('creme.ActivityCalendar.showTimezoneInfo (week view)', [
    [0, 'UTC+00:00'],
    [120, 'UTC+02:00'],
    [-120, 'UTC-02:00']
], function(offset, expectedTzinfo, assert) {
    var element = $('<div class="calendar"></div>').appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events',
                         timezoneOffset: offset,
                         showTimezoneInfo: true,
                         selectedSourceIds: ['1', '2', '10', '11', '20']
                     });

    controller.fullCalendarView('week', {});

    var view = controller.fullCalendar().view;

    assert.equal(view.type, 'week');
    assert.equal(controller.timezoneOffset(), offset);

    var now = controller.fullCalendar().getOption('now')();
    assert.equal(now, moment.utc().add(offset, 'm').milliseconds(0).toISOString(true));

    var indicator = element.find('.fc-timegrid-now-timezone:first');
    assert.equal(1, indicator.get().length);
    assert.equal(indicator.text(), expectedTzinfo);
});

QUnit.test('creme.ActivityCalendar.rendering (week view)', function(assert) {
    var element = $('<div class="calendar"></div>').appendTo(this.qunitFixture());

    var controller = new creme.ActivityCalendar(element, {
        eventFetchUrl: 'mock/calendar/events',
        initialDate: '2023-03-20',
        selectedSourceIds: ['1', '2', '10', '11', '20']
    });

    controller.fullCalendarView('week', {
        start: '2023-03-20'
    });

    var view = controller.fullCalendar().view;
    var hex2rgb = function(color) {
        return $('<div style="color:${color};"></div>'.template({color: color})).css('color');
    };

    assert.equal(view.type, 'week');
    assert.equal('${week} ${num}'.template({week: gettext('Week'), num: moment('2023-03-20').format('W')}),
          element.find('.fc-header-week').text());

    assert.deepEqual([{
            timestamp: '',
            title: "Event #20-3 (all day)",
            typename: '<div class="fc-event-type">Meeting</div>',
            color: hex2rgb('#fc0000'),
            isSmall: false,
            isSmaller: false,
            isBusy: false
        }, {
            timestamp: [this.todayAt({hours: 8}).format('H[h]mm'), this.todayAt({hours: 9}).format('H[h]mm')].join(' − '),
            title: "Event #1",
            typename: '<div class="fc-event-type fc-sticky">Call</div>',
            color: hex2rgb('#fcfcfc'),
            isSmall: false,
            isSmaller: false,
            isBusy: false
        }, {
            timestamp: [this.todayAt({hours: 9}).format('H[h]mm'), this.todayAt({hours: 10}).format('H[h]mm')].join(' − '),
            title: "Event #2",
            typename: '<div class="fc-event-type fc-sticky">Call</div>',
            color: hex2rgb('#fcfcfc'),
            isSmall: false,
            isSmaller: false,
            isBusy: true
        }, {
            timestamp: [this.todayAt({hours: 10, minutes: 30}).format('H[h]mm'), this.todayAt({hours: 12}).format('H[h]mm')].join(' − '),
            title: "Event #10-1",
            typename: '<div class="fc-event-type fc-sticky">Meeting</div>',
            color: hex2rgb('#fc00fc'),
            isSmall: false,
            isSmaller: false,
            isBusy: false
        }, {
            timestamp: this.todayAt({hours: 14, minutes: 30}).format('H[h]mm'),
            title: "Event #20-1 (small)",
            typename: '<div class="fc-event-type">Meeting</div>',
            color: hex2rgb('#fc0000'),
            isSmall: false,
            isSmaller: true,
            isBusy: false
        }, {
            timestamp: [this.todayAt({hours: 16, minutes: 30}).format('H[h]mm'), this.todayAt({hours: 18}).format('H[h]mm')].join(' − '),
            title: "Event #20-2",
            typename: '<div class="fc-event-type fc-sticky">Meeting</div>',
            color: hex2rgb('#fc0000'),
            isSmall: false,
            isSmaller: false,
            isBusy: false
        }
    ], element.find('.fc-event').map(function() {
        return {
            timestamp: $(this).find('.fc-event-time').text(),
            title: $(this).find('.fc-event-title').text(),
            typename: $(this).find('.fc-event-type').prop('outerHTML'),
            color: $(this).is('.fc-daygrid-dot-event') ? $(this).find('.fc-daygrid-event-dot').css('border-color') : $(this).css('background-color'),
            isSmall: $(this).find('.fc-small').length > 0,
            isSmaller: $(this).find('.fc-smaller').length > 0,
            isBusy: $(this).is('.fc-busy')
        };
    }).get());
});

QUnit.test('creme.ActivityCalendar.rendering (hilight, week view)', function(assert) {
    var element = $('<div class="calendar"></div>').appendTo(this.qunitFixture());
    var controller = new creme.ActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events',
                         initialDate: '2023-03-20',
                         selectedSourceIds: ['1', '2', '10', '11', '20'],
                         rendererDelay: 0
                     });

    controller.fullCalendar().changeView('week');

    var timeFormat = "H[h]mm";

    var eventStart = moment.utc('2023-03-25T08:00:00');
    var eventEnd = moment.utc('2023-03-25T09:45:00');

    assert.deepEqual([], element.find('.fc-event-mirror').get());

    controller.fullCalendar().select(eventStart.toDate(), eventEnd.toDate());

    assert.deepEqual([{
        content: '${start} − ${end}'.template({
            start: eventStart.format(timeFormat),
            end: eventEnd.format(timeFormat)
        })
    }], element.find('.fc-event-mirror .fc-event-time').map(function() {
        return {
            content: $(this).text()
        };
    }).get());
});

QUnit.test('creme.ActivityCalendar.create (not allowed, allDay)', function(assert) {
    var controller = this.createDefaultCalendar({
        selectedSourceIds: ['1', '2', '10', '11', '20'],
        allowEventCreate: false
    });
    var view = controller.fullCalendar().view;
    var today = this.todayAt();

    this.assertClosedDialog();

    controller.fullCalendar().select(today.format('YYYY-MM-DD'));

    this.assertClosedDialog();

    assert.deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.ActivityCalendar.create (canceled, allDay)', function(assert) {
    var controller = this.createDefaultCalendar({
        selectedSourceIds: ['1', '2', '10', '11', '20']
    });
    var view = controller.fullCalendar().view;
    var today = this.todayAt();

    this.assertClosedDialog();

    controller.fullCalendar().select(today.format('YYYY-MM-DD'));

    this.assertOpenedDialog();
    this.closeDialog();

    assert.deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
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
        selectedSourceIds: ['1', '2', '10', '11', '20']
    });
    var view = controller.fullCalendar().view;
    var today = this.todayAt();

    this.assertClosedDialog();

    controller.fullCalendar().select(today.format('YYYY-MM-DD'));

    this.assertOpenedDialog();

    assert.deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/create', 'GET', {
            start: today.format('YYYY-MM-DD'),
            end: today.format('YYYY-MM-DD'),
            allDay: 1
        }]
    ], this.mockBackendUrlCalls());

    this.submitFormDialog();

    assert.deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/create', 'GET', {
            start: today.format('YYYY-MM-DD'),
            end: today.format('YYYY-MM-DD'),
            allDay: 1
        }],
        ['mock/calendar/event/create', 'POST', {}]
        /* refetch behaviour has moved to the ActivityCalendarController
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
        */
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.ActivityCalendar.create (ok)', function(assert) {
    var controller = this.createDefaultCalendar({
        selectedSourceIds: ['1', '2', '10', '11', '20']
    });
    var view = controller.fullCalendar().view;
    var eventStart = this.todayAt({hours: 8});
    var eventEnd = eventStart.clone().add(controller.fullCalendar().defaultTimedEventDuration);

    this.assertClosedDialog();

    controller.fullCalendar().select(eventStart.format(), eventEnd.format());

    this.assertOpenedDialog();

    assert.deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/create', 'GET', {
            start: this.toISO8601(eventStart),
            end: this.toISO8601(eventEnd),
            allDay: 0
        }]
    ], this.mockBackendUrlCalls());

    this.submitFormDialog();

    assert.deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/create', 'GET', {
            start: this.toISO8601(eventStart),
            end: this.toISO8601(eventEnd),
            allDay: 0
        }],
        ['mock/calendar/event/create', 'POST', {}]
        /* refetch behaviour has moved to the ActivityCalendarController
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
        */
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.ActivityCalendar.show', function(assert) {
    var controller = this.createDefaultCalendar({
        initialDate: '2023-03-20',
        selectedSourceIds: ['1', '2', '10', '11', '20']
    });
    var view = controller.fullCalendar().view;
    var element = controller.element();

    this.assertClosedDialog();

    this.getItemByTitle(element, 'Event #10-1').find('.fc-event-title').trigger('click');

    this.assertOpenedDialog();
    assert.deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/show', 'GET', {
            id: '3'
        }]
    ], this.mockBackendUrlCalls());

    this.closeDialog();

    assert.deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/show', 'GET', {
            id: '3'
        }],
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.ActivityCalendar.eventDrop (ok)', function(assert) {
    var controller = this.createDefaultCalendar({
        selectedSourceIds: ['1', '2', '10', '11', '20'],
        initialDate: '2023-03-20'
    }).on('event-update', this.mockListener('event-update'));
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    controller.selectedSourceIds(['10']);

    var newEventStart = this.todayAt({hours: 15, minutes: 30}).add(1, 'days');
    var newEventEnd = this.todayAt({hours: 17}).add(1, 'days');

    assert.deepEqual([], this.mockBackendUrlCalls());

    this.simulateCalendarEventDrop(controller, {
        id: '3',
        start: newEventStart.toDate(),
        end: newEventEnd.toDate(),
        allDay: false,
        revert: revertCb
    });

    this.assertClosedDialog();

    // update query sent
    assert.deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: '3',
            allDay: false,
            start: this.toISO8601(newEventStart),
            end: this.toISO8601(newEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    assert.deepEqual([
        ['event-update', {
            activityCalendar: controller,
            activityRange: new creme.CalendarEventRange({
                start: controller._toMoment(newEventStart.toDate()),
                end: controller._toMoment(newEventEnd.toDate()),
                allDay: false
            })
        }]
    ], this.mockListenerCalls('event-update'));

    // revert not called, no pb
    assert.equal(0, fakeRevert.count());
});

QUnit.test('creme.ActivityCalendar.eventDrop (ok, from AllDay)', function(assert) {
    var controller = this.createDefaultCalendar({
        selectedSourceIds: ['1', '2', '10', '11', '20'],
        initialDate: '2023-03-20'
    }).on('event-update', this.mockListener('event-update'));
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    controller.selectedSourceIds(['10']);

    var newEventStart = this.todayAt({hours: 15, minutes: 30}).add(1, 'days');
    var newEventEnd = this.todayAt({hours: 16, minutes: 30}).add(1, 'days');

    assert.deepEqual([], this.mockBackendUrlCalls());

    this.simulateCalendarEventDrop(controller, {
        id: '3',
        start: newEventStart.toDate(),
        end: null,
        allDay: false,
        revert: revertCb
    });

    this.assertClosedDialog();

    // update query sent
    assert.deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: '3',
            allDay: false,
            start: this.toISO8601(newEventStart),
            end: this.toISO8601(newEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    assert.deepEqual([
        ['event-update', {
            activityCalendar: controller,
            activityRange: new creme.CalendarEventRange({
                start: controller._toMoment(newEventStart.toDate()),
                duration: '01:00:00',
                allDay: false
            })
        }]
    ], this.mockListenerCalls('event-update'));

    // revert not called, no pb
    assert.equal(0, fakeRevert.count());
});

QUnit.test('creme.ActivityCalendar.eventDrop (fail)', function(assert) {
    var controller = this.createDefaultCalendar({
        eventUpdateUrl: 'mock/calendar/event/update/400',
        selectedSourceIds: ['1', '2', '10', '11', '20'],
        initialDate: '2023-03-20'
    });
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    controller.selectedSourceIds(['10']);

    var newEventStart = this.todayAt({hours: 15, minutes: 30}).add(1, 'days');
    var newEventEnd = this.todayAt({hours: 17}).add(1, 'days');

    assert.deepEqual([], this.mockBackendUrlCalls());

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
    assert.equal(1, fakeRevert.count());

    assert.deepEqual([
        ['mock/calendar/event/update/400', 'POST', {
            id: '3',
            allDay: false,
            start: this.toISO8601(newEventStart),
            end: this.toISO8601(newEventEnd)
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

    assert.equal(2, fakeRevert.count());

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

    assert.equal(3, fakeRevert.count());
});

QUnit.test('creme.ActivityCalendar.eventResize (ok)', function(assert) {
    var controller = this.createDefaultCalendar({
        selectedSourceIds: ['10'],
        initialDate: '2023-03-20'
    }).on('event-update', this.mockListener('event-update'));
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    var eventStart = moment('2023-03-25T08:00:00');
    var newEventEnd = moment('2023-03-25T13:00:00');

    assert.deepEqual([], this.mockBackendUrlCalls());

    this.simulateCalendarEventResize(controller, {
        id: '3',
        start: eventStart.toDate(),
        end: newEventEnd.toDate(),
        allDay: false,
        revert: revertCb
    });

    this.assertClosedDialog();

    assert.deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: '3',
            allDay: false,
            start: this.toISO8601(eventStart),
            end: this.toISO8601(newEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    assert.equal(0, fakeRevert.count());

    assert.deepEqual([
        ['event-update', {
            activityCalendar: controller,
            activityRange: new creme.CalendarEventRange({
                start: controller._toMoment(eventStart.toDate()),
                end: controller._toMoment(newEventEnd.toDate()),
                allDay: false
            })
        }]
    ], this.mockListenerCalls('event-update'));
});

QUnit.test('creme.ActivityCalendar.eventResize (fail)', function(assert) {
    var controller = this.createDefaultCalendar({
        eventUpdateUrl: 'mock/calendar/event/update/400',
        selectedSourceIds: ['10'],
        initialDate: '2023-03-20'
    }).on('event-update', this.mockListener('event-update'));
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    var eventStart = moment('2023-03-25T08:00:00');
    var newEventEnd = moment('2023-03-25T13:00:00');

    assert.deepEqual([], this.mockBackendUrlCalls());

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
    assert.deepEqual([
        ['mock/calendar/event/update/400', 'POST', {
            id: '3',
            allDay: false,
            start: this.toISO8601(eventStart),
            end: this.toISO8601(newEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    assert.equal(1, fakeRevert.count());

    assert.deepEqual([], this.mockListenerCalls('event-update'));
});

QUnit.parameterize('creme.ActivityCalendar.allowEventOverlaps (bool)', [
    true, false
], function(expected, assert) {
    var controller = this.createDefaultCalendar({
        selectedSourceIds: ['1', '10'],
        initialDate: '2023-03-20',
        allowEventOverlaps: expected
    });

    var stillEventStart = this.todayAt({hours: 10}).add(1, 'days');
    var stillEventEnd = this.todayAt({hours: 12}).add(1, 'days');

    var movingEventStart = this.todayAt({hours: 10, minutes: 30}).add(1, 'days');
    var movingEventEnd = this.todayAt({hours: 13}).add(1, 'days');

    var result = this.simulateCalendarEventOverlap(controller, {
        still: {
            id: '1',
            start: stillEventStart.toDate(),
            end: stillEventEnd.toDate(),
            allDay: false
        },
        moving: {
            id: '3',
            start: movingEventStart.toDate(),
            end: movingEventEnd.toDate(),
            allDay: false
        }
    });

    assert.equal(result, expected);
});

QUnit.parameterize('creme.ActivityCalendar.allowEventOverlaps (function)', [
    true, false
], function(expected, assert) {
    var fakeOverlap = new FunctionFaker({result: expected});
    var overlapCb = fakeOverlap.wrap();

    var controller = this.createDefaultCalendar({
        selectedSourceIds: ['1', '10'],
        initialDate: '2023-03-20',
        allowEventOverlaps: overlapCb
    });

    var stillEventStart = this.todayAt({hours: 10}).add(1, 'days');
    var stillEventEnd = this.todayAt({hours: 12}).add(1, 'days');

    var movingEventStart = this.todayAt({hours: 10, minutes: 30}).add(1, 'days');
    var movingEventEnd = this.todayAt({hours: 13}).add(1, 'days');

    assert.equal(0, fakeOverlap.count());

    var result = this.simulateCalendarEventOverlap(controller, {
        still: {
            id: '1',
            start: stillEventStart.toDate(),
            end: stillEventEnd.toDate(),
            allDay: false
        },
        moving: {
            id: '3',
            start: movingEventStart.toDate(),
            end: movingEventEnd.toDate(),
            allDay: false
        }
    });

    assert.equal(result, expected);

    assert.deepEqual([
        {
            stillRange: new creme.CalendarEventRange({
                start: controller._toMoment(stillEventStart.toDate()),
                end: controller._toMoment(stillEventEnd.toDate()),
                allDay: false
            })
        }
    ], fakeOverlap.calls().map(function(args) {
        return _.pick(args[0], 'stillRange');
    }));
});

QUnit.test('creme.ActivityCalendar.settings (eventTimeFormat)', function(assert) {
    var controller = this.createDefaultCalendar();
    var format = controller.fullCalendar().getOption('eventTimeFormat');

    assert.equal(format({
        start: moment.utc('2025-07-10T08:00:00Z'),
        end: moment.utc('2025-07-10T09:15:30Z'),
        defaultSeparator: ' to ',
        timeZone: 'UTC',
        localeCodes: ['fr']
    }), '8h00 to 9h15');

    assert.equal(format({
        start: moment.utc('2025-07-10T08:00:00Z'),
        end: moment.utc('2025-07-11T09:15:30Z'),
        defaultSeparator: ' to ',
        timeZone: 'UTC',
        localeCodes: ['fr']
    }), '10/07 8h00 to 11/07 9h15');

    assert.equal(format({
        start: moment.utc('2025-07-10T00:00:00Z'),
        end: moment.utc('2025-07-11T00:00:00Z'),
        defaultSeparator: ' to ',
        timeZone: 'UTC',
        localeCodes: ['fr']
    }), '10/07');

    assert.equal(format({
        start: moment.utc('2025-07-10T00:00:00Z'),
        end: moment.utc('2025-07-11T00:00:01Z'),
        defaultSeparator: ' to ',
        timeZone: 'UTC',
        localeCodes: ['fr']
    }), '10/07 0h00 to 11/07 0h00');

    assert.equal(format({
        start: moment.utc('2025-07-10T00:00:00Z'),
        end: moment.utc('2025-07-12T00:00:00Z'),
        defaultSeparator: ' to ',
        timeZone: 'UTC',
        localeCodes: ['fr']
    }), '10/07 to 11/07');
});

QUnit.test('creme.ActivityCalendar.settings (slotLabelFormat)', function(assert) {
    var controller = this.createDefaultCalendar();
    var format = controller.fullCalendar().getOption('slotLabelFormat');

    assert.equal(format({
        start: moment.utc('2025-07-10T08:00:00Z'),
        end: moment.utc('2025-07-10T09:15:30Z'),
        defaultSeparator: ' to ',
        timeZone: 'UTC',
        localeCodes: ['fr']
    }), '8h00');

    assert.equal(format({
        start: moment.utc('1970-01-01T08:30:00Z'),
        defaultSeparator: ' to ',
        timeZone: 'UTC',
        localeCodes: ['fr']
    }), '8h30');
});

}(jQuery));
