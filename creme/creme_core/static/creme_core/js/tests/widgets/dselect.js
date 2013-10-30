MockDynamicSelect = function(backend) {
    return $.extend({}, creme.widget.DynamicSelect, {
        options: {
            url:'',
            backend: backend,
            datatype: 'string',
            filter: ''
        }
    });
};

function mock_dselect_create(url, noauto) {
    var select = $('<select widget="ui-creme-dselect" class="ui-creme-dselect ui-creme-widget"/>');

    if (url !== undefined)
        select.attr('url', url);

    if (!noauto)
        select.addClass('widget-auto');

    return select;
}

function mock_dselect_add_choice(element, label, value) {
    var choice = $('<option value="' + (value.replace ? value.replace(/\"/g, '&quot;') : value) + '">' + label + '</option>');
    $(element).append(choice);
    return choice;
}

function mock_dselect_add_group(element, label) {
    var group = $('<optgroup label="' + (label.replace ? label.replace(/\"/g, '&quot;') : label) + '"></optgroup>');
    $(element).append(group);
    return group;
}

module("creme.widgets.dselect.js", {
  setup: function() {
      this.backend = new creme.ajax.MockAjaxBackend({sync:true});
      $.extend(this.backend.GET, {'mock/options': this.backend.response(200, [[1, 'a'], [15, 'b'], [12.5, 'c']]),
                                  'mock/options/42': this.backend.response(200, [[1, 'a'], [15, 'b'], [12.5, 'c']]),
                                  'mock/options/empty': this.backend.response(200, []),
                                  'mock/forbidden': this.backend.response(403, 'HTTP - Error 403'),
                                  'mock/error': this.backend.response(500, 'HTTP - Error 500')});

      creme.widget.unregister('ui-creme-dselect');
      creme.widget.declare('ui-creme-dselect', new MockDynamicSelect(this.backend));
  },
  teardown: function() {
  }
});

test('creme.widget.DynamicSelect.create (empty)', function() {
    var element = mock_dselect_create();

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

test('creme.widget.DynamicSelect.create (static)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(widget.delegate._enabled, true);
    equal(element.is('[disabled]'), false);

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    deepEqual([1, 'a'], element.creme().widget().choice(1));
    deepEqual([5, 'b'], element.creme().widget().choice(5));
    deepEqual([3, 'c'], element.creme().widget().choice(3));
});

test('creme.widget.DynamicSelect.create (static, disabled)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);

    element.attr('disabled', '');
    equal(element.is('[disabled]'), true);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-ready'), true);

    equal(widget.delegate._enabled, false);
    equal(element.is('[disabled]'), true);

    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);

    equal(element.is('[disabled]'), false);

    var widget = creme.widget.create(element, {disabled: true});

    equal(widget.delegate._enabled, false);
    equal(element.is('[disabled]'), true);
});

test('creme.widget.DynamicSelect.create (static, empty url)', function() {
    var element = mock_dselect_create('');
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    deepEqual([1, 'a'], element.creme().widget().choice(1));
    deepEqual([5, 'b'], element.creme().widget().choice(5));
    deepEqual([3, 'c'], element.creme().widget().choice(3));
});


test('creme.widget.DynamicSelect.create (url)', function() {
    var element = mock_dselect_create('mock/options');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('a', $('option:nth(0)', element).text());

    equal('15', $('option:nth(1)', element).attr('value'));
    equal('b', $('option:nth(1)', element).text());

    equal('12.5', $('option:nth(2)', element).attr('value'));
    equal('c', $('option:nth(2)', element).text());

    deepEqual([1, 'a'], element.creme().widget().choice(1));
    deepEqual([15, 'b'], element.creme().widget().choice(15));
    deepEqual([12.5, 'c'], element.creme().widget().choice(12.5));
});

test('creme.widget.DynamicSelect.create (unknown url)', function() {
    var element = mock_dselect_create('unknown');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

test('creme.widget.DynamicSelect.destroy', function() {
    var element = mock_dselect_create('mock/options');

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

    element.creme().widget().destroy();
    equal(element.creme().widget(), undefined);
    equal(element.hasClass('widget-active'), false);
    equal(element.hasClass('widget-ready'), false);

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));
});

test('creme.widget.DynamicSelect.choices', function()
{
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    creme.widget.create(element);
    equal(element.creme().widget().url(), "");

    deepEqual(element.creme().widget().choices(), [['1', 'a'], ['5', 'b'], ['3', 'c']]);
    deepEqual(element.creme().widget().choice('1'), ['1', 'a']);
    deepEqual(element.creme().widget().choice('5'), ['5', 'b']);
    deepEqual(element.creme().widget().choice('3'), ['3', 'c']);
    equal(element.creme().widget().choice('15'), undefined);
});

test('creme.widget.DynamicSelect.choices (json)', function()
{
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', $.toJSON({id:1, name:'a'}));
    mock_dselect_add_choice(element, 'b', $.toJSON({id:5, name:'b'}));
    mock_dselect_add_choice(element, 'c', $.toJSON({id:3, name:'c'}));

    creme.widget.create(element);
    equal(element.creme().widget().url(), "");

    deepEqual(element.creme().widget().choices(), [[$.toJSON({id:1, name:'a'}), 'a'], 
                                                   [$.toJSON({id:5, name:'b'}), 'b'], 
                                                   [$.toJSON({id:3, name:'c'}), 'c']]);
    deepEqual(element.creme().widget().choice($.toJSON({id:1, name:'a'})), [$.toJSON({id:1, name:'a'}), 'a']);
    deepEqual(element.creme().widget().choice($.toJSON({id:5, name:'b'})), [$.toJSON({id:5, name:'b'}), 'b']);
    deepEqual(element.creme().widget().choice($.toJSON({id:3, name:'c'})), [$.toJSON({id:3, name:'c'}), 'c']);
    equal(element.creme().widget().choice('15'), undefined);
});

test('creme.widget.DynamicSelect.groups', function() {
    var element = mock_dselect_create();

    var group1 = mock_dselect_add_group(element, 'group1');
    mock_dselect_add_choice(group1, 'a', 1);
    mock_dselect_add_choice(group1, 'b', 5);

    var group2 = mock_dselect_add_group(element, 'group2');
    mock_dselect_add_choice(element, 'c', 3);

    var widget = creme.widget.create(element);

    deepEqual(element.creme().widget().choices(), [['1', 'a'], ['5', 'b'], ['3', 'c']]);
    deepEqual(element.creme().widget().choice('1'), ['1', 'a']);
    deepEqual(element.creme().widget().choice('5'), ['5', 'b']);
    deepEqual(element.creme().widget().choice('3'), ['3', 'c']);
    equal(element.creme().widget().choice('15'), undefined);

    deepEqual(element.creme().widget().groups(), ['group1', 'group2']);
});

test('creme.widget.DynamicSelect.url (static, unknown url)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    creme.widget.create(element);
    equal(element.creme().widget().url(), "");

    var response = [];
    element.creme().widget().model().one({
        'fetch-done': function() {response.push('ok');},
        'fetch-error': function() {response.push('error');}
    });

    element.creme().widget().url('unknown');
    deepEqual(response, ['error']);

    equal(element.creme().widget().url(), 'unknown');
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
});

test('creme.widget.DynamicSelect.url (url, unknown url)', function() {
    var element = mock_dselect_create('mock/options');

    creme.widget.create(element);
    equal(element.creme().widget().url(), "mock/options");
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

    var response = [];
    element.creme().widget().model().one({
        'fetch-done': function() {response.push('ok');},
        'fetch-error': function() {response.push('error');}
    });

    element.creme().widget().url('unknown');
    deepEqual(response, ['error']);

    equal(element.creme().widget().url(), 'unknown');
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

test('creme.widget.DynamicSelect.url (static)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    creme.widget.create(element);
    equal(element.creme().widget().url(), "");
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    element.creme().widget().url('mock/options');

    equal(element.creme().widget().url(), 'mock/options');
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

    element.creme().widget().url('mock/options/empty');

    equal(element.creme().widget().url(), 'mock/options/empty');
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

test('creme.widget.DynamicSelect.reload (template url)', function() {
    var element = mock_dselect_create('mock/${name}${content}');
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    creme.widget.create(element);
    equal(element.creme().widget().url(), '');

    var response = [];
    element.creme().widget().reload({name:'options', content:''},
                                    function() {response.push('ok');}, function() {response.push('error');});
    deepEqual(response, ['ok'], 'template');

    equal(element.creme().widget().url(), 'mock/options');
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

    response = [];
    element.creme().widget().reload({name:'options', content:'/empty'},
                                    function() {response.push('ok');}, function() {response.push('error');});
    deepEqual(response, ['ok'], 'other template data');

    equal(element.creme().widget().url(), 'mock/options/empty');
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);

    // invalid template (url is incomplete)
    response = [];
    element.creme().widget().model().one({
        'fetch-done': function() {response.push('ok');},
        'fetch-error': function() {response.push('error');}
    });
    element.creme().widget().url('');
    deepEqual(response, [], 'empty template');

    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);

    // force template in widgetoptions.url
    response = [];
    element.creme().widget().model().unbind(['fetch-done', 'fetch-error']);
    element.creme().widget().model().one({
        'fetch-done': function() {response.push('ok');},
        'fetch-error': function() {response.push('error');}
    });

    element.creme().widget().url('mock/${name}');
    deepEqual(['ok'], response, 'updated template data');

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));
});

test('creme.widget.DynamicSelect.update (undefined)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    creme.widget.create(element);

    element.creme().widget().update(undefined);
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    element.creme().widget().update(null);
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
});

test('creme.widget.DynamicSelect.update (add)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    creme.widget.create(element);

    element.creme().widget().update({added:[[15, 'd'], [6, 'e']]});
    equal(5, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('15', $('option:nth(3)', element).attr('value'));
    equal('6', $('option:nth(4)', element).attr('value'));

    element.creme().widget().update('{"added":[[17, "f"], [35, "g"]]}');
    equal(7, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('15', $('option:nth(3)', element).attr('value'));
    equal('6', $('option:nth(4)', element).attr('value'));
    equal('17', $('option:nth(5)', element).attr('value'));
    equal('35', $('option:nth(6)', element).attr('value'));
});

test('creme.widget.DynamicSelect.update (remove)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);
    mock_dselect_add_choice(element, 'd', 33.5);
    mock_dselect_add_choice(element, 'e', 12);

    creme.widget.create(element);

    element.creme().widget().update({removed:[[1, 'a'], [33.5, 'd']]})
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('5', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));
    equal('12', $('option:nth(2)', element).attr('value'));

    element.creme().widget().update({removed:[[152, 'x'], [112, 'y']]})
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('5', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));
    equal('12', $('option:nth(2)', element).attr('value'));

    element.creme().widget().update({removed:[[5, 'b'], [3, 'c'], [12, 'e']]})
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);

    element.creme().widget().update({removed:[[5, 'b'], [3, 'c'], [12, 'e']]})
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

test('creme.widget.DynamicSelect.update (add/remove)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    creme.widget.create(element);

    element.creme().widget().update({added:[[5, 'bb']], removed:[5]})
    equal(3, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));
    equal('5', $('option:nth(2)', element).attr('value'));
    equal('bb', $('option:nth(2)', element).text());
});

