(function($) {

var RED_DOT_5x5_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==';

var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';
var MOCK_FRAME_CONTENT_LIST = '<div class="mock-content"><ul><li>Item 1</li><li>Item 2</li></ul></div>';
var MOCK_FRAME_CONTENT_WIDGET = '<div class="mock-content">' +
                                    '<input widget="ui-creme-dinput" class="ui-creme-dinput ui-creme-widget widget-auto" type="text"></input>' +
                                '</div>';

var MOCK_FRAME_CONTENT_ACTION = '<div class="mock-content">' +
                                    '<a class="ui-creme-dialog-action" href="/mock/action/1" name="action-1">Action 1</a>' +
                                    '<a class="ui-creme-dialog-action" href="/mock/action/2"></a>' +
                                    '<a class="ui-creme-dialog-action" href="/mock/action/3">Action 3</a>' +
                                '</div>';

var MOCK_FRAME_CONTENT_TITLEBAR = '<div class="mock-content">' +
                                      '<div class="hat-bar-container ui-creme-dialog-titlebar">' +
                                          '<div class="hat-bar">' +
                                              '<div class="bar-icon"><img /></div>' +
                                              '<div class="bar-title"><h1>Mock Dialog ${title}</h1></div>' +
                                          '</div>' +
                                      '</div>' +
                                  '</div>';

var MOCK_FRAME_CONTENT_HATBAR = '<div class="mock-content">' +
                                    '<div class="hat-bar-container">' +
                                        '<div class="hat-bar">' +
                                            '<div class="bar-icon"><img /></div>' +
                                            '<div class="bar-title"><h1>Mock Dialog Title</h1></div>' +
                                        '</div>' +
                                    '</div>' +
                                '</div>';


QUnit.module("creme.dialog.js", new QUnitMixin(QUnitEventMixin,
                                               QUnitAjaxMixin,
                                               QUnitDialogMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({delay: 0, sync: true, name: 'creme.dialog.js'});
    },

    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
            'mock/html': backend.response(200, MOCK_FRAME_CONTENT),
            'mock/html2': backend.response(200, MOCK_FRAME_CONTENT_LIST),
            'mock/widget': backend.response(200, MOCK_FRAME_CONTENT_WIDGET),
            'mock/titlebar': backend.response(200, MOCK_FRAME_CONTENT_TITLEBAR.template({title: 'Title #1'})),
            'mock/titlebar2': backend.response(200, MOCK_FRAME_CONTENT_TITLEBAR.template({title: 'Title #2'})),
            'mock/hatbar': backend.response(200, MOCK_FRAME_CONTENT_HATBAR),
            'mock/actions': backend.response(200, MOCK_FRAME_CONTENT_ACTION),
            'mock/red_dot': backend.response(200, RED_DOT_5x5_BASE64, {'content-type': 'image/png;base64'}),
            'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
            'mock/error': backend.response(500, 'HTTP - Error 500')
        });

        this.setMockBackendPOST({
            'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
            'mock/error': backend.response(500, 'HTTP - Error 500')
        });
    },

    afterEach: function() {
        creme.widget.shutdown($('body'));
    }
}));

QUnit.test('creme.dialog.SelectionDialog (default)', function(assert) {
    var dialog = new creme.dialog.SelectionDialog();
    dialog.onOk(this.mockListener('ok'));
    dialog.onClose(this.mockListener('close'));

    assert.equal(undefined, dialog.validator());
    assert.equal(undefined, dialog.selector());

    assert.deepEqual([], this.mockListenerCalls('ok'));
    assert.deepEqual([], this.mockListenerCalls('close'));

    dialog.ok();

    assert.deepEqual([['ok', []]], this.mockListenerCalls('ok'));
    assert.deepEqual([], this.mockListenerCalls('close'));

    this.resetMockListenerCalls();

    dialog.close();

    assert.deepEqual([], this.mockListenerCalls('ok'));
    assert.deepEqual([['close', dialog.options]], this.mockListenerCalls('close'));
});

