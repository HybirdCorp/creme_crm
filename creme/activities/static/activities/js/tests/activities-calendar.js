(function($) {

var todayAt = function(options) {
    options = $.extend({hours: 0, minutes: 0, seconds: 0}, options || {});
    return moment(options);
};

var todayUTCAt = function(options) {
    options = $.extend({hours: 0, minutes: 0, seconds: 0}, options || {});
    return moment.utc(options);
};

var _defaultCalendarData = function() {
    return [{
            id: '1',
            title: 'Event #1',
            color: '#fcfcfc',
            start: todayAt({hours: 8}).toISOString(),
            end: todayAt({hours: 9}).toISOString(),
            calendar: '1',
            allDay: false,
            editable: true,
            url: 'mock/calendar/event/show?id=1',
            type: 'Call'
        }, {
            id: '2',
            title: 'Event #2',
            color: '#fcfcfc',
            start: todayAt({hours: 9}).toISOString(),
            end: todayAt({hours: 10}).toISOString(),
            calendar: '1',
            allDay: false,
            editable: true,
            url: 'mock/calendar/event/show?id=2',
            type: 'Call'
        }, {
            id: '3',
            title: 'Event #10-1',
            color: '#fc00fc',
            start: todayAt({hours: 10, minutes: 30}).toISOString(),
            end: todayAt({hours: 12}).toISOString(),
            calendar: '10',
            allDay: false,
            editable: true,
            url: 'mock/calendar/event/show?id=3',
            type: 'Meeting'
        }, {
            id: '4',
            title: 'Event #20-1 (small)',
            color: '#fc0000',
            start: todayAt({hours: 14, minutes: 30}).toISOString(),
            end: todayAt({hours: 15}).toISOString(),
            calendar: '20',
            allDay: false,
            editable: true,
            url: 'mock/calendar/event/show?id=4',
            type: 'Meeting'
        }, {
            id: '5',
            title: 'Event #20-2',
            color: '#fc0000',
            start: todayAt({hours: 16, minutes: 30}).toISOString(),
            end: todayAt({hours: 18}).toISOString(),
            calendar: '20',
            allDay: false,
            editable: true,
            url: 'mock/calendar/event/show?id=5',
            type: 'Meeting'
        }, {
            id: '6',
            title: 'Event #20-3 (all day)',
            color: '#fc0000',
            start: todayAt().toISOString(),
            calendar: '20',
            allDay: true,
            editable: true,
            url: 'mock/calendar/event/show?id=6',
            type: 'Meeting'
        }
    ];
};

QUnit.module("creme.activities.CalendarController", new QUnitMixin(QUnitEventMixin,
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
                '<div class="loading-indicator">' +
                    '<span class="loading-icon"></span>' +
                    '<span class="loading-label">Loading...</span>' +
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

        var controller = new creme.activities.CalendarController($.extend({
            owner: 'myuser',
            eventSelectUrl: 'mock/calendar/select',
            eventUpdateUrl: 'mock/calendar/event/update',
            eventCreateUrl: 'mock/calendar/event/create',
            eventFetchUrl: 'mock/calendar/events'
        }, options.options || {}));

        return controller.bind(element);
    },

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
                start: range.start,
                end: range.end,
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
}));

