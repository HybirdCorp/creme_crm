(function($) {

var MockWidget = function() {
 return {
    options: {
        initial: 42
    },

    _create: function(element, options, cb, sync) {
        this.reset(element);
        element.addClass('widget-ready');
    },

    reset: function(element) {
        this.val(element, this.options.initial);
    },

    initial: function(element) {
        return this.options.initial;
    },

    _protected: function(element) {
        return 'protected';
    },

    val: function(element, value) {
        var input = creme.widget.input(element);

        if (value !== undefined) {
            return input.val(Object.isString(value) ? value : JSON.stringify(value));
        }

        return input.val();
    },

    jsonval: function(element) {
        return JSON.stringify(this.val(element));
    }
};
};

QUnit.module("creme.widgets.widget.js", new QUnitMixin({
    afterEach: function() {
        creme.widget.unregister('ui-test');
    }
}));

creme.widget.declare('ui-creme-mock', new MockWidget());

function create_widget_element(name, initial, noauto) {
    var value = (initial !== undefined) ? JSON.stringify(initial) : '42';
    var element =  $('<div widget="' + name + '" class="' + name + ' ui-creme-widget widget-auto" initial=\'' + value + '\'>')
                        .append($('<input type="text" class="ui-creme-input ' + name + '"/>'));

    if (noauto) {
        element.removeClass('widget-auto');
    }

    return element;
}

function create_mock(initial) {
    var value = (initial !== undefined) ? JSON.stringify(initial) : '42';
    var element = $('<div widget="ui-creme-mock" class="ui-creme-mock ui-creme-widget widget-auto" initial=\'' + value + '\'>')
                       .append($('<input type="text" class="ui-creme-input ui-creme-mock"/>'));

    var widget = creme.widget.create(element);

    equal(typeof widget, 'object');
    equal(typeof widget.delegate, 'object');
    equal(widget.val(), (typeof value !== 'string') ? JSON.stringify(value) : value);

    return element;
}

function create_input(initial) {
    var value = (initial !== undefined ? JSON.stringify(initial) : '42');
    return $('<input type="text" class="ui-creme-input" value="' + value + '"/>');
}

function create_mocks(initials) {
    var element = $('<div>');

    for (var i = 0; i < initials.length; ++i) { element.append(create_mock(initials[i])); }

    return element;
}

function create_inputs(initials) {
    var element = $('<div>');

    for (var i = 0; i < initials.length; ++i) { element.append(create_input(initials[i])); }

    return element;
}

QUnit.test('creme.widget.input', function(assert) {
    equal(creme.widget.input($('<input type="text" class="ui-creme-input mywidget"/>')).length, 0);
    equal(creme.widget.input($('<input type="text" class="ui-creme-input mywidget" widget="otherwidget"/>')).length, 0);
    equal(creme.widget.input($('<input type="text" class="ui-creme-input mywidget" widget="mywidget"/>')).length, 1);

    equal(creme.widget.input($('<div>').append($('<input type="text" class="ui-creme-input mywidget"/>'))).length, 0);
    equal(creme.widget.input($('<div widget="otherwidget">').append($('<input type="text" class="ui-creme-input mywidget"/>'))).length, 0);
    equal(creme.widget.input($('<div widget="mywidget">').append($('<input type="text" class="ui-creme-input mywidget"/>'))).length, 1);

    equal(creme.widget.input($('<div widget="mywidget">').append($('<input type="text" class="ui-creme-input mywidget"/>'))
                                                          .append($('<input type="text" class="ui-creme-input mywidget"/>'))
                                                          .append($('<input type="text" class="ui-creme-input mywidget"/>'))).length, 3);
});

QUnit.test('creme.widget.register', function(assert) {
    equal(creme.widget._widgets['ui-test'], undefined);

    var widget = {
        options: {initial: 42},
        init: function() {},
        clone: function() {}
    };

    creme.widget.register('ui-test', widget);
    deepEqual(creme.widget._widgets['ui-test'], widget);

    creme.widget.unregister('ui-test');
    equal(creme.widget._widgets['ui-test'], undefined);
});

QUnit.test('creme.widget.declare (object)', function(assert) {
    equal(creme.widget._widgets['ui-test'], undefined);

    var widget = new MockWidget();
    equal(widget.destroy, undefined);

    var declared = creme.widget.declare('ui-test', widget);
    equal(typeof declared.destroy, 'function');

    deepEqual(creme.widget._widgets['ui-test'], declared);
});

QUnit.test('creme.widget.declare (object, override method)', function(assert) {
    equal(creme.widget._widgets['ui-test'], undefined);

    var widget = $.extend(new MockWidget(), {
        jsonval: function(element) { return 'overriden jsonval'; }
    });
    equal(widget.destroy, undefined);
    equal(typeof widget.jsonval, 'function');

    var declared = creme.widget.declare('ui-test', widget);
    equal(typeof declared.destroy, 'function');
    equal(typeof declared.jsonval, 'function');

    deepEqual(creme.widget._widgets['ui-test'], declared);
    equal(declared.jsonval($('<div/>')), 'overriden jsonval');
});

QUnit.test('creme.widget.ready', function(assert) {
    var elements = $('<div>').append(create_widget_element('ui-creme-readytest', 12),
                                     create_widget_element('ui-creme-readytest', 13),
                                     create_widget_element('ui-creme-unregistered', 14));

    equal($('.ui-creme-widget', elements).length, 3);
    equal($('.ui-creme-widget.widget-active', elements).length, 0);

    creme.widget.ready(elements);
    equal($('.ui-creme-widget', elements).length, 3);
    equal($('.ui-creme-widget.widget-active', elements).length, 0);

    creme.widget.declare('ui-creme-readytest', new MockWidget());

    creme.widget.ready(elements);
    equal($('.ui-creme-widget', elements).length, 3);
    equal($('.ui-creme-widget.widget-active', elements).length, 2);
    equal($('.ui-creme-widget.widget-active.ui-creme-readytest', elements).length, 2);
    equal($('.ui-creme-widget.ui-creme-unregistered:not(.widget-active)', elements).length, 1);
});

QUnit.test('creme.widget.ready (no auto)', function(assert) {
    creme.widget.declare('ui-creme-readytest', new MockWidget());

    var elements = $('<div>').append(create_widget_element('ui-creme-readytest', 12),
                                     create_widget_element('ui-creme-readytest', 13, true),
                                     create_widget_element('ui-creme-unregistered', 14));

    equal($('.ui-creme-widget', elements).length, 3);
    equal($('.ui-creme-widget.widget-active', elements).length, 0);

    creme.widget.ready(elements);
    equal($('.ui-creme-widget', elements).length, 3);
    equal($('.ui-creme-widget.widget-active', elements).length, 1);
    equal($('.ui-creme-widget.widget-active.ui-creme-readytest', elements).length, 1);
    equal($('.ui-creme-widget.ui-creme-readytest:not(.widget-active)', elements).length, 1);
    equal($('.ui-creme-widget.ui-creme-unregistered:not(.widget-active)', elements).length, 1);
});

QUnit.test('creme.widget.is_valid', function(assert) {
    creme.widget.declare('ui-creme-activatetest', new MockWidget());

    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget" initial="51">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    equal(element.hasClass('widget-active'), false);
    equal(element.hasClass('widget-ready'), false);

    equal(creme.widget.is_valid(element), false);
    creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(creme.widget.is_valid(element), true);
});

QUnit.test('creme.widget.create (not registered)', function(assert) {
    creme.widget.declare('ui-creme-activatetest', new MockWidget());

    var element = $('<div widget="ui-creme-notregistered" class="ui-creme-notregistered ui-creme-widget" initial="51">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-notregistered"/>'));

    equal(creme.widget.create(element), undefined);
    equal(element.hasClass('widget-active'), false);
    equal(element.hasClass('widget-ready'), false);

    equal(element.data('CremeWidget'), undefined);
});

QUnit.test('creme.widget.create (default options)', function(assert) {
    var declared = creme.widget.declare('ui-creme-activatetest', new MockWidget());
    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    notEqual(creme.widget.create(element), undefined);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual(element.data('CremeWidget').delegate, declared);
    deepEqual(element.data('CremeWidget').options(), {initial: 42});
    deepEqual(element.data('CremeWidget').arguments(), {});
});

QUnit.test('creme.widget.create (options)', function(assert) {
    var declared = creme.widget.declare('ui-creme-activatetest', new MockWidget());

    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto" initial="51">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    notEqual(creme.widget.create(element), undefined);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual(element.data('CremeWidget').delegate, $.extend({}, declared, {options: {initial: '51'}}));
    deepEqual(element.data('CremeWidget').options(), {initial: '51'});
    deepEqual(element.data('CremeWidget').arguments(), {});
});

QUnit.test('creme.widget.create (default options, extra options)', function(assert) {
    var declared = creme.widget.declare('ui-creme-activatetest', new MockWidget());
    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto" arg1="value1" arg2="value2">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    notEqual(creme.widget.create(element), undefined);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual(element.data('CremeWidget').delegate, $.extend({}, declared, {arguments: {arg1: 'value1', arg2: 'value2'}}));
    deepEqual(element.data('CremeWidget').options(), {initial: 42});
    deepEqual(element.data('CremeWidget').arguments(), {arg1: 'value1', arg2: 'value2'});
});

QUnit.test('creme.widget.create (default options, extra options, create options)', function(assert) {
    var declared = creme.widget.declare('ui-creme-activatetest', new MockWidget());
    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto" arg1="value1" arg2="value2">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    notEqual(creme.widget.create(element, {initial: 58, other: 'another'}), undefined);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual(element.data('CremeWidget').delegate, $.extend({}, declared, {options: {'initial': 58, other: 'another'},
                                                                            arguments: {arg1: 'value1', arg2: 'value2'}}));
    deepEqual(element.data('CremeWidget').options(), {'initial': 58, other: 'another'});
    deepEqual(element.data('CremeWidget').arguments(), {arg1: 'value1', arg2: 'value2'});
});

