(function($) {

function mock_frame_create(url, noauto) {
    var select = $('<div widget="ui-creme-frame" class="ui-creme-frame ui-creme-widget"/>');

    if (url !== undefined) {
        select.attr('url', url);
    }

    if (!noauto) {
        select.addClass('widget-auto');
    }

    return select;
}

var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';
var MOCK_FRAME_CONTENT_LIST = '<div class="mock-content"><ul><li>Item 1</li><li>Item 2</li></ul></div>';
var MOCK_FRAME_CONTENT_FORM = '<form action="mock/submit"><input id="firstname" type="text"><input id="lastname" type="text"></form>';
var MOCK_FRAME_CONTENT_FORM_NOACTION = '<form action=""><input id="firstname" type="text"><input id="lastname" type="text"></form>';
var MOCK_FRAME_CONTENT_SUBMIT_JSON = '<json>' + JSON.stringify({value: 1, added: [1, 'John Doe']}) + '</json>';
var MOCK_FRAME_CONTENT_SUBMIT_JSON_NOTAG = JSON.stringify({value: 1, added: [1, 'John Doe']});
var MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID = '<json>' + '{"value":1, added:[1, "John Doe"}' + '</json>';

QUnit.module("creme.widget.frame.js", new QUnitMixin(QUnitEventMixin,
                                                     QUnitAjaxMixin,
                                                     QUnitDialogMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({delay: 150, sync: true, name: 'creme.widget.frame.js'});
    },

    beforeEach: function() {
        var self = this;
        this.setMockBackendGET({
            'mock/html': this.backend.response(200, MOCK_FRAME_CONTENT),
            'mock/html2': this.backend.response(200, MOCK_FRAME_CONTENT_LIST),
            'mock/submit': this.backend.response(200, MOCK_FRAME_CONTENT_FORM),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500'),
            'mock/custom': function(url, data, options) {
                return self._custom_GET(url, data, options);
            }
        });

        this.setMockBackendPOST({
            'mock/submit/json': this.backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON),
            'mock/submit': this.backend.response(200, MOCK_FRAME_CONTENT_FORM),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500')
        });
    },

    afterEach: function() {
        $('.ui-dialog-content').dialog('destroy');
        creme.widget.shutdown($('body'));
    },

    _custom_GET: function(url, data, options) {
        return this.backend.response(200, '<div>' + JSON.stringify({url: url, method: 'GET', data: data}) + '</div>');
    }
}));

QUnit.test('creme.widget.Frame.create (undefined)', function(assert) {
    var element = mock_frame_create();

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(0, $('h1', element).length);
});

QUnit.test('creme.widget.Frame.create (empty)', function(assert) {
    var element = mock_frame_create();

    creme.widget.create(element, {url: '', backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(0, $('h1', element).length);
});

QUnit.test('creme.widget.Frame.create (url)', function(assert) {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('h1', element).length);
});

QUnit.test('creme.widget.Frame.create (404)', function(assert) {
    var element = mock_frame_create('mock/unknown');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {status: '404', active: true});
    assert.equal(0, $('h1', element).length);
});

QUnit.test('creme.widget.Frame.create (403)', function(assert) {
    var element = mock_frame_create('mock/forbidden');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {status: '403', active: true});
    assert.equal(0, $('h1', element).length);
});

QUnit.test('creme.widget.Frame.create (500)', function(assert) {
    var element = mock_frame_create('mock/error');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {status: '500', active: true});
    assert.equal(0, $('h1', element).length);
});

QUnit.test('creme.widget.Frame.create (url, overlay not shown, async)', function(assert) {
    this.backend.options.sync = false;
    this.backend.options.delay = 100;

    var element = mock_frame_create('mock/html');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.creme().widget().options().overlay_delay, 100);

    this.assertOverlayState(element, {active: false});
    assert.equal(0, $('h1', element).length, 'content');

    var done = assert.async(2);

    var self = this;

    setTimeout(function() {
        self.assertOverlayState(element, {active: false});
        assert.equal($('h1', element).length, 0);
        done();
    }, 90);

    setTimeout(function() {
        self.assertOverlayState(element, {active: false});
        assert.equal($('h1', element).length, 1);
        done();
    }, 150);
});