QUnit.test('creme.dialog.SelectionDialog (selector)', function(assert) {
    var selector = function() {
        return $('option[value="2"]', this.content()).html();
    };
    var dialog = new creme.dialog.SelectionDialog();
    dialog.fill('<option value="1">a</option><option value="2">b</option>')
          .selector(selector);

    dialog.onOk(this.mockListener('ok'));
    dialog.onClose(this.mockListener('close'));

    assert.equal(undefined, dialog.validator());
    assert.equal(selector, dialog.selector());

    assert.deepEqual([], this.mockListenerCalls('ok'));
    assert.deepEqual([], this.mockListenerCalls('close'));

    dialog.ok();

    assert.deepEqual([['ok', 'b']], this.mockListenerCalls('ok'));
    assert.deepEqual([], this.mockListenerCalls('close'));

    this.resetMockListenerCalls();

    dialog.close();

    assert.deepEqual([], this.mockListenerCalls('ok'));
    assert.deepEqual([['close', dialog.options]], this.mockListenerCalls('close'));
});

QUnit.test('creme.dialog.SelectionDialog (validator)', function(assert) {
    var selector = function() {
        return $('select', this.content()).val();
    };
    var validator = function(data) {
        return data !== null && data.length > 0;
    };
    var dialog = new creme.dialog.SelectionDialog();

    dialog.fill('<select multiple><option value="1">a</option><option value="2">b</option></select>')
          .selector(selector)
          .validator(validator);

    dialog.onOk(this.mockListener('ok'));
    dialog.onClose(this.mockListener('close'));

    assert.equal(validator, dialog.validator());
    assert.equal(selector, dialog.selector());

    assert.deepEqual([], this.mockListenerCalls('ok'));
    assert.deepEqual([], this.mockListenerCalls('close'));

    assert.deepEqual([], $('select', dialog.content()).val());
    dialog.ok();

    // no selection, not valid
    assert.deepEqual([], this.mockListenerCalls('ok'));
    assert.deepEqual([], this.mockListenerCalls('close'));

    $('select', dialog.content()).val('2');
    dialog.ok();

    assert.deepEqual([['ok', ['2']]], this.mockListenerCalls('ok'));
    assert.deepEqual([], this.mockListenerCalls('close'));

    this.resetMockListenerCalls();

    dialog.close();

    assert.deepEqual([], this.mockListenerCalls('ok'));
    assert.deepEqual([['close', dialog.options]], this.mockListenerCalls('close'));
});

