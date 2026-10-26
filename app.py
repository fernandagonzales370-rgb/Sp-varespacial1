# =============================================================================
# SpVAR ESPACIAL · HOMICIDIOS × LUCES NOCTURNAS (COLOMBIA)
# Interfaz Streamlit (lee base_app.csv y departamentos_33.gpkg del repositorio)
# =============================================================================
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
import folium
from branca.colormap import LinearColormap
import streamlit as st
from streamlit_folium import st_folium

RUTA = Path(__file__).parent

# -------------------------------------------------
# Configuración de página
# -------------------------------------------------
st.set_page_config(
    page_title="SpVAR Colombia · Homicidios × Luces",
    page_icon="🇨🇴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
    }
    h1, h2, h3 {
        color: #1e3a5f !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #e2e8f0;
        border-radius: 8px;
        color: #334155;
        padding: 8px 18px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e40af !important;
        color: white !important;
    }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# 1. Carga de datos
# -------------------------------------------------
@st.cache_data
def cargar_datos():
    base = pd.read_csv(RUTA / "base_app.csv", dtype={"cod_depto": str})
    base["cod_depto"] = base["cod_depto"].str.zfill(2)

    # Rellenar nombres faltantes con el de otros años del mismo departamento
    base["departamento"] = base.groupby("cod_depto")["departamento"].transform(
        lambda s: s.fillna(s.dropna().iloc[0]) if s.notna().any() else s
    )

    gdf_map = gpd.read_file(RUTA / "departamentos_33.gpkg")
    gdf_map["cod_depto"] = gdf_map["cod_depto"].astype(str).str.zfill(2)
    gdf_map = gdf_map.to_crs(epsg=4326)
    cent = gdf_map.geometry.to_crs(epsg=3116).centroid.to_crs(epsg=4326)
    gdf_map["lat"] = cent.y
    gdf_map["lon"] = cent.x

    anios = sorted(base["anio"].dropna().unique().astype(int).tolist())
    depts = sorted(base["cod_depto"].unique().tolist())
    nombres = base.drop_duplicates("cod_depto").set_index("cod_depto")["departamento"].to_dict()
    return base, gdf_map, anios, depts, nombres

try:
    base, gdf_map, ANIOS, DEPTS, NOMBRES = cargar_datos()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# -------------------------------------------------
# 2. Funciones
# -------------------------------------------------
def explorar(cod, anio):
    sub = base[(base["cod_depto"] == cod) & (base["anio"] == int(anio))]
    serie = base[base["cod_depto"] == cod].sort_values("anio")
    if sub.empty:
        return "—", "—", "—", None

    row = sub.iloc[0]
    vict  = row.get("total_victimas", np.nan)
    tasa  = row.get("tasa", np.nan)
    luces = row.get("luces", np.nan)

    k1 = f"{vict:,.0f}" if pd.notna(vict) else "—"
    k2 = f"{tasa:.1f}" if pd.notna(tasa) else "—"
    k3 = f"{luces:.2f}" if pd.notna(luces) else "—"

    fig, ax1 = plt.subplots(figsize=(9, 4.2))
    fig.patch.set_facecolor("white")
    ax1.set_facecolor("#f8fafc")

    ax1.plot(serie["anio"], serie["tasa"], color="#dc2626", marker="o", lw=2.5, markersize=7)
    ax1.set_ylabel("Tasa de homicidios\n(por 100.000 hab.)", color="#dc2626", fontsize=10)
    ax1.tick_params(axis="y", labelcolor="#dc2626")
    ax1.set_xlabel("Año", fontsize=10)

    ax2 = ax1.twinx()
    ax2.plot(serie["anio"], serie["luces"], color="#2563eb", marker="s", lw=2.5, markersize=7)
    ax2.set_ylabel("Luces nocturnas (VIIRS)", color="#2563eb", fontsize=10)
    ax2.tick_params(axis="y", labelcolor="#2563eb")

    ax1.set_title(f"{NOMBRES.get(cod, cod)}  ·  Evolución 2015-2024",
                  fontsize=14, color="#0f172a", pad=12, fontweight="medium")
    ax1.grid(True, alpha=0.22, linestyle="--")
    ax1.set_xticks(serie["anio"].unique())
    for spine in ["top", "right"]:
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    fig.tight_layout()
    return k1, k2, k3, fig