QUnit.test('creme.widget.Frame.create (url, overlay shown, async)', function(assert) {
    this.backend.options.sync = false;
    this.backend.options.delay = 500;

    var element = mock_frame_create('mock/html');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.creme().widget().options().overlay_delay, 100);

    this.assertOverlayState(element, {active: false});
    assert.equal(0, $('h1', element).length);

    var done = assert.async(3);

    var self = this;

    setTimeout(function() {
        self.assertOverlayState(element, {active: false});
        assert.equal(0, $('h1', element).length);
        done();
    }, 90);

    setTimeout(function() {
        self.assertOverlayState(element, {status: 'wait', active: true});
        assert.equal(0, $('h1', element).length);
        done();
    }, 200);

    setTimeout(function() {
        self.assertOverlayState(element, {active: false});
        assert.equal(1, $('h1', element).length);
        done();
    }, 700);
});

QUnit.test('creme.widget.Frame.create (url, overlay shown, async, error)', function(assert) {
    this.backend.options.sync = false;
    this.backend.options.delay = 500;

    var element = mock_frame_create('mock/forbidden');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.creme().widget().options().overlay_delay, 100);

    this.assertOverlayState(element, {active: false});
    assert.equal(0, $('h1', element).length);

    var done = assert.async(3);

    var self = this;

    setTimeout(function() {
        self.assertOverlayState(element, {active: false});
        assert.equal(0, $('h1', element).length);
        done();
    }, 90);

    setTimeout(function() {
        self.assertOverlayState(element, {status: 'wait', active: true});
        assert.equal(0, $('h1', element).length);
        done();
    }, 150);

    setTimeout(function() {
        self.assertOverlayState(element, {status: '403', active: true});
        assert.equal(0, $('h1', element).length);
        done();
    }, 600);
});

QUnit.test('creme.widget.Frame.fill', function(assert) {
    var element = mock_frame_create();

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(0, $('h1', element).length);
    assert.equal(0, $('ul', element).length);

    element.creme().widget().fill(MOCK_FRAME_CONTENT);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('h1', element).length);
    assert.equal(0, $('ul', element).length);

    element.creme().widget().fill(MOCK_FRAME_CONTENT);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('h1', element).length);
    assert.equal(0, $('ul', element).length);

    element.creme().widget().fill(MOCK_FRAME_CONTENT_LIST);

    this.assertOverlayState(element, {active: false});
    assert.equal(0, $('h1', element).length);
    assert.equal(1, $('ul', element).length);
});

QUnit.test('creme.widget.Frame.reload (none)', function(assert) {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('h1', element).length);
    assert.equal(0, $('ul', element).length);

    this.backend.GET['mock/html'] = this.backend.response(200, MOCK_FRAME_CONTENT_LIST);

    element.creme().widget().reload();

    this.assertOverlayState(element, {active: false});
    assert.equal(0, $('h1', element).length);
    assert.equal(1, $('ul', element).length);
});

QUnit.test('creme.widget.Frame.reload (none, async)', function(assert) {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('h1', element).length);
    assert.equal(0, $('ul', element).length);

    this.backend.options.sync = false;
    this.backend.options.delay = 500;
    this.backend.GET['mock/html'] = this.backend.response(200, MOCK_FRAME_CONTENT_LIST);

    element.creme().widget().reload();

    var done = assert.async(3);

    var self = this;

    setTimeout(function() {
        self.assertOverlayState(element, {active: false});
        assert.equal(1, $('h1', element).length);
        assert.equal(0, $('ul', element).length);
        done();
    }, 90);

    setTimeout(function() {
        self.assertOverlayState(element, {status: 'wait', active: true});
        assert.equal(1, $('h1', element).length);
        assert.equal(0, $('ul', element).length);
        done();
    }, 150);

    setTimeout(function() {
        self.assertOverlayState(element, {active: false});
        assert.equal(0, $('h1', element).length);
        assert.equal(1, $('ul', element).length);
        done();
    }, 600);
});

