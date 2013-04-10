function mock_chainedselect_create(value, noauto)
{
    var element = creme.widget.buildTag($('<span/>'), 'ui-creme-chainedselect', {}, !noauto)
                       .append('<input type="hidden" class="ui-creme-input ui-creme-chainedselect"/>')
                       .append('<ul/>');

    if (value !== undefined) {
        $('input.ui-creme-input', element).val(value);
    }

    return element;
}

function mock_chainedselect_add(element, name, selector)
{
    $('ul', element).append($('<li/>').attr('chained-name', name)
                                      .addClass('ui-creme-chainedselect-item')
                                      .append(selector));

    return selector;
}

function mock_chainedselect_add_div(element, name, selector)
{
    $('ul', element).append($('<div/>').attr('chained-name', name)
                                       .addClass('ui-creme-chainedselect-item')
                                       .append(selector));

    return selector;
}

function mock_chainedselect_add_entityselector(element, name, options)
{
   var selector = mock_entityselector_create(options, true);
   return mock_chainedselect_add(element, name, selector);
}

function assertDSelectAt(widget, name, value, dependencies, url, choices)
{
    equal(widget.selector(name).length, 1);
    assertDSelect(widget.selector(name), value, dependencies, url, choices);
}

function assertDSelect(select, value, dependencies, url, choices)
{
    equal(creme.object.isempty(select), false);

    if (creme.object.isempty(select))
        return;

    equal(select.creme().isActive(), true);
    equal(select.creme().widget().cleanedval(), value);
    deepEqual(select.creme().widget().dependencies(), dependencies);
    equal(select.creme().widget().url(), url);
    deepEqual(select.creme().widget().choices(), choices);
}

function assertEntitySelect(select, value, dependencies, url)
{
    equal(creme.object.isempty(select), false);

    if (creme.object.isempty(select))
        return;

    equal(select.creme().isActive(), true);
    equal(select.creme().widget().cleanedval(), value);
    deepEqual(select.creme().widget().dependencies(), dependencies);
    equal(select.creme().widget().popupURL(), url);
}

module("creme.widgets.chainedselect.js", {
  setup: function() {
      this.backend = new MockAjaxBackend({sync:true});
      $.extend(this.backend.GET, {'mock/entity/label/123': this.backend.response(200, [['John Doe']]),
                                  'mock/entity/label/456': this.backend.response(200, [['Bean Bandit']]),
                                  'mock/popup': this.backend.response(200, MOCK_FRAME_CONTENT),
                                  'mock/options': this.backend.response(200, [[15, 'a'], [5, 'b'], [3, 'c'], [14, 't'], [42, 'y']]),
                                  'mock/rtype/1/options': this.backend.response(200, [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]),
                                  'mock/rtype/5/options': this.backend.response(200, [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]),
                                  'mock/rtype/15/options': this.backend.response(200, [['rtype.12', 'b'], ['rtype.2', 'e']]),
                                  'mock/entity/rtype.12/15/options': this.backend.response(200, [['123', 'John Doe'], ['456', 'Bean Bandit']]),
                                  'mock/entity/rtype.22/5/options': this.backend.response(200, [['456', 'Bean Bandit'], ['789', 'Mini May']]),
                                  'mock/options/empty': this.backend.response(200, []),
                                  'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                  'mock/error': this.backend.response(500, 'HTTP - Error 500')});

      creme.widget.unregister('ui-creme-entityselector');
      creme.widget.declare('ui-creme-entityselector', new MockEntitySelector(this.backend));

      creme.widget.unregister('ui-creme-dselect');
      creme.widget.declare('ui-creme-dselect', new MockDynamicSelect(this.backend));
  },
  teardown: function() {
  }
});


test('creme.widgets.chainedselect.create (empty, no selector)', function() {
    var element = mock_chainedselect_create();
    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), $.toJSON({}));
    equal(widget.selectors().length, 0);
    equal(widget.selector('ctype').length, 0);
});

