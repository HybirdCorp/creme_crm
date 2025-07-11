/* globals QUnitWidgetMixin */

(function($) {

var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';

QUnit.module("creme.widget.selectorlist.js", new QUnitMixin(QUnitAjaxMixin, QUnitEventMixin, QUnitWidgetMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.widget.selectorlist.js'});
    },

    beforeEach: function() {
        this.setMockBackendGET({
            'mock/entity/label/123': this.backend.response(200, [['John Doe']]),
            'mock/entity/label/456': this.backend.response(200, [['Bean Bandit']]),
            'mock/popup': this.backend.response(200, MOCK_FRAME_CONTENT),
            'mock/options': this.backend.responseJSON(200, [[15, 'a'], [5, 'b'], [3, 'c'], [14, 't'], [42, 'y']]),
            'mock/rtype/1/options': this.backend.responseJSON(200, [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]),
            'mock/rtype/5/options': this.backend.responseJSON(200, [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]),
            'mock/rtype/15/options': this.backend.responseJSON(200, [['rtype.12', 'b'], ['rtype.2', 'e']]),
            'mock/entity/rtype.12/15/options': this.backend.responseJSON(200, [['123', 'John Doe'], ['456', 'Bean Bandit']]),
            'mock/entity/rtype.22/5/options': this.backend.responseJSON(200, [['456', 'Bean Bandit'], ['789', 'Mini May']]),
            'mock/options/empty': this.backend.responseJSON(200, []),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500')
        });
    },

    afterEach: function() {
        $('.ui-dialog-content').dialog('destroy');
        creme.widget.shutdown($('body'));
    },

    createSelectorListTag: function(value, noauto, options) {
        var html = (
            '<div class="ui-creme-widget ui-creme-selectorlist ${auto}" ${attrs} widget="ui-creme-selectorlist">' +
                '<input type="hidden" class="ui-creme-input ui-creme-selectorlist" value="${value}"/>' +
                '<div class="inner-selector-model" style="display:none;"/>' +
                '<ul class="selectors ui-layout"/>' +
                '<div class="add"/>' +
            '</div>'
        ).template({
            auto: !noauto ? 'widget-auto' : '',
            value: (Object.isNone(value) ? '' : String(value)).escapeHTML(),
            attrs: this.htmlAttrs(options)
        });

        return $(html);
    },

    appendSelectorListModelTag: function(element, selector, widget, options) {
        var selectorTag = this.fillWidgetTag(selector, {
            widget: widget,
            attrs: options,
            auto: false
        });
        $('.inner-selector-model', element).append(selectorTag);
        return selectorTag;
    },

    createCTypeSelectTag: function() {
        var model = this.createDynamicSelectTag();

        this.appendOptionTag(model, 'a', 15);
        this.appendOptionTag(model, 'b', 5);
        this.appendOptionTag(model, 'c', 3);

        return model;
    },

    createCTypeRTypeSelectorTag: function() {
        var model = this.createChainedSelectTag();

        var ctype = this.createDynamicSelectTag();
        this.appendOptionTag(ctype, 'a', 15);
        this.appendOptionTag(ctype, 'b', 5);
        this.appendOptionTag(ctype, 'c', 3);

        var rtype = this.createDynamicSelectTag();
        this.appendOptionTag(rtype, 'd', 1);
        this.appendOptionTag(rtype, 'e', 6);

        this.appendChainedSelectorTag(model, 'ctype', ctype);
        this.appendChainedSelectorTag(model, 'rtype', rtype);

        return model;
    }
}));

QUnit.test('creme.widgets.selectorlist.create (empty, no model)', function(assert) {
    var element = this.createSelectorListTag();
    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 0);
    assert.equal(widget.lastSelector().length, 0);
    assert.equal(widget.selectors().length, 0);
});

QUnit.test('creme.widgets.selectorlist.create (empty, model)', function(assert) {
    var element = this.createSelectorListTag();
    var ctype = this.createDynamicSelectTag();
    this.appendOptionTag(ctype, 'a', 15);
    this.appendOptionTag(ctype, 'b', 5);
    this.appendOptionTag(ctype, 'c', 3);

    this.appendSelectorListModelTag(element, ctype);

    var widget = creme.widget.create(element);
    assert.equal(widget.delegate._enabled, true);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.lastSelector().length, 0);
    assert.equal(widget.selectors().length, 0);

    assert.equal(widget.selectorModel().creme().isActive(), false);
});

