/* globals QUnitWidgetMixin */
(function($) {

QUnit.module("creme.widgets.dinput.js", new QUnitMixin(QUnitAjaxMixin,
                                                       QUnitEventMixin,
                                                       QUnitWidgetMixin));

QUnit.test('creme.widget.DynamicInput.create (empty)', function(assert) {
    var element = this.createDynamicInputTag();

    creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal('', element.val());
    assert.equal('', element.creme().widget().val());
});

QUnit.test('creme.widget.DynamicInput.create (static)', function(assert) {
    var element = this.createDynamicInputTag('this is a test');

    creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal('this is a test', element.val());
    assert.equal('this is a test', element.creme().widget().val());
});

QUnit.test('creme.widget.DynamicInput.create (static, disabled)', function(assert) {
    var element = this.createDynamicInputTag('this is a test');
    element.attr('disabled', '');

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.is('[disabled]'), true);
    assert.equal(widget.delegate._enabled, false);

    element = this.createDynamicInputTag('this is a test');
    assert.equal(element.is('[disabled]'), false);

    widget = creme.widget.create(element, {disabled: true});

    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.is('[disabled]'), true);
    assert.equal(widget.delegate._enabled, false);
});

QUnit.test('creme.widget.DynamicInput.placeholder', function(assert) {
    var element = this.createDynamicInputTag();
    element.attr('placeholder', 'edit this text');

    creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal('', element.val());
    assert.equal('', element.creme().widget().val());

    element.val('this is a test');
    assert.equal('this is a test', element.val());
    assert.equal('this is a test', element.creme().widget().val());
});

QUnit.test('creme.widget.DynamicInput.reset', function(assert) {
    var element = this.createDynamicInputTag('this is a test');
    var widget = creme.widget.create(element);

    assert.equal('this is a test', widget.val());

    widget.reset();
    assert.equal('', widget.val());
});

}(jQuery));
