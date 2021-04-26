/* globals FunctionFaker, PropertyFaker, DateFaker */

(function($) {

var MockA = function() {
    this.real = 0;
};

MockA.prototype = {
    func: function() {
        this.real += 1;
        return 'MockA!';
    },

    toString: function() {
        return 'MockA';
    },

    data: {
        x: 12,
        func: function() {
            return 'MockA.data.func';
        }
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
    }, Error, 'Error: "12" is not a function nor a path');

    this.assertRaises(function() {
        return new FunctionFaker({
            instance: new MockA(), method: 'unknown'
        });
    }, Error, 'Error: "unknown" is not a property of MockA');

    this.assertRaises(function() {
        return new FunctionFaker({
            method: 'unknown'
        });
    }, Error, 'Error: "unknown" is not a property of ' + String(window));

    this.assertRaises(function() {
        return new FunctionFaker({
            instance: new MockA(), method: 'data.unknown'
        });
    }, Error, 'Error: "unknown" is not a property of MockA.data');

    this.assertRaises(function() {
        return new FunctionFaker({
            instance: new MockA(), method: 'data.x'
        });
    }, Error, 'Error: "data.x" is not a function');
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

QUnit.test('FunctionFaker.wrap (function)', function(assert) {
    function func(a, b) { return a + b; };

    var faker = new FunctionFaker(func);

    equal(func(12, 5), 12 + 5);

    equal(faker._instance, null);
    equal(faker._property, null);
    equal(faker._origin, func);
    equal(faker._follow, false);
    equal(faker.result, undefined);

    deepEqual(faker.calls(), []);
    equal(faker.called(), false);
    equal(faker.count(), 0);

    var wrapper = faker.wrap();

    equal(wrapper(12, 5), undefined);
    deepEqual(faker.calls(), [[12, 5]]);
    equal(faker.called(), true);
    equal(faker.count(), 1);

    faker.result = 'Fake!';
    equal(wrapper(12, 5), 'Fake!');
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

QUnit.test('FunctionFaker.wrap (bound function)', function(assert) {
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

QUnit.parametrize('FunctionFaker.wrap (follow)', [
    {},
    {result: 'Fake!'},
    {callable: function() { return 'FakeCallable!'; }},
    {result: 'Fake!', callable: function() { return 'FakeCallable!'; }}
], function(options, assert) {
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

    // When "follow" is enabled, both faked result & callable are ignored and the original
    // method is called.
    equal(instance.func('arg1', 'arg2'), 'MockA!');
    equal(instance.real, 2);

    deepEqual(faker.calls(), [['arg1', 'arg2']]);
    equal(faker.called(), true);
    equal(faker.count(), 1);
});

QUnit.test('FunctionFaker.wrap (callable)', function(assert) {
    function _callable() {
        return 'FakeCallable!';
    }

    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: 'func', result: 'Fake!', callable: _callable
    });

    equal(instance.func('arg1', 'arg2'), 'MockA!');
    equal(instance.real, 1);

    deepEqual(faker.calls(), []);
    equal(faker.called(), false);
    equal(faker.count(), 0);

    faker.wrap();

    // faker.result is ignored if faker.callable exists
    equal(instance.func('arg1', 'arg2'), 'FakeCallable!');
    equal(instance.real, 1);

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

QUnit.test('FunctionFaker.with (path)', function(assert) {
    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: 'data.func', result: 'Fake!'
    });

    faker.with(function(faker, wrapper) {
        equal(instance.data.func('arg1', 'arg2'), 'Fake!');

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

    equal(instance.data.func('arg1', 'arg2'), 'MockA.data.func');

    deepEqual(faker.calls(), [
        ['arg1', 'arg2'],
        ['arg3', 'arg4']
    ]);
    equal(faker.called(), true);
    equal(faker.count(), 2);
});

QUnit.test('FunctionFaker.with (static path)', function(assert) {
    var faker = new FunctionFaker({
        method: 'JSON.stringify', result: 'Fake!'
    });

    var origin = JSON.stringify;
    var dump = JSON.stringify({a: 12, b: 'B'});

    faker.with(function(faker, wrapper) {
        equal(JSON.stringify({a: 12, b: 'B'}), 'Fake!');

        deepEqual(faker.calls(), [[{a: 12, b: 'B'}]]);
        equal(faker.called(), true);
        equal(faker.count(), 1);

        wrapper({c: 5, d: 'D'});

        deepEqual(faker.calls(), [
            [{a: 12, b: 'B'}],
            [{c: 5, d: 'D'}]
        ]);
        equal(faker.called(), true);
        equal(faker.count(), 2);
    });

    equal(JSON.stringify, origin);
    equal(JSON.stringify({a: 12, b: 'B'}), dump);

    deepEqual(faker.calls(), [
        [{a: 12, b: 'B'}],
        [{c: 5, d: 'D'}]
    ]);
    equal(faker.called(), true);
    equal(faker.count(), 2);
});


QUnit.test('PropertyFaker (null)', function(assert) {
    this.assertRaises(function() {
        return new PropertyFaker();
    }, Error, 'Error: Cannot fake property of undefined or null');

    this.assertRaises(function() {
        return new PropertyFaker({props: {a: 'fake!'}});
    }, Error, 'Error: Cannot fake property of undefined or null');

    this.assertRaises(function() {
        return new PropertyFaker({instance: null});
    }, Error, 'Error: Cannot fake property of undefined or null');
});

QUnit.test('PropertyFaker (replace)', function(assert) {
    var data = {
        a: 12,
        b: 'test'
    };

    var faker = new PropertyFaker({
        instance: data,
        props: {a: 'fake!', b: 'faketoo!'}
    });

    equal(data.a, 12);
    equal(data.b, 'test');

    faker.with(function() {
        equal(data.a, 'fake!');
        equal(data.b, 'faketoo!');
    });

    equal(data.a, 12);
    equal(data.b, 'test');
});

QUnit.test('PropertyFaker (add)', function(assert) {
    var data = {
        a: 12,
        b: 'test'
    };

    var faker = new PropertyFaker({
        instance: data,
        props: {a: 'fake!', b: 'faketoo!', c: 'new!'}
    });

    equal(data.a, 12);
    equal(data.b, 'test');
    equal(data.c, undefined);
    ok(!('c' in data));

    faker.with(function() {
        equal(data.a, 'fake!');
        equal(data.b, 'faketoo!');
        equal(data.c, 'new!');
    });

    equal(data.a, 12);
    equal(data.b, 'test');
    equal(data.c, undefined);
    ok(!('c' in data));
});

QUnit.test('PropertyFaker (not configurable)', function(assert) {
    var data = {};
    Object.defineProperty(data, 'irremovable', {
        value: 12,
        configurable: false
    });

    var faker = new PropertyFaker({
        instance: data,
        props: {irremovable: 'fake!'}
    });

    equal(data.irremovable, 12);

    this.assertRaises(function() {
        faker.with(function() {});
    }, Error, 'Error: The property "irremovable" is not configurable');
});

QUnit.parametrize('DateFaker (invalid date)', [
    ['invalid', 'The value "invalid" is not a valid date'],
    ['2020-10-32', 'The value "2020-10-32" is not a valid date'],
    [undefined, 'The value must be either a string or a Date'],
    [null, 'The value must be either a string or a Date'],
    [new Error(), 'The value must be either a string or a Date']
], function(value, expected, assert) {
    this.assertRaises(function() {
        return new DateFaker(value);
    }, Error, 'Error: ${message}'.template({message: expected}));
});

QUnit.parametrize('DateFaker.with', [
    [new Date(2020, 9, 12, 16, 30), new Date(2020, 9, 12, 16, 30).toISOString()],
    ['2020-10-12', '2020-10-12T00:00:00.000Z'],
    ['2020-10-12T16:30:52.000Z', '2020-10-12T16:30:52.000Z']
], function(value, expected, assert) {
    var origin = window.Date;
    var faker = new DateFaker(value);

    equal(faker.frozen, expected);
    equal(origin, window.Date);

    faker.with(function(datefaker) {
        deepEqual(faker, datefaker);
        equal(expected, new Date().toISOString());
        equal(expected, Date.now().toISOString());
    });

    equal(origin, window.Date);
});

}(jQuery));
