(function($) {

QUnit.module("creme.bricks.dependencies", new QUnitMixin());

QUnit.test('creme.bricks.Dependencies (empty)', function(assert) {
    var deps = new creme.bricks.Dependencies();
    equal(true, deps.isEmpty());
    equal(false, deps.isWildcard());
    deepEqual({}, deps._deps);
    deepEqual([], deps.keys());
});

QUnit.test('creme.bricks.Dependencies (single)', function(assert) {
    var deps = new creme.bricks.Dependencies('a');
    equal(false, deps.isEmpty());
    equal(false, deps.isWildcard());
    deepEqual({a: true}, deps._deps);
    deepEqual(['a'], deps.keys());
});

QUnit.test('creme.bricks.Dependencies (duplicates)', function(assert) {
    var deps = new creme.bricks.Dependencies(['a', 'b', 'a', 'c', 'a', 'a', 'c']);
    equal(false, deps.isEmpty());
    equal(false, deps.isWildcard());
    deepEqual({a: true, b: true, c: true}, deps._deps);
    deepEqual(['a', 'b', 'c'], deps.keys());
});

QUnit.test('creme.bricks.Dependencies (wildcard)', function(assert) {
    var deps = new creme.bricks.Dependencies(['a', 'b', '*', 'c']);
    equal(false, deps.isEmpty());
    equal(true, deps.isWildcard());
    deepEqual({}, deps._deps);
    deepEqual([], deps.keys());
});

QUnit.test('creme.bricks.Dependencies (copy)', function(assert) {
    var deps = new creme.bricks.Dependencies(['a', 'b', 'c']);
    var copy = new creme.bricks.Dependencies(deps);

    equal(false, copy.isEmpty());
    equal(false, copy.isWildcard());
    deepEqual({a: true, b: true, c: true}, copy._deps);
    deepEqual(['a', 'b', 'c'], copy.keys());
});

QUnit.test('creme.bricks.Dependencies (copy wildcard)', function(assert) {
    var deps = new creme.bricks.Dependencies(['a', 'b', '*']);
    var copy = new creme.bricks.Dependencies(deps);

    equal(false, copy.isEmpty());
    equal(true, copy.isWildcard());
    deepEqual({}, copy._deps);
    deepEqual([], copy.keys());
});

QUnit.test('creme.bricks.Dependencies.intersect', function(assert) {
    var deps_A = new creme.bricks.Dependencies(['a', 'b', 'c']);
    var deps_B = new creme.bricks.Dependencies(['d', 'e', 'f']);
    var deps_C = new creme.bricks.Dependencies(['c', 'd']);  // intersect A, B
    var deps_D = new creme.bricks.Dependencies(['g', 'd']);  // intersect B, C
    var deps_E = new creme.bricks.Dependencies(['*']);       // intersect all

    deepEqual(true, deps_A.intersect(deps_A));
    deepEqual(false, deps_A.intersect(deps_B));
    deepEqual(true, deps_A.intersect(deps_C));
    deepEqual(false, deps_A.intersect(deps_D));
    deepEqual(true, deps_A.intersect(deps_E));

    deepEqual(false, deps_B.intersect(deps_A));
    deepEqual(true, deps_B.intersect(deps_B));
    deepEqual(true, deps_B.intersect(deps_C));
    deepEqual(true, deps_B.intersect(deps_D));
    deepEqual(true, deps_B.intersect(deps_E));

    deepEqual(true, deps_C.intersect(deps_A));
    deepEqual(true, deps_C.intersect(deps_B));
    deepEqual(true, deps_C.intersect(deps_C));
    deepEqual(true, deps_C.intersect(deps_D));
    deepEqual(true, deps_C.intersect(deps_E));

    deepEqual(false, deps_D.intersect(deps_A));
    deepEqual(true, deps_D.intersect(deps_B));
    deepEqual(true, deps_D.intersect(deps_C));
    deepEqual(true, deps_D.intersect(deps_D));
    deepEqual(true, deps_D.intersect(deps_E));
});

QUnit.test('creme.bricks.Dependencies.add', function(assert) {
    var deps = new creme.bricks.Dependencies(['a', 'b', 'c']);
    deps.add(['c', 'd', 'e']);

    equal(false, deps.isEmpty());
    equal(false, deps.isWildcard());
    deepEqual(['a', 'b', 'c', 'd', 'e'], deps.keys());

    var other = new creme.bricks.Dependencies(['x', 'y', 'z']);
    deps.add(other);

    equal(false, deps.isEmpty());
    equal(false, deps.isWildcard());
    deepEqual(['a', 'b', 'c', 'd', 'e', 'x', 'y', 'z'], deps.keys());

    deps.add('z');
    deepEqual(['a', 'b', 'c', 'd', 'e', 'x', 'y', 'z'], deps.keys());

    deps.add('h');
    deepEqual(['a', 'b', 'c', 'd', 'e', 'x', 'y', 'z', 'h'], deps.keys());

    this.assertRaises(function() {
        deps.add({});
    }, Error, 'Error: Unable to add invalid dependency data');

    this.assertRaises(function() {
        deps.add(12);
    }, Error, 'Error: Unable to add invalid dependency data');
});

QUnit.test('creme.bricks.Dependencies.add (wildcard)', function(assert) {
    var deps = new creme.bricks.Dependencies(['a', 'b', '*']);
    deps.add(['c', 'd', 'e']);

    equal(false, deps.isEmpty());
    equal(true, deps.isWildcard());
    deepEqual({}, deps._deps);

    deps = new creme.bricks.Dependencies(['a', 'b', 'c']);
    deps.add(['c', 'd', '*']);

    equal(false, deps.isEmpty());
    equal(true, deps.isWildcard());
    deepEqual({}, deps._deps);

    deps = new creme.bricks.Dependencies(['a', 'b', 'c']);
    var other = new creme.bricks.Dependencies(['d', '*', 'f']);
    deps.add(other);

    equal(false, deps.isEmpty());
    equal(true, deps.isWildcard());
    deepEqual({}, deps._deps);
});

}(jQuery));
