/* globals QUnitWidgetMixin */
(function($) {

var MOCK_FRAME_CONTENT = '<div class="mock-content"><h1>This a frame test</h1></div>';

QUnit.module("creme.widget.chainedselect.js", new QUnitMixin(QUnitAjaxMixin, QUnitEventMixin, QUnitWidgetMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.widget.chainedselect.js'});
    },

    beforeEach: function() {
        this.setMockBackendGET({
            'mock/entity/label/123': this.backend.responseJSON(200, [['John Doe']]),
            'mock/entity/label/456': this.backend.responseJSON(200, [['Bean Bandit']]),
            'mock/popup': this.backend.response(200, MOCK_FRAME_CONTENT),
            'mock/options': this.backend.responseJSON(200, [[15, 'a'], [5, 'b'], [3, 'c'], [14, 't'], [42, 'y']]),
            'mock/rtype/1/options': this.backend.responseJSON(200, [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]),
            'mock/rtype/5/options': this.backend.responseJSON(200, [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]),
            'mock/rtype/15/options': this.backend.responseJSON(200, [['rtype.12', 'b'], ['rtype.2', 'e']]),
            'mock/rtype/8/options': this.backend.responseJSON(200, [['rtype.12', 'b'], ['rtype.22', 'y']]),
            'mock/entity/rtype.12/15/options': this.backend.responseJSON(200, [['123', 'John Doe'], ['456', 'Bean Bandit']]),
            'mock/entity/rtype.22/5/options': this.backend.responseJSON(200, [['456', 'Bean Bandit'], ['789', 'Mini May']]),
            'mock/entity/rtype.22/8/options': this.backend.responseJSON(200, [['123', 'John Doe'], ['789', 'Mini May']]),
            'mock/options/empty': this.backend.responseJSON(200, []),
            'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
            'mock/error': this.backend.response(500, 'HTTP - Error 500')
        });
    },

    afterEach: function() {
        $('.ui-dialog-content').dialog('destroy');
        creme.widget.shutdown($('body'));
    }
}));

QUnit.test('creme.widgets.chainedselect.create (empty, no selector)', function(assert) {
    var element = this.createChainedSelectTag();
    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.val(), JSON.stringify({}));
    assert.equal(widget.selectors().length, 0);
    assert.equal(widget.selector('ctype').length, 0);
});

QUnit.test('creme.widgets.chainedselect.create (empty, single selector, static)', function(assert) {
    var element = this.createChainedSelectTag();
    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(widget.val(), JSON.stringify({ctype: '15'}));
    assert.equal(widget.selectors().length, 1);
    assert.deepEqual(widget.context(), {ctype: '15'});

    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    assert.equal(widget.selector('unknown').length, 0);
});

QUnit.test('creme.widgets.chainedselect.create (empty, single selector, static, <div>)', function(assert) {
    var element = this.createChainedSelectTag();
    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype, 'div');

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(widget.val(), JSON.stringify({ctype: '15'}));
    assert.equal(widget.selectors().length, 1);
    assert.deepEqual(widget.context(), {ctype: '15'});

    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    assert.equal(widget.selector('unknown').length, 0);
});

QUnit.test('creme.widgets.chainedselect.create (empty, single selector, url)', function(assert) {
    var element = this.createChainedSelectTag();
    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(widget.val(), JSON.stringify({ctype: '15'}));
    assert.equal(widget.selectors().length, 1);
    assert.deepEqual(widget.context(), {ctype: '15'});

    this.assertDSelectAt(widget, 'ctype', '15', [], 'mock/options', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['14', 't'], ['42', 'y']]);

    assert.equal(widget.selector('unknown').length, 0);
});

QUnit.test('creme.widgets.chainedselect.create (empty, multi selector)', function(assert) {
    var element = this.createChainedSelectTag();

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 1, label: 'd'},
            {value: 6, label: 'e'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '15', rtype: '1'}));
    assert.equal(widget.selectors().length, 2);
    assert.deepEqual(widget.context(), {ctype: '15', rtype: '1'});

    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', '1', [], '', [['1', 'd'], ['6', 'e']]);
});

