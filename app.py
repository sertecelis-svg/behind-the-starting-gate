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

# --- CONTROL DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None
if "es_admin" not in st.session_state:
    st.session_state.es_admin = False

# --- CONTROL DE TIEMPO (VENEZUELA) ---
tz = pytz.timezone('America/Caracas')
ahora = datetime.now(tz)
dia_semana = ahora.weekday() 
hora_actual = ahora.hour

taquilla_abierta = not ( (dia_semana == 5 and hora_actual >= 18) or (dia_semana == 6) )
subasta_abierta = not ( (dia_semana == 5 and hora_actual >= 17) or (dia_semana == 6) )

# --- CARGA DE DATOS ---
def cargar_datos():
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df_usuarios_vacio = pd.DataFrame(columns=["Nombre", "ID_Polla", "C1", "C2", "C3", "C4", "C5", "C6", "Puntos", "Credito", "Password"])
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
# PANTALLA DE ACCESO (LOGIN O REGISTRO)
# ==============================================================================
if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>🏇 Polla Hípica Pro</h1>", unsafe_allow_html=True)
    
    col_login, _ = st.columns([2, 2])
    with col_login:
        tab_log, tab_reg = st.tabs(["🔑 Iniciar Sesión", "📝 Crear Cuenta Nueva"])
        
        # SUB-PESTAÑA: LOGIN
        with tab_log:
            with st.form("form_login"):
                usuario_input = st.text_input("Usuario / Nombre").strip()
                password_input = st.text_input("Contraseña / PIN", type="password").strip()
                bto_login = st.form_submit_button("Ingresar al Sistema")
                
                if bto_login:
                    if usuario_input.lower() == "admin" and password_input == "2026":
                        st.session_state.autenticado = True
                        st.session_state.usuario_actual = "Admin"
                        st.session_state.es_admin = True
                        st.success("¡Bienvenido Administrador!")
                        time.sleep(1)
                        st.rerun()
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
                                st.error("❌ Contraseña incorrecta.")
                        else:
                            st.error("❌ El usuario no está registrado.")
                    else:
                        st.error("❌ Error de comunicación con la base de datos.")
                        
        # SUB-PESTAÑA: REGISTRO AUTÓNOMO
        with tab_reg:
            with st.form("form_registro"):
                reg_usuario = st.text_input("Elige tu Nombre de Usuario (Ej: Pedro)").strip()
                reg_password = st.text_input("Crea tu Contraseña / PIN", type="password").strip()
                bto_registrar = st.form_submit_button("Registrarme Ahora")
                
                if bto_registrar:
                    if len(reg_usuario) < 3 or len(reg_password) < 3:
                        st.warning("⚠️ Nombre y Contraseña deben tener al menos 3 caracteres.")
                    elif reg_usuario.lower() == "admin":
                        st.error("❌ No puedes usar el nombre 'admin'.")
                    else:
                        res_reg = requests.post(WEB_APP_URL, json={"tipo": "registrar", "nombre": reg_usuario, "password": reg_password})
                        if "Éxito" in res_reg.text:
                            st.success("🎉 ¡Cuenta creada con éxito! Ya puedes iniciar sesión en la pestaña izquierda. (Tu saldo inicial es $0)")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(res_reg.text)
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
    tab_ranking, tab_admin_usuarios, tab_edit_perfil, tab_admin_jornada = st.tabs(["📊 Ver Ranking", "👥 Ver Usuarios", "✏️ Editar Saldo/Claves", "⚙️ Manejo de Jornada"])
    
    with tab_ranking:
        st.subheader("🏆 Posiciones Consolidadas en Vivo")
        if df.empty:
            st.info("No hay datos disponibles.")
        else:
            # 1. Limpiar nombres para evitar duplicados por espacios invisibles
            df_rank = df.copy()
            df_rank["Nombre"] = df_rank["Nombre"].astype(str).str.strip()
            
            # 2. Asegurar que Puntos y Crédito sean números válidos
            df_rank["Puntos"] = pd.to_numeric(df_rank["Puntos"], errors='coerce').fillna(0).astype(int)
            df_rank["Credito"] = pd.to_numeric(df_rank["Credito"], errors='coerce').fillna(0.0)
            
            # 3. Agrupar de forma inteligente:
            # - Puntos: Se suman (si tiene 2 pollas de 10pts, tiene 20pts en total)
            # - Crédito: Se toma el ÚLTIMO valor (el saldo real vigente en su última fila)
            df_grouped_rank = df_rank.groupby("Nombre").agg({
                "Puntos": "sum",
                "Credito": "last"
            }).reset_index()
            
            # 4. Ordenar la tabla de mayor a menor puntaje
            df_grouped_rank = df_grouped_rank.sort_values(by="Puntos", ascending=False).reset_index(drop=True)
            
            st.dataframe(df_grouped_rank[["Nombre", "Puntos", "Credito"]], use_container_width=True)

    with tab_admin_usuarios:
        st.subheader("👥 Base de Datos Unificada de Jugadores")
        if df.empty:
            st.info("No hay usuarios registrados.")
        else:
            df_user_view = df.copy()
            df_user_view["Nombre"] = df_user_view["Nombre"].astype(str).str.strip()
            df_user_view["Puntos"] = pd.to_numeric(df_user_view["Puntos"], errors='coerce').fillna(0).astype(int)
            df_user_view["Credito"] = pd.to_numeric(df_user_view["Credito"], errors='coerce').fillna(0.0)
            df_user_view["Password"] = df_user_view["Password"].astype(str).str.strip()
            
            # Agrupar para mostrar una sola línea por persona con sus datos vigentes
            df_grouped_user = df_user_view.groupby("Nombre").agg({
                "Credito": "last",     # Su dinero real actual
                "Password": "last",    # Su contraseña vigente
                "Puntos": "sum"        # Total de puntos acumulados
            }).reset_index()
            
            st.dataframe(df_grouped_user[["Nombre", "Credito", "Password", "Puntos"]], use_container_width=True, hide_index=True)

    # NUEVA PESTAÑA: MODIFICACIÓN DE USUARIOS
    with tab_edit_perfil:
        st.subheader("✏️ Modificar Ficha de Jugador")
        if df.empty:
            st.info("No hay usuarios registrados en el sistema.")
        else:
            lista_nombres_unicos = sorted(df["Nombre"].unique().tolist())
            usuario_a_editar = st.selectbox("Selecciona el jugador que deseas modificar:", lista_nombres_unicos)
            
            # Obtener datos vigentes de su última fila
            info_actual = df[df["Nombre"] == usuario_a_editar].iloc[-1]
            
            with st.form("form_edit_user"):
                edit_nombre = st.text_input("Nombre de Usuario", value=str(info_actual["Nombre"]))
                edit_credito = st.number_input("Crédito Disponible ($)", value=float(info_actual["Credito"]), step=1.0)
                edit_password = st.text_input("Contraseña / PIN", value=str(info_actual["Password"]))
                
                if st.form_submit_button("Guardar Cambios Permanentes"):
                    payload_edit = {
                        "tipo": "editar_usuario",
                        "nombre_original": usuario_a_editar,
                        "nuevo_nombre": edit_nombre,
                        "nuevo_credito": edit_credito,
                        "nueva_clave": edit_password
                    }
                    res_edit = requests.post(WEB_APP_URL, json=payload_edit)
                    if "Éxito" in res_edit.text:
                        st.success(f"¡Usuario '{usuario_a_editar}' actualizado perfectamente!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(res_edit.text)

    with tab_admin_jornada:
        st.subheader("⚙️ Cierre de Carreras y Resultados")
        st.info("💡 Si hay un empate en alguna posición, coloca los números separados por comas (Ej: 4, 7)")
        
        with st.form("form_admin_res"):
            resultados_data = []
            
            # Recorremos las 6 carreras
            for i in range(1, 7):
                st.markdown(f"#### 🏁 Carrera {i}")
                c1, c2, c3, c4 = st.columns(4)
                
                # --- LÓGICA DE PRE-CARGA DE DATOS ---
                # Valores por defecto por si la hoja está vacía
                val_p1 = "0"
                val_p2 = "0"
                val_p3 = "0"
                val_ret = ""
                
                # Si ya existen resultados guardados en el Excel para esta carrera, los extraemos
                if not df_res.empty and i in df_res["Carrera"].astype(int).values:
                    fila_carrera = df_res[df_res["Carrera"].astype(int) == i].iloc[0]
                    val_p1 = str(fila_carrera["1ro"]).replace('nan', '0').strip()
                    val_p2 = str(fila_carrera["2do"]).replace('nan', '0').strip()
                    val_p3 = str(fila_carrera["3ro"]).replace('nan', '0').strip()
                    val_ret = str(fila_carrera["Retirados"]).replace('nan', '').strip()
                
                # Dibujamos las casillas con sus valores ya guardados en el Excel
                p1 = c1.text_input("1º Lugar (Ganador)", value=val_p1, key=f"p1_{i}")
                p2 = c2.text_input("2º Lugar", value=val_p2, key=f"p2_{i}")
                p3 = c3.text_input("3º Lugar", value=val_p3, key=f"p3_{i}")
                ret = c4.text_input("Retirados", value=val_ret, key=f"ret_{i}", placeholder="Ej: 5, 12")
                
                resultados_data.append({"p1": p1, "p2": p2, "p3": p3, "ret": ret})
            
            # --- BOTÓN DE GUARDAR CON VALIDACIONES ---
            if st.form_submit_button("Guardar Resultados y Computar Puntos"):
                error_detectado = False
                
                for idx, r in enumerate(resultados_data):
                    p1_limpio = r["p1"].strip()
                    p2_limpio = r["p2"].strip()
                    p3_limpio = r["p3"].strip()
                    
                    lista_retirados = [x.strip() for x in r["ret"].replace('.', ',').split(",") if x.strip()]
                    
                    lista_p1 = [x.strip() for x in p1_limpio.split(",") if x.strip()]
                    lista_p2 = [x.strip() for x in p2_limpio.split(",") if x.strip()]
                    lista_p3 = [x.strip() for x in p3_limpio.split(",") if x.strip()]
                    
                    todos_los_ingresados = lista_p1 + lista_p2 + lista_p3
                    caballos_en_podio = [c for c in todos_los_ingresados if c != "0"]
                    
                    # REGLA A: Verificar duplicados en el podio
                    if len(caballos_en_podio) != len(set(caballos_en_podio)):
                        st.error(f"❌ Error en Carrera {idx+1}: Hay ejemplares repetidos en las posiciones del podio.")
                        error_detectado = True
                        break
                    
                    # REGLA B: Verificar si algún caballo del podio está retirado
                    caballos_retirados_en_podio = [c for c in caballos_en_podio if c in lista_retirados]
                    if caballos_retirados_en_podio:
                        st.error(f"❌ Error en Carrera {idx+1}: El ejemplar #{caballos_retirados_en_podio[0]} está en la lista de RETIRADOS y no puede estar en el podio.")
                        error_detectado = True
                        break
                
                if not error_detectado:
                    with st.spinner("Computando puntos y guardando..."):
                        res_admin = requests.post(WEB_APP_URL, json={"tipo": "resultados", "ganadores": resultados_data})
                        if "Éxito" in res_admin.text:
                            st.success("🏆 ¡Resultados subidos y puntos recalculados exitosamente!")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error(f"Error en el servidor: {res_admin.text}")

# --- VISTA DE JUGADOR NORMAL ---
else:
    st.title(f"🏇 Panel de {st.session_state.usuario_actual}")
    user_info = df[df["Nombre"] == st.session_state.usuario_actual].iloc[-1]
    credito_disp = user_info["Credito"]
    st.sidebar.metric(label="Mi Saldo Disponible", value=f"${credito_disp:.2f}")

    # ==============================================================================
    # 🚨 SISTEMA DE ALERTAS EN TIEMPO REAL (REEMPLAZO DE PUJAS)
    # ==============================================================================
    df_sub = cargar_subastas()
    
    if not df_sub.empty:
        # Buscamos en el historial del Excel si este usuario ALGUNA VEZ ha tenido una jugada de subasta
        # o si estuvo involucrado en pujas anteriores para avisarle si lo destronaron
        # Para hacerlo simple y exacto: si el usuario NO es el líder actual pero el backend detecta
        # que su saldo fue reembolsado, o simplemente escaneamos si algún caballo que él quiere fue superado.
        
        # Una forma interactiva y brillante es chequear en la base de datos de subastas:
        # Si el usuario NO es líder de una carrera pero en tu lógica local quieres saber si fue superado,
        # podemos ver si en sesiones previas él lideraba. Para no complicar el almacenamiento,
        # hacemos un rastreo rápido: si hay caballos donde el postor anterior era él (eso lo maneja el script al devolver),
        # aquí le mostraremos un resumen de advertencia si tiene rivales activos en la carrera actual.
        pass

    # ==============================================================================
    # CONFIGURACIÓN DE LAS PESTAÑAS DEL JUGADOR (AÑADIDA PESTAÑA 4)
    # ==============================================================================
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Sellar mi Polla", 
        "🔨 Subasta por Carreras", 
        "📊 Ver Tabla General",
        "💰 Mis Deudas (Subasta)"
    ])

    # --- PESTAÑA 1: SELLAR POLLA ---
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
                    payload = {"tipo": "sellar", "nombre": st.session_state.usuario_actual, "nuevo_credito": float(credito_disp - 10), "jugadas": jugadas, "password": str(user_info["Password"])}
                    res = requests.post(WEB_APP_URL, json=payload)
                    if "Éxito" in res.text:
                        st.success("¡Polla sellada exitosamente!")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()

    # --- PESTAÑA 2: SUBASTA EN VIVO CON ALERTA DE REEMPLAZO ---
    # --- PESTAÑA 2: SUBASTA EN VIVO CON ALERTA DE REEMPLAZO ---
    with tab2:
        st.subheader("🔨 Subasta en Vivo")
        if df_sub.empty:
            st.info("No hay subastas activas en este momento.")
        else:
            # ==============================================================================
            # 🚨 DETECTOR DE ALERTAS: Caballos donde tú NO eres el líder
            # ==============================================================================
            # Buscamos caballos que ya tienen dueño (precio > 0) pero el líder es OTRO jugador
            caballos_con_otro_lider = df_sub[(df_sub["postor"].str.lower() != st.session_state.usuario_actual.lower()) & 
                                             (df_sub["precio"] > 0)]
            
            # Si hay caballos activos de otros, le mostramos una alerta para que esté pilas de lo que pasa en la jornada
            if not caballos_con_otro_lider.empty:
                # Tomamos los últimos 3 caballos que se han movido para no saturar la pantalla
                ultimos_movidos = caballos_con_otro_lider.tail(3)
                alertas_texto = ""
                for idx, r_alerta in ultimos_movidos.iterrows():
                    alertas_texto += f"• **Carrera {r_alerta['carrera']}**: El ejemplar *{r_alerta['nombre_caballo']}* lo va ganando **{r_alerta['postor']}** por **${r_alerta['precio']:.2f}**.<br>"
                
                # Desplegamos el banner de advertencia en amarillo
                st.warning("⚠️ **¡ALERTA DE SUBASTA!** Hay usuarios superando ofertas en la jornada:")
                st.markdown(f"<div style='background-color:#fff3cd; color:#856404; padding:10px; border-radius:5px; margin-bottom:15px;'>{alertas_texto}</div>", unsafe_allow_html=True)
            
            # --- SELECCIÓN DE CARRERAS ---
            carrera_sel = st.radio("Selecciona Carrera:", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], horizontal=True)
            df_carrera = df_sub[df_sub["carrera"] == carrera_sel]
            
            for index, row in df_carrera.iterrows():
                ejemplar = int(row["ejemplar"])
                nombre_caballo = str(row["nombre_caballo"]) if pd.notna(row["nombre_caballo"]) else ""
                img_url = str(row["imagen_stud"]) if pd.notna(row["imagen_stud"]) else ""
                precio_act = float(row["precio"])
                postor_act = str(row["postor"])
                texto_caballo = f"#{ejemplar} - {nombre_caballo}" if nombre_caballo.strip() else f"Ejemplar #{ejemplar}"
                
                es_mi_puja = postor_act.lower() == st.session_state.usuario_actual.lower()
                
                with st.container():
                    col_img, col_info, col_puja = st.columns([1, 3, 2])
                    with col_img:
                        if img_url.strip() and img_url.startswith("http"):
                            st.image(img_url, width=60)
                        else:
                            st.caption("🏇")
                    with col_info:
                        if es_mi_puja:
                            st.markdown(f"##### **{texto_caballo}** 👑 <span style='color:#28a745;'>(¡Vas ganando este ejemplar!)</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"##### **{texto_caballo}**")
                        st.markdown(f"💰 Precio Actual: **${precio_act:.2f}** | 👤 Líder: *{postor_act}*")
                    with col_puja:
                        if not subasta_abierta:
                            st.error("🔒 Cerrada")
                        else:
                            nueva_puja = st.number_input(f"Pujar por {texto_caballo}", min_value=float(precio_act + 1.0), step=1.0, key=f"puja_{carrera_sel}_{ejemplar}")
                            if st.button(f"🔥 Ofertar", key=f"btn_{carrera_sel}_{ejemplar}"):
                                payload_puja = {"tipo": "pujar", "carrera": int(carrera_sel), "ejemplar": int(ejemplar), "nueva_puja": float(nueva_puja), "nombre": st.session_state.usuario_actual}
                                res_puja = requests.post(WEB_APP_URL, json=payload_puja)
                                if "Éxito" in res_puja.text:
                                    st.success(f"¡Felicidades! Vas ganando por ${nueva_puja}")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(res_puja.text)

    # --- PESTAÑA 3: TABLA GENERAL ---
    with tab3:
        st.subheader("🏆 Tabla de Posiciones General")
        if not df.empty and df.shape[1] > 1:
            df_jugadas = df[df.iloc[:, 1].astype(str).str.contains("P-", na=False)].copy()
            if not df_jugadas.empty:
                df_jugadas = df_jugadas.sort_values(by=df_jugadas.columns[8], ascending=False).reset_index(drop=True)
                st.dataframe(df_jugadas[["Nombre", "Puntos", "C1", "C2", "C3", "C4", "C5", "C6"]], use_container_width=True)

    # ==============================================================================
    # --- 🗂️ NUEVA PESTAÑA 4: CUENTA DE DEUDAS Y ADVERTENCIA DE REEMPLAZO ---
    # ==============================================================================
    with tab4:
        st.subheader("💰 Resumen de mis Adquisiciones en la Subasta")
        
        if df_sub.empty:
            st.info("No hay información de subastas.")
        else:
            # Filtrar los ejemplares donde el usuario logueado va ganando actualmente
            mis_deudas = df_sub[df_sub["postor"].str.lower() == st.session_state.usuario_actual.lower()].copy()
            
            if mis_deudas.empty:
                st.info("No tienes deudas activas. No vas ganando ningún ejemplar en la subasta en este momento.")
            else:
                # Modificar columnas para que se entienda clarito
                mis_deudas.columns = ["Carrera", "Ejemplar #", "Nombre del Caballo", "Stud Link", "Mi Puja ($)", "Líder"]
                
                # Mostrar los caballos adjudicados momentáneamente
                st.dataframe(mis_deudas[["Carrera", "Ejemplar #", "Nombre del Caballo", "Mi Puja ($)"]], use_container_width=True, hide_index=True)
                
                # Calcular y mostrar el gran total comprometido
                total_deuda = mis_deudas["Mi Puja ($)"].sum()
                st.markdown(f"### 📊 Total Comprometido en Subasta: <span style='color:#ff4b4b'>${total_deuda:.2f}</span>", unsafe_allow_html=True)
                st.caption("⚠️ Nota: Esta cantidad ya fue descontada de tu Saldo Disponible en la barra lateral izquierda.")
