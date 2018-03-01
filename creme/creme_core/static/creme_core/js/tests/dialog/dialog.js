(function($) {

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

var MOCK_FRAME_CONTENT_FORM = '<form action="mock/submit">' +
                                   '<input type="text" name="firstname"></input>' +
                                   '<input type="text" name="lastname" required></input>' +
                                   '<input type="submit" class="ui-creme-dialog-action"></input>' +
                               '</form>';
var MOCK_FRAME_CONTENT_FORM_REQUIRED = '<form action="mock/submit">' +
                                           '<input type="text" name="firstname" required></input>' +
                                           '<input type="text" name="lastname" required></input>' +
                                           '<input type="submit" class="ui-creme-dialog-action"></input>' +
                                       '</form>';
var MOCK_FRAME_CONTENT_FORM_BUTTON = '<form action="mock/submit/button">' +
                                         '<input type="text" name="firstname"></input>' +
                                         '<input type="text" name="lastname" required></input>' +
                                         '<button type="submit" class="ui-creme-dialog-action"></button>' +
                                     '</form>';

var MOCK_FRAME_CONTENT_FORM_MULTI = '<form action="mock/submit/multi">' +
                                        '<input type="text" name="firstname"></input>' +
                                        '<input type="text" name="lastname" required></input>' +
                                        '<input type="submit" value="Submit !"></input>' +
                                        '<input class="ui-creme-dialog-action" type="submit" value="Button A"></input>' +
                                        '<button class="ui-creme-dialog-action" type="submit" value="bbb">Button B</button>' +
                                        '<input class="ui-creme-dialog-action" type="submit" name="send-c" value="Button C"></input>' +
                                        '<button class="ui-creme-dialog-action" type="submit" name="button-d">Button D</button>' +
                                        '<button class="ui-creme-dialog-action" type="submit" name="button-e" value="eee">Button E</button>' +
                                   '</form>';

var MOCK_FRAME_CONTENT_FORM_MULTI_UNNAMED = '<form action="mock/submit/multi">' +
                                                '<input type="text" id="firstname"></input>' +
                                                '<input type="text" id="lastname" required></input>' +
                                                '<input type="submit" class="ui-creme-dialog-action"></input>' +
                                                '<input type="submit" class="ui-creme-dialog-action"></input>' +
                                                '<button class="ui-creme-dialog-action" type="submit"></button>' +
                                                '<button class="ui-creme-dialog-action" type="submit"></button>' +
                                            '</form>';

var MOCK_FRAME_CONTENT_FORM_JSON = '<form action="mock/submit/json">' +
                                        '<input type="text" name="responseType"></input>' +
                                        '<input type="submit" class="ui-creme-dialog-action"></input>' +
                                   '</form>';

var MOCK_FRAME_CONTENT_SUBMIT_JSON = '<json>' + $.toJSON({value: 1, added: [1, 'John Doe']}) + '</json>';
var MOCK_FRAME_CONTENT_SUBMIT_JSON_PRE = '<pre style="word-wrap: break-word; white-space: pre-wrap;">' + $.toJSON({value: 2, added: [5, 'John Pre']}) + '</pre>';
var MOCK_FRAME_CONTENT_SUBMIT_JSON_NOTAG = $.toJSON({value:3, added:[-8, 'John NoTag']});
var MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID = '<json>' + '{"value":1, added:[1, "John Doe"}' + '</json>';

QUnit.module("creme.dialog.js", new QUnitMixin(QUnitEventMixin, QUnitAjaxMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({delay: 0, sync: true, name: 'creme.dialog.js'});
    },

    beforeEach: function() {
        var self = this;
        var backend = this.backend;

        $('<div class="ui-dialog-within-container"></div>').appendTo('body');

        this.setMockBackendGET({
            'mock/html': this.backend.response(200, MOCK_FRAME_CONTENT),
            'mock/html2': this.backend.response(200, MOCK_FRAME_CONTENT_LIST),
            'mock/widget': this.backend.response(200, MOCK_FRAME_CONTENT_WIDGET),
            'mock/submit': this.backend.response(200, MOCK_FRAME_CONTENT_FORM),
            'mock/submit/json': this.backend.response(200, MOCK_FRAME_CONTENT_FORM_JSON),
            'mock/submit/button': this.backend.response(200, MOCK_FRAME_CONTENT_FORM_BUTTON),
            'mock/submit/required': this.backend.response(200, MOCK_FRAME_CONTENT_FORM_REQUIRED),
            'mock/submit/multi': this.backend.response(200, MOCK_FRAME_CONTENT_FORM_MULTI),
            'mock/submit/multi/unnamed': this.backend.response(200, MOCK_FRAME_CONTENT_FORM_MULTI_UNNAMED),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500')
        });

        this.setMockBackendPOST({
            'mock/submit/json': function(url, data, options) {
                var responseType = data.responseType[0];
                if (responseType === 'pre') {
                    return backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON_PRE);
                } else if (responseType === 'notag') {
                    return backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON_NOTAG);
                } else if (responseType === 'invalid') {
                    return backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID);
                } else if (responseType === 'empty') {
                    return backend.response(200, '')
                } else {
                    return backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON);
                }
            },
            'mock/submit': this.backend.response(200, MOCK_FRAME_CONTENT_FORM),
            'mock/submit/required': this.backend.response(200, MOCK_FRAME_CONTENT_FORM_REQUIRED),
            'mock/submit/button': this.backend.response(200, MOCK_FRAME_CONTENT_FORM_BUTTON),
            'mock/submit/multi': this.backend.response(200, MOCK_FRAME_CONTENT_FORM_MULTI),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500')
        });
    },

    afterEach: function() {
        $('.ui-dialog-content').dialog('destroy');
        creme.widget.shutdown($('body'));
        $('.ui-dialog-within-container').detach();
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

    equal(null, $('select', dialog.content()).val());
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

QUnit.test('creme.dialog.Dialog (url)', function(assert) {
    var dialog = new creme.dialog.Dialog({url: 'mock/html', backend: this.backend});
    dialog.on('frame-activated', this.mockListener('frame-activated'));

    dialog.open();

    equal('mock/html', dialog.frame().lastFetchUrl());
    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'));
    equal(MOCK_FRAME_CONTENT, dialog.content().html());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (widget, fill static)', function(assert) {
    var dialog = new creme.dialog.Dialog();
    dialog.on('frame-activated', this.mockListener('frame-activated'));

    dialog.open();

    deepEqual([], this.mockListenerCalls('frame-activated'), 'activated, not opened');
    equal(0, dialog.content().find('.ui-creme-widget').length);

    // already opened, frame widgets are immediately activated
    dialog.fill(MOCK_FRAME_CONTENT_WIDGET);

    deepEqual([['frame-activated', dialog.frame()]], this.mockListenerCalls('frame-activated'), 'activated, after fill');
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

    dialog.close();
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

QUnit.test('creme.dialog.Dialog (action links)', function(assert) {
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

    dialog.close();
});

QUnit.test('creme.dialog.Dialog.fitToFrameSize (closed dialog)', function(assert) {
    var dialog = new creme.dialog.Dialog({width: 200, height: 200});
    var content = $('<div class="mock-content"><h1 style="min-width: 500px; min-height: 400px;">This is a test</h1></div>');

    equal(false, dialog.isOpened());

    dialog.fill(content);
    dialog.fitToFrameSize();  // do nothing
});

QUnit.test('creme.dialog.FormDialog (default validator)', function(assert) {
    var options = {validator: 'default'};
    var dialog = new creme.dialog.FormDialog(options);

    equal(dialog._defaultValidator, dialog.validator());
    equal(true, dialog._validate('', 'success', 'text/html'));
    equal(true, dialog._validate('<div></div>', 'success', 'text/html'));

    equal(false, dialog._validate('<div><form></form></div>', 'success', 'text/html'));
    equal(true, dialog._validate('"<div><form></form></div>"', 'success', 'text/json'));
});

QUnit.test('creme.dialog.FormDialog (compatible validator)', function(assert) {
    var options = {validator: 'innerpopup'};
    var dialog = new creme.dialog.FormDialog(options);

    equal(dialog._compatibleValidator, dialog.validator());
    equal(true, dialog._validate('', 'success', 'text/html'));
    equal(false, dialog._validate('<div></div>', 'success', 'text/html'));
    equal(true, dialog._validate('<div class="in-popup"></div>', 'success', 'text/html'));
    equal(true, dialog._validate('<div class="in-popup" closing="true"></div>', 'success', 'text/html'));
    equal(true, dialog._validate('<div class="in-popup" reload="/" closing="true"></div>', 'success', 'text/html'));
    equal(true, dialog._validate('<div closing="true" class="in-popup"></div>', 'success', 'text/html'));
    equal(true, dialog._validate('<div  closing="true"  reload="/"   class="in-popup"></div>', 'success', 'text/html'));

    equal(false, dialog._validate('<div><form></form></div>', 'success', 'text/html'));
    equal(true, dialog._validate('<div class="in-popup" closing="true"><form></form></div>', 'success', 'text/html'), 'closing+form');
    equal(true, dialog._validate('<div closing="true" class="in-popup"><form></form></div>', 'success', 'text/html'));

    equal(true, dialog._validate('"<div><form></form></div>"', 'success', 'text/json'));
});

QUnit.test('creme.dialog.FormDialog (custom validator)', function(assert) {
    var validateAll = function() {
        return true;
    };
    var options = {validator: validateAll};
    var dialog = new creme.dialog.FormDialog(options);

    equal(validateAll, dialog.validator());
    equal(true, dialog._validate('', 'success', 'text/html'));
    equal(true, dialog._validate('<div></div>', 'success', 'text/html'));
    equal(true, dialog._validate('<div><form></form></div>', 'success', 'text/html'));
    equal(true, dialog._validate('"<div><form></form></div>"', 'success', 'text/json'));
});

QUnit.test('creme.dialog.FormDialog (invalid validator)', function(assert) {
    var options = {validator: 'string'};
    var dialog = new creme.dialog.FormDialog(options);

    // if not a function, use default validator.
    equal(dialog._defaultValidator, dialog.validator());

    this.assertRaises(function() {
        dialog.validator('string');
    }, Error, 'Error: validator is not a function');
});

QUnit.test('creme.dialog.FormDialog (default button, empty form)', function(assert) {
    var dialog = new creme.dialog.FormDialog();
    dialog.on('frame-activated', this.mockListener('frame-activated'));

    dialog.open();
    deepEqual([], this.mockListenerCalls('frame-activated')); // nothing to activate

    equal(1, dialog.buttons().find('button').length);
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.close();
    deepEqual([], this.mockListenerCalls('frame-activated'));
});

QUnit.test('creme.dialog.FormDialog (default button, unamed submit input)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.close();
});

QUnit.test('creme.dialog.FormDialog (default button, unamed submit input + click cancel)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.button('cancel').click();
    equal(false, dialog.isOpened());
});

QUnit.test('creme.dialog.FormDialog (default button, unamed submit button)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/button', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.close();
});