QUnit.test('creme.widgets.chainedselect.create (empty, multi selector, single dependency)', function(assert) {
    var element = this.createChainedSelectTag();

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '15', rtype: 'rtype.12'}));
    assert.equal(widget.selectors().length, 2);

    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);
});

QUnit.test('creme.widgets.chainedselect.create (empty, multi selector, multiple dependency)', function(assert) {
    var element = this.createChainedSelectTag();

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    var entity = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/entity/${rtype}/${ctype}/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);
    this.appendChainedSelectorTag(element, 'entity', entity);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '15', rtype: 'rtype.12', entity: '123'}));
    assert.equal(widget.selectors().length, 3);

    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);
    this.assertDSelectAt(widget, 'entity', '123', ['rtype', 'ctype'], 'mock/entity/rtype.12/15/options', [['123', 'John Doe'], ['456', 'Bean Bandit']]);
});


QUnit.test('creme.widgets.chainedselect.create (empty, multi selector, duplicates)', function(assert) {
    var element = this.createChainedSelectTag();

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 1, label: 'd'},
            {value: 6, label: 'e'}
        ]
    }));

    var rtype2 = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 12.5, label: 'd'},
            {value: 14.78, label: 'g'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);
    this.appendChainedSelectorTag(element, 'rtype', rtype2);

    var widget = creme.widget.create(element);

    // use last one as value
    assert.equal(widget.val(), JSON.stringify({ctype: '15', rtype: '12.5'}));
    assert.equal(widget.selectors().length, 3);

    assert.equal(widget.selector('ctype').length, 1);
    assert.equal(widget.selector('ctype').creme().widget().val(), '15');
    assert.deepEqual(widget.selector('ctype').creme().widget().dependencies(), []);

    assert.equal(widget.selector('rtype').length, 1);

    assert.equal(widget.selector('rtype').creme().widget().val(), '12.5');
    assert.deepEqual(widget.selector('rtype').creme().widget().dependencies(), []);
});

// TODO : implement detection of cross dependencies
/*
QUnit.test('creme.widgets.chainedselect.create (multi selector, cross dependencies)', function(assert) {

});
*/

QUnit.test('creme.widgets.chainedselect.create (valid, no selector)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '12'}));
    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.val(), JSON.stringify({}));
    assert.equal(widget.selectors().length, 0);
    assert.equal(widget.selector('ctype').length, 0);
});

QUnit.test('creme.widgets.chainedselect.create (valid, single selector, static)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5'}));
    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '5'}));
    assert.equal(widget.selectors().length, 1);

    this.assertDSelectAt(widget, 'ctype', '5', [], '',
                  [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

QUnit.test('creme.widgets.chainedselect.create (unknown choice, single selector, static)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '54'}));
    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '15'}));
    assert.equal(widget.selectors().length, 1);

    this.assertDSelectAt(widget, 'ctype', '15', [], '',
                  [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

QUnit.test('creme.widgets.chainedselect.create (valid, single selector, url)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '14'}));
    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '14'}));
    assert.equal(widget.selectors().length, 1);

    this.assertDSelectAt(widget, 'ctype', '14', [], 'mock/options',
                  [['15', 'a'], ['5', 'b'], ['3', 'c'], ['14', 't'], ['42', 'y']]);
});

QUnit.test('creme.widgets.chainedselect.create (valid, multi selector, static)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '3', rtype: '6'}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 1, label: 'd'},
            {value: 6, label: 'e'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '3', rtype: '6'}));
    assert.equal(widget.selectors().length, 2);

    this.assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', '6', [], '', [['1', 'd'], ['6', 'e']]);
});

QUnit.test('creme.widgets.chainedselect.create (unknown choice, multi selector, static)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '3', rtype: '46'}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 1, label: 'd'},
            {value: 6, label: 'e'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '3', rtype: '1'}));
    assert.equal(widget.selectors().length, 2);

    this.assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', '1', [], '', [['1', 'd'], ['6', 'e']]);
});

