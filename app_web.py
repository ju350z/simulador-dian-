import streamlit as st
import sqlite3
import time

# Configuración para que se vea bien en celulares
st.set_page_config(page_title="Simulador DIAN", page_icon="🏛️", layout="centered")

DB_NAME = "banco_preguntas.db"

# Inicializar variables de sesión (Para que la app recuerde en qué pregunta vas)
if "examen_activo" not in st.session_state:
    st.session_state.examen_activo = False
if "preguntas" not in st.session_state:
    st.session_state.preguntas = []
if "indice" not in st.session_state:
    st.session_state.indice = 0
if "puntaje" not in st.session_state:
    st.session_state.puntaje = 0
if "historial" not in st.session_state:
    st.session_state.historial = []

st.title("🏛️ Simulador DIAN 2676 (Versión Móvil)")

# ----------------- PANTALLA PRINCIPAL -----------------
if not st.session_state.examen_activo and len(st.session_state.preguntas) == 0:
    st.write("Conectado exitosamente a tu base de datos local del PC.")
    
    cant = st.number_input("¿Cuántas preguntas deseas en este simulacro?", min_value=1, max_value=160, value=20)
    
    if st.button("▶️ INICIAR SIMULACRO", type="primary", use_container_width=True):
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT * FROM preguntas_pjs ORDER BY RANDOM() LIMIT ?", (cant,))
            st.session_state.preguntas = c.fetchall()
            conn.close()
            
            if not st.session_state.preguntas:
                st.error("Tu banco de preguntas está vacío. Usa la Fábrica en tu PC (.exe) primero.")
            else:
                st.session_state.examen_activo = True
                st.session_state.indice = 0
                st.session_state.puntaje = 0
                st.session_state.historial = []
                st.session_state.tiempo_inicio = time.time()
                st.rerun()
        except Exception as e:
            st.error("Error al conectar con la base de datos.")

# ----------------- PANTALLA DE PREGUNTAS -----------------
elif st.session_state.examen_activo:
    idx = st.session_state.indice
    total = len(st.session_state.preguntas)
    
    if idx < total:
        preg = st.session_state.preguntas[idx]
        _, caso, enunciado, opt_a, opt_b, opt_c, correcta, just = preg
        
        st.progress((idx) / total, text=f"Progreso del examen ({idx + 1}/{total})")
        
        with st.container(border=True):
            st.markdown(f"**📖 CASO:**\n{caso}")
            st.markdown(f"**🎯 ENUNCIADO:**\n{enunciado}")
        
        st.write("Selecciona tu respuesta:")
        resp = st.radio("Opciones", 
                        options=["--", "A", "B", "C"], 
                        label_visibility="collapsed",
                        format_func=lambda x: "Toca aquí para elegir..." if x == "--" else f"{x}. {opt_a if x=='A' else opt_b if x=='B' else opt_c}")
        
        st.write("") # Espaciador
        
        if st.button("Confirmar y Avanzar ➡️", type="primary", use_container_width=True):
            if resp == "--":
                st.warning("⚠️ Debes seleccionar una opción (A, B o C) antes de avanzar.")
            else:
                acierto = (resp == correcta)
                if acierto: st.session_state.puntaje += 1
                
                st.session_state.historial.append({
                    "num": idx + 1, "tu_resp": resp, "correcta": correcta, 
                    "acierto": acierto, "justificacion": just
                })
                st.session_state.indice += 1
                st.rerun()
                
    # ----------------- PANTALLA DE RESULTADOS -----------------
    else:
        st.session_state.examen_activo = False
        tiempo_total = int(time.time() - st.session_state.tiempo_inicio)
        mins, segs = divmod(tiempo_total, 60)
        porcentaje = (st.session_state.puntaje / total) * 100
        
        st.success("🎉 ¡SIMULACRO FINALIZADO!")
        col1, col2 = st.columns(2)
        col1.metric(label="Aciertos", value=f"{st.session_state.puntaje} / {total}", delta=f"{porcentaje:.1f}%")
        col2.metric(label="Tiempo", value=f"{mins}m {segs}s")
        
        if porcentaje >= 70:
            st.info("✅ ESTADO: APROBADO (Superaste el 70.00 requerido para Gestor I)")
        else:
            st.error("❌ ESTADO: NO APROBADO (Mínimo eliminatorio requerido: 70.00)")
            
        st.divider()
        st.subheader("Revisión Oficial (Explicación de Errores)")
        
        for item in st.session_state.historial:
            icono = "✅" if item['acierto'] else "❌"
            with st.expander(f"Pregunta {item['num']} - {icono} Tu respuesta: {item['tu_resp']} (Correcta: {item['correcta']})"):
                st.markdown(f"**Justificación Técnica:**\n{item['justificacion']}")
                
        st.write("")
        if st.button("🔄 Volver al Menú Principal", use_container_width=True):
            st.session_state.preguntas = []
            st.rerun()