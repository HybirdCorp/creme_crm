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
    },

    createWidgetElement: function(name, initial, noauto) {
        var value = (initial !== undefined) ? JSON.stringify(initial) : '42';
        var element =  $('<div widget="' + name + '" class="' + name + ' ui-creme-widget widget-auto" initial=\'' + value + '\'>')
                            .append($('<input type="text" class="ui-creme-input ' + name + '"/>'));

        if (noauto) {
            element.removeClass('widget-auto');
        }

        return element;
    },

    createMockWidgetElement: function(initial) {
        var assert = this.assert;
        var value = (initial !== undefined) ? JSON.stringify(initial) : '42';
        var element = $('<div widget="ui-creme-mock" class="ui-creme-mock ui-creme-widget widget-auto" initial=\'' + value + '\'>')
                           .append($('<input type="text" class="ui-creme-input ui-creme-mock"/>'));

        var widget = creme.widget.create(element);

        assert.equal(typeof widget, 'object');
        assert.equal(typeof widget.delegate, 'object');
        assert.equal(widget.val(), (typeof value !== 'string') ? JSON.stringify(value) : value);

        return element;
    },

    createMockWidgetElements: function(initials) {
        var element = $('<div>');

        for (var i = 0; i < initials.length; ++i) {
            element.append(this.createMockWidgetElement(initials[i]));
        }

        return element;
    }
}));

creme.widget.declare('ui-creme-mock', new MockWidget());

function create_input(initial) {
    var value = (initial !== undefined ? JSON.stringify(initial) : '42');
    return $('<input type="text" class="ui-creme-input" value="' + value + '"/>');
}

function create_inputs(initials) {
    var element = $('<div>');

    for (var i = 0; i < initials.length; ++i) { element.append(create_input(initials[i])); }

    return element;
}

QUnit.test('creme.widget.input', function(assert) {
    assert.equal(creme.widget.input($('<input type="text" class="ui-creme-input mywidget"/>')).length, 0);
    assert.equal(creme.widget.input($('<input type="text" class="ui-creme-input mywidget" widget="otherwidget"/>')).length, 0);
    assert.equal(creme.widget.input($('<input type="text" class="ui-creme-input mywidget" widget="mywidget"/>')).length, 1);

    assert.equal(creme.widget.input($('<div>').append($('<input type="text" class="ui-creme-input mywidget"/>'))).length, 0);
    assert.equal(creme.widget.input($('<div widget="otherwidget">').append($('<input type="text" class="ui-creme-input mywidget"/>'))).length, 0);
    assert.equal(creme.widget.input($('<div widget="mywidget">').append($('<input type="text" class="ui-creme-input mywidget"/>'))).length, 1);

    assert.equal(creme.widget.input($('<div widget="mywidget">').append($('<input type="text" class="ui-creme-input mywidget"/>'))
                                                          .append($('<input type="text" class="ui-creme-input mywidget"/>'))
                                                          .append($('<input type="text" class="ui-creme-input mywidget"/>'))).length, 3);
});

QUnit.test('creme.widget.register', function(assert) {
    assert.equal(creme.widget._widgets['ui-test'], undefined);

    var widget = {
        options: {initial: 42},
        init: function() {},
        clone: function() {}
    };

    creme.widget.register('ui-test', widget);
    assert.deepEqual(creme.widget._widgets['ui-test'], widget);

    creme.widget.unregister('ui-test');
    assert.equal(creme.widget._widgets['ui-test'], undefined);
});

QUnit.test('creme.widget.declare (object)', function(assert) {
    assert.equal(creme.widget._widgets['ui-test'], undefined);

    var widget = new MockWidget();
    assert.equal(widget.destroy, undefined);

    var declared = creme.widget.declare('ui-test', widget);
    assert.equal(typeof declared.destroy, 'function');

    assert.deepEqual(creme.widget._widgets['ui-test'], declared);
});

QUnit.test('creme.widget.declare (object, override method)', function(assert) {
    assert.equal(creme.widget._widgets['ui-test'], undefined);

    var widget = $.extend(new MockWidget(), {
        jsonval: function(element) { return 'overridden jsonval'; }
    });
    assert.equal(widget.destroy, undefined);
    assert.equal(typeof widget.jsonval, 'function');

    var declared = creme.widget.declare('ui-test', widget);
    assert.equal(typeof declared.destroy, 'function');
    assert.equal(typeof declared.jsonval, 'function');

    assert.deepEqual(creme.widget._widgets['ui-test'], declared);
    assert.equal(declared.jsonval($('<div/>')), 'overridden jsonval');
});

