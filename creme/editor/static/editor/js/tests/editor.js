/* globals QUnitWidgetMixin */

(function($) {

QUnit.module("creme.form.TinyMCEditor", new QUnitMixin(QUnitAjaxMixin,
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
        /*
        $('.creme-ckeditor-hidden').each(function() {
            var editor = $(this).data('ck-editor');
            if (editor) {
                editor.destroy();
            }
        });
        */
    },

    createEditorHtml: function() {
        return (
            '<textarea class="ui-creme-widget ui-creme-tinymceditor widget-auto" widget="ui-creme-tinymceditor">' +
            '</textarea>'
        );
    }
}));

}(jQuery));
