/* globals QUnitConsoleMixin */

(function($) {

QUnit.module("color.RGBColor", new QUnitMixin(QUnitConsoleMixin));

QUnit.test('color.RGBColor', function(assert) {
    var color = new RGBColor();

    equal(0, color.r);
    equal(0, color.g);
    equal(0, color.b);
    equal('#000000', new RGBColor().toString());
});

QUnit.test('color.RGBColor (hex)', function(assert) {
    this.assertRaises(function() {
        return new RGBColor('');
    }, Error, 'Error: "" is not a RGB hexadecimal value');

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

    equal('#000000', new RGBColor().toString());
    equal('#FFFFFF', new RGBColor().hex('#ffffff').toString());
    equal('#00FFAA', new RGBColor().hex('#00ffaa').toString());

    equal('00FFAA', new RGBColor().hex('#00ffaa').hex());
    equal('00FFAA', new RGBColor().hex('00ffaa').hex());
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

    equal('#FF12FD', new RGBColor(0xff12fd).toString());
    equal('#FF12FD', new RGBColor().decimal(0xff12fd).toString());

    equal(0, new RGBColor().decimal());
    equal(123456, new RGBColor().decimal(123456).decimal());
});

QUnit.test('color.RGBColor (rgb)', function(assert) {
    equal('#FF12FD', new RGBColor({r: 0xff, g: 0x12, b: 0xfd}).toString());
    equal('#001200', new RGBColor({g: 0x12, b: 0}).toString());
});

QUnit.test('color.RGBColor (set / clone)', function(assert) {
    var a = new RGBColor(0xff12fd);
    var b = new RGBColor().set(a);
    var c = a.clone();

    a.decimal(0xaa73ef);

    equal('#AA73EF', a.toString());
    equal('#FF12FD', b.toString());
    equal('#FF12FD', c.toString());
});

QUnit.test('color.RGBColor.get', function(assert) {
    var a = new RGBColor(0xaa73ef);
    var b = new RGBColor(0xffffff);
    var c = new RGBColor(0);

    deepEqual({r: 0xaa, g: 0x73, b: 0xef}, a.get());
    deepEqual({r: 0xff, g: 0xff, b: 0xff}, b.get());
    deepEqual({r: 0, g: 0, b: 0}, c.get());
});

QUnit.test('color.RGBColor.lightness', function(assert) {
    equal(0, new RGBColor(0).lightness());
    equal(100, new RGBColor(0xffffff).lightness());
    equal(50, new RGBColor(0xff0000).lightness());
    equal(50, new RGBColor(0x00ff00).lightness());
    equal(50, new RGBColor(0x0000ff).lightness());
    equal(39, new RGBColor(0x913434).lightness());
});

QUnit.test('color.RGBColor.intensity', function(assert) {
    equal(0.0, new RGBColor(0).intensity());
    equal(1.0, new RGBColor(0xffffff).intensity());
    equal(0.213, new RGBColor(0xff0000).intensity());
    equal(0.715, new RGBColor(0x00ff00).intensity());
    equal(0.072, new RGBColor(0x0000ff).intensity());
    equal(0.085, new RGBColor(0x913434).intensity());
});

QUnit.test('color.RGBColor.intensity (gamma=1.0)', function(assert) {
    equal(0.0, new RGBColor(0).intensity(1.0));
    equal(1.0, new RGBColor(0xffffff).intensity(1.0));
    equal(0.213, new RGBColor(0xff0000).intensity(1.0));
    equal(0.715, new RGBColor(0x00ff00).intensity(1.0));
    equal(0.072, new RGBColor(0x0000ff).intensity(1.0));
    equal(0.281, new RGBColor(0x913434).intensity(1.0));
});

QUnit.test('color.RGBColor.greyscale', function(assert) {
    equal(0x000000, new RGBColor(0).grayscale().decimal());
    equal(0xFFFFFF, new RGBColor(0xffffff).grayscale().decimal());
    equal(0x363636, new RGBColor(0xff0000).grayscale().decimal());
    equal(0xB6B6B6, new RGBColor(0x00ff00).grayscale().decimal());
    equal(0x121212, new RGBColor(0x0000ff).grayscale().decimal());
    equal(0x151515, new RGBColor(0x913434).grayscale().decimal());
});

QUnit.test('color.RGBColor.contrast', function(assert) {
    var black = new RGBColor(0);
    var white = new RGBColor(0xffffff);

    equal(1.0, black.contrast(black));
    equal(1.0, white.contrast(white));

    equal(21.0, black.contrast(white));
    equal(21.0, white.contrast(black));

    equal(2.909, new RGBColor(0xff0000).contrast(0x00ff00));
    equal(15.300, new RGBColor(0x00ff00).contrast(black));
    equal(2.440, new RGBColor(0x0000ff).contrast(black));

    equal(1.107, new RGBColor(0x913434).contrast(0x0000ff));
    equal(2.713, new RGBColor(0x913434).contrast(0x0000ff, 1.0));
});

QUnit.test('color.RGBColor.foreground', function(assert) {
    var black = new RGBColor(0);
    var white = new RGBColor(0xffffff);

    equal(0x000000, white.foreground().decimal());
    equal(0xFFFFFF, black.foreground().decimal());
    equal(0xFFFFFF, new RGBColor(0xff0000).foreground().decimal()); // red
    equal(0x000000, new RGBColor(0x00ff00).foreground().decimal()); // green
    equal(0x000000, new RGBColor(0xffff00).foreground().decimal()); // yellow
    equal(0xFFFFFF, new RGBColor(0x0000ff).foreground().decimal()); // blue
});

QUnit.test('color.RGBColor.hsl', function(assert) {
    deepEqual({h: 0, s: 0, l: 0, b: 0}, new RGBColor(0).hsl());
    deepEqual({h: 0, s: 0, l: 100, b: 100}, new RGBColor(0xffffff).hsl());
    deepEqual({h: 0, s: 100, l: 50, b: 100}, new RGBColor(0xff0000).hsl());
    deepEqual({h: 120, s: 100, l: 50, b: 100}, new RGBColor(0x00ff00).hsl());
    deepEqual({h: 240, s: 100, l: 50, b: 100}, new RGBColor(0x0000ff).hsl());
    deepEqual({h: 0, s: 47, l: 39, b: 57}, new RGBColor(0x913434).hsl());
});

/*
QUnit.test('creme.color (deprecated functions)', function(assert) {
    deepEqual({r: 0xaa, g: 0x73, b: 0xef}, creme.color.HEXtoRGB(0xaa73ef));
    equal(0.085, creme.color.luminance(0x91, 0x34, 0x34));
    equal(2.440, creme.color.contrast(0, 0, 255, 0, 0, 0));
    equal('white', creme.color.maxContrastingColor(0, 0, 255)); // blue
    equal('black', creme.color.maxContrastingColor(255, 255, 0)); // yellow

    deepEqual([
        ['creme.color.HEXtoRGB is deprecated; Use new RGBColor(hex) instead'],
        ['creme.color.luminance is deprecated; Use new RGBColor({r:r, g:g, b:b}).intensity() instead'],
        ['creme.color.contrast is deprecated; Use new RGBColor({r:r, g:g, b:b}).contrast({r:r2, g:g2, b:b2}) instead'],
        ['creme.color.maxContrastingColor is deprecated; Use new RGBColor({r:r, g:g, b:b}).foreground() instead'],
        ['creme.color.maxContrastingColor is deprecated; Use new RGBColor({r:r, g:g, b:b}).foreground() instead']
    ], this.mockConsoleWarnCalls());
});
*/

}(jQuery));
