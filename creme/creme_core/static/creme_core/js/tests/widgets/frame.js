MockFrame = function(backend) {
    return $.extend({}, creme.widget.Frame, {
        options: {
            url:'',
            backend: backend,
            overlay_delay: 100
        }
    });
};

function mock_frame_create(url, noauto) {
    var select = $('<div widget="ui-creme-frame" class="ui-creme-frame ui-creme-widget"/>');

    if (url !== undefined)
        select.attr('url', url);

    if (!noauto)
        select.addClass('widget-auto');

    return select;
}

var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';
var MOCK_FRAME_CONTENT_LIST = '<div class="mock-content"><ul><li>Item 1</li><li>Item 2</li></ul></div>';
var MOCK_FRAME_CONTENT_FORM = '<form action="mock/submit"><input type="text" id="firstname"/><input type="text" id="lastname"/></form>'
var MOCK_FRAME_CONTENT_SUBMIT_JSON = '<json>' + $.toJSON({value:1, added:[1, 'John Doe']}) + '</json>';
var MOCK_FRAME_CONTENT_SUBMIT_JSON_NOTAG = $.toJSON({value:1, added:[1, 'John Doe']});
var MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID = '<json>' + '{"value":1, added:[1, "John Doe"}' + '</json>';

module("creme.widget.frame.js", {
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
    },

    teardown: function() {
    },

    _custom_GET: function(url, data, options) {
        return this.backend.response(200, '<div>' + $.toJSON({url: url, method: 'GET', data: data}) + '</div>');
    }
});

function assertOverlay(element, status, active)
{
    var overlay = $('.ui-creme-overlay', element);
    equal(overlay.length, active ? 1 : 0, 'has overlay');
    equal(overlay.attr('status'), status, 'overlay status:' + status);
    equal(overlay.hasClass('overlay-active'), active || false, 'overlay isactive');
}

test('creme.widget.Frame.create (empty)', function() {
    var element = mock_frame_create();

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, '404', true);
    equal(0, $('h1', element).length);
});

test('creme.widget.Frame.create (url)', function() {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, undefined, false);
    equal(1, $('h1', element).length);
});

test('creme.widget.Frame.create (404)', function()
{
    var element = mock_frame_create('mock/unknown');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, '404', true);
    equal(0, $('h1', element).length);
});

test('creme.widget.Frame.create (403)', function() {
    var element = mock_frame_create('mock/forbidden');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, '403', true);
    equal(0, $('h1', element).length);
});

test('creme.widget.Frame.create (500)', function() {
    var element = mock_frame_create('mock/error');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, '500', true);
    equal(0, $('h1', element).length);
});

test('creme.widget.Frame.create (url, overlay not shown, async)', function() {
    this.backend.options.sync = false;
    this.backend.options.delay = 100;

    var element = mock_frame_create('mock/html');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(element.creme().widget().options().overlay_delay, 100);

    assertOverlay(element, undefined, false);
    equal(0, $('h1', element).length, 'content');

    stop(2);

    setTimeout(function() {
        assertOverlay(element, undefined, false);
        equal($('h1', element).length, 0);
        start();
    }, 90);

    setTimeout(function() {
        assertOverlay(element, undefined);
        equal($('h1', element).length, 1);
        start();
    }, 150);
});

test('creme.widget.Frame.create (url, overlay shown, async)', function() {
    this.backend.options.sync = false;
    this.backend.options.delay = 500;

    var element = mock_frame_create('mock/html');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(element.creme().widget().options().overlay_delay, 100);

    assertOverlay(element, undefined);
    equal(0, $('h1', element).length);

    stop(3);

    setTimeout(function() {
        assertOverlay(element, undefined);
        equal(0, $('h1', element).length);
        start();
    }, 90);

    setTimeout(function() {
        assertOverlay(element, 'wait', true);
        equal(0, $('h1', element).length);
        start();
    }, 200);

    setTimeout(function() {
        assertOverlay(element, undefined);
        equal(1, $('h1', element).length);
        start();
    }, 700);
});

