(function($) {

QUnit.module("creme.sketch.utils", new QUnitMixin());

QUnit.test('creme.d3BisectScale (linear)', function(assert) {
    var data = [{x: 0, y: 1}, {x: 1, y: 2}, {x: 2, y: 4}, {x: 3, y: 8}];
    var scale = d3.scaleLinear()
                      .domain([0, 3])
                      .range([0, 1000]);

    var bisect = creme.d3BisectScale(function(d) { return d.x; }).scale(scale);

    equal(0, bisect(data, 0));
    equal(0, bisect(data, 100));
    equal(1, bisect(data, 300));
    equal(2, bisect(data, 500));
    equal(3, bisect(data, 1000));
});

QUnit.test('creme.d3BisectScale (ordinal)', function(assert) {
    var data = [{x: 'A', y: 1}, {x: 'B', y: 2}, {x: 'C', y: 4}, {x: 'D', y: 8}];
    var scale = d3.scaleOrdinal()
                      .domain(data.map(function(d) { return d.x; }))
                      .range([0, 1000]);

    var bisect = creme.d3BisectScale(function(d) { return d.x; }).scale(scale);

    equal('A', bisect(data, 0));
    equal('A', bisect(data, 100));
    equal('B', bisect(data, 300));
    equal('C', bisect(data, 500));
    equal('D', bisect(data, 1000));
});

}(jQuery));
