QUnit.module("creme.utils.js", {
    setup: function() {},
    teardown: function() {}
});

QUnit.test('creme.utils.JSON.encode (null)', function(assert) {
    var codec = new creme.utils.JSON();

    equal("null", codec.encode(null));
});

QUnit.test('creme.utils.JSON.encode', function(assert) {
    var codec = new creme.utils.JSON();

    equal(codec.encode('test'), '"test"');
    equal(codec.encode(12), '12');
    equal(codec.encode(['a', 12, 'c', null, undefined]), '["a",12,"c",null,null]');
    equal(codec.encode({'a': ['a', 'b', 150],
                        'b': 'test',
                        'c': 12
                       }), '{"a":["a","b",150],"b":"test","c":12}');

    var encoder = creme.utils.JSON.encoder();

    equal(encoder('test'), '"test"');
    equal(encoder(12), '12');
    equal(encoder(['a', 12, 'c', null, undefined]), '["a",12,"c",null,null]');
    equal(encoder({'a': ['a', 'b', 150],
                   'b': 'test',
                   'c': 12
                  }), '{"a":["a","b",150],"b":"test","c":12}');
});

QUnit.test('creme.utils.JSON.decode (null)', function(assert) {
    var codec = new creme.utils.JSON();

    QUnit.assert.raises(function() {codec.decode(null);});
});

QUnit.test('creme.utils.JSON.decode (invalid)', function(assert) {
    var codec = new creme.utils.JSON();

    QUnit.assert.raises(function() {codec.decode('{"a\':1}');});
    QUnit.assert.raises(function() {codec.decode('{"a":1,}');});
    QUnit.assert.raises(function() {codec.decode('{a:1}');});

    var decoder = creme.utils.JSON.decoder();

    QUnit.assert.raises(function() {decoder('{"a\':1}');});
    QUnit.assert.raises(function() {decoder('{"a":1,}');});
    QUnit.assert.raises(function() {decoder('{a:1}');});
});

QUnit.test('creme.utils.JSON.decode (invalid or null, default)', function(assert) {
    var codec = new creme.utils.JSON();

    equal(codec.decode('{"a\':1}', 'fail'), 'fail');
    equal(codec.decode('{"a":1,}', 'fail'), 'fail');
    equal(codec.decode('{a:1}', 'fail'), 'fail');
    equal(codec.decode(null, 'fail'), 'fail');

    var decoder = creme.utils.JSON.decoder('default');

    equal(decoder('{"a\':1}'), 'default');
    equal(decoder('{"a":1,}'), 'default');
    equal(decoder('{a:1}'), 'default');
    equal(decoder(null), 'default');

    equal(decoder('{"a\':1}', 'fail'), 'fail');
    equal(decoder('{"a":1,}', 'fail'), 'fail');
    equal(decoder('{a:1}', 'fail'), 'fail');
    equal(decoder(null, 'fail'), 'fail');
});

QUnit.test('creme.utils.JSON.decode (valid)', function(assert) {
    var codec = new creme.utils.JSON();

    deepEqual(codec.decode('{"a":1, "b":true, "c":[1, 2, 3]}'), {a: 1, b: true, c: [1, 2, 3]});

    var decoder = creme.utils.JSON.decoder();

    deepEqual(decoder('{"a":1, "b":true, "c":[1, 2, 3]}'), {a: 1, b: true, c: [1, 2, 3]});
});

QUnit.test('creme.utils.JSON.clean', function(assert) {
    var clean = creme.utils.JSON.clean;

    QUnit.assert.raises(function() {clean('{"a\':1}');});
    equal(clean('{"a\':1}', 'default'), 'default');

    equal(clean(null), null);
    equal(clean(null, 'default'), null);

    deepEqual(clean('{"a":1}'), {a: 1});
    deepEqual(clean({a: 1}), {a: 1});
});

QUnit.test('creme.utils.comparator (simple)', function(assert) {
    var compare = creme.utils.comparator();

    deepEqual(compare, creme.utils.compareTo);

    equal(0, compare(12, 12));
    equal(0, compare(4.57, 4.57));
    equal(0, compare('test', 'test'));

    equal(-1, compare(12, 13));
    equal(-1, compare(4.57, 5.57));
    equal(-1, compare('da test', 'test'));

    equal(1, compare(13, 12));
    equal(1, compare(5.57, 4.57));
    equal(1, compare('test', 'da test'));
});

