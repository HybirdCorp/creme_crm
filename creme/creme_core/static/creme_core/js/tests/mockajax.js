MockAjaxBackend = function(options) {
	var options = $.extend({
		delay: 500,
		sync: false,
		debug: false
	}, options);

    return {
    	options: options,

        GET: {},
        POST: {},

        send: function(url, data, method, on_success, on_error, options)
        {
            var self = this;
            var options = $.extend({}, this.options, options);

            if (options.sync !== true)
            {
                 options.sync = true;
                 var delay = options.delay !== undefined ? options.delay : 500;

                 window.setTimeout(function() {self.send(url, data, method, on_success, on_error, options);}, delay);
                 return;
            }

            var response = method !== undefined ? method[url] : undefined;

            if (response === undefined)
                response = this.response(404, '');

            if (options.debug)
                console.log('mockajax > send > url:', url, 'options:', options, 'response:', response);

            if (response.status !== 200)
                return creme.object.invoke(on_error, response.responseText, new creme.ajax.AjaxResponse(response.status,
                                                                                                        response.responseText,
                                                                                                        response.xhr));

            return creme.object.invoke(on_success, response.responseText);
        },

        get:function(url, data, on_success, on_error, options) {
            return this.send(url, data, this.GET, on_success, on_error, options);
        },

        post:function(url, data, on_success, on_error, options) {
            return this.send(url, data, this.POST, on_success, on_error, options);
        },

        submit:function(form, on_success, on_error, options) {
            var options = options || {};
            var action = options.action || form.attr('action');
            return this.send(action, undefined, this.POST, on_success, on_error, options);
        },

        // mock object (thanks to jquery.form author)
        response: function(status, data) {
            return {
                aborted: 0,
                responseText: data,
                responseXML: null,
                status: status,
                statusText: 'n/a',
                getAllResponseHeaders: function() {},
                getResponseHeader: function() {},
                setRequestHeader: function() {},
                abort: function(status) {}
            };
        }
    };
}


var MOCK_AJAX_FORM_CONTENT = '<form action="mock/add"><input id="name" type="text"/></form>';

module("creme.mockajax.js", {
    setup: function() {
        this.backend = new MockAjaxBackend();
        $.extend(this.backend.GET, {'mock/html': this.backend.response(200, 'this is a test'),
                                    'mock/add': this.backend.response(200, MOCK_AJAX_FORM_CONTENT),
                                    'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                    'mock/error': this.backend.response(500, 'HTTP - Error 500')});

        $.extend(this.backend.POST, {'mock/add/widget': this.backend.response(200, '<json>' + $.toJSON({value:'', added:[1, 'newitem']}) + '</json>'),
                                     'mock/add': this.backend.response(200, MOCK_AJAX_FORM_CONTENT),
                                     'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                     'mock/error': this.backend.response(500, 'HTTP - Error 500')});

        creme.widget.unregister('ui-creme-frame');
        creme.widget.declare('ui-creme-frame', new MockFrame(this.backend));
    },

    teardown: function() {
    },
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
