(function($) {

QUnit.module("assert.Assert", new QUnitMixin());

QUnit.test('assert.Assert.that', function(assert) {
    var value = 12;

    Assert.that(true);
    Assert.that(function() { return true; });
    Assert.that(value < 20);
    Assert.that(function() { return value < 20; });

    this.assertRaises(function() {
        Assert.that(false);
    }, Error, 'Error: assertion failed');

    this.assertRaises(function() {
        Assert.that(function() { return false; });
    }, Error, 'Error: assertion failed');

    this.assertRaises(function() {
        Assert.that(value < 10, 'should be < 10');
    }, Error, 'Error: should be < 10');

    this.assertRaises(function() {
        Assert.that(value < 10, '${value} should be < 10', {value: 12});
    }, Error, 'Error: 12 should be < 10');
});

QUnit.test('assert.Assert.not', function(assert) {
    var value = 12;

    Assert.not(false);
    Assert.not(function() { return false; });
    Assert.not(value < 10);
    Assert.not(function() { return value < 10; });

    this.assertRaises(function() {
        Assert.not(true);
    }, Error, 'Error: assertion failed');

    this.assertRaises(function() {
        Assert.not(function() { return true; });
    }, Error, 'Error: assertion failed');

    this.assertRaises(function() {
        Assert.not(value > 10, 'should not be > 10');
    }, Error, 'Error: should not be > 10');

    this.assertRaises(function() {
        Assert.not(value > 10, '${value} should not be > 10', {value: 12});
    }, Error, 'Error: 12 should not be > 10');
});

QUnit.test('assert.Assert.is', function(assert) {
    Assert.is(String(''), 'string');
    Assert.is(function() {}, 'function');
    Assert.is(12, 'number');

    this.assertRaises(function() {
        Assert.is(null, 'string');
    }, Error, 'Error: null is not a string');

    this.assertRaises(function() {
        Assert.is(12, 'string');
    }, Error, 'Error: 12 is not a string');

    this.assertRaises(function() {
        Assert.is('', 'function');
    }, Error, 'Error: "" is not a function');

    this.assertRaises(function() {
        Assert.is(Assert, 'function');
    }, Error, 'Error: ${value} is not a function'.template({value: String(Assert)}));

    this.assertRaises(function() {
        Assert.is(12, 'function', 'this is not a function: ${value}');
    }, Error, 'Error: this is not a function: 12');
});

QUnit.test('assert.Assert.is (class)', function(assert) {
    var MockA = function() {};

    Assert.is([], Array);
    Assert.is(new Array(), Array);  /* eslint-disable-line */
    Assert.is(new MockA(), MockA);

    this.assertRaises(function() {
        Assert.is(null, Array);
    }, Error, 'Error: null is not a Array');

    this.assertRaises(function() {
        Assert.is(12, MockA);
    }, Error, 'Error: 12 is not a ${expected}'.template({expected: MockA}));

    this.assertRaises(function() {
        Assert.is(12, 'function', 'this is not a MockA: ${value}');
    }, Error, 'Error: this is not a MockA: 12');
});

QUnit.test('assert.Assert.isAnyOf', function(assert) {
    var MockA = function() {};

    Assert.isAnyOf([], [Array, 'object']);
    Assert.isAnyOf(new Array(), [Array, MockA]);   /* eslint-disable-line */
    Assert.isAnyOf(new MockA(), ['string', Array, MockA]);
    Assert.isAnyOf(String('a'), ['string', Array]);

    this.assertRaises(function() {
        Assert.isAnyOf(null, [Array, String]);
    }, Error, 'Error: null is none of [Array, String]');

    this.assertRaises(function() {
        Assert.isAnyOf(12, [MockA, 'string', Array]);
    }, Error, 'Error: 12 is none of [${mock}, string, Array]'.template({mock: MockA}));

    this.assertRaises(function() {
        Assert.isAnyOf(12, [MockA, Array], 'this is not a MockA nor an Array: ${value}');
    }, Error, 'Error: this is not a MockA nor an Array: 12');
});

QUnit.test('assert.Assert.in', function(assert) {
    Assert.in('a', ['a', 'b']);
    Assert.in(12, [10, 12]);
    Assert.in('a', {a: 12, b: 10});

    this.assertRaises(function() {
        Assert.in('a', ['b', 'c']);
    }, Error, 'Error: a is not in the collection');

    this.assertRaises(function() {
        Assert.in(0, ['b', 'c']);
    }, Error, 'Error: 0 is not in the collection');

    this.assertRaises(function() {
        Assert.in(5, {a: 12, b: 10});
    }, Error, 'Error: 5 is not in the collection');
});

QUnit.test('assert.Assert.notIn', function(assert) {
    Assert.notIn('c', ['a', 'b']);
    Assert.notIn(5, [10, 12]);
    Assert.notIn('c', {a: 12, b: 10});

    this.assertRaises(function() {
        Assert.notIn('b', ['b', 'c']);
    }, Error, 'Error: b should not be in the collection');

    this.assertRaises(function() {
        Assert.notIn('a', {a: 12, b: 10});
    }, Error, 'Error: a should not be in the collection');
});

QUnit.test('assert.Assert.notThrown', function(assert) {
    Assert.notThrown(function() {
        return 0;
    });

    this.assertRaises(function() {
        Assert.notThrown(function() {
            throw Error('unexpected !');
        });
    }, Error, 'Error: unexpected !');

    this.assertRaises(function() {
        Assert.notThrown(function() {
            throw Error('unexpected !');
        }, 'Should not raise : ${error}');
    }, Error, 'Error: Should not raise : unexpected !');
});

}(jQuery));
