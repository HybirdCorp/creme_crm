
(function($) {
    "use strict";

    var MOCK_BRICK_CONTENT = '<div class="brick ui-creme-widget" widget="brick" id="${id}"></div>';

    var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';
    var MOCK_FRAME_CONTENT_FORM = '<form action="mock/form">' +
        '<input type="text" id="firstname"></input>' +
        '<input type="text" id="lastname"></input>' +
        '<input type="submit" class="ui-creme-dialog-action"></input>' +
    '</form>';

    window.QUnitBrickMixin = {
        beforeEach: function() {
            var self = this;
            this.resetBrickReloadContent();

            this.anchor = $('<div></div>').appendTo($('body'));
            this.mockBrickState = {};

            var backend = this.backend;

            this.setMockBackendGET({
                'mock/brick/status': function(url, data, options) {
                    return backend.response(200, $.toJSON(self.mockBrickState));
                },
                'mock/brick/all/reload': function(url, data, options) {
                    var brickContents = (data.brick_id || []).map(function(id) {
                        var content = self._brickReloadContent[id];
                        return [id, content || MOCK_BRICK_CONTENT.template({id: id})];
                    });

                    return backend.response(200, brickContents);
                },
                'mock/view': backend.response(200, MOCK_FRAME_CONTENT),
                'mock/form': backend.response(200, MOCK_FRAME_CONTENT_FORM),
                'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
                'mock/error': backend.response(500, 'HTTP - Error 500')
            });

            this.setMockBackendPOST({
                'mock/brick/status': function(url, data, options) {
                    self.mockBrickState = data || {};
                    return backend.response(200, $.toJSON(self.mockBrickState));
                },
                'mock/brick/update': function(url, data, options) {
                    if (data.next) {
                        return backend.response(200, data.next);
                    } else {
                        return backend.response(200);
                    }
                },
                'mock/brick/delete': backend.response(200),
                'mock/form': backend.response(200),
                'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
                'mock/error': backend.response(500, 'HTTP - Error 500')
            });

            this.setBrickStateUrl('mock/brick/status');
            this.setBrickAllRefreshUrl('mock/brick/all/reload');
        },

        afterEach: function(env) {
            this.anchor.detach();

            $('.ui-dialog-content').dialog('destroy');
            creme.widget.shutdown($('body'));

            $('.brick').detach();
        },

        setBrickReloadContent: function(id, content) {
            this._brickReloadContent[id] = content;
        },

        resetBrickReloadContent: function() {
            this._brickReloadContent = {};
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
        }
    };
}(jQuery));
