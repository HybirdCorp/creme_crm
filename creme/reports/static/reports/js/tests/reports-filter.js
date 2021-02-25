// (function($) {

// var MOCK_HFILTER_CONTENT = {
//    '127': [["hfilter-1", "Header Filter #1"], ["hfilter-2", "Header Filter #2"]],
//    '74': [["hfilter-3", "Header Filter #3"]],
//    '1': []
// };
//
// var MOCK_EFILTER_CONTENT = {
//    '127': [["efilter-1", "Entity Filter #1"], ["efilter-2", "Entity Filter #2"]],
//    '74': [["efilter-3", "Entity Filter #3"], ["efilter-4", "Entity Filter #4"]],
//    '1': []
// };

// QUnit.module("creme.reports.filter", new QUnitMixin(QUnitEventMixin,
//                                                   QUnitAjaxMixin,
//                                                   QUnitDialogMixin, {
//    beforeEach: function() {
//        var backend = this.backend;
//        backend.options.enableUriSearch = true;
//
//        var __filterResponse = function(filters, ctypeId) {
//            var ctypeFilters = filters[ctypeId];
//
//            if (Object.isNone(ctypeFilters)) {
//                return backend.response(400, 'unknown ctype ${}'.format(ctypeId), {'content-type': 'text/json'});
//            } else {
//                return backend.response(200, JSON.stringify(ctypeFilters), {'content-type': 'text/json'});
//            }
//        };
//
//        this.setMockBackendGET({
//            'mock/reports/hfilter': function(url, data, options) {
//                return __filterResponse(MOCK_HFILTER_CONTENT, data['ct_id']);
//            },
//            'mock/reports/efilter': function(url, data, options) {
//                return __filterResponse(MOCK_EFILTER_CONTENT, data['ct_id']);
//            }
//        });
//    },
//
//    createReportFilterHtml: function(options) {
//        options = $.extend({
//            ctypes: []
//        }, options || {});
//
//        return (
//            '<form>' +
//                '<select name="ct">${ctypes}</select>' +
//                '<select name="hf"></select>' +
//                '<select name="filter"></select>' +
//            '</form>').template({
//                ctypes: options.ctypes.map(function(e) {
//                    return '<option value="${value}">${label}</option>'.template(e);
//                })
//            });
//    }
// }));

// QUnit.test('creme.reports.ReportFormController (url)', function(assert) {
//    this.assertRaises(function() {
//        return new creme.reports.ReportFormController();
//    }, Error, 'Error: Unable to create filter model without fetch url');
//
//    this.assertRaises(function() {
//        return new creme.reports.ReportFormController({
//            hfilterUrl: 'mock/reports/hfilter'
//        });
//    }, Error, 'Error: Unable to create filter model without fetch url');
//
//    this.assertRaises(function() {
//        return new creme.reports.ReportFormController({
//            efilterUrl: 'mock/reports/efilter'
//        });
//    }, Error, 'Error: Unable to create filter model without fetch url');
//
//    // ok both urls aren't empty
//    var report = new creme.reports.ReportFormController({
//        hfilterUrl: 'mock/reports/hfilter',
//        efilterUrl: 'mock/reports/efilter'
//    });
//
//    equal(false, report.isBound());
// });

// QUnit.test('creme.reports.ReportFormController (bind)', function(assert) {
//    var form = $(this.createReportFilterHtml());
//
//    var report = new creme.reports.ReportFormController({
//        hfilterUrl: 'mock/reports/hfilter',
//        efilterUrl: 'mock/reports/efilter'
//    });
//
//    equal(false, report.isBound());
//
//    report.bind(form);
//
//    equal(true, report.isBound());
//
//    this.assertRaises(function() {
//        report.bind(form);
//    }, Error, 'Error: ReportFilterController is already bound');
// });