QUnit.test('creme.widgets.chainedselect.create (valid, multi selector, single dependency)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '1', rtype: 'rtype.3'}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'},
            {value: 1, label: 'd'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '1', rtype: 'rtype.3'}));
    assert.equal(widget.selectors().length, 2);

    this.assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);

    this.assertDSelectAt(widget, 'rtype', 'rtype.3', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);
});

QUnit.test('creme.widgets.chainedselect.create (valid, multi selector, multi dependencies)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5', rtype: 'rtype.22', entity: '789'}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    var entity = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/entity/${rtype}/${ctype}/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);
    this.appendChainedSelectorTag(element, 'entity', entity);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.22', entity: '789'}));
    assert.equal(widget.selectors().length, 3);

    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    this.assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);

    this.assertDSelectAt(widget, 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);
});

QUnit.test('creme.widgets.chainedselect.val (single selector)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5'}));
    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '5'}));
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    widget.val({ctype: '3'});
    assert.equal(widget.val(), JSON.stringify({ctype: '3'}));
    this.assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    widget.val({ctype: '42'});
    assert.equal(widget.val(), JSON.stringify({ctype: '15'}));
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

QUnit.test('creme.widgets.chainedselect.val (multi selector, static)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5', rtype: '6'}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 1, label: 'd'},
            {value: 6, label: 'e'},
            {value: 42, label: 'f'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: '6'}));
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', '6', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);

    widget.val({ctype: '3', rtype: '42'});
    assert.equal(widget.val(), JSON.stringify({ctype: '3', rtype: '42'}));
    this.assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', '42', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);

    widget.val({ctype: '59', rtype: '1'});
    assert.equal(widget.val(), JSON.stringify({ctype: '15', rtype: '1'}));
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', '1', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);
});

QUnit.test('creme.widgets.chainedselect.val (multi selector, single dependency)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '1', rtype: 'rtype.3'}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'},
            {value: 1, label: 'd'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '1', rtype: 'rtype.3'}), 'initial value');
    this.assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.3', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);

    widget.val({ctype: '5', rtype: 'rtype.22'});
    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.22'}), 'updated value');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);

    widget.val({ctype: '59', rtype: 'rtype.22'});
    assert.equal(widget.val(), JSON.stringify({ctype: '15', rtype: 'rtype.12'}), 'invalid ctype');
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);

    widget.val({ctype: '1', rtype: 'rtype.55'});
    assert.equal(widget.val(), JSON.stringify({ctype: '1', rtype: 'rtype.1'}), 'invalid rtype');
    this.assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.1', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);
});

QUnit.test('creme.widgets.chainedselect.val (multi selector, multiple dependencies)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '1', rtype: 'rtype.3', entity: null}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'},
            {value: 1, label: 'd'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    var entity = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/entity/${rtype}/${ctype}/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);
    this.appendChainedSelectorTag(element, 'entity', entity);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '1', rtype: 'rtype.3', entity: null}), 'initial value');
    this.assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.3', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);
    this.assertDSelectAt(widget, 'entity', null, ['rtype', 'ctype'], 'mock/entity/rtype.3/1/options', []);

    widget.val({ctype: '5', rtype: 'rtype.22', entity: '789'});
    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.22', entity: '789'}), 'updated value');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertDSelectAt(widget, 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);

    widget.val({ctype: '59', rtype: 'rtype.22', entity: '789'});
    assert.equal(widget.val(), JSON.stringify({ctype: '15', rtype: 'rtype.12', entity: '123'}), 'invalid ctype');
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);
    this.assertDSelectAt(widget, 'entity', '123', ['rtype', 'ctype'], 'mock/entity/rtype.12/15/options', [['123', 'John Doe'], ['456', 'Bean Bandit']]);

    widget.val({ctype: '5', rtype: 'rtype.489', entity: '789'});
    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.7', entity: null}), 'invalid rtype');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.7', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertDSelectAt(widget, 'entity', null, ['rtype', 'ctype'], 'mock/entity/rtype.7/5/options', []);

    widget.val({ctype: '5', rtype: 'rtype.22', entity: '007'});
    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.22', entity: '456'}), 'invalid entity');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertDSelectAt(widget, 'entity', '456', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);
});

