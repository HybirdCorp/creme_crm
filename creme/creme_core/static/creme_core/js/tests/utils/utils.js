module("creme.utils.js", {
    setup: function() {},
    teardown: function() {}
});

test('creme.utils.JSON.encode (null)', function() {
    var codec = new creme.utils.JSON();

    equal("null", codec.encode(null));
});

test('creme.utils.JSON.encode', function() {
    var codec = new creme.utils.JSON();

    equal(codec.encode('test'), '"test"');
    equal(codec.encode(12), '12');
    equal(codec.encode(['a', 12, 'c', null, undefined]), '["a",12,"c",null,null]');
    equal(codec.encode({'a': ['a', 'b', 150],
                        'b': 'test',
                        'c': 12
                       }), '{"a":["a","b",150],"b":"test","c":12}');

    var encoder = creme.utils.JSON.encoder();

    equal(encoder('test'), '"test"');
    equal(encoder(12), '12');
    equal(encoder(['a', 12, 'c', null, undefined]), '["a",12,"c",null,null]');
    equal(encoder({'a': ['a', 'b', 150],
                   'b': 'test',
                   'c': 12
                  }), '{"a":["a","b",150],"b":"test","c":12}');
});

test('creme.utils.JSON.decode (null)', function() {
    var codec = new creme.utils.JSON();

    raises(function() {codec.decode(null);});
});

test('creme.utils.JSON.decode (invalid)', function() {
    var codec = new creme.utils.JSON();

    raises(function() {codec.decode('{"a\':1}');});
    raises(function() {codec.decode('{"a":1,}');});
    raises(function() {codec.decode('{a:1}');});

    var decoder = creme.utils.JSON.decoder();

    raises(function() {decoder('{"a\':1}');});
    raises(function() {decoder('{"a":1,}');});
    raises(function() {decoder('{a:1}');});
});

test('creme.utils.JSON.decode (invalid or null, default)', function() {
    var codec = new creme.utils.JSON();

    equal(codec.decode('{"a\':1}', 'fail'), 'fail');
    equal(codec.decode('{"a":1,}', 'fail'), 'fail');
    equal(codec.decode('{a:1}', 'fail'), 'fail');
    equal(codec.decode(null, 'fail'), 'fail');

    var decoder = creme.utils.JSON.decoder('default');

    equal(decoder('{"a\':1}'), 'default');
    equal(decoder('{"a":1,}'), 'default');
    equal(decoder('{a:1}'), 'default');
    equal(decoder(null), 'default');

    equal(decoder('{"a\':1}', 'fail'), 'fail');
    equal(decoder('{"a":1,}', 'fail'), 'fail');
    equal(decoder('{a:1}', 'fail'), 'fail');
    equal(decoder(null, 'fail'), 'fail');
});

test('creme.utils.JSON.decode (valid)', function() {
    var codec = new creme.utils.JSON();

    deepEqual(codec.decode('{"a":1, "b":true, "c":[1, 2, 3]}'), {a: 1, b: true, c: [1, 2, 3]});

    var decoder = creme.utils.JSON.decoder();

    deepEqual(decoder('{"a":1, "b":true, "c":[1, 2, 3]}'), {a: 1, b: true, c: [1, 2, 3]});
});

test('creme.utils.JSON.clean', function() {
    var clean = creme.utils.JSON.clean;

    raises(function() {clean('{"a\':1}');});
    equal(clean('{"a\':1}', 'default'), 'default');

    equal(clean(null), null);
    equal(clean(null, 'default'), null);

    deepEqual(clean('{"a":1}'), {a: 1});
    deepEqual(clean({a: 1}), {a: 1});
});

test('creme.utils.comparator (simple)', function() {
    var compare = creme.utils.comparator();

    deepEqual(compare, creme.utils.compareTo);

    equal(0, compare(12, 12));
    equal(0, compare(4.57, 4.57));
    equal(0, compare('test', 'test'));

    equal(-1, compare(12, 13));
    equal(-1, compare(4.57, 5.57));
    equal(-1, compare('da test', 'test'));

    equal(1, compare(13, 12));
    equal(1, compare(5.57, 4.57));
    equal(1, compare('test', 'da test'));
});

test('creme.utils.comparator (key)', function() {
    var compare = creme.utils.comparator('value');

    equal(0, compare({value: 12}, {value: 12}));
    equal(0, compare({value: 4.57}, {value: 4.57}));
    equal(0, compare({value: 'test'}, {value: 'test'}));

    equal(-1, compare({value: 12}, {value: 13}));
    equal(-1, compare({value: 4.57}, {value: 5.57}));
    equal(-1, compare({value: 'da test'}, {value: 'test'}));

    equal(1, compare({value: 13}, {value: 12}));
    equal(1, compare({value: 5.57}, {value: 4.57}));
    equal(1, compare({value: 'test'}, {value: 'da test'}));
});

test('creme.utils.comparator (multiple keys)', function() {
    var compare = creme.utils.comparator('value', 'index');

    equal(0, compare({value: 12, index: 0}, {value: 12, index: 0}));

    equal(1, compare({value: 12, index: 1}, {value: 12, index: 0}));
    equal(1, compare({value: 13, index: 0}, {value: 12, index: 1}));

    equal(-1, compare({value: 12, index: 0}, {value: 12, index: 1}));
    equal(-1, compare({value: 12, index: 1}, {value: 13, index: 0}));
});
