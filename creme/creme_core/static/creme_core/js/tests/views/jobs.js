/* globals QUnitWidgetMixin */

(function($) {

QUnit.module("creme.jobs.js", new QUnitMixin(QUnitAjaxMixin,
                                             QUnitEventMixin,
                                             QUnitWidgetMixin,
                                             QUnitBrickMixin,
                                             QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;

        backend.options.enableUriSearch = true;

        this._mockJobsResponses = [];
        this._mockJobsFetchCount = 0;

        this.setMockBackendGET({
            'mock/jobs': this.nextMockJobsResponse.bind(this),
            'mock/jobs/invalid': backend.responseJSON(200, {
                error: 'Invalid job data'
            }),
            'mock/jobs/fail': backend.response(400, 'Unable to get jobs')
        });
    },

    resetMockJobsResponses: function(data) {
        this._mockJobsResponses = data || [];
        this._mockJobsFetchCount = 0;
    },

    nextMockJobsResponse: function(data) {
        var responses = this._mockJobsResponses;

        if (this._mockJobsFetchCount < responses.length) {
            return this.backend.responseJSON(200, responses[this._mockJobsFetchCount++]);
        } else {
            return this.backend.responseJSON(400, 'Unable to get jobs');
        }
    },

    jobsListHtml: function(options) {
        options = options || {};
        return (
            '<div><div class="global-error hidden"></div>${jobs}</div>'
        ).template({
            jobs: (options.jobs || []).map(function(item) {
                var progress = item.progress || {};

                return (
                    '<div class="job-status" data-job-id="${id}" data-job-status="${status}" data-job-ack-errors="{ack_errors}">' +
                        '<div class="job-progress">' +
                            '<progress class="job-progress-bar" value="${progressValue}" max="100"></progress>' +
                            '<span class="job-progress-bar-label">${label}</span>' +
                            '${progressLabel}' +
                        '</div>' +
                    '</div>'
                ).template({
                    id: item.id,
                    status: item.status,
                    errors: item.ack_errors,
                    progressValue: progress.percentage,
                    label: progress.label,
                    progressLabel: Object.isNone(progress.percentage) === false ? (
                        '<span class="job-progress-percentage-value">${percentage}</span>' +
                        '<span class="job-progress-percentage-mark percentage-mark">%</span>'
                    ).template(progress) : ''
                });
            }).join('\n')
        });
    },

    assertJobItemState: function(controller, jobId, expected) {
        expected = expected || {};
        var assert = this.assert;
        var job = controller.jobItems(jobId);

        assert.equal(job.length, 1);
        assert.equal(job.find('.job-progress-bar-label').text(), expected.label, 'invalid job label');
        assert.equal(job.find('.job-progress-percentage-value').text(), expected.percentage, 'invalid job progress');
        assert.equal(job.data('job-status'), expected.status, 'invalid job-status');
    },

    createJobsBrick: function(options) {
        options = $.extend({
            classes: ['creme_core-job-brick'],
            content: this.jobsListHtml(options)
        }, options || {});

        return this.createBrickWidget(options).brick();
    },

    createJobsPopupHtml: function(options) {
        options = $.extend({
            finishUrl: 'mock/trash/finish',
            fetchUrl: 'mock/jobs'
        }, options || {});

        return (
            '<form method="POST" action="${finishUrl}" widget="job-waiting-ctrl" class="job-waiting-ctrl ui-creme-widget widget-auto"' +
                  'data-jobs-info-url="${fetchUrl}">' +
                  '${jobs}' +
            '</form>'
        ).template({
            finishUrl: options.finishUrl,
            fetchUrl: options.fetchUrl,
            jobs: this.jobsListHtml(options)
        });
    }
}));

QUnit.test('creme.JobsMonitor (default)', function(assert) {
    var element = $(this.jobsListHtml());
    var controller = new creme.jobs.JobsMonitor(element, {url: 'mock/jobs'});

    assert.deepEqual(element, controller.element());
    assert.equal('mock/jobs', controller.url());
    assert.equal(5000, controller.fetchDelay());
});

QUnit.test('creme.JobsMonitor (properties)', function(assert) {
    var element = $(this.jobsListHtml());
    var controller = new creme.jobs.JobsMonitor(element, {url: 'mock/jobs'});

    assert.deepEqual(element, controller.element());
    assert.equal('mock/jobs', controller.url());
    assert.equal(5000, controller.fetchDelay());

    controller.fetchDelay(0);
    assert.equal(0, controller.fetchDelay());
});

