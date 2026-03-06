/* globals PropertyFaker */

(function($) {

QUnit.module("l10n.js", new QUnitMixin());

QUnit.test('_.djangoLanguageCode', function(assert) {
    this.withLanguageCode('en', function() {
        assert.equal(_.djangoLanguageCode(), 'en-US');
    });

    this.withLanguageCode('fr', function() {
        assert.equal(_.djangoLanguageCode(), 'fr-FR');
    });

    this.withLanguageCode('yep', function() {
        assert.equal(_.djangoLanguageCode(), 'yep');
    });

    this.withLanguageCode(null, function() {
        var faker = new PropertyFaker({
            instance: window, props: {navigator: {language: "es-ES"}}
        });

        faker.with(function() {
            assert.equal(_.djangoLanguageCode(), 'es-ES');
        });
    });
});

QUnit.test('_.languageCode', function(assert) {
    var faker = new PropertyFaker({
        instance: window, props: {navigator: {language: "es-ES"}}
    });

    faker.with(function() {
        assert.equal(_.languageCode(), 'es-ES');
    });

    faker = new PropertyFaker({
        instance: window, props: {navigator: {}}
    });

    faker.with(function() {
        assert.equal(_.languageCode(), 'en-US');
    });
});

}(jQuery));

