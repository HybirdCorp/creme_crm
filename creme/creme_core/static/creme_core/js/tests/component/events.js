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
});
