
(function($) {
    "use strict";

    var MOCK_BRICK_CONTENT = '<div class="brick ui-creme-widget" widget="brick" id="${id}"></div>';

    var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';
    var MOCK_FRAME_CONTENT_FORM = '<form action="mock/form">'
        '<input type="text" id="firstname"></input>' +
        '<input type="text" id="lastname"></input>' +
        '<input type="submit" class="ui-creme-dialog-action"></input>' +
    '</form>';

    window.QUnitBrickMixin = {
        setup: function() {
            var self = this;

            this.resetMockCalls();
            this.resetMockRedirectCalls();
            this.resetMockBackendCalls();
            this.resetBrickReloadContent();

            this.anchor = $('<div></div>').appendTo($('body'));
            this.mockBrickState = {};

            this.__goTo = creme.utils.goTo;
            creme.utils.goTo = function(url) {
                self._redirectCalls.push(url);
            };

            var backend = this.backend = new creme.ajax.MockAjaxBackend({delay: 0});

            var __mockBackendCall = function(aux) {
                return function(url, data, options) {
                    self._backendCalls.push([url, data, options]);
                    return aux(url, data, options);
                };
            };

            $.extend(this.backend.GET, {
                'mock/brick/status': __mockBackendCall(function(url, data, options) {
                    return backend.response(200, $.toJSON(self.mockBrickState));
                }),
                'mock/brick/all/reload': __mockBackendCall(function(url, data, options) {
                    var brickContents = (data.brick_id || []).map(function(id) {
                        var content = self._brickReloadContent[id];
                        return [id, content || MOCK_BRICK_CONTENT.template({id: id})];
                    });

                    return backend.response(200, brickContents);
                }),
                'mock/view': __mockBackendCall(function(url, data, options) {
                    return backend.response(200, MOCK_FRAME_CONTENT);
                }),
                'mock/form': __mockBackendCall(function(url, data, options) {
                    return backend.response(200, MOCK_FRAME_CONTENT_FORM);
                }),
                'mock/forbidden': __mockBackendCall(backend.response(403, 'HTTP - Error 403')),
                'mock/error': __mockBackendCall(backend.response(500, 'HTTP - Error 500'))
            });

            $.extend(this.backend.POST, {
                'mock/brick/status': __mockBackendCall(function(url, data, options) {
                    self.mockBrickState = data || {};
                    return backend.response(200, $.toJSON(mockBrickState));
                }),
                'mock/brick/update': __mockBackendCall(function(url, data, options) {
                    if (data.next) {
                        return backend.response(200, data.next);
                    } else {
                        return backend.response(200);
                    }
                }),
                'mock/brick/delete': __mockBackendCall(function(url, data, options) {
                    return backend.response(200);
                }),
                'mock/form': __mockBackendCall(function(url, data, options) {
                    return backend.response(200);
                }),
                'mock/forbidden': __mockBackendCall(backend.response(403, 'HTTP - Error 403')),
                'mock/error': __mockBackendCall(backend.response(500, 'HTTP - Error 500'))
            });

            creme.ajax.defaultBackend(backend);

            this.setBrickStateUrl('mock/brick/status');
            this.setBrickAllRefreshUrl('mock/brick/all/reload');

            this.setupBrick();
        },

        teardown: function(env) {
            this.anchor.detach();

            $('.ui-dialog-content').dialog('destroy');
            creme.widget.shutdown($('body'));

            $('.brick').detach();

            creme.utils.goTo = this.__goTo;
            creme.ajax.defaultBackend(new creme.ajax.Backend());
        },

        setupBrick: function() {},

        setBrickReloadContent: function(id, content) {
            this._brickReloadContent[id] = content;
        },

        resetBrickReloadContent: function() {
            this._brickReloadContent = {};
        },

        resetMockBackendCalls: function() {
            this._backendCalls = [];
        },

        resetMockRedirectCalls: function() {
            this._redirectCalls = [];
        },

        resetMockCalls: function() {
            this._eventListenerCalls = {};
        },

        setBrickStateUrl: function(url) {
            if (url) {
                $('body').attr('data-brick-state-url', url);
            } else {
                $('body').removeAttr('data-brick-state-url');
            }
        },

        setBrickAllRefreshUrl: function(url) {
            if (Object.isString(url)) {
                $('body').attr('data-bricks-reload-url', url);
            } else {
                $('body').removeAttr('data-bricks-reload-url');
            }
        },

        mockBackendCalls: function() {
            return this._backendCalls;
        },

        mockBackendUrlCalls: function(url) {
            return this._backendCalls.filter(function(e) {
                return e[0] === url;
            }).map(function(e) {
                return e[1];
            });
        },

        mockRedirectCalls: function() {
            return this._redirectCalls;
        },

        mockListenerCalls: function(name) {
            if (name == undefined) {
                return $.extend({}, this._eventListenerCalls);
            }

            if (this._eventListenerCalls[name] === undefined)
                this._eventListenerCalls[name] = [];

            return this._eventListenerCalls[name];
        },

        mockListenerJQueryCalls: function(name) {
            return this.mockListenerCalls(name).map(function(e) {
                var event = e[0];
                var data = e.slice(1);
                return Object.isEmpty(data) === false ? [event.type, data] : [event.type];
            })
        },

        mockListener: function(name) {
            var self = this;
            return (function(name) {return function() {
                self.mockListenerCalls(name).push(Array.copy(arguments));
            }})(name);
        },

        assertRaises: function(block, expected, message) {
            QUnit.assert.raises(block,
                   function(error) {
                        ok(error instanceof expected, 'error is ' + expected);
                        equal(message, '' + error);
                        return true;
                   });
        }
    };
}(jQuery));
