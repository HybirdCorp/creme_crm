(function($) {
var RED_DOT_5x5_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==';
var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';
var MOCK_FRAME_CONTENT_WIDGET = '<div class="mock-content">' +
                                    '<input widget="ui-creme-dinput" class="ui-creme-dinput ui-creme-widget widget-auto" type="text"></input>' +
                                '</div>';
var MOCK_FRAME_CONTENT_FORM = '<form>' +
                                  '<input type="text" name="firstname"></input>' +
                                  '<input type="text" name="lastname"></input>' +
                                  '<input type="submit" class="ui-creme-dialog-action"></input>' +
                              '</form>';

QUnit.module("creme.dialog.frame.js", new QUnitMixin(QUnitEventMixin,
                                                     QUnitAjaxMixin,
                                                     QUnitDialogMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({delay: 0, sync: true, name: 'creme.dialog.frame.js'});
    },

    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
            'mock/html': backend.response(200, MOCK_FRAME_CONTENT),
            'mock/red_dot': backend.response(200, RED_DOT_5x5_BASE64, {'content-type': 'image/png;base64'}),
            'mock/widget': backend.response(200, MOCK_FRAME_CONTENT_WIDGET),
            'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
            'mock/error': backend.response(500, 'HTTP - Error 500')
        });

        this.setMockBackendPOST({
            'mock/submit/json': backend.response(200, '{"result": "ok"}', {'content-type': 'text/json'}),
            'mock/submit': backend.response(200, 'ok', {'content-type': 'text/plain'}),
            'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
            'mock/error': backend.response(500, 'HTTP - Error 500')
        });
    },

    afterEach: function() {
        creme.widget.shutdown($('body'));
    },

    assertActive: function(element) {
        equal(element.hasClass('widget-active'), true, 'is widget active');
    },

    assertNotActive: function(element) {
        equal(element.hasClass('widget-active'), false, 'is widget not active');
    }
}));

