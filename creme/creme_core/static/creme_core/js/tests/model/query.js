(function($) {

QUnit.module("creme.model.query.js", new QUnitMixin(QUnitEventMixin, QUnitAjaxMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.model.query.js'});
    },

    beforeEach: function() {
        this.backend = new creme.ajax.MockAjaxBackend({sync: true});

        this.setMockBackendGET({
            'mock/options/1': this.backend.response(200, ['a']),
            'mock/options/2': this.backend.response(200, ['a', 'b']),
            'mock/options/3': this.backend.response(200, ['a', 'b', 'c']),
            'mock/options/diff': this.backend.response(200, {add: ['x'], remove: ['b', 'c'], update: [[0, 'y']]}),
            'mock/options/empty': this.backend.response(200, []),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500')
        });
    },

    assertMockQueryErrorCalls: function(expected, calls) {
        var assert = this.assert;

        assert.equal(expected.length, calls.length, 'length');

        for (var i = 0; i < calls.length; ++i) {
            var call = calls[i];
            var expect = expected[i];

            assert.equal(call[0], expect[0], 'event');
            assert.equal(call[1], expect[1], 'data');
            assert.equal(call[2].type, 'request');
            assert.equal(call[2].status, expect[2], 'status');
            assert.equal(call[2].message, expect[1], 'xhr message');
        }
    }
}));

QUnit.test('creme.model.AjaxArray.constructor', function(assert) {
    var model = new creme.model.AjaxArray(this.backend);

    assert.equal(undefined, model.url());
    assert.equal(this.backend, model.backend());
    assert.deepEqual([], model.all());

    model = new creme.model.AjaxArray(this.backend, [1, 2, 3]);

    assert.equal(undefined, model.url());
    assert.equal(this.backend, model.backend());
    assert.deepEqual([1, 2, 3], model.all());
});

QUnit.test('creme.model.AjaxArray.fetch (url: string)', function(assert) {
    var model = new creme.model.AjaxArray(this.backend);

    assert.equal(undefined, model.url());
    assert.equal(this.backend, model.backend());
    assert.deepEqual([], model.all());

    model.url('mock/options/1');

    assert.equal('mock/options/1', model.url());
    assert.equal(this.backend, model.backend());
    assert.deepEqual([], model.all());

    model.fetch();

    assert.equal('mock/options/1', model.url());
    assert.equal(this.backend, model.backend());
    assert.deepEqual(['a'], model.all());
});

QUnit.test('creme.model.AjaxArray.fetch (url: function)', function(assert) {
    var model = new creme.model.AjaxArray(this.backend);
    var id = 1;
    var url = function() {
        return 'mock/options/%d'.format(id);
    };

    assert.equal(undefined, model.url());
    assert.equal(this.backend, model.backend());
    assert.deepEqual([], model.all());

    model.url(url);

    assert.equal('mock/options/1', model.url()());
    assert.deepEqual([], model.all());

    model.fetch();

    assert.equal('mock/options/1', model.url()());
    assert.deepEqual(['a'], model.all());

    id = 3;

    assert.equal('mock/options/3', model.url()());
    assert.deepEqual(['a'], model.all());

    model.fetch();

    assert.equal('mock/options/3', model.url()());
    assert.deepEqual(['a', 'b', 'c'], model.all());
});

QUnit.test('creme.model.AjaxArray.fetch (array)', function(assert) {
    var model = new creme.model.AjaxArray(this.backend);
    model.bind('fetch-error', this.mockListener('fetch-error'));
    model.bind('fetch-done', this.mockListener('fetch-done'));

    model.fetch();

    assert.deepEqual([], this.mockListenerCalls('fetch-error'));
    assert.deepEqual([], this.mockListenerCalls('fetch-done'));

    model.url('mock/options/1').fetch();

    assert.deepEqual(['a'], model.all());
    assert.deepEqual([], this.mockListenerCalls('fetch-error'));
    assert.deepEqual([
               ['fetch-done', ['a']]
              ], this.mockListenerCalls('fetch-done'));

    model.url('mock/options/3').fetch();

    assert.deepEqual(['a', 'b', 'c'], model.all());
    assert.deepEqual([], this.mockListenerCalls('fetch-error'));
    assert.deepEqual([
               ['fetch-done', ['a']],
               ['fetch-done', ['a', 'b', 'c']]
              ], this.mockListenerCalls('fetch-done'));
});

QUnit.test('creme.model.AjaxArray.fetch (diff)', function(assert) {
    var model = new creme.model.AjaxArray(this.backend, ['a', 'b', 'c']);
    model.bind('fetch-error', this.mockListener('fetch-error'));
    model.bind('fetch-done', this.mockListener('fetch-done'));

    model.fetch();

    assert.deepEqual([], this.mockListenerCalls('fetch-error'));
    assert.deepEqual([], this.mockListenerCalls('fetch-done'));

    model.url('mock/options/diff').fetch();

    assert.deepEqual([], this.mockListenerCalls('fetch-error'));
    assert.deepEqual([
               ['fetch-done', {add: ['x'], remove: ['b', 'c'], update: [[0, 'y']]}]
              ], this.mockListenerCalls('fetch-done'));
});

