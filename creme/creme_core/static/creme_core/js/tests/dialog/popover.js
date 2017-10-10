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
        QUnit.assert.raises(block,
               function(error) {
                    ok(error instanceof expected, 'error is ' + expected);
                    equal(message, '' + error);
                    return true;
               });
    },

    assertPopoverDirection: function(popover, direction) {
        ok(popover._dialog.is('.popover.' + direction), 'popover direction is ' + direction);
        equal(direction, popover.direction());
    },

    assertPopoverTitle: function(popover, title) {
        equal(title, popover.title().html(), 'popover title');
    },

    assertPopoverContent: function(popover, content) {
        equal(content, popover.content().html(), 'popover content');
    }
});

QUnit.test('creme.dialog.Popover (open)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.anchor;

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    equal(false, popover.isOpened());
    deepEqual([], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    popover.open(anchor);
    equal(true, popover.isOpened());
    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    var other = $('<span/>');

    this.assertRaises(function() {
        popover.open(other);
    }, Error, 'Error: popover is already opened');
});

QUnit.test('creme.dialog.Popover (toggle)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.anchor;

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    equal(false, popover.isOpened());
    deepEqual([], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    popover.toggle(anchor);
    equal(true, popover.isOpened());
    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    popover.toggle(anchor);
    equal(false, popover.isOpened());
    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([['closed']], this.mockListenerCalls('closed'));

    popover.toggle(anchor);
    equal(true, popover.isOpened());
    deepEqual([['opened'], ['opened']], this.mockListenerCalls('opened'));
    deepEqual([['closed']], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Popover (title)', function(assert) {
    var popover = new creme.dialog.Popover({title: 'A'});
    var anchor = this.anchor;

    popover.open(anchor);
    this.assertPopoverTitle(popover, 'A');

    popover.title('B');
    this.assertPopoverTitle(popover, 'B');
});

QUnit.test('creme.dialog.Popover (direction)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = $('<div></div>').appendTo($('body'));

    popover.open(anchor);
    this.assertPopoverDirection(popover, 'bottom');

    popover.close();
    popover.open(anchor, {direction: 'top'});
    this.assertPopoverDirection(popover, 'top');

    popover.direction('right');
    this.assertPopoverDirection(popover, 'right');

    popover.direction('left');
    this.assertPopoverDirection(popover, 'left');
    
    this.assertRaises(function() {
        popover.direction('elsewhere');
    }, Error, 'Error: invalid popover direction elsewhere');
});

QUnit.test('creme.dialog.Popover (addClass + direction)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = $('<div></div>').appendTo($('body'));

    popover.addClass('special-popover')
    popover.open(anchor);

    this.assertPopoverDirection(popover, 'bottom');
    ok(popover._dialog.is('.special-popover'));

    popover.close();
    popover.open(anchor, {direction: 'top'});

    this.assertPopoverDirection(popover, 'top');
    ok(popover._dialog.is('.special-popover'));

    popover.direction('right');

    this.assertPopoverDirection(popover, 'right');
    ok(popover._dialog.is('.special-popover'));
});

QUnit.test('creme.dialog.Popover (remove/toggleClass)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = $('<div></div>').appendTo($('body'));

    popover.addClass('special-popover')
    popover.open(anchor);

    ok(popover._dialog.is('.special-popover'));

    popover.removeClass('special-popover');
    equal(false, popover._dialog.is('.special-popover'));

    popover.toggleClass('special-popover', true);
    ok(popover._dialog.is('.special-popover'));

    popover.toggleClass('special-popover', false);
    equal(false, popover._dialog.is('.special-popover'));
});

QUnit.test('creme.dialog.Popover (fill)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.anchor;

    popover.open(anchor);
    popover.fill('<p>this is another sample</p>');
    this.assertPopoverContent(popover, '<p>this is another sample</p>');

    popover.fill($('<div>element sample</div>'));
    this.assertPopoverContent(popover, '<div>element sample</div>');
});

QUnit.test('creme.dialog.Popover (fill)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.anchor;

    popover.fill('<p>this is a sample</p>');
    popover.open(anchor);
    this.assertPopoverContent(popover, '<p>this is a sample</p>');

    popover.fill('<p>this is another sample</p>');
    this.assertPopoverContent(popover, '<p>this is another sample</p>');

    popover.fill($('<div>element sample</div>'));
    this.assertPopoverContent(popover, '<div>element sample</div>');
});

