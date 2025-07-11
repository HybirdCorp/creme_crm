(function($) {

var MockObjectA = function(b) {
    this.b = b;
};

MockObjectA.prototype = {
    add: function(a) {
        return a + this.b;
    },
    mult: function(a) {
        return a * this.b;
    }
};
MockObjectA.prototype.constructor = MockObjectA;

var MockObjectB = function(b, c) {
    this.b = b;
    this.c = c;
};

MockObjectB.prototype = new MockObjectA();
MockObjectB.prototype.constructor = MockObjectB;

$.extend(MockObjectB.prototype, {
    add: function(a) {
        return (a + this.b) * this.c;
    }
});

QUnit.module("creme.fallbacks.js", new QUnitMixin());

QUnit.test('fallbacks.Object.isNone', function(assert) {
    assert.equal(typeof Object.isNone, 'function');

    assert.equal(Object.isNone(undefined), true);
    assert.equal(Object.isNone(null), true);
    assert.equal(Object.isNone({}), false);
    assert.equal(Object.isNone([]), false);
    assert.equal(Object.isNone(0), false);
    assert.equal(Object.isNone(''), false);
});

QUnit.test('fallbacks.Object.isEmpty', function(assert) {
    assert.equal(typeof Object.isEmpty, 'function');

    assert.equal(Object.isEmpty(undefined), true);
    assert.equal(Object.isEmpty(null), true);
    assert.equal(Object.isEmpty({}), true);
    assert.equal(Object.isEmpty([]), true);
    assert.equal(Object.isEmpty(''), true);

    assert.equal(Object.isEmpty(0), false);
    assert.equal(Object.isEmpty(15), false);
    assert.equal(Object.isEmpty({a: 12}), false);
    assert.equal(Object.isEmpty([12]), false);
    assert.equal(Object.isEmpty('a'), false);
});

QUnit.test('fallbacks.Object.isType (undefined)', function(assert) {
    assert.equal(typeof Object.isType, 'function');

    assert.equal(Object.isType(undefined, 'undefined'), true);
    assert.equal(Object.isType(undefined, 'null'),      false);
    assert.equal(Object.isType(undefined, 'function'),  false);
    assert.equal(Object.isType(undefined, 'number'),    false);
    assert.equal(Object.isType(undefined, 'object'),    false);
    assert.equal(Object.isType(undefined, 'boolean'),   false);
    assert.equal(Object.isType(undefined, 'string'),    false);
});

QUnit.test('fallbacks.Object.isType (null)', function(assert) {
    assert.equal(Object.isType(null, 'undefined'), false);
    assert.equal(Object.isType(null, 'null'),      false);
    assert.equal(Object.isType(null, 'function'),  false);
    assert.equal(Object.isType(null, 'number'),    false);
    assert.equal(Object.isType(null, 'object'),    true);
    assert.equal(Object.isType(null, 'boolean'),   false);
    assert.equal(Object.isType(null, 'string'),    false);
});

QUnit.test('fallbacks.Object.isType (string)', function(assert) {
    assert.equal(Object.isType('a', 'undefined'), false);
    assert.equal(Object.isType('a', 'null'),      false);
    assert.equal(Object.isType('a', 'function'),  false);
    assert.equal(Object.isType('a', 'number'),    false);
    assert.equal(Object.isType('a', 'object'),    false);
    assert.equal(Object.isType('a', 'boolean'),   false);
    assert.equal(Object.isType('a', 'string'),    true);
});

QUnit.test('fallbacks.Object.isType (numeric)', function(assert) {
    assert.equal(Object.isType(12, 'undefined'), false);
    assert.equal(Object.isType(12, 'null'),      false);
    assert.equal(Object.isType(12, 'function'),  false);
    assert.equal(Object.isType(12, 'number'),    true);
    assert.equal(Object.isType(12, 'object'),    false);
    assert.equal(Object.isType(12, 'boolean'),   false);
    assert.equal(Object.isType(12, 'string'),    false);

    assert.equal(Object.isType(12.55, 'undefined'), false);
    assert.equal(Object.isType(12.55, 'null'),      false);
    assert.equal(Object.isType(12.55, 'function'),  false);
    assert.equal(Object.isType(12.55, 'number'),    true);
    assert.equal(Object.isType(12.55, 'object'),    false);
    assert.equal(Object.isType(12.55, 'boolean'),   false);
    assert.equal(Object.isType(12.55, 'string'),    false);
});

QUnit.test('fallbacks.Object.isType (boolean)', function(assert) {
    assert.equal(Object.isType(true, 'undefined'), false);
    assert.equal(Object.isType(true, 'null'),      false);
    assert.equal(Object.isType(true, 'function'),  false);
    assert.equal(Object.isType(true, 'number'),    false);
    assert.equal(Object.isType(true, 'object'),    false);
    assert.equal(Object.isType(true, 'boolean'),   true);
    assert.equal(Object.isType(true, 'string'),    false);
});

QUnit.test('fallbacks.Object.isType (function)', function(assert) {
    assert.equal(Object.isType(function() {}, 'undefined'), false);
    assert.equal(Object.isType(function() {}, 'null'),      false);
    assert.equal(Object.isType(function() {}, 'function'),  true);
    assert.equal(Object.isType(function() {}, 'number'),    false);
    assert.equal(Object.isType(function() {}, 'object'),    false);
    assert.equal(Object.isType(function() {}, 'boolean'),   false);
    assert.equal(Object.isType(function() {}, 'string'),    false);

    assert.equal(Object.isFunc(undefined),       false);
    assert.equal(Object.isFunc(null, 'null'),    false);
    assert.equal(Object.isFunc(function() {}),   true);
    assert.equal(Object.isFunc(10, 'number'),    false);
    assert.equal(Object.isFunc({}, 'object'),    false);
    assert.equal(Object.isFunc(true, 'boolean'), false);
    assert.equal(Object.isFunc('a', 'string'),   false);
});

QUnit.test('fallbacks.Object.keys', function(assert) {
    assert.equal(typeof Object.keys, 'function');
    assert.equal({}.keys, undefined);

    assert.deepEqual([], Object.keys({}));
    assert.deepEqual(['a', 'b'], Object.keys({a: 1, b: 2}));
    assert.deepEqual(['a', 'b', 'c', 'd', 'z'], Object.keys({a: 1, b: 2, c: 5, d: 7, z: 8}));
});

QUnit.test('fallbacks.Object.values', function(assert) {
    assert.equal(typeof Object.values, 'function');
    assert.equal({}.values, undefined);

    assert.deepEqual([], Object.values({}));
    assert.deepEqual([1, 2], Object.values({a: 1, b: 2}));
    assert.deepEqual([1, 2, 5, 7, 8], Object.values({a: 1, b: 2, c: 5, d: 7, z: 8}));
});


QUnit.test('fallbacks.Object.entries', function(assert) {
    assert.equal(typeof Object.entries, 'function');
    assert.equal({}.entries, undefined);

    assert.deepEqual([], Object.entries({}));
    assert.deepEqual([['a', 1], ['b', 2]], Object.entries({a: 1, b: 2}));
    assert.deepEqual([['a', 1], ['b', 2], ['c', 5], ['d', 7], ['z', 8]], Object.entries({a: 1, b: 2, c: 5, d: 7, z: 8}));
});

QUnit.test('fallbacks.Object.proxy (undefined)', function(assert) {
    assert.equal(undefined, Object.proxy(null));
    assert.equal(undefined, Object.proxy());
});

QUnit.test('fallbacks.Object.proxy (no context)', function(assert) {
    assert.equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a);

    assert.notDeepEqual(a, proxy);
    assert.deepEqual(a, proxy.__context__);

    assert.equal(a.b, 5);
    assert.equal(proxy.__context__.b, 5);

    assert.equal(a.add(2), 2 + 5);
    assert.equal(proxy.add(2), 2 + 5);

    assert.equal(a.mult(2), 2 * 5);
    assert.equal(proxy.mult(2), 2 * 5);
});

QUnit.test('fallbacks.Object.proxy (context)', function(assert) {
    assert.equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, {b: 12});

    assert.notDeepEqual(a, proxy);
    assert.notDeepEqual(a, proxy.__context__);

    assert.equal(a.b, 5);
    assert.equal(proxy.__context__.b, 12);

    assert.equal(a.add(2), 2 + 5);
    assert.equal(proxy.add(2), 2 + 12);

    assert.equal(a.mult(2), 2 * 5);
    assert.equal(proxy.mult(2), 2 * 12);
});

