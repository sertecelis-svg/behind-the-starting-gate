import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import time

# --- CONFIGURACIÓN ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbz7h53IOklEjl8Lfsoen6LJxgVI8XDWbG1tofKd1GZJVUxLK3PoWRwcnmjavufBgGaRlg/exec".strip()
sheet_id = "10HAMo47BaGVm5WALX5H2G5SX9dfGhaO0PDCcpFT2Efw"

st.set_page_config(page_title="Polla Hípica Pro", page_icon="🏇", layout="wide")

# --- CONTROL DE SESIÓN (LOGIN) ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None
if "es_admin" not in st.session_state:
    st.session_state.es_admin = False

# --- CONTROL DE TIEMPO (VENEZUELA) ---
tz = pytz.timezone('America/Caracas')
ahora = datetime.now(tz)
dia_semana = ahora.weekday()  # 0=Lunes, 5=Sábado, 6=Domingo
hora_actual = ahora.hour

# Sábado (5) después de las 6:00 PM o todo el Domingo (6) -> Cierra Taquilla
taquilla_abierta = not ( (dia_semana == 5 and hora_actual >= 18) or (dia_semana == 6) )

# Sábado (5) después de las 5:00 PM o todo el Domingo (6) -> Cierra Subasta
subasta_abierta = not ( (dia_semana == 5 and hora_actual >= 17) or (dia_semana == 6) )
# --- CARGA DE DATOS ---
def cargar_datos():
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df_usuarios_vacio = pd.DataFrame(columns=["Nombre", "ID", "C1", "C2", "C3", "C4", "C5", "C6", "Puntos", "Credito", "Password"])
    df_resultados_vacio = pd.DataFrame(columns=["Carrera", "1ro", "2do", "3ro", "Retirados"])
    try:
        df_u = pd.read_csv(f"{base_url}&sheet=Usuarios")
        df_u.columns = df_u.columns.str.strip()
        df_r = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Resultados")
        df_r.columns = df_r.columns.str.strip()
        return df_u, df_r
    except:
        return df_usuarios_vacio, df_resultados_vacio

def cargar_subastas():
    df_subasta_vacio = pd.DataFrame(columns=["carrera", "ejemplar", "nombre_caballo", "imagen_stud", "precio", "postor"])
    try:
        res = requests.post(WEB_APP_URL, json={"tipo": "subastas"})
        df_subasta = pd.DataFrame(res.json())
        if not df_subasta.empty:
            df_subasta.columns = df_subasta.columns.str.strip()
            df_subasta["carrera"] = pd.to_numeric(df_subasta["carrera"], errors='coerce').fillna(0).astype(int)
            df_subasta["ejemplar"] = pd.to_numeric(df_subasta["ejemplar"], errors='coerce').fillna(0).astype(int)
            df_subasta["precio"] = pd.to_numeric(df_subasta["precio"], errors='coerce').fillna(0.0).astype(float)
            return df_subasta
        return df_subasta_vacio
    except:
        return df_subasta_vacio

df, df_res = cargar_datos()

# ==============================================================================
# PANTALLA DE LOGIN
# ==============================================================================
if not st.session_state.autenticado:
    # CORREGIDO: Se cambió 'unsafe_html' por 'unsafe_allow_html' para erradicar el TypeError
    st.markdown("<h1 style='text-align: center;'>🏇 Polla Hípica Pro - Login</h1>", unsafe_allow_html=True)
    
    col_login, _ = st.columns([2, 2])
    with col_login:
        with st.form("form_login"):
            usuario_input = st.text_input("Usuario / Nombre").strip()
            password_input = st.text_input("Contraseña / PIN", type="password").strip()
            bto_login = st.form_submit_button("Ingresar al Sistema")
            
            if bto_login:
                # 1. Validar Administrador maestro
                if usuario_input.lower() == "admin" and password_input == "2026":
                    st.session_state.autenticado = True
                    st.session_state.usuario_actual = "Admin"
                    st.session_state.es_admin = True
                    st.success("¡Bienvenido Administrador!")
                    time.sleep(1)
                    st.rerun()
                
                # 2. Validar Jugador desde el Excel
                elif not df.empty and "Nombre" in df.columns:
                    usuario_filtrado = df[df["Nombre"].astype(str).str.lower() == usuario_input.lower()]
                    
                    if not usuario_filtrado.empty:
                        pass_real = str(usuario_filtrado.iloc[-1]["Password"]).strip()
                        
                        if password_input == pass_real:
                            st.session_state.autenticado = True
                            st.session_state.usuario_actual = usuario_filtrado.iloc[-1]["Nombre"]
                            st.session_state.es_admin = False
                            st.success(f"¡Hola, {st.session_state.usuario_actual}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Contraseña o PIN incorrecto.")
                    else:
                        st.error("❌ El usuario no está registrado.")
                else:
                    st.error("❌ No se pudo conectar a la base de datos de usuarios.")
    st.stop() 

