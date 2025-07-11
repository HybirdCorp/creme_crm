(function($) {

QUnit.module("creme.component.EventHandler.js", new QUnitMixin(QUnitEventMixin, {
    mockRawListener: function(name) {
        var self = this;

        return (function(name) {
            return function() {
                var calls = self._eventListenerCalls;
                var listenerCalls = calls[name] || [];

                listenerCalls.push([this].concat(Array.from(arguments)));
                calls[name] = listenerCalls;
            };
        }(name));
    },

    assertListenerUUIDs: function(listeners, expected) {
        var uuid_getter = function(l) { return l.__eventuuid__; };
        this.assert.deepEqual(listeners.map(uuid_getter), expected.map(uuid_getter));
    }
}));

QUnit.test('creme.component.EventHandler.bind (single key, single listener)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('listener1'),
        listener2 = this.mockRawListener('listener2');

    assert.deepEqual({}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));

    handler.bind('event1', listener);

    assert.deepEqual({'event1': [listener]}, handler._listeners);
    assert.deepEqual([listener], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));

    handler.bind('event2', listener);

    assert.deepEqual({'event1': [listener], 'event2': [listener]}, handler._listeners);
    assert.deepEqual([listener], handler.listeners('event1'));
    assert.deepEqual([listener], handler.listeners('event2'));

    handler.bind('event1', listener2);

    assert.deepEqual({'event1': [listener, listener2], 'event2': [listener]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener], handler.listeners('event2'));

    handler.trigger('event1', 'a');
    assert.deepEqual({
        'listener1': [[handler, 'event1', 'a']],
        'listener2': [[handler, 'event1', 'a']]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();

    handler.trigger('event2', 'b');
    assert.deepEqual({
        'listener1': [[handler, 'event2', 'b']]
    }, this.mockListenerCalls(), 'calls');
});

QUnit.test('creme.component.EventHandler.bind (single key, multiple listener)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('listener1'),
        listener2 = this.mockRawListener('listener2');

    assert.deepEqual({}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));

    handler.bind('event1', [listener, listener2]);

    assert.deepEqual({'event1': [listener, listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));

    handler.trigger('event1', 'a');
    assert.deepEqual({
        'listener1': [[handler, 'event1', 'a']],
        'listener2': [[handler, 'event1', 'a']]
    }, this.mockListenerCalls(), 'calls');
});

