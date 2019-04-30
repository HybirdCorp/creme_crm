(function($) {

QUnit.module("creme.model.collection.js", new QUnitMixin(QUnitEventMixin));

QUnit.test('creme.model.Collection', function(assert) {
    var _Collection = creme.model.Collection.sub({
        _init_: function(data) {
            this._super_(creme.model.Collection, '_init_');
            this._data = data || [];
        },

        all: function() {
            return this._data;
        }
    });

    var total = 0;
    var count = 0;
    var each_func = function(e, index) {
        total += e;
        count += 1;
    };
    var map_func = function(e, index) {
        return e + index;
    };
    var filter_func = function(e, index) {
        return e % 2 > 0;
    };

    var model = new _Collection();
    equal(undefined, model.get(0));
    equal(undefined, model.get(1));
    equal(undefined, model.get(3));

    equal(undefined, model.first());
    equal(undefined, model.last());

    model.each(each_func);
    equal(0, total);
    equal(0, count);

    deepEqual([], model.map(map_func));
    deepEqual([], model.where(filter_func));

    model = new _Collection([47, 42, 5]);
    equal(47, model.get(0));
    equal(42, model.get(1));
    equal(undefined, model.get(3));

    equal(47, model.first());
    equal(5, model.last());

    model.each(each_func);
    equal(47 + 42 + 5, total);
    equal(3, count);

    deepEqual([47, 42 + 1, 5 + 2], model.map(map_func));
    deepEqual([47, 5], model.where(filter_func));
});

QUnit.test('creme.model.Array.constructor', function(assert) {
    var model = new creme.model.Array();

    equal(0, model.length());
    deepEqual([], model.all());

    model = new creme.model.Array(['a', 'b', 'c']);

    equal(3, model.length());
    deepEqual(['a', 'b', 'c'], model.all());
});

QUnit.test('creme.model.Array.get', function(assert) {
    var model = new creme.model.Array();

    equal(0, model.length());
    deepEqual([], model.all());
    equal(undefined, model.get(0));
    equal(undefined, model.get(10));

    model = new creme.model.Array(['a', 'b', 'c']);

    equal(3, model.length());
    deepEqual(['a', 'b', 'c'], model.all());
    equal('a', model.get(0));
    equal('c', model.get(2));
    equal(undefined, model.get(10));
});

QUnit.test('creme.model.Array.first/last', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    equal('x', model.first());
    equal('z', model.last());

    model = new creme.model.Array(['a']);
    equal('a', model.first());
    equal('a', model.last());

    model = new creme.model.Array();
    equal(undefined, model.first());
    equal(undefined, model.last());
});

QUnit.test('creme.model.Array.clear (empty)', function(assert) {
    var model = new creme.model.Array();
    deepEqual([], this.mockListenerCalls('removed'));

    model.clear();

    deepEqual([], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.clear', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('remove', this.mockListener('removed'));

    deepEqual(['a', 'b', 'c'], model.all());
    deepEqual([], this.mockListenerCalls('removed'));

    model.clear();
    deepEqual([], model.all());
    deepEqual([
                 ['remove', ['a', 'b', 'c'], 0, 2, 'clear']
              ], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.insert (empty)', function(assert) {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert('a');
    deepEqual(['a'], model.all());

    deepEqual([
               ['add', ['a'], 0, 0, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (empty, array)', function(assert) {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert(['a', 'c', 'h']);
    deepEqual(['a', 'c', 'h'], model.all());

    deepEqual([
               ['add', ['a', 'c', 'h'], 0, 2, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (front)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert('d');
    deepEqual(['d', 'a', 'b', 'c'], model.all());

    deepEqual([
               ['add', ['d'], 0, 0, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (front, array)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert(['d', 'e', 'f']);
    deepEqual(['d', 'e', 'f', 'a', 'b', 'c'], model.all());

    deepEqual([
               ['add', ['d', 'e', 'f'], 0, 2, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (back)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert('d', model.length());
    deepEqual(['a', 'b', 'c', 'd'], model.all());

    deepEqual([
               ['add', ['d'], 3, 3, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (back, array)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert(['d', 'e', 'f'], model.length());
    deepEqual(['a', 'b', 'c', 'd', 'e', 'f'], model.all());

    deepEqual([
               ['add', ['d', 'e', 'f'], 3, 5, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert('d', 1);

    deepEqual(['a', 'd', 'b', 'c'], model.all());

    deepEqual([
               ['add', ['d'], 1, 1, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (array)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert(['d', 'e', 'f'], 1);

    deepEqual(['a', 'd', 'e', 'f', 'b', 'c'], model.all());

    deepEqual([
               ['add', ['d', 'e', 'f'], 1, 3, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (out of bound)', function(assert) {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    this.assertRaises(function() { model.insert('a', 10); }, Error, 'Error: index out of bound');
    this.assertRaises(function() { model.insert('b', -1); }, Error, 'Error: index out of bound');

    deepEqual([], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.append', function(assert) {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.append('a');
    model.append(['b', 'c']);

    deepEqual(['a', 'b', 'c'], model.all());
    deepEqual([
               ['add', ['a'], 0, 0, 'insert'],
               ['add', ['b', 'c'], 1, 2, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.prepend', function(assert) {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.prepend('a');
    model.prepend(['b', 'c']);

    deepEqual(['b', 'c', 'a'], model.all());
    deepEqual([
               ['add', ['a'], 0, 0, 'insert'],
               ['add', ['b', 'c'], 0, 1, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.get', function(assert) {
    var model = new creme.model.Array();
    equal(undefined, model.get(0));

    model.append('a');
    equal('a', model.get(0));
    equal(undefined, model.get(1));
});

QUnit.test('creme.model.Array.each', function(assert) {
    var model = new creme.model.Array();
    var total = 0;
    var count = 0;
    var sum = function(e, index) {
        equal(index, count);
        total += e;
        count += 1;
    };

    model.each(sum);
    equal(0, total);
    equal(0, count);

    model = new creme.model.Array([1, -5, 4.7, 8.1, 12]);

    model.each(sum);
    equal(1 - 5 + 4.7 + 8.1 + 12, total);
    equal(5, count);
});

QUnit.test('creme.model.Array.map', function(assert) {
    var model = new creme.model.Array();
    var addidx = function(e, index) {
        return e + index;
    };

    deepEqual([], model.map(addidx));

    model = new creme.model.Array([1, -5, 4.7, 8.1, 12]);

    deepEqual([1, 1 - 5, 2 + 4.7, 3 + 8.1, 4 + 12], model.map(addidx));
});

QUnit.test('creme.model.Array.indexOf', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c', 'd', 12]);

    equal(undefined, model.comparator());

    equal(0, model.indexOf('a'));
    equal(1, model.indexOf('b'));
    equal(2, model.indexOf('c'));
    equal(3, model.indexOf('d'));
    equal(4, model.indexOf(12));

    equal(-1, model.indexOf('unknown'));
    equal(-1, model.indexOf(1154));
});

QUnit.test('creme.model.Array.indexOf (comparator)', function(assert) {
    var comparator = function(a, b) {
        if (Array.isArray(b) === false) { return a[0] - b; }

        if (a[0] !== b[0]) { return a[0] - b[0]; }

        return a[1] < b[1] ? -1 : (a[1] > b[1] ? 1 : 0);
    };

    var model = new creme.model.Array([[1, 'a'], [1, 'b'], [2, 'c'], [8, 'd'], [12, 12]], comparator);

    equal(0, comparator([1, 'a'], 1));
    equal(-2, comparator([1, 'a'], 3));
    equal(3, comparator([3, 'a'], 0));

    equal(0, comparator([1, 'a'], [1, 'a']));
    equal(-1, comparator([1, 'a'], [1, 'b']));
    equal(1, comparator([1, 'c'], [1, 'a']));
    equal(-1, comparator([1, 'a'], [1, 'c']));

    equal(-5, comparator([3, 'a'], [8, 'b']));
    equal(5, comparator([8, 'b'], [3, 'a']));

    equal(comparator, model.comparator());
    equal(-1, model.indexOf('a'));

    equal(0, model.indexOf(1));
    equal(0, model.indexOf([1, 'a']));
    equal(1, model.indexOf([1, 'b']));

    equal(-1, model.indexOf('d'));
    equal(3, model.indexOf(8));
    equal(3, model.indexOf([8, 'd']));
    equal(-1, model.indexOf([8, 'h']));

    equal(-1, model.indexOf('unknown'));
    equal(-1, model.indexOf(1154));
});

QUnit.test('creme.model.Array.indicesOf', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c', 'd', 12]);

    equal(undefined, model.comparator());

    equal(0, model.indicesOf('a'));
    equal(1, model.indicesOf('b'));
    equal(2, model.indicesOf('c'));
    equal(3, model.indicesOf('d'));
    equal(4, model.indicesOf(12));

    deepEqual([0, 1], model.indicesOf(['a', 'b']));
    deepEqual([2, 3, 4], model.indicesOf(['c', 'd', 12]));
    deepEqual([0, 3], model.indicesOf(['a', 'd']));
    deepEqual([0, 4], model.indicesOf(['a', 'unknown', 1154, 12]));

    equal(-1, model.indicesOf([]));
    equal(-1, model.indicesOf('unknown'));
    equal(-1, model.indicesOf(1154));
    equal(-1, model.indicesOf(['unknown', 1154]));
});

QUnit.test('creme.model.Array.indicesOf (comparator)', function(assert) {
    var comparator = function(a, b) {
        if (Array.isArray(b) === false) { return a[0] - b; }

        if (a[0] !== b[0]) { return a[0] - b[0]; }

        return a[1] < b[1] ? -1 : (a[1] > b[1] ? 1 : 0);
    };

    var model = new creme.model.Array([[1, 'a'], [1, 'b'], [2, 'c'], [8, 'd'], [12, 12]], comparator);

    equal(0, comparator([1, 'a'], 1));
    equal(-2, comparator([1, 'a'], 3));
    equal(3, comparator([3, 'a'], 0));

    equal(0, comparator([1, 'a'], [1, 'a']));
    equal(-1, comparator([1, 'a'], [1, 'b']));
    equal(1, comparator([1, 'c'], [1, 'a']));
    equal(-1, comparator([1, 'a'], [1, 'c']));

    equal(-5, comparator([3, 'a'], [8, 'b']));
    equal(5, comparator([8, 'b'], [3, 'a']));

    equal(comparator, model.comparator());
    equal(-1, model.indicesOf('a'));

    deepEqual([0, 1], model.indicesOf(1));
    equal(2, model.indicesOf(2));

    equal(0, model.indicesOf([[1, 'a']]));
    equal(1, model.indicesOf([[1, 'b']]));

    equal(-1, model.indicesOf('d'));
    equal(3, model.indicesOf(8));
    equal(3, model.indicesOf([[8, 'd']]));
    equal(-1, model.indicesOf([[8, 'h']]));

    deepEqual([0, 1], model.indicesOf([[1, 'a'], [1, 'b']]));
    deepEqual([2, 3, 4], model.indicesOf([[2, 'c'], [8, 'd'], [12, 12]]));
    deepEqual([0, 3], model.indicesOf([[1, 'a'], [8, 'd']]));
    deepEqual([0, 4], model.indicesOf([[1, 'a'], 'unknown', 1154, [12, 12]]));

    equal(-1, model.indicesOf([]));
    equal(-1, model.indicesOf('unknown'));
    equal(-1, model.indicesOf(1154));
    equal(-1, model.indicesOf(['unknown', 1154]));
});
QUnit.test('creme.model.Array.pop (empty)', function(assert) {
    var model = new creme.model.Array();
    model.bind('remove', this.mockListener('removed'));
    deepEqual([], this.mockListenerCalls('removed'));

    equal(undefined, model.pop());

    deepEqual([], model.all());
    deepEqual([], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.pop', function(assert) {
    var model = new creme.model.Array(['a', 'b']);
    model.bind('remove', this.mockListener('removed'));
    deepEqual([], this.mockListenerCalls('removed'));

    equal('b', model.pop());
    equal('a', model.pop());

    deepEqual([], model.all());
    deepEqual([
               ['remove', ['b'], 1, 1, 'remove'],
               ['remove', ['a'], 0, 0, 'remove']
              ], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.remove', function(assert) {
    var model = new creme.model.Array(['a', 'b']);
    model.bind('remove', this.mockListener('removed'));
    deepEqual([], this.mockListenerCalls('removed'));

    deepEqual([], model.remove(undefined));
    deepEqual([], model.remove('c'));

    deepEqual([], this.mockListenerCalls('removed'));

    deepEqual(['a'], model.remove('a'));
    deepEqual(['b'], model.remove('b'));

    deepEqual([
               ['remove', ['a'], 0, 0, 'remove'],
               ['remove', ['b'], 0, 0, 'remove']
              ], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.remove (array)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c', 'd']);
    model.bind('remove', this.mockListener('removed'));
    deepEqual([], this.mockListenerCalls('removed'));

    deepEqual([], model.remove(undefined));
    deepEqual([], model.remove('x'));

    deepEqual([], this.mockListenerCalls('removed'));

    deepEqual(['b', 'd'], model.remove(['b', 'd', 'x']));

    deepEqual([
               ['remove', ['b'], 1, 1, 'remove'],
               ['remove', ['d'], 2, 2, 'remove']
              ], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.removeAt', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c', 'd']);
    model.bind('remove', this.mockListener('removed'));
    deepEqual([], this.mockListenerCalls('removed'));

    this.assertRaises(function() { model.removeAt(-1); }, Error, 'Error: index out of bound');
    this.assertRaises(function() { model.removeAt(10); }, Error, 'Error: index out of bound');

    deepEqual([], this.mockListenerCalls('removed'));

    deepEqual('d', model.removeAt(3));

    deepEqual('a', model.removeAt(0));
    deepEqual('b', model.removeAt(0));

    deepEqual([
               ['remove', ['d'], 3, 3, 'remove'],
               ['remove', ['a'], 0, 0, 'remove'],
               ['remove', ['b'], 0, 0, 'remove']
              ], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.reset (empty)', function(assert) {
    var model = new creme.model.Array();
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset();

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));

    model.reset(['a', 'b', 'c']);

    deepEqual(['a', 'b', 'c'], model.all());
    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([
               ['add', ['a', 'b', 'c'], 0, 2, 'reset']
              ], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Array.reset (clear)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset();

    deepEqual([], model.all());
    deepEqual([
               ['remove', ['x', 'y', 'z'], 0, 2, 'reset']
              ], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Array.reset (update)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset(['a', 'b', 'c']);

    deepEqual(['a', 'b', 'c'], model.all());
    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([
               ['update', ['a', 'b', 'c'], 0, 2, ['x', 'y', 'z'], 'reset']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Array.reset (add)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset(['a', 'b', 'c', 'e', 'f', 'g']);

    deepEqual(['a', 'b', 'c', 'e', 'f', 'g'], model.all());
    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([
               ['add', ['e', 'f', 'g'], 3, 5, 'reset']
              ], this.mockListenerCalls('added'));
    deepEqual([
               ['update', ['a', 'b', 'c'], 0, 2, ['x', 'y', 'z'], 'reset']
              ], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();

    model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset(['a', 'b', 'c', 'e']);

    deepEqual(['a', 'b', 'c', 'e'], model.all());
    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([
               ['add', ['e'], 3, 3, 'reset']
              ], this.mockListenerCalls('added'));
    deepEqual([
               ['update', ['a', 'b', 'c'], 0, 2, ['x', 'y', 'z'], 'reset']
              ], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();

    model = new creme.model.Array(['x']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset(['a', 'b', 'c']);

    deepEqual(['a', 'b', 'c'], model.all());
    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([
               ['add', ['b', 'c'], 1, 2, 'reset']
              ], this.mockListenerCalls('added'));
    deepEqual([
               ['update', ['a'], 0, 0, ['x'], 'reset']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Array.reset (remove)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset(['a']);

    deepEqual(['a'], model.all());
    deepEqual([
               ['remove', ['y', 'z'], 1, 2, 'reset']
              ], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([
               ['update', ['a'], 0, 0, ['x'], 'reset']
              ], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();

    model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset(['a', 'b']);

    deepEqual(['a', 'b'], model.all());
    deepEqual([
               ['remove', ['z'], 2, 2, 'reset']
              ], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([
               ['update', ['a', 'b'], 0, 1, ['x', 'y'], 'reset']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Array.set (update)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.set('a', 1);

    deepEqual(['x', 'a', 'z'], model.all());
    deepEqual([
               ['update', ['a'], 1, 1, ['y'], 'set']
              ], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.set (out of bound)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    this.assertRaises(function() {
        model.set('a', -1);
    }, Error, 'Error: index out of bound');

    this.assertRaises(function() {
        model.set('a', 4);
    }, Error, 'Error: index out of bound');

    deepEqual(['x', 'y', 'z'], model.all());
    deepEqual([], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.patch (array)', function(assert) {
    var model = new creme.model.Array();
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    deepEqual([], this.mockListenerCalls('model'));
    deepEqual([], model.all());

    model.patch(['a', 'b', 'c']);

    deepEqual(['a', 'b', 'c'], model.all());
    deepEqual([['add', ['a', 'b', 'c'], 0, 2, 'reset'], ['reset']], this.mockListenerCalls('model'));

    this.resetMockListenerCalls();
    model.patch(['x', 'y', 'z', 'w']);

    deepEqual(['x', 'y', 'z', 'w'], model.all());
    deepEqual([['update', ['x', 'y', 'z'], 0, 2, ['a', 'b', 'c'], 'reset'],
               ['add', ['w'], 3, 3, 'reset'],
               ['reset']], this.mockListenerCalls('model'));
});

QUnit.test('creme.model.Array.patch (diff, add)', function(assert) {
    var model = new creme.model.Array();
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    deepEqual([], this.mockListenerCalls('model'));
    deepEqual([], model.all());

    model.patch({add: ['x', 'y']});

    deepEqual(['x', 'y'], model.all());
    deepEqual([['add', ['x', 'y'], 0, 1, 'insert']], this.mockListenerCalls('model'));
});

QUnit.test('creme.model.Array.patch (diff, remove)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    deepEqual([], this.mockListenerCalls('model'));
    deepEqual(['a', 'b', 'c'], model.all());

    model.patch({remove: ['b', 'c']});

    deepEqual(['a'], model.all());
    deepEqual([['remove', ['b'], 1, 1, 'remove'],
               ['remove', ['c'], 1, 1, 'remove']], this.mockListenerCalls('model'));
});

QUnit.test('creme.model.Array.patch (diff, update)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    deepEqual([], this.mockListenerCalls('model'));
    deepEqual(['a', 'b', 'c'], model.all());

    model.patch({update: [['y', 0], ['k', 2]]});

    deepEqual(['y', 'b', 'k'], model.all());
    deepEqual([['update', ['y'], 0, 0, ['a'], 'set'],
               ['update', ['k'], 2, 2, ['c'], 'set']], this.mockListenerCalls('model'));
});

QUnit.test('creme.model.Array.reverse', function(assert) {
    var model = new creme.model.Array([1, 4, 5, 3, 7, 0]);
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));
    model.bind('reverse', this.mockListener('reversed'));

    model.reverse();

    deepEqual([0, 7, 3, 5, 4, 1], model.all());
    deepEqual([
               ['update', [0, 7, 3, 5, 4, 1], 0, 5, [1, 4, 5, 3, 7, 0], 'reverse']
              ], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['reverse']], this.mockListenerCalls('reversed'));
});

QUnit.test('creme.model.Array.sort', function(assert) {
    var model = new creme.model.Array([1, 4, 5, 3, 7, 0]);
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));
    model.bind('sort', this.mockListener('sorted'));

    model.sort();

    deepEqual([0, 1, 3, 4, 5, 7], model.all());
    deepEqual([
               ['update', [0, 1, 3, 4, 5, 7], 0, 5, [1, 4, 5, 3, 7, 0], 'sort']
              ], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['sort']], this.mockListenerCalls('sorted'));

    this.resetMockListenerCalls();
    model.sort();

    deepEqual([0, 1, 3, 4, 5, 7], model.all());
    deepEqual([
               ['update', [0, 1, 3, 4, 5, 7], 0, 5, [0, 1, 3, 4, 5, 7], 'sort']
              ], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['sort']], this.mockListenerCalls('sorted'));
});

QUnit.test('creme.model.Array.sort (comparator)', function(assert) {
    var desc = function(a, b) { return b - a; };
    var asc = function(a, b) { return a - b; };

    var model = new creme.model.Array([1, 4, 5, 3, 7, 0]);
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));
    model.bind('sort', this.mockListener('sorted'));

    model.sort();

    deepEqual([0, 1, 3, 4, 5, 7], model.all());
    deepEqual([
               ['update', [0, 1, 3, 4, 5, 7], 0, 5, [1, 4, 5, 3, 7, 0], 'sort']
              ], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['sort']], this.mockListenerCalls('sorted'));

    this.resetMockListenerCalls();
    model.sort(desc);

    deepEqual([7, 5, 4, 3, 1, 0], model.all());
    deepEqual([
               ['update', [7, 5, 4, 3, 1, 0], 0, 5, [0, 1, 3, 4, 5, 7], 'sort']
              ], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['sort']], this.mockListenerCalls('sorted'));

    model.reset([1, 4, 5, 3, 7, 0]);
    this.resetMockListenerCalls();

    model.comparator(desc).sort();

    deepEqual([7, 5, 4, 3, 1, 0], model.all());
    deepEqual([
               ['update', [7, 5, 4, 3, 1, 0], 0, 5, [1, 4, 5, 3, 7, 0], 'sort']
              ], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['sort']], this.mockListenerCalls('sorted'));

    model.reset([1, 4, 5, 3, 7, 0]);
    this.resetMockListenerCalls();

    model.comparator(desc).sort(asc);

    deepEqual([0, 1, 3, 4, 5, 7], model.all());
    deepEqual([
               ['update', [0, 1, 3, 4, 5, 7], 0, 5, [1, 4, 5, 3, 7, 0], 'sort']
              ], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['sort']], this.mockListenerCalls('sorted'));
});

QUnit.test('creme.model.Delegate.constructor (empty)', function(assert) {
    var delegate = new creme.model.Delegate();

    equal(undefined, delegate.delegate());
    equal(0, delegate.length());
    deepEqual([], delegate.all());
});

QUnit.test('creme.model.Delegate.constructor (model)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    var delegate = new creme.model.Delegate(model);

    equal(model, delegate.delegate());
    equal(3, delegate.length());
    deepEqual(['x', 'y', 'z'], delegate.all());
});

QUnit.test('creme.model.Delegate (update)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    var delegate = new creme.model.Delegate(model);
    delegate.bind('remove', this.mockListener('removed'));
    delegate.bind('add', this.mockListener('added'));
    delegate.bind('update', this.mockListener('updated'));

    deepEqual(['x', 'y', 'z'], delegate.all());
    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));

    model.set('a', 1);

    deepEqual(['x', 'a', 'z'], delegate.all());
    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([
               ['update', ['a'], 1, 1, ['y'], 'set']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Delegate (add)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    var delegate = new creme.model.Delegate(model);
    delegate.bind('remove', this.mockListener('removed'));
    delegate.bind('add', this.mockListener('added'));
    delegate.bind('update', this.mockListener('updated'));

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));

    model.append(['a', 'b']);

    deepEqual(['x', 'y', 'z', 'a', 'b'], delegate.all());
    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([
               ['add', ['a', 'b'], 3, 4, 'insert']
              ], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Delegate (remove)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    var delegate = new creme.model.Delegate(model);
    delegate.bind('remove', this.mockListener('removed'));
    delegate.bind('add', this.mockListener('added'));
    delegate.bind('update', this.mockListener('updated'));

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));

    model.removeAt(1);

    deepEqual(['x', 'z'], delegate.all());
    deepEqual([
               ['remove', ['y'], 1, 1, 'remove']
              ], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();
    model.removeAt(0);

    deepEqual(['z'], delegate.all());
    deepEqual([
               ['remove', ['x'], 0, 0, 'remove']
              ], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Delegate (replace delegate)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    var modelB = new creme.model.Array(['a', 'b', 'c']);

    var delegate = new creme.model.Delegate(model);
    delegate.bind('remove', this.mockListener('removed'));
    delegate.bind('add', this.mockListener('added'));
    delegate.bind('update', this.mockListener('updated'));

    equal(model, delegate.delegate());

    delegate.delegate(model);
    equal(model, delegate.delegate());
    deepEqual(['x', 'y', 'z'], delegate.all());

    model.append(12);
    modelB.append(13);

    deepEqual(['x', 'y', 'z', 12], delegate.all());
    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([
               ['add', [12], 3, 3, 'insert']
              ], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();

    // replace delegate model by modelB
    delegate.delegate(modelB);
    equal(modelB, delegate.delegate());

    model.append(14);
    modelB.append(15);

    deepEqual(['a', 'b', 'c', 13, 15], delegate.all());
    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([
               ['add', [15], 4, 4, 'insert']
              ], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();

    // remove delegate model
    delegate.delegate(null);
    equal(null, delegate.delegate());

    model.append(16);
    modelB.append(17);

    deepEqual([], delegate.all());
    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Filter (update)', function(assert) {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var pairs = new creme.model.Filter(model, function(item) { return (item % 2) === 0; });
    pairs.bind('remove', this.mockListener('removed'));
    pairs.bind('add', this.mockListener('added'));
    pairs.bind('update', this.mockListener('updated'));

    deepEqual([1, 2, 3, 4, 5], model.all());
    deepEqual([2, 4], pairs.all());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));

    model.set(16, 2);

    deepEqual([1, 2, 16, 4, 5], model.all(), 'set(16, 2)');
    deepEqual([2, 16, 4], pairs.all());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([
               ['add', [4], 2, 2, 'reset']
              ], this.mockListenerCalls('added'));
    deepEqual([
               ['update', [2, 16], 0, 1, [2, 4], 'reset']
              ], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();
    model.set(15, 2);

    deepEqual([1, 2, 15, 4, 5], model.all());
    deepEqual([2, 4], pairs.all());

    deepEqual([
               ['remove', [4], 2, 2, 'reset']
              ], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([
               ['update', [2, 4], 0, 1, [2, 16], 'reset']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Filter (add)', function(assert) {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var pairs = new creme.model.Filter(model, function(item) { return (item % 2) === 0; });
    pairs.bind('remove', this.mockListener('removed'));
    pairs.bind('add', this.mockListener('added'));
    pairs.bind('update', this.mockListener('updated'));

    deepEqual([1, 2, 3, 4, 5], model.all());
    deepEqual([2, 4], pairs.all());

    model.append([16, 18, 7, 9]);

    deepEqual([1, 2, 3, 4, 5, 16, 18, 7, 9], model.all());
    deepEqual([2, 4, 16, 18], pairs.all());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([
               ['add', [16, 18], 2, 3, 'reset']
              ], this.mockListenerCalls('added'));
    deepEqual([
               ['update', [2, 4], 0, 1, [2, 4], 'reset']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Filter (remove)', function(assert) {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var pairs = new creme.model.Filter(model, function(item) { return (item % 2) === 0; });
    pairs.bind('remove', this.mockListener('removed'));
    pairs.bind('add', this.mockListener('added'));
    pairs.bind('update', this.mockListener('updated'));

    deepEqual([1, 2, 3, 4, 5], model.all());
    deepEqual([2, 4], pairs.all());

    model.removeAt(2);

    deepEqual([1, 2, 4, 5], model.all());
    deepEqual([2, 4], pairs.all());

    deepEqual([], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([
               ['update', [2, 4], 0, 1, [2, 4], 'reset']
              ], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();

    model.removeAt(2);

    deepEqual([1, 2, 5], model.all());
    deepEqual([2], pairs.all());

    deepEqual([
               ['remove', [4], 1, 1, 'reset']
              ], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([
               ['update', [2], 0, 0, [2], 'reset']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Filter (no filter)', function(assert) {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var nofilter = new creme.model.Filter(model, null);
    nofilter.bind('remove', this.mockListener('removed'));
    nofilter.bind('add', this.mockListener('added'));
    nofilter.bind('update', this.mockListener('updated'));

    deepEqual([1, 2, 3, 4, 5], model.all());
    deepEqual([1, 2, 3, 4, 5], nofilter.all());

    model.removeAt(2);

    deepEqual([1, 2, 4, 5], model.all());
    deepEqual([1, 2, 4, 5], nofilter.all());

    model.append([16, 18]);

    deepEqual([1, 2, 4, 5, 16, 18], model.all());
    deepEqual([1, 2, 4, 5, 16, 18], nofilter.all());

    nofilter.filter(function(item) { return (item % 2) === 0; });

    deepEqual([1, 2, 4, 5, 16, 18], model.all());
    deepEqual([2, 4, 16, 18], nofilter.all());

    nofilter.filter(null);

    deepEqual([1, 2, 4, 5, 16, 18], model.all());
    deepEqual([1, 2, 4, 5, 16, 18], nofilter.all());
});

QUnit.test('creme.model.Filter (lambda filter)', function(assert) {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var lambda = new creme.utils.Lambda('(item % (this.divide || 1) === 0)', 'item');
    var filter = new creme.model.Filter(model, lambda);
    filter.bind('remove', this.mockListener('removed'));
    filter.bind('add', this.mockListener('added'));
    filter.bind('update', this.mockListener('updated'));

    deepEqual([1, 2, 3, 4, 5], model.all());
    deepEqual([1, 2, 3, 4, 5], filter.all());

    model.removeAt(2);

    deepEqual([1, 2, 4, 5], model.all());
    deepEqual([1, 2, 4, 5], filter.all());

    model.append([16, 18]);

    deepEqual([1, 2, 4, 5, 16, 18], model.all());
    deepEqual([1, 2, 4, 5, 16, 18], filter.all());

    filter.filter(lambda.bind({divide: 2}));
    deepEqual({divide: 2}, lambda._context);
    equal(false, lambda.invoke(1), '1 is odd');
    equal(true, lambda.invoke(2), '2 is even');

    deepEqual([1, 2, 4, 5, 16, 18], model.all());
    deepEqual([2, 4, 16, 18], filter.all(), 'filtered (%2)');

    filter.filter(lambda.bind({divide: 3}));
    equal(false, lambda.invoke(1));
    equal(false, lambda.invoke(2));
    equal(true, lambda.invoke(3));

    deepEqual([1, 2, 4, 5, 16, 18], model.all());
    deepEqual([18], filter.all(), 'filtered (%3)');

    filter.filter(lambda.bind({divide: 4}));
    deepEqual([1, 2, 4, 5, 16, 18], model.all());
    deepEqual([4, 16], filter.all(), 'filtered (%4)');
});

QUnit.test('creme.model.Filter (string filter)', function(assert) {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var filter = new creme.model.Filter(model, '(item % 2 === 0)');
    filter.bind('remove', this.mockListener('removed'));
    filter.bind('add', this.mockListener('added'));
    filter.bind('update', this.mockListener('updated'));

    deepEqual([1, 2, 3, 4, 5], model.all());
    deepEqual([2, 4], filter.all());

    model.removeAt(2);

    deepEqual([1, 2, 4, 5], model.all());
    deepEqual([2, 4], filter.all());

    model.append([16, 18]);

    deepEqual([1, 2, 4, 5, 16, 18], model.all());
    deepEqual([2, 4, 16, 18], filter.all());
});

}(jQuery));