QUnit.test('creme.JobsMonitor (fetch http error)', function(assert) {
    var element = $(this.jobsListHtml({
        jobs: [
            {id: 'job-a', status: '', ack_errors: '', progress: {percentage: 0, label: 'Job A'}},
            {id: 'job-b', status: '', ack_errors: '', progress: {percentage: 10, label: 'Job B'}}
        ]
    }));
    var controller = new creme.jobs.JobsMonitor(element, {url: 'mock/jobs/fail'});

    controller.fetchDelay(0);
    controller.on('finished', this.mockListener('jobs-finished'));

    assert.equal(element.find('.global-error').is('.hidden'), true);
    assert.equal(element.find('.global-error').text(), '');

    controller.fetch();

    assert.deepEqual([
        ['mock/jobs/fail', 'GET', {id: ['job-a', 'job-b']}]
    ], this.mockBackendUrlCalls());

    assert.deepEqual([], this.mockListenerCalls('jobs-finished'));

    assert.equal(element.find('.global-error').is('.hidden'), false);
    assert.equal(element.find('.global-error').text(), gettext('HTTP server error'));
});

QUnit.test('creme.JobsMonitor (fetch invalid data)', function(assert) {
    var element = $(this.jobsListHtml({
        jobs: [
            {id: 'job-a', status: '', ack_errors: '', progress: {percentage: 0, label: 'Job A'}},
            {id: 'job-b', status: '', ack_errors: '', progress: {percentage: 10, label: 'Job B'}}
        ]
    }));
    var controller = new creme.jobs.JobsMonitor(element, {url: 'mock/jobs/invalid'});

    controller.fetchDelay(0);
    controller.on('finished', this.mockListener('jobs-finished'));

    assert.equal(element.find('.global-error').is('.hidden'), true);
    assert.equal(element.find('.global-error').text(), '');

    controller.fetch();

    assert.deepEqual([
        ['mock/jobs/invalid', 'GET', {id: ['job-a', 'job-b']}]
    ], this.mockBackendUrlCalls());

    assert.deepEqual([], this.mockListenerCalls('jobs-finished'));

    assert.equal(element.find('.global-error').is('.hidden'), false);
    assert.equal(element.find('.global-error').text(), 'Invalid job data');
});

QUnit.test('creme.JobsMonitor (fetch steps)', function(assert) {
    var element = $(this.jobsListHtml({
        jobs: [
            {id: 'job-a', status: 1, ack_errors: '', progress: {percentage: 0, label: 'Job A'}},
            {id: 'job-b', status: 1, ack_errors: '', progress: {percentage: 10, label: 'Job B'}}
        ]
    }));

    this.resetMockJobsResponses([{
        'job-a': {status: 1, progress: {percentage: 50, label: 'Job A'}},
        'job-b': {status: 1, progress: {percentage: 30, label: 'Job B'}}
    }, {
        'job-a': {status: 20},
        'job-b': {status: 1, progress: {percentage: 72, label: 'Job B'}}
    }, {
        'job-a': {status: 20},
        'job-b': {status: 20}
    }]);

    var controller = new creme.jobs.JobsMonitor(element, {url: 'mock/jobs'});

    controller.on('finished', this.mockListener('jobs-finished'));

    assert.equal(element.find('.global-error').is('.hidden'), true);
    assert.equal(element.find('.global-error').text(), '');
    assert.deepEqual([], this.mockBackendUrlCalls());

    this.assertJobItemState(controller, 'job-a', {label: 'Job A', percentage: '0', status: 1});
    this.assertJobItemState(controller, 'job-b', {label: 'Job B', percentage: '10', status: 1});

    // controller._retry() is faked and never called. Use fetch() to get the
    // same behavior step by step.
    this.withFakeMethod({instance: controller, method: '_retry'}, function(retry_faker) {
        controller.fetch();

        this.assertJobItemState(controller, 'job-a', {label: 'Job A', percentage: '50', status: 1});
        this.assertJobItemState(controller, 'job-b', {label: 'Job B', percentage: '30', status: 1});
        assert.deepEqual([], this.mockListenerCalls('jobs-finished'));
        assert.equal(retry_faker.count(), 1);

        controller.fetch();

        assert.equal(controller.jobItems('job-a').text(), gettext('Completed successfully'));
        assert.equal(controller.jobItems('job-a').attr('data-job-status'), 20);
        this.assertJobItemState(controller, 'job-b', {label: 'Job B', percentage: '72', status: 1});

        assert.deepEqual([], this.mockListenerCalls('jobs-finished'));
        assert.equal(retry_faker.count(), 2);

        controller.fetch();

        assert.equal(controller.jobItems('job-a').text(), gettext('Completed successfully'));
        assert.equal(controller.jobItems('job-a').attr('data-job-status'), 20);
        assert.equal(controller.jobItems('job-b').text(), gettext('Completed successfully'));
        assert.equal(controller.jobItems('job-a').attr('data-job-status'), 20);

        assert.deepEqual([['finished']], this.mockListenerCalls('jobs-finished'));
        assert.equal(retry_faker.count(), 2);  // <= the retry is not needed here !

        assert.deepEqual([
            ['mock/jobs', 'GET', {id: ['job-a', 'job-b']}],
            ['mock/jobs', 'GET', {id: ['job-a', 'job-b']}],
            ['mock/jobs', 'GET', {id: ['job-a', 'job-b']}]
        ], this.mockBackendUrlCalls());

        assert.equal(element.find('.global-error').is('.hidden'), true);
    });
});

