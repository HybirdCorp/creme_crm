/* globals RelativeURL */

(function() {

// TODO : move URL tests from ajax/utils.js here.

QUnit.module("RelativeURL", new QUnitMixin({
    assertFormData: function(data, expected) {
        ok(data instanceof FormData);
        deepEqual(Object.fromEntries(_.formDataEntriesAll(data)), expected);
    }
}));

QUnit.test('RelativeURL (URL)', function(assert) {
    var url = new RelativeURL(new URL('http://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash'));

    deepEqual({
        href: 'http://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash',
        protocol: 'http:',
        username: 'joe',
        password: 'pwd',
        host: 'admin.com:8080',
        hostname: 'admin.com',
        port: '8080',
        pathname: '/this/is/a/test',
        search: '?a=1&a=2&b=true&c=a&d=&d=',
        searchData: {a: ['1', '2'], b: 'true', c: 'a', d: ['', '']},
        hash: '#hash'
    }, url.properties());

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
    }, new RelativeURL('http://admin.com/this/is/a/test/?#hash').properties());

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
    }, new RelativeURL('http://admin.com:8080/this/is/a/test?').properties());
});

QUnit.test('RelativeURL.fullPath', function(assert) {
    var url = new RelativeURL('http://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');
    equal(url.fullPath(), '/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');

    url = new RelativeURL('/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');
    equal(url.fullPath(), '/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');

    url.searchData({x: 1, y: 2});
    equal(url.fullPath(), '/this/is/a/test?x=1&y=2#hash');
});

QUnit.test('RelativeURL (properties)', function(assert) {
    var url = new RelativeURL('http://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');

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

    url.search('a=8&b=false&d=');
    equal('https://other:password@yetanother.admin.com:8090/this/is/another/test?a=8&b=false&d=#hackish', url.href());

    url.search(new URLSearchParams({x: 8, y: -5}));
    equal('https://other:password@yetanother.admin.com:8090/this/is/another/test?x=8&y=-5#hackish', url.href());
});


QUnit.test('RelativeURL.searchData (setter)', function(assert) {
    var url = new RelativeURL('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=');

    url.searchData({x: 1, y: -1, z: 0});

    equal('http://admin.com:8080/this/is/a/test?x=1&y=-1&z=0', url.href());
    equal('?x=1&y=-1&z=0', url.search());
    deepEqual({x: '1', y: '-1', z: '0'}, url.searchData());

    url.searchData({'a[one]': '1', b: 'b=1,2,3', 'c[]': ['1', '2', '3']});

    equal('http://admin.com:8080/this/is/a/test?a%5Bone%5D=1&b=b%3D1%2C2%2C3&c%5B%5D=1&c%5B%5D=2&c%5B%5D=3', url.href());
    equal('?a%5Bone%5D=1&b=b%3D1%2C2%2C3&c%5B%5D=1&c%5B%5D=2&c%5B%5D=3', url.search());
    deepEqual({'a[one]': '1', b: 'b=1,2,3', 'c[]': ['1', '2', '3']}, url.searchData());

    url.searchData(new URLSearchParams({x: 8, y: -5, z: 30, a: 'b'}));

    equal('http://admin.com:8080/this/is/a/test?x=8&y=-5&z=30&a=b', url.href());
    equal('?x=8&y=-5&z=30&a=b', url.search());
    deepEqual({x: '8', y: '-5', z: '30', a: 'b'}, url.searchData());

    url.searchData('a=4&c=8');
    deepEqual({a: '4', c: '8'}, url.searchData());
});

QUnit.test('RelativeURL.searchParams', function(assert) {
    var url = new RelativeURL('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=');

    equal(new URLSearchParams({
        a: '1',
        b: '2',
        c: 'true',
        d: ''
    }).toString(), url.searchParams().toString());

    url.searchParams(new URLSearchParams({x: 8, y: -5, z: 30, a: 'b'}));

    equal('http://admin.com:8080/this/is/a/test?x=8&y=-5&z=30&a=b', url.href());
    equal('?x=8&y=-5&z=30&a=b', url.search());
    deepEqual({x: '8', y: '-5', z: '30', a: 'b'}, url.searchData());

    url.searchParams({x: 1, y: -1, z: 0});

    equal('http://admin.com:8080/this/is/a/test?x=1&y=-1&z=0', url.href());
});

QUnit.test('RelativeURL.updateSearchData', function(assert) {
    var url = new RelativeURL('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=');

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

    url.updateSearchData(new URLSearchParams({x: 8, y: -5, a: '33'}));
    equal('http://admin.com:8080/this/is/a/test?a=33&b=5&c=true&d=&e=a&e=b&x=8&y=-5', url.href());
});

QUnit.test('RelativeURL.toString', function(assert) {
    var url = new RelativeURL('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=');

    equal('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=', url.toString());
    equal('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=', String(url));

    url.updateSearchData({b: '5', e: ['a', 'b']});

    equal('http://admin.com:8080/this/is/a/test?a=1&b=5&c=true&d=&e=a&e=b', url.toString());
});

QUnit.test('toFormData', function() {
    var data = _.toFormData();
    equal(0, Array.from(data.keys()).length);

    data = new FormData();
    equal(_.toFormData(data), data);

    data = _.toFormData({
        a: 12,
        b: [1, 2, 3],
        c: new Set([4, 5, 6]),
        d: [],
        e: new Set(),
        f: null
    });

    deepEqual(data.getAll('a'), ['12']);
    deepEqual(data.getAll('b'), ['1', '2', '3']);
    deepEqual(data.getAll('c'), ['4', '5', '6']);
    deepEqual(data.getAll('d'), []);
    deepEqual(data.getAll('e'), []);
    deepEqual(data.getAll('f'), []);

    this.assertFormData(data, {
        a: ['12'],
        b: ['1', '2', '3'],
        c: ['4', '5', '6']
    });

    data = _.toFormData($('<form><input type="text" value="12" name="a"/></form>').get(0));
    deepEqual(data.getAll('a'), ['12']);
});

QUnit.test('assignFormData', function(assert) {
    var data = new FormData();

    data = _.assignFormData(data);
    this.assertFormData(data, {});

    data = _.assignFormData(data, {
        a: 12
    }, {
        b: [1, 2, 3]
    }, {
        c: new Set([4, 5, 6]),
        d: []
    }, {});

    this.assertFormData(data, {
        a: ['12'],
        b: ['1', '2', '3'],
        c: ['4', '5', '6']
    });

    var newData = _.assignFormData(new FormData(), {e: "test"}, data);

    // does not change, the values are applied on a new FormData instance
    this.assertFormData(data, {
        a: ['12'],
        b: ['1', '2', '3'],
        c: ['4', '5', '6']
    });

    this.assertFormData(newData, {
        a: ['12'],
        b: ['1', '2', '3'],
        c: ['4', '5', '6'],
        e: ['test']
    });
});

}());
