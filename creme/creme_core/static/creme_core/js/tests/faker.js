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

    assert.equal(faker._instance, undefined);
    assert.equal(faker._property, undefined);
    assert.equal(Object.isFunc(faker._origin), true);
    assert.equal(faker._follow, false);
    assert.equal(faker.result, undefined);
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

    assert.equal(faker._instance, instance);
    assert.equal(faker._property, 'func');
    assert.equal(faker._origin, MockA.prototype.func);
    assert.equal(faker._follow, false);
    assert.equal(faker.result, 'Fake!');

    assert.equal(instance.func('arg1', 'arg2'), 'MockA!');
    assert.equal(instance.real, 1);

    assert.deepEqual(faker.calls(), []);
    assert.equal(faker.called(), false);
    assert.equal(faker.count(), 0);

    faker.wrap();

    assert.equal(instance.func('arg1', 'arg2'), 'Fake!');
    assert.equal(instance.real, 1);

    assert.deepEqual(faker.calls(), [['arg1', 'arg2']]);
    assert.equal(faker.called(), true);
    assert.equal(faker.count(), 1);
});

QUnit.test('FunctionFaker.wrap (function)', function(assert) {
    function func(a, b) { return a + b; };

    var faker = new FunctionFaker(func);

    assert.equal(func(12, 5), 12 + 5);

    assert.equal(faker._instance, null);
    assert.equal(faker._property, null);
    assert.equal(faker._origin, func);
    assert.equal(faker._follow, false);
    assert.equal(faker.result, undefined);

    assert.deepEqual(faker.calls(), []);
    assert.equal(faker.called(), false);
    assert.equal(faker.count(), 0);

    var wrapper = faker.wrap();

    assert.equal(wrapper(12, 5), undefined);
    assert.deepEqual(faker.calls(), [[12, 5]]);
    assert.equal(faker.called(), true);
    assert.equal(faker.count(), 1);

    faker.result = 'Fake!';
    assert.equal(wrapper(12, 5), 'Fake!');
});

QUnit.test('FunctionFaker.wrap (method)', function(assert) {
    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: instance.func, result: 'Fake!'
    });

    assert.equal(instance.func('arg1', 'arg2'), 'MockA!');
    assert.equal(instance.real, 1);

    assert.deepEqual(faker.calls(), []);
    assert.equal(faker.called(), false);
    assert.equal(faker.count(), 0);

    // returns wrapper for replacement. If the property name is not specified
    // this must be done explicitly
    instance.func = faker.wrap();

    assert.equal(instance.func('arg1', 'arg2'), 'Fake!');
    assert.equal(instance.real, 1);

    assert.deepEqual(faker.calls(), [['arg1', 'arg2']]);
    assert.equal(faker.called(), true);
    assert.equal(faker.count(), 1);
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

    assert.equal(other.bind(instance)('arg1', 'arg2'), 'Other!');
    assert.equal(instance.real, 1);

    assert.deepEqual(faker.calls(), []);
    assert.equal(faker.called(), false);
    assert.equal(faker.count(), 0);

    var fake_other = faker.wrap();

    assert.equal(fake_other('arg1', 'arg2'), 'Fake!');
    assert.equal(instance.real, 1);

    assert.deepEqual(faker.calls(), [['arg1', 'arg2']]);
    assert.deepEqual(faker.calls(function(args) { return args.length; }), [2]);
    assert.equal(faker.called(), true);
    assert.equal(faker.count(), 1);
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

    assert.equal(instance.func('arg1', 'arg2'), 'MockA!');
    assert.equal(instance.real, 1);

    assert.deepEqual(faker.calls(), []);
    assert.equal(faker.called(), false);
    assert.equal(faker.count(), 0);

    faker.wrap();

    // When "follow" is enabled, both faked result & callable are ignored and the original
    // method is called.
    assert.equal(instance.func('arg1', 'arg2'), 'MockA!');
    assert.equal(instance.real, 2);

    assert.deepEqual(faker.calls(), [['arg1', 'arg2']]);
    assert.equal(faker.called(), true);
    assert.equal(faker.count(), 1);
});

QUnit.test('FunctionFaker.wrap (callable)', function(assert) {
    function _callable() {
        return 'FakeCallable!';
    }

    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: 'func', result: 'Fake!', callable: _callable
    });

    assert.equal(instance.func('arg1', 'arg2'), 'MockA!');
    assert.equal(instance.real, 1);

    assert.deepEqual(faker.calls(), []);
    assert.equal(faker.called(), false);
    assert.equal(faker.count(), 0);

    faker.wrap();

    // faker.result is ignored if faker.callable exists
    assert.equal(instance.func('arg1', 'arg2'), 'FakeCallable!');
    assert.equal(instance.real, 1);

    assert.deepEqual(faker.calls(), [['arg1', 'arg2']]);
    assert.equal(faker.called(), true);
    assert.equal(faker.count(), 1);
});

QUnit.test('FunctionFaker.unwrap', function(assert) {
    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: 'func', result: 'Fake!'
    });

    faker.wrap();

    assert.equal(instance.func('arg1', 'arg2'), 'Fake!');
    assert.equal(instance.real, 0);

    assert.deepEqual(faker.calls(), [['arg1', 'arg2']]);
    assert.equal(faker.called(), true);
    assert.equal(faker.count(), 1);

    faker.unwrap();

    assert.equal(instance.func('arg1', 'arg2'), 'MockA!');
    assert.equal(instance.real, 1);

    assert.deepEqual(faker.calls(), [['arg1', 'arg2']]);
    assert.equal(faker.called(), true);
    assert.equal(faker.count(), 1);
});