QUnit.test('creme.widgets.selectorlist.create (empty, model, [disabled])', function(assert) {
    var element = this.createSelectorListTag('', false, {disabled: ''});
    var ctype = this.createDynamicSelectTag();
    this.appendOptionTag(ctype, 'a', 15);
    this.appendSelectorListModelTag(element, ctype);

    assert.equal(element.is('[disabled]'), true);

    var widget = creme.widget.create(element);

    assert.equal(element.is('[disabled]'), true);
    assert.equal(widget.delegate._enabled, false);
});

QUnit.test('creme.widgets.selectorlist.create (empty, model, {disabled: true})', function(assert) {
    var element = this.createSelectorListTag();
    var ctype = this.createDynamicSelectTag();
    this.appendOptionTag(ctype, 'a', 15);
    this.appendSelectorListModelTag(element, ctype);

    assert.equal(element.is('[disabled]'), false);

    var widget = creme.widget.create(element, {disabled: true});

    assert.equal(element.is('[disabled]'), true);
    assert.equal(widget.delegate._enabled, false);
});

QUnit.test('creme.widgets.selectorlist.create (empty, chained selector)', function(assert) {
    var element = this.createSelectorListTag();
    var model = this.createChainedSelectTag();

    var ctype = this.createDynamicSelectTag();
    this.appendOptionTag(ctype, 'a', 15);
    this.appendOptionTag(ctype, 'b', 5);
    this.appendOptionTag(ctype, 'c', 3);

    var rtype = this.createDynamicSelectTag();
    this.appendOptionTag(rtype, 'd', 1);
    this.appendOptionTag(rtype, 'e', 6);

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.lastSelector().length, 0);
    assert.equal(widget.selectors().length, 0);
});

QUnit.test('creme.widgets.selectorlist.create (value, no selector)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '12', rtype: 'rtype.3'}]));
    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 0);
    assert.equal(widget.lastSelector().length, 0);
    assert.equal(widget.selectors().length, 0);
});

QUnit.test('creme.widgets.selectorlist.create (value, invalid selector)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([3]));
    this.appendSelectorListModelTag(element, $('<div class="invalid"></div>'));

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.lastSelector().length, 0);
    assert.equal(widget.selectors().length, 0);

    var last = widget.appendSelector(13);
    assert.equal(last, undefined);

    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.lastSelector().length, 0);
    assert.equal(widget.selectors().length, 0);
});

QUnit.test('creme.widgets.selectorlist.create (value, static selector)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([3, 5, 3, 15]));
    var ctype = this.createDynamicSelectTag();
    this.appendOptionTag(ctype, 'a', 15);
    this.appendOptionTag(ctype, 'b', 5);
    this.appendOptionTag(ctype, 'c', 3);

    this.appendSelectorListModelTag(element, ctype);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([3, 5, 3, 15]));
    assert.equal(widget.selectorModel().length, 1);

    assert.equal(widget.lastSelector().length, 1);
    this.assertDSelect(widget.lastSelector(), '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    assert.equal(widget.selectors().length, 4);

    this.assertDSelect(widget.selector(0), '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelect(widget.selector(1), '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelect(widget.selector(2), '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelect(widget.selector(3), '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

QUnit.test('creme.widgets.selectorlist.create (value, chained selector)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);

    assert.equal(widget.lastSelector().length, 1);

    this.assertDSelectAt(widget.lastSelector().creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.lastSelector().creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    assert.equal(widget.selectors().length, 3);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '1', [], '', [['1', 'd'], ['6', 'e']]);

    this.assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    this.assertDSelectAt(widget.selector(2).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(2).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);
});

QUnit.test('creme.widgets.selectorlist.create (invalid value, multiple dependencies)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '3', rtype: 'rtype.3', entity: null}]));
    var model = this.createChainedSelectTag();

    var ctype = this.createDynamicSelectTag();
    this.appendOptionTag(ctype, 'a', 15);
    this.appendOptionTag(ctype, 'b', 5);
    this.appendOptionTag(ctype, 'c', 3);
    this.appendOptionTag(ctype, 'd', 1);

    var rtype = this.createDynamicSelectTag('mock/rtype/${ctype}/options');
    var entity = this.createDynamicSelectTag('mock/entity/${rtype}/${ctype}/options');

    this.appendChainedSelectorTag(model, 'ctype', ctype);
    this.appendChainedSelectorTag(model, 'rtype', rtype);
    this.appendChainedSelectorTag(model, 'entity', entity);

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: null, entity: null}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 1);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'entity', null, ['rtype', 'ctype'], null, []);
});

