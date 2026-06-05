# PRV Sizing Tool · DOROT S300 / Modelos 30-31
# ─────────────────────────────────────────────
# Instalar:  pip install streamlit numpy matplotlib pandas
# Ejecutar:  streamlit run app.py
# ─────────────────────────────────────────────

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# ══════════════════════════════════════════════
#  CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════
st.set_page_config(
    page_title="PRV Sizing · DOROT S300",
    page_icon="🔧",
    layout="wide",
)

# ══════════════════════════════════════════════
#  DATOS DE VÁLVULA (Catálogo DOROT Mod. 30/31)
# ══════════════════════════════════════════════
DN   = [40,   50,   65,   80,  100,  150,  200,   250,   300,   350,   400,   450,   500,   600]
NOM  = ["1½″","2″","2½″","3″","4″","6″","8″","10″","12″","14″","16″","18″","20″","24″"]

KV_G = [43,   43,   43,  115,  167,  407,  676,  1160,  1600,  1600,  3000,  3150,  3300,  6500]
CV_G = [50,   50,   50,  133,  195,  475,  790,  1360,  1900,  1900,  3500,  3700,  3860,  7600]
K_G  = [2.2, 5.4, 15.4,  4.8,  5.6,  4.8,  5.5,   4.5,   5.0,   9.0,   3.8,   6.0,   5.9,   4.8]

KV_A = [60,   60,  None, 140,  190,  460,  770,  1310,  None,  None,  None,  None,  None,  None]
CV_A = [70,   70,  None, 164,  222,  537,  900,  1533,  None,  None,  None,  None,  None,  None]
K_A  = [1.3, 2.8,  None, 3.3,  4.3,  4.3,  4.2,   3.6,  None,  None,  None,  None,  None,  None]

# Curva característica LTP — DOROT S300 (digitalizada del catálogo)
# X = Kn/Kv  |  Y = % Apertura
LTP_X = [0.00,0.04,0.08,0.12,0.16,0.20,0.25,0.30,0.40,0.50,0.60,0.70,0.80,0.90,1.00]
LTP_Y = [   0,  18,  32,  43,  52,  59,  65,  71,  80,  86,  91,  95,  97,  99, 100]

MCA_TO_PSI = 1.42233   # 1 mca = 1.42233 psi

# ══════════════════════════════════════════════
#  CONVERSIONES DE UNIDADES
# ══════════════════════════════════════════════
_BAR = {"bar": 1.0, "psi": 0.0689476, "kg/cm²": 0.980665, "mca": 0.0980665}
_M3H = {"m³/h": 1.0, "L/s": 3.6, "GPM": 0.22712}

def to_bar(v, u):  return v * _BAR[u]
def fr_bar(v, u):  return v / _BAR[u]
def to_m3h(v, u):  return v * _M3H[u]

# ══════════════════════════════════════════════
#  FUNCIONES DE CÁLCULO
# ══════════════════════════════════════════════
def calc_kv(q_m3h, dp_bar):
    """Kv requerido = Q [m³/h] / √ΔP [bar]"""
    return q_m3h / np.sqrt(dp_bar) if dp_bar > 0 else 0.0

def calc_apertura(kn_kv):
    """% apertura interpolado en la curva LTP del S300"""
    return float(np.interp(np.clip(kn_kv, 0.0, 1.0), LTP_X, LTP_Y))

def calc_zona(p1_bar, p2_bar):
    """
    Zona de cavitación según ratio P2/P1.
    Límites extraídos del diagrama de cavitación DOROT S300:
      P2/P1 ≥ 0.36  → Condiciones seguras
      P2/P1 ∈ [0.22, 0.36) → Operación ruidosa
      P2/P1 < 0.22  → Cavitación destructiva
    """
    r = (p2_bar / p1_bar) if p1_bar > 0 else 1.0
    if r >= 0.36: return "safe"
    if r >= 0.22: return "noisy"
    return "destructive"

ZONA = {
    "safe":        ("🟢", "Condiciones seguras",   "#27AE60"),
    "noisy":       ("🟡", "Operación ruidosa",      "#E67E22"),
    "destructive": ("🔴", "Cavitación destructiva", "#E74C3C"),
}

