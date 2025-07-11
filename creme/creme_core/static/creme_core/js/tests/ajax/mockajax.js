(function($) {

var MOCK_AJAX_FORM_CONTENT = '<form action="mock/add"><input id="name" type="text"/></form>';

QUnit.module("creme.mockajax.js", new QUnitMixin({
    beforeEach: function() {
        var self = this;

        this.backend = new creme.ajax.MockAjaxBackend({sync: false});
        $.extend(this.backend.GET, {
            'mock/html': this.backend.response(200, 'this is a test'),
            'mock/json': this.backend.responseJSON(200, {a: 1, b: "test"}),
            'mock/json/invalid': this.backend.response(200, '{"invalid json', {'Content-Type': 'text/json'}),
            'mock/add': this.backend.response(200, MOCK_AJAX_FORM_CONTENT),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500'),
            'mock/custom': function(url, data, options) {
                return self._custom_GET(url, data, options);
            }
        });

        $.extend(this.backend.POST, {
            'mock/add/widget': this.backend.response(
                200, '<json>' + JSON.stringify({value: '', added: [1, 'newitem']}) + '</json>'
            ),
            'mock/add': this.backend.response(200, MOCK_AJAX_FORM_CONTENT),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500'),
            'mock/custom': function(url, data, options) {
                return self._custom_POST(url, data, options);
            }
        });
    },

    afterEach: function() {
        $('.ui-dialog-content').dialog('destroy');
        creme.widget.shutdown($('body'));
    },

    _custom_GET: function(url, data, options) {
        return this.backend.responseJSON(200, {url: url, method: 'GET', data: data});
    },

    _custom_POST: function(url, data, options) {
        return this.backend.responseJSON(200, {url: url, method: 'POST', data: data});
    }
}));

QUnit.test('MockAjaxBackend.get', function(assert) {
    var response = {};
    this.backend.get('mock/html', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                      function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});
    assert.equal(response.responseText, 'this is a test');

    response = {};
    this.backend.get('mock/add', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                     function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});
    assert.equal(response.responseText, MOCK_AJAX_FORM_CONTENT);

    response = {};
    this.backend.get('mock/unknown', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                         function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});
    assert.equal(response.responseText, undefined);
    assert.equal(response.message, '');
    assert.equal(response.status, 404);

    response = {};
    this.backend.get('mock/forbidden', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                           function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});
    assert.equal(response.responseText, undefined);
    assert.equal(response.message, 'HTTP - Error 403');
    assert.equal(response.status, 403);

    response = {};
    this.backend.get('mock/error', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                       function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});
    assert.equal(response.responseText, undefined);
    assert.equal(response.message, 'HTTP - Error 500');
    assert.equal(response.status, 500);
});

QUnit.test('MockAjaxBackend.get (200, async, not elapsed)', function(assert) {
    var response = {};
    this.backend.get('mock/html', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                      function(responseText, xhr) { $.extend(response, xhr); });
    assert.deepEqual(response, {});

    var done = assert.async();

    setTimeout(function() {
        assert.deepEqual(response, {});
        done();
    }, 200);
});

QUnit.test('MockAjaxBackend.get (200, async)', function(assert) {
    var response = {};
    this.backend.get('mock/html', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                      function(responseText, xhr) { $.extend(response, xhr); });
    assert.deepEqual(response, {});

    var done = assert.async();

    setTimeout(function() {
        assert.equal(response.responseText, 'this is a test');
        done();
    }, 700);
});

QUnit.test('MockAjaxBackend.get (200, async, delay)', function(assert) {
    var response = {};
    this.backend.get('mock/html', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                      function(responseText, xhr) { $.extend(response, xhr); }, {delay: 100});
    assert.deepEqual(response, {});

    var done = assert.async();

    setTimeout(function() {
        assert.equal(response.responseText, 'this is a test');
        done();
    }, 200);
});

QUnit.test('MockAjaxBackend.get (404, async)', function(assert) {
    var response = {};
    this.backend.get('mock/unknown', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                         function(responseText, xhr) { $.extend(response, xhr); });
    assert.deepEqual(response, {});

    var done = assert.async();

    setTimeout(function() {
        assert.equal(response.responseText, undefined);
        assert.equal(response.message, '');
        assert.equal(response.status, 404);
        done();
    }, 600);
});

QUnit.test('MockAjaxBackend.get (custom)', function(assert) {
    var response = {};
    this.backend.get('mock/custom', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                        function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});

    assert.equal(response.responseText, JSON.stringify({url: 'mock/custom', method: 'GET', data: {}}));

    this.backend.get('mock/custom', {a: 1, b: 'test'},
                                        function(responseText) { $.extend(response, {responseText: responseText}); },
                                        function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});

    assert.equal(response.responseText, JSON.stringify({url: 'mock/custom', method: 'GET', data: {a: 1, b: 'test'}}));
});

