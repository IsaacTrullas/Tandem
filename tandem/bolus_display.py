"""Dose-based presentation only; no inference of why a bolus was administered."""
import math


MARKED_BOLUS_LABEL = 'Bolo de 0,05 U'
FOOD_BOLUS_LABEL = 'Bolo con carbohidratos'


def is_food_bolus(point):
    """Visual category from associated positive grams, never inferred ingestion."""
    if not point:return False
    details=point.get('details',{})
    if details.get('ambiguous') or (details.get('revision_count') or 0)>1 or len(details.get('revision_ids') or ())>1:return False
    values=(details.get('carbohydrate_grams'),details.get('csv_values',{}).get('carbohydrate_grams'))
    return any(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>0 for v in values)


def is_005_bolus(point):
    """Recognize recorded 0.05 U, allowing only binary floating-point noise."""
    if not point or point.get('unit') != 'U':
        return False
    details = point.get('details', {})
    if (details.get('ambiguous') or (details.get('revision_count') or 0) > 1
            or len(details.get('revision_ids') or ()) > 1):
        return False
    value = point.get('value')
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isclose(value, .05, rel_tol=0, abs_tol=1e-12))