QUnit.test('creme.widget.create (twice)', function(assert) {
    var declared = creme.widget.declare('ui-creme-activatetest', new MockWidget());
    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    notEqual(creme.widget.create(element), undefined);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    deepEqual(element.data('CremeWidget').delegate, declared);

    equal(creme.widget.create(element), undefined);
});

QUnit.test('creme.widget.create (multiple instances)', function(assert) {
    creme.widget.declare('ui-creme-activatetest', new MockWidget());
    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto" arg1="value1" arg2="value2">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    var element2 = element.clone();

    var widget = creme.widget.create(element, {initial: 58, other: 'another'});
    var widget2 = creme.widget.create(element2, {initial: 51});

    equal(typeof widget, 'object');
    equal(typeof widget2, 'object');

    deepEqual(widget.options(), {initial: 58, other: 'another'});
    deepEqual(widget2.options(), {initial: 51});
});

QUnit.test('creme.widget.destroy', function(assert) {
    var declared = creme.widget.declare('ui-creme-activatetest', new MockWidget());
    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual(element.data('CremeWidget').delegate, declared);
    deepEqual(element.data('CremeWidget').options(), {'initial': 42});
    deepEqual(element.data('CremeWidget').arguments(), {});

    creme.widget.destroy(element);
    equal(element.hasClass('widget-active'), false);
    equal(element.hasClass('widget-ready'), false);

    equal(element.data('CremeWidget'), undefined);
});


