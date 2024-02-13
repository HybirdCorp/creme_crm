/* globals QUnitWidgetMixin */

(function($) {

QUnit.module("creme.form.CKEditor", new QUnitMixin(QUnitAjaxMixin,
                                                   QUnitWidgetMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true});
    },

    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
            'mock/upload': backend.responseJSON(200, {})
        });

        this.setMockBackendPOST({
            'mock/upload': backend.responseJSON(200, {})
        });
    },

    afterEach: function() {
        $('.creme-ckeditor-hidden').each(function() {
            var editor = $(this).data('ck-editor');
            if (editor) {
                editor.destroy();
            }
        });
    },

    createEditorHtml: function() {
        return (
            '<textarea class="ui-creme-widget ui-creme-ckeditor widget-auto" widget="ui-creme-ckeditor"></textarea>'
        );
    }
}));

QUnit.test('creme-ui-ckeditor', function(assert) {
    var element = $(this.createEditorHtml());
    var widget = creme.widget.create(element);

    this.assertActive(element);

    var editor = widget.editor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal(true, element.is('.creme-ckeditor-hidden'));
        equal(false, editor.isReadOnly());
        this.assertReady(element);
    });
});

QUnit.test('creme-ui-ckeditor (destroy)', function(assert) {
    var element = $(this.createEditorHtml());
    var widget = creme.widget.create(element);

    this.assertActive(element);

    var editor = widget.editor(element);

    this.awaitsPromise(editor.ckeditorSetup(), function() {
        equal(true, element.is('.creme-ckeditor-hidden'));
        equal(false, editor.isReadOnly());

        element.creme().widget().destroy();
        equal(false, element.is('.creme-ckeditor-hidden'));
    });
});

}(jQuery));
