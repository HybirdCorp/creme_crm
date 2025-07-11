(function($) {

QUnit.module("creme.sketch.color", new QUnitMixin());

QUnit.test('creme.d3Colorize', function(assert) {
    var data = [{text: 'A'}, {text: 'B'}, {text: 'C'}];
    var colors = ["#000000", "#cccccc", "#ffffff"];
    var scale = d3.scaleOrdinal()
                      .domain([0, 1, 2])
                      .range(colors);

    var colorize = creme.d3Colorize()
                            .scale(scale)
                            .accessor(function(d, i) { return i; });

    assert.deepEqual(colorize(data), [
        {text: 'A', textColor: 'white', color: '#000000', isDarkColor: true},
        {text: 'B', textColor: 'black', color: '#cccccc', isDarkColor: false},
        {text: 'C', textColor: 'black', color: '#ffffff', isDarkColor: false}
    ]);
});

QUnit.test('creme.d3Colorize (default accessor)', function(assert) {
    var data = [{text: 'A', x: 2}, {text: 'B', x: 1}, {text: 'C', x: 0}];
    var colors = ["#000000", "#cccccc", "#ffffff"];
    var scale = d3.scaleOrdinal()
                      .domain([0, 1, 2])
                      .range(colors);

    var colorize = creme.d3Colorize()
                            .scale(scale);

    assert.deepEqual(colorize(data), [
        {text: 'A', x: 2, textColor: 'black', color: '#ffffff', isDarkColor: false},
        {text: 'B', x: 1, textColor: 'black', color: '#cccccc', isDarkColor: false},
        {text: 'C', x: 0, textColor: 'white', color: '#000000', isDarkColor: true}
    ]);
});

QUnit.test('creme.d3Colorize (default scale)', function(assert) {
    var data = [{text: 'A', x: 2}, {text: 'B', x: 1}, {text: 'C', x: 0}];
    var colorize = creme.d3Colorize();

    assert.deepEqual(colorize(data), [
        {text: 'A', x: 2, textColor: 'white', color: 'black', isDarkColor: true},
        {text: 'B', x: 1, textColor: 'white', color: 'black', isDarkColor: true},
        {text: 'C', x: 0, textColor: 'white', color: 'black', isDarkColor: true}
    ]);
});

QUnit.test('creme.d3Colorize (data.color)', function(assert) {
    var data = [{text: 'A', x: 2, color: '#aa0000'}, {text: 'B', x: 1, color: 'yellow'}, {text: 'C', x: 0, color: 'gray'}];
    var scale = d3.scaleOrdinal()
                      .domain([0, 1, 2])
                      .range(["#000000", "#cccccc", "#ffffff"]);
    var textScale = d3.scaleOrdinal()
                          .domain([0, 1, 2])
                          .range(["#ff0000", "#00ff00", "#0000ff"]);

    var colorize = creme.d3Colorize()
                            .scale(scale)
                            .textColor(textScale);

    assert.deepEqual(colorize(data), [
        {text: 'A', x: 2, textColor: '#ff0000', color: '#aa0000', isDarkColor: true},
        {text: 'B', x: 1, textColor: '#00ff00', color: 'yellow', isDarkColor: false},
        {text: 'C', x: 0, textColor: '#0000ff', color: 'gray', isDarkColor: true}
    ]);
});

}(jQuery));