QUnit.test('creme.widget.Frame.reload (url)', function(assert) {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('h1', element).length);
    assert.equal(0, $('ul', element).length);

    element.creme().widget().reload('mock/html2');

    this.assertOverlayState(element, {active: false});
    assert.equal(0, $('h1', element).length);
    assert.equal(1, $('ul', element).length);
});

QUnit.test('creme.widget.Frame.reload (url, data)', function(assert) {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('h1', element).length);
    assert.equal(0, $('ul', element).length);

    element.creme().widget().reload('mock/custom', {});

    this.assertOverlayState(element, {active: false});
    assert.equal(0, $('h1', element).length);
    assert.equal(element.html(), '<div>' + JSON.stringify({url: 'mock/custom', method: 'GET', data: {}}) + '</div>');

    element.creme().widget().reload('mock/custom', {'a': 12});
    assert.equal(0, $('h1', element).length);
    assert.equal(element.html(), '<div>' + JSON.stringify({url: 'mock/custom', method: 'GET', data: {'a': 12}}) + '</div>');
});

QUnit.test('creme.widget.Frame.reload (url, async)', function(assert) {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('h1', element).length);
    assert.equal(0, $('ul', element).length);

    this.backend.options.sync = false;
    this.backend.options.delay = 500;

    element.creme().widget().reload('mock/html2');

    var done = assert.async(3);

    var self = this;

    setTimeout(function() {
        self.assertOverlayState(element, {active: false});
        assert.equal(1, $('h1', element).length);
        assert.equal(0, $('ul', element).length);
        done();
    }, 90);

    setTimeout(function() {
        self.assertOverlayState(element, {status: 'wait', active: true});
        assert.equal(1, $('h1', element).length);
        assert.equal(0, $('ul', element).length);
        done();
    }, 150);

    setTimeout(function() {
        self.assertOverlayState(element, {active: false});
        assert.equal(0, $('h1', element).length);
        assert.equal(1, $('ul', element).length);
        done();
    }, 600);
});

QUnit.test('creme.widget.Frame.reload (invalid url)', function(assert) {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('h1', element).length);
    assert.equal(0, $('ul', element).length);

    element.creme().widget().reload('mock/error');

    this.assertOverlayState(element, {status: '500', active: true});
    assert.equal(1, $('h1', element).length);
    assert.equal(0, $('ul', element).length);
});

QUnit.test('creme.widget.Frame.reload (invalid url, async)', function(assert) {
    var element = mock_frame_create('mock/html');
    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('h1', element).length);
    assert.equal(0, $('ul', element).length);

    this.backend.options.sync = false;
    this.backend.options.delay = 500;

    element.creme().widget().reload('mock/unknown');

    var done = assert.async(3);

    var self = this;

    setTimeout(function() {
        self.assertOverlayState(element, {active: false});
        assert.equal(1, $('h1', element).length);
        assert.equal(0, $('ul', element).length);
        done();
    }, 90);

    setTimeout(function() {
        self.assertOverlayState(element, {status: 'wait', active: true});
        assert.equal(1, $('h1', element).length);
        assert.equal(0, $('ul', element).length);
        done();
    }, 150);

    setTimeout(function() {
        self.assertOverlayState(element, {status: '404', active: true});
        assert.equal(1, $('h1', element).length);
        assert.equal(0, $('ul', element).length);
        done();
    }, 600);
});

