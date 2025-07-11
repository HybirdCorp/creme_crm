/* globals FunctionFaker */

(function($) {

QUnit.module("QUnit.parametrize", new QUnitMixin({
    withQUnitTestFaker: function(block) {
        return new FunctionFaker({
            instance: QUnit,
            method: 'test'
        }).with(block.bind(this));
    }
}));

QUnit.test('parametrize (invalid)', function(assert) {
    this.assertRaises(function() {
        QUnit.parametrize('mytest', function() {});
    });
});

QUnit.test('parametrize (empty)', function(assert) {
    var callable = function() {};
    var faker = this.withQUnitTestFaker(function(faker) {
        QUnit.parametrize('mytest', [], callable);
    });

    assert.deepEqual(faker.calls(), []);
});

QUnit.test('parametrizee (simple)', function(assert) {
    var callable = function() {};
    var faker = this.withQUnitTestFaker(function(faker) {
        QUnit.parametrize('mytest', ['a', 12], callable);
    });

    assert.deepEqual(faker.calls().map(function(c) { return c[0]; }), [
        'mytest-a',
        'mytest-12'
    ]);
});

QUnit.test('parametrize (simple, array)', function(assert) {
    var callable = function() {};

    var faker = this.withQUnitTestFaker(function(faker) {
        QUnit.parametrize('mytest', [['a', 'b'], [12, 13]], callable);
    });

    assert.deepEqual(faker.calls().map(function(c) { return c[0]; }), [
        'mytest-1',
        'mytest-2'
    ]);
});

QUnit.test('parametrize (simple, dict)', function(assert) {
    var callable = function() {};

    var faker = this.withQUnitTestFaker(function(faker) {
        QUnit.parametrize('mytest', {
            paramsA: ['a', 'b'],
            paramsB: [12, 13]
        }, callable);
    });

    assert.deepEqual(faker.calls().map(function(c) { return c[0]; }), [
        'mytest-paramsA',
        'mytest-paramsB'
    ]);
});

QUnit.test('parametrize (combine)', function(assert) {
    var callable = function() {};

    var faker = this.withQUnitTestFaker(function(faker) {
        QUnit.parametrize('mytest', ['a', 'b'], [17.5, 8], [['x', 'y'], ['a', 'b'], []], callable);
    });

    assert.deepEqual(faker.calls().map(function(c) { return c[0]; }), [
        'mytest-a-17.5-1',
        'mytest-a-17.5-2',
        'mytest-a-17.5-3',
        'mytest-a-8-1',
        'mytest-a-8-2',
        'mytest-a-8-3',
        'mytest-b-17.5-1',
        'mytest-b-17.5-2',
        'mytest-b-17.5-3',
        'mytest-b-8-1',
        'mytest-b-8-2',
        'mytest-b-8-3'
    ]);
});

QUnit.test('parametrize (skip)', function(assert) {
    var callable = function() {};

    callable.skipped = true;

    var test_faker = new FunctionFaker({instance: QUnit, method: 'test'});
    var skip_faker = new FunctionFaker({instance: QUnit, method: 'skip'});

    test_faker.with(function() {
        skip_faker.with(function() {
            QUnit.parametrize('myskiptest', {
                paramsA: ['a', 'b'],
                paramsB: [12, 13]
            }, callable);
        });
    });

    assert.deepEqual(test_faker.calls(), []);
    assert.deepEqual(skip_faker.calls().map(function(c) { return c[0]; }), [
        'myskiptest-paramsA',
        'myskiptest-paramsB'
    ]);
});

QUnit.parametrize('parametrize (real, dict)', {
    usecase_A: ['a', 'string', 'usecase_A'],
    usecase_B: [12, 'number', 'usecase_B']
}, function(data, expected, usecaseName, assert) {
    assert.equal(assert.test.testName, 'parametrize (real, dict)-${name}'.template({name: usecaseName}));
    assert.equal(typeof data, expected);
});

QUnit.parametrize('parametrize (real, combine)', [
    1, 3, 5
], [
    ['a', true], ['b', true], ['c', true]
], function(arg1, arg2, arg3, assert) {
    assert.ok(assert.test.testName.startsWith('parametrize (real, combine)-${0}-'.template(arguments)));
    assert.equal(typeof arg1, 'number');
    assert.equal(typeof arg2, 'string');
    assert.equal(arg3, true);
});

QUnit.parametrize('parametrizeIf', [
    [true, []],
    [function() { return true; }, []],
    [false, ['myskiptest-a', 'myskiptest-b']],
    [function() { return false; }, ['myskiptest-a', 'myskiptest-b']]
], function(condition, expected, assert) {
    var callable = function() {};
    var faker = new FunctionFaker({instance: QUnit, method: 'test'});

    faker.with(function() {
        QUnit.parametrizeIf(condition, 'myskiptest', ['a', 'b'], callable);
    });

    assert.deepEqual(faker.calls().map(function(c) { return c[0]; }), expected);
});

}(jQuery));
