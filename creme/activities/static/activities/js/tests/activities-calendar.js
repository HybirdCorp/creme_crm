/* globals FunctionFaker QUnitCalendarViewMixin */

(function($) {
"use strict";

QUnit.module("creme.FullActivityCalendar", new QUnitMixin(QUnitEventMixin,
                                                          QUnitAjaxMixin,
                                                          QUnitDialogMixin,
                                                          QUnitMouseMixin,
                                                          QUnitCalendarViewMixin));

QUnit.test('creme.FullActivityCalendar (empty)', function(assert) {
    var element = $(this.createCalendarViewHtml()).appendTo(this.qunitFixture());

    equal(0, element.find('.calendar .fc-header').length);

    var controller = new creme.FullActivityCalendar(element);

    equal(1, element.find('.calendar .fc-header-toolbar').length, 'calendar header');

    equal('', controller.owner());
    equal('', controller.calendar().eventSelectUrl(), 'select url');
    equal('', controller.calendar().eventUpdateUrl(), 'update url');
    equal('', controller.calendar().eventCreateUrl(), 'create url');
    equal('', controller.calendar().eventFetchUrl(), 'fetch url');

    deepEqual([], controller.selectedSourceIds());
    ok(controller.calendar().fullCalendar() instanceof FullCalendar.Calendar);
    equal(element, controller.element());
});

QUnit.test('creme.FullActivityCalendar (options)', function(assert) {
    var element = $(this.createCalendarViewHtml()).appendTo(this.qunitFixture());
    var controller = new creme.FullActivityCalendar(element, {
        owner: 'myuser',
        eventSelectUrl: 'mock/calendar/select',
        eventUpdateUrl: 'mock/calendar/event/update',
        eventCreateUrl: 'mock/calendar/event/create',
        eventFetchUrl: 'mock/calendar/events'
    });

    equal('myuser', controller.owner());
    equal('mock/calendar/select', controller.calendar().eventSelectUrl());
    equal('mock/calendar/event/update', controller.calendar().eventUpdateUrl());
    equal('mock/calendar/event/create', controller.calendar().eventCreateUrl());
    equal('mock/calendar/events', controller.calendar().eventFetchUrl());

    deepEqual([], controller.selectedSourceIds());
    ok(controller.calendar().fullCalendar() instanceof FullCalendar.Calendar);
    equal(element, controller.element());
});

QUnit.test('creme.FullActivityCalendar (already bound)', function(assert) {
    var element = $(this.createCalendarViewHtml()).appendTo(this.qunitFixture());
    var controller = new creme.FullActivityCalendar(element);  // eslint-disable-line

    this.assertRaises(function() {
        return new creme.FullActivityCalendar(element);
    }, Error, 'Error: An ActivityCalendar instance is already bound');
});

QUnit.test('creme.FullActivityCalendar (no history)', function(assert) {
    var element = $(this.createDefaultCalendarViewHtml()).appendTo(this.qunitFixture());
    var controller = new creme.FullActivityCalendar(element);

    equal(false, controller.calendar().keepState());

    deepEqual([], this.mockHistoryChanges());

    controller.goToDate('2023-03-20');

    deepEqual([], this.mockHistoryChanges());
});

QUnit.test('creme.FullActivityCalendar (history)', function(assert) {
    var element = $(this.createDefaultCalendarViewHtml()).appendTo(this.qunitFixture());
    var controller = new creme.FullActivityCalendar(element, {
        keepState: true
    });

    var view = controller.calendar().fullCalendar().view;
    var initialStart = this.toISO8601(view.activeStart, true);

    equal(true, controller.calendar().keepState());

    deepEqual([
        ['push', '#view=month&date=' + initialStart, undefined]
    ], this.mockHistoryChanges());

    controller.goToDate('2023-03-20');

    deepEqual([
        ['push', '#view=month&date=' + initialStart, undefined],
        ['push', '#view=month&date=' + '2023-02-27', undefined]
    ], this.mockHistoryChanges());
});

QUnit.test('creme.FullActivityCalendar (fetch, empty url)', function(assert) {
    var element = $(this.createDefaultCalendarViewHtml()).appendTo(this.qunitFixture());
    var controller = new creme.FullActivityCalendar(element);

    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.selectedSourceIds().sort());
    deepEqual([], this.mockBackendUrlCalls());
});

QUnit.test('creme.FullActivityCalendar (fetch, empty data)', function(assert) {
    var element = $(this.createDefaultCalendarViewHtml()).appendTo(this.qunitFixture());
    var controller = new creme.FullActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events/empty'
                     });
    var view = controller.calendar().fullCalendar().view;

    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.selectedSourceIds().sort());
    deepEqual([[
        'mock/calendar/events/empty', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }
    ]], this.mockBackendUrlCalls());
    this.assertCalendarEvents(controller.calendar(), []);

    this.assertClosedDialog();
});

