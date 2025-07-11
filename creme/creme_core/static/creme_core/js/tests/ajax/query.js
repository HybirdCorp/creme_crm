/* globals FunctionFaker */

(function($) {
QUnit.module("creme.ajax.query.js", new QUnitMixin(QUnitAjaxMixin, QUnitEventMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.ajax.query.js'});
    },

    beforeEach: function() {
        var self = this;

        this.setMockBackendGET({
            'mock/options/1': this.backend.responseJSON(200, ['a']),
            'mock/options/2': this.backend.responseJSON(200, ['a', 'b']),
            'mock/options/3': this.backend.responseJSON(200, ['a', 'b', 'c']),
            'mock/options/empty': this.backend.responseJSON(200, []),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500'),
            'mock/custom': function(url, data, options) {
                return self._customJSONResponse('GET', url, data);
            },
            'mock/custom/showoptions': function(url, data, options) {
                return self._customJSONResponse('GET', url, data, options);
            }
        });

        this.setMockBackendPOST({
            'mock/add/widget': this.backend.response(
                 200, '<json>' + JSON.stringify({value: '', added: [1, 'newitem']}) + '</json>'
             ),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500'),
            'mock/custom': function(url, data, options) {
                return self._customJSONResponse('POST', url, data);
            }
        });
    },

    _customJSONResponse: function(action, url, data, options) {
        if (Object.isNone(options) === false) {
            return this.backend.responseJSON(200, {url: url, method: action, data: data, options: options});
        } else {
            return this.backend.responseJSON(200, {url: url, method: action, data: data});
        }
    }
}));

QUnit.test('creme.ajax.Query.constructor', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);

    assert.equal(undefined, query.url());
    assert.equal(this.backend, query.backend());
});

QUnit.test('creme.ajax.Query.url (string)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);

    assert.equal(undefined, query.url());
    assert.equal(this.backend, query.backend());

    query.url('mock/options/1');

    assert.equal('mock/options/1', query.url());
    assert.equal(this.backend, query.backend());
});

QUnit.test('creme.ajax.Query.url (function)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    var id = 1;
    var url = function() {
        return 'mock/options/%d'.format(id);
    };

    assert.equal(undefined, query.url());
    assert.equal(this.backend, query.backend());

    query.url(url);
    assert.equal('mock/options/1', query.url());

    id = 2;
    assert.equal('mock/options/2', query.url());

    id = 3;
    assert.equal('mock/options/3', query.url());
});

