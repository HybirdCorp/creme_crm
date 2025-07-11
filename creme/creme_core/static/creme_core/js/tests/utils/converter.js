(function($) {

QUnit.module("creme.utils.ConverterRegistry", new QUnitMixin({
    str2int: function(data) {
        var res = parseInt(data);

        if (isNaN(res)) {
            throw new Error('"' + data + '" <' + typeof data + '> is not a number');
        }

        return res;
    },

    str2float: function(data) {
        var res = parseFloat(data);

        if (isNaN(res)) {
            throw new Error('"' + data + '" <' + typeof data + '> is not a number');
        }

        return res;
    }
}));

QUnit.test('creme.utils.ConverterRegistry.register', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    assert.equal(false, converters.available('string', 'int'));
    assert.equal(false, converters.available('string', 'float'));

    converters.register('string', 'int', this.str2int);

    assert.equal(true, converters.available('string', 'int'));
    assert.equal(false, converters.available('string', 'float'));

    converters.register('string', 'float', this.str2float);

    assert.equal(true, converters.available('string', 'int'));
    assert.equal(true, converters.available('string', 'float'));
});

QUnit.test('creme.utils.ConverterRegistry.register (from array)', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    assert.equal(false, converters.available('string', 'int'));
    assert.equal(false, converters.available('string', 'float'));
    assert.equal(false, converters.available('text', 'int'));
    assert.equal(false, converters.available('text', 'float'));

    converters.register(['text', 'string'], 'int', this.str2int);

    assert.equal(true, converters.available('string', 'int'));
    assert.equal(false, converters.available('string', 'float'));
    assert.equal(true, converters.available('text', 'int'));
    assert.equal(false, converters.available('text', 'float'));

    converters.register(['text', 'string'], 'float', this.str2float);

    assert.equal(true, converters.available('string', 'int'));
    assert.equal(true, converters.available('string', 'float'));
    assert.equal(true, converters.available('text', 'int'));
    assert.equal(true, converters.available('text', 'float'));
});


QUnit.test('creme.utils.ConverterRegistry.register (target dict)', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    assert.equal(false, converters.available('string', 'int'));
    assert.equal(false, converters.available('string', 'float'));

    converters.register('string', {
        int: this.str2int,
        float: this.str2float
    });

    assert.equal(converters.converter('string', 'int'), this.str2int);
    assert.equal(converters.converter('string', 'float'), this.str2float);
});

QUnit.test('creme.utils.ConverterRegistry.register (from list, target dict)', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    assert.equal(false, converters.available('string', 'int'));
    assert.equal(false, converters.available('string', 'float'));
    assert.equal(false, converters.available('text', 'int'));
    assert.equal(false, converters.available('text', 'float'));

    converters.register(['text', 'string'], {
        int: this.str2int,
        float: this.str2float
    });

    assert.equal(converters.converter('string', 'int'), this.str2int);
    assert.equal(converters.converter('string', 'float'), this.str2float);
    assert.equal(converters.converter('text', 'int'), this.str2int);
    assert.equal(converters.converter('text', 'float'), this.str2float);
});

QUnit.test('creme.utils.ConverterRegistry.register (not a function)', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    this.assertRaises(function() {
        converters.register('string', 'int', 12);
    }, Error, 'Error: "string-int" converter must be a function');
});

QUnit.test('creme.utils.ConverterRegistry.register (already registered)', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    converters.register('string', 'int', this.str2int);

    this.assertRaises(function() {
        converters.register('string', 'int', this.str2float);
    }, Error, 'Error: "string-int" is already registered');
});

QUnit.test('creme.utils.ConverterRegistry.unregister', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    converters.register('string', {
        int: this.str2int,
        float: this.str2float
    });

    assert.equal(converters.converter('string', 'int'), this.str2int);
    assert.equal(converters.converter('string', 'float'), this.str2float);

    converters.unregister('string', 'int');

    assert.equal(false, converters.available('string', 'int'));
    assert.equal(true, converters.available('string', 'float'));

    converters.unregister('string', 'float');

    assert.equal(false, converters.available('string', 'int'));
    assert.equal(false, converters.available('string', 'float'));
});

QUnit.test('creme.utils.ConverterRegistry.unregister (fail)', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    assert.equal(false, converters.available('string', 'int'));

    this.assertRaises(function() {
        converters.unregister('string', 'int');
    }, Error, 'Error: "string-int" is not registered');
});

QUnit.test('creme.utils.ConverterRegistry.convert', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    converters.register('string', 'int', this.str2int);
    converters.register('string', 'float', this.str2float);

    assert.equal(converters.convert('12', {from: 'string', to: 'int'}), 12);
    assert.equal(converters.convert('12.65', {from: 'string', to: 'int'}), 12);

    assert.equal(converters.convert('12', {from: 'string', to: 'float'}), 12.0);
    assert.equal(converters.convert('12.65', {from: 'string', to: 'float'}), 12.65);
});

