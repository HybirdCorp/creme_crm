/* globals FunctionFaker ProgressEvent */

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
        this.assert.equal(expected.search, data.search);
        this.assert.deepEqual(expected.searchData, data.searchData);
    }
}));

/*
QUnit.test('creme.ajax.parseUrl (no data)', function(assert) {
    assert.deepEqual({
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

    assert.deepEqual({
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

    assert.deepEqual({
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
*/
/*
QUnit.test('creme.ajax.param', function(assert) {
    assert.equal('a=12&b=1&b=2&d=', creme.ajax.param({a: 12, b: [1, 2], c: [], d: ''}));
});
*/

/*
QUnit.test('creme.ajax.URL (properties)', function(assert) {
    assert.deepEqual({
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

    assert.deepEqual({
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

    assert.deepEqual({
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

    assert.equal('http://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.protocol('https:');
    assert.equal('https://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.username('other');
    assert.equal('https://other:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.password('password');
    assert.equal('https://other:password@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.host('other.admin.com:8085');
    assert.equal('https://other:password@other.admin.com:8085/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.hostname('yetanother.admin.com');
    assert.equal('https://other:password@yetanother.admin.com:8085/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.port('8090');
    assert.equal('https://other:password@yetanother.admin.com:8090/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.pathname('/this/is/another/test');
    assert.equal('https://other:password@yetanother.admin.com:8090/this/is/another/test?a=1&a=2&b=true&c=a&d=&d=#hash', url.href());

    url.hash('#hackish');
    assert.equal('https://other:password@yetanother.admin.com:8090/this/is/another/test?a=1&a=2&b=true&c=a&d=&d=#hackish', url.href());

    url.search('a=8&b=false&d=');
    assert.equal('https://other:password@yetanother.admin.com:8090/this/is/another/test?a=8&b=false&d=#hackish', url.href());

    url.search(new URLSearchParams({x: 8, y: -5}));
    assert.equal('https://other:password@yetanother.admin.com:8090/this/is/another/test?x=8&y=-5#hackish', url.href());
});

QUnit.test('creme.ajax.URL (searchData)', function(assert) {
    assert.deepEqual({
        a: '1',
        b: '2',
        c: 'true',
        d: ''
    }, new creme.ajax.URL('/this/is/a/test?a=1&b=2&c=true&d=').searchData());

    assert.deepEqual({
        a: ['1', '2', 'true'],
        b: '2',
        c: ['a', 'b'],
        d: ['', '']
    }, new creme.ajax.URL('/this/is/a/test?a=1&a=2&a=true&b=2&c=a&c=b&d=&d=').searchData());

    assert.deepEqual({
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

    assert.equal('http://admin.com:8080/this/is/a/test?x=1&y=-1&z=0', url.href());
    assert.equal('?x=1&y=-1&z=0', url.search());
    assert.deepEqual({x: '1', y: '-1', z: '0'}, url.searchData());

    url.searchData({'a[one]': '1', b: 'b=1,2,3', 'c[]': ['1', '2', '3']});

    assert.equal('http://admin.com:8080/this/is/a/test?a%5Bone%5D=1&b=b%3D1%2C2%2C3&c%5B%5D=1&c%5B%5D=2&c%5B%5D=3', url.href());
    assert.equal('?a%5Bone%5D=1&b=b%3D1%2C2%2C3&c%5B%5D=1&c%5B%5D=2&c%5B%5D=3', url.search());
    assert.deepEqual({'a[one]': '1', b: 'b=1,2,3', 'c[]': ['1', '2', '3']}, url.searchData());

    url.searchData(new URLSearchParams({x: 8, y: -5, z: 30, a: 'b'}));

    assert.equal('http://admin.com:8080/this/is/a/test?x=8&y=-5&z=30&a=b', url.href());
    assert.equal('?x=8&y=-5&z=30&a=b', url.search());
    assert.deepEqual({x: '8', y: '-5', z: '30', a: 'b'}, url.searchData());

    url.searchData('a=4&c=8');
    assert.deepEqual({a: '4', c: '8'}, url.searchData());
});

QUnit.test('creme.ajax.URL (searchParams)', function(assert) {
    var url = new creme.ajax.URL('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=');

    assert.equal(new URLSearchParams({
        a: '1',
        b: '2',
        c: 'true',
        d: ''
    }).toString(), url.searchParams().toString());

    url.searchParams(new URLSearchParams({x: 8, y: -5, z: 30, a: 'b'}));

    assert.equal('http://admin.com:8080/this/is/a/test?x=8&y=-5&z=30&a=b', url.href());
    assert.equal('?x=8&y=-5&z=30&a=b', url.search());
    assert.deepEqual({x: '8', y: '-5', z: '30', a: 'b'}, url.searchData());

    url.searchParams({x: 1, y: -1, z: 0});

    assert.equal('http://admin.com:8080/this/is/a/test?x=1&y=-1&z=0', url.href());
});

QUnit.test('creme.ajax.URL (updateSearchData)', function(assert) {
    var url = new creme.ajax.URL('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=');

    assert.deepEqual({
        a: '1',
        b: '2',
        c: 'true',
        d: ''
    }, url.searchData());

    url.updateSearchData({b: '5', e: ['a', 'b']});

    assert.deepEqual({
        a: '1',
        b: '5',
        c: 'true',
        d: '',
        e: ['a', 'b']
    }, url.searchData());
    assert.equal('http://admin.com:8080/this/is/a/test?a=1&b=5&c=true&d=&e=a&e=b', url.href());

    url.updateSearchData(new URLSearchParams({x: 8, y: -5, a: '33'}));
    assert.equal('http://admin.com:8080/this/is/a/test?a=33&b=5&c=true&d=&e=a&e=b&x=8&y=-5', url.href());
});
*/
QUnit.test('creme.ajax.cookieAttr', function(assert) {
    assert.equal(null, creme.ajax.cookieAttr('A'));
    assert.equal(null, creme.ajax.cookieAttr());

    // javascript API allows to set ONE cookie at a time
    document.cookie = 'test-A=12';
    document.cookie = 'test-B=5';
    document.cookie = 'test-C=aaaa';
    document.cookie = 'test-D=%5B1%2C2%2C3%5D';

    assert.equal('12', creme.ajax.cookieAttr('test-A'));
    assert.equal('5', creme.ajax.cookieAttr('test-B'));
    assert.equal('aaaa', creme.ajax.cookieAttr('test-C'));
    assert.equal('[1,2,3]', creme.ajax.cookieAttr('test-D'));
    assert.equal(null, creme.ajax.cookieAttr('unknown'));

    // reset cookies
    document.cookie = 'test-A=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
    document.cookie = 'test-B=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
    document.cookie = 'test-C=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
    document.cookie = 'test-D=;expires=Thu, 01 Jan 1970 00:00:00 GMT';

    assert.equal(null, creme.ajax.cookieAttr('test-A'));
    assert.equal(null, creme.ajax.cookieAttr('test-B'));
    assert.equal(null, creme.ajax.cookieAttr('test-C'));
    assert.equal(null, creme.ajax.cookieAttr('test-D'));
});

