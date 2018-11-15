(function($) {

QUnit.module("creme.glasspane.js", new QUnitMixin(QUnitEventMixin, {
    beforeEach: function() {
        // The "position" is needed by Chromium to set "z-index" (or remains to "auto" value).
        // No problem Firefox.
        this.anchor = $('<div style="position:relative;"></div>').appendTo($('body'));
    },

    afterEach: function() {
        this.anchor.detach();
        $('.glasspane').detach();
    }
}));

QUnit.test('creme.dialog.GlassPane (open)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();
    glasspane.on('opened', this.mockListener('opened'));
    glasspane.on('closed', this.mockListener('closed'));

    equal(false, glasspane.isOpened());
    deepEqual([], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    glasspane.open(this.anchor);

    equal(true, glasspane.isOpened());
    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.GlassPane (already opened)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();
    glasspane.on('opened', this.mockListener('opened'));
    glasspane.on('closed', this.mockListener('closed'));

    glasspane.open(this.anchor);

    equal(true, glasspane.isOpened());
    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    this.assertRaises(function() {
        glasspane.open(this.anchor);
    }, Error, 'Error: glasspane is already opened');

    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.GlassPane (anchor z-index)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();
    glasspane.on('opened', this.mockListener('opened'));
    glasspane.on('closed', this.mockListener('closed'));

    this.anchor.css('z-index', 1000);

    glasspane.open(this.anchor);
    equal(true, glasspane.isOpened());
    equal(999, glasspane.pane().css('z-index'));
});

QUnit.test('creme.dialog.GlassPane (z-index zero)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();
    glasspane.on('opened', this.mockListener('opened'));
    glasspane.on('closed', this.mockListener('closed'));

    this.anchor.css('z-index', 0);

    glasspane.open(this.anchor);
    equal(true, glasspane.isOpened());
    equal('auto', glasspane.pane().css('z-index'));
});

QUnit.test('creme.dialog.GlassPane (add/remove/toggle Class)', function(assert) {
    var glasspane = new creme.dialog.GlassPane();
    glasspane.on('opened', this.mockListener('opened'));
    glasspane.on('closed', this.mockListener('closed'));

    glasspane.open(this.anchor);
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