# ══════════════════════════════════════════════
#  SIDEBAR — ENTRADAS
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Parámetros de entrada")
    st.divider()

    # 1 · Diámetro
    st.markdown("**1 · Diámetro de tubería**")
    u_dn = st.radio("Unidad Ø", ["mm", "in"], horizontal=True, key="u_dn")
    if u_dn == "mm":
        pipe_mm = st.selectbox("Ø Tubería", DN, format_func=lambda x: f"{x} mm")
        idx = DN.index(pipe_mm)
    else:
        pipe_in = st.selectbox("Ø Tubería", NOM)
        idx = NOM.index(pipe_in)
    st.divider()

    # 2 · Tipo de cuerpo
    st.markdown("**2 · Tipo de cuerpo**")
    cuerpo = st.radio("Cuerpo", ["Globo", "Angular"], horizontal=True)
    st.divider()

    # 3 · Caudal
    st.markdown("**3 · Caudal**")
    dinamico = st.toggle("Flujo dinámico (Qmáx / Qmín)", value=True)
    u_q = st.radio("Unidad Q", ["m³/h", "L/s", "GPM"], horizontal=True)
    if dinamico:
        c1, c2 = st.columns(2)
        qmax_ui = c1.number_input("Qmáx", 0.01, 1e6, 50.0, 1.0)
        qmin_ui = c2.number_input("Qmín", 0.0,  1e6, 10.0, 1.0)
        q_dis = qmax_ui
    else:
        q_dis   = st.number_input("Q diseño", 0.01, 1e6, 50.0, 1.0)
        qmin_ui = 0.0

    qmax_m3h = to_m3h(q_dis, u_q)
    qmin_m3h = to_m3h(qmin_ui, u_q) if (dinamico and qmin_ui > 0) else None
    st.divider()

    # 4 · Presiones
    st.markdown("**4 · Presiones**")
    u_p = st.radio("Unidad P", ["bar", "psi", "kg/cm²", "mca"], horizontal=True)
    c1, c2 = st.columns(2)
    p1_ui = c1.number_input("P1 (entrada)", 0.01, 1e4, 8.0, 0.5)
    p2_ui = c2.number_input("P2 (salida)",  0.0,  1e4, 4.0, 0.5)

    p1b = to_bar(p1_ui, u_p)
    p2b = to_bar(p2_ui, u_p)
    dpb = p1b - p2b

# ══════════════════════════════════════════════
#  PANEL PRINCIPAL
# ══════════════════════════════════════════════
st.title("🔧 Dimensionamiento PRV — DOROT S300")
st.caption("Modelos 30 (PN 16 bar) / 31 (PN 25 bar)  ·  Válvulas reductoras de presión")

if dpb <= 0:
    st.error("⚠️  P1 debe ser mayor que P2 para tener reducción de presión.")
    st.stop()

# ─ Kv de la válvula seleccionada
KVL = KV_G if cuerpo == "Globo" else KV_A
CVL = CV_G if cuerpo == "Globo" else CV_A
kv_v = KVL[idx]; cv_v = CVL[idx]
if kv_v is None:
    st.warning(f"⚠️  Cuerpo Angular no disponible en {NOM[idx]}. Se usa Globo automáticamente.")
    kv_v = KV_G[idx]; cv_v = CV_G[idx]

# ─ Cálculos Qmáx
kv_max = calc_kv(qmax_m3h, dpb)
kn_max = kv_max / kv_v
op_max = calc_apertura(kn_max)
z      = calc_zona(p1b, p2b)
zico, zlbl, zcol = ZONA[z]

# ─ Cálculos Qmín (si aplica)
if qmin_m3h:
    kv_min = calc_kv(qmin_m3h, dpb)
    kn_min = kv_min / kv_v
    op_min = calc_apertura(kn_min)
else:
    kv_min = kn_min = op_min = None

# ── Métricas
m = st.columns(5)
m[0].metric("Kv requerido",       f"{kv_max:.1f}")
m[1].metric("Kv válvula (100%)",  f"{kv_v}")
m[2].metric("Kn / Kv",           f"{kn_max:.3f}")
m[3].metric("% Apertura (Qmáx)", f"{op_max:.0f} %")
m[4].metric("Cavitación",        f"{zico} {zlbl}")

if kn_min is not None:
    n = st.columns(5)
    n[0].metric("Kv req. (Qmín)",    f"{kv_min:.1f}")
    n[2].metric("Kn/Kv (Qmín)",     f"{kn_min:.3f}")
    n[3].metric("% Apertura (Qmín)", f"{op_min:.0f} %")

