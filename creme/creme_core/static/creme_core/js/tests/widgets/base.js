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

QUnit.test('creme.widget.template (template:no keys)', function(assert) {
    var result = creme.widget.template('');
    equal(result, '');

    result = creme.widget.template('template without key');
    equal(result, 'template without key');

    result = creme.widget.template('template without key', {});
    equal(result, 'template without key');

    result = creme.widget.template('template without key', {'key1': 'value1', 'key2': 'value2'});
    equal(result, 'template without key');
});

QUnit.test('creme.widget.template (template:keys, values: in template)', function(assert) {
    var result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}');
    equal(result, 'template with key1=${key1} and key2=${key2}, ${key1}');

    result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}', {key1: 'value1'});
    equal(result, 'template with key1=value1 and key2=${key2}, value1');

    result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}', {key2: 'value2'});
    equal(result, 'template with key1=${key1} and key2=value2, ${key1}');

    result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}', {key1: 'value1', key2: 'value2'});
    equal(result, 'template with key1=value1 and key2=value2, value1');

    result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}', {key1: 'value1', key2: undefined});
    equal(result, 'template with key1=value1 and key2=${key2}, value1');
});

QUnit.test('creme.widget.template (template:keys, values: not in template)', function(assert) {
    var result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}', {key3: 'value3'});
    equal(result, 'template with key1=${key1} and key2=${key2}, ${key1}');

    result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}', {key1: 'value1', key3: 'value3'});
    equal(result, 'template with key1=value1 and key2=${key2}, value1');
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

QUnit.test('creme.object.deferred (finished)', function(assert) {
    var element = $('<div/>');
    var result = [];

    var deferred = creme.object.deferred_start(element, 'overlay', function() { result.push('done'); }, 400);
    deepEqual(element.data('deferred__overlay'), deferred);
    deepEqual(result, []);

    stop(2);

    setTimeout(function() {
        deepEqual(element.data('deferred__overlay'), deferred);
        deepEqual(result, []);
        start();
    }, 90);

    setTimeout(function() {
        equal(element.data('deferred__overlay'), undefined);
        deepEqual(result, ['done']);
        start();
    }, 600);
});

QUnit.test('creme.object.deferred (canceled)', function(assert) {
    var element = $('<div/>');
    var result = [];

    var deferred = creme.object.deferred_start(element, 'overlay', function() { result.push('done'); }, 200);
    deepEqual(deferred, element.data('deferred__overlay'));

    stop(2);

    setTimeout(function() {
        deepEqual(deferred, element.data('deferred__overlay'));
        deepEqual(result, []);
        deepEqual(deferred, creme.object.deferred_cancel(element, 'overlay'));

        equal(element.data('deferred__overlay'), undefined);
        deepEqual(result, []);
        start();
    }, 90);

    setTimeout(function() {
        equal(element.data('deferred__overlay'), undefined);
        deepEqual(result, []);
        start();
    }, 300);
});

QUnit.test('creme.object.deferred (restarted)', function(assert) {
    var element = $('<div/>');
    var result = [];

    var deferred = creme.object.deferred_start(element, 'overlay', function() { result.push('done'); }, 200);
    deepEqual(deferred, element.data('deferred__overlay'));

    stop(3);

    setTimeout(function() {
        deepEqual(deferred, element.data('deferred__overlay'));
        deepEqual(result, []);
        notDeepEqual(creme.object.deferred_start(element, 'overlay', function() { result.push('done restarted'); }, 500), deferred);

        notEqual(element.data('deferred__overlay'), undefined, 'replaced');
        deepEqual(result, []);
        start();
    }, 90);

    setTimeout(function() {
        notEqual(element.data('deferred__overlay'), undefined, 'replaced after first elapsed');
        deepEqual(result, []);
        start();
    }, 300);

    setTimeout(function() {
        equal(element.data('deferred__overlay'), undefined, 'replaced done');
        deepEqual(result, ['done restarted']);
        start();
    }, 700);
});

QUnit.test('creme.object.build_callback (invalid script)', function(assert) {
    QUnit.assert.raises(function() { creme.object.build_callback('...'); });
    QUnit.assert.raises(function() { creme.object.build_callback('{', ['arg1', 'arg2']); });
});

QUnit.test('creme.object.build_callback (function)', function(assert) {
    var cb = function() { return 12; };
    equal(cb, creme.object.build_callback(cb));
    equal(cb, creme.object.build_callback(cb, ['arg1', 'arg2']));
});

QUnit.test('creme.object.build_callback (valid script, no parameter)', function(assert) {
    var cb = creme.object.build_callback('12');
    equal(typeof cb, 'function');
    equal(cb(), 12);

    cb = creme.object.build_callback('return 15');
    equal(typeof cb, 'function');
    equal(cb(), 15);
});

QUnit.test('creme.object.build_callback (valid script, parameters)', function(assert) {
    var cb = creme.object.build_callback('arg1 * arg2', ['arg1', 'arg2']);
    equal(typeof cb, 'function');
    equal(cb(0, 0), 0);
    equal(cb(5, 2), 5 * 2);
    equal(cb(4.56, 2), 4.56 * 2);

    cb = creme.object.build_callback('if (arg1 > arg2) {return arg1;} else {return arg2;}', ['arg1', 'arg2']);
    equal(typeof cb, 'function');
    equal(cb(0, 0), 0);
    equal(cb(5, 2), 5);
    equal(cb(4.56, 445), 445);
});

}(jQuery));
