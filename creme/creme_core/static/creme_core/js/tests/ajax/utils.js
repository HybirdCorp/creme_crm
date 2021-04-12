/* globals FunctionFaker */

(function($) {

QUnit.module("creme.ajax.utils.js", new QUnitMixin(QUnitAjaxMixin, QUnitEventMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.ajax.utils.js'});
    },

    afterEach: function() {
        // reset csrftoken cookie
        document.cookie = 'csrftoken=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
    },

    assertUrlSearchData: function(expected, data) {
        equal(expected.search, data.search);
        deepEqual(expected.searchData, data.searchData);
    }
}));

QUnit.test('creme.ajax.parseUrl (no data)', function(assert) {
    deepEqual({
        href: 'http://joe:pwd@admin.com:8080/this/is/a/test#hash',
        protocol: 'http:',
        username: 'joe',
        password: 'pwd',
        host: 'admin.com:8080',
        hostname: 'admin.com',
        port: '8080',
        pathname: '/this/is/a/test',
        search: '',
        searchData: {},
        hash: '#hash'
    }, creme.ajax.parseUrl('http://joe:pwd@admin.com:8080/this/is/a/test#hash'));

    deepEqual({
        href: 'http://admin.com/this/is/a/test/?#hash',
        protocol: 'http:',
        username: '',
        password: '',
        host: 'admin.com',
        hostname: 'admin.com',
        port: '',
        pathname: '/this/is/a/test/',
        search: '',
        searchData: {},
        hash: '#hash'
    }, creme.ajax.parseUrl('http://admin.com/this/is/a/test/?#hash'));

    deepEqual({
        href: 'http://admin.com:8080/this/is/a/test?',
        protocol: 'http:',
        username: '',
        password: '',
        host: 'admin.com:8080',
        hostname: 'admin.com',
        port: '8080',
        pathname: '/this/is/a/test',
        search: '',
        searchData: {},
        hash: ''
    }, creme.ajax.parseUrl('http://admin.com:8080/this/is/a/test?'));
});

QUnit.test('creme.ajax.parseUrl', function(assert) {
    this.assertUrlSearchData({
        search: '?a=1&b=2&c=true&d=',
        searchData: {
            a: '1',
            b: '2',
            c: 'true',
            d: ''
        }
    }, creme.ajax.parseUrl('/this/is/a/test?a=1&b=2&c=true&d='));
});

QUnit.test('creme.ajax.parseUrl (list)', function(assert) {
    this.assertUrlSearchData({
        search: '?a=1&a=2&a=true&b=2&c=a&c=b&d=&d=',
        searchData: {
            a: ['1', '2', 'true'],
            b: '2',
            c: ['a', 'b'],
            d: ['', '']
        }
    }, creme.ajax.parseUrl('/this/is/a/test?a=1&a=2&a=true&b=2&c=a&c=b&d=&d='));
});

QUnit.test('creme.ajax.parseUrl (encoded)', function(assert) {
    this.assertUrlSearchData({
        search: '?a%5Bone%5D=1&a%5Btwo%5D=2&a%5Bthree%5D=3&b=b%3D1%2C2%2C3&c%5B%5D=1&c%5B%5D=2&c%5B%5D=3',
        searchData: {
            'a[one]': '1',
            'a[two]': '2',
            'a[three]': '3',
            b: 'b=1,2,3',
            'c[]': ['1', '2', '3']
        }
    }, creme.ajax.parseUrl('/this/is/a/test?a%5Bone%5D=1&a%5Btwo%5D=2&a%5Bthree%5D=3&b=b%3D1%2C2%2C3&c%5B%5D=1&c%5B%5D=2&c%5B%5D=3'));
});

QUnit.test('creme.ajax.param', function(assert) {
    equal('a=12&b=1&b=2&d=', creme.ajax.param({a: 12, b: [1, 2], c: [], d: ''}));
});

