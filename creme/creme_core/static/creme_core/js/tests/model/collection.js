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
    assert.equal(undefined, model.get(0));
    assert.equal(undefined, model.get(1));
    assert.equal(undefined, model.get(3));

    assert.equal(undefined, model.first());
    assert.equal(undefined, model.last());

    model.each(each_func);
    assert.equal(0, total);
    assert.equal(0, count);

    assert.deepEqual([], model.map(map_func));
    assert.deepEqual([], model.where(filter_func));

    model = new _Collection([47, 42, 5]);
    assert.equal(47, model.get(0));
    assert.equal(42, model.get(1));
    assert.equal(undefined, model.get(3));

    assert.equal(47, model.first());
    assert.equal(5, model.last());

    model.each(each_func);
    assert.equal(47 + 42 + 5, total);
    assert.equal(3, count);

    assert.deepEqual([47, 42 + 1, 5 + 2], model.map(map_func));
    assert.deepEqual([47, 5], model.where(filter_func));
});

QUnit.test('creme.model.Array.constructor', function(assert) {
    var model = new creme.model.Array();

    assert.equal(0, model.length());
    assert.deepEqual([], model.all());

    model = new creme.model.Array(['a', 'b', 'c']);

    assert.equal(3, model.length());
    assert.deepEqual(['a', 'b', 'c'], model.all());
});

QUnit.test('creme.model.Array.get', function(assert) {
    var model = new creme.model.Array();

    assert.equal(0, model.length());
    assert.deepEqual([], model.all());
    assert.equal(undefined, model.get(0));
    assert.equal(undefined, model.get(10));

    model = new creme.model.Array(['a', 'b', 'c']);

    assert.equal(3, model.length());
    assert.deepEqual(['a', 'b', 'c'], model.all());
    assert.equal('a', model.get(0));
    assert.equal('c', model.get(2));
    assert.equal(undefined, model.get(10));
});

QUnit.test('creme.model.Array.first/last', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    assert.equal('x', model.first());
    assert.equal('z', model.last());

    model = new creme.model.Array(['a']);
    assert.equal('a', model.first());
    assert.equal('a', model.last());

    model = new creme.model.Array();
    assert.equal(undefined, model.first());
    assert.equal(undefined, model.last());
});

