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
            'mock/billing/saveall': backend.response(200, ''),
            'mock/billing/saveall/fail': backend.response(400, 'Unable to save lines'),
            'mock/invoice/generatenumber/12': backend.response(200, ''),
            'mock/invoice/generatenumber/12/fail': backend.response(400, 'Unable to generate invoice number')
        });

        this.brickActionListeners = {
            start: this.mockListener('action-start'),
            cancel: this.mockListener('action-cancel'),
            fail: this.mockListener('action-fail'),
            done: this.mockListener('action-done')
        };
    },

    createBillingLineHtml: function(options, index) {
        var renderInput = function(options) {
            options = $.extend({
                validator: "Decimal"
            }, options || {});

            return (
                '<td class="bline-${name}">' +
                     '<input type="text" value="${value}" validator="${validator}"' +
                           ' name="product_line_formset-${index}-${name}" id="product_line_formset-${index}-${name}">' +
                     '</input>' +
                '</td>').template({
                    value: options.value,
                    name: options.name,
                    index: index,
                    validator: options.validator
                });
        };

        return (
           '<div class="bline-container ${classes} ${hidden}">' +
                '<div class="bline-buttons ${deletion}"></div>' +
                '<div class="bline-fields">' +
                    '<table class="linetable"><tr class="content">${inputs}</tr></table>' +
                '</div>' +
           '</div>').template({
               inputs: (options.inputs || []).map(renderInput).join(''),
               classes: (options.classes || []).join(' '),
               deletion: options.deleted ? 'bline-deletion-mark' : ''
           });
    },

    createBillingBrick: function(options) {
        options = $.extend({
            classes: ['billing-lines-brick'],
            ctype: '86'
        }, options || {});

        var header = (
            '<div class="brick-header-buttons">${buttons}</div>'
        ).template({
            buttons: (options.buttons || []).map(this.createBrickActionHtml.bind(this)).join('')
        });

        var content = (
            '<div class="bline-content">' +
                '<div class="bline-form" ct_id="${ctype}" id="form_id_${ctype}">${lines}</div>' +
            '</div>').template({
                lines: (options.lines || []).map(this.createBillingLineHtml.bind(this)).join(''),
                ctype: options.ctype
            });

        return this.createBrickWidget({
            classes: options.classes,
            content: content,
            header: header
        });
    }
}));

QUnit.test('creme.billing.brick (available actions)', function(assert) {
    var brick = this.createBillingBrick().brick();

    equal(true, Object.isSubClassOf(brick.action('billing-line-addonfly'), creme.component.Action));
    equal(true, Object.isSubClassOf(brick.action('billing-line-saveall'), creme.component.Action));
    equal(true, Object.isSubClassOf(brick.action('billing-line-clearonfly'), creme.component.Action));
});

