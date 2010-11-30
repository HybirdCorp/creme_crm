# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.db.models import CharField, ForeignKey, ManyToManyField, PositiveSmallIntegerField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, CremeModel

from persons.models import Organisation


class Strategy(CremeEntity):
    name            = CharField(_(u"Name"), max_length=100)
    evaluated_orgas = ManyToManyField(Organisation, null=True)

    class Meta:
        app_label = "commercial"
        verbose_name = _(u'Commercial strategy')
        verbose_name_plural = _(u'Commercial strategies')

    def __init__(self, *args, **kwargs):
        super(Strategy, self).__init__(*args, **kwargs)

        self._segments_list = None
        self._assets_list = None
        self._assets_scores_map = {} #dict of dict of dict for hierarchy: organisation/segment/asset

    def __unicode__(self):
        return self.name

    def delete(self):
        CommercialAssetScore.objects.filter(asset__strategy=self.id, segment__strategy=self.id).delete()

        self.segments.all().delete()
        self.assets.all().delete()
        self.charms.all().delete()

        super(Strategy, self).delete()

    def get_absolute_url(self):
        return "/commercial/strategy/%s" % self.id

    def get_edit_absolute_url(self):
        return "/commercial/strategy/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/commercial/strategies"

    def get_assets_list(self):
        if self._assets_list is None:
            self._assets_list = list(self.assets.all())

        return self._assets_list

    def _get_assets_scores_objects(self, orga):
        scores = self._assets_scores_map.get(orga.id)

        if scores is None:
            assets = self.get_assets_list()
            segments = self.get_segments_list()

            #build a 'matrix' with default score(=1) everywhere
            scores = dict((segment.id,
                           dict((asset.id,
                                 CommercialAssetScore(score=1, organisation=orga, asset=asset, segment=segment)
                                ) for asset in assets)
                          ) for segment in segments)

            #set the right scores in the matrix
            for score in CommercialAssetScore.objects.filter(organisation=orga, asset__in=assets, segment__in=segments):
                scores[score.segment_id][score.asset_id] = score

            self._assets_scores_map[orga.id] = scores

        return scores

    def _get_asset_score_object(self, orga, asset_id, segment_id):
        return self._get_assets_scores_objects(orga)[segment_id][asset_id]

    def get_asset_score(self, orga, asset, segment):
        return self._get_asset_score_object(orga, asset.id, segment.id).score

    def get_segments_list(self):
        if self._segments_list is None:
            self._segments_list = list(self.segments.all())

        return self._segments_list

    def get_segments_totals(self, orga):
        """@return a list of tuple (total_for_segment, total_category)
        with 1 <= total_category <= 3  (1 is weak, 3 strong)
        """
        orga_scores = self._get_assets_scores_objects(orga)

        if not orga_scores:
            return []

        scores = [sum(score_obj.score for score_obj in orga_scores[segment.id].itervalues())
                    for segment in self.get_segments_list()
                 ]
        max_score = max(scores)
        min_score = min(scores)

        def _compute_category(score):
            if score == max_score: return 3
            if score == min_score: return 1

            return 2

        return [(score, _compute_category(score)) for score in scores]

    def set_asset_score(self, asset_id, segment_id, orga_id, score):
        orga = self.evaluated_orgas.get(pk=orga_id) #raise exception if invalid orga

        score_object = self._get_asset_score_object(orga, asset_id, segment_id)

        if score_object.score != score:
            score_object.score = score
            score_object.save()


class MarketSegment(CremeModel):
    name     = CharField(_(u"Name"), max_length=100)
    strategy = ForeignKey(Strategy, related_name='segments')

    class Meta:
        app_label = "commercial"
        verbose_name = _(u'Market segment')
        verbose_name_plural = _(u'Market segments')

    def __unicode__(self):
        return self.name


class CommercialAsset(CremeModel):
    name     = CharField(_(u"Name"), max_length=100)
    strategy = ForeignKey(Strategy, related_name='assets')

    class Meta:
        app_label = "commercial"
        verbose_name = _(u'Commercial asset')
        verbose_name_plural = _(u'Commercial assets')

    def __unicode__(self):
        return self.name


class CommercialAssetScore(CremeModel):
    score        = PositiveSmallIntegerField()
    segment      = ForeignKey(MarketSegment)
    asset        = ForeignKey(CommercialAsset)
    organisation = ForeignKey(Organisation)

    class Meta:
        app_label = "commercial"

    def __unicode__(self): #debugging
        return u'<AssetScore: orga=%s score=%s segment=%s> asset=%s>' % (
                    self.organisation, self.score, self.segment, self.asset)


class MarketSegmentCharm(CremeModel):
    name     = CharField(_(u"Name"), max_length=100)
    strategy = ForeignKey(Strategy, related_name='charms')

    class Meta:
        app_label = "commercial"
        verbose_name = _(u'Segment charm')
        verbose_name_plural = _(u'Segment charms')

    #def __unicode__(self):
        #return self.name
