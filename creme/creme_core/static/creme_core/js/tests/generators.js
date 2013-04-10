module("creme.generators.js", {
    setup: function() {
    },

    teardown: function() {
    }
});


test('generators.ArrayTools.get', function() {
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

test('generators.ArrayTools.set', function() {
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], 0, "a"), ["a", 3, 8,   5,  44]);
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], 3, "a"), [ 12, 3, 8, "a",  44]);
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], 4, "a"), [ 12, 3, 8,   5, "a"]);
    
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], -1, "a"), [ 12, 3, 8,   5, "a"]);
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], -2, "a"), [ 12, 3, 8, "a",  44]);
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], -5, "a"), ["a", 3, 8,   5,  44]);
    
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], 5, "a"),  [12, 3, 8, 5, 44, "a"]);
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], -6, "a"), ["a", 12, 3, 8, 5, 44]);
    
    var none = undefined;
    
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], 9, "a"),   [12,     3,    8,    5,   44, none, none, none, none, "a"]);
    deepEqual(ArrayTools.set([12, 3, 8, 5, 44], -10, "a"), ["a", none, none, none, none,   12,    3,    8,    5,  44]);
});

test('generators.ArrayTools.remove', function() {
    var array = [12, 3, 8, 5, 44];
    equal(ArrayTools.remove(array, 0), 12);
    deepEqual(array, [3,  8, 5, 44]);
    
    var array = [12, 3, 8, 5, 44];
    equal(ArrayTools.remove(array, 3), 5);
    deepEqual(array, [12, 3, 8, 44]);
    
    var array = [12, 3, 8, 5, 44];
    equal(ArrayTools.remove(array, 4), 44);
    deepEqual(array, [12, 3, 8,  5]);
    
    var array = [12, 3, 8, 5, 44];
    equal(ArrayTools.remove(array, -1), 44);
    deepEqual(array, [12, 3, 8,  5]);
    
    var array = [12, 3, 8, 5, 44];
    equal(ArrayTools.remove(array, -2), 5);
    deepEqual(array, [12, 3, 8, 44]);
    
    var array = [12, 3, 8, 5, 44];
    equal(ArrayTools.remove(array, -5), 12);
    deepEqual(array, [3,  8, 5, 44]);
});

test('generators.ArrayTools.sum', function() {
    equal(0, ArrayTools.sum([]));

    equal(10, ArrayTools.sum([1, 2, 3, 4]));

    equal(7, ArrayTools.sum([1, 2, undefined, 4]));
    equal(7, ArrayTools.sum([1, 2, "a", 4]));
});

test('generators.ArrayTools.swap', function() {
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
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 0, 1), [ 3, 12, 8,  5, 44]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 0, 3), [ 5,  3, 8, 12, 44]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 0, 4), [44,  3, 8,  5, 12]);

    // swap relative
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 0, -1), [44,  3, 8,  5, 12]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], 0, -2), [ 5,  3, 8, 12, 44]);

    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], -1, 0), [44,  3, 8,  5, 12]);
    deepEqual(ArrayTools.swap([12, 3, 8, 5, 44], -2, 0), [ 5,  3, 8, 12, 44]);
});

