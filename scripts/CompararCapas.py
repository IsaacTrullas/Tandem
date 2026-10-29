"""Diagnostic comparison; uses a read-only database and never modifies source PDFs."""
import argparse,io,json,sqlite3
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

parser=argparse.ArgumentParser()
parser.add_argument('--image',required=True,type=int)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args()
db=Path(__file__).resolve().parents[1]/'data'/'tandem.sqlite'
conn=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
try:
    original=conn.execute('SELECT image_png FROM report_images WHERE id=?',(args.image,)).fetchone()
    if not original:raise ValueError('Imagen inexistente')
    image=Image.open(io.BytesIO(original[0])).convert('RGB')
    cal=conn.execute('SELECT zero_y FROM plot_calibrations WHERE image_id=?',(args.image,)).fetchone()
    if not cal:raise ValueError('Imagen sin calibración basal')
    plot=conn.execute('SELECT bbox_json FROM quantitative_layers WHERE image_id=? LIMIT 1',(args.image,)).fetchone()
    box=json.loads(plot[0]);top=max(0,int(box[1])-5);bottom=min(image.height,int(cal[0])+44)
    fig,axes=plt.subplots(2,1,figsize=(15,5),gridspec_kw={'height_ratios':[1,1.35]},layout='constrained')
    axes[0].imshow(image.crop((45,top,2310,bottom)));axes[0].axis('off')
    axes[0].set_title('Evidencia original del carril basal',loc='left')
    maximum=1
    for key,label,color in [('basal_setting','Perfil: etiquetas y escalón','#146585'),('basal_control_iq','Barras variables: altura digitalizada','#e47725')]:
        row=conn.execute('SELECT points_json FROM quantitative_layers WHERE image_id=? AND definition_key=?',(args.image,key)).fetchone()
        if not row:continue
        points=json.loads(row[0])
        if not points:continue
        maximum=max(maximum,max(p[3] for p in points))
        axes[1].scatter([p[1]/60 for p in points],[p[3] for p in points],s=2,label=label,color=color)
    axes[1].set(xlim=(0,24),ylim=(0,max(3,maximum*1.2)),xlabel='Hora del reloj del dispositivo',ylabel='U/h')
    axes[1].set_xticks(range(0,25,2));axes[1].grid(alpha=.2);axes[1].legend(markerscale=4,loc='upper right')
    fig.suptitle('Separación de capas del PDF — ejemplo del histórico',fontsize=14)
    fig.text(.01,.001,'Las capas no se suman. Valores gráficos revisables; las dosis originales permanecen en los CSV.',fontsize=9)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output,dpi=150);plt.close(fig)
finally:conn.close()
