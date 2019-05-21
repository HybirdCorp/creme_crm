(function($) {
QUnit.module("creme.generators.js", new QUnitMixin());

QUnit.test('generators.ArrayTools.get', function(assert) {
    equal(ArrayTools.get([12, 3, 8, 5, 44], 0), 12);
    equal(ArrayTools.get([12, 3, 8, 5, 44], 3), 5);
    equal(ArrayTools.get([12, 3, 8, 5, 44], 4), 44);

    equal(ArrayTools.get([12, 3, 8, 5, 44], -1), 44);
    equal(ArrayTools.get([12, 3, 8, 5, 44], -2), 5);
    equal(ArrayTools.get([12, 3, 8, 5, 44], -5), 12);

    equal(ArrayTools.get([12, 3, 8, 5, 44], 5), undefined);
    equal(ArrayTools.get([12, 3, 8, 5, 44], -6), undefined);

    equal(ArrayTools.get([12, 3, 8, 5, 44], 5, 404), 404);
    equal(ArrayTools.get([12, 3, 8, 5, 44], -6, 404), 404);
});

QUnit.test('generators.ArrayTools.set', function(assert) {
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], 0, "a"), ["a", 3, 8,  5, 44]);
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], 3, "a"), [12, 3, 8, "a", 44]);
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], 4, "a"), [12, 3, 8,  5, "a"]);

    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], -1, "a"), [12, 3, 8, 5, "a"]);
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], -2, "a"), [12, 3, 8, "a", 44]);
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], -5, "a"), ["a", 3, 8, 5, 44]);

    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], 5, "a"),  [12, 3, 8, 5, 44, "a"]);
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], -6, "a"), ["a", 12, 3, 8, 5, 44]);

    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], 9, "a"),   [12,     3,    8,    5,   44, undefined, undefined, undefined, undefined, "a"]);
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], -10, "a"), ["a", undefined, undefined, undefined, undefined,   12,    3,    8,    5,  44]);
});

QUnit.test('generators.ArrayTools.remove', function(assert) {
    var array = [12, 3, 8, 5, 44];
    equal(ArrayTools.remove(array, 0), 12);
    deepEqual(array, [3,  8, 5, 44]);

    array = [12, 3, 8, 5, 44];
    equal(ArrayTools.remove(array, 3), 5);
    deepEqual(array, [12, 3, 8, 44]);

    array = [12, 3, 8, 5, 44];
    equal(ArrayTools.remove(array, 4), 44);
    deepEqual(array, [12, 3, 8,  5]);

    array = [12, 3, 8, 5, 44];
    equal(ArrayTools.remove(array, -1), 44);
    deepEqual(array, [12, 3, 8,  5]);

    array = [12, 3, 8, 5, 44];
    equal(ArrayTools.remove(array, -2), 5);
    deepEqual(array, [12, 3, 8, 44]);

    array = [12, 3, 8, 5, 44];
    equal(ArrayTools.remove(array, -5), 12);
    deepEqual(array, [3,  8, 5, 44]);
});

QUnit.test('generators.ArrayTools.sum', function(assert) {
    equal(0, ArrayTools.sum([]));

    equal(10, ArrayTools.sum([1, 2, 3, 4]));
    equal(3 + 4, ArrayTools.sum([1, 2, 3, 4], 2));
    equal(1 + 2, ArrayTools.sum([1, 2, 3, 4], 0, 2));
    equal(1 + 2 + 3, ArrayTools.sum([1, 2, 3, 4], 0, 3));

    equal(7, ArrayTools.sum([1, 2, undefined, 4]));
    equal(7, ArrayTools.sum([1, 2, "a", 4]));
});

