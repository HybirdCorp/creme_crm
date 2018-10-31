(function($) {

QUnit.module("creme.billing.brick.actions", new QUnitMixin(QUnitEventMixin,
                                                          QUnitAjaxMixin,
                                                          QUnitBrickMixin,
                                                          QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;
    },

    createBillingBrickTable: function(options) {
        options = $.extend({
            classes: ['billing-lines-brick']
        }, options || {});

        return this.createBrickTable(options);
    }
}));

QUnit.test('creme.billing.brick (available actions)', function(assert) {
    var brick = this.createBillingBrickTable().brick();

    equal(true, Object.isSubClassOf(brick.action('billing-line-addonfly'), creme.component.Action));
    equal(true, Object.isSubClassOf(brick.action('billing-line-saveall'), creme.component.Action));
    equal(true, Object.isSubClassOf(brick.action('billing-line-clearonfly'), creme.component.Action));
});


QUnit.test('creme.billing.exportAs (single format)', function(assert) {
    creme.billing.exportAs('mock/export/12');

    this.assertClosedDialog();

    deepEqual(['mock/export/12?format=pdf'], this.mockRedirectCalls());
});

QUnit.test('creme.billing.exportAs (multiple formats, choose one)', function(assert) {
    creme.billing.exportAs('mock/export/12', [{value: 'pdf'}, {value: 'html'}, {value: 'xml'}]);

    this.assertOpenedDialog();

    $('.ui-dialog select').val('html');
    this.acceptConfirmDialog();

    deepEqual(['mock/export/12?format=html'], this.mockRedirectCalls());
});

}(jQuery));
