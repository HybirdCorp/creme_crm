/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2010  Hybird

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*******************************************************************************/

//(function() {
//    var old_Raphael = Raphael;
//    Raphael = function() {
//        var raphael = old_Raphael.apply(this, arguments);
//        var old_set = raphael.set;
//        raphael.set = function() {
//            var set = old_set.apply(this, arguments);
//            set.toString = function () {return 'Object';};
//            return set;
//        };
//        return raphael;
//    };
//})();

creme.graphael = {};

creme.graphael._init = function(selector)
{
    var nodes = $(selector);
    for(var i=-1, l=nodes.length; ++i < l;)
    {
        var node = nodes[i];
        var $node = $(node);
        
        var n_width  = $node.width();
        var n_height = n_width * 0.5;

        var r = Raphael(node, n_width, n_height);
        $node.data('graphael', r);
    }
    return nodes;
};

creme.graphael.init = function(selector)
{
    var initial_nodes = $(selector);
    var nodes = initial_nodes.not('.initialized');

    for(var i=-1, l=nodes.length; ++i < l;)
    {
        var node = nodes[i];
        var $node = $(node);
        //Not really optimized because _init takes a selector and not a node
        creme.graphael._init(node);
        $node.addClass('initialized');
    }
    return initial_nodes;
};

creme.graphael.paddings = {
    'L_PAD': 15,//left padding
    'R_PAD': 15,//right padding
    'H_PAD': 15,//top padding
    'B_PAD': 15,//bottom padding
    'I_PAD': 5,//Inter elements padding not an apple thing ;)
    'CUR_Y': 10
}

creme.graphael.barchart = {};

creme.graphael.barchart.fin = function (r, chart){
    //var dims = chart.bar.getBBox();
    chart.flag = r.g.popup(chart.bar.x, chart.bar.y + creme.graphael.paddings.I_PAD, chart.bar.value || "0").insertBefore(chart);
};

creme.graphael.barchart.fout = function () {
    this.flag.animate({opacity: 0}, 300, function () {this.remove();});
};

creme.graphael.simple_barchart = function(options)
{
    if(!options || options == undefined || options.instance==undefined) return;//Need at least a Raphael's instance
    var graphael = options.instance;
    var container = options.container;

    if(!container.hasClass('graphael-barchart-drawn'))
    {
        var paddings = $.extend(creme.graphael.paddings, options.paddings);
        var x = options.x || [], y = options.y || [];

        var lpad = paddings.L_PAD;
        var hpad = paddings.H_PAD;
        var ipad = paddings.I_PAD;

        var graphael_width = graphael.width;
        var graphael_height = graphael.height;
        var gtext = graphael.g.text;

        graphael.g.txtattr.font = "12px 'Fontin Sans', Fontin-Sans, sans-serif";

        var barchart = graphael.g.barchart(lpad, hpad/2, graphael_width-lpad, graphael_height-hpad, [y], {vgutter:40, gutter:"40%"})
                        .hover(function(e){creme.graphael.barchart.fin(graphael, this)}, creme.graphael.barchart.fout);

        $.each(barchart.bars[0], function(i){//We don't stack bars so [0]...
            this.attr({fill: Raphael.getColor(i)});
        });
        
        var lbl_ordinate = gtext(barchart.getBBox().x/2+lpad, graphael_height/2, options.ordinate_lbl || "").rotate(270);
//        var lbl_ordinate = graphael.g.text(lpad, graphael_height/2, options.ordinate_lbl || "").rotate(270, true);
        var lbl_abscissa = gtext(graphael_width/2, graphael_height - ipad, options.abscissa_lbl || "");

        var show_legend = false ? (options.show_legend == undefined || options.show_legend == false) : true;
        if(!show_legend ||  x.length <=5)
        {
            barchart.label([x], true);
        }
        else
        {
            var range = creme.utils.range(1, x.length+1)
            barchart.label([range], true);

            var previous_height = ipad;
            var init_lbl_x = graphael_width*0.15;

            for(var i=0; i < range.length; i++)
            {
                var lgd = range[i];
                var label = gtext(init_lbl_x, graphael_height + previous_height, lgd+" : "+x[i]);
                label.attr({
                   x : label.getBBox().x+label.getBBox().width
                });
                previous_height += label.getBBox().height
            }
            graphael.setSize(graphael_width,graphael_height+previous_height);
        }

        if(options.gen_date_selector)
        {
            $(options.gen_date_selector).text(new Date().toString("dd-MM-yyyy HH:mm:ss"));//Needs Datejs but doesn't bug when not
        }
        container.addClass('graphael-barchart-drawn');
    }
};