test('creme.widget.DynamicSelect.val (static)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    creme.widget.create(element);
    equal(3, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    deepEqual(['1', 'a'], element.creme().widget().firstchoice());
    equal('1', element.creme().widget().val());

    element.creme().widget().val(3);
    equal('3', element.creme().widget().val());

    element.creme().widget().val(15);
    equal('1', element.creme().widget().val());
});

test('creme.widget.DynamicSelect.val (reload)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    this.backend.GET['mock/options'] = this.backend.response(200, [[1, 'a'], [24, 'b'], [5, 'D'], [12.5, 'c']]);

    creme.widget.create(element);

    element.creme().widget().val(5);
    deepEqual(element.creme().widget().selected(), ['5', 'b']);

    element.creme().widget().url('mock/options');
    deepEqual(element.creme().widget().selected(), ['5', 'D']);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('24', $('option:nth(1)', element).attr('value'));
    equal('5', $('option:nth(2)', element).attr('value'));
    equal('12.5', $('option:nth(3)', element).attr('value'));
});

test('creme.widget.DynamicSelect.val (reload, not exists)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    this.backend.GET['mock/options'] = this.backend.response(200, [[1, 'a'], [24, 'b'], [5, 'D'], [12.5, 'c']]);

    creme.widget.create(element);

    element.creme().widget().val(3);
    deepEqual(element.creme().widget().selected(), ['3', 'c']);

    element.creme().widget().url('mock/options');
    deepEqual(element.creme().widget().selected(), ['1', 'a']);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('24', $('option:nth(1)', element).attr('value'));
    equal('5', $('option:nth(2)', element).attr('value'));
    equal('12.5', $('option:nth(3)', element).attr('value'));
});

