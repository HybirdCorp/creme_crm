function mock_selectorlist_create(value, noauto, options)
{
    var element = creme.widget.buildTag($('<div/>'), 'ui-creme-selectorlist', options, !noauto)
                       .append('<input type="hidden" class="ui-creme-input ui-creme-selectorlist"/>')
                       .append('<div class="inner-selector-model" style="display:none;"/>')
                       .append('<ul class="selectors ui-layout"/>')
                       .append('<div class="add"/>');

    if (value !== undefined) {
        $('input.ui-creme-input', element).val(value);
    }

    return element;
}

function mock_selectorlist_model(element, selector, widget, options)
{
    var selector = creme.widget.buildTag(selector, widget, options, false);
    $('.inner-selector-model', element).append(selector);
    return selector;
}

function mock_ctype_model()
{
    var model = mock_dselect_create();

    mock_dselect_add_choice(model, 'a', 15);
    mock_dselect_add_choice(model, 'b', 5);
    mock_dselect_add_choice(model, 'c', 3);

    return ctype;
}

function mock_ctype_rtype_model()
{
    var model = mock_chainedselect_create();

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    var rtype = mock_dselect_create();
    mock_dselect_add_choice(rtype, 'd', 1);
    mock_dselect_add_choice(rtype, 'e', 6);

    mock_chainedselect_add(model, 'ctype', ctype);
    mock_chainedselect_add(model, 'rtype', rtype);

    return model;
}

module("creme.widgets.selectorlist.js", {
  setup: function() {
      this.backend = new creme.ajax.MockAjaxBackend({sync:true});
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

      creme.widget.unregister('ui-creme-chainedselect');
      creme.widget.declare('ui-creme-chainedselect', new MockChainedSelect(this.backend));
  },
  teardown: function() {
  }
});

test('creme.widets.selectorlist.create (empty, no model)', function() {
    var element = mock_selectorlist_create();
    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 0);
    equal(widget.lastSelector().length, 0);
    equal(widget.selectors().length, 0);
});

test('creme.widets.selectorlist.create (empty, model)', function() {
    var element = mock_selectorlist_create();
    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    mock_selectorlist_model(element, ctype);

    var widget = creme.widget.create(element);
    equal(widget.delegate._enabled, true);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 1);
    equal(widget.lastSelector().length, 0);
    equal(widget.selectors().length, 0);

    equal(widget.selectorModel().creme().isActive(), false);
});

test('creme.widets.selectorlist.create (empty, model, disabled)', function() {
    var element = mock_selectorlist_create('', false, {disabled: ''});
    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_selectorlist_model(element, ctype);

    equal(element.is('[disabled]'), true);

    var widget = creme.widget.create(element);

    equal(element.is('[disabled]'), true);
    equal(widget.delegate._enabled, false);

    var element = mock_selectorlist_create();
    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_selectorlist_model(element, ctype);

    equal(element.is('[disabled]'), false);

    var widget = creme.widget.create(element, {disabled: true});

    equal(element.is('[disabled]'), true);
    equal(widget.delegate._enabled, false);
});

test('creme.widets.selectorlist.create (empty, chained selector)', function() {
    var element = mock_selectorlist_create();
    var model = mock_chainedselect_create();

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    var rtype = mock_dselect_create();
    mock_dselect_add_choice(rtype, 'd', 1);
    mock_dselect_add_choice(rtype, 'e', 6);

    mock_chainedselect_add(element, 'ctype', ctype);
    mock_chainedselect_add(element, 'rtype', rtype);

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 1);
    equal(widget.lastSelector().length, 0);
    equal(widget.selectors().length, 0);
});

test('creme.widets.selectorlist.create (value, no selector)', function() {
    var element = mock_selectorlist_create($.toJSON([{ctype: '12', rtype:'rtype.3'}]));
    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), $.toJSON([{ctype: '12', rtype:'rtype.3'}]));
    equal(widget.selectorModel().length, 0);
    equal(widget.lastSelector().length, 0);
    equal(widget.selectors().length, 0);
});