QUnit.test('creme.widget.ready', function(assert) {
    var elements = $('<div>').append(this.createWidgetElement('ui-creme-readytest', 12),
                                     this.createWidgetElement('ui-creme-readytest', 13),
                                     this.createWidgetElement('ui-creme-unregistered', 14));

    assert.equal($('.ui-creme-widget', elements).length, 3);
    assert.equal($('.ui-creme-widget.widget-active', elements).length, 0);

    creme.widget.ready(elements);
    assert.equal($('.ui-creme-widget', elements).length, 3);
    assert.equal($('.ui-creme-widget.widget-active', elements).length, 0);

    creme.widget.declare('ui-creme-readytest', new MockWidget());

    creme.widget.ready(elements);
    assert.equal($('.ui-creme-widget', elements).length, 3);
    assert.equal($('.ui-creme-widget.widget-active', elements).length, 2);
    assert.equal($('.ui-creme-widget.widget-active.ui-creme-readytest', elements).length, 2);
    assert.equal($('.ui-creme-widget.ui-creme-unregistered:not(.widget-active)', elements).length, 1);
});

QUnit.test('creme.widget.ready (no auto)', function(assert) {
    creme.widget.declare('ui-creme-readytest', new MockWidget());

    var elements = $('<div>').append(this.createWidgetElement('ui-creme-readytest', 12),
                                     this.createWidgetElement('ui-creme-readytest', 13, true),
                                     this.createWidgetElement('ui-creme-unregistered', 14));

    assert.equal($('.ui-creme-widget', elements).length, 3);
    assert.equal($('.ui-creme-widget.widget-active', elements).length, 0);

    creme.widget.ready(elements);
    assert.equal($('.ui-creme-widget', elements).length, 3);
    assert.equal($('.ui-creme-widget.widget-active', elements).length, 1);
    assert.equal($('.ui-creme-widget.widget-active.ui-creme-readytest', elements).length, 1);
    assert.equal($('.ui-creme-widget.ui-creme-readytest:not(.widget-active)', elements).length, 1);
    assert.equal($('.ui-creme-widget.ui-creme-unregistered:not(.widget-active)', elements).length, 1);
});

QUnit.test('creme.widget.is_valid', function(assert) {
    creme.widget.declare('ui-creme-activatetest', new MockWidget());

    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget" initial="51">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    assert.equal(element.hasClass('widget-active'), false);
    assert.equal(element.hasClass('widget-ready'), false);

    assert.equal(creme.widget.is_valid(element), false);
    creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(creme.widget.is_valid(element), true);
});

QUnit.test('creme.widget.create (not registered)', function(assert) {
    creme.widget.declare('ui-creme-activatetest', new MockWidget());

    var element = $('<div widget="ui-creme-notregistered" class="ui-creme-notregistered ui-creme-widget" initial="51">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-notregistered"/>'));

    assert.equal(creme.widget.create(element), undefined);
    assert.equal(element.hasClass('widget-active'), false);
    assert.equal(element.hasClass('widget-ready'), false);

    assert.equal(element.data('CremeWidget'), undefined);
});

QUnit.test('creme.widget.create (default options)', function(assert) {
    var declared = creme.widget.declare('ui-creme-activatetest', new MockWidget());
    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    assert.notEqual(creme.widget.create(element), undefined);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual(element.data('CremeWidget').delegate, declared);
    assert.deepEqual(element.data('CremeWidget').options(), {initial: 42});
    assert.deepEqual(element.data('CremeWidget').arguments(), {});
});

QUnit.test('creme.widget.create (options)', function(assert) {
    var declared = creme.widget.declare('ui-creme-activatetest', new MockWidget());

    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto" initial="51">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    assert.notEqual(creme.widget.create(element), undefined);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual(element.data('CremeWidget').delegate, $.extend({}, declared, {options: {initial: '51'}}));
    assert.deepEqual(element.data('CremeWidget').options(), {initial: '51'});
    assert.deepEqual(element.data('CremeWidget').arguments(), {});
});

QUnit.test('creme.widget.create (default options, extra options)', function(assert) {
    var declared = creme.widget.declare('ui-creme-activatetest', new MockWidget());
    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto" arg1="value1" arg2="value2">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    assert.notEqual(creme.widget.create(element), undefined);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual(element.data('CremeWidget').delegate, $.extend({}, declared, {arguments: {arg1: 'value1', arg2: 'value2'}}));
    assert.deepEqual(element.data('CremeWidget').options(), {initial: 42});
    assert.deepEqual(element.data('CremeWidget').arguments(), {arg1: 'value1', arg2: 'value2'});
});

