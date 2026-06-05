# PRV Sizing Tool · DOROT S300 / Modelos 30-31
# Instalar:  pip install streamlit numpy matplotlib pandas
# Ejecutar:  streamlit run app.py

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# ══════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════
st.set_page_config(
    page_title="PRV Sizing · DOROT S300",
    page_icon="🔧",
    layout="wide",
)

# ══════════════════════════════════════════════
#  DATOS (Catálogo DOROT Mod. 30/31)
# ══════════════════════════════════════════════
DN   = [40,   50,   65,   80,  100,  150,  200,   250,   300,   350,   400,   450,   500,   600]
NOM  = ["1½″","2″","2½″","3″","4″","6″","8″","10″","12″","14″","16″","18″","20″","24″"]

KV_G = [43,  43,  43, 115, 167, 407, 676, 1160, 1600, 1600, 3000, 3150, 3300, 6500]
CV_G = [50,  50,  50, 133, 195, 475, 790, 1360, 1900, 1900, 3500, 3700, 3860, 7600]
K_G  = [2.2,5.4,15.4, 4.8, 5.6, 4.8, 5.5,  4.5,  5.0,  9.0,  3.8,  6.0,  5.9,  4.8]

KV_A = [60,  60, None,140, 190, 460, 770, 1310, None, None, None, None, None, None]
CV_A = [70,  70, None,164, 222, 537, 900, 1533, None, None, None, None, None, None]
K_A  = [1.3,2.8, None,3.3, 4.3, 4.3, 4.2,  3.6, None, None, None, None, None, None]

# Curva LTP — DOROT S300 (digitalizada del catálogo)
LTP_X = [0.00,0.04,0.08,0.12,0.16,0.20,0.25,0.30,0.40,0.50,0.60,0.70,0.80,0.90,1.00]
LTP_Y = [   0,  18,  32,  43,  52,  59,  65,  71,  80,  86,  91,  95,  97,  99, 100]

# ══════════════════════════════════════════════
#  CONSTANTES DOROT S300
# ══════════════════════════════════════════════
PV_MCA      = -9.0    # Presión de vapor del agua (mca gauge, ~20°C)
SIGMA_CRIT  =  1.45   # σ crítico S300 — límite cavitación destructiva
SIGMA_NOISY =  2.00   # Límite estimado zona ruidosa / segura
MCA_TO_PSI  =  1.42233

def _zona_boundary(sigma_t, p2_arr):
    """P1 = (σ_t · P2 + 9) / (σ_t − 1)  — línea de límite en diagrama de cavitación"""
    return (sigma_t * p2_arr + 9) / (sigma_t - 1)

# ══════════════════════════════════════════════
#  CONVERSIONES
# ══════════════════════════════════════════════
_BAR = {"bar":1.0, "psi":0.0689476, "kg/cm²":0.980665, "mca":0.0980665}
_M3H = {"m³/h":1.0, "L/s":3.6, "GPM":0.22712}

def to_bar(v,u):  return v * _BAR[u]
def fr_bar(v,u):  return v / _BAR[u]
def to_m3h(v,u):  return v * _M3H[u]

# ══════════════════════════════════════════════
#  FUNCIONES DE CÁLCULO
# ══════════════════════════════════════════════
def calc_kv(q_m3h, dp_bar):
    """Kv = Q [m³/h] / √ΔP [bar]"""
    return q_m3h / np.sqrt(dp_bar) if dp_bar > 0 else 0.0

def calc_apertura(kn_kv):
    return float(np.interp(np.clip(kn_kv, 0.0, 1.0), LTP_X, LTP_Y))

def calc_sigma(p1_mca, p2_mca):
    """σ = (P1[mca] − Pv[mca]) / (P1[mca] − P2[mca])   Pv = −9 mca"""
    dp = p1_mca - p2_mca
    return (p1_mca - PV_MCA) / dp if dp > 0 else None

def zona_sigma(s):
    if s is None or s < SIGMA_CRIT:  return "destructive"
    if s < SIGMA_NOISY:              return "noisy"
    return "safe"

def calc_vel(q_m3h, d_mm):
    """V [m/s] = Q / A   (ecuación de continuidad, sección circular)"""
    a = np.pi * ((d_mm / 1000) / 2) ** 2
    return (q_m3h / 3600) / a

ZONA = {
    "safe":        ("🟢", "Segura",         "#27AE60"),
    "noisy":       ("🟡", "Op. ruidosa",    "#E67E22"),
    "destructive": ("🔴", "Cav. destruct.", "#E74C3C"),
}

# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Parámetros de entrada")
    st.divider()

    # ── 1. Diámetro ───────────────────────────
    st.markdown("**1 · Diámetro de tubería**")
    u_dn = st.radio("Unidad Ø", ["mm","in"], horizontal=True, key="u_dn")
    if u_dn == "mm":
        sel = st.selectbox("Ø Tubería", DN, format_func=lambda x: f"{x} mm")
        idx = DN.index(sel)
    else:
        sel_in = st.selectbox("Ø Tubería", NOM)
        idx = NOM.index(sel_in)
    st.divider()

    # ── 2. Tipo de cuerpo ─────────────────────
    st.markdown("**2 · Tipo de cuerpo**")
    cuerpo = st.radio("Cuerpo", ["Globo","Angular"], horizontal=True)
    st.divider()

    # ── 3. Caudal y presiones de entrada ──────
    st.markdown("**3 · Caudal y presiones de entrada**")
    dinamico = st.toggle("Flujo dinámico", value=True)
    u_q = st.radio("Unidad Q", ["m³/h","L/s","GPM"],          horizontal=True, key="u_q")
    u_p = st.radio("Unidad P", ["bar","psi","kg/cm²","mca"],   horizontal=True, key="u_p")

    if dinamico:
        st.caption("🅐  Qmáx — P1 mínima  (mayor demanda, menor presión)")
        ca1, ca2 = st.columns(2)
        qmax_ui  = ca1.number_input("Qmáx",   0.01, 1e6, 50.0, 1.0, key="qmax")
        p1min_ui = ca2.number_input("P1 mín",  0.01, 1e4,  6.0, 0.5, key="p1mn")

        st.caption("🅑  Qmín — P1 máxima  (menor demanda, mayor presión)")
        cb1, cb2 = st.columns(2)
        qmin_ui  = cb1.number_input("Qmín",   0.00, 1e6, 10.0, 1.0, key="qmin")
        p1max_ui = cb2.number_input("P1 máx",  0.01, 1e4, 10.0, 0.5, key="p1mx")

        qmax_m3h = to_m3h(qmax_ui, u_q)
        qmin_m3h = to_m3h(qmin_ui, u_q) if qmin_ui > 0 else None
        p1a_bar  = to_bar(p1min_ui, u_p)
        p1b_bar  = to_bar(p1max_ui, u_p)
    else:
        qdes_ui = st.number_input("Q diseño", 0.01, 1e6, 50.0, 1.0)
        p1_ui   = st.number_input("P1",       0.01, 1e4,  8.0, 0.5)
        qmax_m3h = to_m3h(qdes_ui, u_q)
        qmin_m3h = None
        p1a_bar  = to_bar(p1_ui, u_p)
        p1b_bar  = None

    st.divider()

    # ── 4. Presión de ajuste aguas abajo ──────
    st.markdown("**4 · Presión de ajuste aguas abajo**")
    p2_ui  = st.number_input("P2 ajuste", 0.00, 1e4, 4.0, 0.5)
    p2_bar = to_bar(p2_ui, u_p)

# ══════════════════════════════════════════════
#  PANEL PRINCIPAL
# ══════════════════════════════════════════════
st.title("🔧 Dimensionamiento PRV — DOROT S300")
st.caption("Modelos 30 (PN 16 bar) / 31 (PN 25 bar)  ·  Válvulas reductoras de presión")

# Kv de la válvula seleccionada
KVL = KV_G if cuerpo == "Globo" else KV_A
CVL = CV_G if cuerpo == "Globo" else CV_A
kv_v = KVL[idx]; cv_v = CVL[idx]
if kv_v is None:
    st.warning(f"⚠️ Angular no disponible en {NOM[idx]}. Se usa Globo.")
    kv_v = KV_G[idx]; cv_v = CV_G[idx]

# ── Validación P1 > P2
dpa_bar = p1a_bar - p2_bar
p1_label = f"{(p1min_ui if dinamico else p1_ui):.2f} {u_p}"
if dpa_bar <= 0:
    st.error(f"⚠️  P1 mín ({p1_label}) debe ser > P2 ajuste ({p2_ui:.2f} {u_p}).")
    st.stop()