QUnit.test('generators.ArrayTools.swap', function(assert) {
    // same index
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 0, 0), [12, 3, 8, 5, 44]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 2, 2), [12, 3, 8, 5, 44]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 4, 4), [12, 3, 8, 5, 44]);

    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], -1, -1), [12, 3, 8, 5, 44]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], -5, -5), [12, 3, 8, 5, 44]);

    // same relative index
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 0, -5), [12, 3, 8, 5, 44]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], -5, 0), [12, 3, 8, 5, 44]);

    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 3, -2), [12, 3, 8, 5, 44]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], -2, 3), [12, 3, 8, 5, 44]);

    // swap
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 0, 1), [3, 12, 8, 5, 44]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 0, 3), [5, 3, 8, 12, 44]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 0, 4), [44, 3, 8, 5, 12]);

    // swap relative
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 0, -1), [44, 3, 8, 5, 12]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 0, -2), [5, 3, 8, 12, 44]);

    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], -1, 0), [44, 3, 8, 5, 12]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], -2, 0), [5, 3, 8, 12, 44]);
});

QUnit.test('generators.Generator.get (number)', function(assert) {
    var g = new Generator();
    equal(undefined, g.get());

    equal(g, g.get(2));
    equal(true, Object.isFunc(g.get()));
    equal(8, g.get()([12, 3, 8]));
    equal(undefined, g.get()([12, 3]));
    equal(8, g.get()([12, 3, 8, 15]));
});

QUnit.test('generators.Generator.get (function)', function(assert) {
    var g = new Generator();

    equal(g, g.get(function() { return 'test !'; }));
    equal(true, Object.isFunc(g.get()));
    equal('test !', g.get()());
});

QUnit.test('generators.Generator.get (object)', function(assert) {
    var g = new Generator();

    equal(g, g.get('a'));
    equal(true, Object.isFunc(g.get()));

    equal(12, g.get()({a: 12, b: -5}));
    equal(-5, g.get()({a: -5, b: 12}));
    equal(undefined, g.get()({b: 12}));
});

QUnit.test('generators.Generator.get (null)', function(assert) {
    var g = new Generator().get('a');
    equal(true, Object.isFunc(g.get()));

    g.get(null);
    equal(undefined, g.get());
});

QUnit.test('generators.Generator.each (aka processor)', function(assert) {
    var g = new Generator();
    equal(undefined, g.each());

    g.each(function(value, index, data) { return value; });
    equal(true, Object.isFunc(g.each()));
});

QUnit.test('generators.Generator.each (null)', function(assert) {
    var g = new Generator().each(function(value, index, data) { return value; });
    equal(true, Object.isFunc(g.each()));

    g.each(null);
    equal(undefined, g.each());
});

QUnit.test('generators.Generator.iterator', function(assert) {
    var g = new Generator();
    var iter = g.iterator();

    equal(true, Object.isFunc(iter));

    deepEqual([], [].map(iter));
    deepEqual([1, 2, 3], [1, 2, 3].map(iter));
});

QUnit.test('generators.Generator.iterator (with processor)', function(assert) {
    var iter = new Generator().each(function(entry, index, data) {
        if (index > 0) {
            return entry + data[index - 1];
        } else {
            return -1;
        }
    }).iterator();

    equal(true, Object.isFunc(iter));

    deepEqual([], [].map(iter));
    deepEqual([-1, 3 + 15, 15 + 8], [3, 15, 8].map(iter));
});

QUnit.test('generators.GeneratorTools.ratio', function(assert) {
    // percentage of entry[0] on 1500 written to entry[1]
    var iter = GeneratorTools.array.ratio(0, 1500, 100, 1);
    deepEqual([[150, 10], [750, 50], [1500, 100]],
              [[150], [750], [1500]].map(iter));

    // percentage of entry[0] on 1500 written to entry[0]
    iter = GeneratorTools.array.ratio(0, 1500, 100);
    deepEqual([[10], [50], [100]],
              [[150], [750], [1500]].map(iter));
});

QUnit.test('generators.GeneratorTools.format', function(assert) {
    var iter = GeneratorTools.array.format('Value is %s', 1);
    deepEqual([[150, 'Value is 150'], [500, 'Value is 500'], [1000, 'Value is 1000']],
              [[150], [500], [1000]].map(iter));

    iter = GeneratorTools.array.format('Value is %s');
    deepEqual([[150, 'Value is 150'], [500, 'Value is 500'], [1000, 'Value is 1000']],
            [[150], [500], [1000]].map(iter));
});

}(jQuery));
