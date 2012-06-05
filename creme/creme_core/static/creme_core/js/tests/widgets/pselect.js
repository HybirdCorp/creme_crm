function mock_pselect_create(type, noauto)
{
    var select = creme.widget.buildTag($('<span/>'), 'ui-creme-polymorphicselect', {type:type}, !noauto)
                     .append('<input type="hidden" class="ui-creme-input ui-creme-polymorphicselect"/>')
                     .append('<ul class="selector-model"/>');

    return select;
}

function mock_pselect_add_selector(element, type, selector, widget, options, defaults)
{
    var selector = creme.widget.buildTag(selector, widget, options, false);
    var item = $('<li/>').attr('input-type', type).append(selector);

    if (defaults)
        item.addClass('default');

    $('ul.selector-model', element).append(item);
    return selector;
}

function assertSelector(widget, type, value, query)
{
    equal(widget.selectorType(), type, 'selector type');
    equal(widget.val(), $.toJSON({type: type, value: (value !== null) ? value : ''}, 'value'));
    equal(widget.selector().creme().widget().val(), (value !== null) ? (typeof value !== 'string' ? $.toJSON(value) : value) : "", 'selector value');

    equal(widget.selector().length, 1);
    ok(widget.selector().is(query), 'selector');
}

module("creme.widgets.pselect.js", {
  setup: function() {
  },
  teardown: function() {
  },
});


test('creme.widgets.pselect.create (empty, no selector)', function() {
    var element = mock_pselect_create();
    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), $.toJSON({type:null, value:''}));

    equal(widget.selectorModelList().length, 0);
    equal(widget.defaultSelectorModel().length, 0);

    equal(widget.selectorType(), null);
    equal(widget.selector().length, 0);
});

test('creme.widgets.pselect.create (empty, single selector)', function() {
    var element = mock_pselect_create();
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {}, true);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), $.toJSON({type:null, value:''}));

    equal(widget.selectorModelList().length, 1);
    equal(widget.defaultSelectorModel().length, 1);
    equal(widget.selectorModel('text').length, 1);

    equal(widget.selectorType(), null);
    equal(widget.selector().length, 0);
});

test('creme.widgets.pselect.create (empty, multiple selector)', function() {
    var element = mock_pselect_create();
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {}, true);
    var password = mock_pselect_add_selector(element, 'password', $('<input type="password"/>'), 'ui-creme-dinput', {});
    var bool = mock_pselect_add_selector(element, 'boolean', $('<select><option value="true">True</option><option value="false">False</option></select>'), 'ui-creme-dselect', {});

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), $.toJSON({type:null, value:''}));

    equal(widget.selectorModelList().length, 3);
    equal(widget.defaultSelectorModel().length, 1);
    equal(widget.selectorModel('text').length, 1);
    equal(widget.selectorModel('password').length, 1);
    equal(widget.selectorModel('boolean').length, 1);

    // if unknown use default
    equal(widget.selectorModel('double').length, 1);
    equal(widget.selectorModel('int').length, 1);
    equal(widget.selectorModel('float').length, 1);

    equal(widget.selectorType(), null);
    equal(widget.selector().length, 0);
});

test('creme.widgets.pselect.create (empty, multiple selector, no default)', function() {
    var element = mock_pselect_create();
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {});
    var password = mock_pselect_add_selector(element, 'password', $('<input type="password"/>'), 'ui-creme-dinput', {});
    var bool = mock_pselect_add_selector(element, 'boolean', $('<select><option value="true">True</option><option value="false">False</option></select>'), 'ui-creme-dselect', {});

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), $.toJSON({type:null, value:''}));

    equal(widget.selectorModelList().length, 3);
    equal(widget.defaultSelectorModel().length, 0);
    equal(widget.selectorModel('text').length, 1);
    equal(widget.selectorModel('password').length, 1);
    equal(widget.selectorModel('boolean').length, 1);

    equal(widget.selectorModel('double').length, 0);
    equal(widget.selectorModel('int').length, 0);
    equal(widget.selectorModel('float').length, 0);

    equal(widget.selectorType(), null);
    equal(widget.selector().length, 0);
});

test('creme.widgets.pselect.create (type, no value, no selector)', function() {
    var element = mock_pselect_create('text');
    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({type:null, value:''}));

    equal(widget.selectorModelList().length, 0);
    equal(widget.defaultSelectorModel().length, 0);

    equal(widget.selectorType(), null);
    equal(widget.selector().length, 0);
});

test('creme.widgets.pselect.create (type, no value, single selector)', function() {
    var element = mock_pselect_create('text');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {}, true);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({type:'text', value:''}));

    equal(widget.selectorModelList().length, 1);
    equal(widget.defaultSelectorModel().length, 1);

    equal(widget.selectorType(), 'text');
    equal(widget.selector().length, 1);
});

