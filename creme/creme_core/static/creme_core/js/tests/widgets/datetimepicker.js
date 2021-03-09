/* globals QUnitWidgetMixin */
(function($) {

QUnit.module("creme.widgets.dinput.js", new QUnitMixin(QUnitAjaxMixin,
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
            '<ul class="ui-creme-widget widget-auto ui-creme-datetimepicker" widget="ui-creme-datetimepicker" ${format} ${readonly} ${disabled}>' +
                '<input type="hidden" name="${name}" value="${value}" />' +
                '<li class="date"><input type="text" maxlength="12"/></li>' +
                '<li class="hour"><input type="text" maxlength="2"/></li>' +
                '<li class="minute"><input type="text" maxlength="2"/></li>' +
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
    }
}));

QUnit.test('creme.widget.DateTimePicker.create (empty)', function(assert) {
    var element = $(this.createDateTimePickerHtml());

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(element.is('[disabled]'), false);
    equal(element.is('[readonly]'), false);

    equal('', element.find('input[type="hidden"]').val());
    equal('', widget.val());

    equal(widget.delegate._disabled, false);
});

QUnit.test('creme.widget.DateTimePicker.create (disabled)', function(assert) {
    var element = $(this.createDateTimePickerHtml({
        disabled: true
    }));

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-ready'), true);
    equal(element.is('[disabled]'), true);
    equal(widget.delegate._disabled, true);

    element = $(this.createDateTimePickerHtml());
    widget = creme.widget.create(element, {
        disabled: true
    });

    equal(element.hasClass('widget-ready'), true);
    equal(element.is('[disabled]'), true);
    equal(widget.delegate._disabled, true);
});

QUnit.test('creme.widget.DateTimePicker.create (readonly)', function(assert) {
    var element = $(this.createDateTimePickerHtml({
        readonly: true
    }));

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-ready'), true);
    equal(element.is('[readonly]'), true);
    equal(widget.delegate._readonly, true);

    element = $(this.createDateTimePickerHtml());
    widget = creme.widget.create(element, {
        readonly: true
    });

    equal(element.hasClass('widget-ready'), true);
    equal(element.is('[readonly]'), true);
    equal(widget.delegate._readonly, true);
});

QUnit.test('creme.widget.DateTimePicker.val (initial)', function(assert) {
    var element = $(this.createDateTimePickerHtml({
        value: '28-02-2021 18:15:38'
    }));

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-ready'), true);

    equal('28-02-2021 18:15:38', element.find('input[type="hidden"]').val());
    equal('28-02-2021 18:15:38', widget.val());
    equal('28-02-2021', element.find('.date input').val());
    equal('18', element.find('.hour input').val());
    equal('15', element.find('.minute input').val());
});

QUnit.parametrize('creme.widget.DateTimePicker.val (from element)', [
    ['', {date: '', hour: '', minute: ''}],
    ['28-02-2021', {date: '', hour: '', minute: ''}],
    ['27-03-2020 15:37', {date: '27-03-2020', hour: '15', minute: '37'}]
], function(value, expected, assert) {
    var element = $(this.createDateTimePickerHtml());
    var widget = creme.widget.create(element);

    element.find('input[type="hidden"]').val(value).trigger('change');

    equal(widget.val(), value);
    equal(element.find('.date input').val(), expected.date);
    equal(element.find('.hour input').val(), expected.hour);
    equal(element.find('.minute input').val(), expected.minute);
});


QUnit.parametrize('creme.widget.DateTimePicker.val (from widget)', [
    ['', {date: '', hour: '', minute: ''}],
    ['28-02-2021', {date: '', hour: '', minute: ''}],
    ['27-03-2020 15:37', {date: '27-03-2020', hour: '15', minute: '37'}]
], function(value, expected, assert) {
    var element = $(this.createDateTimePickerHtml());
    var widget = creme.widget.create(element);

    widget.val(value);

    equal(element.find('input[type="hidden"]').val(), value);
    equal(element.find('.date input').val(), expected.date);
    equal(element.find('.hour input').val(), expected.hour);
    equal(element.find('.minute input').val(), expected.minute);
});

}(jQuery));
