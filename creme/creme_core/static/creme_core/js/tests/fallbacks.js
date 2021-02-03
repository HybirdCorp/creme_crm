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

QUnit.test('fallbacks.Object.isNone', function() {
    equal(typeof Object.isNone, 'function');

    equal(Object.isNone(undefined), true);
    equal(Object.isNone(null), true);
    equal(Object.isNone({}), false);
    equal(Object.isNone([]), false);
    equal(Object.isNone(0), false);
    equal(Object.isNone(''), false);
});

QUnit.test('fallbacks.Object.isEmpty', function() {
    equal(typeof Object.isEmpty, 'function');

    equal(Object.isEmpty(undefined), true);
    equal(Object.isEmpty(null), true);
    equal(Object.isEmpty({}), true);
    equal(Object.isEmpty([]), true);
    equal(Object.isEmpty(''), true);

    equal(Object.isEmpty(0), false);
    equal(Object.isEmpty(15), false);
    equal(Object.isEmpty({a: 12}), false);
    equal(Object.isEmpty([12]), false);
    equal(Object.isEmpty('a'), false);
});

QUnit.test('fallbacks.Object.isType (undefined)', function() {
    equal(typeof Object.isType, 'function');

    equal(Object.isType(undefined, 'undefined'), true);
    equal(Object.isType(undefined, 'null'),      false);
    equal(Object.isType(undefined, 'function'),  false);
    equal(Object.isType(undefined, 'number'),    false);
    equal(Object.isType(undefined, 'object'),    false);
    equal(Object.isType(undefined, 'boolean'),   false);
    equal(Object.isType(undefined, 'string'),    false);
});

QUnit.test('fallbacks.Object.isType (null)', function() {
    equal(Object.isType(null, 'undefined'), false);
    equal(Object.isType(null, 'null'),      false);
    equal(Object.isType(null, 'function'),  false);
    equal(Object.isType(null, 'number'),    false);
    equal(Object.isType(null, 'object'),    true);
    equal(Object.isType(null, 'boolean'),   false);
    equal(Object.isType(null, 'string'),    false);
});

QUnit.test('fallbacks.Object.isType (string)', function() {
    equal(Object.isType('a', 'undefined'), false);
    equal(Object.isType('a', 'null'),      false);
    equal(Object.isType('a', 'function'),  false);
    equal(Object.isType('a', 'number'),    false);
    equal(Object.isType('a', 'object'),    false);
    equal(Object.isType('a', 'boolean'),   false);
    equal(Object.isType('a', 'string'),    true);
});

QUnit.test('fallbacks.Object.isType (numeric)', function() {
    equal(Object.isType(12, 'undefined'), false);
    equal(Object.isType(12, 'null'),      false);
    equal(Object.isType(12, 'function'),  false);
    equal(Object.isType(12, 'number'),    true);
    equal(Object.isType(12, 'object'),    false);
    equal(Object.isType(12, 'boolean'),   false);
    equal(Object.isType(12, 'string'),    false);

    equal(Object.isType(12.55, 'undefined'), false);
    equal(Object.isType(12.55, 'null'),      false);
    equal(Object.isType(12.55, 'function'),  false);
    equal(Object.isType(12.55, 'number'),    true);
    equal(Object.isType(12.55, 'object'),    false);
    equal(Object.isType(12.55, 'boolean'),   false);
    equal(Object.isType(12.55, 'string'),    false);
});

QUnit.test('fallbacks.Object.isType (boolean)', function() {
    equal(Object.isType(true, 'undefined'), false);
    equal(Object.isType(true, 'null'),      false);
    equal(Object.isType(true, 'function'),  false);
    equal(Object.isType(true, 'number'),    false);
    equal(Object.isType(true, 'object'),    false);
    equal(Object.isType(true, 'boolean'),   true);
    equal(Object.isType(true, 'string'),    false);
});

