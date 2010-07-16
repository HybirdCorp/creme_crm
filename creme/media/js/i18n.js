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

i18n = {
    current_language : 'fr_FR',

    set_language : function(lang) {
        if(typeof(this[lang]) != "undefined") this.current_language = lang;
    },

    get_current_language : function () {
        return this[this.current_language];
    },

    fr_FR :
    {
        NOT_ACCESSIBLE: 'Fonction inaccessible veuillez recharger la page. Si le problème persiste veuillez contacter votre administrateur.',
        DELETE:'Effacer',
        LOADING:'Chargement',
        ADD_PRODUCTS_PICTURES_TO_MAIL:'Voulez vous envoyer les photos des produits en pièce jointe ?',
        YES:'Oui',
        NO:'Non',
        ARE_YOU_SURE:'Êtes-vous sûr?',
        MAKE_A_VALID_CHOICE:'Veuillez faire un choix valide',
        CLOSE:'Fermer',
        SEARCH_RESULTS:'Résultats de recherche...',
        SELECT_AT_LEAST_ONE_ENTITY:'Veuillez sélectionner au moins une entité.'
    },

    en_US :
    {
        NOT_ACCESSIBLE: 'Not accessible',
        DELETE:'Delete',
        LOADING:'Loading',
        ADD_PRODUCTS_PICTURES_TO_MAIL:'Would you send products\' pictures in mail\'s attachments?',
        YES:'Yes',
        NO:'No',
        ARE_YOU_SURE:'Are you sure?',
        MAKE_A_VALID_CHOICE:'Please make a valid choice',
        CLOSE:'Close',
        SEARCH_RESULTS:'Search results...',
        SELECT_AT_LEAST_ONE_ENTITY:'Please select at least one entity.'
    }
};