QUnit.test('creme.dialog.Dialog (open/close)', function(assert) {
    var dialog = new creme.dialog.Dialog({url: 'mock/html', backend: this.backend});
    dialog.onOpen(this.mockListener('opened'));
    dialog.onClose(this.mockListener('closed'));

    assert.deepEqual([], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    assert.equal(false, dialog.isOpened());
    assert.equal(false, dialog._isClosing);

    dialog.open();

    assert.equal(true, dialog.isOpened());
    assert.equal(false, dialog._isClosing);

    this.assertRaises(function() {
        dialog.open();
    }, Error, 'Error: dialog already opened !');

    dialog.close();

    assert.equal(false, dialog.isOpened());
    assert.equal(false, dialog._isClosing);
});

QUnit.test('creme.dialog.Dialog (url)', function(assert) {
    var dialog = new creme.dialog.Dialog({url: 'mock/html', backend: this.backend});
    dialog.on('frame-activated', this.mockListener('frame-activated'));
    dialog.onOpen(this.mockListener('opened'));
    dialog.onClose(this.mockListener('closed'));

    assert.deepEqual([], this.mockListenerCalls('frame-activated'));
    assert.deepEqual([], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    dialog.open();

    assert.equal('mock/html', dialog.frame().lastFetchUrl());
    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    assert.deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    assert.equal(MOCK_FRAME_CONTENT, dialog.content().html());

    dialog.close();

    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    assert.deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    assert.deepEqual([['close', dialog.options]], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Dialog (url, invalid)', function(assert) {
    var dialog = new creme.dialog.Dialog({url: 'mock/unknown', backend: this.backend});
    dialog.on('frame-activated', this.mockListener('frame-activated'));
    dialog.on('frame-fail', this.mockListener('frame-fail'));
    dialog.onOpen(this.mockListener('opened'));
    dialog.onClose(this.mockListener('closed'));

    assert.deepEqual([], this.mockListenerCalls('frame-activated'));
    assert.deepEqual([], this.mockListenerCalls('frame-fail'));
    assert.deepEqual([], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    dialog.open();

    assert.equal(undefined, dialog.frame().lastFetchUrl());

    assert.deepEqual([], this.mockListenerCalls('frame-activated'));
    assert.deepEqual([['frame-fail', dialog.frame()]], this.mockListenerCalls('frame-fail'));
    assert.deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    assert.equal(1, dialog.content().find('.ui-creme-overlay[status="404"]').length);

    dialog.close();

    assert.deepEqual([], this.mockListenerCalls('frame-activated'));
    assert.deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    assert.deepEqual([['close', dialog.options]], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Dialog (html, widget)', function(assert) {
    var dialog = new creme.dialog.Dialog({html: MOCK_FRAME_CONTENT_WIDGET});
    dialog.on('frame-activated', this.mockListener('frame-activated'));
    dialog.onOpen(this.mockListener('opened'));
    dialog.onClose(this.mockListener('closed'));

    assert.deepEqual([], this.mockListenerCalls('frame-activated'));
    assert.deepEqual([], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    dialog.open();

    assert.equal(undefined, dialog.frame().lastFetchUrl());

    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    assert.deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    assert.deepEqual([], this.mockListenerCalls('closed'));

    assert.equal(1, dialog.content().find('.ui-creme-widget').length);
    assert.equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.close();

    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    assert.deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    assert.deepEqual([['close', dialog.options]], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Dialog (widget, fill static)', function(assert) {
    var dialog = new creme.dialog.Dialog();
    dialog.on('frame-activated', this.mockListener('frame-activated'));
    dialog.onOpen(this.mockListener('opened'));
    dialog.onClose(this.mockListener('closed'));

    dialog.open();

    assert.deepEqual([], this.mockListenerCalls('frame-activated'), 'activated, not opened');
    assert.deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    assert.equal(0, dialog.content().find('.ui-creme-widget').length);

    // already opened, frame widgets are immediately activated
    dialog.fill(MOCK_FRAME_CONTENT_WIDGET);

    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'), 'activated, after fill');
    assert.deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));

    assert.equal(1, dialog.content().find('.ui-creme-widget').length);
    assert.equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.close();
    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'), 'activated, after close');
    assert.equal(0, dialog.content().find('.ui-creme-widget').length);
});

QUnit.test('creme.dialog.Dialog (widget, fill static, not opened)', function(assert) {
    var dialog = new creme.dialog.Dialog();
    dialog.on('frame-activated', this.mockListener('frame-activated'));

    dialog.fill(MOCK_FRAME_CONTENT_WIDGET);

    // not opened, frame widgets activation is deferred until opening
    assert.deepEqual([], this.mockListenerCalls('frame-activated'));
    assert.equal(1, dialog.content().find('.ui-creme-widget').length);
    assert.equal(0, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.open();

    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    assert.equal(1, dialog.content().find('.ui-creme-widget').length);
    assert.equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.close();

    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    assert.equal(0, dialog.content().find('.ui-creme-widget').length);
});

QUnit.test('creme.dialog.Dialog (widget, fetch url)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        backend: this.backend,
        id: 'test-popup'
    });
    dialog.on('frame-activated', this.mockListener('frame-activated'));

    $(document).on('dialog-frame-activated', this.mockListener('dialog-frame-activated'));
    $(document).on('dialog-open', this.mockListener('dialog-open'));
    $(document).on('dialog-before-destroy', this.mockListener('dialog-before-destroy'));
    $(document).on('dialog-close', this.mockListener('dialog-close'));

    dialog.open();
    assert.deepEqual([], this.mockListenerCalls('frame-activated'));
    assert.equal(0, dialog.content().find('.ui-creme-widget').length);

    dialog.fetch('mock/widget');
    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    assert.equal(1, dialog.content().find('.ui-creme-widget').length);
    assert.equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.close();
    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    assert.equal(0, dialog.content().find('.ui-creme-widget').length);

    assert.deepEqual([], this.mockListenerCalls('dialog-frame-activated'));
    assert.deepEqual([], this.mockListenerCalls('dialog-open'));
    assert.deepEqual([], this.mockListenerCalls('dialog-before-destroy'));
    assert.deepEqual([], this.mockListenerCalls('dialog-close'));
});

QUnit.test('creme.dialog.Dialog (widget, fetch url, propagateEvent)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        backend: this.backend,
        propagateEvent: true,
        id: 'test-popup'
    });

    dialog.on('frame-activated', this.mockListener('frame-activated'));

    $(document).on('dialog-frame-activated', this.mockListener('dialog-frame-activated'));
    $(document).on('dialog-open', this.mockListener('dialog-open'));
    $(document).on('dialog-before-destroy', this.mockListener('dialog-before-destroy'));
    $(document).on('dialog-close', this.mockListener('dialog-close'));

    dialog.open();
    assert.deepEqual([], this.mockListenerCalls('frame-activated'));
    assert.equal(0, dialog.content().find('.ui-creme-widget').length);

    dialog.fetch('mock/widget');
    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    assert.equal(1, dialog.content().find('.ui-creme-widget').length);
    assert.equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.close();
    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    assert.equal(0, dialog.content().find('.ui-creme-widget').length);

    assert.deepEqual([['dialog-frame-activated', [dialog, dialog.frame()]]], this.mockListenerJQueryCalls('dialog-frame-activated'));
    assert.deepEqual([['dialog-open', [dialog, dialog.options]]], this.mockListenerJQueryCalls('dialog-open'));
    assert.deepEqual([['dialog-before-destroy', [dialog, dialog.options]]], this.mockListenerJQueryCalls('dialog-before-destroy'));
    assert.deepEqual([['dialog-close', [dialog, dialog.options]]], this.mockListenerJQueryCalls('dialog-close'));
});