QUnit.test('creme.widget.values_list (setter, inputs: widget, values: null, parser: none)', function(assert) {
    var element = create_mock();
    var input = creme.widget.input(element);

    creme.widget.values_list(element, null);
    equal(input.val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: widget, values: object, parser: none)', function(assert) {
    var element = create_mock();
    var input = creme.widget.input(element);

    creme.widget.values_list(element, 15);
    equal(input.val(), 15);

    creme.widget.values_list(element, ['array']);
    equal(input.val(), 'array');

    creme.widget.values_list(element, {'0': 'dict'});
    equal(input.val(), '{"0":"dict"}');
});

QUnit.test('creme.widget.values_list (setter, inputs: input, values: null, parser: none)', function(assert) {
    var input = create_input(42);
    equal(input.val(), 42);

    creme.widget.values_list(input, null);
    equal(input.val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: input, values: object, parser: none)', function(assert) {
    var input = create_input(42);
    equal(input.val(), 42);

    creme.widget.values_list(input, 15);
    equal(input.val(), 15);

    creme.widget.values_list(input, ['array']);
    equal(input.val(), 'array');

    creme.widget.values_list(input, {'0': 'dict'});
    equal(input.val(), '[object Object]');
});

QUnit.test('creme.widget.values_list (setter, inputs: widget, values: invalid json)', function(assert) {
    var element = create_mock();
    var input = creme.widget.input(element);

    creme.widget.values_list(element, "{'0':'dict'");
    equal(input.val(), "{'0':'dict'");

    creme.widget.values_list(element, "{'0':'dict'", JSON.parse);
    equal(input.val(), "");
});