creme.graphael.simple_pie = function(options)
{
    if(!options || options == undefined || options.instance==undefined) return;//Need at least a Raphael's instance
    var graphael = options.instance;
    var container = options.container;

    if(!container.hasClass('graphael-pie-drawn'))
    {
        var paddings = $.extend(creme.graphael.paddings, options.paddings);
        var x = options.x || [], y = options.y || [];

        var lpad = paddings.L_PAD;
        var hpad = paddings.H_PAD;
        var ipad = paddings.I_PAD;

        var graphael_width = graphael.width;
        var graphael_height = graphael.height;
        var gtext = graphael.g.text;

        graphael.g.txtattr.font = "12px 'Fontin Sans', Fontin-Sans, sans-serif";

        var parsed_y = [];
        for(var i=-1, l=y.length; ++i < l;)
        {
            var current = parseInt(y[i]);
            if(isNaN(current)) current = 0;

            parsed_y.push(current);
        }

        var pie_width = graphael_width/5;
        var pie = graphael.g.piechart(pie_width+lpad, graphael_height/2, pie_width, parsed_y,
                                      {
                                        legend: x,
                                        legendpos: "east"
                                      });
        pie.hover(function (){
            var sector = this.sector;
            var label  = this.label;
            sector.stop();
            sector.scale(1.1, 1.1, this.cx, this.cy);
            var value = (sector.value != undefined && sector.value.value != undefined) ? sector.value.value : 100;
            this.flag = graphael.g.popup(sector.middle.x, sector.middle.y + creme.graphael.paddings.I_PAD, value);

            if (label) {
                label[0].stop();
                label[0].scale(1.5);
                label[1].attr({"font-weight": 800});
            }
        }, function () {
            var label  = this.label;
            
            this.sector.animate({scale: [1, 1, this.cx, this.cy]}, 500, "bounce");

            this.flag.animate({opacity: 0}, 300, function () {this.remove();});

            if (label) {
                label[0].animate({scale: 1}, 500, "bounce");
                label[1].attr({"font-weight": 400});
            }       
        });

        if(options.gen_date_selector)
        {
            $(options.gen_date_selector).text(new Date().toString("dd-MM-yyyy HH:mm:ss"));//Needs Datejs but doesn't bug when not
        }
        container.addClass('graphael-pie-drawn');
    }
};


creme.graphael.simple_refetch = function(url, type, container_selector, o_lbl, a_lbl, date_selector)
{
    var type_infos = creme.graphael.simple_refetch.types[type];
    if(type_infos != undefined)
    {
        creme.ajax.json.get(url, {}, function(d){
            var x = d.x;
            var y = d.y;

            var $container = $(container_selector);
            var instance = $container.data('graphael');
            instance.clear();
            $container.removeClass(type_infos.css_class);

            type_infos.func({
                   'instance': instance,
                   'container':$container,
                   'x': x,
                   'y': y,
                   'gen_date_selector': date_selector,
                   'abscissa_lbl':a_lbl,
                   'ordinate_lbl':o_lbl
                });
        }, null, true, {
              beforeSend : function(request){
                  creme.utils.loading('loading', false, {});
              },
              complete:function (request, status) {
                  creme.utils.loading('loading', true, {});
              }
        });
    }
};

creme.graphael.simple_refetch.types = {
    histogram: {
                'css_class':'graphael-barchart-drawn',
                'func': creme.graphael.simple_barchart
    },
    pie: {
        'css_class':'graphael-pie-drawn',
        'func': creme.graphael.simple_pie
    }
};