QUnit.test('creme.widgets.chainedselect.val (multi selector, multiple dependencies, entity selector)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '1', rtype: 'rtype.3', entity: null}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'},
            {value: 1, label: 'd'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    var entity = this.createEntitySelectorTag({labelURL: 'mock/label',
                                               popupURL: 'mock/entity/${rtype}/${ctype}/popup'});

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);
    this.appendChainedSelectorTag(element, 'entity', entity);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '1', rtype: 'rtype.3', entity: null}), 'initial value');
    this.assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.3', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);
    this.assertEntitySelect(widget.selector('entity'), null, ['rtype', 'ctype'], 'mock/entity/rtype.3/1/popup');

    widget.val({ctype: '5', rtype: 'rtype.22', entity: '789'});
    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.22', entity: '789'}), 'updated value');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertEntitySelect(widget.selector('entity'), '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/popup');

    widget.val({ctype: '59', rtype: 'rtype.22', entity: '789'});
    assert.equal(widget.val(), JSON.stringify({ctype: '15', rtype: 'rtype.12', entity: '789'}), 'invalid ctype');
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);
    this.assertEntitySelect(widget.selector('entity'), '789', ['rtype', 'ctype'], 'mock/entity/rtype.12/15/popup');

    widget.val({ctype: '5', rtype: 'rtype.489', entity: '789'});
    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.7', entity: '789'}), 'invalid rtype');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.7', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertEntitySelect(widget.selector('entity'), '789', ['rtype', 'ctype'], 'mock/entity/rtype.7/5/popup');

    widget.val({ctype: '5', rtype: 'rtype.22', entity: '007'});
    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.22', entity: '007'}), 'invalid entity');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertEntitySelect(widget.selector('entity'), '007', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/popup');
});

QUnit.test('creme.widgets.chainedselect.change (single selector)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5'}));
    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '5'}));
    assert.equal(5, ctype.creme().widget().val());

    ctype.creme().widget().val(15);
    assert.equal(widget.val(), JSON.stringify({ctype: '15'}));
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);

    ctype.creme().widget().val(null);
    assert.equal(widget.val(), JSON.stringify({ctype: '15'}));
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

QUnit.test('creme.widgets.chainedselect.change (multi selector, static)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5', rtype: '6'}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 1, label: 'd'},
            {value: 6, label: 'e'},
            {value: 42, label: 'f'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: '6'}));
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', '6', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);

    ctype.creme().widget().val(3);
    assert.equal(widget.val(), JSON.stringify({ctype: '3', rtype: '6'}));
    this.assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', '6', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);

    rtype.creme().widget().val(42);
    assert.equal(widget.val(), JSON.stringify({ctype: '3', rtype: '42'}));
    this.assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', '42', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);

    ctype.creme().widget().val(15);
    rtype.creme().widget().val(6);
    assert.equal(widget.val(), JSON.stringify({ctype: '15', rtype: '6'}));
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', '6', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);
});

QUnit.test('creme.widgets.chainedselect.change (multi selector, single dependency)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '1', rtype: 'rtype.3'}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'},
            {value: 1, label: 'd'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '1', rtype: 'rtype.3'}), 'initial value');
    this.assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.3', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);

    ctype.creme().widget().val(3);
    assert.equal(widget.val(), JSON.stringify({ctype: '3', rtype: null}), 'updated ctype, no rtype');
    this.assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);

    ctype.creme().widget().val(5);
    rtype.creme().widget().val('rtype.22');
    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.22'}), 'updated ctype and rtype');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
});

