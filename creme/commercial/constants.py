import warnings

UUID_PROP_IS_A_SALESMAN = '042e6f86-c40d-4e29-a18b-24fe05ad2193'

REL_SUB_SOLD = 'commercial-subject_sold_by'  # NB: keep the value (wrong "_by") for compatibility
REL_OBJ_SOLD = 'commercial-object_sold_by'

REL_SUB_COMPLETE_GOAL = 'commercial-subject_complete_goal'
REL_OBJ_COMPLETE_GOAL = 'commercial-object_complete_goal'

DEFAULT_HFILTER_ACT      = 'commercial-hf_act'
DEFAULT_HFILTER_STRATEGY = 'commercial-hf_strategy'
DEFAULT_HFILTER_PATTERN  = 'commercial-hf_objpattern'


# DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW = \
#     'commercial-display_only_orga_demco_on_orga_detailview'
def __getattr__(name):
    if name == 'DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW':
        warnings.warn(
            '"DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW" is deprecated; '
            'use commercial.setting_keys.orga_approaches_key.id instead.',
            DeprecationWarning,
        )
        return 'commercial-display_only_orga_demco_on_orga_detailview'

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
