QUnit.module("creme.popover.js", {
    setup: function() {
        this.resetMockCalls();
        this.anchor = $('<div></div>').appendTo($('body'));
    },

    teardown: function() {
        this.anchor.detach();
    },

    resetMockCalls: function() {
        this._eventListenerCalls = {};
    },

    mockListenerCalls: function(name) {
        if (this._eventListenerCalls[name] === undefined)
            this._eventListenerCalls[name] = [];

        return this._eventListenerCalls[name];
    },

    mockListener: function(name) {
        var self = this;
        return (function(name) {return function() {
            self.mockListenerCalls(name).push(Array.copy(arguments));
        }})(name);
    },

    assertRaises: function(block, expected, message) {
        QUnit.assert.raises(block.bind(this),
               function(error) {
                    ok(error instanceof expected, 'error is ' + expected);
                    equal(message, '' + error);
                    return true;
               });
    }
});

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
