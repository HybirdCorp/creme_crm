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

from itertools import izip as zip

from django.db.models import CharField, ForeignKey, ManyToManyField, PositiveSmallIntegerField
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.models import CremeEntity, CremeModel, CremePropertyType

from persons.models import Organisation


_CATEGORY_MAP = {
         0: 4, # Weak charms   & weak assets
         1: 2, # Strong charms & weak assets
        10: 3, # Weak charms   & strong assets
        11: 1, # Strong charms & strong assets
    }


class MarketSegment(CremeModel):
    name          = CharField(_(u"Name"), max_length=100)
    property_type = ForeignKey(CremePropertyType)

    class Meta:
        app_label = "commercial"
        verbose_name = _(u'Market segment')
        verbose_name_plural = _(u'Market segments')

    def __unicode__(self):
        return self.name

    @staticmethod
    def generate_property_text(segment_name):
        return ugettext(u'is in the segment "%s"') % segment_name


class Strategy(CremeEntity):
    name            = CharField(_(u"Name"), max_length=100)
    evaluated_orgas = ManyToManyField(Organisation, null=True)
    segments        = ManyToManyField(MarketSegment, null=True)

    class Meta:
        app_label = "commercial"
        verbose_name = _(u'Commercial strategy')
        verbose_name_plural = _(u'Commercial strategies')

    def __init__(self, *args, **kwargs):
        super(Strategy, self).__init__(*args, **kwargs)
        self._clear_caches()

    def __unicode__(self):
        return self.name

    def _clear_caches(self):
        self._segments_list = None

        self._assets_list = None
        self._assets_scores_map = {} #dict of dict of dict for hierarchy: organisation/segment/asset

        self._charms_list = None
        self._charms_scores_map = {} #dict of dict of dict for hierarchy: organisation/segment/charm

        self._segments_categories = {}

    def delete(self):
        CommercialAssetScore.objects.filter(asset__strategy=self.id, segment__strategy=self.id).delete()
        MarketSegmentCharmScore.objects.filter(charm__strategy=self.id, segment__strategy=self.id).delete()
        MarketSegmentCategory.objects.filter(strategy=self.id).delete()

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

    def _get_charms_scores_objects(self, orga):
        scores = self._charms_scores_map.get(orga.id)

        if scores is None:
            charms = self.get_charms_list()
            segments = self.get_segments_list()

            #build a 'matrix' with default score(=1) everywhere
            scores = dict((segment.id,
                           dict((charm.id,
                                 MarketSegmentCharmScore(score=1, organisation=orga, charm=charm, segment=segment)
                                ) for charm in charms)
                          ) for segment in segments)

            #set the right scores in the matrix
            for score in MarketSegmentCharmScore.objects.filter(organisation=orga, charm__in=charms, segment__in=segments):
                scores[score.segment_id][score.charm_id] = score

            self._charms_scores_map[orga.id] = scores

        return scores

    def _get_asset_score_object(self, orga, asset_id, segment_id):
        return self._get_assets_scores_objects(orga)[segment_id][asset_id]

    def get_asset_score(self, orga, asset, segment):
        return self._get_asset_score_object(orga, asset.id, segment.id).score

    def get_assets_list(self):
        if self._assets_list is None:
            self._assets_list = list(self.assets.all())

        return self._assets_list

    def _get_charm_score_object(self, orga, charm_id, segment_id):
        return self._get_charms_scores_objects(orga)[segment_id][charm_id]

    def get_charm_score(self, orga, charm, segment):
        return self._get_charm_score_object(orga, charm.id, segment.id).score

    def get_charms_list(self):
        if self._charms_list is None:
            self._charms_list = list(self.charms.all())

        return self._charms_list

    def _get_totals(self, orga_scores):
        """@return a list of tuple (total_for_segment, total_category)
        with 1 <= total_category <= 3  (1 is weak, 3 strong)
        """
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

    def get_assets_totals(self, orga):
        return self._get_totals(self._get_assets_scores_objects(orga))

    def get_charms_totals(self, orga):
        return self._get_totals(self._get_charms_scores_objects(orga))

    def get_segment_category(self, orga, segment):
        sid = segment.id

        for category, segments in self._get_segments_categories(orga).iteritems():
            for other_segment in segments:
                if other_segment.id == sid:
                    return category

        raise KeyError('Strategy.get_segment_category() for segment: %s' % segment)

    def _get_segments_categories(self, orga):
        """@return A dictionary with key= Category (int, between 1 & 4) and value=list of MarketSegment.
        """
        categories = self._segments_categories.get(orga)

        if categories is None:
            categories = dict((i, []) for i in xrange(1, 5))
            segments = self.get_segments_list()

            if segments:
                assets_totals = [t[0] for t in self.get_assets_totals(orga)]
                charms_totals = [t[0] for t in self.get_charms_totals(orga)]

                asset_threshold = (max(assets_totals) + min(assets_totals)) / 2.0
                charm_threshold = (max(charms_totals) + min(charms_totals)) / 2.0

                stored_categories = dict((cat_obj.segment_id, cat_obj.category)
                                            for cat_obj in MarketSegmentCategory.objects.filter(segment__in=segments,
                                                                                                organisation=orga)
                                        ) #TODO: Use values_list()

                def _get_category(segment, asset_score, charm_score):
                    cat = stored_categories.get(segment.id)

                    if cat is not None:
                        return cat

                    cat_key = 0
                    if charm_score > charm_threshold: cat_key += 1
                    if asset_score > asset_threshold: cat_key += 10

                    return _CATEGORY_MAP[cat_key]

                for segment, asset_total, charm_total in zip(segments, assets_totals, charms_totals):
                    categories[_get_category(segment, asset_total, charm_total)].append(segment)

            self._segments_categories[orga] = categories

        return categories

    def get_segments_for_category(self, orga, category):
        return self._get_segments_categories(orga)[category]

    def get_segments_list(self):
        if self._segments_list is None:
            self._segments_list = list(self.segments.all())

        return self._segments_list

    def _set_score(self, model_id, segment_id, orga_id, score, get_object):
        if not 1 <= score <= 4:
            raise ValueError('Problem with "score" arg: not 1 <= %s <= 4' % score)

        orga = self.evaluated_orgas.get(pk=orga_id) #raise exception if invalid orga

        score_object = get_object(orga, model_id, segment_id)

        if score_object.score != score:
            score_object.score = score
            score_object.save()

    def set_asset_score(self, asset_id, segment_id, orga_id, score):
        self._set_score(asset_id, segment_id, orga_id, score, self._get_asset_score_object)

    def set_charm_score(self, charm_id, segment_id, orga_id, score):
        self._set_score(charm_id, segment_id, orga_id, score, self._get_charm_score_object)

    def set_segment_category(self, segment_id, orga_id, category):
        if not 1 <= category <= 4:
            raise ValueError('Problem with "category" arg: not 1 <= %s <= 4' % category)

        orga    = self.evaluated_orgas.get(pk=orga_id) #raise exception if invalid orga
        segment = self.segments.get(pk=segment_id)  #raise exception if invalid segment

        cats_objs = MarketSegmentCategory.objects.filter(segment=segment, organisation=orga)[:1]

        if cats_objs:
            cat_obj = cats_objs[0]

            if cat_obj.category == category:
                return

            cat_obj.category = category
            cat_obj.save()
        else:
            MarketSegmentCategory.objects.create(strategy=self, segment=segment,
                                                 organisation=orga, category=category
                                                )

        self._segments_categories.pop(orga.id, None) #clean cache

    def unlink_segment(self, segment_id):
        self.segments.remove(segment_id)

        CommercialAssetScore.objects.filter(segment=segment_id, asset__strategy=self.id).delete()
        MarketSegmentCharmScore.objects.filter(segment=segment_id, charm__strategy=self.id).delete()
        MarketSegmentCategory.objects.filter(strategy=self, segment=segment_id).delete()

        self._clear_caches()