QUnit.test('creme.dialog.FormDialog (default button, multiple unamed submit)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/multi/unnamed', backend: this.backend});

    dialog.open();

    equal(4, dialog.buttons().find('button').length);

    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Save'), dialog.button('send-1').text());
    equal(gettext('Save'), dialog.button('send-2').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.close();
});

QUnit.test('creme.dialog.FormDialog (multiple submit input/buttons)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/multi', backend: this.backend});

    dialog.open();

    equal(6, dialog.buttons().find('button').length);
    equal(gettext('Cancel'), dialog.button('cancel').text());

    equal('Button A', dialog.button('send').text());
    equal('Button B', dialog.button('send-bbb').text());   // unamed button with value "bbb"
    equal('Button C', dialog.button('send-c').text());     // input named "button-c"
    equal('Button D', dialog.button('button-d').text());   // button named "button-d"
    equal('Button E', dialog.button('button-e').text());   // button named "button-e" with value "eee"

    dialog.close();
});

QUnit.test('creme.dialog.FormDialog (submit)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/button', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is(':invalid'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.submit();

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (submit lastname required)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/button', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.submit();

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(true, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (submit all required)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/required', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/required'));

    dialog.submit();

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(true, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/required'));

    dialog.form().find('[name="firstname"]').val('');
    dialog.form().find('[name="lastname"]').val('Doe');

    dialog.submit();

    equal(true, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(true, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(false, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/required'));
});

QUnit.test('creme.dialog.FormDialog (submit + form[novalidate])', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/button', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().attr('novalidate', 'novalidate');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.submit();

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: [''],
            lastname: ['']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});


QUnit.test('creme.dialog.FormDialog (submit + options.noValidate)', function(assert) {
    var dialog = new creme.dialog.FormDialog({
        url: 'mock/submit/button',
        backend: this.backend,
        noValidate: true
    });

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.submit();

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: [''],
            lastname: ['']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (submit + extra data)', function(assert) {
    var dialog = new creme.dialog.FormDialog({
        url: 'mock/submit/button',
        backend: this.backend,
        submitData: {
            extra: 12,
            other: 'test'
        }
    });

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.submit();

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe'],
            extra: [12],
            other: ['test']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    dialog.submit({}, {
        extra: 78,
        custom: true,
        lastname: 'Toe'
    });

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe'],
            extra: [12],
            other: ['test']
        }],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe', 'Toe'],
            extra: [78],
            other: ['test'],
            custom: [true]
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));

});

