function mock_actionlist_create(noauto)
{
    var element = creme.widget.buildTag($('<ul/>'), 'ui-creme-actionbuttonlist', {}, !noauto)
                       .append($('<li class="delegate"/>'));

    return element;
}

function mock_actionlist_delegate(element, delegate)
{
    $('> li.delegate', element).empty().append(delegate);
}

function mock_actionlist_add(element, options)
{
    var button = creme.widget.writeAttr($('<button/>').addClass('ui-creme-actionbutton'), options);
    element.append($('<li/>').append(button));
}

function assertAction(action, name, label, type, url, enabled)
{
    equal(creme.object.isempty(action), false);

    if (creme.object.isempty(action))
        return;

    equal(action.attr('name'), name);
    equal(action.attr('label'), label);
    equal(action.attr('action'), type);
    equal(action.attr('url'), url);
    equal(action.attr('disabled') === undefined, enabled)
}

module("creme.widgets.actionlist.js", {
  setup: function() {
      this.backend = new MockAjaxBackend({sync:true});
      $.extend(this.backend.GET, {'mock/options': this.backend.response(200, [[15, 'a'], [5, 'b'], [3, 'c'], [14, 't'], [42, 'y']]),
                                  'mock/rtype/1/options': this.backend.response(200, [['rtype.1', 'a'], ['rtype.12', 'b'], ['rtype.3', 'c']]),
                                  'mock/rtype/5/options': this.backend.response(200, [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]),
                                  'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                  'mock/error': this.backend.response(500, 'HTTP - Error 500')});

      creme.widget.unregister('ui-creme-dselect');
      creme.widget.declare('ui-creme-dselect', new MockDynamicSelect(this.backend));
  },
  teardown: function() {
  }
});

test('creme.widgets.actionlist.create (no delegate, no action)', function() {
    var element = mock_actionlist_create();
    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), '');
    equal(widget.delegate().length, 0);
    equal(widget.actions().length, 0);
    deepEqual(widget.dependencies(), []);
});

test('creme.widgets.actionlist.create (no delegate)', function() {
    var element = mock_actionlist_create();
    mock_actionlist_add(element, {name: 'create', label: 'create', url: 'mock/create/popup'});

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.val(), '');
    equal(widget.delegate().length, 0);
    equal(widget.actions().length, 1);
    deepEqual(widget.dependencies(), []);
});

test('creme.widgets.actionlist.create', function() {
    var delegate = mock_dselect_create();
    mock_dselect_add_choice(delegate, 'a', 1);
    mock_dselect_add_choice(delegate, 'b', 5);
    mock_dselect_add_choice(delegate, 'c', 3);

    var element = mock_actionlist_create();
    mock_actionlist_delegate(element, delegate);
    mock_actionlist_add(element, {name: 'create', label: 'create', url: 'mock/create/popup'});

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(widget.delegate().length, 1);
    equal(widget.actions().length, 1);

    equal(widget.val(), 1);
    deepEqual(widget.dependencies(), []);

    equal(delegate.hasClass('widget-active'), true);
    equal(delegate.hasClass('widget-ready'), true);

    equal(delegate.creme().widget().val(), 1);
    deepEqual(delegate.creme().widget().dependencies(), []);
});

test('creme.widgets.actionlist.dependencies (url delegate)', function() {
    var delegate = mock_dselect_create('mock/${ctype}/options', true);

    var element = mock_actionlist_create();
    mock_actionlist_delegate(element, delegate);
    mock_actionlist_add(element, {name: 'create', label: 'create', url: 'mock/create/popup'});

    var widget = creme.widget.create(element);
    deepEqual(delegate.creme().widget().dependencies(), ['ctype']);
    deepEqual(widget.dependencies(), ['ctype']);
});

// TODO : add dependency support for actions
/*
test('creme.widgets.actionlist.dependencies (url actions)', function() {
    var delegate = mock_dselect_create('mock/${ctype}/options', true);
    mock_dselect_add_choice(delegate, 'a', 1);
    mock_dselect_add_choice(delegate, 'b', 5);
    mock_dselect_add_choice(delegate, 'c', 3);

    var element = mock_actionlist_create();
    mock_actionlist_delegate(element, delegate);
    mock_actionlist_add(element, {name: 'create', label: 'create', url: 'mock/create/${rtype}/popup', enabled: true});

    var widget = creme.widget.create(element);
    deepEqual(delegate.creme().widget().dependencies(), ['ctype']);
    deepEqual(widget.dependencies(), ['ctype', 'rtype']);
});
*/

