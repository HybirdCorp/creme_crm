module("creme.fallbacks.js", {
    setup: function() {
    },

    teardown: function() {
    }
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
