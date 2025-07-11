/* globals QUnitWidgetMixin */
(function($) {

QUnit.module("creme.widget.DateRangeSelector", new QUnitMixin(QUnitEventMixin,
                                                              QUnitWidgetMixin, {
    afterEach: function(env) {
        $('.ui-dialog-content').dialog('destroy');
        creme.widget.shutdown($('body'));

        if ($('#ui-datepicker-div').length > 0) {
            console.warn('Some jQuery.datepicker dialogs has not been cleaned up !');
            $('#ui-datepicker-div').detach();
        }
    },

    createDateRangeSelectorHtml: function(options) {
        options = Object.assign({
            options: [
                {value: '', label: 'Custom'},
                {value: 'previous_year', label: 'Previous year'},
                {value: 'current_year', label: 'Next year'},
                {value: 'next_year', label: 'Next year'}
            ],
            value: {
                type: '',
                start: '',
                end: ''
            }
        }, options || {});

        function renderOption(option) {
            return '<option value="${value}" ${selected}>${label}</option>'.template({
                value: option.value,
                label: option.label,
                selected: option.selected ? 'selected' : ''
            });
        }

        var html = (
            '<span class="ui-creme-widget widget-auto ui-creme-daterange-selector" widget="ui-creme-daterange-selector" ${format}>' +
                '<input type="hidden" datatype="json" class="ui-creme-input ui-creme-daterange-selector" value="${value}" ${readonly} ${disabled}/>' +
                '<select class="daterange-input range-type">${options}</select>' +
                '<span class="daterange-inputs">' +
                    '<input type="text" class="daterange-input date-start" />' +
                    '<input type="text" class="daterange-input date-end" />' +
                '</span>' +
            '</span>'
        ).template({
            readonly: options.readonly ? 'readonly' : '',
            disabled: options.disabled ? 'disabled' : '',
            format: options.format ? 'data-format="${format}"'.template(options) : '',
            value: Object.isString(options.value) ? options.value : JSON.stringify(options.value || {}).escapeHTML(),
            options: (options.options || []).map(renderOption).join('')
        });

        return html;
    }
}));


QUnit.test('creme.widget.DateRangeSelector.create (empty)', function(assert) {
    var element = $(this.createDateRangeSelectorHtml());

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(element.is('[disabled]'), false);
    assert.equal(element.is('[readonly]'), false);

    assert.equal(element.find('.date-start').is('.hasDatepicker'), true);
    assert.equal(element.find('.date-end').is('.hasDatepicker'), true);

    assert.deepEqual({type: '', start: '', end: ''}, JSON.parse(widget.val()));
});


QUnit.parameterize('creme.widget.DateRangeSelector.create (initial)', [
    [null, {type: '', start: '', end: ''}],
    ['', {type: '', start: '', end: ''}],
    ['{"type": null}', {type: '', start: '', end: ''}],
    ['not json', {type: '', start: '', end: ''}],
    [{start: '23-12-1990', end: '31-12-1990'}, {type: '', start: '23-12-1990', end: '31-12-1990'}]
], function(value, expected, assert) {
    var element = $(this.createDateRangeSelectorHtml({value: value}));

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(element.is('[disabled]'), false);
    assert.equal(element.is('[readonly]'), false);

    assert.equal(element.find('.date-start').is('.hasDatepicker'), true);
    assert.equal(element.find('.date-end').is('.hasDatepicker'), true);

    assert.deepEqual(expected, JSON.parse(widget.val()));
});

QUnit.parameterize('creme.widget.DateRangeSelector.create (format)', [
    [undefined, {}, 'dd-mm-yy', {start: '23-12-1990', end: '31-12-1990'}, {type: '', start: '23-12-1990', end: '31-12-1990'}],
    [undefined, {}, 'dd-mm-yy', {start: '23/12/1990', end: '31/12/1990'}, {type: '', start: '23/12/1990', end: '31/12/1990'}],
    ['dd/mm/yy', {}, 'dd/mm/yy', {start: '23/12/1990', end: '31/12/1990'}, {type: '', start: '23/12/1990', end: '31/12/1990'}],
    [undefined, {format: 'dd/mm/yy'}, 'dd/mm/yy', {start: '23/12/1990', end: '31/12/1990'}, {type: '', start: '23/12/1990', end: '31/12/1990'}]
], function(format, options, expectedFormat, value, expected, assert) {
    var element = $(this.createDateRangeSelectorHtml({value: value, format: format}));

    var widget = creme.widget.create(element, options);

    assert.equal(element.find('.date-start').is('.hasDatepicker'), true);
    assert.equal(element.find('.date-end').is('.hasDatepicker'), true);

    assert.equal(element.find('.date-start').datepicker('option', 'dateFormat'), expectedFormat);
    assert.equal(element.find('.date-end').datepicker('option', 'dateFormat'), expectedFormat);

    assert.deepEqual(expected, JSON.parse(widget.val()));
});

QUnit.test('creme.widget.DateRangeSelector.rangeType (switch predefined)', function(assert) {
    var element = $(this.createDateRangeSelectorHtml({
        value: {
            type: '',
            start: '12-05-2018',
            end: '08-04-2025'
        }
    }));
    var widget = creme.widget.create(element);

    assert.equal(element.find('.daterange-inputs').is('.hidden'), false);
    assert.deepEqual({
        type: '', start: '12-05-2018', end: '08-04-2025'
    }, JSON.parse(widget.val()));

    element.find('.range-type').val('next_year').trigger('change');

    assert.equal(element.find('.daterange-inputs').is('.hidden'), true);
    assert.deepEqual({
        type: 'next_year', start: '', end: ''
    }, JSON.parse(widget.val()));
});

QUnit.test('creme.widget.DateRangeSelector.rangeType (switch custom)', function(assert) {
    var element = $(this.createDateRangeSelectorHtml({
        value: {
            type: 'next_year',
            start: '',
            end: ''
        }
    }));
    var widget = creme.widget.create(element);

    assert.equal(element.find('.daterange-inputs').is('.hidden'), true);
    assert.deepEqual({
        type: 'next_year', start: '', end: ''
    }, JSON.parse(widget.val()));

    element.find('.range-type').val('').trigger('change');

    assert.equal(element.find('.daterange-inputs').is('.hidden'), false);
    assert.deepEqual({
        type: '', start: '', end: ''
    }, JSON.parse(widget.val()));
});

QUnit.test('creme.widget.DateRangeSelector.dateInput (predefined)', function(assert) {
    var element = $(this.createDateRangeSelectorHtml({
        value: {
            type: 'next_year',
            start: '',
            end: ''
        }
    }));
    var widget = creme.widget.create(element);

    assert.equal(element.find('.daterange-inputs').is('.hidden'), true);
    assert.deepEqual({
        type: 'next_year', start: '', end: ''
    }, JSON.parse(widget.val()));

    widget.startDate().val('10-05-2016').trigger('change');
    assert.deepEqual({
        type: 'next_year', start: '10-05-2016', end: ''
    }, JSON.parse(widget.val()));

    widget.endDate().val('10-05-2016').trigger('change');
    assert.deepEqual({
        type: 'next_year', start: '10-05-2016', end: '10-05-2016'
    }, JSON.parse(widget.val()));
});

QUnit.test('creme.widget.DateRangeSelector.dateInput (custom)', function(assert) {
    var element = $(this.createDateRangeSelectorHtml({
        value: {
            type: '',
            start: '',
            end: ''
        }
    }));
    var widget = creme.widget.create(element);

    assert.equal(element.find('.daterange-inputs').is('.hidden'), false);
    assert.deepEqual({
        type: '', start: '', end: ''
    }, JSON.parse(widget.val()));

    widget.startDate().val('10-05-2016').trigger('change');
    assert.deepEqual({
        type: '', start: '10-05-2016', end: ''
    }, JSON.parse(widget.val()));

    widget.endDate().val('10-05-2022').trigger('change');
    assert.deepEqual({
        type: '', start: '10-05-2016', end: '10-05-2022'
    }, JSON.parse(widget.val()));
});

QUnit.test('creme.widget.DateRangeSelector.val', function(assert) {
    var element = $(this.createDateRangeSelectorHtml({
        value: {
            type: 'next_year',
            start: '',
            end: ''
        }
    }));
    var widget = creme.widget.create(element);

    assert.equal(element.find('.daterange-inputs').is('.hidden'), true);
    assert.deepEqual({
        type: 'next_year', start: '', end: ''
    }, JSON.parse(widget.val()));

    widget.val({type: '', start: '05-12-2010'});

    assert.equal(element.find('.daterange-inputs').is('.hidden'), false);
    assert.deepEqual({
        type: '', start: '05-12-2010', end: ''
    }, JSON.parse(widget.val()));

    widget.val({type: 'previous_year', start: '05-08-2020'});

    assert.equal(element.find('.daterange-inputs').is('.hidden'), true);
    assert.deepEqual({
        type: 'previous_year', start: '', end: ''
    }, JSON.parse(widget.val()));

    widget.val(null);

    assert.equal(element.find('.daterange-inputs').is('.hidden'), false);
    assert.deepEqual({
        type: '', start: '', end: ''
    }, JSON.parse(widget.val()));
});

}(jQuery));
