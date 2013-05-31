module("creme.fallbacks.js", {
    setup: function() {
    },

    teardown: function() {
    }
});

MockObjectA = function(b) {
    this.b = b;
}

MockObjectA.prototype = {
    'add': function(a) {return a + this.b;},
    'mult': function(a) {return a * this.b;}
}
MockObjectA.prototype.constructor = MockObjectA;

MockObjectB = function(b, c) {
    this.b = b;
    this.c = c;
}

MockObjectB.prototype = new MockObjectA();
MockObjectB.prototype.constructor = MockObjectB;

$.extend(MockObjectB.prototype, {
    'add': function(a) {return (a + this.b) * this.c;}
});

test('fallbacks.Object.isNone', function() {
    equal(typeof Object.isNone, 'function');

    equal(Object.isNone(undefined), true);
    equal(Object.isNone(null), true);
    equal(Object.isNone({}), false);
    equal(Object.isNone([]), false);
    equal(Object.isNone(0), false);
    equal(Object.isNone(''), false);
});

test('fallbacks.Object.isEmpty', function() {
    equal(typeof Object.isEmpty, 'function');

    equal(Object.isEmpty(undefined), true);
    equal(Object.isEmpty(null), true);
    equal(Object.isEmpty({}), true);
    equal(Object.isEmpty([]), true);
    equal(Object.isEmpty(''), true);

    equal(Object.isEmpty(0), false);
    equal(Object.isEmpty(15), false);
    equal(Object.isEmpty({a:12}), false);
    equal(Object.isEmpty([12]), false);
    equal(Object.isEmpty('a'), false);
});

test('fallbacks.Object.isType (undefined)', function() {
    equal(typeof Object.isType, 'function');

    equal(Object.isType(undefined, 'undefined'), true);
    equal(Object.isType(undefined, 'null'),      false);
    equal(Object.isType(undefined, 'function'),  false);
    equal(Object.isType(undefined, 'number'),    false);
    equal(Object.isType(undefined, 'object'),    false);
    equal(Object.isType(undefined, 'boolean'),   false);
    equal(Object.isType(undefined, 'string'),    false);
});

test('fallbacks.Object.isType (null)', function() {
    equal(Object.isType(null, 'undefined'), false);
    equal(Object.isType(null, 'null'),      false);
    equal(Object.isType(null, 'function'),  false);
    equal(Object.isType(null, 'number'),    false);
    equal(Object.isType(null, 'object'),    true);
    equal(Object.isType(null, 'boolean'),   false);
    equal(Object.isType(null, 'string'),    false);
});

test('fallbacks.Object.isType (string)', function() {
    equal(Object.isType('a', 'undefined'), false);
    equal(Object.isType('a', 'null'),      false);
    equal(Object.isType('a', 'function'),  false);
    equal(Object.isType('a', 'number'),    false);
    equal(Object.isType('a', 'object'),    false);
    equal(Object.isType('a', 'boolean'),   false);
    equal(Object.isType('a', 'string'),    true);
});

test('fallbacks.Object.isType (numeric)', function() {
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

test('fallbacks.Object.isType (boolean)', function() {
    equal(Object.isType(true, 'undefined'), false);
    equal(Object.isType(true, 'null'),      false);
    equal(Object.isType(true, 'function'),  false);
    equal(Object.isType(true, 'number'),    false);
    equal(Object.isType(true, 'object'),    false);
    equal(Object.isType(true, 'boolean'),   true);
    equal(Object.isType(true, 'string'),    false);
});

test('fallbacks.Object.isType (function)', function() {
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

test('fallbacks.Object.keys', function() {
    deepEqual([], Object.keys({}));
    deepEqual(['a', 'b'], Object.keys({a:1, b:2}));
    deepEqual(['a', 'b', 'c', 'd', 'z'], Object.keys({a:1, b:2, c:5, d:7, z:8}));
});

test('fallbacks.Object.proxy (no context)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a);

    equal(a == proxy, false);
    equal(a.b, 5);
    equal(proxy.b, undefined);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), 2 + 5);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult(2), 2 * 5);
});