QUnit.test('creme.widgets.selectorlist.value (value, no selector)', function(assert) {
    var element = this.createSelectorListTag();
    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 0);
    assert.equal(widget.lastSelector().length, 0);
    assert.equal(widget.selectors().length, 0);

    widget.val(JSON.stringify([{ctype: '12', rtype: 'rtype.3'}]));
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 0);
    assert.equal(widget.lastSelector().length, 0);
    assert.equal(widget.selectors().length, 0);

    widget.val([{ctype: '12', rtype: 'rtype.3'}]);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 0);
    assert.equal(widget.lastSelector().length, 0);
    assert.equal(widget.selectors().length, 0);
});

QUnit.test('creme.widgets.selectorlist.value (value, static selector)', function(assert) {
    var element = this.createSelectorListTag();
    var ctype = this.createDynamicSelectTag();
    this.appendOptionTag(ctype, 'a', 15);
    this.appendOptionTag(ctype, 'b', 5);
    this.appendOptionTag(ctype, 'c', 3);

    this.appendSelectorListModelTag(element, ctype);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.lastSelector().length, 0);
    assert.equal(widget.selectors().length, 0);

    widget.val(JSON.stringify([3, 5, 3, 15]));
    assert.equal(widget.lastSelector().length, 1);
    assert.equal(widget.selectors().length, 4);

    this.assertDSelect(widget.selector(0), '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelect(widget.selector(1), '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelect(widget.selector(2), '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelect(widget.selector(3), '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    widget.val([5, 15]);
    assert.equal(widget.lastSelector().length, 1);
    assert.equal(widget.selectors().length, 2);

    this.assertDSelect(widget.selector(0), '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelect(widget.selector(1), '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    widget.val(JSON.stringify([]));
    assert.equal(widget.lastSelector().length, 0);
    assert.equal(widget.selectors().length, 0);
});

QUnit.test('creme.widgets.selectorlist.value (value, single dependency)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([]));
    var model = this.createChainedSelectTag();

    var ctype = this.createDynamicSelectTag();
    this.appendOptionTag(ctype, 'a', 15);
    this.appendOptionTag(ctype, 'b', 5);
    this.appendOptionTag(ctype, 'c', 3);
    this.appendOptionTag(ctype, 'd', 1);

    var rtype = this.createDynamicSelectTag('mock/rtype/${ctype}/options');

    this.appendChainedSelectorTag(model, 'ctype', ctype);
    this.appendChainedSelectorTag(model, 'rtype', rtype);

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 0);

    widget.val([{ctype: '3', rtype: 'rtype.3'}, {ctype: '5', rtype: 'rtype.22'}]);
    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: null}, {ctype: '5', rtype: 'rtype.22'}]));
    assert.equal(widget.selectors().length, 2);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);

    this.assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);

    widget.val([{ctype: '5', rtype: 'rtype.7'}]);
    assert.equal(widget.val(), JSON.stringify([{ctype: '5', rtype: 'rtype.7'}]));
    assert.equal(widget.selectors().length, 1);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', 'rtype.7', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);

    widget.val([]);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectors().length, 0);
});

QUnit.test('creme.widgets.selectorlist.value (value, multiple dependencies)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([]));
    var model = this.createChainedSelectTag();

    var ctype = this.createDynamicSelectTag();
    this.appendOptionTag(ctype, 'a', 15);
    this.appendOptionTag(ctype, 'b', 5);
    this.appendOptionTag(ctype, 'c', 3);
    this.appendOptionTag(ctype, 'd', 1);

    var rtype = this.createDynamicSelectTag('mock/rtype/${ctype}/options');
    var entity = this.createDynamicSelectTag('mock/entity/${rtype}/${ctype}/options');

    this.appendChainedSelectorTag(model, 'ctype', ctype);
    this.appendChainedSelectorTag(model, 'rtype', rtype);
    this.appendChainedSelectorTag(model, 'entity', entity);

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 0);

    widget.val([{ctype: '3', rtype: 'rtype.3', entity: null}, {ctype: '5', rtype: 'rtype.22', entity: '789'}]);
    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: null, entity: null}, {ctype: '5', rtype: 'rtype.22', entity: '789'}]));
    assert.equal(widget.selectors().length, 2);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'entity', null, ['rtype', 'ctype'], null, []);

    this.assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertDSelectAt(widget.selector(1).creme().widget(), 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);

    widget.val([{ctype: '5', rtype: 'rtype.7', entity: '789'}]);
    assert.equal(widget.val(), JSON.stringify([{ctype: '5', rtype: 'rtype.7', entity: null}]));
    assert.equal(widget.selectors().length, 1);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', 'rtype.7', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'entity', null, ['rtype', 'ctype'], 'mock/entity/rtype.7/5/options', []);

    widget.val([]);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectors().length, 0);
});

