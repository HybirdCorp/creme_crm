(function($) {

QUnit.module("creme.widgets.base.js", new QUnitMixin());

QUnit.test('creme.widget.parseopt (no default options)', function(assert) {
    var options = creme.widget.parseopt($('<div/>'));
    deepEqual(options, {});

    options = creme.widget.parseopt($('<div attr1="val1" attr2="val2" attr3="val3"/>'));
    deepEqual(options, {});

    options = creme.widget.parseopt($('<div attr1="val1" attr2="val2" attr3="val3"/>'), {}, {}, []);
    deepEqual(options, {});
});

QUnit.test('creme.widget.parseopt (default options)', function(assert) {
    var options = creme.widget.parseopt($('<div/>'), {attr1: 'default1', attr2: 'default2'});
    deepEqual(options, {attr1: 'default1', attr2: 'default2'});

    options = creme.widget.parseopt($('<div attr1="val1" attr2="val2" attr3="val3"/>'), {attr1: 'default1', attr2: 'default2'});
    deepEqual(options, {attr1: 'val1', attr2: 'val2'});

    options = creme.widget.parseopt($('<div attr1="val1" attr3="val3"/>'), {attr1: 'default1', attr2: 'default2'});
    deepEqual(options, {attr1: 'val1', attr2: 'default2'});
});

QUnit.test('creme.widget.parseattr (no exclusion)', function(assert) {
    var attrs = creme.widget.parseattr($('<div/>'));
    deepEqual(attrs, {});

    attrs = creme.widget.parseattr($('<div attr1="val1" attr2="val2" attr3="val3"/>'));
    deepEqual(attrs, {attr1: 'val1', attr2: 'val2', attr3: 'val3'});

    attrs = creme.widget.parseattr($('<div attr1="val1" attr2="val2" attr3="val3" widget="creme.widget"/>'));
    deepEqual(attrs, {attr1: 'val1', attr2: 'val2', attr3: 'val3', widget: "creme.widget"});
});

QUnit.test('creme.widget.parseattr (with exclusion)', function(assert) {
    var attrs = creme.widget.parseattr($('<div/>'), {'attr2': ''});
    deepEqual(attrs, {});

    attrs = creme.widget.parseattr($('<div attr1="val1" attr2="val2" attr3="val3"/>'), {'attr2': ''});
    deepEqual(attrs, {attr1: 'val1', attr3: 'val3'});

    attrs = creme.widget.parseattr($('<div attr1="val1" attr2="val2" attr3="val3"/>'), ['attr1', 'attr3']);
    deepEqual(attrs, {attr2: 'val2'});
});

QUnit.test('creme.widget.parseval (parser: json, value: none)', function(assert) {
    var result = creme.widget.parseval(undefined, JSON.parse);
    equal(result, undefined);

    result = creme.widget.parseval(null, JSON.parse);
    equal(result, null);

    result = creme.widget.parseval(undefined);
    equal(result, undefined);

    result = creme.widget.parseval(null);
    equal(result, null);
});

QUnit.test('creme.widget.parseval (parser: json, value: object)', function(assert) {
    var result = creme.widget.parseval({'a': 2, 'b': 3}, JSON.parse);
    deepEqual(result, {'a': 2, 'b': 3});

    result = creme.widget.parseval({'a': 2, 'b': 3});
    deepEqual(result, {'a': 2, 'b': 3});

    result = creme.widget.parseval(15);
    deepEqual(result, 15);
});

QUnit.test('creme.widget.parseval (parser: json, value: invalid json)', function(assert) {
    var result = creme.widget.parseval('{"a":2, "b":3', JSON.parse);
    equal(result, null);

    result = creme.widget.parseval('', JSON.parse);
    equal(result, null);

    result = creme.widget.parseval('["a", 2', JSON.parse);
    equal(result, null);

    result = creme.widget.parseval("15a335", JSON.parse);
    equal(result, null);
});

QUnit.test('creme.widget.parseval (parser: json, value: valid json)', function(assert) {
    var result = creme.widget.parseval('{"a":2, "b":3}', JSON.parse);
    deepEqual(result, {'a': 2, 'b': 3});

    result = creme.widget.parseval('""', JSON.parse);
    deepEqual(result, "");

    result = creme.widget.parseval('["a", "b", 2]', JSON.parse);
    deepEqual(result, ['a', 'b', 2]);

    result = creme.widget.parseval("15335", JSON.parse);
    equal(result, 15335);
});

QUnit.test('creme.widget.parseval (parser: none, value: invalid json)', function(assert) {
    var result = creme.widget.parseval('{"a":2, "b":3}');
    equal(result, '{"a":2, "b":3}');

    result = creme.widget.parseval('["a", 2');
    equal(result, '["a", 2');
});

QUnit.test('creme.widget.cleanval (parser: default, value: none)', function(assert) {
    var result = creme.widget.cleanval(undefined);
    equal(result, undefined);

    result = creme.widget.cleanval(null);
    equal(result, null);
});

QUnit.test('creme.widget.cleanval (parser: default, value: none, default value)', function(assert) {
    var result = creme.widget.cleanval(undefined, 'default');
    equal(result, 'default');

    result = creme.widget.cleanval(null, 'default');
    equal(result, 'default');
});

QUnit.test('creme.widget.cleanval (parser: none (json), value: object)', function(assert) {
    var result = creme.widget.cleanval({'a': 2, 'b': 3});
    deepEqual(result, {'a': 2, 'b': 3});

    result = creme.widget.cleanval(['a', 2, 'b', 3]);
    deepEqual(result, ['a', 2, 'b', 3]);
});

QUnit.test('creme.widget.cleanval (parser: none (json), value: valid json)', function(assert) {
    var result = creme.widget.cleanval('{"a":2, "b":3}');
    deepEqual(result, {'a': 2, 'b': 3});

    result = creme.widget.cleanval('""');
    deepEqual(result, "");

    result = creme.widget.cleanval('["a", "b", 2]');
    deepEqual(result, ['a', 'b', 2]);

    result = creme.widget.cleanval("15335");
    equal(result, 15335);
});

QUnit.test('creme.widget.cleanval (parser: none (json), value: invalid json)', function(assert) {
    var result = creme.widget.cleanval('{"a":2, "b":3');
    equal(result, null);

    result = creme.widget.cleanval('');
    equal(result, null);

    result = creme.widget.cleanval('["a", 2');
    equal(result, null);

    result = creme.widget.cleanval("15a335");
    equal(result, null);
});

QUnit.test('creme.widget.cleanval (parser: none (json), value: invalid json, default value)', function(assert) {
    var result = creme.widget.cleanval('{"a":2, "b":3', {"a": 15});
    deepEqual(result, {"a": 15});

    result = creme.widget.cleanval('', "");
    equal(result, "");

    result = creme.widget.cleanval('["a", 2', []);
    deepEqual(result, []);

    result = creme.widget.cleanval("15a335", 0);
    equal(result, 0);
});

QUnit.test('creme.object.invoke', function(assert) {
    equal(undefined, creme.object.invoke());
    equal(undefined, creme.object.invoke(undefined));
    equal(undefined, creme.object.invoke(null));

    equal(undefined, creme.object.invoke(null, 5.2));
    equal(undefined, creme.object.invoke(458, 5.2));
    equal(undefined, creme.object.invoke('test', 5.2));

    equal(-458, creme.object.invoke(function() { return -458; }));
    equal(5.2, creme.object.invoke(function(a) { return a; }, 5.2));
    deepEqual([5.2, 12.5], creme.object.invoke(function(a, b) { return [b, a]; }, 12.5, 5.2));
});

QUnit.test('creme.object.delegate', function(assert) {
    equal(undefined, creme.object.delegate());
    equal(undefined, creme.object.delegate(undefined));
    equal(undefined, creme.object.delegate(null));

    var instance = {
        val: function() { return 12; },
        add: function(a, b) { return a + b; }
    };

    equal(undefined, creme.object.delegate(null, 'val'));
    equal(undefined, creme.object.delegate(undefined, 'val'));
    equal(undefined, creme.object.delegate(instance, 'unknown'));

    equal(12, creme.object.delegate(instance, 'val'));
    equal(7, creme.object.delegate(instance, 'add', 3, 4));
});

}(jQuery));
