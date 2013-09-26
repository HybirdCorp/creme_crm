module("creme.model.query.js", {
    setup: function()
    {
        this.backend = new creme.ajax.MockAjaxBackend({sync:true});

        $.extend(this.backend.GET, {'mock/options/1': this.backend.response(200, ['a']),
                                    'mock/options/2': this.backend.response(200, ['a', 'b']),
                                    'mock/options/3': this.backend.response(200, ['a', 'b', 'c']),
                                    'mock/options/diff': this.backend.response(200, {add:['x'], remove:['b', 'c'], update:[[0, 'y']]}),
                                    'mock/options/empty': this.backend.response(200, []),
                                    'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                    'mock/error': this.backend.response(500, 'HTTP - Error 500')});

        this.resetMockCalls();
    },

    teardown: function() {
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

test('creme.model.AjaxArray.constructor', function() {
    var model = new creme.model.AjaxArray(this.backend);

    equal(undefined, model.url());
    equal(this.backend, model.backend());
    deepEqual([], model.all());

    var model = new creme.model.AjaxArray(this.backend, [1, 2, 3]);

    equal(undefined, model.url());
    equal(this.backend, model.backend());
    deepEqual([1, 2, 3], model.all());
});

test('creme.model.AjaxArray.url (string)', function() {
    var model = new creme.model.AjaxArray(this.backend);

    equal(undefined, model.url());
    equal(this.backend, model.backend());
    deepEqual([], model.all());

    model.url('mock/options/1');

    equal('mock/options/1', model.url());
    equal(this.backend, model.backend());
    deepEqual([], model.all());

    model.fetch();

    equal('mock/options/1', model.url());
    equal(this.backend, model.backend());
    deepEqual(['a'], model.all());
});

test('creme.model.AjaxArray.url (function)', function() {
    var model = new creme.model.AjaxArray(this.backend);
    var id = 1;
    var url = function() {
        return 'mock/options/%d'.format(id);
    }

    equal(undefined, model.url());
    equal(this.backend, model.backend());
    deepEqual([], model.all());

    model.url(url);

    equal('mock/options/1', model.url()());
    deepEqual([], model.all());

    model.fetch();

    equal('mock/options/1', model.url()());
    deepEqual(['a'], model.all());

    id = 3;

    equal('mock/options/3', model.url()());
    deepEqual(['a'], model.all());

    model.fetch();

    equal('mock/options/3', model.url()());
    deepEqual(['a', 'b', 'c'], model.all());
});

test('creme.model.AjaxArray._update (array)', function() {
    var model = new creme.model.AjaxArray(this.backend);
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    deepEqual([], this.mockListenerCalls('model'));
    deepEqual([], model.all());

    model._update(['a', 'b', 'c']);

    deepEqual(['a', 'b', 'c'], model.all());
    deepEqual([['add', ['a', 'b', 'c'], 0, 2, 'reset'], ['reset']], this.mockListenerCalls('model'));

    this.resetMockCalls();
    model._update(['x', 'y', 'z', 'w']);

    deepEqual(['x', 'y', 'z', 'w'], model.all());
    deepEqual([['update', ['x', 'y', 'z'], 0, 2, ['a', 'b', 'c'], 'reset'],
               ['add', ['w'], 3, 3, 'reset'],
               ['reset']], this.mockListenerCalls('model'));
});

test('creme.model.AjaxArray._update (diff, add)', function() {
    var model = new creme.model.AjaxArray(this.backend);
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    deepEqual([], this.mockListenerCalls('model'));
    deepEqual([], model.all());

    model._update({add:['x', 'y']});

    deepEqual(['x', 'y'], model.all());
    deepEqual([['add', ['x', 'y'], 0, 1, 'insert']], this.mockListenerCalls('model'));
});

test('creme.model.AjaxArray._update (diff, remove)', function() {
    var model = new creme.model.AjaxArray(this.backend, ['a', 'b', 'c']);
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    deepEqual([], this.mockListenerCalls('model'));
    deepEqual(['a', 'b', 'c'], model.all());

    model._update({remove:['b', 'c']});

    deepEqual(['a'], model.all());
    deepEqual([['remove', ['b'], 1, 1, 'remove'],
               ['remove', ['c'], 1, 1, 'remove']], this.mockListenerCalls('model'));
});

test('creme.model.AjaxArray._update (diff, update)', function() {
    var model = new creme.model.AjaxArray(this.backend, ['a', 'b', 'c']);
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    deepEqual([], this.mockListenerCalls('model'));
    deepEqual(['a', 'b', 'c'], model.all());

    model._update({update:[['y', 0], ['k', 2]]});

    deepEqual(['y', 'b', 'k'], model.all());
    deepEqual([['update', ['y'], 0, 0, ['a'], 'set'],
               ['update', ['k'], 2, 2, ['c'], 'set']], this.mockListenerCalls('model'));
});

test('creme.model.AjaxArray.fetch (array)', function() {
    var model = new creme.model.AjaxArray(this.backend);
    model.bind('fetch-error', this.mockListener('fetch-error'));
    model.bind('fetch-done', this.mockListener('fetch-done'));

    model.fetch();

    deepEqual([], this.mockListenerCalls('fetch-error'));
    deepEqual([], this.mockListenerCalls('fetch-done'));

    model.url('mock/options/1').fetch();

    deepEqual(['a'], model.all());
    deepEqual([], this.mockListenerCalls('fetch-error'));
    deepEqual([
               ['fetch-done', ['a']]
              ], this.mockListenerCalls('fetch-done'));

    model.url('mock/options/3').fetch();

    deepEqual(['a', 'b', 'c'], model.all());
    deepEqual([], this.mockListenerCalls('fetch-error'));
    deepEqual([
               ['fetch-done', ['a']],
               ['fetch-done', ['a', 'b', 'c']]
              ], this.mockListenerCalls('fetch-done'));
});

test('creme.model.AjaxArray.fetch (diff)', function() {
    var model = new creme.model.AjaxArray(this.backend, ['a', 'b', 'c']);
    model.bind('fetch-error', this.mockListener('fetch-error'));
    model.bind('fetch-done', this.mockListener('fetch-done'));

    model.fetch();

    deepEqual([], this.mockListenerCalls('fetch-error'));
    deepEqual([], this.mockListenerCalls('fetch-done'));

    model.url('mock/options/diff').fetch();

    deepEqual([], this.mockListenerCalls('fetch-error'));
    deepEqual([
               ['fetch-done', {add:['x'], remove:['b', 'c'], update:[[0, 'y']]}]
              ], this.mockListenerCalls('fetch-done'));
});

test('creme.model.AjaxArray.fetch (fail)', function() {
    var model = new creme.model.AjaxArray(this.backend);
    model.bind('fetch-error', this.mockListener('fetch-error'));
    model.bind('fetch-done', this.mockListener('fetch-done'));

    model.fetch();

    deepEqual([], this.mockListenerCalls('fetch-error'));
    deepEqual([], this.mockListenerCalls('fetch-done'));

    model.url('mock/unknown').fetch();

    assertMockQueryErrorCalls([
                               ['fetch-error', '', 404]
                              ], this.mockListenerCalls('fetch-error'));
    deepEqual([], this.mockListenerCalls('fetch-done'));

    model.url('mock/forbidden').fetch();

    assertMockQueryErrorCalls([
                               ['fetch-error', '', 404],
                               ['fetch-error', 'HTTP - Error 403', 403]
                              ], this.mockListenerCalls('fetch-error'));
    deepEqual([], this.mockListenerCalls('fetch-done'));

    model.url('mock/error').fetch();

    assertMockQueryErrorCalls([
                               ['fetch-error', '', 404],
                               ['fetch-error', 'HTTP - Error 403', 403],
                               ['fetch-error', 'HTTP - Error 500', 500]
                              ], this.mockListenerCalls('fetch-error'));
    deepEqual([], this.mockListenerCalls('fetch-done'));
});

test('creme.model.AjaxArray.converter', function() {
    var model = new creme.model.AjaxArray(this.backend);
    var converter = function(data) {
        return data.map(function(item, index) {return [item, index];});
    };

    model.url('mock/options/3');
    deepEqual(['a', 'b', 'c'], model.fetch().all());

    model.converter(converter);
    deepEqual([['a', 0], ['b', 1], ['c', 2]], model.fetch().all());
});

test('creme.model.AjaxArray.initial (array)', function() {
    var initial = [1, 2, 3];
    var model = new creme.model.AjaxArray(this.backend, initial);

    equal(undefined, model.url());
    equal(this.backend, model.backend());
    deepEqual([1, 2, 3], model.all());
});

test('creme.model.AjaxArray.initial (function)', function() {
    var initial = function() {return [4, 5, 6];}
    var model = new creme.model.AjaxArray(this.backend, initial);

    equal(undefined, model.url());
    equal(this.backend, model.backend());
    deepEqual([4, 5, 6], model.all());

    model.url('mock/options/3');
    deepEqual(['a', 'b', 'c'], model.fetch().all());

    model.url('mock/options/empty');
    deepEqual([], model.fetch().all());

    model.url('mock/forbidden');
    deepEqual([4, 5, 6], model.fetch().all());
});

test('creme.model.AjaxArray.fetch (listeners)', function() {
    var model = new creme.model.AjaxArray(this.backend);
    var query_listener = {
        fail: this.mockListener('failed'),
        cancel: this.mockListener('canceled'),
        done: this.mockListener('succeded')
    };

    model.fetch({}, {}, query_listener);

    deepEqual([], this.mockListenerCalls('failed'));
    deepEqual([['cancel']], this.mockListenerCalls('canceled'));
    deepEqual([], this.mockListenerCalls('succeded'));

    this.resetMockCalls();
    model.url('mock/options/1').fetch({}, {}, query_listener);
    deepEqual(['a'], model.all());

    deepEqual([], this.mockListenerCalls('failed'));
    deepEqual([], this.mockListenerCalls('canceled'));
    deepEqual([['done', ['a']]], this.mockListenerCalls('succeded'));

    this.resetMockCalls();
    model.url('mock/options/3').fetch({}, {}, query_listener);
    deepEqual(['a', 'b', 'c'], model.all());

    deepEqual([], this.mockListenerCalls('failed'));
    deepEqual([], this.mockListenerCalls('canceled'));
    deepEqual([['done', ['a', 'b', 'c']]], this.mockListenerCalls('succeded'));

    this.resetMockCalls();
    model.url('mock/unknown').fetch({}, {}, query_listener);
    deepEqual([], model.all());

    assertMockQueryErrorCalls([
                               ['fail', '', 404]
                              ], this.mockListenerCalls('failed'));
    deepEqual([], this.mockListenerCalls('canceled'));
    deepEqual([], this.mockListenerCalls('succeded'));
});
