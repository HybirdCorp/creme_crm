/* globals FunctionFaker */

(function($) {

QUnit.module("creme.ajax.Backend", new QUnitMixin(QUnitAjaxMixin,
                                                  QUnitEventMixin, {
    afterEach: function() {
        // reset csrftoken cookie
        document.cookie = 'csrftoken=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
    }
}));

QUnit.parametrize('creme.ajax.Backend (options)', [
    [{}, {dataType: 'html', sync: false, debug: false, traditional: true}],
    [{dataType: 'json'}, {dataType: 'json', sync: false, debug: false, traditional: true}],
    [{any: 'value'}, {dataType: 'html', sync: false, debug: false, any: 'value', traditional: true}]
], function(options, expected, assert) {
    var backend = new creme.ajax.Backend(options);
    assert.deepEqual(backend.options, expected);
});

QUnit.parametrize('creme.ajax.Backend.get', [
    [{}, 'mock/a', {}, {}, {
        url: 'mock/a', type: 'GET', async: true, data: {}, dataType: 'html'
    }],
    [{dataType: 'json'}, 'mock/a', {}, {}, {
        url: 'mock/a', type: 'GET', async: true, data: {}, dataType: 'json'
    }],
    [{dataType: 'json'}, 'mock/a', {}, {dataType: 'text'}, {
        url: 'mock/a', type: 'GET', async: true, data: {}, dataType: 'text'
    }]
], function(backendOptions, url, data, queryOptions, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        var backend = new creme.ajax.Backend(backendOptions);
        backend.get(url, data, successCb, errorCb, queryOptions);
    });

    // retrieve internal callbacks from the $.ajax call
    var ajaxCall = ajaxFaker.calls()[0][0];
    assert.ok(Object.isFunc(ajaxCall.success));
    assert.ok(Object.isFunc(ajaxCall.error));

    assert.equal(ajaxCall.async, expected.async);
    assert.equal(ajaxCall.type, expected.type);
    assert.equal(ajaxCall.url, expected.url);
    assert.equal(ajaxCall.dataType, expected.dataType);

    assert.deepEqual(ajaxCall.data, expected.data);
});

QUnit.parametrize('creme.ajax.Backend.post', [
    [{}, 'mock/a', {}, {}, {
        url: 'mock/a', type: 'POST', async: true, data: {}, dataType: 'html'
    }],
    [{dataType: 'json'}, 'mock/a', {}, {}, {
        url: 'mock/a', type: 'POST', async: true, data: {}, dataType: 'json'
    }],
    [{dataType: 'json'}, 'mock/a', {}, {dataType: 'text'}, {
        url: 'mock/a', type: 'POST', async: true, data: {}, dataType: 'text'
    }]
], function(backendOptions, url, data, queryOptions, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        var backend = new creme.ajax.Backend(backendOptions);
        backend.post(url, data, successCb, errorCb, queryOptions);
    });

    // retrieve internal callbacks from the $.ajax call
    var ajaxCall = ajaxFaker.calls()[0][0];
    assert.ok(Object.isFunc(ajaxCall.success));
    assert.ok(Object.isFunc(ajaxCall.error));

    assert.equal(ajaxCall.async, expected.async);
    assert.equal(ajaxCall.type, expected.type);
    assert.equal(ajaxCall.url, expected.url);
    assert.equal(ajaxCall.dataType, expected.dataType);

    assert.deepEqual(ajaxCall.data, expected.data);
});

QUnit.parametrize('creme.ajax.Backend.submit', [
    [{}, {}, {
        traditional: true,
        url: 'mock/a',
        data: {},
        headers: {
            'X-CSRFToken': 'my-token'
        }
    }],
    [{traditional: false}, {}, {
        traditional: false,
        url: 'mock/a',
        data: {},
        headers: {
            'X-CSRFToken': 'my-token'
        }
    }],
    [{headers: {'X-Client-Id': 'my-key'}}, {action: 'mock/b'}, {
        traditional: true,
        url: 'mock/b',
        data: {},
        headers: {
            'X-CSRFToken': 'my-token',
            'X-Client-Id': 'my-key'
        }
    }],
    [{action: 'mock/b'}, {headers: {'X-Client-Id': 'my-key'}}, {
        traditional: true,
        url: 'mock/b',
        data: {},
        headers: {
            'X-CSRFToken': 'my-token',
            'X-Client-Id': 'my-key'
        }
    }],
    [{}, {data: {any: 'value'}, headers: {'X-Client-Id': 'my-key'}}, {
        traditional: true,
        url: 'mock/a',
        data: {
            text: 'A',
            file: null,
            any: 'value'
        },
        headers: {
            'X-CSRFToken': 'my-token',
            'X-Client-Id': 'my-key'
        }
    }],
    [{}, {data: {any: [1, 2, 3], text: 'B'}, headers: {'X-Client-Id': 'my-key'}}, {
        traditional: true,
        url: 'mock/a',
        data: {
            text: 'B',
            file: null,
            any: [1, 2, 3]
        },
        headers: {
            'X-CSRFToken': 'my-token',
            'X-Client-Id': 'my-key'
        }
    }]
], function(backendOptions, queryOptions, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    document.cookie = 'csrftoken=my-token';

    var form = $(
        '<form action="mock/a">' +
            '<input type="text" name="a" value="A"></input>' +
            '<input type="file" name="b"></input>' +
        '</form>'
    );

    ajaxFaker.with(function() {
        var backend = new creme.ajax.Backend(backendOptions);
        backend.submit(form, successCb, errorCb, queryOptions);
    });

    // retrieve internal callbacks from the $.ajax call
    var ajaxCall = ajaxFaker.calls()[0][0];
    assert.ok(Object.isFunc(ajaxCall.success));
    assert.ok(Object.isFunc(ajaxCall.error));

    assert.equal(ajaxCall.url, expected.url);

    assert.equal(ajaxCall.traditional, expected.traditional);
    assert.deepEqual(ajaxCall.data || new FormData(), _.toFormData(expected.data));
    assert.deepEqual(ajaxCall.headers, expected.headers);
});

QUnit.parametrize('creme.ajax.Backend (debug)', [
    [true, 3],
    [false, 0]
], function(isDebug, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });
    var logFaker = new FunctionFaker({
        instance: console, method: 'log'
    });

    var form = $(
        '<form action="mock/a"><input type="text" name="a" value="A"></input></form>'
    );

    logFaker.with(function() {
        ajaxFaker.with(function() {
            var backend = new creme.ajax.Backend({debug: isDebug});

            backend.get('mock/a', {}, successCb, errorCb, {});
            backend.post('mock/a', {}, successCb, errorCb, {});
            backend.submit(form, successCb, errorCb, {});
        });
    });

    assert.equal(ajaxFaker.count(), 3);
    assert.equal(logFaker.count(), expected);
});

QUnit.test('creme.ajax.Backend.query', function(assert) {
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        var backend = new creme.ajax.Backend();
        var query = backend.query({
            sync: true
        }).url('mock/a');

        assert.deepEqual(query.backend(), backend);
        assert.equal(query.url(), 'mock/a');
        assert.deepEqual(query.data(), {});

        assert.equal(ajaxFaker.count(), 0);

        query.get();
        assert.equal(ajaxFaker.count(), 1);
    });
});

}(jQuery));