QUnit.test('creme.dialog.Dialog (widget, fetch url, reactivate)', function(assert) {
    var dialog = new creme.dialog.Dialog({backend: this.backend});
    dialog.on('frame-activated', this.mockListener('frame-activated'));

    dialog.open();
    assert.deepEqual([], this.mockListenerCalls('frame-activated'));
    assert.equal(0, dialog.content().find('.ui-creme-widget').length);

    dialog.fetch('mock/widget');
    assert.deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'), 'first fetch');
    assert.equal(1, dialog.content().find('.ui-creme-widget').length);
    assert.equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.fetch('mock/widget');
    assert.deepEqual([
        ['frame-activated', dialog.frame()],
        ['frame-activated', dialog.frame()]
    ], this.mockListenerCalls('frame-activated'), 'second fetch');
    assert.equal(1, dialog.content().find('.ui-creme-widget').length);
    assert.equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.close();
    assert.deepEqual([
        ['frame-activated', dialog.frame()],
        ['frame-activated', dialog.frame()]
    ], this.mockListenerCalls('frame-activated'), 'close');
    assert.equal(0, dialog.content().find('.ui-creme-widget').length);
});

QUnit.test('creme.dialog.Dialog (default button)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    assert.equal(0, dialog.buttons().find('button').length);

    dialog.open();

    assert.equal(1, dialog.buttons().find('button').length);
    assert.equal(gettext('Close'), dialog.button('close').text());

    this.assertOpenedDialog();

    dialog.button('close').trigger('click');

    this.assertClosedDialog();
});

QUnit.test('creme.dialog.Dialog (default button, custom names)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        defaultButtonLabels: {
            'close': 'Too Close'
        }
    });

    assert.equal(0, dialog.buttons().find('button').length);

    dialog.open();

    assert.equal(1, dialog.buttons().find('button').length);
    assert.equal('Too Close', dialog.button('close').text());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (action links, fill)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    dialog.fill(MOCK_FRAME_CONTENT_ACTION);

    assert.equal(0, dialog.buttons().find('button').length);

    dialog.open();

    assert.equal(4, dialog.buttons().find('button').length);
    assert.equal(gettext('Action 1'), dialog.button('action-1').text());
    assert.equal(gettext('Action'), dialog.button('link-1').text());
    assert.equal(gettext('Action 3'), dialog.button('link-2').text());
    assert.equal(gettext('Close'), dialog.button('close').text());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (action links, fetch url)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    dialog.fetch('mock/actions');

    assert.equal(0, dialog.buttons().find('button').length);

    dialog.open();

    assert.equal(4, dialog.buttons().find('button').length);
    assert.equal(gettext('Action 1'), dialog.button('action-1').text());
    assert.equal(gettext('Action'), dialog.button('link-1').text());
    assert.equal(gettext('Action 3'), dialog.button('link-2').text());
    assert.equal(gettext('Close'), dialog.button('close').text());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (action links, disabled)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        useFrameActions: false
    });

    dialog.fill(MOCK_FRAME_CONTENT_ACTION);

    assert.equal(0, dialog.buttons().find('button').length);

    dialog.open();

    assert.equal(1, dialog.buttons().find('button').length);
    assert.equal(gettext('Close'), dialog.button('close').text());

    dialog.fetch('mock/actions');

    assert.equal(1, dialog.buttons().find('button').length);
    assert.equal(gettext('Close'), dialog.button('close').text());
});

