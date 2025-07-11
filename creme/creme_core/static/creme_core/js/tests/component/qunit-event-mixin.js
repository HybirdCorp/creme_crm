(function($) {
    "use strict";

    window.QUnitEventMixin = {
        beforeEach: function() {
            this.resetMockListenerCalls();
        },

        resetMockListenerCalls: function() {
            this._eventListenerCalls = {};
        },

        mockListenerCalls: function(name) {
            if (name === undefined) {
                return $.extend({}, this._eventListenerCalls);
            }

            if (this._eventListenerCalls[name] === undefined) {
                this._eventListenerCalls[name] = [];
            }

            return this._eventListenerCalls[name];
        },

        mockListenerJQueryCalls: function(name) {
            if (name === undefined) {
                var calls = {};

                for (var key in this._eventListenerCalls) {
                    calls[key] = this.mockListenerJQueryCalls(key);
                }

                return calls;
            }

            return this.mockListenerCalls(name).map(function(e) {
                var event = e[0];
                var data = e.slice(1);
                return Object.isEmpty(data) === false ? [event.type, data] : [event.type];
            });
        },

        mockListener: function(name) {
            var self = this;
            return (function(name) {
                return function() {
                    self.mockListenerCalls(name).push(Array.from(arguments));
                };
            }(name));
        },

        bindTestOn: function(source, event, callback, args) {
            var self = this;
            var done = self.assert.async();

            source.on(event, function() {
                var success = false;

                /* move call in another "thread" to prevent initialization issues */
                setTimeout(function() {
                    try {
                        callback.apply(self, args);
                        success = true;
                    } finally {
                        self.assert.ok(success, 'async test on event "${event}" as failed. See logs for stacktrace.'.template({
                            event: event
                        }));
                        done();
                    }
                }, 0);
            });
        }
    };
}(jQuery));
