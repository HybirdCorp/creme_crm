(function($) {
var MOCK_FILTERFORM_DATERANGE = '<ul class="ui-creme-widget widget-auto ui-creme-daterange" widget="ui-creme-daterange">' +
                                    '<li class="daterange-field">' +
                                        '<select name="date_filter_0" data-daterange-type="" id="id_date_filter_0">' +
                                            '<option value="" selected="">Custom</option>' +
                                            '<option value="previous_year">Previous year</option>' +
                                            '<option value="next_year">Next year</option>' +
                                        '</select>' +
                                    '</li>' +
                                    '<li class="daterange-field>' +
                                        '<input type="text" name="date_filter_1" data-daterange-field="start" id="id_date_filter_1" class="ui-creme-input ui-creme-widget widget-auto ui-creme-datepicker" widget="ui-creme-datepicker" format="dd-mm-yy" />' +
                                        '<input type="text" name="date_filter_2" data-daterange-field="end" id="id_date_filter_2" class="ui-creme-input ui-creme-widget widget-auto ui-creme-datepicker" widget="ui-creme-datepicker" format="dd-mm-yy" />' +
                                    '</li>' +
                                '</ul>';

var MOCK_FILTERFORM_CONTENT = '<form class="report-preview-header">' +
                                   '<select name="doc_type" id="id_doc_type">' +
                                       '<option value="csv"></option>' +
                                       '<option value="scsv"></option>' +
                                       '<option value="xls"></option>' +
                                   '</select>' +
                                   '<select name="date_field" id="id_date_field">' +
                                       '<option value="">None</option>' +
                                       '<option value="created">Creation date</option>' +
                                       '<option value="modified">Last change date</option>' +
                                   '</select>' +
                                   '<div class="date-filter">' +
                                       MOCK_FILTERFORM_DATERANGE +
                                   '</div>' +
                                   '<input type="submit" value="Export" class="ui-creme-dialog-action"></input>' +
                              '</form>';

QUnit.module("creme.reports.listview.actions", new QUnitMixin(QUnitEventMixin,
                                                              QUnitAjaxMixin,
                                                              QUnitListViewMixin,
                                                              QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendGET({
            'mock/reports/filterform': backend.response(200, MOCK_FILTERFORM_CONTENT),
            'mock/reports/filterform/fail': backend.response(200, MOCK_FILTERFORM_CONTENT),
            'mock/reports/preview': backend.response(200, '')
        });

        this.setMockBackendPOST({
            'mock/reports/filterform': function(url, data, options) {
                var redirectUrl = 'mock/reports/download?' + _.encodeURLSearch(data);
                return backend.response(200, redirectUrl, {'content-type': 'text/plain'});
            },
            'mock/reports/filterform/invalid': backend.response(200, MOCK_FILTERFORM_CONTENT),
            'mock/reports/filterform/fail': backend.response(400, 'HTTP 400 - Invalid arguments')
        });
    },

    afterEach: function() {
        if ($('#ui-datepicker-div').length > 0) {
            console.warn('Some jQuery.datepicker dialogs has not been cleaned up !');
            $('#ui-datepicker-div').detach();
        }
    }
}));