QUnit.test('creme.ajax.cookieCSRF', function(assert) {
    var csrftoken = creme.ajax.cookieAttr('csrftoken');
    assert.equal(csrftoken, creme.ajax.cookieCSRF());

    try {
        document.cookie = 'csrftoken=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
        assert.equal(null, creme.ajax.cookieCSRF());

        document.cookie = 'csrftoken=z56ZnN90D1eeah7roE5';
        assert.equal("z56ZnN90D1eeah7roE5", creme.ajax.cookieCSRF());
    } finally {
        if (csrftoken) {
            document.cookie = 'csrftoken=' + csrftoken;
        } else {
            document.cookie = 'csrftoken=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
        }
    }
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
    }],
    ['mock/a', {a: 12}, {method: 'POST', dataType: 'text', extraData: {b: 6}}, {
        url: 'mock/a',
        async: true,
        data: {a: 12, b: 6},
        dataType: 'text',
        type: 'POST',
        headers: {}
    }]
], function(url, data, options, expected, assert) {
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        creme.ajax.jqueryAjaxSend(Object.assign({
            url: url,
            data: data
        }, options));
    });

    assert.equal(ajaxFaker.count(), 1);

    var ajaxCall = ajaxFaker.calls()[0][0];

    assert.equal(ajaxCall.async, expected.async);
    assert.equal(ajaxCall.url, expected.url);
    assert.deepEqual(ajaxCall.data, expected.data);
    assert.equal(ajaxCall.dataType, expected.dataType);
    assert.equal(ajaxCall.type, expected.type);
    assert.deepEqual(ajaxCall.headers, expected.headers);
});

