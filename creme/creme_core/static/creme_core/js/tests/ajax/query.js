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

    equal(undefined, query.url());
    equal(this.backend, query.backend());
});

QUnit.test('creme.ajax.Query.url (string)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);

    equal(undefined, query.url());
    equal(this.backend, query.backend());

    query.url('mock/options/1');

    equal('mock/options/1', query.url());
    equal(this.backend, query.backend());
});

QUnit.test('creme.ajax.Query.url (function)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    var id = 1;
    var url = function() {
        return 'mock/options/%d'.format(id);
    };

    equal(undefined, query.url());
    equal(this.backend, query.backend());

    query.url(url);
    equal('mock/options/1', query.url());

    id = 2;
    equal('mock/options/2', query.url());

    id = 3;
    equal('mock/options/3', query.url());
});

QUnit.test('creme.ajax.Query.get (empty url)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.get();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', Error('Unable to send request with empty url'), {
                status: 400, message: 'Unable to send request with empty url'
            }]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.get (url)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/options/1').get();

    deepEqual([
               ['done', JSON.stringify(['a'])]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.url('mock/options/3').get();

    deepEqual([
               ['done', JSON.stringify(['a'])],
               ['done', JSON.stringify(['a', 'b', 'c'])]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.get (url, data)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/custom').get();

    deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.url('mock/custom').get({a: [1, 2]});

    deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {}})],
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {a: [1, 2]}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.url('mock/custom').data({b: 'b'}).get({a: [1, 2]});

    deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {}})],
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {a: [1, 2]}})],
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {b: 'b', a: [1, 2]}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
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

    deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {a: 'a', b: [3, 4], c: 12}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
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

    deepEqual([
               ['done', {url: 'mock/custom/showoptions', method: 'GET', data: {c: 12}, options: $.extend({}, backend_options, {dataType: 'json'})}]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.get({a: 'test'}, {sync: true, custom: true});

    deepEqual([
        ['done', {url: 'mock/custom/showoptions', method: 'GET', data: {c: 12}, options: $.extend({}, backend_options, {dataType: 'json'})}],
        ['done', {url: 'mock/custom/showoptions', method: 'GET', data: {a: 'test'}, options: $.extend({}, backend_options, {sync: true, dataType: 'json', custom: true})}]
       ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.get({b: 53}, {dataType: 'text'});

    deepEqual([
        ['done', {url: 'mock/custom/showoptions', method: 'GET', data: {c: 12}, options: $.extend({}, backend_options, {dataType: 'json'})}],
        ['done', {url: 'mock/custom/showoptions', method: 'GET', data: {a: 'test'}, options: $.extend({}, backend_options, {sync: true, dataType: 'json', custom: true})}],
        // datatype is text, so the JSON response is not parsed
        ['done', JSON.stringify({url: 'mock/custom/showoptions', method: 'GET', data: {b: 53}, options: $.extend({}, backend_options, {dataType: 'text'})})]
       ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.get (async)', function(assert) {
    var query = new creme.ajax.Query({backend: {sync: false, delay: 300}}, this.backend);
    query.onCancel(this.mockListener('cancel'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/options/1').get();

    stop(1);
    equal(true, query.isRunning());

    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('complete'));

    var self = this;

    setTimeout(function() {
        deepEqual([], self.mockListenerCalls('cancel'));
        deepEqual([
            ['done', JSON.stringify(['a'])]
        ], self.mockListenerCalls('complete'));
        start();
    }, 400);
});

QUnit.test('creme.ajax.Query.get (async, canceled)', function(assert) {
    var query = new creme.ajax.Query({backend: {sync: false, delay: 300}}, this.backend);
    query.onCancel(this.mockListener('cancel'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/options/1');
    equal(false, query.isRunning());
    equal(false, query.isCancelable());
    equal(false, query.isStatusCancel());

    this.assertRaises(function() {
        query.cancel();
    }, Error, 'Error: unable to cancel this query');

    query.get();

    equal(true, query.isRunning());
    equal(true, query.isCancelable());
    equal(false, query.isStatusCancel());

    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('complete'));

    query.cancel();

    equal(false, query.isRunning());
    equal(false, query.isCancelable());
    equal(true, query.isStatusCancel());

    stop(1);

    var self = this;

    setTimeout(function() {
        deepEqual([['cancel']], self.mockListenerCalls('cancel'));
        deepEqual([['cancel']], self.mockListenerCalls('complete'));
        start();
    }, 400);
});

QUnit.test('creme.ajax.Query.get (fail)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('/mock/options/unkown').get();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', '', {status: 404, message: ''}]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/forbidden').get();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', '', {status: 404, message: ''}],
            ['fail', 'HTTP - Error 403', {status: 403, message: 'HTTP - Error 403'}]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/error').get();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', '', {status: 404, message: ''}],
            ['fail', 'HTTP - Error 403', {status: 403, message: 'HTTP - Error 403'}],
            ['fail', 'HTTP - Error 500', {status: 500, message: 'HTTP - Error 500'}]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
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

    equal(true, Object.isFunc(query.converter()));
    query.converter(converter);
    query.url('mock/custom').get({a: 5});

    deepEqual([
           ['done', 5 + 10]
    ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
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

    equal(true, Object.isFunc(query.converter()));
    query.converter(error_converter);
    query.url('mock/custom').get({a: 5});

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([
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

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', Error('Unable to send request with empty url'),
                {status: 400, message: 'Unable to send request with empty url'}
            ]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.post (url)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/custom').post();

    deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'POST', data: {}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.url('mock/custom').post({a: [1, 2], b: 'a'});

    deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'POST', data: {}})],
               ['done', JSON.stringify({url: 'mock/custom', method: 'POST', data: {a: [1, 2], b: 'a'}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.post (fail)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('/mock/unknown').post();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', '', {status: 404, message: ''}]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/forbidden').post();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', '', {status: 404, message: ''}],
            ['fail', 'HTTP - Error 403', {status: 403, message: 'HTTP - Error 403'}]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/error').post();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', '', {status: 404, message: ''}],
            ['fail', 'HTTP - Error 403', {status: 403, message: 'HTTP - Error 403'}],
            ['fail', 'HTTP - Error 500', {status: 500, message: 'HTTP - Error 500'}]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.query (get)', function(assert) {
    var query = creme.ajax.query('mock/custom', {}, {}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.start();

    deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'GET', data: {}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.query (post)', function(assert) {
    var query = creme.ajax.query('mock/custom', {action: 'POST'}, {}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.start();

    deepEqual([
               ['done', JSON.stringify({url: 'mock/custom', method: 'POST', data: {}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.query (invalid backend)', function(assert) {
    var query = creme.ajax.query('mock/custom', {action: 'UNKNOWN'}, {});
    query.backend(null);

    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.start();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', Error('Missing ajax backend'), {
                status: 400, message: 'Missing ajax backend'
            }]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.query (unknown action)', function(assert) {
    var query = creme.ajax.query('mock/custom', {action: 'UNKNOWN'}, {}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.start();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', Error('Missing ajax backend action "unknown"'), {
                status: 400, message: 'Missing ajax backend action "unknown"'
            }]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.query (empty url)', function(assert) {
    var query = creme.ajax.query(undefined, {}, {}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.start();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertBackendUrlErrors([
            ['fail', Error('Unable to send request with empty url'), {
                status: 400, message: 'Unable to send request with empty url'
            }]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});
}(jQuery));