test('creme.widgets.chainedselect.create (empty, single selector, static)', function() {
    var element = mock_chainedselect_create();
    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    mock_chainedselect_add(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(widget.val(), $.toJSON({ctype: '15'}));
    equal(widget.selectors().length, 1);

    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    equal(widget.selector('unknown').length, 0);
});

test('creme.widgets.chainedselect.create (empty, single selector, static, <div>)', function() {
    var element = mock_chainedselect_create();
    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    mock_chainedselect_add_div(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(widget.val(), $.toJSON({ctype: '15'}));
    equal(widget.selectors().length, 1);

    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    equal(widget.selector('unknown').length, 0);
});

test('creme.widgets.chainedselect.create (empty, single selector, url)', function() {
    var element = mock_chainedselect_create();
    var ctype = mock_dselect_create('mock/options');

    mock_chainedselect_add(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(widget.val(), $.toJSON({ctype: '15'}));
    equal(widget.selectors().length, 1);

    assertDSelectAt(widget, 'ctype', '15', [], 'mock/options', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['14', 't'], ['42', 'y']]);

    equal(widget.selector('unknown').length, 0);
});

test('creme.widgets.chainedselect.create (empty, multi selector)', function() {
    var element = mock_chainedselect_create();

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    var rtype = mock_dselect_create();
    mock_dselect_add_choice(rtype, 'd', 1);
    mock_dselect_add_choice(rtype, 'e', 6);

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '15', rtype: '1'}));
    equal(widget.selectors().length, 2);

    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', '1', [], '', [['1', 'd'], ['6', 'e']]);
});

test('creme.widgets.chainedselect.create (empty, multi selector, single dependency)', function() {
    var element = mock_chainedselect_create();

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '15', rtype: 'rtype.12'}));
    equal(widget.selectors().length, 2);

    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);
});

test('creme.widgets.chainedselect.create (empty, multi selector, multiple dependency)', function() {
    var element = mock_chainedselect_create();

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');
    var entity = mock_dselect_create('mock/entity/${rtype}/${ctype}/options');

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);
    mock_chainedselect_add(element, 'entity', entity);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '15', rtype: 'rtype.12', entity: '123'}));
    equal(widget.selectors().length, 3);

    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);
    assertDSelectAt(widget, 'entity', '123', ['rtype', 'ctype'], 'mock/entity/rtype.12/15/options', [['123', 'John Doe'], ['456', 'Bean Bandit']]);
});


test('creme.widgets.chainedselect.create (empty, multi selector, duplicates)', function() {
    var element = mock_chainedselect_create();

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    var rtype = mock_dselect_create();
    mock_dselect_add_choice(rtype, 'd', 1);
    mock_dselect_add_choice(rtype, 'e', 6);

    var rtype2 = mock_dselect_create();
    mock_dselect_add_choice(rtype2, 'f', 12.5);
    mock_dselect_add_choice(rtype2, 'g', 14.78);

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);
    mock_chainedselect_add(element, 'rtype', rtype2);

    var widget = creme.widget.create(element);

    // use last one as value
    equal(widget.val(), $.toJSON({ctype: '15', rtype: '12.5'}));
    equal(widget.selectors().length, 3);

    equal(widget.selector('ctype').length, 1);
    equal(widget.selector('ctype').creme().widget().val(), '15');
    deepEqual(widget.selector('ctype').creme().widget().dependencies(), []);

    equal(widget.selector('rtype').length, 1);

    equal(widget.selector('rtype').creme().widget().val(), '12.5');
    deepEqual(widget.selector('rtype').creme().widget().dependencies(), []);
});

// TODO : implement detection of cross dependencies
/*
test('creme.widgets.chainedselect.create (multi selector, cross dependencies)', function() {

});
*/

test('creme.widgets.chainedselect.create (valid, no selector)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype:'12'}));
    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), $.toJSON({ctype:'12'}));
    equal(widget.selectors().length, 0);
    equal(widget.selector('ctype').length, 0);
});

test('creme.widgets.chainedselect.create (valid, single selector, static)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype:'5'}));
    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    mock_chainedselect_add(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '5'}));
    equal(widget.selectors().length, 1);

    assertDSelectAt(widget, 'ctype', '5', [], '',
                  [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

test('creme.widgets.chainedselect.create (unknown choice, single selector, static)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype:'54'}));
    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    mock_chainedselect_add(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '15'}));
    equal(widget.selectors().length, 1);

    assertDSelectAt(widget, 'ctype', '15', [], '',
                  [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

test('creme.widgets.chainedselect.create (valid, single selector, url)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype:'14'}));
    var ctype = mock_dselect_create('mock/options');

    mock_chainedselect_add(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '14'}));
    equal(widget.selectors().length, 1);

    assertDSelectAt(widget, 'ctype', '14', [], 'mock/options',
                  [['15', 'a'], ['5', 'b'], ['3', 'c'], ['14', 't'], ['42', 'y']]);
});