// QUnit.test('creme.reports.ReportFormController (initial)', function(assert) {
//    var form = $(this.createReportFilterHtml());
//
//    var report = new creme.reports.ReportFormController({
//        hfilterUrl: 'mock/reports/hfilter',
//        efilterUrl: 'mock/reports/efilter',
//        backend: this.backend
//    });
//
//    equal(false, report.isBound());
//    deepEqual([], this.mockBackendUrlCalls('mock/reports/hfilter'));
//    deepEqual([], this.mockBackendUrlCalls('mock/reports/efilter'));
//
//    report.bind(form);
//
//    equal(true, report.isBound());
//
//    equal(null, form.find('select[name="ct"]').val());
//    deepEqual([], this.mockBackendUrlCalls('mock/reports/hfilter'));
//    deepEqual([], this.mockBackendUrlCalls('mock/reports/efilter'));
//
//    this.equalOuterHtml('<select name="hf">' +
//                            '<option value="">' + gettext('None available') + '</option>' +
//                        '</select>',
//                        form.find('select[name="hf"]'));
//
//    this.equalOuterHtml('<select name="filter">' +
//                            '<option value="">' + gettext('All') + '</option>' +
//                        '</select>',
//                        form.find('select[name="filter"]'));
// });

// QUnit.test('creme.reports.ReportFormController (invalid ctype)', function(assert) {
//    var form = $(this.createReportFilterHtml({
//        ctypes: [
//            {value: 'invalid', label: 'CType Unknown'}
//        ]
//    }));
//
//    var report = new creme.reports.ReportFormController({
//        hfilterUrl: 'mock/reports/hfilter',
//        efilterUrl: 'mock/reports/efilter',
//        backend: this.backend
//    });
//
//    equal(false, report.isBound());
//
//    report.bind(form);
//
//    equal(true, report.isBound());
//    deepEqual([['GET', {ct_id: 'invalid'}]], this.mockBackendUrlCalls('mock/reports/hfilter'));
//    deepEqual([['GET', {ct_id: 'invalid'}]], this.mockBackendUrlCalls('mock/reports/efilter'));
//
//    this.equalOuterHtml('<select name="hf">' +
//                            '<option value="">' + gettext('None available') + '</option>' +
//                        '</select>',
//                        form.find('select[name="hf"]'));
//
//    this.equalOuterHtml('<select name="filter">' +
//                            '<option value="">' + gettext('All') + '</option>' +
//                        '</select>',
//                        form.find('select[name="filter"]'));
// });

// QUnit.test('creme.reports.ReportFormController (empty)', function(assert) {
//    var form = $(this.createReportFilterHtml({
//        ctypes: [
//            {value: '1', label: 'CType #1'}
//        ]
//    }));
//
//    var report = new creme.reports.ReportFormController({
//        hfilterUrl: 'mock/reports/hfilter',
//        efilterUrl: 'mock/reports/efilter',
//        backend: this.backend
//    });
//
//    equal(false, report.isBound());
//
//    report.bind(form);
//
//    equal(true, report.isBound());
//    deepEqual([['GET', {ct_id: '1'}]], this.mockBackendUrlCalls('mock/reports/hfilter'));
//    deepEqual([['GET', {ct_id: '1'}]], this.mockBackendUrlCalls('mock/reports/efilter'));
//
//    this.equalOuterHtml('<select name="hf">' +
//                            '<option value="">' + gettext('None available') + '</option>' +
//                        '</select>',
//                        form.find('select[name="hf"]'));
//
//    this.equalOuterHtml('<select name="filter">' +
//                            '<option value="">' + gettext('All') + '</option>' +
//                        '</select>',
//                        form.find('select[name="filter"]'));
// });

