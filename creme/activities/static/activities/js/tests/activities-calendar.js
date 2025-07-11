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
            'mock/calendar/event/floating': backend.response(200, ''),
            'mock/calendar/event/create': backend.response(200, '<form></form>'),
            'mock/calendar/event/create/redirect': backend.response(200, '<form></form>'),

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
            'mock/calendar/select': backend.response(200, ''),
            'mock/calendar/event/update': backend.response(200, ''),
            'mock/calendar/event/update/400': backend.response(400, 'Unable to update calendar event'),
            'mock/calendar/event/update/403': backend.response(403, 'Unable to update calendar event'),
            'mock/calendar/event/update/409': backend.response(409, 'Unable to update calendar event'),
            'mock/calendar/event/create': backend.response(200, ''),
            'mock/calendar/event/create/redirect': backend.response(200, 'mock/calendar/event')
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

    createUserCalendarMenuItemHtml: function(item) {
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

    createUserCalendarMenuGroupHtml: function(group) {
        return (
            '<div class="calendar-menu-usergroup" data-user="${owner}">' +
                '<h5 class="calendar-menu-usergroup-label">${label}</h5>' +
                '${items}' +
            '</div>'
        ).template({
            owner: group.owner || '',
            label: group.label || '',
            items: (group.items || []).map(this.createUserCalendarMenuItemHtml.bind(this)).join('')
        });
    },

    createUserCalendarHtml: function(options) {
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
            mine: (options.mine || []).map(this.createUserCalendarMenuItemHtml.bind(this)).join(''),
            others: (options.others || []).map(this.createUserCalendarMenuGroupHtml.bind(this)).join(''),
            floating: (options.floating || []).map(this.createFloatingEventMenuItemHtml.bind(this)).join('')
        });
    },

    createDefaultUserCalendarHtml: function(options) {
        return this.createUserCalendarHtml($.extend({
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

    createDefaultUserCalendar: function(options) {
        options = options || {};

        var html = this.createDefaultUserCalendarHtml(options.html);
        var element = $(html).appendTo(this.qunitFixture());

        var controller = creme.userActivityCalendar(element, $.extend({
            owner: 'myuser',
            sourceSelectUrl: 'mock/calendar/select',
            eventUpdateUrl: 'mock/calendar/event/update',
            eventCreateUrl: 'mock/calendar/event/create',
            eventFetchUrl: 'mock/calendar/events'
        }, options.options || {}));

        return controller;
    }
}));

QUnit.test('creme.ActivityCalendarController (empty)', function(assert) {
    var element = $(this.createUserCalendarHtml()).appendTo(this.qunitFixture());

    assert.equal(0, element.find('.calendar .fc-header').length);

    var controller = creme.userActivityCalendar(element);

    assert.equal(1, element.find('.calendar .fc-header-toolbar').length, 'calendar header');

    var calendar = controller.calendar();

    assert.equal('', calendar.owner());
    assert.equal('', calendar.eventUpdateUrl());
    assert.equal('', calendar.eventCreateUrl());
    assert.equal('', calendar.eventFetchUrl());

    assert.equal('', controller.sourceSelectUrl());
    assert.deepEqual([], controller.selectedSourceIds());
    assert.ok(controller.fullCalendar() instanceof FullCalendar.Calendar);
    assert.equal(element, controller.element());

    assert.deepEqual({
        allowEventMove: true,
        allowEventOverlaps: true,
        debounceDelay: 200,
        defaultView: 'month',
        fullCalendarOptions: {},
        keepState: false,
        showWeekNumber: true,
        showTimezoneInfo: false,
        timezoneOffset: 0,
        sourceSelectUrl: ''
    }, controller.props());
});

QUnit.test('creme.ActivityCalendarController (options)', function(assert) {
    var element = $(this.createUserCalendarHtml()).appendTo(this.qunitFixture());
    var controller = creme.userActivityCalendar(element, {
        owner: 'myuser',
        sourceSelectUrl: 'mock/calendar/select',
        eventUpdateUrl: 'mock/calendar/event/update',
        eventCreateUrl: 'mock/calendar/event/create',
        eventFetchUrl: 'mock/calendar/events'
    });

    var calendar = controller.calendar();

    assert.equal('myuser', calendar.owner());
    assert.equal('mock/calendar/event/update', calendar.eventUpdateUrl());
    assert.equal('mock/calendar/event/create', calendar.eventCreateUrl());
    assert.equal('mock/calendar/events', calendar.eventFetchUrl());

    assert.equal('mock/calendar/select', controller.sourceSelectUrl());
    assert.deepEqual([], controller.selectedSourceIds());
    assert.ok(controller.fullCalendar() instanceof FullCalendar.Calendar);
    assert.equal(element, controller.element());

    assert.deepEqual({
        allowEventMove: true,
        allowEventOverlaps: true,
        debounceDelay: 200,
        defaultView: 'month',
        fullCalendarOptions: {},
        keepState: false,
        showWeekNumber: true,
        showTimezoneInfo: false,
        timezoneOffset: 0,
        sourceSelectUrl: 'mock/calendar/select',
        eventUpdateUrl: 'mock/calendar/event/update',
        eventCreateUrl: 'mock/calendar/event/create',
        eventFetchUrl: 'mock/calendar/events',
        owner: 'myuser'
    }, controller.props());

    controller.props({
        owner: 'myotheruser',
        debounceDelay: 300
    });

    controller.prop('timezoneOffset', 60);

    assert.deepEqual({
        allowEventMove: true,
        allowEventOverlaps: true,
        debounceDelay: 300,
        defaultView: 'month',
        fullCalendarOptions: {},
        keepState: false,
        showWeekNumber: true,
        showTimezoneInfo: false,
        timezoneOffset: 60,
        sourceSelectUrl: 'mock/calendar/select',
        eventUpdateUrl: 'mock/calendar/event/update',
        eventCreateUrl: 'mock/calendar/event/create',
        eventFetchUrl: 'mock/calendar/events',
        owner: 'myotheruser'
    }, controller.props());
});

QUnit.test('creme.ActivityCalendarController (already bound)', function(assert) {
    var element = $(this.createUserCalendarHtml()).appendTo(this.qunitFixture());
    var controller = creme.userActivityCalendar(element);  // eslint-disable-line

    this.assertRaises(function() {
        creme.userActivityCalendar(element);
    }, Error, 'Error: creme.ActivityCalendarController is already bound');
});

QUnit.parameterize('creme.ActivityCalendarController (initial)', [
    [
        {initialView: 'month', initialDate: '2023-03-20'},
        {view: 'month', start: '2023-02-27', end: '2023-04-10'}
    ],
    [
        {initialView: 'week', initialDate: '2023-01-30'},
        {view: 'week', start: '2023-01-30', end: '2023-02-06'}
    ]
], function(options, expected, assert) {
    var element = $(this.createDefaultUserCalendarHtml()).appendTo(this.qunitFixture());
    var controller = creme.userActivityCalendar(element, Object.assign({
        debounceDelay: 0
    }, options));

    var view = controller.fullCalendar().view;

    assert.equal(view.type, expected.view);
    assert.equal(moment(view.activeStart).format('YYYY-MM-DD'), expected.start);
    assert.equal(moment(view.activeEnd).format('YYYY-MM-DD'), expected.end);
});

QUnit.test('creme.ActivityCalendarController (no history)', function(assert) {
    var element = $(this.createDefaultUserCalendarHtml()).appendTo(this.qunitFixture());
    var controller = creme.userActivityCalendar(element);

    assert.equal(false, controller.keepState());

    assert.deepEqual([], this.mockHistoryChanges());

    controller.goToDate('2023-03-20');

    assert.deepEqual([], this.mockHistoryChanges());
});

QUnit.test('creme.ActivityCalendarController (history)', function(assert) {
    var element = $(this.createDefaultUserCalendarHtml()).appendTo(this.qunitFixture());
    var controller = creme.userActivityCalendar(element, {
        keepState: true,
        rendererDelay: 0
    });

    assert.equal(true, controller.keepState());

    assert.deepEqual([], this.mockHistoryChanges());

    controller.goToDate('2023-03-20');

    assert.deepEqual([
        ['push', '#view=month&date=' + '2023-02-27', undefined]
    ], this.mockHistoryChanges());

    controller.goToDate('2023-02-27');

    assert.deepEqual([
        ['push', '#view=month&date=' + '2023-02-27', undefined],
        ['push', '#view=month&date=' + '2023-01-30', undefined]
    ], this.mockHistoryChanges());

    this.withFakeMethod({instance: controller, method: '_currentUrl'}, function(faker) {
        faker.result = '/mock#view=month&date=2023-01-30';

        assert.deepEqual(controller._loadStateFromUrl(), {
            view: 'month',
            date: moment('2023-01-30')
        });

        // same date
        controller.goToDate('2023-01-30');

        // month mode & date within the month range
        controller.goToDate('2023-02-10');
        controller.goToDate('2023-02-15');

        assert.deepEqual([
            ['push', '#view=month&date=' + '2023-02-27', undefined],
            ['push', '#view=month&date=' + '2023-01-30', undefined]
        ], this.mockHistoryChanges());
    });
});

QUnit.test('creme.ActivityCalendarController (hashchange)', function(assert) {
    var element = $(this.createDefaultUserCalendarHtml()).appendTo(this.qunitFixture());
    var controller = creme.userActivityCalendar(element, {
        keepState: true,
        initialDate: '2023-03-20'
    });
    var view = controller.fullCalendar().view;

    assert.equal(view.type, 'month');
    assert.equal(moment(view.activeStart).format('YYYY-MM-DD'), '2023-02-27');
    assert.equal(moment(view.activeEnd).format('YYYY-MM-DD'), '2023-04-10');

    this.withFakeMethod({instance: controller, method: '_currentUrl'}, function(faker) {
        faker.result = '/mock#view=week&date=2023-01-30';

        assert.deepEqual(controller._loadStateFromUrl(), {
            view: 'week',
            date: moment('2023-01-30')
        });

        $(window).trigger('hashchange');

        view = controller.fullCalendar().view;
        assert.equal(view.type, 'week');
        assert.equal(moment(view.activeStart).format('YYYY-MM-DD'), '2023-01-30');
        assert.equal(moment(view.activeEnd).format('YYYY-MM-DD'), '2023-02-06');
    });
});

QUnit.test('creme.ActivityCalendarController.setViewState', function(assert) {
    var element = $(this.createDefaultUserCalendarHtml()).appendTo(this.qunitFixture());
    var controller = creme.userActivityCalendar(element, {
        keepState: true,
        initialDate: '2023-03-20'
    });
    var view = controller.fullCalendar().view;

    assert.equal(view.type, 'month');
    assert.equal(moment(view.activeStart).format('YYYY-MM-DD'), '2023-02-27');
    assert.equal(moment(view.activeEnd).format('YYYY-MM-DD'), '2023-04-10');

    controller.setViewState({
        view: 'week',
        date: '2023-01-30'
    });

    view = controller.fullCalendar().view;
    assert.equal(view.type, 'week');
    assert.equal(moment(view.activeStart).format('YYYY-MM-DD'), '2023-01-30');
    assert.equal(moment(view.activeEnd).format('YYYY-MM-DD'), '2023-02-06');
});

QUnit.test('creme.ActivityCalendarController.selectedSourceIds (selection)', function(assert) {
    var controller = this.createDefaultUserCalendar({
        options: {debounceDelay: 0}
    });
    var element = controller.element();
    var view = controller.fullCalendar().view;

    this.resetMockBackendCalls();

    assert.deepEqual(['1', '2', '10', '11', '20'].sort(), controller.checkedSourceIds().sort());
    assert.deepEqual(['1', '2', '10', '11', '20'].sort(), controller.selectedSourceIds().sort());
    assert.deepEqual([], this.mockBackendUrlCalls());

    // uncheck all => call update selection url
    element.find('.calendar-menu-item input').prop('checked', false).trigger('change');

    assert.deepEqual([], controller.selectedSourceIds().sort());
    assert.deepEqual([
        ['mock/calendar/select', 'POST', {
            remove: ['1', '2', '10', '11', '20']
        }]
    ], this.mockBackendUrlCalls());
    this.assertCalendarEvents(controller, []);

    this.resetMockBackendCalls();

    // check '10' => call update selection url
    element.find('.calendar-menu-item input[value="10"]').prop('checked', true).trigger('change');
    assert.deepEqual(['10'], controller.selectedSourceIds().sort());
    assert.deepEqual([
        ['mock/calendar/select', 'POST', {add: ['10']}],
        [
            'mock/calendar/events', 'GET', {
                calendar_id: ['10'],
                start: this.toISO8601(view.activeStart, true),
                end: this.toISO8601(view.activeEnd, true)
            }
        ]
    ], this.mockBackendUrlCalls());

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
    assert.deepEqual(['1', '10'].sort(), controller.selectedSourceIds().sort());
    assert.deepEqual([
        ['mock/calendar/select', 'POST', {add: ['1']}],
        [
            'mock/calendar/events', 'GET', {
                calendar_id: ['1', '10'],
                start: this.toISO8601(view.activeStart, true),
                end: this.toISO8601(view.activeEnd, true)
            }
        ]
    ], this.mockBackendUrlCalls());

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

QUnit.test('creme.ActivityCalendarController.create (ok)', function(assert) {
    var controller = this.createDefaultUserCalendar({
        options: {debounceDelay: 0}
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
        ['mock/calendar/event/create', 'POST', {}],
        /* refetch behaviour has moved to the ActivityCalendarController */
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: this.toISO8601(view.activeStart, true),
            end: this.toISO8601(view.activeEnd, true)
        }]
    ], this.mockBackendUrlCalls());

    assert.deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.ActivityCalendarController.create (redirect)', function(assert) {
    var controller = this.createDefaultUserCalendar({
        options: {
            eventCreateUrl: 'mock/calendar/event/create/redirect',
            debounceDelay: 0
        }
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
        ['mock/calendar/event/create/redirect', 'GET', {
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
        ['mock/calendar/event/create/redirect', 'GET', {
            start: this.toISO8601(eventStart),
            end: this.toISO8601(eventEnd),
            allDay: 0
        }],
        ['mock/calendar/event/create/redirect', 'POST', {}]
        /* redirected */
    ], this.mockBackendUrlCalls());

    assert.deepEqual(['mock/calendar/event'], this.mockRedirectCalls());
});

QUnit.test('creme.ActivityCalendarController.filter (sidebar)', function(assert) {
    var controller = this.createDefaultUserCalendar({
        options: {debounceDelay: 0}
    });
    var element = controller.element();
    var input = element.find('.calendar-menu-filter input');
    var getval = function() { return $(this).val(); };
    var getlabel = function() { return $(this).text(); };

    assert.equal('', input.val());
    assert.deepEqual(
        ['1', '2', '10', '11', '20'].sort(),
        element.find('.calendar-menu-item:not(.hidden) input').map(getval).get().sort()
    );
    assert.deepEqual(
        ['Jon Snow', 'Ramsey Snow'],
        element.find('.calendar-menu-usergroup-label:not(.hidden)').map(getlabel).get().sort()
    );

    // Matches "Jon Snow" group only
    input.val('jon').trigger($.Event("keyup", {keyCode: 13}));
    assert.deepEqual(
        ['1', '2', '10', '11'].sort(),
        element.find('.calendar-menu-item:not(.hidden) input').map(getval).get().sort()
    );
    assert.deepEqual(
        ['Jon Snow'],
        element.find('.calendar-menu-usergroup-label:not(.hidden)').map(getlabel).get().sort()
    );

    // Matches both "Jon Snow" & "Ramsey Snow" groups
    input.val('Snow').trigger($.Event("keyup", {keyCode: 13}));
    assert.deepEqual(
        ['1', '2', '10', '11', '20'].sort(),
        element.find('.calendar-menu-item:not(.hidden) input').map(getval).get().sort()
    );
    assert.deepEqual(
        ['Jon Snow', 'Ramsey Snow'],
        element.find('.calendar-menu-usergroup-label:not(.hidden)').map(getlabel).get().sort()
    );

    // Matches "A Calendar #10"
    input.val('#10').trigger($.Event("keyup", {keyCode: 13}));
    assert.deepEqual(
        ['1', '2', '10'].sort(),
        element.find('.calendar-menu-item:not(.hidden) input').map(getval).get().sort()
    );
    assert.deepEqual(
        ['Jon Snow'],
        element.find('.calendar-menu-usergroup-label:not(.hidden)').map(getlabel).get().sort()
    );

     // Matches "B Calendar #20"
    input.val('#20').trigger($.Event("keyup", {keyCode: 13}));
    assert.deepEqual(
        ['1', '2', '20'].sort(),
        element.find('.calendar-menu-item:not(.hidden) input').map(getval).get().sort()
    );
    assert.deepEqual(
        ['Ramsey Snow'],
        element.find('.calendar-menu-usergroup-label:not(.hidden)').map(getlabel).get().sort()
    );
});

QUnit.test('creme.ActivityCalendarController.filter (floating events)', function(assert) {
    var controller = this.createDefaultUserCalendar({
        options: {debounceDelay: 0}
    });
    var element = controller.element();
    var input = element.find('.floating-event-filter input');
    var getid = function() { return $(this).attr('data-id'); };

    assert.equal('', input.val());
    assert.deepEqual(
        ['51', '52', '53'].sort(),
        element.find('.floating-event:not(.hidden)').map(getid).get().sort()
    );

    input.val('call').trigger($.Event("keyup", {keyCode: 13}));
    assert.deepEqual(
        ['52'],
        element.find('.floating-event:not(.hidden)').map(getid).get()
    );

    input.val('event').trigger($.Event("keyup", {keyCode: 13}));
    assert.deepEqual(
        ['51', '53'].sort(),
        element.find('.floating-event:not(.hidden)').map(getid).get().sort()
    );
});

QUnit.test('creme.ActivityCalendarController.external (ok, allDay)', function(assert) {
    var controller = this.createDefaultUserCalendar({
        options: {debounceDelay: 0}
    });

    var element = controller.element();

    controller.selectSource('10');

    this.resetMockBackendCalls();

    assert.deepEqual([], this.mockBackendUrlCalls());

    assert.equal(false, element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group'));
    assert.equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var dropDate = this.todayAt().add(1, 'days').utc();

    this.simulateCalendarDrop(controller, {
        source: dragSource,
        date: dropDate.toDate(),
        allDay: true
    });

    assert.deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: 52,
            allDay: true,
            start: this.toISO8601(dropDate, true),
            end: this.toISO8601(dropDate, true)
        }]
    ], this.mockBackendUrlCalls());

    // floating event has been removed from menu
    assert.equal(0, element.find('.floating-event[data-id="52"]').length);
    assert.equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    assert.equal(2, element.find('.floating-event').length);
});