# ==============================================================================
# INTERFAZ PRINCIPAL (POST-LOGIN)
# ==============================================================================
st.sidebar.markdown(f"👤 Usuario: **{st.session_state.usuario_actual}**")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.session_state.usuario_actual = None
    st.session_state.es_admin = False
    st.rerun()

# --- VISTA DEL ADMINISTRADOR ---
if st.session_state.es_admin:
    st.title("🔐 Panel de Control - Administrador")
    tab_ranking, tab_admin_usuarios, tab_admin_jornada = st.tabs(["📊 Ver Ranking", "👥 Control de Usuarios", "⚙️ Manejo de Jornada"])
    
    with tab_ranking:
        st.subheader("🏆 Posiciones en Vivo")
        if not df.empty:
            st.dataframe(df[["Nombre", "Puntos", "Credito"]], use_container_width=True)

    with tab_admin_usuarios:
        st.subheader("👥 Base de Datos de Jugadores")
        st.write("Datos actuales registrados en tu Google Sheets:")
        st.dataframe(df[["Nombre", "Credito", "Password", "Puntos"]], use_container_width=True, hide_index=True)

    with tab_admin_jornada: # o tab4 según tengas tu código
        st.subheader("⚙️ Cierre de Carreras y Resultados")
        st.info("💡 Si hay un empate en alguna posición, coloca los números separados por comas (Ej: 4, 7)")
        
        with st.form("form_admin_res"):
            resultados_data = []
            for i in range(1, 7):
                st.markdown(f"#### 🏁 Carrera {i}")
                c1, c2, c3, c4 = st.columns(4)
                
                # Cambiamos a text_input para permitir empates (Ej: "5" o "5, 12")
                p1 = c1.text_input("1º Lugar (Ganador)", value="0", key=f"p1_{i}", placeholder="Ej: 4 o 4,7")
                p2 = c2.text_input("2º Lugar", value="0", key=f"p2_{i}", placeholder="Ej: 2")
                p3 = c3.text_input("3º Lugar", value="0", key=f"p3_{i}", placeholder="Ej: 9")
                ret = c4.text_input("Retirados", key=f"ret_{i}", placeholder="Ej: 5, 12")
                
                resultados_data.append({"p1": p1, "p2": p2, "p3": p3, "ret": ret})
            
            if st.form_submit_button("Guardar Resultados y Computar Puntos"):
                # --- VALIDACIÓN DE ERRORES SILLY (Distracciones) ---
                error_detectado = False
                for idx, r in enumerate(resultados_data):
                    # Si el admin dejó campos idénticos por error (y no es "0")
                    if r["p1"] == r["p2"] == r["p3"] and r["p1"] != "0":
                        st.error(f"❌ Error en Carrera {idx+1}: Pusiste el mismo ejemplar en las tres posiciones.")
                        error_detectado = True
                        break
                
                if not error_detectado:
                    requests.post(WEB_APP_URL, json={"tipo": "resultados", "ganadores": resultados_data})
                    st.success("¡Resultados subidos y puntos recalculados!")
                    time.sleep(1)
                    st.rerun()