QUnit.test('FunctionFaker.reset', function(assert) {
    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: 'func', result: 'Fake!'
    });

    faker.wrap();

    assert.equal(instance.func('arg1', 'arg2'), 'Fake!');
    assert.equal(instance.real, 0);

    assert.deepEqual(faker.calls(), [['arg1', 'arg2']]);
    assert.equal(faker.called(), true);
    assert.equal(faker.count(), 1);

    faker.reset();

    assert.deepEqual(faker.calls(), []);
    assert.equal(faker.called(), false);
    assert.equal(faker.count(), 0);
});

QUnit.test('FunctionFaker.with', function(assert) {
    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: 'func', result: 'Fake!'
    });

    faker.with(function(faker, wrapper) {
        assert.equal(instance.func('arg1', 'arg2'), 'Fake!');
        assert.equal(instance.real, 0);

        assert.deepEqual(faker.calls(), [['arg1', 'arg2']]);
        assert.equal(faker.called(), true);
        assert.equal(faker.count(), 1);

        wrapper('arg3', 'arg4');

        assert.deepEqual(faker.calls(), [
            ['arg1', 'arg2'],
            ['arg3', 'arg4']
        ]);
        assert.equal(faker.called(), true);
        assert.equal(faker.count(), 2);
    });

    assert.equal(instance.func('arg1', 'arg2'), 'MockA!');
    assert.equal(instance.real, 1);

    assert.deepEqual(faker.calls(), [
        ['arg1', 'arg2'],
        ['arg3', 'arg4']
    ]);
    assert.equal(faker.called(), true);
    assert.equal(faker.count(), 2);
});

QUnit.test('FunctionFaker.with (path)', function(assert) {
    var instance = new MockA();
    var faker = new FunctionFaker({
        instance: instance, method: 'data.func', result: 'Fake!'
    });

    faker.with(function(faker, wrapper) {
        assert.equal(instance.data.func('arg1', 'arg2'), 'Fake!');

        assert.deepEqual(faker.calls(), [['arg1', 'arg2']]);
        assert.equal(faker.called(), true);
        assert.equal(faker.count(), 1);

        wrapper('arg3', 'arg4');

        assert.deepEqual(faker.calls(), [
            ['arg1', 'arg2'],
            ['arg3', 'arg4']
        ]);
        assert.equal(faker.called(), true);
        assert.equal(faker.count(), 2);
    });

    assert.equal(instance.data.func('arg1', 'arg2'), 'MockA.data.func');

    assert.deepEqual(faker.calls(), [
        ['arg1', 'arg2'],
        ['arg3', 'arg4']
    ]);
    assert.equal(faker.called(), true);
    assert.equal(faker.count(), 2);
});

QUnit.test('FunctionFaker.with (static path)', function(assert) {
    var faker = new FunctionFaker({
        method: 'JSON.stringify', result: 'Fake!'
    });

    var origin = JSON.stringify;
    var dump = JSON.stringify({a: 12, b: 'B'});

    faker.with(function(faker, wrapper) {
        assert.equal(JSON.stringify({a: 12, b: 'B'}), 'Fake!');

        assert.deepEqual(faker.calls(), [[{a: 12, b: 'B'}]]);
        assert.equal(faker.called(), true);
        assert.equal(faker.count(), 1);

        wrapper({c: 5, d: 'D'});

        assert.deepEqual(faker.calls(), [
            [{a: 12, b: 'B'}],
            [{c: 5, d: 'D'}]
        ]);
        assert.equal(faker.called(), true);
        assert.equal(faker.count(), 2);
    });

    assert.equal(JSON.stringify, origin);
    assert.equal(JSON.stringify({a: 12, b: 'B'}), dump);

    assert.deepEqual(faker.calls(), [
        [{a: 12, b: 'B'}],
        [{c: 5, d: 'D'}]
    ]);
    assert.equal(faker.called(), true);
    assert.equal(faker.count(), 2);
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

    assert.equal(data.a, 12);
    assert.equal(data.b, 'test');

    faker.with(function() {
        assert.equal(data.a, 'fake!');
        assert.equal(data.b, 'faketoo!');
    });

    assert.equal(data.a, 12);
    assert.equal(data.b, 'test');
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

    assert.equal(data.a, 12);
    assert.equal(data.b, 'test');
    assert.equal(data.c, undefined);
    assert.ok(!('c' in data));

    faker.with(function() {
        assert.equal(data.a, 'fake!');
        assert.equal(data.b, 'faketoo!');
        assert.equal(data.c, 'new!');
    });

    assert.equal(data.a, 12);
    assert.equal(data.b, 'test');
    assert.equal(data.c, undefined);
    assert.ok(!('c' in data));
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

    assert.equal(faker.frozen, expected);
    assert.equal(origin, window.Date);

    faker.with(function(datefaker) {
        assert.deepEqual(faker, datefaker);
        assert.equal(expected, new Date().toISOString());
        assert.equal(expected, Date.now().toISOString());

        // constructor should works as usual
        assert.equal('2020-12-31T00:08:30.000Z', new Date('2020-12-31T00:08:30+00:00').toISOString());
        assert.equal(new Date('2020-12-31T00:08:30').toISOString(), new Date(2020, 11, 31, 0, 8, 30, 0).toISOString());

        // same for the static methods
        assert.equal(1609373310000, Date.UTC(2020, 11, 31, 0, 8, 30, 0));
        assert.equal(1609373310000, Date.parse('2020-12-31T00:08:30+00:00'));
    });

    assert.equal(origin, window.Date);
});

}(jQuery));
