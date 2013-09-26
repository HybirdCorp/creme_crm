function mock_pselect_create(key, noauto)
{
    var select = creme.widget.buildTag($('<span/>'), 'ui-creme-polymorphicselect', {key:key}, !noauto)
                      .append('<input type="hidden" class="ui-creme-input ui-creme-polymorphicselect"/>');

    return select;
}

function mock_pselect_add_selector(element, type, selector, widget, options)
{
    var selector = creme.widget.buildTag(selector, widget, options, false);
    var item = $('<script type="text/template">').attr('selector-key', type).text(selector.prop('outerHTML'));

    element.append(item);
    return selector;
}

function assertSelector(widget, type, value, query)
{
    equal(widget.selectorKey(), type, 'selector type');
    equal(widget.val(), value, 'value');

    if (query !== undefined) {
        //console.log(widget.selector().element[0]);
        ok(widget.selector().element.is(query), 'selector');
        equal(widget.selector().val(), value, 'selector value');
    } else {
        equal(widget.selector(), undefined, 'empty selector');
    }
}

module("creme.widgets.pselect.js", {
  setup: function() {
  },
  teardown: function() {
  }
});


test('creme.widgets.pselect.create (empty, no selector)', function() {
    var element = mock_pselect_create();
    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), null);

    equal(widget.selectorModels().length, 0);
    equal(widget.selectorModel('*'), undefined);

    equal(widget.selectorKey(), '');
    equal(widget.selector(), undefined);
});

test('creme.widgets.pselect.create (empty, single selector)', function() {
    var element = mock_pselect_create();
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {}, true);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), null, 'value');

    equal(widget.selectorModels().length, 1, 'model count');
    equal(widget.selectorModel('*'), undefined, '* model');
    notEqual(widget.selectorModel('text'), undefined, 'text model');

    equal(widget.selectorKey(), '', 'key');
    equal(widget.selector(), undefined, 'selector');
});

test('creme.widgets.pselect.create (empty, default single selector)', function() {
    var element = mock_pselect_create();
    var text = mock_pselect_add_selector(element, '*', $('<input type="text"/>'), 'ui-creme-dinput', {}, true);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), '', 'value');

    equal(widget.selectorModels().length, 1);
    notEqual(widget.selectorModel('*'), undefined);
    notEqual(widget.selectorModel('text'), undefined);

    equal(widget.selectorKey(), '');
    equal(widget.selector().val(), '');
    ok(widget.selector().element.is('input[type="text"].ui-creme-dinput'));
});

test('creme.widgets.pselect.create (empty, multiple selector)', function() {
    var element = mock_pselect_create();
    var text = mock_pselect_add_selector(element, '*', $('<input type="text"/>'), 'ui-creme-dinput', {});
    var password = mock_pselect_add_selector(element, 'password', $('<input type="password"/>'), 'ui-creme-dinput', {});
    var bool = mock_pselect_add_selector(element, 'boolean', $('<select><option value="true">True</option><option value="false">False</option></select>'), 'ui-creme-dselect', {});

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), '');

    equal(widget.selectorModels().length, 3);
    notEqual(widget.selectorModel('text'), undefined);
    notEqual(widget.selectorModel('password'), undefined);
    notEqual(widget.selectorModel('boolean'), undefined);

    // if unknown use default
    notEqual(widget.selectorModel('double'), undefined);
    notEqual(widget.selectorModel('int'), undefined);
    notEqual(widget.selectorModel('float'), undefined);

    equal(widget.selectorKey(), '');
    equal(widget.selector().val(), '');
    ok(widget.selector().element.is('input[type="text"].ui-creme-dinput'));
});

test('creme.widgets.pselect.create (empty, multiple selector, no default)', function() {
    var element = mock_pselect_create();
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {});
    var password = mock_pselect_add_selector(element, 'password', $('<input type="password"/>'), 'ui-creme-dinput', {});
    var bool = mock_pselect_add_selector(element, 'boolean', $('<select><option value="true">True</option><option value="false">False</option></select>'), 'ui-creme-dselect', {});

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), null);

    equal(widget.selectorModels().length, 3);
    notEqual(widget.selectorModel('text'), undefined);
    notEqual(widget.selectorModel('password'), undefined);
    notEqual(widget.selectorModel('boolean'), undefined);

    equal(widget.selectorModel('double'), undefined);
    equal(widget.selectorModel('int'), undefined);
    equal(widget.selectorModel('float'), undefined);

    equal(widget.selectorKey(), '');
    equal(widget.selector(), undefined);
});

test('creme.widgets.pselect.val (unknown key, default selector)', function() {
    var element = mock_pselect_create('unknown');
    var text = mock_pselect_add_selector(element, '*', $('<input type="text"/>'), 'ui-creme-dinput', {});

    var widget = creme.widget.create(element);

    assertSelector(widget, 'unknown', '', '.ui-creme-dinput[type="text"]');

    widget.val(12.5);
    assertSelector(widget, 'unknown', 12.5, '.ui-creme-dinput[type="text"]');
});

test('creme.widgets.pselect.val (key, no selector)', function() {
    var element = mock_pselect_create('text');
    var widget = creme.widget.create(element);

    assertSelector(widget, 'text', null);

    widget.val(12.5);
    assertSelector(widget, 'text', null);
});

test('creme.widgets.pselect.val (selector)', function() {
    var element = mock_pselect_create('text');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {});

    var widget = creme.widget.create(element);
    assertSelector(widget, 'text', '', '.ui-creme-dinput[type="text"]');

    widget.val(12.5);
    assertSelector(widget, 'text', 12.5, '.ui-creme-dinput[type="text"]');
});

