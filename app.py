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

# --- CONTROL DE TIEMPO (VENEZUELA) ---
tz = pytz.timezone('America/Caracas')
ahora = datetime.now(tz)
dia_semana = ahora.weekday() 
hora_actual = ahora.hour
taquilla_abierta = not ( (dia_semana == 5 and hora_actual >= 18) or (dia_semana == 6) )

# --- CARGA DE DATOS ---
def cargar_datos():
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    # Inicializamos vacíos para evitar el UnboundLocalError
    df_u = pd.DataFrame()
    df_r = pd.DataFrame(columns=["Carrera", "1ro", "2do", "3ro", "Retirados"])
    
    try:
        # Cargar Usuarios
        df_u = pd.read_csv(f"{base_url}&gid=0")
        df_u.columns = df_u.columns.str.strip()
        
        # Cargar Resultados
        url_res = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Resultados"
        df_r = pd.read_csv(url_res)
        df_r.columns = df_r.columns.str.strip()
    except Exception as e:
        # Si falla la carga, mostramos el error pero no detenemos la app
        st.sidebar.error(f"Error de conexión: {e}")
        
    return df_u, df_r

df, df_res = cargar_datos()

st.title("🏇 Sistema de Polla Hípica Pro")

# --- ESTADO DE TAQUILLA ---
if taquilla_abierta:
    st.success(f"🟢 TAQUILLA ABIERTA - {ahora.strftime('%I:%M %p')}")
else:
    st.error(f"🔴 TAQUILLA CERRADA")

tab1, tab2, tab3 = st.tabs(["📝 Sellar Jugada", "📊 Ranking", "🔐 Admin"])

with tab1:
    if not taquilla_abierta:
        st.warning("Taquilla cerrada hasta el lunes.")
    else:
        nombre_sel = st.selectbox("Selecciona tu nombre", df["Nombre"].unique() if not df.empty else [])
        if nombre_sel:
            # Buscar datos del usuario (última fila para saldo actualizado)
            user_data = df[df["Nombre"] == nombre_sel].iloc[-1]
            credito_disp = user_data["Credito"]
            pass_real = str(user_data["Password"])
            
            st.markdown(f"### 💰 Saldo: **${credito_disp}** | 🎟️ Costo: **$10**")
            pin = st.text_input("Ingresa tu PIN", type="password", key="pin_sellar")
            
            col1, col2 = st.columns(2)
            jugadas = []
            for i in range(1, 7):
                with col1 if i <= 3 else col2:
                    # Filtrar retirados
                    lista_ret = []
                    if not df_res.empty and i in df_res["Carrera"].values:
                       fila_carrera = df_res[df_res["Carrera"].astype(int) == i]
                       if not fila_carrera.empty:
                           # Limpiamos el texto de retirados y lo convertimos en lista de enteros
                        ret_str = str(fila_carrera["Retirados"].values[0]).replace('nan', '')
                        if ret_str.strip():
                            # Esto maneja espacios, comas y puntos
                         lista_ret = [int(x.strip()) for x in ret_str.replace('.', ',').split(",") if x.strip().isdigit()]
                    
                    # Solo mostramos los números que NO están en la lista de retirados
                    opciones = [n for n in range(1, 21) if n not in lista_ret]
                    val = st.selectbox(f"Carrera {i}", opciones, index=None, placeholder="Ejemplar", key=f"c{i}")
                    jugadas.append(val)

            if st.button("🚀 SELLAR POLLA"):
                if pin != pass_real:
                    st.error("PIN incorrecto")
                elif None in jugadas:
                    st.warning("Completa las 6 carreras")
                elif credito_disp < 10:
                    st.error("Saldo insuficiente")
                else:
                    payload = {"tipo": "sellar", "nombre": nombre_sel, "nuevo_credito": int(credito_disp - 10), "jugadas": jugadas, "password": pass_real}
                    res = requests.post(WEB_APP_URL, json=payload)
                    if "Éxito" in res.text:
                        st.success("¡Sella con éxito!")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()

with tab2:
    st.subheader("🏆 Tabla de Posiciones")
    # Filtro robusto para evitar AttributeError
    df_jugadas = df[df.iloc[:, 1].astype(str).str.contains("P-", na=False)].copy()
    
    if df_jugadas.empty:
        st.info("No hay jugadas registradas.")
    else:
        df_jugadas = df_jugadas.sort_values(by=df_jugadas.columns[8], ascending=False).reset_index(drop=True)
        
        def medalla(i):
            if i == 0: return "🥇 Oro"
            if i == 1: return "🥈 Plata"
            if i == 2: return "🥉 Bronce"
            return f"{i+1}º"
        
        df_jugadas.insert(0, "Lugar", [medalla(i) for i in range(len(df_jugadas))])
        st.dataframe(df_jugadas[["Lugar", "Nombre", "Puntos", "C1", "C2", "C3", "C4", "C5", "C6"]], use_container_width=True, hide_index=True)

with tab3:
    if st.text_input("Clave Maestra", type="password") == "2026":
        with st.form("form_admin"):
            resultados_data = []
            for i in range(1, 7):
                st.write(f"Carrera {i}")
                c1, c2, c3, c4 = st.columns(4)
                p1 = c1.number_input("1º", 0, 20, key=f"p1_{i}")
                p2 = c2.number_input("2º", 0, 20, key=f"p2_{i}")
                p3 = c3.number_input("3º", 0, 20, key=f"p3_{i}")
                ret = c4.text_input("Retirados", key=f"ret_{i}", placeholder="Ej: 5, 12")
                resultados_data.append({"p1": p1, "p2": p2, "p3": p3, "ret": ret})
            
            if st.form_submit_button("Guardar Resultados y Retirados"):
                requests.post(WEB_APP_URL, json={"tipo": "resultados", "ganadores": resultados_data})
                st.success("Hoja de Resultados actualizada.")
                time.sleep(1)
                st.rerun()