QUnit.test('creme.widgets.selectorlist.multiple-change (single selector)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([]));
    var model = this.createChainedSelectTag();

    var ctype = this.createDynamicSelectTag();
    this.appendOptionTag(ctype, 'a', 15);
    this.appendOptionTag(ctype, 'b', 5);
    this.appendOptionTag(ctype, 'c', 3);
    this.appendOptionTag(ctype, 'd', 18);
    this.appendOptionTag(ctype, 'e', 24);

    this.appendChainedSelectorTag(model, 'ctype', ctype);

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);

    element.on('change-multiple', this.mockListener('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));

    // append [ctype=15]
    var selector = widget.appendSelector();
    assert.equal(widget.selectors().length, 1);
    assert.equal(widget.val(), JSON.stringify([{ctype: '15'}]));

    // single change [ctype=5]
    selector.selector('ctype').val('5').trigger('change');
    assert.equal(widget.val(), JSON.stringify([{ctype: '5'}]));

    // multiple change [ctype=5, ctype=15, ctype=3]
    selector.selector('ctype').trigger('change-multiple', [['5', '15', '3']]);
    assert.deepEqual([
        ['change-multiple', [[{ctype: '5'}, {ctype: '15'}, {ctype: '3'}]]]
    ], this.mockListenerJQueryCalls('change-multiple'));

    assert.equal(widget.selectors().length, 3);
    assert.equal(widget.val(), JSON.stringify([{ctype: '5'}, {ctype: '15'}, {ctype: '3'}]));

    // append [ctype=5, ctype=15, ctype=3, ctype=15]
    selector = widget.appendSelector();

    assert.equal(widget.selectors().length, 4);
    assert.equal(widget.val(), JSON.stringify([{ctype: '5'}, {ctype: '15'}, {ctype: '3'}, {ctype: '15'}]));

    // single change [ctype=5, ctype=15, ctype=3, ctype=18]
    selector.selector('ctype').val('18').trigger('change');
    assert.equal(widget.selectors().length, 4);
    assert.equal(widget.val(), JSON.stringify([{ctype: '5'}, {ctype: '15'}, {ctype: '3'}, {ctype: '18'}]));

    // multiple change [ctype=5, ctype=15, ctype=3, ctype=18, ctype=24]
    selector.selector('ctype').trigger('change-multiple', [['18', '24']]);
    assert.deepEqual([
        ['change-multiple', [[{ctype: '5'}, {ctype: '15'}, {ctype: '3'}]]],
        ['change-multiple', [[{ctype: '18'}, {ctype: '24'}]]]
    ], this.mockListenerJQueryCalls('change-multiple'));

    assert.equal(widget.selectors().length, 5);
    assert.equal(widget.val(), JSON.stringify([{ctype: '5'}, {ctype: '15'}, {ctype: '3'}, {ctype: '18'}, {ctype: '24'}]));
});

