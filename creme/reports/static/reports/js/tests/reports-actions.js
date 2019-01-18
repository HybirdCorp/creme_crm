/* globals QUnitDetailViewMixin */

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

QUnit.module("creme.reports.actions", new QUnitMixin(QUnitEventMixin,
                                                     QUnitAjaxMixin,
                                                     QUnitBrickMixin,
                                                     QUnitDialogMixin,
                                                     QUnitDetailViewMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendGET({
            'mock/reports/filterform': backend.response(200, MOCK_FILTERFORM_CONTENT),
            'mock/reports/preview': backend.response(200, '')
        });

        this.setMockBackendPOST({
            'mock/reports/filterform': function(url, data, options) {
                var redirectUrl = 'mock/reports/download?' + $.param(data);
                return backend.response(200, redirectUrl, {'content-type': 'text/plain'});
            },
            'mock/reports/filterform/invalid': backend.response(200, MOCK_FILTERFORM_CONTENT),
            'mock/reports/filterform/fail': backend.response(400, 'HTTP 400 - Invalid arguments')
        });

        this.brickActionListeners = {
            start: this.mockListener('action-start'),
            cancel: this.mockListener('action-cancel'),
            fail: this.mockListener('action-fail'),
            done: this.mockListener('action-done')
        };
    }
}));

QUnit.test('creme.reports.hatbar.actions (reports-export, ok)', function(assert) {
    var brick = this.createBrickWidget({
        classes: ['brick-hat-bar']
    }).brick();

    brick.action('reports-export', 'mock/reports/filterform').start();

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    var dialog = this.assertOpenedDialog();

    equal(2, dialog.find('.ui-dialog-buttonset button').length);
    equal(1, this.findDialogButtonsByLabel(gettext('Cancel')).length);
    equal(1, this.findDialogButtonsByLabel(gettext('Export')).length);

    dialog.find('[name="doc_type"]').val('csv');
    dialog.find('[name="date_field"]').val('');

    this.findDialogButtonsByLabel(gettext('Export')).click();

    this.assertClosedDialog();

    var download_url = 'mock/reports/download?' + $.param({doc_type: 'csv', date_field: '', date_filter_0: '', date_filter_2: ''});

    deepEqual([
        ['GET', {}],
        ['POST', {doc_type: ['csv'], date_field: [''], date_filter_0: [''], date_filter_2: ['']}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    deepEqual([download_url], this.mockRedirectCalls());
});

QUnit.test('creme.reports.exportReport (deprecated)', function(assert) {
    creme.reports.exportReport('mock/reports/filterform');

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    var dialog = this.assertOpenedDialog();

    equal(2, dialog.find('.ui-dialog-buttonset button').length);
    equal(1, this.findDialogButtonsByLabel(gettext('Cancel')).length);
    equal(1, this.findDialogButtonsByLabel(gettext('Export')).length);

    dialog.find('[name="doc_type"]').val('csv');
    dialog.find('[name="date_field"]').val('');

    this.findDialogButtonsByLabel(gettext('Export')).click();

    this.assertClosedDialog();

    var download_url = 'mock/reports/download?' + $.param({doc_type: 'csv', date_field: '', date_filter_0: '', date_filter_2: ''});

    deepEqual([
        ['GET', {}],
        ['POST', {doc_type: ['csv'], date_field: [''], date_filter_0: [''], date_filter_2: ['']}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    deepEqual([download_url], this.mockRedirectCalls());
});

}(jQuery));