QUnit.test('creme.reports.ExportReportAction (cancel)', function(assert) {
    var action = new creme.reports.ExportReportAction({
        title: 'Export «Report #1»',
        filterUrl: 'mock/reports/filterform'
    }).on(this.listviewActionListeners);

    action.start();

    assert.deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    var dialog = this.assertOpenedDialog();

    assert.equal(2, dialog.find('.ui-dialog-buttonset button').length);
    assert.equal(1, this.findDialogButtonsByLabel(gettext('Cancel')).length);
    assert.equal(1, this.findDialogButtonsByLabel(gettext('Export')).length);

    dialog.find('[name="doc_type"]').val('csv');
    dialog.find('[name="date_field"]').val('');

    this.closeDialog();

    assert.deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));

    assert.deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    assert.deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.reports.ExportReportAction (csv, none)', function(assert) {
    var action = new creme.reports.ExportReportAction({
        title: 'Export «Report #1»',
        filterUrl: 'mock/reports/filterform'
    }).on(this.listviewActionListeners);

    action.start();

    assert.deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    var dialog = this.assertOpenedDialog();

    assert.equal(2, dialog.find('.ui-dialog-buttonset button').length);
    assert.equal(1, this.findDialogButtonsByLabel(gettext('Cancel')).length);
    assert.equal(1, this.findDialogButtonsByLabel(gettext('Export')).length);

    dialog.find('[name="doc_type"]').val('csv');
    dialog.find('[name="date_field"]').val('');

    this.findDialogButtonsByLabel(gettext('Export')).trigger('click');

    this.assertClosedDialog();

    var download_url = 'mock/reports/download?' + _.encodeURLSearch({doc_type: 'csv', date_field: '', date_filter_0: '', date_filter_2: ''});

    assert.deepEqual([['done', download_url]], this.mockListenerCalls('action-done'));

    assert.deepEqual([
        ['GET', {}],
        ['POST', {doc_type: ['csv'], date_field: [''], date_filter_0: [''], date_filter_2: ['']}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    assert.deepEqual([download_url],
              this.mockRedirectCalls());
});

QUnit.test('creme.reports.ExportReportAction (xls, created, previous_year)', function(assert) {
    var action = new creme.reports.ExportReportAction({
        title: 'Export «Report #1»',
        filterUrl: 'mock/reports/filterform'
    }).on(this.listviewActionListeners);

    action.start();

    assert.deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    var dialog = this.assertOpenedDialog();

    assert.equal(2, dialog.find('.ui-dialog-buttonset button').length);
    assert.equal(1, this.findDialogButtonsByLabel(gettext('Cancel')).length);
    assert.equal(1, this.findDialogButtonsByLabel(gettext('Export')).length);

    dialog.find('[name="doc_type"]').val('xls');
    dialog.find('[name="date_field"]').val('created').trigger('change');
    dialog.find('[name="date_filter_0"]').val('previous_year').trigger('change');

    this.findDialogButtonsByLabel(gettext('Export')).trigger('click');

    this.assertClosedDialog();

    var download_url = 'mock/reports/download?' + _.encodeURLSearch({doc_type: 'xls', date_field: 'created', date_filter_0: 'previous_year', date_filter_2: ''});

    assert.deepEqual([['done', download_url]], this.mockListenerCalls('action-done'));

    assert.deepEqual([
        ['GET', {}],
        ['POST', {doc_type: ['xls'], date_field: ['created'], date_filter_0: ['previous_year'], date_filter_2: ['']}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    assert.deepEqual([download_url],
              this.mockRedirectCalls());
});

QUnit.test('creme.reports.listview.actions (reports-export, ok)', function(assert) {
    var list = this.createDefaultListView().controller();
    var registry = list.actionBuilders();

    var builder = registry.get('reports-export');

    assert.ok(Object.isFunc(builder));
    var action = builder('mock/reports/filterform', {
        title: 'Export «Report #1»'
    });

    action.start();

    assert.deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    var dialog = this.assertOpenedDialog();

    assert.equal(2, dialog.find('.ui-dialog-buttonset button').length);
    assert.equal(1, this.findDialogButtonsByLabel(gettext('Cancel')).length);
    assert.equal(1, this.findDialogButtonsByLabel(gettext('Export')).length);

    dialog.find('[name="doc_type"]').val('csv');
    dialog.find('[name="date_field"]').val('');

    this.findDialogButtonsByLabel(gettext('Export')).trigger('click');

    this.assertClosedDialog();

    var download_url = 'mock/reports/download?' + _.encodeURLSearch({
        doc_type: 'csv', date_field: '', date_filter_0: '', date_filter_2: ''
    });

    assert.deepEqual([
        ['GET', {}],
        ['POST', {doc_type: ['csv'], date_field: [''], date_filter_0: [''], date_filter_2: ['']}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    assert.deepEqual([download_url], this.mockRedirectCalls());
});

}(jQuery));