QUnit.test('creme.widgets.selectorlist.multiple-change (multiple selector)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([]));
    var model = this.createChainedSelectTag();

    var ctype = this.createDynamicSelectTag();
    this.appendOptionTag(ctype, 'a', 15);
    this.appendOptionTag(ctype, 'b', 5);
    this.appendOptionTag(ctype, 'c', 3);
    this.appendOptionTag(ctype, 'd', 18);
    this.appendOptionTag(ctype, 'e', 24);

    var rtype = this.createDynamicSelectTag();
    this.appendOptionTag(rtype, 'f', 1);
    this.appendOptionTag(rtype, 'g', 6);
    this.appendOptionTag(rtype, 'h', 17);

    this.appendChainedSelectorTag(model, 'ctype', ctype);
    this.appendChainedSelectorTag(model, 'rtype', rtype);

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);

    element.on('change-multiple', this.mockListener('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));

    // append [{ctype=15, rtype=1}]
    var selector = widget.appendSelector();
    assert.equal(widget.selectors().length, 1);
    assert.equal(widget.val(), JSON.stringify([{ctype: '15', rtype: '1'}]));

    // single change [{ctype=15, rtype=6}]
    selector.selector('rtype').val('6').trigger('change');
    assert.equal(widget.val(), JSON.stringify([{ctype: '15', rtype: '6'}]));

    // multiple change [{ctype=15, rtype=6}, {ctype=15, rtype=1}, {ctype=15, rtype=17}]
    selector.selector('rtype').trigger('change-multiple', [['6', '1', '17']]);

    assert.deepEqual([
        ['change-multiple', [[{ctype: '15', rtype: '6'}, {ctype: '15', rtype: '1'}, {ctype: '15', rtype: '17'}]]]
    ], this.mockListenerJQueryCalls('change-multiple'));

    assert.equal(widget.selectors().length, 3);
    assert.equal(widget.val(), JSON.stringify([{ctype: '15', rtype: '6'}, {ctype: '15', rtype: '1'}, {ctype: '15', rtype: '17'}]));

    // append [{ctype=15, rtype=6}, {ctype=15, rtype=1}, {ctype=15, rtype=17}, {ctype=15, rtype=1}]
    selector = widget.appendSelector();

    assert.equal(widget.selectors().length, 4);
    assert.equal(widget.val(), JSON.stringify([{ctype: '15', rtype: '6'}, {ctype: '15', rtype: '1'}, {ctype: '15', rtype: '17'}, {ctype: '15', rtype: '1'}]));

    // single change [{ctype=15, rtype=6}, {ctype=15, rtype=1}, {ctype=15, rtype=17}, {ctype=24, rtype=1}]
    selector.selector('ctype').val('24').trigger('change');
    assert.equal(widget.selectors().length, 4);
    assert.equal(widget.val(), JSON.stringify([{ctype: '15', rtype: '6'}, {ctype: '15', rtype: '1'}, {ctype: '15', rtype: '17'}, {ctype: '24', rtype: '1'}]));

    // multiple change [{ctype=15, rtype=6}, {ctype=15, rtype=1}, {ctype=15, rtype=17}, {ctype=24, rtype=1}, {ctype=24, rtype=6}]
    selector.selector('rtype').trigger('change-multiple', [['1', '6']]);
    assert.deepEqual([
        ['change-multiple', [[{ctype: '15', rtype: '6'}, {ctype: '15', rtype: '1'}, {ctype: '15', rtype: '17'}]]],
        ['change-multiple', [[{ctype: '24', rtype: '1'}, {ctype: '24', rtype: '6'}]]]
    ], this.mockListenerJQueryCalls('change-multiple'));

    assert.equal(widget.selectors().length, 5);
    assert.equal(widget.val(), JSON.stringify([{ctype: '15', rtype: '6'}, {ctype: '15', rtype: '1'}, {ctype: '15', rtype: '17'}, {ctype: '24', rtype: '1'}, {ctype: '24', rtype: '6'}]));
});

QUnit.test('creme.widgets.selectorlist.append (empty)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 0);

    var last = widget.appendSelector();
    assert.notEqual(last, undefined);

    assert.equal(widget.val(), JSON.stringify([{ctype: '15', rtype: '1'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 1);
    assert.equal(widget.selectors().creme().widget().val(), JSON.stringify({ctype: '15', rtype: '1'}));

    assert.deepEqual(widget.selector(0).creme().widget(), last);
});

QUnit.test('creme.widgets.selectorlist.append (not empty)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 3);

    var last = widget.appendSelector();
    assert.notEqual(last, undefined);

    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}, {ctype: '15', rtype: '1'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 4);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '1', [], '', [['1', 'd'], ['6', 'e']]);

    this.assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    this.assertDSelectAt(widget.selector(2).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(2).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    this.assertDSelectAt(widget.selector(3).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(3).creme().widget(), 'rtype', '1', [], '', [['1', 'd'], ['6', 'e']]);
});

QUnit.test('creme.widgets.selectorlist.append (not empty, value)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 3);

    var last = widget.appendSelector({ctype: '3', rtype: '6'});
    assert.notEqual(last, undefined);

    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}, {ctype: '3', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 4);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '1', [], '', [['1', 'd'], ['6', 'e']]);

    this.assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    this.assertDSelectAt(widget.selector(2).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(2).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    this.assertDSelectAt(widget.selector(3).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(3).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);
});

