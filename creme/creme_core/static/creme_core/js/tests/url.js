/* globals RelativeURL */

(function() {

// TODO : move URL tests from ajax/utils.js here.

QUnit.module("RelativeURL", new QUnitMixin());

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
});

QUnit.test('RelativeURL.fullPath', function(assert) {
    var url = new RelativeURL('http://joe:pwd@admin.com:8080/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');
    equal(url.fullPath(), '/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');

    url = new RelativeURL('/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');
    equal(url.fullPath(), '/this/is/a/test?a=1&a=2&b=true&c=a&d=&d=#hash');

    url.searchData({x: 1, y: 2});
    equal(url.fullPath(), '/this/is/a/test?x=1&y=2#hash');
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

    data = _.toFormData($('<form><input type="text" value="12" name="a"/></form>').get(0));
    deepEqual(data.getAll('a'), ['12']);
});

}());