QUnit.test('fallbacks.Object.proxy (filter)', function(assert) {
    assert.equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, undefined, {filter: function(key) { return key !== 'mult'; }});

    assert.notDeepEqual(a, proxy);
    assert.deepEqual(a, proxy.__context__);

    assert.equal(a.b, 5);
    assert.equal(proxy.__context__.b, 5);

    assert.equal(a.add(2), 2 + 5);
    assert.equal(proxy.add(2), 2 + 5);

    assert.equal(a.mult(2), 2 * 5);
    assert.equal(proxy.mult, undefined);
});

QUnit.test('fallbacks.Object.proxy (filter, context)', function(assert) {
    assert.equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, {b: 12}, {filter: function(key) { return key !== 'mult'; }});

    assert.notDeepEqual(a, proxy);
    assert.notDeepEqual(a, proxy.__context__);

    assert.equal(a.b, 5);
    assert.equal(proxy.__context__.b, 12);

    assert.equal(a.add(2), 2 + 5);
    assert.equal(proxy.add(2), 2 + 12);

    assert.equal(a.mult(2), 2 * 5);
    assert.equal(proxy.mult, undefined);
});

QUnit.test('fallbacks.Object.proxy (arguments)', function(assert) {
    assert.equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, undefined, {arguments: function(args) { return [args[0] * 0.8]; }});

    assert.notDeepEqual(a, proxy);
    assert.deepEqual(a, proxy.__context__);

    assert.equal(a.add(2), 2 + 5);
    assert.equal(proxy.add(2), (2 * 0.8) + 5);

    assert.equal(a.mult(2), 2 * 5);
    assert.equal(proxy.mult(2), (2 * 0.8) * 5);
});