// QUnit.test('creme.reports.ReportFormController (update)', function(assert) {
//    var form = $(this.createReportFilterHtml({
//        ctypes: [
//            {value: '127', label: 'CType #127'},
//            {value: '74', label: 'CType #74'},
//            {value: '1', label: 'CType #1'}
//        ]
//    }));
//
//    var report = new creme.reports.ReportFormController({
//        hfilterUrl: 'mock/reports/hfilter',
//        efilterUrl: 'mock/reports/efilter',
//        backend: this.backend
//    });
//
//    equal(false, report.isBound());
//
//    report.bind(form);
//
//    equal(true, report.isBound());
//
//    equal('127', form.find('select[name="ct"]').val());
//
//    deepEqual([['GET', {ct_id: '127'}]], this.mockBackendUrlCalls('mock/reports/hfilter'));
//    deepEqual([['GET', {ct_id: '127'}]], this.mockBackendUrlCalls('mock/reports/efilter'));
//
//    this.equalOuterHtml('<select name="hf">' +
//                            '<option value="">' + gettext("No selected view") + '</option>' +
//                            '<option value="hfilter-1">Header Filter #1</option>' +
//                            '<option value="hfilter-2">Header Filter #2</option>' +
//                        '</select>',
//                        form.find('select[name="hf"]'));
//
//    this.equalOuterHtml('<select name="filter">' +
//                            '<option value="">' + gettext("All") + '</option>' +
//                            '<option value="efilter-1">Entity Filter #1</option>' +
//                            '<option value="efilter-2">Entity Filter #2</option>' +
//                        '</select>',
//                        form.find('select[name="filter"]'));
//
//    form.find('select[name="ct"]').val('74').change();
//
//    deepEqual([
//        ['GET', {ct_id: '127'}], ['GET', {ct_id: '74'}]
//    ], this.mockBackendUrlCalls('mock/reports/hfilter'));
//    deepEqual([
//        ['GET', {ct_id: '127'}], ['GET', {ct_id: '74'}]
//    ], this.mockBackendUrlCalls('mock/reports/efilter'));
//
//    this.equalOuterHtml('<select name="hf">' +
//                            '<option value="">' + gettext("No selected view") + '</option>' +
//                            '<option value="hfilter-3">Header Filter #3</option>' +
//                        '</select>',
//                        form.find('select[name="hf"]'));
//
//    this.equalOuterHtml('<select name="filter">' +
//                            '<option value="">' + gettext("All") + '</option>' +
//                            '<option value="efilter-3">Entity Filter #3</option>' +
//                            '<option value="efilter-4">Entity Filter #4</option>' +
//                        '</select>',
//                        form.find('select[name="filter"]'));
// });

// QUnit.test('creme.reports.ReportFormController (update, invalid)', function(assert) {
//    var form = $(this.createReportFilterHtml({
//        ctypes: [
//            {value: '127', label: 'CType #127'},
//            {value: 'invalid'}
//        ]
//    }));
//
//    var report = new creme.reports.ReportFormController({
//        hfilterUrl: 'mock/reports/hfilter',
//        efilterUrl: 'mock/reports/efilter',
//        backend: this.backend
//    });
//
//    equal(false, report.isBound());
//
//    report.bind(form);
//
//    equal(true, report.isBound());
//
//    equal('127', form.find('select[name="ct"]').val());
//
//    deepEqual([['GET', {ct_id: '127'}]], this.mockBackendUrlCalls('mock/reports/hfilter'));
//    deepEqual([['GET', {ct_id: '127'}]], this.mockBackendUrlCalls('mock/reports/efilter'));
//
//    this.equalOuterHtml('<select name="hf">' +
//                            '<option value="">' + gettext("No selected view") + '</option>' +
//                            '<option value="hfilter-1">Header Filter #1</option>' +
//                            '<option value="hfilter-2">Header Filter #2</option>' +
//                        '</select>',
//                        form.find('select[name="hf"]'));
//
//    this.equalOuterHtml('<select name="filter">' +
//                            '<option value="">' + gettext("All") + '</option>' +
//                            '<option value="efilter-1">Entity Filter #1</option>' +
//                            '<option value="efilter-2">Entity Filter #2</option>' +
//                        '</select>',
//                        form.find('select[name="filter"]'));
//
//    form.find('select[name="ct"]').val('invalid').change();
//
//    deepEqual([
//        ['GET', {ct_id: '127'}], ['GET', {ct_id: 'invalid'}]
//    ], this.mockBackendUrlCalls('mock/reports/hfilter'));
//    deepEqual([
//        ['GET', {ct_id: '127'}], ['GET', {ct_id: 'invalid'}]
//    ], this.mockBackendUrlCalls('mock/reports/efilter'));
//
//    this.equalOuterHtml('<select name="hf">' +
//                            '<option value="">' + gettext("None available") + '</option>' +
//                        '</select>',
//                        form.find('select[name="hf"]'));
//
//    this.equalOuterHtml('<select name="filter">' +
//                            '<option value="">' + gettext("All") + '</option>' +
//                        '</select>',
//                        form.find('select[name="filter"]'));
// });

// }(jQuery));