test('creme.widgets.pselect.create (unknown type, no value, single selector)', function() {
    var element = mock_pselect_create('boolean');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {}, true);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({type:'boolean', value:''}));

    equal(widget.selectorModelList().length, 1);
    equal(widget.defaultSelectorModel().length, 1);

    equal(widget.selectorType(), 'boolean');
    equal(widget.selector().length, 1);
});

test('creme.widgets.pselect.create (unknown type, no value, single selector, no default)', function() {
    var element = mock_pselect_create('boolean');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {});

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({type:null, value:''}));

    equal(widget.selectorModelList().length, 1);
    equal(widget.defaultSelectorModel().length, 0);

    equal(widget.selectorType(), null);
    equal(widget.selector().length, 0);
});

test('creme.widgets.pselect.create (type, no value, multiple selector)', function() {
    var element = mock_pselect_create('text');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {}, true);
    var password = mock_pselect_add_selector(element, 'password', $('<input type="password"/>'), 'ui-creme-dinput', {});
    var bool = mock_pselect_add_selector(element, 'boolean', $('<select><option value="true">True</option><option value="false">False</option></select>'), 'ui-creme-dselect', {});

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({type:'text', value:''}));

    equal(widget.selectorModelList().length, 3);
    equal(widget.defaultSelectorModel().length, 1);

    equal(widget.selectorType(), 'text');
    equal(widget.selector().length, 1);
});


test('creme.widgets.pselect.create (type, no value, single selector)', function() {
    var element = mock_pselect_create('text');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {}, true);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({type:'text', value:''}));

    equal(widget.selectorModelList().length, 1);
    equal(widget.defaultSelectorModel().length, 1);

    equal(widget.selectorType(), 'text');
    equal(widget.selector().length, 1);
});

test('creme.widgets.pselect.val (unknown type, single selector)', function() {
    var element = mock_pselect_create('text');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {}, true);

    var widget = creme.widget.create(element);
    assertSelector(widget, 'text', null, '.ui-creme-dinput[type="text"]');

    widget.val({type:'double', value:12.5});
    assertSelector(widget, 'double', 12.5, '.ui-creme-dinput[type="text"]');
});

test('creme.widgets.pselect.val (unknown type, single selector, no default)', function() {
    var element = mock_pselect_create('text');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {});

    var widget = creme.widget.create(element);
    assertSelector(widget, 'text', null, '.ui-creme-dinput[type="text"]');

    // keep the same selector
    widget.val({type:'double', value:12.5});
    assertSelector(widget, 'text', 12.5, '.ui-creme-dinput[type="text"]');
});

test('creme.widgets.pselect.val (type, value, multiple selector)', function() {
    var element = mock_pselect_create('text');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {});
    var password = mock_pselect_add_selector(element, 'password', $('<input type="password"/>'), 'ui-creme-dinput', {});
    var bool = mock_pselect_add_selector(element, 'boolean', $('<select><option value="true">True</option><option value="false">False</option></select>'), 'ui-creme-dselect', {});

    var widget = creme.widget.create(element);
    assertSelector(widget, 'text', null, '.ui-creme-dinput[type="text"]');

    widget.val({type:'password', value:'toor'});
    assertSelector(widget, 'password', 'toor', '.ui-creme-dinput[type="password"]');
});

test('creme.widgets.pselect.reload (unknown type, single selector)', function() {
    var element = mock_pselect_create('text');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {}, true);

    var widget = creme.widget.create(element);
    widget.val({type:'double', value:12.5});
    assertSelector(widget, 'double', 12.5, '.ui-creme-dinput[type="text"]');

    widget.reload({operator:'boolean'});
    assertSelector(widget, 'boolean', 12.5, '.ui-creme-dinput[type="text"]');
});

test('creme.widgets.pselect.reload (unknown type, single selector, no default)', function() {
    var element = mock_pselect_create('text');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {});

    var widget = creme.widget.create(element);
    widget.val({type:'text', value:12.5});
    assertSelector(widget, 'text', 12.5, '.ui-creme-dinput[type="text"]');

    widget.reload({operator:'boolean'});
    assertSelector(widget, 'text', 12.5, '.ui-creme-dinput[type="text"]');
});

test('creme.widgets.pselect.reload (type, value, multiple selector)', function() {
    var element = mock_pselect_create('text');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {});
    var password = mock_pselect_add_selector(element, 'password', $('<input type="password"/>'), 'ui-creme-dinput', {});
    var bool = mock_pselect_add_selector(element, 'boolean', $('<select><option value="true">True</option><option value="false">False</option></select>'), 'ui-creme-dselect', {});

    var widget = creme.widget.create(element);
    widget.val({type:'password', value:'toor'});
    assertSelector(widget, 'password', 'toor', '.ui-creme-dinput[type="password"]');

    widget.reload({operator:'boolean'});
    assertSelector(widget, 'boolean', true, '.ui-creme-dselect');
});