# --- VISTA DE JUGADOR NORMAL ---
else:
    st.title(f"🏇 Panel de {st.session_state.usuario_actual}")
    
    user_info = df[df["Nombre"] == st.session_state.usuario_actual].iloc[-1]
    credito_disp = user_info["Credito"]
    st.sidebar.metric(label="Mi Saldo Disponible", value=f"${credito_disp:.2f}")

    tab1, tab2, tab3 = st.tabs(["📝 Sellar mi Polla", "🔨 Subasta por Carreras", "📊 Ver Tabla General"])

    with tab1:
        if not taquilla_abierta:
            st.warning("🔒 La taquilla tradicional está cerrada.")
        else:
            st.markdown(f"### Sellar Jugada - Costo: **$10**")
            col1, col2 = st.columns(2)
            jugadas = []
            for i in range(1, 7):
                with col1 if i <= 3 else col2:
                    lista_ret = []
                    if not df_res.empty and i in df_res["Carrera"].astype(int).values:
                        fila_carrera = df_res[df_res["Carrera"].astype(int) == i]
                        if not fila_carrera.empty:
                            ret_str = str(fila_carrera["Retirados"].values[0]).replace('nan', '')
                            if ret_str.strip():
                                lista_ret = [int(x.strip()) for x in ret_str.replace('.', ',').split(",") if x.strip().isdigit()]
                    
                    opciones = [n for n in range(1, 21) if n not in lista_ret]
                    val = st.selectbox(f"Carrera {i}", opciones, index=None, placeholder="Ejemplar", key=f"c{i}")
                    jugadas.append(val)

            if st.button("🚀 SELLAR MI JUGADA"):
                if None in jugadas:
                    st.warning("Debes seleccionar un ejemplar para las 6 carreras.")
                elif credito_disp < 10:
                    st.error("Saldo insuficiente para sellar.")
                else:
                    payload = {"tipo": "sellar", "nombre": st.session_state.usuario_actual, "nuevo_credito": int(credito_disp - 10), "jugadas": jugadas, "password": str(user_info["Password"])}
                    res = requests.post(WEB_APP_URL, json=payload)
                    if "Éxito" in res.text:
                        st.success("¡Polla sellada exitosamente!")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()

    with tab2:
        st.subheader("🔨 Subasta en Vivo")
        df_sub = cargar_subastas()
        
        if df_sub.empty:
            st.info("No hay subastas activas en este momento.")
        else:
            carrera_sel = st.radio("Selecciona Carrera:", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], horizontal=True)
            df_carrera = df_sub[df_sub["carrera"] == carrera_sel]
            
            for index, row in df_carrera.iterrows():
                ejemplar = int(row["ejemplar"])
                nombre_caballo = str(row["nombre_caballo"]) if pd.notna(row["nombre_caballo"]) else ""
                img_url = str(row["imagen_stud"]) if pd.notna(row["imagen_stud"]) else ""
                precio_act = float(row["precio"])
                postor_act = str(row["postor"])
                
                texto_caballo = f"#{ejemplar} - {nombre_caballo}" if nombre_caballo.strip() else f"Ejemplar #{ejemplar}"
                
                with st.container():
                    col_img, col_info, col_puja = st.columns([1, 3, 2])
                    with col_img:
                        if img_url.strip() and img_url.startswith("http"):
                            st.image(img_url, width=60)
                        else:
                            st.caption("🏇")
                    with col_info:
                        st.markdown(f"##### **{texto_caballo}**")
                        st.markdown(f"💰 Precio: **${precio_act:.2f}** | 👑 Líder: *{postor_act}*")
                    with col_puja:
                        if not subasta_abierta:
                            st.error("🔒 Cerrada")
                        else:
                            nueva_puja = st.number_input(f"Pujar por {texto_caballo}", min_value=float(precio_act + 1.0), step=1.0, key=f"puja_{carrera_sel}_{ejemplar}")
                            if st.button(f"🔥 Ofertar", key=f"btn_{carrera_sel}_{ejemplar}"):
                                payload_puja = {
                                  "tipo": "pujar",
                                  "carrera": int(carrera_sel),
                                  "ejemplar": int(ejemplar),
                                  "nueva_puja": float(nueva_puja),
                                  "nombre": st.session_state.usuario_actual
                                }
                                res_puja = requests.post(WEB_APP_URL, json=payload_puja)
                                
                                # MEJORA DE RESPUESTA DE ERRORES DE CRÉDITO
                                if "Éxito" in res_puja.text:
                                    st.success(f"¡Vas ganando el ejemplar por ${nueva_puja}!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    # Si no hay crédito o pasa algo, muestra el error exacto que envía Google
                                    st.error(res_puja.text)
    with tab3:
        st.subheader("🏆 Tabla de Posiciones General")
        if not df.empty and df.shape[1] > 1:
            df_jugadas = df[df.iloc[:, 1].astype(str).str.contains("P-", na=False)].copy()
            if not df_jugadas.empty:
                df_jugadas = df_jugadas.sort_values(by=df_jugadas.columns[8], ascending=False).reset_index(drop=True)
                st.dataframe(df_jugadas[["Nombre", "Puntos", "C1", "C2", "C3", "C4", "C5", "C6"]], use_container_width=True)
