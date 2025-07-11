(function($) {
QUnit.module("creme.utils.template.js", new QUnitMixin());

QUnit.test('creme.utils.TemplateRenderer (constructor)', function(assert) {
    var renderer = new creme.utils.TemplateRenderer();
    assert.deepEqual([], renderer.tags('${a}'));
    assert.deepEqual('${a}', renderer.render('${a}', {a: 12}));
});

QUnit.test('creme.utils.Template (constructor)', function(assert) {
    var template = new creme.utils.Template();
    assert.equal(undefined, template.pattern());
    assert.deepEqual(undefined, template.parameters());
    assert.equal('object', typeof template.renderer());

    template = new creme.utils.Template('this is a ${object}', {object: 'backpipe'});
    assert.equal('this is a ${object}', template.pattern());
    assert.deepEqual({object: 'backpipe'}, template.parameters());
    assert.equal('object', typeof template.renderer());
});

QUnit.test('creme.utils.Template (tags)', function(assert) {
    var template = new creme.utils.Template();
    assert.deepEqual([], template.tags());

    template.pattern('${tag} ${tag2} ${last_tag}');
    assert.deepEqual(['tag', 'tag2', 'last_tag'], template.tags());

    template.pattern('${tag} ${tag2} ${{{last_tag}');
    assert.deepEqual(['tag', 'tag2'], template.tags());

    template.pattern('${tag} ${tag2} ${{last_tag}}');
    assert.deepEqual(['tag', 'tag2'], template.tags());

    template.pattern('${tag} ${tag2} $last_tag}');
    assert.deepEqual(['tag', 'tag2'], template.tags());

    template.pattern('${tag} ${tag2} ${last_tag toto');
    assert.deepEqual(['tag', 'tag2'], template.tags());

    template.pattern('${tag} ${tag2} ${last tag}');
    assert.deepEqual(['tag', 'tag2'], template.tags());

    template.pattern('${tag} ${tag2} {last_tag}');
    assert.deepEqual(['tag', 'tag2'], template.tags());

    template.pattern('${tag.id} ${tag.name}');
    assert.deepEqual(['tag'], template.tags());
});

QUnit.test('creme.utils.Template (render, empty data)', function(assert) {
    var template = new creme.utils.Template('this is a template');
    assert.equal('this is a template', template.render());

    template.pattern('${tag} ${tag2} ${last_tag}');
    assert.equal('${tag} ${tag2} ${last_tag}', template.render());
});

QUnit.test('creme.utils.Template (render, empty pattern)', function(assert) {
    var template = new creme.utils.Template('', {tag: 12});
    assert.equal('', template.render());

    template.pattern(null);
    assert.equal(null, template.render());
});

QUnit.test('creme.utils.Template (render, dict)', function(assert) {
    var data = {tag: 12,
                tag2: 'string',
                last_tag: {toString: function() { return 'yo'; }}};

    var template = new creme.utils.Template('this is a template', data);
    assert.equal('this is a template', template.render());

    template.pattern('${tag} ${tag2} ${last_tag}');
    assert.equal('12 string yo', template.render());

    data.tag2 = undefined;
    assert.equal('12 ${tag2} yo', template.render());

    data.tag3 = 'string3';
    assert.equal('12 ${tag2} yo', template.render());

    assert.equal('12 ${tag2} extra_yo', template.render({last_tag: 'extra_yo'}));
    assert.equal('12 ${tag2} yo', template.render({tag3: 'extra_string3'}));
});

QUnit.test('creme.utils.Template (render, array)', function(assert) {
    var data = [12, 13, 14];

    var template = new creme.utils.Template('this is a template', data);

    assert.equal(true, template.iscomplete());
    assert.equal('this is a template', template.render());

    template.pattern('${0} ${1} ${2}');

    assert.equal(true, template.iscomplete());
    assert.equal('12 13 14', template.render());

    template.pattern('${0} ${1} ${3}');

    assert.equal(false, template.iscomplete());
    assert.equal('12 13 ${3}', template.render());
});

QUnit.test('creme.utils.Template (render, function)', function(assert) {
    var data = function(key) { return key + "_rendered"; };
    var extra = function(key) { return key + "_extra"; };

    var template = new creme.utils.Template('this is a template', data);

    assert.equal(true, template.iscomplete());
    assert.equal('this is a template', template.render());

    template.pattern('${tag} ${tag2} ${last_tag}');

    assert.equal(true, template.iscomplete());
    assert.equal('tag_rendered tag2_rendered last_tag_rendered', template.render());

    template.pattern('${tag} ${tag2} ${last_tag} ${last_tag2}');

    assert.equal(true, template.iscomplete());
    assert.equal('tag_rendered tag2_rendered last_tag_rendered last_tag2_rendered', template.render());

    assert.equal('tag_extra tag2_extra last_tag_extra last_tag2_extra', template.render(extra));
});

QUnit.test('creme.utils.Template (render, object attribute)', function(assert) {
    var data = {
         firstname: 'John',
         lastname: 'Doe',
         address: {
             number: 13,
             roadtype: 'rue',
             road: 'des plantes en pot',
             city: {
                 postalcode: 45007,
                 name: 'Melun Sud'
             }
         }
    };

    var template = new creme.utils.Template('this is a template', data);
    assert.equal('this is a template', template.render());

    template.pattern('Mr ${firstname} ${lastname}, living at ${address.number}, ${address.roadtype} ${address.road}, ${address.city.postalcode} ${address.city.name}');
    assert.equal('Mr John Doe, living at 13, rue des plantes en pot, 45007 Melun Sud', template.render());
});

QUnit.test('creme.utils.Template (render, empty object attribute)', function(assert) {
    var data = {
         firstname: 'John',
         lastname: 'Doe',
         address: {
             number: 13,
             roadtype: 'rue',
             road: 'des plantes en pot',
             city: null
         }
    };

    var template = new creme.utils.Template('this is a template', data);
    assert.equal('this is a template', template.render());

    template.pattern('Mr ${firstname} ${lastname}, living at ${address.number}, ${address.roadtype} ${address.road}, ${address.city.postalcode} ${address.city.name}');
    assert.equal('Mr John Doe, living at 13, rue des plantes en pot, ${address.city.postalcode} ${address.city.name}', template.render());
});

QUnit.test('creme.utils.Template (render, object getters)', function(assert) {
    var data = {
        firstname: function() { return 'John'; },
        lastname: function() { return 'Doe'; },
        fullname: function() { return 'JohnDoe'; },
        address: function() {
 return {
            number: function() { return 38; },
            roadtype: 'rue',
            road: 'des plantes en pot',
            city: {
                postalcode: 45007,
                name: 'Melun Sud'
            }
        };
}
    };

    var template = new creme.utils.Template('this is a template', data);
    assert.equal('this is a template', template.render());

    template.pattern('Mr ${firstname} ${lastname} (${fullname}), living at ${address.number}, ${address.roadtype} ${address.road}, ${address.city.postalcode} ${address.city.name}');
    assert.equal('Mr John Doe (JohnDoe), living at 38, rue des plantes en pot, 45007 Melun Sud', template.render());
});

QUnit.test('creme.utils.templatize (none)', function(assert) {
    var template = creme.utils.templatize();

    assert.equal(undefined, template.pattern());
    assert.equal(undefined, template.parameters());
    assert.equal(null, template.render());

    template = creme.utils.templatize(null, {tag: 'tag1'});

    assert.equal(undefined, template.pattern());
    assert.deepEqual({tag: 'tag1'}, template.parameters());
    assert.equal(null, template.render());
});

QUnit.test('creme.utils.templatize (string)', function(assert) {
    var template = creme.utils.templatize('template ${tag}');

    assert.equal('template ${tag}', template.pattern());
    assert.equal(undefined, template.parameters());
    assert.equal('template ${tag}', template.render());

    template = creme.utils.templatize('template ${tag}', {tag: 'tag1'});

    assert.equal('template ${tag}', template.pattern());
    assert.deepEqual({tag: 'tag1'}, template.parameters());
    assert.equal('template tag1', template.render());
});

QUnit.test('creme.utils.templatize (template, context)', function(assert) {
    var source = new creme.utils.Template('template ${tag}');
    var template = creme.utils.templatize(source);

    assert.equal('template ${tag}', template.pattern());
    assert.equal(undefined, template.parameters());
    assert.equal('template ${tag}', template.render());

    template = creme.utils.templatize(source, {tag: 'tag1'});

    assert.equal('template ${tag}', template.pattern());
    assert.deepEqual({tag: 'tag1'}, template.parameters());
    assert.equal('template tag1', template.render());
});
}(jQuery));
