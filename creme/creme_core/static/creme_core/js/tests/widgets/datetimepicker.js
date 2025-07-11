/* globals QUnitWidgetMixin */
(function($) {

QUnit.module("creme.widgets.datetime.js", new QUnitMixin(QUnitAjaxMixin,
                                                       QUnitEventMixin,
                                                       QUnitWidgetMixin, {
    afterEach: function(env) {
        $('.ui-dialog-content').dialog('destroy');
        creme.widget.shutdown($('body'));

        if ($('#ui-datepicker-div').length > 0) {
            console.warn('Some jQuery.datepicker dialogs has not been cleaned up !');
            $('#ui-datepicker-div').detach();
        }
    },

    createDateTimePickerHtml: function(options) {
        options = options || {};
        var html = (
            '<ul class="ui-creme-widget widget-auto ui-creme-datetimepicker" widget="ui-creme-datetimepicker" ${format}>' +
                '<input type="hidden" name="${name}" value="${value}" ${readonly} ${disabled}/>' +
                '<li class="date"><input type="text" maxlength="12"/></li>' +
                '<li class="hour"><input type="number"/></li>' +
                '<li class="minute"><input type="number"/></li>' +
                '<li class="clear"><button type="button">Clean</button></li>' +
                '<li class="now"><button type="button">Now</button></li>' +
            '</ul>'
        ).template({
            format: options.format ? 'format=${format}'.template(options) : '',
            readonly: options.readonly ? 'readonly' : '',
            disabled: options.disabled ? 'disabled' : '',
            name: options.name || 'datetime',
            value: options.value || ''
        });

        return html;
    },

    createDatePickerHtml: function(options) {
        options = Object.assign({
            format: 'dd-mm-yy'
        }, options || {});

        var html = (
            '<input class="ui-creme-widget ui-creme-datepicker" widget="ui-creme-datepicker" type="text" format="${format}" value="${value}" ${readonly} ${disabled} />'
        ).template({
            readonly: options.readonly ? 'readonly' : '',
            disabled: options.disabled ? 'disabled' : '',
            format: options.format,
            value: options.value ? String(options.value) : ''
        });

        return html;
    }
}));

QUnit.test('creme.widget.DateTimePicker.create (empty)', function(assert) {
    var element = $(this.createDateTimePickerHtml());

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(element.is('[disabled]'), false);
    assert.equal(element.is('[readonly]'), false);

    assert.equal('', element.find('input[type="hidden"]').val());
    assert.equal('', widget.val());

    assert.equal(widget.delegate._disabled, false);
});

QUnit.test('creme.widget.DateTimePicker.create (disabled)', function(assert) {
    var element = $(this.createDateTimePickerHtml({
        disabled: true
    }));

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.find('input').prop('disabled'), true);
    assert.equal(widget.delegate._disabled, true);

    element = $(this.createDateTimePickerHtml());
    widget = creme.widget.create(element, {
        disabled: true
    });

    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.find('input').prop('disabled'), true);
    assert.equal(widget.delegate._disabled, true);
});

QUnit.test('creme.widget.DateTimePicker.create (readonly)', function(assert) {
    var element = $(this.createDateTimePickerHtml({
        readonly: true
    }));

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.is('.is-readonly'), true);
    assert.equal(element.find('input').prop('readonly'), true);
    assert.equal(widget.delegate._readonly, true);

    element = $(this.createDateTimePickerHtml());
    widget = creme.widget.create(element, {
        readonly: true
    });

    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.is('.is-readonly'), true);
    assert.equal(element.find('input').prop('readonly'), true);
    assert.equal(widget.delegate._readonly, true);
});

QUnit.test('creme.widget.DateTimePicker.val (initial)', function(assert) {
    var element = $(this.createDateTimePickerHtml({
        value: '28-02-2021 18:15:38'
    }));

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal('28-02-2021 18:15:38', element.find('input[type="hidden"]').val());
    assert.equal('28-02-2021 18:15:38', widget.val());
    assert.equal('28-02-2021', element.find('.date input').val());
    assert.equal('18', element.find('.hour input').val());
    assert.equal('15', element.find('.minute input').val());
});

QUnit.parametrize('creme.widget.DateTimePicker.val (from element)', [
    ['', {date: '', hour: '', minute: ''}],
    ['28-02-2021', {date: '', hour: '', minute: ''}],
    ['27-03-2020 15:37', {date: '27-03-2020', hour: '15', minute: '37'}]
], function(value, expected, assert) {
    var element = $(this.createDateTimePickerHtml());
    var widget = creme.widget.create(element);

    element.find('input[type="hidden"]').val(value).trigger('change');

    assert.equal(widget.val(), value);
    assert.equal(element.find('.date input').val(), expected.date);
    assert.equal(element.find('.hour input').val(), expected.hour);
    assert.equal(element.find('.minute input').val(), expected.minute);
});


