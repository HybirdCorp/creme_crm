(function($) {

QUnit.module("creme.bricks.dependencies", new QUnitMixin());

QUnit.test('creme.bricks.Dependencies (empty)', function(assert) {
    var deps = new creme.bricks.Dependencies();
    assert.equal(true, deps.isEmpty());
    assert.equal(false, deps.isWildcard());
    assert.deepEqual({}, deps._deps);
    assert.deepEqual([], deps.keys());
});

QUnit.test('creme.bricks.Dependencies (single)', function(assert) {
    var deps = new creme.bricks.Dependencies('a');
    assert.equal(false, deps.isEmpty());
    assert.equal(false, deps.isWildcard());
    assert.deepEqual({a: true}, deps._deps);
    assert.deepEqual(['a'], deps.keys());
});

QUnit.test('creme.bricks.Dependencies (duplicates)', function(assert) {
    var deps = new creme.bricks.Dependencies(['a', 'b', 'a', 'c', 'a', 'a', 'c']);
    assert.equal(false, deps.isEmpty());
    assert.equal(false, deps.isWildcard());
    assert.deepEqual({a: true, b: true, c: true}, deps._deps);
    assert.deepEqual(['a', 'b', 'c'], deps.keys());
});

QUnit.test('creme.bricks.Dependencies (wildcard)', function(assert) {
    var deps = new creme.bricks.Dependencies(['a', 'b', '*', 'c']);
    assert.equal(false, deps.isEmpty());
    assert.equal(true, deps.isWildcard());
    assert.deepEqual({}, deps._deps);
    assert.deepEqual([], deps.keys());
});

QUnit.test('creme.bricks.Dependencies (copy)', function(assert) {
    var deps = new creme.bricks.Dependencies(['a', 'b', 'c']);
    var copy = new creme.bricks.Dependencies(deps);

    assert.equal(false, copy.isEmpty());
    assert.equal(false, copy.isWildcard());
    assert.deepEqual({a: true, b: true, c: true}, copy._deps);
    assert.deepEqual(['a', 'b', 'c'], copy.keys());
});

QUnit.test('creme.bricks.Dependencies (copy wildcard)', function(assert) {
    var deps = new creme.bricks.Dependencies(['a', 'b', '*']);
    var copy = new creme.bricks.Dependencies(deps);

    assert.equal(false, copy.isEmpty());
    assert.equal(true, copy.isWildcard());
    assert.deepEqual({}, copy._deps);
    assert.deepEqual([], copy.keys());
});

QUnit.test('creme.bricks.Dependencies.intersect', function(assert) {
    var deps_A = new creme.bricks.Dependencies(['a', 'b', 'c']);
    var deps_B = new creme.bricks.Dependencies(['d', 'e', 'f']);
    var deps_C = new creme.bricks.Dependencies(['c', 'd']);  // intersect A, B
    var deps_D = new creme.bricks.Dependencies(['g', 'd']);  // intersect B, C
    var deps_E = new creme.bricks.Dependencies(['*']);       // intersect all

    assert.deepEqual(true, deps_A.intersect(deps_A));
    assert.deepEqual(false, deps_A.intersect(deps_B));
    assert.deepEqual(true, deps_A.intersect(deps_C));
    assert.deepEqual(false, deps_A.intersect(deps_D));
    assert.deepEqual(true, deps_A.intersect(deps_E));

    assert.deepEqual(false, deps_B.intersect(deps_A));
    assert.deepEqual(true, deps_B.intersect(deps_B));
    assert.deepEqual(true, deps_B.intersect(deps_C));
    assert.deepEqual(true, deps_B.intersect(deps_D));
    assert.deepEqual(true, deps_B.intersect(deps_E));

    assert.deepEqual(true, deps_C.intersect(deps_A));
    assert.deepEqual(true, deps_C.intersect(deps_B));
    assert.deepEqual(true, deps_C.intersect(deps_C));
    assert.deepEqual(true, deps_C.intersect(deps_D));
    assert.deepEqual(true, deps_C.intersect(deps_E));

    assert.deepEqual(false, deps_D.intersect(deps_A));
    assert.deepEqual(true, deps_D.intersect(deps_B));
    assert.deepEqual(true, deps_D.intersect(deps_C));
    assert.deepEqual(true, deps_D.intersect(deps_D));
    assert.deepEqual(true, deps_D.intersect(deps_E));
});

QUnit.test('creme.bricks.Dependencies.add', function(assert) {
    var deps = new creme.bricks.Dependencies(['a', 'b', 'c']);
    deps.add(['c', 'd', 'e']);

    assert.equal(false, deps.isEmpty());
    assert.equal(false, deps.isWildcard());
    assert.deepEqual(['a', 'b', 'c', 'd', 'e'], deps.keys());

    var other = new creme.bricks.Dependencies(['x', 'y', 'z']);
    deps.add(other);

    assert.equal(false, deps.isEmpty());
    assert.equal(false, deps.isWildcard());
    assert.deepEqual(['a', 'b', 'c', 'd', 'e', 'x', 'y', 'z'], deps.keys());

    deps.add('z');
    assert.deepEqual(['a', 'b', 'c', 'd', 'e', 'x', 'y', 'z'], deps.keys());

    deps.add('h');
    assert.deepEqual(['a', 'b', 'c', 'd', 'e', 'x', 'y', 'z', 'h'], deps.keys());

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

    assert.equal(false, deps.isEmpty());
    assert.equal(true, deps.isWildcard());
    assert.deepEqual({}, deps._deps);

    deps = new creme.bricks.Dependencies(['a', 'b', 'c']);
    deps.add(['c', 'd', '*']);

    assert.equal(false, deps.isEmpty());
    assert.equal(true, deps.isWildcard());
    assert.deepEqual({}, deps._deps);

    deps = new creme.bricks.Dependencies(['a', 'b', 'c']);
    var other = new creme.bricks.Dependencies(['d', '*', 'f']);
    deps.add(other);

    assert.equal(false, deps.isEmpty());
    assert.equal(true, deps.isWildcard());
    assert.deepEqual({}, deps._deps);
});

}(jQuery));
