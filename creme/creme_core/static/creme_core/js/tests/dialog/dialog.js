
var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';
var MOCK_FRAME_CONTENT_LIST = '<div class="mock-content"><ul><li>Item 1</li><li>Item 2</li></ul></div>';
var MOCK_FRAME_CONTENT_FORM = '<form action="mock/submit"><input type="text" id="firstname"/><input type="text" id="lastname"/></form>'
var MOCK_FRAME_CONTENT_SUBMIT_JSON = '<json>' + $.toJSON({value:1, added:[1, 'John Doe']}) + '</json>';
var MOCK_FRAME_CONTENT_SUBMIT_JSON_NOTAG = $.toJSON({value:1, added:[1, 'John Doe']});
var MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID = '<json>' + '{"value":1, added:[1, "John Doe"}' + '</json>';

module("creme.dialog.js", {
    setup: function() {
        var self = this;
        this.backend = new creme.ajax.MockAjaxBackend({delay:150, sync:true});
        $.extend(this.backend.GET, {'mock/html': this.backend.response(200, MOCK_FRAME_CONTENT),
                                    'mock/html2': this.backend.response(200, MOCK_FRAME_CONTENT_LIST),
                                    'mock/submit': this.backend.response(200, MOCK_FRAME_CONTENT_FORM),
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
    }
});


test('creme.dialog.SelectionDialog (default)', function() {
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

test('creme.dialog.SelectionDialog (selector)', function() {
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

test('creme.dialog.SelectionDialog (validator)', function() {
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