QUnit.parametrize('creme.widget.DateTimePicker.val (from widget)', [
    ['', {date: '', hour: '', minute: ''}],
    ['28-02-2021', {date: '', hour: '', minute: ''}],
    ['27-03-2020 15:37', {date: '27-03-2020', hour: '15', minute: '37'}]
], function(value, expected, assert) {
    var element = $(this.createDateTimePickerHtml());
    var widget = creme.widget.create(element);

    widget.val(value);

    assert.equal(element.find('input[type="hidden"]').val(), value);
    assert.equal(element.find('.date input').val(), expected.date);
    assert.equal(element.find('.hour input').val(), expected.hour);
    assert.equal(element.find('.minute input').val(), expected.minute);
});

QUnit.parameterize('creme.widget.DatePicker.create (initial)', [
    [{format: 'dd-mm-yy', value: ''}, ''],
    [{format: 'dd-mm-yy', value: '12-02-2025'}, '12-02-2025'],
    [{format: 'dd/mm/yy', value: '12-02-2025'}, ''],
    [{format: 'dd/mm/yy', value: '12/02/2025'}, '12/02/2025']
], function(options, expected, assert) {
    var element = $(this.createDatePickerHtml(options)).appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.hasClass('hasDatepicker'), true);  // jquery datepicker is enabled

    assert.equal(element.is('[disabled]'), false);
    assert.equal(element.is('[readonly]'), false);

    assert.equal(expected, element.val());
    assert.equal(expected, widget.val());
});

QUnit.parameterize('creme.widget.DatePicker.create (disabled, readonly)', [
    [{value: '12-02-2025', disabled: true, readonly: false}],
    [{value: '12-02-2025', disabled: false, readonly: true}],
    [{value: '12-02-2025', disabled: true, readonly: true}]
], function(options, assert) {
    var element = $(this.createDatePickerHtml(options)).appendTo(this.qunitFixture());
    creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.hasClass('hasDatepicker'), true);  // jquery datepicker is enabled

    assert.equal(element.is('[disabled]'), options.disabled || options.readonly);
    assert.equal(element.is('[readonly]'), options.readonly);
});

QUnit.test('creme.widget.DatePicker.val (today)', function(assert) {
    var element = $(this.createDatePickerHtml({
        value: '12-02-2024'
    })).appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal('12-02-2024', element.val());
    assert.equal('12-02-2024', widget.val());

    widget.val('13-03-2023');

    assert.equal('13-03-2023', element.val());
    assert.equal('13-03-2023', widget.val());

    assert.equal(1, $('[name="today"]').length);

    $('[name="today"]').trigger('click');

    var today = moment().format('DD-MM-YYYY');

    assert.equal(today, element.val());
    assert.equal(today, widget.val());
});

QUnit.parameterize('creme.widget.YearPicker.create', [
    [{value: '2025', disabled: false, readonly: false}],
    [{value: '2025', disabled: true, readonly: false}],
    [{value: '2025', disabled: false, readonly: true}],
    [{value: '', disabled: false, readonly: false}]
], function(options, assert) {
    options = options || {};

    var element = $((
        '<input class="ui-creme-widget ui-creme-yearpicker" widget="ui-creme-yearpicker" type="text" value="${value}" ${readonly} ${disabled} />'
    ).template({
        readonly: options.readonly ? 'readonly' : '',
        disabled: options.disabled ? 'disabled' : '',
        value: options.value ? String(options.value) : ''
    })).appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(element.is('[disabled]'), options.disabled || false);
    assert.equal(element.is('[readonly]'), options.readonly || false);

    assert.equal(options.value, element.val());
    assert.equal(options.value, widget.val());
});

QUnit.test('creme.widget.YearPicker.val (current year)', function(assert) {
    var element = $(
        '<input class="ui-creme-widget ui-creme-yearpicker" widget="ui-creme-yearpicker" type="text" value="2025" />'
    ).appendTo(this.qunitFixture());
    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    widget.val('2024');

    assert.equal('2024', element.val());
    assert.equal('2024', widget.val());

    assert.equal(1, $('[name="current-year"]').length);

    $('[name="current-year"]').trigger('click');

    assert.equal(String(new Date().getFullYear()), element.val());
    assert.equal(String(new Date().getFullYear()), widget.val());
});

}(jQuery));