QUnit.test('creme.widget.create (default options, extra options, create options)', function(assert) {
    var declared = creme.widget.declare('ui-creme-activatetest', new MockWidget());
    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto" arg1="value1" arg2="value2">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    assert.notEqual(creme.widget.create(element, {initial: 58, other: 'another'}), undefined);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual(element.data('CremeWidget').delegate, $.extend({}, declared, {options: {'initial': 58, other: 'another'},
                                                                            arguments: {arg1: 'value1', arg2: 'value2'}}));
    assert.deepEqual(element.data('CremeWidget').options(), {'initial': 58, other: 'another'});
    assert.deepEqual(element.data('CremeWidget').arguments(), {arg1: 'value1', arg2: 'value2'});
});

QUnit.test('creme.widget.create (twice)', function(assert) {
    var declared = creme.widget.declare('ui-creme-activatetest', new MockWidget());
    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    assert.notEqual(creme.widget.create(element), undefined);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.deepEqual(element.data('CremeWidget').delegate, declared);

    assert.equal(creme.widget.create(element), undefined);
});

QUnit.test('creme.widget.create (multiple instances)', function(assert) {
    creme.widget.declare('ui-creme-activatetest', new MockWidget());
    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto" arg1="value1" arg2="value2">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    var element2 = element.clone();

    var widget = creme.widget.create(element, {initial: 58, other: 'another'});
    var widget2 = creme.widget.create(element2, {initial: 51});

    assert.equal(typeof widget, 'object');
    assert.equal(typeof widget2, 'object');

    assert.deepEqual(widget.options(), {initial: 58, other: 'another'});
    assert.deepEqual(widget2.options(), {initial: 51});
});

QUnit.test('creme.widget.destroy', function(assert) {
    var declared = creme.widget.declare('ui-creme-activatetest', new MockWidget());
    var element = $('<div widget="ui-creme-activatetest" class="ui-creme-activatetest ui-creme-widget widget-auto">')
                       .append($('<input type="text" class="ui-creme-input ui-creme-activatetest"/>'));

    creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual(element.data('CremeWidget').delegate, declared);
    assert.deepEqual(element.data('CremeWidget').options(), {'initial': 42});
    assert.deepEqual(element.data('CremeWidget').arguments(), {});

    creme.widget.destroy(element);
    assert.equal(element.hasClass('widget-active'), false);
    assert.equal(element.hasClass('widget-ready'), false);

    assert.equal(element.data('CremeWidget'), undefined);
});


QUnit.test('creme.widget.values_list (setter, inputs: widget, values: null, parser: none)', function(assert) {
    var element = this.createMockWidgetElement();
    var input = creme.widget.input(element);

    creme.widget.values_list(element, null);
    assert.equal(input.val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: widget, values: object, parser: none)', function(assert) {
    var element = this.createMockWidgetElement();
    var input = creme.widget.input(element);

    creme.widget.values_list(element, 15);
    assert.equal(input.val(), 15);

    creme.widget.values_list(element, ['array']);
    assert.equal(input.val(), 'array');

    creme.widget.values_list(element, {'0': 'dict'});
    assert.equal(input.val(), '{"0":"dict"}');
});

QUnit.test('creme.widget.values_list (setter, inputs: input, values: null, parser: none)', function(assert) {
    var input = create_input(42);
    assert.equal(input.val(), 42);

    creme.widget.values_list(input, null);
    assert.equal(input.val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: input, values: object, parser: none)', function(assert) {
    var input = create_input(42);
    assert.equal(input.val(), 42);

    creme.widget.values_list(input, 15);
    assert.equal(input.val(), 15);

    creme.widget.values_list(input, ['array']);
    assert.equal(input.val(), 'array');

    creme.widget.values_list(input, {'0': 'dict'});
    assert.equal(input.val(), '[object Object]');
});

QUnit.test('creme.widget.values_list (setter, inputs: widget, values: invalid json)', function(assert) {
    var element = this.createMockWidgetElement();
    var input = creme.widget.input(element);

    creme.widget.values_list(element, "{'0':'dict'");
    assert.equal(input.val(), "{'0':'dict'");

    creme.widget.values_list(element, "{'0':'dict'", JSON.parse);
    assert.equal(input.val(), "");
});

