(function($) {

QUnit.module("creme.widgets.base.js", new QUnitMixin());

QUnit.test('creme.widget.parseopt (no default options)', function(assert) {
    var options = creme.widget.parseopt($('<div/>'));
    assert.deepEqual(options, {});

    options = creme.widget.parseopt($('<div attr1="val1" attr2="val2" attr3="val3"/>'));
    assert.deepEqual(options, {});

    options = creme.widget.parseopt($('<div attr1="val1" attr2="val2" attr3="val3"/>'), {}, {}, []);
    assert.deepEqual(options, {});
});

QUnit.test('creme.widget.parseopt (default options)', function(assert) {
    var options = creme.widget.parseopt($('<div/>'), {attr1: 'default1', attr2: 'default2'});
    assert.deepEqual(options, {attr1: 'default1', attr2: 'default2'});

    options = creme.widget.parseopt($('<div attr1="val1" attr2="val2" attr3="val3"/>'), {attr1: 'default1', attr2: 'default2'});
    assert.deepEqual(options, {attr1: 'val1', attr2: 'val2'});

    options = creme.widget.parseopt($('<div attr1="val1" attr3="val3"/>'), {attr1: 'default1', attr2: 'default2'});
    assert.deepEqual(options, {attr1: 'val1', attr2: 'default2'});
});

QUnit.test('creme.widget.parseattr (no exclusion)', function(assert) {
    var attrs = creme.widget.parseattr($('<div/>'));
    assert.deepEqual(attrs, {});

    attrs = creme.widget.parseattr($('<div attr1="val1" attr2="val2" attr3="val3"/>'));
    assert.deepEqual(attrs, {attr1: 'val1', attr2: 'val2', attr3: 'val3'});

    attrs = creme.widget.parseattr($('<div attr1="val1" attr2="val2" attr3="val3" widget="creme.widget"/>'));
    assert.deepEqual(attrs, {attr1: 'val1', attr2: 'val2', attr3: 'val3', widget: "creme.widget"});
});

QUnit.test('creme.widget.parseattr (with exclusion)', function(assert) {
    var attrs = creme.widget.parseattr($('<div/>'), {'attr2': ''});
    assert.deepEqual(attrs, {});

    attrs = creme.widget.parseattr($('<div attr1="val1" attr2="val2" attr3="val3"/>'), {'attr2': ''});
    assert.deepEqual(attrs, {attr1: 'val1', attr3: 'val3'});

    attrs = creme.widget.parseattr($('<div attr1="val1" attr2="val2" attr3="val3"/>'), ['attr1', 'attr3']);
    assert.deepEqual(attrs, {attr2: 'val2'});
});

QUnit.test('creme.widget.parseval (parser: json, value: none)', function(assert) {
    var result = creme.widget.parseval(undefined, JSON.parse);
    assert.equal(result, undefined);

    result = creme.widget.parseval(null, JSON.parse);
    assert.equal(result, null);

    result = creme.widget.parseval(undefined);
    assert.equal(result, undefined);

    result = creme.widget.parseval(null);
    assert.equal(result, null);
});

QUnit.test('creme.widget.parseval (parser: json, value: object)', function(assert) {
    var result = creme.widget.parseval({'a': 2, 'b': 3}, JSON.parse);
    assert.deepEqual(result, {'a': 2, 'b': 3});

    result = creme.widget.parseval({'a': 2, 'b': 3});
    assert.deepEqual(result, {'a': 2, 'b': 3});

    result = creme.widget.parseval(15);
    assert.deepEqual(result, 15);
});

QUnit.test('creme.widget.parseval (parser: json, value: invalid json)', function(assert) {
    var result = creme.widget.parseval('{"a":2, "b":3', JSON.parse);
    assert.equal(result, null);

    result = creme.widget.parseval('', JSON.parse);
    assert.equal(result, null);

    result = creme.widget.parseval('["a", 2', JSON.parse);
    assert.equal(result, null);

    result = creme.widget.parseval("15a335", JSON.parse);
    assert.equal(result, null);
});

QUnit.test('creme.widget.parseval (parser: json, value: valid json)', function(assert) {
    var result = creme.widget.parseval('{"a":2, "b":3}', JSON.parse);
    assert.deepEqual(result, {'a': 2, 'b': 3});

    result = creme.widget.parseval('""', JSON.parse);
    assert.deepEqual(result, "");

    result = creme.widget.parseval('["a", "b", 2]', JSON.parse);
    assert.deepEqual(result, ['a', 'b', 2]);

    result = creme.widget.parseval("15335", JSON.parse);
    assert.equal(result, 15335);
});

QUnit.test('creme.widget.parseval (parser: none, value: invalid json)', function(assert) {
    var result = creme.widget.parseval('{"a":2, "b":3}');
    assert.equal(result, '{"a":2, "b":3}');

    result = creme.widget.parseval('["a", 2');
    assert.equal(result, '["a", 2');
});

QUnit.test('creme.widget.cleanval (parser: default, value: none)', function(assert) {
    var result = creme.widget.cleanval(undefined);
    assert.equal(result, undefined);

    result = creme.widget.cleanval(null);
    assert.equal(result, null);
});

QUnit.test('creme.widget.cleanval (parser: default, value: none, default value)', function(assert) {
    var result = creme.widget.cleanval(undefined, 'default');
    assert.equal(result, 'default');

    result = creme.widget.cleanval(null, 'default');
    assert.equal(result, 'default');
});

QUnit.test('creme.widget.cleanval (parser: none (json), value: object)', function(assert) {
    var result = creme.widget.cleanval({'a': 2, 'b': 3});
    assert.deepEqual(result, {'a': 2, 'b': 3});

    result = creme.widget.cleanval(['a', 2, 'b', 3]);
    assert.deepEqual(result, ['a', 2, 'b', 3]);
});

QUnit.test('creme.widget.cleanval (parser: none (json), value: valid json)', function(assert) {
    var result = creme.widget.cleanval('{"a":2, "b":3}');
    assert.deepEqual(result, {'a': 2, 'b': 3});

    result = creme.widget.cleanval('""');
    assert.deepEqual(result, "");

    result = creme.widget.cleanval('["a", "b", 2]');
    assert.deepEqual(result, ['a', 'b', 2]);

    result = creme.widget.cleanval("15335");
    assert.equal(result, 15335);
});

QUnit.test('creme.widget.cleanval (parser: none (json), value: invalid json)', function(assert) {
    var result = creme.widget.cleanval('{"a":2, "b":3');
    assert.equal(result, null);

    result = creme.widget.cleanval('');
    assert.equal(result, null);

    result = creme.widget.cleanval('["a", 2');
    assert.equal(result, null);

    result = creme.widget.cleanval("15a335");
    assert.equal(result, null);
});

QUnit.test('creme.widget.cleanval (parser: none (json), value: invalid json, default value)', function(assert) {
    var result = creme.widget.cleanval('{"a":2, "b":3', {"a": 15});
    assert.deepEqual(result, {"a": 15});

    result = creme.widget.cleanval('', "");
    assert.equal(result, "");

    result = creme.widget.cleanval('["a", 2', []);
    assert.deepEqual(result, []);

    result = creme.widget.cleanval("15a335", 0);
    assert.equal(result, 0);
});

QUnit.test('creme.object.invoke', function(assert) {
    assert.equal(undefined, creme.object.invoke());
    assert.equal(undefined, creme.object.invoke(undefined));
    assert.equal(undefined, creme.object.invoke(null));

    assert.equal(undefined, creme.object.invoke(null, 5.2));
    assert.equal(undefined, creme.object.invoke(458, 5.2));
    assert.equal(undefined, creme.object.invoke('test', 5.2));

    assert.equal(-458, creme.object.invoke(function() { return -458; }));
    assert.equal(5.2, creme.object.invoke(function(a) { return a; }, 5.2));
    assert.deepEqual([5.2, 12.5], creme.object.invoke(function(a, b) { return [b, a]; }, 12.5, 5.2));
});

QUnit.test('creme.object.delegate', function(assert) {
    assert.equal(undefined, creme.object.delegate());
    assert.equal(undefined, creme.object.delegate(undefined));
    assert.equal(undefined, creme.object.delegate(null));

    var instance = {
        val: function() { return 12; },
        add: function(a, b) { return a + b; }
    };

    assert.equal(undefined, creme.object.delegate(null, 'val'));
    assert.equal(undefined, creme.object.delegate(undefined, 'val'));
    assert.equal(undefined, creme.object.delegate(instance, 'unknown'));

    assert.equal(12, creme.object.delegate(instance, 'val'));
    assert.equal(7, creme.object.delegate(instance, 'add', 3, 4));
});

}(jQuery));