def mapa_realista(variable, anio):
    try:
        anio = int(anio)
        datos = base[base["anio"] == anio][["cod_depto", "departamento", variable]].dropna()
        gdf_tmp = gdf_map.merge(datos, on="cod_depto", how="left")

        m = folium.Map(location=[4.2, -73.5], zoom_start=5.6,
                       tiles="CartoDB positron", control_scale=True)

        vals = gdf_tmp[variable].dropna()
        if len(vals) == 0:
            return None

        if variable == "tasa":
            colors = ["#fff5f0", "#fee0d2", "#fcbba1", "#fc9272", "#fb6a4a", "#ef3b2c", "#cb181d", "#99000d"]
            caption = "Tasa de homicidios (por 100.000 hab.)"
        else:
            colors = ["#eff6ff", "#dbeafe", "#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1e40af"]
            caption = "Luces nocturnas (VIIRS)"

        colormap = LinearColormap(colors=colors, vmin=float(vals.min()), vmax=float(vals.max()), caption=caption)
        colormap.add_to(m)

        def style_fn(feature):
            val = feature["properties"].get(variable)
            return {
                "fillColor": colormap(val) if val is not None and not np.isnan(val) else "#e2e8f0",
                "color": "#334155",
                "weight": 0.7,
                "fillOpacity": 0.84,
            }

        folium.GeoJson(
            gdf_tmp,
            style_function=style_fn,
            tooltip=folium.GeoJsonTooltip(
                fields=["departamento", variable],
                aliases=["Departamento:", f"{caption}:"],
                localize=True, sticky=True
            )
        ).add_to(m)

        for _, row in gdf_tmp.dropna(subset=[variable]).iterrows():
            val = float(row[variable])
            radio = 5 + (val - vals.min()) / (vals.max() - vals.min() + 1e-6) * 13
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=float(radio),
                color="white", weight=1.8,
                fill=True, fill_color=colormap(val), fill_opacity=0.93,
                tooltip=f"<b>{row['departamento']}</b><br>{caption}: {val:.2f}"
            ).add_to(m)

        return m
    except Exception as e:
        st.error(f"No se pudo generar el mapa: {e}")
        return None

def simular(delta_tasa, delta_luces):
    imp_luces = (-0.23 * delta_tasa) + (-0.57 * delta_tasa * 0.40)
    imp_tasa  = -0.09 * delta_luces
    return f"""
### Resultado de la simulación

| Si cambia... | Magnitud | Impacto estimado |
|--------------|----------|------------------|
| Crecimiento de la **tasa de homicidios** | {delta_tasa:+.2f} | Sobre las luces: **{imp_luces:+.3f}** |
| Crecimiento de las **luces nocturnas** | {delta_luces:+.2f} | Sobre la tasa: **{imp_tasa:+.3f}** |

**Lectura sencilla**
Cuando aumenta el crecimiento de los homicidios, el modelo asocia una **disminución** en el crecimiento de las luces.
El efecto de los departamentos vecinos es más fuerte, pero **no es estable**.
Casi no hay evidencia de que las luces impulsen los homicidios.

> Resultado exploratorio. No constituye un pronóstico causal.
"""