QUnit.test('creme.activities.CalendarController (constructor)', function(assert) {
    var controller = new creme.activities.CalendarController();
    equal('', controller.owner());
    equal('', controller.eventSelectUrl());
    equal('', controller.eventUpdateUrl());
    equal('', controller.eventCreateUrl());
    equal('', controller.eventFetchUrl());

    controller = new creme.activities.CalendarController({
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
});

QUnit.test('creme.activities.CalendarController (properties)', function(assert) {
    var controller = new creme.activities.CalendarController();
    equal('', controller.owner());
    equal('', controller.eventSelectUrl());
    equal('', controller.eventUpdateUrl());
    equal('', controller.eventCreateUrl());
    equal('', controller.eventFetchUrl());

    controller.owner('myuser');
    controller.eventSelectUrl('mock/calendar/select');
    controller.eventUpdateUrl('mock/calendar/event/update');
    controller.eventCreateUrl('mock/calendar/event/create');
    controller.eventFetchUrl('mock/calendar/events');

    equal('myuser', controller.owner());
    equal('mock/calendar/select', controller.eventSelectUrl());
    equal('mock/calendar/event/update', controller.eventUpdateUrl());
    equal('mock/calendar/event/create', controller.eventCreateUrl());
    equal('mock/calendar/events', controller.eventFetchUrl());

    deepEqual([], controller.visibleCalendarIds());
    equal(undefined, controller.fullCalendar());
    equal(undefined, controller.element());
    equal(false, controller.isLoading());
});

QUnit.test('creme.activities.CalendarController.bind', function(assert) {
    var controller = new creme.activities.CalendarController();
    var element = $(this.createCalendarHtml()).appendTo(this.qunitFixture());

    equal(false, controller.isBound());
    equal(0, element.find('.calendar .loading-indicator').length);
    equal(0, element.find('.calendar .fc-header').length);

    controller.bind(element);

    equal(true, controller.isBound());
    equal(1, element.find('.calendar .loading-indicator').length, 'loading indicator');
    equal(1, element.find('.calendar .fc-header-toolbar').length, 'calendar header');

    deepEqual([], controller.visibleCalendarIds());
    deepEqual(element.find('.calendar').fullCalendar('getCalendar'), controller.fullCalendar());
    equal(element, controller.element());
    equal(false, controller.isLoading());
});

QUnit.test('creme.activities.CalendarController.bind (already bound)', function(assert) {
    var controller = new creme.activities.CalendarController();
    var element = $(this.createCalendarHtml()).appendTo(this.qunitFixture());

    controller.bind(element);

    equal(true, controller.isBound());

    this.assertRaises(function() {
        controller.bind(element);
    }, Error, 'Error: CalendarController is already bound');
});

QUnit.test('creme.activities.CalendarController.bind (fetch, empty url)', function(assert) {
    var controller = new creme.activities.CalendarController();
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());

    controller.bind(element);

    equal(true, controller.isBound());
    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.visibleCalendarIds().sort());
    deepEqual([], this.mockBackendUrlCalls());
});

QUnit.test('creme.activities.CalendarController.bind (fetch, empty data)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.activities.CalendarController({
                         eventFetchUrl: 'mock/calendar/events/empty'
                     }).bind(element);
    var view = controller.fullCalendar().view;

    equal(true, controller.isBound());
    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.visibleCalendarIds().sort());
    deepEqual([[
        'mock/calendar/events/empty', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: view.start.unix(),
            end: view.end.unix()
        }
    ]], this.mockBackendUrlCalls());
    deepEqual([], this.getCalendarEvents(element));

    this.assertClosedDialog();
});

QUnit.test('creme.activities.CalendarController.bind (fetch, invalid data)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.activities.CalendarController({
                         eventFetchUrl: 'mock/calendar/events/fail'
                     }).bind(element);
    var view = controller.fullCalendar().view;

    equal(true, controller.isBound());
    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.visibleCalendarIds().sort());
    deepEqual([[
        'mock/calendar/events/fail', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: view.start.unix(),
            end: view.end.unix()
        }
    ]], this.mockBackendUrlCalls());
    deepEqual([], this.getCalendarEvents(element));

    this.assertClosedDialog();
});

QUnit.test('creme.activities.CalendarController.bind (fetch)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.activities.CalendarController({
                         eventFetchUrl: 'mock/calendar/events'
                     }).bind(element);
    var calendar = controller.fullCalendar();
    var view = calendar.view;

    equal(true, controller.isBound());
    deepEqual(['1', '2', '10', '11', '20'].sort(), controller.visibleCalendarIds().sort());
    deepEqual([[
        'mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: view.start.unix(),
            end: view.end.unix()
        }
    ]], this.mockBackendUrlCalls());
    deepEqual([{
            allDay: false,
            start: todayAt({hours: 8}).toString(),
            end: todayAt({hours: 9}).toString(),
            title: "Event #1",
            calendar: '1',
            id: '1'
        }, {
            allDay: false,
            start: todayAt({hours: 9}).toString(),
            end: todayAt({hours: 10}).toString(),
            title: "Event #2",
            calendar: '1',
            id: '2'
        }, {
            allDay: false,
            start: todayAt({hours: 10, minutes: 30}).toString(),
            end: todayAt({hours: 12}).toString(),
            title: "Event #10-1",
            calendar: '10',
            id: '3'
        }, {
            allDay: false,
            start: todayAt({hours: 14, minutes: 30}).toString(),
            end: todayAt({hours: 15}).toString(),
            title: "Event #20-1 (small)",
            calendar: '20',
            id: '4'
        }, {
            allDay: false,
            start: todayAt({hours: 16, minutes: 30}).toString(),
            end: todayAt({hours: 18}).toString(),
            title: "Event #20-2",
            calendar: '20',
            id: '5'
        }, {
            allDay: true,
            start: todayUTCAt().toString(),
            end: null,
            title: "Event #20-3 (all day)",
            calendar: '20',
            id: '6'
        }
    ], this.getCalendarEvents(element));
});