QUnit.test('creme.FullActivityCalendar (fetch, invalid data)', function(assert) {
    var element = $(this.createDefaultCalendarViewHtml()).appendTo(this.qunitFixture());
    var controller = new creme.FullActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events/fail'
                     });
    var view = controller.calendar().fullCalendar().view;

    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.selectedSourceIds().sort());
    deepEqual([[
        'mock/calendar/events/fail', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }
    ]], this.mockBackendUrlCalls());
    this.assertCalendarEvents(controller.calendar(), []);

    this.assertClosedDialog();
});

QUnit.test('creme.FullActivityCalendar (fetch)', function(assert) {
    var element = $(this.createDefaultCalendarViewHtml()).appendTo(this.qunitFixture());
    var controller = new creme.FullActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events',
                         initialDate: '2023-03-20'
                     });
    controller.calendar().fullCalendar();

    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.selectedSourceIds().sort());
    deepEqual([[
        'mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            // 6 weeks from the one containing march 1st 2023
            start: '2023-02-27',
            end: '2023-04-10'
        }
    ]], this.mockBackendUrlCalls());
    this.assertCalendarEvents(controller.calendar(), [{
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
});

QUnit.parameterize('creme.FullActivityCalendar.rendering (month view)', [
    true, false
], function(allowEventMove, assert) {
    var element = $(this.createDefaultCalendarViewHtml({
        options: {debounceDelay: 0}
    })).appendTo(this.qunitFixture());
    var controller = new creme.FullActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events',
                         initialDate: '2023-03-20',
                         allowEventMove: allowEventMove
                     });
    var view = controller.calendar().fullCalendar().view;
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

QUnit.parameterize('creme.FullActivityCalendar.timezoneOffset', [
    0, 120, -120
], function(offset, assert) {
    var element = $(this.createDefaultCalendarViewHtml({
        options: {debounceDelay: 0}
    })).appendTo(this.qunitFixture());
    var controller = new creme.FullActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events',
                         initialDate: '2023-03-20',
                         timezoneOffset: offset
                     });
    var view = controller.calendar().fullCalendar().view;

    equal(view.type, 'month');
    equal(controller.calendar().timezoneOffset(), offset);

    var now = controller.calendar().fullCalendar().getOption('now')();
    var expected = moment.utc().add(offset, 'm').milliseconds(0);

    equal(now, expected.toISOString(true));
});