def diagnostico():
    return """
### Modelos seleccionados

| Pregunta | Respuesta del análisis |
|----------|------------------------|
| ¿Qué explica mejor las **luces nocturnas**? | Modelo **SEM** + vecinos más cercanos (kNN3) |
| ¿Qué explica mejor la **tasa de homicidios**? | Modelo **MCO** |

<div style="background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%); border-left: 4px solid #2563eb; padding: 14px 18px; border-radius: 8px; margin: 16px 0;">
<b>Hallazgo principal</b><br>
Cuando en los departamentos vecinos aumenta el crecimiento de la tasa de homicidios, tiende a disminuir el crecimiento de las luces nocturnas.<br>
Sin embargo, <b>este resultado varía</b> según la matriz de vecinos, los departamentos pequeños y el periodo. Por eso <b>no se considera robusto</b>.
</div>

Es un resultado exploratorio. No permite afirmar relaciones causales.

### Limitaciones
- Periodo temporal corto (baja potencia estadística)
- Algunas observaciones fueron sustituidas
- Saltos importantes en las luces en 2017 y 2023
- El modelo SAC no pudo estimarse

### Fuentes de datos
MinDefensa (homicidios) · DANE (población y cartografía) · VIIRS (luces nocturnas)
"""


# -------------------------------------------------
# 3. Interfaz
# -------------------------------------------------
st.markdown("""
<div style="text-align:center; padding: 18px 0 10px 0;
            background: linear-gradient(135deg, #1e3a5f 0%, #1e40af 55%, #1d4ed8 100%);
            border-radius: 12px; margin-bottom: 18px;">
    <h1 style="margin:0 0 4px 0; font-size:1.85em; color:white; font-weight:700;">
        SpVAR Espacial
    </h1>
    <p style="margin:0; color:#bfdbfe; font-size:1.05em;">
        Homicidios y Luces Nocturnas · Colombia 2015-2024
    </p>
    <p style="margin:5px 0 0 0; color:#93c5fd; font-size:0.88em;">
        33 departamentos · Análisis exploratorio
    </p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "1 · Explorador Territorial",
    "2 · Mapas de Colombia",
    "3 · Simulación",
    "4 · Resultados del modelo"
])

# ---------- TAB 1 ----------
with tab1:
    st.markdown("Seleccione un departamento y un año para consultar los indicadores y su evolución.")

    col1, col2 = st.columns([2, 1])
    with col1:
        dd_depto = st.selectbox(
            "Departamento",
            options=DEPTS,
            format_func=lambda c: f"{NOMBRES.get(c, c)} ({c})",
            index=0
        )
    with col2:
        dd_anio = st.selectbox("Año", options=ANIOS, index=len(ANIOS) - 1)

    k1, k2, k3, fig = explorar(dd_depto, dd_anio)

    m1, m2, m3 = st.columns(3)
    m1.metric("Víctimas de homicidio", k1)
    m2.metric("Tasa por 100.000 hab.", k2)
    m3.metric("Luces nocturnas (VIIRS)", k3)

    if fig is not None:
        st.pyplot(fig)
        plt.close(fig)

# ---------- TAB 2 ----------
with tab2:
    st.markdown("Mapa coroplético por departamento.")
    c1, c2 = st.columns([2, 1])
    with c1:
        var_mapa = st.radio(
            "Variable",
            options=["tasa", "luces"],
            format_func=lambda v: "Tasa de homicidios" if v == "tasa" else "Luces nocturnas",
            horizontal=True
        )
    with c2:
        anio_mapa = st.selectbox("Año del mapa", options=ANIOS, index=len(ANIOS) - 1, key="anio_mapa")

    mapa = mapa_realista(var_mapa, anio_mapa)
    if mapa is not None:
        st_folium(mapa, height=600, use_container_width=True, returned_objects=[])

# ---------- TAB 3 ----------
with tab3:
    st.markdown("Ajuste los cambios en el crecimiento de cada variable y vea el impacto estimado.")
    s1, s2 = st.columns(2)
    with s1:
        d_tasa = st.slider("Cambio en el crecimiento de la tasa de homicidios",
                           -1.0, 1.0, 0.0, 0.05)
    with s2:
        d_luces = st.slider("Cambio en el crecimiento de las luces nocturnas",
                            -1.0, 1.0, 0.0, 0.05)
    st.markdown(simular(d_tasa, d_luces))

# ---------- TAB 4 ----------
with tab4:
    st.markdown(diagnostico(), unsafe_allow_html=True)
