(function($) {
    "use strict";

    window.QUnitAjaxMixin = {
        beforeEach: function() {
            var self = this;

            this.resetMockRedirectCalls();
            this.resetMockReloadCalls();
            this.resetMockBackendCalls();
            this.resetMockHistoryChanges();

            this.__redirect = creme.utils.redirect;
            creme.utils.redirect = function(url) {
                self._redirectCalls.push((url || '').replace(/.*?:\/\/[^\/]*/g, ''));
            };

            this.__reload = creme.utils.reload;
            creme.utils.reload = function() {
                self._reloadCalls.push(window.location.href);
            };

            this.__historyPush = creme.history.push;
            creme.history.push = function(url, title) {
                self._historyChanges.push(['push', url, title]);
            };

            this.__historyReplace = creme.history.replace;
            creme.history.replace = function(url, title) {
                self._historyChanges.push(['replace', url, title]);
            };

            this.backend = this.buildMockBackend();

            // console.info('[qunit-ajax-mixin] setup backend', this.backend.options);
            creme.ajax.defaultBackend(this.backend);

            // console.info('[qunit-ajax-mixin] setup cache backend');
            creme.ajax.defaultCacheBackend(this.backend);
        },

        afterEach: function(env) {
            creme.utils.redirect = this.__redirect;
            creme.utils.reload = this.__reload;
            creme.history.push = this.__historyPush;
            creme.history.replace = this.__historyReplace;

            // console.info('[qunit-ajax-mixin] teardown backend');
            creme.ajax.defaultBackend(new creme.ajax.Backend());

            // console.info('[qunit-ajax-mixin] teardown cache backend');
            creme.ajax.defaultCacheBackend(new creme.ajax.CacheBackend(creme.ajax.defaultBackend(), {
                condition: new creme.ajax.CacheBackendTimeout(120 * 1000)
            }));
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

        resetMockReloadCalls: function() {
            this._reloadCalls = [];
        },

        resetMockHistoryChanges: function() {
            this._historyChanges = [];
        },

        mockBackendCalls: function() {
            return this._backendCalls;
        },

        mockBackendUrlCalls: function(url) {
            var calls = this._backendCalls;

            if (url) {
                calls = calls.filter(function(e) {
                    return e[0] === url;
                });
            }

            return calls.map(function(e) {
                var method = e[1], data = e[2];
                data = (data instanceof jQuery) ? data.html() : data;
                return url ? [method, data] : [e[0], method, data];
            });
        },

        assertBackendUrlErrors: function(expected, calls) {
            this.assert.deepEqual(expected, calls.map(function(e) {
                var data = e[1], xhr = e[2];
                return [e[0], data, {
                    status: xhr.status,
                    message: xhr.message
                }];
            }));
        },

        mockRedirectCalls: function() {
            return this._redirectCalls;
        },

        mockReloadCalls: function() {
            return this._reloadCalls;
        },

        mockHistoryChanges: function() {
            return this._historyChanges;
        }
    };
}(jQuery));
