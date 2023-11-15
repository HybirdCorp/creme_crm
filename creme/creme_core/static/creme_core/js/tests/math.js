(function($) {

QUnit.module("math.js", new QUnitMixin());

QUnit.test('_.scaleRound', function(assert) {
    var scaleRound = _.scaleRound;

    equal(scaleRound(6.28318, undefined), 6);
    equal(scaleRound(6.28318, 0), 6);
    equal(scaleRound(6.28318, 10), 6.28318);
    equal(scaleRound(6.28318, 4), 6.2832);
    equal(scaleRound(6.28318, 1), 6.3);
});

QUnit.test('_.scaleTrunc', function(assert) {
    var scaleTrunc = _.scaleTrunc;

    equal(scaleTrunc(6.28318, undefined), 6);
    equal(scaleTrunc(6.28318, 0), 6);
    equal(scaleTrunc(6.28318, 10), 6.28318);
    equal(scaleTrunc(6.28318, 4), 6.2831);
    equal(scaleTrunc(6.28318, 1), 6.2);
});

QUnit.test('_.clamp', function(assert) {
    var clamp = _.clamp;

    equal(clamp(6.28318, 0, undefined), 6.28318);
    equal(clamp(6.28318, 3.14, undefined), 6.28318);
    equal(clamp(-6.28318, 3.14, undefined), 3.14);
    equal(clamp(-6.28318, undefined, 3.14), -6.28318);
    equal(clamp(6.28318, undefined, 3.14), 3.14);
    equal(clamp(6.28318, 0, 3.14), 3.14);
    equal(clamp(-6.28318, 0, 3.14), 0);
    equal(clamp(6.28318, 7, 8), 7);
    equal(clamp(15, 7, 8), 8);
    equal(clamp(15, 7, 6), 7);
});

QUnit.test('_.absRound', function(assert) {
    var absRound = _.absRound;

    equal(absRound(0), 0);
    equal(absRound(-1), 0);
    equal(absRound(1), 1);
    equal(absRound(0.3), 0);
    equal(absRound(-0.3), 0);
    equal(absRound(0.5), 1);
    equal(absRound(-0.5), 0);
    equal(absRound(0.999), 1);
    equal(absRound(-0.999), 0);
});

QUnit.test('_.toNumber', function(assert) {
    var toNumber = _.toNumber;

    ok(isNaN(toNumber(undefined)));
    ok(isNaN(toNumber("no")));

    equal(toNumber(null), 0);
    equal(toNumber("15.72"), 15.72);
    equal(toNumber("-15"), -15);
});


QUnit.test('_.toRadian', function(assert) {
    var toRadian = _.toRadian;

    equal(toRadian(0), 0);
    equal(toRadian(90), Math.PI / 2);
    equal(toRadian(-90), -Math.PI / 2);
    equal(toRadian(-180), -Math.PI);
});

QUnit.test('_.toDegree', function(assert) {
    var toDegree = _.toDegree;

    equal(toDegree(0), 0);
    equal(toDegree(Math.PI / 2), 90);
    equal(toDegree(-Math.PI / 2), -90);
    equal(toDegree(-Math.PI), -180);
});

}(jQuery));