QUnit.test('fallbacks.Object.isType (function)', function() {
    equal(Object.isType(function() {}, 'undefined'), false);
    equal(Object.isType(function() {}, 'null'),      false);
    equal(Object.isType(function() {}, 'function'),  true);
    equal(Object.isType(function() {}, 'number'),    false);
    equal(Object.isType(function() {}, 'object'),    false);
    equal(Object.isType(function() {}, 'boolean'),   false);
    equal(Object.isType(function() {}, 'string'),    false);

    equal(Object.isFunc(undefined),       false);
    equal(Object.isFunc(null, 'null'),    false);
    equal(Object.isFunc(function() {}),   true);
    equal(Object.isFunc(10, 'number'),    false);
    equal(Object.isFunc({}, 'object'),    false);
    equal(Object.isFunc(true, 'boolean'), false);
    equal(Object.isFunc('a', 'string'),   false);
});

QUnit.test('fallbacks.Object.keys', function() {
    equal(typeof Object.keys, 'function');
    equal({}.keys, undefined);

    deepEqual([], Object.keys({}));
    deepEqual(['a', 'b'], Object.keys({a: 1, b: 2}));
    deepEqual(['a', 'b', 'c', 'd', 'z'], Object.keys({a: 1, b: 2, c: 5, d: 7, z: 8}));
});

QUnit.test('fallbacks.Object.values', function() {
    equal(typeof Object.values, 'function');
    equal({}.values, undefined);

    deepEqual([], Object.values({}));
    deepEqual([1, 2], Object.values({a: 1, b: 2}));
    deepEqual([1, 2, 5, 7, 8], Object.values({a: 1, b: 2, c: 5, d: 7, z: 8}));
});


QUnit.test('fallbacks.Object.entries', function() {
    equal(typeof Object.entries, 'function');
    equal({}.entries, undefined);

    deepEqual([], Object.entries({}));
    deepEqual([['a', 1], ['b', 2]], Object.entries({a: 1, b: 2}));
    deepEqual([['a', 1], ['b', 2], ['c', 5], ['d', 7], ['z', 8]], Object.entries({a: 1, b: 2, c: 5, d: 7, z: 8}));
});

QUnit.test('fallbacks.Object.proxy (undefined)', function() {
    equal(undefined, Object.proxy(null));
    equal(undefined, Object.proxy());
});

QUnit.test('fallbacks.Object.proxy (no context)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a);

    notDeepEqual(a, proxy);
    deepEqual(a, proxy.__context__);

    equal(a.b, 5);
    equal(proxy.__context__.b, 5);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), 2 + 5);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult(2), 2 * 5);
});

QUnit.test('fallbacks.Object.proxy (context)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, {b: 12});

    notDeepEqual(a, proxy);
    notDeepEqual(a, proxy.__context__);

    equal(a.b, 5);
    equal(proxy.__context__.b, 12);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), 2 + 12);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult(2), 2 * 12);
});

QUnit.test('fallbacks.Object.proxy (filter)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, undefined, {filter: function(key) { return key !== 'mult'; }});

    notDeepEqual(a, proxy);
    deepEqual(a, proxy.__context__);

    equal(a.b, 5);
    equal(proxy.__context__.b, 5);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), 2 + 5);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult, undefined);
});

QUnit.test('fallbacks.Object.proxy (filter, context)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, {b: 12}, {filter: function(key) { return key !== 'mult'; }});

    notDeepEqual(a, proxy);
    notDeepEqual(a, proxy.__context__);

    equal(a.b, 5);
    equal(proxy.__context__.b, 12);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), 2 + 12);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult, undefined);
});

QUnit.test('fallbacks.Object.proxy (arguments)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, undefined, {arguments: function(args) { return [args[0] * 0.8]; }});

    notDeepEqual(a, proxy);
    deepEqual(a, proxy.__context__);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), (2 * 0.8) + 5);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult(2), (2 * 0.8) * 5);
});

