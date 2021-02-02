/* globals FunctionFaker */

(function($) {

var MockA = function() {
    this.real = 0;
};

MockA.prototype = {
    func: function() {
        this.real += 1;
        return 'MockA!';
    }
};

QUnit.module("FunctionFaker", new QUnitMixin());

QUnit.test('FunctionFaker', function(assert) {
    var faker = new FunctionFaker();

    equal(faker._instance, undefined);
    equal(faker._property, undefined);
    equal(Object.isFunc(faker._origin), true);
    equal(faker._follow, false);
    equal(faker.result, undefined);
});

QUnit.test('FunctionFaker (errors)', function(assert) {
    this.assertRaises(function() {
        return new FunctionFaker({method: 12});
    }, Error, 'Error: "12" is not a function');

    this.assertRaises(function() {
        return new FunctionFaker({
            instance: new MockA(), method: 'unknown'
        });
    }, Error, 'Error: "unknown" is not a method property');
});

QUnit.test('FunctionFaker.wrap (property)', function(assert) {
    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: 'func', result: 'Fake!'
    });

    equal(faker._instance, instance);
    equal(faker._property, 'func');
    equal(faker._origin, MockA.prototype.func);
    equal(faker._follow, false);
    equal(faker.result, 'Fake!');

    equal(instance.func('arg1', 'arg2'), 'MockA!');
    equal(instance.real, 1);

    deepEqual(faker.calls(), []);
    equal(faker.called(), false);
    equal(faker.count(), 0);

    faker.wrap();

    equal(instance.func('arg1', 'arg2'), 'Fake!');
    equal(instance.real, 1);

    deepEqual(faker.calls(), [['arg1', 'arg2']]);
    equal(faker.called(), true);
    equal(faker.count(), 1);
});

QUnit.test('FunctionFaker.wrap (method)', function(assert) {
    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: instance.func, result: 'Fake!'
    });

    equal(instance.func('arg1', 'arg2'), 'MockA!');
    equal(instance.real, 1);

    deepEqual(faker.calls(), []);
    equal(faker.called(), false);
    equal(faker.count(), 0);

    // returns wrapper for replacement. If the property name is not specified
    // this must be done explicitly
    instance.func = faker.wrap();

    equal(instance.func('arg1', 'arg2'), 'Fake!');
    equal(instance.real, 1);

    deepEqual(faker.calls(), [['arg1', 'arg2']]);
    equal(faker.called(), true);
    equal(faker.count(), 1);
});

QUnit.test('FunctionFaker.wrap (call)', function(assert) {
    var instance = new MockA();
    var other = function() {
        this.real += 1;
        return 'Other!';
    };

    var faker = new FunctionFaker({
        instance: instance, method: other, result: 'Fake!'
    });

    equal(other.bind(instance)('arg1', 'arg2'), 'Other!');
    equal(instance.real, 1);

    deepEqual(faker.calls(), []);
    equal(faker.called(), false);
    equal(faker.count(), 0);

    var fake_other = faker.wrap();

    equal(fake_other('arg1', 'arg2'), 'Fake!');
    equal(instance.real, 1);

    deepEqual(faker.calls(), [['arg1', 'arg2']]);
    deepEqual(faker.calls(function(args) { return args.length; }), [2]);
    equal(faker.called(), true);
    equal(faker.count(), 1);
});

QUnit.test('FunctionFaker.wrap (follow)', function(assert) {
    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: 'func', result: 'Fake!', follow: true
    });

    equal(instance.func('arg1', 'arg2'), 'MockA!');
    equal(instance.real, 1);

    deepEqual(faker.calls(), []);
    equal(faker.called(), false);
    equal(faker.count(), 0);

    faker.wrap();

    // When "follow" is enabled, the faked result is ignored and the original
    // method is called.
    equal(instance.func('arg1', 'arg2'), 'MockA!');
    equal(instance.real, 2);

    deepEqual(faker.calls(), [['arg1', 'arg2']]);
    equal(faker.called(), true);
    equal(faker.count(), 1);
});

QUnit.test('FunctionFaker.unwrap', function(assert) {
    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: 'func', result: 'Fake!'
    });

    faker.wrap();

    equal(instance.func('arg1', 'arg2'), 'Fake!');
    equal(instance.real, 0);

    deepEqual(faker.calls(), [['arg1', 'arg2']]);
    equal(faker.called(), true);
    equal(faker.count(), 1);

    faker.unwrap();

    equal(instance.func('arg1', 'arg2'), 'MockA!');
    equal(instance.real, 1);

    deepEqual(faker.calls(), [['arg1', 'arg2']]);
    equal(faker.called(), true);
    equal(faker.count(), 1);
});

QUnit.test('FunctionFaker.reset', function(assert) {
    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: 'func', result: 'Fake!'
    });

    faker.wrap();

    equal(instance.func('arg1', 'arg2'), 'Fake!');
    equal(instance.real, 0);

    deepEqual(faker.calls(), [['arg1', 'arg2']]);
    equal(faker.called(), true);
    equal(faker.count(), 1);

    faker.reset();

    deepEqual(faker.calls(), []);
    equal(faker.called(), false);
    equal(faker.count(), 0);
});

QUnit.test('FunctionFaker.with', function(assert) {
    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: 'func', result: 'Fake!'
    });

    faker.with(function(faker, wrapper) {
        equal(instance.func('arg1', 'arg2'), 'Fake!');
        equal(instance.real, 0);

        deepEqual(faker.calls(), [['arg1', 'arg2']]);
        equal(faker.called(), true);
        equal(faker.count(), 1);

        wrapper('arg3', 'arg4');

        deepEqual(faker.calls(), [
            ['arg1', 'arg2'],
            ['arg3', 'arg4']
        ]);
        equal(faker.called(), true);
        equal(faker.count(), 2);
    });

    equal(instance.func('arg1', 'arg2'), 'MockA!');
    equal(instance.real, 1);

    deepEqual(faker.calls(), [
        ['arg1', 'arg2'],
        ['arg3', 'arg4']
    ]);
    equal(faker.called(), true);
    equal(faker.count(), 2);
});

}(jQuery));
