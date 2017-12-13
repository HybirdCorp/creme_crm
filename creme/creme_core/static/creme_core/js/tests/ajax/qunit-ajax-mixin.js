(function($) {
    "use strict";

    window.QUnitAjaxMixin = {
        beforeEach: function() {
            var self = this;

            this.resetMockRedirectCalls();
            this.resetMockBackendCalls();

            this.__goTo = creme.utils.goTo;
            creme.utils.goTo = function(url) {
                self._redirectCalls.push(url);
            };

            this.backend = this.buildMockBackend();

            // console.info('[qunit-ajax-mixin] setup backend', this.backend.options);
            creme.ajax.defaultBackend(this.backend);
        },

        afterEach: function(env) {
            creme.utils.goTo = this.__goTo;
            // console.info('[qunit-ajax-mixin] teardown backend');
            creme.ajax.defaultBackend(new creme.ajax.Backend());
        },

        buildMockBackend: function() {
            return new creme.ajax.MockAjaxBackend({delay: 0, sync: true});
        },

        __mockBackendResponse: function(method, response) {
            var self = this;

            return function(url, data, options) {
                self._backendCalls.push([url, method, data, options]);

                if (Object.isFunc(response)) {
                    return response(url, data, options);
                } else {
                    return response;
                }
            };
        },

        setMockBackendPOST: function(responses) {
            for (var url in responses) {
                this.backend.POST[url] = this.__mockBackendResponse('POST', responses[url]);
            }
        },

        setMockBackendGET: function(responses) {
            for (var url in responses) {
                this.backend.GET[url] = this.__mockBackendResponse('GET', responses[url]);
            }
        },

        resetMockBackendCalls: function() {
            this._backendCalls = [];
        },

        resetMockRedirectCalls: function() {
            this._redirectCalls = [];
        },

        mockBackendCalls: function() {
            return this._backendCalls;
        },

        mockBackendUrlCalls: function(url) {
            return this._backendCalls.filter(function(e) {
                return e[0] === url;
            }).map(function(e) {
                var method = e[1], data = e[2];
                data = (data instanceof jQuery) ? data.html() : data;
                return [method, data];
            });
        },

        mockRedirectCalls: function() {
            return this._redirectCalls;
        }
    };
}(jQuery));