QUnit.test('creme.ajax.URL (properties)', function(assert) {
    deepEqual({
        href: 'http://joe:pwd@admin.com:8080/this/is/a/test#hash',
        protocol: 'http:',
        username: 'joe',
        password: 'pwd',
        host: 'admin.com:8080',
        hostname: 'admin.com',
        port: '8080',
        pathname: '/this/is/a/test',
        search: '',
        searchData: {},
        hash: '#hash'
    }, new creme.ajax.URL('http://joe:pwd@admin.com:8080/this/is/a/test#hash').properties());

    deepEqual({
        href: 'http://admin.com/this/is/a/test/?#hash',
        protocol: 'http:',
        username: '',
        password: '',
        host: 'admin.com',
        hostname: 'admin.com',
        port: '',
        pathname: '/this/is/a/test/',
        search: '',
        searchData: {},
        hash: '#hash'
    }, new creme.ajax.URL('http://admin.com/this/is/a/test/?#hash').properties());

    deepEqual({
        href: 'http://admin.com:8080/this/is/a/test?',
        protocol: 'http:',
        username: '',
        password: '',
        host: 'admin.com:8080',
        hostname: 'admin.com',
        port: '8080',
        pathname: '/this/is/a/test',
        search: '',
        searchData: {},
        hash: ''
    }, new creme.ajax.URL('http://admin.com:8080/this/is/a/test?').properties());
});

