"""Original vector symbols shared by the chart, mode lane and readable legend."""
from PySide6.QtCore import Qt,QRectF,QSize
from PySide6.QtGui import QPainterPath,QPainterPathStroker,QColor,QPixmap,QPainter,QIcon,QPen

COLORS={'glucose':'#159575','bg':'#5473ad','bolus':'#3179cd','bolus_005':'#b9407d','iob':'#9665b2',
        'basal':'#3179cd','profile':'#49a4b2','carbs':'#de9130','sleep':'#5276bb',
        'exercise':'#b77b24','alert':'#c85765'}

def symbol(name):
    p=QPainterPath()
    if name in ('bolus','bolus_005'):
        p.moveTo(0,-.5);p.cubicTo(-.17,-.24,-.4,-.05,-.4,.16)
        p.cubicTo(-.4,.58,.4,.58,.4,.16);p.cubicTo(.4,-.05,.17,-.24,0,-.5);p.closeSubpath()
    elif name=='carbs':
        p.moveTo(0,-.28);p.cubicTo(-.4,-.55,-.62,-.16,-.4,.29)
        p.cubicTo(-.25,.58,-.1,.38,0,.43);p.cubicTo(.1,.38,.25,.58,.4,.29)
        p.cubicTo(.62,-.16,.4,-.55,0,-.28);p.closeSubpath()
        p.moveTo(.02,-.29);p.cubicTo(.01,-.5,.16,-.56,.29,-.46);p.cubicTo(.22,-.3,.12,-.26,.02,-.29);p.closeSubpath()
    elif name=='sleep':
        p.addEllipse(QRectF(-.47,-.47,.94,.94));cut=QPainterPath();cut.addEllipse(QRectF(-.13,-.62,.9,.9));p=p.subtracted(cut)
    elif name=='exercise':
        p.addEllipse(QRectF(.04,-.49,.23,.23));lines=QPainterPath();lines.moveTo(.11,-.22);lines.lineTo(-.02,.06);lines.lineTo(.27,.22);lines.lineTo(.42,.45)
        lines.moveTo(-.02,.06);lines.lineTo(-.25,.27);lines.lineTo(-.45,.28)
        lines.moveTo(.07,-.14);lines.lineTo(.29,-.04);lines.lineTo(.43,-.16)
        lines.moveTo(.02,-.17);lines.lineTo(-.25,-.13);lines.lineTo(-.36,.05)
        stroke=QPainterPathStroker();stroke.setWidth(.105);stroke.setCapStyle(Qt.PenCapStyle.RoundCap);stroke.setJoinStyle(Qt.PenJoinStyle.RoundJoin);p.addPath(stroke.createStroke(lines))
    elif name=='alert':
        p.moveTo(0,-.5);p.lineTo(.5,.43);p.lineTo(-.5,.43);p.closeSubpath()
    elif name=='bg':
        p.moveTo(0,-.5);p.lineTo(.5,0);p.lineTo(0,.5);p.lineTo(-.5,0);p.closeSubpath()
    else:p.addEllipse(QRectF(-.4,-.4,.8,.8))
    return p

def icon(name,size=24,color=None):
    pix=QPixmap(size,size);pix.fill(Qt.GlobalColor.transparent);paint=QPainter(pix);paint.setRenderHint(QPainter.RenderHint.Antialiasing)
    c=QColor(color or COLORS.get(name,'#344c65'))
    if name in ('glucose','basal','profile'):
        pen=QPen(c,2.6);pen.setStyle(Qt.PenStyle.DashLine if name=='profile' else Qt.PenStyle.SolidLine);paint.setPen(pen)
        if name=='basal':
            path=QPainterPath();path.moveTo(2,size*.72);path.lineTo(size*.4,size*.72);path.lineTo(size*.4,size*.3);path.lineTo(size-2,size*.3);paint.drawPath(path)
        else:paint.drawLine(2,size//2,size-2,size//2)
    else:
        paint.translate(size/2,size/2);paint.scale(size*.8,size*.8)
        paint.setPen(QPen(c,.07) if name=='bg' else Qt.PenStyle.NoPen)
        paint.setBrush(Qt.GlobalColor.white if name=='bg' else c);paint.drawPath(symbol(name))
    paint.end();return QIcon(pix)