class CommercialAsset(CremeModel):
    name     = CharField(_(u"Name"), max_length=100)
    strategy = ForeignKey(Strategy, related_name='assets')

    class Meta:
        app_label = "commercial"
        verbose_name = _(u'Commercial asset')
        verbose_name_plural = _(u'Commercial assets')

    def __unicode__(self):
        return self.name

    def get_related_entity(self): #for generic views
        return self.strategy


class CommercialAssetScore(CremeModel):
    score        = PositiveSmallIntegerField()
    segment      = ForeignKey(MarketSegment)
    asset        = ForeignKey(CommercialAsset)
    organisation = ForeignKey(Organisation)

    class Meta:
        app_label = "commercial"

    def __unicode__(self): #debugging
        return u'<AssetScore: orga=%s score=%s segment=%s asset=%s>' % (
                    self.organisation, self.score, self.segment, self.asset)


class MarketSegmentCharm(CremeModel):
    name     = CharField(_(u"Name"), max_length=100)
    strategy = ForeignKey(Strategy, related_name='charms')

    class Meta:
        app_label = "commercial"
        verbose_name = _(u'Segment charm')
        verbose_name_plural = _(u'Segment charms')

    def __unicode__(self):
        return self.name

    def get_related_entity(self): #for generic views
        return self.strategy


class MarketSegmentCharmScore(CremeModel):
    score        = PositiveSmallIntegerField()
    segment      = ForeignKey(MarketSegment)
    charm        = ForeignKey(MarketSegmentCharm)
    organisation = ForeignKey(Organisation)

    class Meta:
        app_label = "commercial"

    def __unicode__(self): #debugging
        return u'<CharmScore: orga=%s score=%s segment=%s charm=%s>' % (
                    self.organisation, self.score, self.segment, self.charm)


class MarketSegmentCategory(CremeModel):
    category     = PositiveSmallIntegerField()
    strategy     = ForeignKey(Strategy)
    segment      = ForeignKey(MarketSegment)
    organisation = ForeignKey(Organisation)

    class Meta:
        app_label = "commercial"

    def __unicode__(self): #debugging
        return u'<MarketSegmentCategory: orga=%s cat=%s segment=%s>' % (
                    self.organisation, self.category, self.segment)