QUnit.test('creme.widgets.chainedselect.change (multi selector, multiple dependencies)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '1', rtype: 'rtype.3', entity: null}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'},
            {value: 1, label: 'd'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    var entity = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/entity/${rtype}/${ctype}/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);
    this.appendChainedSelectorTag(element, 'entity', entity);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '1', rtype: 'rtype.3', entity: null}), 'initial value');
    this.assertDSelectAt(widget, 'ctype', '1', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.3', ['ctype'], 'mock/rtype/1/options', [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]);
    this.assertDSelectAt(widget, 'entity', null, ['rtype', 'ctype'], 'mock/entity/rtype.3/1/options', []);

    ctype.creme().widget().val(3);
    assert.equal(widget.val(), JSON.stringify({ctype: '3', rtype: null, entity: null}), 'updated ctype, no rtype, no entity');
    this.assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', null, ['ctype'], 'mock/rtype/3/options', []);
    this.assertDSelectAt(widget, 'entity', null, ['rtype', 'ctype'], null, []);

    ctype.creme().widget().val(5);
    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.7', entity: null}), 'updated ctype');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.7', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertDSelectAt(widget, 'entity', null, ['rtype', 'ctype'], 'mock/entity/rtype.7/5/options', []);

    rtype.creme().widget().val('rtype.22');
    entity.creme().widget().val(789);
    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.22', entity: '789'}), 'updated ctype');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertDSelectAt(widget, 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);
});

QUnit.test('creme.widgets.chainedselect.multiple-change (single selector)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5'}));
    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify({ctype: '5'}));

    element.on('change-multiple', this.mockListener('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));

    ctype.trigger('change-multiple', [['5', '15', '3']]);
    assert.deepEqual([
        ['change-multiple', [[{ctype: '5'}, {ctype: '15'}, {ctype: '3'}]]]
    ], this.mockListenerJQueryCalls('change-multiple'));

    ctype.trigger('change-multiple', ['3']);
    assert.deepEqual([
        ['change-multiple', [[{ctype: '5'}, {ctype: '15'}, {ctype: '3'}]]],
        ['change-multiple', [[{ctype: '3'}]]]
    ], this.mockListenerJQueryCalls('change-multiple'));
});

QUnit.test('creme.widgets.chainedselect.multiple-change (multiple selector)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5'}));
    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    var widget = creme.widget.create(element);
    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.7'}));

    element.on('change-multiple', this.mockListener('change-multiple'));
    assert.deepEqual([], this.mockListenerJQueryCalls('change-multiple'));

    rtype.trigger('change-multiple', [['rtype.7', 'rtype.22']]);
    assert.deepEqual([
        ['change-multiple', [[{ctype: '5', rtype: 'rtype.7'}, {ctype: '5', rtype: 'rtype.22'}]]]
    ], this.mockListenerJQueryCalls('change-multiple'));
});

QUnit.test('creme.widgets.chainedselect.reset (single selector)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5'}));
    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '5'}), 'initial value');
    assert.equal(5, ctype.creme().widget().val());

    widget.reset();

    assert.equal(widget.val(), JSON.stringify({ctype: '15'}), 'reset value');
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

QUnit.test('creme.widgets.chainedselect.reset (multi selector, static)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '3', rtype: '42'}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 1, label: 'd'},
            {value: 6, label: 'e'},
            {value: 42, label: 'f'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '3', rtype: '42'}));
    this.assertDSelectAt(widget, 'ctype', '3', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', '42', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);

    widget.reset();

    assert.equal(widget.val(), JSON.stringify({ctype: '15', rtype: '1'}), 'reset value');
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
    this.assertDSelectAt(widget, 'rtype', '1', [], '', [['1', 'd'], ['6', 'e'], ['42', 'f']]);
});