test('creme.widget.Frame.create (url, overlay shown, async, error)', function() {
    this.backend.options.sync = false;
    this.backend.options.delay = 500;

    var element = mock_frame_create('mock/forbidden');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(element.creme().widget().options().overlay_delay, 100);

    assertOverlay(element, undefined);
    equal(0, $('h1', element).length);

    stop(3);

    setTimeout(function() {
        assertOverlay(element, undefined);
        equal(0, $('h1', element).length);
        start();
    }, 90);

    setTimeout(function() {
        assertOverlay(element, 'wait', true);
        equal(0, $('h1', element).length);
        start();
    }, 150);

    setTimeout(function() {
        assertOverlay(element, '403', true);
        equal(0, $('h1', element).length);
        start();
    }, 600);
});

test('creme.widget.Frame.fill', function() {
    var element = mock_frame_create();

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, 404, true);
    equal(0, $('h1', element).length);
    equal(0, $('ul', element).length);

    element.creme().widget().fill(MOCK_FRAME_CONTENT);

    assertOverlay(element, undefined);
    equal(1, $('h1', element).length);
    equal(0, $('ul', element).length);

    element.creme().widget().fill(MOCK_FRAME_CONTENT);

    assertOverlay(element, undefined);
    equal(1, $('h1', element).length);
    equal(0, $('ul', element).length);

    element.creme().widget().fill(MOCK_FRAME_CONTENT_LIST);

    assertOverlay(element, undefined);
    equal(0, $('h1', element).length);
    equal(1, $('ul', element).length);
});

test('creme.widget.Frame.reload (none)', function() {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, undefined);
    equal(1, $('h1', element).length);
    equal(0, $('ul', element).length);

    this.backend.GET['mock/html'] = this.backend.response(200, MOCK_FRAME_CONTENT_LIST);

    element.creme().widget().reload();

    assertOverlay(element, undefined);
    equal(0, $('h1', element).length);
    equal(1, $('ul', element).length);
});

test('creme.widget.Frame.reload (none, async)', function() {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, undefined);
    equal(1, $('h1', element).length);
    equal(0, $('ul', element).length);

    this.backend.options.sync = false;
    this.backend.options.delay = 500;
    this.backend.GET['mock/html'] = this.backend.response(200, MOCK_FRAME_CONTENT_LIST);

    element.creme().widget().reload();

    stop(3);

    setTimeout(function() {
        assertOverlay(element, undefined);
        equal(1, $('h1', element).length);
        equal(0, $('ul', element).length);
        start();
    }, 90);

    setTimeout(function() {
        assertOverlay(element, 'wait', true);
        equal(1, $('h1', element).length);
        equal(0, $('ul', element).length);
        start();
    }, 150);

    setTimeout(function() {
        assertOverlay(element, undefined);
        equal(0, $('h1', element).length);
        equal(1, $('ul', element).length);
        start();
    }, 600);
});

test('creme.widget.Frame.reload (url)', function() {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, undefined);
    equal(1, $('h1', element).length);
    equal(0, $('ul', element).length);

    element.creme().widget().reload('mock/html2');

    assertOverlay(element, undefined);
    equal(0, $('h1', element).length);
    equal(1, $('ul', element).length);
});

test('creme.widget.Frame.reload (url, data)', function() {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, undefined);
    equal(1, $('h1', element).length);
    equal(0, $('ul', element).length);

    element.creme().widget().reload('mock/custom', {});

    assertOverlay(element, undefined);
    equal(0, $('h1', element).length);
    equal(element.html(), '<div>' + $.toJSON({url: 'mock/custom', method: 'GET', data: {}}) + '</div>');

    element.creme().widget().reload('mock/custom', {'a': 12});
    equal(0, $('h1', element).length);
    equal(element.html(), '<div>' + $.toJSON({url: 'mock/custom', method: 'GET', data: {'a': 12}}) + '</div>');
});

