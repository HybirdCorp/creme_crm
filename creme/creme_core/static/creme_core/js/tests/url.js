/* globals RelativeURL */

(function() {

// TODO : move URL tests from ajax/utils.js here.

QUnit.module("RelativeURL", new QUnitMixin());

QUnit.test('RelativeURL (URL)', function(assert) {
    var url = new RelativeURL(new URL('http://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash'));

    assert.deepEqual({
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
    }, new RelativeURL('http://admin.com/this/is/a/test/?#hash').properties());

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
    }, new RelativeURL('http://admin.com:8080/this/is/a/test?').properties());
});

QUnit.test('RelativeURL.fullPath', function(assert) {
    var url = new RelativeURL('http://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');
    assert.equal(url.fullPath(), '/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');

    url = new RelativeURL('/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');
    assert.equal(url.fullPath(), '/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');

    url.searchData({x: 1, y: 2});
    assert.equal(url.fullPath(), '/this/is/a/test?x=1&y=2#hash');
});

QUnit.test('RelativeURL (properties)', function(assert) {
    var url = new RelativeURL('http://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');

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


QUnit.test('RelativeURL.searchData (setter)', function(assert) {
    var url = new RelativeURL('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=');

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

QUnit.test('RelativeURL.searchParams', function(assert) {
    var url = new RelativeURL('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=');

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

QUnit.test('RelativeURL.updateSearchData', function(assert) {
    var url = new RelativeURL('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=');

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

QUnit.test('RelativeURL.toString', function(assert) {
    var url = new RelativeURL('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=');

    assert.equal('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=', url.toString());
    assert.equal('http://admin.com:8080/this/is/a/test?a=1&b=2&c=true&d=', String(url));

    url.updateSearchData({b: '5', e: ['a', 'b']});

    assert.equal('http://admin.com:8080/this/is/a/test?a=1&b=5&c=true&d=&e=a&e=b', url.toString());
});

QUnit.test('toFormData', function(assert) {
    var data = _.toFormData();
    assert.equal(0, Array.from(data.keys()).length);

    data = new FormData();
    assert.equal(_.toFormData(data), data);

    data = _.toFormData({
        a: 12,
        b: [1, 2, 3],
        c: new Set([4, 5, 6]),
        d: [],
        e: new Set(),
        f: null
    });

    assert.deepEqual(data.getAll('a'), ['12']);
    assert.deepEqual(data.getAll('b'), ['1', '2', '3']);
    assert.deepEqual(data.getAll('c'), ['4', '5', '6']);
    assert.deepEqual(data.getAll('d'), []);
    assert.deepEqual(data.getAll('e'), []);
    assert.deepEqual(data.getAll('f'), []);

    data = _.toFormData($('<form><input type="text" value="12" name="a"/></form>').get(0));
    assert.deepEqual(data.getAll('a'), ['12']);
});

}());
