(function($) {

QUnit.module("creme.ajax.query.js", new QUnitMixin(QUnitAjaxMixin, QUnitEventMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.ajax.query.js'});
    },

    beforeEach: function() {
        var self = this;

        this.setMockBackendGET({
            'mock/options/1': this.backend.response(200, ['a']),
            'mock/options/2': this.backend.response(200, ['a', 'b']),
            'mock/options/3': this.backend.response(200, ['a', 'b', 'c']),
            'mock/options/empty': this.backend.response(200, []),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500'),
            'mock/custom': function(url, data, options) {
                return self._customResponse('GET', url, data);
            },
            'mock/custom/showoptions': function(url, data, options) {
                return self._customResponse('GET', url, data, options);
            }
        });

        this.setMockBackendPOST({
            'mock/add/widget': this.backend.response(200, '<json>' + $.toJSON({value: '', added: [1, 'newitem']}) + '</json>'),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500'),
            'mock/custom': function(url, data, options) {
                return self._customResponse('POST', url, data);
            }
        });
    },

    _customResponse: function(action, url, data, options) {
        if (Object.isNone(options) === false) {
            return this.backend.response(200, $.toJSON({url: url, method: action, data: data, options: options}));
        } else {
            return this.backend.response(200, $.toJSON({url: url, method: action, data: data}));
        }
    },

    assertMockQueryErrorCalls: function(expected, calls) {
        equal(expected.length, calls.length, 'length');

        for (var i = 0; i < calls.length; ++i) {
            var call = calls[i];
            var expect = expected[i];

            equal(call[0], expect[0], 'event');
            equal(call[1], expect[1], 'data');
            equal(call[2].type, 'request');
            equal(call[2].status, expect[2], 'status');
            equal(call[2].message, expect[1], 'xhr message');
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
    deepEqual([['cancel']], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('cancel'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.get (url)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/options/1').get();

    deepEqual([
               ['done', ['a']]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.url('mock/options/3').get();

    deepEqual([
               ['done', ['a']],
               ['done', ['a', 'b', 'c']]
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
               ['done', $.toJSON({url: 'mock/custom', method: 'GET', data: {}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.url('mock/custom').get({a: [1, 2]});

    deepEqual([
               ['done', $.toJSON({url: 'mock/custom', method: 'GET', data: {}})],
               ['done', $.toJSON({url: 'mock/custom', method: 'GET', data: {a: [1, 2]}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.url('mock/custom').data({b: 'b'}).get({a: [1, 2]});

    deepEqual([
               ['done', $.toJSON({url: 'mock/custom', method: 'GET', data: {}})],
               ['done', $.toJSON({url: 'mock/custom', method: 'GET', data: {a: [1, 2]}})],
               ['done', $.toJSON({url: 'mock/custom', method: 'GET', data: {b: 'b', a: [1, 2]}})]
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
               ['done', $.toJSON({url: 'mock/custom', method: 'GET', data: {a: 'a', b: [3, 4], c: 12}})]
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
               ['done', $.toJSON({url: 'mock/custom/showoptions', method: 'GET', data: {c: 12}, options: $.extend({}, backend_options, {dataType: 'json'})})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.get({a: 'test'}, {sync: true, custom: true});

    deepEqual([
        ['done', $.toJSON({url: 'mock/custom/showoptions', method: 'GET', data: {c: 12}, options: $.extend({}, backend_options, {dataType: 'json'})})],
        ['done', $.toJSON({url: 'mock/custom/showoptions', method: 'GET', data: {a: 'test'}, options: $.extend({}, backend_options, {sync: true, dataType: 'json', custom: true})})]
       ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.get({b: 53}, {dataType: 'text'});

    deepEqual([
        ['done', $.toJSON({url: 'mock/custom/showoptions', method: 'GET', data: {c: 12}, options: $.extend({}, backend_options, {dataType: 'json'})})],
        ['done', $.toJSON({url: 'mock/custom/showoptions', method: 'GET', data: {a: 'test'}, options: $.extend({}, backend_options, {sync: true, dataType: 'json', custom: true})})],
        ['done', $.toJSON({url: 'mock/custom/showoptions', method: 'GET', data: {b: 53}, options: $.extend({}, backend_options, {dataType: 'text'})})]
       ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
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
    this.assertMockQueryErrorCalls([
            ['fail', '', 404]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/forbidden').get();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertMockQueryErrorCalls([
            ['fail', '', 404],
            ['fail', 'HTTP - Error 403', 403]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/error').get();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertMockQueryErrorCalls([
            ['fail', '', 404],
            ['fail', 'HTTP - Error 403', 403],
            ['fail', 'HTTP - Error 500', 500]
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
        ['fail', $.toJSON({url: 'mock/custom', method: 'GET', data: {a: 5}}), Error('invalid convert')]
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
    deepEqual([['cancel']], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('cancel'), this.mockListenerCalls('complete'));
});

QUnit.test('creme.ajax.Query.post (url)', function(assert) {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('mock/custom').post();

    deepEqual([
               ['done', $.toJSON({url: 'mock/custom', method: 'POST', data: {}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));

    query.url('mock/custom').post({a: [1, 2], b: 'a'});

    deepEqual([
               ['done', $.toJSON({url: 'mock/custom', method: 'POST', data: {}})],
               ['done', $.toJSON({url: 'mock/custom', method: 'POST', data: {a: [1, 2], b: 'a'}})]
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
    this.assertMockQueryErrorCalls([
            ['fail', '', 404]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/forbidden').post();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertMockQueryErrorCalls([
            ['fail', '', 404],
            ['fail', 'HTTP - Error 403', 403]
        ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/error').post();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    this.assertMockQueryErrorCalls([
            ['fail', '', 404],
            ['fail', 'HTTP - Error 403', 403],
            ['fail', 'HTTP - Error 500', 500]
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
               ['done', $.toJSON({url: 'mock/custom', method: 'GET', data: {}})]
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
               ['done', $.toJSON({url: 'mock/custom', method: 'POST', data: {}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
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
    deepEqual([
               ['fail', Error('no such backend action "unknown"')]
              ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

}(jQuery));
