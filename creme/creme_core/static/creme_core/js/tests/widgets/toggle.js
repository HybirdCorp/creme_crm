/* globals QUnitWidgetMixin */
(function($) {
QUnit.module("creme.widgets.toggle.js", new QUnitMixin(QUnitEventMixin,
                                                       QUnitWidgetMixin, {
    createToggleHtml: function(options) {
        options = Object.assign({
            auto: true,
            collapsed: false,
            isTrigger: false,
            triggers: [],
            targets: []
        }, options || {});

        var attrs = options.attrs || {};

        if (options.isTrigger) {
            attrs['data-toggle'] = '';
        }

        return (
            '<div class="ui-creme-widget ui-creme-toggle ${auto} ${collapsed}" widget="ui-creme-toggle" ${attrs}>' +
                 '${triggers}${targets}' +
            '</div>'
        ).template({
            attrs: this.htmlAttrs(attrs),
            auto: options.auto ? 'widget-auto' : '',
            collapsed: options.collapsed ? 'toggle-collapsed' : '',
            triggers: (options.triggers || []).map(this.createToggleTriggerHtml.bind(this)).join('\n'),
            targets: (options.targets || []).join('\n')
        });
    },

    createToggleTriggerHtml: function(options) {
        options = options || {};
        var classes = options.classes || '';
        return '<a class="${collapsed} ${classes}" data-toggle="${target}" ${attrs}></a>'.template({
            target: options.target,
            attrs: this.htmlAttrs(options.attrs),
            collapsed: options.collapsed ? 'toggle-collapsed' : '',
            classes: Array.isArray(classes) ? classes.join(' ') : classes
        });
    },

    assertIsCollapsed: function(element, state) {
        this.assert.equal(element.hasClass('toggle-collapsed'), state, state ? 'toggle is collapsed' : 'toggle is expanded');
    }
}));

QUnit.test('creme.widget.Toggle.create (expanded)', function(assert) {
    var element = $(this.createToggleHtml());

    creme.widget.create(element);
    this.assertReady(element);

    this.assertIsCollapsed(element, false);
});

QUnit.test('creme.widget.Toggle.destroy', function(assert) {
    var element = $(this.createToggleHtml({
        isTrigger: true
    }));

    var widget = creme.widget.create(element, {
        debounceDelay: 0
    });
    this.assertReady(element);
    this.assertIsCollapsed(element, false);

    element.trigger('click');

    this.assertIsCollapsed(element, true);

    widget.destroy();

    // do nothing
    element.trigger('click');

    this.assertIsCollapsed(element, true);
});

QUnit.test('creme.widget.Toggle.create (self collapsed)', function(assert) {
    var element = $(this.createToggleHtml({
        collapsed: true,
        isTrigger: true
    }));

    creme.widget.create(element);
    this.assertReady(element);

    this.assertIsCollapsed(element, true);
});

QUnit.test('creme.widget.Toggle.create (trigger collapsed)', function(assert) {
    var element = $(this.createToggleHtml({
        triggers: [{
            collapsed: true,
            target: '#target-a'
        }],
        targets: ['<div id="target-a"></div>']
    }));

    // not collapsed.
    this.assertIsCollapsed(element.find('#target-a'), false);

    creme.widget.create(element);
    this.assertReady(element);

    // collapsed : the state is forced by the trigger.
    this.assertIsCollapsed(element.find('#target-a'), true);
});

QUnit.test('creme.widget.Toggle.expandAll (no trigger)', function(assert) {
    var element = $(this.createToggleHtml({
        collapsed: true
    }));

    var widget = creme.widget.create(element);
    this.assertReady(element);

    this.assertIsCollapsed(element, true);
    assert.deepEqual(widget.triggers().get(), []);

    widget.expandAll();

    this.assertIsCollapsed(element, true);
});

QUnit.test('creme.widget.Toggle.expandAll (self trigger)', function(assert) {
    var element = $(this.createToggleHtml({
        collapsed: true,
        isTrigger: true
    }));

    var widget = creme.widget.create(element);
    this.assertReady(element);

    this.assertIsCollapsed(element, true);
    assert.equal(widget.triggers().length, 1);

    widget.expandAll();

    this.assertIsCollapsed(element, false);

    widget.expandAll();

    this.assertIsCollapsed(element, false);

    widget.collapseAll();

    this.assertIsCollapsed(element, true);
});

QUnit.test('creme.widget.Toggle.expandAll (trigger)', function(assert) {
    var element = $(this.createToggleHtml({
        triggers: [{
            collapsed: true,
            target: '#target-a'
        }, {
            collapsed: false,
            target: '#target-b'
        }, {
            collapsed: true,
            target: '#target-c'
        }],
        targets: [
            '<div id="target-a"></div>',
            '<div id="target-b"></div>',
            '<div id="target-c"></div>'
        ]
    }));

    var widget = creme.widget.create(element);
    this.assertReady(element);

    assert.equal(widget.triggers().length, 3);

    this.assertIsCollapsed(element.find('#target-a'), true);
    this.assertIsCollapsed(element.find('#target-b'), false);
    this.assertIsCollapsed(element.find('#target-c'), true);

    widget.expandAll();

    this.assertIsCollapsed(element.find('#target-a'), false);
    this.assertIsCollapsed(element.find('#target-b'), false);
    this.assertIsCollapsed(element.find('#target-c'), false);

    widget.collapseAll();

    this.assertIsCollapsed(element.find('#target-a'), true);
    this.assertIsCollapsed(element.find('#target-b'), true);
    this.assertIsCollapsed(element.find('#target-c'), true);
});

QUnit.test('creme.widget.Toggle.toggle (click)', function(assert) {
    var element = $(this.createToggleHtml({
        triggers: [{
            collapsed: true,
            target: '#target-a',
            classes: 'trigger-a'
        }, {
            collapsed: false,
            target: '#target-b',
            classes: 'trigger-b'
        }, {
            collapsed: true,
            target: '.target-c',
            classes: 'trigger-c'
        }],
        targets: [
            '<div id="target-a"></div>',
            '<div id="target-b"></div>',
            '<div id="target-c01" class="target-c"></div>',
            '<div id="target-c02" class="target-c"></div>',
            '<div id="target-c03" class="target-c"></div>'
        ]
    }));

    var widget = creme.widget.create(element, {
        debounceDelay: 0
    });
    this.assertReady(element);

    assert.equal(widget.triggers().length, 3);

    this.assertIsCollapsed(element.find('#target-a'), true);
    this.assertIsCollapsed(element.find('#target-b'), false);
    this.assertIsCollapsed(element.find('#target-c01'), true);
    this.assertIsCollapsed(element.find('#target-c02'), true);
    this.assertIsCollapsed(element.find('#target-c03'), true);

    element.find('.trigger-a').trigger('click');
    element.find('.trigger-b').trigger('click');
    element.find('.trigger-c').trigger('click');

    this.assertIsCollapsed(element.find('#target-a'), false);
    this.assertIsCollapsed(element.find('#target-b'), true);
    this.assertIsCollapsed(element.find('#target-c01'), false);
    this.assertIsCollapsed(element.find('#target-c02'), false);
    this.assertIsCollapsed(element.find('#target-c03'), false);

    element.find('.trigger-a').trigger('click');
    element.find('.trigger-b').trigger('click');
    element.find('.trigger-c').trigger('click');

    this.assertIsCollapsed(element.find('#target-a'), true);
    this.assertIsCollapsed(element.find('#target-b'), false);
    this.assertIsCollapsed(element.find('#target-c01'), true);
    this.assertIsCollapsed(element.find('#target-c02'), true);
    this.assertIsCollapsed(element.find('#target-c03'), true);
});

QUnit.test('creme.widget.Toggle.toggle (outside)', function(assert) {
    var element = $(this.createToggleHtml({
        triggers: [{
            collapsed: true,
            target: '#target-a',
            classes: 'trigger-a'
        }]
    })).appendTo(this.qunitFixture());

    var target = $('<div id="target-a"></div>').appendTo(this.qunitFixture());

    var widget = creme.widget.create(element, {
        debounceDelay: 0
    });
    this.assertReady(element);

    assert.equal(widget.triggers().length, 1);

    // trigger is already collapsed -> forced to target
    this.assertIsCollapsed(target, true);

    element.find('.trigger-a').trigger('click');

    this.assertIsCollapsed(target, false);
});

}(jQuery));
