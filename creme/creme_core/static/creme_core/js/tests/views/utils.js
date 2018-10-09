/* globals setTimeout */

(function($) {

/**
 * Old creme creme_core/unit.js unit tests.
 */

QUnit.module("creme.core.utils.js", new QUnitMixin(QUnitAjaxMixin,
                                                   QUnitDialogMixin, {
    beforeEach: function() {
        var _mockInlineHtmlEventCalls = this._mockInlineHtmlEventCalls = [];

        QUnit.mockInlineHtmlEvent = function() {
            _mockInlineHtmlEventCalls.push(Array.copy(arguments));
        };
    },
    afterEach: function() {
        QUnit.mockInlineHtmlEvent = undefined;
    },
    assertMockInlineHtmlEventCalls: function(expected) {
        deepEqual(expected, this._mockInlineHtmlEventCalls);
    },
    mockRedirectCalls: function() {
        return this._redirectCalls;
    }
}));

QUnit.test('creme.utils.showErrorNReload', function(assert) {
    var self = this;
    var current_url = window.location.href;

    this.assertClosedDialog();

    creme.utils.showErrorNReload(150);

    this.assertOpenedAlertDialog(gettext('Error !') + gettext("The page will be reload !"));
    deepEqual([], this.mockRedirectCalls());

    stop(1);

    setTimeout(function() {
        self.assertClosedDialog();
        deepEqual([current_url], self.mockRedirectCalls());
        start();
    }, 300);
});

QUnit.test('creme.utils.showErrorNReload (close)', function(assert) {
    var current_url = window.location.href;

    this.assertClosedDialog();

    creme.utils.showErrorNReload();

    this.assertOpenedAlertDialog(gettext('Error !') + gettext("The page will be reload !"));
    deepEqual([], this.mockRedirectCalls());

    this.closeDialog();
    deepEqual([current_url], this.mockRedirectCalls());
});

QUnit.test('creme.utils.reload', function(assert) {
    var current_url = window.location.href;

    deepEqual([], this.mockRedirectCalls());

    creme.utils.reload();
    deepEqual([current_url], this.mockRedirectCalls());
});

QUnit.test('creme.utils.appendInUrl', function(assert) {
    equal(creme.utils.appendInUrl('/', ''), '/');
    equal(creme.utils.appendInUrl('/test', '?foo=1'), '/test?foo=1');
    equal(creme.utils.appendInUrl('/test?bar=0', '?foo=1'), '/test?foo=1&bar=0');
    equal(creme.utils.appendInUrl('/test?bar=0&plop=2', '?foo=1'), '/test?foo=1&bar=0&plop=2');
    equal(creme.utils.appendInUrl('/test?bar=0#id_node', '?foo=1&plop=2'), '/test?foo=1&plop=2&bar=0#id_node');
});

/* REMOVED
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
*/

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

}(jQuery));
