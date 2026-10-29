"""Shared visual language and original vector navigation icons for the Qt app."""
from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QIcon,QPixmap,QPainter,QPen,QColor,QPainterPath

STYLE="""
QMainWindow { background:#f3f6fa; }
QWidget#contentPage { background:#f3f6fa; }
QWidget { font-family:'Segoe UI'; font-size:11pt; color:#20334a; }
QLabel#pageTitle { font-size:22pt; font-weight:700; color:#172b42; }
QLabel#subtitle,QLabel#muted { color:#64758b; font-size:10pt; }
QLabel#badge { color:#196d66; background:#e4f2ed; border-radius:12px; padding:5px 11px; font-size:9pt; }
QFrame#navigation { background:#172b42; border:none; }
QLabel#navTitle { color:#ffffff; font-size:14pt; font-weight:700; }
QLabel#navCaption { color:#9fb2c8; font-size:9pt; }
QPushButton { background:#ffffff; border:1px solid #ced9e5; border-radius:8px; padding:9px 13px; min-height:20px; font-weight:600; }
QPushButton:hover { background:#edf4f8; border-color:#9cb4c7; }
QPushButton:focus { border:2px solid #268d8c; }
QPushButton:disabled { color:#97a5b5; background:#edf1f5; border-color:#dfe6ed; }
QPushButton#primary { background:#107d80; border-color:#107d80; color:#ffffff; }
QPushButton#primary:hover { background:#086b70; }
QPushButton#primary:disabled { background:#a5c7ca; border-color:#a5c7ca; }
QPushButton[nav="true"] { text-align:left; color:#bbcbdd; background:transparent; border:none; border-radius:8px; padding:10px; min-height:23px; font-weight:500; }
QPushButton[nav="true"]:hover { background:#203b55; color:white; }
QPushButton[nav="true"]:checked { background:#294963; color:white; font-weight:700; }
QPushButton#collapse { background:transparent; border:1px solid #355168; padding:8px; }
QPushButton#collapse:hover { background:#294963; }
QFrame#navDivider { background:#355068; max-height:1px; border:none; }
QFrame#card { background:white; border:1px solid #dde5ee; border-radius:12px; }
QFrame#timelineInspector { background:#ffffff; border-left:1px solid #e0e8ef; }
QFrame#inspectorMetric { background:#f5f9fc; border:1px solid #e2eaf2; border-radius:9px; }
QFrame#pumpSettings { background:#ffffff; border:none; }
QFrame#timelineLegend { background:#ffffff; border-bottom:1px solid #e3eaf1; }
QLabel#metric { font-size:27pt; font-weight:700; color:#172b42; }
QTabWidget::pane { border:none; background:#ffffff; border-radius:12px; }
QTabBar::tab { padding:10px 18px; color:#64758b; }
QTabBar::tab:selected { color:#107d80; border-bottom:3px solid #107d80; }
QGroupBox { border:1px solid #dde5ee; border-radius:10px; margin-top:14px; padding:14px 12px 12px; font-weight:600; background:#ffffff; }
QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 6px; color:#243b53; }
QLineEdit,QComboBox,QDateEdit { border:1px solid #ced9e5; border-radius:7px; padding:7px 9px; background:#ffffff; min-height:20px; selection-background-color:#cce9e7; }
QLineEdit:focus,QComboBox:focus,QDateEdit:focus { border:2px solid #268d8c; }
QComboBox::drop-down,QDateEdit::drop-down { border:none; width:20px; }
QTableView { background:white; alternate-background-color:#f6f9fc; border:1px solid #dfe7ef; border-radius:6px; gridline-color:#edf2f7; selection-background-color:#d9eeeb; selection-color:#183b45; font-size:10pt; }
QHeaderView::section { background:#edf3f8; border:none; border-bottom:1px solid #d8e3ed; padding:10px; font-size:10pt; font-weight:600; }
QProgressBar { border:none; background:#e2eaf1; border-radius:2px; max-height:4px; }
QProgressBar::chunk { background:#107d80; border-radius:2px; }
QStatusBar { color:#6b7d91; background:#f3f6fa; font-size:9pt; border-top:1px solid #e1e8ef; }
QScrollArea { background:transparent; border:none; }
QScrollBar:vertical { width:10px; background:#f0f4f7; margin:0; }
QScrollBar::handle:vertical { background:#c3cfdb; border-radius:5px; min-height:30px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; }
QToolTip { color:#20334a; background:#ffffff; border:1px solid #c8d5e2; padding:7px; font-size:10pt; }
QToolButton { color:#107d80; background:transparent; border:none; border-radius:6px; padding:5px 3px; font-size:10pt; }
QToolButton:hover { background:#e5f1f0; }
QToolButton:checked { color:#085e62; background:#e5f1f0; }
"""

def icon(name,color='#bbcbdd'):
    result=QIcon()
    for size in (20,24,32,48,64):
        pix=QPixmap(size,size);pix.fill(Qt.GlobalColor.transparent);p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.scale(size/24,size/24)
        p.setPen(QPen(QColor(color),1.8,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin));p.setBrush(Qt.BrushStyle.NoBrush)
        if name in ('chart','pulse'):
            if name=='chart':p.drawRoundedRect(QRectF(3,3,18,18),3,3)
            path=QPainterPath(QPointF(3,13));path.lineTo(7,13);path.lineTo(10,7);path.lineTo(14,17);path.lineTo(17,11);path.lineTo(21,11);p.drawPath(path)
        elif name=='archive':
            for x,y in ((3,3),(13,3),(3,13),(13,13)):p.drawRoundedRect(QRectF(x,y,8,8),1.5,1.5)
        elif name=='data':
            p.drawRoundedRect(QRectF(3,3,18,18),2,2);p.drawLine(3,9,21,9);p.drawLine(3,15,21,15);p.drawLine(10,3,10,21)
        elif name=='history':
            p.drawArc(QRectF(4,4,16,16),35*16,285*16);p.drawLine(4,5,4,10);p.drawLine(4,10,9,10);p.drawLine(12,7,12,12);p.drawLine(12,12,16,14)
        elif name=='key':
            p.drawEllipse(QRectF(3,4,9,9));p.drawLine(11,12,21,21);p.drawLine(16,17,19,14);p.drawLine(19,20,22,17)
        elif name=='import':
            p.drawLine(12,3,12,16);p.drawLine(7,11,12,16);p.drawLine(12,16,17,11);p.drawLine(4,16,4,21);p.drawLine(4,21,20,21);p.drawLine(20,21,20,16)
        elif name=='refresh':
            p.drawArc(QRectF(4,4,16,16),25*16,285*16);p.drawLine(20,3,20,9);p.drawLine(20,9,15,9)
        else:
            for y in (6,12,18):p.drawLine(5,y,19,y)
        p.end();result.addPixmap(pix)
    return result