QUnit.test('fallbacks.Object.proxy (arguments, context)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, {b: 12}, {arguments: function(args) { return [args[0] * 0.8]; }});

    notDeepEqual(a, proxy);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), (2 * 0.8) + 12);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult(2), (2 * 0.8) * 12);
});


QUnit.test('fallbacks.Object.proxy (arguments, filter)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, undefined, {
        arguments: function(args) { return [args[0] * 0.8]; },
        filter: function(key) { return key !== 'mult'; }
    });

    notDeepEqual(a, proxy);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), (2 * 0.8) + 5);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult, undefined);
});

QUnit.test('fallbacks.Object.proxy (arguments, filter, context)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, {b: 12}, {
        arguments: function(args) { return [args[0] * 0.8]; },
        filter: function(key) { return key !== 'mult'; }
    });

    notDeepEqual(a, proxy);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), (2 * 0.8) + 12);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult, undefined);
});

QUnit.test('fallbacks.Object.getPrototypeOf (object)', function() {
    equal(typeof Object.getPrototypeOf, 'function');

    var a = new MockObjectA(5);
    var b = new MockObjectB(8, 3);

    equal(Object.getPrototypeOf(a), MockObjectA.prototype, 'a.prototype');
    equal(Object.getPrototypeOf(a).constructor, MockObjectA, 'a.constructor');

    equal(Object.getPrototypeOf(b), MockObjectB.prototype, 'b.prototype');
    equal(Object.getPrototypeOf(b).constructor, MockObjectB, 'b.constructor');
});

QUnit.test('fallbacks.Object.isPrototypeOf (object)', function() {
    equal(typeof Object.prototype.isPrototypeOf, 'function');

    var a = new MockObjectA(5);
    var b = new MockObjectB(8, 3);

    equal(true, Object.prototype.isPrototypeOf(a), 'Object isPrototype of a');
    equal(true, Object.prototype.isPrototypeOf(b), 'Object isPrototype of b');

    equal(true, MockObjectA.prototype.isPrototypeOf(a), 'MockObjectA isPrototype of a');
    equal(true, MockObjectA.prototype.isPrototypeOf(b), 'MockObjectA isPrototype of b');

    equal(false, MockObjectB.prototype.isPrototypeOf(a), 'MockObjectB not isPrototype of a');
    equal(true, MockObjectB.prototype.isPrototypeOf(b), 'MockObjectB isPrototype of b');
});

QUnit.test('fallbacks.Object.isSubClassOf (object)', function() {
    equal(typeof Object.isSubClassOf, 'function');

    var o = {};
    var a = new MockObjectA(5);
    var b = new MockObjectB(8, 3);

    equal(false, Object.isSubClassOf(null, Object), 'Object not isPrototype of null');
    equal(false, Object.isSubClassOf(undefined, Object), 'Object not isPrototype of undefined');
    equal(true, Object.isSubClassOf(o, Object), 'Object isPrototype of o');
    equal(true, Object.isSubClassOf(a, Object), 'Object isPrototype of a');
    equal(true, Object.isSubClassOf(a, Object), 'Object isPrototype of b');
    equal(false, Object.isSubClassOf(a, null), 'null not isPrototype of a');
    equal(false, Object.isSubClassOf(a, undefined), 'undefined not isPrototype of b');

    equal(false, Object.isSubClassOf(null, MockObjectA), 'MockObjectA not isPrototype of null');
    equal(false, Object.isSubClassOf(undefined, MockObjectA), 'MockObjectA not isPrototype of undefined');
    equal(false, Object.isSubClassOf(o, MockObjectA), 'MockObjectA not isPrototype of o');
    equal(true, Object.isSubClassOf(a, MockObjectA), 'MockObjectA isPrototype of a');
    equal(true, Object.isSubClassOf(b, MockObjectA), 'MockObjectA isPrototype of b');

    equal(false, Object.isSubClassOf(null, MockObjectB), 'MockObjectB not isPrototype of null');
    equal(false, Object.isSubClassOf(undefined, MockObjectB), 'MockObjectB not isPrototype of undefined');
    equal(false, Object.isSubClassOf(o, MockObjectB), 'MockObjectB not isPrototype of o');
    equal(false, Object.isSubClassOf(a, MockObjectB), 'MockObjectB not isPrototype of a');
    equal(true, Object.isSubClassOf(b, MockObjectB), 'MockObjectB isPrototype of b');
});