QUnit.test('fallbacks.Object.proxy (arguments, context)', function(assert) {
    assert.equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, {b: 12}, {arguments: function(args) { return [args[0] * 0.8]; }});

    assert.notDeepEqual(a, proxy);

    assert.equal(a.add(2), 2 + 5);
    assert.equal(proxy.add(2), (2 * 0.8) + 12);

    assert.equal(a.mult(2), 2 * 5);
    assert.equal(proxy.mult(2), (2 * 0.8) * 12);
});


QUnit.test('fallbacks.Object.proxy (arguments, filter)', function(assert) {
    assert.equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, undefined, {
        arguments: function(args) { return [args[0] * 0.8]; },
        filter: function(key) { return key !== 'mult'; }
    });

    assert.notDeepEqual(a, proxy);

    assert.equal(a.add(2), 2 + 5);
    assert.equal(proxy.add(2), (2 * 0.8) + 5);

    assert.equal(a.mult(2), 2 * 5);
    assert.equal(proxy.mult, undefined);
});

QUnit.test('fallbacks.Object.proxy (arguments, filter, context)', function(assert) {
    assert.equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, {b: 12}, {
        arguments: function(args) { return [args[0] * 0.8]; },
        filter: function(key) { return key !== 'mult'; }
    });

    assert.notDeepEqual(a, proxy);

    assert.equal(a.add(2), 2 + 5);
    assert.equal(proxy.add(2), (2 * 0.8) + 12);

    assert.equal(a.mult(2), 2 * 5);
    assert.equal(proxy.mult, undefined);
});