QUnit.test('creme.widgets.selectorlist.append (not empty, multiple dependencies, value)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '3', rtype: 'rtype.3', entity: null}]));
    var model = this.createChainedSelectTag();

    var ctype = this.createDynamicSelectTag();
    this.appendOptionTag(ctype, 'a', 15);
    this.appendOptionTag(ctype, 'b', 5);
    this.appendOptionTag(ctype, 'c', 3);
    this.appendOptionTag(ctype, 'd', 1);

    var rtype = this.createDynamicSelectTag('mock/rtype/${ctype}/options');
    var entity = this.createDynamicSelectTag('mock/entity/${rtype}/${ctype}/options');

    this.appendChainedSelectorTag(model, 'ctype', ctype);
    this.appendChainedSelectorTag(model, 'rtype', rtype);
    this.appendChainedSelectorTag(model, 'entity', entity);

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: null, entity: null}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 1);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'entity', null, ['rtype', 'ctype'], null, []);

    var last = widget.appendSelector({ctype: '5', rtype: 'rtype.22', entity: '789'});
    assert.notEqual(last, undefined);

    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: null, entity: null}, {ctype: '5', rtype: 'rtype.22', entity: '789'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 2);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'entity', null, ['rtype', 'ctype'], null, []);

    this.assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertDSelectAt(widget.selector(1).creme().widget(), 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);
});

QUnit.test('creme.widgets.selectorlist.removeAt (empty)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 0);

    var removed = widget.removeSelectorAt(0);
    assert.equal(removed, undefined);

    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 0);
});

QUnit.test('creme.widgets.selectorlist.removeAt (not empty)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 3);

    var removed = widget.removeSelectorAt(0);
    assert.notEqual(removed, undefined);

    assert.equal(widget.val(), JSON.stringify([{ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 2);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    this.assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    widget.removeSelectorAt(1);
    assert.equal(widget.val(), JSON.stringify([{ctype: '15', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 1);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);
});

QUnit.test('creme.widgets.selectorlist.remove (empty)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 0);

    var removed = widget.removeSelector(undefined);
    assert.equal(removed, undefined);

    assert.equal(widget.val(), JSON.stringify([]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 0);
});

QUnit.test('creme.widgets.selectorlist.remove (not empty)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 3);

    var removed = widget.removeSelector(widget.selector(0));
    assert.notEqual(removed, undefined);

    assert.equal(widget.val(), JSON.stringify([{ctype: '15', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 2);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    this.assertDSelectAt(widget.selector(1).creme().widget(), 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(1).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);

    widget.removeSelector(widget.selector(1));
    assert.equal(widget.val(), JSON.stringify([{ctype: '15', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 1);

    this.assertDSelectAt(widget.selector(0).creme().widget(), 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget.selector(0).creme().widget(), 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);
});

QUnit.test('creme.widgets.selectorlist.appendLast (not empty)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element, {cloneLast: true});
    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 2);

    var last = widget.appendLastSelector();
    assert.notEqual(last, undefined);

    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}, {ctype: '5', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 3);
});

QUnit.test('creme.widgets.selectorlist.appendLast (not empty, no clone last)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 2);

    var last = widget.appendLastSelector();
    assert.notEqual(last, undefined);

    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}, {ctype: '15', rtype: '1'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 3);
});

QUnit.test('creme.widgets.selectorlist (add button)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);
    element.append('<button type="button" class="selectorlist-add">');

    var widget = creme.widget.create(element);
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 2);

    element.find('.selectorlist-add').trigger('click');

    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}, {ctype: '15', rtype: '1'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 3);
});

QUnit.test('creme.widgets.selectorlist (create button)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);
    element.append('<button type="button" class="selectorlist-create">');

    var widget = creme.widget.create(element);
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 2);

    element.find('.selectorlist-create').trigger('click');

    assert.equal(widget.val(), JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}, {ctype: '15', rtype: '1'}]));
    assert.equal(widget.selectorModel().length, 1);
    assert.equal(widget.selectors().length, 3);
});

QUnit.test('creme.widgets.selectorlist (delete buttons)', function(assert) {
    var element = this.createSelectorListTag(JSON.stringify([{ctype: '3', rtype: '1'}, {ctype: '5', rtype: '6'}]));
    var model = this.createCTypeRTypeSelectorTag();

    this.appendSelectorListModelTag(element, model);

    var widget = creme.widget.create(element);
    assert.equal(widget.selectors().length, 2);

    assert.equal(element.find('.delete').length, 2);
    element.find('.delete:first').trigger('click');

    assert.equal(widget.val(), JSON.stringify([{ctype: '5', rtype: '6'}]));
    assert.equal(widget.selectors().length, 1);
});

}(jQuery));