test('creme.widgets.chainedselect.create (valid, multi selector, static)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '3', rtype: '6'}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    var rtype = mock_dselect_create();
    mock_dselect_add_choice(rtype, 'd', 1);
    mock_dselect_add_choice(rtype, 'e', 6);

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '3', rtype: '6'}));
    equal(widget.selectors().length, 2);

    assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);
});

test('creme.widgets.chainedselect.create (unknown choice, multi selector, static)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '3', rtype: '46'}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    var rtype = mock_dselect_create();
    mock_dselect_add_choice(rtype, 'd', 1);
    mock_dselect_add_choice(rtype, 'e', 6);

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '3', rtype: '1'}));
    equal(widget.selectors().length, 2);

    assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', '1', [], '', [['1', 'd'], ['6', 'e']]);
});

test('creme.widgets.chainedselect.create (valid, multi selector, single dependency)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '1', rtype: 'rtype.3'}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);
    mock_dselect_add_choice(ctype, 'd', 1);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '1', rtype: 'rtype.3'}));
    equal(widget.selectors().length, 2);

    assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);

    assertDSelectAt(widget, 'rtype', 'rtype.3', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);
});

test('creme.widgets.chainedselect.create (valid, multi selector, multi dependencies)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '5', rtype: 'rtype.22', entity: '789'}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');
    var entity = mock_dselect_create('mock/entity/${rtype}/${ctype}/options');

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);
    mock_chainedselect_add(element, 'entity', entity);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.22', entity: '789'}));
    equal(widget.selectors().length, 3);

    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);

    assertDSelectAt(widget, 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);
});

test('creme.widgets.chainedselect.val (single selector)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype:'5'}));
    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    mock_chainedselect_add(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '5'}));
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    widget.val({ctype: '3'})
    equal(widget.val(), $.toJSON({ctype: '3'}));
    assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    widget.val({ctype: '42'})
    equal(widget.val(), $.toJSON({ctype: '15'}));
    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

test('creme.widgets.chainedselect.val (multi selector, static)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '5', rtype: '6'}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    var rtype = mock_dselect_create();
    mock_dselect_add_choice(rtype, 'd', 1);
    mock_dselect_add_choice(rtype, 'e', 6);
    mock_dselect_add_choice(rtype, 'f', 42);

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '5', rtype: '6'}));
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', '6', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);

    widget.val({ctype: '3', rtype: '42'});
    equal(widget.val(), $.toJSON({ctype: '3', rtype: '42'}));
    assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', '42', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);

    widget.val({ctype: '59', rtype: '1'});
    equal(widget.val(), $.toJSON({ctype: '15', rtype: '1'}));
    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', '1', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);
});

test('creme.widgets.chainedselect.val (multi selector, single dependency)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '1', rtype: 'rtype.3'}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);
    mock_dselect_add_choice(ctype, 'd', 1);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '1', rtype: 'rtype.3'}), 'initial value');
    assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.3', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);

    widget.val({ctype: '5', rtype: 'rtype.22'});
    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.22'}), 'updated value');
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);

    widget.val({ctype: '59', rtype: 'rtype.22'});
    equal(widget.val(), $.toJSON({ctype: '15', rtype: 'rtype.12'}), 'invalid ctype');
    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);

    widget.val({ctype: '1', rtype: 'rtype.55'});
    equal(widget.val(), $.toJSON({ctype: '1', rtype: 'rtype.1'}), 'invalid rtype');
    assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.1', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);
});