QUnit.test('creme.dialog.Dialog (title)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        title: 'Default title'
    });

    dialog.open();

    assert.equal('Default title', dialog.title());
    this.assertDialogTitleHtml('Default title');

    dialog.title('Modified title');

    assert.equal('Modified title', dialog.title());
    this.assertDialogTitleHtml('Modified title');

    this.assertNoXSS(function(value) {
        dialog.title(value);
    });
});

QUnit.test('creme.dialog.Dialog (title, escaped)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        title: 'Default&nbsp;title &amp; &lt; escaped&gt;'
    });

    dialog.open();

    assert.equal('Default\u00A0title & < escaped>', dialog.title());
    this.assertDialogTitleHtml('Default\u00A0title & < escaped>');

    dialog.title('Modified title &quot;escaped&quot;');

    assert.equal('Modified title "escaped"', dialog.title());
    this.assertDialogTitleHtml('Modified title "escaped"');
});

QUnit.test('creme.dialog.Dialog (clear)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    assert.equal('', dialog.content().html());

    dialog.clear();
    assert.equal('', dialog.content().html());

    dialog.fill(MOCK_FRAME_CONTENT);
    assert.equal(MOCK_FRAME_CONTENT, dialog.content().html());

    dialog.clear();
    assert.equal('', dialog.content().html());
});

QUnit.test('creme.dialog.Dialog (dialog)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    assert.equal(false, dialog.isOpened());
    assert.equal(undefined, dialog.dialog());

    dialog.open();

    assert.equal(true, dialog.isOpened());
    assert.ok(dialog.dialog() !== undefined);

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (center)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    dialog.center();

    assert.equal(false, dialog.isOpened());
    assert.equal(undefined, dialog.position());
    assert.equal(undefined, dialog.cssPosition());

    dialog.open();
    dialog.center();

    assert.equal(true, dialog.isOpened());
    assert.deepEqual({
        my: 'center center',
        at: 'center center',
        collision: 'fit',
        within: $('.ui-dialog-within-container')
    }, dialog.position());

    dialog.center({top: 5});
    assert.deepEqual({
        my: 'center center',
        at: 'center center',
        collision: 'fit',
        within: $('.ui-dialog-within-container')
    }, dialog.position());

    dialog.position({my: 'center top', at: 'center center'});
    assert.deepEqual({
        my: 'center top',
        at: 'center center',
        collision: 'fit',
        within: $('.ui-dialog-within-container')
    }, dialog.position());

    var top = dialog.cssPosition().top + 10;

    dialog.center({top: top});
    assert.deepEqual({
        my: 'center top',
        at: 'center top+' + top,
        collision: 'fit',
        within: $('.ui-dialog-within-container')
    }, dialog.position());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (position, no within container)', function(assert) {
    $('.ui-dialog-within-container').detach();
    assert.equal(true, Object.isEmpty($('.ui-dialog-within-container')));

    var dialog = new creme.dialog.Dialog();

    dialog.open();

    var position = dialog.position();

    assert.equal(position.my, 'center center');
    assert.equal(position.at, 'center center');
    assert.equal(position.collision, 'fit');
    assert.equal(position.within, undefined);

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (scroll)', function(assert) {
    var dialog = new creme.dialog.Dialog();
    assert.equal('frame', dialog.options.scroll);

    dialog.open();

    assert.equal(false, dialog._dialogBackground().is('.ui-dialog-scrollbackground'));
    assert.equal(true, dialog.dialog().css('overflow-y') !== 'hidden');

    dialog.close();

    dialog = new creme.dialog.Dialog({scroll: 'background'});
    assert.equal('background', dialog.options.scroll);

    dialog.open();

    assert.equal(true, dialog._dialogBackground().is('.ui-dialog-scrollbackground'));
    assert.equal('hidden', dialog.dialog().css('overflow-y'));

    dialog.close();

    assert.equal(false, dialog._dialogBackground().is('.ui-dialog-scrollbackground'));

    dialog.open({scroll: 'frame'});

    assert.equal(false, dialog._dialogBackground().is('.ui-dialog-scrollbackground'));
    assert.equal(true, dialog.dialog().css('overflow-y') !== 'hidden');

    dialog.close();

    this.assertRaises(function() {
        dialog.open({scroll: 'unknown'});
    }, Error, 'Error: scroll type "unknown" is invalid');

    this.assertRaises(function() {
        var d = new creme.dialog.Dialog({scroll: 'unknown2'});
        d.open();
    }, Error, 'Error: scroll type "unknown2" is invalid');
});

