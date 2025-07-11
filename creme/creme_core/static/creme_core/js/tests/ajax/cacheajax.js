(function($) {

QUnit.module("creme.cacheajax.js", new QUnitMixin(QUnitAjaxMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.cacheajax.js'});
    },

    beforeEach: function() {
        var self = this;

        this.setMockBackendGET({
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500'),
            'mock/default': function(url, data, options) {
                return self.backend.response(200, 'this is a test message %d'.format(self.backend.counts.GET));
            },
            'mock/html': function(url, data, options) {
                return self._custom_GET(url, data, options);
            }
        });

        this.setMockBackendPOST({
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
             'mock/error': this.backend.response(500, 'HTTP - Error 500'),
             'mock/html': function(url, data, options) {
                 return self._custom_POST(url, data, options);
             }
        });
    },

    _custom_GET: function(url, data, options) {
        return this.backend.response(200, 'received data %s'.format(JSON.stringify(data)));
    },

    _custom_POST: function(url, data, options) {
        return this.backend.responseJSON(200, {url: url, method: 'POST', data: data});
    },

    doRequest: function(backend, url, data, options) {
        options = $.extend({sync: true}, options);
        var response = {};

        backend.get(url, data, function(responseText) { $.extend(response, {responseText: responseText, status: 200}); },
                               function(responseText, xhr) { $.extend(response, xhr); },
                               options);

        return response;
    },

    assertCacheResponseOk: function(response, text) {
        var assert = this.assert;

        assert.equal(response.responseText, text, 'valid response text');
        assert.equal(response.message, undefined, 'valid response message');
        assert.equal(response.status, 200, 'valid response status');
    },

    assertCacheResponseError: function(response, error, message) {
        var assert = this.assert;

        assert.equal(response.responseText, undefined, 'invalid response text');
        assert.equal(response.message, message, 'invalid response message');
        assert.equal(response.status, error, 'invalid response status');
    },

    assertCacheEntry: function(backend, url, data, response) {
        var assert = this.assert;
        var entry = backend._getEntry(url, data, backend.options.dataType);

        assert.equal(entry.url, url, 'cache entry url');
        assert.equal(entry.data, data, 'cache entry data');
        assert.equal(entry.dataType, backend.options.dataType, 'cache entry datatype');
        assert.equal(entry.response.data, response, 'cache entry response');
    }
}));

QUnit.test('defaultBackend (invalid)', function(assert) {
    assert.deepEqual(this.backend, creme.ajax.defaultBackend());

    this.assertRaises(function() {
        creme.ajax.defaultBackend('not a backend');
    }, Error, 'Error: Default ajax backend must be a creme.ajax.Backend instance');
});

QUnit.test('defaultCacheBackend (invalid)', function(assert) {
    assert.deepEqual(this.backend, creme.ajax.defaultCacheBackend());

    this.assertRaises(function() {
        creme.ajax.defaultCacheBackend('not a backend');
    }, Error, 'Error: Default ajax cache backend must be a creme.ajax.Backend instance');
});

