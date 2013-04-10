MockDynamicSelect = function(backend) {
    return $.extend({}, creme.widget.DynamicSelect, {
        options: {
            url:'',
            backend: backend,
            datatype: 'string'
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
    var choice = $('<option value="' + value + '">' + label + '</option>');
    $(element).append(choice);
    return choice;
}

function mock_dselect_add_group(element, label) {
    var group = $('<optgroup label="' + label + '"></optgroup>');
    $(element).append(group);
    return group;
}

module("creme.widgets.dselect.js", {
  setup: function() {
      this.backend = new creme.ajax.MockAjaxBackend({sync:true});
      $.extend(this.backend.GET, {'mock/options': this.backend.response(200, [[1, 'a'], [15, 'b'], [12.5, 'c']]),
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

    deepEqual(element.creme().widget().groups(), ['group1', 'group2']);
});

test('creme.widget.DynamicSelect.reload (static, unknown url)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    creme.widget.create(element);
    equal(element.creme().widget().url(), "");

    assertHTMLEqual(element.creme().widget().delegate._initial, '<option value="1">a</option>' +
                                                                '<option value="5">b</option>' +
                                                                '<option value="3">c</option>');

    var response = [];
    element.creme().widget().reload('unknown', function() {response.push('ok');}, function() {response.push('error');});
    deepEqual(response, ['error']);

    equal(element.creme().widget().url(), 'unknown');
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));
});

test('creme.widget.DynamicSelect.reload (url, unknown url)', function() {
    var element = mock_dselect_create('mock/options');

    creme.widget.create(element);
    equal(element.creme().widget().url(), "mock/options");
    deepEqual(element.creme().widget().delegate._initial, '');

    var response = [];
    element.creme().widget().reload('unknown', function() {response.push('ok');}, function() {response.push('error');});
    deepEqual(response, ['error']);

    equal(element.creme().widget().url(), 'unknown');
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

test('creme.widget.DynamicSelect.reload (static)', function() {
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

    element.creme().widget().reload('mock/options');

    equal(element.creme().widget().url(), 'mock/options');
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

    element.creme().widget().reload('mock/options/empty');

    equal(element.creme().widget().url(), 'mock/options/empty');
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);
});

test('creme.widget.DynamicSelect.reload (template url)', function() {
    var element = mock_dselect_create();
    mock_dselect_add_choice(element, 'a', 1);
    mock_dselect_add_choice(element, 'b', 5);
    mock_dselect_add_choice(element, 'c', 3);

    creme.widget.create(element);
    equal(element.creme().widget().url(), "");

    var response = [];
    element.creme().widget().reload(['mock/${name}${content}', {name:'options', content:''}],
                                    function() {response.push('ok');}, function() {response.push('error');});
    deepEqual(response, ['ok'], 'template');

    equal(element.creme().widget().url(), 'mock/options');
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('15', $('option:nth(1)', element).attr('value'));
    equal('12.5', $('option:nth(2)', element).attr('value'));

    response = [];
    element.creme().widget().reload(['mock/${name}${content}', {name:'options', content:'/empty'}],
                                    function() {response.push('ok');}, function() {response.push('error');});
    deepEqual(response, ['ok'], 'other template data');

    equal(element.creme().widget().url(), 'mock/options/empty');
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);

    // invalid template (url is empty)
    response = [];
    element.creme().widget().delegate.previous = undefined;
    element.creme().widget().reload(['', {name:'options', content:''}],
                                    function() {response.push('ok');}, function() {response.push('error');});
    deepEqual(response, ['error'], 'empty template');

    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('1', $('option:nth(0)', element).attr('value'));
    equal('5', $('option:nth(1)', element).attr('value'));
    equal('3', $('option:nth(2)', element).attr('value'));

    // force template in widgetoptions.url
    response = [];
    element.creme().widget().reload(['mock/${name}${content}', {name:'options', content:''}],
                                    function() {response.push('ok');}, function() {response.push('error');});
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

    element.creme().widget().update({removed:[1, 33.5]})
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('5', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));
    equal('12', $('option:nth(2)', element).attr('value'));

    element.creme().widget().update({removed:[152, 112]})
    equal(3, $('option', element).length);
    equal(element.is(':disabled'), false);
    equal('5', $('option:nth(0)', element).attr('value'));
    equal('3', $('option:nth(1)', element).attr('value'));
    equal('12', $('option:nth(2)', element).attr('value'));

    element.creme().widget().update({removed:[5, 3, 12]})
    equal(0, $('option', element).length);
    equal(element.is(':disabled'), true);

    element.creme().widget().update({removed:[5, 3, 12]})
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

    element.creme().widget().reload('mock/options');
    deepEqual(element.creme().widget().selected(), ['5', 'D']);
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