QUnit.test('fallbacks.Object.getPrototypeOf (object)', function(assert) {
    assert.equal(typeof Object.getPrototypeOf, 'function');

    var a = new MockObjectA(5);
    var b = new MockObjectB(8, 3);

    assert.equal(Object.getPrototypeOf(a), MockObjectA.prototype, 'a.prototype');
    assert.equal(Object.getPrototypeOf(a).constructor, MockObjectA, 'a.constructor');

    assert.equal(Object.getPrototypeOf(b), MockObjectB.prototype, 'b.prototype');
    assert.equal(Object.getPrototypeOf(b).constructor, MockObjectB, 'b.constructor');
});

QUnit.test('fallbacks.Object.isPrototypeOf (object)', function(assert) {
    assert.equal(typeof Object.prototype.isPrototypeOf, 'function');

    var a = new MockObjectA(5);
    var b = new MockObjectB(8, 3);

    assert.equal(true, Object.prototype.isPrototypeOf(a), 'Object isPrototype of a');
    assert.equal(true, Object.prototype.isPrototypeOf(b), 'Object isPrototype of b');

    assert.equal(true, MockObjectA.prototype.isPrototypeOf(a), 'MockObjectA isPrototype of a');
    assert.equal(true, MockObjectA.prototype.isPrototypeOf(b), 'MockObjectA isPrototype of b');

    assert.equal(false, MockObjectB.prototype.isPrototypeOf(a), 'MockObjectB not isPrototype of a');
    assert.equal(true, MockObjectB.prototype.isPrototypeOf(b), 'MockObjectB isPrototype of b');
});

QUnit.test('fallbacks.Object.isSubClassOf (object)', function(assert) {
    assert.equal(typeof Object.isSubClassOf, 'function');

    var o = {};
    var a = new MockObjectA(5);
    var b = new MockObjectB(8, 3);

    assert.equal(false, Object.isSubClassOf(null, Object), 'Object not isPrototype of null');
    assert.equal(false, Object.isSubClassOf(undefined, Object), 'Object not isPrototype of undefined');
    assert.equal(true, Object.isSubClassOf(o, Object), 'Object isPrototype of o');
    assert.equal(true, Object.isSubClassOf(a, Object), 'Object isPrototype of a');
    assert.equal(true, Object.isSubClassOf(a, Object), 'Object isPrototype of b');
    assert.equal(false, Object.isSubClassOf(a, null), 'null not isPrototype of a');
    assert.equal(false, Object.isSubClassOf(a, undefined), 'undefined not isPrototype of b');

    assert.equal(false, Object.isSubClassOf(null, MockObjectA), 'MockObjectA not isPrototype of null');
    assert.equal(false, Object.isSubClassOf(undefined, MockObjectA), 'MockObjectA not isPrototype of undefined');
    assert.equal(false, Object.isSubClassOf(o, MockObjectA), 'MockObjectA not isPrototype of o');
    assert.equal(true, Object.isSubClassOf(a, MockObjectA), 'MockObjectA isPrototype of a');
    assert.equal(true, Object.isSubClassOf(b, MockObjectA), 'MockObjectA isPrototype of b');

    assert.equal(false, Object.isSubClassOf(null, MockObjectB), 'MockObjectB not isPrototype of null');
    assert.equal(false, Object.isSubClassOf(undefined, MockObjectB), 'MockObjectB not isPrototype of undefined');
    assert.equal(false, Object.isSubClassOf(o, MockObjectB), 'MockObjectB not isPrototype of o');
    assert.equal(false, Object.isSubClassOf(a, MockObjectB), 'MockObjectB not isPrototype of a');
    assert.equal(true, Object.isSubClassOf(b, MockObjectB), 'MockObjectB isPrototype of b');
});

