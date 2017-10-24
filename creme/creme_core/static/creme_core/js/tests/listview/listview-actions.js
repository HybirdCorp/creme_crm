QUnit.module("creme.listview.actions", {
    setup: function() {
        this.resetMockCalls();
        this.resetMockRedirectCalls();
        this.resetMockBackendCalls();
        this.resetListviewReloadContent();

        var self = this;

        this.anchor = $('<div></div>').appendTo($('body'));

        this.__goTo = creme.utils.goTo;
        creme.utils.goTo = function(url) {
            self._redirectCalls.push(url);
        };

        var backend = this.backend = new creme.ajax.MockAjaxBackend({delay: 0, sync: true});

        var __mockBackendCall = function(aux) {
            return function(url, data, options) {
                self._backendCalls.push([url, data, options]);
                return aux(url, data, options);
            };
        };

        var MOCK_FORM_EDIT = '<form><input type="text" name="edit" value=""/></form>';
        var MOCK_FORM_ADDTO = '<form><input type="text" name="addto" value=""/></form>';
        var MOCK_EDIT_SUMMARY = '<div><span class="bulk-selection-summary"></span></div>';

        $.extend(this.backend.GET, {
            'mock/entity/edit': __mockBackendCall(function(url, data, options) {
                return backend.response(200, MOCK_FORM_EDIT);
            }),
            'mock/entity/addto': __mockBackendCall(function(url, data, options) {
                return backend.response(200, MOCK_FORM_ADDTO);
            }),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500'),
        });

        $.extend(this.backend.POST, {
            'mock/listview/reload': __mockBackendCall(function(url, data, options) {
                var content = self._listviewReloadContent[id] || '';
                return backend.response(Object.isEmpty(content) ? 200 : 404, content);
            }),
            'mock/entity/delete':  __mockBackendCall(function(url, data, options) {
                return backend.response(200, '');
            }),
            'mock/entity/delete/fail':  __mockBackendCall(function(url, data, options) {
                return backend.response(400, 'invalid response !');
            }),
            'mock/entity/delete/nothing': __mockBackendCall(function(url, data, options) {
                var ids = (data.ids || '').split(',');

                return backend.response(400, $.toJSON({
                    count: ids.length,
                    errors: ids.map(function(id) {return id + ' cannot be deleted';})
                }));
            }),
            'mock/entity/delete/firstonly': __mockBackendCall(function(url, data, options) {
                var ids = (data.ids || '').split(',');

                return backend.response(400, $.toJSON({
                    count: ids.length,
                    errors: ids.slice(1).map(function(id) {return id + ' cannot be deleted';})
                }));
            }),
            'mock/entity/edit': __mockBackendCall(function(url, data, options) {
                var value = $('input[name="edit"]', data).val();
                if (Object.isEmpty(value)) {
                    return backend.response(200, MOCK_FORM_EDIT);
                } else if (value === 'summary') {
                    return backend.response(200, MOCK_EDIT_SUMMARY);
                } else {
                    return backend.response(200, '');
                }
            }),
            'mock/entity/addto': __mockBackendCall(function(url, data, options) {
                if (Object.isEmpty($('input[name="addto"]', data).val())) {
                    return backend.response(200, MOCK_FORM_ADDTO);
                } else {
                    return backend.response(200, '');
                }
            }),
        });

        creme.ajax.defaultBackend(backend);

        this.listviewActionListeners = {
            start: this.mockListener('action-start'),
            cancel: this.mockListener('action-cancel'),
            fail: this.mockListener('action-fail'),
            done: this.mockListener('action-done')
        };
    },

    teardown: function() {
        $('.ui-dialog-content').dialog('destroy');

        creme.widget.shutdown(this.anchor);
        this.anchor.detach();

        creme.utils.goTo = this.__goTo;
        creme.ajax.defaultBackend(new creme.ajax.Backend());
    },

    createListViewHtml: function(options) {
        var defaultStatus = {
            sort_field: 'regular_field-name',
            sort_order: '',
            selected_rows: '',
            q_filter: '{}',
            ct_id: 67
        };

        options = $.extend({
            id: 'list',
            columns: [],
            rows: [],
            actions: [],
            status: {}
        }, options || {});

        var renderRow = function(row) {
            return Array.isArray(row) ? '<tr class="selectable">' + row.join('') + '</tr>' : row;
        };

        var renderStatus = function(status) {
            return Object.entries(status).map(function(data) {
                return '<input value="${value}" id="${name}" type="hidden" name="${name}" />'.template({name: data[0], value: data[1]});
            }).join('');
        };

        return (
            '<form class="ui-creme-widget widget-auto ui-creme-listview" widget="ui-creme-listview" multiple>'
          + '<div class="list-header-container sticky-container sticky-container-standalone"></div>'
               + '<table id="${id}" class="list_view listview listview-standalone listview-selection-multiple" data-total-count="${rowcount}">'
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
                   + '</thead>'
               + '<tbody>${rows}</tbody>'
           + '</table>'
           + '</form>').template({
               id: options.id,
               formdata: renderStatus($.extend({}, defaultStatus, options.status)),
               headeractions: options.actions.join(''),
               columns: options.columns.join(''),
               rows: options.rows.map(renderRow).join(''),
               rowcount: options.rows.length
           });

    },

    createListView: function(options) {
        var html = this.createListViewHtml(options);
        var element = $(html).appendTo(this.anchor);

        creme.widget.create(element);

        var listview = element.data('list_view');
        listview.setReloadUrl('mock/listview/reload');
        return listview;
    },

    setUpDefaultListView: function(options) {
        var list_options = $.extend({
            columns: ['<th class="sorted column sortable cl_lv">Name</th>'],
            rows: [
                ['<td class="lv-cell lv-cell-content sorted column" name="regular_field-name">A</td>'],
                ['<td class="lv-cell lv-cell-content sorted column" name="regular_field-name">B</td>'],
                ['<td class="lv-cell lv-cell-content sorted column" name="regular_field-name">C</td>']
            ]
        }, options || {});

        var html = this.createListViewHtml(list_options);
        var list = this.createListView(list_options);

        this.setListviewReloadContent(html);
        return list;
    },

    assertClosedDialog: function() {
        equal(0, $('.ui-dialog').length, 'is dialog not opened');
    },

    assertOpenedDialog: function() {
        equal(1, $('.ui-dialog').length, 'is dialog opened');
    },

    assertOpenedAlertDialog: function(message, header) {
        equal(1, $('.ui-dialog .ui-creme-dialog-warn').length, 'is alert dialog opened');

        if (message !== undefined) {
            equal(message, $('.ui-dialog .ui-creme-dialog-warn .message').text());
        }

        if (header !== undefined) {
            equal(header,  $('.ui-dialog .ui-creme-dialog-warn .header').text());
        }
    },

    closeDialog: function() {
        equal(1, $('.ui-dialog').length, 'single form dialog allowed');
        $('.ui-dialog-content').dialog('close');
    },

    submitFormDialog: function(data) {
        equal(1, $('.ui-dialog').length, 'single form dialog allowed');
        equal(1, $('.ui-dialog button[name="send"]').length, 'single form submit button allowed');

        for (var key in data) {
            $('.ui-dialog form [name="' + key + '"]').val(data[key]);
        }

        var formHtml = $('.ui-dialog form').html();
        $('.ui-dialog button[name="send"]').click();

        return formHtml;
    },

    acceptConfirmDialog: function() {
        equal(1, $('.ui-dialog').length, 'single confirm dialog allowed');
        equal(1, $('.ui-dialog button[name="ok"]').length, 'single confirm ok button allowed');

        $('.ui-dialog button[name="ok"]').click();
    },

    resetListviewReloadContent: function() {
        this._listviewReloadContent = {};
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

    setListviewReloadContent: function(id, content) {
        this._listviewReloadContent[id] = content;
    },

    mockBackendCalls: function() {
        return this._backendCalls;
    },

    mockBackendUrlCalls: function(url) {
        return this._backendCalls.filter(function(e) {
            return e[0] === url;
        }).map(function(e) {
            var data = e[1];
            return (data instanceof jQuery) ? data.html() : data;
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
});

QUnit.test('creme.listview.DeleteSelectedAction (no selection)', function(assert) {
    var list = this.createListView();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete'
    }).on(this.listviewActionListeners);

    equal(0, list.countEntities());
    deepEqual([], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (not confirmed)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (error)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete/fail'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('1,2');

    equal(2, list.countEntities());
    deepEqual(['1', '2'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.acceptConfirmDialog();

    this.assertOpenedAlertDialog(undefined, gettext('Bad Request'));

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([{ids: '1,2'}], this.mockBackendUrlCalls('mock/entity/delete/fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    deepEqual([{ids: '1,2'}], this.mockBackendUrlCalls('mock/entity/delete/fail'));
    deepEqual([{
        sort_field: ['regular_field-name'],
        sort_order: [''],
        selected_rows: ['1,2'],
        q_filter: ['{}'],
        ct_id: ['67'],
        selection: 'multiple'
    }], this.mockBackendUrlCalls('mock/listview/reload'));
});


QUnit.test('creme.listview.DeleteSelectedAction (not allowed)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete/nothing'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('1,2');

    equal(2, list.countEntities());
    deepEqual(['1', '2'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete/nothing'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.acceptConfirmDialog();

    var header = ngettext(' %d entity cannot be deleted.', ' %d entities cannot be deleted.', 2).format(2);
    this.assertOpenedAlertDialog(undefined, header);

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([{ids: '1,2'}], this.mockBackendUrlCalls('mock/entity/delete/nothing'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    deepEqual([{ids: '1,2'}], this.mockBackendUrlCalls('mock/entity/delete/nothing'));
    deepEqual([{
        sort_field: ['regular_field-name'],
        sort_order: [''],
        selected_rows: ['1,2'],
        q_filter: ['{}'],
        ct_id: ['67'],
        selection: 'multiple'
    }], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (partially allowed)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete/firstonly'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('1,2,3');

    equal(3, list.countEntities());
    deepEqual(['1', '2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    this.acceptConfirmDialog();

    var header = ngettext('%d entity have been deleted.', '%d entities have been deleted.', 1).format(1) +
                 ngettext(' %d entity cannot be deleted.', ' %d entities cannot be deleted.', 2).format(2);

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([{ids: '1,2,3'}], this.mockBackendUrlCalls('mock/entity/delete/firstonly'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.assertOpenedAlertDialog(undefined, header);
    this.closeDialog();

    deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    deepEqual([{ids: '1,2,3'}], this.mockBackendUrlCalls('mock/entity/delete/firstonly'));
    deepEqual([{
        sort_field: ['regular_field-name'],
        sort_order: [''],
        selected_rows: ['1,2,3'],
        q_filter: ['{}'],
        ct_id: ['67'],
        selection: 'multiple'
    }], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.DeleteSelectedAction (ok)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.DeleteSelectedAction(list, {
        url: 'mock/entity/delete'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('1,2,3');

    equal(3, list.countEntities());
    deepEqual(['1', '2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    this.acceptConfirmDialog();

    deepEqual([{ids: '1,2,3'}], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([{
        sort_field: ['regular_field-name'],
        sort_order: [''],
        selected_rows: ['1,2,3'],
        q_filter: ['{}'],
        ct_id: ['67'],
        selection: 'multiple'
    }], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (no selection)', function(assert) {
    var list = this.createListView();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    equal(0, list.countEntities());
    deepEqual([], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (cancel)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([{ids: ['2', '3'], persist: 'ids'}], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([{ids: ['2', '3'], persist: 'ids'}], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (submit fail + cancel)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    deepEqual([{ids: ['2', '3'], persist: 'ids'}], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    var formHtml = this.submitFormDialog();

    this.assertOpenedDialog();
    deepEqual([{ids: ['2', '3'], persist: 'ids'}, formHtml], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (ok)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.AddToSelectedAction(list, {
        url: 'mock/entity/addto'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([{ids: ['2', '3'], persist: 'ids'}], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    var formHtml = this.submitFormDialog({
        addto: 'ok'
    });

    this.assertClosedDialog();

    deepEqual([{ids: ['2', '3'], persist: 'ids'}, formHtml], this.mockBackendUrlCalls('mock/entity/addto'));
    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([{
        sort_field: ['regular_field-name'],
        sort_order: [''],
        selected_rows: ['2,3'],
        q_filter: ['{}'],
        ct_id: ['67'],
        selection: 'multiple'
    }], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (no selection)', function(assert) {
    var list = this.createListView();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    equal(0, list.countEntities());
    deepEqual([], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one entity."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (cancel)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([{}], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([{}], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (submit => form error => close)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    deepEqual([{}], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    var formHtml = this.submitFormDialog();

    this.assertOpenedDialog();

    equal(0, $('.ui-dialog .bulk-selection-summary').length);
    deepEqual([{}, formHtml], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.AddToSelectedAction (submit => partially fail => close)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([{}], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    var formHtml = this.submitFormDialog({
        edit: 'summary'
    });

    this.assertOpenedDialog();

    equal(1, $('.ui-dialog .bulk-selection-summary').length);
    deepEqual([{}, formHtml], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([{
        sort_field: ['regular_field-name'],
        sort_order: [''],
        selected_rows: ['2,3'],
        q_filter: ['{}'],
        ct_id: ['67'],
        selection: 'multiple'
    }], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.EditSelectedAction (ok)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.EditSelectedAction(list, {
        url: 'mock/entity/edit'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([{}], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    var formHtml = this.submitFormDialog({
        edit: 'ok'
    });

    this.assertClosedDialog();

    deepEqual([{}, formHtml], this.mockBackendUrlCalls('mock/entity/edit'));
    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([{
        sort_field: ['regular_field-name'],
        sort_order: [''],
        selected_rows: ['2,3'],
        q_filter: ['{}'],
        ct_id: ['67'],
        selection: 'multiple'
    }], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.listview.MergeSelectedAction (no selection)', function(assert) {
    var list = this.createListView();
    var action = new creme.lv_widget.MergeSelectedAction(list, {
        url: 'mock/entity/merge'
    }).on(this.listviewActionListeners);

    equal(0, list.countEntities());
    deepEqual([], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select 2 entities."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.listview.MergeSelectedAction (invalid selection)', function(assert) {
    var list = this.createListView();
    var action = new creme.lv_widget.MergeSelectedAction(list, {
        url: 'mock/entity/merge'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2');

    equal(1, list.countEntities());
    deepEqual(['2'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    // try with one selection
    action.start();

    this.assertOpenedAlertDialog(gettext("Please select 2 entities."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockRedirectCalls());

    this.resetMockCalls();

    $(list).find('#selected_rows').val('1,2,3');

    equal(3, list.countEntities());
    deepEqual(['1', '2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    // retry with 3 selections
    action.start();

    this.assertOpenedAlertDialog(gettext("Please select 2 entities."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.listview.MergeSelectedAction (ok)', function(assert) {
    var list = this.setUpDefaultListView();
    var action = new creme.lv_widget.MergeSelectedAction(list, {
        url: 'mock/entity/merge'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertClosedDialog();

    deepEqual(['mock/entity/merge?id1=2&id2=3'], this.mockRedirectCalls());
});
