/* globals QUnitSketchMixin */

(function($) {

QUnit.module("creme.D3GraphRelationChart", new QUnitMixin(QUnitSketchMixin));

QUnit.test('creme.D3GraphRelationChart (empty)', function(assert) {
    var chart = new creme.D3GraphRelationChart();
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);

    assert.deepEqual($.extend({drawOnResize: false}, chart.defaultProps), chart.props());
    assert.equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();
    chart.draw();

    assert.equal(1, sketch.svg().select('.d3-chart').size());
});

QUnit.test('creme.D3GraphRelationChart (asImage, empty)', function(assert) {
    var chart = new creme.D3GraphRelationChart();
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);

    var done = assert.async();

    setTimeout(function() {
        chart.asImage(function(image) {
            assert.equal(image.width, 300);
            assert.equal(image.height, 200);
            done();
        }, {width: 300, height: 200});
    });
});

QUnit.parametrize('creme.D3GraphRelationChart (hierarchy)', [
    [[], {nodes: [], types: [], edges: []}],
    // root nodes without edges
    [
        [
            {id: 'node-a', label: 'Node A', url: '/mock/nodes/node-a'},
            {id: 'node-b', label: 'Node B', url: '/mock/nodes/node-b'}
        ],
        {
            nodes: [
                {id: 'node-a', edgeCount: 0, data: {label: 'Node A', url: '/mock/nodes/node-a'}},
                {id: 'node-b', edgeCount: 0, data: {label: 'Node B', url: '/mock/nodes/node-b'}}
            ],
            types: [],
            edges: []
        }
    ],
    // root nodes with a single type of edges
    [
        [
            {id: 'node-a', label: 'Node A', url: '/mock/nodes/node-a'},
            {id: 'node-b', label: 'Node B', url: '/mock/nodes/node-b'},
            {id: 'child-a1', label: 'Node A1', url: '/mock/nodes/child-a1', parent: 'node-a', relation: {id: 'rtype-1', label: 'is 1 related'}},
            {id: 'child-a2', label: 'Node A2', url: '/mock/nodes/child-a2', parent: 'node-a', relation: {id: 'rtype-1', label: 'is 1 related'}},
            {id: 'child-b1', label: 'Node B1', url: '/mock/nodes/child-b1', parent: 'node-b', relation: {id: 'rtype-1', label: 'is 1 related'}}
        ],
        {
            nodes: [
                {id: 'node-a', edgeCount: 2, data: {label: 'Node A', url: '/mock/nodes/node-a'}},
                {id: 'node-b', edgeCount: 1, data: {label: 'Node B', url: '/mock/nodes/node-b'}},
                {id: 'child-a1', edgeCount: 1, data: {label: 'Node A1', url: '/mock/nodes/child-a1'}},
                {id: 'child-a2', edgeCount: 1, data: {label: 'Node A2', url: '/mock/nodes/child-a2'}},
                {id: 'child-b1', edgeCount: 1, data: {label: 'Node B1', url: '/mock/nodes/child-b1'}}
            ],
            types: [
                {id: 'rtype-1', label: 'is 1 related'}
            ],
            edges: [
                {
                    source: 'node-a',
                    target: 'child-a1',
                    data: {id: 'child-a1', label: 'Node A1', url: '/mock/nodes/child-a1', parent: 'node-a', relation: {id: 'rtype-1', label: 'is 1 related'}}
                },
                {
                    source: 'node-a',
                    target: 'child-a2',
                    data: {id: 'child-a2', label: 'Node A2', url: '/mock/nodes/child-a2', parent: 'node-a', relation: {id: 'rtype-1', label: 'is 1 related'}}
                },
                {
                    source: 'node-b',
                    target: 'child-b1',
                    data: {id: 'child-b1', label: 'Node B1', url: '/mock/nodes/child-b1', parent: 'node-b', relation: {id: 'rtype-1', label: 'is 1 related'}}
                }
            ]
        }
    ],
    // root nodes with multiple edge types
    [
        [
            {id: 'node-a', label: 'Node A', url: '/mock/nodes/node-a'},
            {id: 'node-b', label: 'Node B', url: '/mock/nodes/node-b'},
            {id: 'child-a1', label: 'Node A1', url: '/mock/nodes/child-a1', parent: 'node-a', relation: {id: 'rtype-1', label: 'is 1 related'}},
            {id: 'child-a2', label: 'Node A2', url: '/mock/nodes/child-a2', parent: 'node-a', relation: {id: 'rtype-2', label: 'is 2 related'}},
            {id: 'child-b1', label: 'Node B1', url: '/mock/nodes/child-b1', parent: 'node-b', relation: {id: 'rtype-3', label: 'is 3 related'}}
        ],
        {
            nodes: [
                {id: 'node-a', edgeCount: 2, data: {label: 'Node A', url: '/mock/nodes/node-a'}},
                {id: 'node-b', edgeCount: 1, data: {label: 'Node B', url: '/mock/nodes/node-b'}},
                {id: 'child-a1', edgeCount: 1, data: {label: 'Node A1', url: '/mock/nodes/child-a1'}},
                {id: 'child-a2', edgeCount: 1, data: {label: 'Node A2', url: '/mock/nodes/child-a2'}},
                {id: 'child-b1', edgeCount: 1, data: {label: 'Node B1', url: '/mock/nodes/child-b1'}}
            ],
            types: [
                {id: 'rtype-1', label: 'is 1 related'},
                {id: 'rtype-2', label: 'is 2 related'},
                {id: 'rtype-3', label: 'is 3 related'}
            ],
            edges: [
                {
                    source: 'node-a',
                    target: 'child-a1',
                    data: {id: 'child-a1', label: 'Node A1', url: '/mock/nodes/child-a1', parent: 'node-a', relation: {id: 'rtype-1', label: 'is 1 related'}}
                },
                {
                    source: 'node-a',
                    target: 'child-a2',
                    data: {id: 'child-a2', label: 'Node A2', url: '/mock/nodes/child-a2', parent: 'node-a', relation: {id: 'rtype-2', label: 'is 2 related'}}
                },
                {
                    source: 'node-b',
                    target: 'child-b1',
                    data: {id: 'child-b1', label: 'Node B1', url: '/mock/nodes/child-b1', parent: 'node-b', relation: {id: 'rtype-3', label: 'is 3 related'}}
                }
            ]
        }
    ],
    // root nodes sharing children
    [
        [
            {id: 'node-a', label: 'Node A', url: '/mock/nodes/node-a'},
            {id: 'node-b', label: 'Node B', url: '/mock/nodes/node-b'},
            {id: 'child-ab', label: 'Node AB', url: '/mock/nodes/child-ab', parent: 'node-a', relation: {id: 'rtype-1', label: 'is 1 related'}},
            {id: 'child-ab', label: 'Node AB', url: '/mock/nodes/child-ab', parent: 'node-b', relation: {id: 'rtype-1', label: 'is 1 related'}}
        ],
        {
            nodes: [
                {id: 'node-a', edgeCount: 1, data: {label: 'Node A', url: '/mock/nodes/node-a'}},
                {id: 'node-b', edgeCount: 1, data: {label: 'Node B', url: '/mock/nodes/node-b'}},
                {id: 'child-ab', edgeCount: 2, data: {label: 'Node AB', url: '/mock/nodes/child-ab'}}
            ],
            types: [
                {id: 'rtype-1', label: 'is 1 related'}
            ],
            edges: [
                {
                    source: 'node-a',
                    target: 'child-ab',
                    data: {id: 'child-ab', label: 'Node AB', url: '/mock/nodes/child-ab', parent: 'node-a', relation: {id: 'rtype-1', label: 'is 1 related'}}
                },
                {
                    source: 'node-b',
                    target: 'child-ab',
                    data: {id: 'child-ab', label: 'Node AB', url: '/mock/nodes/child-ab', parent: 'node-b', relation: {id: 'rtype-1', label: 'is 1 related'}}
                }
            ]
        }
    ],
    // both root and child node
    [
        [
            {id: 'node-a', label: 'Node A', url: '/mock/nodes/node-a'},
            {id: 'node-b', label: 'Node B', url: '/mock/nodes/node-b'},
            {id: 'child-ab', label: 'Node AB', url: '/mock/nodes/child-ab', parent: 'node-a', relation: {id: 'rtype-1', label: 'is 1 related'}},
            {id: 'child-ab', label: 'Node AB', url: '/mock/nodes/child-ab', parent: 'node-b', relation: {id: 'rtype-1', label: 'is 1 related'}},
            {id: 'node-a', label: 'Node A', url: '/mock/nodes/node-a', parent: 'child-ab', relation: {id: 'rtype-2', label: 'is 2 related'}}
        ],
        {
            nodes: [
                {id: 'node-a', edgeCount: 2, data: {label: 'Node A', url: '/mock/nodes/node-a'}},
                {id: 'node-b', edgeCount: 1, data: {label: 'Node B', url: '/mock/nodes/node-b'}},
                {id: 'child-ab', edgeCount: 3, data: {label: 'Node AB', url: '/mock/nodes/child-ab'}}
            ],
            types: [
                {id: 'rtype-1', label: 'is 1 related'},
                {id: 'rtype-2', label: 'is 2 related'}
            ],
            edges: [
                {
                    source: 'node-a',
                    target: 'child-ab',
                    data: {id: 'child-ab', label: 'Node AB', url: '/mock/nodes/child-ab', parent: 'node-a', relation: {id: 'rtype-1', label: 'is 1 related'}}
                },
                {
                    source: 'node-b',
                    target: 'child-ab',
                    data: {id: 'child-ab', label: 'Node AB', url: '/mock/nodes/child-ab', parent: 'node-b', relation: {id: 'rtype-1', label: 'is 1 related'}}
                },
                {
                    source: 'child-ab',
                    target: 'node-a',
                    data: {id: 'node-a', label: 'Node A', url: '/mock/nodes/node-a', parent: 'child-ab', relation: {id: 'rtype-2', label: 'is 2 related'}}
                }
            ]
        }
    ]
], function(data, expected, assert) {
    var chart = new creme.D3GraphRelationChart();
    assert.deepEqual(chart.hierarchy(data), expected);
});