QUnit.test('fallbacks.Object.isString', function(assert) {
    assert.equal(typeof Object.isString, 'function');

    assert.equal(Object.isString(''), true);
    assert.equal(Object.isString(String('')), true);
    assert.equal(Object.isString(false), false);
    assert.equal(Object.isString([12, 13]), false);
    assert.equal(Object.isString(new MockObjectA()), false);
    assert.equal(Object.isString({}), false);
    assert.equal(Object.isString(undefined), false);
    assert.equal(Object.isString(null), false);
});

QUnit.test('fallbacks.Object.isNumber', function(assert) {
    assert.equal(typeof Object.isNumber, 'function');

    assert.equal(Object.isNumber(''), false);
    assert.equal(Object.isNumber(String('')), false);
    assert.equal(Object.isNumber(false), false);
    assert.equal(Object.isNumber([12, 13]), false);
    assert.equal(Object.isNumber(new MockObjectA()), false);
    assert.equal(Object.isNumber({}), false);
    assert.equal(Object.isNumber(undefined), false);
    assert.equal(Object.isNumber(null), false);
    assert.equal(Object.isNumber(12), true);
    assert.equal(Object.isNumber(12.154), true);
    assert.equal(Object.isNumber(Number(12)), true);
    assert.equal(Object.isNumber(Number(12.154)), true);
});

QUnit.test('fallbacks.Array.indexOf', function(assert) {
    assert.equal(typeof Array.prototype.indexOf, 'function');
    assert.equal(typeof [].indexOf, 'function');

    assert.equal([12, 5, 8, 5, 44].indexOf(5), 1);
    assert.equal([12, 5, 8, 5, 44].indexOf(5, 2), 3);

    assert.equal([12, 5, 8, 5, 44].indexOf(15), -1);

    assert.equal([12, 5, 8, 5, 44].indexOf(12), 0);
    assert.equal([12, 5, 8, 5, 44].indexOf(12, 1), -1);
});

QUnit.test('fallbacks.Array.slice', function(assert) {
    assert.equal(typeof Array.prototype.slice, 'function');
    assert.equal(typeof [].slice, 'function');

    var original = [1, 2, 1, 4, 5, 4];
    var copy = original.slice();
    copy[2] = 12;

    assert.deepEqual(original, [1, 2, 1, 4, 5, 4]);
    assert.deepEqual(copy, [1, 2, 12, 4, 5, 4]);

    assert.deepEqual([1, 2, 1, 4, 5, 4].slice(3), [4, 5, 4]);
    assert.deepEqual([1, 2, 1, 4, 5, 4].slice(1, 4), [2, 1, 4]);
});

QUnit.test('fallbacks.Array.map', function(assert) {
    assert.equal(typeof Array.prototype.map, 'function');
    assert.equal(typeof [].map, 'function');

    assert.deepEqual(["my", "Name", "is", "HARRY"].map(function(element, index, array) {
                                                   return element.toUpperCase();
                                                }), ["MY", "NAME", "IS", "HARRY"]);
});

QUnit.test('fallbacks.Array.forEach', function(assert) {
    assert.equal(typeof Array.prototype.forEach, 'function');
    assert.equal(typeof [].forEach, 'function');

    var value = "";
    ["This", "is", "a", "forEach", "test"].forEach(function(element, index, array) { value += element; });

    assert.equal(value, 'ThisisaforEachtest');
});

QUnit.test('fallbacks.Array.isArray', function(assert) {
    assert.equal(typeof Array.isArray, 'function');
    assert.equal(Array.isArray([]), true);
    assert.equal(Array.isArray([12, 5, 5]), true);
    assert.equal(Array.isArray(new Array()), true);  // eslint-disable-line no-array-constructor

    assert.equal(Array.isArray(undefined), false);
    assert.equal(Array.isArray(null), false);

    assert.equal(Array.isArray({}), false);
    assert.equal(Array.isArray({'test': 1}), false);
});