# ── Cálculos Escenario A  (Qmáx, P1mín)
p1a_mca = fr_bar(p1a_bar, "mca")
p2_mca  = fr_bar(p2_bar,  "mca")
kv_a    = calc_kv(qmax_m3h, dpa_bar)
kn_a    = kv_a / kv_v
op_a    = calc_apertura(kn_a)
sig_a   = calc_sigma(p1a_mca, p2_mca)
z_a     = zona_sigma(sig_a)
vel_a   = calc_vel(qmax_m3h, DN[idx])

# ── Cálculos Escenario B  (Qmín, P1máx) — sólo si dinámico
has_b = bool(dinamico and qmin_m3h and p1b_bar)
if has_b:
    dpb_bar = p1b_bar - p2_bar
    if dpb_bar <= 0:
        st.warning("⚠️ P1 máx debe ser > P2. Escenario B omitido.")
        has_b = False
    else:
        p1b_mca = fr_bar(p1b_bar, "mca")
        kv_b    = calc_kv(qmin_m3h, dpb_bar)
        kn_b    = kv_b / kv_v
        op_b    = calc_apertura(kn_b)
        sig_b   = calc_sigma(p1b_mca, p2_mca)
        z_b     = zona_sigma(sig_b)
        vel_b   = calc_vel(qmin_m3h, DN[idx])

# ══════════════════════════════════════════════
#  MÉTRICAS
# ══════════════════════════════════════════════
st.divider()

# Fila: info válvula
ic = st.columns(4)
ic[0].metric("Válvula",          f"{DN[idx]} mm  ({NOM[idx]})")
ic[1].metric("Kv  (100%)",       str(kv_v))
ic[2].metric("Cv  (100%)",       str(cv_v))
ic[3].metric("Vel. válvula 🅐",  f"{vel_a:.2f} m/s")

st.markdown("")

# Escenario A
st.markdown("**🅐 Qmáx — P1 mín**" if dinamico else "**Escenario de diseño**")
ca = st.columns(6)
ca[0].metric("ΔP",      f"{fr_bar(dpa_bar, u_p):.2f} {u_p}")
ca[1].metric("Kv req.", f"{kv_a:.1f}")
ca[2].metric("Kn/Kv",  f"{kn_a:.3f}")
ca[3].metric("Apertura",f"{op_a:.0f} %")
ca[4].metric("σ",       f"{sig_a:.2f}" if sig_a else "—")
ca[5].metric("Zona",    f"{ZONA[z_a][0]}  {ZONA[z_a][1]}")

# Escenario B
if has_b:
    st.markdown("**🅑 Qmín — P1 máx**")
    cb = st.columns(6)
    cb[0].metric("ΔP",      f"{fr_bar(dpb_bar, u_p):.2f} {u_p}")
    cb[1].metric("Kv req.", f"{kv_b:.1f}")
    cb[2].metric("Kn/Kv",  f"{kn_b:.3f}")
    cb[3].metric("Apertura",f"{op_b:.0f} %")
    cb[4].metric("σ",       f"{sig_b:.2f}" if sig_b else "—")
    cb[5].metric("Zona",    f"{ZONA[z_b][0]}  {ZONA[z_b][1]}")

    vr = st.columns(4)
    vr[3].metric("Vel. válvula 🅑", f"{vel_b:.2f} m/s")

st.divider()

# ══════════════════════════════════════════════
#  GRÁFICOS
# ══════════════════════════════════════════════
gcol1, gcol2 = st.columns(2)

# ── Curva LTP ──────────────────────────────────
with gcol1:
    st.subheader("📈 Curva característica LTP")
    fig, ax = plt.subplots(figsize=(6,5))
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
    ax.set_xlim(0, 1); ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.2)
    ax.legend(fontsize=9, loc="lower right")
    ax.set_title("% Apertura vs Kn/Kv  —  LTP DOROT S300", fontsize=11)
    plt.tight_layout()
    st.pyplot(fig); plt.close(fig)