QUnit.test('creme.JobsMonitor (retry defers fetch)', function(assert) {
    var element = $(this.jobsListHtml({
        jobs: [
            {id: 'job-a', status: 1, ack_errors: '', progress: {percentage: 0, label: 'Job A'}},
            {id: 'job-b', status: 1, ack_errors: '', progress: {percentage: 10, label: 'Job B'}}
        ]
    }));

    var controller = new creme.jobs.JobsMonitor(element, {url: 'mock/jobs'});

    this.withFakeMethod({instance: window, method: 'setTimeout'}, function(timeout_faker) {
        timeout_faker.result = 14565227;
        this.withFakeMethod({instance: window, method: 'clearTimeout'}, function(cleartimeout_faker) {
            controller._retry(200);

            assert.equal(timeout_faker.count(), 1);
            assert.equal(cleartimeout_faker.count(), 0);
            assert.equal(controller._deferred, 14565227);

            timeout_faker.result = 7895227;
            controller._retry(200);

            assert.equal(timeout_faker.count(), 2);
            assert.equal(cleartimeout_faker.count(), 1);
            assert.equal(controller._deferred, 7895227);
        });
    });
});

QUnit.test('creme.JobsMonitor (start, no retry)', function(assert) {
    var element = $(this.jobsListHtml({
        jobs: [
            {id: 'job-a', status: 1, ack_errors: '', progress: {percentage: 0, label: 'Job A'}},
            {id: 'job-b', status: 1, ack_errors: '', progress: {percentage: 10, label: 'Job B'}}
        ]
    }));

    var controller = new creme.jobs.JobsMonitor(element, {url: 'mock/jobs'});
    controller.on('finished', this.mockListener('jobs-finished'));

    this.resetMockJobsResponses([{
        'job-a': {status: 20},
        'job-b': {status: 20}
    }]);

    this.withFakeMethod({instance: window, method: 'setTimeout'}, function(timeout_faker) {
        timeout_faker.callable = function() {
            return controller.fetch();
        };

        this.withFakeMethod({instance: window, method: 'clearTimeout'}, function(cleartimeout_faker) {
            controller._deferred = 123457;

            controller.fetch();

            assert.equal(timeout_faker.count(), 0);
            assert.equal(cleartimeout_faker.count(), 1);
            assert.equal(controller._deferred, null);

            assert.deepEqual([['finished']], this.mockListenerCalls('jobs-finished'));
            assert.deepEqual([
                ['mock/jobs', 'GET', {id: ['job-a', 'job-b']}]
            ], this.mockBackendUrlCalls());
        });
    });
});