QUnit.test('fallbacks.Object.isString', function() {
    equal(typeof Object.isString, 'function');

    equal(Object.isString(''), true);
    equal(Object.isString(String('')), true);
    equal(Object.isString(false), false);
    equal(Object.isString([12, 13]), false);
    equal(Object.isString(new MockObjectA()), false);
    equal(Object.isString({}), false);
    equal(Object.isString(undefined), false);
    equal(Object.isString(null), false);
});

QUnit.test('fallbacks.Array.indexOf', function() {
    equal(typeof Array.prototype.indexOf, 'function');
    equal(typeof [].indexOf, 'function');

    equal([12, 5, 8, 5, 44].indexOf(5), 1);
    equal([12, 5, 8, 5, 44].indexOf(5, 2), 3);

    equal([12, 5, 8, 5, 44].indexOf(15), -1);

    equal([12, 5, 8, 5, 44].indexOf(12), 0);
    equal([12, 5, 8, 5, 44].indexOf(12, 1), -1);
});

QUnit.test('fallbacks.Array.slice', function() {
    equal(typeof Array.prototype.slice, 'function');
    equal(typeof [].slice, 'function');

    var original = [1, 2, 1, 4, 5, 4];
    var copy = original.slice();
    copy[2] = 12;

    deepEqual(original, [1, 2, 1, 4, 5, 4]);
    deepEqual(copy, [1, 2, 12, 4, 5, 4]);

    deepEqual([1, 2, 1, 4, 5, 4].slice(3), [4, 5, 4]);
    deepEqual([1, 2, 1, 4, 5, 4].slice(1, 4), [2, 1, 4]);
});

QUnit.test('fallbacks.Array.map', function() {
    equal(typeof Array.prototype.map, 'function');
    equal(typeof [].map, 'function');

    deepEqual(["my", "Name", "is", "HARRY"].map(function(element, index, array) {
                                                   return element.toUpperCase();
                                                }), ["MY", "NAME", "IS", "HARRY"]);
});

QUnit.test('fallbacks.Array.forEach', function() {
    equal(typeof Array.prototype.forEach, 'function');
    equal(typeof [].forEach, 'function');

    var value = "";
    ["This", "is", "a", "forEach", "test"].forEach(function(element, index, array) { value += element; });

    equal(value, 'ThisisaforEachtest');
});

QUnit.test('fallbacks.Array.isArray', function() {
    equal(typeof Array.isArray, 'function');
    equal(Array.isArray([]), true);
    equal(Array.isArray([12, 5, 5]), true);
    equal(Array.isArray(new Array()), true);  // eslint-disable-line no-array-constructor

    equal(Array.isArray(undefined), false);
    equal(Array.isArray(null), false);

    equal(Array.isArray({}), false);
    equal(Array.isArray({'test': 1}), false);
});

QUnit.test('fallbacks.Array.copy', function() {
    equal(typeof Array.copy, 'function');

    deepEqual([], Array.copy([]));
    deepEqual(['a', 'b'], Array.copy(['a', 'b']));

    deepEqual(['b', 'c'], Array.copy(['a', 'b', 'c'], 1));
    deepEqual([], Array.copy(['a', 'b', 'c'], 10));

    deepEqual(['b'], Array.copy(['a', 'b', 'c'], 1, 2));
    deepEqual([], Array.copy(['a', 'b', 'c'], 1, 1));
    deepEqual(['b', 'c'], Array.copy(['a', 'b', 'c'], 1, 10));
});