QUnit.test('creme.activities.CalendarController.rendering (month view)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.activities.CalendarController({
                         eventFetchUrl: 'mock/calendar/events'
                     }).bind(element);
    var view = controller.fullCalendar().view;
    var hex2rgb = function(color) {
        return $('<div style="color:${color};"></div>'.template({color: color})).css('color');
    };

    equal(view.name, 'month');
    equal(0, element.find('.fc-header-week').length);

    deepEqual([{
            timestamp: '',
            title: "Event #20-3 (all day)",
            typename: '<span class="fc-type">Meeting</span>',
            color: hex2rgb('#fc0000'),
            isSmall: false
        }, {
            timestamp: todayAt({hours: 8}).format('H[h]mm'),
            title: "Event #1",
            typename: '<span class="fc-type">Call</span>',
            color: hex2rgb('#fcfcfc'),
            isSmall: false
        }, {
            timestamp: todayAt({hours: 9}).format('H[h]mm'),
            title: "Event #2",
            typename: '<span class="fc-type">Call</span>',
            color: hex2rgb('#fcfcfc'),
            isSmall: false
        }, {
            timestamp: todayAt({hours: 10, minutes: 30}).format('H[h]mm'),
            title: "Event #10-1",
            typename: '<span class="fc-type">Meeting</span>',
            color: hex2rgb('#fc00fc'),
            isSmall: false
        }, {
            timestamp: todayAt({hours: 14, minutes: 30}).format('H[h]mm'),
            title: "Event #20-1 (small)",
            typename: '<span class="fc-type">Meeting</span>',
            color: hex2rgb('#fc0000'),
            isSmall: false
        }, {
            timestamp: todayAt({hours: 16, minutes: 30}).format('H[h]mm'),
            title: "Event #20-2",
            typename: '<span class="fc-type">Meeting</span>',
            color: hex2rgb('#fc0000'),
            isSmall: false
        }
    ], element.find('.calendar .fc-event').map(function() {
        return {
            timestamp: $(this).find('.fc-time').text(),
            title: $(this).find('.fc-title').text(),
            typename: $(this).find('.fc-type').prop('outerHTML'),
            color: $(this).css('background-color'),
            isSmall: $(this).is('.fc-small')
        };
    }).get());
});

