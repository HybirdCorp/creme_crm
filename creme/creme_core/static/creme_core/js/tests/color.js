/* globals QUnitConsoleMixin */

(function($) {

QUnit.module("color.RGBColor", new QUnitMixin(QUnitConsoleMixin));

QUnit.test('color.RGBColor', function(assert) {
    var color = new RGBColor();

    assert.equal(0, color.r);
    assert.equal(0, color.g);
    assert.equal(0, color.b);
    assert.equal('#000000', new RGBColor().toString());
});

QUnit.test('color.RGBColor (hex)', function(assert) {
    this.assertRaises(function() {
        return new RGBColor('');
    }, Error, 'Error: "" is not a RGB css value');

    this.assertRaises(function() {
        return new RGBColor('#gggggg');
    }, Error, 'Error: "#gggggg" is not a RGB hexadecimal value');

    this.assertRaises(function() {
        return new RGBColor('#00000012');
    }, Error, 'Error: "#00000012" is not a RGB hexadecimal value');

    this.assertRaises(function() {
        return new RGBColor().hex('');
    }, Error, 'Error: "" is not a RGB hexadecimal value');

    this.assertRaises(function() {
        return new RGBColor().hex('#gggggg');
    }, Error, 'Error: "#gggggg" is not a RGB hexadecimal value');

    this.assertRaises(function() {
        return new RGBColor().hex('#00000012');
    }, Error, 'Error: "#00000012" is not a RGB hexadecimal value');

    assert.equal('#000000', new RGBColor().toString());
    assert.equal('#FFFFFF', new RGBColor().hex('#ffffff').toString());
    assert.equal('#00FFAA', new RGBColor().hex('#00ffaa').toString());

    assert.equal('00FFAA', new RGBColor().hex('#00ffaa').hex());
    assert.equal('00FFAA', new RGBColor().hex('00ffaa').hex());
});

QUnit.test('color.RGBColor (decimal)', function(assert) {
    this.assertRaises(function() {
        return new RGBColor(-12);
    }, Error, 'Error: "-12" is not a RGB decimal value');

    this.assertRaises(function() {
        return new RGBColor(0xFFFFFF00);
    }, Error, 'Error: "' + 0xFFFFFF00 + '" is not a RGB decimal value');

    this.assertRaises(function() {
        return new RGBColor().decimal(-12);
    }, Error, 'Error: "-12" is not a RGB decimal value');

    this.assertRaises(function() {
        return new RGBColor().decimal(0xFFFFFF00);
    }, Error, 'Error: "' + 0xFFFFFF00 + '" is not a RGB decimal value');

    this.assertRaises(function() {
        return new RGBColor().decimal('#aa12fd');
    }, Error, 'Error: "#aa12fd" is not a RGB decimal value');

    assert.equal('#FF12FD', new RGBColor(0xff12fd).toString());
    assert.equal('#FF12FD', new RGBColor().decimal(0xff12fd).toString());

    assert.equal(0, new RGBColor().decimal());
    assert.equal(123456, new RGBColor().decimal(123456).decimal());
});

QUnit.test('color.RGBColor (rgb)', function(assert) {
    assert.equal('#FF12FD', new RGBColor({r: 0xff, g: 0x12, b: 0xfd}).toString());
    assert.equal('#001200', new RGBColor({g: 0x12, b: 0}).toString());

    assert.equal('#FF12FD', new RGBColor([255, 18, 253]).toString());
    assert.equal('#FF12FD', new RGBColor('rgb(255, 18, 253)').toString());

    assert.equal('rgb(255,18,253)', new RGBColor('#FF12FD').rgb());
    assert.equal('rgb(0,18,0)', new RGBColor({g: 0x12, b: 0}).rgb());

    this.assertRaises(function() {
        return new RGBColor().rgb('#aa12fd');
    }, Error, 'Error: "#aa12fd" is not a RGB css value');

    this.assertRaises(function() {
        return new RGBColor().rgb('hls(1.0, 0.0, 0.0)');
    }, Error, 'Error: "hls(1.0, 0.0, 0.0)" is not a RGB css value');

    this.assertRaises(function() {
        return new RGBColor().rgb(12);
    }, Error, 'Error: "12" is not a RGB css value');
});

QUnit.test('color.RGBColor (css name)', function(assert) {
    assert.equal('#000000', new RGBColor('black').toString());

    this.assertRaises(function() {
        return new RGBColor('unknown');
    }, Error, 'Error: "unknown" is not a valid css named color');

    assert.equal('#FFFF00', new RGBColor('yellow').toString());
    assert.equal('#FFD700', new RGBColor('gold').toString());
});

QUnit.test('color.RGBColor (set / clone)', function(assert) {
    var a = new RGBColor(0xff12fd);
    var b = new RGBColor().set(a);
    var c = a.clone();

    a.decimal(0xaa73ef);

    assert.equal('#AA73EF', a.toString());
    assert.equal('#FF12FD', b.toString());
    assert.equal('#FF12FD', c.toString());
});

QUnit.test('color.RGBColor.get', function(assert) {
    var a = new RGBColor(0xaa73ef);
    var b = new RGBColor(0xffffff);
    var c = new RGBColor(0);

    assert.deepEqual({r: 0xaa, g: 0x73, b: 0xef}, a.get());
    assert.deepEqual({r: 0xff, g: 0xff, b: 0xff}, b.get());
    assert.deepEqual({r: 0, g: 0, b: 0}, c.get());
});

QUnit.test('color.RGBColor.lightness', function(assert) {
    assert.equal(0, new RGBColor(0).lightness());
    assert.equal(100, new RGBColor(0xffffff).lightness());
    assert.equal(50, new RGBColor(0xff0000).lightness());
    assert.equal(50, new RGBColor(0x00ff00).lightness());
    assert.equal(50, new RGBColor(0x0000ff).lightness());
    assert.equal(39, new RGBColor(0x913434).lightness());
});

QUnit.test('color.RGBColor.intensity', function(assert) {
    assert.equal(0.0, new RGBColor(0).intensity());
    assert.equal(1.0, new RGBColor(0xffffff).intensity());
    assert.equal(0.213, new RGBColor(0xff0000).intensity());
    assert.equal(0.715, new RGBColor(0x00ff00).intensity());
    assert.equal(0.072, new RGBColor(0x0000ff).intensity());
    assert.equal(0.085, new RGBColor(0x913434).intensity());
});

QUnit.test('color.RGBColor.intensity (gamma=1.0)', function(assert) {
    assert.equal(0.0, new RGBColor(0).intensity(1.0));
    assert.equal(1.0, new RGBColor(0xffffff).intensity(1.0));
    assert.equal(0.213, new RGBColor(0xff0000).intensity(1.0));
    assert.equal(0.715, new RGBColor(0x00ff00).intensity(1.0));
    assert.equal(0.072, new RGBColor(0x0000ff).intensity(1.0));
    assert.equal(0.281, new RGBColor(0x913434).intensity(1.0));
});

QUnit.test('color.RGBColor.greyscale', function(assert) {
    assert.equal(0x000000, new RGBColor(0).grayscale().decimal());
    assert.equal(0xFFFFFF, new RGBColor(0xffffff).grayscale().decimal());
    assert.equal(0x363636, new RGBColor(0xff0000).grayscale().decimal());
    assert.equal(0xB6B6B6, new RGBColor(0x00ff00).grayscale().decimal());
    assert.equal(0x121212, new RGBColor(0x0000ff).grayscale().decimal());
    assert.equal(0x151515, new RGBColor(0x913434).grayscale().decimal());
});

QUnit.test('color.RGBColor.contrast', function(assert) {
    var black = new RGBColor(0);
    var white = new RGBColor(0xffffff);

    assert.equal(1.0, black.contrast(black));
    assert.equal(1.0, white.contrast(white));

    assert.equal(21.0, black.contrast(white));
    assert.equal(21.0, white.contrast(black));

    assert.equal(2.909, new RGBColor(0xff0000).contrast(0x00ff00));
    assert.equal(15.300, new RGBColor(0x00ff00).contrast(black));
    assert.equal(2.440, new RGBColor(0x0000ff).contrast(black));

    assert.equal(1.107, new RGBColor(0x913434).contrast(0x0000ff));
    assert.equal(2.713, new RGBColor(0x913434).contrast(0x0000ff, 1.0));
});

QUnit.test('color.RGBColor.foreground', function(assert) {
    var black = new RGBColor(0);
    var white = new RGBColor(0xffffff);

    assert.equal(0x000000, white.foreground().decimal());
    assert.equal(0xFFFFFF, black.foreground().decimal());
    assert.equal(0xFFFFFF, new RGBColor(0xff0000).foreground().decimal()); // red
    assert.equal(0x000000, new RGBColor(0x00ff00).foreground().decimal()); // green
    assert.equal(0x000000, new RGBColor(0xffff00).foreground().decimal()); // yellow
    assert.equal(0xFFFFFF, new RGBColor(0x0000ff).foreground().decimal()); // blue
});

QUnit.test('color.RGBColor.hsl', function(assert) {
    assert.deepEqual({h: 0, s: 0, l: 0, b: 0}, new RGBColor(0).hsl());
    assert.deepEqual({h: 0, s: 0, l: 100, b: 100}, new RGBColor(0xffffff).hsl());
    assert.deepEqual({h: 0, s: 100, l: 50, b: 100}, new RGBColor(0xff0000).hsl());
    assert.deepEqual({h: 120, s: 100, l: 50, b: 100}, new RGBColor(0x00ff00).hsl());
    assert.deepEqual({h: 240, s: 100, l: 50, b: 100}, new RGBColor(0x0000ff).hsl());
    assert.deepEqual({h: 0, s: 47, l: 39, b: 57}, new RGBColor(0x913434).hsl());
});

}(jQuery));