QUnit.test('creme.model.AjaxArray.fetch (fail)', function(assert) {
    var model = new creme.model.AjaxArray(this.backend);
    model.bind('fetch-error', this.mockListener('fetch-error'));
    model.bind('fetch-done', this.mockListener('fetch-done'));

    model.fetch();

    assert.deepEqual([], this.mockListenerCalls('fetch-error'));
    assert.deepEqual([], this.mockListenerCalls('fetch-done'));

    model.url('mock/unknown').fetch();

    this.assertMockQueryErrorCalls([
                                    ['fetch-error', '', 404]
                                   ], this.mockListenerCalls('fetch-error'));
    assert.deepEqual([], this.mockListenerCalls('fetch-done'));

    model.url('mock/forbidden').fetch();

    this.assertMockQueryErrorCalls([
                                    ['fetch-error', '', 404],
                                    ['fetch-error', 'HTTP - Error 403', 403]
                                   ], this.mockListenerCalls('fetch-error'));
    assert.deepEqual([], this.mockListenerCalls('fetch-done'));

    model.url('mock/error').fetch();

    this.assertMockQueryErrorCalls([
                                    ['fetch-error', '', 404],
                                    ['fetch-error', 'HTTP - Error 403', 403],
                                    ['fetch-error', 'HTTP - Error 500', 500]
                                   ], this.mockListenerCalls('fetch-error'));
    assert.deepEqual([], this.mockListenerCalls('fetch-done'));
});

QUnit.test('creme.model.AjaxArray.fetch (debounce)', function(assert) {
    this.backend.options = {
        sync: false,
        delay: 100
    };

    var model = new creme.model.AjaxArray(this.backend);
    model.bind('fetch-error', this.mockListener('fetch-error'));
    model.bind('fetch-done', this.mockListener('fetch-done'));
    model.bind('fetch-cancel', this.mockListener('fetch-cancel'));

    assert.deepEqual([], model.all());

    model.url('mock/options/1');
    model.fetch();

    model.url('mock/options/2');
    model.fetch();

    model.url('mock/options/3');
    model.fetch();

    var done = assert.async();
    var self = this;

    setTimeout(function() {
        assert.deepEqual([
                   ['fetch-cancel'],
                   ['fetch-cancel']
                  ], self.mockListenerCalls('fetch-cancel'));
        assert.deepEqual([
                   ['fetch-done', ['a', 'b', 'c']]
                  ], self.mockListenerCalls('fetch-done'));
        assert.deepEqual([], self.mockListenerCalls('fetch-error'));
        assert.deepEqual(['a', 'b', 'c'], model.all());
        done();
    }, 200);
});


QUnit.test('creme.model.AjaxArray.converter', function(assert) {
    var model = new creme.model.AjaxArray(this.backend);
    var converter = function(data) {
        return data.map(function(item, index) { return [item, index]; });
    };

    model.url('mock/options/3');
    assert.deepEqual(['a', 'b', 'c'], model.fetch().all());

    model.converter(converter);
    assert.deepEqual([['a', 0], ['b', 1], ['c', 2]], model.fetch().all());
});

QUnit.test('creme.model.AjaxArray.initial (array)', function(assert) {
    var initial = [1, 2, 3];
    var model = new creme.model.AjaxArray(this.backend, initial);

    assert.equal(undefined, model.url());
    assert.equal(this.backend, model.backend());
    assert.deepEqual([1, 2, 3], model.all());
});

QUnit.test('creme.model.AjaxArray.initial (function)', function(assert) {
    var initial = function() { return [4, 5, 6]; };
    var model = new creme.model.AjaxArray(this.backend, initial);

    assert.equal(undefined, model.url());
    assert.equal(this.backend, model.backend());
    assert.deepEqual([4, 5, 6], model.all());

    model.url('mock/options/3');
    assert.deepEqual(['a', 'b', 'c'], model.fetch().all());

    model.url('mock/options/empty');
    assert.deepEqual([], model.fetch().all());

    model.url('mock/forbidden');
    assert.deepEqual([4, 5, 6], model.fetch().all());
});

QUnit.test('creme.model.AjaxArray.fetch (listeners)', function(assert) {
    var model = new creme.model.AjaxArray(this.backend);
    var query_listener = {
        fail: this.mockListener('failed'),
        cancel: this.mockListener('canceled'),
        done: this.mockListener('succeded')
    };

    model.fetch({}, {}, query_listener);

    assert.deepEqual([], this.mockListenerCalls('failed'));
    assert.deepEqual([['cancel']], this.mockListenerCalls('canceled'));
    assert.deepEqual([], this.mockListenerCalls('succeded'));

    this.resetMockListenerCalls();
    model.url('mock/options/1').fetch({}, {}, query_listener);
    assert.deepEqual(['a'], model.all());

    assert.deepEqual([], this.mockListenerCalls('failed'));
    assert.deepEqual([], this.mockListenerCalls('canceled'));
    assert.deepEqual([['done', ['a']]], this.mockListenerCalls('succeded'));

    this.resetMockListenerCalls();
    model.url('mock/options/3').fetch({}, {}, query_listener);
    assert.deepEqual(['a', 'b', 'c'], model.all());

    assert.deepEqual([], this.mockListenerCalls('failed'));
    assert.deepEqual([], this.mockListenerCalls('canceled'));
    assert.deepEqual([['done', ['a', 'b', 'c']]], this.mockListenerCalls('succeded'));

    this.resetMockListenerCalls();
    model.url('mock/unknown').fetch({}, {}, query_listener);
    assert.deepEqual([], model.all());

    this.assertMockQueryErrorCalls([
                                    ['fail', '', 404]
                                   ], this.mockListenerCalls('failed'));
    assert.deepEqual([], this.mockListenerCalls('canceled'));
    assert.deepEqual([], this.mockListenerCalls('succeded'));
});

}(jQuery));

