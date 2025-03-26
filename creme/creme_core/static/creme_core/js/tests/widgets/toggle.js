/* globals QUnitWidgetMixin */
(function($) {
/*
function mock_toggle_create(options, noauto) {
    var select =  creme.widget.writeAttr($('<div widget="ui-creme-toggle" class="ui-creme-toggle ui-creme-widget"/>'), options || {});

    if (!noauto) {
        select.addClass('widget-auto');
    }

    return select;
}

function mock_toggle_trigger(options) {
    return creme.widget.writeAttr($('<div class="toggle-trigger"/>'), options || {});
}

function mock_toggle_target(options) {
    return creme.widget.writeAttr($('<div class="toggle-target">'), options || {});
}

function append_mock_toggle_target(element, options) {
    var target = mock_toggle_target(options);
    element.append(target);
    return target;
}

function append_mock_toggle_trigger(element, options) {
    var target = mock_toggle_trigger(options);
    element.append(target);
    return target;
}
*/

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
        equal(element.hasClass('toggle-collapsed'), state, state ? 'toggle is collapsed' : 'toggle is expanded');
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
    deepEqual(widget.triggers().get(), []);

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
    equal(widget.triggers().length, 1);

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

    equal(widget.triggers().length, 3);

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

    equal(widget.triggers().length, 3);

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

    equal(widget.triggers().length, 1);

    // trigger is already collapsed -> forced to target
    this.assertIsCollapsed(target, true);

    element.find('.trigger-a').trigger('click');

    this.assertIsCollapsed(target, false);
});

