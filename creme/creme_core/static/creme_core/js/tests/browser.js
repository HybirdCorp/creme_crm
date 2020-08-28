/* globals BrowserVersion */

(function($) {

QUnit.module("BrowserVersion", new QUnitMixin());

QUnit.parametrize('BrowserVersion.match (invalid op or version)', [
    ['', '85.0.5.1404'],
    ['85', ''],
    ['other', '85.0.5.1404']
], function(pattern, version, assert) {
    equal(BrowserVersion.match(pattern, version), false);
});

QUnit.parametrize('BrowserVersion.match (==)', [
    ['85', '85.0.5.1404', true],
    ['85', '85.0.6.2404', true],
    ['85', '86.0.6.2404', false],
    ['85', '84.0.6.2404', false],
    ['==85', '85.0.5.1404', true],
    ['==85', '85.0.6.2404', true],
    ['==85', '86.0.6.2404', false],
    ['==85', '84.0.6.2404', false]
], function(pattern, version, expected, assert) {
    equal(BrowserVersion.match(pattern, version), expected);
});

QUnit.parametrize('BrowserVersion.match (>=)', [
    ['>=85', '85.0.5.1404', true],
    ['>=85', '85.0.6.2404', true],
    ['>=85', '86.0.6.2404', true],
    ['>=85', '84.0.6.2404', false]
], function(pattern, version, expected, assert) {
    equal(BrowserVersion.match(pattern, version), expected);
});

QUnit.parametrize('BrowserVersion.match (<=)', [
    ['<=85', '85.0.5.1404', true],
    ['<=85', '85.0.6.2404', true],
    ['<=85', '86.0.6.2404', false],
    ['<=85', '84.0.6.2404', true]
], function(pattern, version, expected, assert) {
    equal(BrowserVersion.match(pattern, version), expected);
});

QUnit.parametrize('BrowserVersion.match (<)', [
    ['<85', '85.0.5.1404', false],
    ['<85', '85.0.6.2404', false],
    ['<85', '86.0.6.2404', false],
    ['<85', '84.0.6.2404', true]
], function(pattern, version, expected, assert) {
    equal(BrowserVersion.match(pattern, version), expected);
});

QUnit.parametrize('BrowserVersion.match (>)', [
    ['>85', '85.0.5.1404', false],
    ['>85', '85.0.6.2404', false],
    ['>85', '86.0.6.2404', true],
    ['>85', '84.0.6.2404', false]
], function(pattern, version, expected, assert) {
    equal(BrowserVersion.match(pattern, version), expected);
});

}(jQuery));