QUnit.test('creme.ActivityCalendarController.external (fail, allDay)', function(assert) {
    var controller = this.createDefaultUserCalendar({
        options: {
            debounceDelay: 0,
            eventUpdateUrl: 'mock/calendar/event/update/400'
        }
    });
    var element = controller.element();

    controller.selectSource('10');

    this.resetMockBackendCalls();

    assert.deepEqual([], this.mockBackendUrlCalls());

    assert.equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    assert.equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var dropDate = this.todayAt().add(1, 'days').utc();

    this.simulateCalendarDrop(controller, {
        source: dragSource,
        date: dropDate.toDate(),
        allDay: true
    });

    this.assertOpenedDialog(gettext('Error, please reload the page.'));
    this.closeDialog();

    assert.deepEqual([
        ['mock/calendar/event/update/400', 'POST', {
            id: 52,
            allDay: true,
            start: this.toISO8601(dropDate, true),
            end: this.toISO8601(dropDate, true)
        }]
    ], this.mockBackendUrlCalls());

    // floating event remains in menu
    assert.equal(1, element.find('.floating-event[data-id="52"]').length);
    assert.equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    assert.equal(3, element.find('.floating-event').length);
});

QUnit.test('creme.ActivityCalendarController.external (ok, none remains, allDay)', function(assert) {
    var controller = this.createDefaultUserCalendar({
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

    assert.equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    assert.equal(1, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="51"]');
    var dropDate = this.todayAt().add(1, 'days').utc();

    this.simulateCalendarDrop(controller, {
        source: dragSource,
        date: dropDate.toDate(),
        allDay: true
    });

    assert.deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: 51,
            allDay: true,
            start: this.toISO8601(dropDate, true),
            end: this.toISO8601(dropDate, true)
        }]
    ], this.mockBackendUrlCalls());

    // floating event has been removed from menu
    assert.equal(0, element.find('.floating-event[data-id="51"]').length);
    assert.equal(
        true,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    assert.equal(0, element.find('.floating-event').length);
});

