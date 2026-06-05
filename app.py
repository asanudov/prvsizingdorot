# PRV Sizing Tool · DOROT S300
# Instalar:  pip install "streamlit>=1.31" numpy matplotlib pandas
# Ejecutar:  streamlit run app.py

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

st.set_page_config(page_title="PRV Sizing · DOROT S300", page_icon="🔧", layout="wide")

# ══════════════════════════════════════════════
#  DATOS (Catálogo DOROT Mod. 30/31)
# ══════════════════════════════════════════════
DN   = [40,   50,   65,   80,  100,  150,  200,   250,   300,   350,   400,   450,   500,   600]
NOM  = ["1½″","2″","2½″","3″","4″","6″","8″","10″","12″","14″","16″","18″","20″","24″"]
KV_G = [43,  43,  43, 115, 167, 407, 676, 1160, 1600, 1600, 3000, 3150, 3300, 6500]
CV_G = [50,  50,  50, 133, 195, 475, 790, 1360, 1900, 1900, 3500, 3700, 3860, 7600]
KV_A = [60,  60, None,140, 190, 460, 770, 1310, None, None, None, None, None, None]
CV_A = [70,  70, None,164, 222, 537, 900, 1533, None, None, None, None, None, None]

LTP_X = [0.00,0.04,0.08,0.12,0.16,0.20,0.25,0.30,0.40,0.50,0.60,0.70,0.80,0.90,1.00]
LTP_Y = [   0,  18,  32,  43,  52,  59,  65,  71,  80,  86,  91,  95,  97,  99, 100]

PV_MCA      = -9.0
SIGMA_CRIT  =  1.45
SIGMA_NOISY =  2.00
MCA_TO_PSI  =  1.42233

# ══════════════════════════════════════════════
#  CONVERSIONES
# ══════════════════════════════════════════════
_BAR = {"bar":1.0,"psi":0.0689476,"kg/cm²":0.980665,"mca":0.0980665}
_M3H = {"m³/h":1.0,"L/s":3.6,"GPM":0.22712}

def to_bar(v, u): return v * _BAR[u]
def fr_bar(v, u): return v / _BAR[u]
def to_m3h(v, u): return v * _M3H[u]

# ══════════════════════════════════════════════
#  CÁLCULOS
# ══════════════════════════════════════════════
def calc_kv(q, dp):   return q / np.sqrt(dp) if dp > 0 else 0.0
def calc_ap(kn):      return float(np.interp(np.clip(kn, 0, 1), LTP_X, LTP_Y))
def calc_vel(q, d):   return (q / 3600) / (np.pi * ((d / 1000) / 2) ** 2)

def calc_sigma(p1m, p2m):
    dp = p1m - p2m
    return (p1m - PV_MCA) / dp if dp > 0 else None

def zona_sigma(s):
    if s is None or s < SIGMA_CRIT:  return "destruct"
    return "safe" if s >= SIGMA_NOISY else "noisy"

def zona_boundary(sigma_t, p2_arr):
    """P1 = (σ·P2 + 9) / (σ − 1)  — línea de límite en diagrama de cavitación"""
    return (sigma_t * p2_arr + 9) / (sigma_t - 1)

ZONA_MAP = {
    "safe":    ("🟢", "Condiciones seguras",   "success"),
    "noisy":   ("🟡", "Operación ruidosa",      "warning"),
    "destruct":("🔴", "Cavitación destructiva", "error"),
}

def banner_zona(z, sig):
    ico, lbl, kind = ZONA_MAP[z]
    sv  = f"σ = {sig:.2f}" if sig else "σ = —"
    msg = f"{ico} &nbsp;**{lbl}** &nbsp;—&nbsp; {sv}"
    getattr(st, kind)(msg)

# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Parámetros de entrada")
    st.divider()

    # 1 · Diámetro
    st.markdown("**1 · Diámetro de tubería**")
    u_dn = st.radio("Unidad Ø", ["mm","in"], horizontal=True, key="u_dn")
    if u_dn == "mm":
        sel  = st.selectbox("Ø Tubería", DN, format_func=lambda x: f"{x} mm")
        idx  = DN.index(sel)
    else:
        sel_in = st.selectbox("Ø Tubería", NOM)
        idx    = NOM.index(sel_in)
    st.divider()

    # 2 · Tipo de cuerpo
    st.markdown("**2 · Tipo de cuerpo**")
    cuerpo = st.radio("Cuerpo", ["Globo","Angular"], horizontal=True)
    st.divider()

    # 3 · Caudal + presiones de entrada
    st.markdown("**3 · Caudal y presiones de entrada**")
    dinamico = st.toggle("Flujo dinámico", value=True)
    u_q = st.radio("Unidad Q", ["m³/h","L/s","GPM"],         horizontal=True, key="u_q")
    u_p = st.radio("Unidad P", ["bar","psi","kg/cm²","mca"],  horizontal=True, key="u_p")

    if dinamico:
        st.caption("🅐  Qmáx — P1 mínima  (mayor demanda)")
        ca1, ca2 = st.columns(2)
        qmax_ui  = ca1.number_input("Qmáx",   min_value=0.01, value=None, placeholder="ej. 50",  key="qmax")
        p1min_ui = ca2.number_input("P1 mín",  min_value=0.01, value=None, placeholder="ej. 6.0", key="p1mn")
        st.caption("🅑  Qmín — P1 máxima  (menor demanda)")
        cb1, cb2 = st.columns(2)
        qmin_ui  = cb1.number_input("Qmín",   min_value=0.0,  value=None, placeholder="ej. 10",  key="qmin")
        p1max_ui = cb2.number_input("P1 máx",  min_value=0.01, value=None, placeholder="ej. 10",  key="p1mx")

        qmax_m3h = to_m3h(qmax_ui,  u_q) if qmax_ui  is not None else None
        qmin_m3h = to_m3h(qmin_ui,  u_q) if (qmin_ui is not None and qmin_ui > 0) else None
        p1a_bar  = to_bar(p1min_ui, u_p) if p1min_ui is not None else None
        p1b_bar  = to_bar(p1max_ui, u_p) if (p1max_ui is not None and qmin_m3h is not None) else None
    else:
        qdes_ui  = st.number_input("Q diseño", min_value=0.01, value=None, placeholder="ej. 50",  key="qdes")
        p1_ui    = st.number_input("P1",        min_value=0.01, value=None, placeholder="ej. 8.0", key="p1st")
        qmax_m3h = to_m3h(qdes_ui, u_q) if qdes_ui is not None else None
        qmin_m3h = None
        p1a_bar  = to_bar(p1_ui,   u_p) if p1_ui   is not None else None
        p1b_bar  = None

    st.divider()

    # 4 · Presión de ajuste aguas abajo
    st.markdown("**4 · Presión de ajuste aguas abajo**")
    p2_ui  = st.number_input("P2 ajuste", min_value=0.0, value=None, placeholder="ej. 4.0", key="p2adj")
    p2_bar = to_bar(p2_ui, u_p) if p2_ui is not None else None

# ══════════════════════════════════════════════
#  PANEL PRINCIPAL
# ══════════════════════════════════════════════
st.title("🔧 Dimensionamiento PRV — DOROT S300")
st.caption("Modelos 30 (PN 16 bar) / 31 (PN 25 bar)  ·  Válvulas reductoras de presión")

# Válvula seleccionada
KVL = KV_G if cuerpo == "Globo" else KV_A
CVL = CV_G if cuerpo == "Globo" else CV_A
kv_v = KVL[idx]; cv_v = CVL[idx]
if kv_v is None:
    st.warning(f"Angular no disponible en {NOM[idx]}. Se usa Globo.")
    kv_v = KV_G[idx]; cv_v = CV_G[idx]