test('creme.widets.selectorlist.create (value, static selector)', function() {
    var element = mock_selectorlist_create($.toJSON([3, 5, 3, 15]));
    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    mock_selectorlist_model(element, ctype);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([3, 5, 3, 15]));
    equal(widget.selectorModel().length, 1);

    equal(widget.lastSelector().length, 1);
    assertDSelect(widget.lastSelector(), '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    equal(widget.selectors().length, 4);

    assertDSelect(widget.selector(0), '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelect(widget.selector(1), '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelect(widget.selector(2), '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelect(widget.selector(3), '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

test('creme.widets.selectorlist.create (value, chained selector)', function() {
    var element = mock_selectorlist_create($.toJSON([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    var model = mock_ctype_rtype_model();

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);

    equal(widget.lastSelector().length, 1);

    assertDSelectAt(widget.lastSelector().creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.lastSelector().creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    equal(widget.selectors().length, 3);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '1', [], '', [['1', 'd'], ['6', 'e']]);

    assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    assertDSelectAt(widget.selector(2).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(2).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);
});

test('creme.widets.selectorlist.create (invalid value, multiple dependencies)', function() {
    var element = mock_selectorlist_create($.toJSON([{ctype: '3', rtype: 'rtype.3', entity: null}]));
    var model = mock_chainedselect_create();

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);
    mock_dselect_add_choice(ctype, 'd', 1);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');
    var entity = mock_dselect_create('mock/entity/${rtype}/${ctype}/options');

    mock_chainedselect_add(model, 'ctype', ctype);
    mock_chainedselect_add(model, 'rtype', rtype);
    mock_chainedselect_add(model, 'entity', entity);

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([{ctype: '3', rtype: null, entity: null}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 1);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);
    assertDSelectAt(widget.selector(0).creme().widget(), 'entity', null, ['rtype', 'ctype'], 'mock/entity/null/3/options', []);
});

test('creme.widets.selectorlist.value (value, no selector)', function() {
    var element = mock_selectorlist_create();
    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 0);
    equal(widget.lastSelector().length, 0);
    equal(widget.selectors().length, 0);

    widget.val($.toJSON([{ctype: '12', rtype:'rtype.3'}]));
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 0);
    equal(widget.lastSelector().length, 0);
    equal(widget.selectors().length, 0);

    widget.val([{ctype: '12', rtype:'rtype.3'}]);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 0);
    equal(widget.lastSelector().length, 0);
    equal(widget.selectors().length, 0);
});

test('creme.widets.selectorlist.value (value, static selector)', function() {
    var element = mock_selectorlist_create();
    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);

    mock_selectorlist_model(element, ctype);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 1);
    equal(widget.lastSelector().length, 0);
    equal(widget.selectors().length, 0);

    widget.val($.toJSON([3, 5, 3, 15]));
    equal(widget.lastSelector().length, 1);
    equal(widget.selectors().length, 4);

    assertDSelect(widget.selector(0), '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelect(widget.selector(1), '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelect(widget.selector(2), '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelect(widget.selector(3), '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    widget.val([5, 15]);
    equal(widget.lastSelector().length, 1);
    equal(widget.selectors().length, 2);

    assertDSelect(widget.selector(0), '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelect(widget.selector(1), '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    widget.val($.toJSON([]));
    equal(widget.lastSelector().length, 0);
    equal(widget.selectors().length, 0);
});

test('creme.widets.selectorlist.value (value, single dependency)', function() {
    var element = mock_selectorlist_create($.toJSON([]));
    var model = mock_chainedselect_create();

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);
    mock_dselect_add_choice(ctype, 'd', 1);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');

    mock_chainedselect_add(model, 'ctype', ctype);
    mock_chainedselect_add(model, 'rtype', rtype);

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 0);

    widget.val([{ctype: '3', rtype: 'rtype.3'}, {ctype: '5', rtype: 'rtype.22'}]);
    equal(widget.val(), $.toJSON([{ctype: '3', rtype: null}, {ctype: '5', rtype: 'rtype.22'}]));
    equal(widget.selectors().length, 2);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);

    assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);

    widget.val([{ctype: '5', rtype: 'rtype.7'}]);
    equal(widget.val(), $.toJSON([{ctype: '5', rtype: 'rtype.7'}]));
    equal(widget.selectors().length, 1);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', 'rtype.7', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);

    widget.val([]);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectors().length, 0);
});

