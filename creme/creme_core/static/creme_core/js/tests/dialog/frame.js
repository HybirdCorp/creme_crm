(function($) {
var RED_DOT_5X5_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==';
var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';
var MOCK_FRAME_CONTENT_WIDGET = '<div class="mock-content">' +
                                    '<input widget="ui-creme-dinput" class="ui-creme-dinput ui-creme-widget widget-auto" type="text"></input>' +
                                '</div>';
var MOCK_FRAME_CONTENT_FORM = '<form>' +
                                  '<input type="text" name="firstname"></input>' +
                                  '<input type="text" name="lastname"></input>' +
                                  '<input type="submit" class="ui-creme-dialog-action"></input>' +
                              '</form>';

var MOCK_ERROR_403_HTML = '<div class="mock-error">HTTP - Error 403</div>';
var MOCK_ERROR_500_HTML = '<div class="mock-error">HTTP - Error 500</div>';


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
            'mock/red_dot': backend.response(200, RED_DOT_5X5_BASE64, {'content-type': 'image/png;base64'}),
            'mock/widget': backend.response(200, MOCK_FRAME_CONTENT_WIDGET),
            'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
            'mock/forbidden_html': backend.response(403, MOCK_ERROR_403_HTML, {'content-type': 'text/html'}),
            'mock/error': backend.response(500, 'HTTP - Error 500'),
            'mock/error_html': backend.response(500, MOCK_ERROR_500_HTML, {'content-type': 'text/html'})
        });

        this.setMockBackendPOST({
            'mock/submit/json': backend.response(200, '{"result": "ok"}', {'content-type': 'text/json'}),
            'mock/submit': backend.response(200, 'ok', {'content-type': 'text/plain'}),
            'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
            'mock/forbidden_html': backend.response(403, MOCK_ERROR_403_HTML, {'content-type': 'text/html'}),
            'mock/error': backend.response(500, 'HTTP - Error 500'),
            'mock/error_html': backend.response(500, MOCK_ERROR_500_HTML, {'content-type': 'text/html'})
        });
    },

    afterEach: function() {
        creme.widget.shutdown($('body'));
    },

    assertActive: function(element) {
        this.assert.equal(element.hasClass('widget-active'), true, 'is widget active');
    },

    assertNotActive: function(element) {
        this.assert.equal(element.hasClass('widget-active'), false, 'is widget not active');
    }
}));

