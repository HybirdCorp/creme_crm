module("creme.model.collection.js", {
    setup: function() {
        this.resetMockCalls();
    },

    teardown: function() {
    },

    resetMockCalls: function() {
        this._eventListenerCalls = {};
    },

    mockListenerCalls: function(name)
    {
        if (this._eventListenerCalls[name] === undefined)
            this._eventListenerCalls[name] = [];

        return this._eventListenerCalls[name];
    },

    mockListener: function(name)
    {
        var self = this;
        return (function(name) {return function() {
            self.mockListenerCalls(name).push(Array.copy(arguments));
        }})(name);
    }
});

function assertRaises(block, expected, message)
{
    raises(block,
           function(error) {
                ok(error instanceof expected, 'error is ' + expected);
                equal(message, '' + error);
                return true;
           });
}

test('creme.model.Array.constructor', function() {
    var model = new creme.model.Array();

    equal(0, model.length());
    deepEqual([], model.all());

    model = new creme.model.Array(['a', 'b', 'c']);

    equal(3, model.length());
    deepEqual(['a', 'b', 'c'], model.all());
});

test('creme.model.Array.get', function() {
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

test('creme.model.Array.first/last', function() {
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

test('creme.model.Array.clear (empty)', function() {
    var model = new creme.model.Array();
    deepEqual([], this.mockListenerCalls('removed'));

    model.clear();

    deepEqual([], this.mockListenerCalls('removed'));
});

test('creme.model.Array.clear', function() {
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

test('creme.model.Array.insert (empty)', function() {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert('a');
    deepEqual(['a'], model.all());

    deepEqual([
               ['add', ['a'], 0, 0, 'insert']
              ], this.mockListenerCalls('added'));
});

test('creme.model.Array.insert (empty, array)', function() {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert(['a', 'c', 'h']);
    deepEqual(['a', 'c', 'h'], model.all());

    deepEqual([
               ['add', ['a', 'c', 'h'], 0, 2, 'insert']
              ], this.mockListenerCalls('added'));
});

test('creme.model.Array.insert (front)', function() {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert('d');
    deepEqual(['d', 'a', 'b', 'c'], model.all());

    deepEqual([
               ['add', ['d'], 0, 0, 'insert']
              ], this.mockListenerCalls('added'));
});

test('creme.model.Array.insert (front, array)', function() {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert(['d', 'e', 'f']);
    deepEqual(['d', 'e', 'f', 'a', 'b', 'c'], model.all());

    deepEqual([
               ['add', ['d', 'e', 'f'], 0, 2, 'insert']
              ], this.mockListenerCalls('added'));
});

test('creme.model.Array.insert (back)', function() {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert('d', model.length());
    deepEqual(['a', 'b', 'c', 'd'], model.all());

    deepEqual([
               ['add', ['d'], 3, 3, 'insert']
              ], this.mockListenerCalls('added'));
});

test('creme.model.Array.insert (back, array)', function() {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert(['d', 'e', 'f'], model.length());
    deepEqual(['a', 'b', 'c', 'd', 'e', 'f'], model.all());

    deepEqual([
               ['add', ['d', 'e', 'f'], 3, 5, 'insert']
              ], this.mockListenerCalls('added'));
});

test('creme.model.Array.insert', function() {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert('d', 1);

    deepEqual(['a', 'd', 'b', 'c'], model.all());

    deepEqual([
               ['add', ['d'], 1, 1, 'insert']
              ], this.mockListenerCalls('added'));
});

test('creme.model.Array.insert (array)', function() {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    model.insert(['d', 'e', 'f'], 1);

    deepEqual(['a', 'd', 'e', 'f', 'b', 'c'], model.all());

    deepEqual([
               ['add', ['d', 'e', 'f'], 1, 3, 'insert']
              ], this.mockListenerCalls('added'));
});

test('creme.model.Array.insert (out of bound)', function() {
    var model = new creme.model.Array();
    model.bind('add', this.mockListener('added'));
    deepEqual([], this.mockListenerCalls('added'));

    assertRaises(function() {model.insert('a', 10);}, Error, 'Error: index out of bound');
    assertRaises(function() {model.insert('b', -1);}, Error, 'Error: index out of bound');

    deepEqual([], this.mockListenerCalls('added'));
});

test('creme.model.Array.append', function() {
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

test('creme.model.Array.prepend', function() {
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

test('creme.model.Array.indexOf', function() {
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

test('creme.model.Array.indexOf (comparator)', function() {
    var comparator = function(a, b) {
        if (Array.isArray(b) === false)
            return a[0] - b;

        if (a[0] !== b[0])
            return a[0] - b[0];

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

test('creme.model.Array.pop (empty)', function() {
    var model = new creme.model.Array();
    model.bind('remove', this.mockListener('removed'));
    deepEqual([], this.mockListenerCalls('removed'));

    equal(undefined, model.pop());

    deepEqual([], model.all());
    deepEqual([], this.mockListenerCalls('removed'));
});

test('creme.model.Array.pop', function() {
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

test('creme.model.Array.remove', function() {
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

test('creme.model.Array.remove (array)', function() {
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

test('creme.model.Array.removeAt', function() {
    var model = new creme.model.Array(['a', 'b', 'c', 'd']);
    model.bind('remove', this.mockListener('removed'));
    deepEqual([], this.mockListenerCalls('removed'));

    assertRaises(function() {model.removeAt(-1);}, Error, 'Error: index out of bound');
    assertRaises(function() {model.removeAt(10);}, Error, 'Error: index out of bound');

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

test('creme.model.Array.reset (empty)', function() {
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

test('creme.model.Array.reset (clear)', function() {
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

test('creme.model.Array.reset (update)', function() {
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

test('creme.model.Array.reset (add)', function() {
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

    this.resetMockCalls();

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

    this.resetMockCalls();

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

test('creme.model.Array.reset (remove)', function() {
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

    this.resetMockCalls();

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

test('creme.model.Array.set (update)', function() {
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


test('creme.model.Array.patch (array)', function() {
    var model = new creme.model.Array();
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    deepEqual([], this.mockListenerCalls('model'));
    deepEqual([], model.all());

    model.patch(['a', 'b', 'c']);

    deepEqual(['a', 'b', 'c'], model.all());
    deepEqual([['add', ['a', 'b', 'c'], 0, 2, 'reset'], ['reset']], this.mockListenerCalls('model'));

    this.resetMockCalls();
    model.patch(['x', 'y', 'z', 'w']);

    deepEqual(['x', 'y', 'z', 'w'], model.all());
    deepEqual([['update', ['x', 'y', 'z'], 0, 2, ['a', 'b', 'c'], 'reset'],
               ['add', ['w'], 3, 3, 'reset'],
               ['reset']], this.mockListenerCalls('model'));
});

test('creme.model.Array.patch (diff, add)', function() {
    var model = new creme.model.AjaxArray(this.backend);
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    deepEqual([], this.mockListenerCalls('model'));
    deepEqual([], model.all());

    model.patch({add:['x', 'y']});

    deepEqual(['x', 'y'], model.all());
    deepEqual([['add', ['x', 'y'], 0, 1, 'insert']], this.mockListenerCalls('model'));
});

test('creme.model.Array.patch (diff, remove)', function() {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    deepEqual([], this.mockListenerCalls('model'));
    deepEqual(['a', 'b', 'c'], model.all());

    model.patch({remove:['b', 'c']});

    deepEqual(['a'], model.all());
    deepEqual([['remove', ['b'], 1, 1, 'remove'],
               ['remove', ['c'], 1, 1, 'remove']], this.mockListenerCalls('model'));
});

test('creme.model.Array.patch (diff, update)', function() {
    var model = new creme.model.Array(['a', 'b', 'c']);
    model.bind(['add', 'remove', 'update', 'reset'], this.mockListener('model'));

    deepEqual([], this.mockListenerCalls('model'));
    deepEqual(['a', 'b', 'c'], model.all());

    model.patch({update:[['y', 0], ['k', 2]]});

    deepEqual(['y', 'b', 'k'], model.all());
    deepEqual([['update', ['y'], 0, 0, ['a'], 'set'],
               ['update', ['k'], 2, 2, ['c'], 'set']], this.mockListenerCalls('model'));
});

test('creme.model.Array.reverse', function() {
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

test('creme.model.Array.sort', function() {
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

    this.resetMockCalls();
    model.sort();

    deepEqual([0, 1, 3, 4, 5, 7], model.all());
    deepEqual([
               ['update', [0, 1, 3, 4, 5, 7], 0, 5, [0, 1, 3, 4, 5, 7], 'sort']
              ], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['sort']], this.mockListenerCalls('sorted'));
});

test('creme.model.Array.sort (comparator)', function() {
    var desc = function(a, b) {return b - a;};
    var asc = function(a, b) {return a - b;};

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

    this.resetMockCalls();
    model.sort(desc);

    deepEqual([7, 5, 4, 3, 1, 0], model.all());
    deepEqual([
               ['update', [7, 5, 4, 3, 1, 0], 0, 5, [0, 1, 3, 4, 5, 7], 'sort']
              ], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['sort']], this.mockListenerCalls('sorted'));

    model.reset([1, 4, 5, 3, 7, 0]);
    this.resetMockCalls();

    model.comparator(desc).sort();

    deepEqual([7, 5, 4, 3, 1, 0], model.all());
    deepEqual([
               ['update', [7, 5, 4, 3, 1, 0], 0, 5, [1, 4, 5, 3, 7, 0], 'sort']
              ], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['sort']], this.mockListenerCalls('sorted'));

    model.reset([1, 4, 5, 3, 7, 0]);
    this.resetMockCalls();

    model.comparator(desc).sort(asc);

    deepEqual([0, 1, 3, 4, 5, 7], model.all());
    deepEqual([
               ['update', [0, 1, 3, 4, 5, 7], 0, 5, [1, 4, 5, 3, 7, 0], 'sort']
              ], this.mockListenerCalls('updated'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([['sort']], this.mockListenerCalls('sorted'));
});

test('creme.model.Delegate.constructor (empty)', function() {
    var delegate = new creme.model.Delegate();

    equal(undefined, delegate.delegate());
    equal(0, delegate.length());
    deepEqual([], delegate.all());
});

test('creme.model.Delegate.constructor (model)', function() {
    var model = new creme.model.Array(['x', 'y', 'z']);
    var delegate = new creme.model.Delegate(model);

    equal(model, delegate.delegate());
    equal(3, delegate.length());
    deepEqual(['x', 'y', 'z'], delegate.all());
});

test('creme.model.Delegate (update)', function() {
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

test('creme.model.Delegate (add)', function() {
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

test('creme.model.Delegate (remove)', function() {
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

    this.resetMockCalls();
    model.removeAt(0);

    deepEqual(['z'], delegate.all());
    deepEqual([
               ['remove', ['x'], 0, 0, 'remove']
              ], this.mockListenerCalls('removed'));
    deepEqual([], this.mockListenerCalls('added'));
    deepEqual([], this.mockListenerCalls('updated'));
});

test('creme.model.Filter (update)', function() {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var pairs = new creme.model.Filter(model, function(item) {return (item % 2) === 0;});
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

    this.resetMockCalls();
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

test('creme.model.Filter (add)', function() {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var pairs = new creme.model.Filter(model, function(item) {return (item % 2) === 0;});
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

test('creme.model.Filter (remove)', function() {
    var model = new creme.model.Array([1, 2, 3, 4, 5]);
    var pairs = new creme.model.Filter(model, function(item) {return (item % 2) === 0;});
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
    
    this.resetMockCalls();

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

test('creme.model.Filter (no filter)', function() {
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

    nofilter.filter(function(item) {return (item % 2) === 0;});

    deepEqual([1, 2, 4, 5, 16, 18], model.all());
    deepEqual([2, 4, 16, 18], nofilter.all());
    
    nofilter.filter(null);

    deepEqual([1, 2, 4, 5, 16, 18], model.all());
    deepEqual([1, 2, 4, 5, 16, 18], nofilter.all());
});

test('creme.model.Filter (lambda filter)', function() {
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
    equal(false, lambda.invoke(1));
    equal(true, lambda.invoke(2));

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
