"""Presentation-only guides for discrete events in the loaded timeline window."""
from bisect import bisect_left, bisect_right
from datetime import datetime, timedelta
import math

import pyqtgraph as pg
from pyqtgraph.graphicsItems.UIGraphicsItem import UIGraphicsItem
from PySide6.QtGui import QPainterPath
from .bolus_display import is_005_bolus, MARKED_BOLUS_LABEL,is_food_bolus,FOOD_BOLUS_LABEL


EPOCH = datetime(1970, 1, 1)
GUIDE_COLOR = (121, 146, 170, 62)


def collect_event_times(data):
    """Coalesce coincident guides without changing or retaining source records.

    Continuous CGM, IOB and basal observations are deliberately not events here.
    A manual glucose entry is a discrete action and has its own guide.
    """
    grouped = {}

    def add(point, label, priority):
        x = point.get('x')
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            return
        event = grouped.setdefault(x, {'x': x, 'labels': [], 'priority': priority})
        if label not in event['labels']:
            event['labels'].append(label)
        event['priority'] = max(priority, event['priority'])

    for point in data.get('boluses', ()):
        marked = is_005_bolus(point)
        add(point, FOOD_BOLUS_LABEL if is_food_bolus(point) else MARKED_BOLUS_LABEL if marked else 'Bolo', 4 if marked or is_food_bolus(point) else 2)
    for point in data.get('carbs', ()):
        add(point, 'Carbohidratos', 4)
    for point in data.get('glucose', ()):
        if point.get('details', {}).get('kind') == 'bg':
            add(point, 'Glucemia introducida', 3)
    for key in ('events', 'clock_changes'):
        for point in data.get(key, ()):
            details = point.get('details', {})
            code = details.get('event_code')
            priority = 5 if code in (4, 5, 11, 12, 13, 14, 229) else 3
            add(point, details.get('label') or 'Evento', priority)
    return tuple({**event, 'labels': tuple(event['labels'])}
                 for _, event in sorted(grouped.items()))


def place_event_labels(events, start, end, width, measure, rows=2):
    """Choose non-overlapping labels, centered on their exact event coordinate.

    Only labels are thinned, never guides. A closer zoom reveals more times.
    Important transitions/meals keep priority over a dense run of auto-boluses.
    All geometry is in logical pixels, so the rule also works at high DPI.
    """
    if end <= start or width <= 0:
        return []
    occupied = [[] for _ in range(rows)]
    placed = []
    short = end - start <= 3 * 3600
    multiple_days = end - start > 24 * 3600
    for event in sorted(events, key=lambda e: (-e['priority'], e['x'])):
        if not start <= event['x'] <= end:
            continue
        instant = EPOCH + timedelta(seconds=event['x'])
        text = instant.strftime('%d/%m %H:%M' if multiple_days else '%H:%M:%S' if short else '%H:%M')
        size = measure(text) + 4
        center = (event['x'] - start) * width / (end - start)
        left, right = center - size / 2, center + size / 2
        # Edge labels are revealed when the event is panned away from the edge.
        if left < 0 or right > width:
            continue
        for row in range(rows):
            if all(right + 6 <= a or left >= b + 6 for a, b in occupied[row]):
                occupied[row].append((left, right))
                placed.append({**event, 'text': text, 'row': row,
                               'center': center, 'left': left, 'right': right})
                break
    return sorted(placed, key=lambda label: (label['x'], label['row']))


class EventGuideItem(UIGraphicsItem):
    """One light graphics item per panel, rather than one QObject per event."""
    def __init__(self, times):
        super().__init__()
        self.times = times
        self.pen = pg.mkPen(GUIDE_COLOR, width=.8)
        self.pen.setCosmetic(True)
        self.setZValue(-5)
        self.setAcceptedMouseButtons(pg.QtCore.Qt.MouseButton.NoButton)

    def paint(self, painter, option, widget=None):
        rect = self.boundingRect()
        first = bisect_left(self.times, rect.left())
        last = bisect_right(self.times, rect.right())
        path = QPainterPath()
        for x in self.times[first:last]:
            path.moveTo(x, rect.top())
            path.lineTo(x, rect.bottom())
        painter.setPen(self.pen)
        painter.drawPath(path)