QUnit.test('creme.widgets.chainedselect.reset (multi selector, single dependency)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5', rtype: 'rtype.22'}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'},
            {value: 1, label: 'd'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.22'}), 'updated ctype and rtype');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);

    widget.reset();

    assert.equal(widget.val(), JSON.stringify({ctype: '15', rtype: 'rtype.12'}), 'initial value');
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);
});

QUnit.test('creme.widgets.chainedselect.reset (multi selector, multiple dependencies)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5', rtype: 'rtype.22', entity: '789'}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'},
            {value: 1, label: 'd'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    var entity = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/entity/${rtype}/${ctype}/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);
    this.appendChainedSelectorTag(element, 'entity', entity);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.22', entity: '789'}), 'updated ctype');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertDSelectAt(widget, 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);

    widget.reset();

    assert.equal(widget.val(), JSON.stringify({ctype: '15', rtype: 'rtype.12', entity: '123'}), 'initial value');
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.12', ['ctype'], 'mock/rtype/15/options', [['rtype.12', 'b'], ['rtype.2', 'e']]);
    this.assertDSelectAt(widget, 'entity', '123', ['rtype', 'ctype'], 'mock/entity/rtype.12/15/options', [['123', 'John Doe'], ['456', 'Bean Bandit']]);
});

QUnit.test('creme.widgets.chainedselect.reset (click)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5'}));
    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'}
        ]
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    element.append($('<img class="reset" />'));

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '5'}), 'initial value');
    assert.equal(5, ctype.creme().widget().val());

    element.find('img.reset').trigger('click');

    assert.equal(widget.val(), JSON.stringify({ctype: '15'}), 'reset value');
    this.assertDSelectAt(widget, 'ctype', '15', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c']]);
});

QUnit.test('creme.widgets.chainedselect.update (multi selector, multiple dependencies)', function(assert) {
    var element = this.createChainedSelectTag(JSON.stringify({ctype: '5', rtype: 'rtype.22', entity: '789'}));

    var ctype = $(this.createSelectHtml({
        noEmpty: true,
        choices: [
            {value: 15, label: 'a'},
            {value: 5, label: 'b'},
            {value: 3, label: 'c'},
            {value: 1, label: 'd'}
        ]
    }));

    var rtype = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/rtype/${ctype}/options'
    }));

    var entity = $(this.createSelectHtml({
        noEmpty: true,
        url: 'mock/entity/${rtype}/${ctype}/options'
    }));

    this.appendChainedSelectorTag(element, 'ctype', ctype);
    this.appendChainedSelectorTag(element, 'rtype', rtype);
    this.appendChainedSelectorTag(element, 'entity', entity);

    var widget = creme.widget.create(element);

    assert.equal(widget.val(), JSON.stringify({ctype: '5', rtype: 'rtype.22', entity: '789'}), 'updated ctype');
    this.assertDSelectAt(widget, 'ctype', '5', [], '', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['1', 'd']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);
    this.assertDSelectAt(widget, 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/5/options', [['456', 'Bean Bandit'], ['789', 'Mini May']]);

    widget.update({
        added: [{
            ctype: {value: 8, label: 'e'},
            rtype: {value: 'rtype.25', label: 'e'}
        }],
        removed: [{
            ctype: {value: 5, label: 'b'}
        }],
        value: {ctype: '8', rtype: 'rtype.22', entity: '789'}
    });

    assert.equal(widget.val(), JSON.stringify({ctype: '8', rtype: 'rtype.22', entity: '789'}), 'initial value');
    this.assertDSelectAt(widget, 'ctype', '8', [], '', [['15', 'a'], ['3', 'c'], ['1', 'd'], ['8', 'e']]);
    this.assertDSelectAt(widget, 'rtype', 'rtype.22', ['ctype'], 'mock/rtype/8/options', [['rtype.12', 'b'], ['rtype.22', 'y']]);
    this.assertDSelectAt(widget, 'entity', '789', ['rtype', 'ctype'], 'mock/entity/rtype.22/8/options', [['123', 'John Doe'], ['789', 'Mini May']]);
});

}(jQuery));
