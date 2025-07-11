(function($) {

QUnit.module("creme.reports.actions", new QUnitMixin(QUnitEventMixin,
                                                     QUnitAjaxMixin,
                                                     QUnitBrickMixin,
                                                     QUnitDialogMixin, {
    createPreviewFilterFieldsHtml: function() {
        return (
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
                '<ul class="ui-creme-widget widget-auto ui-creme-daterange" widget="ui-creme-daterange">' +
                    '<li class="daterange-field">' +
                        '<select name="date_filter_0" data-daterange-type id="id_date_filter_0">' +
                            '<option value="" selected="">Custom</option>' +
                            '<option value="previous_year">Previous year</option>' +
                            '<option value="next_year">Next year</option>' +
                        '</select>' +
                    '</li>' +
                    '<li class="daterange-field">' +
                        '<input type="text" name="date_filter_1" data-daterange-field="start" id="id_date_filter_1" ' +
                                'class="ui-creme-input ui-creme-widget widget-auto ui-creme-datepicker" widget="ui-creme-datepicker" format="dd-mm-yy" />' +
                        '<input type="text" name="date_filter_2" data-daterange-field="end" id="id_date_filter_2" ' +
                                'class="ui-creme-input ui-creme-widget widget-auto ui-creme-datepicker" widget="ui-creme-datepicker" format="dd-mm-yy" />' +
                    '</li>' +
                '</ul>' +
            '</div>'
        );
    },

    createExportDialogHtml: function() {
        return (
            '<form class="report-preview-header">' +
                '${fields}' +
                '<input type="submit" value="Export" class="ui-creme-dialog-action"></input>' +
            '</form>'
        ).template({
            fields: this.createPreviewFilterFieldsHtml()
        });
    },

    createPreviewPageHtml: function() {
        return (
            '<div class="report-preview">' +
                '<div class="scrollable-block-container report-preview-header">' +
                    '<form>${fields}</form>' +
                    '<button type="button" name="generate">Preview</button>' +
                    '<button type="button" name="download">Download</button>' +
                '</div>' +
            '</div>'
        ).template({
            fields: this.createPreviewFilterFieldsHtml()
        });
    },

    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendGET({
            'mock/reports/filterform': backend.response(200, this.createExportDialogHtml()),
            'mock/reports/preview': backend.response(200, '')
        });

        this.setMockBackendPOST({
            'mock/reports/filterform': function(url, data, options) {
                var redirectUrl = 'mock/reports/download?' + _.encodeURLSearch(data);
                return backend.response(200, redirectUrl, {'content-type': 'text/plain'});
            },
            'mock/reports/filterform/invalid': backend.response(200, this.createExportDialogHtml()),
            'mock/reports/filterform/fail': backend.response(400, 'HTTP 400 - Invalid arguments')
        });

        this.brickActionListeners = {
            start: this.mockListener('action-start'),
            cancel: this.mockListener('action-cancel'),
            fail: this.mockListener('action-fail'),
            done: this.mockListener('action-done')
        };
    },

    afterEach: function() {
        if ($('#ui-datepicker-div').length > 0) {
            console.warn('Some jQuery.datepicker dialogs has not been cleaned up !');
            $('#ui-datepicker-div').detach();
        }
    }
}));

QUnit.test('creme.reports.hatbar.actions (reports-export, ok)', function(assert) {
    var brick = this.createBrickWidget({
        classes: ['brick-hat-bar']
    }).brick();

    assert.equal(0, $('#ui-datepicker-div').length);

    brick.action('reports-export', 'mock/reports/filterform').start();

    assert.deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    var dialog = this.assertOpenedDialog();
    assert.equal(1, $('#ui-datepicker-div').length);

    assert.equal(2, dialog.find('.ui-dialog-buttonset button').length);
    assert.equal(1, this.findDialogButtonsByLabel(gettext('Cancel')).length);
    assert.equal(1, this.findDialogButtonsByLabel(gettext('Export')).length);

    dialog.find('[name="doc_type"]').val('csv');
    dialog.find('[name="date_field"]').val('');

    this.findDialogButtonsByLabel(gettext('Export')).trigger('click');

    this.assertClosedDialog();

    var downloadUrl = 'mock/reports/download?' + _.encodeURLSearch({
        doc_type: 'csv',
        date_field: '',
        date_filter_0: '',
        date_filter_1: '',
        date_filter_2: ''
    });

    assert.deepEqual([
        ['GET', {}],
        ['POST', {
            doc_type: ['csv'],
            date_field: [''],
            date_filter_0: [''],
            date_filter_1: [''],
            date_filter_2: ['']
        }]
    ], this.mockBackendUrlCalls('mock/reports/filterform'));

    assert.deepEqual([downloadUrl], this.mockRedirectCalls());
});


QUnit.test('creme.reports.PreviewController (create)', function(assert) {
    var controller = new creme.reports.PreviewController();

    assert.equal(controller._downloadUrl, '');
    assert.equal(controller._redirectUrl, '');

    controller = new creme.reports.PreviewController({
        downloadUrl: 'mock/reports/download',
        previewUrl: 'mock/reports/preview'
    });

    assert.equal(controller._downloadUrl, 'mock/reports/download');
    assert.equal(controller._redirectUrl, 'mock/reports/preview');
});

QUnit.test('creme.reports.PreviewController (bind)', function(assert) {
    var element = $(this.createPreviewPageHtml());
    var controller = new creme.reports.PreviewController();

    creme.widget.ready(element);

    assert.equal(controller.isBound(), false);

    controller.bind(element);
    assert.equal(controller.isBound(), true);

    this.assertRaises(function() {
        controller.bind(element);
    }, Error, 'Error: creme.reports.PreviewController is already bound.');
});

QUnit.test('creme.reports.PreviewController (unbind)', function(assert) {
    var element = $(this.createPreviewPageHtml());
    var controller = new creme.reports.PreviewController();

    creme.widget.ready(element);

    this.assertRaises(function() {
        controller.unbind();
    }, Error, 'Error: creme.reports.PreviewController is not bound.');

    controller.bind(element);
    assert.equal(controller.isBound(), true);

    controller.unbind();
    assert.equal(controller.isBound(), false);
});

QUnit.test('creme.reports.PreviewController (preview or download)', function(assert) {
    var element = $(this.createPreviewPageHtml());
    var controller = new creme.reports.PreviewController({
        downloadUrl: 'mock/reports/download',
        previewUrl: 'mock/reports/preview'
    });

    creme.widget.ready(element);
    controller.bind(element);

    element.find('[name="doc_type"]').val('csv');
    element.find('[data-daterange-type]').val('previous_year').trigger('change');

    var downloadUrl = '/mock/reports/download?' + _.encodeURLSearch({
        doc_type: 'csv',
        date_field: '',
        date_filter_0: 'previous_year',
        date_filter_1: '',
        date_filter_2: ''
    });

    var previewUrl = '/mock/reports/preview?' + _.encodeURLSearch({
        doc_type: 'csv',
        date_field: '',
        date_filter_0: 'previous_year',
        date_filter_1: '',
        date_filter_2: ''
    });

    element.find('button[name="download"]').trigger('click');

    assert.deepEqual([downloadUrl], this.mockRedirectCalls());

    element.find('button[name="generate"]').trigger('click');

    assert.deepEqual([
        downloadUrl,
        previewUrl
    ], this.mockRedirectCalls());
});


}(jQuery));