st.divider()

# ══════════════════════════════════════════════
#  GRÁFICOS
# ══════════════════════════════════════════════
col1, col2 = st.columns(2)

# ── Gráfico 1: Curva LTP ──────────────────────
with col1:
    st.subheader("📈 Curva característica LTP")
    fig, ax = plt.subplots(figsize=(6, 5))

    ax.plot(LTP_X, LTP_Y, lw=2.5, color="#16A085", label="LTP — DOROT S300")
    ax.axvspan(0.10, 0.80, alpha=0.07, color="green", label="Zona óptima (0.10 – 0.80)")
    ax.axvline(0.10, ls=":", lw=1, color="green", alpha=0.6)
    ax.axvline(0.80, ls=":", lw=1, color="green", alpha=0.6)

    kn_p = min(kn_max, 1.0)
    ax.plot(kn_p, op_max, "o", ms=10, color="crimson", zorder=5,
            label=f"Qmáx  Kn/Kv={kn_p:.3f} → {op_max:.0f}%")
    ax.axvline(kn_p, ls="--", lw=1, color="crimson", alpha=0.4)
    ax.axhline(op_max, ls="--", lw=1, color="crimson", alpha=0.4)

    if kn_min is not None:
        kn_pm = min(kn_min, 1.0)
        ax.plot(kn_pm, op_min, "s", ms=9, color="darkorange", zorder=5,
                label=f"Qmín  Kn/Kv={kn_pm:.3f} → {op_min:.0f}%")
        ax.axvline(kn_pm, ls=":", lw=1, color="darkorange", alpha=0.4)
        ax.axhline(op_min, ls=":", lw=1, color="darkorange", alpha=0.4)

    ax.set_xlabel("Kn / Kv", fontsize=11)
    ax.set_ylabel("Apertura de la válvula (%)", fontsize=11)
    ax.set_xlim(0, 1); ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.2)
    ax.legend(fontsize=9, loc="lower right")
    ax.set_title("% Apertura vs Kn/Kv  (curva LTP DOROT S300)", fontsize=11)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

# ── Gráfico 2: Diagrama de cavitación ─────────
with col2:
    st.subheader("💧 Diagrama de cavitación")
    p1m = fr_bar(p1b, "mca")
    p2m = fr_bar(p2b, "mca")
    xmax = max(p2m * 2.5, 100)
    ymax = max(p1m * 1.5, 260)

    fig2, ax2 = plt.subplots(figsize=(6, 5))
    xs = np.linspace(0, xmax, 500)
    L1 = np.minimum(xs / 0.36, ymax)   # límite seguro / ruidoso
    L2 = np.minimum(xs / 0.22, ymax)   # límite ruidoso / destructivo

    ax2.fill_between(xs, 0,    L1,    color="#27AE60", alpha=0.30, label="Condiciones seguras")
    ax2.fill_between(xs, L1,   L2,    color="#95A5A6", alpha=0.45, label="Operación ruidosa")
    ax2.fill_between(xs, L2,   ymax,  color="#E74C3C", alpha=0.30, label="Cav. destructiva")

    ax2.plot(p2m, p1m, "ko", ms=11, zorder=6)
    tx = p2m + xmax*0.04 if p2m < xmax*0.6 else p2m - xmax*0.20
    ty = p1m - ymax*0.10 if p1m > ymax*0.7 else p1m + ymax*0.03
    ax2.annotate(
        f"P1 = {p1m:.1f} mca\nP2 = {p2m:.1f} mca",
        xy=(p2m, p1m), xytext=(tx, ty), fontsize=8,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.85),
        arrowprops=dict(arrowstyle="->", color="gray", lw=0.8),
    )

    ax2b = ax2.twiny()
    ax2b.set_xlim(0, xmax * MCA_TO_PSI)
    ax2b.set_xlabel("P2 (psi)", fontsize=9, color="gray")
    ax2b.tick_params(axis="x", labelsize=8, colors="gray")

    ax2.set_xlabel("P2 — Presión aguas abajo (mca)", fontsize=11)
    ax2.set_ylabel("P1 — Presión aguas arriba (mca)", fontsize=11)
    ax2.set_xlim(0, xmax); ax2.set_ylim(0, ymax)
    ax2.grid(True, alpha=0.2)
    ax2.legend(fontsize=9, loc="lower right")
    ax2.set_title("Diagrama de cavitación — DOROT S300", fontsize=11)
    plt.tight_layout()
    st.pyplot(fig2)
    plt.close(fig2)

