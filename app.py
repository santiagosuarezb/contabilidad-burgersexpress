import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import os
import io
import psycopg2
import psycopg2.extras

st.set_page_config(
    page_title="Burgers Express - Gestión",
    layout="wide",
    page_icon="🍔"
)

# ─── PALETA DE COLORES ─────────────────────────────────────────────────────────
COLOR_PRIMARY   = "#92e27a"   # verde principal
COLOR_SECONDARY = "#ffd166"   # dorado cálido
COLOR_DARK      = "#2d6a1f"   # verde oscuro (textos/bordes)
COLOR_LIGHT     = "#e4f5dc"   # verde muy claro (fondos)
COLOR_DANGER    = "#e74c3c"
COLOR_WARN      = "#f39c12"

st.markdown(f"""
<style>
/* ── Fuente global ── */
html, body, [class*="css"] {{
    font-family: 'Segoe UI', sans-serif;
}}

/* ── Encabezado superior ── */
header[data-testid="stHeader"] {{
    background: linear-gradient(90deg, {COLOR_PRIMARY} 0%, {COLOR_SECONDARY} 100%);
}}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {{
    background-color: {COLOR_LIGHT};
    border-right: 2px solid {COLOR_PRIMARY};
}}

/* ── Título principal ── */
h1 {{
    color: {COLOR_DARK} !important;
    font-weight: 800;
    letter-spacing: -0.5px;
    font-size: 40px !important;
}}
h2, h3 {{
    color: {COLOR_DARK} !important;
}}

/* ── Botones primarios ── */
div.stButton > button[kind="primary"],
div.stButton > button {{
    background: linear-gradient(135deg, {COLOR_PRIMARY}, #6ed45a) !important;
    color: #1a2e1a !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    padding: 0.55rem 1.2rem !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}}
div.stButton > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 14px rgba(146,226,122,0.45) !important;
}}

/* ── Botones secundarios ── */
div.stButton > button[kind="secondary"] {{
    background: transparent !important;
    border: 2px solid {COLOR_PRIMARY} !important;
    color: {COLOR_DARK} !important;
    border-radius: 8px !important;
}}

/* ── Form submit button ── */
div.stFormSubmitButton > button {{
    background: linear-gradient(135deg, {COLOR_PRIMARY}, #6ed45a) !important;
    color: #1a2e1a !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.6rem 1.4rem !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}}
div.stFormSubmitButton > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 14px rgba(146,226,122,0.45) !important;
}}

/* ── Métricas ── */
div[data-testid="metric-container"] {{
    background: white;
    border: 1.5px solid {COLOR_PRIMARY};
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    box-shadow: 0 2px 8px rgba(146,226,122,0.18);
}}
div[data-testid="metric-container"] label {{
    color: {COLOR_DARK} !important;
    font-weight: 600;
}}
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {{
    color: {COLOR_DARK} !important;
    font-weight: 800;
}}

/* ── Tabs ── */
div[data-testid="stTabs"] button[data-baseweb="tab"] {{
    font-weight: 600;
    border-radius: 8px 8px 0 0;
}}
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {{
    color: {COLOR_DARK} !important;
    border-bottom: 3px solid {COLOR_PRIMARY} !important;
}}

/* ── Alertas personalizadas ── */
div[data-testid="stAlert"] {{
    border-radius: 10px !important;
}}

/* ── Dataframe ── */
div[data-testid="stDataFrame"] {{
    border: 1.5px solid {COLOR_LIGHT};
    border-radius: 10px;
    overflow: hidden;
}}

/* ── Input fields ── */
div[data-baseweb="input"] input,
div[data-baseweb="select"] {{
    border-radius: 8px !important;
}}
div[data-baseweb="input"] input:focus {{
    border-color: {COLOR_PRIMARY} !important;
    box-shadow: 0 0 0 2px rgba(146,226,122,0.3) !important;
}}

/* ── Divisor ── */
hr {{
    border-color: {COLOR_LIGHT} !important;
    border-width: 2px !important;
}}

/* ── Download button ── */
div.stDownloadButton > button {{
    background: linear-gradient(135deg, {COLOR_SECONDARY}, #ffbb33) !important;
    color: #1a2e1a !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
}}
div.stDownloadButton > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 14px rgba(255,209,102,0.45) !important;
}}
</style>
""", unsafe_allow_html=True)

# ─── BASE DE DATOS ─────────────────────────────────────────────────────────────
PRECIOS_DEFAULT = {
    "Combo Simple": 0.0,
    "Combo Doble": 0.0,
    "Porción de Papas": 0.0,
}

def get_conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        st.error("⚠️ DATABASE_URL no está configurada. Agregá el secret en Streamlit Cloud.")
        st.stop()
    return psycopg2.connect(url)


def drop_meta(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[c for c in df.columns if c.startswith("_")], errors="ignore")

VENTAS_COLS = ["Fecha", "Cliente", "Domicilio/Retiro",
               "Cant. Combo Simple", "Cant. Combo Doble", "Cantidad Papas",
               "Precio Combo Simple", "Precio Combo Doble", "Precio Papas",
               "Total", "Forma de Pago"]
GASTOS_COLS = ["Fecha", "Descripción", "Categoría", "Monto", "Notas"]
INVENTARIO_COLS = ["Producto", "Categoría", "Unidad", "Stock Actual", "Stock Mínimo", "Costo Unitario"]
MOVIMIENTOS_COLS = ["Fecha", "Producto", "Tipo", "Cantidad", "Stock Resultante", "Notas"]

CATEGORIAS_GASTOS = [
    "Ingredientes / Insumos",
    "Packaging / Envases",
    "Servicios (luz, agua, gas)",
    "Alquiler",
    "Sueldos / Personal",
    "Marketing / Publicidad",
    "Transporte / Delivery",
    "Equipamiento",
    "Impuestos / Tasas",
    "Otros",
]

CATEGORIAS_INV = [
    "Carnes / Proteínas",
    "Vegetales / Frescos",
    "Lácteos",
    "Panes / Harinas",
    "Salsas / Condimentos",
    "Bebidas",
    "Packaging / Envases",
    "Limpieza / Higiene",
    "Otro",
]

UNIDADES = ["kg", "g", "litros", "ml", "unidades", "docenas", "bolsas", "cajas", "paquetes"]

PRODUCTOS_VENTA = [
    "Combo Simple",
    "Combo Doble",
    "Combo Triple",
    "Hamburguesa Simple",
    "Hamburguesa Doble",
    "Papas Fritas",
    "Bebida",
    "Postre",
    "Otro",
]


def fmt_currency(value):
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "-"


def fmt_num(value, decimals=2):
    try:
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return "-"


# ─── CAPA DE DATOS (PostgreSQL) ───────────────────────────────────────────────
def load_ventas() -> pd.DataFrame:
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id AS _id, fecha AS \"Fecha\", cliente AS \"Cliente\","
            " domicilio_retiro AS \"Domicilio/Retiro\","
            " cant_combo_simple AS \"Cant. Combo Simple\","
            " cant_combo_doble AS \"Cant. Combo Doble\","
            " cantidad_papas AS \"Cantidad Papas\","
            " precio_combo_simple AS \"Precio Combo Simple\","
            " precio_combo_doble AS \"Precio Combo Doble\","
            " precio_papas AS \"Precio Papas\","
            " total AS \"Total\", forma_pago AS \"Forma de Pago\""
            " FROM ventas ORDER BY fecha DESC, id DESC"
        )
        rows = cur.fetchall()
        conn.close()
        df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame(columns=["_id"] + VENTAS_COLS)
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error al cargar ventas: {e}")
        return pd.DataFrame(columns=["_id"] + VENTAS_COLS)


