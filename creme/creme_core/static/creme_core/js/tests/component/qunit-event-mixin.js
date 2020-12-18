(function($) {
    "use strict";

    window.QUnitEventMixin = {
        beforeEach: function() {
            this.resetMockListenerCalls();
        },

        resetMockListenerCalls: function() {
            this._eventListenerCalls = {};
        },

        mockSummarizeObject: function(data) {
            var dump = data;

            if (Object.isSubClassOf(data, creme.component.Component)) {
                dump = {__class__: 'Component'};

                for (var key in data) {
                    var value = data[key];

                    if (!Object.isFunc(value)) {
                        dump[key] = this.mockSummarizeObject(value);
                    }
                }

                return dump;
            } else if (Object.getPrototypeOf(data).jquery) {
                if (data.length === 1) {
                    return $('<div>').append(data).html();
                } else {
                    return {__class__: 'jQuery', selector: data.selector};
                }
            } else {
                return data;
            }
        },

        mockListenerCalls: function(key, summarize) {
            var filtered = {};
            var calls = this._eventListenerCalls;
            var nokey = Object.isEmpty(key);

            var names = nokey ? Object.keys(calls) : key.split(' ');

            names.forEach(function(name) {
                if (Object.isFunc(summarize)) {
                    filtered[name] = (calls[name] || []).map(summarize);
                } else {
                    filtered[name] = calls[name] || [];
                }
            });

            if (!nokey && names.length === 1) {
                return filtered[names[0]];
            } else {
                return filtered;
            }
        },

        mockListenerJQueryCalls: function(key) {
            return this.mockListenerCalls(key, function(e) {
                var event = e[0];
                var data = e.slice(1);
                return Object.isEmpty(data) === false ? [event.type, data] : [event.type];
            });
        },

        mockListener: function(name) {
            var self = this;

            return (function(name) {
                return function() {
                    var calls = self._eventListenerCalls;
                    var listenerCalls = calls[name] || [];

                    listenerCalls.push(Array.copy(arguments));
                    calls[name] = listenerCalls;
                };
            }(name));
        },

        bindTestOn: function(source, event, callback, args) {
            var self = this;

            source.on(event, function() {
                var success = false;

                /* move call in another "thread" to prevent initialization issues */
                setTimeout(function() {
                    try {
                        callback.apply(self, args);
                        success = true;
                    } finally {
                        ok(success, 'async test on event "${event}" as failed. See logs for stacktrace.'.template({
                            event: event
                        }));
                        start();
                    }
                }, 0);
            });
        }
    };
}(jQuery));
