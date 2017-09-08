
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

var MOCK_FRAME_CONTENT_FORM = '<form action="mock/submit">'
                                   '<input type="text" id="firstname"></input>' +
                                   '<input type="text" id="lastname"></input>' +
                                   '<input type="submit" class="ui-creme-dialog-action"></input>' +
                               '</form>';
var MOCK_FRAME_CONTENT_FORM_BUTTON = '<form action="mock/submit">'
                                         '<input type="text" id="firstname"></input>' +
                                         '<input type="text" id="lastname"></input>' +
                                         '<button type="submit" class="ui-creme-dialog-action"></button>' +
                                     '</form>';

var MOCK_FRAME_CONTENT_FORM_MULTI = '<form action="mock/submit">' +
                                        '<input type="text" id="firstname"></input>' +
                                        '<input type="text" id="lastname"></input>' +
                                        '<input type="submit" value="Submit !"></input>' +
                                        '<input class="ui-creme-dialog-action" type="submit" value="Button A"></input>' +
                                        '<button class="ui-creme-dialog-action" type="submit">Button B</button>' +
                                        '<input class="ui-creme-dialog-action" type="submit" name="send-c" value="Button C"></input>' +
                                        '<button class="ui-creme-dialog-action" type="submit" name="button-d">Button D</button>' +
                                   '</form>';

var MOCK_FRAME_CONTENT_FORM_MULTI_UNNAMED = '<form action="mock/submit">' +
                                                '<input type="text" id="firstname"></input>' +
                                                '<input type="text" id="lastname"></input>' +
                                                '<input type="submit" class="ui-creme-dialog-action"></input>' +
                                                '<input type="submit" class="ui-creme-dialog-action"></input>' +
                                                '<button class="ui-creme-dialog-action" type="submit"></button>' +
                                                '<button class="ui-creme-dialog-action" type="submit"></button>' +
                                            '</form>';

var MOCK_FRAME_CONTENT_SUBMIT_JSON = '<json>' + $.toJSON({value:1, added:[1, 'John Doe']}) + '</json>';
var MOCK_FRAME_CONTENT_SUBMIT_JSON_NOTAG = $.toJSON({value:1, added:[1, 'John Doe']});
var MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID = '<json>' + '{"value":1, added:[1, "John Doe"}' + '</json>';

QUnit.module("creme.dialog.js", {
    setup: function() {
        var MockFrame = function(backend) {
            return $.extend({}, creme.widget.Frame, {
                options: {
                    url:'',
                    backend: backend,
                    overlay_delay: 100
                }
            });
        };

        var self = this;
        this.backend = new creme.ajax.MockAjaxBackend({delay:150, sync:true});
        $.extend(this.backend.GET, {'mock/html': this.backend.response(200, MOCK_FRAME_CONTENT),
                                    'mock/html2': this.backend.response(200, MOCK_FRAME_CONTENT_LIST),
                                    'mock/widget': this.backend.response(200, MOCK_FRAME_CONTENT_WIDGET),
                                    'mock/submit': this.backend.response(200, MOCK_FRAME_CONTENT_FORM),
                                    'mock/submit/button': this.backend.response(200, MOCK_FRAME_CONTENT_FORM_BUTTON),
                                    'mock/submit/multi': this.backend.response(200, MOCK_FRAME_CONTENT_FORM_MULTI),
                                    'mock/submit/multi/unnamed': this.backend.response(200, MOCK_FRAME_CONTENT_FORM_MULTI_UNNAMED),
                                    'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                    'mock/error': this.backend.response(500, 'HTTP - Error 500'),
                                    'mock/custom': function(url, data, options) {
                                        return self._custom_GET(url, data, options);
                                     }});

        $.extend(this.backend.POST, {'mock/submit/json': this.backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON),
                                     'mock/submit': this.backend.response(200, MOCK_FRAME_CONTENT_FORM),
                                     'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                     'mock/error': this.backend.response(500, 'HTTP - Error 500')});

        creme.widget.unregister('ui-creme-frame');
        creme.widget.declare('ui-creme-frame', new MockFrame(this.backend));

        this.resetMockCalls();
    },

    teardown: function() {
    },

    _custom_GET: function(url, data, options) {
        return this.backend.response(200, '<div>' + $.toJSON({url: url, method: 'GET', data: data}) + '</div>');
    },

    resetMockCalls: function() {
        this._eventListenerCalls = {};
    },

    mockListenerCalls: function(name)
    {
        if (this._eventListenerCalls[name] === undefined)
            this._eventListenerCalls[name] = [];

        return this._eventListenerCalls[name];
    },

    mockListener: function(name)
    {
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
    }
});


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

    this.resetMockCalls();

    dialog.close();

    deepEqual([], this.mockListenerCalls('ok'));
    deepEqual([['close', dialog.options]], this.mockListenerCalls('close'));
});