# ── Validación: campos requeridos vacíos
if any(v is None for v in [qmax_m3h, p1a_bar, p2_bar]):
    st.info("⬅️  Completa todos los parámetros de entrada para ver los resultados.")
    st.stop()

# ── Validación: P1 > P2
dpa_bar = p1a_bar - p2_bar
if dpa_bar <= 0:
    p1_lbl = f"{(p1min_ui if dinamico else p1_ui):.2f} {u_p}"
    st.error(f"⚠️  P1 mín ({p1_lbl}) debe ser mayor que P2 ajuste ({p2_ui:.2f} {u_p}).")
    st.stop()

# ── Cálculos Escenario A  (Qmáx, P1mín)
p1a_mca = fr_bar(p1a_bar, "mca");  p2_mca = fr_bar(p2_bar, "mca")
kv_a    = calc_kv(qmax_m3h, dpa_bar)
kn_a    = kv_a / kv_v;  op_a = calc_ap(kn_a)
sig_a   = calc_sigma(p1a_mca, p2_mca);  z_a = zona_sigma(sig_a)
vel_a   = calc_vel(qmax_m3h, DN[idx])

# ── Cálculos Escenario B  (Qmín, P1máx)
has_b = bool(dinamico and qmin_m3h and p1b_bar)
if has_b:
    dpb_bar = p1b_bar - p2_bar
    if dpb_bar <= 0:
        st.warning("P1 máx debe ser > P2. Escenario B omitido.")
        has_b = False
    else:
        p1b_mca = fr_bar(p1b_bar, "mca")
        kv_b    = calc_kv(qmin_m3h, dpb_bar)
        kn_b    = kv_b / kv_v;  op_b = calc_ap(kn_b)
        sig_b   = calc_sigma(p1b_mca, p2_mca);  z_b = zona_sigma(sig_b)
        vel_b   = calc_vel(qmin_m3h, DN[idx])

# ══════════════════════════════════════════════
#  MÉTRICAS
# ══════════════════════════════════════════════
st.divider()

# Fila: info válvula + velocidades
n_ic = 5 if has_b else 4
ic   = st.columns(n_ic)
ic[0].metric("Válvula",   f"{DN[idx]} mm  ({NOM[idx]})")
ic[1].metric("Kv (100%)", str(kv_v))
ic[2].metric("Cv (100%)", str(cv_v))
ic[3].metric("Vel. 🅐" if dinamico else "Velocidad", f"{vel_a:.2f} m/s")
if has_b:
    ic[4].metric("Vel. 🅑", f"{vel_b:.2f} m/s")

st.markdown("")

# ── Escenario A ──────────────────────────────
st.markdown("**🅐 &nbsp; Qmáx — P1 mín**" if dinamico else "**Parámetros de diseño**")
ca = st.columns(5)
ca[0].metric("ΔP",       f"{fr_bar(dpa_bar, u_p):.2f} {u_p}")
ca[1].metric("Kv req.",  f"{kv_a:.1f}")
ca[2].metric("Kn / Kv",  f"{kn_a:.3f}")
ca[3].metric("Apertura", f"{op_a:.0f} %")
ca[4].metric("σ",        f"{sig_a:.2f}" if sig_a else "—")
banner_zona(z_a, sig_a)

# ── Escenario B ──────────────────────────────
if has_b:
    st.markdown("**🅑 &nbsp; Qmín — P1 máx**")
    cb = st.columns(5)
    cb[0].metric("ΔP",       f"{fr_bar(dpb_bar, u_p):.2f} {u_p}")
    cb[1].metric("Kv req.",  f"{kv_b:.1f}")
    cb[2].metric("Kn / Kv",  f"{kn_b:.3f}")
    cb[3].metric("Apertura", f"{op_b:.0f} %")
    cb[4].metric("σ",        f"{sig_b:.2f}" if sig_b else "—")
    banner_zona(z_b, sig_b)

st.divider()