def append_venta(row: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ventas (fecha,cliente,domicilio_retiro,cant_combo_simple,"
        "cant_combo_doble,cantidad_papas,precio_combo_simple,precio_combo_doble,"
        "precio_papas,total,forma_pago) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            row["Fecha"], row["Cliente"], row["Domicilio/Retiro"],
            int(row.get("Cant. Combo Simple", 0)),
            int(row.get("Cant. Combo Doble", 0)),
            int(row.get("Cantidad Papas", 0)),
            float(row.get("Precio Combo Simple", 0)),
            float(row.get("Precio Combo Doble", 0)),
            float(row.get("Precio Papas", 0)),
            float(row["Total"]),
            row["Forma de Pago"],
        )
    )
    conn.commit()
    conn.close()


def delete_ventas(ids: list):
    if not ids:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM ventas WHERE id = ANY(%s)", (ids,))
    conn.commit()
    conn.close()


def load_gastos() -> pd.DataFrame:
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id AS _id, fecha AS \"Fecha\","
            " descripcion AS \"Descripción\", categoria AS \"Categoría\","
            " monto AS \"Monto\", notas AS \"Notas\""
            " FROM gastos ORDER BY fecha DESC, id DESC"
        )
        rows = cur.fetchall()
        conn.close()
        df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame(columns=["_id"] + GASTOS_COLS)
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error al cargar gastos: {e}")
        return pd.DataFrame(columns=["_id"] + GASTOS_COLS)


def append_gasto(row: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO gastos (fecha,descripcion,categoria,monto,notas) VALUES (%s,%s,%s,%s,%s)",
        (row["Fecha"], row["Descripción"], row["Categoría"],
         float(row["Monto"]), row.get("Notas", ""))
    )
    conn.commit()
    conn.close()


def delete_gastos(ids: list):
    if not ids:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM gastos WHERE id = ANY(%s)", (ids,))
    conn.commit()
    conn.close()


def load_inventario() -> pd.DataFrame:
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id AS _id, producto AS \"Producto\", categoria AS \"Categoría\","
            " unidad AS \"Unidad\", stock_actual AS \"Stock Actual\","
            " stock_minimo AS \"Stock Mínimo\", costo_unitario AS \"Costo Unitario\""
            " FROM inventario ORDER BY producto"
        )
        rows = cur.fetchall()
        conn.close()
        return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame(columns=["_id"] + INVENTARIO_COLS)
    except Exception as e:
        st.error(f"Error al cargar inventario: {e}")
        return pd.DataFrame(columns=["_id"] + INVENTARIO_COLS)


def insert_inventario(row: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO inventario (producto,categoria,unidad,stock_actual,stock_minimo,costo_unitario)"
        " VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (producto) DO NOTHING",
        (row["Producto"], row["Categoría"], row["Unidad"],
         float(row["Stock Actual"]), float(row["Stock Mínimo"]), float(row["Costo Unitario"]))
    )
    conn.commit()
    conn.close()


def update_stock_inventario(producto: str, nuevo_stock: float):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE inventario SET stock_actual = %s WHERE producto = %s",
                (round(nuevo_stock, 3), producto))
    conn.commit()
    conn.close()


def update_inventario(old_producto: str, nuevo_nombre: str, nueva_cat: str,
                      nueva_unidad: str, nuevo_stock_min: float, nuevo_costo: float):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE inventario SET producto=%s, categoria=%s, unidad=%s,"
        " stock_minimo=%s, costo_unitario=%s WHERE producto=%s",
        (nuevo_nombre, nueva_cat, nueva_unidad,
         round(nuevo_stock_min, 3), round(nuevo_costo, 2), old_producto)
    )
    conn.commit()
    conn.close()


def delete_inventario(producto: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM inventario WHERE producto = %s", (producto,))
    conn.commit()
    conn.close()


def load_movimientos() -> pd.DataFrame:
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id AS _id, fecha AS \"Fecha\", producto AS \"Producto\","
            " tipo AS \"Tipo\", cantidad AS \"Cantidad\","
            " stock_resultante AS \"Stock Resultante\", notas AS \"Notas\""
            " FROM movimientos_inv ORDER BY fecha DESC, id DESC"
        )
        rows = cur.fetchall()
        conn.close()
        df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame(columns=["_id"] + MOVIMIENTOS_COLS)
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error al cargar movimientos: {e}")
        return pd.DataFrame(columns=["_id"] + MOVIMIENTOS_COLS)


def append_movimiento(row: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO movimientos_inv (fecha,producto,tipo,cantidad,stock_resultante,notas)"
        " VALUES (%s,%s,%s,%s,%s,%s)",
        (row["Fecha"], row["Producto"], row["Tipo"],
         float(row["Cantidad"]), float(row["Stock Resultante"]), row.get("Notas", ""))
    )
    conn.commit()
    conn.close()


def load_precios() -> dict:
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT producto, precio FROM precios")
        rows = cur.fetchall()
        conn.close()
        return {r["producto"]: float(r["precio"]) for r in rows} if rows else PRECIOS_DEFAULT.copy()
    except Exception:
        return PRECIOS_DEFAULT.copy()


def save_precios(precios: dict):
    conn = get_conn()
    cur = conn.cursor()
    for producto, precio in precios.items():
        cur.execute(
            "INSERT INTO precios (producto, precio) VALUES (%s,%s)"
            " ON CONFLICT (producto) DO UPDATE SET precio=EXCLUDED.precio",
            (producto, float(precio))
        )
    conn.commit()
    conn.close()


def get_estado_stock(actual, minimo):
    try:
        actual, minimo = float(actual), float(minimo)
        if actual <= minimo:
            return "🔴 Crítico"
        elif actual <= minimo * 1.5:
            return "🟡 Bajo"
        else:
            return "🟢 OK"
    except Exception:
        return "⚪ S/D"


@st.cache_data
def load_excel(file):
    return pd.read_excel(file, sheet_name=None)


# ─── ALERTAS GLOBALES (barra superior) ────────────────────────────────────────
df_inv_global = load_inventario()
if not df_inv_global.empty and "Stock Actual" in df_inv_global.columns and "Stock Mínimo" in df_inv_global.columns:
    criticos = df_inv_global[
        pd.to_numeric(df_inv_global["Stock Actual"], errors="coerce") <=
        pd.to_numeric(df_inv_global["Stock Mínimo"], errors="coerce")
    ]
    bajos = df_inv_global[
        (pd.to_numeric(df_inv_global["Stock Actual"], errors="coerce") >
         pd.to_numeric(df_inv_global["Stock Mínimo"], errors="coerce")) &
        (pd.to_numeric(df_inv_global["Stock Actual"], errors="coerce") <=
         pd.to_numeric(df_inv_global["Stock Mínimo"], errors="coerce") * 1.5)
    ]
    if not criticos.empty:
        nombres = ", ".join(criticos["Producto"].tolist())
        st.error(f"🔴 **Stock crítico** — Reponer urgente: {nombres}")
    if not bajos.empty:
        nombres_b = ", ".join(bajos["Producto"].tolist())
        st.warning(f"🟡 **Stock bajo** — Pronto a agotarse: {nombres_b}")

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.title("🍔 Burgers Express: Sistema de gestión")
st.markdown("---")

