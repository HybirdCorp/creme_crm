(function($) {
QUnit.module("creme.utils.template.js", new QUnitMixin());

QUnit.test('creme.utils.TemplateRenderer (constructor)', function(assert) {
    var renderer = new creme.utils.TemplateRenderer();
    deepEqual([], renderer.tags('${a}'));
    deepEqual('${a}', renderer.render('${a}', {a: 12}));
});

QUnit.test('creme.utils.Template (constructor)', function(assert) {
    var template = new creme.utils.Template();
    equal(undefined, template.pattern());
    deepEqual(undefined, template.parameters());
    equal('object', typeof template.renderer());

    template = new creme.utils.Template('this is a ${object}', {object: 'backpipe'});
    equal('this is a ${object}', template.pattern());
    deepEqual({object: 'backpipe'}, template.parameters());
    equal('object', typeof template.renderer());
});

QUnit.test('creme.utils.Template (tags)', function(assert) {
    var template = new creme.utils.Template();
    deepEqual([], template.tags());

    template.pattern('${tag} ${tag2} ${last_tag}');
    deepEqual(['tag', 'tag2', 'last_tag'], template.tags());

    template.pattern('${tag} ${tag2} ${{{last_tag}');
    deepEqual(['tag', 'tag2'], template.tags());

    template.pattern('${tag} ${tag2} ${{last_tag}}');
    deepEqual(['tag', 'tag2'], template.tags());

    template.pattern('${tag} ${tag2} $last_tag}');
    deepEqual(['tag', 'tag2'], template.tags());

    template.pattern('${tag} ${tag2} ${last_tag toto');
    deepEqual(['tag', 'tag2'], template.tags());

    template.pattern('${tag} ${tag2} ${last tag}');
    deepEqual(['tag', 'tag2'], template.tags());

    template.pattern('${tag} ${tag2} {last_tag}');
    deepEqual(['tag', 'tag2'], template.tags());

    template.pattern('${tag.id} ${tag.name}');
    deepEqual(['tag'], template.tags());
});

QUnit.test('creme.utils.Template (render, empty data)', function(assert) {
    var template = new creme.utils.Template('this is a template');
    equal('this is a template', template.render());

    template.pattern('${tag} ${tag2} ${last_tag}');
    equal('${tag} ${tag2} ${last_tag}', template.render());
});

QUnit.test('creme.utils.Template (render, empty pattern)', function(assert) {
    var template = new creme.utils.Template('', {tag: 12});
    equal('', template.render());

    template.pattern(null);
    equal(null, template.render());
});

QUnit.test('creme.utils.Template (render, dict)', function(assert) {
    var data = {tag: 12,
                tag2: 'string',
                last_tag: {toString: function() { return 'yo'; }}};

    var template = new creme.utils.Template('this is a template', data);
    equal('this is a template', template.render());

    template.pattern('${tag} ${tag2} ${last_tag}');
    equal('12 string yo', template.render());

    data.tag2 = undefined;
    equal('12 ${tag2} yo', template.render());

    data.tag3 = 'string3';
    equal('12 ${tag2} yo', template.render());

    equal('12 ${tag2} extra_yo', template.render({last_tag: 'extra_yo'}));
    equal('12 ${tag2} yo', template.render({tag3: 'extra_string3'}));
});

QUnit.test('creme.utils.Template (render, array)', function(assert) {
    var data = [12, 13, 14];

    var template = new creme.utils.Template('this is a template', data);

    equal(true, template.iscomplete());
    equal('this is a template', template.render());

    template.pattern('${0} ${1} ${2}');

    equal(true, template.iscomplete());
    equal('12 13 14', template.render());

    template.pattern('${0} ${1} ${3}');

    equal(false, template.iscomplete());
    equal('12 13 ${3}', template.render());
});

QUnit.test('creme.utils.Template (render, function)', function(assert) {
    var data = function(key) { return key + "_rendered"; };
    var extra = function(key) { return key + "_extra"; };

    var template = new creme.utils.Template('this is a template', data);

    equal(true, template.iscomplete());
    equal('this is a template', template.render());

    template.pattern('${tag} ${tag2} ${last_tag}');

    equal(true, template.iscomplete());
    equal('tag_rendered tag2_rendered last_tag_rendered', template.render());

    template.pattern('${tag} ${tag2} ${last_tag} ${last_tag2}');

    equal(true, template.iscomplete());
    equal('tag_rendered tag2_rendered last_tag_rendered last_tag2_rendered', template.render());

    equal('tag_extra tag2_extra last_tag_extra last_tag2_extra', template.render(extra));
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
    equal('this is a template', template.render());

    template.pattern('Mr ${firstname} ${lastname}, living at ${address.number}, ${address.roadtype} ${address.road}, ${address.city.postalcode} ${address.city.name}');
    equal('Mr John Doe, living at 13, rue des plantes en pot, 45007 Melun Sud', template.render());
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
    equal('this is a template', template.render());

    template.pattern('Mr ${firstname} ${lastname}, living at ${address.number}, ${address.roadtype} ${address.road}, ${address.city.postalcode} ${address.city.name}');
    equal('Mr John Doe, living at 13, rue des plantes en pot, ${address.city.postalcode} ${address.city.name}', template.render());
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
    equal('this is a template', template.render());

    template.pattern('Mr ${firstname} ${lastname} (${fullname}), living at ${address.number}, ${address.roadtype} ${address.road}, ${address.city.postalcode} ${address.city.name}');
    equal('Mr John Doe (JohnDoe), living at 38, rue des plantes en pot, 45007 Melun Sud', template.render());
});

QUnit.test('creme.utils.templatize (none)', function(assert) {
    var template = creme.utils.templatize();

    equal(undefined, template.pattern());
    equal(undefined, template.parameters());
    equal(null, template.render());

    template = creme.utils.templatize(null, {tag: 'tag1'});

    equal(undefined, template.pattern());
    deepEqual({tag: 'tag1'}, template.parameters());
    equal(null, template.render());
});

QUnit.test('creme.utils.templatize (string)', function(assert) {
    var template = creme.utils.templatize('template ${tag}');

    equal('template ${tag}', template.pattern());
    equal(undefined, template.parameters());
    equal('template ${tag}', template.render());

    template = creme.utils.templatize('template ${tag}', {tag: 'tag1'});

    equal('template ${tag}', template.pattern());
    deepEqual({tag: 'tag1'}, template.parameters());
    equal('template tag1', template.render());
});

QUnit.test('creme.utils.templatize (template, context)', function(assert) {
    var source = new creme.utils.Template('template ${tag}');
    var template = creme.utils.templatize(source);

    equal('template ${tag}', template.pattern());
    equal(undefined, template.parameters());
    equal('template ${tag}', template.render());

    template = creme.utils.templatize(source, {tag: 'tag1'});

    equal('template ${tag}', template.pattern());
    deepEqual({tag: 'tag1'}, template.parameters());
    equal('template tag1', template.render());
});
}(jQuery));
