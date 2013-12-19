module("creme.utils.converters.js", {
    setup: function() {
        this.str2int = function(data) {
            res = parseInt(data);

            if (isNaN(res))
                throw '"' + data + '" <' + typeof data + '> is not a number';

            return res;
        };
        this.str2float = function(data) {
            res = parseFloat(data);

            if (isNaN(res))
                throw '"' + data + '" <' + typeof data + '> is not a number';

            return res;
        };

        this.converters = new creme.utils.ConverterRegistry();
    },

    teardown: function() {
    }
});

function assertRaises(block, expected, message)
{
    raises(block,
           function(error) {
                ok(error instanceof expected);
                equal(message, '' + error);
                return true;
           });
}

test('creme.utils.ConverterRegistry.register', function() {
    equal(this.converters.converter('string', 'int'), undefined);
    equal(this.converters.converter('string', 'float'), undefined);

    this.converters.register('string', 'int', this.str2int);

    equal(this.converters.converter('string', 'int'), this.str2int);
    equal(this.converters.converter('string', 'float'), undefined);

    this.converters.register('string', 'float', this.str2float);

    equal(this.converters.converter('string', 'int'), this.str2int);
    equal(this.converters.converter('string', 'float'), this.str2float);
});

test('creme.utils.ConverterRegistry.register (fail)', function() {
    this.converters.register('string', 'int', this.str2int);
    equal(this.converters.converter('string', 'int'), this.str2int);

    assertRaises(function() {
               this.converters.register('string', 'int', this.str2float);
           }, Error, 'Error: converter "string-int" is already registered');
});

test('creme.utils.ConverterRegistry.unregister', function() {
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

test('creme.utils.ConverterRegistry.unregister (fail)', function() {
    equal(this.converters.converter('string', 'int'), undefined);

    assertRaises(function() {
               this.converters.unregister('string', 'int');
           }, Error, 'Error: no such converter "string-int"');
});

test('creme.utils.ConverterRegistry.convert', function() {
    this.converters.register('string', 'int', this.str2int);
    this.converters.register('string', 'float', this.str2float);

    equal(this.converters.convert('string', 'int', '12'), 12);
    equal(this.converters.convert('string', 'int', '12.65'), 12);

    equal(this.converters.convert('string', 'float', '12'), 12.0);
    equal(this.converters.convert('string', 'float', '12.65'), 12.65);
});

test('creme.utils.ConverterRegistry.convert (not found)', function() {
    equal(this.converters.converter('string', 'int'), undefined);

    assertRaises(function() {
        this.converters.convert('string', 'int', '15446');
    }, Error, 'Error: no such converter "string-int"');
});

test('creme.utils.ConverterRegistry.convert (fail)', function() {
    this.converters.register('string', 'int', this.str2int);
    
    assertRaises(function() {
        this.converters.convert('string', 'int', {});
    }, Error, 'Error: unable to convert data from "string" to "int" : \"[object Object]\" <object> is not a number');
});

test('creme.utils.ConverterRegistry.convert (same)', function() {
    equal(this.converters.converter('int', 'int'), undefined);
    equal(this.converters.convert('int', 'int', 15446), 15446);
});

test('creme.utils.ConverterRegistry.convert (default)', function() {
    equal(this.converters.converter('string', 'int'), undefined);
    equal(this.converters.convert('string', 'int', '15446', 10), 10);

    this.converters.register('string', 'int', this.str2int);
    equal(this.converters.convert('string', 'int', '15446', 10), 15446);
});

test('creme.utils.converters (string-number)', function() {
    equal(true, Object.isFunc(creme.utils.converter('string', 'number')));

    assertRaises(function() {
        creme.utils.convert('string', 'number', 'nan');
    }, Error, 'Error: unable to convert data from \"string\" to \"number\" : "nan" is not a number');

    assertRaises(function() {
        creme.utils.convert('string', 'number', '');
    }, Error, 'Error: unable to convert data from \"string\" to \"number\" : "" is not a number');

    assertRaises(function() {
        creme.utils.convert('string', 'number', 454);
    }, Error, 'Error: unable to convert data from \"string\" to \"number\" : "454" is not a string');

    equal(1456, creme.utils.convert('string', 'number', '1456'));
    equal(15, creme.utils.convert('string', 'number', '15ab'));
});

test('creme.utils.converters (string-float)', function() {
    equal(true, Object.isFunc(creme.utils.converter('string', 'float')));

    assertRaises(function() {
        creme.utils.convert('string', 'float', 'nan');
    }, Error, 'Error: unable to convert data from \"string\" to \"float\" : "nan" is not a number');

    assertRaises(function() {
        creme.utils.convert('string', 'float', '');
    }, Error, 'Error: unable to convert data from \"string\" to \"float\" : "" is not a number');

    assertRaises(function() {
        creme.utils.convert('string', 'float', 454);
    }, Error, 'Error: unable to convert data from \"string\" to \"float\" : "454" is not a string');

    equal(1456.445, creme.utils.convert('string', 'float', '1456.445'));
    equal(15, creme.utils.convert('string', 'float', '15ab'));
});

test('creme.utils.converters (string-int)', function() {
    equal(true, Object.isFunc(creme.utils.converter('string', 'int')));

    assertRaises(function() {
        creme.utils.convert('string', 'int', 'nan');
    }, Error, 'Error: unable to convert data from \"string\" to \"int\" : "nan" is not a number');

    assertRaises(function() {
        creme.utils.convert('string', 'int', '');
    }, Error, 'Error: unable to convert data from \"string\" to \"int\" : "" is not a number');

    assertRaises(function() {
        creme.utils.convert('string', 'int', 454);
    }, Error, 'Error: unable to convert data from \"string\" to \"int\" : "454" is not a string');

    equal(1456, creme.utils.convert('string', 'int', '1456.445'));
    equal(15, creme.utils.convert('string', 'int', '15ab'));
});