QUnit.test('creme.dialog.SelectionDialog (selector)', function(assert) {
    var selector = function() {return $('option[value="2"]', this.content()).html();};
    var dialog = new creme.dialog.SelectionDialog();
    dialog.fill('<option value="1">a</option><option value="2">b</option>')
          .selector(selector)

    dialog.onOk(this.mockListener('ok'));
    dialog.onClose(this.mockListener('close'));

    equal(undefined, dialog.validator());
    equal(selector, dialog.selector());

    deepEqual([], this.mockListenerCalls('ok'));
    deepEqual([], this.mockListenerCalls('close'));

    dialog.ok();

    deepEqual([['ok', 'b']], this.mockListenerCalls('ok'));
    deepEqual([], this.mockListenerCalls('close'));

    this.resetMockCalls();

    dialog.close();

    deepEqual([], this.mockListenerCalls('ok'));
    deepEqual([['close', dialog.options]], this.mockListenerCalls('close'));
});

QUnit.test('creme.dialog.SelectionDialog (validator)', function(assert) {
    var selector = function() {return $('select', this.content()).val();};
    var validator = function(data) {return data != null && data.length > 0;}
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

    this.resetMockCalls();

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
    deepEqual({my: 'center center', at: 'center center', of: window}, dialog.position());

    dialog.center({top: 5});
    deepEqual({my: 'center center', at: 'center center', of: window}, dialog.position());

    dialog.position({my: 'center top', at: 'center center', of: window});
    deepEqual({my: 'center top', at: 'center center', of: window}, dialog.position());

    var top = dialog.cssPosition().top + 10;

    dialog.center({top: top});
    deepEqual({my: 'center top', at: 'center top+'+top, of: window}, dialog.position());

    dialog.close();
});

QUnit.test('creme.dialog.Dialog (scroll)', function(assert) {
    var dialog = new creme.dialog.Dialog();
    equal('frame', dialog.options.scroll);

    dialog.open();

    equal(false, dialog._dialogBackground().is('.ui-dialog-scrollbackground'))
    equal(true, dialog.dialog().css('overflow-y') !== 'hidden');

    dialog.close();

    dialog = new creme.dialog.Dialog({scroll: 'background'});
    equal('background', dialog.options.scroll);

    dialog.open();

    equal(true, dialog._dialogBackground().is('.ui-dialog-scrollbackground'))
    equal('hidden', dialog.dialog().css('overflow-y'))

    dialog.close();

    equal(false, dialog._dialogBackground().is('.ui-dialog-scrollbackground'))

    dialog.open({scroll: 'frame'});

    equal(false, dialog._dialogBackground().is('.ui-dialog-scrollbackground'))
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
    var options = $.extend({compatible: false}, options || {});
    var dialog = new creme.dialog.FormDialog(options);

    equal(dialog._defaultValidator, dialog.validator());
    equal(true, dialog._validate('', 'success', 'text/html'));
    equal(true, dialog._validate('<div></div>', 'success', 'text/html'));

    equal(false, dialog._validate('<div><form></form></div>', 'success', 'text/html'));
    equal(true, dialog._validate('"<div><form></form></div>"', 'success', 'text/json'));
});

QUnit.test('creme.dialog.FormDialog (compatible validator)', function(assert) {
    var options = $.extend({compatible: true}, options || {});
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
    equal(gettext('Button'), dialog.button('button').text());
    equal(gettext('Button'), dialog.button('button-1').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.close();
});

QUnit.test('creme.dialog.FormDialog (multiple submit input/buttons)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/multi', backend: this.backend});

    dialog.open();

    equal(5, dialog.buttons().find('button').length);
    equal(gettext('Cancel'), dialog.button('cancel').text());
    equal('Button A', dialog.button('send').text());
    equal('Button B', dialog.button('button').text());
    equal('Button C', dialog.button('send-c').text());
    equal('Button D', dialog.button('button-d').text());

    dialog.close();
});
