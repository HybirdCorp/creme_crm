(function($) {

QUnit.module("creme.utils.lambda.js", new QUnitMixin());

QUnit.test('creme.utils.Lambda (constructor, default)', function(assert) {
    var lambda = new creme.utils.Lambda();
    equal(false, lambda.isValid());
    equal(undefined, lambda._context);
    equal(undefined, lambda._lambda);
});

QUnit.test('creme.utils.Lambda (constructor, function)', function(assert) {
    var f = function() { return 1; };
    var lambda = new creme.utils.Lambda(f);

    equal(true, lambda.isValid());
    equal(undefined, lambda._context);
    equal(f, lambda._lambda);

    equal(1, lambda.call(this));
    equal(1, lambda.apply(this));
});

QUnit.test('creme.utils.Lambda (constructor, script, no parameter)', function(assert) {
    var lambda = new creme.utils.Lambda('return 48;');

    equal(true, lambda.isValid());
    equal(undefined, lambda._context);
    equal('function', typeof lambda._lambda);

    equal(48, lambda.call(this));
    equal(48, lambda.apply(this));
    equal(48, lambda.apply(this, [1, 3]));
});

QUnit.test('creme.utils.Lambda (constructor, script, parameter)', function(assert) {
    var lambda = new creme.utils.Lambda('return a;', 'a');

    equal(true, lambda.isValid());
    equal(undefined, lambda._context);
    equal('function', typeof lambda._lambda);

    equal(undefined, lambda.call());
    equal('test', lambda.call(this, 'test'));
    equal(4, lambda.call(this, 4));

    equal(undefined, lambda.apply(this));
    equal('test', lambda.apply(this, ['test']));
    equal(7, lambda.apply(this, [7]));
});

QUnit.test('creme.utils.Lambda (constructor, script, multi parameter string)', function(assert) {
    var lambda = new creme.utils.Lambda('return a + b + c;', 'a, b, c');

    equal(true, lambda.isValid());
    equal(undefined, lambda._context);
    equal('function', typeof lambda._lambda);

    equal('test, test2, test3', lambda.call(this, 'test', ', test2', ', test3'));
    equal(1 + 2 + 3, lambda.call(this, 1, 2, 3));

    equal('test, test2, test3', lambda.apply(this, ['test', ', test2', ', test3']));
    equal(4 + 5 + 6, lambda.apply(this, [4, 5, 6]));
});

QUnit.test('creme.utils.Lambda (constructor, script, multi parameter array)', function(assert) {
    var lambda = new creme.utils.Lambda('return a + b + c;', ['a', 'b', 'c']);

    equal(true, lambda.isValid());
    equal(undefined, lambda._context);
    equal('function', typeof lambda._lambda);

    equal('test, test2, test3', lambda.call(this, 'test', ', test2', ', test3'));
    equal(1 + 2 + 3, lambda.call(this, 1, 2, 3));

    equal('test, test2, test3', lambda.apply(this, ['test', ', test2', ', test3']));
    equal(4 + 5 + 6, lambda.apply(this, [4, 5, 6]));
});

QUnit.test('creme.utils.Lambda (constructor, constant)', function(assert) {
    var lambda = new creme.utils.Lambda(12);

    equal(true, lambda.isValid());
    equal(undefined, lambda._context);
    equal('function', typeof lambda._lambda);

    equal(12, lambda.call(this));
    equal(12, lambda.call(this, 4));

    equal(12, lambda.apply(this));
    equal(12, lambda.apply(this, [7]));
});

QUnit.test('creme.utils.Lambda (constructor, invalid script)', function(assert) {
    this.assertRaises(function() {
        return new creme.utils.Lambda('');
    }, Error, 'Error: empty lambda script');

    QUnit.assert.raises(function() {
               return new creme.utils.Lambda('(new invalid;-4)');
           },
           function(error) {
                ok(error instanceof Error);
                ok(('' + error).startsWith('SyntaxError'));
                return true;
           });
});

QUnit.test('creme.utils.Lambda (lambda)', function(assert) {
    var f = function(b) { return (this.a || 0) - b; };
    var lambda = new creme.utils.Lambda();

    equal(false, lambda.isValid());
    equal(undefined, lambda._context);
    equal(undefined, lambda._lambda);
    equal(undefined, lambda.callable());

    lambda.lambda(f);

    equal(true, lambda.isValid());
    equal(undefined, lambda._context);
    equal(f, lambda._lambda);
    equal(f, lambda.callable());

    this.a = 15;
    equal(15 - 12, lambda.call(this, 12));
    equal(15 - 12, lambda._lambda.call(this, 12));

    lambda.lambda('b', 'b');

    equal(true, lambda.isValid());
    equal(undefined, lambda._context);
    equal('function', typeof lambda._lambda);
    equal('function', typeof lambda.callable());
    equal(lambda._lambda, lambda.callable());

    this.a = 0;
    equal(12, lambda.call(this, 12));
});

QUnit.test('creme.utils.Lambda (bind)', function(assert) {
    var f = function(b) { return (this.a || 0) - b; };
    var lambda = new creme.utils.Lambda(f);

    equal(true, lambda.isValid());
    equal(undefined, lambda._context);
    equal(f, lambda._lambda);
    equal(f, lambda.callable());

    this.a = 47;

    equal(-1, lambda.callable()(1), 'callable none');
    equal(-2, lambda.invoke(2), 'invoke none');

    equal(-1, lambda.call({}, 1), 'call {}');
    equal(47 - 1, lambda.call(this, 1), 'call this');
    equal(-2, lambda.callable().call({}, 2), 'callable.call {}');
    equal(47 - 2, lambda.callable().call(this, 2), 'callable.call this');

    equal(-1, lambda.apply({}, [1]), 'apply {}');
    equal(47 - 1, lambda.apply(this, [1]), 'apply this');
    equal(-2, lambda.callable().apply({}, [2]), 'callable.apply {}');
    equal(47 - 2, lambda.callable().apply(this, [2]), 'callable.apply this');

    lambda.bind(this);
    equal(f, lambda._lambda);
    notEqual(f, lambda.callable());

    equal(47 - 1, lambda.invoke(1), 'invoke this');
    equal(47 - 3, lambda.invoke(3));
    equal(47 - 4, lambda.callable().call({}, 4), 'callable.call already bound');

    equal(47 - 1, lambda.apply(this, [1]));
    equal(47 - 3, lambda.apply(this, [3]));
    equal(47 - 4, lambda.callable().apply(this, [4]), 'callable.apply');

    lambda.bind({a: 78});

    equal(78 - 1, lambda.invoke(1));
    equal(78 - 3, lambda.invoke(3));
    equal(78 - 4, lambda.callable().call(lambda, 4), 'callable.call');

    equal(47 - 1, lambda.apply(this, [1]));
    equal(47 - 3, lambda.apply(this, [3]));
    equal(78 - 4, lambda.callable().apply(this, [4]), 'callable.apply');
});
}(jQuery));