QUnit.parameterize('creme.ajax.jqueryAjaxSend (form data)', [
    [
        function() {
            return new FormData();
        }, {},
        function(data, assert) {
            assert.deepEqual(Array.from(data.keys()), []);
        }
    ],
    [
        function() {
            var formdata = new FormData();
            formdata.set('a', 12);
            formdata.append('b', 4);
            formdata.append('b', 5);
            formdata.append('b', 6);
            return formdata;
        }, {},
        function(data, assert) {
            assert.deepEqual(data.getAll('a'), ['12']);
            assert.deepEqual(data.getAll('b'), ['4', '5', '6']);
        }
    ],
    [
        function() {
            var formdata = new FormData();
            formdata.set('a', 12);
            formdata.append('b', 4);
            formdata.append('b', 5);
            formdata.append('b', 6);
            return formdata;
        }, {
            extraData: {
                c: 'test',
                b: [1, 2, 3],
                d: new Set([7, 8, 9])
            }
        },
        function(data, assert) {
            assert.deepEqual(data.getAll('a'), ['12']);
            assert.deepEqual(data.getAll('b'), ['1', '2', '3']);
            assert.deepEqual(data.getAll('c'), ['test']);
            assert.deepEqual(data.getAll('d'), ['7', '8', '9']);
        }
    ]
], function(createData, options, assertExpected, assert) {
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        creme.ajax.jqueryAjaxSend(Object.assign({
            url: 'mock/a',
            data: createData(),
            method: 'POST'
        }, options));
    });

    assert.equal(ajaxFaker.count(), 1);

    var ajaxCall = ajaxFaker.calls()[0][0];

    assert.equal(ajaxCall.async, true);
    assert.equal(ajaxCall.url, 'mock/a');
    assert.deepEqual(ajaxCall.headers, {});
    assert.equal(ajaxCall.type, 'POST');

    assertExpected(ajaxCall.data, assert);
});

QUnit.parameterize('creme.ajax.jqueryAjaxSend (headers)', [
    ['', {csrf: 'my-query-token'}, {
        headers: {'X-CSRFToken': 'my-query-token'}
    }],
    ['', {csrf: true}, {
        headers: {}
    }],
    ['', {headers: {'X-CSRFToken': 'my-query-token'}}, {
        headers: {'X-CSRFToken': 'my-query-token'}
    }],
    ['my-token', {csrf: true}, {
        headers: {'X-CSRFToken': 'my-token'}
    }],
    ['my-token', {headers: {'X-CSRFToken': 'my-other-token'}}, {
        headers: {'X-CSRFToken': 'my-other-token'}
    }]
], function(token, options, expected, assert) {
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        if (token.length) {
            document.cookie = 'csrftoken=' + token;
        }

        creme.ajax.jqueryAjaxSend(Object.assign({
            url: 'mock/a'
        }, options || {}));
    });

    assert.equal(ajaxFaker.count(), 1);

    var ajaxCall = ajaxFaker.calls()[0][0];

    assert.deepEqual(ajaxCall.headers, expected.headers);
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
        creme.ajax.jqueryAjaxSend({
            url: 'mock/a'
        }, {
            done: successCb.wrap(),
            fail: errorCb.wrap()
        });
    });

    // retrieve internal callbacks from the $.ajax call
    var ajaxCall = ajaxFaker.calls()[0][0];
    assert.ok(Object.isFunc(ajaxCall.success));
    assert.ok(Object.isFunc(ajaxCall.error));

    // now call internal error callback
    ajaxCall.error(xhr, textStatus);

    assert.equal(successCb.count(), 0);
    assert.equal(errorCb.count(), 1);

    assert.deepEqual(errorCb.calls(), [
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
        creme.ajax.jqueryAjaxSend({
            url: 'mock/a'
        }, {
            done: successCb.wrap(),
            fail: errorCb.wrap()
        });
    });

    // retrieve internal callbacks from the $.ajax call
    var ajaxCall = ajaxFaker.calls()[0][0];
    assert.ok(Object.isFunc(ajaxCall.success));
    assert.ok(Object.isFunc(ajaxCall.error));

    // now call internal error callback
    ajaxCall.success({a: 12}, 'success', {status: 200, responseText: 'Ok'});

    assert.equal(successCb.count(), 1);
    assert.equal(errorCb.count(), 0);

    assert.deepEqual(successCb.calls(), [
        [{a: 12}, 'success', {status: 200, responseText: 'Ok'}]
    ]);
});

