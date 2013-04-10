var MOCK_AJAX_FORM_CONTENT = '<form action="mock/add"><input id="name" type="text"/></form>';

module("creme.mockajax.js", {
    setup: function() {
        var self = this;

        this.backend = new creme.ajax.MockAjaxBackend();
        $.extend(this.backend.GET, {'mock/html': this.backend.response(200, 'this is a test'),
                                    'mock/add': this.backend.response(200, MOCK_AJAX_FORM_CONTENT),
                                    'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                    'mock/error': this.backend.response(500, 'HTTP - Error 500'),
                                    'mock/custom': function(url, data, options) {
                                        return self._custom_GET(url, data, options);
                                    }});

        $.extend(this.backend.POST, {'mock/add/widget': this.backend.response(200, '<json>' + $.toJSON({value:'', added:[1, 'newitem']}) + '</json>'),
                                     'mock/add': this.backend.response(200, MOCK_AJAX_FORM_CONTENT),
                                     'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                     'mock/error': this.backend.response(500, 'HTTP - Error 500'),
                                     'mock/custom': function(url, data, options) {
                                         return self._custom_POST(url, data, options);
                                     }});

        creme.widget.unregister('ui-creme-frame');
        creme.widget.declare('ui-creme-frame', new MockFrame(this.backend));
    },

    teardown: function() {
    },

    _custom_GET: function(url, data, options) {
        return this.backend.response(200, $.toJSON({url: url, method: 'GET', data: data}));
    },

    _custom_POST: function(url, data, options) {
        return this.backend.response(200, $.toJSON({url: url, method: 'POST', data: data}));
    }
});


test('MockAjaxBackend.get', function() {
    var response = {}
    this.backend.get('mock/html', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                      function(responseText, xhr) {$.extend(response, xhr);}, {sync:true});
    equal(response.responseText, 'this is a test');

    var response = {}
    this.backend.get('mock/add', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                     function(responseText, xhr) {$.extend(response, xhr);}, {sync:true});
    equal(response.responseText, MOCK_AJAX_FORM_CONTENT);

    response = {}
    this.backend.get('mock/unknown', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                         function(responseText, xhr) {$.extend(response, xhr);}, {sync:true});
    equal(response.responseText, undefined);
    equal(response.message, '');
    equal(response.status, 404);

    response = {}
    this.backend.get('mock/forbidden', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                           function(responseText, xhr) {$.extend(response, xhr);}, {sync:true});
    equal(response.responseText, undefined);
    equal(response.message, 'HTTP - Error 403');
    equal(response.status, 403);

    response = {}
    this.backend.get('mock/error', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                       function(responseText, xhr) {$.extend(response, xhr);}, {sync:true});
    equal(response.responseText, undefined);
    equal(response.message, 'HTTP - Error 500');
    equal(response.status, 500);
});

asyncTest('MockAjaxBackend.get (200, async, not elapsed)', function() {
    var response = {}
    this.backend.get('mock/html', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                      function(responseText, xhr) {$.extend(response, xhr);});
    deepEqual(response, {});

    setTimeout(function() {
        deepEqual(response, {});
        start();
    }, 200);
});

asyncTest('MockAjaxBackend.get (200, async)', function() {
    var response = {}
    this.backend.get('mock/html', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                      function(responseText, xhr) {$.extend(response, xhr);});
    deepEqual(response, {});

    setTimeout(function() {
        equal(response.responseText, 'this is a test');
        start();
    }, 700);
});

asyncTest('MockAjaxBackend.get (200, async, delay)', function() {
    var response = {}
    this.backend.get('mock/html', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                      function(responseText, xhr) {$.extend(response, xhr);}, {delay:100});
    deepEqual(response, {});

    setTimeout(function() {
        equal(response.responseText, 'this is a test');
        start();
    }, 200);
});