QUnit.test('creme.widget.values_list (setter, inputs: widget, values: valid json)', function(assert) {
    var element = this.createMockWidgetElement();
    var input = creme.widget.input(element);

    creme.widget.values_list(element, '{"0":"dict",   "1":  15}');
    assert.equal(input.val(), '{"0":"dict",   "1":  15}');

    creme.widget.values_list(element, '{"0":"dict",   "1":  15}', JSON.parse);
    assert.equal(input.val(), '{"0":"dict","1":15}');

    creme.widget.values_list(element, '["0"]');
    assert.equal(input.val(), '["0"]');

    creme.widget.values_list(element, '["0"]', JSON.parse);
    assert.equal(input.val(), 0);
});

QUnit.test('creme.widget.values_list (setter, inputs: multiple input, values: object array)', function(assert) {
    var element = create_inputs([40, 41, 42]);
    var inputs = $('input.ui-creme-input', element);

    assert.equal(inputs.length, 3);
    assert.equal($(inputs[0]).val(), 40);
    assert.equal($(inputs[1]).val(), 41);
    assert.equal($(inputs[2]).val(), 42);

    creme.widget.values_list(inputs, ['a', 'b', 'c']);
    assert.equal($(inputs[0]).val(), 'a');
    assert.equal($(inputs[1]).val(), 'b');
    assert.equal($(inputs[2]).val(), 'c');

    creme.widget.values_list(inputs, ['f', 'g']);
    assert.equal($(inputs[0]).val(), 'f');
    assert.equal($(inputs[1]).val(), 'g');
    assert.equal($(inputs[2]).val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: multiple input, values: invalid json array)', function(assert) {
    var element = create_inputs([40, 41, 42]);
    var inputs = $('input.ui-creme-input', element);

    assert.equal(inputs.length, 3);
    assert.equal($(inputs[0]).val(), 40);
    assert.equal($(inputs[1]).val(), 41);
    assert.equal($(inputs[2]).val(), 42);

    creme.widget.values_list(inputs, '["51", "52", 53', JSON.parse);
    assert.equal($(inputs[0]).val(), '');
    assert.equal($(inputs[1]).val(), '');
    assert.equal($(inputs[2]).val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: multiple input, values: valid json array)', function(assert) {
    var element = create_inputs([40, 41, 42]);
    var inputs = $('input.ui-creme-input', element);

    assert.equal(inputs.length, 3);
    assert.equal($(inputs[0]).val(), 40);
    assert.equal($(inputs[1]).val(), 41);
    assert.equal($(inputs[2]).val(), 42);

    creme.widget.values_list(inputs, '["51", "52", "53"]', JSON.parse);
    assert.equal($(inputs[0]).val(), 51);
    assert.equal($(inputs[1]).val(), 52);
    assert.equal($(inputs[2]).val(), 53);

    creme.widget.values_list(inputs, '["a", "b"]', JSON.parse);
    assert.equal($(inputs[0]).val(), "a");
    assert.equal($(inputs[1]).val(), "b");
    assert.equal($(inputs[2]).val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: widget , values: object array)', function(assert) {
    var element = this.createMockWidgetElements([{'a': 40}, {'b': 41}, {'c': 42}]);
    var mocks = $('.ui-creme-widget.ui-creme-mock', element);

    assert.equal(mocks.length, 3);
    assert.equal($(mocks[0]).creme().widget().val(), '{"a":40}');
    assert.equal($(mocks[1]).creme().widget().val(), '{"b":41}');
    assert.equal($(mocks[2]).creme().widget().val(), '{"c":42}');

    creme.widget.values_list(mocks, ['a', 'b', 'c']);
    assert.equal($(mocks[0]).creme().widget().val(), 'a');
    assert.equal($(mocks[1]).creme().widget().val(), 'b');
    assert.equal($(mocks[2]).creme().widget().val(), 'c');

    creme.widget.values_list(mocks, [{'a': 51}, {'b': 52}]);
    assert.equal($(mocks[0]).creme().widget().val(), '{"a":51}');
    assert.equal($(mocks[1]).creme().widget().val(), '{"b":52}');
    assert.equal($(mocks[2]).creme().widget().val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: widget multiple, values: invalid json array)', function(assert) {
    var element = this.createMockWidgetElements([40, 41, 42]);
    var mocks = $('.ui-creme-widget.ui-creme-mock', element);

    assert.equal(mocks.length, 3);
    assert.equal($(mocks[0]).creme().widget().val(), 40);
    assert.equal($(mocks[1]).creme().widget().val(), 41);
    assert.equal($(mocks[2]).creme().widget().val(), 42);

    creme.widget.values_list(mocks, '["51", "52", 53', JSON.parse);
    assert.equal($(mocks[0]).creme().widget().val(), '');
    assert.equal($(mocks[1]).creme().widget().val(), '');
    assert.equal($(mocks[2]).creme().widget().val(), '');
});

