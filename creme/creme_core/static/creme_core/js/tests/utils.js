/*
QUnit tests of utils.js
 */

module("creme.utils.js", {
  setup: function() {
  },
  teardown: function() {

  }
});

test('Loading:creme.utils.loading()', function() {
    expect(3);
    var dt = +new Date;
    var gen_id = 'loading'+dt;
    equal($("#"+gen_id).size(), 0);
    creme.utils.loading(gen_id, false);
    equal($("#"+gen_id).size(), 1);
    creme.utils.loading(gen_id, true);
    equal($("#"+gen_id).size(), 0);

});

test('Append params in url:creme.utils.appendInUrl()', function() {
    expect(5);
    equal(creme.utils.appendInUrl('/', ''), '/');
    equal(creme.utils.appendInUrl('/test', '?foo=1'), '/test?foo=1');
    equal(creme.utils.appendInUrl('/test?bar=0', '?foo=1'), '/test?foo=1&bar=0');
    equal(creme.utils.appendInUrl('/test?bar=0&plop=2', '?foo=1'), '/test?foo=1&bar=0&plop=2');
    equal(creme.utils.appendInUrl('/test?bar=0#id_node', '?foo=1&plop=2'), '/test?foo=1&plop=2&bar=0#id_node');
});

test('(Un)Check all boxes:creme.utils.autoCheckallState() / creme.utils.toggleCheckallState()', function() {
    expect(19);
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
test('Range:creme.utils.range()', function() {
//    expect(5);
    deepEqual(creme.utils.range(),    []);
    deepEqual(creme.utils.range(0,1), [0]);
    deepEqual(creme.utils.range(1,5), [1, 2, 3, 4]);
});
*/