QUnit.test('creme.widget.values_list (setter, inputs: widget, values: valid json)', function(assert) {
    var element = create_mock();
    var input = creme.widget.input(element);

    creme.widget.values_list(element, '{"0":"dict",   "1":  15}');
    equal(input.val(), '{"0":"dict",   "1":  15}');

    creme.widget.values_list(element, '{"0":"dict",   "1":  15}', JSON.parse);
    equal(input.val(), '{"0":"dict","1":15}');

    creme.widget.values_list(element, '["0"]');
    equal(input.val(), '["0"]');

    creme.widget.values_list(element, '["0"]', JSON.parse);
    equal(input.val(), 0);
});

QUnit.test('creme.widget.values_list (setter, inputs: multiple input, values: object array)', function(assert) {
    var element = create_inputs([40, 41, 42]);
    var inputs = $('input.ui-creme-input', element);

    equal(inputs.length, 3);
    equal($(inputs[0]).val(), 40);
    equal($(inputs[1]).val(), 41);
    equal($(inputs[2]).val(), 42);

    creme.widget.values_list(inputs, ['a', 'b', 'c']);
    equal($(inputs[0]).val(), 'a');
    equal($(inputs[1]).val(), 'b');
    equal($(inputs[2]).val(), 'c');

    creme.widget.values_list(inputs, ['f', 'g']);
    equal($(inputs[0]).val(), 'f');
    equal($(inputs[1]).val(), 'g');
    equal($(inputs[2]).val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: multiple input, values: invalid json array)', function(assert) {
    var element = create_inputs([40, 41, 42]);
    var inputs = $('input.ui-creme-input', element);

    equal(inputs.length, 3);
    equal($(inputs[0]).val(), 40);
    equal($(inputs[1]).val(), 41);
    equal($(inputs[2]).val(), 42);

    creme.widget.values_list(inputs, '["51", "52", 53', JSON.parse);
    equal($(inputs[0]).val(), '');
    equal($(inputs[1]).val(), '');
    equal($(inputs[2]).val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: multiple input, values: valid json array)', function(assert) {
    var element = create_inputs([40, 41, 42]);
    var inputs = $('input.ui-creme-input', element);

    equal(inputs.length, 3);
    equal($(inputs[0]).val(), 40);
    equal($(inputs[1]).val(), 41);
    equal($(inputs[2]).val(), 42);

    creme.widget.values_list(inputs, '["51", "52", "53"]', JSON.parse);
    equal($(inputs[0]).val(), 51);
    equal($(inputs[1]).val(), 52);
    equal($(inputs[2]).val(), 53);

    creme.widget.values_list(inputs, '["a", "b"]', JSON.parse);
    equal($(inputs[0]).val(), "a");
    equal($(inputs[1]).val(), "b");
    equal($(inputs[2]).val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: widget , values: object array)', function(assert) {
    var element = create_mocks([{'a': 40}, {'b': 41}, {'c': 42}]);
    var mocks = $('.ui-creme-widget.ui-creme-mock', element);

    equal(mocks.length, 3);
    equal($(mocks[0]).creme().widget().val(), '{"a":40}');
    equal($(mocks[1]).creme().widget().val(), '{"b":41}');
    equal($(mocks[2]).creme().widget().val(), '{"c":42}');

    creme.widget.values_list(mocks, ['a', 'b', 'c']);
    equal($(mocks[0]).creme().widget().val(), 'a');
    equal($(mocks[1]).creme().widget().val(), 'b');
    equal($(mocks[2]).creme().widget().val(), 'c');

    creme.widget.values_list(mocks, [{'a': 51}, {'b': 52}]);
    equal($(mocks[0]).creme().widget().val(), '{"a":51}');
    equal($(mocks[1]).creme().widget().val(), '{"b":52}');
    equal($(mocks[2]).creme().widget().val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: widget multiple, values: invalid json array)', function(assert) {
    var element = create_mocks([40, 41, 42]);
    var mocks = $('.ui-creme-widget.ui-creme-mock', element);

    equal(mocks.length, 3);
    equal($(mocks[0]).creme().widget().val(), 40);
    equal($(mocks[1]).creme().widget().val(), 41);
    equal($(mocks[2]).creme().widget().val(), 42);

    creme.widget.values_list(mocks, '["51", "52", 53', JSON.parse);
    equal($(mocks[0]).creme().widget().val(), '');
    equal($(mocks[1]).creme().widget().val(), '');
    equal($(mocks[2]).creme().widget().val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: widget multiple, values: valid json array, parser: none (json))', function(assert) {
    var element = create_mocks([40, 41, 42]);
    var mocks = $('.ui-creme-widget.ui-creme-mock', element);

    equal(mocks.length, 3);
    equal($(mocks[0]).creme().widget().val(), 40);
    equal($(mocks[1]).creme().widget().val(), 41);
    equal($(mocks[2]).creme().widget().val(), 42);

    creme.widget.values_list(mocks, '["51", "52", 53]', JSON.parse);
    equal($(mocks[0]).creme().widget().val(), 51);
    equal($(mocks[1]).creme().widget().val(), 52);
    equal($(mocks[2]).creme().widget().val(), 53);
});