QUnit.test('creme.utils.ConverterRegistry.convert (not found)', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    assert.equal(false, converters.available('string', 'int'));

    this.assertRaises(function() {
        converters.converter('string', 'int');
    }, Error, 'Error: "string-int" is not registered');

    this.assertRaises(function() {
        converters.convert('15446', {from: 'string', to: 'int'});
    }, Error, 'Error: "string-int" is not registered');
});

QUnit.test('creme.utils.ConverterRegistry.convert (fail)', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    converters.register('string', 'int', this.str2int);

    this.assertRaises(function() {
        converters.convert({}, {from: 'string', to: 'int'});
    }, Error, 'Error: \"[object Object]\" <object> is not a number');
});

QUnit.test('creme.utils.ConverterRegistry.convert (same)', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    assert.equal(true, converters.available('int', 'int'));
    assert.equal(converters.convert(15446, {from: 'int', to: 'int'}), 15446);
});

QUnit.test('creme.utils.ConverterRegistry.convert (default)', function(assert) {
    var converters = new creme.utils.ConverterRegistry();

    assert.equal(false, converters.available('string', 'int'));
    assert.equal(converters.convert('15446', {from: 'string', to: 'int', defaults: 10}), 10);

    converters.register('string', 'int', this.str2int);
    assert.equal(converters.convert('15446', {from: 'string', to: 'int', defaults: 10}), 15446);
    assert.equal(converters.convert({}, {from: 'string', to: 'int', defaults: 10}), 10);
});

QUnit.parameterize('creme.utils.converters (string-number)', [
    [{from: 'string', to: 'number'}, '15', 15.0],
    [{from: 'string', to: 'int'}, '15', 15],
    [{from: 'string', to: 'float'}, '15', 15.0],
    [{from: 'text', to: 'number'}, '15', 15.0],
    [{from: 'text', to: 'int'}, '15', 15],
    [{from: 'text', to: 'float'}, '15', 15.0],
    [{from: 'string', to: 'number'}, '15.52', 15.52],
    [{from: 'string', to: 'int'}, '15.52', 15],
    [{from: 'string', to: 'float'}, '15.52', 15.52],
    [{from: 'text', to: 'number'}, '15.52', 15.52],
    [{from: 'text', to: 'int'}, '15.52', 15],
    [{from: 'text', to: 'float'}, '15.52', 15.52]
], function(options, value, expected, assert) {
    var converters = creme.utils.converters();

    assert.equal(expected, converters.convert(value, options));
});

QUnit.parameterize('creme.utils.converters (string-number, fail)', [
    [{from: 'string', to: 'number'}, '"nan" is not a number'],
    [{from: 'string', to: 'int'}, '"nan" is not an integer'],
    [{from: 'string', to: 'float'}, '"nan" is not a number'],
    [{from: 'string', to: 'number'}, '"nan" is not a number'],
    [{from: 'string', to: 'int'}, '"nan" is not an integer'],
    [{from: 'string', to: 'float'}, '"nan" is not a number']
], function(options, expected, assert) {
    var converters = creme.utils.converters();

    this.assertRaises(function() {
        converters.convert('nan', options);
    }, Error, 'Error: ${expected}'.template({expected: expected}));

    assert.equal(0, converters.convert('nan', $.extend({}, options, {defaults: 0})));
});

QUnit.parameterize('creme.utils.converters (string-datetime)', [
    [{from: 'string', to: 'date'},
        '2019-11-28',
        moment({year: 2019, month: 10, day: 28, hour: 0, minute: 0, second: 0})],
    [{from: 'string', to: 'date'},
        '2019-11-28T08:10:30',
        moment({year: 2019, month: 10, day: 28, hour: 0, minute: 0, second: 0})],
    [{from: 'string', to: 'datetime'},
        '2019-11-28T08:10:30',
        moment({year: 2019, month: 10, day: 28, hour: 8, minute: 10, second: 30})],
    [{from: 'text', to: 'date'},
        '2019-11-28',
        moment({year: 2019, month: 10, day: 28, hour: 0, minute: 0, second: 0})],
    [{from: 'text', to: 'datetime'},
        '2019-11-28T08:10:30',
        moment({year: 2019, month: 10, day: 28, hour: 8, minute: 10, second: 30})]
], function(options, value, expected, assert) {
    var converters = creme.utils.converters();
    var result = converters.convert(value, options);

    assert.ok(result instanceof moment, result);
    assert.ok(result.isValid());
    assert.ok(expected.isValid());
    assert.equal(expected.format(), result.format());
});