QUnit.test('creme.dialog.Dialog (resize)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    assert.equal(false, dialog.isOpened());
    assert.equal(undefined, dialog.size());
    assert.equal(640, dialog.options.width);
    assert.equal(350, dialog.options.height);

    dialog.resize(800, 600);

    assert.equal(undefined, dialog.size());
    assert.equal(640, dialog.options.width);
    assert.equal(350, dialog.options.height);

    dialog.open();

    assert.equal(true, dialog.isOpened());
    assert.deepEqual({width: 640, height: 350}, dialog.size());
    assert.equal(640, dialog.options.width);
    assert.equal(350, dialog.options.height);

    dialog.resize(800, 600);

    assert.deepEqual({width: 800, height: 600}, dialog.size());
    assert.equal(640, dialog.options.width);
    assert.equal(350, dialog.options.height);

    dialog.resizeToDefault();
    assert.deepEqual({width: 640, height: 350}, dialog.size());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (max size)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    assert.equal(false, dialog.isOpened());
    assert.equal(undefined, dialog.maxSize());

    dialog.maxSize({width: 800, height: 600});

    assert.equal(undefined, dialog.maxSize());

    dialog.open();

    assert.equal(true, dialog.isOpened());
    assert.deepEqual({width: null, height: 1024}, dialog.maxSize());

    dialog.maxSize({width: 800, height: 600});

    assert.deepEqual({width: 800, height: 600}, dialog.maxSize());

    dialog.resize(300, 400);
    assert.deepEqual({width: 300, height: 400}, dialog.size());

    dialog.resize(1024, 768);
    assert.deepEqual({width: 800, height: 600}, dialog.size());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (min size)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    assert.equal(false, dialog.isOpened());
    assert.equal(undefined, dialog.minSize());

    dialog.minSize({width: 800, height: 600});

    assert.equal(undefined, dialog.minSize());

    dialog.open();

    assert.equal(true, dialog.isOpened());
    assert.deepEqual({width: 150, height: 150}, dialog.minSize());

    dialog.minSize({width: 800, height: 600});

    assert.deepEqual({width: 800, height: 600}, dialog.minSize());

    dialog.resize(300, 400);
    assert.deepEqual({width: 800, height: 600}, dialog.size());

    dialog.resize(1024, 768);
    assert.deepEqual({width: 1024, height: 768}, dialog.size());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (autosize)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        width: 200,
        height: 100,
        fitFrame: true
    });

    dialog.open();

    assert.deepEqual({width: 200, height: 100}, dialog.size());

    var content = $('<div style="width: 300px;height: 300px;">&nbsp;</div>');
    assert.equal(300, content.outerWidth());
    assert.equal(300, content.outerHeight());

    dialog.fill(content);

    assert.equal(true, dialog.size().height > 300, 'height >= 300');
});

QUnit.test('creme.dialog.Dialog (autosize, disabled)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        width: 200,
        height: 100,
        fitFrame: false
    });

    dialog.open();

    assert.deepEqual({width: 200, height: 100}, dialog.size());

    var content = $('<div style="width: 300px;height: 300px;">&nbsp;</div>');
    assert.equal(300, content.outerWidth());
    assert.equal(300, content.outerHeight());

    dialog.fill(content);

    assert.deepEqual({width: 200, height: 100}, dialog.size());
});