/*
QUnit.test('fallbacks.Array.copy', function(assert) {
    assert.equal(typeof Array.copy, 'function');

    assert.deepEqual([], Array.copy([]));
    assert.deepEqual(['a', 'b'], Array.copy(['a', 'b']));

    assert.deepEqual(['b', 'c'], Array.copy(['a', 'b', 'c'], 1));
    assert.deepEqual([], Array.copy(['a', 'b', 'c'], 10));

    assert.deepEqual(['b'], Array.copy(['a', 'b', 'c'], 1, 2));
    assert.deepEqual([], Array.copy(['a', 'b', 'c'], 1, 1));
    assert.deepEqual(['b', 'c'], Array.copy(['a', 'b', 'c'], 1, 10));
});

QUnit.test('fallbacks.Array.copy (arguments)', function(assert) {
    var f = function() {
        return Array.copy(arguments);
    };

    var f_1 = function() {
        return Array.copy(arguments, 1);
    };

    var f_1_2 = function() {
        return Array.copy(arguments, 1, 2);
    };

    assert.deepEqual([], f());
    assert.deepEqual(['a', 'b', 'c'], f('a', 'b', 'c'));
    assert.deepEqual([['a', 'b', 'c']], f(['a', 'b', 'c']));

    assert.deepEqual([], f_1());
    assert.deepEqual(['b', 'c'], f_1('a', 'b', 'c'));
    assert.deepEqual([], f_1(['a', 'b', 'c']));

    assert.deepEqual([], f_1_2());
    assert.deepEqual(['b'], f_1_2('a', 'b', 'c'));
    assert.deepEqual([], f_1_2(['a', 'b', 'c']));
});
*/

QUnit.test('fallbacks.HTMLDocument', function(assert) {
    assert.notEqual(typeof HTMLDocument, 'undefined');
});

QUnit.test('fallbacks.HTMLDocument.createElementNS', function(assert) {
    assert.equal(typeof HTMLDocument.prototype.createElementNS, 'function');
});

QUnit.test('fallbacks.CSSStyleDeclaration', function(assert) {
    assert.notEqual(typeof CSSStyleDeclaration, 'undefined');
});

QUnit.test('fallbacks.Event', function(assert) {
    assert.notEqual(typeof Event, 'undefined');
});

QUnit.test('fallbacks.Event.preventDefault', function(assert) {
    assert.equal(typeof Event.prototype.preventDefault, 'function');
});

QUnit.test('fallbacks.String.format (skip format)', function(assert) {
    assert.equal('%d', '%%d'.format(12));
    assert.equal('%12', '%%%d'.format(12));
});

QUnit.test('fallbacks.String.format (array)', function(assert) {
    assert.equal('12', '%d'.format([12, 5]));
    assert.equal('12', '%0$d'.format([12, 5]));
    assert.equal('5', '%1$d'.format([12, 5]));
    assert.equal('8', '%2$d'.format([12, 5, 8, 7]));
});

QUnit.test('fallbacks.String.format (padding)', function(assert) {
    assert.equal('ab', '%s'.format('ab'));
    assert.equal('12', '%s'.format(12));
    assert.equal('12.05', '%s'.format(12.05));

    assert.equal('   ab', '%5s'.format('ab'));
    assert.equal('   12', '%5s'.format(12));
    assert.equal('12.05', '%5s'.format(12.05));

    assert.equal('+   ab', '+%5s'.format('ab'));  // bug ! "   ab"
    assert.equal('&nbsp;&nbsp;&nbsp;ab', '%&5s'.format('ab'));
    assert.equal('   ab', '%#5s'.format('ab'));

    assert.equal('ab   ', '%-5s'.format('ab'));
    assert.equal('12   ', '%-5s'.format(12));
    assert.equal('12.05', '%-5s'.format(12.05));
});

