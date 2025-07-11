(function($) {

var TestComponent = creme.component.Component.sub({
    _init_: function(element, options) {
        this.options = options || {};
        this.element = element;
        this.count(options.count || 0);
        this.data([]);
    },

    add: function(a, b) {
        return a + b;
    },

    mult: function(a, b) {
        return a * b;
    },

    count: function(count) {
        return Object.property(this, '_count', count);
    },

    data: function(data) {
        return Object.property(this, '_data', data);
    },

    isReady: function() {
        return true;
    },

    id: function() {
        return this.options.id;
    }
});

QUnit.module("creme.utils.plugin.js", new QUnitMixin(QUnitEventMixin, {
    afterEach: function() {
        if (Object.isNone($.fn['testplugin']) === false) {
            delete $.fn['testplugin'];
        }
    }
}));

QUnit.test('creme.utils.newJQueryPlugin (constructor, default)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        }
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    assert.equal(elements.find('span').length, 3);
    assert.deepEqual([], elements.find('span').map(function() {
        return $(this).data('-testplugin');
    }).get());

    var instances = elements.find('span').testplugin({a: 12, b: 'test'});
    assert.equal(instances.length, 3);
    assert.deepEqual(instances, elements.find('span').map(function() {
        return $(this).data('-testplugin');
    }).get());

    assert.deepEqual({a: 12, b: 'test', id: 'a'}, instances[0].options);
    this.equalOuterHtml('<span data-id="a"></span>', instances[0].element);
    assert.equal(instances[0], elements.find('span[data-id="a"]').testplugin());

    assert.deepEqual({a: 12, b: 'test', id: 'b'}, instances[1].options);
    this.equalOuterHtml('<span data-id="b"></span>', instances[1].element);
    assert.deepEqual(instances[1], elements.find('span[data-id="b"]').testplugin());

    assert.deepEqual({a: 12, b: 'test', id: 'c'}, instances[2].options);
    this.equalOuterHtml('<span data-id="c"></span>', instances[2].element);
    assert.deepEqual(instances[2], elements.find('span[data-id="c"]').testplugin());
});

QUnit.test('creme.utils.newJQueryPlugin (destroy, default)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        }
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    var instances = elements.find('span').testplugin({a: 12, b: 'test'});
    assert.equal(instances.length, 3);
    assert.deepEqual(instances, elements.find('span').map(function() {
        return $(this).data('-testplugin');
    }).get());

    elements.find('span[data-id="b"]').testplugin('destroy');

    assert.deepEqual([instances[0], instances[2]], elements.find('span').map(function() {
        return $(this).data('-testplugin');
    }).get());

    elements.find('span').testplugin('destroy');

    assert.deepEqual([], elements.find('span').map(function() {
        return $(this).data('-testplugin');
    }).get());
});

QUnit.test('creme.utils.newJQueryPlugin (destroy, not a function)', function(assert) {
    this.assertRaises(function() {
        creme.utils.newJQueryPlugin({
            name: 'testplugin',
            create: function(options) {
                return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
            },
            destroy: 12
        });
    }, Error, 'Error: JQuery plugin "testplugin" destructor is not a function.');

    this.assertRaises(function() {
        creme.utils.newJQueryPlugin({
            name: 'testplugin',
            create: function(options) {
                return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
            },
            destroy: 'this is not a method'
        });
    }, Error, 'Error: JQuery plugin "testplugin" destructor is not a function.');

});

QUnit.test('creme.utils.newJQueryPlugin (destroy, fail)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        },
        destroy: function() {
            throw new Error('Destroy failure !');
        }
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    var instances = elements.find('span').testplugin({a: 12, b: 'test'});
    assert.equal(instances.length, 3);

    assert.deepEqual(instances, elements.find('span').map(function() {
        return $(this).data('-testplugin');
    }).get());

    this.assertRaises(function() {
        elements.find('span').testplugin('destroy');
    }, Error, 'Error: Destroy failure !');

    assert.deepEqual(instances, elements.find('span').map(function() {
        return $(this).data('-testplugin');
    }).get());
});

QUnit.test('creme.utils.newJQueryPlugin (destroy, custom)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        },
        destroy: function(instance) {
            $(this).parent().trigger('destroy-testplugin', [instance.id()]);
        }
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    elements.on('destroy-testplugin', this.mockListener('destroy'));

    var instances = elements.find('span').testplugin({a: 12, b: 'test'});
    assert.equal(instances.length, 3);

    assert.deepEqual([], this.mockListenerJQueryCalls('destroy'));
    assert.deepEqual(instances, elements.find('span').map(function() {
        return $(this).data('-testplugin');
    }).get());

    elements.find('span').testplugin('destroy');

    assert.deepEqual([
        ['destroy-testplugin', ['a']],
        ['destroy-testplugin', ['b']],
        ['destroy-testplugin', ['c']]
    ], this.mockListenerJQueryCalls('destroy'));

    assert.deepEqual([], elements.find('span').map(function() {
        return $(this).data('-testplugin');
    }).get());
});

