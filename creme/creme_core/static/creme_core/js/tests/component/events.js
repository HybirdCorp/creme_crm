module("creme.component.EventHandler.js", {
  setup: function() {
      this.resetMockCalls();
  },

  teardown: function() {},

  resetMockCalls: function() {
      this._eventListenerCalls = [];
  },

  mockListener: function(name)
  {
      var self = this;
      return (function(name) {return function() {
          self._eventListenerCalls.push([name, this].concat(Array.copy(arguments)));
      }})(name);
  }
});

function assertListenerUUIDs(listeners, expected)
{
    var uuid_getter = function(l) {return l.__eventuuid__;};
    deepEqual(listeners.map(uuid_getter), expected.map(uuid_getter));
}

test('creme.component.EventHandler.bind (single key, single listener)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    deepEqual({}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));

    handler.bind('event1', listener);

    deepEqual({'event1':[listener]}, handler._listeners);
    deepEqual([listener], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));

    handler.bind('event2', listener);

    deepEqual({'event1':[listener], 'event2':[listener]}, handler._listeners);
    deepEqual([listener], handler.listeners('event1'));
    deepEqual([listener], handler.listeners('event2'));

    handler.bind('event1', listener2);

    deepEqual({'event1':[listener, listener2], 'event2':[listener]}, handler._listeners);
    deepEqual([listener, listener2], handler.listeners('event1'));
    deepEqual([listener], handler.listeners('event2'));

    handler.trigger('event1', 'a');
    deepEqual([['1', handler, 'event1', 'a'], ['2', handler, 'event1', 'a']], this._eventListenerCalls);

    this.resetMockCalls();

    handler.trigger('event2', 'b');
    deepEqual([['1', handler, 'event2', 'b']], this._eventListenerCalls);
});

test('creme.component.EventHandler.bind (single key, multiple listener)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    deepEqual({}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));

    handler.bind('event1', [listener, listener2]);

    deepEqual({'event1':[listener, listener2]}, handler._listeners);
    deepEqual([listener, listener2], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));

    handler.trigger('event1', 'a');
    deepEqual([['1', handler, 'event1', 'a'], ['2', handler, 'event1', 'a']], this._eventListenerCalls);
});

test('creme.component.EventHandler.bind (multiple key, single listener)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    deepEqual({}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));
    deepEqual([], handler.listeners('event3'));

    handler.bind(['event1', 'event2'], listener);

    deepEqual({'event1':[listener], 'event2':[listener]}, handler._listeners);
    deepEqual([listener], handler.listeners('event1'));
    deepEqual([listener], handler.listeners('event2'));
    deepEqual([], handler.listeners('event3'));

    handler.bind(['event1', 'event2', 'event3'], listener2);

    deepEqual({'event1':[listener, listener2], 'event2':[listener, listener2], 'event3':[listener2]}, handler._listeners);
    deepEqual([listener, listener2], handler.listeners('event1'));
    deepEqual([listener, listener2], handler.listeners('event2'));
    deepEqual([listener2], handler.listeners('event3'));

    handler.trigger('event1', 'a');
    deepEqual([['1', handler, 'event1', 'a'], ['2', handler, 'event1', 'a']], this._eventListenerCalls);

    this.resetMockCalls();

    handler.trigger('event2', 'b');
    deepEqual([['1', handler, 'event2', 'b'], ['2', handler, 'event2', 'b']], this._eventListenerCalls);

    this.resetMockCalls();

    handler.trigger('event3', 'd');
    deepEqual([['2', handler, 'event3', 'd']], this._eventListenerCalls);

    handler.trigger('event3', 'd');
    deepEqual([['2', handler, 'event3', 'd'], ['2', handler, 'event3', 'd']], this._eventListenerCalls);
});

