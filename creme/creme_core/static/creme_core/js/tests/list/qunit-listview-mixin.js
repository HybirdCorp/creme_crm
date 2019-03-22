/* eslint operator-linebreak: ["error", "before"] */

(function($) {
    "use strict";

    var MOCK_FORM_EDIT = '<form><input type="text" name="edit" value=""/></form>';
    var MOCK_FORM_ADDTO = '<form><input type="text" name="addto" value=""/></form>';
    var MOCK_EDIT_SUMMARY = '<div><span class="bulk-selection-summary"></span></div>';

    window.QUnitListViewMixin = {
        beforeEach: function() {
            var self = this;
            this.resetListviewReloadContent();

            var backend = this.backend;

            this.setMockBackendGET({
                'mock/entity/edit': function(url, data, options) {
                    return backend.response(200, MOCK_FORM_EDIT);
                },
                'mock/entity/addto': function(url, data, options) {
                    return backend.response(200, MOCK_FORM_ADDTO);
                },
                'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
                'mock/error': backend.response(500, 'HTTP - Error 500')
            });

            this.setMockBackendPOST({
                'mock/listview/reload': function(url, data, options) {
                    var content = self._listviewReloadContent[data.id] || '';
                    return backend.response(Object.isEmpty(content) ? 200 : 404, content);
                },
                'mock/entity/delete': function(url, data, options) {
                    return backend.response(200, '');
                },
                'mock/entity/delete/fail': function(url, data, options) {
                    return backend.response(400, 'invalid response !');
                },
                'mock/entity/delete/nothing': function(url, data, options) {
                    var ids = (data.ids || '').split(',');

                    return backend.responseJSON(400, {
                        count: ids.length,
                        errors: ids.map(function(id) {
                            return id + ' cannot be deleted';
                        })
                    });
                },
                'mock/entity/delete/firstonly': function(url, data, options) {
                    var ids = (data.ids || '').split(',');

                    return backend.responseJSON(400, {
                        count: ids.length,
                        errors: ids.slice(1).map(function(id) {
                            return id + ' cannot be deleted';
                        })
                    });
                },
                'mock/entity/edit': function(url, data, options) {
                    var value = data.edit[0];

                    if (Object.isEmpty(value)) {
                        return backend.response(200, MOCK_FORM_EDIT);
                    } else if (value === 'summary') {
                        return backend.response(200, MOCK_EDIT_SUMMARY);
                    } else {
                        return backend.response(200, '');
                    }
                },
                'mock/entity/addto': function(url, data, options) {
                    if (Object.isEmpty(data.addto[0])) {
                        return backend.response(200, MOCK_FORM_ADDTO);
                    } else {
                        return backend.response(200, '');
                    }
                }
            });

            this.listviewActionListeners = {
                start: this.mockListener('action-start'),
                cancel: this.mockListener('action-cancel'),
                fail: this.mockListener('action-fail'),
                done: this.mockListener('action-done')
            };

            this._mockNextInnerPopupUUID = 1000;
            this.__innerPopupUUID = creme.utils.innerPopupUUID;

            creme.utils.innerPopupUUID = function() {
                var next = String(self._mockNextInnerPopupUUID);
                self._mockNextInnerPopupUUID += 1;
                return next;
            };
        },

        afterEach: function(env) {
            creme.utils.innerPopupUUID = this.__innerPopupUUID;

            $('.ui-dialog-content').dialog('destroy');
            creme.widget.shutdown($('body'));
        },

        createListViewHtml: function(options) {
            var defaultStatus = {
                /* TODO: (genglert) in rea list-views
                    - "sort_field" has been renamed "sort_key"
                    - the value of "sort_order" is "ASC" or "DESC"
                */
                sort_key: 'regular_field-name',
                sort_order: 'ASC',
                selected_rows: '',
                q_filter: '{}',
                ct_id: 67
            };

            options = $.extend({
                id: 'list',
                multiple: true,
                widgetclasses: [],
                tableclasses: [],
                columns: [],
                rows: [],
                actions: [],
                status: {}
            }, options || {});

            var renderRow = function(row) {
                return Array.isArray(row) ? '<tr class="selectable">' + row.join('') + '</tr>' : row;
            };

            var renderColumnTitle = function(column) {
                return Object.isString(column) ? column : column.title;
            };

            var renderColumnSearch = function(column) {
                return Object.isString(column) ? '' : column.search || '<tr></tr>';
            };

            var renderStatus = function(status) {
                return Object.entries(status).map(function(data) {
                    return '<input value="${value}" id="${name}" type="hidden" name="${name}" />'.template({name: data[0], value: data[1]});
                }).join('');
            };

            return (
                '<form class="ui-creme-widget widget-auto ui-creme-listview ${widgetclasses}" widget="ui-creme-listview" ${multiple} ${reloadurl}>'
                   + '<div class="list-header-container sticky-container sticky-container-standalone"></div>'
                   + '<table id="${id}" class="list_view listview listview-selection-multiple ${tableclasses}" data-total-count="${rowcount}">'
                       + '<thead>'
                           + '<tr><th>${formdata}</th></tr>'
                           + '<tr class="columns_top">'
                               + '<th class="choices"><input name="select_all" value="all" type="checkbox" title="Select All"/></th>'
                               + '<th class="actions">'
                                  + '<ul class="header-actions-list">'
                                       + '<li class="header-actions-trigger" title="Actions on the selected entities">'
                                           + '<span>Actions</span>'
                                           + '<div class="listview-actions-container">${headeractions}</div>'
                                       + '</li>'
                                  + '</ul>'
                               + '</th>'
                               + '${columns}'
                           + '</tr>'
                           + '<tr id="list_thead_search" class="columns_bottom">'
                               + '${searches}'
                           + '</tr>'
                       + '</thead>'
                       + '<tbody>${rows}</tbody>'
                   + '</table>'
               + '</form>').template({
                   id: options.id,
                   multiple: options.multiple ? 'multiple' : '',
                   reloadurl: options.reloadurl ? 'reload-url="' + options.reloadurl + '"' : '',
                   widgetclasses: options.widgetclasses.join(' '),
                   tableclasses: options.tableclasses.join(' '),
                   formdata: renderStatus($.extend({}, defaultStatus, options.status)),
                   headeractions: options.actions.join(''),
                   columns: options.columns.map(renderColumnTitle).join(''),
                   searches: options.columns.map(renderColumnSearch).join(''),
                   rows: options.rows.map(renderRow).join(''),
                   rowcount: options.rows.length
               });
        },

        createListView: function(options) {
            var html = this.createListViewHtml(options);
            var element = $(html).appendTo(this.qunitFixture());

            creme.widget.create(element);

            var listview = element.data('list_view');
            listview.setReloadUrl('mock/listview/reload');
            return listview;
        },

        createCellHtml: function(name, content, options) {
            options = options || {};
            return '<td class="lv-cell lv-cell-content ${sorted} column" name="${name}">${content}</td>'.template({
                name: name,
                content: content,
                sorted: options.sorted ? 'sorted' : ''
            });
        },

        createCheckCellHtml: function(id) {
            return '<td class="choices"><input type="checkbox" name="select_one" value="${id}" /></td>'.template({id: id});
        },

        createIdCellHtml: function(id) {
            return '<td><input type="hidden" name="entity_id" value="${id}" /></td>'.template({id: id});
        },

        createCheckAllColumnHtml: function() {
            return '<th class="choices"><center><input name="select_all" value="all" type="checkbox" title="Select All"></center></th>';
        },

        defaultListViewHtmlOptions: function(options) {
            return $.extend({
                columns: [this.createCheckAllColumnHtml(), '<th class="sorted column sortable cl_lv">Name</th>'],
                rows: [
                    [this.createCheckCellHtml('1'), this.createIdCellHtml('1'), this.createCellHtml('regular_field-name', 'A', {sorted: true})],
                    [this.createCheckCellHtml('2'), this.createIdCellHtml('2'), this.createCellHtml('regular_field-name', 'B', {sorted: true})],
                    [this.createCheckCellHtml('3'), this.createIdCellHtml('3'), this.createCellHtml('regular_field-name', 'C', {sorted: true})]
                ]
            }, options || {});
        },

        createDefaultListView: function(options) {
            var list_options = $.extend(this.defaultListViewHtmlOptions(), options || {});

            var html = this.createListViewHtml(list_options);
            var list = this.createListView(list_options);

            this.setListviewReloadContent(list_options.id || 'list', html);
            return list;
        },

        resetListviewReloadContent: function() {
            this._listviewReloadContent = {};
        },

        setListviewReloadContent: function(id, content) {
            this._listviewReloadContent[id] = content;
        },

        setListviewSelection: function(list, ids) {
            $(list).find('#selected_rows').val(ids.join(','));
        },

        assertOpenedListViewDialog: function() {
            var dialog = $('.ui-dialog [widget="ui-creme-listview"]');
            equal(1, dialog.length, 'is listview dialog opened');
            return dialog;
        },

        submitListViewSelectionDialog: function() {
            var button = this.findDialogButtonsByLabel(gettext("Validate the selection"));
            equal(1, button.length, 'is validation button exists');
            button.click();
        },

        mockNextInnerPopupUUID: function() {
            return String(this._mockNextInnerPopupUUID);
        }
    };
}(jQuery));
