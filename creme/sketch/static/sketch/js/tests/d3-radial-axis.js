/* globals QUnitSketchMixin */
(function($) {

QUnit.module("d3.axisRadial", new QUnitMixin(QUnitSketchMixin));

QUnit.test('d3.axisRadial (default props)', function(assert) {
    var scale = d3.scaleLinear()
                  .domain([0, 100])
                  .range([_.toRadian(-180), _.toRadian(180)]);

    var axis = d3.axisRadialInner(scale, 10);

    assert.equal(axis.radius(), 10);
    assert.equal(axis.tickSize(), 6);
    assert.equal(axis.tickSizeInner(), 6);
    assert.equal(axis.tickSizeOuter(), 6);
    assert.deepEqual(axis.ticks(), axis);
    assert.deepEqual(axis.tickArguments(), []);
    assert.equal(axis.tickValues(), null);
    assert.equal(axis.tickFormat(), null);
    assert.equal(axis.tickPadding(), 12);
    assert.equal(axis.offset(), window.devicePixelRatio > 1 ? 0 : 0.5);
    assert.equal(axis.outer(), false);
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

    assert.equal(axis.radius(), 20);
    assert.equal(axis.tickSize(), 20);
    assert.equal(axis.tickSizeInner(), 8);
    assert.equal(axis.tickSizeOuter(), 20);
    assert.deepEqual(axis.tickArguments(), ['s']);
    assert.deepEqual(axis.tickValues(), [1, 2, 3, 4, 5]);
    assert.equal(axis.tickFormat(), fmt);
    assert.equal(axis.tickPadding(), 25);
    assert.deepEqual(axis.scale(), scale2);
    assert.equal(axis.outer(), true);

    axis.ticks(null)
        .outer(false)
        .tickSize(17);

    assert.deepEqual(axis.tickArguments(), [null]);
    assert.equal(axis.outer(), false);
    assert.equal(axis.tickSize(), 17);
    assert.equal(axis.tickSizeInner(), 17);
    assert.equal(axis.tickSizeOuter(), 17);

    axis.tickArguments(null)
        .offset(1);

    assert.deepEqual(axis.tickArguments(), []);
    assert.equal(axis.offset(), 1);
});

QUnit.test('d3.axisRadialInner (linear scale)', function(assert) {
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

QUnit.test('d3.axisRadialInner (ordinal scale)', function(assert) {
    var scale = d3.scaleBand()
                    .domain([0, 25, 50, 75, 100])
                    .range([_.toRadian(-180), _.toRadian(180)], 0.1)
                    .padding(0.1);

    var axis = d3.axisRadialInner(scale, 10)
                      .tickFormat(function(d) { return 'V' + d; })
                      .tickPadding(0);

    var output = d3.select(document.createElement('g'));

    output.call(axis);

    this.assertD3Nodes(output, {
        '.tick text': 5,  /* V0 V25 V25 V75 V100 */
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

    var done = assert.async();

    setTimeout(function() {
        this.assertD3Nodes(output, {
            '.tick text': ticksAfter.length,
            '.domain': 1
        });
        done();
    }.bind(this), 100);
});

}(jQuery));
