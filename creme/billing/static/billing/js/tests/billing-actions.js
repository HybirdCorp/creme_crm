/* global QUnitDetailViewMixin */

(function($) {

QUnit.module("creme.billing.brick.actions", new QUnitMixin(QUnitEventMixin,
                                                           QUnitAjaxMixin,
                                                           QUnitBrickMixin,
                                                           QUnitDialogMixin,
                                                           QUnitDetailViewMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;

        this.setMockBackendPOST({
            'mock/invoice/generatenumber/12': backend.response(200, ''),
            'mock/invoice/generatenumber/12/fail': backend.response(400, 'Unable to generate invoice number')
        });
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

QUnit.test('creme.billing.hatmenubar.export', function(assert) {
    var brick = this.createBrickWidget({
        classes: ['brick-hat-bar']
    }).brick();

    brick.action('billing-export', 'mock/export/12').start();

    deepEqual(['mock/export/12?format=pdf'], this.mockRedirectCalls());
});

QUnit.test('creme.billing.hatmenubar.invoice-number (fail)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: 'mock/invoice/generatenumber/12/fail',
                action: 'billing-hatmenubar-invoice-number'
            })
        ]
    });

    $(widget.element).find('a.menu_button').click();

    this.assertOpenedAlertDialog('Unable to generate invoice number');
    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/invoice/generatenumber/12'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.billing.hatmenubar.invoice-number (ok)', function(assert) {
    var current_url = window.location.href;
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: 'mock/invoice/generatenumber/12',
                action: 'billing-hatmenubar-invoice-number'
            })
        ]
    });

    $(widget.element).find('a.menu_button').click();

    this.assertClosedDialog();

    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/invoice/generatenumber/12'));
    deepEqual([current_url], this.mockRedirectCalls());
});

QUnit.test('creme.billing.hatmenubar.invoice-number (confirm, cancel)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: 'mock/invoice/generatenumber/12/fail',
                action: 'billing-hatmenubar-invoice-number',
                options: {
                    confirm: 'Are you sure ?'
                }
            })
        ]
    });

    $(widget.element).find('a.menu_button').click();

    this.assertOpenedConfirmDialog('Are you sure ?');
    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/invoice/generatenumber/12'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.billing.hatmenubar.invoice-number (confirm, fail)', function(assert) {
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: 'mock/invoice/generatenumber/12/fail',
                action: 'billing-hatmenubar-invoice-number',
                options: {
                    confirm: 'Are you sure ?'
                }
            })
        ]
    });

    $(widget.element).find('a.menu_button').click();

    this.assertOpenedConfirmDialog('Are you sure ?');
    this.acceptConfirmDialog();

    this.assertOpenedAlertDialog('Unable to generate invoice number');
    this.closeDialog();

    deepEqual([], this.mockBackendUrlCalls('mock/invoice/generatenumber/12'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.billing.hatmenubar.invoice-number (confirm, ok)', function(assert) {
    var current_url = window.location.href;
    var widget = this.createHatMenuBar({
        buttons: [
            this.createHatMenuActionButton({
                url: 'mock/invoice/generatenumber/12',
                action: 'billing-hatmenubar-invoice-number',
                options: {
                    confirm: 'Are you sure ?'
                }
            })
        ]
    });

    $(widget.element).find('a.menu_button').click();

    this.assertOpenedConfirmDialog('Are you sure ?');
    this.acceptConfirmDialog();

    this.assertClosedDialog();

    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/invoice/generatenumber/12'));
    deepEqual([current_url], this.mockRedirectCalls());
});

QUnit.test('creme.billing.generateInvoiceNumber', function(assert) {
    var current_url = window.location.href;

    creme.billing.generateInvoiceNumber('mock/invoice/generatenumber/12');

    this.assertClosedDialog();

    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/invoice/generatenumber/12'));
    deepEqual([current_url], this.mockRedirectCalls());
});

}(jQuery));