QUnit.test('creme.dialog.FormDialog (click + submit)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/button', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is(':invalid'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.button('send').click();

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe'],
            send: ['']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (prevent multiple submit click)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/button', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(false, dialog.button('send').is('.ui-state-disabled'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.button('send').click();
    dialog.button('send').click();
    dialog.button('send').click();
    dialog.button('send').click();
    dialog.button('send').click();

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe'],
            send: ['']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (<json>JSON</json> response)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/json', backend: this.backend});

    dialog.onFormSuccess(this.mockListener('form-success'));
    dialog.open();

    dialog.submit();

    deepEqual([
        ['GET', {}],
        ['POST', {
            responseType: ['']
        }]
    ], this.mockBackendUrlCalls('mock/submit/json'));

    deepEqual([
        ['form-success', $.toJSON({value: 1, added: [1, 'John Doe']}), 'ok', 'text/json']
    ], this.mockListenerCalls('form-success'));
});

QUnit.test('creme.dialog.FormDialog (<pre>JSON</pre> response)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/json', backend: this.backend});

    dialog.onFormSuccess(this.mockListener('form-success'));
    dialog.open();

    dialog.form().find('[name="responseType"]').val('pre');
    dialog.submit();

    deepEqual([
        ['GET', {}],
        ['POST', {
            responseType: ['pre']
        }]
    ], this.mockBackendUrlCalls('mock/submit/json'));

    deepEqual([
        ['form-success', $.toJSON({value: 2, added: [5, 'John Pre']}), 'ok', 'text/json']
    ], this.mockListenerCalls('form-success'));
});