# ══════════════════════════════════════════════
#  DIAGNÓSTICO Y RECOMENDACIONES
# ══════════════════════════════════════════════
st.divider()
st.subheader("🏥 Diagnóstico y recomendaciones")
dcol, tcol = st.columns(2)

with dcol:
    if z == "destructive":
        st.error(
            "🚨 **Cavitación destructiva.**\n\n"
            "Medidas recomendadas:\n"
            "- Reducción de presión en dos etapas (PRV en cascada)\n"
            "- Tapón regulador U-Plug o V-Plug\n"
            "- Revisar presiones de diseño del sistema"
        )
    elif z == "noisy":
        st.warning("⚠️ **Operación ruidosa.** Considerar tapón V-Plug o U-Plug.")
    else:
        st.success("✅ **Condiciones seguras de funcionamiento.**")

    st.markdown("---")

    if kn_max > 0.80:
        st.warning(f"⚠️ Apertura demasiado alta ({op_max:.0f}%). Considera un tamaño mayor de válvula.")
    elif kn_max < 0.10:
        st.warning(f"⚠️ Apertura demasiado baja ({op_max:.0f}%). Considera un tamaño menor de válvula.")
    else:
        st.success(f"✅ Apertura en rango óptimo de regulación ({op_max:.0f}%).")

    if kn_min is not None and kn_min < 0.05:
        st.warning("⚠️ A Qmín la apertura es muy pequeña — riesgo de inestabilidad en regulación.")

with tcol:
    st.markdown("**Comparativa de tamaños disponibles**")
    KV_SEL = KV_G if cuerpo == "Globo" else KV_A
    rows = []
    for i in range(len(DN)):
        kvi = KV_SEL[i] if KV_SEL[i] is not None else KV_G[i]
        ri  = kv_max / kvi
        oi  = calc_apertura(ri)
        tag = ("✅ " if 0.10 <= ri <= 0.80 else "") + ("← elegido" if i == idx else "")
        rows.append({
            "Tamaño":    f"{DN[i]} mm ({NOM[i]})",
            "Kv":         kvi,
            "Kn/Kv":     round(ri, 3),
            "% Apert.":  round(oi, 0),
            "":           tag,
        })

    df = pd.DataFrame(rows)
    def hl(row):
        bg = "#d4edda" if 0.10 <= row["Kn/Kv"] <= 0.80 else ""
        return [f"background-color:{bg}"] * len(row)

    st.dataframe(df.style.apply(hl, axis=1), hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════
#  TABLA RESUMEN (expandible)
# ══════════════════════════════════════════════
st.divider()
with st.expander("📋 Ver tabla de resultados completa"):
    filas = [
        ("Tamaño de válvula",     f"{DN[idx]} mm — {NOM[idx]}"),
        ("Tipo de cuerpo",         cuerpo),
        ("Caudal Qmáx",           f"{q_dis:.2f} {u_q}  →  {qmax_m3h:.2f} m³/h"),
        ("P1 (aguas arriba)",     f"{p1_ui:.2f} {u_p}  →  {p1b:.4f} bar"),
        ("P2 (aguas abajo)",      f"{p2_ui:.2f} {u_p}  →  {p2b:.4f} bar"),
        ("ΔP",                    f"{fr_bar(dpb, u_p):.3f} {u_p}  →  {dpb:.4f} bar"),
        ("Kv requerido (Qmáx)",   f"{kv_max:.2f}"),
        ("Kv válvula (100%)",      str(kv_v)),
        ("Cv válvula (100%)",      str(cv_v)),
        ("Kn / Kv",               f"{kn_max:.4f}"),
        ("% Apertura (Qmáx)",     f"{op_max:.1f} %"),
        ("Zona de cavitación",     zlbl),
    ]
    if qmin_m3h:
        filas += [
            ("Caudal Qmín",       f"{qmin_ui:.2f} {u_q}  →  {qmin_m3h:.2f} m³/h"),
            ("Kv req. (Qmín)",    f"{kv_min:.2f}"),
            ("Kn/Kv (Qmín)",      f"{kn_min:.4f}"),
            ("% Apertura (Qmín)", f"{op_min:.1f} %"),
        ]
    st.table(pd.DataFrame(filas, columns=["Parámetro", "Valor"]))