test('creme.component.EventHandler.bind (multiple key, multiple listener)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    deepEqual({}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));
    deepEqual([], handler.listeners('event3'));

    handler.bind(['event1', 'event2'], [listener, listener2]);

    deepEqual({'event1':[listener, listener2], 'event2':[listener, listener2]}, handler._listeners);
    deepEqual([listener, listener2], handler.listeners('event1'));
    deepEqual([listener, listener2], handler.listeners('event2'));
    deepEqual([], handler.listeners('event3'));

    handler.bind(['event1', 'event2', 'event3'], [listener, listener2]);

    deepEqual({'event1':[listener, listener2, listener, listener2], 
               'event2':[listener, listener2, listener, listener2],
               'event3':[listener, listener2]}, handler._listeners);
    deepEqual([listener, listener2, listener, listener2], handler.listeners('event1'));
    deepEqual([listener, listener2, listener, listener2], handler.listeners('event2'));
    deepEqual([listener, listener2], handler.listeners('event3'));
});

test('creme.component.EventHandler.bind (split key, multiple listener)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    deepEqual({}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));
    deepEqual([], handler.listeners('event3'));

    handler.bind('event1 event2', [listener, listener2]);

    deepEqual({'event1':[listener, listener2], 'event2':[listener, listener2]}, handler._listeners);
    deepEqual([listener, listener2], handler.listeners('event1'));
    deepEqual([listener, listener2], handler.listeners('event2'));
    deepEqual([], handler.listeners('event3'));

    handler.bind('event1 event2 event3', [listener, listener2]);

    deepEqual({'event1':[listener, listener2, listener, listener2], 
               'event2':[listener, listener2, listener, listener2],
               'event3':[listener, listener2]}, handler._listeners);
    deepEqual([listener, listener2, listener, listener2], handler.listeners('event1'));
    deepEqual([listener, listener2, listener, listener2], handler.listeners('event2'));
    deepEqual([listener, listener2], handler.listeners('event3'));
});

test('creme.component.EventHandler.bind (decorator)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');
    var decorator = function(key, listener, args) {
        return listener.apply(this, args.concat(['decorated']));
    }

    deepEqual({}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));
    deepEqual([], handler.listeners('event3'));

    handler.bind(['event1', 'event2'], listener);
    handler.bind(['event1', 'event3'], listener2, decorator);

    handler.trigger('event1');
    deepEqual([['1', handler, 'event1'], ['2', handler, 'event1', 'decorated']], this._eventListenerCalls);
    
    this.resetMockCalls();
    handler.trigger('event2', 12);
    deepEqual([['1', handler, 'event2', 12]], this._eventListenerCalls);

    this.resetMockCalls();
    handler.trigger('event3', 38);
    deepEqual([['2', handler, 'event3', 38, 'decorated']], this._eventListenerCalls);
});

test('creme.component.EventHandler.bind (object)', function() {
    var handler = new creme.component.EventHandler();
    var listeners = {
            event1: this.mockListener('1'),
            event2: [this.mockListener('2'), this.mockListener('3')],
        }

    deepEqual({}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));

    handler.bind(listeners);

    deepEqual({'event1':[listeners.event1], 
               'event2':[listeners.event2[0], listeners.event2[1]]}, handler._listeners);

    handler.trigger('event1');
    deepEqual([['1', handler, 'event1']], this._eventListenerCalls);

    this.resetMockCalls();
    handler.trigger('event2');
    deepEqual([['2', handler, 'event2'], ['3', handler, 'event2']], this._eventListenerCalls);

    this.resetMockCalls();
    handler.trigger('event3');
    deepEqual([], this._eventListenerCalls);
});

