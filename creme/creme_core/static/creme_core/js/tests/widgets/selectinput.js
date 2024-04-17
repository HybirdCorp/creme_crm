/* globals QUnitWidgetMixin  */

(function($) {

QUnit.module("creme.widget.SelectOrInputWidget", new QUnitMixin(QUnitEventMixin,
                                                                QUnitWidgetMixin, {
    createSelectOrInputHtml: function(options) {
        options = options || {};

        function renderOption(option) {
            return '<option value="${value}" ${selected}>${label}</option>'.template({
                value: option.value,
                label: option.label,
                selected: option.selected ? 'selected' : ''
            });
        }

        var html = (
            '<span widget="ui-creme-selectorinput" class="ui-creme-selectorinput ui-creme-widget ${auto}">' +
                '<input type="text" value="${text}"/>' +
                '<select>${options}</select>' +
            '</span>'
        ).template({
            auto: options.auto ? 'widget-auto' : '',
            text: options.text || '',
            options: (options.options || []).map(renderOption).join('')
        });

        return html;
    }
}));

QUnit.test('creme.widget.SelectOrInputWidget.create', function(assert) {
    var element = $(this.createSelectOrInputHtml({
        options: [{value: 0, label: 'Other'}, {value: 1, label: 'A', selected: true}, {value: 2, label: 'B'}]
    }));

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal('1', $('select', element).val());
    equal('', $('input', element).val());
    equal('1', widget.val());
});

QUnit.test('creme.widget.SelectOrInputWidget.create (other)', function(assert) {
    var element = $(this.createSelectOrInputHtml({
        options: [{value: 0, label: 'Other', selected: true}, {value: 1, label: 'A'}, {value: 2, label: 'B'}],
        text: '17'
    }));

    var widget = creme.widget.create(element);

    equal('0', $('select', element).val());
    equal('17', $('input', element).val());
    equal('17', widget.val());
});

QUnit.test('creme.widget.SelectOrInputWidget (input cache)', function(assert) {
    var element = $(this.createSelectOrInputHtml({
        options: [{value: 0, label: 'Other', selected: true}, {value: 1, label: 'A'}, {value: 2, label: 'B'}],
        text: '17'
    }));

    var widget = creme.widget.create(element);

    $('select', element).val('2').trigger('change');

    equal('', $('input', element).val());
    equal('2', widget.val());

    $('select', element).val('0').trigger('change');

    equal('17', $('input', element).val());
    equal('17', widget.val());
});

QUnit.test('creme.widget.SelectOrInputWidget (input keyup)', function(assert) {
    var element = $(this.createSelectOrInputHtml({
        options: [{value: 0, label: 'Other'}, {value: 1, label: 'A', selected: true}, {value: 2, label: 'B'}],
        text: '17'
    }));

    var widget = creme.widget.create(element);

    equal('1', $('select', element).val());
    equal('17', $('input', element).val());
    equal('1', widget.val());

    $('input', element).val('73').trigger($.Event("keyup", {keyCode: 48})); /* 0 */

    equal('0', $('select', element).val());
    equal('73', $('input', element).val());
    equal('73', widget.val());
});

}(jQuery));
