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

    deepEqual(Klass.__super__, Object.prototype);

    equal(Object.isFunc(obj._init_), false);
    equal(Object.isFunc(Klass.sub), true);

    equal(Object.isSubClassOf(obj, Object), true, 'is Object');
    equal(Object.isSubClassOf(obj, Klass), true, 'is klass');
    equal(Object.isSubClassOf(obj, creme.component.Component), false);
    equal(Object.isSubClassOf(obj, MockComponentA), false);
    equal(Object.isSubClassOf(obj, MockComponentAB), false);
});

QUnit.test('creme.component (inherits Component)', function(assert) {
    var obj = new creme.component.Component();

    deepEqual(creme.component.Component.__super__, Object.prototype);

    equal(Object.isFunc(obj._init_), true);
    equal(Object.isFunc(creme.component.Component.sub), true);

    equal(obj.is(Object), true, 'is Object');
    equal(obj.is(creme.component.Component), true, 'is Component');
    equal(obj.is(MockComponentA), false);
    equal(obj.is(MockComponentAB), false);
});

QUnit.test('creme.component (MockA)', function(assert) {
    var a = new MockComponentA(12);

    deepEqual(MockComponentA.__super__, creme.component.Component.prototype);
    equal(a.get(), 12);
    equal(a.add(485), 12 + 485);
    equal(a.add(), 12);

    equal(Object.isFunc(MockComponentA.sub), true);

    equal(a.is(Object), true, 'is Object');
    equal(a.is(creme.component.Component), true, 'is Component');
    equal(a.is(MockComponentA), true, 'is MockComponentA');
    equal(a.is(MockComponentAB), false, 'not MockComponentAB');
    equal(a.is(MockComponentAC), false, 'not MockComponentAC');
});

QUnit.test('creme.component (MockAB)', function(assert) {
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

QUnit.test('creme.component (MockAC)', function(assert) {
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

QUnit.test('creme.component (no _init_)', function(assert) {
    var MockDefaultInit = MockComponentA.sub();

    var a = new MockDefaultInit(12);

    deepEqual(MockDefaultInit.__super__, MockComponentA.prototype);
    equal(a.get(), 12);
    equal(a.add(485), 12 + 485);
    equal(a.add(), 12);

    equal(Object.isFunc(MockDefaultInit.sub), true);

    equal(a.is(Object), true, 'is Object');
    equal(a.is(creme.component.Component), true, 'is Component');
    equal(a.is(MockComponentA), true, 'is MockComponentA');
    equal(a.is(MockDefaultInit), true, 'is MockDefaultInit');
    equal(a.is(MockComponentAB), false, 'not MockComponentAB');
    equal(a.is(MockComponentAC), false, 'not MockComponentAC');
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
    equal(mandatory_a.a, 12);
    equal(mandatory_a.is(Object), true, 'is Object');
    equal(mandatory_a.is(creme.component.Component), true, 'is Component');
    equal(mandatory_a.is(MockMandatoryBase), true, 'is MockMandatoryBase');
    equal(mandatory_a.is(MockMandatoryA), true, 'is MockMandatoryA');
    equal(mandatory_a.is(MockMandatoryMissing), false, 'not MockMandatoryMissing');

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

    equal(12, MockStaticA.static_base());
    equal('A', MockStaticA.static_name());

    equal(12, MockStaticAB.static_base());
    equal('AB', MockStaticAB.static_name());
});

/* This test checks that an inherited collection is not shared between subclasses */
QUnit.test('creme.component (Collection)', function(assert) {
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

QUnit.test('creme.component._super_', function(assert) {
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

}(jQuery));
