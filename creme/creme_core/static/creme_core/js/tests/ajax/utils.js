(function($) {

QUnit.module("creme.ajax.utils.js", new QUnitMixin(QUnitAjaxMixin, QUnitEventMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.ajax.utils.js'});
    },

    beforeEach: function() {
    },

    afterEach: function() {
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

QUnit.test('creme.ajax.URL (no data)', function(assert) {
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

QUnit.test('creme.ajax.URL (data)', function(assert) {
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

QUnit.test('creme.ajax.URL (update data)', function(assert) {
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

}(jQuery));