test('creme.widgets.actionlist.value', function()
{
    var delegate = mock_dselect_create(undefined, true);
    mock_dselect_add_choice(delegate, 'a', 1);
    mock_dselect_add_choice(delegate, 'b', 5);
    mock_dselect_add_choice(delegate, 'c', 3);

    var element = mock_actionlist_create();
    mock_actionlist_delegate(element, delegate);
    mock_actionlist_add(element, {name: 'create', label: 'create', url: 'mock/create/popup'});

    var widget = creme.widget.create(element);

    equal(delegate.val(), 1);
    equal(widget.val(), 1);

    widget.val(5);
    equal(delegate.val(), 5);
    equal(widget.val(), 5);

    widget.val(15);
    equal(delegate.val(), 1);
    equal(widget.val(), 1);
});

test('creme.widgets.actionlist.reset', function()
{
    var delegate = mock_dselect_create(undefined, true);
    mock_dselect_add_choice(delegate, 'a', 12);
    mock_dselect_add_choice(delegate, 'b', 5);
    mock_dselect_add_choice(delegate, 'c', 3);

    var element = mock_actionlist_create();
    mock_actionlist_delegate(element, delegate);
    mock_actionlist_add(element, {name: 'create', label: 'create', url: 'mock/create/popup'});

    var widget = creme.widget.create(element);
    widget.val(5);
    equal(delegate.val(), 5);
    equal(widget.val(), 5);

    widget.reset();

    equal(delegate.val(), 12);
    equal(widget.val(), 12);
});

test('creme.widgets.actionlist.reload', function() {
    var delegate = mock_dselect_create(undefined, true);
    mock_dselect_add_choice(delegate, 'a', 1);
    mock_dselect_add_choice(delegate, 'b', 5);
    mock_dselect_add_choice(delegate, 'c', 3);

    var element = mock_actionlist_create();
    mock_actionlist_delegate(element, delegate);
    mock_actionlist_add(element, {name: 'create', label: 'create', url: 'mock/create/popup'});

    var widget = creme.widget.create(element);

    equal(widget.val(), 1);
    deepEqual(widget.dependencies(), []);

    element.creme().widget().reload('mock/options');
    assertDSelect(delegate, '15', [], 'mock/options', [['15', 'a'], ['5', 'b'], ['3', 'c'], ['14', 't'], ['42', 'y']]);

    equal(widget.val(), 15);
    deepEqual(widget.dependencies(), []);

    element.creme().widget().reload(['mock/rtype/${ctype}/options', {ctype: 5}]);
    assertDSelect(delegate, 'rtype.7', ['ctype'], 'mock/rtype/5/options', [['rtype.7', 'x'], ['rtype.22', 'y'], ['rtype.3', 'c']]);

    equal(widget.val(), 'rtype.7');
    deepEqual(widget.dependencies(), ['ctype']);
});

test('creme.widgets.actionlist.action', function() {
    var delegate = mock_dselect_create('mock/${ctype}/options', true);
    mock_dselect_add_choice(delegate, 'a', 1);
    mock_dselect_add_choice(delegate, 'b', 5);
    mock_dselect_add_choice(delegate, 'c', 3);

    var element = mock_actionlist_create();
    mock_actionlist_delegate(element, delegate);
    mock_actionlist_add(element, {name: 'create', label: 'create', url: 'mock/create/popup'});
    mock_actionlist_add(element, {name: 'delete', label: 'delete', url: 'mock/delete/popup', disabled:''});
    mock_actionlist_add(element, {name: 'reset', action:'reset', label: 'reset'});

    var widget = creme.widget.create(element);
    deepEqual(widget.dependencies(), ['ctype']);

    equal(widget.actions().length, 3);
    assertAction(widget.action(0), 'create', 'create', undefined, 'mock/create/popup', true);
    assertAction(widget.action(1), 'delete', 'delete', undefined, 'mock/delete/popup', false);
    assertAction(widget.action(2), 'reset', 'reset', 'reset', undefined, true);
});