QUnit.test('creme.activities.CalendarController.rendering (week view)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.activities.CalendarController({
                         eventFetchUrl: 'mock/calendar/events'
                     }).bind(element);

    controller.fullCalendar('renderView', 'agendaWeek');

    var view = controller.fullCalendar().view;
    var hex2rgb = function(color) {
        return $('<div style="color:${color};"></div>'.template({color: color})).css('color');
    };

    equal(view.name, 'agendaWeek');

    equal(1, element.find('.fc-header-week').length);
    equal('${week} ${num}'.template({week: gettext('Week'), num: todayAt().format('W')}),
          element.find('.fc-header-week').text());

    deepEqual([{
            timestamp: '',
            title: "Event #20-3 (all day)",
            typename: '<span class="fc-type">Meeting</span>',
            color: hex2rgb('#fc0000'),
            isSmall: false
        }, {
            timestamp: [todayAt({hours: 8}).format('H[h]mm'), todayAt({hours: 9}).format('H[h]mm')].join(' - '),
            title: "Event #1",
            typename: '<span class="fc-type">Call</span>',
            color: hex2rgb('#fcfcfc'),
            isSmall: false
        }, {
            timestamp: [todayAt({hours: 9}).format('H[h]mm'), todayAt({hours: 10}).format('H[h]mm')].join(' - '),
            title: "Event #2",
            typename: '<span class="fc-type">Call</span>',
            color: hex2rgb('#fcfcfc'),
            isSmall: false
        }, {
            timestamp: [todayAt({hours: 10, minutes: 30}).format('H[h]mm'), todayAt({hours: 12}).format('H[h]mm')].join(' - '),
            title: "Event #10-1",
            typename: '<span class="fc-type">Meeting</span>',
            color: hex2rgb('#fc00fc'),
            isSmall: false
        }, {
            timestamp: [todayAt({hours: 14, minutes: 30}).format('H[h]mm'), todayAt({hours: 15}).format('H[h]mm')].join(' - '),
            title: "Event #20-1 (small)",
            typename: '<span class="fc-type">Meeting</span>',
            color: hex2rgb('#fc0000'),
            isSmall: true
        }, {
            timestamp: [todayAt({hours: 16, minutes: 30}).format('H[h]mm'), todayAt({hours: 18}).format('H[h]mm')].join(' - '),
            title: "Event #20-2",
            typename: '<span class="fc-type">Meeting</span>',
            color: hex2rgb('#fc0000'),
            isSmall: false
        }
    ], element.find('.calendar .fc-event').map(function() {
        return {
            timestamp: $(this).find('.fc-time').text(),
            title: $(this).find('.fc-title').text(),
            typename: $(this).find('.fc-type').prop('outerHTML'),
            color: $(this).css('background-color'),
            isSmall: $(this).is('.fc-small')
        };
    }).get());
});

QUnit.test('creme.activities.CalendarController.rendering (hilight, week view)', function(assert) {
    var element = $(this.createDefaultCalendarHtml()).appendTo(this.qunitFixture());
    var controller = new creme.activities.CalendarController({
                         eventFetchUrl: 'mock/calendar/events'
                     }).bind(element);

    controller.fullCalendar('renderView', 'agendaWeek');

    var view = controller.fullCalendar().view;
    var start = todayAt({hours: 8});
    var end = todayAt({hours: 9, minutes: 45});

    deepEqual([], element.find('.calendar .fc-event.fc-event-highlight').get());

    // HACK : Simulate range selection rendering
    view.timeGrid.renderSelectionFootprint(new $.fullCalendar.ComponentFootprint(
        new $.fullCalendar.UnzonedRange(start, end),
        false  /* all day */
    ));

    deepEqual([{
        content: '${start} − ${end}'.template({
            start: start.format(view.options.timeFormat),
            end: end.format(view.options.timeFormat)
        })
    }], element.find('.calendar .fc-event.fc-event-highlight').map(function() {
        return {
            content: $(this).text()
        };
    }).get());
});

QUnit.test('creme.activities.CalendarController.visibleCalendarIds (selection)', function(assert) {
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
    deepEqual([], this.getCalendarEvents(element));

    this.resetMockBackendCalls();

    // check '10' => call update selection url
    element.find('.calendar-menu-item input[value="10"]').prop('checked', true).trigger('change');
    deepEqual(['10'], controller.visibleCalendarIds().sort());
    deepEqual([[
        'mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: view.start.unix(),
            end: view.end.unix()
        }
    ]], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: todayAt({hours: 10, minutes: 30}).toString(),
        end: todayAt({hours: 12}).toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));

    this.resetMockBackendCalls();

    // check '1' => call update selection url
    element.find('.calendar-menu-item input[value="1"]').prop('checked', true).trigger('change');
    deepEqual(['1', '10'].sort(), controller.visibleCalendarIds().sort());
    deepEqual([[
        'mock/calendar/events', 'GET', {
            calendar_id: ['1', '10'],
            start: view.start.unix(),
            end: view.end.unix()
        }
    ]], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: todayAt({hours: 8}).toString(),
        end: todayAt({hours: 9}).toString(),
        title: "Event #1",
        calendar: '1',
        id: '1'
    }, {
        allDay: false,
        start: todayAt({hours: 9}).toString(),
        end: todayAt({hours: 10}).toString(),
        title: "Event #2",
        calendar: '1',
        id: '2'
    }, {
        allDay: false,
        start: todayAt({hours: 10, minutes: 30}).toString(),
        end: todayAt({hours: 12}).toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));
});