QUnit.test('creme.billing.brick (billing-line-saveall, invalid input)', function(assert) {
    var brick = this.createBillingBrick({
        lines: [
            {inputs: [{name: 'quantity', value: 1}, {name: 'product', value: '', validator: 'Value'}]}
        ]
    }).brick();

    ok(creme.billing.formsHaveErrors());

    brick.action('billing-line-saveall', 'mock/billing/saveall').on(this.brickActionListeners).start();

    this.assertOpenedAlertDialog(gettext('There are some errors in your lines.'));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/billing/saveall'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.billing.brick (billing-line-saveall, invalid response)', function(assert) {
    var brick = this.createBillingBrick({
        lines: [
            {inputs: [{name: 'quantity', value: 1}, {name: 'product', value: '', validator: 'Value'}]}
        ]
    }).brick();

    brick.element().find('#product_line_formset-0-quantity').val('5').change();
    brick.element().find('#product_line_formset-0-product').val('Product #1').change();

    equal(false, creme.billing.formsHaveErrors());

    brick.action('billing-line-saveall', 'mock/billing/saveall/fail').on(this.brickActionListeners).start();

    deepEqual([
        ['POST', {
            '86': $.toJSON({'product_line_formset-0-quantity': '5', 'product_line_formset-0-product': 'Product #1'})
         }]
    ], this.mockBackendUrlCalls('mock/billing/saveall/fail'));

    this.assertOpenedAlertDialog('Unable to save lines');
    this.closeDialog();

    deepEqual([['fail', 'Unable to save lines']], this.mockListenerCalls('action-fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.billing.brick (billing-line-saveall, ok)', function(assert) {
    var brick = this.createBillingBrick({
        lines: [
            {inputs: [{name: 'quantity', value: 1}, {name: 'product', value: '', validator: 'Value'}]}
        ]
    }).brick();

    brick.element().find('#product_line_formset-0-quantity').val('5').change();
    brick.element().find('#product_line_formset-0-product').val('Product #1').change();

    equal(false, creme.billing.formsHaveErrors());

    brick.action('billing-line-saveall', 'mock/billing/saveall').on(this.brickActionListeners).start();

    deepEqual([
        ['POST', {
            '86': $.toJSON({'product_line_formset-0-quantity': '5', 'product_line_formset-0-product': 'Product #1'})
         }]
    ], this.mockBackendUrlCalls('mock/billing/saveall'));

    this.assertClosedDialog();

    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([
        ['GET', {"brick_id": ["brick-for-test"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.billing.brick (billing-line-addonfly)', function(assert) {
    var brick = this.createBillingBrick({
        buttons: [{
                classes: ['brick-header-button action-type-add'],
                action: 'billing-line-addonfly',
                data: {ctype_id: 86, prefix: "product_line_formset", count: 1}
            }],
        lines: [{
                inputs: [{name: 'quantity', value: 1}, {name: 'product', value: 'Product #1', validator: 'Value'}]
            }, {
                inputs: [{name: 'quantity', value: 1}, {name: 'product', value: '', validator: 'Value'}],
                classes: ['hidden-form empty_form_${ctype} empty_form_inputs_${ctype}'.template({ctype: 86})]
            }]
    }).brick();

    var addonflyLink = brick.element().find('[data-action="billing-line-addonfly"]');

    equal(false, creme.billing.formsHaveErrors());
    equal(1, brick.element().find('.hidden-form').length);
    equal(false, addonflyLink.is('.forbidden'));

    addonflyLink.click();

    equal(true, creme.billing.formsHaveErrors());
    equal(0, brick.element().find('.hidden-form').length);
    equal(true, addonflyLink.is('.forbidden'));
});

QUnit.test('creme.billing.brick (billing-line-addonfly, forbidden)', function(assert) {
    var brick = this.createBillingBrick({
        buttons: [{
                classes: ['brick-header-button action-type-add forbidden'],
                action: 'billing-line-addonfly',
                data: {ctype_id: 86, prefix: "product_line_formset", count: 1}
            }],
        lines: [{
                inputs: [{name: 'quantity', value: 1}, {name: 'product', value: 'Product #1', validator: 'Value'}]
            }, {
                inputs: [{name: 'quantity', value: 1}, {name: 'product', value: '', validator: 'Value'}],
                classes: ['hidden-form empty_form_${ctype} empty_form_inputs_${ctype}'.template({ctype: 86})]
            }]
    }).brick();

    var addonflyLink = brick.element().find('[data-action="billing-line-addonfly"]');

    equal(false, creme.billing.formsHaveErrors());
    equal(1, brick.element().find('.hidden-form').length);
    equal(true, addonflyLink.is('.forbidden'));

    addonflyLink.click();

    equal(false, creme.billing.formsHaveErrors());
    equal(1, brick.element().find('.hidden-form').length);
    equal(true, addonflyLink.is('.forbidden'));
});

QUnit.test('creme.billing.exportAs (single format)', function(assert) {
    creme.billing.exportAs('mock/export/12');

    this.assertClosedDialog();

    deepEqual(['/mock/export/12?format=pdf'], this.mockRedirectCalls());
});

QUnit.test('creme.billing.exportAs (multiple formats, choose one)', function(assert) {
    creme.billing.exportAs('mock/export/12', [{value: 'pdf'}, {value: 'html'}, {value: 'xml'}]);

    this.assertOpenedDialog();

    $('.ui-dialog select').val('html');
    this.acceptConfirmDialog();

    deepEqual(['/mock/export/12?format=html'], this.mockRedirectCalls());
});

QUnit.test('creme.billing.hatmenubar.export', function(assert) {
    var brick = this.createBrickWidget({
        classes: ['brick-hat-bar']
    }).brick();

    brick.action('billing-export', 'mock/export/12').start();

    deepEqual(['/mock/export/12?format=pdf'], this.mockRedirectCalls());
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
    deepEqual([current_url], this.mockReloadCalls());
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
    deepEqual([], this.mockReloadCalls());
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
    deepEqual([current_url], this.mockReloadCalls());
});

QUnit.test('creme.billing.generateInvoiceNumber', function(assert) {
    var current_url = window.location.href;

    creme.billing.generateInvoiceNumber('mock/invoice/generatenumber/12');

    this.assertClosedDialog();

    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/invoice/generatenumber/12'));
    deepEqual([current_url], this.mockReloadCalls());
});

}(jQuery));
