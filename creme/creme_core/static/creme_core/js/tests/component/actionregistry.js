(function($) {
"use strict";


QUnit.module("creme.component.factory.js", new QUnitMixin(QUnitEventMixin, {
    beforeEach: function() {
        this.resetMockActionCalls();

        var self = this;

        this.mockActionA = new creme.component.Action(function(options) {
            self.pushActionCall('a');
            this.done();
        });

        this.mockActionB = new creme.component.Action(function(options) {
            self.pushActionCall('b');
            this.done();
        });

        this.mockActionDoIt = new creme.component.Action(function(options) {
            self.pushActionCall('do-it');
            this.done();
        });

        this.mockActionRaises = new creme.component.Action(function(options) {
            throw Error('this is an error !');
        });

        this.mockActionSlow = new creme.component.TimeoutAction({delay: 200});
        this.mockActionSlow.onDone(function() {
            self.pushActionCall('slow');
        });

        this.mockActionBuilderDict = {
            a: function(options) {
                return self.mockActionA;
            },
            b: function(options) {
                return self.mockActionB;
            },
            'do-it': function(options) {
                return self.mockActionDoIt;
            },
            raises: function(options) {
                return self.mockActionRaises;
            },
            slow: function(options) {
                return self.mockActionSlow;
            },
            none: function(options) {
                return null;
            }
        };
    },

    teardown: function() {},

    resetMockActionCalls: function() {
        this._mockActionCalls = [];
    },

    mockActionCalls: function() {
        return this._mockActionCalls;
    },

    pushActionCall: function() {
        this._mockActionCalls.push(Array.copy(arguments));
    },

    mapLinkStartEventType: function(d) {
        var uievent = d.length > 4 ? d[4] : undefined;
        var data = d.slice(0, 4);

        if (uievent) {
            data.push(uievent.type);
        }

        return data;
    }
}));

QUnit.test('creme.component.FactoryRegistry (empty)', function(assert) {
    var registry = new creme.component.FactoryRegistry();
    deepEqual([], registry.builders());
    equal(false, registry.has('a'));

    equal(undefined, registry.get('a'));

    this.assertRaises(function() {
        registry.get('a', true);
    }, Error, 'Error: no such builder "a"');
});

QUnit.test('creme.component.FactoryRegistry (strict) ', function(assert) {
    var test = this;
    var registry = new creme.component.FactoryRegistry({
        strict: true
    });

    registry.register('action-A', function() {
        return test.mockActionA;
    });

    equal(this.mockActionA, registry.get('action-A')());

    this.assertRaises(function() {
        registry.get('a');
    }, Error, 'Error: no such builder "a"');

    equal(undefined, registry.get('a', false));
});

QUnit.test('creme.component.FactoryRegistry.fallback (default="_build_")', function(assert) {
    var test = this;
    var registry = new creme.component.FactoryRegistry({
        strict: true
    });

    // by default returns action built by registry._build_{actionname}
    equal(true, Object.isFunc(registry.fallback()));
    deepEqual([], registry.builders());
    deepEqual([], registry.fallbackBuilders());

    this.assertRaises(function() {
        registry.get('a');
    }, Error, 'Error: no such builder "a"');

    registry._build_a = function(key) {
        return test.mockActionA;
    };

    deepEqual([], registry.builders());
    deepEqual(['a'], registry.fallbackBuilders());

    equal(this.mockActionA, registry.get('a')());
});

QUnit.test('creme.component.FactoryRegistry.fallback (null)', function(assert) {
    var test = this;
    var registry = new creme.component.FactoryRegistry({
        strict: true,
        fallback: null
    });

    equal(null, registry.fallback());
    deepEqual([], registry.builders());
    deepEqual([], registry.fallbackBuilders());

    this.assertRaises(function() {
        registry.get('a');
    }, Error, 'Error: no such builder "a"');

    registry._build_a = function(key) {
        return test.mockActionA;
    };

    deepEqual([], registry.builders());
    deepEqual([], registry.fallbackBuilders());

    this.assertRaises(function() {
        registry.get('a');
    }, Error, 'Error: no such builder "a"');
});

QUnit.test('creme.component.FactoryRegistry.fallback (string)', function(assert) {
    var test = this;
    var registry = new creme.component.FactoryRegistry({
        strict: true,
        fallback: '_myactionbuild_'
    });

    equal(true, Object.isFunc(registry.fallback()));
    deepEqual([], registry.builders());
    deepEqual([], registry.fallbackBuilders());

    this.assertRaises(function() {
        registry.get('a');
    }, Error, 'Error: no such builder "a"');

    registry._myactionbuild_a = function(key) {
        return test.mockActionA;
    };

    registry._myactionbuild_b = function(key) {
        return test.mockActionB;
    };

    deepEqual([], registry.builders());
    deepEqual(['a', 'b'], registry.fallbackBuilders());

    equal(this.mockActionA, registry.get('a')());
    equal(this.mockActionB, registry.get('b')());

    this.assertRaises(function() {
        registry.get('c');
    }, Error, 'Error: no such builder "c"');
});

QUnit.test('creme.component.FactoryRegistry.fallback (function)', function(assert) {
    var test = this;
    var registry = new creme.component.FactoryRegistry({
        strict: true
    });
    var fallback = function(key) {
        return function() {
            return test.mockActionDoIt;
        };
    };

    deepEqual([], registry.builders());
    deepEqual([], registry.fallbackBuilders());

    this.assertRaises(function() {
        registry.get('a');
    }, Error, 'Error: no such builder "a"');

    registry.fallback(fallback);

    deepEqual([], registry.builders());
    deepEqual([], registry.fallbackBuilders());

    equal(this.mockActionDoIt, registry.get('a')());
    equal(this.mockActionDoIt, registry.get('any')());
    equal(this.mockActionDoIt, registry.get('thing !')());
});

QUnit.test('creme.component.FactoryRegistry.fallback (invalid)', function(assert) {
    var registry = new creme.component.FactoryRegistry();

    this.assertRaises(function() {
        registry.fallback(12);
    }, Error, 'Error: invalid fallback builder');

    this.assertRaises(function() {
        registry.fallback('');
    }, Error, 'Error: invalid fallback builder');
});

QUnit.test('creme.component.FactoryRegistry.register', function(assert) {
    var test = this;
    var registry = new creme.component.FactoryRegistry();

    registry.register('action-A', function() {
        return test.mockActionA;
    });

    registry.register('action-B', function() {
        return test.mockActionB;
    });

    deepEqual(['action-A', 'action-B'], registry.builders());

    equal(this.mockActionA, registry.get('action-A')());
    equal(this.mockActionB, registry.get('action-B')());
});

QUnit.test('creme.component.FactoryRegistry.register (not a function)', function(assert) {
    var registry = new creme.component.FactoryRegistry();

    this.assertRaises(function() {
        registry.register('action-A', 'a string');
    }, Error, 'Error: builder "action-A" is not a function');

    this.assertRaises(function() {
        registry.register('action-A', 12);
    }, Error, 'Error: builder "action-A" is not a function');

    this.assertRaises(function() {
        registry.register('action-A', null);
    }, Error, 'Error: builder "action-A" is not a function');
});

QUnit.test('creme.component.FactoryRegistry.register (already registered)', function(assert) {
    var test = this;
    var registry = new creme.component.FactoryRegistry();

    registry.register('action-A', function() {
        return test.mockActionA;
    });

    this.assertRaises(function() {
        registry.register('action-A', function() {
            return test.mockActionA;
        });
    }, Error, 'Error: builder "action-A" is already registered');

    deepEqual(['action-A'], registry.builders());

    equal(this.mockActionA, registry.get('action-A')());
});

QUnit.test('creme.component.FactoryRegistry.registerAll', function(assert) {
    var test = this;
    var registry = new creme.component.FactoryRegistry();

    registry.registerAll({
        'action-A': function() {
            return test.mockActionA;
        },
        'action-B': function() {
            return test.mockActionB;
        }
    });

    deepEqual(['action-A', 'action-B'], registry.builders());

    equal(this.mockActionA, registry.get('action-A')());
    equal(this.mockActionB, registry.get('action-B')());
});

QUnit.test('creme.component.FactoryRegistry.registerAll (already registered)', function(assert) {
    var test = this;
    var registry = new creme.component.FactoryRegistry();

    registry.registerAll({
        'action-A': function() {
            return test.mockActionA;
        },
        'action-B': function() {
            return test.mockActionB;
        }
    });

    this.assertRaises(function() {
        registry.registerAll({
            'action-C': function() {
                return test.mockActionA;
            },
            'action-D': function() {
                return test.mockActionB;
            },
            'action-B': function() {
                return test.mockActionDoIt;
            }
        });
    }, Error, 'Error: builder "action-B" is already registered');

    deepEqual(['action-A', 'action-B'], registry.builders());
});

QUnit.test('creme.component.FactoryRegistry.registerAll (invalid)', function(assert) {
    var test = this;
    var registry = new creme.component.FactoryRegistry();

    this.assertRaises(function() {
        registry.registerAll({
            'action-A': function() {
                return test.mockActionA;
            },
            'action-B': 'invalid'
        });
    }, Error, 'Error: builder "action-B" is not a function');

    deepEqual([], registry.builders());

    this.assertRaises(function() {
        registry.registerAll({
            'action-A': function() {
                return test.mockActionA;
            },
            'action-B': 12
        });
    }, Error, 'Error: builder "action-B" is not a function');

    deepEqual([], registry.builders());

    this.assertRaises(function() {
        registry.registerAll(['action-A', 'action-B']);
    }, Error, 'Error: builders data must be a dict');

    deepEqual([], registry.builders());

    this.assertRaises(function() {
        registry.registerAll('action-A');
    }, Error, 'Error: builders data must be a dict');

    deepEqual([], registry.builders());
});

QUnit.test('creme.component.FactoryRegistry.unregister', function(assert) {
    var test = this;
    var registry = new creme.component.FactoryRegistry();

    registry.registerAll({
        'action-A': function() {
            return test.mockActionA;
        },
        'action-B': function() {
            return test.mockActionB;
        }
    });

    deepEqual(['action-A', 'action-B'], registry.builders());
    equal(this.mockActionA, registry.get('action-A')());
    equal(this.mockActionB, registry.get('action-B')());

    registry.unregister('action-B');

    deepEqual(['action-A'], registry.builders());
    equal(this.mockActionA, registry.get('action-A')());
    equal(undefined, registry.get('action-B'));

    registry.unregister('action-A');
    deepEqual([], registry.builders());
    equal(undefined, registry.get('action-A'));
    equal(undefined, registry.get('action-B'));
});

QUnit.test('creme.component.FactoryRegistry.unregister (not registered)', function(assert) {
    var registry = new creme.component.FactoryRegistry();

    this.assertRaises(function() {
        registry.unregister('action-A');
    }, Error, 'Error: builder "action-A" is not registered');
});
}(jQuery));