QUnit.test('creme.activities.CalendarController.isLoading', function(assert) {
    var controller = this.createDefaultCalendar();
    var element = controller.element();

    var indicator = element.find('.calendar .loading-indicator');
    equal(1, indicator.length);

    equal(false, controller.isLoading());
    equal(false, indicator.is('.is-loading'));

    controller.isLoading(true);

    equal(true, controller.isLoading());
    equal(true, indicator.is('.is-loading'));

    controller.isLoading(false);

    equal(false, controller.isLoading());
    equal(false, indicator.is('.is-loading'));
});

QUnit.test('creme.activities.CalendarController.filter (sidebar)', function(assert) {
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

QUnit.test('creme.activities.CalendarController.filter (floating events)', function(assert) {
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

QUnit.test('creme.activities.CalendarController.create (canceled, allDay)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var view = controller.fullCalendar().view;
    var today = $.fullCalendar.moment(todayAt());

    today.stripTime();
    equal(false, today.hasTime());

    this.assertClosedDialog();

    controller.fullCalendar('select', today);

    this.assertOpenedDialog();
    this.closeDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: view.start.unix(),
            end: view.end.unix()
        }],
        ['mock/calendar/event/create', 'GET', {
            start: today.format(),
            end: today.format(),
            allDay: 1
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.activities.CalendarController.create (ok, allDay)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var view = controller.fullCalendar().view;
    var today = $.fullCalendar.moment(todayAt());

    today.stripTime();
    equal(false, today.hasTime());

    this.assertClosedDialog();

    controller.fullCalendar('select', today);

    this.assertOpenedDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: view.start.unix(),
            end: view.end.unix()
        }],
        ['mock/calendar/event/create', 'GET', {
            start: today.format(),
            end: today.format(),
            allDay: 1
        }]
    ], this.mockBackendUrlCalls());

    this.submitFormDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: view.start.unix(),
            end: view.end.unix()
        }],
        ['mock/calendar/event/create', 'GET', {
            start: today.format(),
            end: today.format(),
            allDay: 1
        }],
        ['mock/calendar/event/create', 'POST', {}],
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: view.start.unix(),
            end: view.end.unix()
        }]
    ], this.mockBackendUrlCalls());
});


QUnit.test('creme.activities.CalendarController.create (ok)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var view = controller.fullCalendar().view;
    var eventStart = $.fullCalendar.moment(todayAt({hours: 8}));
    var eventEnd = eventStart.clone().add(controller.fullCalendar().defaultTimedEventDuration);

    equal(true, eventStart.hasTime());
    equal(true, eventEnd.hasTime());

    this.assertClosedDialog();

    controller.fullCalendar('select', eventStart);

    this.assertOpenedDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: view.start.unix(),
            end: view.end.unix()
        }],
        ['mock/calendar/event/create', 'GET', {
            start: eventStart.format(),
            end: eventEnd.format(),
            allDay: 0
        }]
    ], this.mockBackendUrlCalls());

    this.submitFormDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: view.start.unix(),
            end: view.end.unix()
        }],
        ['mock/calendar/event/create', 'GET', {
            start: eventStart.format(),
            end: eventEnd.format(),
            allDay: 0
        }],
        ['mock/calendar/event/create', 'POST', {}],
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: view.start.unix(),
            end: view.end.unix()
        }]
    ], this.mockBackendUrlCalls());
});


QUnit.test('creme.activities.CalendarController.show', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var view = controller.fullCalendar().view;
    var element = controller.element();

    this.assertClosedDialog();

    var event = this.findCalendarEventItem(element, '3');
    equal(event.length, 1);
    event.trigger('click');

    this.assertOpenedDialog();
    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['1', '2', '10', '11', '20'],
            start: view.start.unix(),
            end: view.end.unix()
        }],
        ['mock/calendar/event/show', 'GET', {
            id: '3'
        }]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.activities.CalendarController.move (ok)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var view = controller.fullCalendar().view;
    var element = controller.element();

    this.resetMockBackendCalls();

    controller.visibleCalendarIds(['10']);

    var eventStart = todayAt({hours: 10, minutes: 30});
    var eventEnd = todayAt({hours: 12});

    var newEventStart = todayAt({hours: 15, minutes: 30}).add(1, 'days');
    var newEventEnd = todayAt({hours: 17}).add(1, 'days');

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: view.start.unix(),
            end: view.end.unix()
        }]
    ], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: eventStart.toString(),
        end: eventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));

    var dragSource = this.findCalendarEventItem(element, '3');
    equal(
       todayAt({hours: 10, minutes: 30}).format('H[h]mm'),
       dragSource.find('.fc-time').text()
    );

    this.simulateCalendarDragNDrop(controller, dragSource, {
        start: newEventStart,
        end: newEventEnd
    });

    this.assertClosedDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: view.start.unix(),
            end: view.end.unix()
        }],
        ['mock/calendar/event/update', 'POST', {
            id: '3',
            allDay: false,
            start: newEventStart.valueOf(),
            end: newEventEnd.valueOf()
        }]
    ], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: newEventStart.toString(),
        end: newEventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));
});