# ── Diagrama de cavitación ─────────────────────
with gcol2:
    st.subheader("💧 Diagrama de cavitación")

    p1_vals = [p1a_mca] + ([p1b_mca] if has_b else [])
    xmax = max(p2_mca * 2.5, 100)
    ymax = max(max(p1_vals) * 1.5, 260)

    fig2, ax2 = plt.subplots(figsize=(6,5))
    xs = np.linspace(0, xmax, 500)

    # Límites de zona derivados de la fórmula σ = (P1+9)/(P1−P2)
    L_noisy    = np.minimum(_zona_boundary(SIGMA_NOISY, xs),   ymax)
    L_destruct = np.minimum(_zona_boundary(SIGMA_CRIT,  xs),   ymax)

    ax2.fill_between(xs, 0,           L_noisy,    color="#27AE60", alpha=0.28,
                     label=f"Segura  (σ ≥ {SIGMA_NOISY:.1f})")
    ax2.fill_between(xs, L_noisy,     L_destruct, color="#95A5A6", alpha=0.45,
                     label=f"Ruidosa  ({SIGMA_CRIT} ≤ σ < {SIGMA_NOISY})")
    ax2.fill_between(xs, L_destruct,  ymax,       color="#E74C3C", alpha=0.28,
                     label=f"Cav. destruct.  (σ < {SIGMA_CRIT})")
    ax2.plot(xs, L_noisy,    "--", lw=1, color="#27AE60", alpha=0.7)
    ax2.plot(xs, L_destruct, "--", lw=1, color="#E74C3C",  alpha=0.7)

    # ── Punto A
    right_a = p2_mca < xmax * 0.60
    ax2.plot(p2_mca, p1a_mca, "o", color="crimson", ms=11, zorder=6)
    ax2.annotate(
        f"{'🅐  ' if dinamico else ''}P1={p1a_mca:.1f} mca\nP2={p2_mca:.1f} mca\nσ={sig_a:.2f}",
        xy=(p2_mca, p1a_mca),
        xytext=(p2_mca + xmax*(0.09 if right_a else -0.28),
                p1a_mca + ymax * 0.04),
        fontsize=7,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="crimson", alpha=0.9),
        arrowprops=dict(arrowstyle="->", color="crimson", lw=0.8),
    )

    # ── Punto B
    if has_b:
        ax2.plot(p2_mca, p1b_mca, "s", color="darkorange", ms=10, zorder=6)
        ax2.annotate(
            f"🅑  P1={p1b_mca:.1f} mca\nP2={p2_mca:.1f} mca\nσ={sig_b:.2f}",
            xy=(p2_mca, p1b_mca),
            xytext=(p2_mca + xmax*(0.09 if right_a else -0.28),
                    p1b_mca - ymax * 0.12),
            fontsize=7,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="darkorange", alpha=0.9),
            arrowprops=dict(arrowstyle="->", color="darkorange", lw=0.8),
        )

    # Eje secundario psi
    ax2b = ax2.twiny()
    ax2b.set_xlim(0, xmax * MCA_TO_PSI)
    ax2b.set_xlabel("P2 (psi)", fontsize=9, color="gray")
    ax2b.tick_params(axis="x", labelsize=8, colors="gray")

    ax2.set_xlabel("P2 — Presión ajuste aguas abajo (mca)", fontsize=10)
    ax2.set_ylabel("P1 — Presión aguas arriba (mca)", fontsize=10)
    ax2.set_xlim(0, xmax); ax2.set_ylim(0, ymax)
    ax2.grid(True, alpha=0.2)
    ax2.legend(fontsize=8, loc="lower right")
    ax2.set_title(f"Cavitación  DOROT S300  —  σ crítico = {SIGMA_CRIT}", fontsize=11)
    plt.tight_layout()
    st.pyplot(fig2); plt.close(fig2)

# ══════════════════════════════════════════════
#  DIAGNÓSTICO
# ══════════════════════════════════════════════
st.divider()
st.subheader("🏥 Diagnóstico y recomendaciones")
dcol, tcol = st.columns(2)

with dcol:
    def msg_cav(z, sig, label=""):
        sv = f"{sig:.2f}" if sig else "—"
        if z == "destructive":
            st.error(f"🚨 **{label}Cav. destructiva (σ={sv} < {SIGMA_CRIT}).**\n\n"
                     "- PRV en cascada (2 etapas)\n- Tapón U-Plug / V-Plug\n"
                     "- Revisar presiones de diseño")
        elif z == "noisy":
            st.warning(f"⚠️ **{label}Operación ruidosa** (σ={sv}). Considerar tapón V-Plug.")
        else:
            st.success(f"✅ **{label}Condiciones seguras** (σ={sv}).")

    msg_cav(z_a, sig_a, "🅐 " if dinamico else "")
    if has_b:
        msg_cav(z_b, sig_b, "🅑 ")

    st.markdown("---")

    def msg_ap(kn, op, vel, label=""):
        if kn > 0.80:
            st.warning(f"⚠️ {label}Apertura alta ({op:.0f}%) — considera tamaño mayor.")
        elif kn < 0.10:
            st.warning(f"⚠️ {label}Apertura baja ({op:.0f}%) — considera tamaño menor.")
        else:
            st.success(f"✅ {label}Apertura óptima ({op:.0f}%).  V = {vel:.2f} m/s.")

    msg_ap(kn_a, op_a, vel_a, "🅐 " if dinamico else "")
    if has_b:
        msg_ap(kn_b, op_b, vel_b, "🅑 ")

