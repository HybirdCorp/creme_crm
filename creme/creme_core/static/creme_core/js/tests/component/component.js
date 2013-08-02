module("creme.component.js", {
    setup: function() {
    },

    teardown: function() {
    }
});

MockComponentA = creme.component.Component.sub({
   _init_: function(a) {
       this._a = a || 0;
   },

   get: function() {
       return this._a;
   },

   add: function(value) {
       return this._a + (value || 0);
   }
});

MockComponentAB = MockComponentA.sub({
   _init_: function(a, b) {
       MockComponentAB.__super__._init_.apply(this, arguments);
       this._b = b || 0;;
   },

   get: function() {
       return [this._super_(MockComponentA).get(), this._b];
   },

   add: function(value) {
       return this._b * this._super_(MockComponentA).add(value);
   }
});

MockComponentAC = MockComponentA.sub({
    _init_: function(a, c) {
        MockComponentAB.__super__._init_.apply(this, arguments);
        this._c = c || 0;;
    },

    get: function() {
        return [this._super_(MockComponentA).get(), this._c];
    },

    add: function(value) {
        return this._c + this._super_(MockComponentA).add(value);
    }
 });

MockCollection = creme.component.Component.sub({
    _init_: function() {
        this._data = {};
    },

    get: function(key) {
        return this._data[key];
    },

    set: function(key, data) {
        this._data[key] = data;
    },

    clear: function() {
        this._data = {};
    },

    size: function() {
        return Object.keys(this._data).length;
    }
});

MockCollectionA = MockCollection.sub({
    set: function(key, data) {
        this._super_(MockCollection).set('A_' + key, data);
    }
});

MockCollectionB = MockCollection.sub({
    set: function(key, data) {
        this._super_(MockCollection).set('B_' + key, data);
    }
});

MockCollectionBC = MockCollectionB.sub({
    set: function(key, data) {
        this._super_(MockCollectionB).set('C_' + key, data);
    }
});

test('creme.component (Component)', function() {
    var obj = new creme.component.Component();

    deepEqual(creme.component.Component.__super__, Object.prototype);

    equal(Object.isFunc(obj._init_), true);
    equal(Object.isFunc(creme.component.Component.sub), true);

    equal(obj.is(Object), true, 'is Object');
    equal(obj.is(creme.component.Component), true, 'is Component');
    equal(obj.is(MockComponentA), false);
    equal(obj.is(MockComponentAB), false);
});

test('creme.component (MockA)', function() {
    var a = new MockComponentA(12);

    deepEqual(MockComponentA.__super__, creme.component.Component.prototype);
    equal(a.get(), 12);
    equal(a.add(485), 12 + 485);
    equal(a.add(), 12);

    equal(Object.isFunc(MockComponentA.sub), true);

    equal(a.is(Object), true);
    equal(a.is(creme.component.Component), true);
    equal(a.is(MockComponentA), true, 'is MockComponentA');
    equal(a.is(MockComponentAB), false);
    equal(a.is(MockComponentAC), false);
});

test('creme.component (MockAB)', function() {
    var ab = new MockComponentAB(12, 8);

    deepEqual(MockComponentAB.__super__, MockComponentA.prototype);
    deepEqual(MockComponentAB.__super__.constructor.__super__, creme.component.Component.prototype);

    deepEqual(ab.get(), [12, 8]);
    equal(ab.add(485), 8 * (12 + 485));
    equal(ab.add(), 8 * 12);

    equal(Object.isFunc(MockComponentAB.sub), true);

    equal(ab.is(Object), true);
    equal(ab.is(creme.component.Component), true);
    equal(ab.is(MockComponentA), true);
    equal(ab.is(MockComponentAB), true);
    equal(ab.is(MockComponentAC), false);
});

test('creme.component (MockAC)', function() {
    var ac = new MockComponentAC(12, 8);

    deepEqual(MockComponentAC.__super__, MockComponentA.prototype);
    deepEqual(MockComponentAC.__super__.constructor.__super__, creme.component.Component.prototype);

    deepEqual(ac.get(), [12, 8]);
    equal(ac.add(485), 8 + (12 + 485));
    equal(ac.add(), 8 + 12);

    equal(Object.isFunc(MockComponentAC.sub), true);

    equal(ac.is(Object), true);
    equal(ac.is(creme.component.Component), true);
    equal(ac.is(MockComponentA), true);
    equal(ac.is(MockComponentAB), false);
    equal(ac.is(MockComponentAC), true);
});

/* This test checks that an inherited collection is not shared between subclasses */
test('creme.component (Collection)', function() {
    var collection = new MockCollection();
    var a = new MockCollectionA();
    var a2 = new MockCollectionA();
    var b = new MockCollectionB();
    var bc = new MockCollectionBC();

    deepEqual(MockCollection.__super__, creme.component.Component.prototype);

    deepEqual(MockCollectionA.__super__, MockCollection.prototype);
    deepEqual(MockCollectionA.__super__.constructor.__super__, creme.component.Component.prototype);

    deepEqual(MockCollectionB.__super__, MockCollection.prototype);
    deepEqual(MockCollectionB.__super__.constructor.__super__, creme.component.Component.prototype);

    deepEqual(MockCollectionBC.__super__, MockCollectionB.prototype);
    deepEqual(MockCollectionBC.__super__.constructor.__super__, MockCollection.prototype);
    deepEqual(MockCollectionBC.__super__.constructor.__super__.constructor.__super__, creme.component.Component.prototype);

    equal(collection.size(), 0);
    equal(a.size(), 0);
    equal(a2.size(), 0);
    equal(b.size(), 0);
    equal(bc.size(), 0);

    collection.set('a', 12);

    equal(collection.size(), 1);
    equal(a.size(), 0);
    equal(a2.size(), 0);
    equal(b.size(), 0);
    equal(bc.size(), 0);

    deepEqual(collection._data, {'a': 12});

    a.set('1', 134);
    a.set('2', 2);

    b.set('1', 445);
    bc.set('1', 875);

    equal(collection.size(), 1);
    equal(a.size(), 2);
    equal(a2.size(), 0);
    equal(b.size(), 1);
    equal(bc.size(), 1);

    deepEqual(collection._data, {'a': 12});
    deepEqual(a._data, {'A_1': 134, 'A_2': 2});
    deepEqual(b._data, {'B_1': 445});
    deepEqual(bc._data, {'B_C_1': 875});

    a.clear();

    equal(collection.size(), 1);
    equal(a.size(), 0);
    equal(a2.size(), 0);
    equal(b.size(), 1);
    equal(bc.size(), 1);

    deepEqual(collection._data, {'a': 12});
    deepEqual(b._data, {'B_1': 445});
    deepEqual(bc._data, {'B_C_1': 875});
});

test('creme.component._super', function() {
    var ab = new MockComponentAB(12, 8);

    deepEqual(ab.get(), [12, 8]);
    equal(ab.add(485), 8 * (12 + 485));
    equal(ab.add(), 8 * 12);

    equal(12, ab._super_(MockComponentA).get());
    equal(12 + 485, ab._super_(MockComponentA).add(485));
    equal(12, ab._super_(MockComponentA).add());

    equal(12, ab._super_(MockComponentA, 'get'));
    equal(12 + 485, ab._super_(MockComponentA, 'add', 485));
    equal(12, ab._super_(MockComponentA, 'add'));
});
