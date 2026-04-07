(function() {

QUnit.module("underscore-object", new QUnitMixin());

QUnit.test('pop', function(assert) {
    var data = {a: 12, b: null, c: 'hello'};

    equal(_.pop(data, 'other'), undefined);
    equal(_.pop(data, 'other', 'mydefault'), 'mydefault');
    deepEqual(data, {a: 12, b: null, c: 'hello'});

    equal(_.pop(data, 'a'), 12);
    equal(_.pop(data, 'a'), undefined);
    deepEqual(data, {b: null, c: 'hello'});

    equal(_.pop(data, 'b'), null);
    equal(_.pop(data, 'b'), undefined);
    deepEqual(data, {c: 'hello'});

    equal(_.pop(data, 'c'), 'hello');
    equal(_.pop(data, 'c', 'mydefault'), 'mydefault');
    deepEqual(data, {});
});

QUnit.test('append', function(assert) {
    var data = {};

    _.append(data, 'a', 1);
    deepEqual(data, {a: 1});

    _.append(data, 'a', 2);
    deepEqual(data, {a: [1, 2]});

    _.append(data, 'a', [3, 4]);
    deepEqual(data, {a: [1, 2, [3, 4]]});

    _.append(data, 'b', 'hello');
    deepEqual(data, {a: [1, 2, [3, 4]], b: 'hello'});
});

}());