QUnit.test('creme.utils.newJQueryPlugin (already initialized)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        }
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    assert.equal(elements.find('span').length, 3);

    var instances = elements.find('span').testplugin({a: 12, b: 'test'});
    assert.equal(instances.length, 3);

    this.assertRaises(function() {
        elements.find('span').testplugin({a: 12, b: 'test'});
    }, Error, 'Error: Jquery plugin "testplugin" is already initialized.');
});

QUnit.test('creme.utils.newJQueryPlugin (already exists)', function(assert) {
    creme.utils.newJQueryPlugin({name: 'testplugin', create: function() {}});

    this.assertRaises(function() {
        creme.utils.newJQueryPlugin({name: 'testplugin', create: function() {}});
    }, Error, 'Error: JQuery plugin "testplugin" already exist.');
});

QUnit.test('creme.utils.newJQueryPlugin (empty name)', function(assert) {
    this.assertRaises(function() {
        creme.utils.newJQueryPlugin();
    }, Error, 'Error: Missing JQuery plugin name.');

    this.assertRaises(function() {
        creme.utils.newJQueryPlugin({name: ''});
    }, Error, 'Error: Missing JQuery plugin name.');
});

QUnit.test('creme.utils.newJQueryPlugin (invalid constructor)', function(assert) {
    this.assertRaises(function() {
        creme.utils.newJQueryPlugin({name: 'testplugin'});
    }, Error, 'Error: JQuery plugin "testplugin" constructor is not a function.');

    this.assertRaises(function() {
        creme.utils.newJQueryPlugin({name: 'testplugin', create: 12});
    }, Error, 'Error: JQuery plugin "testplugin" constructor is not a function.');
});

QUnit.test('creme.utils.newJQueryPlugin (constructor returns nothing)', function(assert) {
    creme.utils.newJQueryPlugin({name: 'testplugin', create: function() {}});
    var element = $('<div>');

    this.assertRaises(function() {
        element.testplugin();
    }, Error, 'Error: Jquery plugin "testplugin" constructor has returned nothing.');
});

QUnit.test('creme.utils.test_plugin (instance)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        }
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    assert.equal(elements.find('span').testplugin('instance').length, 0);

    elements.find('[data-id="a"]').testplugin({a: 12, b: 'test'});
    assert.equal(elements.find('span').testplugin('instance').length, 1);
});

QUnit.test('creme.utils.test_plugin (props, no property)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        }
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    assert.deepEqual([], elements.find('span').testplugin('props'));

    elements.find('span').testplugin({a: 12, b: 'test'});
    assert.deepEqual([{}, {}, {}], elements.find('span').testplugin('props'));
});

QUnit.test('creme.utils.test_plugin (props)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        },
        properties: ['count', 'isReady', 'id']
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    assert.deepEqual([], elements.find('span').testplugin('props'));

    elements.find('span').testplugin({count: 12, b: 'test'});
    assert.deepEqual([
        {count: 12, isReady: true, id: 'a'},
        {count: 12, isReady: true, id: 'b'},
        {count: 12, isReady: true, id: 'c'}
    ], elements.find('span').testplugin('props'));
});

QUnit.test('creme.utils.test_plugin (property setter)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        },
        properties: ['count', 'id']
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    elements.find('span').testplugin();

    assert.deepEqual([
        {count: 0, id: 'a'},
        {count: 0, id: 'b'},
        {count: 0, id: 'c'}
    ], elements.find('span').testplugin('props'));

    elements.find('span').testplugin('prop', 'count', 754);

    assert.deepEqual([
        {count: 754, id: 'a'},
        {count: 754, id: 'b'},
        {count: 754, id: 'c'}
    ], elements.find('span').testplugin('props'));
});