test('creme.widget.Frame.reload (url, async)', function() {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, undefined);
    equal(1, $('h1', element).length);
    equal(0, $('ul', element).length);

    this.backend.options.sync = false;
    this.backend.options.delay = 500;

    element.creme().widget().reload('mock/html2');

    stop(3);

    setTimeout(function() {
        assertOverlay(element, undefined);
        equal(1, $('h1', element).length);
        equal(0, $('ul', element).length);
        start();
    }, 90);

    setTimeout(function() {
        assertOverlay(element, 'wait', true);
        equal(1, $('h1', element).length);
        equal(0, $('ul', element).length);
        start();
    }, 150);

    setTimeout(function() {
        assertOverlay(element, undefined);
        equal(0, $('h1', element).length);
        equal(1, $('ul', element).length);
        start();
    }, 600);
});

test('creme.widget.Frame.reload (invalid url)', function() {
    var element = mock_frame_create('mock/html');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, undefined);
    equal(1, $('h1', element).length);
    equal(0, $('ul', element).length);

    element.creme().widget().reload('mock/error');

    assertOverlay(element, '500', true);
    equal(1, $('h1', element).length);
    equal(0, $('ul', element).length);
});

test('creme.widget.Frame.reload (invalid url, async)', function() {
    var element = mock_frame_create('mock/html');
    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, undefined);
    equal(1, $('h1', element).length);
    equal(0, $('ul', element).length);

    this.backend.options.sync = false;
    this.backend.options.delay = 500;

    element.creme().widget().reload('mock/unknown');

    stop(3);

    setTimeout(function() {
        assertOverlay(element, undefined);
        equal(1, $('h1', element).length);
        equal(0, $('ul', element).length);
        start();
    }, 90);

    setTimeout(function() {
        assertOverlay(element, 'wait', true);
        equal(1, $('h1', element).length);
        equal(0, $('ul', element).length);
        start();
    }, 150);

    setTimeout(function() {
        assertOverlay(element, '404', true);
        equal(1, $('h1', element).length);
        equal(0, $('ul', element).length);
        start();
    }, 600);
});


test('creme.widget.Frame.submit', function() {
    var element = mock_frame_create('mock/submit');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertOverlay(element, undefined);
    equal(1, $('form', element).length);

    var listeners = {
        done: function(event, data, statusText, dataType) {response.push([data, dataType]);},
        fail: function(event, data, error) {response.push('error')}
    };

    var response = [];
    element.creme().widget().submit($('form', element), listeners);
    deepEqual(response, [[MOCK_FRAME_CONTENT_FORM, 'text/html']], 'form html');

    this.backend.POST['mock/submit'] = this.backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON);

    response = [];
    element.creme().widget().reload('mock/submit');
    element.creme().widget().submit($('form', element), listeners);
    deepEqual(response, [[$.toJSON({value:1, added:[1, 'John Doe']}), 'text/json']], 'form json');

    this.backend.POST['mock/submit'] = this.backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON_NOTAG);

    response = [];
    element.creme().widget().reload('mock/submit');
    element.creme().widget().submit($('form', element), listeners);
    deepEqual(response, [[MOCK_FRAME_CONTENT_SUBMIT_JSON_NOTAG, 'text/html']], 'form json no tag');

    this.backend.POST['mock/submit'] = this.backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID);

    response = [];
    element.creme().widget().reload('mock/submit');
    element.creme().widget().submit($('form', element), listeners);
    deepEqual(response, [[MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID, 'text/html']], 'form json invalid');

    this.backend.POST['mock/submit'] = this.backend.response(500, 'HTTP - Error 500');

    response = [];
    element.creme().widget().reload('mock/submit');
    element.creme().widget().submit($('form', element), listeners);
    deepEqual(response, ['error']);
});