QUnit.test('creme.JobsMonitor (start, no retry)', function(assert) {
    var element = $(this.jobsListHtml({
        jobs: [
            {id: 'job-a', status: 1, ack_errors: '', progress: {percentage: 0, label: 'Job A'}},
            {id: 'job-b', status: 1, ack_errors: '', progress: {percentage: 10, label: 'Job B'}}
        ]
    }));

    var controller = new creme.jobs.JobsMonitor(element, {url: 'mock/jobs'});
    controller.on('finished', this.mockListener('jobs-finished'));

    this.resetMockJobsResponses([{
        'job-a': {status: 1, progress: {percentage: 50, label: 'Job A'}},
        'job-b': {status: 1, progress: {percentage: 30, label: 'Job B'}}
    }, {
        'job-a': {status: 1, progress: {percentage: 80, label: 'Job A'}},
        'job-b': {status: 1, progress: {percentage: 40, label: 'Job B'}}
    }, {
        'job-a': {status: 20},
        'job-b': {status: 1, progress: {percentage: 57, label: 'Job B'}}
    }, {
        'job-a': {status: 20},
        'job-b': {status: 1, progress: {percentage: 72, label: 'Job B'}}
    }, {
        'job-a': {status: 20},
        'job-b': {status: 20}
    }]);

    this.withFakeMethod({instance: window, method: 'setTimeout'}, function(timeout_faker) {
        timeout_faker.callable = function() {
            return controller.fetch();
        };

        this.withFakeMethod({instance: window, method: 'clearTimeout'}, function(cleartimeout_faker) {
            controller._deferred = 123457;

            assert.equal(timeout_faker.count(), 0);
            assert.equal(cleartimeout_faker.count(), 0);

            controller.fetch();

            assert.equal(timeout_faker.count(), 4);
            assert.equal(cleartimeout_faker.count(), 1);
            assert.equal(controller._deferred, null);

            assert.deepEqual([['finished']], this.mockListenerCalls('jobs-finished'));
            assert.deepEqual([
                ['mock/jobs', 'GET', {id: ['job-a', 'job-b']}],
                ['mock/jobs', 'GET', {id: ['job-a', 'job-b']}],
                ['mock/jobs', 'GET', {id: ['job-a', 'job-b']}],
                ['mock/jobs', 'GET', {id: ['job-a', 'job-b']}],
                ['mock/jobs', 'GET', {id: ['job-a', 'job-b']}]
            ], this.mockBackendUrlCalls());
        });
    });
});

QUnit.test('creme.BrickJobsMonitor (setup)', function(assert) {
    var brick = this.createJobsBrick({
        jobs: [
            {id: 'job-a', status: 1, ack_errors: '', progress: {percentage: 0, label: 'Job A'}},
            {id: 'job-b', status: 1, ack_errors: '', progress: {percentage: 10, label: 'Job B'}}
        ]
    });

    var controller = new creme.jobs.BrickJobsMonitor(brick, {url: 'mock/jobs'});

    assert.equal(controller._brickId, brick.id());

    controller.on('finished', this.mockListener('jobs-finished'));

    this.resetMockJobsResponses([{
        'job-a': {status: 20},
        'job-b': {status: 20}
    }]);

    controller.fetch();

    assert.deepEqual([['finished']], this.mockListenerCalls('jobs-finished'));
    assert.deepEqual([
        ['mock/jobs', 'GET', {id: ['job-a', 'job-b']}]
    ], this.mockBackendUrlCalls());
});

QUnit.test('creme.PopupJobsWaitingController (setup)', function(assert) {
    var dialog = new creme.dialog.FormDialog();
    var content = this.createJobsPopupHtml({
        jobs: [
            {id: 'job-a', status: 1, ack_errors: '', progress: {percentage: 0, label: 'Job A'}},
            {id: 'job-b', status: 1, ack_errors: '', progress: {percentage: 10, label: 'Job B'}}
        ]
    });

    this.resetMockJobsResponses([{
        'job-a': {status: 20},
        'job-b': {status: 20}
    }]);

    assert.deepEqual([], this.mockBackendUrlCalls());

    dialog.fill(content);
    dialog.open();

    assert.equal(dialog.button('cancel').text(), gettext('Close (process in background)'));
    assert.equal(dialog.button('cancel').is(':visible'), false);
    assert.equal(dialog.button('send').is(':visible'), true);

    assert.deepEqual([
        ['mock/jobs', 'GET', {id: ['job-a', 'job-b']}]
    ], this.mockBackendUrlCalls());

    dialog.close();
});

}(jQuery));