QUnit.test('creme.dialog.FormDialog (JSON response)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/json', backend: this.backend});

    dialog.onFormSuccess(this.mockListener('form-success'));
    dialog.open();

    dialog.form().find('[name="responseType"]').val('notag');
    dialog.submit();

    deepEqual([
        ['GET', {}],
        ['POST', {
            responseType: ['notag']
        }]
    ], this.mockBackendUrlCalls('mock/submit/json'));

    deepEqual([
        ['form-success', $.toJSON({value: 3, added: [-8, 'John NoTag']}), 'ok', 'text/json']
    ], this.mockListenerCalls('form-success'));
});

QUnit.test('creme.dialog.FormDialog (invalid JSON response)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/json', backend: this.backend});

    dialog.onFormSuccess(this.mockListener('form-success'));
    dialog.open();

    dialog.form().find('[name="responseType"]').val('invalid');
    dialog.submit();

    deepEqual([
        ['GET', {}],
        ['POST', {
            responseType: ['invalid']
        }]
    ], this.mockBackendUrlCalls('mock/submit/json'));

    deepEqual([
        ['form-success', '<json>{"value":1, added:[1, "John Doe"}</json>', 'ok', 'text/html']
    ], this.mockListenerCalls('form-success'));
});

QUnit.test('creme.dialog.FormDialog (empty response)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/json', backend: this.backend});

    dialog.onFormSuccess(this.mockListener('form-success'));
    dialog.open();

    dialog.form().find('[name="responseType"]').val('empty');
    dialog.submit();

    deepEqual([
        ['GET', {}],
        ['POST', {
            responseType: ['empty']
        }]
    ], this.mockBackendUrlCalls('mock/submit/json'));

    deepEqual([
        ['form-success', '', 'ok', 'text/html']
    ], this.mockListenerCalls('form-success'));
});
}(jQuery));