QUnit.test('creme.widget.values_list (getter, inputs: input)', function(assert) {
    var input = create_input(40);

    var values = creme.widget.values_list(input);
    deepEqual(values, ["40"]);
});

QUnit.test('creme.widget.values_list (getter, inputs: input multiple)', function(assert) {
    var element = create_inputs([40, 41, 42]);
    var inputs = $('input.ui-creme-input', element);

    var values = creme.widget.values_list(inputs);
    deepEqual(values, ["40", "41", "42"]);
});

QUnit.test('creme.widget.values_list (getter, inputs: widget)', function(assert) {
    var element = create_mock({"a": 152});

    var values = creme.widget.values_list(element);
    deepEqual(values, ['{"a":152}']);
});

QUnit.test('creme.widget.values_list (getter, inputs: widget multiple)', function(assert) {
    var element = create_mocks([{'a': 40}, {'b': 41}, {'c': 42}]);
    var mocks = $('.ui-creme-widget.ui-creme-mock', element);

    var values = creme.widget.values_list(mocks);
    deepEqual(values, ['{"a":40}', '{"b":41}', '{"c":42}']);
});

QUnit.test('creme.widget.proxy (none)', function(assert) {
    var element = create_widget_element('ui-creme-mock');
    equal(creme.widget.proxy(element, undefined), undefined);
    equal(creme.widget.proxy(element, null), undefined);
});

QUnit.test('creme.widget.proxy', function(assert) {
    var delegate = new MockWidget();
    var element = create_widget_element('ui-creme-mock');
    var proxy = creme.widget.proxy(element, delegate);

    deepEqual(delegate, proxy.delegate);
    deepEqual(proxy.options(), {initial: 42});
    equal(42, proxy.initial());
    equal(42, delegate.initial(element));
});

QUnit.test('creme.widget.proxy (protected methods)', function(assert) {
    var delegate = $.extend({}, new creme.widget.Widget(), new MockWidget());
    delegate.__private = function(element) {};

    var element = create_widget_element('ui-creme-mock');
    var proxy = creme.widget.proxy(element, delegate);

    equal(typeof delegate._protected, 'function');
    equal(typeof delegate.__private, 'function');
    equal(typeof delegate._create, 'function');
    equal(typeof delegate._destroy, 'function');
    equal(typeof delegate.reset, 'function');
    equal(typeof delegate.val, 'function');
    equal(typeof delegate.initial, 'function');

    equal(proxy._protected, undefined);
    equal(proxy.__private, undefined);
    equal(proxy._create, undefined);
    equal(proxy._destroy, undefined);
    equal(typeof proxy.reset, 'function');
    equal(typeof proxy.val, 'function');
    equal(typeof proxy.initial, 'function');
});

QUnit.test('creme.widget', function(assert) {
    var element = create_widget_element('ui-creme-mock');
    var proxy = creme.widget.create(element);
    var delegate = proxy.delegate;

    deepEqual(proxy, element.creme().widget());
    deepEqual({initial: '42'}, element.creme().widget().options());

    element.creme().widget().val(15);
    equal('15', delegate.val(element));

    element.creme().widget().reset();
    equal('42', delegate.val(element));
});
}(jQuery));