test('fallbacks.Object.proxy (context)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, {b: 12});

    equal(a == proxy, false);
    equal(a.b, 5);
    equal(proxy.b, 12);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), 2 + 12);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult(2), 2 * 12);
});

test('fallbacks.Object.proxy (filter)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, undefined, {filter: function(key) {return key !== 'mult';}});

    equal(a == proxy, false);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), 2 + 5);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult, undefined);
});

test('fallbacks.Object.proxy (filter, context)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, {b: 12}, {filter: function(key) {return key !== 'mult';}});

    equal(a == proxy, false);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), 2 + 12);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult, undefined);
});

test('fallbacks.Object.proxy (arguments)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, undefined, {arguments: function(args) {return [args[0] * 0.8];}});

    equal(a == proxy, false);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), (2 * 0.8) + 5);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult(2), (2 * 0.8) * 5);
});

test('fallbacks.Object.proxy (arguments, context)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, {b: 12}, {arguments: function(args) {return [args[0] * 0.8];}});

    equal(a == proxy, false);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), (2 * 0.8) + 12);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult(2), (2 * 0.8) * 12);
});


test('fallbacks.Object.proxy (arguments, filter)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, undefined, {
        arguments: function(args) {return [args[0] * 0.8];},
        filter: function(key) {return key !== 'mult';}
    });

    equal(a == proxy, false);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), (2 * 0.8) + 5);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult, undefined);
});

test('fallbacks.Object.proxy (arguments, filter, context)', function() {
    equal(typeof Object.proxy, 'function');

    var a = new MockObjectA(5);
    var proxy = Object.proxy(a, {b: 12}, {
        arguments: function(args) {return [args[0] * 0.8];},
        filter: function(key) {return key !== 'mult';}
    });

    equal(a == proxy, false);

    equal(a.add(2), 2 + 5);
    equal(proxy.add(2), (2 * 0.8) + 12);

    equal(a.mult(2), 2 * 5);
    equal(proxy.mult, undefined);
});

test('fallbacks.Object.getPrototypeOf (object)', function() {
    equal(typeof Object.getPrototypeOf, 'function');

    var a = new MockObjectA(5);
    var b = new MockObjectB(8, 3);

    equal(Object.getPrototypeOf(a), MockObjectA.prototype, 'a.prototype');
    equal(Object.getPrototypeOf(a).constructor, MockObjectA, 'a.constructor');

    equal(Object.getPrototypeOf(b), MockObjectB.prototype, 'b.prototype');
    equal(Object.getPrototypeOf(b).constructor, MockObjectB, 'b.constructor');
});

test('fallbacks.Object._super (object)', function() {
    equal(typeof Object._super, 'function');

    var a = new MockObjectA(5);
    var b = new MockObjectB(8, 3);

    equal(b.add(2), (2 + 8)*3);
    equal(b.mult(2), 2 * 8);

    equal(Object._super(MockObjectB, b).add(2), 2 + 8);
    equal(Object._super(MockObjectB, b).mult(2), 2 * 8);
});

test('fallbacks.Object._super (method)', function() {
    equal(typeof Object._super, 'function');

    var a = new MockObjectA(5);
    var b = new MockObjectB(8, 3);

    equal(b.add(2), (2 + 8)*3);
    equal(b.mult(2), 2 * 8);

    equal(Object._super(MockObjectB, b, 'add', 2), 2 + 8);
    equal(Object._super(MockObjectB, b, 'mult', 2), 2 * 8);
});

test('fallbacks.Array.indexOf', function() {
    equal(typeof Array.prototype.indexOf, 'function');
    equal(typeof [].indexOf, 'function');

    equal([12, 5, 8, 5, 44].indexOf(5), 1);
    equal([12, 5, 8, 5, 44].indexOf(5, 2), 3);
    
    equal([12, 5, 8, 5, 44].indexOf(15), -1);
    
    equal([12, 5, 8, 5, 44].indexOf(12), 0);
    equal([12, 5, 8, 5, 44].indexOf(12, 1), -1);
});

