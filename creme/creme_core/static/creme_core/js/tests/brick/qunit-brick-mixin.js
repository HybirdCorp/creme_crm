/* eslint operator-linebreak: ["error", "before"] */

(function($) {
    "use strict";

    var MOCK_BRICK_CONTENT = '<div class="brick ui-creme-widget" widget="brick" id="${id}"></div>';

    var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';
    var MOCK_FRAME_CONTENT_FORM = '<form action="${action}">'
                                    + '<input type="text" id="firstname"></input>'
                                    + '<input type="text" id="lastname"></input>'
                                    + '<input type="submit" class="ui-creme-dialog-action"></input>'
                                + '</form>';

    var quoteHtml = function(d) {
        return '&quot;' + d + '&quot;';
    };

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
                'mock/form': backend.response(200, MOCK_FRAME_CONTENT_FORM.template({action: 'mock/form'})),
                'mock/form/redirect': backend.response(200,
                                                       MOCK_FRAME_CONTENT_FORM.template({action: 'mock/form/redirect'})),
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
                'mock/form/redirect': backend.response(200, 'mock/redirect', {'Content-Type': 'text/json'}),
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
        },

        createBrickHtml: function(options) {
            options = $.extend({
                id: 'brick-for-test',
                title: 'Test it',
                header: '',
                content: '',
                classes: [],
                deps: []
            }, options || {});

            var header = Array.isArray(options.header) ? options.header.join('') : options.header;
            var content = Array.isArray(options.content) ? options.content.join('') : options.content;

            var html = (
                '<div class="brick ui-creme-widget ${classes}" widget="brick" id="${id}" data-brick-deps="[${deps}]">'
                     + '<div class="brick-header">'
                         + '<div class="brick-title">${title}</div>'
                         + '${header}'
                     + '</div>'
                     + '<div class="brick-content">${content}</div>'
                 + '</div>').template({
                     id: options.id,
                     content: content,
                     header: header,
                     title: options.title,
                     classes: options.classes.join(' '),
                     deps: options.deps.map(quoteHtml).join(',')
                 });

            return html;
        },

        createBrickWidget: function(options) {
            var html = this.createBrickHtml(options);

            var element = $(html).appendTo($('body'));
            var widget = creme.widget.create(element);
            var brick = widget.brick();

            equal(true, brick.isBound());
            equal(false, brick.isLoading());

            return widget;
        },

        createBrickTableHtml: function(options) {
            options = $.extend({
                columns: [],
                rows: []
            }, options || {});

            var renderRow = function(row) {
                return Array.isArray(row) ? '<tr>' + row.join('') + '</tr>' : row;
            };

            var header = Array.isArray(options.header) ? options.header : [options.header];
            header.push(
                 '<div class="brick-selection-indicator">'
                    + '<span class="brick-selection-title" data-title-format="%d entry on %d" data-plural-format="%d entries on %d"></span>'
                 + '</div>');

            var content = Array.isArray(options.content) ? options.content : [options.content];
            content.push((
                '<table class="brick-table-content">'
                    + '<thead><tr>${columns}</tr></thead>'
                    + '<tbody>${rows}</tbody>'
              + '</table>').template({
                  columns: options.columns.join(''),
                  rows: options.rows.map(renderRow).join('')
              }));

            return this.createBrickHtml($.extend({
                content: content,
                header: options.header ? [header, options.header] : header
            }, options));
        },

        createBrickTable: function(options) {
            var html = this.createBrickTableHtml(options);

            var element = $(html).appendTo($('body'));
            var widget = creme.widget.create(element);
            var brick = widget.brick();

            equal(true, brick.isBound());
            equal(false, brick.isLoading());

            return widget;
        },

        _brickTableItemInfo: function(d) {
            return {
                selected: d.selected,
                ui: d.ui.get()
            };
        },

        assertBrickTableItems: function(expected, items) {
            deepEqual(expected, items.map(this._brickTableItemInfo));
        },

        toggleBrickTableRows: function(brick, ids) {
            var element = brick.element();

            ids.forEach(function(id) {
                $('tr[data-row-index="' + id + '"] td[data-selectable-selector-column]', element).click();
            });
        }
    };
}(jQuery));