QUnit.test('creme.utils.comparator (key)', function(assert) {
    var compare = creme.utils.comparator('value');

    equal(0, compare({value: 12}, {value: 12}));
    equal(0, compare({value: 4.57}, {value: 4.57}));
    equal(0, compare({value: 'test'}, {value: 'test'}));

    equal(-1, compare({value: 12}, {value: 13}));
    equal(-1, compare({value: 4.57}, {value: 5.57}));
    equal(-1, compare({value: 'da test'}, {value: 'test'}));

    equal(1, compare({value: 13}, {value: 12}));
    equal(1, compare({value: 5.57}, {value: 4.57}));
    equal(1, compare({value: 'test'}, {value: 'da test'}));
});

QUnit.test('creme.utils.comparator (multiple keys)', function(assert) {
    var compare = creme.utils.comparator('value', 'index');

    equal(0, compare({value: 12, index: 0}, {value: 12, index: 0}));

    equal(1, compare({value: 12, index: 1}, {value: 12, index: 0}));
    equal(1, compare({value: 13, index: 0}, {value: 12, index: 1}));

    equal(-1, compare({value: 12, index: 0}, {value: 12, index: 1}));
    equal(-1, compare({value: 12, index: 1}, {value: 13, index: 0}));
});

QUnit.test('creme.utils.isHTMLDataType', function(assert) {
    equal(creme.utils.isHTMLDataType('html'), true);
    equal(creme.utils.isHTMLDataType('text/html'), true);
    equal(creme.utils.isHTMLDataType('HTML'), true);
    equal(creme.utils.isHTMLDataType('json'), false);
});

/**
 * Old creme creme_core/unit.js unit tests.
 */

QUnit.test('creme.utils.appendInUrl', function(assert) {
    equal(creme.utils.appendInUrl('/', ''), '/');
    equal(creme.utils.appendInUrl('/test', '?foo=1'), '/test?foo=1');
    equal(creme.utils.appendInUrl('/test?bar=0', '?foo=1'), '/test?foo=1&bar=0');
    equal(creme.utils.appendInUrl('/test?bar=0&plop=2', '?foo=1'), '/test?foo=1&bar=0&plop=2');
    equal(creme.utils.appendInUrl('/test?bar=0#id_node', '?foo=1&plop=2'), '/test?foo=1&plop=2&bar=0#id_node');
});

QUnit.test('creme.utils.autoCheckallState / creme.utils.toggleCheckallState', function(assert) {
    var _checkbox            = '<input type="checkbox" checked="checked"/>';
    var _all_selector        = "[name=check_all]";
    var _checkboxes_selector = "[name=check_one]"

    var $check_all = $(_checkbox).attr('name', 'check_all').click(function(){creme.utils.toggleCheckallState(_all_selector, _checkboxes_selector);});
    var $check1 = $(_checkbox).attr('name', 'check_one').click(function(){creme.utils.autoCheckallState(this, _all_selector, _checkboxes_selector)});
    var $check2 = $(_checkbox).attr('name', 'check_one').click(function(){creme.utils.autoCheckallState(this, _all_selector, _checkboxes_selector)});

    $(document.body).append($check_all).append($check1).append($check2);
    equal($(_all_selector).size(), 1);
    equal($(_checkboxes_selector).size(), 2);

    ok($check1.is(':checked'));
    ok($check2.is(':checked'));
    ok($check_all.is(':checked'));

    $check1.get(0).click(true);//Real DOM click with bubbling
    ok(!$check1.is(':checked'), 'Is $check1 checked?');
    equal($check_all.is(':checked'), false, 'Is $check_all checked?');

    $check1.get(0).click(true);
    ok($check1.is(':checked'), 'Is $check1 checked?');
    ok($check_all.is(':checked'));

    $check1.get(0).click(true);
    $check2.get(0).click(true);
    ok(!$check_all.is(':checked'));

    $check1.get(0).click(true);
    $check2.get(0).click(true);
    ok($check_all.is(':checked'));

    ok($check1.is(':checked'));
    ok($check2.is(':checked'));
    ok($check_all.is(':checked'));
    $check_all.get(0).click(true);
    ok(!$check1.is(':checked'));
    ok(!$check2.is(':checked'));
    ok(!$check_all.is(':checked'));

    $check_all.remove(); $check1.remove(); $check2.remove();
    equal($(_all_selector).size(), 0);
    equal($(_checkboxes_selector).size(), 0);
});

/*
QUnit.test('creme.utils.loading', function(assert) {
    equal($('.ui-creme-overlay').size(), 0);
    equal($('.ui-creme-overlay.overlay-active').size(), 0);

    creme.utils.loading('', false);
    equal($('.ui-creme-overlay').size(), 1);
    equal($('.ui-creme-overlay.overlay-active').size(), 1, 'overlay shown');

    creme.utils.loading('', true);

    equal($('.ui-creme-overlay').size(), 1);
    equal($('.ui-creme-overlay.overlay-active').size(), 1, 'overlay hidden');
});
*/