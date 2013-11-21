module("creme.ajax.query.js", {
    setup: function()
    {
        var self = this;

        this.backend = new creme.ajax.MockAjaxBackend({sync:true});

        $.extend(this.backend.GET, {'mock/options/1': this.backend.response(200, ['a']),
                                    'mock/options/2': this.backend.response(200, ['a', 'b']),
                                    'mock/options/3': this.backend.response(200, ['a', 'b', 'c']),
                                    'mock/options/empty': this.backend.response(200, []),
                                    'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                    'mock/error': this.backend.response(500, 'HTTP - Error 500'),
                                    'mock/custom': function(url, data, options) {
                                         return self._custom_GET(url, data, options);
                                     }});

        $.extend(this.backend.POST, {'mock/add/widget': this.backend.response(200, '<json>' + $.toJSON({value:'', added:[1, 'newitem']}) + '</json>'),
                                     'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                     'mock/error': this.backend.response(500, 'HTTP - Error 500'),
                                     'mock/custom': function(url, data, options) {
                                         return self._custom_POST(url, data, options);
                                     }});

        this.resetMockCalls();
    },

    teardown: function() {
    },

    _custom_POST: function(url, data, options) {
        return this.backend.response(200, $.toJSON({url: url, method: 'POST', data: data}));
    },

    _custom_GET: function(url, data, options) {
        return this.backend.response(200, $.toJSON({url: url, method: 'GET', data: data}));
    },

    resetMockCalls: function() {
        this._eventListenerCalls = {};
    },

    mockListenerCalls: function(name)
    {
        if (this._eventListenerCalls[name] === undefined)
            this._eventListenerCalls[name] = [];

        return this._eventListenerCalls[name];
    },

    mockListener: function(name)
    {
        var self = this;
        return (function(name) {return function() {
            self.mockListenerCalls(name).push(Array.copy(arguments));
        }})(name);
    }
});

function assertMockQueryErrorCalls(expected, calls)
{
    equal(expected.length, calls.length, 'length');

    for(var i = 0; i < calls.length; ++i)
    {
        var call = calls[i];
        var expect = expected[i];

        equal(call[0], expect[0], 'event');
        equal(call[1], expect[1], 'data');
        equal(call[2].type, 'request');
        equal(call[2].status, expect[2], 'status');
        equal(call[2].message, expect[1], 'xhr message');
    }
}

test('creme.ajax.Query.constructor', function() {
    var query = new creme.ajax.Query({}, this.backend);

    equal(undefined, query.url());
    equal(this.backend, query.backend());
});

test('creme.ajax.Query.url (string)', function() {
    var query = new creme.ajax.Query({}, this.backend);

    equal(undefined, query.url());
    equal(this.backend, query.backend());

    query.url('mock/options/1');

    equal('mock/options/1', query.url());
    equal(this.backend, query.backend());
});

test('creme.ajax.Query.url (function)', function() {
    var query = new creme.ajax.Query({}, this.backend);
    var id = 1;
    var url = function() {
        return 'mock/options/%d'.format(id);
    }

    equal(undefined, query.url());
    equal(this.backend, query.backend());

    query.url(url);
    equal('mock/options/1', query.url());

    id = 2
    equal('mock/options/2', query.url());

    id = 3
    equal('mock/options/3', query.url());
});

test('creme.ajax.Query.get (empty url)', function() {
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

test('creme.ajax.Query.get (url)', function() {
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
               ['done', ['a', 'b', 'c']],
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

test('creme.ajax.Query.get (url, data)', function() {
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

test('creme.ajax.Query.get (fail)', function() {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('/mock/options/unkown').get();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    assertMockQueryErrorCalls([
                               ['fail', '', 404]
                              ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/forbidden').get();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    assertMockQueryErrorCalls([
                               ['fail', '', 404],
                               ['fail', 'HTTP - Error 403', 403]
                              ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/error').get();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    assertMockQueryErrorCalls([
                               ['fail', '', 404],
                               ['fail', 'HTTP - Error 403', 403],
                               ['fail', 'HTTP - Error 500', 500]
                              ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});

test('creme.ajax.Query.post (empty url)', function() {
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

test('creme.ajax.Query.post (url)', function() {
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

    query.url('mock/custom').post({a:[1, 2], b:'a'});

    deepEqual([
               ['done', $.toJSON({url: 'mock/custom', method: 'POST', data: {}})],
               ['done', $.toJSON({url: 'mock/custom', method: 'POST', data: {a:[1, 2], b:'a'}})]
              ], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    deepEqual([], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('success'), this.mockListenerCalls('complete'));
});

test('creme.ajax.Query.post (fail)', function() {
    var query = new creme.ajax.Query({}, this.backend);
    query.onDone(this.mockListener('success'));
    query.onCancel(this.mockListener('cancel'));
    query.onFail(this.mockListener('error'));
    query.onComplete(this.mockListener('complete'));

    query.url('/mock/unknown').post();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    assertMockQueryErrorCalls([
                               ['fail', '', 404]
                              ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/forbidden').post();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    assertMockQueryErrorCalls([
                               ['fail', '', 404],
                               ['fail', 'HTTP - Error 403', 403]
                              ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));

    query.url('mock/error').post();

    deepEqual([], this.mockListenerCalls('success'));
    deepEqual([], this.mockListenerCalls('cancel'));
    assertMockQueryErrorCalls([
                               ['fail', '', 404],
                               ['fail', 'HTTP - Error 403', 403],
                               ['fail', 'HTTP - Error 500', 500]
                              ], this.mockListenerCalls('error'));
    deepEqual(this.mockListenerCalls('error'), this.mockListenerCalls('complete'));
});