test('creme.widets.selectorlist.value (value, multiple dependencies)', function() {
    var element = mock_selectorlist_create($.toJSON([]));
    var model = mock_chainedselect_create();

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);
    mock_dselect_add_choice(ctype, 'd', 1);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');
    var entity = mock_dselect_create('mock/entity/${rtype}/${ctype}/options');

    mock_chainedselect_add(model, 'ctype', ctype);
    mock_chainedselect_add(model, 'rtype', rtype);
    mock_chainedselect_add(model, 'entity', entity);

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 0);

    widget.val([{ctype: '3', rtype: 'rtype.3', entity: null}, {ctype: '5', rtype: 'rtype.22', entity: '789'}]);
    equal(widget.val(), $.toJSON([{ctype: '3', rtype: null, entity: null}, {ctype: '5', rtype: 'rtype.22', entity: '789'}]));
    equal(widget.selectors().length, 2);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);
    assertDSelectAt(widget.selector(0).creme().widget(), 'entity', null, ['rtype', 'ctype'], 'mock/entity/null/3/options', []);

    assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    assertDSelectAt(widget.selector(1).creme().widget(), 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);

    widget.val([{ctype: '5', rtype: 'rtype.7', entity: '789'}]);
    equal(widget.val(), $.toJSON([{ctype: '5', rtype: 'rtype.7', entity: null}]));
    equal(widget.selectors().length, 1);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', 'rtype.7', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'entity', null, ['rtype', 'ctype'], 'mock/entity/rtype.7/5/options', []);

    widget.val([]);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectors().length, 0);
});