test('fallbacks.Array.slice', function() {
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

test('fallbacks.Array.map', function() {
    equal(typeof Array.prototype.map, 'function');
    equal(typeof [].map, 'function');

    deepEqual(["my", "Name", "is", "HARRY"].map(function(element, index, array) {
                                                   return element.toUpperCase();
                                                }), ["MY", "NAME", "IS", "HARRY"]);
});

test('fallbacks.Array.forEach', function() {
    equal(typeof Array.prototype.forEach, 'function');
    equal(typeof [].forEach, 'function');

    var value = "";
    ["This", "is", "a", "forEach", "test"].forEach(function(element, index, array) {value += element;});

    equal(value, 'ThisisaforEachtest');
});

test('fallbacks.Array.isArray', function() {
    equal(typeof Array.isArray, 'function');
    equal(Array.isArray([]), true);
    equal(Array.isArray([12, 5, 5]), true);
    equal(Array.isArray(new Array()), true);

    equal(Array.isArray(undefined), false);
    equal(Array.isArray(null), false);

    equal(Array.isArray({}), false);
    equal(Array.isArray({'test': 1}), false);
});

if (jQuery === undefined)
{
    test('fallbacks.Array.contains', function() {
        equal(typeof Array.prototype.contains, 'function');
        equal(typeof [].contains, 'function');
    
        equal([1, 2, 1, 4, 5, 4].contains(1), true);
        equal([1, 2, 1, 4, 5, 4].contains(2), true);
        equal([1, 2, 1, 4, 5, 4].contains(12), false);
    });
    
    test('fallbacks.Array.exfiltrate', function() {
        equal(typeof Array.prototype.exfiltrate, 'function');
        equal(typeof [].exfiltrate, 'function');
    
        deepEqual([1, 2, 1, 4, 5, 4].exfiltrate([1, 2]), [4, 5, 4]);
    });
    
    test('fallbacks.Array.every', function() {
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
    
    test('fallbacks.Array.filter', function() {
        equal(typeof Array.prototype.filter, 'function');
        equal(typeof [].filter, 'function');
    
        deepEqual([12, 5, 8, 1, 44].filter(function(element, index, array) {
                                               return element >= 10;
                                           }), [12, 44]);
    });

    test('fallbacks.Array.getRange', function() {
        equal(typeof Array.prototype.getRange, 'function');
        equal(typeof [].getRange, 'function');
    
        deepEqual([1, 2, 1, 4, 5, 4].getRange(2, 4), [1, 4, 5]);
    });
    
    
    test('fallbacks.Array.inArray', function() {
        equal(typeof Array.prototype.inArray, 'function');
        equal(typeof [].inArray, 'function');
    
        equal([12, 5, 8, 5, 44].inArray(5), true);
        equal([12, 5, 8, 5, 44].inArray(58), false);
    });
    
    test('fallbacks.Array.insertAt', function() {
        equal(typeof Array.prototype.insertAt, 'function');
        equal(typeof [].insertAt, 'function');
    
        deepEqual(['dog', 'cat', 'horse'].insertAt(2, 'mouse'), ['dog', 'cat', 'mouse', 'horse']);
    });
    
    test('fallbacks.Array.removeAt', function() {
        equal(typeof Array.prototype.removeAt, 'function');
        equal(typeof [].removeAt, 'function');
    
        deepEqual(['dog', 'cat', 'mouse', 'horse'].removeAt(2), ['dog', 'cat', 'horse']);
    });
    
    test('fallbacks.Array.some', function() {
        equal(typeof Array.prototype.some, 'function');
        equal(typeof [].some, 'function');
    
        equal([101, 199, 250, 20].some(function(element, index, array) {
                                            return element >= 100;
                                        }), true);
        
        equal([11, 99, 50, 20].some(function(element, index, array) {
                                          return element >= 100;
                                    }), false);
    });
    
    test('fallbacks.Array.unique', function() {
        equal(typeof Array.prototype.unique, 'function');
        equal(typeof [].unique, 'function');
    
        deepEqual([1, 2, 1, 4, 5, 4].unique(), [1, 2, 4, 5]);
    });
}

test('fallbacks.HTMLDocument', function() {
    notEqual(typeof HTMLDocument, 'undefined');
});

test('fallbacks.HTMLDocument.createElementNS', function() {
    equal(typeof HTMLDocument.prototype.createElementNS, 'function');
});

test('fallbacks.CSSStyleDeclaration', function() {
    notEqual(typeof CSSStyleDeclaration, 'undefined');
});

test('fallbacks.Event', function() {
    notEqual(typeof Event, 'undefined');
});

test('fallbacks.Event.preventDefault', function() {
    equal(typeof Event.prototype.preventDefault, 'function');
});

test('fallbacks.String.trim', function() {
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

test('fallbacks.String.ltrim', function() {
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

test('fallbacks.String.rtrim', function() {
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

test('fallbacks.String.startsWith', function() {
    equal(''.startsWith(''), true);
    equal(''.startsWith('a'), false);

    equal('a'.startsWith('a'), true);
    equal('abcd'.startsWith('a'), true);
    equal('abcd'.startsWith('abcd'), true);

    equal('d'.startsWith('a'), false);
    equal('dcba'.startsWith('a'), false);
    equal('dcba'.startsWith('abcd'), false);
});

test('fallbacks.String.endsWith', function() {
    equal(''.endsWith(''), true);
    equal(''.endsWith('a'), false);

    equal('d'.endsWith('d'), true);
    equal('abcd'.endsWith('d'), true);
    equal('abcd'.endsWith('abcd'), true);

    equal('a'.endsWith('d'), false);
    equal('dcba'.endsWith('d'), false);
    equal('dcba'.startsWith('abcd'), false);
});

test('fallbacks.String.format', function() {
    equal('12',    '%d'.format(12))
    equal('00012', '%05d'.format(12))
    equal('   12', '%5d'.format(12))
    equal('12   ', '%-5d'.format(12))
    
    equal('12.457000', '%f'.format(12.457))
    equal('12.457000', '%09f'.format(12.457))
    equal('12.457000', '%9f'.format(12.457))
    equal('12.457000', '%-9f'.format(12.457))
    equal('12.457',    '%05.3f'.format(12.457))
    equal('12.457',    '%5.3f'.format(12.457))
    equal('12.457',    '%-5.3f'.format(12.457))
    equal('12.46',     '%.2f'.format(12.457))
    equal('12.46',     '%.2f'.format(12.457))
    equal('12.46',     '%-.2f'.format(12.457))
});

test('fallbacks.String.capitalize', function() {
    equal('', ''.capitalize());
    equal('A', 'A'.capitalize());
    equal('A', 'a'.capitalize());
    equal('Abcd', 'abcd'.capitalize());
});

test('fallbacks.String.isDigit', function() {
    equal(''.isDigit(), false);
    equal('abcd'.isDigit(), false);
    equal('0'.isDigit(), true);
    equal('01124'.isDigit(), true);
    equal('52400'.isDigit(), true);
    equal('-52400'.isDigit(), true);
    equal('+52400'.isDigit(), true);
});

test('fallbacks.String.isAlpha', function() {
    equal(''.isAlpha(), false);
    equal('0'.isAlpha(), false);
    equal('01124'.isAlpha(), false);
    equal('abcd'.isAlpha(), true);
    equal('éõô'.isAlpha(), false);
});

test('fallbacks.String.isSpace', function() {
    equal(''.isSpace(), false);
    equal('0'.isSpace(), false);
    equal('abcd'.isSpace(), false);
    equal(' '.isSpace(), true);
    equal('   '.isSpace(), true);
    equal('\t'.isSpace(), true);
    equal('\t   \t'.isSpace(), true);
});