QUnit.test('creme.dialog.FrameContentData (empty)', function(assert) {
    var data = new creme.dialog.FrameContentData();
    equal('', data.content);
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(undefined, 'text/html');
    equal('', data.content);
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(undefined, 'text/json');
    equal('', data.content);
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(undefined, 'text/plain');
    equal('', data.content);
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (<pre></pre>)', function(assert) {
    var data = new creme.dialog.FrameContentData('<pre></pre>');
    equal('', data.content);
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>sample</pre>');
    equal('sample', data.content);
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre></pre>', 'text/html');
    equal('', data.content);
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>sample</pre>', 'text/html');
    equal('sample', data.content);
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre></pre>', 'text/json');
    equal('', data.content);
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>sample</pre>', 'text/json');
    equal('sample', data.content);
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre></pre>', 'text/plain');
    equal('<pre></pre>', data.content);
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>sample</pre>', 'text/plain');
    equal('<pre>sample</pre>', data.content);
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json, text/plain)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', 'text/plain');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.data());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,', 'text/plain');
    equal('{"a": 12, "b": [1,', data.content);
    equal('{"a": 12, "b": [1,', data.data());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json, text/json)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', 'text/json');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal(true, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', 'text/json');
    equal('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', data.content);
    equal('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', data.data());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', 'text/json');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal(true, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,', 'text/json');
    equal('{"a": 12, "b": [1,', data.content);
    equal('{"a": 12, "b": [1,', data.data());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1,</json>', 'text/json');
    equal('<json>{"a": 12, "b": [1,</json>', data.content);
    equal('<json>{"a": 12, "b": [1,</json>', data.data());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>{"a": 12, "b": [1,</pre>', 'text/json');
    equal('{"a": 12, "b": [1,', data.content);
    equal('{"a": 12, "b": [1,', data.data());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json, application/json)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', 'application/json');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal(true, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', 'application/json');
    equal('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', data.content);
    equal('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', data.data());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', 'application/json');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal(true, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,', 'application/json');
    equal('{"a": 12, "b": [1,', data.content);
    equal('{"a": 12, "b": [1,', data.data());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1,</json>', 'application/json');
    equal('<json>{"a": 12, "b": [1,</json>', data.content);
    equal('<json>{"a": 12, "b": [1,</json>', data.data());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json, text/html)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', 'text/html');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.data());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', 'text/html');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal(true, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', 'text/html');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal(true, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,', 'text/html');
    equal('{"a": 12, "b": [1,', data.content);
    equal('{"a": 12, "b": [1,', data.data());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1,</json>', 'text/html');
    equal('<json>{"a": 12, "b": [1,</json>', data.content);
    this.equalOuterHtml('<json>{"a": 12, "b": [1,</json>', data.data());
    equal(false, data.isJSONOrObject());
    equal(true, data.isHTMLOrElement());
    equal('text/html', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal(true, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal(true, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,');
    equal('{"a": 12, "b": [1,', data.content);
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1,</json>');
    equal('<json>{"a": 12, "b": [1,</json>', data.content);
    this.equalOuterHtml('<json>{"a": 12, "b": [1,</json>', data.data());
    equal(false, data.isJSONOrObject());
    equal(true, data.isHTMLOrElement());
    equal('text/html', data.type);
});

QUnit.test('creme.dialog.FrameContentData (html, text/plain)', function(assert) {
    var data = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT, 'text/plain');
    equal(MOCK_FRAME_CONTENT, data.content);
    equal(MOCK_FRAME_CONTENT, data.data());
    equal(true, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('http://localhost:7777/a/b/c', 'text/plain');
    equal('http://localhost:7777/a/b/c', data.content);
    equal('http://localhost:7777/a/b/c', data.data());
    equal(true, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (html, text/html)', function(assert) {
    var data = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT, 'text/html');
    equal(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal(false, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(true, data.isHTMLOrElement());
    equal('text/html', data.type);

    data = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT, 'html');
    equal(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal(false, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(true, data.isHTMLOrElement());
    equal('text/html', data.type);

    data = new creme.dialog.FrameContentData('http://localhost:7777/a/b/c', 'text/html');
    equal('http://localhost:7777/a/b/c', data.content);
    equal('http://localhost:7777/a/b/c', data.data());
    equal(true, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('http://localhost:7777/a/b/c', 'html');
    equal('http://localhost:7777/a/b/c', data.content);
    equal('http://localhost:7777/a/b/c', data.data());
    equal(true, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (html)', function(assert) {
    var data = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT);
    equal(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal(false, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(true, data.isHTMLOrElement());
    equal('text/html', data.type);

    data = new creme.dialog.FrameContentData('http://localhost:7777/a/b/c');
    equal('http://localhost:7777/a/b/c', data.content);
    equal('http://localhost:7777/a/b/c', data.data());
    equal(true, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (object)', function(assert) {
    var data = new creme.dialog.FrameContentData({a: 12}, 'text/plain');
    deepEqual({a: 12}, data.content);
    deepEqual({a: 12}, data.data());
    equal(false, data.isPlainText());
    equal(true, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('object', data.type);

    data = new creme.dialog.FrameContentData({a: 12}, 'text/html');
    deepEqual({a: 12}, data.content);
    deepEqual({a: 12}, data.data());
    equal(false, data.isPlainText());
    equal(true, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('object', data.type);

    data = new creme.dialog.FrameContentData({a: 12}, 'text/json');
    deepEqual({a: 12}, data.content);
    deepEqual({a: 12}, data.data());
    equal(false, data.isPlainText());
    equal(true, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('object', data.type);

    data = new creme.dialog.FrameContentData({a: 12});
    deepEqual({a: 12}, data.content);
    deepEqual({a: 12}, data.data());
    equal(false, data.isPlainText());
    equal(true, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('object', data.type);
});

QUnit.test('creme.dialog.FrameContentData (object/jquery)', function(assert) {
    var data = new creme.dialog.FrameContentData($(MOCK_FRAME_CONTENT), 'text/plain');
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal(false, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(true, data.isHTMLOrElement());
    equal('object/jquery', data.type);

    data = new creme.dialog.FrameContentData($(MOCK_FRAME_CONTENT), 'text/html');
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal(false, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(true, data.isHTMLOrElement());
    equal('object/jquery', data.type);

    data = new creme.dialog.FrameContentData($(MOCK_FRAME_CONTENT), 'text/json');
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal(false, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(true, data.isHTMLOrElement());
    equal('object/jquery', data.type);

    data = new creme.dialog.FrameContentData($(MOCK_FRAME_CONTENT));
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal(false, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(true, data.isHTMLOrElement());
    equal('object/jquery', data.type);
});

QUnit.test('creme.dialog.FrameContentData (any)', function(assert) {
    var data = new creme.dialog.FrameContentData(12, 'text/plain');
    equal('12', data.content);
    equal(12, data.data());
    equal(true, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(12, 'text/html');
    equal('12', data.content);
    equal(12, data.data());
    equal(true, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(12);
    equal('12', data.content);
    equal(12, data.data());
    equal(true, data.isPlainText());
    equal(false, data.isJSONOrObject());
    equal(false, data.isHTMLOrElement());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (copy)', function(assert) {
    var delegate = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT, 'text/html');
    var data = new creme.dialog.FrameContentData(delegate, 'text/html');

    equal(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal('text/html', data.type);
});

QUnit.test('creme.dialog.Frame', function(assert) {
    var frame = new creme.dialog.Frame();

    equal(undefined, frame.delegate());
    equal(false, frame.isContentReady());
    equal(undefined, frame.lastFetchUrl());
    equal(200, frame.overlayDelay());
    equal(false, frame.isBound());

    equal(true, Object.isSubClassOf(frame.backend(), creme.ajax.Backend));
});

QUnit.test('creme.dialog.Frame.bind', function(assert) {
    var frame = new creme.dialog.Frame();
    var element = $('<div>');

    equal(false, frame.isBound());
    deepEqual(undefined, frame.delegate());

    frame.bind(element);

    equal(true, frame.isBound());
    deepEqual(element, frame.delegate());
});

QUnit.test('creme.dialog.Frame.bind (already bound)', function(assert) {
    var frame = new creme.dialog.Frame();
    var element = $('<div>');

    frame.bind(element);

    equal(true, frame.isBound());
    deepEqual(element, frame.delegate());

    this.assertRaises(function() {
        frame.bind(element);
    }, Error, 'Error: frame component is already bound');
});

QUnit.test('creme.dialog.Frame.unbind', function(assert) {
    var frame = new creme.dialog.Frame();
    var element = $('<div>');

    frame.bind(element);

    equal(true, frame.isBound());
    deepEqual(element, frame.delegate());

    frame.unbind();

    equal(false, frame.isBound());
    equal(undefined, frame.delegate());
});

QUnit.test('creme.dialog.Frame.unbind (not bound)', function(assert) {
    var frame = new creme.dialog.Frame();
    var element = $('<div>');

    this.assertRaises(function() {
        frame.unbind(element);
    }, Error, 'Error: frame component is not bound');
});

QUnit.test('creme.dialog.Frame.fill', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    this.equalHtml('', frame.delegate());
    deepEqual({}, this.mockListenerCalls());

    frame.fill('<span>Fill test</span>');

    this.equalHtml('<span>Fill test</span>', frame.delegate());
    deepEqual({
        'frame-cleanup': [['cleanup', frame.delegate(), undefined]],
        'frame-update': [['update', '<span>Fill test</span>', 'text/html', undefined]]
    }, this.mockListenerCalls());

    frame.clear();

    this.equalHtml('', frame.delegate());
    deepEqual({
        'frame-cleanup': [
            ['cleanup', frame.delegate(), undefined],
            ['cleanup', frame.delegate(), undefined]
         ],
        'frame-update': [
            ['update', '<span>Fill test</span>', 'text/html', undefined],
            ['update', '', 'text/html', undefined]
         ]
    }, this.mockListenerCalls());
});

QUnit.test('creme.dialog.Frame.fill (action)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    this.equalHtml('', frame.delegate());
    deepEqual({}, this.mockListenerCalls());

    frame.fill('<span>Fill test</span>', 'action-A');

    this.equalHtml('<span>Fill test</span>', frame.delegate());
    deepEqual({
        'frame-cleanup': [['cleanup', frame.delegate(), 'action-A']],
        'frame-update': [['update', '<span>Fill test</span>', 'text/html', 'action-A']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.dialog.Frame.fill (not html)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    this.equalHtml('', frame.delegate());
    deepEqual({}, this.mockListenerCalls());

    frame.fill('{"result": "not html"}', 'action-A');

    this.equalHtml('', frame.delegate());
    deepEqual({}, this.mockListenerCalls());
});

QUnit.test('creme.dialog.Frame.fetch (error)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.on('before-fetch', this.mockListener('fetch-before'));
    frame.onFetchDone(this.mockListener('fetch-done'));
    frame.onFetchFail(this.mockListener('fetch-fail'));
    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    equal(undefined, frame.lastFetchUrl());
    deepEqual({}, this.mockListenerCalls());

    frame.fetch('mock/forbidden', {sync: true}, {a: 12});

    equal(undefined, frame.lastFetchUrl());
    deepEqual([
        ['before-fetch', 'mock/forbidden', {sync: true}]
    ], this.mockListenerCalls('fetch-before'));
    deepEqual([
        ['fetch-fail', 'HTTP - Error 403']
    ], this.mockListenerCalls('fetch-fail').map(function(e) { return e.slice(0, 2); }));
    deepEqual([], this.mockListenerCalls('frame-cleanup'));
    deepEqual([], this.mockListenerCalls('frame-update'));
});

QUnit.test('creme.dialog.Frame.fetch (ok)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.on('before-fetch', this.mockListener('fetch-before'));
    frame.onFetchDone(this.mockListener('fetch-done'));
    frame.onFetchFail(this.mockListener('fetch-fail'));
    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    equal(undefined, frame.lastFetchUrl());
    deepEqual({}, this.mockListenerCalls());

    frame.fetch('mock/html', {sync: true}, {a: 12});

    equal('mock/html', frame.lastFetchUrl());
    deepEqual([
        ['before-fetch', 'mock/html', {sync: true}]
    ], this.mockListenerCalls('fetch-before'));
    deepEqual([], this.mockListenerCalls('fetch-fail'));
    deepEqual([
        ['fetch-done', frame.delegate().html()]
    ], this.mockListenerCalls('fetch-done').map(function(e) { return e.slice(0, 2); }));
    deepEqual([
        ['cleanup', frame.delegate(), 'fetch']
    ], this.mockListenerCalls('frame-cleanup'));
    deepEqual([
        ['update', MOCK_FRAME_CONTENT, 'text/html', 'fetch']
    ], this.mockListenerCalls('frame-update'));
});

QUnit.test('creme.dialog.Frame.fetch (async, no overlay)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);
    var self = this;

    frame.on('before-fetch', this.mockListener('fetch-before'));
    frame.onFetchDone(this.mockListener('fetch-done'));
    frame.onFetchFail(this.mockListener('fetch-fail'));
    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    equal(undefined, frame.lastFetchUrl());
    deepEqual({}, this.mockListenerCalls());

    equal(200, frame.overlayDelay());

    frame.fetch('mock/html', {delay: 150, sync: false}, {a: 12});

    this.assertOverlayState(frame.delegate(), {active: false});

    stop(2);

    setTimeout(function() {
        self.assertOverlayState(frame.delegate(), {active: false});

        deepEqual({
            'fetch-before': [['before-fetch', 'mock/html', {delay: 150, sync: false}]]
        }, self.mockListenerCalls());

        start();
    }, 100);

    setTimeout(function() {
        self.assertOverlayState(frame.delegate(), {active: false});

        deepEqual([
            ['before-fetch', 'mock/html', {delay: 150, sync: false}]
        ], self.mockListenerCalls('fetch-before'));
        deepEqual([], self.mockListenerCalls('fetch-fail'));
        deepEqual([
            ['fetch-done', frame.delegate().html()]
        ], self.mockListenerCalls('fetch-done').map(function(e) { return e.slice(0, 2); }));
        deepEqual([
            ['cleanup', frame.delegate(), 'fetch']
        ], self.mockListenerCalls('frame-cleanup'));
        deepEqual([
            ['update', MOCK_FRAME_CONTENT, 'text/html', 'fetch']
        ], self.mockListenerCalls('frame-update'));

        start();
    }, 200);
});

QUnit.test('creme.dialog.Frame.fetch (async, with overlay)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);
    var self = this;

    frame.on('before-fetch', this.mockListener('fetch-before'));
    frame.onFetchDone(this.mockListener('fetch-done'));
    frame.onFetchFail(this.mockListener('fetch-fail'));
    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    equal(undefined, frame.lastFetchUrl());
    deepEqual({}, this.mockListenerCalls());

    equal(200, frame.overlayDelay());

    frame.fetch('mock/html', {delay: 300, sync: false}, {a: 12});

    this.assertOverlayState(frame.delegate(), {active: false});

    stop(3);

    setTimeout(function() {
        self.assertOverlayState(frame.delegate(), {active: false});

        deepEqual({
            'fetch-before': [['before-fetch', 'mock/html', {delay: 300, sync: false}]]
        }, self.mockListenerCalls());

        start();
    }, 100);

    setTimeout(function() {
        self.assertOverlayState(frame.delegate(), {status: 'wait', active: true});

        deepEqual({
            'fetch-before': [['before-fetch', 'mock/html', {delay: 300, sync: false}]]
        }, self.mockListenerCalls());

        start();
    }, 200);

    setTimeout(function() {
        self.assertOverlayState(frame.delegate(), {active: false});

        deepEqual([
            ['before-fetch', 'mock/html', {delay: 300, sync: false}]
        ], self.mockListenerCalls('fetch-before'));
        deepEqual([], self.mockListenerCalls('fetch-fail'));
        deepEqual([
            ['fetch-done', frame.delegate().html()]
        ], self.mockListenerCalls('fetch-done').map(function(e) { return e.slice(0, 2); }));
        deepEqual([
            ['cleanup', frame.delegate(), 'fetch']
        ], self.mockListenerCalls('frame-cleanup'));
        deepEqual([
            ['update', MOCK_FRAME_CONTENT, 'text/html', 'fetch']
        ], self.mockListenerCalls('frame-update'));

        start();
    }, 400);
});

QUnit.test('creme.dialog.Frame.submit (fail)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.on('before-submit', this.mockListener('submit-before'));
    frame.onSubmitDone(this.mockListener('submit-done'));
    frame.onSubmitFail(this.mockListener('submit-fail'));
    frame.onCleanup(this.mockListener('submit-cleanup'));
    frame.onUpdate(this.mockListener('submit-update'));

    equal(undefined, frame.lastFetchUrl());
    deepEqual({}, this.mockListenerCalls());

    frame.submit('mock/forbidden', {sync: true}, $(MOCK_FRAME_CONTENT_FORM));

    equal(undefined, frame.lastFetchUrl());
    deepEqual([
        ['before-submit', $(MOCK_FRAME_CONTENT_FORM), {action: 'mock/forbidden', sync: true}]
    ], this.mockListenerCalls('submit-before'));
    deepEqual([
        ['submit-fail', 'HTTP - Error 403']
    ], this.mockListenerCalls('submit-fail').map(function(e) { return e.slice(0, 2); }));
    deepEqual([], this.mockListenerCalls('submit-cleanup'));
    deepEqual([], this.mockListenerCalls('submit-update'));
});

QUnit.test('creme.dialog.Frame.submit (empty url)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.on('before-submit', this.mockListener('submit-before'));
    frame.onSubmitDone(this.mockListener('submit-done'));
    frame.onSubmitFail(this.mockListener('submit-fail'));
    frame.onCleanup(this.mockListener('submit-cleanup'));
    frame.onUpdate(this.mockListener('submit-update'));

    equal(undefined, frame.lastFetchUrl());
    deepEqual({}, this.mockListenerCalls());

    frame.submit('', {sync: true}, $(MOCK_FRAME_CONTENT_FORM));

    equal(undefined, frame.lastFetchUrl());
    deepEqual([
        ['before-submit', $(MOCK_FRAME_CONTENT_FORM), {action: undefined, sync: true}]
    ], this.mockListenerCalls('submit-before'));
    deepEqual([
        ['submit-fail', '']
    ], this.mockListenerCalls('submit-fail').map(function(e) { return e.slice(0, 2); }));
    deepEqual([], this.mockListenerCalls('submit-cleanup'));
    deepEqual([], this.mockListenerCalls('submit-update'));
});

QUnit.test('creme.dialog.Frame.submit (ok, plain/text)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.on('before-submit', this.mockListener('submit-before'));
    frame.onSubmitDone(this.mockListener('submit-done'));
    frame.onSubmitFail(this.mockListener('submit-fail'));
    frame.onCleanup(this.mockListener('submit-cleanup'));
    frame.onUpdate(this.mockListener('submit-update'));

    equal(undefined, frame.lastFetchUrl());
    deepEqual({}, this.mockListenerCalls());

    frame.submit('mock/submit', {sync: true}, $(MOCK_FRAME_CONTENT_FORM));

    equal(undefined, frame.lastFetchUrl());
    deepEqual([
        ['before-submit', $(MOCK_FRAME_CONTENT_FORM), {action: 'mock/submit', sync: true}]
    ], this.mockListenerCalls('submit-before'));
    deepEqual([], this.mockListenerCalls('submit-fail'));
    deepEqual([
        ['submit-done', new creme.dialog.FrameContentData('ok', 'text/plain')]
    ], this.mockListenerCalls('submit-done').map(function(e) { return e.slice(0, 2); }));

    // content type is not html, so fill() step is ignored.
    deepEqual([], this.mockListenerCalls('submit-cleanup'));
    deepEqual([], this.mockListenerCalls('submit-update'));
});

QUnit.test('creme.dialog.Frame.submit (ok, json)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.on('before-submit', this.mockListener('submit-before'));
    frame.onSubmitDone(this.mockListener('submit-done'));
    frame.onSubmitFail(this.mockListener('submit-fail'));
    frame.onCleanup(this.mockListener('submit-cleanup'));
    frame.onUpdate(this.mockListener('submit-update'));

    equal(undefined, frame.lastFetchUrl());
    deepEqual({}, this.mockListenerCalls());

    frame.submit('mock/submit/json', {sync: true}, $(MOCK_FRAME_CONTENT_FORM));

    equal(undefined, frame.lastFetchUrl());
    deepEqual([
        ['before-submit', $(MOCK_FRAME_CONTENT_FORM), {action: 'mock/submit/json', sync: true}]
    ], this.mockListenerCalls('submit-before'));
    deepEqual([], this.mockListenerCalls('submit-fail'));
    deepEqual([
        ['submit-done', new creme.dialog.FrameContentData('{"result": "ok"}', 'text/json')]
    ], this.mockListenerCalls('submit-done').map(function(e) { return e.slice(0, 2); }));

    // content type is not html, so fill() step is ignored.
    deepEqual([], this.mockListenerCalls('submit-cleanup'));
    deepEqual([], this.mockListenerCalls('submit-update'));
});

QUnit.test('creme.dialog.Frame (activate content, auto)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    equal(true, frame.autoActivate());
    frame.fill(MOCK_FRAME_CONTENT_WIDGET);

    equal(true, frame.isContentReady());
    this.assertActive(frame.delegate().find('input'));

    frame.deactivateContent();

    equal(false, frame.isContentReady());
    this.assertNotActive(frame.delegate().find('input'));

    // do nothing
    frame.deactivateContent();

    equal(false, frame.isContentReady());
    this.assertNotActive(frame.delegate().find('input'));
});

QUnit.test('creme.dialog.Frame (activate content, manually)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame({
        autoActivate: false
    }).bind(element);

    equal(false, frame.autoActivate());
    frame.fill(MOCK_FRAME_CONTENT_WIDGET);

    equal(false, frame.isContentReady());
    this.assertNotActive(frame.delegate().find('input'));

    frame.activateContent();

    equal(true, frame.isContentReady());
    this.assertActive(frame.delegate().find('input'));

    // do nothing
    frame.activateContent();

    equal(true, frame.isContentReady());
    this.assertActive(frame.delegate().find('input'));
});

}(jQuery));
