module("creme.cacheajax.js", {
    setup: function() {
        var self = this;

        this.backend = new creme.ajax.MockAjaxBackend({delay: 0});
        $.extend(this.backend.GET, {'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                    'mock/error': this.backend.response(500, 'HTTP - Error 500'),
                                    'mock/default': function(url, data, options) {
                                        return self.backend.response(200, 'this is a test message %d'.format(self.backend.counts.GET));
                                    },
                                    'mock/html': function(url, data, options) {
                                        return self._custom_GET(url, data, options);
                                    }});

        $.extend(this.backend.POST, {'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                     'mock/error': this.backend.response(500, 'HTTP - Error 500'),
                                     'mock/html': function(url, data, options) {
                                         return self._custom_POST(url, data, options);
                                     }});
    },

    teardown: function() {
    },

    _custom_GET: function(url, data, options) {
        return this.backend.response(200, 'received data %s'.format($.toJSON(data)));
    },

    _custom_POST: function(url, data, options) {
        return this.backend.response(200, $.toJSON({url: url, method: 'POST', data: data}));
    },

    doRequest: function(backend, url, data, options)
    {
        var response = {}
        var options = $.extend({sync:true}, options);

        backend.get(url, data, function(responseText) {$.extend(response, {responseText:responseText, status: 200});},
                               function(responseText, xhr) {$.extend(response, xhr);},
                               options);

        return response;
    }
});

function assertCacheResponseOk(response, text)
{
    equal(response.responseText, text, 'valid response text');
    equal(response.message, undefined, 'valid response message');
    equal(response.status, 200, 'valid response status');
}

function assertCacheResponseError(response, error, message)
{
    equal(response.responseText, undefined, 'invalid response text');
    equal(response.message, message, 'invalid response message');
    equal(response.status, error, 'invalid response status');
}

function assertCacheEntry(backend, url, data, response)
{
    var entry = backend._getEntry(url, data, backend.options.dataType);

    equal(entry.url, url, 'cache entry url');
    equal(entry.data, data, 'cache entry data');
    equal(entry.dataType, backend.options.dataType, 'cache entry datatype');
    equal(entry.response.data, response, 'cache entry response');
}

