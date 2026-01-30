/* globals QUnitWidgetMixin FunctionFaker */

(function($) {

QUnit.module("creme.widget.TinyMCEditor", new QUnitMixin(QUnitEventMixin,
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

QUnit.test('creme.widget.TinyMCEditor.create', function(assert) {
    var element = $(
       '<textarea widget="ui-creme-tinymceditor" class="ui-creme-tinymceditor ui-creme-widget widget-auto"></textarea>'
    ).appendTo(this.qunitFixture());

    var widget = creme.widget.create(element);

    this.awaitsPromise(widget.editor().editorSetup(), function() {
        assert.equal(element.hasClass('widget-active'), true);
        assert.equal(element.hasClass('widget-ready'), true);
        assert.equal(widget.editor() instanceof creme.TinyMCEditor, true);
        assert.equal(widget.editor().editor() instanceof tinymce.Editor, true);
    });
});

}(jQuery));
