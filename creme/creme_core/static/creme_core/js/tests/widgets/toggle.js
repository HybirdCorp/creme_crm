(function($) {

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

QUnit.module("creme.widgets.toggle.js", new QUnitMixin());

function assertActive(element) {
    equal(element.hasClass('widget-active'), true, 'is widget active');
}

function assertReady(element) {
    assertActive(element);
    equal(element.hasClass('widget-ready'), true, 'is widget ready');
}

function assertToggleOpen(element) {
    equal(element.hasClass('toggle-collapsed'), false, 'element opened');
}

function assertToggleClose(element) {
    equal(element.hasClass('toggle-collapsed'), true, 'element closed');
}

QUnit.test('creme.widget.Toggle.create (opened)', function(assert) {
    var element = mock_toggle_create();
    var widget = creme.widget.create(element);
    assertReady(element);

    assertToggleOpen(element);
    equal(widget.is_opened(), true);
    equal(widget.is_closed(), false);
});

QUnit.test('creme.widget.Toggle.create (close)', function(assert) {
    var element = mock_toggle_create().addClass('toggle-collapsed');
    var widget = creme.widget.create(element);
    assertReady(element);

    assertToggleClose(element);
    equal(widget.is_opened(), false);
    equal(widget.is_closed(), true);
});

QUnit.test('creme.widget.Toggle.expand', function(assert) {
    var element = mock_toggle_create().addClass('toggle-collapsed');
    var widget = creme.widget.create(element);
    assertReady(element);

    equal(widget.is_opened(), false);
    assertToggleClose(element);

    widget.expand();

    equal(widget.is_opened(), true);
    assertToggleOpen(element);

    widget.expand();

    equal(widget.is_opened(), true);
    assertToggleOpen(element);
});

QUnit.test('creme.widget.Toggle.expand (subtoggle, not recursive)', function(assert) {
    var element = mock_toggle_create().addClass('toggle-collapsed');
    var sub_element = mock_toggle_create().addClass('toggle-collapsed');

    element.append(sub_element);

    var widget = creme.widget.create(element);
    var sub_widget = creme.widget.create(sub_element);

    equal(widget.is_opened(), false);
    equal(sub_widget.is_opened(), false);

    widget.expand();

    equal(widget.is_opened(), true);
    equal(sub_widget.is_opened(), false);
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
    assertReady(element);

    equal(widget.is_opened(), true);
    assertToggleOpen(element);

    widget.collapse();

    equal(widget.is_opened(), false);
    assertToggleClose(element);

    widget.collapse();

    equal(widget.is_opened(), false);
    assertToggleClose(element);
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
    assertReady(element);

    assertToggleClose(element);
    assertToggleClose(target);
    equal(target.attr('rowspan'), 5);

    widget.toggle(true);

    assertToggleOpen(element);
    assertToggleOpen(target);
    equal(target.attr('rowspan'), 1);

    widget.toggle(false);

    assertToggleClose(element);
    assertToggleClose(target);
    equal(target.attr('rowspan'), 5);
});

QUnit.test('creme.widget.Toggle.toggle (multiple targets)', function(assert) {
    var element = mock_toggle_create().addClass('toggle-collapsed');
    var target1 = append_mock_toggle_target(element, {'toggle-open-rowspan': 1, 'toggle-close-rowspan': 5});
    var target2 = append_mock_toggle_target(element, {'toggle-open-rowspan': 8, 'toggle-close-rowspan': 4});

    var widget = creme.widget.create(element);
    assertReady(element);

    assertToggleClose(element);
    assertToggleClose(target1);
    assertToggleClose(target2);
    equal(target1.attr('rowspan'), 5);
    equal(target2.attr('rowspan'), 4);

    widget.toggle(true);

    assertToggleOpen(element);
    assertToggleOpen(target1);
    assertToggleOpen(target2);
    equal(target1.attr('rowspan'), 1);
    equal(target2.attr('rowspan'), 8);

    widget.toggle(false);

    assertToggleClose(element);
    assertToggleClose(target1);
    assertToggleClose(target2);
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

    assertReady(element);

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

    assertReady(element);
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

    assertReady(element);
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

    assertReady(element);

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
}(jQuery));