QUnit.test('CacheBackend.get (create entry)', function(assert) {
    var cache = new creme.ajax.CacheBackend(this.backend);

    assert.equal(0, Object.keys(cache.entries).length);
    assert.equal(0, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/default');
    this.assertCacheResponseOk(response, 'this is a test message 1');

    assert.equal(1, Object.keys(cache.entries).length);
    this.assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 1');

    assert.equal(1, this.backend.counts.GET);

    response = this.doRequest(cache, 'mock/default');
    this.assertCacheResponseOk(response, 'this is a test message 1');

    assert.equal(1, Object.keys(cache.entries).length);
    this.assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 1');

    assert.equal(1, this.backend.counts.GET);
});

QUnit.test('CacheBackend.get (create entry, unknown url)', function(assert) {
    var cache = new creme.ajax.CacheBackend(this.backend);

    assert.equal(0, Object.keys(cache.entries).length);
    assert.equal(0, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/unknown');
    this.assertCacheResponseError(response, 404, '');

    assert.equal(0, Object.keys(cache.entries).length);
    assert.equal(1, this.backend.counts.GET);

    response = this.doRequest(cache, 'mock/unknown');
    this.assertCacheResponseError(response, 404, '');

    assert.equal(0, Object.keys(cache.entries).length);
    assert.equal(2, this.backend.counts.GET);
});

QUnit.test('CacheBackend.get (force entry)', function(assert) {
    var cache = new creme.ajax.CacheBackend(this.backend);

    assert.equal(0, Object.keys(cache.entries).length);
    assert.equal(0, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/default', undefined, {forcecache: true});
    this.assertCacheResponseOk(response, 'this is a test message 1');

    assert.equal(1, Object.keys(cache.entries).length);
    this.assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 1');

    assert.equal(1, this.backend.counts.GET);

    response = this.doRequest(cache, 'mock/default', undefined, {forcecache: true});
    this.assertCacheResponseOk(response, 'this is a test message 2');

    assert.equal(1, Object.keys(cache.entries).length);
    this.assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 2');

    assert.equal(2, this.backend.counts.GET);
});

QUnit.test('CacheBackend.get (create entry, data)', function(assert) {
    var cache = new creme.ajax.CacheBackend(this.backend);

    assert.equal(0, Object.keys(cache.entries).length);
    assert.equal(0, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/html', 'data 1');
    this.assertCacheResponseOk(response, 'received data "data 1"');

    assert.equal(1, Object.keys(cache.entries).length);
    this.assertCacheEntry(cache, 'mock/html', 'data 1', 'received data "data 1"');

    assert.equal(1, this.backend.counts.GET);

    response = this.doRequest(cache, 'mock/html', 'data 1');
    this.assertCacheResponseOk(response, 'received data "data 1"');

    assert.equal(1, Object.keys(cache.entries).length);
    this.assertCacheEntry(cache, 'mock/html', 'data 1', 'received data "data 1"');

    assert.equal(1, this.backend.counts.GET);
});

QUnit.test('CacheBackend.get (create entry, data changes)', function(assert) {
    var cache = new creme.ajax.CacheBackend(this.backend);

    assert.equal(0, Object.keys(cache.entries).length);
    assert.equal(0, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/html', 'data 1');
    this.assertCacheResponseOk(response, 'received data "data 1"');

    assert.equal(1, Object.keys(cache.entries).length);
    this.assertCacheEntry(cache, 'mock/html', 'data 1', 'received data "data 1"');

    assert.equal(1, this.backend.counts.GET);

    response = this.doRequest(cache, 'mock/html', 'data 2');
    this.assertCacheResponseOk(response, 'received data "data 2"');

    assert.equal(2, Object.keys(cache.entries).length);
    this.assertCacheEntry(cache, 'mock/html', 'data 1', 'received data "data 1"');
    this.assertCacheEntry(cache, 'mock/html', 'data 2', 'received data "data 2"');

    assert.equal(2, this.backend.counts.GET);

    response = this.doRequest(cache, 'mock/html', 'data 2');
    this.assertCacheResponseOk(response, 'received data "data 2"');

    response = this.doRequest(cache, 'mock/html', 'data 1');
    this.assertCacheResponseOk(response, 'received data "data 1"');

    assert.equal(2, Object.keys(cache.entries).length);
    this.assertCacheEntry(cache, 'mock/html', 'data 1', 'received data "data 1"');
    this.assertCacheEntry(cache, 'mock/html', 'data 2', 'received data "data 2"');

    assert.equal(2, this.backend.counts.GET);
});

QUnit.test('CacheBackend.get (create entry, async)', function(assert) {
    var cache = new creme.ajax.CacheBackend(this.backend);

    assert.equal(0, Object.keys(cache.entries).length);
    assert.equal(0, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/default', {}, {delay: 200, sync: false});

    assert.equal(1, Object.keys(cache.entries).length);
    var entry = cache.entries[Object.keys(cache.entries)[0]];

    assert.equal(true, entry.waiting);
    assert.equal(undefined, entry.response);
    assert.equal(1, entry.events.listeners('complete').length);
    assert.equal(undefined, response.responseText);

    var done = assert.async();

    setTimeout(function() {
        assert.equal(false, entry.waiting);
        assert.deepEqual({data: 'this is a test message 1', textStatus: 'ok'}, entry.response);
        assert.equal(0, entry.events.listeners('complete').length);
        assert.deepEqual({responseText: 'this is a test message 1', status: 200}, response);
        done();
    }, 300);
});

QUnit.test('CacheBackend.get (create entry, async, 403)', function(assert) {
    var cache = new creme.ajax.CacheBackend(this.backend);

    assert.equal(0, Object.keys(cache.entries).length);
    assert.equal(0, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/forbidden', {}, {delay: 200, sync: false});

    assert.equal(1, Object.keys(cache.entries).length);
    var entry = cache.entries[Object.keys(cache.entries)[0]];

    assert.equal(true, entry.waiting);
    assert.equal(undefined, entry.response);
    assert.equal(1, entry.events.listeners('complete').length);
    assert.equal(undefined, response.responseText);

    var done = assert.async();

    setTimeout(function() {
        assert.equal(false, entry.waiting);
        assert.equal(undefined, entry.response);
        assert.equal(0, entry.events.listeners('complete').length);
        assert.equal('HTTP - Error 403', response.message);
        assert.equal(403, response.status);
        done();
    }, 300);
});

QUnit.test('CacheBackend.get (create entry, async, waiting queue)', function(assert) {
    var cache = new creme.ajax.CacheBackend(this.backend);

    assert.equal(0, Object.keys(cache.entries).length);
    assert.equal(0, this.backend.counts.GET);

    var response1 = this.doRequest(cache, 'mock/default', {}, {delay: 200, sync: false});
    var response2 = this.doRequest(cache, 'mock/default', {}, {delay: 200, sync: false});
    var response3 = this.doRequest(cache, 'mock/default', {}, {delay: 200, sync: false});

    assert.equal(1, Object.keys(cache.entries).length);
    var entry = cache.entries[Object.keys(cache.entries)[0]];

    assert.equal(true, entry.waiting);
    assert.equal(undefined, entry.response);
    assert.equal(3, entry.events.listeners('complete').length);
    assert.equal(undefined, response1.responseText);
    assert.equal(undefined, response2.responseText);
    assert.equal(undefined, response3.responseText);

    var done = assert.async();

    setTimeout(function() {
        assert.equal(false, entry.waiting);
        assert.deepEqual({data: 'this is a test message 1', textStatus: 'ok'}, entry.response);
        assert.equal(0, entry.events.listeners('complete').length);
        assert.deepEqual({responseText: 'this is a test message 1', status: 200}, response1);
        assert.deepEqual({responseText: 'this is a test message 1', status: 200}, response2);
        assert.deepEqual({responseText: 'this is a test message 1', status: 200}, response3);
        done();
    }, 300);
});


QUnit.test('CacheBackend.get (create entry, async, waiting queue, 403)', function(assert) {
    var cache = new creme.ajax.CacheBackend(this.backend);

    assert.equal(0, Object.keys(cache.entries).length);
    assert.equal(0, this.backend.counts.GET);

    var response1 = this.doRequest(cache, 'mock/forbidden', {}, {delay: 200, sync: false});
    var response2 = this.doRequest(cache, 'mock/forbidden', {}, {delay: 200, sync: false});
    var response3 = this.doRequest(cache, 'mock/forbidden', {}, {delay: 200, sync: false});

    assert.equal(1, Object.keys(cache.entries).length);
    var entry = cache.entries[Object.keys(cache.entries)[0]];

    assert.equal(true, entry.waiting);
    assert.equal(undefined, entry.response);
    assert.equal(3, entry.events.listeners('complete').length);
    assert.equal(undefined, response1.responseText);
    assert.equal(undefined, response2.responseText);
    assert.equal(undefined, response3.responseText);

    var done = assert.async();

    setTimeout(function() {
        assert.equal(false, entry.waiting);
        assert.equal(undefined, entry.response);
        assert.equal(0, entry.events.listeners('complete').length);
        assert.equal('HTTP - Error 403', response1.message); assert.equal(403, response1.status);
        assert.equal('HTTP - Error 403', response2.message); assert.equal(403, response2.status);
        assert.equal('HTTP - Error 403', response3.message); assert.equal(403, response3.status);
        done();
    }, 300);
});

QUnit.test('CacheBackend.get (entry expired)', function(assert) {
    var condition = new creme.ajax.CacheBackendCondition(function() { return (condition.mock_expired === true); });
    var cache = new creme.ajax.CacheBackend(this.backend,
                                            {condition: condition});

    assert.equal(0, Object.keys(cache.entries).length);
    assert.equal(0, this.backend.counts.GET);

    assert.equal(cache.condition.expired({state: undefined}), true);
    assert.equal(cache.condition.expired({state: {}}), false);

    var response = this.doRequest(cache, 'mock/default');
    this.assertCacheResponseOk(response, 'this is a test message 1');

    assert.equal(1, this.backend.counts.GET);
    assert.equal(1, Object.keys(cache.entries).length);
    this.assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 1');

    assert.equal(cache.condition.expired({state: {}}), false);

    response = this.doRequest(cache, 'mock/default');
    this.assertCacheResponseOk(response, 'this is a test message 1');

    assert.equal(1, this.backend.counts.GET);
    assert.equal(1, Object.keys(cache.entries).length);
    this.assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 1');

    condition.mock_expired = true;
    assert.equal(cache.condition.expired({state: {}}), true);

    response = this.doRequest(cache, 'mock/default');
    this.assertCacheResponseOk(response, 'this is a test message 2');

    assert.equal(1, Object.keys(cache.entries).length);
    this.assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 2');

    assert.equal(2, this.backend.counts.GET);
});

QUnit.test('CacheBackend.get (entry timeout, not expired)', function(assert) {
    var self = this;
    var condition = new creme.ajax.CacheBackendTimeout(500);
    var cache = new creme.ajax.CacheBackend(this.backend, {condition: condition});

    assert.equal(cache.condition.expired({state: undefined}), true);
    assert.equal(cache.condition.expired({state: {time: new Date().getTime()}}), false);
    assert.equal(cache.condition.expired({state: {time: (new Date().getTime() - 200)}}), false);
    assert.equal(cache.condition.expired({state: {time: (new Date().getTime() - 500)}}), true);
    assert.equal(cache.condition.expired({state: {time: (new Date().getTime() - 10000)}}), true);

    var response = this.doRequest(cache, 'mock/default');
    this.assertCacheResponseOk(response, 'this is a test message 1');

    var done = assert.async();

    setTimeout(function() {
        var response = self.doRequest(cache, 'mock/default');
        self.assertCacheResponseOk(response, 'this is a test message 1');
        done();
    }, 100);
});

QUnit.test('CacheBackend.get (entry timeout, expired)', function(assert) {
    var self = this;
    var condition = new creme.ajax.CacheBackendTimeout(500);
    var cache = new creme.ajax.CacheBackend(this.backend, {condition: condition});

    assert.equal(cache.condition.expired({state: undefined}), true);
    assert.equal(cache.condition.expired({state: {time: new Date().getTime()}}), false);
    assert.equal(cache.condition.expired({state: {time: (new Date().getTime() - 200)}}), false);
    assert.equal(cache.condition.expired({state: {time: (new Date().getTime() - 500)}}), true);
    assert.equal(cache.condition.expired({state: {time: (new Date().getTime() - 10000)}}), true);

    var response = this.doRequest(cache, 'mock/default');
    this.assertCacheResponseOk(response, 'this is a test message 1');

    var done = assert.async();

    setTimeout(function() {
        var response = self.doRequest(cache, 'mock/default');
        self.assertCacheResponseOk(response, 'this is a test message 2');
        done();
    }, 700);
});

QUnit.test('CacheBackend.reset', function(assert) {
    var condition = new creme.ajax.CacheBackendTimeout(500);
    var cache = new creme.ajax.CacheBackend(this.backend, {condition: condition});

    assert.equal(0, Object.keys(cache.entries).length);

    var response = this.doRequest(cache, 'mock/default');
    this.assertCacheResponseOk(response, 'this is a test message 1');
    assert.equal(1, Object.keys(cache.entries).length);

    response = this.doRequest(cache, 'mock/default');
    this.assertCacheResponseOk(response, 'this is a test message 1');
    assert.equal(1, Object.keys(cache.entries).length);

    cache.reset();
    assert.equal(0, Object.keys(cache.entries).length);

    response = this.doRequest(cache, 'mock/default');
    this.assertCacheResponseOk(response, 'this is a test message 2');
    assert.equal(1, Object.keys(cache.entries).length);

    response = this.doRequest(cache, 'mock/default');
    this.assertCacheResponseOk(response, 'this is a test message 2');
    assert.equal(1, Object.keys(cache.entries).length);
});
}(jQuery));
