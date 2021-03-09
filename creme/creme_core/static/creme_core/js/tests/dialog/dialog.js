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

    equal(undefined, dialog.validator());
    equal(undefined, dialog.selector());

    deepEqual([], this.mockListenerCalls('ok'));
    deepEqual([], this.mockListenerCalls('close'));

    dialog.ok();

    deepEqual([['ok', []]], this.mockListenerCalls('ok'));
    deepEqual([], this.mockListenerCalls('close'));

    this.resetMockListenerCalls();

    dialog.close();

    deepEqual([], this.mockListenerCalls('ok'));
    deepEqual([['close', dialog.options]], this.mockListenerCalls('close'));
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

    equal(undefined, dialog.validator());
    equal(selector, dialog.selector());

    deepEqual([], this.mockListenerCalls('ok'));
    deepEqual([], this.mockListenerCalls('close'));

    dialog.ok();

    deepEqual([['ok', 'b']], this.mockListenerCalls('ok'));
    deepEqual([], this.mockListenerCalls('close'));

    this.resetMockListenerCalls();

    dialog.close();

    deepEqual([], this.mockListenerCalls('ok'));
    deepEqual([['close', dialog.options]], this.mockListenerCalls('close'));
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

    equal(validator, dialog.validator());
    equal(selector, dialog.selector());

    deepEqual([], this.mockListenerCalls('ok'));
    deepEqual([], this.mockListenerCalls('close'));

    deepEqual([], $('select', dialog.content()).val());
    dialog.ok();

    // no selection, not valid
    deepEqual([], this.mockListenerCalls('ok'));
    deepEqual([], this.mockListenerCalls('close'));

    $('select', dialog.content()).val('2');
    dialog.ok();

    deepEqual([['ok', ['2']]], this.mockListenerCalls('ok'));
    deepEqual([], this.mockListenerCalls('close'));

    this.resetMockListenerCalls();

    dialog.close();

    deepEqual([], this.mockListenerCalls('ok'));
    deepEqual([['close', dialog.options]], this.mockListenerCalls('close'));
});