QUnit.test('fallbacks.String.format (integer)', function(assert) {
    assert.equal('12',    '%d'.format(12.0));
    assert.equal('12',    '%u'.format(12.0));
    assert.equal('12',    '%i'.format(12.0));

    assert.equal('',    '%d'.format({}));
    assert.equal('0',    '%u'.format({}));  // bug ! NaN => ""
    assert.equal('',    '%i'.format({}));

    assert.equal('+12',    '%+d'.format(12));  // bug ! "12"
    assert.equal(' 12',    '% d'.format(12));  // bug ! "12"
    assert.equal('-12',    '%d'.format(-12));
    assert.equal('00012', '%05d'.format(12));
    assert.equal('   12', '%5d'.format(12));
    assert.equal('12   ', '%-5d'.format(12));

    assert.equal('12', '%\'d'.format(12));
    assert.equal("12,412", '%\'d'.format(12412));
});

QUnit.test('fallbacks.String.format (base change)', function(assert) {
    assert.equal('c1f',      '%x'.format(3103));
    assert.equal('C1F',      '%X'.format(3103));
    assert.equal('c1f',      '%+x'.format(3103));  // bug ! "0xc1f"
    assert.equal('c1f',      '% x'.format(3103));  // bug ! "0xc1f"
    assert.equal('fffff3e1', '%x'.format(-3103));
    assert.equal('00c1f', '%05x'.format(3103));
    assert.equal('  c1f', '%5x'.format(3103));
    assert.equal('c1f  ', '%-5x'.format(3103));

    assert.equal('1101',   '%b'.format(13));
    assert.equal('1101',   '%+b'.format(13));  // bug ! "0b1101"
    assert.equal('1101',   '% b'.format(13));  // bug ! "0b1101"
    assert.equal('11111111111111111111111111110011',   '%b'.format(-13));
    assert.equal('01101', '%05b'.format(13));
    assert.equal(' 1101', '%5b'.format(13));
    assert.equal(' 1101', '%+5b'.format(13));
    assert.equal('1101 ', '%-5b'.format(13));

    assert.equal('15',   '%o'.format(13));
    assert.equal('15',   '%+o'.format(13));  // bug ! "015"
    assert.equal('15',   '% o'.format(13));  // bug ! "015"
    assert.equal('37777777763',   '%o'.format(-13));
    assert.equal('00015', '%05o'.format(13));
    assert.equal('   15', '%5o'.format(13));
    assert.equal('   15', '%+5o'.format(13));
    assert.equal('15   ', '%-5o'.format(13));
});

QUnit.test('fallbacks.String.format (decimal)', function(assert) {
    assert.equal('0.012', '%.3p'.format(0.012));
    assert.equal('12', '%.4p'.format(12.0));
    assert.equal('4.321e-5', '%.4p'.format(0.00004321));

    assert.equal('0.0120', '%.3g'.format(0.012));
    assert.equal('12.00', '%.4g'.format(12.0));
    assert.equal('0.00004321', '%.4g'.format(0.00004321));  // bug !

    assert.equal('12.457000', '%f'.format(12.457));
    assert.equal('12.457000', '%09f'.format(12.457));
    assert.equal('12.457000', '%9f'.format(12.457));
    assert.equal('12.457000', '%-9f'.format(12.457));
    assert.equal('12.457',    '%05.3f'.format(12.457));
    assert.equal('12.457',    '%5.3f'.format(12.457));
    assert.equal('12.457',    '%-5.3f'.format(12.457));
    assert.equal('12.46',     '%.2f'.format(12.457));
    assert.equal('12.46',     '%.2f'.format(12.457));
    assert.equal('12.46',     '%-.2f'.format(12.457));
});

QUnit.test('fallbacks.String.template', function(assert) {
    assert.equal('12', '${a}'.template({a: 12}));
    assert.equal('12 monkeys are jumping.', '${a} ${b} are jumping.'.template({a: 12, b: 'monkeys'}));
    assert.equal('12 ${b} are jumping.', '${a} ${b} are jumping.'.template({a: 12}));
    assert.equal('${a} monkeys are jumping.', '${a} ${b} are jumping.'.template({b: 'monkeys'}));

    assert.equal('${a} ${b} are jumping.', '${a} ${b} are jumping.'.template());
    assert.equal('${a} ${b} are jumping.', '${a} ${b} are jumping.'.template({}));

    assert.equal('this an empty template.', 'this an empty template.'.template({a: 12}));
});

