(function($) {

QUnit.module("creme.utils.converters.js", new QUnitMixin({
    beforeEach: function() {
        this.converters = new creme.utils.ConverterRegistry();
    },

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
    equal(this.converters.converter('string', 'int'), undefined);
    equal(this.converters.converter('string', 'float'), undefined);

    this.converters.register('string', 'int', this.str2int);

    equal(this.converters.converter('string', 'int'), this.str2int);
    equal(this.converters.converter('string', 'float'), undefined);

    this.converters.register('string', 'float', this.str2float);

    equal(this.converters.converter('string', 'int'), this.str2int);
    equal(this.converters.converter('string', 'float'), this.str2float);
});

QUnit.test('creme.utils.ConverterRegistry.register (fail)', function(assert) {
    this.converters.register('string', 'int', this.str2int);
    equal(this.converters.converter('string', 'int'), this.str2int);

    this.assertRaises(function() {
               this.converters.register('string', 'int', this.str2float);
           }, Error, 'Error: converter "string-int" is already registered');
});

QUnit.test('creme.utils.ConverterRegistry.unregister', function(assert) {
    this.converters.register('string', 'int', this.str2int);
    this.converters.register('string', 'float', this.str2float);

    equal(this.converters.converter('string', 'int'), this.str2int);
    equal(this.converters.converter('string', 'float'), this.str2float);

    this.converters.unregister('string', 'int');

    equal(this.converters.converter('string', 'int'), undefined);
    equal(this.converters.converter('string', 'float'), this.str2float);

    this.converters.unregister('string', 'float');

    equal(this.converters.converter('string', 'int'), undefined);
    equal(this.converters.converter('string', 'float'), undefined);
});

QUnit.test('creme.utils.ConverterRegistry.unregister (fail)', function(assert) {
    equal(this.converters.converter('string', 'int'), undefined);

    this.assertRaises(function() {
               this.converters.unregister('string', 'int');
           }, Error, 'Error: no such converter "string-int"');
});

QUnit.test('creme.utils.ConverterRegistry.convert', function(assert) {
    this.converters.register('string', 'int', this.str2int);
    this.converters.register('string', 'float', this.str2float);

    equal(this.converters.convert('string', 'int', '12'), 12);
    equal(this.converters.convert('string', 'int', '12.65'), 12);

    equal(this.converters.convert('string', 'float', '12'), 12.0);
    equal(this.converters.convert('string', 'float', '12.65'), 12.65);
});

QUnit.test('creme.utils.ConverterRegistry.convert (not found)', function(assert) {
    equal(this.converters.converter('string', 'int'), undefined);

    this.assertRaises(function() {
        this.converters.convert('string', 'int', '15446');
    }, Error, 'Error: no such converter "string-int"');
});

QUnit.test('creme.utils.ConverterRegistry.convert (fail)', function(assert) {
    this.converters.register('string', 'int', this.str2int);

    this.assertRaises(function() {
        this.converters.convert('string', 'int', {});
    }, Error, 'Error: unable to convert data from "string" to "int" : \"[object Object]\" <object> is not a number');
});

QUnit.test('creme.utils.ConverterRegistry.convert (same)', function(assert) {
    equal(this.converters.converter('int', 'int'), undefined);
    equal(this.converters.convert('int', 'int', 15446), 15446);
});

QUnit.test('creme.utils.ConverterRegistry.convert (default)', function(assert) {
    equal(this.converters.converter('string', 'int'), undefined);
    equal(this.converters.convert('string', 'int', '15446', 10), 10);

    this.converters.register('string', 'int', this.str2int);
    equal(this.converters.convert('string', 'int', '15446', 10), 15446);

    equal(this.converters.convert('string', 'int', {}, 10), 10);
});

QUnit.test('creme.utils.converters (string-number)', function(assert) {
    equal(true, Object.isFunc(creme.utils.converter('string', 'number')));

    this.assertRaises(function() {
        creme.utils.convert('string', 'number', 'nan');
    }, Error, 'Error: unable to convert data from \"string\" to \"number\" : "nan" is not a number');

    this.assertRaises(function() {
        creme.utils.convert('string', 'number', '');
    }, Error, 'Error: unable to convert data from \"string\" to \"number\" : "" is not a number');

    this.assertRaises(function() {
        creme.utils.convert('string', 'number', 454);
    }, Error, 'Error: unable to convert data from \"string\" to \"number\" : "454" is not a string');

    equal(1456, creme.utils.convert('string', 'number', '1456'));
    equal(15, creme.utils.convert('string', 'number', '15ab'));
});

QUnit.test('creme.utils.converters (string-float)', function(assert) {
    equal(true, Object.isFunc(creme.utils.converter('string', 'float')));

    this.assertRaises(function() {
        creme.utils.convert('string', 'float', 'nan');
    }, Error, 'Error: unable to convert data from \"string\" to \"float\" : "nan" is not a number');

    this.assertRaises(function() {
        creme.utils.convert('string', 'float', '');
    }, Error, 'Error: unable to convert data from \"string\" to \"float\" : "" is not a number');

    this.assertRaises(function() {
        creme.utils.convert('string', 'float', 454);
    }, Error, 'Error: unable to convert data from \"string\" to \"float\" : "454" is not a string');

    equal(1456.445, creme.utils.convert('string', 'float', '1456.445'));
    equal(15, creme.utils.convert('string', 'float', '15ab'));
});

QUnit.test('creme.utils.converters (string-int)', function(assert) {
    equal(true, Object.isFunc(creme.utils.converter('string', 'int')));

    this.assertRaises(function() {
        creme.utils.convert('string', 'int', 'nan');
    }, Error, 'Error: unable to convert data from \"string\" to \"int\" : "nan" is not a number');

    this.assertRaises(function() {
        creme.utils.convert('string', 'int', '');
    }, Error, 'Error: unable to convert data from \"string\" to \"int\" : "" is not a number');

    this.assertRaises(function() {
        creme.utils.convert('string', 'int', 454);
    }, Error, 'Error: unable to convert data from \"string\" to \"int\" : "454" is not a string');

    equal(1456, creme.utils.convert('string', 'int', '1456.445'));
    equal(15, creme.utils.convert('string', 'int', '15ab'));
});

}(jQuery));