QUnit.test('creme.dialog.Dialog (open/close)', function(assert) {
    var dialog = new creme.dialog.Dialog({url: 'mock/html', backend: this.backend});
    dialog.onOpen(this.mockListener('opened'));
    dialog.onClose(this.mockListener('closed'));

    deepEqual([], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    equal(false, dialog.isOpened());
    equal(false, dialog._isClosing);

    dialog.open();

    equal(true, dialog.isOpened());
    equal(false, dialog._isClosing);

    this.assertRaises(function() {
        dialog.open();
    }, Error, 'Error: dialog already opened !');

    dialog.close();

    equal(false, dialog.isOpened());
    equal(false, dialog._isClosing);
});

QUnit.test('creme.dialog.Dialog (url)', function(assert) {
    var dialog = new creme.dialog.Dialog({url: 'mock/html', backend: this.backend});
    dialog.on('frame-activated', this.mockListener('frame-activated'));
    dialog.onOpen(this.mockListener('opened'));
    dialog.onClose(this.mockListener('closed'));

    deepEqual([], this.mockListenerCalls('frame-activated'));
    deepEqual([], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    dialog.open();

    equal('mock/html', dialog.frame().lastFetchUrl());
    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    equal(MOCK_FRAME_CONTENT, dialog.content().html());

    dialog.close();

    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    deepEqual([['close', dialog.options]], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Dialog (url, invalid)', function(assert) {
    var dialog = new creme.dialog.Dialog({url: 'mock/unknown', backend: this.backend});
    dialog.on('frame-activated', this.mockListener('frame-activated'));
    dialog.onOpen(this.mockListener('opened'));
    dialog.onClose(this.mockListener('closed'));

    deepEqual([], this.mockListenerCalls('frame-activated'));
    deepEqual([], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    dialog.open();

    equal(undefined, dialog.frame().lastFetchUrl());

    deepEqual([], this.mockListenerCalls('frame-activated'));
    deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    equal(1, dialog.content().find('.ui-creme-overlay[status="404"]').length);

    dialog.close();

    deepEqual([], this.mockListenerCalls('frame-activated'));
    deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    deepEqual([['close', dialog.options]], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Dialog (html, widget)', function(assert) {
    var dialog = new creme.dialog.Dialog({html: MOCK_FRAME_CONTENT_WIDGET});
    dialog.on('frame-activated', this.mockListener('frame-activated'));
    dialog.onOpen(this.mockListener('opened'));
    dialog.onClose(this.mockListener('closed'));

    deepEqual([], this.mockListenerCalls('frame-activated'));
    deepEqual([], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    dialog.open();

    equal(undefined, dialog.frame().lastFetchUrl());

    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    deepEqual([], this.mockListenerCalls('closed'));

    equal(1, dialog.content().find('.ui-creme-widget').length);
    equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.close();

    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    deepEqual([['close', dialog.options]], this.mockListenerCalls('closed'));
});

QUnit.test('creme.dialog.Dialog (widget, fill static)', function(assert) {
    var dialog = new creme.dialog.Dialog();
    dialog.on('frame-activated', this.mockListener('frame-activated'));
    dialog.onOpen(this.mockListener('opened'));
    dialog.onClose(this.mockListener('closed'));

    dialog.open();

    deepEqual([], this.mockListenerCalls('frame-activated'), 'activated, not opened');
    deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));
    equal(0, dialog.content().find('.ui-creme-widget').length);

    // already opened, frame widgets are immediately activated
    dialog.fill(MOCK_FRAME_CONTENT_WIDGET);

    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'), 'activated, after fill');
    deepEqual([['open', dialog.options]], this.mockListenerCalls('opened'));

    equal(1, dialog.content().find('.ui-creme-widget').length);
    equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.close();
    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'), 'activated, after close');
    equal(0, dialog.content().find('.ui-creme-widget').length);
});

QUnit.test('creme.dialog.Dialog (widget, fill static, not opened)', function(assert) {
    var dialog = new creme.dialog.Dialog();
    dialog.on('frame-activated', this.mockListener('frame-activated'));

    dialog.fill(MOCK_FRAME_CONTENT_WIDGET);

    // not opened, frame widgets activation is deferred until opening
    deepEqual([], this.mockListenerCalls('frame-activated'));
    equal(1, dialog.content().find('.ui-creme-widget').length);
    equal(0, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.open();

    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    equal(1, dialog.content().find('.ui-creme-widget').length);
    equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.close();

    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    equal(0, dialog.content().find('.ui-creme-widget').length);
});

QUnit.test('creme.dialog.Dialog (widget, fetch url)', function(assert) {
    var dialog = new creme.dialog.Dialog({backend: this.backend});
    dialog.on('frame-activated', this.mockListener('frame-activated'));

    dialog.open();
    deepEqual([], this.mockListenerCalls('frame-activated'));
    equal(0, dialog.content().find('.ui-creme-widget').length);

    dialog.fetch('mock/widget');
    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    equal(1, dialog.content().find('.ui-creme-widget').length);
    equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.close();
    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    equal(0, dialog.content().find('.ui-creme-widget').length);
});

QUnit.test('creme.dialog.Dialog (widget, fetch url, reactivate)', function(assert) {
    var dialog = new creme.dialog.Dialog({backend: this.backend});
    dialog.on('frame-activated', this.mockListener('frame-activated'));

    dialog.open();
    deepEqual([], this.mockListenerCalls('frame-activated'));
    equal(0, dialog.content().find('.ui-creme-widget').length);

    dialog.fetch('mock/widget');
    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'), 'first fetch');
    equal(1, dialog.content().find('.ui-creme-widget').length);
    equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.fetch('mock/widget');
    deepEqual([
        ['frame-activated', dialog.frame()],
        ['frame-activated', dialog.frame()]
    ], this.mockListenerCalls('frame-activated'), 'second fetch');
    equal(1, dialog.content().find('.ui-creme-widget').length);
    equal(1, dialog.content().find('.ui-creme-widget.widget-ready').length);

    dialog.close();
    deepEqual([
        ['frame-activated', dialog.frame()],
        ['frame-activated', dialog.frame()]
    ], this.mockListenerCalls('frame-activated'), 'close');
    equal(0, dialog.content().find('.ui-creme-widget').length);
});

QUnit.test('creme.dialog.Dialog (default button)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    equal(0, dialog.buttons().find('button').length);

    dialog.open();

    equal(1, dialog.buttons().find('button').length);
    equal(gettext('Close'), dialog.button('close').text());

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

    equal(0, dialog.buttons().find('button').length);

    dialog.open();

    equal(1, dialog.buttons().find('button').length);
    equal('Too Close', dialog.button('close').text());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (action links, fill)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    dialog.fill(MOCK_FRAME_CONTENT_ACTION);

    equal(0, dialog.buttons().find('button').length);

    dialog.open();

    equal(4, dialog.buttons().find('button').length);
    equal(gettext('Action 1'), dialog.button('action-1').text());
    equal(gettext('Action'), dialog.button('link-1').text());
    equal(gettext('Action 3'), dialog.button('link-2').text());
    equal(gettext('Close'), dialog.button('close').text());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (action links, fetch url)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    dialog.fetch('mock/actions');

    equal(0, dialog.buttons().find('button').length);

    dialog.open();

    equal(4, dialog.buttons().find('button').length);
    equal(gettext('Action 1'), dialog.button('action-1').text());
    equal(gettext('Action'), dialog.button('link-1').text());
    equal(gettext('Action 3'), dialog.button('link-2').text());
    equal(gettext('Close'), dialog.button('close').text());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (action links, disabled)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        useFrameActions: false
    });

    dialog.fill(MOCK_FRAME_CONTENT_ACTION);

    equal(0, dialog.buttons().find('button').length);

    dialog.open();

    equal(1, dialog.buttons().find('button').length);
    equal(gettext('Close'), dialog.button('close').text());

    dialog.fetch('mock/actions');

    equal(1, dialog.buttons().find('button').length);
    equal(gettext('Close'), dialog.button('close').text());
});

QUnit.test('creme.dialog.Dialog (title)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        title: 'Default title'
    });

    dialog.open();

    equal('Default title', dialog.title());
    this.assertDialogTitleHtml('Default title');

    dialog.title('Modified title');

    equal('Modified title', dialog.title());
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

    equal('Default\u00A0title & < escaped>', dialog.title());
    this.assertDialogTitleHtml('Default\u00A0title & < escaped>');

    dialog.title('Modified title &quot;escaped&quot;');

    equal('Modified title "escaped"', dialog.title());
    this.assertDialogTitleHtml('Modified title "escaped"');
});