test('creme.widgets.chainedselect.val (multi selector, multiple dependencies)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '1', rtype: 'rtype.3', entity: null}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);
    mock_dselect_add_choice(ctype, 'd', 1);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');
    var entity = mock_dselect_create('mock/entity/${rtype}/${ctype}/options');

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);
    mock_chainedselect_add(element, 'entity', entity);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '1', rtype: 'rtype.3', entity: null}), 'initial value');
    assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.3', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);
    assertDSelectAt(widget, 'entity', null, ['rtype', 'ctype'], 'mock/entity/rtype.3/1/options', []);

    widget.val({ctype: '5', rtype: 'rtype.22', entity: '789'})
    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.22', entity: '789'}), 'updated value');
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    assertDSelectAt(widget, 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);

    widget.val({ctype: '59', rtype: 'rtype.22', entity: '789'});
    equal(widget.val(), $.toJSON({ctype: '15', rtype: 'rtype.12', entity: '123'}), 'invalid ctype');
    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);
    assertDSelectAt(widget, 'entity', '123', ['rtype', 'ctype'], 'mock/entity/rtype.12/15/options', [['123', 'John Doe'], ['456', 'Bean Bandit']]);

    widget.val({ctype: '5', rtype: 'rtype.489', entity: '789'});
    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.7', entity: null}), 'invalid rtype');
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.7', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    assertDSelectAt(widget, 'entity', null, ['rtype', 'ctype'], 'mock/entity/rtype.7/5/options', []);

    widget.val({ctype: '5', rtype: 'rtype.22', entity: '007'});
    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.22', entity: '456'}), 'invalid entity');
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    assertDSelectAt(widget, 'entity', '456', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);
});

test('creme.widgets.chainedselect.val (multi selector, multiple dependencies, entity selector)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '1', rtype: 'rtype.3', entity: null}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);
    mock_dselect_add_choice(ctype, 'd', 1);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');
    var entity = mock_entityselector_create({labelURL:'mock/label',
                                             popupURL:'mock/entity/${rtype}/${ctype}/popup'});

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);
    mock_chainedselect_add(element, 'entity', entity);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '1', rtype: 'rtype.3', entity: null}), 'initial value');
    assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.3', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);
    assertEntitySelect(widget.selector('entity'), null, ['rtype', 'ctype'], 'mock/entity/rtype.3/1/popup');

    widget.val({ctype: '5', rtype: 'rtype.22', entity: '789'})
    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.22', entity: '789'}), 'updated value');
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    assertEntitySelect(widget.selector('entity'), '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/popup');

    widget.val({ctype: '59', rtype: 'rtype.22', entity: '789'});
    equal(widget.val(), $.toJSON({ctype: '15', rtype: 'rtype.12', entity: '789'}), 'invalid ctype');
    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);
    assertEntitySelect(widget.selector('entity'), '789', ['rtype', 'ctype'], 'mock/entity/rtype.12/15/popup');

    widget.val({ctype: '5', rtype: 'rtype.489', entity: '789'});
    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.7', entity: '789'}), 'invalid rtype');
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.7', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    assertEntitySelect(widget.selector('entity'), '789', ['rtype', 'ctype'], 'mock/entity/rtype.7/5/popup');

    widget.val({ctype: '5', rtype: 'rtype.22', entity: '007'});
    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.22', entity: '007'}), 'invalid entity');
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    assertEntitySelect(widget.selector('entity'), '007', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/popup');
});

test('creme.widgets.chainedselect.change (single selector)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype:'5'}));
    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    mock_chainedselect_add(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '5'}));
    equal(5, ctype.creme().widget().val());

    ctype.creme().widget().val(15);
    equal(widget.val(), $.toJSON({ctype: '15'}));
    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    ctype.creme().widget().val(null);
    equal(widget.val(), $.toJSON({ctype: '15'}));
    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

test('creme.widgets.chainedselect.change (multi selector, static)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '5', rtype: '6'}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    var rtype = mock_dselect_create();
    mock_dselect_add_choice(rtype, 'd', 1);
    mock_dselect_add_choice(rtype, 'e', 6);
    mock_dselect_add_choice(rtype, 'f', 42);

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '5', rtype: '6'}));
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', '6', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);

    ctype.creme().widget().val(3);
    equal(widget.val(), $.toJSON({ctype: '3', rtype: '6'}));
    assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', '6', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);

    rtype.creme().widget().val(42);
    equal(widget.val(), $.toJSON({ctype: '3', rtype: '42'}));
    assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', '42', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);

    ctype.creme().widget().val(15);
    rtype.creme().widget().val(6);
    equal(widget.val(), $.toJSON({ctype: '15', rtype: '6'}));
    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', '6', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);
});

