(function($) {

var RED_DOT_5x5_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==';

QUnit.module("creme.popover.js", new QUnitMixin(QUnitEventMixin,
                                                QUnitDialogMixin, {
    assertPopoverDirection: function(popover, direction) {
        this.assert.ok(popover._dialog.is('.popover.' + direction), 'popover direction is ' + direction);
        this.assert.equal(direction, popover.direction());
    }
}));

QUnit.test('creme.dialog.Popover (open)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.qunitFixture('popover');

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    assert.equal(false, popover.isOpened());
    assert.equal(undefined, popover.anchor());
    assert.deepEqual([], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    popover.open(anchor);

    assert.equal(true, popover.isOpened());
    this.equalOuterHtml('<div id="qunit-fixture-popover"></div>', popover.anchor());
    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    var other = $('<span/>');

    this.assertRaises(function() {
        popover.open(other);
    }, Error, 'Error: popover is already opened');
});

QUnit.test('creme.dialog.Popover (toggle)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.qunitFixture('popover');

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    assert.equal(false, popover.isOpened());
    assert.deepEqual([], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    popover.toggle(anchor);
    assert.equal(true, popover.isOpened());
    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    popover.toggle(anchor);
    assert.equal(false, popover.isOpened());
    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([['closed']], this.mockListenerCalls('closed'));

    popover.toggle(anchor);
    assert.equal(true, popover.isOpened());
    assert.deepEqual([['opened'], ['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([['closed']], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Popover (title)', function(assert) {
    var popover = new creme.dialog.Popover({title: 'A'});
    var anchor = this.qunitFixture('popover');

    popover.open(anchor);
    this.assertPopoverTitle('A');
    this.equalHtml('A', popover.title());

    popover.title('B');
    this.assertPopoverTitle('B');
    this.equalHtml('B', popover.title());

    this.assertNoXSS(function(value) {
        popover.title(value);
    });
});

QUnit.test('creme.dialog.Popover (title, escaped)', function(assert) {
    var popover = new creme.dialog.Popover({
        title: 'Default&nbsp;title &amp; &lt; escaped&gt;'
    });
    var anchor = this.qunitFixture('popover');

    popover.open(anchor);
    this.assertPopoverTitle('Default\u00A0title & < escaped>');
    this.equalHtml('Default\u00A0title & < escaped>', popover.title());

    popover.title('Modified title &quot;escaped&quot;');

    this.equalHtml('Modified title "escaped"', popover.title());
    this.assertPopoverTitle('Modified title "escaped"');
});

QUnit.test('creme.dialog.Popover (direction)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.qunitFixture('popover');

    popover.open(anchor);
    this.assertPopoverDirection(popover, 'bottom');

    popover.close();
    popover.open(anchor, {direction: 'top'});
    this.assertPopoverDirection(popover, 'top');

    popover.direction('right');
    this.assertPopoverDirection(popover, 'right');

    popover.direction('left');
    this.assertPopoverDirection(popover, 'left');

    popover.direction('bottom-left');
    this.assertPopoverDirection(popover, 'bottom-left');

    popover.direction('bottom-right');
    this.assertPopoverDirection(popover, 'bottom-right');

    popover.direction('center');
    this.assertPopoverDirection(popover, 'center');

    popover.direction('center-window');
    this.assertPopoverDirection(popover, 'center-window');

    this.assertRaises(function() {
        popover.direction('elsewhere');
    }, Error, 'Error: invalid popover direction elsewhere');
});

QUnit.test('creme.dialog.Popover (addClass + direction)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.qunitFixture('popover');

    popover.addClass('special-popover');
    popover.open(anchor);

    this.assertPopoverDirection(popover, 'bottom');
    assert.ok(popover._dialog.is('.special-popover'));

    popover.close();
    popover.open(anchor, {direction: 'top'});

    this.assertPopoverDirection(popover, 'top');
    assert.ok(popover._dialog.is('.special-popover'));

    popover.direction('right');

    this.assertPopoverDirection(popover, 'right');
    assert.ok(popover._dialog.is('.special-popover'));
});

QUnit.test('creme.dialog.Popover (remove/toggleClass)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.qunitFixture('popover');

    popover.addClass('special-popover');
    popover.open(anchor);

    assert.ok(popover._dialog.is('.special-popover'));

    popover.removeClass('special-popover');
    assert.equal(false, popover._dialog.is('.special-popover'));

    popover.toggleClass('special-popover', true);
    assert.ok(popover._dialog.is('.special-popover'));

    popover.toggleClass('special-popover', false);
    assert.equal(false, popover._dialog.is('.special-popover'));
});

QUnit.test('creme.dialog.Popover (fill)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.qunitFixture('popover');

    popover.open(anchor);
    popover.fill('<p>this is another sample</p>');
    this.equalHtml('<p>this is another sample</p>', popover.content());

    popover.fill($('<div>element sample</div>'));
    this.equalHtml('<div>element sample</div>', popover.content());
});

QUnit.test('creme.dialog.Popover (fill)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.qunitFixture('popover');

    popover.fill('<p>this is a sample</p>');
    popover.open(anchor);
    this.equalHtml('<p>this is a sample</p>', popover.content());

    popover.fill('<p>this is another sample</p>');
    this.equalHtml('<p>this is another sample</p>', popover.content());

    popover.fill($('<div>element sample</div>'));
    this.equalHtml('<div>element sample</div>', popover.content());
});

QUnit.test('creme.dialog.Popover (fill, function)', function(assert) {
    var popover = new creme.dialog.Popover({title: 'A'});
    var anchor = this.qunitFixture('popover');

    popover.open(anchor);
    popover.fill(function(options) {
                return '<p>content for ${title}</p>'.template(options);
            });

    this.equalHtml('<p>content for A</p>', popover.content());
});

QUnit.test('creme.dialog.Popover (on/one/off events)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.qunitFixture('popover');
    var opened_cb = this.mockListener('opened');

    popover.on('opened', opened_cb);
    popover.one('closed', this.mockListener('closed'));

    popover.open(anchor);

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    popover.close();

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([['closed']], this.mockListenerCalls('closed'));

    popover.open(anchor);
    popover.close();

    assert.deepEqual([['opened'], ['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([['closed']], this.mockListenerCalls('closed'));

    popover.off('opened', opened_cb);

    popover.open(anchor);
    popover.close();

    assert.deepEqual([['opened'], ['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([['closed']], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Popover (closeIfOut)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.qunitFixture('popover');

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    assert.ok(popover.options().closeIfOut);

    popover.open(anchor);
    assert.equal(true, popover.isOpened());
    this.equalOuterHtml('<div id="qunit-fixture-popover"></div>', popover.anchor());

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    popover._glasspane.pane().trigger('mousedown');
    assert.equal(false, popover.isOpened());
    assert.equal(undefined, popover.anchor());

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([['closed']], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Popover (closeIfOut, disabled)', function(assert) {
    var popover = new creme.dialog.Popover({
        closeIfOut: false
    });

    var anchor = this.qunitFixture('popover');

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    assert.equal(false, popover.options().closeIfOut);

    popover.open(anchor);
    assert.equal(true, popover.isOpened());
    this.equalOuterHtml('<div id="qunit-fixture-popover"></div>', popover.anchor());

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    popover._glasspane.pane().trigger('mousedown');
    assert.equal(true, popover.isOpened());

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));
});


QUnit.test('creme.dialog.Popover (scrollbackOnClose)', function(assert) {
    this.withScrollBackFaker(function(faker) {
        faker.result = 789;

        var popover = new creme.dialog.Popover({
            scrollbackOnClose: true
        });
        var anchor = this.qunitFixture('popover');

        assert.equal(true, popover.options().scrollbackOnClose);
        assert.equal(Object.isNone(popover._scrollbackPosition), true);
        assert.deepEqual(faker.calls(), []);

        popover.open(anchor);

        assert.equal(789, popover._scrollbackPosition);
        assert.deepEqual(faker.calls(), [
            []
        ]);

        creme.utils.scrollBack(50);

        assert.deepEqual(faker.calls(), [
            [],
            [50]
        ]);

        popover.close();

        assert.equal(Object.isNone(popover._scrollbackPosition), true);
        assert.deepEqual(faker.calls(), [
            [],
            [50],
            [789, 'slow']
        ]);
    });
});


QUnit.test('creme.dialog.Popover (scrollbackOnClose, disabled)', function(assert) {
    this.withScrollBackFaker(function(faker) {
        faker.result = 789;

        var popover = new creme.dialog.Popover();
        var anchor = this.qunitFixture('popover');

        assert.equal(false, popover.options().scrollbackOnClose);
        assert.equal(Object.isNone(popover._scrollbackPosition), true);
        assert.deepEqual(faker.calls(), []);

        popover.open(anchor);

        assert.equal(Object.isNone(popover._scrollbackPosition), true);
        assert.deepEqual(faker.calls(), []);

        popover.close();

        // close always call creme.utils.scrollBack
        assert.deepEqual(faker.calls(), [
            [undefined, 'slow']
        ]);
    });
});


QUnit.test('creme.dialog.Popover (trigger modal close)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.qunitFixture('popover');

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    assert.ok(popover.options().closeIfOut);

    popover.open(anchor);
    assert.equal(true, popover.isOpened());

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    $('.popover').trigger('modal-close');
    assert.equal(false, popover.isOpened());

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([['closed']], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Popover (modal)', function(assert) {
    var popover = new creme.dialog.Popover();
    var popover2 = new creme.dialog.Popover();

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    popover2.on('opened', this.mockListener('opened2'));
    popover2.on('closed', this.mockListener('closed2'));

    var anchor = this.qunitFixture('popover');

    assert.ok(popover.options().modal);
    assert.ok(popover2.options().modal);

    popover.open(anchor);
    assert.equal(true, popover.isOpened());
    assert.equal(false, popover2.isOpened());

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('opened2'));
    assert.deepEqual([], this.mockListenerCalls('closed'));
    assert.deepEqual([], this.mockListenerCalls('closed2'));

    popover2.open(anchor);
    assert.equal(false, popover.isOpened());
    assert.equal(true, popover2.isOpened());

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([['opened']], this.mockListenerCalls('opened2'));
    assert.deepEqual([['closed']], this.mockListenerCalls('closed'));
    assert.deepEqual([], this.mockListenerCalls('closed2'));
});


QUnit.test('creme.dialog.Popover (not modal)', function(assert) {
    var popover = new creme.dialog.Popover({modal: false});
    var popover2 = new creme.dialog.Popover({modal: false});

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    popover2.on('opened', this.mockListener('opened2'));
    popover2.on('closed', this.mockListener('closed2'));

    var anchor = this.qunitFixture('popover');

    popover.open(anchor);
    assert.equal(true, popover.isOpened());
    assert.equal(false, popover2.isOpened());

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('opened2'));
    assert.deepEqual([], this.mockListenerCalls('closed'));
    assert.deepEqual([], this.mockListenerCalls('closed2'));

    popover2.open(anchor);
    assert.equal(true, popover.isOpened());
    assert.equal(true, popover2.isOpened());

    assert.deepEqual([['opened']], this.mockListenerCalls('opened'));
    assert.deepEqual([['opened']], this.mockListenerCalls('opened2'));
    assert.deepEqual([], this.mockListenerCalls('closed'));
    assert.deepEqual([], this.mockListenerCalls('closed2'));
});

QUnit.test('creme.dialog.Popover (close with arguments)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.qunitFixture('popover');

    popover.on('closed', this.mockListener('closed'));

    popover.open(anchor);
    assert.equal(true, popover.isOpened());
    assert.deepEqual([], this.mockListenerCalls('closed'));

    popover.close('a', 12, {});
    assert.deepEqual([['closed', 'a', 12, {}]], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Popover (open/close cycles)', function(assert) {
    var popover = new creme.dialog.Popover();
    var anchor = this.qunitFixture('popover');

    popover.on('opened', this.mockListener('opened'));
    popover.on('closed', this.mockListener('closed'));

    assert.equal(false, popover.isOpened());
    assert.deepEqual([], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    popover.open(anchor).close();

    popover.open(anchor);
    popover._glasspane.pane().trigger('mousedown');

    popover.open(anchor);
    popover._glasspane.pane().trigger('mousedown');

    popover.open(anchor);
    $('.popover').trigger('modal-close');

    popover.open(anchor);
    $('.popover').trigger('modal-close');

    assert.equal(false, popover.isOpened());
    assert.deepEqual([['opened'], ['opened'], ['opened'], ['opened'], ['opened']],
              this.mockListenerCalls('opened'));
    assert.deepEqual([['closed'], ['closed'], ['closed'], ['closed'], ['closed']],
              this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.ImagePopover (src)', function(assert) {
    var self = this;
    var popover = new creme.dialog.ImagePopover();

    assert.equal(false, popover.options().title);
    assert.equal(true, popover._dialog.is('.popover-picture'));

    popover.fillImage('data:image/png;base64, ' + RED_DOT_5x5_BASE64);

    this.equalHtml('<div class="picture-wait">&nbsp;</div>', popover.content());

    var done = assert.async();

    // deferred loading
    setTimeout(function() {
        self.equalHtml('<img src="data:image/png;base64, ' + RED_DOT_5x5_BASE64 + '" class="no-title">', popover.content());

        popover.open();
        self.assertPopoverDirection(popover, 'center-window');

        done();
    }, 200);
});

QUnit.test('creme.dialog.ImagePopover (img)', function(assert) {
    var popover = new creme.dialog.ImagePopover();

    assert.equal(false, popover.options().title);
    assert.equal(true, popover._dialog.is('.popover-picture'));

    popover.fillImage($('<img src="nowhere" />'));

    this.equalHtml('<img src="nowhere" class="no-title"/>', popover.content());

    popover.open();
    this.assertPopoverDirection(popover, 'center-window');
});

QUnit.test('creme.dialog.ImagePopover (title)', function(assert) {
    var popover = new creme.dialog.ImagePopover({
        title: 'Picture #1'
    });

    assert.equal('Picture #1', popover.options().title);
    this.equalHtml('Picture #1', popover.title());
    assert.equal(true, popover._dialog.is('.popover-picture'));

    popover.fillImage($('<img src="nowhere" />'));

    this.equalHtml('<img src="nowhere"/>', popover.content());

    popover.open();
    this.assertPopoverDirection(popover, 'center-window');
});

QUnit.test('creme.dialog.ImagePopover (close on click)', function(assert) {
    var anchor = this.qunitFixture('popover');
    var popover = new creme.dialog.ImagePopover();

    popover.fillImage($('<img src="nowhere" />'));

    popover.open(anchor);
    assert.equal(true, popover.isOpened());

    // close on click on glasspane
    popover._glasspane.pane().trigger('mousedown');
    assert.equal(false, popover.isOpened());

    popover.open(anchor);
    assert.equal(true, popover.isOpened());

    // close on click on image
    popover.content().trigger('click');
    assert.equal(false, popover.isOpened());
});

QUnit.test('creme.dialog.ImagePopover (close on click, disabled)', function(assert) {
    var anchor = this.qunitFixture('popover');
    var popover = new creme.dialog.ImagePopover({
        closeOnClick: false
    });

    popover.fillImage($('<img src="nowhere" />'));

    popover.open(anchor);
    assert.equal(true, popover.isOpened());

    // close on click on glasspane
    popover._glasspane.pane().trigger('mousedown');
    assert.equal(false, popover.isOpened());

    popover.open(anchor);
    assert.equal(true, popover.isOpened());

    // nothing done
    popover.content().trigger('click');
    assert.equal(true, popover.isOpened());
});

QUnit.test('creme.dialog.PopoverAction.fromTarget', function(assert) {
    var anchor = this.qunitFixture('popover');
    var target = $(
       '<a data-title="My title">' +
           '<script type="text/html">Hello world ! Go <a href="/">here !</a></script>' +
       '</a>'
    );

    var action = creme.dialog.PopoverAction.fromTarget(target);

    action.start({target: anchor});
    var popover = this.assertOpenedPopover();

    this.equalHtml('My title', popover.find('.popover-title'));
    this.equalHtml('Hello world ! Go <a href="/">here !</a>', popover.find('.popover-content'));
});

QUnit.test('creme.dialog.PopoverAction.fromTarget (summary)', function(assert) {
    var anchor = this.qunitFixture('popover');
    var target = $(
       '<a>' +
           '<summary><h1>My title</h1></summary>' +
           '<script type="text/html">Hello world ! Go <a href="/">here !</a></script>' +
       '</a>'
    );

    var action = creme.dialog.PopoverAction.fromTarget(target);

    action.start({target: anchor});
    var popover = this.assertOpenedPopover();

    this.equalHtml('My title', popover.find('.popover-title'));
    this.equalHtml('Hello world ! Go <a href="/">here !</a>', popover.find('.popover-content'));
});

QUnit.test('creme.dialog.PopoverAction.fromTarget (legacy)', function(assert) {
    var anchor = this.qunitFixture('popover');
    var target = $(
       '<a>' +
           '<summary>My title</summary>' +
           '<details>Hello world ! Go here !</details>' +
       '</a>'
    );

    var action = creme.dialog.PopoverAction.fromTarget(target);

    action.start({target: anchor});
    var popover = this.assertOpenedPopover();

    this.equalHtml('My title', popover.find('.popover-title'));
    this.equalHtml('Hello world ! Go here !', popover.find('.popover-content'));
});

QUnit.test('creme.dialog.PopoverAction.fromTarget (contentHref)', function(assert) {
    var anchor = this.qunitFixture('popover');
    var target = $(
       '<a data-title="My title" data-content-href="#my-popover">' +
            '<script type="text/html">Hello world ! Go <a href="/">here !</a></script>' +
       '</a>' +
       '<script type="text/html" id="my-popover">Hello guys ! Go <a href="/">there !</a></script>'
    ).appendTo(anchor);

    var action = creme.dialog.PopoverAction.fromTarget(target);

    action.start({target: anchor});
    var popover = this.assertOpenedPopover();

    this.equalHtml('My title', popover.find('.popover-title'));
    this.equalHtml('Hello guys ! Go <a href="/">there !</a>', popover.find('.popover-content'));
});

}(jQuery));