# ══════════════════════════════════════════════
#  GRÁFICOS
# ══════════════════════════════════════════════
gcol1, gcol2 = st.columns(2)

# ── Curva LTP ──────────────────────────────────
with gcol1:
    st.subheader("📈 Curva característica LTP")
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(LTP_X, LTP_Y, lw=2.5, color="#16A085", label="LTP — DOROT S300")
    ax.axvspan(0.10, 0.80, alpha=0.07, color="green", label="Zona óptima (0.10–0.80)")
    ax.axvline(0.10, ls=":", lw=1, color="green", alpha=0.6)
    ax.axvline(0.80, ls=":", lw=1, color="green", alpha=0.6)

    kn_ap = min(kn_a, 1.0)
    ax.plot(kn_ap, op_a, "o", ms=10, color="crimson", zorder=5,
            label=f"{'🅐 Qmáx' if dinamico else 'Diseño'}  {kn_ap:.3f} → {op_a:.0f}%")
    ax.axvline(kn_ap, ls="--", lw=1, color="crimson", alpha=0.4)
    ax.axhline(op_a,  ls="--", lw=1, color="crimson", alpha=0.4)

    if has_b:
        kn_bp = min(kn_b, 1.0)
        ax.plot(kn_bp, op_b, "s", ms=9, color="darkorange", zorder=5,
                label=f"🅑 Qmín  {kn_bp:.3f} → {op_b:.0f}%")
        ax.axvline(kn_bp, ls=":", lw=1, color="darkorange", alpha=0.4)
        ax.axhline(op_b,  ls=":", lw=1, color="darkorange", alpha=0.4)

    ax.set_xlabel("Kn / Kv", fontsize=11)
    ax.set_ylabel("Apertura (%)", fontsize=11)
    ax.set_xlim(0, 1);  ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.2)
    ax.legend(fontsize=9, loc="lower right")
    ax.set_title("% Apertura vs Kn/Kv — LTP DOROT S300", fontsize=11)
    plt.tight_layout()
    st.pyplot(fig);  plt.close(fig)

# ── Diagrama de cavitación ─────────────────────
with gcol2:
    st.subheader("💧 Diagrama de cavitación")
    p1_vals = [p1a_mca] + ([p1b_mca] if has_b else [])
    xmax = max(p2_mca * 2.5, 100)
    ymax = max(max(p1_vals) * 1.5, 260)

    fig2, ax2 = plt.subplots(figsize=(6, 5))
    xs  = np.linspace(0, xmax, 500)
    L_n = np.minimum(zona_boundary(SIGMA_NOISY, xs), ymax)
    L_d = np.minimum(zona_boundary(SIGMA_CRIT,  xs), ymax)

    ax2.fill_between(xs, 0,   L_n,  color="#27AE60", alpha=0.28, label=f"Segura  σ≥{SIGMA_NOISY}")
    ax2.fill_between(xs, L_n, L_d,  color="#95A5A6", alpha=0.45, label=f"Ruidosa  {SIGMA_CRIT}≤σ<{SIGMA_NOISY}")
    ax2.fill_between(xs, L_d, ymax, color="#E74C3C", alpha=0.28, label=f"Cav. destruct.  σ<{SIGMA_CRIT}")
    ax2.plot(xs, L_n, "--", lw=1, color="#27AE60", alpha=0.7)
    ax2.plot(xs, L_d, "--", lw=1, color="#E74C3C",  alpha=0.7)

    right = p2_mca < xmax * 0.60
    xoff  = xmax * (0.09 if right else -0.28)

    ax2.plot(p2_mca, p1a_mca, "o", color="crimson", ms=11, zorder=6)
    ax2.annotate(
        f"{'🅐 ' if dinamico else ''}P1={p1a_mca:.1f}\nP2={p2_mca:.1f} mca\nσ={sig_a:.2f}",
        xy=(p2_mca, p1a_mca),
        xytext=(p2_mca + xoff, p1a_mca + ymax * 0.04),
        fontsize=7,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="crimson", alpha=0.9),
        arrowprops=dict(arrowstyle="->", color="crimson", lw=0.8),
    )
    if has_b:
        ax2.plot(p2_mca, p1b_mca, "s", color="darkorange", ms=10, zorder=6)
        ax2.annotate(
            f"🅑 P1={p1b_mca:.1f}\nP2={p2_mca:.1f} mca\nσ={sig_b:.2f}",
            xy=(p2_mca, p1b_mca),
            xytext=(p2_mca + xoff, p1b_mca - ymax * 0.12),
            fontsize=7,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="darkorange", alpha=0.9),
            arrowprops=dict(arrowstyle="->", color="darkorange", lw=0.8),
        )

    ax2b = ax2.twiny()
    ax2b.set_xlim(0, xmax * MCA_TO_PSI)
    ax2b.set_xlabel("P2 (psi)", fontsize=9, color="gray")
    ax2b.tick_params(axis="x", labelsize=8, colors="gray")

    ax2.set_xlabel("P2 — Presión ajuste aguas abajo (mca)", fontsize=10)
    ax2.set_ylabel("P1 — Presión aguas arriba (mca)", fontsize=10)
    ax2.set_xlim(0, xmax);  ax2.set_ylim(0, ymax)
    ax2.grid(True, alpha=0.2)
    ax2.legend(fontsize=8, loc="lower right")
    ax2.set_title(f"Cavitación  DOROT S300  —  σ crítico = {SIGMA_CRIT}", fontsize=11)
    plt.tight_layout()
    st.pyplot(fig2);  plt.close(fig2)