QUnit.test('creme.widget.Frame.submit', function(assert) {
    var element = mock_frame_create('mock/submit');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('form', element).length);

    var listeners = {
        'submit-done': this.mockListener('success'),
        'submit-fail': this.mockListener('error')
    };

    element.creme().widget().submit($('form', element), listeners);
    assert.deepEqual(this.mockFormSubmitCalls('success'), [
        ['submit-done', {
            content: MOCK_FRAME_CONTENT_FORM,
            data: MOCK_FRAME_CONTENT_FORM,
            type: 'text/html'
        }, 'text/html']
    ], 'form html');
});

QUnit.test('creme.widget.Frame.submit (empty action)', function(assert) {
    var element = mock_frame_create('');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    element.creme().widget().fill(MOCK_FRAME_CONTENT_FORM_NOACTION);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('form', element).length);

    var listeners = {
        'submit-done': this.mockListener('success'),
        'submit-fail': this.mockListener('error')
    };

    // <form> action is empty. returns 404
    this.resetMockListenerCalls();
    this.setMockBackendPOST({
        'mock/submit': this.backend.response(200, MOCK_FRAME_CONTENT_FORM_NOACTION)
    });

    element.creme().widget().submit($('form', element), listeners);
    assert.deepEqual(this.mockListenerCalls('error').map(function(e) { return e.slice(0, 1); }), [
        ['submit-fail']
    ]);
});

QUnit.test('creme.widget.Frame.submit (json)', function(assert) {
    var element = mock_frame_create('mock/submit');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('form', element).length);

    var listeners = {
        'submit-done': this.mockListener('success'),
        'submit-fail': this.mockListener('error')
    };

    // <json>{...}</json> response
    this.setMockBackendPOST({
        'mock/submit': this.backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON)
    });

    element.creme().widget().submit($('form', element), listeners);
    assert.deepEqual(this.mockFormSubmitCalls('success'), [
        ['submit-done', {
            content: JSON.stringify({value: 1, added: [1, 'John Doe']}),
            data: {value: 1, added: [1, 'John Doe']},
            type: 'text/json'
        }, 'text/json']
    ], 'form json');

    // {...} response
    this.resetMockListenerCalls();
    this.setMockBackendPOST({
        'mock/submit': this.backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON_NOTAG, {'content-type': 'text/json'})
    });

    element.creme().widget().reload('mock/submit');
    element.creme().widget().submit($('form', element), listeners);
    assert.deepEqual(this.mockFormSubmitCalls('success'), [
        ['submit-done', {
            content: JSON.stringify({value: 1, added: [1, 'John Doe']}),
            data: {value: 1, added: [1, 'John Doe']},
            type: 'text/json'
        }, 'text/json']
    ], 'form json no tag');

    // {invalid json} response
    this.resetMockListenerCalls();
    this.setMockBackendPOST({
        'mock/submit': this.backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID)
    });

    element.creme().widget().reload('mock/submit');
    element.creme().widget().submit($('form', element), listeners);
    assert.deepEqual(this.mockFormSubmitCalls('success'), [
        ['submit-done', {
            content: MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID,
            data: MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID,
            type: 'text/html'
        }, 'text/html']
    ], 'form json invalid');
});

QUnit.test('creme.widget.Frame.submit (error)', function(assert) {
    var element = mock_frame_create('mock/submit');

    creme.widget.create(element, {backend: this.backend});
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertOverlayState(element, {active: false});
    assert.equal(1, $('form', element).length);

    var listeners = {
        'submit-done': this.mockListener('success'),
        'submit-fail': this.mockListener('error')
    };

    this.setMockBackendPOST({
        'mock/submit': this.backend.response(500, 'HTTP - Error 500')
    });

    element.creme().widget().submit($('form', element), listeners);
    assert.deepEqual(this.mockListenerCalls('error').map(function(e) { return e.slice(0, 1); }), [
        ['submit-fail']
    ]);
});

}(jQuery));