QUnit.test('creme.utils.test_plugin (property getter)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        },
        properties: ['count', 'isReady', 'data', 'id']
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    assert.deepEqual([], elements.find('span').testplugin('prop', 'count'));
    assert.deepEqual([], elements.find('span').testplugin('prop', 'isReady'));
    assert.deepEqual([], elements.find('span').testplugin('prop', 'data'));

    assert.equal(undefined, elements.find('span[data-id="a"]').testplugin('prop', 'count'));
    assert.equal(undefined, elements.find('span[data-id="a"]').testplugin('prop', 'isReady'));
    assert.equal(undefined, elements.find('span[data-id="a"]').testplugin('prop', 'data'));

    elements.find('span').testplugin();

    assert.deepEqual([0, 0, 0], elements.find('span').testplugin('prop', 'count'));
    assert.deepEqual([true, true, true], elements.find('span').testplugin('prop', 'isReady'));
    assert.deepEqual([[], [], []], elements.find('span').testplugin('prop', 'data'));

    assert.equal(0, elements.find('span[data-id="a"]').testplugin('prop', 'count'));
    assert.equal(true, elements.find('span[data-id="a"]').testplugin('prop', 'isReady'));
    assert.deepEqual([], elements.find('span[data-id="a"]').testplugin('prop', 'data'));

    elements.find('span').testplugin('prop', 'count', 754);
    elements.find('span').testplugin('prop', 'data', [12, 13, 14]);

    assert.deepEqual([754, 754, 754], elements.find('span').testplugin('prop', 'count'));
    assert.deepEqual([true, true, true], elements.find('span').testplugin('prop', 'isReady'));
    assert.deepEqual([
        [12, 13, 14], [12, 13, 14], [12, 13, 14]
    ], elements.find('span').testplugin('prop', 'data'));

    assert.equal(754, elements.find('span[data-id="a"]').testplugin('prop', 'count'));
    assert.equal(true, elements.find('span[data-id="a"]').testplugin('prop', 'isReady'));
    assert.deepEqual([12, 13, 14], elements.find('span[data-id="a"]').testplugin('prop', 'data'));
});

QUnit.test('creme.utils.test_plugin (invalid property)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        },
        properties: ['count', 'id']
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    elements.find('span').testplugin();

    this.assertRaises(function() {
        elements.find('span').testplugin('prop', 'unknown');
    }, Error, 'Error: No such property "unknown" in jQuery plugin "testplugin"');

    this.assertRaises(function() {
        elements.find('span').testplugin('prop', 'unknown', 754);
    }, Error, 'Error: No such property "unknown" in jQuery plugin "testplugin"');
});

QUnit.test('creme.utils.test_plugin (method)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        },
        methods: ['add', 'mult']
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    elements.find('span').testplugin();
    assert.deepEqual([22, 22, 22], elements.find('span').testplugin('add', 5, 17));
    assert.deepEqual(22, elements.find('span[data-id="a"]').testplugin('add', 5, 17));
    assert.equal(undefined, elements.find('span.unknown').testplugin('add', 5, 17));

    assert.deepEqual([16, 16, 16], elements.find('span').testplugin('mult', 2, 8));
    assert.deepEqual(16, elements.find('span[data-id="a"]').testplugin('mult', 2, 8));
    assert.equal(undefined, elements.find('span.unknown').testplugin('mult', 2, 8));
});

QUnit.test('creme.utils.test_plugin (invalid method)', function(assert) {
    creme.utils.newJQueryPlugin({
        name: 'testplugin',
        create: function(options) {
            return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
        },
        methods: ['add', 'mult', 'nofunc']
    });

    var elements = $('<div>' +
            '<span data-id="a"></span>' +
            '<span data-id="b"></span>' +
            '<span data-id="c"></span>' +
        '</div>');

    elements.find('span').testplugin();

    this.assertRaises(function() {
        elements.find('span').testplugin('unknown');
    }, Error, 'Error: No such method "unknown" in jQuery plugin "testplugin"');

    this.assertRaises(function() {
        elements.find('span[data-id="a"]').testplugin('unknown');
    }, Error, 'Error: No such method "unknown" in jQuery plugin "testplugin"');

    this.assertRaises(function() {
        elements.find('span').testplugin('nofunc');
    }, Error, 'Error: Attribute "nofunc" is not a function in jQuery plugin "testplugin"');

    this.assertRaises(function() {
        elements.find('span[data-id="a"]').testplugin('nofunc');
    }, Error, 'Error: Attribute "nofunc" is not a function in jQuery plugin "testplugin"');
});

QUnit.parametrize('creme.utils.test_plugin (builtin method)', [
    ['prop'], ['props'], ['destroy'], ['instance']
], function(methodname, assert) {
    this.assertRaises(function() {
        creme.utils.newJQueryPlugin({
            name: 'testplugin',
            create: function(options) {
                return new TestComponent($(this), $.extend({id: $(this).attr('data-id')}, options || {}));
            },
            methods: [methodname]
        });
    }, Error, 'Error: Method "${name}" is a builtin of JQuery plugin "testplugin".'.template({name: methodname}));
});

}(jQuery));
