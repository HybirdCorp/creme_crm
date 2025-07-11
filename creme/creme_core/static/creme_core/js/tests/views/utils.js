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
            _mockInlineHtmlEventCalls.push(Array.from(arguments));
        };
    },
    afterEach: function() {
        QUnit.mockInlineHtmlEvent = undefined;
    },
    assertMockInlineHtmlEventCalls: function(expected) {
        this.assert.deepEqual(expected, this._mockInlineHtmlEventCalls);
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

    this.assertOpenedAlertDialog(gettext('Error!') + gettext("The page will be reloaded!"));
    assert.deepEqual([], this.mockReloadCalls());

    var done = assert.async();

    setTimeout(function() {
        self.assertClosedDialog();
        assert.deepEqual([current_url], self.mockReloadCalls());
        done();
    }, 300);
});

QUnit.test('creme.utils.showErrorNReload (close)', function(assert) {
    var current_url = window.location.href;

    this.assertClosedDialog();

    creme.utils.showErrorNReload();

    this.assertOpenedAlertDialog(gettext('Error!') + gettext("The page will be reloaded!"));
    assert.deepEqual([], this.mockReloadCalls());

    this.closeDialog();
    assert.deepEqual([current_url], this.mockReloadCalls());
});

QUnit.test('creme.utils.reload', function(assert) {
    var current_url = window.location.href;

    assert.deepEqual([], this.mockReloadCalls());

    creme.utils.reload();
    assert.deepEqual([current_url], this.mockReloadCalls());
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

    assert.deepEqual([
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
        assert.deepEqual(faker.calls(), []);

        creme.utils.scrollBack(null, 20);
        assert.deepEqual(faker.calls(), []);

        assert.equal(creme.utils.scrollBack(50));
        assert.deepEqual(faker.calls(), []);

        assert.equal(creme.utils.scrollBack(12, 200));
        assert.deepEqual(faker.calls(), [
            [{scrollTop: 12}, 200],
            [{scrollTop: 12}, 200]
        ]);
    });
});

QUnit.test('creme.utils.clickOnce', function(assert) {
    var once = $('<a onclick="creme.utils.clickOnce(this, QUnit.mockInlineHtmlEvent, \'once call\', 12)"></a>');
    var normal = $('<a onclick="QUnit.mockInlineHtmlEvent(\'normal call\', 13)"></a>');

    assert.equal(false, once.is('.clickonce'));
    assert.equal(false, normal.is('.clickonce'));
    this.assertMockInlineHtmlEventCalls([]);

    once.trigger('click');
    normal.trigger('click');

    assert.equal(true, once.is('.clickonce'));
    assert.equal(false, normal.is('.clickonce'));
    this.assertMockInlineHtmlEventCalls([
        ['once call', 12],
        ['normal call', 13]
    ]);

    once.trigger('click');
    normal.trigger('click');

    assert.equal(true, once.is('.clickonce'));
    assert.equal(false, normal.is('.clickonce'));
    this.assertMockInlineHtmlEventCalls([
        ['once call', 12],
        ['normal call', 13],
        ['normal call', 13]
    ]);
});

}(jQuery));
