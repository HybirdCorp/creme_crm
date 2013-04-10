module("creme.converters.js", {
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

        this.converters = new jQuery.ConverterRegistry();
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

test('converters.register', function() {
    equal(this.converters.converter('string', 'int'), undefined);
    equal(this.converters.converter('string', 'float'), undefined);

    this.converters.register('string', 'int', this.str2int);

    equal(this.converters.converter('string', 'int'), this.str2int);
    equal(this.converters.converter('string', 'float'), undefined);

    this.converters.register('string', 'float', this.str2float);

    equal(this.converters.converter('string', 'int'), this.str2int);
    equal(this.converters.converter('string', 'float'), this.str2float);
});

test('converters.register (fail)', function() {
    this.converters.register('string', 'int', this.str2int);
    equal(this.converters.converter('string', 'int'), this.str2int);

    assertRaises(function() {
               this.converters.register('string', 'int', this.str2float);
           }, Error, 'Error: converter "string-int" is already registered');
});

test('converters.unregister', function() {
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

test('converters.unregister (fail)', function() {
    equal(this.converters.converter('string', 'int'), undefined);

    assertRaises(function() {
               this.converters.unregister('string', 'int');
           }, Error, 'Error: no such converter "string-int"');
});

test('converters.convert', function() {
    this.converters.register('string', 'int', this.str2int);
    this.converters.register('string', 'float', this.str2float);

    equal(this.converters.convert('string', 'int', '12'), 12);
    equal(this.converters.convert('string', 'int', '12.65'), 12);

    equal(this.converters.convert('string', 'float', '12'), 12.0);
    equal(this.converters.convert('string', 'float', '12.65'), 12.65);
});

test('converters.convert (not found)', function() {
    equal(this.converters.converter('string', 'int'), undefined);

    assertRaises(function() {
        this.converters.convert('string', 'int', '15446');
    }, Error, 'Error: no such converter "string-int"');
});

test('converters.convert (fail)', function() {
    this.converters.register('string', 'int', this.str2int);
    
    assertRaises(function() {
        this.converters.convert('string', 'int', {});
    }, Error, 'Error: unable to convert data from "string" to "int" : \"[object Object]\" <object> is not a number');
});

test('converters.convert (same)', function() {
    equal(this.converters.converter('int', 'int'), undefined);
    equal(this.converters.convert('int', 'int', 15446), 15446);
});

test('converters.convert (default)', function() {
    equal(this.converters.converter('string', 'int'), undefined);
    equal(this.converters.convert('string', 'int', '15446', 10), 10);

    this.converters.register('string', 'int', this.str2int);
    equal(this.converters.convert('string', 'int', '15446', 10), 15446);
});
