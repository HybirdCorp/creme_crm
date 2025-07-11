/* globals QUnitWidgetMixin FunctionFaker */

(function($) {

QUnit.module("creme.widget.Editor", new QUnitMixin(QUnitEventMixin,
                                                   QUnitWidgetMixin, {
    afterEach: function() {
        creme.widget.shutdown(this.qunitFixture());
    },

    withTinymceLoaderFaker: function(block) {
        return new FunctionFaker({
            instance: tinymce.PluginManager,
            method: 'load'
        }).with(function() {
            return new FunctionFaker({
                instance: tinymce.ThemeManager,
                method: 'load'
            }).with(block.bind(this));
        });
    }
}));

QUnit.test('creme.widget.Editor.create', function(assert) {
    var element = $(
       '<textarea widget="ui-creme-editor" class="ui-creme-editor ui-creme-widget widget-auto"></textarea>'
    ).appendTo(this.qunitFixture());

    var faker = this.withTinymceLoaderFaker(function() {
        var widget = creme.widget.create(element);

        assert.equal(element.hasClass('widget-active'), true);
        assert.equal(element.hasClass('widget-ready'), true);
        assert.equal(widget.editor() instanceof tinymce.Editor, true);
    });

    assert.deepEqual(faker.calls().map(function(c) { return c[0]; }), [
        "spellchecker",
        "pagebreak",
        "style",
        "layer",
        "table",
        "save",
        "advhr",
        "advimage",
        "advlink",
        "emotions",
        "iespell",
        "inlinepopups",
        "insertdatetime",
        "preview",
        "media",
        "searchreplace",
        "print",
        "contextmenu",
        "paste",
        "directionality",
        "fullscreen",
        "noneditable",
        "visualchars",
        "nonbreaking",
        "xhtmlxtras",
        "template",
        "fullpage"
    ]);
});

}(jQuery));