QUnit.test('creme.dialog.Popover (fill, function)', function(assert) {
    var popover = new creme.dialog.Popover({title: 'A'});
    var anchor = $('<div></div>').appendTo($('body'));

    popover.open(anchor);
    popover.fill(function(options) {
                return '<p>content for ${title}</p>'.template(options);
            });

    this.assertPopoverContent(popover, '<p>content for A</p>');
});

QUnit.test('creme.dialog.Popover (closeIfOut)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.anchor;

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    ok(popover.options().closeIfOut);

    popover.open(anchor);
    equal(true, popover.isOpened());

    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    popover._glasspane.pane().trigger('mousedown');
    equal(false, popover.isOpened());

    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([['closed']], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Popover (trigger modal close)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.anchor;

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    ok(popover.options().closeIfOut);

    popover.open(anchor);
    equal(true, popover.isOpened());

    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    $('.popover').trigger('modal-close');
    equal(false, popover.isOpened());

    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([['closed']], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Popover (modal)', function(assert) {
    var popover = new creme.dialog.Popover();
    var popover2 = new creme.dialog.Popover();

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    popover2.on('opened', this.mockListener('opened2'));
    popover2.on('closed', this.mockListener('closed2'));

    var anchor = this.anchor;

    ok(popover.options().modal);
    ok(popover2.options().modal);

    popover.open(anchor);
    equal(true, popover.isOpened());
    equal(false, popover2.isOpened());

    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('opened2'));
    deepEqual([], this.mockListenerCalls('closed'));
    deepEqual([], this.mockListenerCalls('closed2'));

    popover2.open(anchor);
    equal(false, popover.isOpened());
    equal(true, popover2.isOpened());

    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([['opened']], this.mockListenerCalls('opened2'));
    deepEqual([['closed']], this.mockListenerCalls('closed'));
    deepEqual([], this.mockListenerCalls('closed2'));
});


QUnit.test('creme.dialog.Popover (not modal)', function(assert) {
    var popover = new creme.dialog.Popover({modal: false});
    var popover2 = new creme.dialog.Popover({modal: false});

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    popover2.on('opened', this.mockListener('opened2'));
    popover2.on('closed', this.mockListener('closed2'));

    var anchor = this.anchor;

    popover.open(anchor);
    equal(true, popover.isOpened());
    equal(false, popover2.isOpened());

    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('opened2'));
    deepEqual([], this.mockListenerCalls('closed'));
    deepEqual([], this.mockListenerCalls('closed2'));

    popover2.open(anchor);
    equal(true, popover.isOpened());
    equal(true, popover2.isOpened());

    deepEqual([['opened']], this.mockListenerCalls('opened'));
    deepEqual([['opened']], this.mockListenerCalls('opened2'));
    deepEqual([], this.mockListenerCalls('closed'));
    deepEqual([], this.mockListenerCalls('closed2'));
});

QUnit.test('creme.dialog.Popover (close with arguments)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.anchor;

    popover.on('closed', this.mockListener('closed'));

    popover.open(anchor);
    equal(true, popover.isOpened());
    deepEqual([], this.mockListenerCalls('closed'));

    popover.close('a', 12, {});
    deepEqual([['closed', 'a', 12, {}]], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Popover (open/close cycles)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.anchor;

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    equal(false, popover.isOpened());
    deepEqual([], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    popover.open(anchor).close();

    popover.open(anchor);
    popover._glasspane.pane().trigger('mousedown');

    popover.open(anchor);
    popover._glasspane.pane().trigger('mousedown');

    popover.open(anchor);
    $('.popover').trigger('modal-close');

    popover.open(anchor);
    $('.popover').trigger('modal-close');

    equal(false, popover.isOpened());
    deepEqual([['opened'], ['opened'], ['opened'], ['opened'], ['opened']],
              this.mockListenerCalls('opened'));
    deepEqual([['closed'], ['closed'], ['closed'], ['closed'], ['closed']],
              this.mockListenerCalls('closed'));
});
