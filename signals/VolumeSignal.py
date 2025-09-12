import numpy as np
import pandas as pd

def genVolumeSignal(daily_change, 
                           obv_slope, 
                           adl_slope, 
                           vol_ratio_5, 
                           vol_z, 
                           ZSURGE, 
                           SURGE_X, 
                           DRYUP_X):
    # --- VolumeSignal with OBV/A&D confirmation ---

    price_up  = daily_change > 0
    price_dn  = daily_change < 0
    surge     = (not np.isnan(vol_ratio_5)) and (vol_ratio_5 >= SURGE_X) and (not np.isnan(vol_z)) and (vol_z >= ZSURGE)
    dryup     = (not np.isnan(vol_ratio_5)) and (vol_ratio_5 <= DRYUP_X)
    obv_up    = obv_slope > 0
    obv_dn    = obv_slope < 0
    ad_up     = adl_slope > 0
    ad_dn     = adl_slope < 0

    if price_up and surge:
        if obv_up and ad_up:
            return "Strong Buy (Accumulation)"
        elif obv_up or ad_up:
            return "Weak Buy (Unconfirmed Accum.)"
        else:
            return "Weak Buy (No OBV/A/D conf.)"
    if price_dn and surge:
        if obv_dn and ad_dn:
            return "Strong Sell (Distribution)"
        elif obv_dn or ad_dn:
            return "Weak Sell (Unconfirmed Distr.)"
        else:
            return "Weak Sell (No OBV/A/D conf.)"
    if price_up and dryup:
        return "Caution (Price up on dry volume)"
    return "Neutral"