test('CacheBackend.get (create entry)', function() {
    var cache = new creme.ajax.CacheBackend(this.backend);

    equal(0, Object.keys(cache.entries).length);
    equal(0, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/default');
    assertCacheResponseOk(response, 'this is a test message 1');

    equal(1, Object.keys(cache.entries).length);
    assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 1')

    equal(1, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/default');
    assertCacheResponseOk(response, 'this is a test message 1');

    equal(1, Object.keys(cache.entries).length);
    assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 1')

    equal(1, this.backend.counts.GET);
});

test('CacheBackend.get (create entry, unknown url)', function() {
    var cache = new creme.ajax.CacheBackend(this.backend);

    equal(0, Object.keys(cache.entries).length);
    equal(0, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/unknown');
    assertCacheResponseError(response, 404, '');

    equal(0, Object.keys(cache.entries).length);
    equal(1, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/unknown');
    assertCacheResponseError(response, 404, '');

    equal(0, Object.keys(cache.entries).length);
    equal(2, this.backend.counts.GET);
});

test('CacheBackend.get (force entry)', function() {
    var cache = new creme.ajax.CacheBackend(this.backend);

    equal(0, Object.keys(cache.entries).length);
    equal(0, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/default', undefined, {forcecache:true});
    assertCacheResponseOk(response, 'this is a test message 1');

    equal(1, Object.keys(cache.entries).length);
    assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 1');

    equal(1, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/default', undefined, {forcecache:true});
    assertCacheResponseOk(response, 'this is a test message 2');

    equal(1, Object.keys(cache.entries).length);
    assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 2');

    equal(2, this.backend.counts.GET);
});

test('CacheBackend.get (create entry, data)', function() {
    var cache = new creme.ajax.CacheBackend(this.backend);

    equal(0, Object.keys(cache.entries).length);
    equal(0, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/html', 'data 1');
    assertCacheResponseOk(response, 'received data "data 1"');

    equal(1, Object.keys(cache.entries).length);
    assertCacheEntry(cache, 'mock/html', 'data 1', 'received data "data 1"');

    equal(1, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/html', 'data 1');
    assertCacheResponseOk(response, 'received data "data 1"');

    equal(1, Object.keys(cache.entries).length);
    assertCacheEntry(cache, 'mock/html', 'data 1', 'received data "data 1"');

    equal(1, this.backend.counts.GET);
});

test('CacheBackend.get (create entry, data changes)', function() {
    var cache = new creme.ajax.CacheBackend(this.backend);

    equal(0, Object.keys(cache.entries).length);
    equal(0, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/html', 'data 1');
    assertCacheResponseOk(response, 'received data "data 1"');

    equal(1, Object.keys(cache.entries).length);
    assertCacheEntry(cache, 'mock/html', 'data 1', 'received data "data 1"');

    equal(1, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/html', 'data 2');
    assertCacheResponseOk(response, 'received data "data 2"');

    equal(2, Object.keys(cache.entries).length);
    assertCacheEntry(cache, 'mock/html', 'data 1', 'received data "data 1"');
    assertCacheEntry(cache, 'mock/html', 'data 2', 'received data "data 2"');

    equal(2, this.backend.counts.GET);

    var response = this.doRequest(cache, 'mock/html', 'data 2');
    assertCacheResponseOk(response, 'received data "data 2"');

    var response = this.doRequest(cache, 'mock/html', 'data 1');
    assertCacheResponseOk(response, 'received data "data 1"');

    equal(2, Object.keys(cache.entries).length);
    assertCacheEntry(cache, 'mock/html', 'data 1', 'received data "data 1"');
    assertCacheEntry(cache, 'mock/html', 'data 2', 'received data "data 2"');

    equal(2, this.backend.counts.GET);
});

test('CacheBackend.get (entry expired)', function() {

    var self = this;
    var condition = new creme.ajax.CacheBackendCondition(function() {return (condition.mock_expired === true)});
    var cache = new creme.ajax.CacheBackend(this.backend,
                                            {condition: condition});

    equal(0, Object.keys(cache.entries).length);
    equal(0, this.backend.counts.GET);

    equal(cache.condition.expired({state:undefined}), true);
    equal(cache.condition.expired({state:{}}), false);

    var response = this.doRequest(cache, 'mock/default');
    assertCacheResponseOk(response, 'this is a test message 1');

    equal(1, this.backend.counts.GET);
    equal(1, Object.keys(cache.entries).length);
    assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 1')

    equal(cache.condition.expired({state:{}}), false);

    var response = this.doRequest(cache, 'mock/default');
    assertCacheResponseOk(response, 'this is a test message 1');

    equal(1, this.backend.counts.GET);
    equal(1, Object.keys(cache.entries).length);
    assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 1')

    condition.mock_expired = true;
    equal(cache.condition.expired({state:{}}), true);

    var response = this.doRequest(cache, 'mock/default');
    assertCacheResponseOk(response, 'this is a test message 2');

    equal(1, Object.keys(cache.entries).length);
    assertCacheEntry(cache, 'mock/default', undefined, 'this is a test message 2')

    equal(2, this.backend.counts.GET);
});

asyncTest('CacheBackend.get (entry timeout, not expired)', function() {
    var self = this;
    var condition = new creme.ajax.CacheBackendTimeout(500);
    var cache = new creme.ajax.CacheBackend(this.backend, {condition: condition});

    equal(cache.condition.expired({state:undefined}), true);
    equal(cache.condition.expired({state:{time:new Date().getTime()}}), false);
    equal(cache.condition.expired({state:{time:(new Date().getTime() - 200)}}), false);
    equal(cache.condition.expired({state:{time:(new Date().getTime() - 500)}}), true);
    equal(cache.condition.expired({state:{time:(new Date().getTime() - 10000)}}), true);

    var response = this.doRequest(cache, 'mock/default');
    assertCacheResponseOk(response, 'this is a test message 1');

    setTimeout(function() {
        var response = self.doRequest(cache, 'mock/default');
        assertCacheResponseOk(response, 'this is a test message 1');
        start();
    }, 100);
});

asyncTest('CacheBackend.get (entry timeout, expired)', function() {
    var self = this;
    var condition = new creme.ajax.CacheBackendTimeout(500);
    var cache = new creme.ajax.CacheBackend(this.backend, {condition: condition});

    equal(cache.condition.expired({state:undefined}), true);
    equal(cache.condition.expired({state:{time:new Date().getTime()}}), false);
    equal(cache.condition.expired({state:{time:(new Date().getTime() - 200)}}), false);
    equal(cache.condition.expired({state:{time:(new Date().getTime() - 500)}}), true);
    equal(cache.condition.expired({state:{time:(new Date().getTime() - 10000)}}), true);

    var response = this.doRequest(cache, 'mock/default');
    assertCacheResponseOk(response, 'this is a test message 1');

    setTimeout(function() {
        var response = self.doRequest(cache, 'mock/default');
        assertCacheResponseOk(response, 'this is a test message 2');
        start();
    }, 700);
});

