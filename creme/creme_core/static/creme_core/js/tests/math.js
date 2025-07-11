(function($) {

QUnit.module("math.js", new QUnitMixin());

QUnit.test('_.scaleRound', function(assert) {
    var scaleRound = _.scaleRound;

    assert.equal(scaleRound(6.28318, undefined), 6);
    assert.equal(scaleRound(6.28318, 0), 6);
    assert.equal(scaleRound(6.28318, 10), 6.28318);
    assert.equal(scaleRound(6.28318, 4), 6.2832);
    assert.equal(scaleRound(6.28318, 1), 6.3);
});

QUnit.test('_.scaleTrunc', function(assert) {
    var scaleTrunc = _.scaleTrunc;

    assert.equal(scaleTrunc(6.28318, undefined), 6);
    assert.equal(scaleTrunc(6.28318, 0), 6);
    assert.equal(scaleTrunc(6.28318, 10), 6.28318);
    assert.equal(scaleTrunc(6.28318, 4), 6.2831);
    assert.equal(scaleTrunc(6.28318, 1), 6.2);
});

QUnit.test('_.clamp', function(assert) {
    var clamp = _.clamp;

    assert.equal(clamp(6.28318, 0, undefined), 6.28318);
    assert.equal(clamp(6.28318, 3.14, undefined), 6.28318);
    assert.equal(clamp(-6.28318, 3.14, undefined), 3.14);
    assert.equal(clamp(-6.28318, undefined, 3.14), -6.28318);
    assert.equal(clamp(6.28318, undefined, 3.14), 3.14);
    assert.equal(clamp(6.28318, 0, 3.14), 3.14);
    assert.equal(clamp(-6.28318, 0, 3.14), 0);
    assert.equal(clamp(6.28318, 7, 8), 7);
    assert.equal(clamp(15, 7, 8), 8);
    assert.equal(clamp(15, 7, 6), 7);
});

QUnit.test('_.absRound', function(assert) {
    var absRound = _.absRound;

    assert.equal(absRound(0), 0);
    assert.equal(absRound(-1), 0);
    assert.equal(absRound(1), 1);
    assert.equal(absRound(0.3), 0);
    assert.equal(absRound(-0.3), 0);
    assert.equal(absRound(0.5), 1);
    assert.equal(absRound(-0.5), 0);
    assert.equal(absRound(0.999), 1);
    assert.equal(absRound(-0.999), 0);
});

QUnit.test('_.toNumber', function(assert) {
    var toNumber = _.toNumber;

    assert.ok(isNaN(toNumber(undefined)));
    assert.ok(isNaN(toNumber("no")));

    assert.equal(toNumber(null), 0);
    assert.equal(toNumber("15.72"), 15.72);
    assert.equal(toNumber("-15"), -15);
});


QUnit.test('_.toRadian', function(assert) {
    var toRadian = _.toRadian;

    assert.equal(toRadian(0), 0);
    assert.equal(toRadian(90), Math.PI / 2);
    assert.equal(toRadian(-90), -Math.PI / 2);
    assert.equal(toRadian(-180), -Math.PI);
});

QUnit.test('_.toDegree', function(assert) {
    var toDegree = _.toDegree;

    assert.equal(toDegree(0), 0);
    assert.equal(toDegree(Math.PI / 2), 90);
    assert.equal(toDegree(-Math.PI / 2), -90);
    assert.equal(toDegree(-Math.PI), -180);
});

}(jQuery));
