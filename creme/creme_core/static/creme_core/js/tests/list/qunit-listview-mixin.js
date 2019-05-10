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
                    var q_filter = data.q_filter ? data.q_filter[0] : '';
                    var content = self._listviewReloadContent[q_filter] || '';
                    return backend.response(Object.isEmpty(content) ? 404 : 200, content);
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
                },
                'mock/listview/filter/delete': backend.response(200, ''),
                'mock/listview/view/delete': backend.response(200, '')
            });

            this.listviewActionListeners = {
                start: this.mockListener('action-start'),
                cancel: this.mockListener('action-cancel'),
                fail: this.mockListener('action-fail'),
                done: this.mockListener('action-done')
            };
/*
            this._mockNextInnerPopupUUID = 1000;
            this.__innerPopupUUID = creme.utils.innerPopupUUID;

            creme.utils.innerPopupUUID = function() {
                var next = String(self._mockNextInnerPopupUUID);
                self._mockNextInnerPopupUUID += 1;
                return next;
            };
*/
        },

        afterEach: function(env) {
            // creme.utils.innerPopupUUID = this.__innerPopupUUID;

            $('.ui-dialog-content').dialog('destroy');
            creme.widget.shutdown($('body'));
        },

        createActionHtml: function(options) {
            var renderAttr = function(attr) {
                return '${0}="${1}"'.template(attr);
            };

            return (
                '<a href="${url}" data-action="${action}" class="${classes}" ${attrs}>'
                  + '<script type="application/json"><!-- ${data} --></script>'
              + '</a>').template({
                classes: (options.classes || []).join(' '),
                url: options.url || '',
                action: options.action || '',
                attrs: Object.entries(options.attrs || {}).map(renderAttr).join(' '),
                data: $.toJSON({
                    data: options.data || {},
                    options: options.options || {}
                })
            });
        },

        createListViewHtml: function(options) {
            var defaultStatus = {
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
                hatbarcontrols: [],
                hatbarbuttons: [],
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

            var createActionHtml = this.createActionHtml.bind(this);

            var renderHatBarButton = function(button) {
                if (Object.isString(button)) {
                    return button;
                }

                return createActionHtml($.extend({
                    classes: ['with-icon']
                }, button || {}));
            };

            var renderPopupMenuAction = function(button) {
                if (Object.isString(button)) {
                    return button;
                }

                return '<div class="listview-action">' + createActionHtml(button) + '</div>';
            };


            var renderHeaderControl = function(options) {
                if (Object.isString(options)) {
                    return options;
                }

                options = options || {};

                return (
                    '<div class="list-control-group list-${group}">'
                        + '<fieldset>'
                            + '<select name="${name}" class="list-${group}-selector">${options}</select>'
                            + '${actions}'
                        + '</fieldset>'
                    + '</div>').template({
                        name: options.name || '',
                        group: options.group || 'filters',
                        options: (options.options || []).join(''),
                        actions: (options.actions || []).map(createActionHtml)
                    });
            };

            return (
                '<form class="ui-creme-widget widget-auto ui-creme-listview ${widgetclasses}" widget="ui-creme-listview" ${multiple} ${reloadurl}>'
                   + '<div class="list-header-container sticky-container sticky-container-standalone">'
                       + '<div class="list-header sticks-horizontally">'
                           + '<div class="list-title-container">'
                               + '<span class="list-title"></title>'
                               + '<div class="list-controls">${hatbarcontrols}</div>'
                           + '</div>'
                           + '<div class="list-header-buttons clearfix">${hatbarbuttons}</div>'
                       + '</div>'
                   + '</div>'
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
                       + '<tfoot><tr><td>'
                           + '<div class="list-footer-container sticks-horizontally">'
                               + '<div class="list-footer-stats"></div>'
                               + '<div class="listview-pagination"></div>'
                               + '<div class="list-footer-page-selector">'
                                   + '<select name="rows" class="list-pagesize-selector">'
                                       + '<option value="10">10</option>'
                                       + '<option value="25">25</option>'
                                   + '</select>'
                               + '</div>'
                           + '</div>'
                       + '</td></tr></tfoot>'
                   + '</table>'
               + '</form>').template({
                   id: options.id,
                   multiple: options.multiple ? 'multiple' : '',
                   reloadurl: options.reloadurl ? 'reload-url="' + options.reloadurl + '"' : '',
                   hatbarbuttons: options.hatbarbuttons.map(renderHatBarButton).join(''),
                   hatbarcontrols: options.hatbarcontrols.map(renderHeaderControl).join(''),
                   widgetclasses: options.widgetclasses.join(' '),
                   tableclasses: options.tableclasses.join(' '),
                   formdata: renderStatus($.extend({}, defaultStatus, options.status)),
                   headeractions: options.actions.map(renderPopupMenuAction).join(''),
                   columns: options.columns.map(renderColumnTitle).join(''),
                   searches: options.columns.map(renderColumnSearch).join(''),
                   rows: options.rows.map(renderRow).join(''),
                   rowcount: options.rows.length
               });
        },

        createListView: function(options) {
            var html = this.createListViewHtml(options);
            var element = $(html).appendTo(this.qunitFixture());

            var widget = creme.widget.create(element);
            widget.controller().setReloadUrl('mock/listview/reload');

            return widget;
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

        createColumnTitleHtml: function(label, options) {
            options = options || {};
            var is_sorted = options.sorted;
            var is_sortable = options.sortable || is_sorted;

            return (
                '<th data-column-key="${name}" class="column cl_lv ${sortable} ${sorted}">'
                    + '<button type="button" title="" ${disabled}>${label}</button>'
                + '</th>').template({
                    label: label,
                    name: options.name,
                    sortable: is_sortable ? 'sortable' : '',
                    sorted: is_sorted ? 'sorted' : '',
                    disabled: options.disabled ? 'disabled' : ''
                });
        },

        createColumnSearchHtml: function(label, options) {
            options = options || {};

            return (
                '<th class="column hd_cl_lv ${sorted}">'
                    + '<input name="${name}" title="${label}" type="text" value="${search}">'
                + '</th>').template({
                    label: label,
                    name: options.name,
                    sorted: options.sorted ? 'sorted' : '',
                    search: options.search || ''
                });
        },

        createActionCellHtml: function(options) {
            var createActionHtml = this.createActionHtml.bind(this);

            var renderAction = function(button) {
                return '<div class="listview-action ${isdefault}">${action}</div>'.template({
                    isdefault: button.isdefault ? 'default-row-action' : '',
                    action: createActionHtml(button)
                });
            };

            return (
                '<td class="list_view_actions actions">'
                   + '<ul class="row-actions-list">'
                     + '<li class="row-actions-trigger">'
                       + '<div class="listview-actions-container">${actions}</div>'
                     + '</li>'
                   + '</ul>'
              + '</td>').template({
                    actions: (options.actions || []).map(renderAction).join('')
                });
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
            var listOptions = $.extend(this.defaultListViewHtmlOptions(), options || {});

            var html = this.createListViewHtml(listOptions);
            var list = this.createListView(listOptions);

            this.setListviewReloadContent(listOptions.id || 'list', html);
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

        validateListViewSelectionDialog: function(dialog) {
            dialog = (dialog || $('.ui-dialog')).filter(function() {
                return $(this).find('[widget="ui-creme-listview"]').length > 0;
            });

            var button = this.findDialogButtonsByLabel(gettext("Validate the selection"), dialog);
            equal(1, button.length, 'is validation button exists');
            button.click();
        },

        assertOpenedListViewDialog: function() {
            var dialog = $('.ui-dialog').filter(function() {
                return $(this).find('[widget="ui-creme-listview"]').length > 0;
            });

            equal(1, dialog.length, 'is listview dialog opened');
            return dialog;
        }
/*
        submitListViewSelectionDialog: function() {
            var button = this.findDialogButtonsByLabel(gettext("Validate the selection"));
            equal(1, button.length, 'is validation button exists');
            button.click();
        },

        mockNextInnerPopupUUID: function() {
            return String(this._mockNextInnerPopupUUID);
        }
*/
    };
}(jQuery));