# ══════════════════════════════════════════════
#  DIAGNÓSTICO
# ══════════════════════════════════════════════
st.divider()
st.subheader("🏥 Diagnóstico y recomendaciones")
dcol, tcol = st.columns(2)

with dcol:
    def msg_cav(z, sig, label=""):
        sv = f"{sig:.2f}" if sig else "—"
        if z == "destruct":
            st.error(f"🚨 **{label}Cav. destructiva** (σ={sv} < {SIGMA_CRIT})\n\n"
                     "- PRV en cascada (2 etapas)\n- Tapón U-Plug / V-Plug")
        elif z == "noisy":
            st.warning(f"⚠️ **{label}Operación ruidosa** (σ={sv}). Considerar tapón V-Plug.")
        else:
            st.success(f"✅ **{label}Condiciones seguras** (σ={sv}).")

    def msg_ap(kn, op, vel, label=""):
        if kn > 0.80:
            st.warning(f"⚠️ {label}Apertura alta ({op:.0f}%) — considera tamaño mayor.")
        elif kn < 0.10:
            st.warning(f"⚠️ {label}Apertura baja ({op:.0f}%) — considera tamaño menor.")
        else:
            st.success(f"✅ {label}Apertura óptima ({op:.0f}%).  V = {vel:.2f} m/s.")

    msg_cav(z_a, sig_a, "🅐 " if dinamico else "")
    msg_ap(kn_a, op_a, vel_a, "🅐 " if dinamico else "")
    if has_b:
        msg_cav(z_b, sig_b, "🅑 ")
        msg_ap(kn_b, op_b, vel_b, "🅑 ")