QUnit.test('creme.ajax.Query.get (empty url)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.get();

    assert.deepEqual([], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', Error('Unable to send request with empty url'), {
                status: 400, message: 'Unable to send request with empty url'
            }]
        ], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.get (url)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/options/1').get();

    assert.deepEqual([
               ['done', JSON.stringify(['a'])]
              ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.url('mock/options/3').get();

    assert.deepEqual([
               ['done', JSON.stringify(['a'])],
               ['done', JSON.stringify(['a', 'b', 'c'])]
              ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.get (url, data)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/custom').get();

    assert.deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {}})]
              ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.url('mock/custom').get({a: [1, 2]});

    assert.deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {}})],
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {a: [1, 2]}})]
              ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.url('mock/custom').data({b: 'b'}).get({a: [1, 2]});

    assert.deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {}})],
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {a: [1, 2]}})],
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {b: 'b', a: [1, 2]}})]
              ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.get (url, data function)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    var datasource = function() {
        return {a: 'a', b: [3, 4]};
    };

    query.url('mock/custom').data(datasource).get({c: 12});

    assert.deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {a: 'a', b: [3, 4], c: 12}})]
              ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.get (url, merge backend options)', function(assert) {
    var query = new creme.ajax.Query({
        backend: {
            dataType: 'json'
        }
    });

    var backend_options = {
        delay: 500,
        enableUriSearch: false,
        sync: true,
        name: 'creme.ajax.query.js'
    };

    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/custom/showoptions').get({c: 12});

    assert.deepEqual([
               ['done', {url: 'mock/custom/showoptions', method: 'GET', data: {c: 12}, options: $.extend({}, backend_options, {dataType: 'json'})}]
              ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.get({a: 'test'}, {sync: true, custom: true});

    assert.deepEqual([
        ['done', {url: 'mock/custom/showoptions', method: 'GET', data: {c: 12}, options: $.extend({}, backend_options, {dataType: 'json'})}],
        ['done', {url: 'mock/custom/showoptions', method: 'GET', data: {a: 'test'}, options: $.extend({}, backend_options, {sync: true, dataType: 'json', custom: true})}]
       ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.get({b: 53}, {dataType: 'text'});

    assert.deepEqual([
        ['done', {url: 'mock/custom/showoptions', method: 'GET', data: {c: 12}, options: $.extend({}, backend_options, {dataType: 'json'})}],
        ['done', {url: 'mock/custom/showoptions', method: 'GET', data: {a: 'test'}, options: $.extend({}, backend_options, {sync: true, dataType: 'json', custom: true})}],
        // datatype is text, so the JSON response is not parsed
        ['done', JSON.stringify({url: 'mock/custom/showoptions', method: 'GET', data: {b: 53}, options: $.extend({}, backend_options, {dataType: 'text'})})]
       ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.get (async)', function(assert) {
    var query = new creme.ajax.Query({backend: {sync: false, delay: 300}}, this.backend);
    query.onCancel(this.mockListener('cancel'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/options/1').get();

    var done = assert.async();

    assert.equal(true, query.isRunning());

    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('complete'));

    var self = this;

    setTimeout(function() {
        assert.deepEqual([], self.mockListenerCalls('cancel'));
        assert.deepEqual([
            ['done', JSON.stringify(['a'])]
        ], self.mockListenerCalls('complete'));
        done();
    }, 400);
});

QUnit.test('creme.ajax.Query.get (async, canceled)', function(assert) {
    var query = new creme.ajax.Query({backend: {sync: false, delay: 300}}, this.backend);
    query.onCancel(this.mockListener('cancel'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/options/1');
    assert.equal(false, query.isRunning());
    assert.equal(false, query.isCancelable());
    assert.equal(false, query.isStatusCancel());

    this.assertRaises(function() {
        query.cancel();
    }, Error, 'Error: unable to cancel this query');

    query.get();

    assert.equal(true, query.isRunning());
    assert.equal(true, query.isCancelable());
    assert.equal(false, query.isStatusCancel());

    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('complete'));

    query.cancel();

    assert.equal(false, query.isRunning());
    assert.equal(false, query.isCancelable());
    assert.equal(true, query.isStatusCancel());

    var done = assert.async();

    var self = this;

    setTimeout(function() {
        assert.deepEqual([['cancel']], self.mockListenerCalls('cancel'));
        assert.deepEqual([['cancel']], self.mockListenerCalls('complete'));
        done();
    }, 400);
});

QUnit.test('creme.ajax.Query.get (fail)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('/mock/options/unkown').get();

    assert.deepEqual([], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', '', {status: 404, message: ''}]
        ], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/forbidden').get();

    assert.deepEqual([], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', '', {status: 404, message: ''}],
            ['fail', 'HTTP - Error 403', {status: 403, message: 'HTTP - Error 403'}]
        ], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/error').get();

    assert.deepEqual([], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', '', {status: 404, message: ''}],
            ['fail', 'HTTP - Error 403', {status: 403, message: 'HTTP - Error 403'}],
            ['fail', 'HTTP - Error 500', {status: 500, message: 'HTTP - Error 500'}]
        ], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.get (converter)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    var converter = function(response) {
        return JSON.parse(response).data.a + 10;
    };

    assert.equal(true, Object.isFunc(query.converter()));
    query.converter(converter);
    query.url('mock/custom').get({a: 5});

    assert.deepEqual([
           ['done', 5 + 10]
    ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
});

QUnit.test('creme.ajax.Query.get (converter, raises)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    var error_converter = function(response) {
        throw new Error('invalid convert');
    };

    assert.equal(true, Object.isFunc(query.converter()));
    query.converter(error_converter);
    query.url('mock/custom').get({a: 5});

    assert.deepEqual([], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([
        ['fail', JSON.stringify({url: 'mock/custom', method: 'GET', data: {a: 5}}), Error('invalid convert')]
    ], this.mockListenerCalls('error'));
});

QUnit.test('creme.ajax.Query.get (invalid converter)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);

    this.assertRaises(function() {
        query.converter('not a function');
    }, Error, 'Error: converter is not a function');
});

QUnit.test('creme.ajax.Query.post (empty url)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.post();

    assert.deepEqual([], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', Error('Unable to send request with empty url'),
                {status: 400, message: 'Unable to send request with empty url'}
            ]
        ], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.post (url)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/custom').post();

    assert.deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'POST', data: {}})]
              ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.url('mock/custom').post({a: [1, 2], b: 'a'});

    assert.deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'POST', data: {}})],
               ['done', JSON.stringify({url: 'mock/custom', method: 'POST', data: {a: [1, 2], b: 'a'}})]
              ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.post (fail)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('/mock/unknown').post();

    assert.deepEqual([], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', '', {status: 404, message: ''}]
        ], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/forbidden').post();

    assert.deepEqual([], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', '', {status: 404, message: ''}],
            ['fail', 'HTTP - Error 403', {status: 403, message: 'HTTP - Error 403'}]
        ], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/error').post();

    assert.deepEqual([], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', '', {status: 404, message: ''}],
            ['fail', 'HTTP - Error 403', {status: 403, message: 'HTTP - Error 403'}],
            ['fail', 'HTTP - Error 500', {status: 500, message: 'HTTP - Error 500'}]
        ], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query (progress, all handlers)', function(assert) {
    this.backend.progressSteps = [0, 10, 30, 50, 100];

    var progressCb = new FunctionFaker();
    var progressEventCb = new FunctionFaker();
    var uploadCb = new FunctionFaker();
    var uploadEventCb = new FunctionFaker();

    var query = new creme.ajax.Query({}, this.backend);
    query.onProgress(progressEventCb.wrap());
    query.onUploadProgress(uploadEventCb.wrap());

    query.get({}, {
        progress: progressCb.wrap(),
        uploadProgress: uploadCb.wrap()
    });

    assert.deepEqual(0, progressCb.count());
    assert.deepEqual(0, uploadCb.count());
    assert.deepEqual(0, progressEventCb.count());
    assert.deepEqual(0, uploadEventCb.count());

    query.url('mock/custom').get({}, {
        progress: progressCb.wrap(),
        uploadProgress: uploadCb.wrap()
    });

    function progressCall(args) {
        return [args[0], args[1].loadedPercent];
    }

    assert.deepEqual(5, progressCb.count());
    assert.deepEqual(5, uploadCb.count());
    assert.deepEqual([
        ['progress', 0],
        ['progress', 10],
        ['progress', 30],
        ['progress', 50],
        ['progress', 100]
    ], progressEventCb.calls().map(progressCall));
    assert.deepEqual([
        ['upload-progress', 0],
        ['upload-progress', 10],
        ['upload-progress', 30],
        ['upload-progress', 50],
        ['upload-progress', 100]
    ], uploadEventCb.calls().map(progressCall));
});

