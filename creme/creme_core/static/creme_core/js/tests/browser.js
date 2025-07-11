/* globals BrowserVersion PropertyFaker */

(function($) {

QUnit.module("BrowserVersion", new QUnitMixin());

QUnit.parametrize('BrowserVersion.match (invalid op or version)', [
    ['', '85.0.5.1404'],
    ['85', ''],
    ['85', undefined],
    ['other', '85.0.5.1404'],
    ['#85', '85.0.5.1404']
], function(pattern, version, assert) {
    assert.equal(BrowserVersion.match(pattern, version), false);
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
    assert.equal(BrowserVersion.match(pattern, version), expected);
});

QUnit.parametrize('BrowserVersion.match (>=)', [
    ['>=85', '85.0.5.1404', true],
    ['>=85', '85.0.6.2404', true],
    ['>=85', '86.0.6.2404', true],
    ['>=85', '84.0.6.2404', false]
], function(pattern, version, expected, assert) {
    assert.equal(BrowserVersion.match(pattern, version), expected);
});

QUnit.parametrize('BrowserVersion.match (<=)', [
    ['<=85', '85.0.5.1404', true],
    ['<=85', '85.0.6.2404', true],
    ['<=85', '86.0.6.2404', false],
    ['<=85', '84.0.6.2404', true]
], function(pattern, version, expected, assert) {
    assert.equal(BrowserVersion.match(pattern, version), expected);
});

QUnit.parametrize('BrowserVersion.match (<)', [
    ['<85', '85.0.5.1404', false],
    ['<85', '85.0.6.2404', false],
    ['<85', '86.0.6.2404', false],
    ['<85', '84.0.6.2404', true]
], function(pattern, version, expected, assert) {
    assert.equal(BrowserVersion.match(pattern, version), expected);
});

QUnit.parametrize('BrowserVersion.match (>)', [
    ['>85', '85.0.5.1404', false],
    ['>85', '85.0.6.2404', false],
    ['>85', '86.0.6.2404', true],
    ['>85', '84.0.6.2404', false]
], function(pattern, version, expected, assert) {
    assert.equal(BrowserVersion.match(pattern, version), expected);
});

QUnit.parametrize('BrowserVersion.isIE', [
    ['>8', {appVersion: 'MSIE 9'}, true],
    ['==9', {appVersion: 'MSIE 9'}, true],
    ['==10', {appVersion: 'MSIE 9'}, false],
    ['==9', {appVersion: 'Firefox 9'}, false],
    ['==9', {}, false]
], function(pattern, navigatorInfo, expected, assert) {
    var faker = new PropertyFaker({
        instance: window, props: {navigator: navigatorInfo}
    });

    faker.with(function() {
        assert.equal(BrowserVersion.isIE(pattern), expected);
    });
});

QUnit.parametrize('BrowserVersion.isChrome', [
    ['', true, {userAgent: 'Chrome/86'}, true],
    ['>85', true, {userAgent: 'Chrome/86'}, true],
    ['>85', true, {userAgent: 'Chromium/86'}, true],
    ['>85', true, {userAgent: 'HeadlessChrome/86'}, true],

    ['>85', false, {userAgent: 'HeadlessChrome/86'}, true],
    ['>85', false, {userAgent: 'Chromium/86'}, false],
    ['', false, {userAgent: 'Chrome/86'}, false],
    ['', false, {userAgent: 'HeadlessChrome/86'}, true],

    ['<85', true, {userAgent: 'HeadlessChrome/86'}, false],
    ['<85', true, {userAgent: 'Firefox/84'}, false],
    ['', true, {userAgent: 'Firefox/84'}, false]
], function(pattern, chromeFlag, navigatorInfo, expected, assert) {
    var nav_faker = new PropertyFaker({
        instance: window, props: {navigator: navigatorInfo}
    });

    var chrome_faker = new PropertyFaker({
        instance: window, props: {chrome: chromeFlag}
    });

    nav_faker.with(function() {
        chrome_faker.with(function() {
            assert.equal(BrowserVersion.isChrome(pattern), expected);
        });
    });
});

QUnit.parametrize('BrowserVersion.isHeadless', [
    [{webdriver: true}, true],
    [{}, false]
], function(navigatorInfo, expected, assert) {
    var faker = new PropertyFaker({
        instance: window, props: {navigator: navigatorInfo}
    });

    faker.with(function() {
        assert.equal(BrowserVersion.isHeadless(), expected);
    });
});

QUnit.parametrize('BrowserVersion.isFirefox', [
    ['>40', {MozAppearance: true}, {userAgent: 'Firefox/42'}, true],
    ['>40', {MozAppearance: true}, {userAgent: 'Firefox/30'}, false],
    ['>40', {MozAppearance: true}, {userAgent: 'Chrome/85'}, false],
    ['>40', {}, {userAgent: 'Firefox/42'}, false]
], function(pattern, styleInfo, navigatorInfo, expected, assert) {
    var nav_faker = new PropertyFaker({
        instance: window, props: {navigator: navigatorInfo}
    });

    var style_faker = new PropertyFaker({
        instance: document.documentElement,
        props: {style: styleInfo}
    });

    nav_faker.with(function() {
        style_faker.with(function() {
            assert.equal(BrowserVersion.isFirefox(pattern), expected);
        });
    });
});

}(jQuery));