# ─── TABS PRINCIPALES ─────────────────────────────────────────────────────────
tabs = st.tabs([
    "📊 Resumen",
    "➕ Registrar Venta",
    "➕ Registrar Gasto",
    "📦 Inventario",
    "🤝 Historial Ventas",
    "💸 Historial Gastos",
    "💰 Precios",
    "📂 Importar Excel",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — RESUMEN
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.header("Resumen General")

    df_v_all = load_ventas()
    df_g_all = load_gastos()
    df_inv_res = load_inventario()

    total_ventas = df_v_all["Total"].sum() if not df_v_all.empty else 0
    total_gastos = df_g_all["Monto"].sum() if not df_g_all.empty else 0
    balance = total_ventas - total_gastos
    margen = (balance / total_ventas * 100) if total_ventas > 0 else 0

    # Valor del inventario
    valor_inv = 0
    if not df_inv_res.empty and "Stock Actual" in df_inv_res.columns and "Costo Unitario" in df_inv_res.columns:
        df_inv_res["Stock Actual"] = pd.to_numeric(df_inv_res["Stock Actual"], errors="coerce").fillna(0)
        df_inv_res["Costo Unitario"] = pd.to_numeric(df_inv_res["Costo Unitario"], errors="coerce").fillna(0)
        valor_inv = (df_inv_res["Stock Actual"] * df_inv_res["Costo Unitario"]).sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Ingresos", fmt_currency(total_ventas))
    c2.metric("Total Gastos", fmt_currency(total_gastos))
    c3.metric("Balance Neto", fmt_currency(balance),
              delta=f"{margen:.1f}% margen" if total_ventas > 0 else None)
    c4.metric("Valor del Inventario", fmt_currency(valor_inv))
    c5.metric("Transacciones",
              f"{len(df_v_all)} ventas / {len(df_g_all)} gastos")

    if not df_v_all.empty or not df_g_all.empty:
        st.markdown("---")
        col_r1, col_r2 = st.columns(2)

        with col_r1:
            if not df_v_all.empty:
                if "Cant. Combo Simple" in df_v_all.columns and "Cant. Combo Doble" in df_v_all.columns:
                    tot_s = df_v_all["Cant. Combo Simple"].sum()
                    tot_d = df_v_all["Cant. Combo Doble"].sum()
                    df_combos = pd.DataFrame({
                        "Tipo": ["Combo Simple", "Combo Doble"],
                        "Cantidad": [tot_s, tot_d]
                    })
                    df_combos = df_combos[df_combos["Cantidad"] > 0]
                    if not df_combos.empty:
                        fig = px.pie(df_combos, values="Cantidad", names="Tipo",
                                     hole=0.4, title="Combos vendidos por tipo",
                                     color_discrete_sequence=["#92e27a","#ffd166"])
                        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                        st.plotly_chart(fig, use_container_width=True)

        with col_r2:
            if not df_g_all.empty:
                cat_counts = df_g_all.groupby("Categoría")["Monto"].sum().reset_index()
                fig2 = px.pie(cat_counts, values="Monto", names="Categoría",
                              hole=0.4, title="Distribución de Gastos",
                              color_discrete_sequence=["#ffd166","#ffb733","#e8a020","#c47d00","#ffe599","#92e27a","#6ed45a","#4fc43a"])
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

        if not df_v_all.empty and "Fecha" in df_v_all.columns:
            df_v_all["Fecha"] = pd.to_datetime(df_v_all["Fecha"], errors="coerce")
            df_v_all["Mes"] = df_v_all["Fecha"].dt.to_period("M").astype(str)
            ventas_mes = df_v_all.groupby("Mes")["Total"].sum().reset_index()
            ventas_mes.columns = ["Mes", "Ingresos"]

            if not df_g_all.empty and "Fecha" in df_g_all.columns:
                df_g_all["Fecha"] = pd.to_datetime(df_g_all["Fecha"], errors="coerce")
                df_g_all["Mes"] = df_g_all["Fecha"].dt.to_period("M").astype(str)
                gastos_mes = df_g_all.groupby("Mes")["Monto"].sum().reset_index()
                gastos_mes.columns = ["Mes", "Gastos"]
                merged = ventas_mes.merge(gastos_mes, on="Mes", how="outer").fillna(0)
            else:
                merged = ventas_mes.copy()
                merged["Gastos"] = 0

            fig3 = px.bar(
                merged.melt(id_vars="Mes", var_name="Tipo", value_name="Monto"),
                x="Mes", y="Monto", color="Tipo", barmode="group",
                title="Ingresos vs Gastos por Mes",
                color_discrete_map={"Ingresos": "#92e27a", "Gastos": "#ffd166"}
            )
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               yaxis=dict(gridcolor="#e4f5dc"))
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Aún no hay datos registrados. Usá las pestañas **Registrar Venta** y **Registrar Gasto** para comenzar.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — REGISTRAR VENTA
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.header("Registrar Nueva Venta")

    precios_act = load_precios()
    precio_simple_act = precios_act.get("Combo Simple", 0.0)
    precio_doble_act  = precios_act.get("Combo Doble", 0.0)
    precio_papas_act  = precios_act.get("Porción de Papas", 0.0)

    if precio_simple_act == 0 and precio_doble_act == 0 and precio_papas_act == 0:
        st.warning("⚠️ Los precios están en $0. Configurá los precios en la pestaña **💰 Precios** antes de registrar ventas.")

    # Mostrar precios vigentes
    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("Combo Simple vigente", fmt_currency(precio_simple_act))
    pc2.metric("Combo Doble vigente",  fmt_currency(precio_doble_act))
    pc3.metric("Porción de Papas vigente", fmt_currency(precio_papas_act))

    st.markdown("---")

    with st.form("form_venta", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            fecha_v     = st.date_input("Fecha de la venta", value=date.today())
            cliente_v   = st.text_input("Cliente", placeholder="Nombre del cliente")
            domicilio_v = st.text_input("Domicilio de envío", placeholder="Dirección o dejá vacío si retiró")
            retiro_v    = st.checkbox("¿Retiró en el local?")

        with col2:
            st.markdown("**Combos**")
            cant_simples_v = st.number_input("Cantidad Combo Simple", min_value=0, step=1, value=0)
            cant_dobles_v  = st.number_input("Cantidad Combo Doble",  min_value=0, step=1, value=0)
            st.markdown("**Papas**")
            cant_papas_v   = st.number_input("Porciones de papas",    min_value=0, step=1, value=0)
            forma_pago_v   = st.selectbox("Forma de pago", ["Efectivo", "Transferencia"])

        with col3:
            st.markdown("**Detalle del total:**")
            subtotal_simples = cant_simples_v * precio_simple_act
            subtotal_dobles  = cant_dobles_v  * precio_doble_act
            subtotal_papas   = cant_papas_v   * precio_papas_act
            total_v          = subtotal_simples + subtotal_dobles + subtotal_papas

            if cant_simples_v > 0:
                st.markdown(f"🍔 Combo Simple × {cant_simples_v} @ {fmt_currency(precio_simple_act)} = **{fmt_currency(subtotal_simples)}**")
            if cant_dobles_v > 0:
                st.markdown(f"🍔🍔 Combo Doble × {cant_dobles_v} @ {fmt_currency(precio_doble_act)} = **{fmt_currency(subtotal_dobles)}**")
            if cant_papas_v > 0:
                st.markdown(f"🍟 Papas × {cant_papas_v} @ {fmt_currency(precio_papas_act)} = **{fmt_currency(subtotal_papas)}**")

            st.metric("💰 Total de la venta", fmt_currency(total_v))

        submitted_v = st.form_submit_button("✅ Registrar Venta", use_container_width=True)

    if submitted_v:
        if cant_simples_v == 0 and cant_dobles_v == 0 and cant_papas_v == 0:
            st.error("Ingresá al menos 1 combo o 1 porción de papas.")
        else:
            domicilio_final = "Retiró en local" if retiro_v else (domicilio_v.strip() or "Sin especificar")
            resumen = []
            if cant_simples_v > 0: resumen.append(f"Simple ×{cant_simples_v}")
            if cant_dobles_v  > 0: resumen.append(f"Doble ×{cant_dobles_v}")
            if cant_papas_v   > 0: resumen.append(f"Papas ×{cant_papas_v}")
            append_venta({
                "Fecha":              fecha_v.strftime("%Y-%m-%d"),
                "Cliente":            cliente_v.strip() or "Mostrador",
                "Domicilio/Retiro":   domicilio_final,
                "Cant. Combo Simple": int(cant_simples_v),
                "Cant. Combo Doble":  int(cant_dobles_v),
                "Cantidad Papas":     int(cant_papas_v),
                "Precio Combo Simple": precio_simple_act,
                "Precio Combo Doble":  precio_doble_act,
                "Precio Papas":        precio_papas_act,
                "Total":               round(total_v, 2),
                "Forma de Pago":       forma_pago_v,
            })
            st.success(f"✅ Venta registrada — {' + '.join(resumen)} → **{fmt_currency(total_v)}** ({forma_pago_v})")
            st.rerun()

    st.markdown("---")
    st.subheader("Últimas 5 ventas registradas")
    df_recientes_v = load_ventas()
    if not df_recientes_v.empty:
        cols_show_rec = [c for c in ["Fecha", "Cliente", "Domicilio/Retiro",
                                      "Cant. Combo Simple", "Cant. Combo Doble",
                                      "Cantidad Papas", "Total", "Forma de Pago"]
                         if c in df_recientes_v.columns]
        st.dataframe(df_recientes_v.tail(5)[cols_show_rec], use_container_width=True, hide_index=True)
    else:
        st.info("Todavía no hay ventas registradas.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — REGISTRAR GASTO
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.header("Registrar Nuevo Gasto")

    with st.form("form_gasto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha_g = st.date_input("Fecha", value=date.today(), key="fecha_g")
            descripcion_g = st.text_input("Descripción", placeholder="¿En qué se gastó?")
            categoria_g = st.selectbox("Categoría", CATEGORIAS_GASTOS)
        with col2:
            monto_g = st.number_input("Monto ($)", min_value=0.0, step=0.5, format="%.2f")
            notas_g = st.text_area("Notas (opcional)", placeholder="Proveedor, factura, etc.", key="notas_g")

        submitted_g = st.form_submit_button("✅ Registrar Gasto", use_container_width=True)

    if submitted_g:
        if monto_g <= 0:
            st.error("El monto debe ser mayor a $0.")
        elif not descripcion_g.strip():
            st.error("Por favor ingresá una descripción.")
        else:
            append_gasto({
                "Fecha": fecha_g.strftime("%Y-%m-%d"),
                "Descripción": descripcion_g.strip(),
                "Categoría": categoria_g,
                "Monto": round(monto_g, 2),
                "Notas": notas_g.strip(),
            })
            st.success(f"Gasto registrado: {descripcion_g.strip()} — {fmt_currency(monto_g)}")
            st.rerun()

    st.markdown("---")
    st.subheader("Últimos 5 gastos registrados")
    df_recientes_g = load_gastos()
    if not df_recientes_g.empty:
        st.dataframe(df_recientes_g.tail(5)[["Fecha", "Descripción", "Categoría", "Monto"]],
                     use_container_width=True, hide_index=True)
    else:
        st.info("Todavía no hay gastos registrados.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — INVENTARIO
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.header("Gestión de Inventario")

    df_inv = load_inventario()

    inv_sub = st.tabs([
        "📋 Estado del Stock",
        "🔄 Actualizar Stock",
        "➕ Agregar Producto/Materia Prima",
        "📜 Historial de Movimientos",
        "✏️ Editar / Eliminar Producto",
    ])

    # ── SUB-TAB A: ESTADO DEL STOCK ──────────────────────────────────────────
    with inv_sub[0]:
        if df_inv.empty:
            st.info("No hay productos cargados todavía. Usá la pestaña **Agregar Producto/Materia Prima** para empezar.")
        else:
            df_inv["Stock Actual"] = pd.to_numeric(df_inv["Stock Actual"], errors="coerce").fillna(0)
            df_inv["Stock Mínimo"] = pd.to_numeric(df_inv["Stock Mínimo"], errors="coerce").fillna(0)
            df_inv["Costo Unitario"] = pd.to_numeric(df_inv["Costo Unitario"], errors="coerce").fillna(0)
            df_inv["Estado"] = df_inv.apply(
                lambda r: get_estado_stock(r["Stock Actual"], r["Stock Mínimo"]), axis=1
            )
            df_inv["Valor Total"] = df_inv["Stock Actual"] * df_inv["Costo Unitario"]

            # KPIs
            total_items = len(df_inv)
            criticos_n = len(df_inv[df_inv["Estado"] == "🔴 Crítico"])
            bajos_n = len(df_inv[df_inv["Estado"] == "🟡 Bajo"])
            valor_total_inv = df_inv["Valor Total"].sum()

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Productos / Insumos", str(total_items))
            k2.metric("En estado crítico", str(criticos_n), delta=f"-{criticos_n}" if criticos_n > 0 else None,
                      delta_color="inverse" if criticos_n > 0 else "off")
            k3.metric("Stock bajo", str(bajos_n), delta=f"-{bajos_n}" if bajos_n > 0 else None,
                      delta_color="inverse" if bajos_n > 0 else "off")
            k4.metric("Valor total del inventario", fmt_currency(valor_total_inv))

            # Tabla de estado
            st.markdown("---")
            orden_estado = {"🔴 Crítico": 0, "🟡 Bajo": 1, "🟢 OK": 2, "⚪ S/D": 3}
            df_display = df_inv.copy()
            df_display["_orden"] = df_display["Estado"].map(orden_estado)
            df_display = df_display.sort_values("_orden").drop(columns=["_orden"])

            cols_show = ["Producto", "Categoría", "Unidad", "Stock Actual", "Stock Mínimo", "Estado", "Valor Total"]
            df_display["Valor Total"] = df_display["Valor Total"].apply(fmt_currency)
            st.dataframe(df_display[cols_show], use_container_width=True, hide_index=True)

            # Gráfico de stock vs mínimo
            st.markdown("---")
            st.subheader("Stock Actual vs Mínimo por Producto")
            df_grafico = df_inv[["Producto", "Stock Actual", "Stock Mínimo"]].copy()
            df_grafico_melt = df_grafico.melt(id_vars="Producto", var_name="Tipo", value_name="Cantidad")
            fig_inv = px.bar(
                df_grafico_melt,
                x="Producto", y="Cantidad", color="Tipo", barmode="group",
                color_discrete_map={"Stock Actual": "#92e27a", "Stock Mínimo": "#ffd166"},
                title="Comparación Stock Actual vs Mínimo"
            )
            fig_inv.update_layout(xaxis_tickangle=-30, paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)", yaxis=dict(gridcolor="#e4f5dc"))
            st.plotly_chart(fig_inv, use_container_width=True)

            # Por categoría
            if "Categoría" in df_inv.columns:
                cat_val = df_inv.groupby("Categoría")["Valor Total"].sum().reset_index()
                fig_cat = px.pie(cat_val, values="Valor Total", names="Categoría",
                                 hole=0.4, title="Valor del Inventario por Categoría",
                                 color_discrete_sequence=["#92e27a","#6ed45a","#4fc43a","#2d6a1f","#b8f0a4","#ffd166","#ffb733","#e8a020","#c47d00"])
                fig_cat.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_cat, use_container_width=True)

    # ── SUB-TAB B: ACTUALIZAR STOCK ──────────────────────────────────────────
    with inv_sub[1]:
        if df_inv.empty:
            st.info("Primero agregá productos en la pestaña **Agregar Producto/Materia Prima**.")
        else:
            st.subheader("Actualizar Stock de un Producto")
            df_inv["Stock Actual"] = pd.to_numeric(df_inv["Stock Actual"], errors="coerce").fillna(0)

            with st.form("form_actualizar_stock", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    producto_sel = st.selectbox(
                        "Seleccioná el producto",
                        df_inv["Producto"].tolist()
                    )
                    tipo_mov = st.selectbox(
                        "Tipo de movimiento",
                        ["Entrada (compra/recepción)", "Salida (uso/merma)", "Ajuste manual"]
                    )
                with col2:
                    cantidad_mov = st.number_input("Cantidad", min_value=0.0, step=0.5, format="%.2f")
                    fecha_mov = st.date_input("Fecha", value=date.today(), key="fecha_mov")
                    notas_mov = st.text_area("Notas (opcional)", placeholder="Proveedor, motivo, etc.", key="notas_mov")

                # Mostrar stock actual del producto seleccionado
                row_sel = df_inv[df_inv["Producto"] == producto_sel].iloc[0]
                stock_actual_sel = float(row_sel["Stock Actual"])
                stock_min_sel = float(row_sel["Stock Mínimo"])
                unidad_sel = row_sel.get("Unidad", "")
                st.info(f"Stock actual de **{producto_sel}**: {fmt_num(stock_actual_sel)} {unidad_sel} | "
                        f"Mínimo: {fmt_num(stock_min_sel)} {unidad_sel} | "
                        f"Estado: {get_estado_stock(stock_actual_sel, stock_min_sel)}")

                submitted_mov = st.form_submit_button("✅ Registrar Movimiento", use_container_width=True)

            if submitted_mov:
                if cantidad_mov <= 0:
                    st.error("La cantidad debe ser mayor a 0.")
                else:
                    df_inv_upd = load_inventario()
                    df_inv_upd["Stock Actual"] = pd.to_numeric(df_inv_upd["Stock Actual"], errors="coerce").fillna(0)
                    idx = df_inv_upd[df_inv_upd["Producto"] == producto_sel].index[0]

                    if "Entrada" in tipo_mov:
                        nuevo_stock = df_inv_upd.at[idx, "Stock Actual"] + cantidad_mov
                        tipo_label = "Entrada"
                    elif "Salida" in tipo_mov:
                        nuevo_stock = max(0, df_inv_upd.at[idx, "Stock Actual"] - cantidad_mov)
                        tipo_label = "Salida"
                    else:
                        nuevo_stock = cantidad_mov
                        tipo_label = "Ajuste"

                    update_stock_inventario(producto_sel, nuevo_stock)

                    append_movimiento({
                        "Fecha": fecha_mov.strftime("%Y-%m-%d"),
                        "Producto": producto_sel,
                        "Tipo": tipo_label,
                        "Cantidad": round(cantidad_mov, 3),
                        "Stock Resultante": round(nuevo_stock, 3),
                        "Notas": notas_mov.strip(),
                    })

                    nuevo_estado = get_estado_stock(nuevo_stock, stock_min_sel)
                    st.success(f"Stock actualizado: **{producto_sel}** → {fmt_num(nuevo_stock)} {unidad_sel}  |  Estado: {nuevo_estado}")

                    if nuevo_estado == "🔴 Crítico":
                        st.error(f"⚠️ **{producto_sel}** está en stock crítico. Reponerlo lo antes posible.")
                    elif nuevo_estado == "🟡 Bajo":
                        st.warning(f"⚠️ **{producto_sel}** está por debajo del nivel mínimo sugerido.")

                    st.rerun()

    # ── SUB-TAB C: AGREGAR PRODUCTO ──────────────────────────────────────────
    with inv_sub[2]:
        st.subheader("Agregar Nuevo Producto o Materia Prima")

        with st.form("form_nuevo_producto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre_prod = st.text_input("Nombre del producto / insumo", placeholder="Ej: Carne picada, Pan de hamburguesa...")
                categoria_prod = st.selectbox("Categoría", CATEGORIAS_INV)
                unidad_prod = st.selectbox("Unidad de medida", UNIDADES)
            with col2:
                stock_inicial = st.number_input("Stock inicial", min_value=0.0, step=0.5, format="%.3f")
                stock_minimo = st.number_input("Stock mínimo (alerta)", min_value=0.0, step=0.5, format="%.3f",
                                               help="Cuando el stock baje de este valor, recibirás una alerta")
                costo_unitario = st.number_input("Costo unitario ($)", min_value=0.0, step=0.5, format="%.2f")

            submitted_prod = st.form_submit_button("✅ Agregar al Inventario", use_container_width=True)

        if submitted_prod:
            if not nombre_prod.strip():
                st.error("El nombre del producto es obligatorio.")
            else:
                df_inv_check = load_inventario()
                if not df_inv_check.empty and nombre_prod.strip() in df_inv_check["Producto"].tolist():
                    st.error(f"Ya existe un producto llamado **{nombre_prod.strip()}**. Cambiá el nombre o editalo desde la pestaña correspondiente.")
                else:
                    nuevo = {
                        "Producto": nombre_prod.strip(),
                        "Categoría": categoria_prod,
                        "Unidad": unidad_prod,
                        "Stock Actual": round(stock_inicial, 3),
                        "Stock Mínimo": round(stock_minimo, 3),
                        "Costo Unitario": round(costo_unitario, 2),
                    }
                    insert_inventario(nuevo)

                    if stock_inicial > 0:
                        append_movimiento({
                            "Fecha": date.today().strftime("%Y-%m-%d"),
                            "Producto": nombre_prod.strip(),
                            "Tipo": "Entrada",
                            "Cantidad": round(stock_inicial, 3),
                            "Stock Resultante": round(stock_inicial, 3),
                            "Notas": "Stock inicial al dar de alta el producto",
                        })

                    st.success(f"Producto **{nombre_prod.strip()}** agregado al inventario con stock inicial de {fmt_num(stock_inicial, 3)} {unidad_prod}.")
                    st.rerun()

        # Previsualización de inventario actual
        df_inv_preview = load_inventario()
        if not df_inv_preview.empty:
            st.markdown("---")
            st.subheader("Inventario actual")
            st.dataframe(drop_meta(df_inv_preview), use_container_width=True, hide_index=True)

    # ── SUB-TAB D: HISTORIAL DE MOVIMIENTOS ──────────────────────────────────
    with inv_sub[3]:
        st.subheader("Historial de Movimientos de Stock")
        df_mov = load_movimientos()

        if df_mov.empty:
            st.info("No hay movimientos registrados todavía.")
        else:
            df_mov["Fecha"] = pd.to_datetime(df_mov["Fecha"], errors="coerce")

            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                fecha_mov_desde = st.date_input("Desde", value=df_mov["Fecha"].min().date(), key="mov_desde")
            with col_f2:
                fecha_mov_hasta = st.date_input("Hasta", value=date.today(), key="mov_hasta")
            with col_f3:
                filtro_tipo = st.multiselect("Tipo", options=["Entrada", "Salida", "Ajuste"], default=[])

            mask_mov = (df_mov["Fecha"].dt.date >= fecha_mov_desde) & (df_mov["Fecha"].dt.date <= fecha_mov_hasta)
            if filtro_tipo:
                mask_mov = mask_mov & df_mov["Tipo"].isin(filtro_tipo)
            df_mov_f = df_mov[mask_mov].sort_values("Fecha", ascending=False).reset_index(drop=True)

            entradas = df_mov_f[df_mov_f["Tipo"] == "Entrada"]["Cantidad"].sum()
            salidas = df_mov_f[df_mov_f["Tipo"] == "Salida"]["Cantidad"].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Total entradas", fmt_num(entradas, 3))
            m2.metric("Total salidas", fmt_num(salidas, 3))
            m3.metric("Registros", str(len(df_mov_f)))

            st.dataframe(drop_meta(df_mov_f), use_container_width=True, hide_index=True)

            csv_mov = df_mov_f.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar CSV", data=csv_mov,
                               file_name="movimientos_inventario.csv", mime="text/csv")

    # ── SUB-TAB E: EDITAR / ELIMINAR ─────────────────────────────────────────
    with inv_sub[4]:
        st.subheader("Editar o Eliminar Producto")
        df_inv_edit = load_inventario()

        if df_inv_edit.empty:
            st.info("No hay productos cargados todavía.")
        else:
            producto_editar = st.selectbox("Seleccioná un producto", df_inv_edit["Producto"].tolist(), key="sel_edit")
            idx_edit = df_inv_edit[df_inv_edit["Producto"] == producto_editar].index[0]
            row_edit = df_inv_edit.loc[idx_edit]

            with st.form("form_editar_producto"):
                col1, col2 = st.columns(2)
                with col1:
                    nuevo_nombre = st.text_input("Nombre", value=str(row_edit["Producto"]))
                    nueva_cat = st.selectbox("Categoría", CATEGORIAS_INV,
                                            index=CATEGORIAS_INV.index(row_edit["Categoría"])
                                            if row_edit["Categoría"] in CATEGORIAS_INV else 0)
                    nueva_unidad = st.selectbox("Unidad", UNIDADES,
                                               index=UNIDADES.index(row_edit["Unidad"])
                                               if row_edit["Unidad"] in UNIDADES else 0)
                with col2:
                    nuevo_stock_min = st.number_input("Stock Mínimo",
                                                      value=float(row_edit["Stock Mínimo"]),
                                                      min_value=0.0, step=0.5, format="%.3f",
                                                      key="edit_min")
                    nuevo_costo = st.number_input("Costo Unitario ($)",
                                                  value=float(row_edit["Costo Unitario"]),
                                                  min_value=0.0, step=0.5, format="%.2f",
                                                  key="edit_costo")
                    st.info(f"Stock actual: **{fmt_num(float(row_edit['Stock Actual']), 3)} {row_edit['Unidad']}**  \n"
                            "Para cambiar el stock usá la pestaña **Actualizar Stock**.")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    guardar_edit = st.form_submit_button("💾 Guardar cambios", use_container_width=True)
                with col_btn2:
                    eliminar_prod = st.form_submit_button("🗑️ Eliminar producto", use_container_width=True,
                                                          type="secondary")

            if guardar_edit:
                update_inventario(producto_editar, nuevo_nombre.strip(), nueva_cat,
                                  nueva_unidad, nuevo_stock_min, nuevo_costo)
                st.success(f"Producto **{nuevo_nombre.strip()}** actualizado correctamente.")
                st.rerun()

            if eliminar_prod:
                delete_inventario(producto_editar)
                st.success(f"Producto **{producto_editar}** eliminado del inventario.")
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — HISTORIAL VENTAS
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.header("Historial de Ventas")
    df_hv = load_ventas()

    if not df_hv.empty:
        df_hv["Fecha"] = pd.to_datetime(df_hv["Fecha"], errors="coerce")

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            fecha_desde = st.date_input("Desde", value=df_hv["Fecha"].min().date(), key="hv_desde")
        with col_f2:
            fecha_hasta = st.date_input("Hasta", value=date.today(), key="hv_hasta")
        with col_f3:
            filtro_pago = st.multiselect("Forma de pago", options=["Efectivo", "Transferencia"], default=[])

        mask = (df_hv["Fecha"].dt.date >= fecha_desde) & (df_hv["Fecha"].dt.date <= fecha_hasta)
        if filtro_pago and "Forma de Pago" in df_hv.columns:
            mask = mask & df_hv["Forma de Pago"].isin(filtro_pago)
        df_filtrado_v = df_hv[mask]

        total_f   = df_filtrado_v["Total"].sum()
        ticket_f  = df_filtrado_v["Total"].mean() if not df_filtrado_v.empty else 0
        tot_simples = df_filtrado_v["Cant. Combo Simple"].sum() if "Cant. Combo Simple" in df_filtrado_v.columns else 0
        tot_dobles  = df_filtrado_v["Cant. Combo Doble"].sum()  if "Cant. Combo Doble"  in df_filtrado_v.columns else 0
        tot_papas_f = df_filtrado_v["Cantidad Papas"].sum()     if "Cantidad Papas"     in df_filtrado_v.columns else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total del período",  fmt_currency(total_f))
        c2.metric("Ticket promedio",    fmt_currency(ticket_f))
        c3.metric("Combos Simples",     str(int(tot_simples)))
        c4.metric("Combos Dobles",      str(int(tot_dobles)))
        c5.metric("Porciones de papas", str(int(tot_papas_f)))

        st.dataframe(
            drop_meta(df_filtrado_v.sort_values("Fecha", ascending=False).reset_index(drop=True)),
            use_container_width=True, hide_index=True
        )

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_v = df_filtrado_v.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar CSV", data=csv_v,
                               file_name="ventas.csv", mime="text/csv")
        with col_dl2:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_filtrado_v.to_excel(writer, index=False, sheet_name="Ventas")
            st.download_button("⬇️ Descargar Excel", data=buffer.getvalue(),
                               file_name="ventas.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("---")
        with st.expander("🗑️ Eliminar ventas"):
            df_hv_del = load_ventas()
            df_hv_del["Fecha"] = pd.to_datetime(df_hv_del["Fecha"], errors="coerce")
            df_hv_del = df_hv_del.sort_values("Fecha", ascending=False).reset_index(drop=True)

            # Construir etiqueta legible para cada venta
            def label_venta(row):
                fecha = row["Fecha"].strftime("%d/%m/%Y") if pd.notna(row["Fecha"]) else "?"
                cliente = row.get("Cliente", "?")
                total = fmt_currency(row.get("Total", 0))
                s = int(row.get("Cant. Combo Simple", 0) or 0)
                d = int(row.get("Cant. Combo Doble", 0) or 0)
                p = int(row.get("Cantidad Papas", 0) or 0)
                detalle = " | ".join(filter(None, [
                    f"Simple ×{s}" if s else "",
                    f"Doble ×{d}"  if d else "",
                    f"Papas ×{p}"  if p else "",
                ]))
                return f"{fecha} — {cliente} — {detalle} — {total}"

            etiquetas = df_hv_del.apply(label_venta, axis=1).tolist()
            opciones_del = {lbl: idx for idx, lbl in enumerate(etiquetas)}

            seleccionadas = st.multiselect(
                "Seleccioná las ventas que querés eliminar:",
                options=list(opciones_del.keys()),
                key="del_ventas_sel"
            )

            if seleccionadas:
                st.warning(f"Se eliminarán **{len(seleccionadas)}** venta(s). Esta acción no se puede deshacer.")
                if st.button("🗑️ Confirmar eliminación", type="secondary", key="confirmar_del_ventas"):
                    ids_borrar = [int(df_hv_del.loc[opciones_del[lbl], "_id"]) for lbl in seleccionadas]
                    delete_ventas(ids_borrar)
                    st.success(f"✅ {len(seleccionadas)} venta(s) eliminada(s).")
                    st.rerun()
    else:
        st.info("No hay ventas registradas aún.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 — HISTORIAL GASTOS
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.header("Historial de Gastos")
    df_hg = load_gastos()

    if not df_hg.empty:
        df_hg["Fecha"] = pd.to_datetime(df_hg["Fecha"], errors="coerce")

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            fecha_desde_g = st.date_input("Desde", value=df_hg["Fecha"].min().date(), key="hg_desde")
        with col_f2:
            fecha_hasta_g = st.date_input("Hasta", value=date.today(), key="hg_hasta")
        with col_f3:
            filtro_cat = st.multiselect("Categoría", options=df_hg["Categoría"].unique().tolist(), default=[])

        mask_g = (df_hg["Fecha"].dt.date >= fecha_desde_g) & (df_hg["Fecha"].dt.date <= fecha_hasta_g)
        if filtro_cat:
            mask_g = mask_g & df_hg["Categoría"].isin(filtro_cat)
        df_filtrado_g = df_hg[mask_g]

        total_fg = df_filtrado_g["Monto"].sum()
        c1, c2 = st.columns(2)
        c1.metric("Total gastos del período", fmt_currency(total_fg))
        c2.metric("Registros", str(len(df_filtrado_g)))

        st.dataframe(
            drop_meta(df_filtrado_g.sort_values("Fecha", ascending=False).reset_index(drop=True)),
            use_container_width=True, hide_index=True
        )

        if not df_filtrado_g.empty:
            cat_sum = df_filtrado_g.groupby("Categoría")["Monto"].sum().reset_index()
            fig = px.bar(cat_sum.sort_values("Monto", ascending=True),
                         x="Monto", y="Categoría", orientation="h",
                         title="Gastos por Categoría (período seleccionado)",
                         color="Monto", color_continuous_scale=["#ffe599", "#ffd166", "#ffb733", "#e8a020", "#c47d00"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              xaxis=dict(gridcolor="#e4f5dc"))
            st.plotly_chart(fig, use_container_width=True)

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_g = df_filtrado_g.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar CSV", data=csv_g,
                               file_name="gastos.csv", mime="text/csv")
        with col_dl2:
            buffer_g = io.BytesIO()
            with pd.ExcelWriter(buffer_g, engine="openpyxl") as writer:
                df_filtrado_g.to_excel(writer, index=False, sheet_name="Gastos")
            st.download_button("⬇️ Descargar Excel", data=buffer_g.getvalue(),
                               file_name="gastos.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("---")
        with st.expander("🗑️ Eliminar gastos"):
            df_hg_del = load_gastos()
            df_hg_del["Fecha"] = pd.to_datetime(df_hg_del["Fecha"], errors="coerce")
            df_hg_del = df_hg_del.sort_values("Fecha", ascending=False).reset_index(drop=True)

            def label_gasto(row):
                fecha = row["Fecha"].strftime("%d/%m/%Y") if pd.notna(row["Fecha"]) else "?"
                desc  = row.get("Descripción", "?")
                cat   = row.get("Categoría", "?")
                monto = fmt_currency(row.get("Monto", 0))
                return f"{fecha} — {desc} — {cat} — {monto}"

            etiquetas_g = df_hg_del.apply(label_gasto, axis=1).tolist()
            opciones_del_g = {lbl: idx for idx, lbl in enumerate(etiquetas_g)}

            seleccionados_g = st.multiselect(
                "Seleccioná los gastos que querés eliminar:",
                options=list(opciones_del_g.keys()),
                key="del_gastos_sel"
            )

            if seleccionados_g:
                st.warning(f"Se eliminarán **{len(seleccionados_g)}** gasto(s). Esta acción no se puede deshacer.")
                if st.button("🗑️ Confirmar eliminación", type="secondary", key="confirmar_del_gastos"):
                    ids_borrar_g = [int(df_hg_del.loc[opciones_del_g[lbl], "_id"]) for lbl in seleccionados_g]
                    delete_gastos(ids_borrar_g)
                    st.success(f"✅ {len(seleccionados_g)} gasto(s) eliminado(s).")
                    st.rerun()
    else:
        st.info("No hay gastos registrados aún.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7 — PRECIOS
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[6]:
    st.header("💰 Configuración de Precios")
    st.markdown("Actualizá los precios vigentes. Los cambios se aplican **solo a las ventas nuevas** — las ventas anteriores conservan el precio con el que fueron registradas.")

    precios_cfg = load_precios()

    with st.form("form_precios"):
        st.subheader("Precios actuales")
        cp1, cp2, cp3 = st.columns(3)
        with cp1:
            nuevo_simple = st.number_input(
                "Combo Simple ($)",
                min_value=0.0, step=0.5, format="%.2f",
                value=float(precios_cfg.get("Combo Simple", 0.0))
            )
        with cp2:
            nuevo_doble = st.number_input(
                "Combo Doble ($)",
                min_value=0.0, step=0.5, format="%.2f",
                value=float(precios_cfg.get("Combo Doble", 0.0))
            )
        with cp3:
            nuevo_papas = st.number_input(
                "Porción de Papas ($)",
                min_value=0.0, step=0.5, format="%.2f",
                value=float(precios_cfg.get("Porción de Papas", 0.0))
            )

        guardar_precios = st.form_submit_button("💾 Guardar precios", use_container_width=True)

    if guardar_precios:
        save_precios({
            "Combo Simple":    round(nuevo_simple, 2),
            "Combo Doble":     round(nuevo_doble, 2),
            "Porción de Papas": round(nuevo_papas, 2),
        })
        st.success(f"✅ Precios actualizados — Combo Simple: {fmt_currency(nuevo_simple)} | Combo Doble: {fmt_currency(nuevo_doble)} | Papas: {fmt_currency(nuevo_papas)}")
        st.rerun()

    st.markdown("---")
    st.subheader("Historial de precios en ventas registradas")
    df_hv_p = load_ventas()
    if not df_hv_p.empty and "Precio Combo" in df_hv_p.columns:
        cols_precio = [c for c in ["Fecha", "Tipo Combo", "Precio Combo", "Precio Papas"] if c in df_hv_p.columns]
        df_precios_hist = df_hv_p[cols_precio].drop_duplicates().sort_values("Fecha", ascending=False)
        st.info("Cada venta almacena el precio vigente al momento del registro, por lo que los precios históricos quedan preservados.")
        st.dataframe(df_precios_hist, use_container_width=True, hide_index=True)
    else:
        st.info("Registrá ventas para ver el historial de precios utilizados.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 8 — IMPORTAR EXCEL
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[7]:
    st.header("Importar desde Excel")
    st.markdown("Subí tu planilla Excel para ver los datos históricos. "
                "Los datos del Excel se muestran aquí pero **no reemplazan** los registros manuales.")

    uploaded_file = st.file_uploader(
        "📂 Subir archivo Excel",
        type=["xlsx", "xls"],
        help="Hojas esperadas: VENTAS, STOCK, GASTOS, INGEGR"
    )

    if uploaded_file:
        data = load_excel(uploaded_file)
        sheet_names = list(data.keys())
        st.success(f"Hojas encontradas: {', '.join(sheet_names)}")

        excel_tabs = st.tabs(["📈 Finanzas", "📦 Inventario", "🤝 Ventas", "💸 Gastos", "📋 Datos Crudos"])

        with excel_tabs[0]:
            fin_sheet = next((s for s in sheet_names if "ING" in s.upper()), None)
            if fin_sheet:
                df_fin = data[fin_sheet].dropna(how="all")
                col_map = {}
                for col in df_fin.columns:
                    cu = str(col).upper()
                    if "INGR" in cu: col_map["ingresos"] = col
                    elif "EGRE" in cu or "GASTO" in cu: col_map["egresos"] = col
                    elif "DIFER" in cu or "BALAN" in cu or "GANANCI" in cu: col_map["diferencia"] = col
                    elif "MES" in cu or "FECHA" in cu or "PERIOD" in cu: col_map["periodo"] = col
                if "ingresos" in col_map and "egresos" in col_map:
                    df_fin = df_fin.dropna(subset=[col_map["ingresos"]])
                    ti = df_fin[col_map["ingresos"]].sum()
                    te = df_fin[col_map["egresos"]].sum()
                    bal = ti - te
                    m = (bal / ti * 100) if ti > 0 else 0
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Ingresos", fmt_currency(ti))
                    c2.metric("Egresos", fmt_currency(te))
                    c3.metric("Balance", fmt_currency(bal))
                    c4.metric("Margen", f"{m:.1f}%")
                    if "periodo" in col_map:
                        fig = px.line(df_fin, x=col_map["periodo"],
                                      y=[col_map["ingresos"], col_map["egresos"]],
                                      markers=True,
                                      color_discrete_sequence=["#2ecc71", "#e74c3c"])
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.dataframe(df_fin, use_container_width=True)
            else:
                st.info("No se encontró la hoja INGEGR.")

        with excel_tabs[1]:
            stock_sheet = next((s for s in sheet_names if "STOCK" in s.upper() or "INVENT" in s.upper()), None)
            if stock_sheet:
                df_stock = data[stock_sheet].dropna(how="all")
                prod_col = next((c for c in df_stock.columns if any(k in str(c).upper() for k in ["PROD", "ITEM", "NOMBRE"])), None)
                cant_col = next((c for c in df_stock.columns if any(k in str(c).upper() for k in ["STOCK", "CANT", "ACTUAL"])), None)
                cost_col = next((c for c in df_stock.columns if any(k in str(c).upper() for k in ["COST", "PRECIO"])), None)
                if prod_col and cant_col:
                    cols = [c for c in [prod_col, cant_col, cost_col] if c]
                    df_clean = df_stock[cols].dropna(subset=[prod_col])
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.dataframe(df_clean, use_container_width=True, hide_index=True)
                    with c2:
                        fig = px.bar(df_clean, x=prod_col, y=cant_col,
                                     color=cant_col, color_continuous_scale="Greens",
                                     title="Stock por Producto")
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.dataframe(df_stock, use_container_width=True)
            else:
                st.info("No se encontró la hoja STOCK.")

        with excel_tabs[2]:
            venta_sheet = next((s for s in sheet_names if "VENTA" in s.upper()), None)
            if venta_sheet:
                df_ve = data[venta_sheet].dropna(how="all")
                total_col = next((c for c in df_ve.columns if any(k in str(c).upper() for k in ["TOTAL", "MONTO", "IMPORTE"])), None)
                if total_col:
                    df_ve[total_col] = pd.to_numeric(df_ve[total_col], errors="coerce")
                    st.metric("Total Ventas (Excel)", fmt_currency(df_ve[total_col].sum()))
                st.dataframe(df_ve, use_container_width=True, hide_index=True)
            else:
                st.info("No se encontró la hoja VENTAS.")

        with excel_tabs[3]:
            gasto_sheet = next((s for s in sheet_names if "GASTO" in s.upper() or "EGRE" in s.upper()), None)
            if gasto_sheet:
                df_ge = data[gasto_sheet].dropna(how="all")
                monto_col = next((c for c in df_ge.columns if any(k in str(c).upper() for k in ["MONTO", "TOTAL", "IMPORTE"])), None)
                if monto_col:
                    df_ge[monto_col] = pd.to_numeric(df_ge[monto_col], errors="coerce")
                    st.metric("Total Gastos (Excel)", fmt_currency(df_ge[monto_col].sum()))
                st.dataframe(df_ge, use_container_width=True, hide_index=True)
            else:
                st.info("No se encontró la hoja GASTOS.")

        with excel_tabs[4]:
            selected = st.selectbox("Hoja", sheet_names)
            st.dataframe(data[selected], use_container_width=True)
            csv_raw = data[selected].to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar CSV", data=csv_raw,
                               file_name=f"{selected}.csv", mime="text/csv")
    else:
        st.info("Subí tu planilla Excel para ver los datos históricos.")