QUnit.test('creme.widget.values_list (setter, inputs: widget multiple, values: valid json array, parser: none (json))', function(assert) {
    var element = this.createMockWidgetElements([40, 41, 42]);
    var mocks = $('.ui-creme-widget.ui-creme-mock', element);

    assert.equal(mocks.length, 3);
    assert.equal($(mocks[0]).creme().widget().val(), 40);
    assert.equal($(mocks[1]).creme().widget().val(), 41);
    assert.equal($(mocks[2]).creme().widget().val(), 42);

    creme.widget.values_list(mocks, '["51", "52", 53]', JSON.parse);
    assert.equal($(mocks[0]).creme().widget().val(), 51);
    assert.equal($(mocks[1]).creme().widget().val(), 52);
    assert.equal($(mocks[2]).creme().widget().val(), 53);
});

QUnit.test('creme.widget.values_list (getter, inputs: input)', function(assert) {
    var input = create_input(40);

    var values = creme.widget.values_list(input);
    assert.deepEqual(values, ["40"]);
});

QUnit.test('creme.widget.values_list (getter, inputs: input multiple)', function(assert) {
    var element = create_inputs([40, 41, 42]);
    var inputs = $('input.ui-creme-input', element);

    var values = creme.widget.values_list(inputs);
    assert.deepEqual(values, ["40", "41", "42"]);
});

QUnit.test('creme.widget.values_list (getter, inputs: widget)', function(assert) {
    var element = this.createMockWidgetElement({"a": 152});

    var values = creme.widget.values_list(element);
    assert.deepEqual(values, ['{"a":152}']);
});

QUnit.test('creme.widget.values_list (getter, inputs: widget multiple)', function(assert) {
    var element = this.createMockWidgetElements([{'a': 40}, {'b': 41}, {'c': 42}]);
    var mocks = $('.ui-creme-widget.ui-creme-mock', element);

    var values = creme.widget.values_list(mocks);
    assert.deepEqual(values, ['{"a":40}', '{"b":41}', '{"c":42}']);
});

QUnit.test('creme.widget.proxy (none)', function(assert) {
    var element = this.createWidgetElement('ui-creme-mock');
    assert.equal(creme.widget.proxy(element, undefined), undefined);
    assert.equal(creme.widget.proxy(element, null), undefined);
});

QUnit.test('creme.widget.proxy', function(assert) {
    var delegate = new MockWidget();
    var element = this.createWidgetElement('ui-creme-mock');
    var proxy = creme.widget.proxy(element, delegate);

    assert.deepEqual(delegate, proxy.delegate);
    assert.deepEqual(proxy.options(), {initial: 42});
    assert.equal(42, proxy.initial());
    assert.equal(42, delegate.initial(element));
});

QUnit.test('creme.widget.proxy (protected methods)', function(assert) {
    var delegate = $.extend({}, new creme.widget.Widget(), new MockWidget());
    delegate.__private = function(element) {};

    var element = this.createWidgetElement('ui-creme-mock');
    var proxy = creme.widget.proxy(element, delegate);

    assert.equal(typeof delegate._protected, 'function');
    assert.equal(typeof delegate.__private, 'function');
    assert.equal(typeof delegate._create, 'function');
    assert.equal(typeof delegate._destroy, 'function');
    assert.equal(typeof delegate.reset, 'function');
    assert.equal(typeof delegate.val, 'function');
    assert.equal(typeof delegate.initial, 'function');

    assert.equal(proxy._protected, undefined);
    assert.equal(proxy.__private, undefined);
    assert.equal(proxy._create, undefined);
    assert.equal(proxy._destroy, undefined);
    assert.equal(typeof proxy.reset, 'function');
    assert.equal(typeof proxy.val, 'function');
    assert.equal(typeof proxy.initial, 'function');
});

QUnit.test('creme.widget', function(assert) {
    var element = this.createWidgetElement('ui-creme-mock');
    var proxy = creme.widget.create(element);
    var delegate = proxy.delegate;

    assert.deepEqual(proxy, element.creme().widget());
    assert.deepEqual({initial: '42'}, element.creme().widget().options());

    element.creme().widget().val(15);
    assert.equal('15', delegate.val(element));

    element.creme().widget().reset();
    assert.equal('42', delegate.val(element));
});
}(jQuery));