test('creme.component.EventHandler.bind (object array)', function() {
    var handler = new creme.component.EventHandler();
    var listeners1 = {
            event1: this.mockListener('1'),
            event2: [this.mockListener('2'), this.mockListener('3')],
        },
        listeners2 = {
            event1: this.mockListener('2.1'),
            event3: [this.mockListener('2.2'), this.mockListener('2.3')],
        };

    deepEqual({}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));
    deepEqual([], handler.listeners('event3'));

    handler.bind([listeners1, listeners2]);

    deepEqual({'event1':[listeners1.event1, listeners2.event1], 
               'event2':[listeners1.event2[0], listeners1.event2[1]],
               'event3':[listeners2.event3[0], listeners2.event3[1]]}, handler._listeners);

    handler.trigger('event1');
    deepEqual([['1', handler, 'event1'], ['2.1', handler, 'event1']], this._eventListenerCalls);

    this.resetMockCalls();
    handler.trigger('event2');
    deepEqual([['2', handler, 'event2'], ['3', handler, 'event2']], this._eventListenerCalls);

    this.resetMockCalls();
    handler.trigger('event3');
    deepEqual([['2.2', handler, 'event3'], ['2.3', handler, 'event3']], this._eventListenerCalls);
});

test('creme.component.EventHandler.trigger', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    handler.trigger('event1');
    deepEqual([['1', handler, 'event1'], ['2', handler, 'event1']], this._eventListenerCalls);

    this.resetMockCalls();
    handler.trigger('event1', [], this);
    deepEqual([['1', this, 'event1'], ['2', this, 'event1']], this._eventListenerCalls);

    this.resetMockCalls();
    handler.trigger('event1', ['a', 12], this);
    deepEqual([['1', this, 'event1', 'a', 12], ['2', this, 'event1', 'a', 12]], this._eventListenerCalls);
});

test('creme.component.EventHandler.unbind (single key, single listener)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    deepEqual({'event1':[listener, listener2], 'event2':[listener2]}, handler._listeners);
    deepEqual([listener, listener2], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event2', listener); // not bound, do nothing

    deepEqual({'event1':[listener, listener2], 'event2':[listener2]}, handler._listeners);
    deepEqual([listener, listener2], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event1', listener);

    deepEqual({'event1':[listener2], 'event2':[listener2]}, handler._listeners);
    deepEqual([listener2], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event1', listener);

    deepEqual({'event1':[listener2], 'event2':[listener2]}, handler._listeners);
    deepEqual([listener2], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));
});

test('creme.component.EventHandler.unbind (single key, multiple listener)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    deepEqual({'event1':[listener, listener2], 'event2':[listener2]}, handler._listeners);
    deepEqual([listener, listener2], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event1', [listener, listener2]);

    deepEqual({'event1':[], 'event2':[listener2]}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event1', [listener, listener2]);

    deepEqual({'event1':[], 'event2':[listener2]}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));
});

test('creme.component.EventHandler.unbind (multiple key, single listener)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    deepEqual({'event1':[listener, listener2], 'event2':[listener2]}, handler._listeners);
    deepEqual([listener, listener2], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));

    handler.unbind(['event1', 'event2'], [listener2]);

    deepEqual({'event1':[listener], 'event2':[]}, handler._listeners);
    deepEqual([listener], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));

    handler.unbind(['event1', 'event2'], [listener2]);

    deepEqual({'event1':[listener], 'event2':[]}, handler._listeners);
    deepEqual([listener], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));
});

test('creme.component.EventHandler.unbind (multiple key, multiple listener)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    deepEqual({'event1':[listener, listener2], 'event2':[listener2]}, handler._listeners);
    deepEqual([listener, listener2], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));

    handler.unbind(['event1', 'event2'], [listener, listener2]);

    deepEqual({'event1':[], 'event2':[]}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));

    handler.unbind(['event1', 'event2'], [listener, listener2]);

    deepEqual({'event1':[], 'event2':[]}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));
});

test('creme.component.EventHandler.unbind (single key, all listeners)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    deepEqual({'event1':[listener, listener2], 'event2':[listener2]}, handler._listeners);
    deepEqual([listener, listener2], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event1');

    deepEqual({'event1':[], 'event2':[listener2]}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));

    handler.unbind('event1');

    deepEqual({'event1':[], 'event2':[listener2]}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));
});