QUnit.test('fallbacks.String.template (method)', function(assert) {
    assert.equal('12', '${a}'.template(function() {
        return 12;
    }));
    assert.equal('12 monkeys are jumping.', '${a} ${b} are jumping.'.template(function(key) {
        if (key === 'a') {
            return 12;
        } else {
            return 'monkeys';
        }
    }));
    assert.equal('12 ${b} are jumping.', '${a} ${b} are jumping.'.template(function(key) {
        if (key === 'a') {
            return 12;
        }
    }));
    assert.equal('${a} monkeys are jumping.', '${a} ${b} are jumping.'.template(function(key) {
        if (key === 'b') {
            return 'monkeys';
        }
    }));
});

QUnit.test('fallbacks.String.capitalize', function(assert) {
    assert.equal('', ''.capitalize());
    assert.equal('A', 'A'.capitalize());
    assert.equal('A', 'a'.capitalize());
    assert.equal('Abcd', 'abcd'.capitalize());
});

QUnit.test('fallbacks.String.isDigit', function(assert) {
    assert.equal(''.isDigit(), false);
    assert.equal('abcd'.isDigit(), false);
    assert.equal('0'.isDigit(), true);
    assert.equal('01124'.isDigit(), true);
    assert.equal('52400'.isDigit(), true);
    assert.equal('-52400'.isDigit(), true);
    assert.equal('+52400'.isDigit(), true);
});

QUnit.test('fallbacks.String.isAlpha', function(assert) {
    assert.equal(''.isAlpha(), false);
    assert.equal('0'.isAlpha(), false);
    assert.equal('01124'.isAlpha(), false);
    assert.equal('abcd'.isAlpha(), true);
    assert.equal('éõô'.isAlpha(), false);
});

QUnit.test('fallbacks.String.isSpace', function(assert) {
    assert.equal(''.isSpace(), false);
    assert.equal('0'.isSpace(), false);
    assert.equal('abcd'.isSpace(), false);
    assert.equal(' '.isSpace(), true);
    assert.equal('   '.isSpace(), true);
    assert.equal('\t'.isSpace(), true);
    assert.equal('\t   \t'.isSpace(), true);
});

QUnit.test('fallbacks.String.removeDiacritics', function(assert) {
    assert.equal(''.removeDiacritics(), '');
    assert.equal('Éé'.removeDiacritics(), 'Ee');
    assert.equal('åkà ! çétÔwîÂrg.'.removeDiacritics(), 'aka ! cetOwiArg.');
});

QUnit.test('fallbacks.String.decodeHTMLEntities', function(assert) {
    assert.equal(''.decodeHTMLEntities(), '');
    assert.equal('&amp;&quot;&apos;&lt;&gt;&unk;'.decodeHTMLEntities(), '&"\'<>&unk;');
    assert.equal('&#x000C8;&&#x000C9;;'.decodeHTMLEntities(), 'È&É;');
    assert.equal('&#200;&&#201;;'.decodeHTMLEntities(), 'È&É;');
    assert.equal('\\u00C8&\\u00C9;'.decodeHTMLEntities(), 'È&É;');
});

QUnit.test('fallbacks.String.unescapeHTML', function(assert) {
    assert.equal('  &amp;&quot;&apos;&lt;&gt;  &unk;  '.unescapeHTML(), '  &"\'<>  &unk;  ');
});

QUnit.test('fallbacks.String.escapeHTML', function(assert) {
    assert.equal('  &"\'<>\u00A0'.escapeHTML(), '  &amp;&quot;&apos;&lt;&gt;&nbsp;');
});

}(jQuery));