with tcol:
    st.markdown("**Comparativa de tamaños disponibles**")
    KV_SEL = KV_G if cuerpo == "Globo" else KV_A
    rows   = []
    for i in range(len(DN)):
        kvi  = KV_SEL[i] if KV_SEL[i] is not None else KV_G[i]
        ri_a = kv_a / kvi;  oi_a = calc_ap(ri_a)
        ok_a = 0.10 <= ri_a <= 0.80
        if has_b:
            ri_b = kv_b / kvi;  oi_b = calc_ap(ri_b)
            ok   = ok_a and 0.10 <= ri_b <= 0.80
            row  = {"Tamaño": f"{DN[i]}mm ({NOM[i]})", "Kv": kvi,
                    "Kn/Kv 🅐": round(ri_a,3), "Ap.🅐%": round(oi_a,0),
                    "Kn/Kv 🅑": round(ri_b,3), "Ap.🅑%": round(oi_b,0),
                    "": ("✅ " if ok else "") + ("← elegido" if i==idx else "")}
        else:
            ok  = ok_a
            row = {"Tamaño": f"{DN[i]}mm ({NOM[i]})", "Kv": kvi,
                   "Kn/Kv": round(ri_a,3), "Apert.%": round(oi_a,0),
                   "": ("✅ " if ok else "") + ("← elegido" if i==idx else "")}
        rows.append(row)

    df = pd.DataFrame(rows)
    def hl(row):
        if has_b:
            ok = 0.10 <= row["Kn/Kv 🅐"] <= 0.80 and 0.10 <= row["Kn/Kv 🅑"] <= 0.80
        else:
            ok = 0.10 <= row["Kn/Kv"] <= 0.80
        bg = "#d4edda" if ok else ""
        return [f"background-color:{bg}"] * len(row)
    st.dataframe(df.style.apply(hl, axis=1), hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════
#  TABLA RESUMEN
# ══════════════════════════════════════════════
st.divider()
with st.expander("📋 Ver tabla de resultados completa"):
    q_lbl  = qmax_ui if dinamico else qdes_ui
    p1_lbl = p1min_ui if dinamico else p1_ui
    filas  = [
        ("Válvula",            f"{DN[idx]} mm — {NOM[idx]}"),
        ("Tipo de cuerpo",      cuerpo),
        ("Kv válvula (100%)",   str(kv_v)),
        ("Cv válvula (100%)",   str(cv_v)),
        ("P2 ajuste",          f"{p2_ui:.2f} {u_p}  →  {p2_bar:.4f} bar"),
        ("— ESCENARIO 🅐" if dinamico else "— DISEÑO", ""),
        (f"Q{'máx' if dinamico else ''}",
                               f"{q_lbl:.2f} {u_q}  →  {qmax_m3h:.2f} m³/h"),
        ("P1" + (" mín" if dinamico else ""),
                               f"{p1_lbl:.2f} {u_p}  →  {p1a_bar:.4f} bar"),
        ("ΔP",                 f"{fr_bar(dpa_bar,u_p):.3f} {u_p}  →  {dpa_bar:.4f} bar"),
        ("Kv requerido",       f"{kv_a:.2f}"),
        ("Kn / Kv",            f"{kn_a:.4f}"),
        ("% Apertura",         f"{op_a:.1f} %"),
        ("Velocidad válvula",  f"{vel_a:.3f} m/s"),
        ("σ",                  f"{sig_a:.3f}" if sig_a else "—"),
        ("Zona cavitación",    ZONA_MAP[z_a][1]),
    ]
    if has_b:
        filas += [
            ("— ESCENARIO 🅑",""),
            ("Qmín",           f"{qmin_ui:.2f} {u_q}  →  {qmin_m3h:.2f} m³/h"),
            ("P1 máx",         f"{p1max_ui:.2f} {u_p}  →  {p1b_bar:.4f} bar"),
            ("ΔP",             f"{fr_bar(dpb_bar,u_p):.3f} {u_p}  →  {dpb_bar:.4f} bar"),
            ("Kv requerido",   f"{kv_b:.2f}"),
            ("Kn / Kv",        f"{kn_b:.4f}"),
            ("% Apertura",     f"{op_b:.1f} %"),
            ("Velocidad",      f"{vel_b:.3f} m/s"),
            ("σ",              f"{sig_b:.3f}" if sig_b else "—"),
            ("Zona cavitación",ZONA_MAP[z_b][1]),
        ]
    st.table(pd.DataFrame(filas, columns=["Parámetro","Valor"]))