QUnit.test('creme.activities.CalendarController.move (fail)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {
            debounceDelay: 0,
            eventUpdateUrl: 'mock/calendar/event/update/400'
        }
    });
    var view = controller.fullCalendar().view;
    var element = controller.element();

    this.resetMockBackendCalls();

    controller.visibleCalendarIds(['10']);

    var eventStart = todayAt({hours: 10, minutes: 30});
    var eventEnd = todayAt({hours: 12});

    var newEventStart = todayAt({hours: 15, minutes: 30}).add(1, 'days');
    var newEventEnd = todayAt({hours: 17}).add(1, 'days');

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: view.start.unix(),
            end: view.end.unix()
        }]
    ], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: eventStart.toString(),
        end: eventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));

    var dragSource = this.findCalendarEventItem(element, '3');
    equal(
       todayAt({hours: 10, minutes: 30}).format('H[h]mm'),
       dragSource.find('.fc-time').text()
    );

    this.simulateCalendarDragNDrop(controller, dragSource, {
        start: newEventStart,
        end: newEventEnd
    });

    this.assertOpenedDialog(gettext('Error, please reload the page.'));
    this.closeDialog();

    // Invalid update, call revert
    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: view.start.unix(),
            end: view.end.unix()
        }],
        ['mock/calendar/event/update/400', 'POST', {
            id: '3',
            allDay: false,
            start: newEventStart.valueOf(),
            end: newEventEnd.valueOf()
        }]
    ], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: eventStart.toString(),
        end: eventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));

    controller.eventUpdateUrl('mock/calendar/event/update/403');

    dragSource = this.findCalendarEventItem(element, '3');

    this.simulateCalendarDragNDrop(controller, dragSource, {
        start: newEventStart,
        end: newEventEnd
    });

    this.assertOpenedDialog(gettext('You do not have permission, the change will not be saved.'));
    this.closeDialog();

    controller.eventUpdateUrl('mock/calendar/event/update/409');

    dragSource = this.findCalendarEventItem(element, '3');

    this.simulateCalendarDragNDrop(controller, dragSource, {
        start: newEventStart,
        end: newEventEnd
    });

    this.assertOpenedDialog('Unable to update calendar event');
    this.closeDialog();
});

QUnit.test('creme.activities.CalendarController.resize (ok)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var view = controller.fullCalendar().view;
    var element = controller.element();

    this.resetMockBackendCalls();

    controller.visibleCalendarIds(['10']);

    var eventStart = todayAt({hours: 10, minutes: 30});
    var eventEnd = todayAt({hours: 12});

    var newEventEnd = todayAt({hours: 17});

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: view.start.unix(),
            end: view.end.unix()
        }]
    ], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: eventStart.toString(),
        end: eventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));

    var item = this.findCalendarEventItem(element, '3');
    equal(
       todayAt({hours: 10, minutes: 30}).format('H[h]mm'),
       item.find('.fc-time').text()
    );

    this.simulateCalendarResize(controller, item, {
        start: eventStart,
        end: newEventEnd
    });

    this.assertClosedDialog();

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: view.start.unix(),
            end: view.end.unix()
        }],
        ['mock/calendar/event/update', 'POST', {
            id: '3',
            allDay: false,
            start: eventStart.valueOf(),
            end: newEventEnd.valueOf()
        }]
    ], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: eventStart.toString(),
        end: newEventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));
});