QUnit.test('creme.ajax.URL (property)', function(assert) {
    var url = new creme.ajax.URL('http://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');

    equal('http://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.protocol('https:');
    equal('https://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.username('other');
    equal('https://other:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.password('password');
    equal('https://other:password@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.host('other.admin.com:8085');
    equal('https://other:password@other.admin.com:8085/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.hostname('yetanother.admin.com');
    equal('https://other:password@yetanother.admin.com:8085/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.port('8090');
    equal('https://other:password@yetanother.admin.com:8090/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.pathname('/this/is/another/test');
    equal('https://other:password@yetanother.admin.com:8090/this/is/another/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.hash('#hackish');
    equal('https://other:password@yetanother.admin.com:8090/this/is/another/test?a=1&a=2&b=true&c=a&d=&d=#hackish', url.href());
});

QUnit.test('creme.ajax.URL (searchData)', function(assert) {
    deepEqual({
        a: '1',
        b: '2',
        c: 'true',
        d: ''
    }, new creme.ajax.URL('/this/is/a/test?a=1&b=2&c=true&d=').searchData());

    deepEqual({
        a: ['1', '2', 'true'],
        b: '2',
        c: ['a', 'b'],
        d: ['', '']
    }, new creme.ajax.URL('/this/is/a/test?a=1&a=2&a=true&b=2&c=a&c=b&d=&d=').searchData());

    deepEqual({
        'a[one]': '1',
        'a[two]': '2',
        'a[three]': '3',
        b: 'b=1,2,3',
        'c[]': ['1', '2', '3']
    }, new creme.ajax.URL('/this/is/a/test?a%5Bone%5D=1&a%5Btwo%5D=2&a%5Bthree%5D=3&b=b%3D1%2C2%2C3&c%5B%5D=1&c%5B%5D=2&c%5B%5D=3').searchData());
});

QUnit.test('creme.ajax.URL (searchData, setter)', function(assert) {
    var url = new creme.ajax.URL('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=');

    url.searchData({x: 1, y: -1, z: 0});

    equal('http://admin.com:8080/this/is/a/test?x=1&y=-1&z=0', url.href());
    equal('?x=1&y=-1&z=0', url.search());
    deepEqual({x: '1', y: '-1', z: '0'}, url.searchData());

    url.searchData({'a[one]': '1', b: 'b=1,2,3', 'c[]': ['1', '2', '3']});

    equal('http://admin.com:8080/this/is/a/test?a%5Bone%5D=1&b=b%3D1%2C2%2C3&c%5B%5D=1&c%5B%5D=2&c%5B%5D=3', url.href());
    equal('?a%5Bone%5D=1&b=b%3D1%2C2%2C3&c%5B%5D=1&c%5B%5D=2&c%5B%5D=3', url.search());
    deepEqual({'a[one]': '1', b: 'b=1,2,3', 'c[]': ['1', '2', '3']}, url.searchData());
});

QUnit.test('creme.ajax.URL (updateSearchData)', function(assert) {
    var url = new creme.ajax.URL('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=');

    deepEqual({
        a: '1',
        b: '2',
        c: 'true',
        d: ''
    }, url.searchData());

    url.updateSearchData({b: '5', e: ['a', 'b']});

    deepEqual({
        a: '1',
        b: '5',
        c: 'true',
        d: '',
        e: ['a', 'b']
    }, url.searchData());
    equal('http://admin.com:8080/this/is/a/test?a=1&b=5&c=true&d=&e=a&e=b', url.href());
});

QUnit.test('creme.ajax.cookieAttr', function(assert) {
    equal(null, creme.ajax.cookieAttr('A'));
    equal(null, creme.ajax.cookieAttr());

    // javascript API allows to set ONE cookie at a time
    document.cookie = 'test-A=12';
    document.cookie = 'test-B=5';
    document.cookie = 'test-C=aaaa';
    document.cookie = 'test-D=%5B1%2C2%2C3%5D';

    equal('12', creme.ajax.cookieAttr('test-A'));
    equal('5', creme.ajax.cookieAttr('test-B'));
    equal('aaaa', creme.ajax.cookieAttr('test-C'));
    equal('[1,2,3]', creme.ajax.cookieAttr('test-D'));
    equal(null, creme.ajax.cookieAttr('unknown'));

    // reset cookies
    document.cookie = 'test-A=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
    document.cookie = 'test-B=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
    document.cookie = 'test-C=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
    document.cookie = 'test-D=;expires=Thu, 01 Jan 1970 00:00:00 GMT';

    equal(null, creme.ajax.cookieAttr('test-A'));
    equal(null, creme.ajax.cookieAttr('test-B'));
    equal(null, creme.ajax.cookieAttr('test-C'));
    equal(null, creme.ajax.cookieAttr('test-D'));
});

QUnit.test('creme.ajax.cookieCSRF', function(assert) {
    var csrftoken = creme.ajax.cookieAttr('csrftoken');
    equal(csrftoken, creme.ajax.cookieCSRF());

    try {
        document.cookie = 'csrftoken=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
        equal(null, creme.ajax.cookieCSRF());

        document.cookie = 'csrftoken=z56ZnN90D1eeah7roE5';
        equal("z56ZnN90D1eeah7roE5", creme.ajax.cookieCSRF());

    } finally {
        if (csrftoken) {
            document.cookie = 'csrftoken=' + csrftoken;
        } else {
            document.cookie = 'csrftoken=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
        }
    }
});

QUnit.parameterize('creme.ajax.json.send (deprecated alias)', [
    [false, 'GET', {}, {sync: false, method: 'GET'}],
    [false, 'GET', {sync: true}, {sync: true, method: 'GET'}],
    [false, 'GET', {dataType: 'text'}, {sync: false, method: 'GET', dataType: 'text'}],
    [true, 'POST', {dataType: 'text'}, {sync: true, method: 'POST', dataType: 'text'}]
], function(isSync, method, options, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};

    var faker = new FunctionFaker({
        method: 'creme.ajax.jqueryAjaxSend'
    });

    faker.with(function() {
        creme.ajax.json.send('mock/a', {a: 12}, successCb, errorCb, isSync, method, options);
    });

    deepEqual(faker.calls(), [
        ['mock/a', {a: 12}, successCb, errorCb, expected]
    ]);
});

QUnit.parameterize('creme.ajax.json.get (deprecated alias)', [
    [false, {}, {sync: false, method: 'GET'}],
    [false, {sync: true}, {sync: true, method: 'GET'}],
    [false, {dataType: 'text'}, {sync: false, method: 'GET', dataType: 'text'}]
], function(isSync, options, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};

    var faker = new FunctionFaker({
        method: 'creme.ajax.jqueryAjaxSend'
    });

    faker.with(function() {
        creme.ajax.json.get('mock/a', {a: 12}, successCb, errorCb, isSync, options);
    });

    deepEqual(faker.calls(), [
        ['mock/a', {a: 12}, successCb, errorCb, expected]
    ]);
});

QUnit.parameterize('creme.ajax.json.post (deprecated alias)', [
    [false, {}, {sync: false, method: 'POST'}],
    [false, {sync: true}, {sync: true, method: 'POST'}],
    [false, {dataType: 'text'}, {sync: false, method: 'POST', dataType: 'text'}]
], function(isSync, options, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};

    var faker = new FunctionFaker({
        method: 'creme.ajax.jqueryAjaxSend'
    });

    faker.with(function() {
        creme.ajax.json.post('mock/a', {a: 12}, successCb, errorCb, isSync, options);
    });

    deepEqual(faker.calls(), [
        ['mock/a', {a: 12}, successCb, errorCb, expected]
    ]);
});

QUnit.parameterize('creme.ajax.jqueryFormSubmit (url)', [
    ['', {}, {
        action: undefined
    }],
    ['action="mock/a"', {}, {
        action: 'mock/a'
    }],
    ['', {action: 'mock/default'}, {
        action: 'mock/default'
    }],
    ['action="mock/a"', {action: 'mock/default'}, {
        action: 'mock/default'
    }]
], function(attrs, options, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};
    var faker = new FunctionFaker({
        instance: $.fn, method: 'ajaxSubmit'
    });

    creme.ajax.cookieAttr('csrftoken');

    var form = $((
        '<form ${attrs}>' +
            '<input type="text" name="a" value="A"></input>' +
        '</form>'
    ).template({attrs: attrs}));

    faker.with(function() {
        creme.ajax.jqueryFormSubmit(form, successCb, errorCb, options);
    });

    equal(form.attr('action'), expected.action);
    equal(faker.count(), 1);

    var call = faker.calls()[0][0];
    equal(call.iframe, false);
});

QUnit.parameterize('creme.ajax.jqueryFormSubmit (options)', [
    [{myflag: true}, {
        action: 'mock/a',
        myflag: true,
        headers: {'X-CSRFToken': 'my-token'}
    }],
    [{headers: {'X-CSRFToken': 'othertoken'}}, {
        action: 'mock/a',
        headers: {'X-CSRFToken': 'othertoken'}
    }],
    [{headers: {'X-API-Id': 'myid'}}, {
        action: 'mock/a',
        headers: {'X-CSRFToken': 'my-token', 'X-API-Id': 'myid'}
    }]
], function(options, expected) {
    var successCb = function() {};
    var errorCb = function() {};
    var faker = new FunctionFaker({
        instance: $.fn, method: 'ajaxSubmit'
    });

    var form = $(
        '<form action="mock/a">' +
            '<input type="text" name="a" value="A"></input>' +
        '</form>'
    );

    faker.with(function() {
        document.cookie = 'csrftoken=my-token';
        creme.ajax.jqueryFormSubmit(form, successCb, errorCb, options);
    });

    equal(form.attr('action'), expected.action);

    var call = faker.calls()[0][0];
    equal(call.iframe, false);
    deepEqual(call.headers, expected.headers);
});

QUnit.parameterize('creme.ajax.jqueryFormSubmit (django csrftoken)', [
    [{}, {
        action: 'mock/a',
        headers: {}
    }],
    [{headers: {'X-CSRFToken': 'my-token'}}, {
        action: 'mock/a',
        headers: {'X-CSRFToken': 'my-token'}
    }]
], function(options, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};
    var faker = new FunctionFaker({
        instance: $.fn, method: 'ajaxSubmit'
    });

    var form = $(
        '<form action="mock/a">' +
            '<input type="text" name="a" value="A"></input>' +
            '<input type="hidden" name="csrfmiddlewaretoken" value="any"></input>' +
        '</form>'
    );

    faker.with(function() {
        creme.ajax.jqueryFormSubmit(form, successCb, errorCb, options);
    });

    equal(form.attr('action'), expected.action);

    var call = faker.calls()[0][0];
    equal(call.iframe, false);
    deepEqual(call.headers, expected.headers);
});

QUnit.test('creme.ajax.jqueryFormSubmit (iframe)', function(assert) {
    var successCb = function() {};
    var errorCb = function() {};
    var faker = new FunctionFaker({
        instance: $.fn, method: 'ajaxSubmit'
    });

    document.cookie = 'csrftoken=my-token';

    var form = $(
        '<form action="mock/a">' +
            '<input type="text" name="a" value="A"></input>' +
            '<input type="file" name="b"></input>' +
        '</form>'
    );

    faker.with(function() {
        creme.ajax.jqueryFormSubmit(form, successCb, errorCb);
    });

    var call = faker.calls()[0][0];
    equal(call.iframe, true);
});

QUnit.test('creme.ajax.jqueryFormSubmit (error callback)', function(assert) {
    var successCb = new FunctionFaker();
    var errorCb = new FunctionFaker();
    var submitFaker = new FunctionFaker({
        instance: $.fn, method: 'ajaxSubmit'
    });

    var form = $('<form action="mock/a"><input type="text" name="a" value="A"></input></form>');

    submitFaker.with(function() {
        creme.ajax.jqueryFormSubmit(form, successCb.wrap(), errorCb.wrap());
    });

    // retrieve internal callbacks from the ajaxSubmit call
    var submitCall = submitFaker.calls()[0][0];
    ok(Object.isFunc(submitCall.success));
    ok(Object.isFunc(submitCall.error));

    // now call internal error callback
    submitCall.error({status: 400, responseText: "Wrong call!"});

    equal(successCb.count(), 0);
    equal(errorCb.count(), 1);

    deepEqual(errorCb.calls(), [
        [
            "Wrong call!", {
                type: "request",
                status:  400,
                message: "HTTP - 400 error",
                request: {status: 400, responseText: "Wrong call!"}
            }
        ]
    ]);
});

QUnit.parametrize('creme.ajax.jqueryFormSubmit (success callback)', [
    [{}, 'Ok', 'success', {status: 200, responseText: 'Ok'}, {
        isSuccess: true,
        responseText: 'Ok',
        statusText: 'success',
        xhr: {status: 200, responseText: 'Ok'}
    }],
    [{iframe: true}, 'Ok', 'success', {status: 200, responseText: 'Ok'}, {
        isSuccess: true,
        responseText: 'Ok',
        statusText: 'success',
        xhr: {status: 200, responseText: 'Ok'}
    }],
    [{}, 'Not Found', 'error', {status: 404, responseText: 'Not Found'}, {
        isSuccess: false,
        responseText: 'Not Found',
        message: 'HTTP - 404 error',
        status: 404,
        request: {status: 404, responseText: 'Not Found'}
    }],
    [{iframe: false}, 'HTTPError 403', 'success', {status: 200, responseText: 'HTTPError 403'}, {
        isSuccess: true,
        responseText: 'HTTPError 403',
        statusText: 'success',
        xhr: {status: 200, responseText: 'HTTPError 403'}
    }],
    [{iframe: false}, 'HTTPError 403', 'success', {status: 0, responseText: 'HTTPError 403'}, {
        isSuccess: false,
        responseText: 'HTTPError 403',
        message: 'HTTP - 0 error',
        status: 0,
        request: {status: 0, responseText: 'HTTPError 403'}
    }],
    [{iframe: true}, 'Ok', 'success', {status: 0, responseText: 'Ok'}, {
        isSuccess: true,
        responseText: 'Ok',
        statusText: 'success',
        xhr: {status: 200, responseText: 'Ok'}
    }],
    // both status == 0 & iframe == true are needed to enable the "iframe error" mode
    [{iframe: true}, 'HTTPError 403', 'success', {status: 0, responseText: 'HTTPError 403'}, {
        isSuccess: false,
        responseText: 'HTTPError 403',
        message: 'HTTP - 403 error',
        status: 403,
        request: {status: 403, responseText: 'HTTPError 403'}
    }]
], function(options, responseText, statusText, xhr, expected, assert) {
    var successCb = new FunctionFaker();
    var errorCb = new FunctionFaker();
    var submitFaker = new FunctionFaker({
        instance: $.fn, method: 'ajaxSubmit'
    });

    var form = $('<form action="mock/a"><input type="text" name="a" value="A"></input></form>');

    submitFaker.with(function() {
        creme.ajax.jqueryFormSubmit(form, successCb.wrap(), errorCb.wrap(), options);
    });

    // retrieve internal callbacks from the ajaxSubmit call
    var submitCall = submitFaker.calls()[0][0];
    ok(Object.isFunc(submitCall.success));
    ok(Object.isFunc(submitCall.error));

    // now call internal success callback
    submitCall.success(responseText, statusText, xhr, form);

    if (expected.isSuccess) {
        equal(successCb.count(), 1);
        equal(errorCb.count(), 0);

        deepEqual(successCb.calls(), [
            [
                expected.responseText,
                expected.statusText,
                expected.xhr,
                form
            ]
        ]);
    } else {
        equal(successCb.count(), 0);
        equal(errorCb.count(), 1);

        deepEqual(errorCb.calls(), [
            [
                expected.responseText, {
                    type: "request",
                    status:  expected.status,
                    message: expected.message,
                    request: expected.request
                }
            ]
        ]);
    }
});

QUnit.test('creme.ajax.jqueryFormSubmit (no callback)', function(assert) {
    var submitFaker = new FunctionFaker({
        instance: $.fn, method: 'ajaxSubmit'
    });

    var form = $('<form action="mock/a"><input type="file" name="a"></input></form>');

    submitFaker.with(function() {
        creme.ajax.jqueryFormSubmit(form, undefined, undefined, {iframe: true});
    });

    // retrieve internal callbacks from the ajaxSubmit call
    var submitCall = submitFaker.calls()[0][0];
    ok(Object.isFunc(submitCall.success));
    ok(Object.isFunc(submitCall.error));

    // now call internal error callback
    submitCall.error({status: 400, responseText: "Wrong call!"});
    submitCall.success('Ok', 'success', {status: 200, responseText: "Ok"}, form);
    submitCall.success('HTTPError 403', 'success', {status: 0, responseText: "HTTPError 403"}, form);
    submitCall.success('Ok', 'success', {status: 0, responseText: "Ok"}, form);
});

QUnit.parameterize('creme.ajax.jqueryAjaxSend (options)', [
    ['', {}, {}, {
        url: '',
        async: true,
        data: {},
        dataType: 'json',
        type: 'GET',
        headers: {}
    }],
    ['mock/a', {a: 12}, {sync: true}, {
        url: 'mock/a',
        async: false,
        data: {a: 12},
        dataType: 'json',
        type: 'GET',
        headers: {}
    }],
    ['mock/a', {a: 12}, {method: 'POST', dataType: 'text'}, {
        url: 'mock/a',
        async: true,
        data: {a: 12},
        dataType: 'text',
        type: 'POST',
        headers: {}
    }]
], function(url, data, options, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        creme.ajax.jqueryAjaxSend(url, data, successCb, errorCb, options);
    });

    equal(ajaxFaker.count(), 1);

    var ajaxCall = ajaxFaker.calls()[0][0];

    equal(ajaxCall.async, expected.async);
    equal(ajaxCall.url, expected.url);
    deepEqual(ajaxCall.data, expected.data);
    equal(ajaxCall.dataType, expected.dataType);
    equal(ajaxCall.type, expected.type);
    deepEqual(ajaxCall.headers, expected.headers);
});

QUnit.parameterize('creme.ajax.jqueryAjaxSend (headers)', [
    ['my-token', {}, {
        headers: {'X-CSRFToken': 'my-token'}
    }],
    ['', {headers: {'X-CSRFToken': 'my-token'}}, {
        headers: {'X-CSRFToken': 'my-token'}
    }],
    ['my-token', {headers: {'X-CSRFToken': 'my-other-token'}}, {
        headers: {'X-CSRFToken': 'my-other-token'}
    }]
], function(token, options, expected, assert) {
    var successCb = function() {};
    var errorCb = function() {};
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        if (token.length) {
            document.cookie = 'csrftoken=' + token;
        }

        creme.ajax.jqueryAjaxSend('mock/a', {}, successCb, errorCb, options);
    });

    equal(ajaxFaker.count(), 1);

    var ajaxCall = ajaxFaker.calls()[0][0];

    deepEqual(ajaxCall.headers, expected.headers);
});