test('creme.component.EventHandler.unbind (multiple key, all listeners)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    handler.bind('event1', listener);
    handler.bind(['event1', 'event2'], listener2);

    deepEqual({'event1':[listener, listener2], 'event2':[listener2]}, handler._listeners);
    deepEqual([listener, listener2], handler.listeners('event1'));
    deepEqual([listener2], handler.listeners('event2'));

    handler.unbind(['event1', 'event2']);

    deepEqual({'event1':[], 'event2':[]}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));

    handler.unbind(['event1', 'event2']);

    deepEqual({'event1':[], 'event2':[]}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));
});

test('creme.component.EventHandler.unbind (dict)', function() {
    var handler = new creme.component.EventHandler();
    var listeners = {
            event1: this.mockListener('1'),
            event2: [this.mockListener('2'), this.mockListener('3')],
        }

    handler.bind(listeners);

    deepEqual({'event1':[listeners.event1], 
               'event2':[listeners.event2[0], listeners.event2[1]]}, handler._listeners);

    handler.unbind(listeners);

    deepEqual({'event1':[], 'event2':[]}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));

    handler.unbind(listeners);

    deepEqual({'event1':[], 'event2':[]}, handler._listeners);
    deepEqual([], handler.listeners('event1'));
    deepEqual([], handler.listeners('event2'));
});

test('creme.component.EventHandler.unbind (dict array)', function() {
    var handler = new creme.component.EventHandler();
    var listeners1 = {
            event1: this.mockListener('1'),
            event2: [this.mockListener('2'), this.mockListener('3')],
        },
        listeners2 = {
            event1: this.mockListener('2.1'),
            event3: [this.mockListener('2.2'), this.mockListener('2.3')],
        };

    handler.bind([listeners1, listeners2]);

    deepEqual({'event1':[listeners1.event1, listeners2.event1], 
               'event2':[listeners1.event2[0], listeners1.event2[1]],
               'event3':[listeners2.event3[0], listeners2.event3[1]]}, handler._listeners);

    handler.unbind([listeners1, listeners2]);

    deepEqual({'event1':[], 'event2':[], 'event3':[]}, handler._listeners);

    handler.unbind([listeners1, listeners2]);

    deepEqual({'event1':[], 'event2':[], 'event3': []}, handler._listeners);
});

test('creme.component.EventHandler.one (single key, single listener)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    handler.one('event1', listener);
    handler.bind('event1', listener2);

    assertListenerUUIDs(handler.listeners('event1'), [listener, listener2]);

    deepEqual([], this._eventListenerCalls);

    handler.trigger('event1', 'a');
    deepEqual([['1', handler, 'event1', 'a'], ['2', handler, 'event1', 'a']], this._eventListenerCalls, 'calls');

    assertListenerUUIDs(handler.listeners('event1'), [listener2]);

    this._eventListenerCalls = [];
    handler.trigger('event1', 'a');
    deepEqual([['2', handler, 'event1', 'a']], this._eventListenerCalls, 'calls');

    assertListenerUUIDs(handler.listeners('event1'), [listener2]);
});

test('creme.component.EventHandler.one (single key, multiple listeners)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2'),
        listener3 = this.mockListener('3');

    handler.one('event1', [listener, listener2]);
    handler.bind('event1', listener3);

    assertListenerUUIDs(handler.listeners('event1'), [listener, listener2, listener3]);

    deepEqual([], this._eventListenerCalls);

    handler.trigger('event1', 'a');
    deepEqual([['1', handler, 'event1', 'a'], ['2', handler, 'event1', 'a'], ['3', handler, 'event1', 'a']], this._eventListenerCalls, 'calls');

    assertListenerUUIDs(handler.listeners('event1'), [listener3]);
});

