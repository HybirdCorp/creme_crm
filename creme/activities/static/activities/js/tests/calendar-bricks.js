/* globals QUnitCalendarMixin */

(function($) {

QUnit.module("creme.ActivityCalendarBrickController", new QUnitMixin(QUnitEventMixin,
                                                                     QUnitAjaxMixin,
                                                                     QUnitDialogMixin,
                                                                     QUnitMouseMixin,
                                                                     QUnitBrickMixin,
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
    },

    createCalendarBrickHtml: function(options) {
        options = $.extend({
            classes: ['activity-calendar-brick'],
            ctype: '86'
        }, options || {});

        var header = (
            '<div class="brick-header-buttons">${buttons}</div>'
        ).template({
            buttons: (options.buttons || []).map(this.createBrickActionHtml.bind(this)).join('')
        });

        var content = '<div class="brick-calendar calendar">';

        if (!Object.isEmpty(options.settings)) {
            content += (
                '<script class="brick-calendar-settings" type="application/json"><!--${settings} --></script>'
            ).template({
                settings: JSON.stringify(options.settings)
            });
        }

        if (!Object.isEmpty(options.sources)) {
            content += (
                '<script class="brick-calendar-sources" type="application/json"><!--${sources} --></script>'
            ).template({
                sources: JSON.stringify(options.sources)
            });
        }

        return this.createBrickHtml($.extend({
            classes: options.classes,
            content: content,
            header: header
        }, options));
    },

    createCalendarBrick: function(options) {
        var html = this.createCalendarBrickHtml(options);

        var element = $(html).appendTo(this.qunitFixture());
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        this.assert.equal(true, brick.isBound());
        this.assert.equal(false, brick.isLoading());

        return widget;
    }
}));

QUnit.test('creme.ActivityCalendarBrickController.bind', function(assert) {
    var widget = this.createCalendarBrick();
    var brick = widget.brick();
    var controller = new creme.ActivityCalendarBrickController();

    this.assertRaises(function() {
        controller.bind(widget);
    }, Error, 'Error: ${brick} is not a creme.bricks.Brick'.template({brick: brick}));

    controller.bind(brick);

    this.assertRaises(function() {
        controller.bind(brick);
    }, Error, 'Error: ActivityCalendarBrickController is already bound');
});

QUnit.test('creme.ActivityCalendarBrickController.setup (settings & sources)', function(assert) {
    var widget = this.createCalendarBrick({
        settings: {
            allow_keep_state: true,
            view: 'week',
            utc_offset: 120,
            day_start: '08:00:00',
            day_end: '18:30:00',
            slot_duration: '00:10:00',
            week_days: [1, 2, 4, 5],
            week_start: 1,
            extra_data: {}
        },
        sources: [1, 2, 10, 11]
    });

    var brick = widget.brick();
    var controller = new creme.ActivityCalendarBrickController({
        allowEventCreate: false
    });

    assert.deepEqual({
        allowEventCreate: false,
        fullCalendarOptions: {}
    }, controller.props());

    controller.bind(brick);

    assert.deepEqual({
        allowEventCreate: false,
        allowEventMove: false,
        allowEventOverlaps: true,
        defaultView: "week",
        eventCreateUrl: "",
        eventFetchUrl: "",
        eventUpdateUrl: "",
        externalEventData: _.noop,
        fullCalendarOptions: {},
        headlessMode: false,
        keepState: true,
        owner: "",
        showTimezoneInfo: false,
        showWeekNumber: true,
        timezoneOffset: 120,
        rendererDelay: 100
    }, controller.calendar().props());

    assert.deepEqual([1, 2, 10, 11], controller.calendar().selectedSourceIds());
});

QUnit.test('creme.setupActivityCalendarBrick', function(assert) {
    var element = $(this.createCalendarBrickHtml()).appendTo(this.qunitFixture());
    var controller = creme.setupActivityCalendarBrick(element);

    assert.equal(controller.isBound(), false);
    assert.equal(controller.calendar(), undefined);

    var widget = creme.widget.create(element);

    assert.equal(controller.isBound(), true);
    assert.deepEqual(controller.brick(), widget.brick());
});

}(jQuery));
