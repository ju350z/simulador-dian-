import os
import sys
import time
import json
import random
import sqlite3
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
import PyPDF2
from google import genai
from google.genai import types
from pydantic import BaseModel

# ==========================================
# 1. RUTAS FIJAS Y ESQUEMAS ESTRUCTURADOS
# ==========================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_NAME = os.path.join(BASE_DIR, "banco_preguntas.db")
CARPETA_PDFS_FUNC = os.path.join(BASE_DIR, "documentos_dian")
CARPETA_PDFS_COMP = os.path.join(BASE_DIR, "documentos_comportamentales")

class PreguntaPJS(BaseModel):
    caso: str
    enunciado: str
    opcion_a: str
    opcion_b: str
    opcion_c: str
    correcta: str
    justificacion: str

class LotePreguntasPJS(BaseModel):
    preguntas: list[PreguntaPJS]

class PreguntaLikert(BaseModel):
    categoria: str
    competencia_o_valor: str
    tipo_item: str
    afirmacion: str
    respuesta_optima: str
    respuesta_aceptable: str
    justificacion_psicometrica: str

class LotePreguntasLikert(BaseModel):
    preguntas: list[PreguntaLikert]

def inicializar_bd():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tablas Funcionales (Se conservan intactas)
    c.execute('''CREATE TABLE IF NOT EXISTS preguntas_pjs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, caso TEXT, enunciado TEXT,
        opcion_a TEXT, opcion_b TEXT, opcion_c TEXT, correcta TEXT, justificacion TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS fragmentos_pdf (
        id INTEGER PRIMARY KEY AUTOINCREMENT, origen TEXT, texto TEXT)''')
    # Tablas Comportamentales e Integridad (Likert)
    c.execute('''CREATE TABLE IF NOT EXISTS preguntas_likert (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria TEXT,
        competencia_o_valor TEXT,
        tipo_item TEXT,
        afirmacion TEXT,
        respuesta_optima TEXT,
        respuesta_aceptable TEXT,
        justificacion_psicometrica TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS fragmentos_comportamentales (
        id INTEGER PRIMARY KEY AUTOINCREMENT, origen TEXT, texto TEXT)''')
    conn.commit()
    conn.close()