QUnit.test('creme.ajax.Query (progress, only cb)', function(assert) {
    this.backend.progressSteps = [0, 10, 30, 50, 100];

    var progressCb = new FunctionFaker();
    var uploadCb = new FunctionFaker();

    var query = new creme.ajax.Query({}, this.backend);

    query.get({}, {
        progress: progressCb.wrap(),
        uploadProgress: uploadCb.wrap()
    });

    assert.deepEqual(0, progressCb.count());
    assert.deepEqual(0, uploadCb.count());

    query.url('mock/custom').get({}, {
        progress: progressCb.wrap(),
        uploadProgress: uploadCb.wrap()
    });

    function progressCall(args) {
        return args[0].loadedPercent;
    }

    assert.deepEqual([0, 10, 30, 50, 100], progressCb.calls().map(progressCall));
    assert.deepEqual([0, 10, 30, 50, 100], uploadCb.calls().map(progressCall));
});

QUnit.test('creme.ajax.Query (progress, only event cb)', function(assert) {
    this.backend.progressSteps = [0, 10, 30, 50, 100];

    var progressEventCb = new FunctionFaker();
    var uploadEventCb = new FunctionFaker();

    var query = new creme.ajax.Query({}, this.backend);

    query.onProgress(progressEventCb.wrap());
    query.onUploadProgress(uploadEventCb.wrap());

    query.get();

    assert.deepEqual(0, progressEventCb.count());
    assert.deepEqual(0, uploadEventCb.count());

    query.url('mock/custom').get();

    function progressCall(args) {
        return args[1].loadedPercent;
    }

    assert.deepEqual([0, 10, 30, 50, 100], progressEventCb.calls().map(progressCall));
    assert.deepEqual([0, 10, 30, 50, 100], uploadEventCb.calls().map(progressCall));
});

QUnit.test('creme.ajax.query (get)', function(assert) {
    var query = creme.ajax.query('mock/custom', {}, {}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.start();

    assert.deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {}})]
              ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.query (post)', function(assert) {
    var query = creme.ajax.query('mock/custom', {action: 'POST'}, {}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.start();

    assert.deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'POST', data: {}})]
              ], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    assert.deepEqual([], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.query (invalid backend)', function(assert) {
    var query = creme.ajax.query('mock/custom', {action: 'UNKNOWN'}, {});
    query.backend(null);

    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.start();

    assert.deepEqual([], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', Error('Missing ajax backend'), {
                status: 400, message: 'Missing ajax backend'
            }]
        ], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.query (unknown action)', function(assert) {
    var query = creme.ajax.query('mock/custom', {action: 'UNKNOWN'}, {}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.start();

    assert.deepEqual([], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', Error('Missing ajax backend action "unknown"'), {
                status: 400, message: 'Missing ajax backend action "unknown"'
            }]
        ], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.query (empty url)', function(assert) {
    var query = creme.ajax.query(undefined, {}, {}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.start();

    assert.deepEqual([], this.mockListenerCalls('success'));
    assert.deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', Error('Unable to send request with empty url'), {
                status: 400, message: 'Unable to send request with empty url'
            }]
        ], this.mockListenerCalls('error'));
    assert.deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

}(jQuery));
