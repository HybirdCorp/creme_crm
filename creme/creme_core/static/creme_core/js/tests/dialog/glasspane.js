(function($) {

QUnit.module("creme.glasspane.js", new QUnitMixin(QUnitEventMixin, {
    beforeEach: function() {
        // The "position" is needed by Chromium to set "z-index" (or remains to "auto" value).
        // No problem Firefox.
        this.qunitFixture().attr('style', 'position: relative;');

        this.glassPaneListeners = {
            opened: this.mockListener('opened'),
            closed: this.mockListener('closed')
        };

        this.glassPaneJqueryListeners = {
            'glasspane-opened': this.mockListener('glasspane-opened'),
            'glasspane-closed': this.mockListener('glasspane-closed')
        };
    },

    afterEach: function() {
        $('.glasspane').detach();
    }
}));

QUnit.test('creme.dialog.GlassPane (open)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();
    glasspane.on(this.glassPaneListeners);
    glasspane.pane().on(this.glassPaneJqueryListeners);

    equal(false, glasspane.isOpened());
    deepEqual([], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));
    deepEqual([], this.mockListenerJQueryCalls('glasspane-opened'));
    deepEqual([], this.mockListenerJQueryCalls('glasspane-closed'));

    glasspane.open(this.qunitFixture());

    equal(true, glasspane.isOpened());
    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));
    deepEqual([['glasspane-opened', [glasspane]]], this.mockListenerJQueryCalls('glasspane-opened'));
    deepEqual([], this.mockListenerJQueryCalls('glasspane-closed'));
});

QUnit.test('creme.dialog.GlassPane (already opened)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();
    glasspane.on(this.glassPaneListeners);
    glasspane.pane().on(this.glassPaneJqueryListeners);

    glasspane.open(this.qunitFixture());

    equal(true, glasspane.isOpened());
    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));
    deepEqual([['glasspane-opened', [glasspane]]], this.mockListenerJQueryCalls('glasspane-opened'));
    deepEqual([], this.mockListenerJQueryCalls('glasspane-closed'));

    this.assertRaises(function() {
        glasspane.open(this.qunitFixture());
    }, Error, 'Error: glasspane is already opened');

    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));
    deepEqual([['glasspane-opened', [glasspane]]], this.mockListenerJQueryCalls('glasspane-opened'));
    deepEqual([], this.mockListenerJQueryCalls('glasspane-closed'));
});

QUnit.test('creme.dialog.GlassPane (close)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();
    glasspane.on(this.glassPaneListeners);
    glasspane.pane().on(this.glassPaneJqueryListeners);

    glasspane.open(this.qunitFixture());

    equal(true, glasspane.isOpened());
    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));
    deepEqual([['glasspane-opened', [glasspane]]], this.mockListenerJQueryCalls('glasspane-opened'));
    deepEqual([], this.mockListenerJQueryCalls('glasspane-closed'));

    glasspane.close();

    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([['closed']], this.mockListenerCalls('closed'));
    deepEqual([['glasspane-opened', [glasspane]]], this.mockListenerJQueryCalls('glasspane-opened'));
    deepEqual([['glasspane-closed', [glasspane]]], this.mockListenerJQueryCalls('glasspane-closed'));

    glasspane.close().close();

    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([['closed']], this.mockListenerCalls('closed'));
    deepEqual([['glasspane-opened', [glasspane]]], this.mockListenerJQueryCalls('glasspane-opened'));
    deepEqual([['glasspane-closed', [glasspane]]], this.mockListenerJQueryCalls('glasspane-closed'));
});

QUnit.test('creme.dialog.GlassPane (toggle)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();
    glasspane.on(this.glassPaneListeners);
    glasspane.pane().on(this.glassPaneJqueryListeners);

    equal(false, glasspane.isOpened());

    glasspane.toggle(this.qunitFixture());

    equal(true, glasspane.isOpened());

    glasspane.toggle(this.qunitFixture());

    equal(false, glasspane.isOpened());
});

QUnit.skipIf(QUnit.browsers.isChrome('<85'), 'creme.dialog.GlassPane (anchor z-index) - firefox', function(assert) {
    var glasspane = new creme.dialog.GlassPane();

    this.qunitFixture().css('z-index', 1000);

    glasspane.open(this.qunitFixture());
    equal(true, glasspane.isOpened());
    equal(999, glasspane.pane().css('z-index'));
});

QUnit.skipIf(QUnit.browsers.isFirefox() || QUnit.browsers.isChrome('>=85'), 'creme.dialog.GlassPane (anchor z-index) - chrome', function(assert) {
    var glasspane = new creme.dialog.GlassPane();

    this.qunitFixture().css('z-index', 1000);

    glasspane.open(this.qunitFixture());
    equal(true, glasspane.isOpened());
    equal('auto', glasspane.pane().css('z-index'));
});

QUnit.test('creme.dialog.GlassPane (z-index zero)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();

    this.qunitFixture().css('z-index', 0);

    glasspane.open(this.qunitFixture());
    equal(true, glasspane.isOpened());
    equal('auto', glasspane.pane().css('z-index'));
});

QUnit.test('creme.dialog.GlassPane (add/remove/toggle Class)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();

    glasspane.open(this.qunitFixture());
    equal(true, glasspane.isOpened());
    equal(false, glasspane.pane().is('.custom-glass'));

    glasspane.addClass('custom-glass');
    equal(true, glasspane.pane().is('.custom-glass'));

    glasspane.removeClass('custom-glass');
    equal(false, glasspane.pane().is('.custom-glass'));

    glasspane.toggleClass('custom-glass');
    equal(true, glasspane.pane().is('.custom-glass'));
    glasspane.toggleClass('custom-glass');
    equal(false, glasspane.pane().is('.custom-glass'));
});

}(jQuery));