QUnit.parameterize('creme.utils.converters (string-datetime, fail)', [
    [{from: 'string', to: 'date'}, '2019-13-52', '"2019-13-52" is not an iso8601 date'],
    [{from: 'string', to: 'date'}, 'nodate', '"nodate" is not an iso8601 date'],
    [{from: 'string', to: 'datetime'}, '12-12-2019Tnodate', '"12-12-2019Tnodate" is not an iso8601 datetime'],
    [{from: 'string', to: 'datetime'}, '2019-11-28T23:67:00', '"2019-11-28T23:67:00" is not an iso8601 datetime']
], function(options, value, expected, assert) {
    var converters = creme.utils.converters();

    this.assertRaises(function() {
        converters.convert(value, options);
    }, Error, 'Error: ${expected}'.template({expected: expected}));
});

QUnit.parameterize('creme.utils.converters (datetime-string)', [
    [{from: 'date', to: 'string'},
        moment({year: 2019, month: 10, day: 28}),
        '2019-11-28'],
    [{from: 'date', to: 'string'},
        new Date(2019, 10, 28),
        '2019-11-28'],
    [{from: 'date', to: 'string'},
        moment({year: 2019, month: 10, day: 28, hour: 8, minute: 10, second: 30}),
        '2019-11-28'],
    [{from: 'date', to: 'string'},
        new Date(2019, 10, 28, 8, 10, 30),
        '2019-11-28'],
    [{from: 'datetime', to: 'string'},
        moment.utc({year: 2019, month: 10, day: 28, hour: 8, minute: 10, second: 30}),
        '2019-11-28T08:10:30Z'],
    [{from: 'datetime', to: 'string'},
        new Date(2019, 10, 28, 8, 10, 30),
        '2019-11-28T08:10:30' + moment('2019-11-28').format('Z')], // timezone shift at this date
    [{from: 'date', to: 'text'},
        moment({year: 2019, month: 10, day: 28}),
        '2019-11-28'],
    [{from: 'datetime', to: 'text'},
        moment({year: 2019, month: 10, day: 28, hour: 8, minute: 10, second: 30}),
        '2019-11-28T08:10:30' + moment('2019-11-28').format('Z')]
], function(options, value, expected, assert) {
    var converters = creme.utils.converters();
    var result = converters.convert(value, options);

    assert.equal(result, expected);
});

QUnit.parameterize('creme.utils.converters (string-datetime, fail)', [
    [{from: 'date', to: 'string'}, '2019-13-52', '"2019-13-52" is not a date nor datetime'],
    [{from: 'date', to: 'text'}, 12, '12 is not a date nor datetime'],
    [{from: 'datetime', to: 'string'}, '12-12-2019', '"12-12-2019" is not a date nor datetime'],
    [{from: 'datetime', to: 'text'}, 12, '12 is not a date nor datetime']
], function(options, value, expected, assert) {
    var converters = creme.utils.converters();

    this.assertRaises(function() {
        converters.convert(value, options);
    }, Error, 'Error: ${expected}'.template({expected: expected}));
});

QUnit.parameterize('creme.utils.converters (string-json)', [
    [{from: 'string', to: 'json'}, '12', 12],
    [{from: 'string', to: 'json'}, '"a"', 'a'],
    [{from: 'string', to: 'json'}, '[1, 3, "a"]', [1, 3, 'a']],
    [{from: 'text', to: 'json'}, '{"a": 12, "b": [1, 3, 0]}', {a: 12, b: [1, 3, 0]}]
], function(options, value, expected, assert) {
    var converters = creme.utils.converters();
    var result = converters.convert(value, options);

    assert.deepEqual(result, expected);
});

QUnit.parametrize('creme.utils.converters (string-json, fail)', [
    [{from: 'string', to: 'json'}, '12-'],
    [{from: 'string', to: 'json'}, '{"a"'],
    [{from: 'text', to: 'json'}, '[1 "a"]']
], function(options, value, expected, assert) {
    var converters = creme.utils.converters();

    this.assertRaises(function() {
        converters.convert(value, options);
    }, SyntaxError);
});

QUnit.parameterize('creme.utils.converters (json-string)', [
    [{from: 'json', to: 'string'}, 12, '12'],
    [{from: 'json', to: 'string'}, 'a', '"a"'],
    [{from: 'json', to: 'text'}, {a: 12, b: [1, 3, 0]}, '{"a":12,"b":[1,3,0]}']
], function(options, value, expected, assert) {
    var converters = creme.utils.converters();
    var result = converters.convert(value, options);

    assert.deepEqual(result, expected);
});

}(jQuery));
