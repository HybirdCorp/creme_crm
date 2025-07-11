(function() {

QUnit.module("underscore-object", new QUnitMixin());

QUnit.test('pop', function(assert) {
    var data = {a: 12, b: null, c: 'hello'};

    assert.equal(_.pop(data, 'other'), undefined);
    assert.equal(_.pop(data, 'other', 'mydefault'), 'mydefault');
    assert.deepEqual(data, {a: 12, b: null, c: 'hello'});

    assert.equal(_.pop(data, 'a'), 12);
    assert.equal(_.pop(data, 'a'), undefined);
    assert.deepEqual(data, {b: null, c: 'hello'});

    assert.equal(_.pop(data, 'b'), null);
    assert.equal(_.pop(data, 'b'), undefined);
    assert.deepEqual(data, {c: 'hello'});

    assert.equal(_.pop(data, 'c'), 'hello');
    assert.equal(_.pop(data, 'c', 'mydefault'), 'mydefault');
    assert.deepEqual(data, {});
});

QUnit.test('append', function(assert) {
    var data = {};

    _.append(data, 'a', 1);
    assert.deepEqual(data, {a: 1});

    _.append(data, 'a', 2);
    assert.deepEqual(data, {a: [1, 2]});

    _.append(data, 'a', [3, 4]);
    assert.deepEqual(data, {a: [1, 2, [3, 4]]});

    _.append(data, 'b', 'hello');
    assert.deepEqual(data, {a: [1, 2, [3, 4]], b: 'hello'});
});

}());