QUnit.test('creme.activities.CalendarController.resize (fail)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {
            debounceDelay: 0,
            eventUpdateUrl: 'mock/calendar/event/update/400'
        }
    });
    var view = controller.fullCalendar().view;
    var element = controller.element();

    this.resetMockBackendCalls();

    controller.visibleCalendarIds(['10']);

    var eventStart = todayAt({hours: 10, minutes: 30});
    var eventEnd = todayAt({hours: 12});

    var newEventEnd = todayAt({hours: 17});

    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: view.start.unix(),
            end: view.end.unix()
        }]
    ], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: eventStart.toString(),
        end: eventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));

    var item = this.findCalendarEventItem(element, '3');
    equal(
       todayAt({hours: 10, minutes: 30}).format('H[h]mm'),
       item.find('.fc-time').text()
    );

    this.simulateCalendarResize(controller, item, {
        start: eventStart,
        end: newEventEnd
    });

    this.assertOpenedDialog(gettext('Error, please reload the page.'));
    this.closeDialog();

    // Invalid update, call revert
    deepEqual([
        ['mock/calendar/events', 'GET', {
            calendar_id: ['10'],
            start: view.start.unix(),
            end: view.end.unix()
        }],
        ['mock/calendar/event/update/400', 'POST', {
            id: '3',
            allDay: false,
            start: eventStart.valueOf(),
            end: newEventEnd.valueOf()
        }]
    ], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: eventStart.toString(),
        end: eventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));
});

QUnit.test('creme.activities.CalendarController.external (ok, allDay)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var element = controller.element();

    controller.visibleCalendarIds(['10']);

    this.resetMockBackendCalls();

    var eventStart = todayAt({hours: 10, minutes: 30});
    var eventEnd = todayAt({hours: 12});

    deepEqual([], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: eventStart.toString(),
        end: eventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));

//    equal(false, element.find('.floating-activities').parents('.menu-group:first').is('.is-empty-group'));
    equal(false, element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group'));
    equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var extEventStart = todayAt({hours: 8}).add(1, 'days');
    var extEventEnd = extEventStart.clone().set({hours: 0, minutes: 0, seconds: 0});

    this.simulateCalendarExternalDragNDrop(controller, dragSource, {
        start: extEventStart
    });

    deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: '52',
            allDay: true,
            start: extEventStart.valueOf(),
            end: extEventEnd.valueOf()
        }]
    ], this.mockBackendUrlCalls());
    deepEqual([{
            allDay: false,
            start: eventStart.toString(),
            end: eventEnd.toString(),
            title: "Event #10-1",
            calendar: '10',
            id: '3'
        }, {
            allDay: true,
            start: todayUTCAt().add(1, 'days').toString(),
            end: null,
            title: "Floating call #2",
            calendar: '10',
            id: '52'
        }
    ], this.getCalendarEvents(element));

    // floating event has been removed from menu
    equal(0, element.find('.floating-event[data-id="52"]').length);
//    equal(false, element.find('.floating-activities').parents('.menu-group:first').is('.is-empty-group'));
    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(2, element.find('.floating-event').length);
});

QUnit.test('creme.activities.CalendarController.external (ok, hour)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {debounceDelay: 0}
    });
    var element = controller.element();

    controller.visibleCalendarIds(['10']);
    controller.fullCalendar('renderView', 'agendaWeek');

    equal('agendaWeek', controller.calendarView().name);

    this.resetMockBackendCalls();

    var eventStart = todayAt({hours: 10, minutes: 30});
    var eventEnd = todayAt({hours: 12});

    deepEqual([], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: eventStart.toString(),
        end: eventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));

//    equal(false, element.find('.floating-activities').parents('.menu-group:first').is('.is-empty-group'));
    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var extEventStart = todayAt({hours: 8}).add(1, 'days');
    var extEventEnd = extEventStart.clone().add(controller.fullCalendar().defaultTimedEventDuration);

    this.simulateCalendarExternalDragNDrop(controller, dragSource, {
        start: extEventStart
    });

    deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: '52',
            allDay: false,
            start: extEventStart.valueOf(),
            end: extEventEnd.valueOf()
        }]
    ], this.mockBackendUrlCalls());
    deepEqual([{
            allDay: false,
            start: eventStart.toString(),
            end: eventEnd.toString(),
            title: "Event #10-1",
            calendar: '10',
            id: '3'
        }, {
            allDay: false,
            start: extEventStart.toString(),
            end: extEventEnd.toString(),
            title: "Floating call #2",
            calendar: '10',
            id: '52'
        }
    ], this.getCalendarEvents(element));

    // floating event has been removed from menu
    equal(0, element.find('.floating-event[data-id="52"]').length);