QUnit.parameterize('creme.ajax.jqueryAjaxSend (error callback)', [
    ['Wrong', {status: 400, statusText: 'error', responseText: "Wrong call!"}, {
        responseText: 'Wrong call!',
        message: 'HTTP 400 - error',
        status: 400,
        xhr: {status: 400, statusText: 'error', responseText: "Wrong call!"}
    }],
    ['parseerror', {status: 0, statusText: 'parseerror', responseText: "Invalid JSON"}, {
        responseText: 'Invalid JSON',
        message: 'JSON parse error',
        status: 0,
        xhr: {status: 0, statusText: 'parseerror', responseText: "Invalid JSON"}
    }]
], function(textStatus, xhr, expected, assert) {
    var successCb = new FunctionFaker();
    var errorCb = new FunctionFaker();
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        creme.ajax.jqueryAjaxSend('mock/a', {}, successCb.wrap(), errorCb.wrap(), {});
    });

    // retrieve internal callbacks from the ajaxSubmit call
    var ajaxCall = ajaxFaker.calls()[0][0];
    ok(Object.isFunc(ajaxCall.success));
    ok(Object.isFunc(ajaxCall.error));

    // now call internal error callback
    ajaxCall.error(xhr, textStatus);

    equal(successCb.count(), 0);
    equal(errorCb.count(), 1);

    deepEqual(errorCb.calls(), [
        [
            expected.responseText, {
                type: "request",
                status:  expected.status,
                message: expected.message,
                request: expected.xhr
            }
        ]
    ]);
});

