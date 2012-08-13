function mock_dinput_create(value, noauto) {
    var select = $('<input type="text" widget="ui-creme-dinput" class="ui-creme-dinput ui-creme-widget"/>');

    if (value !== undefined)
        select.attr('value', value);

    if (!noauto)
        select.addClass('widget-auto');

    return select;
}


module("creme.widgets.dinput.js", {
  setup: function() {
  },
  teardown: function() {
  }
});

test('creme.widget.DynamicInput.create (empty)', function() {
    var element = mock_dinput_create();

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal('', element.val());
    equal('', element.creme().widget().val());
});

test('creme.widget.DynamicInput.create (static)', function() {
    var element = mock_dinput_create('this is a test');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal('this is a test', element.val());
    equal('this is a test', element.creme().widget().val());
});

test('creme.widget.DynamicInput.placeholder', function() {
    var element = mock_dinput_create();
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