QUnit.test('creme.model.Array.clear (empty)', function(assert) {
    var model = new creme.model.Array();
    assert.deepEqual([], this.mockListenerCalls('removed'));

    model.clear();

    assert.deepEqual([], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.clear', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('remove', this.mockListener('removed'));

    assert.deepEqual(['a', 'b', 'c'], model.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));

    model.clear();
    assert.deepEqual([], model.all());
    assert.deepEqual([
                 ['remove', ['a', 'b', 'c'], 0, 2, 'clear']
              ], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.insert (empty)', function(assert) {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    assert.deepEqual([], this.mockListenerCalls('added'));

    model.insert('a');
    assert.deepEqual(['a'], model.all());

    assert.deepEqual([
               ['add', ['a'], 0, 0, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (empty, array)', function(assert) {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    assert.deepEqual([], this.mockListenerCalls('added'));

    model.insert(['a', 'c', 'h']);
    assert.deepEqual(['a', 'c', 'h'], model.all());

    assert.deepEqual([
               ['add', ['a', 'c', 'h'], 0, 2, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (front)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    assert.deepEqual([], this.mockListenerCalls('added'));

    model.insert('d');
    assert.deepEqual(['d', 'a', 'b', 'c'], model.all());

    assert.deepEqual([
               ['add', ['d'], 0, 0, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (front, array)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    assert.deepEqual([], this.mockListenerCalls('added'));

    model.insert(['d', 'e', 'f']);
    assert.deepEqual(['d', 'e', 'f', 'a', 'b', 'c'], model.all());

    assert.deepEqual([
               ['add', ['d', 'e', 'f'], 0, 2, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (back)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    assert.deepEqual([], this.mockListenerCalls('added'));

    model.insert('d', model.length());
    assert.deepEqual(['a', 'b', 'c', 'd'], model.all());

    assert.deepEqual([
               ['add', ['d'], 3, 3, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (back, array)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    assert.deepEqual([], this.mockListenerCalls('added'));

    model.insert(['d', 'e', 'f'], model.length());
    assert.deepEqual(['a', 'b', 'c', 'd', 'e', 'f'], model.all());

    assert.deepEqual([
               ['add', ['d', 'e', 'f'], 3, 5, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    assert.deepEqual([], this.mockListenerCalls('added'));

    model.insert('d', 1);

    assert.deepEqual(['a', 'd', 'b', 'c'], model.all());

    assert.deepEqual([
               ['add', ['d'], 1, 1, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (array)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    assert.deepEqual([], this.mockListenerCalls('added'));

    model.insert(['d', 'e', 'f'], 1);

    assert.deepEqual(['a', 'd', 'e', 'f', 'b', 'c'], model.all());

    assert.deepEqual([
               ['add', ['d', 'e', 'f'], 1, 3, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.insert (out of bound)', function(assert) {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    assert.deepEqual([], this.mockListenerCalls('added'));

    this.assertRaises(function() { model.insert('a', 10); }, Error, 'Error: index out of bound');
    this.assertRaises(function() { model.insert('b', -1); }, Error, 'Error: index out of bound');

    assert.deepEqual([], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.append', function(assert) {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    assert.deepEqual([], this.mockListenerCalls('added'));

    model.append('a');
    model.append(['b', 'c']);

    assert.deepEqual(['a', 'b', 'c'], model.all());
    assert.deepEqual([
               ['add', ['a'], 0, 0, 'insert'],
               ['add', ['b', 'c'], 1, 2, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.prepend', function(assert) {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    assert.deepEqual([], this.mockListenerCalls('added'));

    model.prepend('a');
    model.prepend(['b', 'c']);

    assert.deepEqual(['b', 'c', 'a'], model.all());
    assert.deepEqual([
               ['add', ['a'], 0, 0, 'insert'],
               ['add', ['b', 'c'], 0, 1, 'insert']
              ], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.get', function(assert) {
    var model = new creme.model.Array();
    assert.equal(undefined, model.get(0));

    model.append('a');
    assert.equal('a', model.get(0));
    assert.equal(undefined, model.get(1));
});

QUnit.test('creme.model.Array.each', function(assert) {
    var model = new creme.model.Array();
    var total = 0;
    var count = 0;
    var sum = function(e, index) {
        assert.equal(index, count);
        total += e;
        count += 1;
    };

    model.each(sum);
    assert.equal(0, total);
    assert.equal(0, count);

    model = new creme.model.Array([1, -5, 4.7, 8.1, 12]);

    model.each(sum);
    assert.equal(1 - 5 + 4.7 + 8.1 + 12, total);
    assert.equal(5, count);
});

QUnit.test('creme.model.Array.map', function(assert) {
    var model = new creme.model.Array();
    var addidx = function(e, index) {
        return e + index;
    };

    assert.deepEqual([], model.map(addidx));

    model = new creme.model.Array([1, -5, 4.7, 8.1, 12]);

    assert.deepEqual([1, 1 - 5, 2 + 4.7, 3 + 8.1, 4 + 12], model.map(addidx));
});

QUnit.test('creme.model.Array.indexOf', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c', 'd', 12]);

    assert.equal(undefined, model.comparator());

    assert.equal(0, model.indexOf('a'));
    assert.equal(1, model.indexOf('b'));
    assert.equal(2, model.indexOf('c'));
    assert.equal(3, model.indexOf('d'));
    assert.equal(4, model.indexOf(12));

    assert.equal(-1, model.indexOf('unknown'));
    assert.equal(-1, model.indexOf(1154));
});

QUnit.test('creme.model.Array.indexOf (comparator)', function(assert) {
    var comparator = function(a, b) {
        if (Array.isArray(b) === false) { return a[0] - b; }

        if (a[0] !== b[0]) { return a[0] - b[0]; }

        return a[1] < b[1] ? -1 : (a[1] > b[1] ? 1 : 0);
    };

    var model = new creme.model.Array([[1, 'a'], [1, 'b'], [2, 'c'], [8, 'd'], [12, 12]], comparator);

    assert.equal(0, comparator([1, 'a'], 1));
    assert.equal(-2, comparator([1, 'a'], 3));
    assert.equal(3, comparator([3, 'a'], 0));

    assert.equal(0, comparator([1, 'a'], [1, 'a']));
    assert.equal(-1, comparator([1, 'a'], [1, 'b']));
    assert.equal(1, comparator([1, 'c'], [1, 'a']));
    assert.equal(-1, comparator([1, 'a'], [1, 'c']));

    assert.equal(-5, comparator([3, 'a'], [8, 'b']));
    assert.equal(5, comparator([8, 'b'], [3, 'a']));

    assert.equal(comparator, model.comparator());
    assert.equal(-1, model.indexOf('a'));

    assert.equal(0, model.indexOf(1));
    assert.equal(0, model.indexOf([1, 'a']));
    assert.equal(1, model.indexOf([1, 'b']));

    assert.equal(-1, model.indexOf('d'));
    assert.equal(3, model.indexOf(8));
    assert.equal(3, model.indexOf([8, 'd']));
    assert.equal(-1, model.indexOf([8, 'h']));

    assert.equal(-1, model.indexOf('unknown'));
    assert.equal(-1, model.indexOf(1154));
});

QUnit.test('creme.model.Array.indicesOf', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c', 'd', 12]);

    assert.equal(undefined, model.comparator());

    assert.deepEqual([0], model.indicesOf('a'));
    assert.deepEqual([1], model.indicesOf('b'));
    assert.deepEqual([2], model.indicesOf('c'));
    assert.deepEqual([3], model.indicesOf('d'));
    assert.deepEqual([4], model.indicesOf(12));

    assert.deepEqual([0, 1], model.indicesOf(['a', 'b']));
    assert.deepEqual([2, 3, 4], model.indicesOf(['c', 'd', 12]));
    assert.deepEqual([0, 3], model.indicesOf(['a', 'd']));
    assert.deepEqual([0, 4], model.indicesOf(['a', 'unknown', 1154, 12]));

    assert.deepEqual([], model.indicesOf([]));
    assert.deepEqual([], model.indicesOf('unknown'));
    assert.deepEqual([], model.indicesOf(1154));
    assert.deepEqual([], model.indicesOf(['unknown', 1154]));
});

QUnit.test('creme.model.Array.indicesOf (comparator)', function(assert) {
    var comparator = function(a, b) {
        if (Array.isArray(b) === false) { return a[0] - b; }

        if (a[0] !== b[0]) { return a[0] - b[0]; }

        return a[1] < b[1] ? -1 : (a[1] > b[1] ? 1 : 0);
    };

    var model = new creme.model.Array([[1, 'a'], [1, 'b'], [2, 'c'], [8, 'd'], [12, 12]], comparator);

    assert.equal(0, comparator([1, 'a'], 1));
    assert.equal(-2, comparator([1, 'a'], 3));
    assert.equal(3, comparator([3, 'a'], 0));

    assert.equal(0, comparator([1, 'a'], [1, 'a']));
    assert.equal(-1, comparator([1, 'a'], [1, 'b']));
    assert.equal(1, comparator([1, 'c'], [1, 'a']));
    assert.equal(-1, comparator([1, 'a'], [1, 'c']));

    assert.equal(-5, comparator([3, 'a'], [8, 'b']));
    assert.equal(5, comparator([8, 'b'], [3, 'a']));

    assert.equal(comparator, model.comparator());
    assert.deepEqual([], model.indicesOf('a'));

    assert.deepEqual([0, 1], model.indicesOf(1));
    assert.deepEqual([2], model.indicesOf(2));

    assert.deepEqual([0], model.indicesOf([[1, 'a']]));
    assert.deepEqual([1], model.indicesOf([[1, 'b']]));

    assert.deepEqual([], model.indicesOf('d'));
    assert.deepEqual([3], model.indicesOf(8));
    assert.deepEqual([3], model.indicesOf([[8, 'd']]));
    assert.deepEqual([], model.indicesOf([[8, 'h']]));

    assert.deepEqual([0, 1], model.indicesOf([[1, 'a'], [1, 'b']]));
    assert.deepEqual([2, 3, 4], model.indicesOf([[2, 'c'], [8, 'd'], [12, 12]]));
    assert.deepEqual([0, 3], model.indicesOf([[1, 'a'], [8, 'd']]));
    assert.deepEqual([0, 4], model.indicesOf([[1, 'a'], 'unknown', 1154, [12, 12]]));

    assert.deepEqual([], model.indicesOf([]));
    assert.deepEqual([], model.indicesOf('unknown'));
    assert.deepEqual([], model.indicesOf(1154));
    assert.deepEqual([], model.indicesOf(['unknown', 1154]));
});
QUnit.test('creme.model.Array.pop (empty)', function(assert) {
    var model = new creme.model.Array();
    model.bind('remove', this.mockListener('removed'));
    assert.deepEqual([], this.mockListenerCalls('removed'));

    assert.equal(undefined, model.pop());

    assert.deepEqual([], model.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.pop', function(assert) {
    var model = new creme.model.Array(['a', 'b']);
    model.bind('remove', this.mockListener('removed'));
    assert.deepEqual([], this.mockListenerCalls('removed'));

    assert.equal('b', model.pop());
    assert.equal('a', model.pop());

    assert.deepEqual([], model.all());
    assert.deepEqual([
               ['remove', ['b'], 1, 1, 'remove'],
               ['remove', ['a'], 0, 0, 'remove']
              ], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.remove', function(assert) {
    var model = new creme.model.Array(['a', 'b']);
    model.bind('remove', this.mockListener('removed'));
    assert.deepEqual([], this.mockListenerCalls('removed'));

    assert.deepEqual([], model.remove(undefined));
    assert.deepEqual([], model.remove('c'));

    assert.deepEqual([], this.mockListenerCalls('removed'));

    assert.deepEqual(['a'], model.remove('a'));
    assert.deepEqual(['b'], model.remove('b'));

    assert.deepEqual([
               ['remove', ['a'], 0, 0, 'remove'],
               ['remove', ['b'], 0, 0, 'remove']
              ], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.remove (array)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c', 'd']);
    model.bind('remove', this.mockListener('removed'));
    assert.deepEqual([], this.mockListenerCalls('removed'));

    assert.deepEqual([], model.remove(undefined));
    assert.deepEqual([], model.remove('x'));

    assert.deepEqual([], this.mockListenerCalls('removed'));

    assert.deepEqual(['b', 'd'], model.remove(['b', 'd', 'x']));

    assert.deepEqual([
               ['remove', ['b'], 1, 1, 'remove'],
               ['remove', ['d'], 2, 2, 'remove']
              ], this.mockListenerCalls('removed'));
});

QUnit.test('creme.model.Array.removeAt', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c', 'd']);
    model.bind('remove', this.mockListener('removed'));
    assert.deepEqual([], this.mockListenerCalls('removed'));

    this.assertRaises(function() { model.removeAt(-1); }, Error, 'Error: index out of bound');
    this.assertRaises(function() { model.removeAt(10); }, Error, 'Error: index out of bound');

    assert.deepEqual([], this.mockListenerCalls('removed'));

    assert.deepEqual('d', model.removeAt(3));

    assert.deepEqual('a', model.removeAt(0));
    assert.deepEqual('b', model.removeAt(0));

    assert.deepEqual([
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

    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));

    model.reset(['a', 'b', 'c']);

    assert.deepEqual(['a', 'b', 'c'], model.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([
               ['add', ['a', 'b', 'c'], 0, 2, 'reset']
              ], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Array.reset (clear)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset();

    assert.deepEqual([], model.all());
    assert.deepEqual([
               ['remove', ['x', 'y', 'z'], 0, 2, 'reset']
              ], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Array.reset (update)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset(['a', 'b', 'c']);

    assert.deepEqual(['a', 'b', 'c'], model.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([
               ['update', ['a', 'b', 'c'], 0, 2, ['x', 'y', 'z'], 'reset']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Array.reset (add)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset(['a', 'b', 'c', 'e', 'f', 'g']);

    assert.deepEqual(['a', 'b', 'c', 'e', 'f', 'g'], model.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([
               ['add', ['e', 'f', 'g'], 3, 5, 'reset']
              ], this.mockListenerCalls('added'));
    assert.deepEqual([
               ['update', ['a', 'b', 'c'], 0, 2, ['x', 'y', 'z'], 'reset']
              ], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();

    model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset(['a', 'b', 'c', 'e']);

    assert.deepEqual(['a', 'b', 'c', 'e'], model.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([
               ['add', ['e'], 3, 3, 'reset']
              ], this.mockListenerCalls('added'));
    assert.deepEqual([
               ['update', ['a', 'b', 'c'], 0, 2, ['x', 'y', 'z'], 'reset']
              ], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();

    model = new creme.model.Array(['x']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset(['a', 'b', 'c']);

    assert.deepEqual(['a', 'b', 'c'], model.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([
               ['add', ['b', 'c'], 1, 2, 'reset']
              ], this.mockListenerCalls('added'));
    assert.deepEqual([
               ['update', ['a'], 0, 0, ['x'], 'reset']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Array.reset (remove)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset(['a']);

    assert.deepEqual(['a'], model.all());
    assert.deepEqual([
               ['remove', ['y', 'z'], 1, 2, 'reset']
              ], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([
               ['update', ['a'], 0, 0, ['x'], 'reset']
              ], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();

    model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('remove', this.mockListener('removed'));
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.reset(['a', 'b']);

    assert.deepEqual(['a', 'b'], model.all());
    assert.deepEqual([
               ['remove', ['z'], 2, 2, 'reset']
              ], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([
               ['update', ['a', 'b'], 0, 1, ['x', 'y'], 'reset']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Array.set (update)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));

    model.set('a', 1);

    assert.deepEqual(['x', 'a', 'z'], model.all());
    assert.deepEqual([
               ['update', ['a'], 1, 1, ['y'], 'set']
              ], this.mockListenerCalls('updated'));
    assert.deepEqual([], this.mockListenerCalls('added'));
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

    assert.deepEqual(['x', 'y', 'z'], model.all());
    assert.deepEqual([], this.mockListenerCalls('updated'));
    assert.deepEqual([], this.mockListenerCalls('added'));
});

QUnit.test('creme.model.Array.patch (array)', function(assert) {
    var model = new creme.model.Array();
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    assert.deepEqual([], this.mockListenerCalls('model'));
    assert.deepEqual([], model.all());

    model.patch(['a', 'b', 'c']);

    assert.deepEqual(['a', 'b', 'c'], model.all());
    assert.deepEqual([['add', ['a', 'b', 'c'], 0, 2, 'reset'], ['reset']], this.mockListenerCalls('model'));

    this.resetMockListenerCalls();
    model.patch(['x', 'y', 'z', 'w']);

    assert.deepEqual(['x', 'y', 'z', 'w'], model.all());
    assert.deepEqual([['update', ['x', 'y', 'z'], 0, 2, ['a', 'b', 'c'], 'reset'],
               ['add', ['w'], 3, 3, 'reset'],
               ['reset']], this.mockListenerCalls('model'));
});

QUnit.test('creme.model.Array.patch (diff, add)', function(assert) {
    var model = new creme.model.Array();
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    assert.deepEqual([], this.mockListenerCalls('model'));
    assert.deepEqual([], model.all());

    model.patch({add: ['x', 'y']});

    assert.deepEqual(['x', 'y'], model.all());
    assert.deepEqual([['add', ['x', 'y'], 0, 1, 'insert']], this.mockListenerCalls('model'));
});

QUnit.test('creme.model.Array.patch (diff, remove)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    assert.deepEqual([], this.mockListenerCalls('model'));
    assert.deepEqual(['a', 'b', 'c'], model.all());

    model.patch({remove: ['b', 'c']});

    assert.deepEqual(['a'], model.all());
    assert.deepEqual([['remove', ['b'], 1, 1, 'remove'],
               ['remove', ['c'], 1, 1, 'remove']], this.mockListenerCalls('model'));
});

QUnit.test('creme.model.Array.patch (diff, update)', function(assert) {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    assert.deepEqual([], this.mockListenerCalls('model'));
    assert.deepEqual(['a', 'b', 'c'], model.all());

    model.patch({update: [['y', 0], ['k', 2]]});

    assert.deepEqual(['y', 'b', 'k'], model.all());
    assert.deepEqual([['update', ['y'], 0, 0, ['a'], 'set'],
               ['update', ['k'], 2, 2, ['c'], 'set']], this.mockListenerCalls('model'));
});

QUnit.test('creme.model.Array.reverse', function(assert) {
    var model = new creme.model.Array([1, 4, 5, 3, 7, 0]);
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));
    model.bind('reverse', this.mockListener('reversed'));

    model.reverse();

    assert.deepEqual([0, 7, 3, 5, 4, 1], model.all());
    assert.deepEqual([
               ['update', [0, 7, 3, 5, 4, 1], 0, 5, [1, 4, 5, 3, 7, 0], 'reverse']
              ], this.mockListenerCalls('updated'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([['reverse']], this.mockListenerCalls('reversed'));
});

QUnit.test('creme.model.Array.sort', function(assert) {
    var model = new creme.model.Array([1, 4, 5, 3, 7, 0]);
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));
    model.bind('sort', this.mockListener('sorted'));

    model.sort();

    assert.deepEqual([0, 1, 3, 4, 5, 7], model.all());
    assert.deepEqual([
               ['update', [0, 1, 3, 4, 5, 7], 0, 5, [1, 4, 5, 3, 7, 0], 'sort']
              ], this.mockListenerCalls('updated'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([['sort']], this.mockListenerCalls('sorted'));

    this.resetMockListenerCalls();
    model.sort();

    assert.deepEqual([0, 1, 3, 4, 5, 7], model.all());
    assert.deepEqual([
               ['update', [0, 1, 3, 4, 5, 7], 0, 5, [0, 1, 3, 4, 5, 7], 'sort']
              ], this.mockListenerCalls('updated'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([['sort']], this.mockListenerCalls('sorted'));
});

QUnit.test('creme.model.Array.sort (comparator)', function(assert) {
    var desc = function(a, b) { return b - a; };
    var asc = function(a, b) { return a - b; };

    var model = new creme.model.Array([1, 4, 5, 3, 7, 0]);
    model.bind('add', this.mockListener('added'));
    model.bind('update', this.mockListener('updated'));
    model.bind('sort', this.mockListener('sorted'));

    model.sort();

    assert.deepEqual([0, 1, 3, 4, 5, 7], model.all());
    assert.deepEqual([
               ['update', [0, 1, 3, 4, 5, 7], 0, 5, [1, 4, 5, 3, 7, 0], 'sort']
              ], this.mockListenerCalls('updated'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([['sort']], this.mockListenerCalls('sorted'));

    this.resetMockListenerCalls();
    model.sort(desc);

    assert.deepEqual([7, 5, 4, 3, 1, 0], model.all());
    assert.deepEqual([
               ['update', [7, 5, 4, 3, 1, 0], 0, 5, [0, 1, 3, 4, 5, 7], 'sort']
              ], this.mockListenerCalls('updated'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([['sort']], this.mockListenerCalls('sorted'));

    model.reset([1, 4, 5, 3, 7, 0]);
    this.resetMockListenerCalls();

    model.comparator(desc).sort();

    assert.deepEqual([7, 5, 4, 3, 1, 0], model.all());
    assert.deepEqual([
               ['update', [7, 5, 4, 3, 1, 0], 0, 5, [1, 4, 5, 3, 7, 0], 'sort']
              ], this.mockListenerCalls('updated'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([['sort']], this.mockListenerCalls('sorted'));

    model.reset([1, 4, 5, 3, 7, 0]);
    this.resetMockListenerCalls();

    model.comparator(desc).sort(asc);

    assert.deepEqual([0, 1, 3, 4, 5, 7], model.all());
    assert.deepEqual([
               ['update', [0, 1, 3, 4, 5, 7], 0, 5, [1, 4, 5, 3, 7, 0], 'sort']
              ], this.mockListenerCalls('updated'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([['sort']], this.mockListenerCalls('sorted'));
});

QUnit.test('creme.model.Delegate.constructor (empty)', function(assert) {
    var delegate = new creme.model.Delegate();

    assert.equal(undefined, delegate.delegate());
    assert.equal(0, delegate.length());
    assert.deepEqual([], delegate.all());
});

QUnit.test('creme.model.Delegate.constructor (model)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    var delegate = new creme.model.Delegate(model);

    assert.equal(model, delegate.delegate());
    assert.equal(3, delegate.length());
    assert.deepEqual(['x', 'y', 'z'], delegate.all());
});

QUnit.test('creme.model.Delegate (update)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    var delegate = new creme.model.Delegate(model);
    delegate.bind('remove', this.mockListener('removed'));
    delegate.bind('add', this.mockListener('added'));
    delegate.bind('update', this.mockListener('updated'));

    assert.deepEqual(['x', 'y', 'z'], delegate.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));

    model.set('a', 1);

    assert.deepEqual(['x', 'a', 'z'], delegate.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([
               ['update', ['a'], 1, 1, ['y'], 'set']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Delegate (add)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    var delegate = new creme.model.Delegate(model);
    delegate.bind('remove', this.mockListener('removed'));
    delegate.bind('add', this.mockListener('added'));
    delegate.bind('update', this.mockListener('updated'));

    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));

    model.append(['a', 'b']);

    assert.deepEqual(['x', 'y', 'z', 'a', 'b'], delegate.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([
               ['add', ['a', 'b'], 3, 4, 'insert']
              ], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Delegate (remove)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    var delegate = new creme.model.Delegate(model);
    delegate.bind('remove', this.mockListener('removed'));
    delegate.bind('add', this.mockListener('added'));
    delegate.bind('update', this.mockListener('updated'));

    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));

    model.removeAt(1);

    assert.deepEqual(['x', 'z'], delegate.all());
    assert.deepEqual([
               ['remove', ['y'], 1, 1, 'remove']
              ], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();
    model.removeAt(0);

    assert.deepEqual(['z'], delegate.all());
    assert.deepEqual([
               ['remove', ['x'], 0, 0, 'remove']
              ], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Delegate (replace delegate)', function(assert) {
    var model = new creme.model.Array(['x', 'y', 'z']);
    var modelB = new creme.model.Array(['a', 'b', 'c']);

    var delegate = new creme.model.Delegate(model);
    delegate.bind('remove', this.mockListener('removed'));
    delegate.bind('add', this.mockListener('added'));
    delegate.bind('update', this.mockListener('updated'));

    assert.equal(model, delegate.delegate());

    delegate.delegate(model);
    assert.equal(model, delegate.delegate());
    assert.deepEqual(['x', 'y', 'z'], delegate.all());

    model.append(12);
    modelB.append(13);

    assert.deepEqual(['x', 'y', 'z', 12], delegate.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([
               ['add', [12], 3, 3, 'insert']
              ], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();

    // replace delegate model by modelB
    delegate.delegate(modelB);
    assert.equal(modelB, delegate.delegate());

    model.append(14);
    modelB.append(15);

    assert.deepEqual(['a', 'b', 'c', 13, 15], delegate.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([
               ['add', [15], 4, 4, 'insert']
              ], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();

    // remove delegate model
    delegate.delegate(null);
    assert.equal(null, delegate.delegate());

    model.append(16);
    modelB.append(17);

    assert.deepEqual([], delegate.all());
    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Filter (update)', function(assert) {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var pairs = new creme.model.Filter(model, function(item) { return (item % 2) === 0; });
    pairs.bind('remove', this.mockListener('removed'));
    pairs.bind('add', this.mockListener('added'));
    pairs.bind('update', this.mockListener('updated'));

    assert.deepEqual([1, 2, 3, 4, 5], model.all());
    assert.deepEqual([2, 4], pairs.all());

    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([], this.mockListenerCalls('updated'));

    model.set(16, 2);

    assert.deepEqual([1, 2, 16, 4, 5], model.all(), 'set(16, 2)');
    assert.deepEqual([2, 16, 4], pairs.all());

    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([
               ['add', [4], 2, 2, 'reset']
              ], this.mockListenerCalls('added'));
    assert.deepEqual([
               ['update', [2, 16], 0, 1, [2, 4], 'reset']
              ], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();
    model.set(15, 2);

    assert.deepEqual([1, 2, 15, 4, 5], model.all());
    assert.deepEqual([2, 4], pairs.all());

    assert.deepEqual([
               ['remove', [4], 2, 2, 'reset']
              ], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([
               ['update', [2, 4], 0, 1, [2, 16], 'reset']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Filter (add)', function(assert) {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var pairs = new creme.model.Filter(model, function(item) { return (item % 2) === 0; });
    pairs.bind('remove', this.mockListener('removed'));
    pairs.bind('add', this.mockListener('added'));
    pairs.bind('update', this.mockListener('updated'));

    assert.deepEqual([1, 2, 3, 4, 5], model.all());
    assert.deepEqual([2, 4], pairs.all());

    model.append([16, 18, 7, 9]);

    assert.deepEqual([1, 2, 3, 4, 5, 16, 18, 7, 9], model.all());
    assert.deepEqual([2, 4, 16, 18], pairs.all());

    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([
               ['add', [16, 18], 2, 3, 'reset']
              ], this.mockListenerCalls('added'));
    assert.deepEqual([
               ['update', [2, 4], 0, 1, [2, 4], 'reset']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Filter (remove)', function(assert) {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var pairs = new creme.model.Filter(model, function(item) { return (item % 2) === 0; });
    pairs.bind('remove', this.mockListener('removed'));
    pairs.bind('add', this.mockListener('added'));
    pairs.bind('update', this.mockListener('updated'));

    assert.deepEqual([1, 2, 3, 4, 5], model.all());
    assert.deepEqual([2, 4], pairs.all());

    model.removeAt(2);

    assert.deepEqual([1, 2, 4, 5], model.all());
    assert.deepEqual([2, 4], pairs.all());

    assert.deepEqual([], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([
               ['update', [2, 4], 0, 1, [2, 4], 'reset']
              ], this.mockListenerCalls('updated'));

    this.resetMockListenerCalls();

    model.removeAt(2);

    assert.deepEqual([1, 2, 5], model.all());
    assert.deepEqual([2], pairs.all());

    assert.deepEqual([
               ['remove', [4], 1, 1, 'reset']
              ], this.mockListenerCalls('removed'));
    assert.deepEqual([], this.mockListenerCalls('added'));
    assert.deepEqual([
               ['update', [2], 0, 0, [2], 'reset']
              ], this.mockListenerCalls('updated'));
});

QUnit.test('creme.model.Filter (no filter)', function(assert) {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var nofilter = new creme.model.Filter(model, null);
    nofilter.bind('remove', this.mockListener('removed'));
    nofilter.bind('add', this.mockListener('added'));
    nofilter.bind('update', this.mockListener('updated'));

    assert.deepEqual([1, 2, 3, 4, 5], model.all());
    assert.deepEqual([1, 2, 3, 4, 5], nofilter.all());

    model.removeAt(2);

    assert.deepEqual([1, 2, 4, 5], model.all());
    assert.deepEqual([1, 2, 4, 5], nofilter.all());

    model.append([16, 18]);

    assert.deepEqual([1, 2, 4, 5, 16, 18], model.all());
    assert.deepEqual([1, 2, 4, 5, 16, 18], nofilter.all());

    nofilter.filter(function(item) { return (item % 2) === 0; });

    assert.deepEqual([1, 2, 4, 5, 16, 18], model.all());
    assert.deepEqual([2, 4, 16, 18], nofilter.all());

    nofilter.filter(null);

    assert.deepEqual([1, 2, 4, 5, 16, 18], model.all());
    assert.deepEqual([1, 2, 4, 5, 16, 18], nofilter.all());
});

QUnit.test('creme.model.Filter (lambda filter)', function(assert) {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var lambda = new creme.utils.Lambda('(item % (this.divide || 1) === 0)', 'item');
    var filter = new creme.model.Filter(model, lambda);
    filter.bind('remove', this.mockListener('removed'));
    filter.bind('add', this.mockListener('added'));
    filter.bind('update', this.mockListener('updated'));

    assert.deepEqual([1, 2, 3, 4, 5], model.all());
    assert.deepEqual([1, 2, 3, 4, 5], filter.all());

    model.removeAt(2);

    assert.deepEqual([1, 2, 4, 5], model.all());
    assert.deepEqual([1, 2, 4, 5], filter.all());

    model.append([16, 18]);

    assert.deepEqual([1, 2, 4, 5, 16, 18], model.all());
    assert.deepEqual([1, 2, 4, 5, 16, 18], filter.all());

    filter.filter(lambda.bind({divide: 2}));
    assert.deepEqual({divide: 2}, lambda._context);
    assert.equal(false, lambda.invoke(1), '1 is odd');
    assert.equal(true, lambda.invoke(2), '2 is even');

    assert.deepEqual([1, 2, 4, 5, 16, 18], model.all());
    assert.deepEqual([2, 4, 16, 18], filter.all(), 'filtered (%2)');

    filter.filter(lambda.bind({divide: 3}));
    assert.equal(false, lambda.invoke(1));
    assert.equal(false, lambda.invoke(2));
    assert.equal(true, lambda.invoke(3));

    assert.deepEqual([1, 2, 4, 5, 16, 18], model.all());
    assert.deepEqual([18], filter.all(), 'filtered (%3)');

    filter.filter(lambda.bind({divide: 4}));
    assert.deepEqual([1, 2, 4, 5, 16, 18], model.all());
    assert.deepEqual([4, 16], filter.all(), 'filtered (%4)');
});

QUnit.test('creme.model.Filter (string filter)', function(assert) {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var filter = new creme.model.Filter(model, '(item % 2 === 0)');
    filter.bind('remove', this.mockListener('removed'));
    filter.bind('add', this.mockListener('added'));
    filter.bind('update', this.mockListener('updated'));

    assert.deepEqual([1, 2, 3, 4, 5], model.all());
    assert.deepEqual([2, 4], filter.all());

    model.removeAt(2);

    assert.deepEqual([1, 2, 4, 5], model.all());
    assert.deepEqual([2, 4], filter.all());

    model.append([16, 18]);

    assert.deepEqual([1, 2, 4, 5, 16, 18], model.all());
    assert.deepEqual([2, 4, 16, 18], filter.all());
});

}(jQuery));
