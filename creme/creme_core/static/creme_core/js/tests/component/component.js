(function($) {

var MockComponentA = creme.component.Component.sub({
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

var MockComponentAB = MockComponentA.sub({
   _init_: function(a, b) {
       MockComponentAB.__super__._init_.apply(this, arguments);
       this._b = b || 0;
   },

   get: function() {
       return [this._super_(MockComponentA).get(), this._b];
   },

   add: function(value) {
       return this._b * this._super_(MockComponentA).add(value);
   }
});

var MockComponentAC = MockComponentA.sub({
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

var MockCollection = creme.component.Component.sub({
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

var MockCollectionA = MockCollection.sub({
    set: function(key, data) {
        this._super_(MockCollection).set('A_' + key, data);
    }
});

var MockCollectionB = MockCollection.sub({
    set: function(key, data) {
        this._super_(MockCollection).set('B_' + key, data);
    }
});

var MockCollectionBC = MockCollectionB.sub({
    set: function(key, data) {
        this._super_(MockCollectionB).set('C_' + key, data);
    }
});

QUnit.module("creme.component.js", new QUnitMixin());

QUnit.test('creme.component (inherits Object)', function(assert) {
    var Klass = creme.component.extend();
    var obj = new Klass();

    assert.deepEqual(Klass.__super__, Object.prototype);

    assert.equal(Object.isFunc(obj._init_), false);
    assert.equal(Object.isFunc(Klass.sub), true);

    assert.equal(Object.isSubClassOf(obj, Object), true, 'is Object');
    assert.equal(Object.isSubClassOf(obj, Klass), true, 'is klass');
    assert.equal(Object.isSubClassOf(obj, creme.component.Component), false);
    assert.equal(Object.isSubClassOf(obj, MockComponentA), false);
    assert.equal(Object.isSubClassOf(obj, MockComponentAB), false);
});

QUnit.test('creme.component (inherits Component)', function(assert) {
    var obj = new creme.component.Component();

    assert.deepEqual(creme.component.Component.__super__, Object.prototype);

    assert.equal(Object.isFunc(obj._init_), true);
    assert.equal(Object.isFunc(creme.component.Component.sub), true);

    assert.equal(obj.is(Object), true, 'is Object');
    assert.equal(obj.is(creme.component.Component), true, 'is Component');
    assert.equal(obj.is(MockComponentA), false);
    assert.equal(obj.is(MockComponentAB), false);
});

QUnit.test('creme.component (MockA)', function(assert) {
    var a = new MockComponentA(12);

    assert.deepEqual(MockComponentA.__super__, creme.component.Component.prototype);
    assert.equal(a.get(), 12);
    assert.equal(a.add(485), 12 + 485);
    assert.equal(a.add(), 12);

    assert.equal(Object.isFunc(MockComponentA.sub), true);

    assert.equal(a.is(Object), true, 'is Object');
    assert.equal(a.is(creme.component.Component), true, 'is Component');
    assert.equal(a.is(MockComponentA), true, 'is MockComponentA');
    assert.equal(a.is(MockComponentAB), false, 'not MockComponentAB');
    assert.equal(a.is(MockComponentAC), false, 'not MockComponentAC');
});

QUnit.test('creme.component (MockAB)', function(assert) {
    var ab = new MockComponentAB(12, 8);

    assert.deepEqual(MockComponentAB.__super__, MockComponentA.prototype);
    assert.deepEqual(MockComponentAB.__super__.constructor.__super__, creme.component.Component.prototype);

    assert.deepEqual(ab.get(), [12, 8]);
    assert.equal(ab.add(485), 8 * (12 + 485));
    assert.equal(ab.add(), 8 * 12);

    assert.equal(Object.isFunc(MockComponentAB.sub), true);

    assert.equal(ab.is(Object), true);
    assert.equal(ab.is(creme.component.Component), true);
    assert.equal(ab.is(MockComponentA), true);
    assert.equal(ab.is(MockComponentAB), true);
    assert.equal(ab.is(MockComponentAC), false);
});

QUnit.test('creme.component (MockAC)', function(assert) {
    var ac = new MockComponentAC(12, 8);

    assert.deepEqual(MockComponentAC.__super__, MockComponentA.prototype);
    assert.deepEqual(MockComponentAC.__super__.constructor.__super__, creme.component.Component.prototype);

    assert.deepEqual(ac.get(), [12, 8]);
    assert.equal(ac.add(485), 8 + (12 + 485));
    assert.equal(ac.add(), 8 + 12);

    assert.equal(Object.isFunc(MockComponentAC.sub), true);

    assert.equal(ac.is(Object), true);
    assert.equal(ac.is(creme.component.Component), true);
    assert.equal(ac.is(MockComponentA), true);
    assert.equal(ac.is(MockComponentAB), false);
    assert.equal(ac.is(MockComponentAC), true);
});

QUnit.test('creme.component (no _init_)', function(assert) {
    var MockDefaultInit = MockComponentA.sub();

    var a = new MockDefaultInit(12);

    assert.deepEqual(MockDefaultInit.__super__, MockComponentA.prototype);
    assert.equal(a.get(), 12);
    assert.equal(a.add(485), 12 + 485);
    assert.equal(a.add(), 12);

    assert.equal(Object.isFunc(MockDefaultInit.sub), true);

    assert.equal(a.is(Object), true, 'is Object');
    assert.equal(a.is(creme.component.Component), true, 'is Component');
    assert.equal(a.is(MockComponentA), true, 'is MockComponentA');
    assert.equal(a.is(MockDefaultInit), true, 'is MockDefaultInit');
    assert.equal(a.is(MockComponentAB), false, 'not MockComponentAB');
    assert.equal(a.is(MockComponentAC), false, 'not MockComponentAC');
});

QUnit.test('creme.component (sub with mandatory arguments)', function(assert) {
    var MockMandatoryBase = creme.component.Component.sub({
        _init_: function(a, b) {
            if (a === undefined) {
                throw new Error('first argument is mandatory');
            }
            this.a = a;
            this.b = b;
        }
    });

    var MockMandatoryA = MockMandatoryBase.sub({
        _init_: function(a) {
            this._super_(MockMandatoryBase, '_init_', a);
        }
    });

    var MockMandatoryMissing = MockMandatoryBase.sub({
        _init_: function() {
            this._super_(MockMandatoryBase, '_init_');
        }
    });

    var mandatory_a = new MockMandatoryA(12);
    assert.equal(mandatory_a.a, 12);
    assert.equal(mandatory_a.is(Object), true, 'is Object');
    assert.equal(mandatory_a.is(creme.component.Component), true, 'is Component');
    assert.equal(mandatory_a.is(MockMandatoryBase), true, 'is MockMandatoryBase');
    assert.equal(mandatory_a.is(MockMandatoryA), true, 'is MockMandatoryA');
    assert.equal(mandatory_a.is(MockMandatoryMissing), false, 'not MockMandatoryMissing');

    this.assertRaises(function() {
        return new MockMandatoryA();
    }, Error, 'Error: first argument is mandatory');

    this.assertRaises(function() {
        return new MockMandatoryMissing();
    }, Error, 'Error: first argument is mandatory');
});

QUnit.test('creme.component (inherit statics)', function(assert) {
    var MockStaticBase = creme.component.Component.sub({
        _init_: function(options) {
            this.options = options || {};
        }
    });

    MockStaticBase.static_base = function() {
        return 12;
    };

    var MockStaticA = MockStaticBase.sub({});
    MockStaticA.static_name = function() {
        return 'A';
    };

    var MockStaticAB = MockStaticA.sub({});
    MockStaticAB.static_name = function() {
        return 'AB';
    };

    assert.equal(12, MockStaticA.static_base());
    assert.equal('A', MockStaticA.static_name());

    assert.equal(12, MockStaticAB.static_base());
    assert.equal('AB', MockStaticAB.static_name());
});

/* This test checks that an inherited collection is not shared between subclasses */
QUnit.test('creme.component (Collection)', function(assert) {
    var collection = new MockCollection();
    var a = new MockCollectionA();
    var a2 = new MockCollectionA();
    var b = new MockCollectionB();
    var bc = new MockCollectionBC();

    assert.deepEqual(MockCollection.__super__, creme.component.Component.prototype);

    assert.deepEqual(MockCollectionA.__super__, MockCollection.prototype);
    assert.deepEqual(MockCollectionA.__super__.constructor.__super__, creme.component.Component.prototype);

    assert.deepEqual(MockCollectionB.__super__, MockCollection.prototype);
    assert.deepEqual(MockCollectionB.__super__.constructor.__super__, creme.component.Component.prototype);

    assert.deepEqual(MockCollectionBC.__super__, MockCollectionB.prototype);
    assert.deepEqual(MockCollectionBC.__super__.constructor.__super__, MockCollection.prototype);
    assert.deepEqual(MockCollectionBC.__super__.constructor.__super__.constructor.__super__, creme.component.Component.prototype);

    assert.equal(collection.size(), 0);
    assert.equal(a.size(), 0);
    assert.equal(a2.size(), 0);
    assert.equal(b.size(), 0);
    assert.equal(bc.size(), 0);

    collection.set('a', 12);

    assert.equal(collection.size(), 1);
    assert.equal(a.size(), 0);
    assert.equal(a2.size(), 0);
    assert.equal(b.size(), 0);
    assert.equal(bc.size(), 0);

    assert.deepEqual(collection._data, {'a': 12});

    a.set('1', 134);
    a.set('2', 2);

    b.set('1', 445);
    bc.set('1', 875);

    assert.equal(collection.size(), 1);
    assert.equal(a.size(), 2);
    assert.equal(a2.size(), 0);
    assert.equal(b.size(), 1);
    assert.equal(bc.size(), 1);

    assert.deepEqual(collection._data, {'a': 12});
    assert.deepEqual(a._data, {'A_1': 134, 'A_2': 2});
    assert.deepEqual(b._data, {'B_1': 445});
    assert.deepEqual(bc._data, {'B_C_1': 875});

    a.clear();

    assert.equal(collection.size(), 1);
    assert.equal(a.size(), 0);
    assert.equal(a2.size(), 0);
    assert.equal(b.size(), 1);
    assert.equal(bc.size(), 1);

    assert.deepEqual(collection._data, {'a': 12});
    assert.deepEqual(b._data, {'B_1': 445});
    assert.deepEqual(bc._data, {'B_C_1': 875});
});

QUnit.test('creme.component._super_', function(assert) {
    var ab = new MockComponentAB(12, 8);

    assert.deepEqual(ab.get(), [12, 8]);
    assert.equal(ab.add(485), 8 * (12 + 485));
    assert.equal(ab.add(), 8 * 12);

    assert.equal(12, ab._super_(MockComponentA).get());
    assert.equal(12 + 485, ab._super_(MockComponentA).add(485));
    assert.equal(12, ab._super_(MockComponentA).add());

    assert.equal(12, ab._super_(MockComponentA, 'get'));
    assert.equal(12 + 485, ab._super_(MockComponentA, 'add', 485));
    assert.equal(12, ab._super_(MockComponentA, 'add'));
});

}(jQuery));