QUnit.test('MockAjaxBackend.get (json, dataType=text)', function(assert) {
    var response = {};
    this.backend.get('mock/json', {},
                     function(responseText, data, xhr) { $.extend(response, {responseText: responseText, xhr: xhr}); },
                     function(responseText, xhr) { $.extend(response, xhr); },
                     {sync: true});

    assert.equal(response.xhr.status, 200);
    assert.equal(response.responseText, JSON.stringify({a: 1, b: 'test'}));
    assert.equal('text/json', response.xhr.getResponseHeader('Content-Type'));
    assert.equal('text/json', response.xhr.getResponseHeader('content-type'));
});

QUnit.test('MockAjaxBackend.get (json, dataType=json)', function(assert) {
    var response = {};
    this.backend.get('mock/json', {},
                     function(responseText, data, xhr) { $.extend(response, {responseText: responseText, xhr: xhr}); },
                     function(responseText, xhr) { $.extend(response, {xhr: xhr}); },
                     {sync: true, dataType: 'json'});

    assert.equal(response.xhr.status, 200);
    assert.deepEqual(response.responseText, {a: 1, b: 'test'});
    assert.equal('text/json', response.xhr.getResponseHeader('Content-Type'));
    assert.equal('text/json', response.xhr.getResponseHeader('content-type'));
});

QUnit.test('MockAjaxBackend.get (text, dataType=json)', function(assert) {
    var response = {};
    this.backend.get('mock/html', {},
                     function(responseText, data, xhr) { $.extend(response, {responseText: responseText, xhr: xhr}); },
                     function(responseText, xhr) { $.extend(response, {responseText: responseText, xhr: xhr}); },
                     {sync: true, dataType: 'json'});

    assert.equal(response.xhr.status, 500);
    assert.equal(true, response.responseText.indexOf('SyntaxError') !== -1);
});


QUnit.test('MockAjaxBackend.post', function(assert) {
    var response = {};
    this.backend.post('mock/add', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                      function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});
    assert.equal(response.responseText, MOCK_AJAX_FORM_CONTENT);

    response = {};
    this.backend.post('mock/add/widget', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                             function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});
    assert.equal(response.responseText, '<json>{"value":"","added":[1,"newitem"]}</json>');

    response = {};
    this.backend.post('mock/unknown', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                          function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});
    assert.equal(response.responseText, undefined);
    assert.equal(response.message, '');
    assert.equal(response.status, 404);

    response = {};
    this.backend.post('mock/forbidden', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                            function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});
    assert.equal(response.responseText, undefined);
    assert.equal(response.message, 'HTTP - Error 403');
    assert.equal(response.status, 403);

    response = {};
    this.backend.post('mock/error', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                        function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});
    assert.equal(response.responseText, undefined);
    assert.equal(response.message, 'HTTP - Error 500');
    assert.equal(response.status, 500);
});

QUnit.test('MockAjaxBackend.submit', function(assert) {
    var form = $(MOCK_AJAX_FORM_CONTENT);

    var response = {};
    this.backend.submit(form, function(responseText) { $.extend(response, {responseText: responseText}); },
                              function(responseText, xhr) { $.extend(response, xhr); }, {action: 'mock/add', sync: true});
    assert.equal(response.responseText, MOCK_AJAX_FORM_CONTENT);

    response = {};
    this.backend.submit(form, function(responseText) { $.extend(response, {responseText: responseText}); },
                              function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});
    assert.equal(response.responseText, MOCK_AJAX_FORM_CONTENT);

    response = {};
    this.backend.submit(form, function(responseText) { $.extend(response, {responseText: responseText}); },
                              function(responseText, xhr) { $.extend(response, xhr); }, {action: 'mock/error', sync: true});
    assert.equal(response.responseText, undefined);
    assert.equal(response.message, 'HTTP - Error 500');
    assert.equal(response.status, 500);
});

QUnit.test('MockAjaxBackend.post (custom)', function(assert) {
    var response = {};
    this.backend.post('mock/custom', {}, function(responseText) { $.extend(response, {responseText: responseText}); },
                                         function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});

    assert.equal(response.responseText, JSON.stringify({url: 'mock/custom', method: 'POST', data: {}}));

    this.backend.post('mock/custom', {a: 1, b: 'test'},
                                        function(responseText) { $.extend(response, {responseText: responseText}); },
                                        function(responseText, xhr) { $.extend(response, xhr); }, {sync: true});

    assert.equal(response.responseText, JSON.stringify({url: 'mock/custom', method: 'POST', data: {a: 1, b: 'test'}}));
});

}(jQuery));