QUnit.test('fallbacks.Array.copy (arguments)', function() {
    var f = function() {
        return Array.copy(arguments);
    };

    var f_1 = function() {
        return Array.copy(arguments, 1);
    };

    var f_1_2 = function() {
        return Array.copy(arguments, 1, 2);
    };

    deepEqual([], f());
    deepEqual(['a', 'b', 'c'], f('a', 'b', 'c'));
    deepEqual([['a', 'b', 'c']], f(['a', 'b', 'c']));

    deepEqual([], f_1());
    deepEqual(['b', 'c'], f_1('a', 'b', 'c'));
    deepEqual([], f_1(['a', 'b', 'c']));

    deepEqual([], f_1_2());
    deepEqual(['b'], f_1_2('a', 'b', 'c'));
    deepEqual([], f_1_2(['a', 'b', 'c']));
});

if (jQuery === undefined) {
    QUnit.test('fallbacks.Array.contains', function() {
        equal(typeof Array.prototype.contains, 'function');
        equal(typeof [].contains, 'function');

        equal([1, 2, 1, 4, 5, 4].contains(1), true);
        equal([1, 2, 1, 4, 5, 4].contains(2), true);
        equal([1, 2, 1, 4, 5, 4].contains(12), false);
    });

    QUnit.test('fallbacks.Array.exfiltrate', function() {
        equal(typeof Array.prototype.exfiltrate, 'function');
        equal(typeof [].exfiltrate, 'function');

        deepEqual([1, 2, 1, 4, 5, 4].exfiltrate([1, 2]), [4, 5, 4]);
    });

    QUnit.test('fallbacks.Array.every', function() {
        equal(typeof Array.prototype.every, 'function');
        equal(typeof [].every, 'function');

        // all elements >= 15
        equal([22, 72, 16, 99, 254].every(function(element, index, array) {
                                              return element >= 15;
                                          }), true);

        // first element is < 15
        equal([12, 72, 16, 99, 254].every(function(element, index, array) {
                                              return element >= 15;
                                          }), false);
    });

    QUnit.test('fallbacks.Array.filter', function() {
        equal(typeof Array.prototype.filter, 'function');
        equal(typeof [].filter, 'function');

        deepEqual([12, 5, 8, 1, 44].filter(function(element, index, array) {
                                               return element >= 10;
                                           }), [12, 44]);
    });

    QUnit.test('fallbacks.Array.getRange', function() {
        equal(typeof Array.prototype.getRange, 'function');
        equal(typeof [].getRange, 'function');

        deepEqual([1, 2, 1, 4, 5, 4].getRange(2, 4), [1, 4, 5]);
    });


    QUnit.test('fallbacks.Array.inArray', function() {
        equal(typeof Array.prototype.inArray, 'function');
        equal(typeof [].inArray, 'function');

        equal([12, 5, 8, 5, 44].inArray(5), true);
        equal([12, 5, 8, 5, 44].inArray(58), false);
    });

    QUnit.test('fallbacks.Array.insertAt', function() {
        equal(typeof Array.prototype.insertAt, 'function');
        equal(typeof [].insertAt, 'function');

        deepEqual(['dog', 'cat', 'horse'].insertAt(2, 'mouse'), ['dog', 'cat', 'mouse', 'horse']);
    });

    QUnit.test('fallbacks.Array.removeAt', function() {
        equal(typeof Array.prototype.removeAt, 'function');
        equal(typeof [].removeAt, 'function');

        deepEqual(['dog', 'cat', 'mouse', 'horse'].removeAt(2), ['dog', 'cat', 'horse']);
    });

    QUnit.test('fallbacks.Array.some', function() {
        equal(typeof Array.prototype.some, 'function');
        equal(typeof [].some, 'function');

        equal([101, 199, 250, 20].some(function(element, index, array) {
                                            return element >= 100;
                                        }), true);

        equal([11, 99, 50, 20].some(function(element, index, array) {
                                          return element >= 100;
                                    }), false);
    });

    QUnit.test('fallbacks.Array.unique', function() {
        equal(typeof Array.prototype.unique, 'function');
        equal(typeof [].unique, 'function');

        deepEqual([1, 2, 1, 4, 5, 4].unique(), [1, 2, 4, 5]);
    });
}

