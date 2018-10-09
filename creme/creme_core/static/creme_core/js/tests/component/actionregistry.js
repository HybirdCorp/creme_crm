(function($) {
"use strict";

var MockActionBuilderRegistry = creme.action.ActionBuilderRegistry.sub({
    _init_: function(context, options) {
        this._super_(creme.action.ActionBuilderRegistry, '_init_', options);
        this.context = context;
    },

    _build_a: function(options) {
        return this.context.mockActionA;
    },
    _build_b: function(options) {
        return this.context.mockActionB;
    },
    _build_do_it: function(options) {
        return this.context.mockActionDoIt;
    },
    _build_raises: function(options) {
        return this.context.mockActionRaises;
    },
    _build_slow: function(options) {
        return this.context.mockActionSlow;
    },
    _build_none: function(options) {
        return null;
    }
});

QUnit.module("creme.actionlink.js", {
    setup: function() {
        this.resetMockCalls();
        this.resetMockActionCalls();

        var actionCalls = this._mockActionCalls;
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

    resetMockCalls: function() {
        this._eventListenerCalls = {};
    },

    mapLinkStartEventType: function(d) {
        var uievent = d.length > 4 ? d[4] : undefined;
        var data = d.slice(0, 4);

        if (uievent) {
            data.push(uievent.type);
        }

        return data;
    },

    mockListenerCalls: function(name) {
        if (this._eventListenerCalls[name] === undefined)
            this._eventListenerCalls[name] = [];

        return this._eventListenerCalls[name];
    },

    mockListener: function(name) {
        var self = this;
        return (function(name) {return function() {
            self.mockListenerCalls(name).push(Array.copy(arguments));
        }})(name);
    },

    assertRaises: function(block, expected, message) {
        QUnit.assert.raises(block,
               function(error) {
                    ok(error instanceof expected, 'error is ' + expected);
                    equal(message, '' + error, 'error message');
                    return true;
               });
    }
});

QUnit.test('creme.action.ActionBuilderRegistry (empty)', function(assert) {
    var registry = new creme.action.ActionBuilderRegistry();
    deepEqual([], registry.actions());
    equal(false, registry.has('a'));

    equal(undefined, registry.get('a'));

    this.assertRaises(function() {
        registry.get('a', true);
    }, Error, 'Error: no such action builder "a"');
});

QUnit.test('creme.action.ActionBuilderRegistry (strict) ', function(assert) {
    var test = this;
    var registry = new creme.action.ActionBuilderRegistry({
        strict: true
    });

    registry.register('action-A', function() {
        return test.mockActionA;
    });

    equal(this.mockActionA, registry.get('action-A')());

    this.assertRaises(function() {
        registry.get('a');
    }, Error, 'Error: no such action builder "a"');

    equal(undefined, registry.get('a', false));
});

QUnit.test('creme.action.ActionBuilderRegistry.fallback (default="_build_")', function(assert) {
    var test = this;
    var registry = new creme.action.ActionBuilderRegistry({
        strict: true
    });

    // by default returns action built by registry._build_{actionname}
    equal(true, Object.isFunc(registry.fallback()));
    deepEqual([], registry.actions());
    deepEqual([], registry.fallbackActions());

    this.assertRaises(function() {
        registry.get('a');
    }, Error, 'Error: no such action builder "a"');

    registry._build_a = function(key) {
        return test.mockActionA;
    };

    deepEqual([], registry.actions());
    deepEqual(['a'], registry.fallbackActions());

    equal(this.mockActionA, registry.get('a')());
});

QUnit.test('creme.action.ActionBuilderRegistry.fallback (null)', function(assert) {
    var test = this;
    var registry = new creme.action.ActionBuilderRegistry({
        strict: true,
        fallback: null
    });

    equal(null, registry.fallback());
    deepEqual([], registry.actions());
    deepEqual([], registry.fallbackActions());

    this.assertRaises(function() {
        registry.get('a');
    }, Error, 'Error: no such action builder "a"');

    registry._build_a = function(key) {
        return test.mockActionA;
    }

    deepEqual([], registry.actions());
    deepEqual([], registry.fallbackActions());

    this.assertRaises(function() {
        registry.get('a');
    }, Error, 'Error: no such action builder "a"');
});

QUnit.test('creme.action.ActionBuilderRegistry.fallback (string)', function(assert) {
    var test = this;
    var registry = new creme.action.ActionBuilderRegistry({
        strict: true,
        fallback: '_myactionbuild_'
    });

    equal(true, Object.isFunc(registry.fallback()));
    deepEqual([], registry.actions());
    deepEqual([], registry.fallbackActions());

    this.assertRaises(function() {
        registry.get('a');
    }, Error, 'Error: no such action builder "a"');

    registry._myactionbuild_a = function(key) {
        return test.mockActionA;
    };

    registry._myactionbuild_b = function(key) {
        return test.mockActionB;
    };

    deepEqual([], registry.actions());
    deepEqual(['a', 'b'], registry.fallbackActions());

    equal(this.mockActionA, registry.get('a')());
    equal(this.mockActionB, registry.get('b')());

    this.assertRaises(function() {
        registry.get('c');
    }, Error, 'Error: no such action builder "c"');
});

QUnit.test('creme.action.ActionBuilderRegistry.fallback (function)', function(assert) {
    var test = this;
    var registry = new creme.action.ActionBuilderRegistry({
        strict: true
    });
    var fallback = function(key) {
        return function() {
            return test.mockActionDoIt;
        }
    }

    deepEqual([], registry.actions());
    deepEqual([], registry.fallbackActions());

    this.assertRaises(function() {
        registry.get('a');
    }, Error, 'Error: no such action builder "a"');

    registry.fallback(fallback);

    deepEqual([], registry.actions());
    deepEqual([], registry.fallbackActions());

    equal(this.mockActionDoIt, registry.get('a')());
    equal(this.mockActionDoIt, registry.get('any')());
    equal(this.mockActionDoIt, registry.get('thing !')());
});

QUnit.test('creme.action.ActionBuilderRegistry.fallback (invalid)', function(assert) {
    var registry = new creme.action.ActionBuilderRegistry();

    this.assertRaises(function() {
        registry.fallback(12);
    }, Error, 'Error: invalid action builder registry fallback');

    this.assertRaises(function() {
        registry.fallback('');
    }, Error, 'Error: invalid action builder registry fallback');
});

QUnit.test('creme.action.ActionBuilderRegistry.register', function(assert) {
    var test = this;
    var registry = new creme.action.ActionBuilderRegistry();

    registry.register('action-A', function() {
        return test.mockActionA;
    });

    registry.register('action-B', function() {
        return test.mockActionB;
    });

    deepEqual(['action-A', 'action-B'], registry.actions());

    equal(this.mockActionA, registry.get('action-A')());
    equal(this.mockActionB, registry.get('action-B')());
});

QUnit.test('creme.action.ActionBuilderRegistry.register (not a function)', function(assert) {
    var test = this;
    var registry = new creme.action.ActionBuilderRegistry();

    this.assertRaises(function() {
        registry.register('action-A', 'a string');
    }, Error, 'Error: action builder "action-A" is not a function');

    this.assertRaises(function() {
        registry.register('action-A', 12);
    }, Error, 'Error: action builder "action-A" is not a function');

    this.assertRaises(function() {
        registry.register('action-A', null);
    }, Error, 'Error: action builder "action-A" is not a function');
});

QUnit.test('creme.action.ActionBuilderRegistry.register (already registered)', function(assert) {
    var test = this;
    var registry = new creme.action.ActionBuilderRegistry();

    registry.register('action-A', function() {
        return test.mockActionA;
    });

    this.assertRaises(function() {
        registry.register('action-A', function() {
            return test.mockActionA;
        });
    }, Error, 'Error: action builder "action-A" is already registered');

    deepEqual(['action-A'], registry.actions());

    equal(this.mockActionA, registry.get('action-A')());
});

QUnit.test('creme.action.ActionBuilderRegistry.registerAll', function(assert) {
    var test = this;
    var registry = new creme.action.ActionBuilderRegistry();

    registry.registerAll({
        'action-A': function() {
            return test.mockActionA;
        },
        'action-B': function() {
            return test.mockActionB;
        }
    });

    deepEqual(['action-A', 'action-B'], registry.actions());

    equal(this.mockActionA, registry.get('action-A')());
    equal(this.mockActionB, registry.get('action-B')());
});

QUnit.test('creme.action.ActionBuilderRegistry.registerAll (already registered)', function(assert) {
    var test = this;
    var registry = new creme.action.ActionBuilderRegistry();

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
    }, Error, 'Error: action builder "action-B" is already registered');

    deepEqual(['action-A', 'action-B'], registry.actions());
});

QUnit.test('creme.action.ActionBuilderRegistry.registerAll (invalid)', function(assert) {
    var test = this;
    var registry = new creme.action.ActionBuilderRegistry();

    this.assertRaises(function() {
        registry.registerAll({
            'action-A': function() {
                return test.mockActionA;
            },
            'action-B': 'invalid'
        });
    }, Error, 'Error: action builder "action-B" is not a function');

    deepEqual([], registry.actions());

    this.assertRaises(function() {
        registry.registerAll({
            'action-A': function() {
                return test.mockActionA;
            },
            'action-B': 12
        });
    }, Error, 'Error: action builder "action-B" is not a function');

    deepEqual([], registry.actions());

    this.assertRaises(function() {
        registry.registerAll(['action-A', 'action-B']);
    }, Error, 'Error: action builders data must be a dict');

    deepEqual([], registry.actions());

    this.assertRaises(function() {
        registry.registerAll('action-A');
    }, Error, 'Error: action builders data must be a dict');

    deepEqual([], registry.actions());
});

QUnit.test('creme.action.ActionBuilderRegistry.unregister', function(assert) {
    var test = this;
    var registry = new creme.action.ActionBuilderRegistry();

    registry.registerAll({
        'action-A': function() {
            return test.mockActionA;
        },
        'action-B': function() {
            return test.mockActionB;
        }
    });

    deepEqual(['action-A', 'action-B'], registry.actions());
    equal(this.mockActionA, registry.get('action-A')());
    equal(this.mockActionB, registry.get('action-B')());

    registry.unregister('action-B');

    deepEqual(['action-A'], registry.actions());
    equal(this.mockActionA, registry.get('action-A')());
    equal(undefined, registry.get('action-B'));

    registry.unregister('action-A');
    deepEqual([], registry.actions());
    equal(undefined, registry.get('action-A'));
    equal(undefined, registry.get('action-B'));
});

QUnit.test('creme.action.ActionBuilderRegistry.unregister (not registered)', function(assert) {
    var registry = new creme.action.ActionBuilderRegistry();

    self.assertRaises(function() {
        registry.unregister('action-A');
    }, Error, 'Error: action builder "action-A" is not registered');
});

}(jQuery));