QUnit.test('creme.ajax.jqueryAjaxSend (success callback)', function(assert) {
    var successCb = new FunctionFaker();
    var errorCb = new FunctionFaker();
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        creme.ajax.jqueryAjaxSend('mock/a', {}, successCb.wrap(), errorCb.wrap(), {});
    });

    // retrieve internal callbacks from the ajaxSubmit call
    var ajaxCall = ajaxFaker.calls()[0][0];
    ok(Object.isFunc(ajaxCall.success));
    ok(Object.isFunc(ajaxCall.error));

    // now call internal error callback
    ajaxCall.success({a: 12}, 'success', {status: 200, responseText: 'Ok'});

    equal(successCb.count(), 1);
    equal(errorCb.count(), 0);

    deepEqual(successCb.calls(), [
        [{a: 12}, 'success', {status: 200, responseText: 'Ok'}]
    ]);
});

QUnit.test('creme.ajax.jqueryAjaxSend (no callback)', function(assert) {
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        creme.ajax.jqueryAjaxSend('mock/a', {}, undefined, undefined, {});
    });

 // retrieve internal callbacks from the ajaxSubmit call
    var ajaxCall = ajaxFaker.calls()[0][0];
    ok(Object.isFunc(ajaxCall.success));
    ok(Object.isFunc(ajaxCall.error));

    // now call internal error callback
    ajaxCall.error({status: 400, responseText: "Wrong call!"}, 'error');
    ajaxCall.error({status: 0, responseText: "JSON error"}, 'parseerror');
    ajaxCall.success('Ok', 'success', {status: 200, responseText: "Ok"});
});

}(jQuery));