QUnit.test('fallbacks.HTMLDocument', function() {
    notEqual(typeof HTMLDocument, 'undefined');
});

QUnit.test('fallbacks.HTMLDocument.createElementNS', function() {
    equal(typeof HTMLDocument.prototype.createElementNS, 'function');
});

QUnit.test('fallbacks.CSSStyleDeclaration', function() {
    notEqual(typeof CSSStyleDeclaration, 'undefined');
});

QUnit.test('fallbacks.Event', function() {
    notEqual(typeof Event, 'undefined');
});

QUnit.test('fallbacks.Event.preventDefault', function() {
    equal(typeof Event.prototype.preventDefault, 'function');
});

QUnit.test('fallbacks.String.trim', function() {
    equal('', ''.trim());
    equal('', '   '.trim());
    equal('', '\t\t'.trim());
    equal('abc', 'abc'.trim());
    equal('abc', '  abc'.trim());
    equal('abc', 'abc  '.trim());
    equal('abc', '  abc  '.trim());
    equal('abc', '\tabc'.trim());
    equal('abc', 'abc\t'.trim());
    equal('abc', '\tabc\t'.trim());
});

QUnit.test('fallbacks.String.ltrim', function() {
    equal('', ''.ltrim());
    equal('', '   '.ltrim());
    equal('', '\t\t'.ltrim());
    equal('abc', 'abc'.ltrim());
    equal('abc', 'abc'.ltrim());
    equal('abc  ', 'abc  '.ltrim());
    equal('abc  ', '  abc  '.ltrim());
    equal('abc', '\tabc'.ltrim());
    equal('abc\t', 'abc\t'.ltrim());
    equal('abc\t', '\tabc\t'.ltrim());
});

QUnit.test('fallbacks.String.rtrim', function() {
    equal('', ''.rtrim());
    equal('', '   '.rtrim());
    equal('', '\t\t'.rtrim());
    equal('abc', 'abc'.rtrim());
    equal('  abc', '  abc'.rtrim());
    equal('abc', 'abc  '.rtrim());
    equal('  abc', '  abc  '.rtrim());
    equal('\tabc', '\tabc'.rtrim());
    equal('abc', 'abc\t'.rtrim());
    equal('\tabc', '\tabc\t'.rtrim());
});

QUnit.test('fallbacks.String.startsWith', function() {
    equal(''.startsWith(''), true);
    equal(''.startsWith('a'), false);

    equal('a'.startsWith('a'), true);
    equal('abcd'.startsWith('a'), true);
    equal('abcd'.startsWith('abcd'), true);

    equal('d'.startsWith('a'), false);
    equal('dcba'.startsWith('a'), false);
    equal('dcba'.startsWith('abcd'), false);
});

QUnit.test('fallbacks.String.endsWith', function() {
    equal(''.endsWith(''), true);
    equal(''.endsWith('a'), false);

    equal('d'.endsWith('d'), true);
    equal('abcd'.endsWith('d'), true);
    equal('abcd'.endsWith('abcd'), true);

    equal('a'.endsWith('d'), false);
    equal('dcba'.endsWith('d'), false);
    equal('dcba'.startsWith('abcd'), false);
});

QUnit.test('fallbacks.String.format (skip format)', function() {
    equal('%d', '%%d'.format(12));
    equal('%12', '%%%d'.format(12));
});

QUnit.test('fallbacks.String.format (array)', function() {
    equal('12', '%d'.format([12, 5]));
    equal('12', '%0$d'.format([12, 5]));
    equal('5', '%1$d'.format([12, 5]));
    equal('8', '%2$d'.format([12, 5, 8, 7]));
});