QUnit.parametrize('creme.D3GraphRelationChart (draw)', [
    [
        [],
        {
            '.graphs-relation-chart .graph-edge': 0,
            '.graphs-relation-chart .graph-node': 0,
            '.legend .legend-item': 0
        }
    ], [
        [
            {id: 'node-a', label: 'Node A', url: '/mock/nodes/node-a'},
            {id: 'node-b', label: 'Node B', url: '/mock/nodes/node-b'},
            {id: 'child-ab', label: 'Node AB', url: '/mock/nodes/child-ab', parent: 'node-a', relation: {id: 'rtype-1', label: 'is 1 related'}},
            {id: 'child-ab', label: 'Node AB', url: '/mock/nodes/child-ab', parent: 'node-b', relation: {id: 'rtype-1', label: 'is 1 related'}},
            {id: 'node-a', label: 'Node A', url: '/mock/nodes/node-a', parent: 'child-ab', relation: {id: 'rtype-2', label: 'is 2 related'}},
            {id: 'child-a1', label: 'Node A1', url: '/mock/nodes/child-a1', parent: 'node-a', relation: {id: 'rtype-1', label: 'is 1 related'}},
            {id: 'child-a2', label: 'Node A2', url: '/mock/nodes/child-a2', parent: 'node-a', relation: {id: 'rtype-3', label: 'is 3 related'}}
        ],
        {
            '.graphs-relation-chart .graph-edge': 5,
            '.graphs-relation-chart .graph-node': 5,
            '.legend .legend-item': 3
        }
    ]
], function(data, expected, assert) {
    var chart = new creme.D3GraphRelationChart({transition: false});
    var sketch = new creme.D3Sketch().bind($('<div>'));

    chart.sketch(sketch);
    chart.model(data);

    assert.equal(0, sketch.svg().select('.d3-chart').size());

    chart.draw();

    assert.equal(1, sketch.svg().select('.d3-chart').size());

    this.assertD3Nodes(sketch.svg(), expected);
});

}(jQuery));
