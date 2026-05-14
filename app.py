import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- CONFIGURACIÓN ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbz7h53IOklEjl8Lfsoen6LJxgVI8XDWbG1tofKd1GZJVUxLK3PoWRwcnmjavufBgGaRlg/exec".strip()
sheet_id = "10HAMo47BaGVm5WALX5H2G5SX9dfGhaO0PDCcpFT2Efw"
url_lectura = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Usuarios"

st.set_page_config(page_title="Polla Hípica Pro", page_icon="🏇", layout="wide")

# --- ESTADO INICIAL (Session State) ---
if 'retirados' not in st.session_state:
    st.session_state.retirados = []

# --- CONTROL DE TIEMPO ---
tz = pytz.timezone('America/Caracas')
ahora = datetime.now(tz)
dia_semana = ahora.weekday() 
hora_actual = ahora.hour

taquilla_abierta = not ( (dia_semana == 5 and hora_actual >= 18) or (dia_semana == 6) )

# --- CARGA DE DATOS ---
def cargar_datos():
    try:
        temp_df = pd.read_csv(url_lectura)
        temp_df.columns = temp_df.columns.str.strip()
        temp_df.rename(columns={'Crédito': 'Credito', 'Puntuación': 'Puntos'}, inplace=True)
        st.session_state.df = temp_df
    except Exception as e:
        st.error(f"Error al sincronizar: {e}")

if 'df' not in st.session_state:
    cargar_datos()

df = st.session_state.df

# --- PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["📝 Sellar Jugada", "📊 Ranking Multijugada", "🔐 Admin"])

with tab1:
    if not taquilla_abierta:
        st.error(f"🔴 TAQUILLA CERRADA - Hora actual: {ahora.strftime('%I:%M %p')}")
    else:
        st.success(f"🟢 TAQUILLA ABIERTA - Hora: {ahora.strftime('%I:%M %p')}")
        
        nombre_sel = st.selectbox("Selecciona tu nombre", df["Nombre"].unique(), index=None, placeholder="Elige un jugador...")
        
        if nombre_sel:
            user_row = df[df["Nombre"] == nombre_sel].iloc[-1]
            credito_disp = user_row["Credito"]
            pass_real = str(df[df["Nombre"] == nombre_sel]["Password"].iloc[0])
            
            st.info(f"Saldo disponible: **${credito_disp}**")
            pin = st.text_input("Ingresa tu PIN de seguridad", type="password")
            
            st.markdown("### Selecciona tus 6 ejemplares:")
            # Filtrar opciones: del 1 al 20 excluyendo los retirados
            opciones_base = list(range(1, 21))
            opciones_validas = [n for n in opciones_base if n not in st.session_state.retirados]
            
            col1, col2 = st.columns(2)
            jugadas = []
            for i in range(1, 7):
                with col1 if i <= 3 else col2:
                    # Usamos selectbox con opción nula (placeholder) para obligar selección
                    val = st.selectbox(f"Carrera {i}", opciones_validas, index=None, placeholder="--", key=f"sel_{i}")
                    jugadas.append(val)

            if st.button("🚀 Confirmar y Sellar ($10)"):
                # VALIDACIONES
                if not pin or pin != pass_real:
                    st.error("❌ PIN incorrecto o vacío.")
                elif None in jugadas:
                    st.warning("⚠️ Debes seleccionar los 6 ejemplares para poder sellar.")
                elif credito_disp < 10:
                    st.error("❌ Crédito insuficiente para esta jugada.")
                else:
                    payload = {
                        "tipo": "sellar", 
                        "nombre": nombre_sel, 
                        "credito": int(credito_disp - 10), 
                        "jugadas": jugadas
                    }
                    with st.spinner("Procesando jugada..."):
                        res = requests.post(WEB_APP_URL, json=payload)
                        if "Éxito" in res.text:
                            st.success("¡Jugada guardada con éxito! El crédito se ha actualizado.")
                            st.balloons()
                            # Limpieza automática: Recargamos datos y reiniciamos la app
                            cargar_datos()
                            st.rerun()
                        else: 
                            st.error(f"Error del servidor: {res.text}")

with tab2:
    st.subheader("Tabla de Posiciones en Tiempo Real")
    if not df.empty:
        df_rank = df.copy()
        
        # Convertir columnas a numérico por seguridad y manejar Nones
        cols_c = ["C1", "C2", "C3", "C4", "C5", "C6"]
        for c in cols_c:
            df_rank[c] = pd.to_numeric(df_rank[c], errors='coerce')
        
        # FILTRO CRÍTICO: Solo mostrar filas que tengan al menos la Carrera 1 marcada
        df_rank = df_rank[df_rank["C1"].notnull()]
        
        if not df_rank.empty:
            df_rank['#'] = df_rank.groupby('Nombre').cumcount() + 1
            ranking_final = df_rank[["Nombre", "#", "Puntos", "C1", "C2", "C3", "C4", "C5", "C6"]]
            st.dataframe(
                ranking_final.sort_values("Puntos", ascending=False), 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("Aún no hay jugadas selladas para mostrar.")
    st.subheader("Tabla de Posiciones")
    if not df.empty:
        df_rank = df.copy()
        df_rank['#'] = df_rank.groupby('Nombre').cumcount() + 1
        ranking_final = df_rank[["Nombre", "#", "Puntos", "C1", "C2", "C3", "C4", "C5", "C6"]]
        st.dataframe(ranking_final.sort_values("Puntos", ascending=False), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("⚙️ Gestión Administrativa")
    if st.text_input("Clave de Administrador", type="password") == "2026":
        
        # --- SECCIÓN DE RETIRADOS ---
        st.divider()
        st.subheader("🚫 Gestión de Retirados")
        retirados_input = st.multiselect(
            "Selecciona los números de ejemplares retirados (no aparecerán en la lista de jugadas):",
            list(range(1, 21)),
            default=st.session_state.retirados
        )
        if st.button("Actualizar Retirados"):
            st.session_state.retirados = retirados_input
            st.success("Lista de retirados actualizada.")

        # --- SECCIÓN DE RESULTADOS ---
        st.divider()
        st.subheader("🏆 Cargar Resultados de la Jornada")
        with st.form("admin_puntos"):
            resultados_jornada = []
            error_podio = False
            for i in range(1, 7):
                st.write(f"**Carrera {i}**")
                c1, c2, c3 = st.columns(3)
                p1 = c1.number_input("1ro", 0, 20, key=f"r1_{i}")
                p2 = c2.number_input("2do", 0, 20, key=f"r2_{i}")
                p3 = c3.number_input("3ro", 0, 20, key=f"r3_{i}")
                
                podio_activos = [n for n in [p1, p2, p3] if n != 0]
                if len(podio_activos) != len(set(podio_activos)):
                    st.error(f"Repetición detectada en Carrera {i}")
                    error_podio = True
                resultados_jornada.append({"p1": p1, "p2": p2, "p3": p3})

            if st.form_submit_button("Publicar y Calcular Puntos"):
                if not error_podio:
                    requests.post(WEB_APP_URL, json={"tipo": "resultados", "ganadores": resultados_jornada})
                    st.success("Resultados enviados al servidor.")
                    cargar_datos()