QUnit.test('fallbacks.String.format (padding)', function() {
    equal('ab', '%s'.format('ab'));
    equal('12', '%s'.format(12));
    equal('12.05', '%s'.format(12.05));

    equal('   ab', '%5s'.format('ab'));
    equal('   12', '%5s'.format(12));
    equal('12.05', '%5s'.format(12.05));

    equal('+   ab', '+%5s'.format('ab'));  // bug ! "   ab"
    equal('&nbsp;&nbsp;&nbsp;ab', '%&5s'.format('ab'));
    equal('   ab', '%#5s'.format('ab'));

    equal('ab   ', '%-5s'.format('ab'));
    equal('12   ', '%-5s'.format(12));
    equal('12.05', '%-5s'.format(12.05));
});

QUnit.test('fallbacks.String.format (integer)', function() {
    equal('12',    '%d'.format(12.0));
    equal('12',    '%u'.format(12.0));
    equal('12',    '%i'.format(12.0));

    equal('',    '%d'.format({}));
    equal('0',    '%u'.format({}));  // bug ! NaN => ""
    equal('',    '%i'.format({}));

    equal('+12',    '%+d'.format(12));  // bug ! "12"
    equal(' 12',    '% d'.format(12));  // bug ! "12"
    equal('-12',    '%d'.format(-12));
    equal('00012', '%05d'.format(12));
    equal('   12', '%5d'.format(12));
    equal('12   ', '%-5d'.format(12));

    equal('12', '%\'d'.format(12));
    equal("12,412", '%\'d'.format(12412));
});

QUnit.test('fallbacks.String.format (base change)', function() {
    equal('c1f',      '%x'.format(3103));
    equal('C1F',      '%X'.format(3103));
    equal('c1f',      '%+x'.format(3103));  // bug ! "0xc1f"
    equal('c1f',      '% x'.format(3103));  // bug ! "0xc1f"
    equal('fffff3e1', '%x'.format(-3103));
    equal('00c1f', '%05x'.format(3103));
    equal('  c1f', '%5x'.format(3103));
    equal('c1f  ', '%-5x'.format(3103));

    equal('1101',   '%b'.format(13));
    equal('1101',   '%+b'.format(13));  // bug ! "0b1101"
    equal('1101',   '% b'.format(13));  // bug ! "0b1101"
    equal('11111111111111111111111111110011',   '%b'.format(-13));
    equal('01101', '%05b'.format(13));
    equal(' 1101', '%5b'.format(13));
    equal(' 1101', '%+5b'.format(13));
    equal('1101 ', '%-5b'.format(13));

    equal('15',   '%o'.format(13));
    equal('15',   '%+o'.format(13));  // bug ! "015"
    equal('15',   '% o'.format(13));  // bug ! "015"
    equal('37777777763',   '%o'.format(-13));
    equal('00015', '%05o'.format(13));
    equal('   15', '%5o'.format(13));
    equal('   15', '%+5o'.format(13));
    equal('15   ', '%-5o'.format(13));
});

QUnit.test('fallbacks.String.format (decimal)', function() {
    equal('0.012', '%.3p'.format(0.012));
    equal('12', '%.4p'.format(12.0));
    equal('4.321e-5', '%.4p'.format(0.00004321));

    equal('0.0120', '%.3g'.format(0.012));
    equal('12.00', '%.4g'.format(12.0));
    equal('0.00004321', '%.4g'.format(0.00004321));  // bug !

    equal('12.457000', '%f'.format(12.457));
    equal('12.457000', '%09f'.format(12.457));
    equal('12.457000', '%9f'.format(12.457));
    equal('12.457000', '%-9f'.format(12.457));
    equal('12.457',    '%05.3f'.format(12.457));
    equal('12.457',    '%5.3f'.format(12.457));
    equal('12.457',    '%-5.3f'.format(12.457));
    equal('12.46',     '%.2f'.format(12.457));
    equal('12.46',     '%.2f'.format(12.457));
    equal('12.46',     '%-.2f'.format(12.457));
});

