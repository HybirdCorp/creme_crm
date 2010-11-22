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

/*
 * Fonction faite pour étendre (faire apparaitre) une liste de type ul / li qui ont pour class expandlist / expandedlist
 * TODO: delete when folders use a common listview
 **/
function expandme(obj)
{
    if(typeof(obj) == "string") obj = document.getElementById(obj);
    if(!obj || typeof(obj) == "undefined") return;
    var ul_child = obj.parentNode.getElementsByTagName('ul');

    if(obj.className == "expandedlist")
    {
        obj.className = "expandlist";
        for(var i=0; i < ul_child.length; i++)
        {
            if(ul_child[i].parentNode == obj.parentNode)
            ul_child[i].style.display = 'none';
        }
    }
    else
    {
        obj.className = "expandedlist";

        for(var i=0; i < ul_child.length; i++)
        {
            //ul_child[i].className = "expandedlist";
            if(ul_child[i].parentNode == obj.parentNode)
            ul_child[i].style.display = 'block';
        }
    }
}

function loadChildFolders(nodeToAttach, nodePk)
{
    if(typeof(nodeToAttach) == "string") nodeToAttach = document.getElementById(nodeToAttach);
    if(!nodeToAttach || typeof(nodeToAttach) == 'undefined') return;
    if(!nodePk || isNaN(parseInt(nodePk))) return;


          $('#'+nodeToAttach.parentNode.id+' > ul').empty();
          $('#'+nodeToAttach.parentNode.id+' > ul').remove();
          $(nodeToAttach).addClass('wait');
          //Gestion des classeurs
          $.ajax({
                  url: "/documents/getChildFolders/",
                  async : false,
//                  global: false,
                  type: "POST",
                  data: ({id : nodePk}),
                  dataType: "json",
                  cache : false,
                  success: function(data){
//                    $(nodeToAttach)
//                          .append(
//                            $('<ul></ul>'));
                     for(var ind in data)
                     {
                          $('#'+nodeToAttach.id)
                          .after(
                            $('<ul></ul>')
                              .attr('id', 'parent_folder_'+data[ind].pk+'_id')
                              .append(
                                  $('<li></li>')
                                        .addClass('expandlist')
                                        .attr('id','folder_'+data[ind].pk+'_id')
                                        .attr('title',data[ind].fields.description)
//                                        .attr('onclick','loadChildClasseurs(this, '+data[ind].pk+');expandme(this);')
                                        .bind('click',{pk:data[ind].pk, id : 'folder_'+data[ind].pk+'_id'},function(e){loadChildFolders(e.data.id, e.data.pk);expandme(e.data.id);})
//                                        .bind("click", function(e){loadChildClasseurs('classeur_'+data[ind].pk+'_id', data[ind].pk); expandme('classeur_'+data[ind].pk+'_id');})
                                        .append(
                                           $('<a>'+data[ind].fields.title+'<a/>')
                                            .attr('href','/documents/folder/'+data[ind].pk)
                                        )
                              )
                          );
                     }
                  }
               });
           //Gestion des documents
            $.ajax({
                  url: "/documents/getChildDocuments/",
                  async : false,
                  type: "POST",
                  data: ({id : nodePk}),
                  dataType: "json",
                  cache : false,
                  success: function(data){
                     for(var ind in data)
                     {
                          $('#'+nodeToAttach.id)
                          .after(
                            $('<ul></ul>')
                              .attr('id', 'parent_folder_doc_'+data[ind].pk+'_id')
                              .append(
                                  $('<li></li>')
                                        .addClass('document')
                                        .attr('id','folder_doc_'+data[ind].pk+'_id')
                                        .attr('title',data[ind].fields.description)
                                        .append(
                                           $('<a>'+data[ind].fields.title+'<a/>')
                                            .attr('href','/documents/document/'+data[ind].pk)
                                        )
                                        .append(
                                                    $('<span></span>')
                                                        .attr('id','dl_doc_'+data[ind].pk)
                                                        .css('display','none')
                                                        .append($('<a> | Télécharger</a>')
                                                            .attr('href','/download_file/'+data[ind].fields.filedata)
                                                        )
                                        )
//                                        .attr('onmouseover', "$('#dl_doc_"+data[ind].pk+"').css('display','inline');")
//                                        .attr('onmouseout', "$('#dl_doc_"+data[ind].pk+"').css('display','none');")
                                        .bind('mouseout', {pk : data[ind].pk}, function(e){$('#dl_doc_'+e.data.pk).css('display','none');})
                                        .bind('mouseover', {pk : data[ind].pk}, function(e){$('#dl_doc_'+e.data.pk).css('display','inline');})
                              )
                          );
                     }
                  }
               });
           $(nodeToAttach).removeClass('wait');

}