// SWITCHING TO 'week' DO NOT WORK WITH FULLCALENDAR 5.x
// TODO : Find why !
/*
QUnit.test('creme.FullActivityCalendar.rendering (week view)', function(assert) {
    var element = $(this.createDefaultCalendarViewHtml({
        options: {debounceDelay: 0}
    })).appendTo(this.qunitFixture());

    var controller = new creme.FullActivityCalendar(element, {
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
    equal('${week} ${num}'.template({week: gettext('Week'), num: this.todayAt().format('W')}),
          element.find('.fc-header-week').text());

    deepEqual([{
            timestamp: '',
            title: "Event #20-3 (all day)",
            typename: '<div class="fc-event-type">Meeting</div>',
            color: hex2rgb('#fc0000'),
            isSmall: false
        }, {
            timestamp: [this.todayAt({hours: 8}).format('H[h]mm'), this.todayAt({hours: 9}).format('H[h]mm')].join(' − '),
            title: "Event #1",
            typename: '<div class="fc-event-type">Call</div>',
            color: hex2rgb('#fcfcfc'),
            isSmall: false
        }, {
            timestamp: [this.todayAt({hours: 9}).format('H[h]mm'), this.todayAt({hours: 10}).format('H[h]mm')].join(' − '),
            title: "Event #2",
            typename: '<div class="fc-event-type">Call</div>',
            color: hex2rgb('#fcfcfc'),
            isSmall: false
        }, {
            timestamp: [this.todayAt({hours: 10, minutes: 30}).format('H[h]mm'), this.todayAt({hours: 12}).format('H[h]mm')].join(' − '),
            title: "Event #10-1",
            typename: '<div class="fc-event-type">Meeting</div>',
            color: hex2rgb('#fc00fc'),
            isSmall: false
        }, {
            timestamp: [this.todayAt({hours: 14, minutes: 30}).format('H[h]mm'), this.todayAt({hours: 14, minutes: 45}).format('H[h]mm')].join(' − '),
            title: "Event #20-1 (small)",
            typename: '<div class="fc-event-type">M.</div>',
            color: hex2rgb('#fc0000'),
            isSmall: true
        }, {
            timestamp: [this.todayAt({hours: 16, minutes: 30}).format('H[h]mm'), this.todayAt({hours: 18}).format('H[h]mm')].join(' − '),
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
QUnit.test('creme.FullActivityCalendar.rendering (hilight, week view)', function(assert) {
    var element = $(this.createDefaultCalendarViewHtml()).appendTo(this.qunitFixture());
    var controller = new creme.FullActivityCalendar(element, {
                         eventFetchUrl: 'mock/calendar/events'
                     });

    controller.fullCalendar().changeView('week');

    var timeFormat = "H[h]mm";

    var start = this.todayAt({hours: 8});
    var end = this.todayAt({hours: 9, minutes: 45});

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

QUnit.test('creme.FullActivityCalendar.selectedSourceIds (selection)', function(assert) {
    var controller = this.createDefaultCalendarView();
    var element = controller.element();
    var view = controller.calendar().fullCalendar().view;

    this.resetMockBackendCalls();

    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.selectedSourceIds().sort());
    deepEqual([], this.mockBackendUrlCalls());

    // uncheck all => call update selection url
    element.find('.calendar-menu-item input').prop('checked', false).trigger('change');
    deepEqual([], controller.selectedSourceIds().sort());
    deepEqual([
        ['mock/calendar/select', 'POST', {remove: '1'}],
        ['mock/calendar/select', 'POST', {remove: '2'}],
        ['mock/calendar/select', 'POST', {remove: '10'}],
        ['mock/calendar/select', 'POST', {remove: '11'}],
        ['mock/calendar/select', 'POST', {remove: '20'}]
    ], this.mockBackendUrlCalls());
    this.assertCalendarEvents(controller.calendar(), []);

    this.resetMockBackendCalls();

    // check '10' => call update selection url
    element.find('.calendar-menu-item input[value="10"]').prop('checked', true).trigger('change');
    deepEqual(['10'], controller.selectedSourceIds().sort());
    deepEqual([[
        'mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }
    ]], this.mockBackendUrlCalls());
    this.assertCalendarEvents(controller, [{
        allDay: false,
        start: this.toISO8601(moment.utc('2023-03-25T10:30:00')),
        end: this.toISO8601(moment.utc('2023-03-25T12:00:00')),
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
    deepEqual(['1', '10'].sort(), controller.selectedSourceIds().sort());
    deepEqual([[
        'mock/calendar/events', 'GET', {
            calendar_id: ['1', '10'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
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
    }]);
});

QUnit.test('creme.FullActivityCalendar.filter (sidebar)', function(assert) {
    var controller = this.createDefaultCalendarView({
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

QUnit.test('creme.FullActivityCalendar.filter (floating events)', function(assert) {
    var controller = this.createDefaultCalendarView({
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

QUnit.test('creme.FullActivityCalendar.create (canceled, allDay)', function(assert) {
    var controller = this.createDefaultCalendarView({
        options: {debounceDelay: 0}
    });
    var view = controller.calendar().fullCalendar().view;
    var today = this.todayAt();

    this.assertClosedDialog();

    controller.calendar().fullCalendar().select(today.format('YYYY-MM-DD'));

    this.assertOpenedDialog();
    this.closeDialog();

    deepEqual([
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

QUnit.test('creme.FullActivityCalendar.create (ok, allDay)', function(assert) {
    var controller = this.createDefaultCalendarView({
        options: {debounceDelay: 0}
    });
    var view = controller.calendar().fullCalendar().view;
    var today = this.todayAt();

    this.assertClosedDialog();

    controller.calendar().fullCalendar().select(today.format('YYYY-MM-DD'));

    this.assertOpenedDialog();

    deepEqual([
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

    deepEqual([
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
        ['mock/calendar/event/create', 'POST', {}],
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.FullActivityCalendar.create (ok)', function(assert) {
    var controller = this.createDefaultCalendarView({
        options: {debounceDelay: 0}
    });
    var view = controller.calendar().fullCalendar().view;
    var eventStart = this.todayAt({hours: 8});
    var eventEnd = eventStart.clone().add(controller.calendar().fullCalendar().defaultTimedEventDuration);

    this.assertClosedDialog();

    controller.calendar().fullCalendar().select(eventStart.format(), eventEnd.format());

    this.assertOpenedDialog();

    deepEqual([
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

    deepEqual([
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
        ['mock/calendar/event/create', 'POST', {}],
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.FullActivityCalendar.show', function(assert) {
    var controller = this.createDefaultCalendarView({
        options: {
            debounceDelay: 0,
            initialDate: '2023-03-20'
        }
    });
    var view = controller.calendar().fullCalendar().view;
    var element = controller.element();

    this.assertClosedDialog();

    this.getItemByTitle(element, 'Event #10-1').find('.fc-event-title').trigger('click');

    this.assertOpenedDialog();
    deepEqual([
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

    deepEqual([
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

QUnit.test('creme.FullActivityCalendar.eventDrop (ok)', function(assert) {
    var controller = this.createDefaultCalendarView({
        options: {debounceDelay: 0}
    });
    var view = controller.calendar().fullCalendar().view;
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    controller.selectSource('10');

    var newEventStart = this.todayAt({hours: 15, minutes: 30}).add(1, 'days');
    var newEventEnd = this.todayAt({hours: 17}).add(1, 'days');

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());

    this.simulateCalendarEventDrop(controller.calendar(), {
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
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/update', 'POST', {
            id: '3',
            allDay: false,
            start: this.toISO8601(newEventStart),
            end: this.toISO8601(newEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    // revert not called, no pb
    equal(0, fakeRevert.count());
});

QUnit.test('creme.FullActivityCalendar.eventDrop (fail)', function(assert) {
    var controller = this.createDefaultCalendarView({
        options: {
            debounceDelay: 0,
            eventUpdateUrl: 'mock/calendar/event/update/400'
        }
    });
    var view = controller.calendar().fullCalendar().view;
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    controller.selectSource('10');

    var newEventStart = this.todayAt({hours: 15, minutes: 30}).add(1, 'days');
    var newEventEnd = this.todayAt({hours: 17}).add(1, 'days');

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());

    this.simulateCalendarEventDrop(controller.calendar(), {
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
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/update/400', 'POST', {
            id: '3',
            allDay: false,
            start: this.toISO8601(newEventStart),
            end: this.toISO8601(newEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    controller.calendar().eventUpdateUrl('mock/calendar/event/update/403');

    this.simulateCalendarEventDrop(controller.calendar(), {
        id: '3',
        start: newEventStart.toDate(),
        end: newEventEnd.toDate(),
        allDay: false,
        revert: revertCb
    });

    this.assertOpenedDialog(gettext('You do not have permission, the change will not be saved.'));
    this.closeDialog();

    equal(2, fakeRevert.count());

    controller.calendar().eventUpdateUrl('mock/calendar/event/update/409');

    this.simulateCalendarEventDrop(controller.calendar(), {
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

QUnit.test('creme.FullActivityCalendar.resize (ok)', function(assert) {
    var controller = this.createDefaultCalendarView({
        options: {debounceDelay: 0}
    });
    var view = controller.calendar().fullCalendar().view;
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    controller.selectSource('10');

    var eventStart = this.todayAt({hours: 10, minutes: 30});
    var newEventEnd = this.todayAt({hours: 17});

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());

    this.simulateCalendarEventResize(controller.calendar(), {
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
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/update', 'POST', {
            id: '3',
            allDay: false,
            start: this.toISO8601(eventStart),
            end: this.toISO8601(newEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    equal(0, fakeRevert.count());
});

QUnit.test('creme.FullActivityCalendar.resize (fail)', function(assert) {
    var controller = this.createDefaultCalendarView({
        options: {
            debounceDelay: 0,
            eventUpdateUrl: 'mock/calendar/event/update/400'
        }
    });
    var view = controller.calendar().fullCalendar().view;
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    this.resetMockBackendCalls();

    controller.selectSource('10');

    var eventStart = this.todayAt({hours: 10, minutes: 30});
    var newEventEnd = this.todayAt({hours: 17});

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());

    this.simulateCalendarEventResize(controller.calendar(), {
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
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }],
        ['mock/calendar/event/update/400', 'POST', {
            id: '3',
            allDay: false,
            start: this.toISO8601(eventStart),
            end: this.toISO8601(newEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    equal(1, fakeRevert.count());
});

QUnit.test('creme.FullActivityCalendar.external (ok, allDay)', function(assert) {
    var controller = this.createDefaultCalendarView({
        options: {debounceDelay: 0}
    });

    var element = controller.element();

    controller.selectSource('10');

    this.resetMockBackendCalls();

    deepEqual([], this.mockBackendUrlCalls());

    equal(false, element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group'));
    equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var dropDate = this.todayAt().add(1, 'days').utc();

    this.simulateCalendarDrop(controller.calendar(), {
        source: dragSource,
        date: dropDate.toDate(),
        allDay: true
    });

    deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: 52,
            allDay: true,
            start: this.toISO8601(dropDate, true),
            end: this.toISO8601(dropDate, true)
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

QUnit.test('creme.FullActivityCalendar.external (fail, allDay)', function(assert) {
    var controller = this.createDefaultCalendarView({
        options: {
            debounceDelay: 0,
            eventUpdateUrl: 'mock/calendar/event/update/400'
        }
    });
    var element = controller.element();

    controller.selectSource('10');

    this.resetMockBackendCalls();

    deepEqual([], this.mockBackendUrlCalls());

    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var dropDate = this.todayAt().add(1, 'days').utc();

    this.simulateCalendarDrop(controller.calendar(), {
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
            start: this.toISO8601(dropDate, true),
            end: this.toISO8601(dropDate, true)
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

QUnit.test('creme.FullActivityCalendar.external (ok, none remains, allDay)', function(assert) {
    var controller = this.createDefaultCalendarView({
        options: {debounceDelay: 0},
        html: {
            floating: [
                {id: '51', label: 'Floating event #1', typename: 'Call', calendar: '1', color: '#ccffcc'}
            ]
        }
    });
    var element = controller.element();

    controller.selectSource('10');

    this.resetMockBackendCalls();

    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(1, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="51"]');
    var dropDate = this.todayAt().add(1, 'days').utc();

    this.simulateCalendarDrop(controller.calendar(), {
        source: dragSource,
        date: dropDate.toDate(),
        allDay: true
    });

    deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: 51,
            allDay: true,
            start: this.toISO8601(dropDate, true),
            end: this.toISO8601(dropDate, true)
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
QUnit.test('creme.FullActivityCalendar.external (ok, hour)', function(assert) {
    var controller = this.createDefaultCalendarView({
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
    var dropEventStart = this.todayAt({hours: 8}).add(1, 'days');
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

QUnit.test('creme.FullActivityCalendar.external (fail, hour)', function(assert) {
    var controller = this.createDefaultCalendarView({
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
    var dropEventStart = this.todayAt({hours: 8}).add(1, 'days');
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

QUnit.test('creme.FullActivityCalendar.external (ok, none remains, hour)', function(assert) {
    var controller = this.createDefaultCalendarView({
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
    var dropEventStart = this.todayAt({hours: 8}).add(1, 'days');
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
