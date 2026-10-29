import streamlit as st
import sqlite3
import time

st.set_page_config(page_title="Simulador DIAN 2676", page_icon="🏛️", layout="centered")
DB_NAME = "banco_preguntas.db"

for key, val in [
    ("examen_activo", False),
    ("cola", []),
    ("indice", 0),
    ("historial", []),
    ("modo", "LIKERT"),
]:
    if key not in st.session_state:
        st.session_state[key] = val

def obtener_totales():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS preguntas_pjs (id INTEGER PRIMARY KEY)")
    c.execute("CREATE TABLE IF NOT EXISTS preguntas_likert (id INTEGER PRIMARY KEY)")
    c.execute("SELECT COUNT(*) FROM preguntas_pjs")
    t_pjs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM preguntas_likert")
    t_lik = c.fetchone()[0]
    conn.close()
    return t_pjs, t_lik

st.title("🏛️ Simulador DIAN 2676 (PJS + Likert)")

# ----------------- PANTALLA PRINCIPAL -----------------
if not st.session_state.examen_activo and len(st.session_state.cola) == 0:
    t_pjs, t_lik = obtener_totales()
    col_a, col_b = st.columns(2)
    col_a.metric("📘 Banco Funcional (PJS)", t_pjs)
    col_b.metric("⚖️ Banco Likert (Comportamental/Ética)", t_lik)

    modo_sel = st.radio(
        "Selecciona el Modo de Entrenamiento:",
        options=["LIKERT", "PJS", "INTEGRAL"],
        format_func=lambda x: (
            "⚖️ Comportamentales e Integridad (Escala Likert A, B, C, D)" if x == "LIKERT"
            else "📘 Competencias Funcionales (Juicio Situacional A, B, C)" if x == "PJS"
            else "🏛️ Simulacro Integral Ponderado (Funcional 70% + Likert 30%)"
        )
    )

    cant = st.number_input("¿Cuántas preguntas deseas resolver?", min_value=1, max_value=160, value=20)

    if st.button("▶️ INICIAR SIMULACRO", type="primary", use_container_width=True):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        cola = []
        if modo_sel in ["PJS", "INTEGRAL"]:
            n_p = cant if modo_sel == "PJS" else max(1, cant // 2)
            c.execute("SELECT * FROM preguntas_pjs ORDER BY RANDOM() LIMIT ?", (n_p,))
            for r in c.fetchall():
                cola.append({"formato": "PJS", "datos": r})
        if modo_sel in ["LIKERT", "INTEGRAL"]:
            n_l = cant if modo_sel == "LIKERT" else (cant - len(cola))
            c.execute("SELECT * FROM preguntas_likert ORDER BY RANDOM() LIMIT ?", (n_l,))
            for r in c.fetchall():
                cola.append({"formato": "LIKERT", "datos": r})
        conn.close()

        if not cola:
            st.error("No hay preguntas disponibles en este modo. Fabrícalas primero en tu PC y actualiza 'banco_preguntas.db'.")
        else:
            st.session_state.cola = cola
            st.session_state.modo = modo_sel
            st.session_state.examen_activo = True
            st.session_state.indice = 0
            st.session_state.historial = []
            st.session_state.tiempo_inicio = time.time()
            st.rerun()

# ----------------- PANTALLA DE PREGUNTAS -----------------
elif st.session_state.examen_activo:
    idx = st.session_state.indice
    total = len(st.session_state.cola)

    if idx < total:
        item = st.session_state.cola[idx]
        formato = item["formato"]
        datos = item["datos"]

        st.progress(idx / total, text=f"Pregunta {idx + 1} de {total}")

        if formato == "PJS":
            _, caso, enunciado, opt_a, opt_b, opt_c, correcta, just = datos
            st.caption("📘 PRUEBA DE COMPETENCIAS FUNCIONALES (PJS)")
            with st.container(border=True):
                st.markdown(f"**📖 CASO:**\n{caso}")
                st.markdown(f"**🎯 ENUNCIADO:**\n{enunciado}")
            mapa_opciones = {"A": opt_a, "B": opt_b, "C": opt_c}
            lista_letras = ["--", "A", "B", "C"]
        else:
            _, categoria, comp_val, tipo_item, afirmacion, optima, aceptable, just = datos
            st.caption(f"⚖️ PRUEBA {categoria} — Eje: {comp_val}")
            with st.container(border=True):
                st.markdown(f"**📝 AFIRMACIÓN:**\n\n> *\"{afirmacion}\"*")
            mapa_opciones = {
                "A": "Totalmente en desacuerdo.",
                "B": "En desacuerdo.",
                "C": "De acuerdo.",
                "D": "Totalmente de acuerdo."
            }
            lista_letras = ["--", "A", "B", "C", "D"]

        resp = st.radio(
            "Selecciona tu respuesta:",
            options=lista_letras,
            label_visibility="collapsed",
            format_func=lambda x: "Toca aquí para elegir una opción..." if x == "--" else f"{x}. {mapa_opciones[x]}"
        )

        if st.button("Confirmar y Avanzar ➡️", type="primary", use_container_width=True):
            if resp == "--":
                st.warning("⚠️ Selecciona una opción antes de continuar.")
            else:
                if formato == "PJS":
                    _, caso, enunciado, opt_a, opt_b, opt_c, correcta, just = datos
                    pts = 1.0 if resp == correcta else 0.0
                    st.session_state.historial.append({
                        "num": idx + 1,
                        "formato": "PJS",
                        "subtipo": "Funcional",
                        "caso": caso,
                        "enunciado": enunciado,
                        "opciones": {"A": opt_a, "B": opt_b, "C": opt_c},
                        "tu_resp": resp,
                        "optima": correcta,
                        "aceptable": correcta,
                        "puntos": pts,
                        "just": just
                    })
                else:
                    _, categoria, comp_val, tipo_item, afirmacion, optima, aceptable, just = datos
                    pts = 1.0 if resp == optima else (0.5 if resp == aceptable else 0.0)
                    st.session_state.historial.append({
                        "num": idx + 1,
                        "formato": "LIKERT",
                        "categoria": categoria,
                        "subtipo": f"{comp_val} ({tipo_item})",
                        "tipo_item": tipo_item,
                        "afirmacion": afirmacion,
                        "opciones": mapa_opciones,
                        "tu_resp": resp,
                        "optima": optima,
                        "aceptable": aceptable,
                        "puntos": pts,
                        "just": just
                    })
                st.session_state.indice += 1
                st.rerun()

    # ----------------- PANTALLA DE RESULTADOS -----------------
    else:
        st.session_state.examen_activo = False
        tiempo_total = int(time.time() - st.session_state.tiempo_inicio)
        mins, segs = divmod(tiempo_total, 60)

        items_pjs = [x for x in st.session_state.historial if x["formato"] == "PJS"]
        items_lik = [x for x in st.session_state.historial if x["formato"] == "LIKERT"]

        score_pjs = (sum(x["puntos"] for x in items_pjs) / len(items_pjs) * 100) if items_pjs else 0.0
        score_lik = (sum(x["puntos"] for x in items_lik) / len(items_lik) * 100) if items_lik else 0.0

        st.success(f"🎉 ¡Simulacro finalizado en {mins}m {segs}s!")

        if items_pjs:
            st.metric("📘 Puntaje Funcional (PJS)", f"{score_pjs:.2f} / 100.00")
        if items_lik:
            extremos = sum(1 for x in items_lik if x["tu_resp"] in ["A", "D"])
            medios = sum(1 for x in items_lik if x["tu_resp"] in ["B", "C"])
            ctrl_fallos = sum(1 for x in items_lik if ("CONTROL" in x["tipo_item"] or x["categoria"] == "CONTROL_DESEABILIDAD") and x["puntos"] == 0.0)

            st.metric("⚖️ Puntaje Psicométrico Likert", f"{score_lik:.2f} / 100.00")
            st.info(f"📊 **Tendencia de respuesta:** Extremos (A/D): **{extremos}** | Medios (B/C): **{medios}**")
            if ctrl_fallos > 0:
                st.warning(f"⚠️ **Subescala de Control:** Fallaste en {ctrl_fallos} ítem(s) de control de deseabilidad social (evita respuestas absolutistas irreales).")
            else:
                st.success("✅ **Subescala de Control:** Superada sin alertas de fingimiento.")

        if items_pjs and items_lik:
            ponderado = (score_pjs * 0.70) + (score_lik * 0.30)
            st.subheader(f"🏆 Puntaje Ponderado Total: {ponderado:.2f} / 100.00")

        st.divider()
        st.subheader("🔍 Revisión Completa: Preguntas, Opciones y Justificación")

        filtro = st.radio(
            "Mostrar en la revisión:",
            options=["TODAS", "ERRORES"],
            horizontal=True,
            format_func=lambda x: "📋 Todas las preguntas" if x == "TODAS" else "❌ Solo incorrectas / parciales"
        )

        for item in st.session_state.historial:
            if filtro == "ERRORES" and item["puntos"] == 1.0:
                continue

            icono = "✅" if item["puntos"] == 1.0 else ("⚠️" if item["puntos"] == 0.5 else "❌")
            titulo = f"Pregunta {item['num']} [{item['formato']}] — {icono} Tu resp: {item['tu_resp']} | Correcta: {item['optima']}"

            with st.expander(titulo, expanded=(item["puntos"] < 1.0)):
                if item["formato"] == "PJS":
                    st.markdown(f"**📖 CASO:**\n{item['caso']}")
                    st.markdown(f"**🎯 ENUNCIADO:**\n{item['enunciado']}")
                    st.markdown("**📋 OPCIONES DE RESPUESTA:**")

                    for letra, texto_opt in item["opciones"].items():
                        if letra == item["optima"] and letra == item["tu_resp"]:
                            st.success(f"**{letra}.** {texto_opt}  \n*(✅ Tu respuesta — Correcta)*")
                        elif letra == item["tu_resp"]:
                            st.error(f"**{letra}.** {texto_opt}  \n*(❌ Tu elección — Incorrecta)*")
                        elif letra == item["optima"]:
                            st.success(f"**{letra}.** {texto_opt}  \n*(✔️ Respuesta Correcta)*")
                        else:
                            st.markdown(f"**{letra}.** {texto_opt}")
                else:
                    st.markdown(f"**Eje evaluado:** `{item['subtipo']}`")
                    st.markdown(f"**📝 Afirmación:**\n> *\"{item['afirmacion']}\"*")
                    txt_tu = item["opciones"].get(item["tu_resp"], "")
                    txt_opt = item["opciones"].get(item["optima"], "")
                    txt_acep = item["opciones"].get(item["aceptable"], "")
                    st.markdown(f"- **Tu elección:** `{item['tu_resp']}` ({txt_tu})")
                    st.markdown(f"- **Clave Óptima (100%):** `{item['optima']}` ({txt_opt}) | **Aceptable (50%):** `{item['aceptable']}` ({txt_acep})")

                st.divider()
                st.markdown(f"**💡 Análisis y Justificación:**\n{item['just']}")

        if st.button("🔄 Volver al Menú Principal", use_container_width=True):
            st.session_state.cola = []
            st.rerun()