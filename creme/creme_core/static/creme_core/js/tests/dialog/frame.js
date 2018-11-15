(function($) {

var RED_DOT_5x5_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==';
var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';

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

QUnit.test('creme.dialog.FrameContentData (empty)', function(assert) {
    var data = new creme.dialog.FrameContentData();
    equal('', data.content);
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(undefined, 'text/html');
    equal('', data.content);
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(undefined, 'text/json');
    equal('', data.content);
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(undefined, 'text/plain');
    equal('', data.content);
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json, text/plain)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', 'text/plain');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,', 'text/plain');
    equal('{"a": 12, "b": [1,', data.content);
    equal('{"a": 12, "b": [1,', data.data());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json, text/json)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', 'text/json');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', 'text/json');
    equal('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', data.content);
    equal('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', 'text/json');
    equal('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', data.content);
    equal('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,', 'text/json');
    equal('{"a": 12, "b": [1,', data.content);
    equal('{"a": 12, "b": [1,', data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1,</json>', 'text/json');
    equal('<json>{"a": 12, "b": [1,</json>', data.content);
    equal('<json>{"a": 12, "b": [1,</json>', data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>{"a": 12, "b": [1,</pre>', 'text/json');
    equal('<pre>{"a": 12, "b": [1,</pre>', data.content);
    equal('<pre>{"a": 12, "b": [1,</pre>', data.data());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json, application/json)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', 'application/json');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', 'application/json');
    equal('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', data.content);
    equal('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', 'application/json');
    equal('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', data.content);
    equal('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,', 'application/json');
    equal('{"a": 12, "b": [1,', data.content);
    equal('{"a": 12, "b": [1,', data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1,</json>', 'application/json');
    equal('<json>{"a": 12, "b": [1,</json>', data.content);
    equal('<json>{"a": 12, "b": [1,</json>', data.data());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json, text/html)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', 'text/html');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>', 'text/html');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('<pre>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</pre>', 'text/html');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,', 'text/html');
    equal('{"a": 12, "b": [1,', data.content);
    equal('{"a": 12, "b": [1,', data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1,</json>', 'text/html');
    equal('<json>{"a": 12, "b": [1,</json>', data.content);
    this.equalOuterHtml('<json>{"a": 12, "b": [1,</json>', data.data());
    equal('text/html', data.type);
});

QUnit.test('creme.dialog.FrameContentData (json)', function(assert) {
    var data = new creme.dialog.FrameContentData('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}</json>');
    equal('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}', data.content);
    deepEqual({"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}, data.data());
    equal('text/json', data.type);

    data = new creme.dialog.FrameContentData('{"a": 12, "b": [1,');
    equal('{"a": 12, "b": [1,', data.content);
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('<json>{"a": 12, "b": [1,</json>');
    equal('<json>{"a": 12, "b": [1,</json>', data.content);
    this.equalOuterHtml('<json>{"a": 12, "b": [1,</json>', data.data());
    equal('text/html', data.type);
});

QUnit.test('creme.dialog.FrameContentData (html, text/plain)', function(assert) {
    var data = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT, 'text/plain');
    equal(MOCK_FRAME_CONTENT, data.content);
    equal(MOCK_FRAME_CONTENT, data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData('http://localhost:7777/a/b/c', 'text/plain');
    equal('http://localhost:7777/a/b/c', data.content);
    equal('http://localhost:7777/a/b/c', data.data());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (html, text/html)', function(assert) {
    var data = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT, 'text/html');
    equal(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal('text/html', data.type);

    data = new creme.dialog.FrameContentData('http://localhost:7777/a/b/c', 'text/html');
    equal('http://localhost:7777/a/b/c', data.content);
    equal('http://localhost:7777/a/b/c', data.data());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (html)', function(assert) {
    var data = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT);
    equal(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal('text/html', data.type);

    data = new creme.dialog.FrameContentData('http://localhost:7777/a/b/c');
    equal('http://localhost:7777/a/b/c', data.content);
    equal('http://localhost:7777/a/b/c', data.data());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (object)', function(assert) {
    var data = new creme.dialog.FrameContentData({a: 12}, 'text/plain');
    deepEqual({a: 12}, data.content);
    deepEqual({a: 12}, data.data());
    equal('object', data.type);

    data = new creme.dialog.FrameContentData({a: 12}, 'text/html');
    deepEqual({a: 12}, data.content);
    deepEqual({a: 12}, data.data());
    equal('object', data.type);

    data = new creme.dialog.FrameContentData({a: 12}, 'text/json');
    deepEqual({a: 12}, data.content);
    deepEqual({a: 12}, data.data());
    equal('object', data.type);

    data = new creme.dialog.FrameContentData({a: 12});
    deepEqual({a: 12}, data.content);
    deepEqual({a: 12}, data.data());
    equal('object', data.type);
});

QUnit.test('creme.dialog.FrameContentData (object/jquery)', function(assert) {
    var data = new creme.dialog.FrameContentData($(MOCK_FRAME_CONTENT), 'text/plain');
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal('object/jquery', data.type);

    data = new creme.dialog.FrameContentData($(MOCK_FRAME_CONTENT), 'text/html');
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal('object/jquery', data.type);

    data = new creme.dialog.FrameContentData($(MOCK_FRAME_CONTENT), 'text/json');
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal('object/jquery', data.type);

    data = new creme.dialog.FrameContentData($(MOCK_FRAME_CONTENT));
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal('object/jquery', data.type);
});

QUnit.test('creme.dialog.FrameContentData (any)', function(assert) {
    var data = new creme.dialog.FrameContentData(12, 'text/plain');
    equal('12', data.content);
    equal(12, data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(12, 'text/html');
    equal('12', data.content);
    equal(12, data.data());
    equal('text/plain', data.type);

    data = new creme.dialog.FrameContentData(12);
    equal('12', data.content);
    equal(12, data.data());
    equal('text/plain', data.type);
});

QUnit.test('creme.dialog.FrameContentData (copy)', function(assert) {
    var delegate = new creme.dialog.FrameContentData(MOCK_FRAME_CONTENT, 'text/html');
    var data = new creme.dialog.FrameContentData(delegate, 'text/html');

    equal(MOCK_FRAME_CONTENT, data.content);
    this.equalOuterHtml(MOCK_FRAME_CONTENT, data.data());
    equal('text/html', data.type);
});

}(jQuery));