test('creme.widets.selectorlist.append (empty)', function() {
    var element = mock_selectorlist_create($.toJSON([]));
    var model = mock_ctype_rtype_model();

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 0);

    var last = widget.appendSelector();
    notEqual(last, undefined);

    equal(widget.val(), $.toJSON([{ctype: '15', rtype: '1'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 1);
    equal(widget.selectors().creme().widget().val(), $.toJSON({ctype: '15', rtype: '1'}));

    deepEqual(widget.selector(0).creme().widget(), last.creme().widget());
});

test('creme.widets.selectorlist.append (not empty)', function() {
    var element = mock_selectorlist_create($.toJSON([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    var model = mock_ctype_rtype_model();

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 3);

    var last = widget.appendSelector();
    notEqual(last, undefined);

    equal(widget.val(), $.toJSON([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}, {ctype: '15', rtype: '1'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 4);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '1', [], '', [['1', 'd'], ['6', 'e']]);

    assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    assertDSelectAt(widget.selector(2).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(2).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    assertDSelectAt(widget.selector(3).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(3).creme().widget(), 'rtype', '1', [], '', [['1', 'd'], ['6', 'e']]);
});

test('creme.widets.selectorlist.append (not empty, value)', function() {
    var element = mock_selectorlist_create($.toJSON([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    var model = mock_ctype_rtype_model();

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 3);

    var last = widget.appendSelector({ctype: '3', rtype: '6'});
    notEqual(last, undefined);

    equal(widget.val(), $.toJSON([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}, {ctype: '3', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 4);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '1', [], '', [['1', 'd'], ['6', 'e']]);

    assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    assertDSelectAt(widget.selector(2).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(2).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    assertDSelectAt(widget.selector(3).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(3).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);
});

test('creme.widets.selectorlist.append (not empty, multiple dependencies, value)', function() {
    var element = mock_selectorlist_create($.toJSON([{ctype: '3', rtype: 'rtype.3', entity: null}]));
    var model = mock_chainedselect_create();

    var ctype = mock_dselect_create();
    mock_dselect_add_choice(ctype, 'a', 15);
    mock_dselect_add_choice(ctype, 'b', 5);
    mock_dselect_add_choice(ctype, 'c', 3);
    mock_dselect_add_choice(ctype, 'd', 1);

    var rtype = mock_dselect_create('mock/rtype/${ctype}/options');
    var entity = mock_dselect_create('mock/entity/${rtype}/${ctype}/options');

    mock_chainedselect_add(model, 'ctype', ctype);
    mock_chainedselect_add(model, 'rtype', rtype);
    mock_chainedselect_add(model, 'entity', entity);

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([{ctype: '3', rtype: null, entity: null}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 1);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);
    assertDSelectAt(widget.selector(0).creme().widget(), 'entity', null, ['rtype', 'ctype'], 'mock/entity/null/3/options', []);

    var last = widget.appendSelector({ctype: '5', rtype: 'rtype.22', entity: '789'});
    notEqual(last, undefined);

    equal(widget.val(), $.toJSON([{ctype: '3', rtype: null, entity: null}, {ctype: '5', rtype: 'rtype.22', entity: '789'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 2);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);
    assertDSelectAt(widget.selector(0).creme().widget(), 'entity', null, ['rtype', 'ctype'], 'mock/entity/null/3/options', []);

    assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    assertDSelectAt(widget.selector(1).creme().widget(), 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);
});

test('creme.widets.selectorlist.removeAt (empty)', function() {
    var element = mock_selectorlist_create($.toJSON([]));
    var model = mock_ctype_rtype_model();

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 0);

    var removed = widget.removeSelectorAt(0);
    equal(removed, undefined);

    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 0);
});

test('creme.widets.selectorlist.removeAt (not empty)', function() {
    var element = mock_selectorlist_create($.toJSON([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    var model = mock_ctype_rtype_model();

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 3);

    var removed = widget.removeSelectorAt(0);
    notEqual(removed, undefined);

    equal(widget.val(), $.toJSON([{ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 2);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    widget.removeSelectorAt(1);
    equal(widget.val(), $.toJSON([{ctype: '15', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 1);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);
});

test('creme.widets.selectorlist.remove (empty)', function() {
    var element = mock_selectorlist_create($.toJSON([]));
    var model = mock_ctype_rtype_model();

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 0);

    var removed = widget.removeSelector(undefined);
    equal(removed, undefined);

    equal(widget.val(), $.toJSON([]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 0);
});

test('creme.widets.selectorlist.remove (not empty)', function() {
    var element = mock_selectorlist_create($.toJSON([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    var model = mock_ctype_rtype_model();

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 3);

    var removed = widget.removeSelector(widget.selector(0));
    notEqual(removed, undefined);

    equal(widget.val(), $.toJSON([{ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 2);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    widget.removeSelector(widget.selector(1));
    equal(widget.val(), $.toJSON([{ctype: '15', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 1);

    assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);
});

test('creme.widets.selectorlist.appendLast (not empty)', function() {
    var element = mock_selectorlist_create($.toJSON([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}]));
    var model = mock_ctype_rtype_model();

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element, {cloneLast: true});
    equal(widget.val(), $.toJSON([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 2);

    var last = widget.appendLastSelector();
    notEqual(last, undefined);

    equal(widget.val(), $.toJSON([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 3);
});

test('creme.widets.selectorlist.appendLast (not empty, no clone last)', function() {
    var element = mock_selectorlist_create($.toJSON([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}]));
    var model = mock_ctype_rtype_model();

    mock_selectorlist_model(element, model);

    var widget = creme.widget.create(element);
    equal(widget.val(), $.toJSON([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 2);

    var last = widget.appendLastSelector();
    notEqual(last, undefined);

    equal(widget.val(), $.toJSON([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}, {ctype: '15', rtype: '1'}]));
    equal(widget.selectorModel().length, 1);
    equal(widget.selectors().length, 3);
});