test('creme.widgets.pselect.val (multiple selector)', function() {
    var element = mock_pselect_create('password');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {});
    var password = mock_pselect_add_selector(element, 'password', $('<input type="password"/>'), 'ui-creme-dinput', {});
    var bool = mock_pselect_add_selector(element, 'boolean', $('<select><option value="true">True</option><option value="false">False</option></select>'), 'ui-creme-dselect', {});

    var widget = creme.widget.create(element);
    widget.val('toor');
    assertSelector(widget, 'password', 'toor', '.ui-creme-dinput[type="password"]');
});

test('creme.widgets.pselect.reload (unknown type, default selector)', function() {
    var element = mock_pselect_create('${operator}');
    var text = mock_pselect_add_selector(element, '*', $('<input type="text"/>'), 'ui-creme-dinput', {});

    var widget = creme.widget.create(element);
    deepEqual(['operator'], widget.dependencies())
    assertSelector(widget, '', '', '.ui-creme-dinput[type="text"]');

    widget.reload({operator:'text'});
    widget.val(12.5);
    assertSelector(widget, 'text', 12.5, '.ui-creme-dinput[type="text"]');

    widget.reload({operator:'boolean'});
    assertSelector(widget, 'boolean', 12.5, '.ui-creme-dinput[type="text"]');
});

test('creme.widgets.pselect.reload (any type, default selector, template)', function() {
    var element = mock_pselect_create('${operator}');
    var text = mock_pselect_add_selector(element, '*', $('<input type="${operator}"/>'), 'ui-creme-dinput', {});

    var widget = creme.widget.create(element);
    deepEqual(['operator'], widget.dependencies());
    assertSelector(widget, '', '', '.ui-creme-dinput[type]');

    widget.reload({operator:'text'});
    widget.val(12.5);
    assertSelector(widget, 'text', 12.5, '.ui-creme-dinput[type="text"]');

    widget.reload({operator:'boolean'});
    assertSelector(widget, 'boolean', '', '.ui-creme-dinput[type="boolean"]');
});

test('creme.widgets.pselect.reload (unknown type, single selector, no default)', function() {
    var element = mock_pselect_create('${operator}');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {});

    var widget = creme.widget.create(element);
    deepEqual(['operator'], widget.dependencies())
    assertSelector(widget, '', null);

    widget.reload({operator:'text'});
    widget.val(12.5);
    assertSelector(widget, 'text', 12.5, '.ui-creme-dinput[type="text"]');

    widget.reload({operator:'boolean'});
    assertSelector(widget, 'boolean', null);
});

test('creme.widgets.pselect.reload (type, value, multiple selector)', function() {
    var element = mock_pselect_create('${operator}');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {});
    var password = mock_pselect_add_selector(element, 'password', $('<input type="password"/>'), 'ui-creme-dinput', {});
    var bool = mock_pselect_add_selector(element, 'boolean', $('<select><option value="true">True</option><option value="false">False</option></select>'), 'ui-creme-dselect', {});

    var widget = creme.widget.create(element);
    assertSelector(widget, '', null);

    widget.reload({operator: 'password'});
    widget.val('toor');

    assertSelector(widget, 'password', 'toor', '.ui-creme-dinput[type="password"]');

    widget.reload({operator:'boolean'});
    assertSelector(widget, 'boolean', 'true', '.ui-creme-dselect');
});

test('creme.widgets.pselect.reload (type, value, multiple selector, template)', function() {
    var element = mock_pselect_create('${operator}.${type}');
    var text = mock_pselect_add_selector(element, 'text.*', $('<input type="text"/>'), 'ui-creme-dinput', {});
    var password = mock_pselect_add_selector(element, 'input.*', $('<input type="${type}"/>'), 'ui-creme-dinput', {});
    var bool = mock_pselect_add_selector(element, 'boolean.*', $('<select><option value="true" selected>True</option><option value="false">False</option></select>'), 'ui-creme-dselect', {});

    var widget = creme.widget.create(element);
    assertSelector(widget, '', null);

    widget.reload({operator: 'input', type: 'password'});
    widget.val('toor');

    assertSelector(widget, 'input.password', 'toor', '.ui-creme-dinput[type="password"]');

    widget.reload({operator:'input', type: 'boolean'});
    assertSelector(widget, 'input.boolean', '', '.ui-creme-dinput[type="boolean"]');

    widget.reload({operator:'text', type: 'boolean'});
    assertSelector(widget, 'text.boolean', '', '.ui-creme-dinput[type="text"]');

    widget.reload({operator:'boolean'});
    assertSelector(widget, 'boolean.boolean', 'true', '.ui-creme-dselect');
});

test('creme.widgets.pselect.reset (type, value, multiple selector)', function() {
    var element = mock_pselect_create('${operator}');
    var text = mock_pselect_add_selector(element, 'text', $('<input type="text"/>'), 'ui-creme-dinput', {});
    var password = mock_pselect_add_selector(element, 'password', $('<input type="password"/>'), 'ui-creme-dinput', {});
    var bool = mock_pselect_add_selector(element, 'boolean', $('<select><option value="true">True</option><option value="false">False</option></select>'), 'ui-creme-dselect', {});

    var widget = creme.widget.create(element);

    widget.reload({operator: 'password'});
    widget.val('toor');
    assertSelector(widget, 'password', 'toor', '.ui-creme-dinput[type="password"]');

    widget.reset();
    assertSelector(widget, 'password', '', '.ui-creme-dinput[type="password"]');
});
