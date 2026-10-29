"""Dose-based presentation only; no inference of why a bolus was administered."""
import math


MARKED_BOLUS_LABEL = 'Bolo de 0,05 U'


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
