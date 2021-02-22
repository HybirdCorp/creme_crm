/* globals FunctionFaker */

(function($) {

QUnit.module("creme.ajax.utils.js", new QUnitMixin(QUnitAjaxMixin,
                                                   QUnitEventMixin, {
    afterEach: function() {
        // reset csrftoken cookie
        document.cookie = 'csrftoken=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
    }
}));

QUnit.parametrize('creme.ajax.Backend (options)', [
    [{}, {dataType: 'html', sync: false, debug: false}],
    [{dataType: 'json'}, {dataType: 'json', sync: false, debug: false}],
    [{any: 'value'}, {dataType: 'html', sync: false, debug: false, any: 'value'}]
], function(options, expected, assert) {
    var backend = new creme.ajax.Backend(options);
    deepEqual(backend.options, expected);
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

    // retrieve internal callbacks from the ajaxSubmit call
    var ajaxCall = ajaxFaker.calls()[0][0];
    ok(Object.isFunc(ajaxCall.success));
    ok(Object.isFunc(ajaxCall.error));

    equal(ajaxCall.async, expected.async);
    equal(ajaxCall.type, expected.type);
    equal(ajaxCall.url, expected.url);
    equal(ajaxCall.dataType, expected.dataType);

    deepEqual(ajaxCall.data, expected.data);
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

    // retrieve internal callbacks from the ajaxSubmit call
    var ajaxCall = ajaxFaker.calls()[0][0];
    ok(Object.isFunc(ajaxCall.success));
    ok(Object.isFunc(ajaxCall.error));

    equal(ajaxCall.async, expected.async);
    equal(ajaxCall.type, expected.type);
    equal(ajaxCall.url, expected.url);
    equal(ajaxCall.dataType, expected.dataType);

    deepEqual(ajaxCall.data, expected.data);
});

QUnit.parametrize('creme.ajax.Backend.submit', [
    [{}, {}, {
        iframe: true,
        url: 'mock/a',
        data: {},
        headers: {
            'X-CSRFToken': 'my-token'
        }
    }],
    [{headers: {'X-Client-Id': 'my-key'}}, {action: 'mock/b'}, {
        iframe: true,
        url: 'mock/b',
        data: {},
        headers: {
            'X-CSRFToken': 'my-token',
            'X-Client-Id': 'my-key'
        }
    }],
    [{action: 'mock/b'}, {headers: {'X-Client-Id': 'my-key'}}, {
        iframe: true,
        url: 'mock/b',
        data: {},
        headers: {
            'X-CSRFToken': 'my-token',
            'X-Client-Id': 'my-key'
        }
    }],
    [{}, {data: {any: 'value'}, headers: {'X-Client-Id': 'my-key'}}, {
        iframe: true,
        url: 'mock/a',
        data: {
            any: 'value'
        },
        headers: {
            'X-CSRFToken': 'my-token',
            'X-Client-Id': 'my-key'
        }
    }]
], function(backendOptions, queryOptions, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};
    var submitFaker = new FunctionFaker({
        instance: $.fn, method: 'ajaxSubmit'
    });

    document.cookie = 'csrftoken=my-token';

    var form = $(
        '<form action="mock/a">' +
            '<input type="text" name="a" value="A"></input>' +
            '<input type="file" name="b"></input>' +
        '</form>'
    );

    submitFaker.with(function() {
        var backend = new creme.ajax.Backend(backendOptions);
        backend.submit(form, successCb, errorCb, queryOptions);
    });

    // retrieve internal callbacks from the ajaxSubmit call
    var submitCall = submitFaker.calls()[0][0];
    ok(Object.isFunc(submitCall.success));
    ok(Object.isFunc(submitCall.error));

    equal(form.attr('action'), expected.url);

    equal(submitCall.iframe, expected.iframe);
    deepEqual(submitCall.data || {}, expected.data);
    deepEqual(submitCall.headers, expected.headers);
});

QUnit.parametrize('creme.ajax.Backend (debug)', [
    [true, 3],
    [false, 0]
], function(isDebug, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};
    var submitFaker = new FunctionFaker({
        instance: $.fn, method: 'ajaxSubmit'
    });
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
        submitFaker.with(function() {
            ajaxFaker.with(function() {
                var backend = new creme.ajax.Backend({debug: isDebug});

                backend.get('mock/a', {}, successCb, errorCb, {});
                backend.post('mock/a', {}, successCb, errorCb, {});
                backend.submit(form, successCb, errorCb, {});
            });
        });
    });

    equal(submitFaker.count(), 1);
    equal(ajaxFaker.count(), 2);
    equal(logFaker.count(), expected);
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

        deepEqual(query.backend(), backend);
        equal(query.url(), 'mock/a');
        deepEqual(query.data(), {});

        equal(ajaxFaker.count(), 0);

        query.get();
        equal(ajaxFaker.count(), 1);
    });
});

}(jQuery));