QUnit.test('creme.dialog.Dialog.fitToFrameSize (closed dialog)', function(assert) {
    var dialog = new creme.dialog.Dialog({width: 200, height: 200});
    var content = $('<div class="mock-content"><h1 style="min-width: 500px; min-height: 400px;">This is a test</h1></div>');

    assert.equal(false, dialog.isOpened());

    dialog.fill(content);
    dialog.fitToFrameSize();  // do nothing
});

QUnit.test('creme.dialog.Dialog (titlebar, no titlebar, fill)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        title: 'Default title'
    });

    dialog.open();

    this.assertDialogTitleHtml('Default title');

    dialog.fill($(MOCK_FRAME_CONTENT_HATBAR));

    this.assertDialogTitleHtml('Default title');
});

QUnit.test('creme.dialog.Dialog (titlebar, disabled)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        title: 'Default title',
        useFrameTitleBar: false
    });

    dialog.open();

    this.assertDialogTitleHtml('Default title');

    dialog.fill($(MOCK_FRAME_CONTENT_TITLEBAR));

    this.assertDialogTitleHtml('Default title');

    dialog.fetch('mock/titlebar');

    this.assertDialogTitleHtml('Default title');
});

QUnit.test('creme.dialog.Dialog (titlebar, fill)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        title: 'Default title'
    });

    dialog.open();

    this.assertDialogTitleHtml('Default title');

    dialog.fill($(MOCK_FRAME_CONTENT_TITLEBAR.template({title: 'Title #1'})));

    this.assertDialogTitleHtml(
        '<div class="hat-bar-container ui-creme-dialog-titlebar">' +
            '<div class="hat-bar">' +
            '<div class="bar-icon"><img /></div>' +
            '<div class="bar-title"><h1>Mock Dialog Title #1</h1></div>' +
        '</div>');

    dialog.fill($(MOCK_FRAME_CONTENT_TITLEBAR.template({title: 'Title #154'})));

    this.assertDialogTitleHtml(
        '<div class="hat-bar-container ui-creme-dialog-titlebar">' +
            '<div class="hat-bar">' +
            '<div class="bar-icon"><img /></div>' +
            '<div class="bar-title"><h1>Mock Dialog Title #154</h1></div>' +
        '</div>');
});

QUnit.test('creme.dialog.Dialog (titlebar, no titlebar, fetch url)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        title: 'Default title'
    });

    dialog.open();

    this.assertOpenedDialog();
    this.assertDialogTitleHtml('Default title');

    dialog.fetch('mock/hatbar');

    this.assertDialogTitleHtml('Default title');
});

QUnit.test('creme.dialog.Dialog (titlebar, fetch url)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        title: 'Default title'
    });

    dialog.open();

    this.assertOpenedDialog();
    this.assertDialogTitleHtml('Default title');

    dialog.fetch('mock/titlebar');

    this.assertDialogTitleHtml(
        '<div class="hat-bar-container ui-creme-dialog-titlebar">' +
            '<div class="hat-bar">' +
            '<div class="bar-icon"><img /></div>' +
            '<div class="bar-title"><h1>Mock Dialog Title #1</h1></div>' +
        '</div>');

    dialog.fetch('mock/titlebar2');

    this.assertDialogTitleHtml(
        '<div class="hat-bar-container ui-creme-dialog-titlebar">' +
            '<div class="hat-bar">' +
            '<div class="bar-icon"><img /></div>' +
            '<div class="bar-title"><h1>Mock Dialog Title #2</h1></div>' +
        '</div>');
});

QUnit.test('creme.dialog.Dialog (scrollbackOnClose)', function(assert) {
    this.withScrollBackFaker(function(faker) {
        faker.result = 789;

        var dialog = new creme.dialog.Dialog().open();

        assert.equal(true, dialog.options.scrollbackOnClose);

        assert.deepEqual(faker.calls(), [
            []
        ]);
        assert.equal(789, dialog._scrollbackPosition);

        creme.utils.scrollBack(50);
        assert.deepEqual(faker.calls(), [
            [],
            [50]
        ]);

        dialog.close();
        assert.deepEqual(faker.calls(), [
            [],
            [50],
            [789, 'slow']
        ]);
    });
});