QUnit.test('fallbacks.String.template', function() {
    equal('12', '${a}'.template({a: 12}));
    equal('12 monkeys are jumping.', '${a} ${b} are jumping.'.template({a: 12, b: 'monkeys'}));
    equal('12 ${b} are jumping.', '${a} ${b} are jumping.'.template({a: 12}));
    equal('${a} monkeys are jumping.', '${a} ${b} are jumping.'.template({b: 'monkeys'}));

    equal('${a} ${b} are jumping.', '${a} ${b} are jumping.'.template());
    equal('${a} ${b} are jumping.', '${a} ${b} are jumping.'.template({}));

    equal('this an empty template.', 'this an empty template.'.template({a: 12}));
});

QUnit.test('fallbacks.String.template (method)', function() {
    equal('12', '${a}'.template(function() {
        return 12;
    }));
    equal('12 monkeys are jumping.', '${a} ${b} are jumping.'.template(function(key) {
        if (key === 'a') {
            return 12;
        } else {
            return 'monkeys';
        }
    }));
    equal('12 ${b} are jumping.', '${a} ${b} are jumping.'.template(function(key) {
        if (key === 'a') {
            return 12;
        }
    }));
    equal('${a} monkeys are jumping.', '${a} ${b} are jumping.'.template(function(key) {
        if (key === 'b') {
            return 'monkeys';
        }
    }));
});

QUnit.test('fallbacks.String.capitalize', function() {
    equal('', ''.capitalize());
    equal('A', 'A'.capitalize());
    equal('A', 'a'.capitalize());
    equal('Abcd', 'abcd'.capitalize());
});

QUnit.test('fallbacks.String.isDigit', function() {
    equal(''.isDigit(), false);
    equal('abcd'.isDigit(), false);
    equal('0'.isDigit(), true);
    equal('01124'.isDigit(), true);
    equal('52400'.isDigit(), true);
    equal('-52400'.isDigit(), true);
    equal('+52400'.isDigit(), true);
});

QUnit.test('fallbacks.String.isAlpha', function() {
    equal(''.isAlpha(), false);
    equal('0'.isAlpha(), false);
    equal('01124'.isAlpha(), false);
    equal('abcd'.isAlpha(), true);
    equal('éõô'.isAlpha(), false);
});

QUnit.test('fallbacks.String.isSpace', function() {
    equal(''.isSpace(), false);
    equal('0'.isSpace(), false);
    equal('abcd'.isSpace(), false);
    equal(' '.isSpace(), true);
    equal('   '.isSpace(), true);
    equal('\t'.isSpace(), true);
    equal('\t   \t'.isSpace(), true);
});

QUnit.test('fallbacks.String.removeDiacritics', function() {
    equal(''.removeDiacritics(), '');
    equal('Éé'.removeDiacritics(), 'Ee');
    equal('åkà ! çétÔwîÂrg.'.removeDiacritics(), 'aka ! cetOwiArg.');
});

QUnit.test('fallbacks.String.decodeHTMLEntities', function() {
    equal(''.decodeHTMLEntities(), '');
    equal('&amp;&quot;&apos;&lt;&gt;&unk;'.decodeHTMLEntities(), '&"\'<>&unk;');
    equal('&#x000C8;&&#x000C9;;'.decodeHTMLEntities(), 'È&É;');
    equal('&#200;&&#201;;'.decodeHTMLEntities(), 'È&É;');
    equal('\\u00C8&\\u00C9;'.decodeHTMLEntities(), 'È&É;');
});

QUnit.test('fallbacks.String.unescapeHTML', function() {
    equal('  &amp;&quot;&apos;&lt;&gt;  &unk;  '.unescapeHTML(), '  &"\'<>  &unk;  ');
});

QUnit.test('fallbacks.String.escapeHTML', function() {
    equal('  &"\'<>\u00A0'.escapeHTML(), '  &amp;&quot;&apos;&lt;&gt;&nbsp;');
});

}(jQuery));