QUnit.test('creme.dialog.Dialog (clear)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    equal('', dialog.content().html());

    dialog.clear();
    equal('', dialog.content().html());

    dialog.fill(MOCK_FRAME_CONTENT);
    equal(MOCK_FRAME_CONTENT, dialog.content().html());

    dialog.clear();
    equal('', dialog.content().html());
});

QUnit.test('creme.dialog.Dialog (dialog)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    equal(false, dialog.isOpened());
    equal(undefined, dialog.dialog());

    dialog.open();

    equal(true, dialog.isOpened());
    ok(dialog.dialog() !== undefined);

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (center)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    dialog.center();

    equal(false, dialog.isOpened());
    equal(undefined, dialog.position());
    equal(undefined, dialog.cssPosition());

    dialog.open();
    dialog.center();

    equal(true, dialog.isOpened());
    deepEqual({
        my: 'center center',
        at: 'center center',
        collision: 'fit',
        within: $('.ui-dialog-within-container')
    }, dialog.position());

    dialog.center({top: 5});
    deepEqual({
        my: 'center center',
        at: 'center center',
        collision: 'fit',
        within: $('.ui-dialog-within-container')
    }, dialog.position());

    dialog.position({my: 'center top', at: 'center center'});
    deepEqual({
        my: 'center top',
        at: 'center center',
        collision: 'fit',
        within: $('.ui-dialog-within-container')
    }, dialog.position());

    var top = dialog.cssPosition().top + 10;

    dialog.center({top: top});
    deepEqual({
        my: 'center top',
        at: 'center top+' + top,
        collision: 'fit',
        within: $('.ui-dialog-within-container')
    }, dialog.position());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (position, no within container)', function(asser) {
    $('.ui-dialog-within-container').detach();
    equal(true, Object.isEmpty($('.ui-dialog-within-container')));

    var dialog = new creme.dialog.Dialog();

    dialog.open();

    var position = dialog.position();

    equal(position.my, 'center center');
    equal(position.at, 'center center');
    equal(position.collision, 'fit');
    equal(position.within, undefined);

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (scroll)', function(assert) {
    var dialog = new creme.dialog.Dialog();
    equal('frame', dialog.options.scroll);

    dialog.open();

    equal(false, dialog._dialogBackground().is('.ui-dialog-scrollbackground'));
    equal(true, dialog.dialog().css('overflow-y') !== 'hidden');

    dialog.close();

    dialog = new creme.dialog.Dialog({scroll: 'background'});
    equal('background', dialog.options.scroll);

    dialog.open();

    equal(true, dialog._dialogBackground().is('.ui-dialog-scrollbackground'));
    equal('hidden', dialog.dialog().css('overflow-y'));

    dialog.close();

    equal(false, dialog._dialogBackground().is('.ui-dialog-scrollbackground'));

    dialog.open({scroll: 'frame'});

    equal(false, dialog._dialogBackground().is('.ui-dialog-scrollbackground'));
    equal(true, dialog.dialog().css('overflow-y') !== 'hidden');

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

    equal(false, dialog.isOpened());
    equal(undefined, dialog.size());
    equal(640, dialog.options.width);
    equal(350, dialog.options.height);

    dialog.resize(800, 600);

    equal(undefined, dialog.size());
    equal(640, dialog.options.width);
    equal(350, dialog.options.height);

    dialog.open();

    equal(true, dialog.isOpened());
    deepEqual({width: 640, height: 350}, dialog.size());
    equal(640, dialog.options.width);
    equal(350, dialog.options.height);

    dialog.resize(800, 600);

    deepEqual({width: 800, height: 600}, dialog.size());
    equal(640, dialog.options.width);
    equal(350, dialog.options.height);

    dialog.resizeToDefault();
    deepEqual({width: 640, height: 350}, dialog.size());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (max size)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    equal(false, dialog.isOpened());
    equal(undefined, dialog.maxSize());

    dialog.maxSize({width: 800, height: 600});

    equal(undefined, dialog.maxSize());

    dialog.open();

    equal(true, dialog.isOpened());
    deepEqual({width: null, height: null}, dialog.maxSize());

    dialog.maxSize({width: 800, height: 600});

    deepEqual({width: 800, height: 600}, dialog.maxSize());

    dialog.resize(300, 400);
    deepEqual({width: 300, height: 400}, dialog.size());

    dialog.resize(1024, 768);
    deepEqual({width: 800, height: 600}, dialog.size());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (min size)', function(assert) {
    var dialog = new creme.dialog.Dialog();

    equal(false, dialog.isOpened());
    equal(undefined, dialog.minSize());

    dialog.minSize({width: 800, height: 600});

    equal(undefined, dialog.minSize());

    dialog.open();

    equal(true, dialog.isOpened());
    deepEqual({width: 150, height: 150}, dialog.minSize());

    dialog.minSize({width: 800, height: 600});

    deepEqual({width: 800, height: 600}, dialog.minSize());

    dialog.resize(300, 400);
    deepEqual({width: 800, height: 600}, dialog.size());

    dialog.resize(1024, 768);
    deepEqual({width: 1024, height: 768}, dialog.size());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (autosize)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        width: 200,
        height: 100,
        fitFrame: true
    });

    dialog.open();

    deepEqual({width: 200, height: 100}, dialog.size());

    var content = $('<div style="width: 300px;height: 300px;">&nbsp;</div>');
    equal(300, content.outerWidth());
    equal(300, content.outerHeight());

    dialog.fill(content);

    equal(true, dialog.size().height > 300, 'height >= 300');
});

