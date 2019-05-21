/* globals QUnitWidgetMixin */
(function($) {

QUnit.module("creme.widgets.dinput.js", new QUnitMixin(QUnitAjaxMixin,
                                                       QUnitEventMixin,
                                                       QUnitWidgetMixin));

QUnit.test('creme.widget.DynamicInput.create (empty)', function(assert) {
    var element = this.createDynamicInputTag();

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal('', element.val());
    equal('', element.creme().widget().val());
});

QUnit.test('creme.widget.DynamicInput.create (static)', function(assert) {
    var element = this.createDynamicInputTag('this is a test');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal('this is a test', element.val());
    equal('this is a test', element.creme().widget().val());
});

QUnit.test('creme.widget.DynamicInput.create (static, disabled)', function(assert) {
    var element = this.createDynamicInputTag('this is a test');
    element.attr('disabled', '');

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-ready'), true);
    equal(element.is('[disabled]'), true);
    equal(widget.delegate._enabled, false);

    element = this.createDynamicInputTag('this is a test');
    equal(element.is('[disabled]'), false);

    widget = creme.widget.create(element, {disabled: true});

    equal(element.hasClass('widget-ready'), true);
    equal(element.is('[disabled]'), true);
    equal(widget.delegate._enabled, false);
});

QUnit.test('creme.widget.DynamicInput.placeholder', function(assert) {
    var element = this.createDynamicInputTag();
    element.attr('placeholder', 'edit this text');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal('', element.val());
    equal('', element.creme().widget().val());

    element.val('this is a test');
    equal('this is a test', element.val());
    equal('this is a test', element.creme().widget().val());
});

QUnit.test('creme.widget.DynamicInput.reset', function(assert) {
    var element = this.createDynamicInputTag('this is a test');
    var widget = creme.widget.create(element);

    equal('this is a test', widget.val());

    widget.reset();
    equal('', widget.val());
});

}(jQuery));