asyncTest('MockAjaxBackend.get (404, async)', function() {
    var response = {}
    this.backend.get('mock/unknown', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                         function(responseText, xhr) {$.extend(response, xhr);});
    deepEqual(response, {});

    setTimeout(function() {
        equal(response.responseText, undefined);
        equal(response.message, '');
        equal(response.status, 404);
        start();
    }, 600);
});


test('MockAjaxBackend.get (custom)', function() {
    var response = {}
    this.backend.get('mock/custom', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                        function(responseText, xhr) {$.extend(response, xhr);}, {sync: true});

    equal(response.responseText, $.toJSON({url: 'mock/custom', method: 'GET', data: {}}));

    this.backend.get('mock/custom', {a: 1, b: 'test'},
                                        function(responseText) {$.extend(response, {responseText:responseText});},
                                        function(responseText, xhr) {$.extend(response, xhr);}, {sync: true});

    equal(response.responseText, $.toJSON({url: 'mock/custom', method: 'GET', data: {a: 1, b: 'test'}}));
});

test('MockAjaxBackend.post', function() {
    var response = {}
    this.backend.post('mock/add', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                      function(responseText, xhr) {$.extend(response, xhr);}, {sync:true});
    equal(response.responseText, MOCK_AJAX_FORM_CONTENT);

    var response = {}
    this.backend.post('mock/add/widget', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                             function(responseText, xhr) {$.extend(response, xhr);}, {sync:true});
    equal(response.responseText, '<json>{"value":"","added":[1,"newitem"]}</json>');

    response = {}
    this.backend.post('mock/unknown', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                          function(responseText, xhr) {$.extend(response, xhr);}, {sync:true});
    equal(response.responseText, undefined);
    equal(response.message, '');
    equal(response.status, 404);

    response = {}
    this.backend.post('mock/forbidden', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                            function(responseText, xhr) {$.extend(response, xhr);}, {sync:true});
    equal(response.responseText, undefined);
    equal(response.message, 'HTTP - Error 403');
    equal(response.status, 403);

    response = {}
    this.backend.post('mock/error', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                        function(responseText, xhr) {$.extend(response, xhr);}, {sync:true});
    equal(response.responseText, undefined);
    equal(response.message, 'HTTP - Error 500');
    equal(response.status, 500);
});

test('MockAjaxBackend.submit', function() {
    var form = $(MOCK_AJAX_FORM_CONTENT);

    var response = {}
    this.backend.submit(form, function(responseText) {$.extend(response, {responseText:responseText});},
                              function(responseText, xhr) {$.extend(response, xhr);}, {action:'mock/add', sync:true});
    equal(response.responseText, MOCK_AJAX_FORM_CONTENT);

    response = {}
    this.backend.submit(form, function(responseText) {$.extend(response, {responseText:responseText});},
                              function(responseText, xhr) {$.extend(response, xhr);}, {sync:true});
    equal(response.responseText, MOCK_AJAX_FORM_CONTENT);

    response = {}
    this.backend.submit(form, function(responseText) {$.extend(response, {responseText:responseText});},
                              function(responseText, xhr) {$.extend(response, xhr);}, {action:'mock/error', sync:true});
    equal(response.responseText, undefined);
    equal(response.message, 'HTTP - Error 500');
    equal(response.status, 500);
});


test('MockAjaxBackend.post (custom)', function() {
    var response = {}
    this.backend.post('mock/custom', {}, function(responseText) {$.extend(response, {responseText:responseText});},
                                        function(responseText, xhr) {$.extend(response, xhr);}, {sync: true});

    equal(response.responseText, $.toJSON({url: 'mock/custom', method: 'POST', data: {}}));

    this.backend.post('mock/custom', {a: 1, b: 'test'},
                                        function(responseText) {$.extend(response, {responseText:responseText});},
                                        function(responseText, xhr) {$.extend(response, xhr);}, {sync: true});

    equal(response.responseText, $.toJSON({url: 'mock/custom', method: 'POST', data: {a: 1, b: 'test'}}));
});

