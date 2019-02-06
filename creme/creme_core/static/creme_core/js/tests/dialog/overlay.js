(function($) {

QUnit.module("creme.overlay.js", new QUnitMixin(QUnitEventMixin,
                                                QUnitDialogMixin, {
    beforeEach: function() {
        // The "position" is needed by Chromium to set "z-index" (or remains to "auto" value).
        // No problem Firefox.
        this.anchor = $('<div style="position:relative;"></div>').appendTo($('body'));
    },

    afterEach: function() {
        this.anchor.detach();
    }
}));

QUnit.test('creme.dialog.Overlay', function(assert) {
    var overlay = new creme.dialog.Overlay();

    equal(false, overlay.visible());
    equal(false, overlay.isBound());
    equal(undefined, overlay.state());
    equal(undefined, overlay.target());

    this.equalHtml('', overlay.content());
});

QUnit.test('creme.dialog.Overlay.bind', function(assert) {
    var overlay = new creme.dialog.Overlay();

    overlay.bind(this.anchor);

    equal(false, overlay.visible());
    equal(true, overlay.isBound());
    equal(this.anchor, overlay.target());

    this.assertRaises(function() {
        overlay.bind($('<div>'));
    }, Error, 'Error: Overlay is already bound.');
});

QUnit.test('creme.dialog.Overlay.unbind', function(assert) {
    var overlay = new creme.dialog.Overlay();

    overlay.bind(this.anchor);

    equal(false, overlay.visible());
    equal(true, overlay.isBound());
    equal(this.anchor, overlay.target());

    overlay.unbind();

    equal(false, overlay.visible());
    equal(false, overlay.isBound());
    equal(undefined, overlay.target());

    this.assertRaises(function() {
        overlay.unbind();
    }, Error, 'Error: Overlay is not bound.');
});

QUnit.test('creme.dialog.Overlay (visible)', function(assert) {
    var overlay = new creme.dialog.Overlay();

    overlay.bind(this.anchor);

    equal(false, overlay.visible())
    equal(0, this.anchor.find('.ui-creme-overlay').length)

    overlay.update(true);

    equal(true, overlay.visible())
    equal(1, this.anchor.find('.ui-creme-overlay').length)

    overlay.update(false);

    equal(false, overlay.visible())
    equal(0, this.anchor.find('.ui-creme-overlay').length)
});

QUnit.test('creme.dialog.Overlay (add|remove|toggleClasses)', function(assert) {
    var overlay = new creme.dialog.Overlay();

    overlay.bind(this.anchor).update(true);

    equal(true, overlay.visible())

    var overlayTag = this.anchor.find('.ui-creme-overlay');

    overlay.addClass('style-A');
    equal(true, overlayTag.is('.style-A'));
    equal(false, overlayTag.is('.style-B'));

    overlay.toggleClass('style-A')
    equal(false, overlayTag.is('.style-A'));
    equal(false, overlayTag.is('.style-B'));

    overlay.toggleClass('style-A style-B');
    equal(true, overlayTag.is('.style-A'));
    equal(true, overlayTag.is('.style-B'));

    overlay.removeClass('style-A');
    equal(false, overlayTag.is('.style-A'));
    equal(true, overlayTag.is('.style-B'));
});

}(jQuery));
