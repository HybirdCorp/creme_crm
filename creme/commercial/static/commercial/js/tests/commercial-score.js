(function($) {

QUnit.module("creme.commercial.assets", new QUnitMixin(QUnitEventMixin,
                                                       QUnitAjaxMixin,
                                                       QUnitDialogMixin,
                                                       QUnitBrickMixin, {
    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendPOST({
            'mock/score/fail': backend.response(400, 'Unable to save score'),
            'mock/score': backend.response(200, 'Score saved')
        });
    },

    createAssetsMatrixBrick: function(options) {
        options = $.extend({
            id: 'commercial-test_assets',
            classes: ['assets-matrix'],
            columns: [
                '<th>segment A</th>'
            ],
            rows: [
                '<tr><td><select><option value="2.5"></option></select></td></tr>'
            ]
        }, options || {});

        return this.createBrickTable(options);
    }
}));

QUnit.test('creme.commercial.setScore (failed)', function(assert) {
    var brick = this.createAssetsMatrixBrick().brick();
    var select = brick.element().find('select');

    creme.commercial.setScore(select, 'mock/score/fail', 12, 5, 8);

    this.assertOpenedAlertDialog("Unable to save score");
    this.closeDialog();

    assert.deepEqual([
        ['POST', {
            score:           '2.5',
            model_id:        12,
            segment_desc_id: 5,
            orga_id:         8
        }]
    ], this.mockBackendUrlCalls('mock/score/fail'));

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.commercial.setScore (ok)', function(assert) {
    var brick = this.createAssetsMatrixBrick().brick();
    var select = brick.element().find('select');

    creme.commercial.setScore(select, 'mock/score', 12, 5, 8);

    this.assertClosedDialog();

    assert.deepEqual([
        ['POST', {
            score:           '2.5',
            model_id:        12,
            segment_desc_id: 5,
            orga_id:         8
        }]
    ], this.mockBackendUrlCalls('mock/score'));

    assert.deepEqual([
        ['GET', {"brick_id": ["commercial-test_assets"], "extra_data": "{}"}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

}(jQuery));