QUnit.test('creme.dialog.FrameContentData (empty)', function(assert) {
    var data = new creme.dialog.FrameContentData();
    assert.equal('', data.content);
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(undefined, 'text/html');
    assert.equal('', data.content);
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(undefined, 'text/json');
    assert.equal('', data.content);
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(undefined, 'text/plain');
    assert.equal('', data.content);
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (<pre></pre>)', function(assert) {
    var data = new creme.dialog.FrameContentData('<pre></pre>');
    assert.equal('', data.content);
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>sample</pre>');
    assert.equal('sample', data.content);
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre></pre>', 'text/html');
    assert.equal('', data.content);
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>sample</pre>', 'text/html');
    assert.equal('sample', data.content);
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre></pre>', 'text/json');
    assert.equal('', data.content);
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>sample</pre>', 'text/json');
    assert.equal('sample', data.content);
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>sample</pre><div class="json-formatter-container"></div>', 'text/json');
    assert.equal('sample', data.content);
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>sample</pre><pre>other data</pre>', 'text/json');
    assert.equal('sample', data.content);
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre></pre>', 'text/plain');
    assert.equal('<pre></pre>', data.content);
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>sample</pre>', 'text/plain');
    assert.equal('<pre>sample</pre>', data.content);
    assert.equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json, text/plain)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', 'text/plain');
    assert.equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    assert.equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,', 'text/plain');
    assert.equal('{"a": 12, "b": [1,', data.content);
    assert.equal('{"a": 12, "b": [1,', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json, text/json)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', 'text/json');
    assert.equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    assert.deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    assert.equal(true, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', 'text/json');
    assert.equal('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', data.content);
    assert.equal('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', 'text/json');
    assert.equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    assert.deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    assert.equal(true, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,', 'text/json');
    assert.equal('{"a": 12, "b": [1,', data.content);
    assert.equal('{"a": 12, "b": [1,', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1,</json>', 'text/json');
    assert.equal('<json>{"a": 12, "b": [1,</json>', data.content);
    assert.equal('<json>{"a": 12, "b": [1,</json>', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>{"a": 12, "b": [1,</pre>', 'text/json');
    assert.equal('{"a": 12, "b": [1,', data.content);
    assert.equal('{"a": 12, "b": [1,', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json, application/json)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', 'application/json');
    assert.equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    assert.deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    assert.equal(true, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', 'application/json');
    assert.equal('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', data.content);
    assert.equal('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', 'application/json');
    assert.equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    assert.deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    assert.equal(true, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,', 'application/json');
    assert.equal('{"a": 12, "b": [1,', data.content);
    assert.equal('{"a": 12, "b": [1,', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1,</json>', 'application/json');
    assert.equal('<json>{"a": 12, "b": [1,</json>', data.content);
    assert.equal('<json>{"a": 12, "b": [1,</json>', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json, text/html)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', 'text/html');
    assert.equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    assert.equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', 'text/html');
    assert.equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    assert.deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    assert.equal(true, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', 'text/html');
    assert.equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    assert.deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    assert.equal(true, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,', 'text/html');
    assert.equal('{"a": 12, "b": [1,', data.content);
    assert.equal('{"a": 12, "b": [1,', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1,</json>', 'text/html');
    assert.equal('<json>{"a": 12, "b": [1,</json>', data.content);
    this.equalOuterHtml('<json>{"a": 12, "b": [1,</json>', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(true, data.isHTMLOrElement());
    assert.equal('text/html', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}');
    assert.equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    assert.deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    assert.equal(true, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>');
    assert.equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    assert.deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    assert.equal(true, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,');
    assert.equal('{"a": 12, "b": [1,', data.content);
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1,</json>');
    assert.equal('<json>{"a": 12, "b": [1,</json>', data.content);
    this.equalOuterHtml('<json>{"a": 12, "b": [1,</json>', data.data());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(true, data.isHTMLOrElement());
    assert.equal('text/html', data.type);
});

QUnit.test('creme.dialog.FrameContentData (html, text/plain)', function(assert) {
    var data = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT, 'text/plain');
    assert.equal(MOCK_FRAME_CONTENT, data.content);
    assert.equal(MOCK_FRAME_CONTENT, data.data());
    assert.equal(true, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('http://localhost:7777/a/b/c', 'text/plain');
    assert.equal('http://localhost:7777/a/b/c', data.content);
    assert.equal('http://localhost:7777/a/b/c', data.data());
    assert.equal(true, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (html, text/html)', function(assert) {
    var data = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT, 'text/html');
    assert.equal(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    assert.equal(false, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(true, data.isHTMLOrElement());
    assert.equal('text/html', data.type);

    data = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT, 'html');
    assert.equal(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    assert.equal(false, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(true, data.isHTMLOrElement());
    assert.equal('text/html', data.type);

    data = new creme.dialog.FrameContentData('http://localhost:7777/a/b/c', 'text/html');
    assert.equal('http://localhost:7777/a/b/c', data.content);
    assert.equal('http://localhost:7777/a/b/c', data.data());
    assert.equal(true, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('http://localhost:7777/a/b/c', 'html');
    assert.equal('http://localhost:7777/a/b/c', data.content);
    assert.equal('http://localhost:7777/a/b/c', data.data());
    assert.equal(true, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (html)', function(assert) {
    var data = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT);
    assert.equal(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    assert.equal(false, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(true, data.isHTMLOrElement());
    assert.equal('text/html', data.type);

    data = new creme.dialog.FrameContentData('http://localhost:7777/a/b/c');
    assert.equal('http://localhost:7777/a/b/c', data.content);
    assert.equal('http://localhost:7777/a/b/c', data.data());
    assert.equal(true, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (object)', function(assert) {
    var data = new creme.dialog.FrameContentData({a: 12}, 'text/plain');
    assert.deepEqual({a: 12}, data.content);
    assert.deepEqual({a: 12}, data.data());
    assert.equal(false, data.isPlainText());
    assert.equal(true, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('object', data.type);

    data = new creme.dialog.FrameContentData({a: 12}, 'text/html');
    assert.deepEqual({a: 12}, data.content);
    assert.deepEqual({a: 12}, data.data());
    assert.equal(false, data.isPlainText());
    assert.equal(true, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('object', data.type);

    data = new creme.dialog.FrameContentData({a: 12}, 'text/json');
    assert.deepEqual({a: 12}, data.content);
    assert.deepEqual({a: 12}, data.data());
    assert.equal(false, data.isPlainText());
    assert.equal(true, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('object', data.type);

    data = new creme.dialog.FrameContentData({a: 12});
    assert.deepEqual({a: 12}, data.content);
    assert.deepEqual({a: 12}, data.data());
    assert.equal(false, data.isPlainText());
    assert.equal(true, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('object', data.type);
});

QUnit.test('creme.dialog.FrameContentData (object/jquery)', function(assert) {
    var data = new creme.dialog.FrameContentData($(MOCK_FRAME_CONTENT), 'text/plain');
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    assert.equal(false, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(true, data.isHTMLOrElement());
    assert.equal('object/jquery', data.type);

    data = new creme.dialog.FrameContentData($(MOCK_FRAME_CONTENT), 'text/html');
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    assert.equal(false, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(true, data.isHTMLOrElement());
    assert.equal('object/jquery', data.type);

    data = new creme.dialog.FrameContentData($(MOCK_FRAME_CONTENT), 'text/json');
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    assert.equal(false, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(true, data.isHTMLOrElement());
    assert.equal('object/jquery', data.type);

    data = new creme.dialog.FrameContentData($(MOCK_FRAME_CONTENT));
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    assert.equal(false, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(true, data.isHTMLOrElement());
    assert.equal('object/jquery', data.type);
});

QUnit.test('creme.dialog.FrameContentData (any)', function(assert) {
    var data = new creme.dialog.FrameContentData(12, 'text/plain');
    assert.equal('12', data.content);
    assert.equal(12, data.data());
    assert.equal(true, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(12, 'text/html');
    assert.equal('12', data.content);
    assert.equal(12, data.data());
    assert.equal(true, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(12);
    assert.equal('12', data.content);
    assert.equal(12, data.data());
    assert.equal(true, data.isPlainText());
    assert.equal(false, data.isJSONOrObject());
    assert.equal(false, data.isHTMLOrElement());
    assert.equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (copy)', function(assert) {
    var delegate = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT, 'text/html');
    var data = new creme.dialog.FrameContentData(delegate, 'text/html');

    assert.equal(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    assert.equal('text/html', data.type);
});

QUnit.test('creme.dialog.Frame', function(assert) {
    var frame = new creme.dialog.Frame();

    assert.equal(undefined, frame.delegate());
    assert.equal(false, frame.isContentReady());
    assert.equal(undefined, frame.lastFetchUrl());
    assert.equal(200, frame.overlayDelay());
    assert.equal(false, frame.isBound());

    assert.equal(true, Object.isSubClassOf(frame.backend(), creme.ajax.Backend));
});

QUnit.test('creme.dialog.Frame.bind', function(assert) {
    var frame = new creme.dialog.Frame();
    var element = $('<div>');

    assert.equal(false, frame.isBound());
    assert.deepEqual(undefined, frame.delegate());

    frame.bind(element);

    assert.equal(true, frame.isBound());
    assert.deepEqual(element, frame.delegate());
});

QUnit.test('creme.dialog.Frame.bind (already bound)', function(assert) {
    var frame = new creme.dialog.Frame();
    var element = $('<div>');

    frame.bind(element);

    assert.equal(true, frame.isBound());
    assert.deepEqual(element, frame.delegate());

    this.assertRaises(function() {
        frame.bind(element);
    }, Error, 'Error: frame component is already bound');
});

QUnit.test('creme.dialog.Frame.unbind', function(assert) {
    var frame = new creme.dialog.Frame();
    var element = $('<div>');

    frame.bind(element);

    assert.equal(true, frame.isBound());
    assert.deepEqual(element, frame.delegate());

    frame.unbind();

    assert.equal(false, frame.isBound());
    assert.equal(undefined, frame.delegate());
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
    assert.deepEqual({}, this.mockListenerCalls());

    frame.fill('<span>Fill test</span>');

    this.equalHtml('<span>Fill test</span>', frame.delegate());
    assert.deepEqual({
        'frame-cleanup': [['cleanup', frame.delegate(), undefined]],
        'frame-update': [['update', '<span>Fill test</span>', 'text/html', undefined]]
    }, this.mockListenerCalls());

    frame.clear();

    this.equalHtml('', frame.delegate());
    assert.deepEqual({
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
    assert.deepEqual({}, this.mockListenerCalls());

    frame.fill('<span>Fill test</span>', 'action-A');

    this.equalHtml('<span>Fill test</span>', frame.delegate());
    assert.deepEqual({
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
    assert.deepEqual({}, this.mockListenerCalls());

    frame.fill('{"result": "not html"}', 'action-A');

    this.equalHtml('', frame.delegate());
    assert.deepEqual({}, this.mockListenerCalls());
});

QUnit.parameterize('creme.dialog.Frame.fetch (error)', [
    [
        'mock/forbidden', 'HTTP - Error 403', (
            '<h2>${statusMessage}&nbsp;(${status})<div class="subtitle">${url}</div></h2>' +
            '<p class="message">${message}</p>' +
            '<a class="redirect" onclick="creme.utils.reload();">' +
                gettext('Reload the page or click here. If the problem persists, please contact your administrator.') +
            '</a>'
        ).template({
            statusMessage: gettext('Forbidden Access'),
            status: 403,
            url: 'mock/forbidden',
            message: 'HTTP - Error 403'
        })
    ],
    ['mock/forbidden_html', MOCK_ERROR_403_HTML, MOCK_ERROR_403_HTML]
], function(url, expectedResponse, expectedMessage, assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.on('before-fetch', this.mockListener('fetch-before'));
    frame.onFetchDone(this.mockListener('fetch-done'));
    frame.onFetchFail(this.mockListener('fetch-fail'));
    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual({}, this.mockListenerCalls());

    frame.fetch(url, {sync: true}, {a: 12});

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual([
        ['before-fetch', url, {sync: true}]
    ], this.mockListenerCalls('fetch-before'));
    assert.deepEqual([
        ['fetch-fail', expectedResponse]
    ], this.mockListenerCalls('fetch-fail').map(function(e) { return e.slice(0, 2); }));
    assert.deepEqual([], this.mockListenerCalls('frame-cleanup'));
    assert.deepEqual([], this.mockListenerCalls('frame-update'));

    this.equalHtml(expectedMessage, frame._overlay.content());
    assert.equal(true, frame._overlay.visible());
});

QUnit.parameterize('creme.dialog.Frame.fetch (error, fillOnError)', [
    [
        'mock/forbidden', 'HTTP - Error 403', (
            '<h2>${statusMessage}&nbsp;(${status})<div class="subtitle">${url}</div></h2>' +
            '<p class="message">${message}</p>' +
            '<a class="redirect" onclick="creme.utils.reload();">' +
                gettext('Reload the page or click here. If the problem persists, please contact your administrator.') +
            '</a>'
        ).template({
            statusMessage: gettext('Forbidden Access'),
            status: 403,
            url: 'mock/forbidden',
            message: 'HTTP - Error 403'
        })
    ],
    ['mock/forbidden_html', MOCK_ERROR_403_HTML, MOCK_ERROR_403_HTML]
], function(url, expectedResponse, expectedMessage, assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame({
        fillOnError: true
    }).bind(element);

    frame.on('before-fetch', this.mockListener('fetch-before'));
    frame.onFetchDone(this.mockListener('fetch-done'));
    frame.onFetchFail(this.mockListener('fetch-fail'));
    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual({}, this.mockListenerCalls());

    frame.fetch(url, {sync: true}, {a: 12});

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual([
        ['before-fetch', url, {sync: true}]
    ], this.mockListenerCalls('fetch-before'));
    assert.deepEqual([
        ['fetch-fail', expectedResponse]
    ], this.mockListenerCalls('fetch-fail').map(function(e) { return e.slice(0, 2); }));
    assert.deepEqual([
        ['cleanup', frame.delegate(), 'fetch']
    ], this.mockListenerCalls('frame-cleanup'));
    assert.deepEqual([
        ['update', expectedMessage, 'text/html', 'fetch']
    ], this.mockListenerCalls('frame-update'));

    assert.equal(false, frame._overlay.visible());
});

QUnit.test('creme.dialog.Frame.fetch (ok)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.on('before-fetch', this.mockListener('fetch-before'));
    frame.onFetchDone(this.mockListener('fetch-done'));
    frame.onFetchFail(this.mockListener('fetch-fail'));
    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual({}, this.mockListenerCalls());

    frame.fetch('mock/html', {sync: true}, {a: 12});

    assert.equal('mock/html', frame.lastFetchUrl());
    assert.deepEqual([
        ['before-fetch', 'mock/html', {sync: true}]
    ], this.mockListenerCalls('fetch-before'));
    assert.deepEqual([], this.mockListenerCalls('fetch-fail'));
    assert.deepEqual([
        ['fetch-done', frame.delegate().html()]
    ], this.mockListenerCalls('fetch-done').map(function(e) { return e.slice(0, 2); }));
    assert.deepEqual([
        ['cleanup', frame.delegate(), 'fetch']
    ], this.mockListenerCalls('frame-cleanup'));
    assert.deepEqual([
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

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual({}, this.mockListenerCalls());

    assert.equal(200, frame.overlayDelay());

    frame.fetch('mock/html', {delay: 150, sync: false}, {a: 12});

    this.assertOverlayState(frame.delegate(), {active: false});

    var done = assert.async(2);

    setTimeout(function() {
        self.assertOverlayState(frame.delegate(), {active: false});

        assert.deepEqual({
            'fetch-before': [['before-fetch', 'mock/html', {delay: 150, sync: false}]]
        }, self.mockListenerCalls());

        done();
    }, 100);

    setTimeout(function() {
        self.assertOverlayState(frame.delegate(), {active: false});

        assert.deepEqual([
            ['before-fetch', 'mock/html', {delay: 150, sync: false}]
        ], self.mockListenerCalls('fetch-before'));
        assert.deepEqual([], self.mockListenerCalls('fetch-fail'));
        assert.deepEqual([
            ['fetch-done', frame.delegate().html()]
        ], self.mockListenerCalls('fetch-done').map(function(e) { return e.slice(0, 2); }));
        assert.deepEqual([
            ['cleanup', frame.delegate(), 'fetch']
        ], self.mockListenerCalls('frame-cleanup'));
        assert.deepEqual([
            ['update', MOCK_FRAME_CONTENT, 'text/html', 'fetch']
        ], self.mockListenerCalls('frame-update'));

        done();
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

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual({}, this.mockListenerCalls());

    assert.equal(200, frame.overlayDelay());

    frame.fetch('mock/html', {delay: 300, sync: false}, {a: 12});

    this.assertOverlayState(frame.delegate(), {active: false});

    var done = assert.async(3);

    setTimeout(function() {
        self.assertOverlayState(frame.delegate(), {active: false});

        assert.deepEqual({
            'fetch-before': [['before-fetch', 'mock/html', {delay: 300, sync: false}]]
        }, self.mockListenerCalls());

        done();
    }, 100);

    setTimeout(function() {
        self.assertOverlayState(frame.delegate(), {status: 'wait', active: true});

        assert.deepEqual({
            'fetch-before': [['before-fetch', 'mock/html', {delay: 300, sync: false}]]
        }, self.mockListenerCalls());

        done();
    }, 200);

    setTimeout(function() {
        self.assertOverlayState(frame.delegate(), {active: false});

        assert.deepEqual([
            ['before-fetch', 'mock/html', {delay: 300, sync: false}]
        ], self.mockListenerCalls('fetch-before'));
        assert.deepEqual([], self.mockListenerCalls('fetch-fail'));
        assert.deepEqual([
            ['fetch-done', frame.delegate().html()]
        ], self.mockListenerCalls('fetch-done').map(function(e) { return e.slice(0, 2); }));
        assert.deepEqual([
            ['cleanup', frame.delegate(), 'fetch']
        ], self.mockListenerCalls('frame-cleanup'));
        assert.deepEqual([
            ['update', MOCK_FRAME_CONTENT, 'text/html', 'fetch']
        ], self.mockListenerCalls('frame-update'));

        done();
    }, 400);
});

QUnit.parameterize('creme.dialog.Frame.submit (fail)', [
    [
        'mock/forbidden', 'HTTP - Error 403', (
            '<h2>${statusMessage}&nbsp;(${status})<div class="subtitle">${url}</div></h2>' +
            '<p class="message">${message}</p>' +
            '<a class="redirect" onclick="creme.utils.reload();">' +
                gettext('Reload the page or click here. If the problem persists, please contact your administrator.') +
            '</a>'
        ).template({
            statusMessage: gettext('Forbidden Access'),
            status: 403,
            url: 'mock/forbidden',
            message: 'HTTP - Error 403'
        })
    ],
    ['mock/forbidden_html', MOCK_ERROR_403_HTML, MOCK_ERROR_403_HTML]
], function(url, expectedResponse, expectedMessage, assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.on('before-submit', this.mockListener('submit-before'));
    frame.onSubmitDone(this.mockListener('submit-done'));
    frame.onSubmitFail(this.mockListener('submit-fail'));
    frame.onCleanup(this.mockListener('submit-cleanup'));
    frame.onUpdate(this.mockListener('submit-update'));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual({}, this.mockListenerCalls());

    frame.submit(url, {sync: true}, $(MOCK_FRAME_CONTENT_FORM));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual([
        ['before-submit', $(MOCK_FRAME_CONTENT_FORM), {action: url, sync: true}]
    ], this.mockListenerCalls('submit-before'));
    assert.deepEqual([
        ['submit-fail', expectedResponse]
    ], this.mockListenerCalls('submit-fail').map(function(e) { return e.slice(0, 2); }));
    assert.deepEqual([], this.mockListenerCalls('submit-cleanup'));
    assert.deepEqual([], this.mockListenerCalls('submit-update'));

    this.equalHtml(expectedMessage, frame._overlay.content());
    assert.equal(true, frame._overlay.visible());
});

QUnit.parameterize('creme.dialog.Frame.submit (fail, fillOnError)', [
    [
        'mock/forbidden', 'HTTP - Error 403', (
            '<h2>${statusMessage}&nbsp;(${status})<div class="subtitle">${url}</div></h2>' +
            '<p class="message">${message}</p>' +
            '<a class="redirect" onclick="creme.utils.reload();">' +
                gettext('Reload the page or click here. If the problem persists, please contact your administrator.') +
            '</a>'
        ).template({
            statusMessage: gettext('Forbidden Access'),
            status: 403,
            url: 'mock/forbidden',
            message: 'HTTP - Error 403'
        })
    ],
    ['mock/forbidden_html', MOCK_ERROR_403_HTML, MOCK_ERROR_403_HTML]
], function(url, expectedResponse, expectedMessage, assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame({
        fillOnError: true
    }).bind(element);

    frame.on('before-submit', this.mockListener('submit-before'));
    frame.onSubmitDone(this.mockListener('submit-done'));
    frame.onSubmitFail(this.mockListener('submit-fail'));
    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual({}, this.mockListenerCalls());

    frame.submit(url, {sync: true}, $(MOCK_FRAME_CONTENT_FORM));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual([
        ['before-submit', $(MOCK_FRAME_CONTENT_FORM), {action: url, sync: true}]
    ], this.mockListenerCalls('submit-before'));
    assert.deepEqual([
        ['submit-fail', expectedResponse]
    ], this.mockListenerCalls('submit-fail').map(function(e) { return e.slice(0, 2); }));
    assert.deepEqual([
        ['cleanup', frame.delegate(), 'submit']
    ], this.mockListenerCalls('frame-cleanup'));
    assert.deepEqual([
        ['update', expectedMessage, 'text/html', 'submit']
    ], this.mockListenerCalls('frame-update'));

    assert.equal(false, frame._overlay.visible());
});

QUnit.test('creme.dialog.Frame.submit (empty url)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.on('before-submit', this.mockListener('submit-before'));
    frame.onSubmitDone(this.mockListener('submit-done'));
    frame.onSubmitFail(this.mockListener('submit-fail'));
    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual({}, this.mockListenerCalls());

    frame.submit('', {sync: true}, $(MOCK_FRAME_CONTENT_FORM));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual([
        ['before-submit', $(MOCK_FRAME_CONTENT_FORM), {action: undefined, sync: true}]
    ], this.mockListenerCalls('submit-before'));
    assert.deepEqual([
        ['submit-fail', '']
    ], this.mockListenerCalls('submit-fail').map(function(e) { return e.slice(0, 2); }));
    assert.deepEqual([], this.mockListenerCalls('submit-cleanup'));
    assert.deepEqual([], this.mockListenerCalls('submit-update'));
});

QUnit.test('creme.dialog.Frame.submit (ok, plain/text)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.on('before-submit', this.mockListener('submit-before'));
    frame.onSubmitDone(this.mockListener('submit-done'));
    frame.onSubmitFail(this.mockListener('submit-fail'));
    frame.onCleanup(this.mockListener('submit-cleanup'));
    frame.onUpdate(this.mockListener('submit-update'));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual({}, this.mockListenerCalls());

    frame.submit('mock/submit', {sync: true}, $(MOCK_FRAME_CONTENT_FORM));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual([
        ['before-submit', $(MOCK_FRAME_CONTENT_FORM), {action: 'mock/submit', sync: true}]
    ], this.mockListenerCalls('submit-before'));
    assert.deepEqual([], this.mockListenerCalls('submit-fail'));
    assert.deepEqual([
        ['submit-done', new creme.dialog.FrameContentData('ok', 'text/plain')]
    ], this.mockListenerCalls('submit-done').map(function(e) { return e.slice(0, 2); }));

    // content type is not html, so fill() step is ignored.
    assert.deepEqual([], this.mockListenerCalls('frame-cleanup'));
    assert.deepEqual([], this.mockListenerCalls('frame-update'));
});

QUnit.test('creme.dialog.Frame.submit (ok, json)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    frame.on('before-submit', this.mockListener('submit-before'));
    frame.onSubmitDone(this.mockListener('submit-done'));
    frame.onSubmitFail(this.mockListener('submit-fail'));
    frame.onCleanup(this.mockListener('frame-cleanup'));
    frame.onUpdate(this.mockListener('frame-update'));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual({}, this.mockListenerCalls());

    frame.submit('mock/submit/json', {sync: true}, $(MOCK_FRAME_CONTENT_FORM));

    assert.equal(undefined, frame.lastFetchUrl());
    assert.deepEqual([
        ['before-submit', $(MOCK_FRAME_CONTENT_FORM), {action: 'mock/submit/json', sync: true}]
    ], this.mockListenerCalls('submit-before'));
    assert.deepEqual([], this.mockListenerCalls('submit-fail'));
    assert.deepEqual([
        ['submit-done', new creme.dialog.FrameContentData('{"result": "ok"}', 'text/json')]
    ], this.mockListenerCalls('submit-done').map(function(e) { return e.slice(0, 2); }));

    // content type is not html, so fill() step is ignored.
    assert.deepEqual([], this.mockListenerCalls('frame-cleanup'));
    assert.deepEqual([], this.mockListenerCalls('frame-update'));
});

QUnit.test('creme.dialog.Frame (activate content, auto)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame().bind(element);

    assert.equal(true, frame.autoActivate());
    frame.fill(MOCK_FRAME_CONTENT_WIDGET);

    assert.equal(true, frame.isContentReady());
    this.assertActive(frame.delegate().find('input'));

    frame.deactivateContent();

    assert.equal(false, frame.isContentReady());
    this.assertNotActive(frame.delegate().find('input'));

    // do nothing
    frame.deactivateContent();

    assert.equal(false, frame.isContentReady());
    this.assertNotActive(frame.delegate().find('input'));
});

QUnit.test('creme.dialog.Frame (activate content, manually)', function(assert) {
    var element = $('<div>');
    var frame = new creme.dialog.Frame({
        autoActivate: false
    }).bind(element);

    assert.equal(false, frame.autoActivate());
    frame.fill(MOCK_FRAME_CONTENT_WIDGET);

    assert.equal(false, frame.isContentReady());
    this.assertNotActive(frame.delegate().find('input'));

    frame.activateContent();

    assert.equal(true, frame.isContentReady());
    this.assertActive(frame.delegate().find('input'));

    // do nothing
    frame.activateContent();

    assert.equal(true, frame.isContentReady());
    this.assertActive(frame.delegate().find('input'));
});
}(jQuery));