test('creme.widgets.chainedselect.change (multi selector, single dependency)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '1', rtype: 'rtype.3'}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);
    mock_dselect_add_choice(ctype, 'd', 1);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '1', rtype: 'rtype.3'}), 'initial value');
    assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.3', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);

    ctype.creme().widget().val(3);
    equal(widget.val(), $.toJSON({ctype: '3', rtype: null}), 'updated ctype, no rtype');
    assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);

    ctype.creme().widget().val(5);
    rtype.creme().widget().val('rtype.22');
    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.22'}), 'updated ctype and rtype');
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
});

test('creme.widgets.chainedselect.change (multi selector, multiple dependencies)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '1', rtype: 'rtype.3', entity: null}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);
    mock_dselect_add_choice(ctype, 'd', 1);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');
    var entity = mock_dselect_create('mock/entity/${rtype}/${ctype}/options');

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);
    mock_chainedselect_add(element, 'entity', entity);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '1', rtype: 'rtype.3', entity: null}), 'initial value');
    assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.3', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);
    assertDSelectAt(widget, 'entity', null, ['rtype', 'ctype'], 'mock/entity/rtype.3/1/options', []);

    ctype.creme().widget().val(3);
    equal(widget.val(), $.toJSON({ctype: '3', rtype: null, entity: null}), 'updated ctype, no rtype, no entity');
    assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);
    assertDSelectAt(widget, 'entity', null, ['rtype', 'ctype'], 'mock/entity/null/3/options', []);

    ctype.creme().widget().val(5);
    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.7', entity: null}), 'updated ctype');
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.7', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    assertDSelectAt(widget, 'entity', null, ['rtype', 'ctype'], 'mock/entity/rtype.7/5/options', []);

    rtype.creme().widget().val('rtype.22');
    entity.creme().widget().val(789);
    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.22', entity: '789'}), 'updated ctype');
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    assertDSelectAt(widget, 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);
});


test('creme.widgets.chainedselect.reset (single selector)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype:'5'}));
    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    mock_chainedselect_add(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '5'}), 'initial value');
    equal(5, ctype.creme().widget().val());

    widget.reset();

    equal(widget.val(), $.toJSON({ctype: '15'}), 'reset value');
    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

test('creme.widgets.chainedselect.reset (multi selector, static)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '3', rtype: '42'}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    var rtype = mock_dselect_create();
    mock_dselect_add_choice(rtype, 'd', 1);
    mock_dselect_add_choice(rtype, 'e', 6);
    mock_dselect_add_choice(rtype, 'f', 42);

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '3', rtype: '42'}));
    assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', '42', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);

    widget.reset();

    equal(widget.val(), $.toJSON({ctype: '15', rtype: '1'}), 'reset value');
    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget, 'rtype', '1', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);
});

test('creme.widgets.chainedselect.reset (multi selector, single dependency)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '5', rtype: 'rtype.22'}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);
    mock_dselect_add_choice(ctype, 'd', 1);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.22'}), 'updated ctype and rtype');
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);

    widget.reset();

    equal(widget.val(), $.toJSON({ctype: '15', rtype: 'rtype.12'}), 'initial value');
    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);
});

test('creme.widgets.chainedselect.reset (multi selector, multiple dependencies)', function() {
    var element = mock_chainedselect_create($.toJSON({ctype: '5', rtype: 'rtype.22', entity: '789'}));

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);
    mock_dselect_add_choice(ctype, 'd', 1);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');
    var entity = mock_dselect_create('mock/entity/${rtype}/${ctype}/options');

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);
    mock_chainedselect_add(element, 'entity', entity);

    var widget = creme.widget.create(element);

    equal(widget.val(), $.toJSON({ctype: '5', rtype: 'rtype.22', entity: '789'}), 'updated ctype');
    assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    assertDSelectAt(widget, 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);

    widget.reset();

    equal(widget.val(), $.toJSON({ctype: '15', rtype: 'rtype.12', entity: '123'}), 'initial value');
    assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);
    assertDSelectAt(widget, 'entity', '123', ['rtype', 'ctype'], 'mock/entity/rtype.12/15/options', [['123', 'John Doe'], ['456', 'Bean Bandit']]);
});
