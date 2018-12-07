/* global QUnitConsoleMixin */

(function($) {

QUnit.module("creme.widget.utils.js", new QUnitMixin(QUnitConsoleMixin));

QUnit.test('creme.utils.JSON.encode (null)', function(assert) {
    var codec = new creme.utils.JSON();

    equal("null", codec.encode(null));
});

QUnit.test('creme.utils.JSON.encode', function(assert) {
    var codec = new creme.utils.JSON();

    equal(codec.encode('test'), '"test"');
    equal(codec.encode(12), '12');
    equal(codec.encode(['a', 12, 'c', null, undefined]), '["a",12,"c",null,null]');
    equal(codec.encode({'a': ['a', 'b', 150],
                        'b': 'test',
                        'c': 12
                       }), '{"a":["a","b",150],"b":"test","c":12}');

    var encoder = creme.utils.JSON.encoder();

    equal(encoder('test'), '"test"');
    equal(encoder(12), '12');
    equal(encoder(['a', 12, 'c', null, undefined]), '["a",12,"c",null,null]');
    equal(encoder({'a': ['a', 'b', 150],
                   'b': 'test',
                   'c': 12
                  }), '{"a":["a","b",150],"b":"test","c":12}');
});

QUnit.test('creme.utils.JSON.decode (null)', function(assert) {
    var codec = new creme.utils.JSON();

    QUnit.assert.raises(function() { codec.decode(null); });
});

QUnit.test('creme.utils.JSON.decode (invalid)', function(assert) {
    var codec = new creme.utils.JSON();

    QUnit.assert.raises(function() { codec.decode('{"a\':1}'); });
    QUnit.assert.raises(function() { codec.decode('{"a":1,}'); });
    QUnit.assert.raises(function() { codec.decode('{a:1}'); });

    var decoder = creme.utils.JSON.decoder();

    QUnit.assert.raises(function() { decoder('{"a\':1}'); });
    QUnit.assert.raises(function() { decoder('{"a":1,}'); });
    QUnit.assert.raises(function() { decoder('{a:1}'); });
});

QUnit.test('creme.utils.JSON.decode (invalid or null, default)', function(assert) {
    var codec = new creme.utils.JSON();

    equal(codec.decode('{"a\':1}', 'fail'), 'fail');
    equal(codec.decode('{"a":1,}', 'fail'), 'fail');
    equal(codec.decode('{a:1}', 'fail'), 'fail');
    equal(codec.decode(null, 'fail'), 'fail');

    var decoder = creme.utils.JSON.decoder('default');

    equal(decoder('{"a\':1}'), 'default');
    equal(decoder('{"a":1,}'), 'default');
    equal(decoder('{a:1}'), 'default');
    equal(decoder(null), 'default');

    equal(decoder('{"a\':1}', 'fail'), 'fail');
    equal(decoder('{"a":1,}', 'fail'), 'fail');
    equal(decoder('{a:1}', 'fail'), 'fail');
    equal(decoder(null, 'fail'), 'fail');
});

QUnit.test('creme.utils.JSON.decode (valid)', function(assert) {
    var codec = new creme.utils.JSON();

    deepEqual(codec.decode('{"a":1, "b":true, "c":[1, 2, 3]}'), {a: 1, b: true, c: [1, 2, 3]});

    var decoder = creme.utils.JSON.decoder();

    deepEqual(decoder('{"a":1, "b":true, "c":[1, 2, 3]}'), {a: 1, b: true, c: [1, 2, 3]});
});

QUnit.test('creme.utils.JSON.clean', function(assert) {
    var clean = creme.utils.JSON.clean;

    QUnit.assert.raises(function() { clean('{"a\':1}'); });
    equal(clean('{"a\':1}', 'default'), 'default');

    equal(clean(null), null);
    equal(clean(null, 'default'), null);

    deepEqual(clean('{"a":1}'), {a: 1});
    deepEqual(clean({a: 1}), {a: 1});
});

QUnit.test('creme.utils.comparator (simple)', function(assert) {
    var compare = creme.utils.comparator();

    deepEqual(compare, creme.utils.compareTo);

    equal(0, compare(12, 12));
    equal(0, compare(4.57, 4.57));
    equal(0, compare('test', 'test'));

    equal(-1, compare(12, 13));
    equal(-1, compare(4.57, 5.57));
    equal(-1, compare('da test', 'test'));

    equal(1, compare(13, 12));
    equal(1, compare(5.57, 4.57));
    equal(1, compare('test', 'da test'));
});

QUnit.test('creme.utils.comparator (key)', function(assert) {
    var compare = creme.utils.comparator('value');

    equal(0, compare({value: 12}, {value: 12}));
    equal(0, compare({value: 4.57}, {value: 4.57}));
    equal(0, compare({value: 'test'}, {value: 'test'}));

    equal(-1, compare({value: 12}, {value: 13}));
    equal(-1, compare({value: 4.57}, {value: 5.57}));
    equal(-1, compare({value: 'da test'}, {value: 'test'}));

    equal(1, compare({value: 13}, {value: 12}));
    equal(1, compare({value: 5.57}, {value: 4.57}));
    equal(1, compare({value: 'test'}, {value: 'da test'}));
});

QUnit.test('creme.utils.comparator (multiple keys)', function(assert) {
    var compare = creme.utils.comparator('value', 'index');

    equal(0, compare({value: 12, index: 0}, {value: 12, index: 0}));

    equal(1, compare({value: 12, index: 1}, {value: 12, index: 0}));
    equal(1, compare({value: 13, index: 0}, {value: 12, index: 1}));

    equal(-1, compare({value: 12, index: 0}, {value: 12, index: 1}));
    equal(-1, compare({value: 12, index: 1}, {value: 13, index: 0}));
});

QUnit.test('creme.utils.isHTMLDataType', function(assert) {
    equal(creme.utils.isHTMLDataType('html'), true);
    equal(creme.utils.isHTMLDataType('text/html'), true);
    equal(creme.utils.isHTMLDataType('HTML'), true);
    equal(creme.utils.isHTMLDataType('json'), false);

    equal(creme.utils.isHTMLDataType(''), false);
    equal(creme.utils.isHTMLDataType(), false);
    equal(creme.utils.isHTMLDataType(null), false);
    equal(creme.utils.isHTMLDataType(false), false);
    equal(creme.utils.isHTMLDataType(12), false);
});

QUnit.test('creme.utils.JSON.readScriptText', function(assert) {
    equal('', creme.utils.JSON.readScriptText(''));

    this.resetMockConsoleWarnCalls();

    // wrong element type
    var invalidTag = $('<div>This not a script</div>');
    equal('', creme.utils.JSON.readScriptText(invalidTag));

    deepEqual([['This element is not a JSON script']],
              this.mockConsoleWarnCalls().map(function(e) { return e.slice(0, 1); }));

    this.resetMockConsoleWarnCalls();

    // wrong script type
    invalidTag = $('<script type="application/csv">{}</script>');
    equal('', creme.utils.JSON.readScriptText(invalidTag));

    deepEqual([['This element is not a JSON script']],
            this.mockConsoleWarnCalls().map(function(e) { return e.slice(0, 1); }));

    equal('', creme.utils.JSON.readScriptText('<script type="text/json"></script>'));
    equal('', creme.utils.JSON.readScriptText('<script type="text/json"><!-- --></script>'));
    equal('', creme.utils.JSON.readScriptText('<script type="text/json"><!-- -->\n</script>'));

    this.resetMockConsoleWarnCalls();

    equal('<!-- ->', creme.utils.JSON.readScriptText('<script type="text/json"><!-- -></script>'));
    deepEqual([['Please use html comment <!-- --> within JSON <script> tag to prevent some browsers to interpret it as javascript']],
              this.mockConsoleWarnCalls());

    this.resetMockConsoleWarnCalls();

    equal('<!--', creme.utils.JSON.readScriptText('<script type="text/json"><!--</script>'));
    deepEqual([['Please use html comment <!-- --> within JSON <script> tag to prevent some browsers to interpret it as javascript']],
              this.mockConsoleWarnCalls());

    this.resetMockConsoleWarnCalls();

    equal('-->', creme.utils.JSON.readScriptText('<script type="text/json">--></script>'));
    deepEqual([['Please use html comment <!-- --> within JSON <script> tag to prevent some browsers to interpret it as javascript']],
              this.mockConsoleWarnCalls());

    this.resetMockConsoleWarnCalls();

    equal('{}', creme.utils.JSON.readScriptText('<script type="text/json">{}</script>'));
    deepEqual([['Please use html comment <!-- --> within JSON <script> tag to prevent some browsers to interpret it as javascript']],
              this.mockConsoleWarnCalls());

    equal('{}', creme.utils.JSON.readScriptText('<script type="text/json"><!-- {} --></script>'));
    equal('{}', creme.utils.JSON.readScriptText('<script type="text/json">\n<!-- {} -->\n\n</script>'));

    equal('{}', creme.utils.JSON.readScriptText('<script type="application/json"><!-- {} --></script>'));
    equal('{}', creme.utils.JSON.readScriptText('<script type="application/json">\n<!-- {} -->\n\n</script>'));

    equal('{"a": 12, "b": "-->alert();<script/>"}', creme.utils.JSON.readScriptText('<script type="application/json">\n<!-- {"a": 12, "b": "--\\u003ealert();\\u003cscript/\\u003e"} -->\n\n</script>'));
});

QUnit.test('creme.utils.JSON.readScriptText (ignore empty)', function(assert) {
    equal('', creme.utils.JSON.readScriptText(''));

    deepEqual([['No such JSON script element']],
              this.mockConsoleWarnCalls().map(function(e) { return e.slice(0, 1); }));

    this.resetMockConsoleWarnCalls();
    equal('', creme.utils.JSON.readScriptText($('script.unknown')));

    deepEqual([['No such JSON script element']],
              this.mockConsoleWarnCalls().map(function(e) { return e.slice(0, 1); }));

    this.resetMockConsoleWarnCalls();

    equal('', creme.utils.JSON.readScriptText('', {ignoreEmpty: true}));
    deepEqual([], this.mockConsoleWarnCalls());

    equal('', creme.utils.JSON.readScriptText($('script.unknown'), {ignoreEmpty: true}));
    deepEqual([], this.mockConsoleWarnCalls());
});

}(jQuery));