QUnit.test('creme.dialog.Dialog (autosize, disabled)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        width: 200,
        height: 100,
        fitFrame: false
    });

    dialog.open();

    deepEqual({width: 200, height: 100}, dialog.size());

    var content = $('<div style="width: 300px;height: 300px;">&nbsp;</div>');
    equal(300, content.outerWidth());
    equal(300, content.outerHeight());

    dialog.fill(content);

    deepEqual({width: 200, height: 100}, dialog.size());
});

QUnit.test('creme.dialog.Dialog.fitToFrameSize (closed dialog)', function(assert) {
    var dialog = new creme.dialog.Dialog({width: 200, height: 200});
    var content = $('<div class="mock-content"><h1 style="min-width: 500px; min-height: 400px;">This is a test</h1></div>');

    equal(false, dialog.isOpened());

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


QUnit.test('creme.dialogs.Dialog (scrollbackOnClose)', function(assert) {
    this.withScrollBackFaker(function(faker) {
        faker.result = 789;

        var dialog = new creme.dialog.Dialog().open();

        equal(true, dialog.options.scrollbackOnClose);

        deepEqual(faker.calls(), [
            []
        ]);
        equal(789, dialog._scrollbackPosition);

        creme.utils.scrollBack(50);
        deepEqual(faker.calls(), [
            [],
            [50]
        ]);

        dialog.close();
        deepEqual(faker.calls(), [
            [],
            [50],
            [789, 'slow']
        ]);
    });
});


QUnit.test('creme.dialogs.Dialog (scrollbackOnClose, disabled)', function(assert) {
    this.withScrollBackFaker(function(faker) {
        var dialog = new creme.dialog.Dialog({
            scrollbackOnClose: false
        });

        equal(false, dialog.options.scrollbackOnClose);

        dialog.open();
        deepEqual(faker.calls(), []);

        // close() always call creme.utils.scrollBack
        dialog.close();
        deepEqual(faker.calls(), [
            [undefined, 'slow']
        ]);
    });
});


QUnit.test('creme.dialogs.Dialog (closeOnEscape)', function(assert) {
    var dialog = new creme.dialog.Dialog().open();

    equal(true, dialog.options.closeOnEscape);

    $(dialog.dialog()).trigger($.Event("keydown", {keyCode: $.ui.keyCode.ESCAPE}));
    ok(dialog.isOpened() === false);
});


QUnit.test('creme.dialogs.Dialog (closeOnEscape, disabled)', function(assert) {
    var dialog = new creme.dialog.Dialog({
        closeOnEscape: false
    }).open();

    equal(false, dialog.options.closeOnEscape);

    $(dialog.dialog()).trigger($.Event("keydown", {keyCode: $.ui.keyCode.ESCAPE}));
    ok(dialog.isOpened() === true);

    dialog.close();
});

QUnit.test('creme.dialogs.image (url)', function(assert) {
    var dialog = creme.dialogs.image('data:image/png;base64, ' + RED_DOT_5x5_BASE64);
    var self = this;

    self.equalHtml('<div class="picture-wait">&nbsp;</div>', dialog.content());

    stop(1);

    // deferred loading
    setTimeout(function() {
        self.equalHtml('<img src="data:image/png;base64, ' + RED_DOT_5x5_BASE64 + '" class="no-title">', dialog.content());
        start();
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

    equal(this.mockReloadCalls().length, expected.reloadCount);
});

QUnit.parametrize('creme.dialogs.url', [
    ['', {}, {content: 'Bad Request', fetchCount: 0, reloadCount: 0}],
    ['mock/error', {reloadOnClose: false}, {content: 'HTTP - Error 500', fetchCount: 1, reloadCount: 0}],
    ['mock/error', {reloadOnClose: true}, {content: 'HTTP - Error 500', fetchCount: 1, reloadCount: 1}],
    ['mock/html', {reloadOnClose: false}, {content: 'This a frame test', fetchCount: 1, reloadCount: 0}],
    ['mock/html', {reloadOnClose: true}, {content: 'This a frame test', fetchCount: 1, reloadCount: 1}]
], function(url, options, expected, assert) {
    var dialog = creme.dialogs.url(url, options);

    equal(this.mockBackendCalls().length, expected.fetchCount);
    equal(this.mockReloadCalls().length, 0);
    ok(dialog.content().html().indexOf(expected.content) !== -1);

    dialog.open();
    equal(this.mockReloadCalls().length, 0);

    dialog.close();
    equal(this.mockReloadCalls().length, expected.reloadCount);
});

}(jQuery));