QUnit.test('creme.dialog.Dialog (scrollbackOnClose, disabled)', function(assert) {
    this.withScrollBackFaker(function(faker) {
        var dialog = new creme.dialog.Dialog({
            scrollbackOnClose: false
        });

        assert.equal(false, dialog.options.scrollbackOnClose);

        dialog.open();
        assert.deepEqual(faker.calls(), []);

        // close() always call creme.utils.scrollBack
        dialog.close();
        assert.deepEqual(faker.calls(), [
            [undefined, 'slow']
        ]);
    });
});

QUnit.test('creme.dialog.Dialog (closeOnEscape)', function(assert) {
    var dialog = new creme.dialog.Dialog().open();

    assert.equal(true, dialog.options.closeOnEscape);

    $(dialog.dialog()).trigger($.Event("keydown", {keyCode: $.ui.keyCode.ESCAPE}));
    assert.ok(dialog.isOpened() === false);
});

QUnit.test('creme.dialog.Dialog (closeOnEscape, disabled)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        closeOnEscape: false
    }).open();

    assert.equal(false, dialog.options.closeOnEscape);

    $(dialog.dialog()).trigger($.Event("keydown", {keyCode: $.ui.keyCode.ESCAPE}));
    assert.ok(dialog.isOpened() === true);

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (id)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        id: 'test-popup'
    }).open();

    assert.ok(dialog.isOpened() === true);
    assert.ok($('#test-popup').is('.ui-dialog-content') === true);
    assert.deepEqual($('#test-popup').data('uiCremeDialog'), dialog);

    dialog.close();
    assert.equal($('#test-popup').length, 0);
});

QUnit.test('creme.dialog.Dialog (jquery creme dialog methods)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        id: 'test-popup'
    }).open();

    assert.ok(dialog.isOpened() === true);
    assert.deepEqual($('#test-popup').dialog('cremeInstance'), dialog);
    $('#test-popup').dialog('fitToFrameSize');
    $('#test-popup').dialog('resize', 100, 100);

    dialog.close();
});

QUnit.test('creme.dialogs.image (url)', function(assert) {
    var dialog = creme.dialogs.image('data:image/png;base64, ' + RED_DOT_5x5_BASE64);
    var self = this;

    self.equalHtml('<div class="picture-wait">&nbsp;</div>', dialog.content());

    var done = assert.async();

    // deferred loading
    setTimeout(function() {
        self.equalHtml('<img src="data:image/png;base64, ' + RED_DOT_5x5_BASE64 + '" class="no-title">', dialog.content());
        done();
    }, 200);
});

QUnit.test('creme.dialogs.image (element)', function(assert) {
    var dialog = creme.dialogs.image($('<img src="nowhere" />'));
    this.equalHtml('<img src="nowhere" class="no-title"/>', dialog.content());
});

QUnit.parametrize('creme.dialogs.html', [
    [{}, {reloadCount: 0}],
    [{reloadOnClose: false}, {reloadCount: 0}],
    [{reloadOnClose: true}, {reloadCount: 1}]
], function(options, expected, assert) {
    var dialog = creme.dialogs.html('<p>This is a test</p>',  options);

    dialog.open();

    this.equalHtml('<p>This is a test</p>', dialog.content());
    dialog.close();

    assert.equal(this.mockReloadCalls().length, expected.reloadCount);
});

QUnit.parametrize('creme.dialogs.url', [
    ['', {}, {content: gettext('Bad Request'), fetchCount: 0, reloadCount: 0}],
    ['mock/error', {reloadOnClose: false}, {content: 'HTTP - Error 500', fetchCount: 1, reloadCount: 0}],
    ['mock/error', {reloadOnClose: true}, {content: 'HTTP - Error 500', fetchCount: 1, reloadCount: 1}],
    ['mock/html', {reloadOnClose: false}, {content: 'This a frame test', fetchCount: 1, reloadCount: 0}],
    ['mock/html', {reloadOnClose: true}, {content: 'This a frame test', fetchCount: 1, reloadCount: 1}]
], function(url, options, expected, assert) {
    var dialog = creme.dialogs.url(url, options);

    assert.equal(this.mockBackendCalls().length, expected.fetchCount);
    assert.equal(this.mockReloadCalls().length, 0);
    assert.ok(dialog.content().html().indexOf(expected.content) !== -1);

    dialog.open();
    assert.equal(this.mockReloadCalls().length, 0);

    dialog.close();
    assert.equal(this.mockReloadCalls().length, expected.reloadCount);
});

}(jQuery));