//    equal(false, element.find('.floating-activities').parents('.menu-group:first').is('.is-empty-group'));
    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(2, element.find('.floating-event').length);
});

QUnit.test('creme.activities.CalendarController.external (fail)', function(assert) {
    var controller = this.createDefaultCalendar({
        options: {
            debounceDelay: 0,
            eventUpdateUrl: 'mock/calendar/event/update/400'
        }
    });
    var element = controller.element();

    controller.visibleCalendarIds(['10']);
    controller.fullCalendar('renderView', 'agendaWeek');

    this.resetMockBackendCalls();

    var eventStart = todayAt({hours: 10, minutes: 30});
    var eventEnd = todayAt({hours: 12});

    deepEqual([], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: eventStart.toString(),
        end: eventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));

//    equal(false, element.find('.floating-activities').parents('.menu-group:first').is('.is-empty-group'));
    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(3, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="52"]');
    var extEventStart = todayAt({hours: 8}).add(1, 'days');
    var extEventEnd = extEventStart.clone().add(controller.fullCalendar().defaultTimedEventDuration);

    this.simulateCalendarExternalDragNDrop(controller, dragSource, {
        start: extEventStart
    });

    this.assertOpenedDialog(gettext('Error, please reload the page.'));
    this.closeDialog();

    deepEqual([
        ['mock/calendar/event/update/400', 'POST', {
            id: '52',
            allDay: false,
            start: extEventStart.valueOf(),
            end: extEventEnd.valueOf()
        }]
    ], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: eventStart.toString(),
        end: eventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));

    // floating event remains in menu
    equal(1, element.find('.floating-event[data-id="52"]').length);
//    equal(false, element.find('.floating-activities').parents('.menu-group:first').is('.is-empty-group'));
    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(3, element.find('.floating-event').length);
});

QUnit.test('creme.activities.CalendarController.external (ok, none remains)', function(assert) {
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
    controller.fullCalendar('renderView', 'agendaWeek');

    equal('agendaWeek', controller.calendarView().name);

    this.resetMockBackendCalls();

    var eventStart = todayAt({hours: 10, minutes: 30});
    var eventEnd = todayAt({hours: 12});

    deepEqual([], this.mockBackendUrlCalls());
    deepEqual([{
        allDay: false,
        start: eventStart.toString(),
        end: eventEnd.toString(),
        title: "Event #10-1",
        calendar: '10',
        id: '3'
    }], this.getCalendarEvents(element));

//    equal(false, element.find('.floating-activities').parents('.menu-group:first').is('.is-empty-group'));
    equal(
        false,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(1, element.find('.floating-event').length);

    var dragSource = element.find('.floating-event[data-id="51"]');
    var extEventStart = todayAt({hours: 8}).add(1, 'days');
    var extEventEnd = extEventStart.clone().add(controller.fullCalendar().defaultTimedEventDuration);

    this.simulateCalendarExternalDragNDrop(controller, dragSource, {
        start: extEventStart
    });

    deepEqual([
        ['mock/calendar/event/update', 'POST', {
            id: '51',
            allDay: false,
            start: extEventStart.valueOf(),
            end: extEventEnd.valueOf()
        }]
    ], this.mockBackendUrlCalls());
    deepEqual([{
            allDay: false,
            start: eventStart.toString(),
            end: eventEnd.toString(),
            title: "Event #10-1",
            calendar: '10',
            id: '3'
        }, {
            allDay: false,
            start: extEventStart.toString(),
            end: extEventEnd.toString(),
            title: "Floating event #1",
            calendar: '1',
            id: '51'
        }
    ], this.getCalendarEvents(element));

    // floating event has been removed from menu
    equal(0, element.find('.floating-event[data-id="51"]').length);
//    equal(true, element.find('.floating-activities').parents('.menu-group:first').is('.is-empty-group'));
    equal(
        true,
        element.find('.floating-activities').parents('.menu-group').first().is('.is-empty-group')
    );
    equal(0, element.find('.floating-event').length);
});

}(jQuery));