/*
QUnit.test('creme.widget.Toggle.expand (subtoggle, not recursive)', function(assert) {
    var element = $(this.createToggleHtml({
        collapsed: true,
        isTrigger: true
    }));
    var subElement = $(this.createToggleHtml({
        collapsed: true,
        triggers: [{
            collapsed: true,
            target: '#target-a'
        }],
        targets: ['<div id="target-a"></div>']
    }));

    element.append(subElement);

    var widget = creme.widget.create(element);
    var subWidget = creme.widget.create(subElement);

    this.assertIsCollapsed(element);
    this.assertIsCollapsed(subElement.find('#target-a'));

    widget.expandAll();

    this.assertIsExpanded(element);
    this.assertIsCollapsed(subElement.find('#target-a'));

    subWidget.expandAll();

    this.assertIsExpanded(element);
    this.assertIsExpanded(subElement.find('#target-a'));
});

QUnit.test('creme.widget.Toggle.expand (subtoggle, recursive)', function(assert) {
    var element = mock_toggle_create().addClass('toggle-collapsed');
    var sub_element = mock_toggle_create().addClass('toggle-collapsed');

    element.append(sub_element);

    var widget = creme.widget.create(element);
    var sub_widget = creme.widget.create(sub_element);

    equal(widget.is_opened(), false);
    equal(sub_widget.is_opened(), false);

    widget.expand({recursive: true});

    equal(widget.is_opened(), true);
    equal(sub_widget.is_opened(), true);
});

QUnit.test('creme.widget.Toggle.collapse', function(assert) {
    var element = mock_toggle_create();
    var widget = creme.widget.create(element);
    this.assertReady(element);

    equal(widget.is_opened(), true);
    this.assertToggleIsCollapsed(element);

    widget.collapse();

    equal(widget.is_opened(), false);
    this.assertIsCollapsed(element);

    widget.collapse();

    equal(widget.is_opened(), false);
    this.assertIsCollapsed(element);
});

QUnit.test('creme.widget.Toggle.collapse (subtoggle, not recursive)', function(assert) {
    var element = mock_toggle_create();
    var sub_element = mock_toggle_create();

    element.append(sub_element);

    var widget = creme.widget.create(element);
    var sub_widget = creme.widget.create(sub_element);

    equal(widget.is_opened(), true);
    equal(sub_widget.is_opened(), true);

    widget.collapse();

    equal(widget.is_opened(), false);
    equal(sub_widget.is_opened(), true);
});

QUnit.test('creme.widget.Toggle.collapse (subtoggle, recursive)', function(assert) {
    var element = mock_toggle_create();
    var sub_element = mock_toggle_create();

    element.append(sub_element);

    var widget = creme.widget.create(element);
    var sub_widget = creme.widget.create(sub_element);

    equal(widget.is_opened(), true);
    equal(sub_widget.is_opened(), true);

    widget.collapse({recursive: true});

    equal(widget.is_opened(), false);
    equal(sub_widget.is_opened(), false);
});

QUnit.test('creme.widget.Toggle.toggle (single target)', function(assert) {
    var element = mock_toggle_create().addClass('toggle-collapsed'); ;
    var target = append_mock_toggle_target(element, {'toggle-open-rowspan': 1, 'toggle-close-rowspan': 5});

    var widget = creme.widget.create(element);
    this.assertReady(element);

    this.assertIsCollapsed(element);
    this.assertIsCollapsed(target);
    equal(target.attr('rowspan'), 5);

    widget.toggle(true);

    this.assertToggleIsCollapsed(element);
    this.assertToggleIsCollapsed(target);
    equal(target.attr('rowspan'), 1);

    widget.toggle(false);

    this.assertIsCollapsed(element);
    this.assertIsCollapsed(target);
    equal(target.attr('rowspan'), 5);
});

QUnit.test('creme.widget.Toggle.toggle (multiple targets)', function(assert) {
    var element = mock_toggle_create().addClass('toggle-collapsed');
    var target1 = append_mock_toggle_target(element, {'toggle-open-rowspan': 1, 'toggle-close-rowspan': 5});
    var target2 = append_mock_toggle_target(element, {'toggle-open-rowspan': 8, 'toggle-close-rowspan': 4});

    var widget = creme.widget.create(element);
    this.assertReady(element);

    this.assertIsCollapsed(element);
    this.assertIsCollapsed(target1);
    this.assertIsCollapsed(target2);
    equal(target1.attr('rowspan'), 5);
    equal(target2.attr('rowspan'), 4);

    widget.toggle(true);

    this.assertToggleIsCollapsed(element);
    this.assertToggleIsCollapsed(target1);
    this.assertToggleIsCollapsed(target2);
    equal(target1.attr('rowspan'), 1);
    equal(target2.attr('rowspan'), 8);

    widget.toggle(false);

    this.assertIsCollapsed(element);
    this.assertIsCollapsed(target1);
    this.assertIsCollapsed(target2);
    equal(target1.attr('rowspan'), 5);
    equal(target2.attr('rowspan'), 4);
});

QUnit.test('creme.widget.Toggle.toggle (attributes)', function(assert) {
    var element = mock_toggle_create().addClass('toggle-collapsed');
    var target1 = append_mock_toggle_target(element, {'toggle-open-rowspan': 1,
'toggle-close-rowspan': 5,
                                                      'toggle-open-name': 'open',
'toggle-close-name': 'close'});
    var target2 = append_mock_toggle_target(element, {'toggle-open-rowspan': 8, 'toggle-close-rowspan': 4});

    var widget = creme.widget.create(element);

    this.assertReady(element);

    equal(target1.attr('rowspan'), 5);
    equal(target1.attr('name'), 'close');

    equal(target2.attr('rowspan'), 4);
    equal(target2.attr('name'), undefined);

    widget.toggle(true);

    equal(target1.attr('rowspan'), 1);
    equal(target1.attr('name'), 'open');

    equal(target2.attr('rowspan'), 8);
    equal(target2.attr('name'), undefined);

    widget.toggle(false);

    equal(target1.attr('rowspan'), 5);
    equal(target1.attr('name'), 'close');

    equal(target2.attr('rowspan'), 4);
    equal(target2.attr('name'), undefined);
});

QUnit.test('creme.widget.Toggle.toggle (callback)', function(assert) {
    var self = this;

    equal(self.mock_collapsed, undefined);
    equal(self.mock_options, undefined);

    var element = mock_toggle_create().addClass('toggle-collapsed');
    var widget = creme.widget.create(element, {
        'ontoggle': function(collapsed, options) {
            self.mock_collapsed = collapsed;
            self.mock_options = options;
         }
    });

    equal(self.mock_collapsed, undefined);
    equal(self.mock_options, undefined);

    widget.expand();
    equal(self.mock_collapsed, false);
    deepEqual(self.mock_options, {});

    widget.collapse({recursive: true});
    equal(self.mock_collapsed, true);
    deepEqual(self.mock_options, {recursive: true});
});

QUnit.test('creme.widget.Toggle.toggle (callback script)', function(assert) {
    equal(window.LAST_CREME_WIDGET_TOGGLE_STATE, undefined);

    var element = mock_toggle_create({'ontoggle': 'window.LAST_CREME_WIDGET_TOGGLE_STATE = !collapsed;'}).addClass('toggle-collapsed');
    var widget = creme.widget.create(element);

    equal(window.LAST_CREME_WIDGET_TOGGLE_STATE, undefined);

    widget.expand();
    equal(window.LAST_CREME_WIDGET_TOGGLE_STATE, true);

    widget.collapse();
    equal(window.LAST_CREME_WIDGET_TOGGLE_STATE, false);

    delete window['LAST_CREME_WIDGET_TOGGLE_STATE'];
});

QUnit.test('creme.widget.Toggle.trigger (single target, click)', function(assert) {
    var element = mock_toggle_create().addClass('toggle-collapsed'); ;
    var target = append_mock_toggle_target(element, {'toggle-open-rowspan': 8, 'toggle-close-rowspan': 4});
    var trigger = append_mock_toggle_trigger(element, {});

    creme.widget.create(element);

    this.assertReady(element);
    equal(target.attr('rowspan'), 4);

    trigger.trigger('click');
    equal(target.attr('rowspan'), 8);

    trigger.trigger('click');
    equal(target.attr('rowspan'), 4);
});

QUnit.test('creme.widget.Toggle.trigger (single target, over)', function(assert) {
    var element = mock_toggle_create().addClass('toggle-collapsed');
    var target = append_mock_toggle_target(element, {'toggle-open-rowspan': 8, 'toggle-close-rowspan': 4});
    var trigger = append_mock_toggle_trigger(element, {'toggle-event': 'over'});

    creme.widget.create(element);

    this.assertReady(element);
    equal(target.attr('rowspan'), 4);

    trigger.trigger('click');
    equal(target.attr('rowspan'), 4);

    trigger.trigger('over');
    equal(target.attr('rowspan'), 8);

    trigger.trigger('click');
    equal(target.attr('rowspan'), 8);

    trigger.trigger('over');
    equal(target.attr('rowspan'), 4);
});

QUnit.test('creme.widget.Toggle.trigger (multiple targets)', function(assert) {
    var element = mock_toggle_create().addClass('toggle-collapsed');
    var target1 = append_mock_toggle_target(element, {'toggle-open-rowspan': 1,
'toggle-close-rowspan': 5,
                                                      'toggle-open-name': 'open',
'toggle-close-name': 'close'});
    var target2 = append_mock_toggle_target(element, {'toggle-open-rowspan': 8, 'toggle-close-rowspan': 4});
    var trigger = append_mock_toggle_trigger(element, {});
    creme.widget.create(element);

    this.assertReady(element);

    equal(target1.attr('rowspan'), 5);
    equal(target1.attr('name'), 'close');

    equal(target2.attr('rowspan'), 4);
    equal(target2.attr('name'), undefined);

    trigger.trigger('click');

    equal(target1.attr('rowspan'), 1);
    equal(target1.attr('name'), 'open');

    equal(target2.attr('rowspan'), 8);
    equal(target2.attr('name'), undefined);

    trigger.trigger('click');

    equal(target1.attr('rowspan'), 5);
    equal(target1.attr('name'), 'close');

    equal(target2.attr('rowspan'), 4);
    equal(target2.attr('name'), undefined);
});
*/
}(jQuery));