// SWITCHING TO 'week' DO NOT WORK WITH FULLCALENDAR 5.x
// TODO : Find why !
QUnit.test('creme.ActivityCalendarController.external (ok, hour)', function(assert) {
    var controller = this.createDefaultUserCalendar({
        options: {debounceDelay: 0}
    });
    var element = controller.element();
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    controller.selectSource('10');
    controller.fullCalendar().changeView('week');

    this.resetMockBackendCalls();

    assert.deepEqual([], this.mockBackendUrlCalls());

    assert.equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    assert.equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var dropEventStart = this.todayAt({hours: 8}).add(1, 'days');
    var dropEventEnd = dropEventStart.clone().add(moment.duration(
        controller.fullCalendar().getOption('defaultTimedEventDuration')
    ));

    this.simulateCalendarDrop(controller, {
        source: dragSource,
        date: dropEventStart.toDate(),
        allDay: false,
        revert: revertCb
    });

    assert.deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: 52,
            allDay: false,
            start: this.toISO8601(dropEventStart),
            end: this.toISO8601(dropEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    // floating event has been removed from menu
    assert.equal(0, element.find('.floating-event[data-id="52"]').length);
    assert.equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    assert.equal(2, element.find('.floating-event').length);

    assert.equal(0, fakeRevert.count());
});

QUnit.test('creme.ActivityCalendarController.external (fail, hour)', function(assert) {
    var controller = this.createDefaultUserCalendar({
        options: {
            debounceDelay: 0,
            eventUpdateUrl: 'mock/calendar/event/update/400'
        }
    });
    var element = controller.element();
    var fakeRevert = new FunctionFaker();
    var revertCb = fakeRevert.wrap();

    controller.selectSource('10');
    controller.fullCalendar().changeView('week');

    this.resetMockBackendCalls();

    assert.deepEqual([], this.mockBackendUrlCalls());

    assert.equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    assert.equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var dropEventStart = this.todayAt({hours: 8}).add(1, 'days');
    var dropEventEnd = dropEventStart.clone().add(moment.duration(
        controller.fullCalendar().getOption('defaultTimedEventDuration')
    ));

    this.simulateCalendarDrop(controller, {
        source: dragSource,
        date: dropEventStart.toDate(),
        allDay: false,
        revert: revertCb
    });

    this.assertOpenedDialog(gettext('Error, please reload the page.'));
    this.closeDialog();

    assert.deepEqual([
        ['mock/calendar/event/update/400', 'POST', {
            id: 52,
            allDay: false,
            start: this.toISO8601(dropEventStart),
            end: this.toISO8601(dropEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    // floating event remains in menu
    assert.equal(1, element.find('.floating-event[data-id="52"]').length);
    assert.equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    assert.equal(3, element.find('.floating-event').length);

    assert.equal(1, fakeRevert.count());
});

QUnit.test('creme.ActivityCalendarController.external (ok, none remains, hour)', function(assert) {
    var controller = this.createDefaultUserCalendar({
        options: {debounceDelay: 0},
        html: {
            floating: [
                {id: '51', label: 'Floating event #1', typename: 'Call', calendar: '1', color: '#ccffcc'}
            ]
        }
    });
    var element = controller.element();

    controller.selectSource('10');
    controller.fullCalendar().changeView('week');

    this.resetMockBackendCalls();

    assert.equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    assert.equal(1, element.find('.floating-event').length);

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

    assert.deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: 51,
            allDay: false,
            start: this.toISO8601(dropEventStart),
            end: this.toISO8601(dropEventEnd)
        }]
    ], this.mockBackendUrlCalls());

    // floating event has been removed from menu
    assert.equal(0, element.find('.floating-event[data-id="51"]').length);
    assert.equal(
        true,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    assert.equal(0, element.find('.floating-event').length);
});

}(jQuery));