# ==========================================
# 2. INTERFAZ GRÁFICA INTEGRAL (PC)
# ==========================================
class SimuladorDIANApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador DIAN 2676 - Funcional (PJS) + Comportamental e Integridad (Likert)")
        self.root.geometry("980x780")
        self.root.configure(bg="#f4f6f9")
        inicializar_bd()
        self.fabricando = False
        self.api_keys_guardadas = ""
        self.main_frame = tk.Frame(self.root, bg="#f4f6f9")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=12)
        self.mostrar_menu_principal()

    def limpiar_pantalla(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def obtener_conteos(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM preguntas_pjs")
        p_pjs = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM fragmentos_pdf")
        f_pjs = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM preguntas_likert")
        p_lik = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM fragmentos_comportamentales")
        f_lik = c.fetchone()[0]
        conn.close()
        return p_pjs, f_pjs, p_lik, f_lik

    def mostrar_menu_principal(self):
        self.limpiar_pantalla()
        p_pjs, f_pjs, p_lik, f_lik = self.obtener_conteos()

        tk.Label(
            self.main_frame, text="CENTRO DE ENTRENAMIENTO DIAN 2676 - GESTOR I",
            font=("Segoe UI", 17, "bold"), bg="#f4f6f9", fg="#1a365d"
        ).pack(pady=(2, 6))

        # PANEL DE ESTADÍSTICAS
        stats_frame = tk.Frame(self.main_frame, bg="white", bd=1, relief="solid", padx=15, pady=10)
        stats_frame.pack(fill="x", pady=5)

        col_izq = tk.Frame(stats_frame, bg="white")
        col_izq.pack(side="left", expand=True)
        tk.Label(col_izq, text=f"📘 Preguntas Funcionales (PJS): {p_pjs}", font=("Segoe UI", 11, "bold"), bg="white", fg="#2b6cb0").pack(anchor="w")
        tk.Label(col_izq, text=f"📄 Fragmentos Técnicos ('documentos_dian'): {f_pjs}", font=("Segoe UI", 9), bg="white", fg="#4a5568").pack(anchor="w")

        col_der = tk.Frame(stats_frame, bg="white")
        col_der.pack(side="right", expand=True)
        tk.Label(col_der, text=f"⚖️ Preguntas Likert (Comportamental/Integridad): {p_lik}", font=("Segoe UI", 11, "bold"), bg="white", fg="#6b46c1").pack(anchor="w")
        tk.Label(col_der, text=f"📄 Fragmentos Éticos ('documentos_comportamentales'): {f_lik}", font=("Segoe UI", 9), bg="white", fg="#4a5568").pack(anchor="w")

        # SECCIÓN 1: SELECTOR DE MODO DE SIMULACRO
        sim_frame = tk.LabelFrame(
            self.main_frame, text=" 1. Seleccionar Modo de Entrenamiento (Instantáneo Offline) ",
            font=("Segoe UI", 11, "bold"), bg="#f4f6f9", padx=15, pady=10
        )
        sim_frame.pack(fill="x", pady=6)

        self.modo_examen_var = tk.StringVar(value="LIKERT")
        modos_box = tk.Frame(sim_frame, bg="#f4f6f9")
        modos_box.pack(fill="x", pady=4)

        tk.Radiobutton(
            modos_box, text="📘 1. Solo Competencias Funcionales (PJS - Opciones A, B, C)",
            variable=self.modo_examen_var, value="PJS", font=("Segoe UI", 10, "bold"), bg="#f4f6f9"
        ).pack(anchor="w")
        tk.Radiobutton(
            modos_box, text="⚖️ 2. Solo Comportamentales e Integridad (Escala Likert A, B, C, D - Psicometría Anti-Sesgo)",
            variable=self.modo_examen_var, value="LIKERT", font=("Segoe UI", 10, "bold"), bg="#f4f6f9", fg="#553c9a"
        ).pack(anchor="w")
        tk.Radiobutton(
            modos_box, text="🏛️ 3. Simulacro Integral Ponderado (50% PJS + 50% Likert en sesión continua)",
            variable=self.modo_examen_var, value="INTEGRAL", font=("Segoe UI", 10, "bold"), bg="#f4f6f9", fg="#2f855a"
        ).pack(anchor="w")

        ctrl_sim = tk.Frame(sim_frame, bg="#f4f6f9")
        ctrl_sim.pack(fill="x", pady=(8, 2))
        tk.Label(ctrl_sim, text="Cantidad total de preguntas:", font=("Segoe UI", 10), bg="#f4f6f9").pack(side="left")
        self.cant_examen_var = tk.StringVar(value="20")
        tk.Entry(ctrl_sim, textvariable=self.cant_examen_var, width=8, font=("Segoe UI", 10)).pack(side="left", padx=10)
        tk.Button(
            ctrl_sim, text="▶ INICIAR SIMULACRO SELECCIONADO", font=("Segoe UI", 10, "bold"),
            bg="#2b6cb0", fg="white", padx=15, pady=4, command=self.iniciar_examen
        ).pack(side="left", padx=10)

        # SECCIÓN 2: FÁBRICA DUAL (PJS Y LIKERT)
        fab_frame = tk.LabelFrame(
            self.main_frame, text=" 2. Mega-Fábrica Dual con IA (Rotación Multiclave y Multimodelo) ",
            font=("Segoe UI", 11, "bold"), bg="#f4f6f9", padx=15, pady=10
        )
        fab_frame.pack(fill="both", expand=True, pady=6)

        f_keys = tk.Frame(fab_frame, bg="#f4f6f9")
        f_keys.pack(fill="x", pady=4)
        tk.Label(f_keys, text="API Keys (separadas por coma):", bg="#f4f6f9", font=("Segoe UI", 9)).pack(side="left")
        self.api_keys_var = tk.StringVar(value=self.api_keys_guardadas)
        tk.Entry(f_keys, textvariable=self.api_keys_var, width=55, show="*").pack(side="left", padx=8)

        tk.Label(f_keys, text="Meta a fabricar:", bg="#f4f6f9", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 4))
        self.meta_fab_var = tk.StringVar(value="100")
        tk.Entry(f_keys, textvariable=self.meta_fab_var, width=7).pack(side="left")

        f_botones = tk.Frame(fab_frame, bg="#f4f6f9")
        f_botones.pack(fill="x", pady=6)

        tk.Button(
            f_botones, text="📥 1A. Escanear 'documentos_dian'", font=("Segoe UI", 9, "bold"),
            bg="#4a5568", fg="white", command=lambda: self.hilo_procesar_pdfs("PJS")
        ).pack(side="left", padx=4)

        tk.Button(
            f_botones, text="⚡ 2A. Fabricar Funcionales (PJS)", font=("Segoe UI", 9, "bold"),
            bg="#2b6cb0", fg="white", command=lambda: self.hilo_fabricar("PJS")
        ).pack(side="left", padx=4)

        tk.Button(
            f_botones, text="📥 1B. Escanear 'documentos_comportamentales'", font=("Segoe UI", 9, "bold"),
            bg="#553c9a", fg="white", command=lambda: self.hilo_procesar_pdfs("LIKERT")
        ).pack(side="left", padx=(18, 4))

        self.btn_fab_likert = tk.Button(
            f_botones, text="⚡ 2B. Fabricar Likert (Comportamental/Integridad)", font=("Segoe UI", 9, "bold"),
            bg="#38a169", fg="white", command=lambda: self.hilo_fabricar("LIKERT")
        )
        self.btn_fab_likert.pack(side="left", padx=4)

        self.log_box = scrolledtext.ScrolledText(fab_frame, height=11, font=("Consolas", 9), bg="#1a202c", fg="#e2e8f0")
        self.log_box.pack(fill="both", expand=True, pady=6)
        self.escribir_log(
            "Sistema Dual listo.\n"
            "• Para cargar el Diccionario Res. 065 y el Código de Integridad: ponlos en la carpeta 'documentos_comportamentales' y pulsa '1B'.\n"
            "• Luego pulsa '2B. Fabricar Likert' para crear preguntas calibradas sin sesgos (Extremos A/D, Medios B/C y Subescala de Control)."
        )

    def escribir_log(self, texto):
        if hasattr(self, "log_box") and self.log_box.winfo_exists():
            self.log_box.insert(tk.END, texto + "\n")
            self.log_box.see(tk.END)

    # ------------------------------------------
    # ESCANEO DE PDFS POR CARPETA SEPARADA
    # ------------------------------------------
    def hilo_procesar_pdfs(self, tipo):
        threading.Thread(target=self.procesar_pdfs, args=(tipo,), daemon=True).start()

    def procesar_pdfs(self, tipo):
        carpeta = CARPETA_PDFS_FUNC if tipo == "PJS" else CARPETA_PDFS_COMP
        tabla = "fragmentos_pdf" if tipo == "PJS" else "fragmentos_comportamentales"

        if not os.path.exists(carpeta):
            os.makedirs(carpeta)
            self.escribir_log(f"[!] Se creó la carpeta '{carpeta}'. Mete allí los PDFs correspondientes y vuelve a pulsar.")
            return

        archivos = [f for f in os.listdir(carpeta) if f.lower().endswith(".pdf")]
        if not archivos:
            self.escribir_log(f"[!] No hay archivos PDF en '{carpeta}'.")
            return

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(f"DELETE FROM {tabla}")
        contador = 0
        for arch in archivos:
            try:
                with open(os.path.join(carpeta, arch), "rb") as f:
                    lector = PyPDF2.PdfReader(f)
                    texto_total = "\n".join([p.extract_text() for p in lector.pages if p.extract_text()])
                    for i in range(0, len(texto_total), 850):
                        trozo = texto_total[i:i + 1000].strip()
                        if len(trozo) > 80:
                            c.execute(f"INSERT INTO {tabla} (origen, texto) VALUES (?, ?)", (arch, trozo))
                            contador += 1
                self.escribir_log(f"✔ Leído ({tipo}): {arch}")
            except Exception as e:
                self.escribir_log(f"❌ Error en {arch}: {e}")
        conn.commit()
        conn.close()
        self.escribir_log(f"✅ {contador} fragmentos guardados en '{tabla}' (Tus preguntas previas están intactas).")
        self.root.after(800, self.mostrar_menu_principal)

    # ------------------------------------------
    # FÁBRICA DUAL (PJS O LIKERT PSICOMÉTRICO)
    # ------------------------------------------
    def hilo_fabricar(self, tipo):
        if self.fabricando:
            self.fabricando = False
            self.escribir_log("⏹ Deteniendo fábrica al terminar el lote actual...")
            return
        self.api_keys_guardadas = self.api_keys_var.get()
        threading.Thread(target=self.fabricar_preguntas, args=(tipo,), daemon=True).start()

    def obtener_modelos(self, cliente):
        modelos = ["gemini-2.5-flash", "gemini-2.0-flash"]
        try:
            for m in cliente.models.list():
                nom = m.name.replace("models/", "")
                if "gemini" in nom and not any(x in nom for x in ["vision", "embedding", "imagen", "veo", "audio", "tts"]):
                    if nom not in modelos:
                        modelos.append(nom)
        except Exception:
            pass
        return modelos

    def fabricar_preguntas(self, tipo):
        keys = [k.strip() for k in self.api_keys_var.get().split(",") if k.strip()]
        if not keys:
            return self.escribir_log("[!] Ingresa al menos una API Key válida.")

        tabla_frag = "fragmentos_pdf" if tipo == "PJS" else "fragmentos_comportamentales"
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(f"SELECT texto FROM {tabla_frag}")
        filas = [r[0] for r in c.fetchall()]
        conn.close()

        if not filas:
            return self.escribir_log(f"[!] Primero escanea los PDFs de la sección {tipo}.")

        try:
            meta = int(self.meta_fab_var.get())
        except ValueError:
            return self.escribir_log("[!] Meta inválida.")

        self.fabricando = True
        creadas = 0
        idx_key = 0
        cliente = genai.Client(api_key=keys[idx_key])
        modelos = self.obtener_modelos(cliente)
        idx_mod = 0

        while creadas < meta and self.fabricando:
            if idx_mod >= len(modelos):
                idx_key += 1
                if idx_key >= len(keys):
                    self.escribir_log("🛑 Se agotaron todas las API Keys y modelos disponibles.")
                    break
                cliente = genai.Client(api_key=keys[idx_key])
                modelos = self.obtener_modelos(cliente)
                idx_mod = 0
                continue

            mod_actual = modelos[idx_mod]
            lote = min(10, meta - creadas)
            contexto = "\n\n---\n\n".join(random.sample(filas, min(8, len(filas))))

            if tipo == "PJS":
                prompt = f"""
                Actúa como el evaluador más estricto de la CNSC para la convocatoria DIAN 2676.
                Diseña EXACTAMENTE {lote} preguntas de Prueba de Juicio Situacional (PJS) de NIVEL AVANZADO para Gestor I.
                Basado en estos manuales:
                {contexto}
                REGLAS:
                1. 'caso': Escenario laboral muy complejo, con sobrecarga de datos, variables o fechas límite en la DIAN.
                2. 'enunciado': Acción que le corresponde realizar al funcionario.
                3. 'opcion_a', 'opcion_b', 'opcion_c': Opciones LARGAS y detalladas (mínimo 2 líneas, sin letra inicial).
                4. 'correcta': "A", "B" o "C" (varía aleatoriamente la posición).
                5. TRAMPAS: Un distractor con falla de competencia y otro con etapa procesal equivocada o regla general vs excepción.
                6. 'justificacion': Análisis jurídico y técnico profundo.
                """
                esquema = LotePreguntasPJS
            else:
                prompt = f"""
                Actúa como psicómetra experto de la CNSC y la Fundación Universitaria del Área Andina (FUAA) diseñando la Prueba Escrita de Competencias Comportamentales (Resolución 065 de 2024) y la Prueba de Integridad (Código de Integridad DIAN CG-TAH-0002) para el cargo Gestor I (Proceso DIAN 2676).

                Básate en estos fragmentos oficiales del Diccionario de Competencias y Código de Integridad:
                {contexto}

                Diseña EXACTAMENTE {lote} ítems en formato de autoinforme con Escala Likert de 4 niveles:
                A. Totalmente en desacuerdo.
                B. En desacuerdo.
                C. De acuerdo.
                D. Totalmente de acuerdo.

                REGLAS PSICOMÉTRICAS ESTRICTAS (ANTI-SESGO):
                Cada afirmación debe estar redactada en primera persona del singular (ej. "Adapto la manera de dar mis explicaciones técnicas ampliando el tiempo asignado al trámite", "Exploro las nuevas plataformas digitales de la entidad asumiendo tiempo adicional de mi jornada"), cruzando conductas del empleo con tensiones operativas reales (plazos, carga de trabajo, cierre de jornada, presión de usuarios o compañeros).

                Para evitar sesgos, distribuye equitativamente los ítems del lote entre estos 5 tipos ('tipo_item'):
                1. 'EXTREMO_POSITIVO_D': Conducta ética innegociable ("Lo que hago" del Código de Integridad: Honestidad, Respeto, Compromiso, Diligencia, Justicia; o valores aspiracionales: Valentía, Objetividad, Templanza, Providencia) o conducta observable pura sin infringir normas.
                   -> 'respuesta_optima': "D", 'respuesta_aceptable': "C".
                2. 'EXTREMO_NEGATIVO_A': Transgresión ética o conductual camuflada de eficiencia, pragmatismo o compañerismo ("Lo que no hago" del Código de Integridad, conflicto de interés, trato preferencial, uso indebido de recursos/información).
                   -> 'respuesta_optima': "A", 'respuesta_aceptable': "A" (en faltas éticas no hay término medio).
                3. 'MEDIO_POSITIVO_C': Dilema de tensión operativa (estilo Guía FUAA): la afirmación propone una conducta deseable (Adaptabilidad, Orientación al usuario, Solución de problemas, Innovación, Trabajo en equipo) pero sacrifica levemente tiempos del trámite, jornada propia o pausas. La respuesta ideal es "C" (De acuerdo) porque demuestra disposición conductual positiva sin caer en exageración irreal ni descuido temerario de plazos.
                   -> 'respuesta_optima': "C", 'respuesta_aceptable': "D".
                4. 'MEDIO_NEGATIVO_B': Conducta rígida, pasiva o individualista que NO es falta disciplinaria (porque protege las entregas propias o sigue el reglamento al pie de la letra), pero limita la cooperación, la innovación o el servicio al ciudadano. La respuesta ideal es "B" (En desacuerdo) y no "A", porque parte de una premisa laboralmente válida pero insuficiente.
                   -> 'respuesta_optima': "B", 'respuesta_aceptable': "A".
                5. 'CONTROL_DESEABILIDAD': Ítem de la Subescala de Control de Deseabilidad Social (para detectar fingimiento o respuestas exageradamente favorables). Usa afirmaciones absolutistas ("Jamás en mi vida he sentido dudas...", "Nunca experimento cansancio ni molestia ante groserías..."). Según el Código de Integridad ("es humano cometer errores", "es válido no saberlo todo y pedir ayuda"), el aspirante honesto marca un grado medio ("B" o "C") y evita el extremo falso.
                   -> 'respuesta_optima': "B" (si la frase niega una limitación humana normal) o "C" (si admite con mesura una realidad humana), 'respuesta_aceptable': la otra opción media.

                En 'categoria' escribe únicamente: "COMPORTAMENTAL", "INTEGRIDAD" o "CONTROL_DESEABILIDAD".
                En 'competencia_o_valor' escribe el nombre exacto (ej. "Adaptabilidad", "Solución de problemas", "Innovación", "Trabajo en equipo", "Orientación al logro", "Orientación al usuario", "Comunicación efectiva", "Comportamiento ético", "Honestidad", "Justicia", "Diligencia", "Templanza", "Subescala de Control").
                En 'justificacion_psicometrica' explica detalladamente por qué la letra óptima (A, B, C o D) es la psicométricamente correcta según el Diccionario Res. 065/2024 o el Código de Integridad y por qué irse al extremo o al medio equivocado penaliza el puntaje.
                """
                esquema = LotePreguntasLikert

            try:
                self.escribir_log(f"🔑 Key {idx_key+1} | 🤖 [{mod_actual}] -> Generando {lote} ítems ({tipo})...")
                resp = cliente.models.generate_content(
                    model=mod_actual,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=esquema,
                        temperature=0.75,
                    ),
                )
                datos = json.loads(resp.text).get("preguntas", [])
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                guardadas = 0
                for p in datos:
                    if tipo == "PJS":
                        letra = p["correcta"].strip().upper()[:1]
                        if letra in ["A", "B", "C"]:
                            c.execute('''INSERT INTO preguntas_pjs
                                (caso, enunciado, opcion_a, opcion_b, opcion_c, correcta, justificacion)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                (p["caso"], p["enunciado"], p["opcion_a"], p["opcion_b"], p["opcion_c"], letra, p["justificacion"]))
                            creadas += 1
                            guardadas += 1
                    else:
                        optima = p["respuesta_optima"].strip().upper()[:1]
                        aceptable = p["respuesta_aceptable"].strip().upper()[:1]
                        if optima in ["A", "B", "C", "D"]:
                            if aceptable not in ["A", "B", "C", "D"]:
                                aceptable = optima
                            c.execute('''INSERT INTO preguntas_likert
                                (categoria, competencia_o_valor, tipo_item, afirmacion, respuesta_optima, respuesta_aceptable, justificacion_psicometrica)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                (p["categoria"], p["competencia_o_valor"], p["tipo_item"], p["afirmacion"], optima, aceptable, p["justificacion_psicometrica"]))
                            creadas += 1
                            guardadas += 1
                conn.commit()
                conn.close()
                self.escribir_log(f"✅ +{guardadas} ítems ({tipo}) guardados. Progreso: {creadas}/{meta}")
                time.sleep(5)
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    if "PerDay" in err or "limit: 20" in err or "limit: 0" in err:
                        self.escribir_log(f"⚠️ Cuota agotada en [{mod_actual}]. Rotando modelo...")
                        idx_mod += 1
                    else:
                        self.escribir_log("⏳ Límite por minuto. Pausando 45s...")
                        time.sleep(45)
                else:
                    self.escribir_log(f"⚠️ Saltando [{mod_actual}] ({err[:55]}...)")
                    idx_mod += 1

        self.fabricando = False
        self.root.after(1000, self.mostrar_menu_principal)

    # ------------------------------------------
    # MOTOR DE SIMULACRO (PJS, LIKERT E INTEGRAL)
    # ------------------------------------------
    def iniciar_examen(self):
        try:
            cant = int(self.cant_examen_var.get())
        except ValueError:
            return messagebox.showerror("Error", "Ingresa un número válido de preguntas.")

        modo = self.modo_examen_var.get()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        self.cola_examen = []

        if modo in ["PJS", "INTEGRAL"]:
            n_pjs = cant if modo == "PJS" else max(1, cant // 2)
            c.execute("SELECT * FROM preguntas_pjs ORDER BY RANDOM() LIMIT ?", (n_pjs,))
            for r in c.fetchall():
                self.cola_examen.append({"formato": "PJS", "datos": r})

        if modo in ["LIKERT", "INTEGRAL"]:
            n_lik = cant if modo == "LIKERT" else (cant - len(self.cola_examen))
            c.execute("SELECT * FROM preguntas_likert ORDER BY RANDOM() LIMIT ?", (n_lik,))
            for r in c.fetchall():
                self.cola_examen.append({"formato": "LIKERT", "datos": r})

        conn.close()

        if not self.cola_examen:
            return messagebox.showwarning("Banco vacío", "No hay preguntas para el modo seleccionado. Usa primero la Fábrica.")

        self.indice_actual = 0
        self.historial_examen = []
        self.tiempo_inicio = time.time()
        self.examen_activo = True
        self.mostrar_pregunta_examen()
        self.actualizar_reloj()

    def actualizar_reloj(self):
        if getattr(self, "examen_activo", False) and hasattr(self, "lbl_reloj") and self.lbl_reloj.winfo_exists():
            segs = int(time.time() - self.tiempo_inicio)
            self.lbl_reloj.config(text=f"⏱ {segs//3600:02d}:{(segs%3600)//60:02d}:{segs%60:02d}")
            self.root.after(1000, self.actualizar_reloj)

    def mostrar_pregunta_examen(self):
        self.limpiar_pantalla()
        item = self.cola_examen[self.indice_actual]
        formato = item["formato"]
        datos = item["datos"]

        color_barra = "#1a365d" if formato == "PJS" else "#44337a"
        etiqueta_tipo = "COMPETENCIAS FUNCIONALES (PJS)" if formato == "PJS" else f"ESCALA LIKERT - {datos[1]} ({datos[2]})"

        top_bar = tk.Frame(self.main_frame, bg=color_barra, padx=15, pady=10)
        top_bar.pack(fill="x")
        tk.Label(
            top_bar, text=f"Pregunta {self.indice_actual + 1} de {len(self.cola_examen)}  |  {etiqueta_tipo}",
            font=("Segoe UI", 11, "bold"), bg=color_barra, fg="white"
        ).pack(side="left")
        self.lbl_reloj = tk.Label(top_bar, text="⏱ 00:00:00", font=("Segoe UI", 12, "bold"), bg=color_barra, fg="#fbd38d")
        self.lbl_reloj.pack(side="right")

        txt = scrolledtext.ScrolledText(self.main_frame, height=8 if formato == "PJS" else 5, font=("Segoe UI", 11), wrap="word", padx=12, pady=12)
        txt.pack(fill="x", pady=12)

        self.opcion_sel = tk.StringVar(value="")

        if formato == "PJS":
            _, caso, enunciado, opt_a, opt_b, opt_c, _, _ = datos
            txt.insert(tk.END, f"CASO:\n{caso}\n\nENUNCIADO:\n{enunciado}")
            opciones = [("A", opt_a), ("B", opt_b), ("C", opt_c)]
        else:
            _, categoria, comp_val, _, afirmacion, _, _, _ = datos
            txt.insert(tk.END, f"AFIRMACIÓN (Seleccione su nivel de acuerdo habitual frente a la situación):\n\n\"{afirmacion}\"")
            opciones = [
                ("A", "Totalmente en desacuerdo."),
                ("B", "En desacuerdo."),
                ("C", "De acuerdo."),
                ("D", "Totalmente de acuerdo.")
            ]
        txt.config(state="disabled")

        for letra, texto_opt in opciones:
            tk.Radiobutton(
                self.main_frame, text=f"{letra}. {texto_opt}", variable=self.opcion_sel, value=letra,
                font=("Segoe UI", 10), bg="white", anchor="w", justify="left", wraplength=850,
                padx=15, pady=10, bd=1, relief="solid", selectcolor="#ebf8ff"
            ).pack(fill="x", pady=4)

        tk.Button(
            self.main_frame, text="Confirmar y Avanzar ➡", font=("Segoe UI", 11, "bold"),
            bg="#2b6cb0", fg="white", padx=20, pady=8, command=self.procesar_respuesta
        ).pack(pady=12)

    def procesar_respuesta(self):
        resp = self.opcion_sel.get()
        if not resp:
            return messagebox.showinfo("Atención", "Selecciona una opción antes de continuar.")

        item = self.cola_examen[self.indice_actual]
        formato = item["formato"]
        datos = item["datos"]

        if formato == "PJS":
            _, caso, enunciado, opt_a, opt_b, opt_c, correcta, just = datos
            pts = 1.0 if resp == correcta else 0.0
            self.historial_examen.append({
                "num": self.indice_actual + 1,
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
            if resp == optima:
                pts = 1.0
            elif resp == aceptable:
                pts = 0.5
            else:
                pts = 0.0
            self.historial_examen.append({
                "num": self.indice_actual + 1,
                "formato": "LIKERT",
                "categoria": categoria,
                "subtipo": f"{comp_val} ({tipo_item})",
                "tipo_item": tipo_item,
                "afirmacion": afirmacion,
                "opciones": {
                    "A": "Totalmente en desacuerdo.",
                    "B": "En desacuerdo.",
                    "C": "De acuerdo.",
                    "D": "Totalmente de acuerdo."
                },
                "tu_resp": resp,
                "optima": optima,
                "aceptable": aceptable,
                "puntos": pts,
                "just": just
            })

        self.indice_actual += 1
        if self.indice_actual < len(self.cola_examen):
            self.mostrar_pregunta_examen()
        else:
            self.mostrar_resultados()

    def renderizar_revision_texto(self, modo_filtro="TODAS"):
        self.rev_box.config(state="normal")
        self.rev_box.delete("1.0", tk.END)

        mostradas = 0
        for i in self.historial_examen:
            if modo_filtro == "ERRORES" and i["puntos"] == 1.0:
                continue
            mostradas += 1

            if i["formato"] == "PJS":
                icono = "✅ CORRECTA (100%)" if i["puntos"] == 1.0 else "❌ INCORRECTA (0%)"
                self.rev_box.insert(tk.END, f"PREGUNTA {i['num']} [FUNCIONAL PJS]  ➔  {icono}\n")
                self.rev_box.insert(tk.END, f"{'-'*80}\n")
                self.rev_box.insert(tk.END, f"📖 CASO:\n{i['caso']}\n\n")
                self.rev_box.insert(tk.END, f"🎯 ENUNCIADO:\n{i['enunciado']}\n\n")
                self.rev_box.insert(tk.END, "📋 OPCIONES DE RESPUESTA:\n")
                for letra, texto_opt in i["opciones"].items():
                    etiqueta = ""
                    if letra == i["optima"] and letra == i["tu_resp"]:
                        etiqueta = "   ✅ [TU RESPUESTA - CORRECTA]"
                    elif letra == i["tu_resp"]:
                        etiqueta = "   ❌ [TU ELECCIÓN - INCORRECTA]"
                    elif letra == i["optima"]:
                        etiqueta = "   ✔️ [RESPUESTA CORRECTA]"
                    self.rev_box.insert(tk.END, f"   {letra}. {texto_opt}{etiqueta}\n\n")
                self.rev_box.insert(tk.END, f"👉 Resumen: Marcaste {i['tu_resp']}  |  Opción Correcta: {i['optima']}\n\n")
                self.rev_box.insert(tk.END, f"💡 JUSTIFICACIÓN TÉCNICA Y ANÁLISIS DE DISTRACTORES:\n{i['just']}\n")
            else:
                icono = "✅ ÓPTIMA (100%)" if i["puntos"] == 1.0 else ("⚠️ ACEPTABLE PARCIAL (50%)" if i["puntos"] == 0.5 else "❌ DESVIACIÓN PSICOMÉTRICA (0%)")
                self.rev_box.insert(tk.END, f"PREGUNTA {i['num']} [LIKERT - {i['subtipo']}]  ➔  {icono}\n")
                self.rev_box.insert(tk.END, f"{'-'*80}\n")
                self.rev_box.insert(tk.END, f"📝 AFIRMACIÓN EVALUADA:\n\"{i['afirmacion']}\"\n\n")
                self.rev_box.insert(tk.END, "📋 ESCALA DE OPCIONES:\n")
                for letra, texto_opt in i["opciones"].items():
                    etiqueta = ""
                    if letra == i["optima"] and letra == i["tu_resp"]:
                        etiqueta = "   ✅ [TU ELECCIÓN - ÓPTIMA 100%]"
                    elif letra == i["aceptable"] and letra == i["tu_resp"]:
                        etiqueta = "   ⚠️ [TU ELECCIÓN - ACEPTABLE 50%]"
                    elif letra == i["tu_resp"]:
                        etiqueta = "   ❌ [TU ELECCIÓN - 0%]"
                    elif letra == i["optima"]:
                        etiqueta = "   ✔️ [ÓPTIMA CNSC 100%]"
                    elif letra == i["aceptable"]:
                        etiqueta = "   🔹 [ACEPTABLE 50%]"
                    self.rev_box.insert(tk.END, f"   {letra}. {texto_opt}{etiqueta}\n")
                self.rev_box.insert(tk.END, f"\n👉 Tu respuesta: {i['tu_resp']}  |  Óptima CNSC: {i['optima']} (Aceptable: {i['aceptable']})\n\n")
                self.rev_box.insert(tk.END, f"💡 ANÁLISIS PSICOMÉTRICO:\n{i['just']}\n")

            self.rev_box.insert(tk.END, f"{'='*85}\n\n")

        if mostradas == 0:
            self.rev_box.insert(tk.END, "🎉 ¡Felicitaciones! No tuviste ningún error o desviación en este simulacro.")

        self.rev_box.config(state="disabled")

    def mostrar_resultados(self):
        self.examen_activo = False
        self.limpiar_pantalla()

        items_pjs = [x for x in self.historial_examen if x["formato"] == "PJS"]
        items_lik = [x for x in self.historial_examen if x["formato"] == "LIKERT"]

        score_pjs = (sum(x["puntos"] for x in items_pjs) / len(items_pjs) * 100) if items_pjs else 0.0
        score_lik = (sum(x["puntos"] for x in items_lik) / len(items_lik) * 100) if items_lik else 0.0

        tk.Label(self.main_frame, text="DIAGNÓSTICO Y RESULTADOS DEL SIMULACRO", font=("Segoe UI", 15, "bold"), bg="#f4f6f9", fg="#1a365d").pack(pady=2)

        res_panel = tk.Frame(self.main_frame, bg="white", bd=1, relief="solid", padx=15, pady=8)
        res_panel.pack(fill="x", pady=4)

        if items_pjs and not items_lik:
            estado = "✅ APROBADO (Supera 70.00)" if score_pjs >= 70.0 else "❌ NO APROBADO (Mínimo 70.00)"
            tk.Label(res_panel, text=f"Puntaje Funcional (PJS): {score_pjs:.2f} / 100.00  |  {estado}", font=("Segoe UI", 12, "bold"), bg="white").pack()
        elif items_lik and not items_pjs:
            extremos = sum(1 for x in items_lik if x["tu_resp"] in ["A", "D"])
            medios = sum(1 for x in items_lik if x["tu_resp"] in ["B", "C"])
            ctrl_items = [x for x in items_lik if x["categoria"] == "CONTROL_DESEABILIDAD" or "CONTROL" in x["tipo_item"]]
            fallos_ctrl = sum(1 for x in ctrl_items if x["puntos"] == 0.0)
            alerta_ctrl = "⚠️ ALERTA: Caíste en trampas de Deseabilidad Social (marcar extremos irreales)." if fallos_ctrl > 0 else "✅ Subescala de Control superada (Perfil consistente y honesto)."

            tk.Label(res_panel, text=f"Puntaje Psicométrico Likert: {score_lik:.2f} / 100.00", font=("Segoe UI", 12, "bold"), bg="white", fg="#553c9a").pack()
            tk.Label(res_panel, text=f"Balance de Respuestas: Extremos (A/D): {extremos}  |  Medios (B/C): {medios}", font=("Segoe UI", 10), bg="white").pack()
            tk.Label(res_panel, text=alerta_ctrl, font=("Segoe UI", 10, "bold"), bg="white", fg="#c53030" if fallos_ctrl > 0 else "#2f855a").pack()
        else:
            ponderado = (score_pjs * 0.70) + (score_lik * 0.30)
            tk.Label(
                res_panel,
                text=f"Funcional (70%): {score_pjs:.2f} pts  |  Likert Comportamental/Integridad (30%): {score_lik:.2f} pts\n"
                     f"🏆 PUNTAJE PONDERADO CONCURSO DIAN: {ponderado:.2f} / 100.00",
                font=("Segoe UI", 11, "bold"), bg="white", fg="#1a365d"
            ).pack()

        # Barra de filtro para ver Todas o Solo Errores
        filtro_bar = tk.Frame(self.main_frame, bg="#f4f6f9")
        filtro_bar.pack(fill="x", pady=4)
        tk.Label(filtro_bar, text="Filtrar revisión:", font=("Segoe UI", 10, "bold"), bg="#f4f6f9", fg="#2d3748").pack(side="left", padx=(0, 8))
        tk.Button(
            filtro_bar, text="📋 Ver Todas las Preguntas", font=("Segoe UI", 9, "bold"),
            bg="#2b6cb0", fg="white", padx=10, command=lambda: self.renderizar_revision_texto("TODAS")
        ).pack(side="left", padx=4)
        tk.Button(
            filtro_bar, text="❌ Ver Solo Errores / Parciales", font=("Segoe UI", 9, "bold"),
            bg="#c53030", fg="white", padx=10, command=lambda: self.renderizar_revision_texto("ERRORES")
        ).pack(side="left", padx=4)

        self.rev_box = scrolledtext.ScrolledText(self.main_frame, height=17, font=("Segoe UI", 10), wrap="word", padx=12, pady=12)
        self.rev_box.pack(fill="both", expand=True, pady=4)

        self.renderizar_revision_texto("TODAS")

        tk.Button(
            self.main_frame, text="⬅ Volver al Menú Principal", font=("Segoe UI", 11, "bold"),
            bg="#4a5568", fg="white", padx=15, pady=6, command=self.mostrar_menu_principal
        ).pack(pady=4)

if __name__ == "__main__":
    root = tk.Tk()
    app = SimuladorDIANApp(root)
    root.mainloop()