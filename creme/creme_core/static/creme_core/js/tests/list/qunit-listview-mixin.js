/* eslint operator-linebreak: ["error", "before"] */

(function($) {
    "use strict";

    var MOCK_FORM_ADDTO = '<form><input type="text" name="addto" value=""/></form>';

    window.QUnitListViewMixin = {
        beforeEach: function() {
            var backend = this.backend;
            var createEditActionFormHtml = this.createEditActionFormHtml.bind(this);

            this.setMockBackendGET({
                'mock/entity/edit': function(url, data, options) {
                    return backend.response(200, createEditActionFormHtml({
                        entities: (data.entities ? data.entities.split('.') : [])
                    }));
                },
                'mock/entity/edit/field-a': function(url, data, options) {
                    return backend.response(200, createEditActionFormHtml({
                        field_name: 'mock/entity/edit/field-a',
                        entities: (data.entities ? data.entities.split('.') : [])
                    }));
                },
                'mock/entity/edit/field-b': function(url, data, options) {
                    return backend.response(200, createEditActionFormHtml({
                        field_name: 'mock/entity/edit/field-b',
                        entities: (data.entities ? data.entities.split('.') : [])
                    }));
                },
                'mock/entity/addto': function(url, data, options) {
                    return backend.response(200, MOCK_FORM_ADDTO);
                },
                'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
                'mock/error': backend.response(500, 'HTTP - Error 500')
            });

            function _entity_edit_view(url, data, options) {
                var value = data.field_value[0];

                if (Object.isEmpty(value)) {
                    return backend.response(200, createEditActionFormHtml({
                        field_name: data._bulk_fieldname,
                        entities: (data.entities ? data.entities.split('.') : [])
                    }));
                } else {
                    return backend.response(200, '<div>${count} entitie(s) have been updated !</div>'.template({
                        count: (data.entities || []).length
                    }));
                }
            }

            this.setMockBackendPOST({
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
                'mock/entity/edit': _entity_edit_view,
                'mock/entity/edit/field-a': _entity_edit_view,
                'mock/entity/edit/field-b': _entity_edit_view,
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

            // setup a default reload response for listviews
            this.setListviewReloadResponse(this.createListViewHtml());

            this.listviewActionListeners = {
                start: this.mockListener('action-start'),
                cancel: this.mockListener('action-cancel'),
                fail: this.mockListener('action-fail'),
                done: this.mockListener('action-done')
            };
        },

        afterEach: function(env) {
            $('.ui-dialog-content').dialog('destroy');
            creme.widget.shutdown($('body'));

            if ($('#ui-datepicker-div').length > 0) {
                console.warn('Some jQuery.datepicker dialogs has not been cleaned up !');
                $('#ui-datepicker-div').detach();
            }
        },

        createEditActionFormHtml: function(options) {
            options = $.extend({
                fields: [
                    {value: 'mock/entity/edit/field-a', label: 'Field A'},
                    {value: 'mock/entity/edit/field-b', label: 'Field B'}
                ],
                field_name: 'mock/entity/edit/field-a',
                field_value: '',
                entities: []
            }, options || {});

            return (
                '<div>'
                  + '<div class="help-sign"><p>${help}</p></div>'
                  + '<form>'
                      + '<select name="_bulk_fieldname">${fields}</selected>'
                      + '<input type="text" name="field_value" value="${value}"/>'
                  + '</form>'
              + '</div>'
            ).template({
                fields: (options.fields || []).map(function(field) {
                    return '<option value="${value}" ${selected}>${label}</option>'.template({
                        value: field.value,
                        label: field.label,
                        selected: field.value === options.field_name ? 'selected=""' : ''
                    });
                }).join(''),
                value: options.field_value,
                help: ngettext("%d entity is selected", "%d entities are selected", options.entities.length).format(options.entities.length)
            });
        },

        createActionHtml: function(options) {
            var renderAttr = function(attr) {
                return '${0}="${1}"'.template(attr);
            };

            return (
                '<a href="${url}" data-action="${action}" class="${classes}" ${attrs}>'
                  + '<script type="application/json"><!-- ${data} --></script>'
                  + '${html}'
              + '</a>').template({
                classes: (options.classes || []).join(' '),
                url: options.url || '',
                action: options.action || '',
                attrs: Object.entries(options.attrs || {}).map(renderAttr).join(' '),
                html: options.html || '',
                data: JSON.stringify({
                    data: options.data || {},
                    options: options.options || {}
                })
            });
        },

        createListViewHtml: function(options) {
            var defaultStatus = {
                sort_key: 'regular_field-name',
                sort_order: 'ASC',
                selection: 'multiple',
                selected_rows: '',
                q_filter: '{}',
                ct_id: 67
            };

            options = $.extend({
                mode: 'multiple',
                widgetclasses: [],
                tableclasses: [],
                columns: [],
                rows: [],
                actions: [],
                hatbarcontrols: [],
                hatbarbuttons: [],
                status: {},
                pager: '',
                reloadurl: 'mock/listview/reload'
            }, options || {});

            var isSelectableMode = options.mode !== 'none';

            var renderRow = function(row) {
                if (Object.isString(row)) {
                    return row;
                }

                return '<tr class="lv-row ${selectable}">${cells}</tr>'.template({
                    selectable: isSelectableMode ? 'selectable' : '',
                    cells: row
                });
            };

            var renderColumnTitle = function(column) {
                return Object.isString(column) ? column : column.title;
            };

            var renderColumnSearch = function(column) {
                return Object.isString(column) ? '' : column.search || '<tr></tr>';
            };

            var renderStatus = function(status) {
                return Object.entries(status).map(function(data) {
                    return '<input class="lv-state-field" value="${value}" id="${name}" type="hidden" name="${name}" />'.template({name: data[0], value: data[1]});
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
                            + '<select name="${name}" class="lv-state-field list-${group}-selector">${options}</select>'
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
                '<form class="ui-creme-widget widget-auto ui-creme-listview ${widgetclasses}" widget="ui-creme-listview" selection-mode="${selectionmode}" ${reloadurl}>'
                   + '<div class="list-header-container sticky-container sticky-container-standalone">'
                       + '<div class="list-header sticks-horizontally">'
                           + '<div class="list-title-container">'
                               + '<span class="list-title">'
                                   + '<span class="list-main-title">${title}</span>'
                                   + '<span class="list-sub-title">${subtitle}</span>'
                                   + '<span class="list-title-stats">${titlestats}</span>'
                               + '</span>'
                               + '<div class="list-controls">${hatbarcontrols}</div>'
                           + '</div>'
                           + '<div class="list-header-buttons clearfix">${hatbarbuttons}</div>'
                       + '</div>'
                   + '</div>'
                   + '<table class="listview listview-selection-multiple ${tableclasses}" data-total-count="${rowcount}">'
                       + '<thead>'
                           + '<tr class="lv-state-form">'
                               + '<th>${formdata}</th>'
                           + '</tr>'
                           + '<tr class="lv-columns-header">'
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
                           + '<tr class="lv-search-header">'
                               + '${searches}'
                           + '</tr>'
                       + '</thead>'
                       + '<tbody>${rows}</tbody>'
                       + '<tfoot><tr><td>'
                           + '<div class="list-footer-container sticks-horizontally">'
                               + '<div class="list-footer-stats"></div>'
                               + '<div class="listview-pagination">${pager}</div>'
                               + '<div class="list-footer-page-selector">'
                                   + '<select name="rows" class="lv-state-field list-pagesize-selector">'
                                       + '<option value="10">10</option>'
                                       + '<option value="25">25</option>'
                                   + '</select>'
                               + '</div>'
                           + '</div>'
                       + '</td></tr></tfoot>'
                   + '</table>'
               + '</form>').template({
                   id: options.id,
                   title: options.title || '',
                   subtitle: options.subtitle || '',
                   titlestats: options.titlestats || '',
                   selectionmode: options.mode,
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
                   rowcount: options.rows.length,
                   pager: options.pager || ''
               });
        },

        createListView: function(options) {
            var html = this.createListViewHtml(options);
            var element = $(html).appendTo(this.qunitFixture());
            var widget = creme.widget.create(element);

            return widget;
        },

        createCellHtml: function(name, content, options) {
            options = options || {};
            return '<td class="lv-cell lv-cell-content ${sorted} lv-column" name="${name}">${content}</td>'.template({
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
                '<th data-column-key="${name}" class="lv-column cl_lv ${sortable} ${sorted}">'
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
                '<th class="lv-column hd_cl_lv ${sorted}">'
                    + '<input class="lv-state-field" name="${name}" title="${label}" type="text" value="${search}">'
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
                '<td class="lv-actions actions">'
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
                columns: [this.createCheckAllColumnHtml(), '<th class="sorted lv-column sortable cl_lv">Name</th>'],
                rows: [
                    [this.createCheckCellHtml('1'), this.createIdCellHtml('1'), this.createCellHtml('regular_field-name', 'A', {sorted: true})],
                    [this.createCheckCellHtml('2'), this.createIdCellHtml('2'), this.createCellHtml('regular_field-name', 'B', {sorted: true})],
                    [this.createCheckCellHtml('3'), this.createIdCellHtml('3'), this.createCellHtml('regular_field-name', 'C', {sorted: true})]
                ]
            }, options || {});
        },

        createDefaultListView: function(options) {
            var listOptions = $.extend(this.defaultListViewHtmlOptions(), options || {});
            return this.createListView(listOptions);
        },

        setListviewReloadResponse: function(content, id) {
            var url = id ? 'mock/listview/reload/%s'.format(id) : 'mock/listview/reload';
            var responses = {};

            responses[url] = this.backend.response(200, content);
            this.setMockBackendPOST(responses);
        },

        setListviewSelection: function(list, ids) {
            list.element().find('#selected_rows').val(ids.join(','));
        },

        validateListViewSelectionDialog: function(dialog) {
            dialog = (dialog || $('.ui-dialog')).filter(function() {
                return $(this).find('[widget="ui-creme-listview"]').length > 0;
            });

            var button = this.findDialogButtonsByLabel(gettext("Validate the selection"), dialog);
            this.assert.equal(1, button.length, 'is validation button exists');
            button.trigger('click');
        },

        assertOpenedListViewDialog: function() {
            var dialog = $('.ui-dialog').filter(function() {
                return $(this).find('[widget="ui-creme-listview"]').length > 0;
            });

            this.assert.equal(1, dialog.length, 'is listview dialog opened');
            return dialog;
        }
    };
}(jQuery));
