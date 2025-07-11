(function($) {

QUnit.module("creme.utils.lambda.js", new QUnitMixin());

QUnit.test('creme.utils.Lambda (constructor, default)', function(assert) {
    var lambda = new creme.utils.Lambda();
    assert.equal(false, lambda.isValid());
    assert.equal(undefined, lambda._context);
    assert.equal(undefined, lambda._lambda);
});

QUnit.test('creme.utils.Lambda (constructor, function)', function(assert) {
    var f = function() { return 1; };
    var lambda = new creme.utils.Lambda(f);

    assert.equal(true, lambda.isValid());
    assert.equal(undefined, lambda._context);
    assert.equal(f, lambda._lambda);

    assert.equal(1, lambda.call(this));
    assert.equal(1, lambda.apply(this));
});

QUnit.test('creme.utils.Lambda (constructor, script, no parameter)', function(assert) {
    var lambda = new creme.utils.Lambda('return 48;');

    assert.equal(true, lambda.isValid());
    assert.equal(undefined, lambda._context);
    assert.equal('function', typeof lambda._lambda);

    assert.equal(48, lambda.call(this));
    assert.equal(48, lambda.apply(this));
    assert.equal(48, lambda.apply(this, [1, 3]));
});

QUnit.test('creme.utils.Lambda (constructor, script, parameter)', function(assert) {
    var lambda = new creme.utils.Lambda('return a;', 'a');

    assert.equal(true, lambda.isValid());
    assert.equal(undefined, lambda._context);
    assert.equal('function', typeof lambda._lambda);

    assert.equal(undefined, lambda.call());
    assert.equal('test', lambda.call(this, 'test'));
    assert.equal(4, lambda.call(this, 4));

    assert.equal(undefined, lambda.apply(this));
    assert.equal('test', lambda.apply(this, ['test']));
    assert.equal(7, lambda.apply(this, [7]));
});

QUnit.test('creme.utils.Lambda (constructor, script, multi parameter string)', function(assert) {
    var lambda = new creme.utils.Lambda('return a + b + c;', 'a, b, c');

    assert.equal(true, lambda.isValid());
    assert.equal(undefined, lambda._context);
    assert.equal('function', typeof lambda._lambda);

    assert.equal('test, test2, test3', lambda.call(this, 'test', ', test2', ', test3'));
    assert.equal(1 + 2 + 3, lambda.call(this, 1, 2, 3));

    assert.equal('test, test2, test3', lambda.apply(this, ['test', ', test2', ', test3']));
    assert.equal(4 + 5 + 6, lambda.apply(this, [4, 5, 6]));
});

QUnit.test('creme.utils.Lambda (constructor, script, multi parameter array)', function(assert) {
    var lambda = new creme.utils.Lambda('return a + b + c;', ['a', 'b', 'c']);

    assert.equal(true, lambda.isValid());
    assert.equal(undefined, lambda._context);
    assert.equal('function', typeof lambda._lambda);

    assert.equal('test, test2, test3', lambda.call(this, 'test', ', test2', ', test3'));
    assert.equal(1 + 2 + 3, lambda.call(this, 1, 2, 3));

    assert.equal('test, test2, test3', lambda.apply(this, ['test', ', test2', ', test3']));
    assert.equal(4 + 5 + 6, lambda.apply(this, [4, 5, 6]));
});

QUnit.test('creme.utils.Lambda (constructor, constant)', function(assert) {
    var lambda = new creme.utils.Lambda(12);

    assert.equal(true, lambda.isValid());
    assert.equal(undefined, lambda._context);
    assert.equal('function', typeof lambda._lambda);

    assert.equal(12, lambda.call(this));
    assert.equal(12, lambda.call(this, 4));

    assert.equal(12, lambda.apply(this));
    assert.equal(12, lambda.apply(this, [7]));
});

QUnit.test('creme.utils.Lambda (constructor, invalid script)', function(assert) {
    this.assertRaises(function() {
        return new creme.utils.Lambda('');
    }, Error, 'Error: empty lambda script');

    assert.raises(function() {
       return new creme.utils.Lambda('(new invalid;-4)');
    },
    function(error) {
        assert.ok(error instanceof Error);
        assert.ok(('' + error).startsWith('SyntaxError'));
        return true;
    });
});

QUnit.test('creme.utils.Lambda (lambda)', function(assert) {
    var f = function(b) { return (this.a || 0) - b; };
    var lambda = new creme.utils.Lambda();

    assert.equal(false, lambda.isValid());
    assert.equal(undefined, lambda._context);
    assert.equal(undefined, lambda._lambda);
    assert.equal(undefined, lambda.callable());

    lambda.lambda(f);

    assert.equal(true, lambda.isValid());
    assert.equal(undefined, lambda._context);
    assert.equal(f, lambda._lambda);
    assert.equal(f, lambda.callable());

    this.a = 15;
    assert.equal(15 - 12, lambda.call(this, 12));
    assert.equal(15 - 12, lambda._lambda.call(this, 12));

    lambda.lambda('b', 'b');

    assert.equal(true, lambda.isValid());
    assert.equal(undefined, lambda._context);
    assert.equal('function', typeof lambda._lambda);
    assert.equal('function', typeof lambda.callable());
    assert.equal(lambda._lambda, lambda.callable());

    this.a = 0;
    assert.equal(12, lambda.call(this, 12));
});

QUnit.test('creme.utils.Lambda (bind)', function(assert) {
    var f = function(b) { return (this.a || 0) - b; };
    var lambda = new creme.utils.Lambda(f);

    assert.equal(true, lambda.isValid());
    assert.equal(undefined, lambda._context);
    assert.equal(f, lambda._lambda);
    assert.equal(f, lambda.callable());

    this.a = 47;

    assert.equal(-1, lambda.callable()(1), 'callable none');
    assert.equal(-2, lambda.invoke(2), 'invoke none');

    assert.equal(-1, lambda.call({}, 1), 'call {}');
    assert.equal(47 - 1, lambda.call(this, 1), 'call this');
    assert.equal(-2, lambda.callable().call({}, 2), 'callable.call {}');
    assert.equal(47 - 2, lambda.callable().call(this, 2), 'callable.call this');

    assert.equal(-1, lambda.apply({}, [1]), 'apply {}');
    assert.equal(47 - 1, lambda.apply(this, [1]), 'apply this');
    assert.equal(-2, lambda.callable().apply({}, [2]), 'callable.apply {}');
    assert.equal(47 - 2, lambda.callable().apply(this, [2]), 'callable.apply this');

    lambda.bind(this);
    assert.equal(f, lambda._lambda);
    assert.notEqual(f, lambda.callable());

    assert.equal(47 - 1, lambda.invoke(1), 'invoke this');
    assert.equal(47 - 3, lambda.invoke(3));
    assert.equal(47 - 4, lambda.callable().call({}, 4), 'callable.call already bound');

    assert.equal(47 - 1, lambda.apply(this, [1]));
    assert.equal(47 - 3, lambda.apply(this, [3]));
    assert.equal(47 - 4, lambda.callable().apply(this, [4]), 'callable.apply');

    lambda.bind({a: 78});

    assert.equal(78 - 1, lambda.invoke(1));
    assert.equal(78 - 3, lambda.invoke(3));
    assert.equal(78 - 4, lambda.callable().call(lambda, 4), 'callable.call');

    assert.equal(47 - 1, lambda.apply(this, [1]));
    assert.equal(47 - 3, lambda.apply(this, [3]));
    assert.equal(78 - 4, lambda.callable().apply(this, [4]), 'callable.apply');
});
}(jQuery));

