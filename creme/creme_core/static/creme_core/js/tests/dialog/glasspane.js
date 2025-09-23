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

    assert.equal(false, glasspane.isOpened());
    assert.deepEqual([], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));
    assert.deepEqual([], this.mockListenerJQueryCalls('glasspane-opened'));
    assert.deepEqual([], this.mockListenerJQueryCalls('glasspane-closed'));

    glasspane.open(this.qunitFixture());

    assert.equal(true, glasspane.isOpened());
    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));
    assert.deepEqual([['glasspane-opened', [glasspane]]], this.mockListenerJQueryCalls('glasspane-opened'));
    assert.deepEqual([], this.mockListenerJQueryCalls('glasspane-closed'));
});

QUnit.test('creme.dialog.GlassPane (already opened)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();
    glasspane.on(this.glassPaneListeners);
    glasspane.pane().on(this.glassPaneJqueryListeners);

    glasspane.open(this.qunitFixture());

    assert.equal(true, glasspane.isOpened());
    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));
    assert.deepEqual([['glasspane-opened', [glasspane]]], this.mockListenerJQueryCalls('glasspane-opened'));
    assert.deepEqual([], this.mockListenerJQueryCalls('glasspane-closed'));

    this.assertRaises(function() {
        glasspane.open(this.qunitFixture());
    }, Error, 'Error: glasspane is already opened');

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));
    assert.deepEqual([['glasspane-opened', [glasspane]]], this.mockListenerJQueryCalls('glasspane-opened'));
    assert.deepEqual([], this.mockListenerJQueryCalls('glasspane-closed'));
});

QUnit.test('creme.dialog.GlassPane (close)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();
    glasspane.on(this.glassPaneListeners);
    glasspane.pane().on(this.glassPaneJqueryListeners);

    glasspane.open(this.qunitFixture());

    assert.equal(true, glasspane.isOpened());
    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));
    assert.deepEqual([['glasspane-opened', [glasspane]]], this.mockListenerJQueryCalls('glasspane-opened'));
    assert.deepEqual([], this.mockListenerJQueryCalls('glasspane-closed'));

    glasspane.close();

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([['closed']], this.mockListenerCalls('closed'));
    assert.deepEqual([['glasspane-opened', [glasspane]]], this.mockListenerJQueryCalls('glasspane-opened'));
    assert.deepEqual([['glasspane-closed', [glasspane]]], this.mockListenerJQueryCalls('glasspane-closed'));

    glasspane.close().close();

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([['closed']], this.mockListenerCalls('closed'));
    assert.deepEqual([['glasspane-opened', [glasspane]]], this.mockListenerJQueryCalls('glasspane-opened'));
    assert.deepEqual([['glasspane-closed', [glasspane]]], this.mockListenerJQueryCalls('glasspane-closed'));
});

QUnit.test('creme.dialog.GlassPane (toggle)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();
    glasspane.on(this.glassPaneListeners);
    glasspane.pane().on(this.glassPaneJqueryListeners);

    assert.equal(false, glasspane.isOpened());

    glasspane.toggle(this.qunitFixture());

    assert.equal(true, glasspane.isOpened());

    glasspane.toggle(this.qunitFixture());

    assert.equal(false, glasspane.isOpened());
});

QUnit.skipIf(!QUnit.browsers.isChrome('>=85'), 'creme.dialog.GlassPane (anchor z-index) - chrome >= 85', function(assert) {
    var glasspane = new creme.dialog.GlassPane();

    this.qunitFixture().css('z-index', 1000);

    glasspane.open(this.qunitFixture());
    assert.equal(true, glasspane.isOpened());
    assert.equal(999, glasspane.pane().css('z-index'));
});

QUnit.skipIf(!QUnit.browsers.isFirefox('>=143'), 'creme.dialog.GlassPane (anchor z-index) - firefox >= 143', function(assert) {
    var glasspane = new creme.dialog.GlassPane();

    this.qunitFixture().css('z-index', 1000);

    glasspane.open(this.qunitFixture());
    assert.equal(true, glasspane.isOpened());
    assert.equal(999, glasspane.pane().css('z-index'));
});

QUnit.skipIf(!QUnit.browsers.isFirefox('<143'), 'creme.dialog.GlassPane (anchor z-index) - firefox < 143', function(assert) {
    var glasspane = new creme.dialog.GlassPane();

    this.qunitFixture().css('z-index', 1000);

    glasspane.open(this.qunitFixture());
    assert.equal(true, glasspane.isOpened());
    assert.equal('auto', glasspane.pane().css('z-index'));
});

QUnit.skipIf(!QUnit.browsers.isChrome('<85'), 'creme.dialog.GlassPane (anchor z-index) - chrome < 143', function(assert) {
    var glasspane = new creme.dialog.GlassPane();

    this.qunitFixture().css('z-index', 1000);

    glasspane.open(this.qunitFixture());
    assert.equal(true, glasspane.isOpened());
    assert.equal('auto', glasspane.pane().css('z-index'));
});

QUnit.test('creme.dialog.GlassPane (z-index zero)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();

    this.qunitFixture().css('z-index', 0);

    glasspane.open(this.qunitFixture());
    assert.equal(true, glasspane.isOpened());
    assert.equal('auto', glasspane.pane().css('z-index'));
});

QUnit.test('creme.dialog.GlassPane (add/remove/toggle Class)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();

    glasspane.open(this.qunitFixture());
    assert.equal(true, glasspane.isOpened());
    assert.equal(false, glasspane.pane().is('.custom-glass'));

    glasspane.addClass('custom-glass');
    assert.equal(true, glasspane.pane().is('.custom-glass'));

    glasspane.removeClass('custom-glass');
    assert.equal(false, glasspane.pane().is('.custom-glass'));

    glasspane.toggleClass('custom-glass');
    assert.equal(true, glasspane.pane().is('.custom-glass'));
    glasspane.toggleClass('custom-glass');
    assert.equal(false, glasspane.pane().is('.custom-glass'));
});

}(jQuery));
