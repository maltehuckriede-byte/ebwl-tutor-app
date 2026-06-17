import streamlit as st
from google import genai
from google.genai import types
from groq import Groq
import pypdf
import os
import json
import random
import re
import time
from fpdf import FPDF

# --- 1. SETUP & API-CLIENTS ---
st.set_page_config(page_title="Wolf of Wüllnerstraße | RWTH Aachen", page_icon="🐺", layout="wide")

GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
google_client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ==========================================
# 📄 HELPER FÜR PDF-GENERIERUNG
# ==========================================
def generate_pdf_bytes(thema, text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    pdf.cell(0, 10, f"Lernzettel: {thema.replace('/zettel', '').strip().upper()}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 11)
    
    safe_text = text.replace("**", "").replace("#", "").replace("•", "-").replace("*", "-")
    safe_text = safe_text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    safe_text = safe_text.replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue").replace("ß", "ss")
    
    for line in safe_text.split("\n"):
        clean_line = line.encode('latin-1', 'replace').decode('latin-1').replace("?", "-")
        pdf.multi_cell(0, 6, clean_line)
        
    return pdf.output()

# ==========================================
# 🃏 HELPER FÜR INTERAKTIVE KARTEIKARTEN
# ==========================================
def display_html_flashcards(ai_text):
    # NEUER REGEX: Sehr robust, ignoriert Klammern wie "(Frage)" und liest sauber bis zum "|" oder Zeilenumbruch
    cards = re.findall(r'(?:Vorderseite|Frage).*?\:\s*([^|\n]+)(?:\s*\|\s*|\n+)(?:Rückseite|Antwort).*?\:\s*([^\n]+)', ai_text, re.IGNORECASE)
    
    if not cards:
        # Fallback-Regex
        cards = re.findall(r'\*\*(?:Vorderseite|Frage).*?\*\*\s*([^|\n]+)(?:\s*\|\s*|\n+)\*\*(?:Rückseite|Antwort).*?\*\*\s*([^\n]+)', ai_text, re.IGNORECASE)

    if cards:
        # Wir blenden die Überschrift aus, da wir diese gleich im Chat-Verlauf dynamisch rendern
        cards_html = ""
        
        for i, (front, back) in enumerate(cards):
            # Eventuelle Markdown-Sterne vom Bot entfernen, damit sie nicht in der 3D Karte landen
            front_text = front.replace("**", "").strip()
            back_text = back.replace("**", "").strip()
            
            cards_html += f"""
            <div class="card-box">
                <input type="checkbox" id="card-{i}" class="flip-checkbox" style="display:none;">
                <label for="card-{i}" class="flip-card">
                    <div class="flip-card-inner">
                        <div class="flip-card-front">
                            <div class="card-header" style="color: #00549F;">FRAGE</div>
                            <div class="card-content">{front_text}</div>
                        </div>
                        <div class="flip-card-inner-back">
                            <div class="card-header" style="color: #57AB27;">ANTWORT</div>
                            <div class="card-content" style="font-weight: normal;">{back_text}</div>
                        </div>
                    </div>
                </label>
            </div>
            """
            
        full_html = f"""
        <style>
            .container {{ display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; font-family: 'Segoe UI', Arial, sans-serif; padding: 15px; }}
            .card-box {{ display: inline-block; perspective: 1000px; }}
            .flip-card {{ display: block; width: 280px; height: 180px; cursor: pointer; }}
            .flip-card-inner {{ position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s cubic-bezier(0.4, 0.2, 0.2, 1); transform-style: preserve-3d; box-shadow: 0 6px 15px rgba(0,0,0,0.08); border-radius: 12px; }}
            .flip-card:hover .flip-card-inner {{ box-shadow: 0 10px 20px rgba(0,84,159,0.15); }}
            .flip-checkbox:checked + .flip-card .flip-card-inner {{ transform: rotateY(180deg); }}
            .flip-card-front, .flip-card-inner-back {{ position: absolute; width: 100%; height: 100%; backface-visibility: hidden; -webkit-backface-visibility: hidden; border-radius: 12px; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; align-items: center; }}
            .flip-card-front {{ background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); color: #0f172a; border: 1px solid #cbd5e1; }}
            .flip-card-inner-back {{ background: #ffffff; color: #1e293b; transform: rotateY(180deg); border: 2px solid #57AB27; }}
            .card-header {{ font-size: 11px; font-weight: 800; text-transform: uppercase; margin-bottom: 12px; letter-spacing: 1px; }}
            .card-content {{ font-size: 14px; font-weight: 600; line-height: 1.5; overflow-y: auto; max-height: 120px; }}
            .card-content::-webkit-scrollbar {{ display: none; }}
        </style>
        <div class="container">{cards_html}</div>
        """
        # Moderne Render-Methode (Post-Juni 2026), um den Deprecation-Error zu vermeiden
        st.markdown(f'<div style="height: {230 if len(cards) <= 3 else 460}px; overflow-y: auto;">{full_html}</div>', unsafe_allow_html=True)

# --- 2. DATENBANK-SYSTEM & LERNFORTSCHRITT ---
DATA_FILE = "savegames.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)

database = load_data()

# ==========================================
# 📊 NEU: BERECHNUNGSLOGIK FÜR DAS DASHBOARD
# ==========================================

def calculate_progress(stats_dict):
    """Berechnet den Lernfortschritt (0.0 bis 1.0) basierend auf dem EBWL-Konzept."""
    if not stats_dict or stats_dict.get("attempts", 0) == 0:
        return 0.0

    # 1. Trefferquote (Richtig / Gesamt)
    trefferquote = stats_dict["correct"] / stats_dict["attempts"]

    # 2. Schwierigkeitsgewicht / Cap (Maximal erreichbarer Fortschritt je Level)
    level_weights = {"Einsteiger": 0.4, "Solide": 0.75, "Klausurniveau": 1.0, "Maximal": 1.0}
    schwierigkeitsgewicht = level_weights.get(stats_dict.get("max_level", "Einsteiger"), 0.4)

    # 3. Confidence-Gewicht (Gleitender Durchschnitt der Metakognition)
    confidence_gewicht = stats_dict.get("avg_confidence", 1.0)

    # 4. Aktualität (Spaced Repetition Decay)
    # Zieht 5 % Fortschritt pro inaktivem Tag ab (maximal 50 % Abzug)
    days_inactive = (time.time() - stats_dict.get("last_update", time.time())) / 86400
    aktualitaet = max(0.5, 1.0 - (days_inactive * 0.05))

    # Finale Berechnung
    fortschritt = trefferquote * schwierigkeitsgewicht * confidence_gewicht * aktualitaet
    
    return min(1.0, fortschritt)

def record_learning_event(username, pdf_name, is_correct, level, confidence_str="sicher"):
    """Speichert eine beantwortete Frage als Datenpunkt in der Datenbank ab."""
    user_data = database.get(username, {})
    if "progress" not in user_data:
        user_data["progress"] = {}
        
    if pdf_name not in user_data["progress"]:
        user_data["progress"][pdf_name] = {
            "attempts": 0, "correct": 0, "avg_confidence": 1.0, 
            "max_level": "Einsteiger", "last_update": time.time()
        }
        
    p_data = user_data["progress"][pdf_name]
    p_data["attempts"] += 1
    
    if is_correct:
        p_data["correct"] += 1
        # Höchstes erreichtes Level updaten (Cap verschieben)
        levels = ["Einsteiger", "Solide", "Klausurniveau", "Maximal"]
        current_idx = levels.index(p_data["max_level"]) if p_data["max_level"] in levels else 0
        new_idx = levels.index(level) if level in levels else 0
        
        if new_idx > current_idx:
            p_data["max_level"] = level
            
    # Confidence updaten (Gewichtung exakt nach Konzept Kapitel 6)
    conf_map = {"sicher": 1.0, "unsicher": 0.75, "geraten": 0.4}
    val = conf_map.get(confidence_str.lower(), 1.0)
    
    # Neuen gleitenden Durchschnitt der Sicherheit berechnen
    p_data["avg_confidence"] = ((p_data["avg_confidence"] * (p_data["attempts"] - 1)) + val) / p_data["attempts"]
    p_data["last_update"] = time.time()
    
    database[username] = user_data
    save_data(database)

# Initialisierung der Session States
if "current_page" not in st.session_state: st.session_state.current_page = "login"
if "username" not in st.session_state: st.session_state.username = ""
if "messages" not in st.session_state: st.session_state.messages = []
if "level" not in st.session_state: st.session_state.level = "Solide"
if "klausur_modus" not in st.session_state: st.session_state.klausur_modus = False
if "active_mode" not in st.session_state: st.session_state.active_mode = None

# --- 3. STARTBILDSCHIRM & LOGIN ---
if st.session_state.current_page == "login":
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("") 
        st.markdown("<h1 style='text-align: center; color: #00549F;'>Wolf of Wüllnerstraße</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; margin-top: -15px;'>RWTH Aachen | EBWL Lernbot</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        new_user = st.text_input("Wie lautet dein Name?")
        beta_code = st.text_input("Zugangscode:", type="password")
        
        st.write("") 
        if st.button("Anmelden", use_container_width=True):
            if beta_code != "PITCH2026": 
                st.error("❌ Falscher Zugangscode!")
            elif not new_user: 
                st.error("Bitte gib einen Namen ein!")
            else:
                st.session_state.username = new_user
                if new_user not in database:
                    database[new_user] = {"history": [], "progress": {}}
                save_data(database)
                st.session_state.messages = database[new_user].get("history", [])
                
                # Wir wechseln zum Dashboard statt direkt in den Chat!
                st.session_state.current_page = "dashboard"
                st.rerun()
    st.stop()

# --- 3.5 LERN-DASHBOARD ---
if st.session_state.current_page == "dashboard":
    st.title("📊 Dein Lern-Dashboard")
    st.markdown(f"Willkommen zurück, **{st.session_state.username}**. Hier ist dein aktueller Wissensstand basierend auf deinen Antworten und deiner Selbsteinschätzung.")
    st.write("")
    
    # Nutzerdaten abrufen
    user_data = database.get(st.session_state.username, {})
    progress_data = user_data.get("progress", {})
    
    # Globale KPIs berechnen
    total_questions = sum(p.get("attempts", 0) for p in progress_data.values())
    total_correct = sum(p.get("correct", 0) for p in progress_data.values())
    global_accuracy = int((total_correct / total_questions * 100)) if total_questions > 0 else 0
    
    # 3-Spalten-Layout für eine cleane "Web-App" Optik
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric(label="Beantwortete Fragen", value=total_questions)
    kpi2.metric(label="Trefferquote (Global)", value=f"{global_accuracy} %")
    kpi3.metric(label="Aktuelles Level", value=st.session_state.level)
    
    st.markdown("---")
    st.subheader("📚 Fortschritt pro Kapitel")
    
    if not progress_data:
        st.info("Du hast noch keine Fragen beantwortet. Starte eine Sitzung, um deinen Fortschritt zu füllen!")
    else:
        for pdf_name, stats in progress_data.items():
            # Die harte, ungeschönte Berechnung aufrufen
            score = calculate_progress(stats)
            score_percent = int(score * 100)
            
            # Ampelfarben nach EBWL-Konzept
            if score_percent >= 80: color = "🟢"
            elif score_percent >= 50: color = "🟡"
            else: color = "🔴"
            
            col_text, col_bar = st.columns([1, 2])
            with col_text:
                clean_name = pdf_name.replace(".pdf", "").replace("_", " ")
                st.markdown(f"**{color} {clean_name}**")
                st.caption(f"Cap-Level: {stats.get('max_level', 'Einsteiger')} | Versuche: {stats.get('attempts', 0)}")
            with col_bar:
                st.progress(score)
                
    st.markdown("---")
    col_start, col_empty = st.columns([1, 3])
    with col_start:
        # Der Button, der den User in den Chat leitet
        if st.button("➡️ Lern-Sitzung starten", use_container_width=True, type="primary"):
            st.session_state.current_page = "chat"
            st.rerun()
            
    st.stop() # Stoppt hier, damit der Chat nicht drunter gerendert wird

# --- 4. DYNAMISCHES SKRIPT VERZEICHNIS ---
verfuegbare_pdfs = []
if os.path.exists("studienmaterial"):
    
    # Hilfsfunktion, die Zahlen im Dateinamen als echte Zahlen erkennt
    def natural_sort_key(s):
        # Zerlegt den String in Text- und Zahlenblöcke und wandelt Zahlen in Integer um
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
        
    roh_pdfs = [f for f in os.listdir("studienmaterial") if f.endswith(".pdf")]
    
    # Hier wenden wir unseren neuen Sortier-Schlüssel an
    verfuegbare_pdfs = sorted(roh_pdfs, key=natural_sort_key)

# --- 5. SEITENLEISTE ---
with st.sidebar:
    st.title("📚 Studienmaterial")
    if verfuegbare_pdfs:
        # Wir behalten "Alle Foliensätze" als übergreifende Option an Position 0 im Menü bei
        pdf_auswahl = ["Alle Foliensätze"] + verfuegbare_pdfs
        
        # Durch index=1 zwingen wir das Dropdown, standardmäßig das erste aufsteigend
        # sortierte PDF anzuzeigen, statt auf "Alle Foliensätze" (index=0) zu springen.
        gewaehlter_foliensatz = st.selectbox("Aktuelle Referenz:", pdf_auswahl, index=1)
    else:
        gewaehlter_foliensatz = "Kein Skript gefunden"
        st.warning("Bitte lade PDFs in 'studienmaterial' hoch.")
        
    st.markdown("---")
    st.title("⚙️ System")
    st.info(f"Angemeldet als: **{st.session_state.username}**")
    
    # Neues Level-Dropdown für cleanere UI
    neues_level = st.selectbox("Schwierigkeitsgrad:", ["Einsteiger", "Solide", "Klausurniveau", "Maximal"], index=["Einsteiger", "Solide", "Klausurniveau", "Maximal"].index(st.session_state.level))
    if neues_level != st.session_state.level:
        st.session_state.level = neues_level
        st.rerun()
        
    ki_modus = st.radio("Sprachmodell:", ["Google (Gemini Base)", "Groq (RAG Highspeed)"])
    
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Abmelden", width="stretch"):
            st.session_state.username = ""
            st.rerun()
    with col_btn2:
        if st.button("Chat leeren", width="stretch"):
            st.session_state.messages = [] 
            database[st.session_state.username]["history"] = [] 
            save_data(database)
            st.rerun()

# --- 6. BACKEND WISSEN (Google & RAG für Groq) ---
@st.cache_resource
def get_google_files(filename):
    hochgeladene_dateien = []
    if google_client and filename != "Kein Skript gefunden":
        dateien_zum_laden = [f for f in os.listdir("studienmaterial") if f.endswith(".pdf")] if filename == "Alle Foliensätze" else [filename]
        
        for datei in dateien_zum_laden:
            file_path = os.path.join("studienmaterial", datei)
            hochgeladene_dateien.append(google_client.files.upload(file=file_path))
    return hochgeladene_dateien

@st.cache_data
def load_pdf_pages(filename):
    pages_dict = {}
    if filename != "Kein Skript gefunden":
        dateien_zum_laden = [f for f in os.listdir("studienmaterial") if f.endswith(".pdf")] if filename == "Alle Foliensätze" else [filename]
        
        global_page_count = 1
        for datei in dateien_zum_laden:
            file_path = os.path.join("studienmaterial", datei)
            try:
                with open(file_path, "rb") as f:
                    reader = pypdf.PdfReader(f)
                    for page in reader.pages:
                        text = page.extract_text()
                        if text: 
                            pages_dict[global_page_count] = f"[Aus {datei}]:\n{text}"
                            global_page_count += 1
            except Exception as e: st.error(f"PDF Lesefehler bei {datei}: {e}")
    return pages_dict

def get_rag_context(prompt, pages_dict, top_k=3):
    if not pages_dict: return ""
    stopwords = {"was", "ist", "der", "die", "das", "und", "oder", "ein", "eine", "wie", "erkläre", "bitte"}
    prompt_words = set(re.findall(r'\w{3,}', prompt.lower())) - stopwords
    if not prompt_words: return "\n".join(list(pages_dict.values())[:top_k])
    scored = []
    for p_num, text in pages_dict.items():
        score = sum(text.lower().count(w) for w in prompt_words)
        scored.append((score, p_num, text))
    scored.sort(key=lambda x: x[0], reverse=True)
    context = ""
    for score, p_num, text in scored[:top_k]:
        if score > 0: context += f"\n--- ABSCHNITT {p_num} ---\n{text}\n"
    return context if context else "Keine direkten Treffer auf den Folien gefunden."

# --- 7. SYSTEM PROMPT ---
SYSTEM_PROMPT = f"""Du bist EBWL-Coach, ein spezialisierter Lernbegleiter für Studierende der Einführung in die Betriebswirtschaftslehre an der RWTH Aachen.
Dein Auftrag ist nicht, einfache Antworten zu liefern, sondern echtes Verständnis aufzubauen. Du arbeitest auf Basis des offiziellen Vorlesungsmaterials.
Behandle den Nutzer als intelligenten Studierenden. Sei geduldig, fair und feiere Fortschritte nüchtern.

AKTUELLER FOLIENSATZ: {gewaehlter_foliensatz}

# Fachlicher Kontext (RWTH-Curriculum):
1. Grundbegriffe, konstitutive Entscheidungen (Rechtsform, Standort)
2. Funktionsbereiche: Beschaffung, Produktion, Marketing, Personal, Investition & Finanzierung
3. Organisation & Unternehmensführung
4. Rechnungswesen
5. Quantitative Methoden: Break-Even, optimale Bestellmenge, Kapitalwertmethode etc.

# Sprache und Stil:
- Sprache: Deutsch, Du-Form, durchgängig.
- Tonfall: Sachlich-warm. Niemals herablassend, niemals übertrieben enthusiastisch. Keine Floskeln wie "Klasse Frage!" oder "Du schaffst das!".
- Fachsprache: Verwende BWL-Terminologie präzise. Erkläre Fachbegriffe bei der ersten Verwendung in maximal einem Satz.
- Länge: So kurz wie möglich, so lang wie nötig. Eine Definition ist maximal zwei Sätze lang. Ein Lernfeedback drei Sätze. Vermeide Wall-of-Texts.
- Formatierung: Nutze Listen nur für Klarheit. Keine Emoji-Inflation – nutze sie sparsam zur Strukturierung (z.B. ✅ / ❌).

# Quellen und Wahrheitstreue:
- Stütze dich primär auf die bereitgestellten Folien und Auszüge.
- Gib bei Sachverhaltsaussagen, die aus den Quellen stammen, eine kompakte Quellenangabe an (z.B. "Laut den Vorlesungsfolien...").
- Erfinde keine Definitionen, Zahlen oder Autoren. Wenn du etwas nicht weißt, sage sachlich: "Das kann ich aus den vorliegenden Materialien nicht sicher beantworten."

# Didaktisches Vorgehen:
- Wenn der Nutzer einen Fehler macht, stelle eine Hilfsfrage, anstatt sofort die Lösung zu präsentieren. Führe ihn zur richtigen Antwort.
- Liefere keine Komplettlösungen für Rechenaufgaben sofort. Zerlege Aufgaben in Einzelschritte und frage den ersten Schritt ab.
"""

LADE_ZITATE = [
    "Skript wird analysiert...",
    "Klausurrelevanz wird geprüft...",
    "Lernfortschritt wird synchronisiert...",
    "Definitionen werden geladen..."
]

# --- 8. BENUTZEROBERFLÄCHE & CHAT LOGIK ---
if st.session_state.current_page == "chat":
    col_title, col_back = st.columns([4, 1])
    with col_title:
        st.title(f"Wolf of Wüllnerstraße | {st.session_state.username}")
    with col_back:
        st.write("") # Abstand
        if st.button("🔙 Zum Dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()

    # 8.1 Chat-Verlauf rendern
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]): 
            
            if message.get("is_flashcard"):
                # Prüfen, ob der Text Karteikarten-Schlüsselwörter enthält
                cards_found = re.search(r'(?:Vorderseite|Frage).*?\:', message["content"], re.IGNORECASE)
                
                if cards_found:
                    # Wir entfernen die unschönen Rohtext-Zeilen aus der Chat-Blase
                    clean_text = re.sub(r'(?i).*(?:Vorderseite|Frage|Rückseite|Antwort).*', '', message["content"])
                    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text).strip()
                    
                    # Intro-Satz des Bots rendern, falls vorhanden
                    if clean_text:
                        st.markdown(clean_text)
                    
                    # HTML 3D-Karten direkt darunter rendern
                    display_html_flashcards(message["content"])
                else:
                    # Fallback, falls der Bot komplett vom Format abweicht
                    st.markdown(message["content"])
            else:
                st.markdown(message["content"])
            
            if "pdf_data" in message:
                st.download_button(
                    label="📄 Lernzettel herunterladen (PDF)",
                    data=message["pdf_data"],
                    file_name=message["pdf_name"],
                    mime="application/pdf",
                    key=f"dl_btn_{i}"
                )

# 8.2 Das neue, cleane Aktions-Menü (ersetzt die rohen /befehle)
action = None
with st.popover("➕ Lern-Aktionen"):
    st.markdown("**Wähle einen Modus:**")
    if st.button("📝 Quiz starten", use_container_width=True): action = "/quiz"
    if st.button("🃏 Karteikarten generieren", use_container_width=True): action = "/karten"
    if st.button("📄 Lernzettel erstellen", use_container_width=True): action = "/zettel"
    if st.button("🎓 Klausur-Modus (Start/Auswerten)", use_container_width=True): action = "/klausur"
    if st.button("🤔 Sokratischer Modus", use_container_width=True): action = "/sokratisch"

# 8.3 Eingabe verarbeiten (Textfeld ODER Button-Klick)
prompt = st.chat_input("Frage zum Skript stellen...")
user_input = prompt or action

if user_input:
    # 1. Übersetzung für das UI (Damit der User nicht "/quiz" als eigene Nachricht sieht)
    display_texts = {
        "/quiz": "📝 Ich möchte ein kurzes Quiz starten.",
        "/karten": "🃏 Erstelle mir bitte Karteikarten zum aktuellen Thema.",
        "/zettel": "📄 Fasse das aktuelle Thema als kompakten Lernzettel zusammen.",
        "/klausur": "🎓 Lass uns den Klausur-Modus starten (bzw. auswerten, falls wir mittendrin sind).",
        "/sokratisch": "🤔 Aktiviere den sokratischen Modus für mich."
    }
    
    # Was der Nutzer im Chatverlauf sieht:
    ui_message = display_texts.get(user_input, user_input)
    st.session_state.messages.append({"role": "user", "content": ui_message})
    
    with st.chat_message("user"): 
        st.markdown(ui_message)

    # ==========================================
    # LOGIK-PARSER FÜR DIE BACKGROUND-BEFEHLE
    # ==========================================
    system_override = ""
    user_input_lower = user_input.strip().lower()

    if user_input_lower.startswith("/klausur"):
        if st.session_state.klausur_modus:
            st.session_state.klausur_modus = False
            st.session_state.active_mode = None
            system_override = "Bewerte nun die gesamte Klausur schrittweise. Vergib Teilpunkte (z.B. Formel korrekt 2/2, Rechenfehler 1/2) und stelle eine Schlussbewertung zusammen."
        else:
            st.session_state.klausur_modus = True
            st.session_state.active_mode = "klausur"
            system_override = "Starte den Klausur-Modus. Stelle eine vollständige, mehrstufige Klausuraufgabe (rechnen + argumentieren). Nenne NICHT die Lösung. Warte auf die erste Teilantwort des Nutzers."

    elif st.session_state.klausur_modus:
        system_override = "Der Nutzer bearbeitet gerade eine Klausuraufgabe. Führe ihn schrittweise durch die Aufgabe. Korrigiere fehlerhafte Teilaspekte, bevor du zum nächsten Schritt übergehst."

    elif user_input_lower.startswith("/zettel"):
        st.session_state.active_mode = None
        system_override = "Erstelle ein extrem kompaktes Cheatsheet zum Thema (Behandelte Themen in 2-4 Bullets, wichtige Formeln mit Variablen, identifizierte Schwächen falls zutreffend)."

    elif user_input_lower.startswith("/karten"):
        st.session_state.active_mode = None
        system_override = "Erstelle 3 kompakte Karteikarten zum Thema. Format: **Vorderseite (Frage):** ... | **Rückseite (Antwort):** ..."

    elif user_input_lower.startswith("/sokratisch"):
        st.session_state.active_mode = None
        system_override = "SOKRATISCHER MODUS: Gib KEINE direkten Antworten. Reagiere auf Wissensfragen mit einer Gegenfrage. Hinterfrage falsche Annahmen des Nutzers. Gib erst nach 3 Fehlversuchen eine geführte Erklärung ab."

    elif user_input_lower.startswith("/quiz"):
        st.session_state.active_mode = "quiz"
        system_override = "QUIZ-MODUS: Stelle genau eine Frage (Offen oder MC) passend zum aktuellen Skript. Warte auf die Antwort."

    # 🚨 NEU: Das heimliche Tracking-System für Nutzer-Antworten!
    if not user_input_lower.startswith("/") and st.session_state.active_mode in ["quiz", "klausur"]:
        system_override += "\n\nWICHTIG FÜR DAS TRACKING: Der Nutzer hat gerade eine inhaltliche Frage beantwortet. Bewerte diese Antwort! Hänge ganz am Ende deiner Ausgabe ZWINGEND folgenden unsichtbaren HTML-Tag an: (Wähle zutreffend 'richtig' oder 'falsch' und schätze die Metakognition/Sicherheit des Nutzers anhand seiner Formulierung auf 'sicher', 'unsicher' oder 'geraten'). Beispiel: "

    FINAL_SYSTEM_PROMPT = SYSTEM_PROMPT + f"\nAktuelles Schwierigkeitsniveau: {st.session_state.level}"

    if system_override:
        FINAL_SYSTEM_PROMPT += "\n\nSONDERBEFEHL FÜR DIESE NACHRICHT:\n" + system_override

    # ==========================================
    # KI-AUFRUF
    # ==========================================
    with st.chat_message("assistant"):
        with st.spinner(random.choice(LADE_ZITATE)):
            try:
                answer = ""
                # --- GROQ PFAD ---
                if "Groq" in ki_modus:
                    if not groq_client: st.error("Groq API Key fehlt!")
                    else:
                        pages_dict = load_pdf_pages(gewaehlter_foliensatz)
                        rag_context = get_rag_context(prompt if prompt else "Zusammenfassung", pages_dict)
                        groq_messages = [{"role": "system", "content": FINAL_SYSTEM_PROMPT + "\n\nAUSZUG AUS DEM SKRIPT:\n" + rag_context}]
                        for msg in st.session_state.messages[-8:]: groq_messages.append({"role": msg["role"], "content": msg["content"]})
                        
                        completion = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=groq_messages
                        )
                        answer = completion.choices[0].message.content

                # --- GOOGLE PFAD ---
                else:
                    if not google_client: st.error("Google API Key fehlt!")
                    else:
                        google_files = get_google_files(gewaehlter_foliensatz)
                        history_for_api = [msg["content"] for msg in st.session_state.messages[-8:]]
                        
                        full_contents = []
                        if google_files: full_contents.extend(google_files)
                        full_contents.extend(history_for_api)
                        
                        response = google_client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=full_contents,
                            config=types.GenerateContentConfig(system_instruction=FINAL_SYSTEM_PROMPT)
                        )
                        answer = response.text
                
                # --- ANTWORT VERARBEITEN ---
                if answer:
                    
                    # 🚨 NEU: EVAL-Tag auslesen und Lernfortschritt in Datenbank speichern
                    eval_match = re.search(r'', answer, re.IGNORECASE)
                    if eval_match:
                        is_correct = eval_match.group(1).lower() == "richtig"
                        confidence = eval_match.group(2).lower()
                        
                        # Datenbank wird befüllt!
                        record_learning_event(st.session_state.username, gewaehlter_foliensatz, is_correct, st.session_state.level, confidence)
                        
                        # Den unsichtbaren Tag aus der Nachricht löschen, damit der User ihn nicht sieht
                        answer = re.sub(r'', '', answer).strip()

                    # -- Ab hier bleibt dein Code gleich --
                    pdf_bytes = None
                    pdf_filename = None
                    if user_input.strip().lower().startswith("/zettel"):
                        pdf_bytes = generate_pdf_bytes(user_input, answer)
                        pdf_filename = f"Lernzettel_{gewaehlter_foliensatz.replace('.pdf','')}.pdf"

                    neue_nachricht = {"role": "assistant", "content": answer}
                    if pdf_bytes:
                        neue_nachricht["pdf_data"] = pdf_bytes
                        neue_nachricht["pdf_name"] = pdf_filename
                    if user_input.strip().lower().startswith("/karten"):
                        neue_nachricht["is_flashcard"] = True
                        
                    st.session_state.messages.append(neue_nachricht)

                    database[st.session_state.username]["history"] = st.session_state.messages
                    save_data(database)
                    
                    time.sleep(0.5)
                    st.rerun()

            except Exception as e:
                st.error(f"❌ Fehler bei der Server-Anfrage: {e}")
                            
                