with tcol:
    st.markdown("**Comparativa de tamaños disponibles**")
    KV_SEL = KV_G if cuerpo == "Globo" else KV_A
    rows = []
    for i in range(len(DN)):
        kvi  = KV_SEL[i] if KV_SEL[i] is not None else KV_G[i]
        ri_a = kv_a / kvi;  oi_a = calc_apertura(ri_a)
        ok_a = 0.10 <= ri_a <= 0.80
        if has_b:
            ri_b = kv_b / kvi; oi_b = calc_apertura(ri_b)
            ok   = ok_a and 0.10 <= ri_b <= 0.80
            row  = {"Tamaño": f"{DN[i]} mm ({NOM[i]})", "Kv": kvi,
                    "Kn/Kv 🅐": round(ri_a,3), "Apert.🅐": round(oi_a,0),
                    "Kn/Kv 🅑": round(ri_b,3), "Apert.🅑": round(oi_b,0),
                    "": ("✅ " if ok else "") + ("← elegido" if i==idx else "")}
        else:
            ok  = ok_a
            row = {"Tamaño": f"{DN[i]} mm ({NOM[i]})", "Kv": kvi,
                   "Kn/Kv": round(ri_a,3), "Apert. %": round(oi_a,0),
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
#  TABLA RESUMEN (expandible)
# ══════════════════════════════════════════════
st.divider()
with st.expander("📋 Ver tabla de resultados completa"):
    q_lbl  = qmax_ui if dinamico else qdes_ui
    p1_lbl = p1min_ui if dinamico else p1_ui
    filas = [
        ("Válvula seleccionada",  f"{DN[idx]} mm — {NOM[idx]}"),
        ("Tipo de cuerpo",         cuerpo),
        ("Kv válvula (100%)",      str(kv_v)),
        ("Cv válvula (100%)",      str(cv_v)),
        ("P2 ajuste",              f"{p2_ui:.2f} {u_p}  →  {p2_bar:.4f} bar"),
        ("— ESCENARIO 🅐" if dinamico else "— DISEÑO", ""),
        (f"Q{'máx' if dinamico else ''}",
                                   f"{q_lbl:.2f} {u_q}  →  {qmax_m3h:.2f} m³/h"),
        ("P1" + (" mín" if dinamico else ""),
                                   f"{p1_lbl:.2f} {u_p}  →  {p1a_bar:.4f} bar"),
        ("ΔP",                     f"{fr_bar(dpa_bar,u_p):.3f} {u_p}  →  {dpa_bar:.4f} bar"),
        ("Kv requerido",           f"{kv_a:.2f}"),
        ("Kn / Kv",                f"{kn_a:.4f}"),
        ("% Apertura",             f"{op_a:.1f} %"),
        ("Velocidad en válvula",   f"{vel_a:.3f} m/s"),
        ("σ",                      f"{sig_a:.3f}" if sig_a else "—"),
        ("Zona cavitación",        ZONA[z_a][1]),
    ]
    if has_b:
        filas += [
            ("— ESCENARIO 🅑", ""),
            ("Qmín",           f"{qmin_ui:.2f} {u_q}  →  {qmin_m3h:.2f} m³/h"),
            ("P1 máx",         f"{p1max_ui:.2f} {u_p}  →  {p1b_bar:.4f} bar"),
            ("ΔP",             f"{fr_bar(dpb_bar,u_p):.3f} {u_p}  →  {dpb_bar:.4f} bar"),
            ("Kv requerido",   f"{kv_b:.2f}"),
            ("Kn / Kv",        f"{kn_b:.4f}"),
            ("% Apertura",     f"{op_b:.1f} %"),
            ("Velocidad",      f"{vel_b:.3f} m/s"),
            ("σ",              f"{sig_b:.3f}" if sig_b else "—"),
            ("Zona cavitación",ZONA[z_b][1]),
        ]
    st.table(pd.DataFrame(filas, columns=["Parámetro","Valor"]))
