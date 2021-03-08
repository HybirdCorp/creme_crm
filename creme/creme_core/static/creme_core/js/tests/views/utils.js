/* globals FunctionFaker */

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
    deepEqual([], this.mockReloadCalls());

    stop(1);

    setTimeout(function() {
        self.assertClosedDialog();
        deepEqual([current_url], self.mockReloadCalls());
        start();
    }, 300);
});

QUnit.test('creme.utils.showErrorNReload (close)', function(assert) {
    var current_url = window.location.href;

    this.assertClosedDialog();

    creme.utils.showErrorNReload();

    this.assertOpenedAlertDialog(gettext('Error !') + gettext("The page will be reload !"));
    deepEqual([], this.mockReloadCalls());

    this.closeDialog();
    deepEqual([current_url], this.mockReloadCalls());
});

QUnit.test('creme.utils.reload', function(assert) {
    var current_url = window.location.href;

    deepEqual([], this.mockReloadCalls());

    creme.utils.reload();
    deepEqual([current_url], this.mockReloadCalls());
});

QUnit.test('creme.utils.goTo', function(assert) {
    creme.utils.goTo('/test');
    creme.utils.goTo('/test', {});
    creme.utils.goTo('/test', {foo: 1});
    creme.utils.goTo('/test?foo=1', {bar: [2, 3]});
    creme.utils.goTo('/test?foo=1', {foo: 5, bar: [2, 3]});
    creme.utils.goTo('/test?bar=7&bar=8&bar=9', {foo: 1, bar: [2, 3]});
    creme.utils.goTo('/test?bar=0#id_node', {foo: 1, plop: 2});
    creme.utils.goTo('/test', 'a=1&b=2&b=3');
    creme.utils.goTo('/test?bar=0#id_node', 'foo=1&bar=2&bar=3');

    deepEqual([
        '/test',
        '/test',
        '/test?foo=1',
        '/test?foo=1&bar=2&bar=3',
        '/test?foo=5&bar=2&bar=3',
        '/test?bar=2&bar=3&foo=1',
        '/test?bar=0&foo=1&plop=2#id_node',
        '/test?a=1&b=2&b=3',
        '/test?bar=2&bar=3&foo=1#id_node'
    ], this.mockRedirectCalls());
});

QUnit.test('creme.utils.scrollBack', function(assert) {
    new FunctionFaker({
        instance: $.fn,
        method: 'animate'
    }).with(function(faker) {
        creme.utils.scrollBack(null);
        deepEqual(faker.calls(), []);

        creme.utils.scrollBack(null, 20);
        deepEqual(faker.calls(), []);

        equal(creme.utils.scrollBack(50));
        deepEqual(faker.calls(), []);

        equal(creme.utils.scrollBack(12, 200));
        deepEqual(faker.calls(), [
            [{scrollTop: 12}, 200],
            [{scrollTop: 12}, 200]
        ]);
    });
});

/*
QUnit.test('creme.utils.appendInUrl', function(assert) {
    equal(creme.utils.appendInUrl('/', ''), '/');
    equal(creme.utils.appendInUrl('/test', '?foo=1'), '/test?foo=1');
    equal(creme.utils.appendInUrl('/test?bar=0', '?foo=1'), '/test?foo=1&bar=0');
    equal(creme.utils.appendInUrl('/test?bar=0&plop=2', '?foo=1'), '/test?foo=1&bar=0&plop=2');
    equal(creme.utils.appendInUrl('/test?bar=0#id_node', '?foo=1&plop=2'), '/test?foo=1&plop=2&bar=0#id_node');
});
*/

QUnit.test('creme.utils.clickOnce', function(assert) {
    var once = $('<a onclick="creme.utils.clickOnce(this, QUnit.mockInlineHtmlEvent, \'once call\', 12)"></a>');
    var normal = $('<a onclick="QUnit.mockInlineHtmlEvent(\'normal call\', 13)"></a>');

    equal(false, once.is('.clickonce'));
    equal(false, normal.is('.clickonce'));
    this.assertMockInlineHtmlEventCalls([]);

    once.trigger('click');
    normal.trigger('click');

    equal(true, once.is('.clickonce'));
    equal(false, normal.is('.clickonce'));
    this.assertMockInlineHtmlEventCalls([
        ['once call', 12],
        ['normal call', 13]
    ]);

    once.trigger('click');
    normal.trigger('click');

    equal(true, once.is('.clickonce'));
    equal(false, normal.is('.clickonce'));
    this.assertMockInlineHtmlEventCalls([
        ['once call', 12],
        ['normal call', 13],
        ['normal call', 13]
    ]);
});

}(jQuery));
