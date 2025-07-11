/* eslint operator-linebreak: ["error", "before"] */

(function($) {
    "use strict";

    var MOCK_BRICK_CONTENT = '<div class="brick ui-creme-widget" widget="brick" id="brick-${id}" data-brick-id="${id}"></div>';

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

            this.mockBrickState = {};

            var backend = this.backend;

            this.setMockBackendGET({
                'mock/brick/status': function(url, data, options) {
                    return backend.responseJSON(200, self.mockBrickState);
                },
                'mock/brick/all/reload': function(url, data, options) {
                    var brickContents = (data.brick_id || []).map(function(brick_type_id) {
                        var content = self._brickReloadContent['brick-' + brick_type_id];
                        return [brick_type_id, content || MOCK_BRICK_CONTENT.template({id: brick_type_id})];
                    });

                    return backend.responseJSON(200, brickContents);
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
                    return backend.responseJSON(200, self.mockBrickState);
                },
                'mock/brick/update': function(url, data, options) {
                    if (data.next) {
                        return backend.responseJSON(200, data.next);
                    } else {
                        return backend.response(200);
                    }
                },
                'mock/brick/delete': backend.response(200),
                'mock/form': backend.response(200),
                'mock/form/redirect': backend.response(200, 'mock/redirect', {'Content-Type': 'text/plain'}),
                'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
                'mock/error': backend.response(500, 'HTTP - Error 500')
            });

            this.setBrickStateUrl('mock/brick/status');
            this.setBrickAllRefreshUrl('mock/brick/all/reload');
        },

        afterEach: function(env) {
            $('.popover').trigger('modal-close');
            $('.ui-dialog-content').dialog('destroy');

            creme.widget.shutdown($('body'));
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
//                id: 'brick-for-test',
                id: 'creme_core-test',
                title: 'Test it',
                header: '',
                content: '',
                classes: [],
                deps: []
            }, options || {});

            var header = Array.isArray(options.header) ? options.header.join('') : options.header;
            var content = Array.isArray(options.content) ? options.content.join('') : options.content;
            var renderAttr = function(attr) {
                return '${0}="${1}"'.template(attr);
            };

            var html = (
//                '<div class="brick ui-creme-widget ${classes}" widget="brick" id="${id}" data-brick-deps="[${deps}]" ${attributes}>'
                '<div class="brick ui-creme-widget ${classes}" widget="brick" id="brick-${id}" data-brick-id="${id}" data-brick-deps="[${deps}]" ${attributes}>'
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
                     deps: options.deps.map(quoteHtml).join(','),
                     attributes: Object.entries(options.attributes || {}).map(renderAttr).join(' ')
                 });

            return html;
        },

        createBrickWidget: function(options) {
            var html = this.createBrickHtml(options);

            var element = $(html).appendTo(this.qunitFixture());
            var widget = creme.widget.create(element);
            var brick = widget.brick();

            this.assert.equal(true, brick.isBound());
            this.assert.equal(false, brick.isLoading());

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

            var element = $(html).appendTo(this.qunitFixture());
            var widget = creme.widget.create(element);
            var brick = widget.brick();

            this.assert.equal(true, brick.isBound());
            this.assert.equal(false, brick.isLoading());

            return widget;
        },

        createBrickActionHtml: function(options) {
            return (
                  '<a href="${url}" class="${classes} ${isasync} ${isdisabled}" data-action="${action}">'
                    + '<script type="application/json"><!-- {"options": ${options}, "data": ${data}} --></script>'
                + '</a>').template({
                    url: options.url || '',
                    action: options.action || 'redirect',
                    classes: (options.classes || []).join(' '),
                    isasync: options.async ? 'is-async-action' : '',
                    isdisabled: options.disabled ? 'is-disabled' : '',
                    options: JSON.stringify(options.options || {}),
                    data: JSON.stringify(options.data || {})
                });
        },

        _brickTableItemInfo: function(d) {
            return {
                selected: d.selected,
                ui: d.ui.get()
            };
        },

        assertBrickTableItems: function(expected, items) {
            this.assert.deepEqual(expected, items.map(this._brickTableItemInfo));
        },

        toggleBrickTableRows: function(brick, ids) {
            var element = brick.element();

            ids.forEach(function(id) {
                $('tr[data-row-index="' + id + '"] td[data-selectable-selector-column]', element).trigger('click');
            });
        }
    };
}(jQuery));
