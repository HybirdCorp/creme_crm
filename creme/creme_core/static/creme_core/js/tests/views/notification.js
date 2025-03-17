/* globals FunctionFaker PropertyFaker */

(function($) {
"use strict";

QUnit.module("creme.NotificationBox", new QUnitMixin(QUnitEventMixin,
                                                     QUnitAjaxMixin,
                                                     QUnitDialogMixin, {
    beforeEach: function() {
        var self = this;
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendGET({
            'mock/notifs/refresh': function() {
                return backend.response(200, JSON.stringify(self.defaultNotificationData()));
            },
            'mock/notifs/refresh/fail': backend.response(400, ''),
            'mock/notifs/all': backend.response(200, '')
        });

        this.setMockBackendPOST({
            'mock/notifs/discard': backend.response(200, ''),
            'mock/notifs/discard/fail': backend.response(400, '')
        });
    },

    afterEach: function() {
        $('.glasspane').detach();
    },

    defaultNotificationData: function() {
        return {
            count: 3,
            notifications: [
                {
                    id: 1,
                    created: '2025-01-15T16:30:00',
                    level: '1',
                    channel: 'A',
                    subject: 'Subject #1',
                    body: 'Content #1'
                },
                {
                    id: 2,
                    created: '2025-01-16T08:35:00',
                    level: '2',
                    channel: 'A',
                    subject: 'Subject #2',
                    body: 'Content #2'
                },
                {
                    id: 3,
                    created: '2025-01-16T17:12:00',
                    level: '2',
                    channel: 'B',
                    subject: 'Subject #3',
                    body: 'Content #3'
                }
            ]
        };
    },

    createNotificationBoxHtml: function(options) {
        options = Object.assign({
            props: {},
            initialData: {
                count: 0
            }
        }, options || {});

        return (
            '<div class="notification-box">' +
                '<script class="notification-box-data" type="application/json"><!--${data} --></script>' +
                '<span class="notification-box-count is-empty"></span>' +
                '<span class="notification-box-icon"><img title="Notifications" alt="Notifications"></span>' +
                '<div class="notification-panel">' +
                    '<div class="notification-error is-empty"><span>??</span></div>' +
                    '<ul class="notification-items"></ul>' +
                    '<div class="notification-all-link">' +
                        '<a href="mock/notifs/all">See all notifications</a>' +
                    '</div>' +
                '</div>' +
            '</div>'
        ).template({
            data: JSON.stringify(options.initialData)
        });
    }
}));

QUnit.test('creme.NotificationBox', function() {
    var element = $(this.createNotificationBoxHtml()).appendTo(this.qunitFixture());

    equal(element.is('.is-active'), false);

    var box = new creme.notification.NotificationBox(element, {
        refreshUrl: 'mock/notifs/refresh',
        discardUrl: 'mock/notifs/discard'
    }).stopFetch();

    equal(element.is('.is-active'), true);
    deepEqual(box._element, element);
    deepEqual(box._refreshUrl, 'mock/notifs/refresh');
    deepEqual(box._discardUrl, 'mock/notifs/discard');
    deepEqual(box.initialData(), {
        count: 0,
        notifications: []
    });
});

QUnit.test('creme.NotificationBox (invalid urls)', function() {
    var element = $(this.createNotificationBoxHtml({
        initialData: this.defaultNotificationData()
    })).appendTo(this.qunitFixture());

    this.assertRaises(function() {
        return new creme.notification.NotificationBox(element, {});
    });

    this.assertRaises(function() {
        return new creme.notification.NotificationBox(element, {
            refreshUrl:  'mock/notifs/refresh'
        });
    });

    this.assertRaises(function() {
        return new creme.notification.NotificationBox(element, {
            discardUrl:  'mock/notifs/discard'
        });
    });
});

QUnit.test('creme.NotificationBox (already active)', function() {
    var element = $(this.createNotificationBoxHtml({
        initialData: this.defaultNotificationData()
    })).appendTo(this.qunitFixture());

    element.addClass('is-active');

    this.assertRaises(function() {
        return new creme.notification.NotificationBox(element, {
            refreshUrl: 'mock/notifs/refresh',
            discardUrl: 'mock/notids/all'
        });
    }, Error, 'Error: NotificationBox is already active');
});

QUnit.test('creme.NotificationBox (initialData)', function() {
    var element = $(this.createNotificationBoxHtml({
        initialData: this.defaultNotificationData()
    })).appendTo(this.qunitFixture());

    this.withFrozenTime('2025-01-16T17:30:00', function() {
        var box = new creme.notification.NotificationBox(element, {
            refreshUrl: 'mock/notifs/refresh',
            discardUrl: 'mock/notids/all'
        }).stopFetch();

        deepEqual(box.initialData(), this.defaultNotificationData());

        var counter = element.find('.notification-box-count');

        equal(counter.text(), '3');
        equal(counter.is('.is-empty'), false);

        this.equalHtml((
            '<li class="notification-item notification-item-level1" data-id="1" data-created="${timestampA}">' +
                '<span class="notification-channel">A</span>' +
                '<span class="notification-subject">Subject #1</span>' +
                '<span class="notification-created" title="${createdTitleA}">${deltaLabelA}</span>' +
                '<div class="notification-body">Content #1</div>' +
                '<button type="button" class="discard-notification">${discardLabel}</button>' +
            '</li>' +
            '<li class="notification-item notification-item-level2" data-id="2" data-created="${timestampB}">' +
                '<span class="notification-channel">A</span>' +
                '<span class="notification-subject">Subject #2</span>' +
                '<span class="notification-created" title="${createdTitleB}">${deltaLabelB}</span>' +
                '<div class="notification-body">Content #2</div>' +
                '<button type="button" class="discard-notification">${discardLabel}</button>' +
            '</li>' +
            '<li class="notification-item notification-item-level2" data-id="3" data-created="${timestampC}">' +
                '<span class="notification-channel">B</span>' +
                '<span class="notification-subject">Subject #3</span>' +
                '<span class="notification-created" title="${createdTitleC}">${deltaLabelC}</span>' +
                '<div class="notification-body">Content #3</div>' +
                '<button type="button" class="discard-notification">${discardLabel}</button>' +
            '</li>'
        ).template({
            discardLabel: gettext('Validate'),
            timestampA: Date.parse('2025-01-15T16:30:00'),
            timestampB: Date.parse('2025-01-16T08:35:00'),
            timestampC: Date.parse('2025-01-16T17:12:00'),
            createdTitleA: new Date('2025-01-15T16:30:00').toLocaleString(),
            createdTitleB: new Date('2025-01-16T08:35:00').toLocaleString(),
            createdTitleC: new Date('2025-01-16T17:12:00').toLocaleString(),
            deltaLabelA: ngettext('More than %d day ago', 'More than %d days ago', 1).format(1),
            deltaLabelB: ngettext('More than %d hour ago', 'More than %d hours ago', 8).format(8),
            deltaLabelC: ngettext('%d minute ago', '%d minutes ago', 18).format(18)
        }), element.find('.notification-items'));
    });
});

QUnit.test('creme.NotificationBox (fetch)', function() {
    var element = $(this.createNotificationBoxHtml()).appendTo(this.qunitFixture());
    var box = new creme.notification.NotificationBox(element, {
        refreshDelay: 150,
        refreshUrl: 'mock/notifs/refresh',
        discardUrl: 'mock/notifs/discard'
    });

    stop(2);

    setTimeout(function() {
        box.stopFetch();

        var counter = element.find('.notification-box-count');

        equal(counter.text(), '3');
        equal(counter.is('.is-empty'), false);

        deepEqual([], this.mockBackendUrlCalls('mock/notifs/discard'));
        deepEqual([
            ['GET', {}],
            ['GET', {}]
        ], this.mockBackendUrlCalls('mock/notifs/refresh'));

        start();
    }.bind(this), 350);

    setTimeout(function() {
        deepEqual([], this.mockBackendUrlCalls('mock/notifs/discard'));

        // no changes, the job is already stopped
        deepEqual([
            ['GET', {}],
            ['GET', {}]
        ], this.mockBackendUrlCalls('mock/notifs/refresh'));

        start();
    }.bind(this), 350);
});

QUnit.test('creme.NotificationBox (fetch, update deltas)', function() {
    var element = $(this.createNotificationBoxHtml({
        initialData: this.defaultNotificationData()
    })).appendTo(this.qunitFixture());
    var box = new creme.notification.NotificationBox(element, {
        deltaRefreshDelay: 150,
        refreshUrl: 'mock/notifs/refresh',
        discardUrl: 'mock/notifs/discard'
    }).stopFetch();

    var faker = new FunctionFaker();
    box._updateDeltas = faker.wrap();

    equal(0, faker.calls());
    box.startFetch();

    equal(0, faker.calls().length);

    stop(2);

    setTimeout(function() {
        equal(2, faker.calls().length);
        box.stopFetch();
        start();
    }, 350);

    setTimeout(function() {
        // no changes, the job is already stopped
        equal(2, faker.calls().length);
        start();
    }, 450);
});

QUnit.test('creme.NotificationBox (fetch, error)', function() {
    var element = $(this.createNotificationBoxHtml({
        initialData: this.defaultNotificationData()
    })).appendTo(this.qunitFixture());

    var box = new creme.notification.NotificationBox(element, {
        refreshDelay: 150,
        refreshUrl: 'mock/notifs/refresh/fail',
        discardUrl: 'mock/notifs/discard'
    });

    stop(1);

    setTimeout(function() {
        var counter = element.find('.notification-box-count');

        equal(counter.text(), '3');
        equal(counter.is('.is-empty'), false);

        var errors = element.find('.notification-error');
        equal(errors.is('.is-empty'), false);
        equal(errors.text(), gettext('An error happened when retrieving notifications (%s)').format(''));

        deepEqual([
            ['GET', {}]
        ], this.mockBackendUrlCalls('mock/notifs/refresh/fail'));

        box.stopFetch();
        start();
    }.bind(this), 200);
});

QUnit.test('creme.NotificationBox (discard)', function() {
    var element = $(this.createNotificationBoxHtml({
        initialData: this.defaultNotificationData()
    })).appendTo(this.qunitFixture());

    var box = new creme.notification.NotificationBox(element, {
        refreshUrl: 'mock/notifs/refresh',
        discardUrl: 'mock/notifs/discard'
    }).stopFetch();

    var counter = element.find('.notification-box-count');

    equal(counter.text(), '3');
    equal(counter.is('.is-empty'), false);
    equal(element.find('.notification-item .discard-notification').length, 3);
    deepEqual([], this.mockBackendUrlCalls('mock/notifs/discard'));

    element.find('[data-id="2"] .discard-notification').trigger('click');

    deepEqual([
        ['POST', {id: 2}]
    ], this.mockBackendUrlCalls('mock/notifs/discard'));

    equal(element.find('.notification-item .discard-notification').length, 2);

    counter = element.find('.notification-box-count');
    equal(counter.text(), '2');
    equal(counter.is('.is-empty'), false);

    element.find('.discard-notification').trigger('click');

    deepEqual([
        ['POST', {id: 2}],
        ['POST', {id: 1}],
        ['POST', {id: 3}]
    ], this.mockBackendUrlCalls('mock/notifs/discard'));

    equal(element.find('.notification-item .discard-notification').length, 0);

    counter = element.find('.notification-box-count');
    equal(counter.text(), '0');
    equal(counter.is('.is-empty'), true);

    box.stopFetch();
});

QUnit.test('creme.NotificationBox (fetch, document.hidden)', function() {
    var element = $(this.createNotificationBoxHtml({
        initialData: this.defaultNotificationData()
    })).appendTo(this.qunitFixture());

    var hiddenFaker = new PropertyFaker({
        instance: document, props: {hidden: true}
    });

    var box = new creme.notification.NotificationBox(element, {
        refreshDelay: 150,
        refreshUrl: 'mock/notifs/refresh',
        discardUrl: 'mock/notifs/discard'
    });

    hiddenFaker.with(function() {
        equal(document.hidden, true);
        equal(box.isFetchActive(), true);
        equal(box.isPaused(), true);

        // when doc is hidden, the fetch is automatically stopped even without
        // any event
        box._fetchItems();

        deepEqual([], this.mockBackendUrlCalls('mock/notifs/refresh'));
    }.bind(this));

    equal(document.hidden, false);
    box.stopFetch();
});

}(jQuery));