test('creme.widget.DynamicSelect.reset', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    var widget = creme.widget.create(element);

    widget.val(5);
    deepEqual(widget.selected(), ['5', 'b']);

    widget.reset();
    deepEqual(widget.selected(), ['1', 'a']);
});

test('creme.widget.DynamicSelect.filter (script)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    element.attr('filter', 'item.value < 4');

    var widget = creme.widget.create(element);
    equal('item.value < 4', widget.element.attr('filter'));
    equal('item.value < 4', widget.filter());

    equal(2, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));
});

test('creme.widget.DynamicSelect.filter (script update)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    var widget = creme.widget.create(element);
    equal(3, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    widget.filter('item.value < 4');

    equal(2, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));

    widget.filter('item.value > 4');

    equal(1, $('option', element).length);
    equal('5', $('option:nth(0)', element).attr('value'));

    widget.filter("item.label !== 'c'");

    equal(2, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
});

test('creme.widget.DynamicSelect.filter (template)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);
    mock_dselect_add_choice(element, 'd', 7);
    mock_dselect_add_choice(element, 'e', 4);

    var widget = creme.widget.create(element);
    deepEqual([], widget.dependencies());
    
    equal(5, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('7', $('option:nth(3)', element).attr('value'));
    equal('4', $('option:nth(4)', element).attr('value'));

    widget.filter('item.value < ${max}');
    deepEqual(['max'], widget.dependencies());

    equal(5, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('7', $('option:nth(3)', element).attr('value'));
    equal('4', $('option:nth(4)', element).attr('value'));

    widget.reload({max: 4});

    equal(2, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));

    widget.reload({max: 6});

    equal(4, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('4', $('option:nth(3)', element).attr('value'));
});

test('creme.widget.DynamicSelect.filter (context)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);
    mock_dselect_add_choice(element, 'd', 7);
    mock_dselect_add_choice(element, 'e', 4);

    var widget = creme.widget.create(element, {dependencies:['max']});
    deepEqual(['max'], widget.dependencies());
    
    equal(5, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('7', $('option:nth(3)', element).attr('value'));
    equal('4', $('option:nth(4)', element).attr('value'));

    widget.filter('item.value < (context.max ? context.max : 10000)');
    deepEqual(['max'], widget.dependencies());

    equal(5, $('option', element).length, '');
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('7', $('option:nth(3)', element).attr('value'));
    equal('4', $('option:nth(4)', element).attr('value'));

    widget.reload({max: 4});

    equal(2, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));

    widget.reload({max: 6});

    equal(4, $('option', element).length);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
    equal('4', $('option:nth(3)', element).attr('value'));
});