QUnit.test('creme.component.EventHandler.bind (multiple key, single listener)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('listener1'),
        listener2 = this.mockRawListener('listener2');

    assert.deepEqual({}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));
    assert.deepEqual([], handler.listeners('event3'));

    handler.bind(['event1', 'event2'], listener);

    assert.deepEqual({'event1': [listener], 'event2': [listener]}, handler._listeners);
    assert.deepEqual([listener], handler.listeners('event1'));
    assert.deepEqual([listener], handler.listeners('event2'));
    assert.deepEqual([], handler.listeners('event3'));

    handler.bind(['event1', 'event2', 'event3'], listener2);

    assert.deepEqual({'event1': [listener, listener2], 'event2': [listener, listener2], 'event3': [listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener, listener2], handler.listeners('event2'));
    assert.deepEqual([listener2], handler.listeners('event3'));

    handler.trigger('event1', 'a');
    assert.deepEqual({
        'listener1': [[handler, 'event1', 'a']],
        'listener2': [[handler, 'event1', 'a']]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();

    handler.trigger('event2', 'b');
    assert.deepEqual({
        'listener1': [[handler, 'event2', 'b']],
        'listener2': [[handler, 'event2', 'b']]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();

    handler.trigger('event3', 'd');
    assert.deepEqual({
        'listener2': [[handler, 'event3', 'd']]
    }, this.mockListenerCalls(), 'calls');

    handler.trigger('event3', 'd');
    assert.deepEqual({
        'listener2': [[handler, 'event3', 'd'], [handler, 'event3', 'd']]
    }, this.mockListenerCalls(), 'calls');
});

QUnit.test('creme.component.EventHandler.bind (multiple key, multiple listener)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('1'),
        listener2 = this.mockRawListener('2');

    assert.deepEqual({}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));
    assert.deepEqual([], handler.listeners('event3'));

    handler.bind(['event1', 'event2'], [listener, listener2]);

    assert.deepEqual({'event1': [listener, listener2], 'event2': [listener, listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener, listener2], handler.listeners('event2'));
    assert.deepEqual([], handler.listeners('event3'));

    handler.bind(['event1', 'event2', 'event3'], [listener, listener2]);

    assert.deepEqual({'event1': [listener, listener2, listener, listener2],
               'event2': [listener, listener2, listener, listener2],
               'event3': [listener, listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2, listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener, listener2, listener, listener2], handler.listeners('event2'));
    assert.deepEqual([listener, listener2], handler.listeners('event3'));
});

QUnit.test('creme.component.EventHandler.bind (split key, multiple listener)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('1'),
        listener2 = this.mockRawListener('2');

    assert.deepEqual({}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));
    assert.deepEqual([], handler.listeners('event3'));

    handler.bind('event1 event2', [listener, listener2]);

    assert.deepEqual({'event1': [listener, listener2], 'event2': [listener, listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener, listener2], handler.listeners('event2'));
    assert.deepEqual([], handler.listeners('event3'));

    handler.bind('event1 event2 event3', [listener, listener2]);

    assert.deepEqual({'event1': [listener, listener2, listener, listener2],
               'event2': [listener, listener2, listener, listener2],
               'event3': [listener, listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2, listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener, listener2, listener, listener2], handler.listeners('event2'));
    assert.deepEqual([listener, listener2], handler.listeners('event3'));
});

QUnit.test('creme.component.EventHandler.bind (decorator)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('listener1'),
        listener2 = this.mockRawListener('listener2');
    var decorator = function(key, listener, args) {
        return listener.apply(this, args.concat(['decorated']));
    };

    assert.deepEqual({}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));
    assert.deepEqual([], handler.listeners('event3'));

    handler.bind(['event1', 'event2'], listener);
    handler.bind(['event1', 'event3'], listener2, decorator);

    handler.trigger('event1');
    assert.deepEqual({
        'listener1': [[handler, 'event1']],
        'listener2': [[handler, 'event1', 'decorated']]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();
    handler.trigger('event2', 12);
    assert.deepEqual({
        'listener1': [[handler, 'event2', 12]]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();
    handler.trigger('event3', 38);
    assert.deepEqual({
        'listener2': [[handler, 'event3', 38, 'decorated']]
    }, this.mockListenerCalls(), 'calls');
});

QUnit.test('creme.component.EventHandler.bind (object)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listeners = {
            event1: this.mockRawListener('listener1'),
            event2: [this.mockRawListener('listener2'), this.mockRawListener('listener3')]
        };

    assert.deepEqual({}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));

    handler.bind(listeners);

    assert.deepEqual({'event1': [listeners.event1],
               'event2': [listeners.event2[0], listeners.event2[1]]}, handler._listeners);

    handler.trigger('event1');
    assert.deepEqual({
        'listener1': [[handler, 'event1']]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();
    handler.trigger('event2');
    assert.deepEqual({
        'listener2': [[handler, 'event2']],
        'listener3': [[handler, 'event2']]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();
    handler.trigger('event3');
    assert.deepEqual({}, this.mockListenerCalls());
});

QUnit.test('creme.component.EventHandler.bind (object array)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listeners1 = {
            event1: this.mockRawListener('listener1'),
            event2: [this.mockRawListener('listener2'), this.mockRawListener('listener3')]
        },
        listeners2 = {
            event1: this.mockRawListener('listener2.1'),
            event3: [this.mockRawListener('listener2.2'), this.mockRawListener('listener2.3')]
        };

    assert.deepEqual({}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));
    assert.deepEqual([], handler.listeners('event3'));

    handler.bind([listeners1, listeners2]);

    assert.deepEqual({'event1': [listeners1.event1, listeners2.event1],
               'event2': [listeners1.event2[0], listeners1.event2[1]],
               'event3': [listeners2.event3[0], listeners2.event3[1]]}, handler._listeners);

    handler.trigger('event1');
    assert.deepEqual({
        'listener1': [[handler, 'event1']],
        'listener2.1': [[handler, 'event1']]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();
    handler.trigger('event2');
    assert.deepEqual({
        'listener2': [[handler, 'event2']],
        'listener3': [[handler, 'event2']]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();
    handler.trigger('event3');
    assert.deepEqual({
        'listener2.2': [[handler, 'event3']],
        'listener2.3': [[handler, 'event3']]
    }, this.mockListenerCalls(), 'calls');
});

QUnit.test('creme.component.EventHandler.bind (errors)', function(assert) {
    var handler = new creme.component.EventHandler();

    this.assertRaises(function() {
        handler.bind('event1', 'b');
    }, Error, 'Error: unable to bind event "event1", listener is not a function');

    this.assertRaises(function() {
        handler.on('event1', 'b');
    }, Error, 'Error: unable to bind event "event1", listener is not a function');

    this.assertRaises(function() {
        handler.on({
            'event1': function() {},
            'event2': 'b'
        });
    }, Error, 'Error: unable to bind event "event2", listener is not a function');
});

QUnit.test('creme.component.EventHandler.on/off (bind/unbind aliases)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('listener1');

    handler.on('event1', listener);

    handler.trigger('event1');
    assert.deepEqual({
        'listener1': [[handler, 'event1']]
    }, this.mockListenerCalls(), 'calls');

    handler.off('event1', listener);

    this.resetMockListenerCalls();
    handler.trigger('event1');

    assert.deepEqual({}, this.mockListenerCalls());
});

QUnit.test('creme.component.EventHandler.trigger', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('listener1'),
        listener2 = this.mockRawListener('listener2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    handler.trigger('event1');
    assert.deepEqual({
        'listener1': [[handler, 'event1']],
        'listener2': [[handler, 'event1']]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();
    handler.trigger('event1', [], this);
    assert.deepEqual({
        'listener1': [[this, 'event1']],
        'listener2': [[this, 'event1']]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();
    handler.trigger('event1', ['a', 12], this);
    assert.deepEqual({
        'listener1': [[this, 'event1', 'a', 12]],
        'listener2': [[this, 'event1', 'a', 12]]
    }, this.mockListenerCalls(), 'calls');
});

QUnit.test('creme.component.EventHandler.unbind (single key, single listener)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('1'),
        listener2 = this.mockRawListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    assert.deepEqual({'event1': [listener, listener2], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event2', listener); // not bound, do nothing

    assert.deepEqual({'event1': [listener, listener2], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event1', listener);

    assert.deepEqual({'event1': [listener2], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([listener2], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event1', listener);

    assert.deepEqual({'event1': [listener2], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([listener2], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));
});

QUnit.test('creme.component.EventHandler.unbind (single key, multiple listener)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('1'),
        listener2 = this.mockRawListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    assert.deepEqual({'event1': [listener, listener2], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event1', [listener, listener2]);

    assert.deepEqual({'event1': [], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event1', [listener, listener2]);

    assert.deepEqual({'event1': [], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));
});

QUnit.test('creme.component.EventHandler.unbind (multiple key, single listener)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('1'),
        listener2 = this.mockRawListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    assert.deepEqual({'event1': [listener, listener2], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));

    handler.unbind(['event1', 'event2'], [listener2]);

    assert.deepEqual({'event1': [listener], 'event2': []}, handler._listeners);
    assert.deepEqual([listener], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));

    handler.unbind(['event1', 'event2'], [listener2]);

    assert.deepEqual({'event1': [listener], 'event2': []}, handler._listeners);
    assert.deepEqual([listener], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));
});

QUnit.test('creme.component.EventHandler.unbind (multiple key, multiple listener)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('1'),
        listener2 = this.mockRawListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    assert.deepEqual({'event1': [listener, listener2], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));

    handler.unbind(['event1', 'event2'], [listener, listener2]);

    assert.deepEqual({'event1': [], 'event2': []}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));

    handler.unbind(['event1', 'event2'], [listener, listener2]);

    assert.deepEqual({'event1': [], 'event2': []}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));
});

QUnit.test('creme.component.EventHandler.unbind (single key, all listeners)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('1'),
        listener2 = this.mockRawListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    assert.deepEqual({'event1': [listener, listener2], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event1');

    assert.deepEqual({'event1': [], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event1');

    assert.deepEqual({'event1': [], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));
});


QUnit.test('creme.component.EventHandler.unbind (multiple key, all listeners)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('1'),
        listener2 = this.mockRawListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    assert.deepEqual({'event1': [listener, listener2], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));

    handler.unbind(['event1', 'event2']);

    assert.deepEqual({'event1': [], 'event2': []}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));

    handler.unbind(['event1', 'event2']);

    assert.deepEqual({'event1': [], 'event2': []}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));
});

QUnit.test('creme.component.EventHandler.unbind (split key, all listeners)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('1'),
        listener2 = this.mockRawListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    assert.deepEqual({'event1': [listener, listener2], 'event2': [listener2]}, handler._listeners);
    assert.deepEqual([listener, listener2], handler.listeners('event1'));
    assert.deepEqual([listener2], handler.listeners('event2'));

    handler.unbind(['event1 event2']);

    assert.deepEqual({'event1': [], 'event2': []}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));

    handler.unbind(['event1 event2']);

    assert.deepEqual({'event1': [], 'event2': []}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));
});

QUnit.test('creme.component.EventHandler.unbind (dict)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listeners = {
            event1: this.mockRawListener('1'),
            event2: [this.mockRawListener('2'), this.mockRawListener('3')]
        };

    handler.bind(listeners);

    assert.deepEqual({'event1': [listeners.event1],
               'event2': [listeners.event2[0], listeners.event2[1]]}, handler._listeners);

    handler.unbind(listeners);

    assert.deepEqual({'event1': [], 'event2': []}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));

    handler.unbind(listeners);

    assert.deepEqual({'event1': [], 'event2': []}, handler._listeners);
    assert.deepEqual([], handler.listeners('event1'));
    assert.deepEqual([], handler.listeners('event2'));
});

QUnit.test('creme.component.EventHandler.unbind (dict array)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listeners1 = {
            event1: this.mockRawListener('1'),
            event2: [this.mockRawListener('2'), this.mockRawListener('3')]
        },
        listeners2 = {
            event1: this.mockRawListener('2.1'),
            event3: [this.mockRawListener('2.2'), this.mockRawListener('2.3')]
        };

    handler.bind([listeners1, listeners2]);

    assert.deepEqual({'event1': [listeners1.event1, listeners2.event1],
               'event2': [listeners1.event2[0], listeners1.event2[1]],
               'event3': [listeners2.event3[0], listeners2.event3[1]]}, handler._listeners);

    handler.unbind([listeners1, listeners2]);

    assert.deepEqual({'event1': [], 'event2': [], 'event3': []}, handler._listeners);

    handler.unbind([listeners1, listeners2]);

    assert.deepEqual({'event1': [], 'event2': [], 'event3': []}, handler._listeners);
});

QUnit.test('creme.component.EventHandler.error', function(assert) {
    var handler = new creme.component.EventHandler();
    var handled_error = null;
    var invalid_listener = function() {
        throw Error('event handler error !');
    };

    assert.equal(true, Object.isFunc(handler.error()));

    handler.on('event1', invalid_listener);
    handler.error(function(e, key, args, listener) {
        handled_error = {
            error: e,
            event: key,
            args: args,
            listener: listener,
            source: this
        };
    });

    handler.trigger('event1', 'a');

    assert.equal('event1', handled_error.event);
    assert.deepEqual(['a'], handled_error.args);
    assert.equal(invalid_listener, handled_error.listener);
    assert.equal(handler, handled_error.source);
    assert.equal('Error: event handler error !', String(handled_error.error));
});

QUnit.test('creme.component.EventHandler.error (disable)', function(assert) {
    var handler = new creme.component.EventHandler();
    var handled_error = null;
    var error_listener = function() {
        throw Error('event handler error !');
    };

    assert.equal(true, Object.isFunc(handler.error()));

    handler.on('event1', error_listener);
    handler.error(function(e, key, args, listener) {
        handled_error = {
            error: e,
            event: key,
            args: args,
            listener: listener,
            source: this
        };
    });

    handler.trigger('event1', 'a');
    assert.equal('event1', handled_error.event);

    handled_error = null;
    handler.error(null); // disable error handler !

    handler.trigger('event1', 'a');
    assert.equal(null, handled_error); // nothing happens !
});

QUnit.test('creme.component.EventHandler.error (not a function)', function(assert) {
    var handler = new creme.component.EventHandler();

    this.assertRaises(function() {
        handler.error('not a function');
    }, Error, 'Error: event error handler is not a function');
});

QUnit.test('creme.component.EventHandler.one (single key, single listener)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('listener1'),
        listener2 = this.mockRawListener('listener2');

    handler.one('event1', listener);
    handler.bind('event1', listener2);

    this.assertListenerUUIDs(handler.listeners('event1'), [listener, listener2]);

    assert.deepEqual({}, this.mockListenerCalls());

    handler.trigger('event1', 'a');
    assert.deepEqual({
        'listener1': [[handler, 'event1', 'a']],
        'listener2': [[handler, 'event1', 'a']]
    }, this.mockListenerCalls(), 'calls');

    this.assertListenerUUIDs(handler.listeners('event1'), [listener2]);

    this.resetMockListenerCalls();
    handler.trigger('event1', 'a');
    assert.deepEqual({
        'listener2': [[handler, 'event1', 'a']]
    }, this.mockListenerCalls(), 'calls');

    this.assertListenerUUIDs(handler.listeners('event1'), [listener2]);
});

QUnit.test('creme.component.EventHandler.one (single key, multiple listeners)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('listener1'),
        listener2 = this.mockRawListener('listener2'),
        listener3 = this.mockRawListener('listener3');

    handler.one('event1', [listener, listener2]);
    handler.bind('event1', listener3);

    this.assertListenerUUIDs(handler.listeners('event1'), [listener, listener2, listener3]);

    assert.deepEqual({}, this.mockListenerCalls());

    handler.trigger('event1', 'a');
    assert.deepEqual({
        'listener1': [[handler, 'event1', 'a']],
        'listener2': [[handler, 'event1', 'a']],
        'listener3': [[handler, 'event1', 'a']]
    }, this.mockListenerCalls(), 'calls');

    this.assertListenerUUIDs(handler.listeners('event1'), [listener3]);
});

QUnit.test('creme.component.EventHandler.one (multiple key, single listener)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('listener1'),
        listener2 = this.mockRawListener('listener2');

    handler.one(['event1', 'event2'], listener);
    handler.bind(['event1', 'event2'], listener2);

    this.assertListenerUUIDs(handler.listeners('event1'), [listener, listener2]);
    this.assertListenerUUIDs(handler.listeners('event2'), [listener, listener2]);

    assert.deepEqual({}, this.mockListenerCalls());

    handler.trigger('event1', 'a');
    assert.deepEqual({
        'listener1': [[handler, 'event1', 'a']],
        'listener2': [[handler, 'event1', 'a']]
    }, this.mockListenerCalls(), 'calls');

    this.assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    this.assertListenerUUIDs(handler.listeners('event2'), [listener, listener2]);

    this.resetMockListenerCalls();
    handler.trigger('event1', 'a');
    assert.deepEqual({
        'listener2': [[handler, 'event1', 'a']]
    }, this.mockListenerCalls(), 'calls');

    this.assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    this.assertListenerUUIDs(handler.listeners('event2'), [listener, listener2]);

    this.resetMockListenerCalls();
    handler.trigger('event2', 12);
    assert.deepEqual({
        'listener1': [[handler, 'event2', 12]],
        'listener2': [[handler, 'event2', 12]]
    }, this.mockListenerCalls(), 'calls');

    this.assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    this.assertListenerUUIDs(handler.listeners('event2'), [listener2]);
});

QUnit.test('creme.component.EventHandler.one (multiple key, multiple listeners)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('listener1'),
        listener2 = this.mockRawListener('listener2'),
        listener3 = this.mockRawListener('listener3');

    handler.one(['event1', 'event2'], [listener, listener2]);
    handler.bind(['event1', 'event2'], listener3);

    this.assertListenerUUIDs(handler.listeners('event1'), [listener, listener2, listener3]);
    this.assertListenerUUIDs(handler.listeners('event2'), [listener, listener2, listener3]);

    assert.deepEqual({}, this.mockListenerCalls());

    handler.trigger('event1', 'a');
    assert.deepEqual({
        'listener1': [[handler, 'event1', 'a']],
        'listener2': [[handler, 'event1', 'a']],
        'listener3': [[handler, 'event1', 'a']]
    }, this.mockListenerCalls(), 'calls');

    this.assertListenerUUIDs(handler.listeners('event1'), [listener3]);
    this.assertListenerUUIDs(handler.listeners('event2'), [listener, listener2, listener3]);

    this.resetMockListenerCalls();
    handler.trigger('event1', 'a');
    assert.deepEqual({
        'listener3': [[handler, 'event1', 'a']]
    }, this.mockListenerCalls(), 'calls');

    this.assertListenerUUIDs(handler.listeners('event1'), [listener3]);
    this.assertListenerUUIDs(handler.listeners('event2'), [listener, listener2, listener3]);

    this.resetMockListenerCalls();
    handler.trigger('event2', 12);
    assert.deepEqual({
        'listener1': [[handler, 'event2', 12]],
        'listener2': [[handler, 'event2', 12]],
        'listener3': [[handler, 'event2', 12]]
    }, this.mockListenerCalls(), 'calls');

    this.assertListenerUUIDs(handler.listeners('event1'), [listener3]);
    this.assertListenerUUIDs(handler.listeners('event2'), [listener3]);
});

QUnit.test('creme.component.EventHandler.one ()', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('listener1'),
        listener2 = this.mockRawListener('listener2');

    handler.one('event1', listener);
    handler.bind('event1', listener2);
    handler.one('event2', listener);

    this.assertListenerUUIDs(handler.listeners('event1'), [listener, listener2]);
    this.assertListenerUUIDs(handler.listeners('event2'), [listener]);

    assert.deepEqual({}, this.mockListenerCalls());

    handler.trigger('event1', 'a');
    assert.deepEqual({
        'listener1': [[handler, 'event1', 'a']],
        'listener2': [[handler, 'event1', 'a']]
    }, this.mockListenerCalls(), 'calls');

    this.assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    this.assertListenerUUIDs(handler.listeners('event2'), [listener]);

    this.resetMockListenerCalls();
    handler.trigger('event2', 12);

    this.assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    this.assertListenerUUIDs(handler.listeners('event2'), []);

    assert.deepEqual({
        'listener1': [[handler, 'event2', 12]]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();
    handler.trigger('event2', 12);

    this.assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    this.assertListenerUUIDs(handler.listeners('event2'), []);

    assert.deepEqual({}, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();
    handler.trigger('event1', 12);

    this.assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    this.assertListenerUUIDs(handler.listeners('event2'), []);

    assert.deepEqual({
        'listener2': [[handler, 'event1', 12]]
    }, this.mockListenerCalls(), 'calls');
});

QUnit.test('creme.component.EventHandler.one (decorator)', function(assert) {
    var handler = new creme.component.EventHandler();
    var listener = this.mockRawListener('listener1');
    var decorator_listeners = {
         'event1-pre': this.mockRawListener('listener1a'),
         'event1-post': this.mockRawListener('listener1b')
    };

    var decorator = function(key, listener, args) {
        handler.trigger(key + '-pre', Array.from(args).slice(1));
        listener.apply(this, args);
        handler.trigger(key + '-post', Array.from(args).slice(1));
    };

    handler.on(decorator_listeners);
    handler.one('event1', listener, decorator);
    handler.trigger('event1', 'a');

    assert.deepEqual({
        'listener1a': [[handler, 'event1-pre', 'a']],
        'listener1': [[handler, 'event1', 'a']],
        'listener1b': [[handler, 'event1-post', 'a']]
    }, this.mockListenerCalls(), 'calls');

    this.resetMockListenerCalls();
    handler.trigger('event1', 'a');

    assert.deepEqual({}, this.mockListenerCalls(), 'calls');
});
}(jQuery));
