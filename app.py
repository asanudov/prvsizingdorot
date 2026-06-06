# PRV Sizing Tool · DOROT S300 (v5)
# pip install "streamlit>=1.31" numpy matplotlib pandas reportlab pillow
# streamlit run app.py

import io
import os
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date

# Logo por defecto (desde el repo)
_LOGO_PATH = "logo.png"
_default_logo = None
if os.path.exists(_LOGO_PATH):
    with open(_LOGO_PATH, "rb") as _f:
        _default_logo = _f.read()

st.set_page_config(page_title="PRV Sizing · DOROT S300", page_icon="🔧", layout="wide")

st.markdown("""<style>
[data-testid="stSidebar"]{min-width:380px!important;max-width:380px!important;}
[data-testid="stNumberInput"] input{font-size:13px!important;}
</style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  DATOS
# ══════════════════════════════════════════════
DN   = [40,50,65,80,100,150,200,250,300,350,400,450,500,600]
NOM  = ["1½″","2″","2½″","3″","4″","6″","8″","10″","12″","14″","16″","18″","20″","24″"]
KV_G = [43,43,43,115,167,407,676,1160,1600,1600,3000,3150,3300,6500]
CV_G = [50,50,50,133,195,475,790,1360,1900,1900,3500,3700,3860,7600]
KV_A = [60,60,None,140,190,460,770,1310,None,None,None,None,None,None]
CV_A = [70,70,None,164,222,537,900,1533,None,None,None,None,None,None]
LTP_X=[0.00,0.04,0.08,0.12,0.16,0.20,0.25,0.30,0.40,0.50,0.60,0.70,0.80,0.90,1.00]
LTP_Y=[0,18,32,43,52,59,65,71,80,86,91,95,97,99,100]
PV_MCA=-9.0; SIGMA_CRIT=1.45; SIGMA_NOISY=2.00; MCA_TO_PSI=1.42233

# ══════════════════════════════════════════════
#  CONVERSIONES Y CÁLCULOS
# ══════════════════════════════════════════════
_BAR={"bar":1.0,"psi":0.0689476,"kg/cm²":0.980665,"mca":0.0980665}
_M3H={"m³/h":1.0,"L/s":3.6,"GPM":0.22712}
def to_bar(v,u): return v*_BAR[u]
def fr_bar(v,u): return v/_BAR[u]
def to_m3h(v,u): return v*_M3H[u]
def calc_kv(q,dp): return q/np.sqrt(dp) if dp>0 else 0.0
def calc_ap(kn):   return float(np.interp(np.clip(kn,0,1),LTP_X,LTP_Y))
def calc_vel(q,d): return (q/3600)/(np.pi*((d/1000)/2)**2)
def calc_sig(p1m,p2m):
    dp=p1m-p2m; return (p1m-PV_MCA)/dp if dp>0 else None
def zona(s):
    if s is None or s<SIGMA_CRIT: return "destruct"
    return "safe" if s>=SIGMA_NOISY else "noisy"
def z_bnd(s,p2): return (s*p2+9)/(s-1)

ZONA_MAP={"safe":   ("🟢","Condiciones seguras",   "success"),
          "noisy":  ("🟡","Operación ruidosa",      "warning"),
          "destruct":("🔴","Cavitación destructiva","error")}

# ══════════════════════════════════════════════
#  HTML CARDS
# ══════════════════════════════════════════════
def _card(label,value,unit=""):
    u_html=f"<div style='font-size:9px;color:#94A3B8;margin-top:2px;'>{unit}</div>" if unit else ""
    return f"""<div style='flex:1;min-width:0;border:1.5px solid #E2E8F0;border-radius:12px;
               padding:12px 6px;text-align:center;background:#fff;
               box-shadow:0 2px 6px rgba(0,0,0,0.07);'>
      <div style='font-size:9px;color:#94A3B8;font-weight:700;text-transform:uppercase;
                  letter-spacing:0.5px;margin-bottom:5px;overflow:hidden;text-overflow:ellipsis;
                  white-space:nowrap;' title='{label}'>{label}</div>
      <div style='font-size:20px;font-weight:800;color:#1E293B;line-height:1.15;'>{value}</div>
      {u_html}</div>"""

def cards_row(title,items,accent="#1B2A4A"):
    inner="".join(_card(l,v,u) for l,v,u in items)
    return f"""<div style='margin:10px 0 4px 0;'>
      <div style='font-size:10px;font-weight:800;color:{accent};text-transform:uppercase;
                  letter-spacing:1.2px;margin-bottom:8px;'>{title}</div>
      <div style='display:flex;gap:8px;'>{inner}</div></div>"""

def banner_zona(z,sig):
    ico,lbl,kind=ZONA_MAP[z]; sv=f"σ = {sig:.1f}" if sig else "σ = —"
    getattr(st,kind)(f"{ico} **{lbl}** — {sv}")

# ══════════════════════════════════════════════
#  FIGURAS
# ══════════════════════════════════════════════
def make_ltp_fig(kn_a,op_a,kn_b=None,op_b=None,din=True,figsize=(5,4)):
    fig,ax=plt.subplots(figsize=figsize)
    ax.plot(LTP_X,LTP_Y,lw=2.5,color="#16A085",label="LTP — DOROT S300")
    ax.axvspan(0.10,0.80,alpha=0.07,color="green",label="Zona óptima")
    ax.axvline(0.10,ls=":",lw=1,color="green",alpha=0.6)
    ax.axvline(0.80,ls=":",lw=1,color="green",alpha=0.6)
    kp=min(kn_a,1.0)
    ax.plot(kp,op_a,"o",ms=9,color="crimson",zorder=5,
            label=f"{'🅐 Qmáx' if din else 'Diseño'}  {kp:.2f}→{op_a:.0f}%")
    ax.axvline(kp,ls="--",lw=1,color="crimson",alpha=0.4)
    ax.axhline(op_a,ls="--",lw=1,color="crimson",alpha=0.4)
    if kn_b is not None and op_b is not None:
        kbp=min(kn_b,1.0)
        ax.plot(kbp,op_b,"s",ms=8,color="darkorange",zorder=5,
                label=f"🅑 Qmín  {kbp:.2f}→{op_b:.0f}%")
        ax.axvline(kbp,ls=":",lw=1,color="darkorange",alpha=0.4)
        ax.axhline(op_b,ls=":",lw=1,color="darkorange",alpha=0.4)
    ax.set_xlabel("Kn / Kv",fontsize=9); ax.set_ylabel("Apertura (%)",fontsize=9)
    ax.set_xlim(0,1); ax.set_ylim(0,100)
    ax.grid(True,alpha=0.2); ax.legend(fontsize=8,loc="lower right")
    ax.set_title("Apertura vs Kn/Kv — LTP DOROT S300",fontsize=10)
    plt.tight_layout(); return fig

def make_cav_fig(p1a,p2m,sig_a,p1b=None,sig_b=None,has_b=False,figsize=(5,4)):
    p1_vals=[p1a]+([p1b] if has_b and p1b else [])
    xmax=max(p2m*2.5,100); ymax=max(max(p1_vals)*1.5,260)
    fig,ax=plt.subplots(figsize=figsize)
    xs=np.linspace(0,xmax,500)
    Ln=np.minimum(z_bnd(SIGMA_NOISY,xs),ymax)
    Ld=np.minimum(z_bnd(SIGMA_CRIT,xs),ymax)
    ax.fill_between(xs,0,Ln,color="#27AE60",alpha=0.28,label=f"Segura σ≥{SIGMA_NOISY}")
    ax.fill_between(xs,Ln,Ld,color="#95A5A6",alpha=0.45,label="Ruidosa")
    ax.fill_between(xs,Ld,ymax,color="#E74C3C",alpha=0.28,label="Cav. destruct.")
    ax.plot(xs,Ln,"--",lw=1,color="#27AE60",alpha=0.7)
    ax.plot(xs,Ld,"--",lw=1,color="#E74C3C",alpha=0.7)
    right=p2m<xmax*0.6; xoff=xmax*(0.08 if right else -0.28)
    ax.plot(p2m,p1a,"o",color="crimson",ms=9,zorder=6)
    ax.annotate(f"{'🅐 ' if has_b else ''}P1={p1a:.1f}\nσ={sig_a:.1f}",
                xy=(p2m,p1a),xytext=(p2m+xoff,p1a+ymax*0.04),fontsize=7,
                bbox=dict(boxstyle="round,pad=0.2",fc="white",ec="crimson",alpha=0.9),
                arrowprops=dict(arrowstyle="->",color="crimson",lw=0.8))
    if has_b and p1b and sig_b:
        ax.plot(p2m,p1b,"s",color="darkorange",ms=8,zorder=6)
        ax.annotate(f"🅑 P1={p1b:.1f}\nσ={sig_b:.1f}",
                    xy=(p2m,p1b),xytext=(p2m+xoff,p1b-ymax*0.12),fontsize=7,
                    bbox=dict(boxstyle="round,pad=0.2",fc="white",ec="darkorange",alpha=0.9),
                    arrowprops=dict(arrowstyle="->",color="darkorange",lw=0.8))
    axb=ax.twiny(); axb.set_xlim(0,xmax*MCA_TO_PSI)
    axb.set_xlabel("P2 (psi)",fontsize=8,color="gray")
    axb.tick_params(axis="x",labelsize=7,colors="gray")
    ax.set_xlabel("P2 — Presión ajuste aguas abajo (mca)",fontsize=9)
    ax.set_ylabel("P1 — Presión aguas arriba (mca)",fontsize=9)
    ax.set_xlim(0,xmax); ax.set_ylim(0,ymax)
    ax.grid(True,alpha=0.2); ax.legend(fontsize=7,loc="lower right")
    ax.set_title(f"Cavitación DOROT S300 — σ crítico={SIGMA_CRIT}",fontsize=10)
    plt.tight_layout(); return fig

# ══════════════════════════════════════════════
#  PDF
# ══════════════════════════════════════════════
def generate_pdf(logo_bytes,d):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors as C
        from reportlab.lib.styles import ParagraphStyle as PS
        from reportlab.platypus import (SimpleDocTemplate,Paragraph,Table,
                                         TableStyle,Image as RLI,Spacer,HRFlowable)
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        return None
    buf=io.BytesIO(); PAGE_W,_=A4; MARGIN=1.8*cm; FW=PAGE_W-2*MARGIN
    doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=MARGIN,leftMargin=MARGIN,
                          topMargin=MARGIN,bottomMargin=2*cm)
    NAVY=C.HexColor('#1B2A4A'); TEAL=C.HexColor('#00D4AA')
    LGRAY=C.HexColor('#F8F9FA'); MGRAY=C.HexColor('#E9ECEF')
    DKGRY=C.HexColor('#6C757D'); NAVY2=C.HexColor('#2C4A7C')
    GRN=C.HexColor('#28A745'); WARN=C.HexColor('#FD7E14'); ERR=C.HexColor('#DC3545')
    def sty(n,**kw): return PS(n,**kw)
    H2=sty('h2',fontName='Helvetica-Bold',fontSize=11,textColor=NAVY,spaceBefore=10,spaceAfter=4)
    H3=sty('h3',fontName='Helvetica-Bold',fontSize=9,textColor=NAVY2,spaceBefore=6,spaceAfter=3)
    BODY=sty('bd',fontName='Helvetica',fontSize=9,leading=14)
    FOOT=sty('ft',fontName='Helvetica',fontSize=8,textColor=DKGRY,alignment=TA_CENTER)
    def TS(hc=NAVY):
        return TableStyle([
            ('BACKGROUND',(0,0),(-1,0),hc),('TEXTCOLOR',(0,0),(-1,0),C.white),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,0),9),
            ('FONTNAME',(0,1),(-1,-1),'Helvetica'),('FONTSIZE',(0,1),(-1,-1),9),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[C.white,LGRAY]),
            ('GRID',(0,0),(-1,-1),0.5,MGRAY),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8)])
    story=[]
    hdr_txt=(f'<font color="white"><b>Reporte de Dimensionamiento PRV</b><br/>'
             f'DOROT S300 — Modelos 30 / 31<br/></font>'
             f'<font color="#A8C4D4">Fecha: {date.today().strftime("%d/%m/%Y")}</font>')
    left=Paragraph('<font color="white"><b>Aquestia</b></font>',
                   sty('lh',fontName='Helvetica-Bold',fontSize=14,textColor=C.white))
    if logo_bytes:
        try: left=RLI(io.BytesIO(logo_bytes),width=4.5*cm,height=1.4*cm,kind='proportional')
        except: pass
    hdr=Table([[left,Paragraph(hdr_txt,sty('rh',fontName='Helvetica',fontSize=11,leading=16))]],
              colWidths=[FW*0.38,FW*0.62])
    hdr.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),NAVY),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),14),('BOTTOMPADDING',(0,0),(-1,-1),14),
        ('LEFTPADDING',(0,0),(-1,-1),14),('RIGHTPADDING',(0,0),(-1,-1),14)]))
    story.append(hdr); story.append(HRFlowable(width=FW,thickness=3,color=TEAL,spaceAfter=4))
    story.append(Spacer(1,0.2*cm))
    story.append(Paragraph("1. Datos de Entrada",H2))
    e=[['Parámetro','Valor','Unidad']]
    if d['din']:
        e+=[['Caudal máximo (Qmáx)',f"{d['qmax_ui']:.1f}",d['u_q']],
            ['Caudal mínimo (Qmín)',f"{d['qmin_ui']:.1f}" if d.get('qmin_ui') else '—',d['u_q']],
            ['P1 mínima — Esc. A',f"{d['p1min_ui']:.1f}",d['u_p']],
            ['P1 máxima — Esc. B',f"{d['p1max_ui']:.1f}" if d.get('p1max_ui') else '—',d['u_p']]]
    else:
        e+=[['Caudal de diseño',f"{d['qmax_ui']:.1f}",d['u_q']],
            ['Presión entrada P1',f"{d['p1min_ui']:.1f}",d['u_p']]]
    e+=[['Presión de ajuste P2',f"{d['p2_ui']:.1f}",d['u_p']],
        ['Diámetro de tubería',f"{d['pipe_mm']} mm",f"({d['pipe_nom']})"],
        ['Diámetro de válvula',f"{d['dn_mm']} mm",f"({d['dn_nom']})"],
        ['Tipo de cuerpo',d['cuerpo'],'—']]
    t_e=Table(e,colWidths=[FW*0.55,FW*0.28,FW*0.17]); t_e.setStyle(TS()); story.append(t_e)
    story.append(Spacer(1,0.2*cm))
    story.append(Paragraph("2. Válvula Seleccionada — DOROT S300",H2))
    v=[['Parámetro','Valor'],['Modelo','DOROT S300  (Mod. 30 / 31)'],
       ['Tamaño válvula',f"{d['dn_mm']} mm  ({d['dn_nom']})"],
       ['Diámetro tubería',f"{d['pipe_mm']} mm  ({d['pipe_nom']})"],
       ['Tipo de cuerpo',d['cuerpo']],['Kv (100%)',str(d['kv_v'])],['Cv (100%)',str(d['cv_v'])],
       ['Presión nominal','16 bar (Mod. 30)  /  25 bar (Mod. 31)']]
    t_v=Table(v,colWidths=[FW*0.55,FW*0.45]); t_v.setStyle(TS()); story.append(t_v)
    story.append(Spacer(1,0.2*cm))
    story.append(Paragraph("3. Parámetros de Cálculo",H2))
    def ctbl(rows):
        t=Table(rows,colWidths=[FW*0.52,FW*0.28,FW*0.20]); t.setStyle(TS(hc=NAVY2)); return t
    lbl_a="Escenario A — Qmáx/P1 mín  (dimensionamiento caudal máximo)" if d['din'] else "Escenario de diseño"
    story.append(Paragraph(lbl_a,H3))
    story.append(ctbl([['Parámetro','Valor','Unidad'],
        ['Caudal Q',f"{d['qmax_m3h']:.1f}",'m³/h'],['P1',f"{d['p1a_mca']:.1f}",'mca'],
        ['P2 ajuste',f"{d['p2_mca']:.1f}",'mca'],['ΔP',f"{d['dpa_mca']:.1f}",'mca'],
        ['Kv requerido',f"{d['kv_a']:.1f}",'m³/h/√bar'],['Kn / Kv',f"{d['kn_a']:.2f}",'—'],
        ['% Apertura',f"{d['op_a']:.1f}",'%'],['Velocidad',f"{d['vel_a']:.1f}",'m/s'],
        ['σ cavitación',f"{d['sig_a']:.2f}" if d['sig_a'] else '—','—'],
        ['Zona',ZONA_MAP[d['z_a']][1],'']]))
    if d.get('has_b'):
        story.append(Spacer(1,0.15*cm))
        story.append(Paragraph("Escenario B — Qmín/P1 máx  (verificación cavitación)",H3))
        story.append(ctbl([['Parámetro','Valor','Unidad'],
            ['Caudal Q',f"{d['qmin_m3h']:.1f}",'m³/h'],['P1',f"{d['p1b_mca']:.1f}",'mca'],
            ['P2 ajuste',f"{d['p2_mca']:.1f}",'mca'],['ΔP',f"{d['dpb_mca']:.1f}",'mca'],
            ['Kv requerido',f"{d['kv_b']:.1f}",'m³/h/√bar'],['Kn / Kv',f"{d['kn_b']:.2f}",'—'],
            ['% Apertura',f"{d['op_b']:.1f}",'%'],['Velocidad',f"{d['vel_b']:.1f}",'m/s'],
            ['σ cavitación',f"{d['sig_b']:.2f}" if d.get('sig_b') else '—','—'],
            ['Zona',ZONA_MAP[d['z_b']][1],'']]))
    story.append(Spacer(1,0.2*cm))
    story.append(Paragraph("4. Gráficas",H2))
    fl=make_ltp_fig(d['kn_a'],d['op_a'],d.get('kn_b'),d.get('op_b'),d['din'],figsize=(4.5,3.5))
    lbuf=io.BytesIO(); fl.savefig(lbuf,format='png',dpi=150,bbox_inches='tight')
    plt.close(fl); lbuf.seek(0)
    fc=make_cav_fig(d['p1a_mca'],d['p2_mca'],d['sig_a'],d.get('p1b_mca'),
                    d.get('sig_b'),d.get('has_b',False),figsize=(4.5,3.5))
    cbuf=io.BytesIO(); fc.savefig(cbuf,format='png',dpi=150,bbox_inches='tight')
    plt.close(fc); cbuf.seek(0)
    iw=FW*0.48; ih=iw*3.5/4.5
    it=Table([[RLI(lbuf,width=iw,height=ih),RLI(cbuf,width=iw,height=ih)]],
             colWidths=[FW*0.5,FW*0.5])
    it.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                             ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
    story.append(it); story.append(Spacer(1,0.2*cm))
    story.append(Paragraph("5. Conclusiones y Recomendaciones",H2))
    za=d['z_a']; zb=d.get('z_b'); hb=d.get('has_b',False)
    concs=[]
    if za=='safe' and (not hb or zb=='safe'):
        concs.append(("✅ Cavitación — ","Condiciones seguras en todos los escenarios.",GRN))
    elif za=='destruct' or zb=='destruct':
        concs.append(("🚨 Cavitación — ","CAVITACIÓN DESTRUCTIVA. PRV en cascada o tapón U-Plug/V-Plug.",ERR))
    else:
        concs.append(("⚠️ Cavitación — ",f"Operación ruidosa (σ={d['sig_a']:.1f}). Tapón V-Plug recomendado.",WARN))
    if 0.10<=d['kn_a']<=0.80:
        concs.append(("✅ Apertura A — ",f"Apertura {d['op_a']:.1f}% en rango óptimo (10%–80%).",GRN))
    elif d['kn_a']>0.80:
        concs.append(("⚠️ Apertura A — ",f"Apertura {d['op_a']:.1f}% alta. Evaluar tamaño mayor.",WARN))
    else:
        concs.append(("⚠️ Apertura A — ",f"Apertura {d['op_a']:.1f}% baja. Evaluar tamaño menor.",WARN))
    if hb:
        if 0.10<=d['kn_b']<=0.80:
            concs.append(("✅ Apertura B — ",f"Apertura {d['op_b']:.1f}% en rango óptimo.",GRN))
        else:
            concs.append(("⚠️ Apertura B — ",f"Apertura {d['op_b']:.1f}% fuera de rango. Verificar.",WARN))
    concs.append(("📐 Selección — ",
                  f"Válvula DOROT S300 {d['dn_mm']} mm. "
                  f"Kv req. {d['kv_a']:.1f} / Kv nominal {d['kv_v']} (Kn/Kv={d['kn_a']:.2f}).",NAVY))
    for pre,txt,col in concs:
        ct=Table([[Paragraph(f"<b>{pre}</b>{txt}",BODY)]],colWidths=[FW])
        ct.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
                                 ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
                                 ('LINEBELOW',(0,0),(-1,-1),0.5,MGRAY)]))
        story.append(ct)
    story.append(Spacer(1,0.4*cm))
    story.append(HRFlowable(width=FW,thickness=2,color=TEAL))
    story.append(Spacer(1,0.2*cm))
    story.append(Paragraph("Generado con PRV Sizing Tool · DOROT S300 — Aquestia",FOOT))
    doc.build(story); buf.seek(0); return buf.getvalue()

# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Parámetros de entrada")
    st.divider()

    # 1. Diámetro tubería
    st.markdown("**1 · Diámetro de tubería**")
    u_dn=st.radio("Unidad Ø",["mm","in"],horizontal=True,key="u_dn")
    if u_dn=="mm":
        sel=st.selectbox("Ø Tubería",DN,format_func=lambda x:f"{x} mm"); idx=DN.index(sel)
    else:
        sel_in=st.selectbox("Ø Tubería",NOM); idx=NOM.index(sel_in)

    # 1b. ¿Misma DN para la válvula?
    st.markdown("**¿Misma DN para la válvula?**")
    same_diam = st.radio("",["Sí","No"],horizontal=True,key="sdiam",
                          label_visibility="collapsed") == "Sí"
    if not same_diam:
        v_mm=st.selectbox("Ø Válvula",DN,index=idx,
                           format_func=lambda x:f"{x} mm ({NOM[DN.index(x)]})",key="vsel")
        valve_idx=DN.index(v_mm)
    else:
        valve_idx=idx

    st.divider()

    # 2. Tipo de cuerpo
    st.markdown("**2 · Tipo de cuerpo**")
    cuerpo=st.radio("Cuerpo",["Globo","Angular"],horizontal=True)
    st.divider()

    # 3. Caudal y presiones de entrada
    st.markdown("**3 · Caudal y presiones de entrada**")
    din=st.toggle("Flujo dinámico",value=True)
    u_q=st.radio("Unidad Q",["m³/h","L/s","GPM"],horizontal=True,key="u_q")
    u_p=st.radio("Unidad P",["bar","psi","kg/cm²","mca"],horizontal=True,key="u_p")
    if din:
        st.caption("🅐  Qmáx — P1 mínima")
        ca1,ca2=st.columns(2)
        qmax_ui =ca1.number_input("Qmáx", min_value=0.01,value=None,placeholder="ej. 50", key="qmax")
        p1min_ui=ca2.number_input("P1 mín",min_value=0.01,value=None,placeholder="ej. 6.0",key="p1mn")
        st.caption("🅑  Qmín — P1 máxima")
        cb1,cb2=st.columns(2)
        qmin_ui =cb1.number_input("Qmín", min_value=0.0, value=None,placeholder="ej. 10", key="qmin")
        p1max_ui=cb2.number_input("P1 máx",min_value=0.01,value=None,placeholder="ej. 10", key="p1mx")
        qmax_m3h=to_m3h(qmax_ui, u_q) if qmax_ui  is not None else None
        qmin_m3h=to_m3h(qmin_ui, u_q) if (qmin_ui is not None and qmin_ui>0) else None
        p1a_bar =to_bar(p1min_ui,u_p) if p1min_ui is not None else None
        p1b_bar =to_bar(p1max_ui,u_p) if (p1max_ui is not None and qmin_m3h is not None) else None
    else:
        qdes_ui =st.number_input("Q diseño",min_value=0.01,value=None,placeholder="ej. 50", key="qdes")
        p1_ui   =st.number_input("P1",      min_value=0.01,value=None,placeholder="ej. 8.0",key="p1st")
        qmax_m3h=to_m3h(qdes_ui,u_q) if qdes_ui is not None else None
        qmin_m3h=None; p1a_bar=to_bar(p1_ui,u_p) if p1_ui is not None else None; p1b_bar=None
    st.divider()

    # 4. Presión de ajuste
    st.markdown("**4 · Presión de ajuste aguas abajo**")
    p2_ui =st.number_input("P2 ajuste",min_value=0.0,value=None,placeholder="ej. 4.0",key="p2adj")
    p2_bar=to_bar(p2_ui,u_p) if p2_ui is not None else None
    st.divider()

    # Logo
    logo_bytes = _default_logo

# ══════════════════════════════════════════════
#  PANEL PRINCIPAL
# ══════════════════════════════════════════════
st.markdown("<h1 style='font-size:28px;'> Dimensionamiento PRV — DOROT S300</h1>", unsafe_allow_html=True)
st.caption("Modelos 30 (PN 16 bar) / 31 (PN 25 bar)  ·  Válvulas reductoras de presión")
st.caption("Desarrollado por M.I. Alan Sañudo, Ingeniería de Aplicaciones")

# Kv válvula (usa valve_idx) — velocidad usa idx (diámetro tubería)
KVL=KV_G if cuerpo=="Globo" else KV_A
CVL=CV_G if cuerpo=="Globo" else CV_A
kv_v=KVL[valve_idx]; cv_v=CVL[valve_idx]
if kv_v is None:
    st.warning(f"Angular no disponible en {NOM[valve_idx]}. Se usa Globo.")
    kv_v=KV_G[valve_idx]; cv_v=CV_G[valve_idx]

if any(v is None for v in [qmax_m3h,p1a_bar,p2_bar]):
    st.info("⬅️  Completa todos los parámetros de entrada para ver los resultados.")
    st.stop()

dpa_bar=p1a_bar-p2_bar
if dpa_bar<=0:
    st.error("⚠️  P1 debe ser mayor que P2 ajuste."); st.stop()

# Cálculos A  — velocidad con DN tubería (idx), Kv con DN válvula (valve_idx)
p1a_mca=fr_bar(p1a_bar,"mca"); p2_mca=fr_bar(p2_bar,"mca")
kv_a=calc_kv(qmax_m3h,dpa_bar); kn_a=kv_a/kv_v; op_a=calc_ap(kn_a)
sig_a=calc_sig(p1a_mca,p2_mca); z_a=zona(sig_a)
vel_a=calc_vel(qmax_m3h,DN[idx])          # ← diámetro tubería

# Cálculos B
has_b=bool(din and qmin_m3h and p1b_bar)
p1b_mca=kv_b=kn_b=op_b=sig_b=z_b=vel_b=dpb_bar=None
if has_b:
    dpb_bar=p1b_bar-p2_bar
    if dpb_bar<=0:
        st.warning("P1 máx debe ser > P2. Esc. B omitido."); has_b=False
    else:
        p1b_mca=fr_bar(p1b_bar,"mca")
        kv_b=calc_kv(qmin_m3h,dpb_bar); kn_b=kv_b/kv_v; op_b=calc_ap(kn_b)
        sig_b=calc_sig(p1b_mca,p2_mca); z_b=zona(sig_b)
        vel_b=calc_vel(qmin_m3h,DN[idx])  # ← diámetro tubería

# ══════════════════════════════════════════════
#  CARDS
# ══════════════════════════════════════════════
st.divider()
vel_items=[("Velocidad",f"{vel_a:.1f}","m/s")]
if has_b:
    vel_items=[("Vel. 🅐",f"{vel_a:.1f}","m/s"),("Vel. 🅑",f"{vel_b:.1f}","m/s")]

# Si diámetros distintos, mostrar ambos
if same_diam:
    top_items=[("Válvula",f"{DN[valve_idx]} mm",NOM[valve_idx]),
               ("Kv (100%)",str(kv_v),""),("Cv (100%)",str(cv_v),"")] + vel_items
else:
    top_items=[("Tubería",f"{DN[idx]} mm",NOM[idx]),
               ("Válvula",f"{DN[valve_idx]} mm",NOM[valve_idx]),
               ("Kv (100%)",str(kv_v),""),("Cv (100%)",str(cv_v),"")] + vel_items

st.markdown(cards_row("Datos de entrada",top_items), unsafe_allow_html=True)

st.markdown(cards_row(
    "🅐 Parámetros — Qmáx / P1 mín" if din else "Parámetros de diseño",
    [("ΔP",      f"{fr_bar(dpa_bar,u_p):.1f}",u_p),
     ("Kv req.", f"{kv_a:.1f}",""),("Kn/Kv",f"{kn_a:.1f}",""),
     ("Apertura",f"{op_a:.0f}","%"),("σ",f"{sig_a:.1f}" if sig_a else "—","")],
    accent="#C0392B"), unsafe_allow_html=True)
banner_zona(z_a,sig_a)

if has_b:
    st.markdown(cards_row("🅑 Parámetros — Qmín / P1 máx",
        [("ΔP",      f"{fr_bar(dpb_bar,u_p):.1f}",u_p),
         ("Kv req.", f"{kv_b:.1f}",""),("Kn/Kv",f"{kn_b:.1f}",""),
         ("Apertura",f"{op_b:.0f}","%"),("σ",f"{sig_b:.1f}" if sig_b else "—","")],
        accent="#E67E22"), unsafe_allow_html=True)
    banner_zona(z_b,sig_b)

st.divider()

# ══════════════════════════════════════════════
#  GRÁFICOS
# ══════════════════════════════════════════════
gcol1,gcol2=st.columns(2)
with gcol1:
    st.subheader("📈 Curva característica LTP")
    fig_ltp=make_ltp_fig(kn_a,op_a,kn_b,op_b,din)
    st.pyplot(fig_ltp); plt.close(fig_ltp)
with gcol2:
    st.subheader("💧 Diagrama de cavitación")
    fig_cav=make_cav_fig(p1a_mca,p2_mca,sig_a,p1b_mca,sig_b,has_b)
    st.pyplot(fig_cav); plt.close(fig_cav)

# ══════════════════════════════════════════════
#  DIAGNÓSTICO (ancho completo)
# ══════════════════════════════════════════════
st.divider()
st.subheader("🏥 Diagnóstico y recomendaciones")

def msg_cav(z,sig,lbl=""):
    sv=f"{sig:.1f}" if sig else "—"
    if z=="destruct":
        st.error(f"🚨 **{lbl}Cav. destructiva** (σ={sv})\n\n- PRV en cascada\n- Tapón U-Plug/V-Plug")
    elif z=="noisy":
        st.warning(f"⚠️ **{lbl}Op. ruidosa** (σ={sv}). Considerar tapón V-Plug.")
    else:
        st.success(f"✅ **{lbl}Condiciones seguras** (σ={sv}).")

def msg_ap(kn,op,vel,lbl=""):
    if kn>0.80:    st.warning(f"⚠️ {lbl}Apertura {op:.0f}% alta — considera tamaño mayor.")
    elif kn<0.10:  st.warning(f"⚠️ {lbl}Apertura {op:.0f}% baja — considera tamaño menor.")
    else:          st.success(f"✅ {lbl}Apertura óptima {op:.0f}%.  V = {vel:.1f} m/s.")

msg_cav(z_a,sig_a,"🅐 " if din else "")
msg_ap(kn_a,op_a,vel_a,"🅐 " if din else "")
if has_b:
    msg_cav(z_b,sig_b,"🅑 ")
    msg_ap(kn_b,op_b,vel_b,"🅑 ")

# ── COMPARATIVA DE TAMAÑOS (abajo del diagnóstico)
st.markdown("#### 📊 Comparativa de tamaños disponibles")
if not same_diam:
    st.caption(f"💡 Tubería: **{DN[idx]} mm** — Válvula seleccionada: **{DN[valve_idx]} mm** "
               f"({NOM[valve_idx]}). Elige el tamaño en el panel lateral.")

KV_SEL=KV_G if cuerpo=="Globo" else KV_A
rows=[]
for i in range(len(DN)):
    kvi=KV_SEL[i] if KV_SEL[i] else KV_G[i]
    ri_a=kv_a/kvi; oi_a=calc_ap(ri_a); ok_a=0.10<=ri_a<=0.80
    # Etiqueta de fila
    tag=""
    if i==valve_idx: tag="← válvula"
    if i==idx and not same_diam: tag=(tag+" (tubería)").strip()
    if has_b:
        ri_b=kv_b/kvi; oi_b=calc_ap(ri_b)
        ok=ok_a and 0.10<=ri_b<=0.80
        rows.append({"Tamaño":f"{DN[i]}mm ({NOM[i]})","Kv":kvi,
                     "Kn/Kv 🅐":ri_a,"Ap.🅐 %":oi_a,
                     "Kn/Kv 🅑":ri_b,"Ap.🅑 %":oi_b,
                     "":("✅ " if ok else "")+tag})
    else:
        ok=ok_a
        rows.append({"Tamaño":f"{DN[i]}mm ({NOM[i]})","Kv":kvi,
                     "Kn/Kv":ri_a,"Apert. %":oi_a,
                     "":("✅ " if ok else "")+tag})

df=pd.DataFrame(rows)

def hl(row):
    k="Kn/Kv 🅐" if has_b else "Kn/Kv"
    ok=0.10<=row[k]<=0.80
    if has_b: ok=ok and 0.10<=row["Kn/Kv 🅑"]<=0.80
    return [f"background-color:{'#d4edda' if ok else ''}"]*len(row)

if has_b:
    fmt={"Kn/Kv 🅐":"{:.2f}","Ap.🅐 %":"{:.0f}","Kn/Kv 🅑":"{:.2f}","Ap.🅑 %":"{:.0f}"}
else:
    fmt={"Kn/Kv":"{:.2f}","Apert. %":"{:.0f}"}

st.dataframe(df.style.apply(hl,axis=1).format(fmt), hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════
#  TABLA RESUMEN
# ══════════════════════════════════════════════
st.divider()
with st.expander("📋 Ver tabla de resultados completa"):
    ql=qmax_ui if din else qdes_ui; pl=p1min_ui if din else p1_ui
    filas=[("Tubería",f"{DN[idx]} mm — {NOM[idx]}"),
           ("Válvula",f"{DN[valve_idx]} mm — {NOM[valve_idx]}"),
           ("Cuerpo",cuerpo),("Kv (100%)",str(kv_v)),("Cv (100%)",str(cv_v)),
           ("P2 ajuste",f"{p2_ui:.1f} {u_p}"),
           ("— ESC. A —" if din else "— DISEÑO —",""),
           (f"Q{'máx' if din else ''}",f"{ql:.1f} {u_q} → {qmax_m3h:.1f} m³/h"),
           ("P1"+(" mín" if din else ""),f"{pl:.1f} {u_p} → {p1a_bar:.2f} bar"),
           ("ΔP",f"{fr_bar(dpa_bar,u_p):.1f} {u_p}"),
           ("Kv req.",f"{kv_a:.1f}"),("Kn/Kv",f"{kn_a:.2f}"),
           ("Apertura",f"{op_a:.1f} %"),("Velocidad",f"{vel_a:.1f} m/s"),
           ("σ",f"{sig_a:.2f}" if sig_a else "—"),("Zona",ZONA_MAP[z_a][1])]
    if has_b:
        filas+=[("— ESC. B —",""),
                ("Qmín",f"{qmin_ui:.1f} {u_q} → {qmin_m3h:.1f} m³/h"),
                ("P1 máx",f"{p1max_ui:.1f} {u_p} → {p1b_bar:.2f} bar"),
                ("ΔP",f"{fr_bar(dpb_bar,u_p):.1f} {u_p}"),
                ("Kv req.",f"{kv_b:.1f}"),("Kn/Kv",f"{kn_b:.2f}"),
                ("Apertura",f"{op_b:.1f} %"),("Velocidad",f"{vel_b:.1f} m/s"),
                ("σ",f"{sig_b:.2f}" if sig_b else "—"),("Zona",ZONA_MAP[z_b][1])]
    st.table(pd.DataFrame(filas,columns=["Parámetro","Valor"]))

# ══════════════════════════════════════════════
#  PDF
# ══════════════════════════════════════════════
st.divider(); st.subheader("📄 Reporte PDF Profesional")
st.caption("Datos · válvula · parámetros · gráficas · conclusiones")
if "pdf_bytes" not in st.session_state: st.session_state.pdf_bytes=None
c1,c2,_=st.columns([1,1,3])
with c1:
    if st.button("📄 Generar PDF",type="primary",use_container_width=True):
        rd={"din":din,"u_q":u_q,"u_p":u_p,"cuerpo":cuerpo,
            "qmax_ui":qmax_ui if din else qdes_ui,
            "qmin_ui":qmin_ui if din else None,
            "p1min_ui":p1min_ui if din else p1_ui,
            "p1max_ui":p1max_ui if (din and has_b) else None,
            "p2_ui":p2_ui,
            "pipe_mm":DN[idx],"pipe_nom":NOM[idx],
            "dn_mm":DN[valve_idx],"dn_nom":NOM[valve_idx],
            "kv_v":kv_v,"cv_v":cv_v,
            "qmax_m3h":qmax_m3h,"p1a_mca":p1a_mca,"p2_mca":p2_mca,
            "dpa_mca":fr_bar(dpa_bar,"mca"),
            "kv_a":kv_a,"kn_a":kn_a,"op_a":op_a,"vel_a":vel_a,
            "sig_a":sig_a,"z_a":z_a,"has_b":has_b}
        if has_b:
            rd.update({"qmin_m3h":qmin_m3h,"p1b_mca":p1b_mca,
                       "dpb_mca":fr_bar(dpb_bar,"mca"),
                       "kv_b":kv_b,"kn_b":kn_b,"op_b":op_b,"vel_b":vel_b,
                       "sig_b":sig_b,"z_b":z_b})
        with st.spinner("Generando reporte..."):
            st.session_state.pdf_bytes=generate_pdf(logo_bytes,rd)
        if not st.session_state.pdf_bytes:
            st.error("Error. Verifica que `reportlab` esté instalado.")
with c2:
    if st.session_state.pdf_bytes:
        st.download_button("⬇️ Descargar PDF",data=st.session_state.pdf_bytes,
            file_name=f"PRV_DOROT_{DN[valve_idx]}mm_{date.today().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",use_container_width=True)
