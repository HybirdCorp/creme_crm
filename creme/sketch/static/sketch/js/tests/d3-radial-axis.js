/* globals QUnitSketchMixin */
(function($) {

QUnit.module("d3.axisRadial", new QUnitMixin(QUnitSketchMixin));

QUnit.test('d3.axisRadial (default props)', function(assert) {
    var scale = d3.scaleLinear()
                  .domain([0, 100])
                  .range([_.toRadian(-180), _.toRadian(180)]);

    var axis = d3.axisRadialInner(scale, 10);

    equal(axis.radius(), 10);
    equal(axis.tickSize(), 6);
    equal(axis.tickSizeInner(), 6);
    equal(axis.tickSizeOuter(), 6);
    deepEqual(axis.ticks(), axis);
    deepEqual(axis.tickArguments(), []);
    equal(axis.tickValues(), null);
    equal(axis.tickFormat(), null);
    equal(axis.tickPadding(), 12);
    equal(axis.offset(), window.devicePixelRatio > 1 ? 0 : 0.5);
    equal(axis.outer(), false);
});

QUnit.test('d3.axisRadial (set props)', function(assert) {
    var scale = d3.scaleLinear()
                  .domain([0, 100])
                  .range([_.toRadian(-180), _.toRadian(180)]);

    var scale2 = d3.scaleLinear()
                    .domain([0, 100])
                    .range([_.toRadian(-180), _.toRadian(180)]);

    var axis = d3.axisRadialInner(scale, 10);
    var fmt = function(d) { return 'A' + d; };

    axis.radius(20)
        .tickSizeInner(8)
        .tickSizeOuter(20)
        .tickArguments(['s'])
        .tickValues([1, 2, 3, 4, 5])
        .tickFormat(fmt)
        .tickPadding(25)
        .outer(true)
        .scale(scale2);

    equal(axis.radius(), 20);
    equal(axis.tickSize(), 20);
    equal(axis.tickSizeInner(), 8);
    equal(axis.tickSizeOuter(), 20);
    deepEqual(axis.tickArguments(), ['s']);
    deepEqual(axis.tickValues(), [1, 2, 3, 4, 5]);
    equal(axis.tickFormat(), fmt);
    equal(axis.tickPadding(), 25);
    deepEqual(axis.scale(), scale2);
    equal(axis.outer(), true);

    axis.ticks(null)
        .outer(false)
        .tickSize(17);

    deepEqual(axis.tickArguments(), [null]);
    equal(axis.outer(), false);
    equal(axis.tickSize(), 17);
    equal(axis.tickSizeInner(), 17);
    equal(axis.tickSizeOuter(), 17);

    axis.tickArguments(null)
        .offset(1);

    deepEqual(axis.tickArguments(), []);
    equal(axis.offset(), 1);
});

QUnit.test('d3.axisRadialInner', function(assert) {
    var scale = d3.scaleLinear()
                  .domain([0, 100])
                  .range([_.toRadian(-180), _.toRadian(180)]);

    var axis = d3.axisRadialInner(scale, 10)
                      .tickFormat(function(d) { return 'V' + d; })
                      .tickPadding(0);

    var output = d3.select(document.createElement('g'));

    output.call(axis);

    this.assertD3Nodes(output, {
        '.tick text': 11,  /* V0 V10 ... V90 V100 */
        '.domain': 1
    });

    axis.tickValues([0, 50, 100]);
    output.call(axis);

    this.assertD3Nodes(output, {
        '.tick text': 3,  /* V0 V50 V100 */
        '.domain': 1
    });
});

QUnit.test('d3.axisRadialOuter', function(assert) {
    var scale = d3.scaleLinear()
                  .domain([0, 100])
                  .range([_.toRadian(-180), _.toRadian(180)]);

    var axis = d3.axisRadialOuter(scale, 10)
                      .tickFormat(function(d) { return 'V' + d; })
                      .tickPadding(0);

    var output = d3.select(document.createElement('g'));

    output.call(axis);

    this.assertD3Nodes(output, {
        '.tick text': 11,  /* V0 V10 ... V90 V100 */
        '.domain': 1
    });

    axis.tickValues([0, 50, 100]);
    output.call(axis);

    this.assertD3Nodes(output, {
        '.tick text': 3,  /* V0 V50 V100 */
        '.domain': 1
    });
});

QUnit.parameterize('d3.axisRadial (arc path)', [
    [-90, 90],      // regular half-circle  (range < 2 * PI)
    [-180, 180],    // full circle (range = 2 * PI)
    [0, 360],       // full circle
    [-90, 100],     // before full and half circle (range % 2PI < PI)
    [-90, 200],     // after full and half circle (range % 2PI > PI)
    [-360, 360],    // full circle twice (range % 2PI < PI)
    [90, -90]       // anti clockwise
], function(start, end, assert) {
    var scale = d3.scaleLinear()
                  .domain([0, 100])
                  .range([_.toRadian(start), _.toRadian(end)]);

    var axis = d3.axisRadialOuter(scale, 10)
                 .tickPadding(0)
                 .tickValues([0, 50, 100]);

    var output = d3.select(document.createElement('g'));

    output.call(axis);

    this.assertD3Nodes(output, {
        '.tick text': 3,  /* 0 50 100 */
        '.domain': 1
    });
});

QUnit.parameterize('d3.axisRadial (ticks transition)', [
    [[0, 25, 50, 75, 100], [0, 50, 100], 3],
    [[0, 50, 100], [0, 25, 50, 75, 100], 5]
], function(ticksBefore, ticksAfter, expected, assert) {
    var scale = d3.scaleLinear()
                  .domain([0, 100])
                  .range([_.toRadian(-90), _.toRadian(90)]);

    var axis = d3.axisRadialOuter(scale, 10)
                 .tickFormat(function(d) { return 'V' + d; })
                 .tickPadding(0)
                 .tickValues(ticksBefore);

    var output = d3.select(document.createElement('g'));

    output.call(axis);

    this.assertD3Nodes(output, {
        '.tick text': ticksBefore.length,
        '.domain': 1
    });

    axis.tickValues(ticksAfter);
    output.transition().duration(50).call(axis);

    stop();

    setTimeout(function() {
        this.assertD3Nodes(output, {
            '.tick text': ticksAfter.length,
            '.domain': 1
        });
        start();
    }.bind(this), 100);
});

}(jQuery));