QUnit.test('creme.ajax.jqueryAjaxSend (no callback)', function(assert) {
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        creme.ajax.jqueryAjaxSend({
            url: 'mock/a'
        });
    });

    // retrieve internal callbacks from the $.ajax call
    var ajaxCall = ajaxFaker.calls()[0][0];
    assert.ok(Object.isFunc(ajaxCall.success));
    assert.ok(Object.isFunc(ajaxCall.error));

    // now call internal error callback
    ajaxCall.error({status: 400, responseText: "Wrong call!"}, 'error');
    ajaxCall.error({status: 0, responseText: "JSON error"}, 'parseerror');
    ajaxCall.success('Ok', 'success', {status: 200, responseText: "Ok"});
});

QUnit.test('creme.ajax.jqueryAjaxSend (legacy callbacks)', function(assert) {
    var successCb = new FunctionFaker();
    var errorCb = new FunctionFaker();
    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        creme.ajax.jqueryAjaxSend({
            url: 'mock/a',
            success: successCb.wrap(),
            error: errorCb.wrap()
        });
    });

    // retrieve internal callbacks from the $.ajax call
    var ajaxCall = ajaxFaker.calls()[0][0];
    assert.ok(Object.isFunc(ajaxCall.success));
    assert.ok(Object.isFunc(ajaxCall.error));

    // now call internal error callback
    ajaxCall.error({status: 400, responseText: "Wrong call!", statusText: 'error'}, 'error');
    ajaxCall.error({status: 0, responseText: "JSON error"}, 'parseerror');
    ajaxCall.success('Ok', 'success', {status: 200, responseText: "Ok"});

    assert.deepEqual(errorCb.calls(), [
        ['Wrong call!', {
            type: 'request',
            status: 400,
            message: 'HTTP 400 - error',
            request: {status: 400, statusText: 'error', responseText: "Wrong call!"}
        }],
        ['JSON error', {
            type: 'request',
            status: 0,
            message: 'JSON parse error',
            request: {status: 0, responseText: "JSON error"}
        }]
    ]);

    assert.deepEqual(successCb.calls(), [
        ['Ok', 'success', {status: 200, responseText: 'Ok'}]
    ]);
});

QUnit.parameterize('creme.ajax.jqueryAjaxSend (progress)', [
    [
        {lengthComputable: false, loaded: 1024, total: 4096},
        {lengthComputable: false, loaded: 1024, total: 4096, loadedPercent: 0}
    ],
    [
        {lengthComputable: true, loaded: 1024, total: 4096},
        {lengthComputable: true, loaded: 1024, total: 4096, loadedPercent: 25}
    ],
    [
        {lengthComputable: true, loaded: 4096, total: 4096},
        {lengthComputable: true, loaded: 4096, total: 4096, loadedPercent: 100}
    ]
], function(state, expected, assert) {
    var progressCb = new FunctionFaker();
    var uploadCb = new FunctionFaker();

    var ajaxFaker = new FunctionFaker({
        instance: $, method: 'ajax'
    });

    ajaxFaker.with(function() {
        creme.ajax.jqueryAjaxSend({
            url: 'mock/a'
        }, {
            progress: progressCb.wrap(),
            uploadProgress: uploadCb.wrap()
        });
    });

    // retrieve internal callbacks from the $.ajax call
    var ajaxCall = ajaxFaker.calls()[0][0];
    var xhr = ajaxCall.xhr();

    xhr.dispatchEvent(new ProgressEvent('progress', state));
    xhr.upload.dispatchEvent(new ProgressEvent('progress', state));

    assert.equal(progressCb.count(), 1);
    assert.equal(uploadCb.count(), 1);

    function _progressEventData(args) {
        var event = args[0];

        return {
            lengthComputable: event.lengthComputable,
            loaded: event.loaded,
            total: event.total,
            loadedPercent: event.loadedPercent
        };
    };

    assert.deepEqual(progressCb.calls().map(_progressEventData), [expected]);
    assert.deepEqual(uploadCb.calls().map(_progressEventData), [expected]);
});

}(jQuery));