test('creme.component.EventHandler.one (multiple key, single listener)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    handler.one(['event1', 'event2'], listener);
    handler.bind(['event1', 'event2'], listener2);

    assertListenerUUIDs(handler.listeners('event1'), [listener, listener2]);
    assertListenerUUIDs(handler.listeners('event2'), [listener, listener2]);

    deepEqual([], this._eventListenerCalls);

    handler.trigger('event1', 'a');
    deepEqual([['1', handler, 'event1', 'a'], ['2', handler, 'event1', 'a']], this._eventListenerCalls, 'calls');

    assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    assertListenerUUIDs(handler.listeners('event2'), [listener, listener2]);

    this._eventListenerCalls = [];
    handler.trigger('event1', 'a');
    deepEqual([['2', handler, 'event1', 'a']], this._eventListenerCalls, 'calls');

    assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    assertListenerUUIDs(handler.listeners('event2'), [listener, listener2]);

    this._eventListenerCalls = [];
    handler.trigger('event2', 12);
    deepEqual([['1', handler, 'event2', 12], ['2', handler, 'event2', 12]], this._eventListenerCalls, 'calls');

    assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    assertListenerUUIDs(handler.listeners('event2'), [listener2]);
});

test('creme.component.EventHandler.one (multiple key, multiple listeners)', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2'),
        listener3 = this.mockListener('3');

    handler.one(['event1', 'event2'], [listener, listener2]);
    handler.bind(['event1', 'event2'], listener3);

    assertListenerUUIDs(handler.listeners('event1'), [listener, listener2, listener3]);
    assertListenerUUIDs(handler.listeners('event2'), [listener, listener2, listener3]);

    deepEqual([], this._eventListenerCalls);

    handler.trigger('event1', 'a');
    deepEqual([['1', handler, 'event1', 'a'], ['2', handler, 'event1', 'a'], ['3', handler, 'event1', 'a']], this._eventListenerCalls, 'calls');

    assertListenerUUIDs(handler.listeners('event1'), [listener3]);
    assertListenerUUIDs(handler.listeners('event2'), [listener, listener2, listener3]);

    this._eventListenerCalls = [];
    handler.trigger('event1', 'a');
    deepEqual([['3', handler, 'event1', 'a']], this._eventListenerCalls, 'calls');

    assertListenerUUIDs(handler.listeners('event1'), [listener3]);
    assertListenerUUIDs(handler.listeners('event2'), [listener, listener2, listener3]);

    this._eventListenerCalls = [];
    handler.trigger('event2', 12);
    deepEqual([['1', handler, 'event2', 12], ['2', handler, 'event2', 12], ['3', handler, 'event2', 12]], this._eventListenerCalls, 'calls');

    assertListenerUUIDs(handler.listeners('event1'), [listener3]);
    assertListenerUUIDs(handler.listeners('event2'), [listener3]);
});

test('creme.component.EventHandler.one ()', function() {
    var handler = new creme.component.EventHandler();
    var listener = this.mockListener('1'),
        listener2 = this.mockListener('2');

    handler.one('event1', listener);
    handler.bind('event1', listener2);
    handler.one('event2', listener);

    assertListenerUUIDs(handler.listeners('event1'), [listener, listener2]);
    assertListenerUUIDs(handler.listeners('event2'), [listener]);

    deepEqual([], this._eventListenerCalls);

    handler.trigger('event1', 'a');
    deepEqual([['1', handler, 'event1', 'a'], ['2', handler, 'event1', 'a']], this._eventListenerCalls, 'calls');

    assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    assertListenerUUIDs(handler.listeners('event2'), [listener]);

    this._eventListenerCalls = [];
    handler.trigger('event2', 12);

    assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    assertListenerUUIDs(handler.listeners('event2'), []);

    deepEqual([['1', handler, 'event2', 12]], this._eventListenerCalls, 'calls');

    this._eventListenerCalls = [];
    handler.trigger('event2', 12);

    assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    assertListenerUUIDs(handler.listeners('event2'), []);

    deepEqual([], this._eventListenerCalls, 'calls');
    
    this._eventListenerCalls = [];
    handler.trigger('event1', 12);

    assertListenerUUIDs(handler.listeners('event1'), [listener2]);
    assertListenerUUIDs(handler.listeners('event2'), []);

    deepEqual([['2', handler, 'event1', 12]], this._eventListenerCalls, 'calls');
});
