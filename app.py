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
from PIL import Image
from supabase import create_client, Client
import hashlib
import time

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
    
    # 🚨 FIX: Verhindert den "Not enough horizontal space"-Crash bei langen KI-Trennlinien
    safe_text = re.sub(r'[-_=#]{5,}', '---', safe_text)
    
    for line in safe_text.split("\n"):
        clean_line = line.encode('latin-1', 'replace').decode('latin-1').replace("?", "-")
        try:
            pdf.multi_cell(0, 6, clean_line)
        except Exception:
            # Fallback: Falls ein einzelnes "Wort" das Blatt sprengt, wird es abgeschnitten
            pdf.multi_cell(0, 6, clean_line[:80] + " [...]")
            
    return pdf.output()

# ==========================================
# 🃏 HELPER FÜR INTERAKTIVE KARTEIKARTEN (PREMIUM UI)
# ==========================================
def display_html_flashcards(ai_text):
    # Regex bleibt identisch robust
    cards = re.findall(r'(?:Vorderseite|Frage).*?\:\s*([^|\n]+)(?:\s*\|\s*|\n+)(?:Rückseite|Antwort).*?\:\s*([^\n]+)', ai_text, re.IGNORECASE)
    if not cards:
        cards = re.findall(r'\*\*(?:Vorderseite|Frage).*?\*\*\s*([^|\n]+)(?:\s*\|\s*|\n+)\*\*(?:Rückseite|Antwort).*?\*\*\s*([^\n]+)', ai_text, re.IGNORECASE)

    if cards:
        cards_html = ""
        for i, (front, back) in enumerate(cards):
            front_text = front.replace("**", "").strip()
            back_text = back.replace("**", "").strip()
            
            # 🚨 FIX: Eine garantiert einmalige ID für jede Karte generieren
            unique_id = f"card-{random.randint(1000000, 9999999)}-{i}"
            
            # Premium HTML-Struktur mit Icons und einzigartiger ID
            cards_html += f"""
            <div class="card-box">
                <input type="checkbox" id="{unique_id}" class="flip-checkbox" style="display:none;">
                <label for="{unique_id}" class="flip-card">
                    <div class="flip-card-inner">
                        <div class="flip-card-front">
                            <div class="card-icon">❓</div>
                            <div class="card-header">FRAGE</div>
                            <div class="card-content">{front_text}</div>
                            <div class="card-hint">Klicken zum Drehen</div>
                        </div>
                        <div class="flip-card-inner-back">
                            <div class="card-icon">💡</div>
                            <div class="card-header" style="color: #57AB27;">ANTWORT</div>
                            <div class="card-content">{back_text}</div>
                        </div>
                    </div>
                </label>
            </div>
            """
            
        # Premium CSS mit RWTH-Farben und flüssigen 3D-Schatten
        full_html = f"""
        <style>
            .container {{ display: flex; flex-wrap: wrap; gap: 25px; justify-content: center; font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; }}
            .card-box {{ display: inline-block; perspective: 1200px; }}
            .flip-card {{ display: block; width: 300px; height: 210px; cursor: pointer; }}
            .flip-card-inner {{ position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s cubic-bezier(0.4, 0.2, 0.2, 1); transform-style: preserve-3d; }}
            .flip-card-front, .flip-card-inner-back {{ position: absolute; width: 100%; height: 100%; backface-visibility: hidden; -webkit-backface-visibility: hidden; border-radius: 16px; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: 0 8px 25px rgba(0,0,0,0.08); }}
            .flip-card-front {{ background: linear-gradient(135deg, #00549F 0%, #003a6d 100%); color: #ffffff; border: none; }}
            .flip-card-inner-back {{ background: #ffffff; color: #1e293b; transform: rotateY(180deg); border: 3px solid #57AB27; }}
            .card-header {{ font-size: 12px; font-weight: 800; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1.5px; opacity: 0.9; }}
            .flip-card-front .card-header {{ color: #e2e8f0; }}
            .card-content {{ font-size: 15px; font-weight: 600; line-height: 1.4; overflow-y: auto; flex-grow: 1; display: flex; align-items: center; justify-content: center; }}
            .card-icon {{ font-size: 26px; margin-bottom: 5px; }}
            .card-hint {{ font-size: 11px; font-weight: 500; opacity: 0.6; margin-top: auto; text-transform: uppercase; letter-spacing: 1px; }}
            .card-content::-webkit-scrollbar {{ display: none; }}
            .flip-checkbox:checked + .flip-card .flip-card-inner {{ transform: rotateY(180deg); }}
            /* Der neue Hover-Effekt (Karte hebt sich an) */
            .flip-card:hover .flip-card-inner {{ box-shadow: 0 15px 35px rgba(0,84,159,0.25); transform: translateY(-5px); transition: all 0.3s ease; }}
            .flip-checkbox:checked + .flip-card:hover .flip-card-inner {{ transform: rotateY(180deg) translateY(-5px); }}
        </style>
        <div class="container">{cards_html}</div>
        """
        st.html(f'<div style="min-height: 250px;">{full_html}</div>')

# ==========================================
# 🎨 PREMIUM HTML/CSS DASHBOARD GENERATOR (OBSIDIAN THEME)
# ==========================================
def render_premium_dashboard(username, total_q, accuracy, level, progress_data):
    
    css = """
    <style>
        .kpi-card {
            flex: 1; min-width: 200px; 
            background: var(--secondary-background-color); 
            border-radius: 16px; padding: 24px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.4); 
            border: 1px solid rgba(255, 255, 255, 0.07);
            transition: transform 0.2s ease;
        }
        .kpi-card:hover { transform: translateY(-3px); border-color: rgba(255,255,255,0.15); }
        
        .dash-card {
            background: var(--secondary-background-color); 
            border-radius: 16px; padding: 20px; 
            box-shadow: 0 8px 20px rgba(0,0,0,0.3); 
            border: 1px solid rgba(255, 255, 255, 0.07);
            transition: all 0.3s ease;
        }
        .dash-card:hover {
            transform: translateY(-4px); 
            box-shadow: 0 15px 30px rgba(0,0,0,0.5);
            border-color: var(--primary-color);
        }
        
        .progress-track {
            width: 100%; background-color: rgba(0,0,0,0.3); 
            border-radius: 8px; height: 8px; margin-bottom: 15px; overflow: hidden; 
            border: inset 1px rgba(0,0,0,0.5);
        }
        .kpi-label { color: var(--text-color); opacity: 0.6; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
        .kpi-value { color: var(--text-color); font-size: 36px; font-weight: 800; margin-top: 8px; }
    </style>
    """

    kpi_html = f"""
    <div style="display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap;">
        <div class="kpi-card" style="border-top: 4px solid var(--primary-color);">
            <div class="kpi-label">Beantwortete Fragen</div>
            <div class="kpi-value">{total_q}</div>
        </div>
        <div class="kpi-card" style="border-top: 4px solid #10B981;">
            <div class="kpi-label">Trefferquote</div>
            <div class="kpi-value">{accuracy}<span style="font-size: 20px; opacity: 0.5;"> %</span></div>
        </div>
        <div class="kpi-card" style="border-top: 4px solid #8B5CF6;">
            <div class="kpi-label">Aktuelles Cap</div>
            <div class="kpi-value">{level}</div>
        </div>
    </div>
    """

    cards_html = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-bottom: 40px;">'
    
    if not progress_data:
        cards_html += """
        <div style="grid-column: 1 / -1; background: var(--secondary-background-color); border-radius: 16px; padding: 40px; text-align: center; border: 1px dashed rgba(255,255,255,0.2);">
            <h3 style="color: var(--text-color); margin: 0; opacity: 0.8;">Noch keine Daten vorhanden</h3>
            <p style="color: var(--text-color); opacity: 0.6; font-size: 14px;">Starte deine erste Sitzung, um deinen Fortschritt hier zu sehen.</p>
        </div>"""
    else:
        for pdf_name, stats in progress_data.items():
            
            # 🚨 HIER LAG DER FEHLER: Diese Zeilen fehlten vermutlich bei dir!
            score = calculate_progress(stats)
            score_percent = int(score * 100)
            clean_name = pdf_name.replace(".pdf", "").replace("_", " ")
            
            bar_color = "#10B981" if score_percent >= 80 else ("#F59E0B" if score_percent >= 50 else "#EF4444")
            
            cards_html += f"""
            <div class="dash-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
                    <div style="font-weight: 600; color: var(--text-color); font-size: 16px; line-height: 1.3;">{clean_name}</div>
                    <div style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; color: {bar_color};">{score_percent}%</div>
                </div>
                
                <div class="progress-track">
                    <div style="width: {score_percent}%; background-color: {bar_color}; height: 100%; border-radius: 8px; transition: width 1s ease-in-out; box-shadow: 0 0 10px {bar_color};"></div>
                </div>
                
                <div style="display: flex; justify-content: space-between; color: var(--text-color); opacity: 0.6; font-size: 12px;">
                    <span>Versuche: {stats.get('attempts', 0)}</span>
                    <span>Level: <b style="opacity: 0.9;">{stats.get('max_level', 'Einsteiger')}</b></span>
                </div>
            </div>
            """
    cards_html += '</div>'

    st.html(css + kpi_html + cards_html)

# --- SUPABASE INITIALISIEREN ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

import json

# --- DATEN LADEN ---
def load_user_data(username):
    try:
        response = supabase.table("savegames").select("*").eq("username", username).execute()
        if len(response.data) > 0:
            user_data = response.data[0]
                
            # Wir geben die Daten nur zurück, ohne den Streamlit-Speicher zu manipulieren!
            return user_data
        else:
            return {"username": username, "score": 0.0, "total_questions": 0, "level": "Einsteiger"} 
    except Exception as e:
        st.error(f"Datenbank-Fehler beim Laden: {e}")
        return None

# --- DATEN SPEICHERN ---
def save_user_data(username, new_data):
    try:
        new_data["username"] = username
        
        # Den aktuellen Chatverlauf an das Speicherpaket anhängen
        if "messages" in st.session_state:
            new_data["chat_history"] = st.session_state.messages
            
        supabase.table("savegames").upsert(new_data).execute()
    except Exception as e:
        st.error(f"Datenbank-Fehler beim Speichern: {e}")

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
    """Speichert eine beantwortete Frage als Datenpunkt direkt in der Cloud ab."""
    # 1. Aktuelle Daten aus der Cloud holen
    user_data = load_user_data(username)
    if not user_data: return
    
    # 2. Progress-Dictionary initialisieren, falls noch leer
    if "progress" not in user_data or not user_data["progress"]:
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
        levels = ["Einsteiger", "Solide", "Klausurniveau", "Maximal"]
        current_idx = levels.index(p_data["max_level"]) if p_data["max_level"] in levels else 0
        new_idx = levels.index(level) if level in levels else 0
        
        if new_idx > current_idx:
            p_data["max_level"] = level
            
    conf_map = {"sicher": 1.0, "unsicher": 0.75, "geraten": 0.4}
    val = conf_map.get(confidence_str.lower(), 1.0)
    
    p_data["avg_confidence"] = ((p_data["avg_confidence"] * (p_data["attempts"] - 1)) + val) / p_data["attempts"]
    p_data["last_update"] = time.time()
    
    # 3. Aktualisierte Daten wieder in die Cloud schießen
    save_user_data(username, user_data)

# Initialisierung der Session States
if "current_page" not in st.session_state: st.session_state.current_page = "login"
if "username" not in st.session_state: st.session_state.username = ""
if "messages" not in st.session_state: st.session_state.messages = []
if "level" not in st.session_state: st.session_state.level = "Solide"
if "klausur_modus" not in st.session_state: st.session_state.klausur_modus = False
if "active_mode" not in st.session_state: st.session_state.active_mode = None
# 🚨 NEU: Der Schlüssel, um den Bilder-Uploader zu leeren
if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0

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

# --- 3. STARTBILDSCHIRM & LOGIN ---
if st.session_state.current_page == "login":
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("") 
        st.markdown("<h1 style='text-align: center; color: var(--primary-color);'>Wolf of Wüllnerstraße</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; margin-top: -15px;'>RWTH Aachen | Interaktiver Tutor</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        # 1. Die doppelten Felder sind weg! Nur noch Name und persönliches Passwort.
        username_input = st.text_input("Wie lautet dein Benutzername?")
        password_input = st.text_input("Wähle ein Passwort (oder logge dich ein):", type="password")
        
        st.write("") 
        if st.button("Anmelden", use_container_width=True, type="primary"):
            if not username_input or not password_input: 
                st.error("Bitte gib einen Namen und ein Passwort ein!")
            else:
                # Passwort kryptografisch verschlüsseln (Hashing)
                hashed_pw = hashlib.sha256(password_input.encode()).hexdigest()
                
                user_data = load_user_data(username_input)
                
                if user_data and user_data.get("password_hash"):
                    if user_data["password_hash"] == hashed_pw:
                        st.session_state.username = username_input
                        st.session_state.messages = user_data.get("chat_history", [])
                        st.session_state.current_page = "dashboard"
                        st.rerun()
                    else:
                        st.error("❌ Dieser Name ist bereits vergeben oder dein Passwort ist falsch!")
                else:
                    if user_data is None: user_data = {}
                    user_data["password_hash"] = hashed_pw
                    save_user_data(username_input, user_data)
                    
                    st.success("Account erfolgreich erstellt! Logge ein...")
                    st.session_state.username = username_input
                    st.session_state.messages = []
                    st.session_state.current_page = "dashboard"
                    import time
                    time.sleep(1)
                    st.rerun()

        st.write("")
        st.write("")

        # 2. Die versteckte Admin-Hintertür für euch
        with st.expander("🛠️ Admin-Bereich (Passwörter verwalten)"):
            admin_pw = st.text_input("Admin-Masterpasswort:", type="password")
            
            # Hier nutzen wir euer altes Zugangspasswort als geheimen Admin-Schlüssel
            if admin_pw == st.secrets.get("ADMIN_PASSWORD", "fallback_passwort_123"):
                st.success("Admin-Zugriff gewährt!")
                target_user = st.text_input("Nutzername des Kommilitonen:")
                new_user_pw = st.text_input("Neues Passwort vergeben:", type="password")
                
                if st.button("Passwort überschreiben"):
                    if not target_user or not new_user_pw:
                        st.warning("Bitte beide Felder ausfüllen.")
                    else:
                        target_data = load_user_data(target_user)
                        # Prüfen, ob der Nutzer überhaupt existiert
                        if target_data and target_data.get("password_hash"):
                            # Neues Passwort hashen und speichern
                            target_data["password_hash"] = hashlib.sha256(new_user_pw.encode()).hexdigest()
                            save_user_data(target_user, target_data)
                            st.success(f"✅ Das Passwort für '{target_user}' wurde erfolgreich geändert!")
                        else:
                            st.error("❌ Nutzer nicht gefunden!")
            elif admin_pw:
                st.error("Falsches Admin-Passwort!")

    st.stop()

# --- 5. SEITENLEISTE ---
with st.sidebar:
    # 🚨 FIX: Permanenter Navigations-Button am Kopf der Sidebar (nur im Chat sichtbar)
    if st.session_state.current_page == "chat":
        if st.button("📊 Zurück zum Dashboard", use_container_width=True):
            st.session_state.current_page = "dashboard"
            st.rerun()
        st.markdown("---")

    # Cleanere Überschriften via Markdown statt st.title()
    st.markdown("### 📋 Studienmaterial")
    if verfuegbare_pdfs:
        pdf_auswahl = ["Alle Foliensätze"] + verfuegbare_pdfs
        gewaehlter_foliensatz = st.selectbox("Aktuelle Referenz:", pdf_auswahl, index=1)
    else:
        gewaehlter_foliensatz = "Kein Skript gefunden"
        st.warning("Bitte lade PDFs in 'studienmaterial' hoch.")
        
    st.markdown("---")
    st.markdown("### ⚙️ System")
    
    # Cleanere Darstellung des Benutzers ohne klobige blaue Infobox
    st.markdown(f"Nutzer: **{st.session_state.username}**")
    
    neues_level = st.selectbox("Schwierigkeitsgrad:", ["Einsteiger", "Solide", "Klausurniveau", "Maximal"], index=["Einsteiger", "Solide", "Klausurniveau", "Maximal"].index(st.session_state.level))
    if neues_level != st.session_state.level:
        st.session_state.level = neues_level
        st.rerun()
        
    ki_modus = st.radio("Sprachmodell:", ["Google (Gemini Base)", "Groq (RAG Highspeed)"])
    
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Abmelden", use_container_width=True):
            st.session_state.username = ""
            st.session_state.current_page = "login" # 🚨 NEU: Wirft den Nutzer zurück zum Login
            st.rerun()
    with col_btn2:
        if st.button("Chat leeren", use_container_width=True):
            # 1. Chat im aktuellen Streamlit-Fenster leeren
            st.session_state.messages = [] 
            
            # 2. Aktuelle Daten aus der Cloud holen und leeren Chat überschreiben
            user_data = load_user_data(st.session_state.username)
            if user_data:
                save_user_data(st.session_state.username, user_data)
                
            st.rerun()

# --- 3.5 LERN-DASHBOARD ---
if st.session_state.current_page == "dashboard":
    st.title("📊 Dein Lern-Dashboard")
    st.markdown(f"Willkommen zurück, **{st.session_state.username}**. Hier ist dein aktueller Wissensstand basierend auf deinen Antworten und deiner Selbsteinschätzung.")
    st.write("")
    
  # Echte Nutzerdaten abrufen
    user_data = load_user_data(st.session_state.username) or {}
    
    # 🚨 DER FIX: "or {}" fängt das leere Datenbankfeld sicher ab
    progress_data = user_data.get("progress") or {}
    
    # KPIs berechnen
    total_questions = sum(p.get("attempts", 0) for p in progress_data.values())
    total_correct = sum(p.get("correct", 0) for p in progress_data.values())
    global_accuracy = int((total_correct / total_questions * 100)) if total_questions > 0 else 0
    
    # 🎨 HIER KOMMT DIE MAGIE: Unser Premium-Dashboard rendern
    render_premium_dashboard(
        st.session_state.username, 
        total_questions, 
        global_accuracy, 
        st.session_state.level, 
        progress_data
    )

    # ---------------------------------------------------------
    # 🔍 DETAILLIERTE FORMEL-ANALYSE & ECHTER SIMULATOR (Unverändert, aber optisch eingebettet)
    # ---------------------------------------------------------
    with st.expander("🔍 Simulator: Wie wirkt sich deine nächste Antwort aus?"):
        st.info("Dieser Simulator lädt deinen **echten, aktuellen Lernstand** für das ausgewählte Kapitel. Er zeigt dir exakt, wie sich dein Gesamtfortschritt verändert, wenn du jetzt eine weitere Frage beantwortest.")
        
        bekannte_themen = list(progress_data.keys()) if progress_data else ["Bisher keine Daten"]
        sim_thema = st.selectbox("Wähle das Kapitel für die Simulation:", bekannte_themen)
        
        # Echte Daten für das ausgewählte Modul laden
        p_data = progress_data.get(sim_thema, {"attempts": 0, "correct": 0, "avg_confidence": 1.0, "max_level": "Einsteiger"})
        
        current_attempts = p_data.get("attempts", 0)
        current_correct = p_data.get("correct", 0)
        current_conf = p_data.get("avg_confidence", 1.0)
        current_max_level = p_data.get("max_level", "Einsteiger")
        
        level_weights = {"Einsteiger": 0.4, "Solide": 0.75, "Klausurniveau": 1.0, "Maximal": 1.0}
        curr_score = 0.0
        if current_attempts > 0:
            curr_score = (current_correct / current_attempts) * level_weights.get(current_max_level, 0.4) * current_conf

        st.markdown(f"**Aktueller Stand ({sim_thema}):** {current_attempts} Versuche | {current_correct} Richtig | Cap: {current_max_level}")
        st.markdown("---")
        
        sim_col1, sim_col2, sim_col3 = st.columns(3)
        with sim_col1:
            sim_correct = st.radio("Ergebnis der nächsten Antwort:", ["Richtig", "Falsch"])
        with sim_col2:
            sim_level = st.selectbox("Gespieltes Level:", ["Einsteiger", "Solide", "Klausurniveau", "Maximal"], index=["Einsteiger", "Solide", "Klausurniveau", "Maximal"].index(current_max_level) if current_max_level in ["Einsteiger", "Solide", "Klausurniveau", "Maximal"] else 0)
        with sim_col3:
            sim_conf = st.selectbox("Eigene Sicherheit:", ["Sicher (1.0)", "Unsicher (0.75)", "Geraten (0.4)"])
            
        new_attempts = current_attempts + 1
        new_correct = current_correct + (1 if sim_correct == "Richtig" else 0)
        
        levels_list = ["Einsteiger", "Solide", "Klausurniveau", "Maximal"]
        curr_idx = levels_list.index(current_max_level) if current_max_level in levels_list else 0
        sim_idx = levels_list.index(sim_level)
        new_max_level = sim_level if (sim_correct == "Richtig" and sim_idx > curr_idx) else current_max_level
        
        conf_val = {"Sicher (1.0)": 1.0, "Unsicher (0.75)": 0.75, "Geraten (0.4)": 0.4}[sim_conf]
        new_conf = ((current_conf * current_attempts) + conf_val) / new_attempts if new_attempts > 0 else conf_val
        
        new_score = (new_correct / new_attempts) * level_weights.get(new_max_level, 0.4) * new_conf
        
        st.markdown("#### Resultierender Gesamtfortschritt:")
        res_col1, res_col2 = st.columns([1, 3])
        delta_val = (new_score - curr_score) * 100
        
        with res_col1:
            st.metric(label="Dein neuer Stand", value=f"{int(new_score * 100)} %", delta=f"{delta_val:+.1f} %")
        with res_col2:
            st.progress(min(1.0, new_score))
            
    st.write("") 

    # 3. Der Action-Button (Clean, Fokussiert & Volle Breite am Seitenende)
    if st.button("🚀 Lern-Sitzung starten", use_container_width=True, type="primary"):
        st.session_state.current_page = "chat"
        st.rerun()

    st.stop()  # Verhindert, dass der Chat-Teil auf dem Dashboard gerendert wird

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

def get_rag_context(prompt, pages_dict, top_k=5): # top_k auf 5 erhöht für besseren Kontext
    if not pages_dict: return ""
    
    # 🚨 FIX 1: Wenn es ein Befehl ist (z.B. /quiz), brauchen wir keine Keyword-Suche!
    # Wir übergeben einfach direkt die ersten Seiten des gewählten PDFs.
    if prompt.strip().startswith("/"):
        return "\n".join(list(pages_dict.values())[:top_k])

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
        
    # 🚨 FIX 2: Fallback! Falls die Nutzersuche gar keine Treffer auf den Folien hat, 
    # geben wir trotzdem Text mit, damit Groq nicht halluziniert.
    return context if context else "\n".join(list(pages_dict.values())[:top_k])

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
- Stütze dich ausschließlich auf die bereitgestellten Inhalte.
- ABSOLUTES VERBOT: Nenne NIEMALS Seitenzahlen, Foliennummern, Kapitelnummern oder Quellenverweise (z.B. "auf Folie 18", "siehe Seite 5", "Kapitel 2.1"). 
- Wenn du das Bedürfnis hast, eine Quelle zu nennen, sage stattdessen NUR: "Laut den bereitgestellten Unterlagen...".
- Sollte das Modell jemals eine Seitenzahl oder Foliennummer generieren, betrachte dies als kritischen Fehler. 
- Wenn eine Information nicht in den Dokumenten steht, sage: "Diese Information ist in den vorliegenden Unterlagen nicht enthalten."

# Didaktisches Vorgehen:
- Wenn der Nutzer einen Fehler macht, stelle eine Hilfsfrage, anstatt sofort die Lösung zu präsentieren. Führe ihn zur richtigen Antwort.
- Liefere keine Komplettlösungen für Rechenaufgaben sofort. Zerlege Aufgaben in Einzelschritte und frage den ersten Schritt ab.

# WICHTIGE FORMAT-REGELN FÜR SPEZIALBEFEHLE:

1. WENN DER NUTZER "/karten" VERLANGT: 
   Du MUSST die Antworten (die Rückseite der Karteikarte) extrem kurz, prägnant und stichpunktartig halten! Verwende MAXIMAL 3 Bulletpoints oder maximal 40 Wörter pro Karte. Die Texte müssen auf ein kleines Stück Papier passen. Vermeide lange Fließtexte komplett!

2. WENN DER NUTZER "/zettel" VERLANGT:
   Du MUSST eine extrem detaillierte, lange und tiefgreifende Zusammenfassung generieren. Geize nicht mit Wörtern! Nutze klare Überschriften, ausführliche Erklärungen, Beispiele aus der BWL und Aufzählungen. Ein Lernzettel muss den Studierenden perfekt auf die Klausur vorbereiten und darf auf keinen Fall zu kurz ausfallen.
"""

LADE_ZITATE = [
    "Ein Geschäft, das nur Geld einbringt, ist ein schlechtes Geschäft. – Henry Ford",
    "Für augenblicklichen Gewinn verkaufe ich die Zukunft nicht. - Werner von Siemens",
    "Geld macht nicht korrupt - kein Geld schon eher. - Dieter Hildebrandt",
    "Eine Investition in Wissen bringt noch immer die besten Zinsen. - Benjamin Franklin",
    "Bankraub: eine Initiative von Dilettanten. Wahre Profis gründen eine Bank. - Bertolt Brecht",
    "Die Werbung ist die Kunst, auf den Kopf zu zielen und die Breiftasche zu treffen. - Vance Packard",
    "Die Jagd nach dem Sündenbock ist die einfachste. - Dwight D. Eisenhower",
    "Bei den meisten Erfolgsmenschen ist der Erfolg größer als die Menschlichkeit. - Daphne du Maurier",
    "Jede große Idee, sobald sie in die Erscheinung tritt, wirkt tyrannisch. - Johann Wolfgang von Goethe",
    "Lach nie über die Dummheit der anderen. Sie ist deine Chance. - Winston Churchill",
    "Das Geld zieht nur den Eigennutz an und verführt stets unwiderstehlich zum Missbrauch. - Albert Einstein",
    "Nicht Sieg sollte der Sinn der Diskussion sein, sondern Gewinn. - Joseph Joubert"
]

# --- 8. BENUTZEROBERFLÄCHE & CHAT LOGIK ---
if st.session_state.current_page == "chat":
    # Der Dashboard-Button hier oben fällt komplett weg, da er jetzt fest in der Sidebar verankert ist!
    st.title(f"Wolf of Wüllnerstraße | {st.session_state.username}")
    st.markdown("---")

    # 8.1 Chat-Verlauf rendern
    for i, message in enumerate(st.session_state.messages):
        # 🚨 FIX: Filigrane, minimalistische Avatare statt bunter Comic-Blöcke
        avatar_icon = "👤" if message["role"] == "user" else "🎓"
        
        with st.chat_message(message["role"], avatar=avatar_icon): 
            if message.get("is_flashcard"):
                cards_found = re.search(r'(?:Vorderseite|Frage).*?\:', message["content"], re.IGNORECASE)
                if cards_found:
                    clean_text = re.sub(r'(?i).*(?:Vorderseite|Frage|Rückseite|Antwort).*', '', message["content"])
                    clean_text = re.sub(r'[-_*]{3,}', '', clean_text)
                    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text).strip()
                    if clean_text:
                        st.markdown(clean_text)
                    display_html_flashcards(message["content"])
                else:
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

    # 8.2 Das bereinigte Aktions-Menü (Ohne Emoji-Salad in den Buttons)
    action = None
    uploaded_image = None 

    with st.popover("➕ Lern-Aktionen & Upload"):
        st.markdown("**Wähle einen Modus:**")
        if st.button("Quiz starten", use_container_width=True): action = "/quiz"
        
        st.markdown("---")
        karten_anzahl = st.slider("Anzahl Karteikarten:", min_value=2, max_value=8, value=3)
        if st.button(f"Karteikarten generieren ({karten_anzahl})", use_container_width=True): 
            action = f"/karten {karten_anzahl}"
        st.markdown("---")
        
        uploaded_image = st.file_uploader("Bild / Skizze hochladen:", type=["png", "jpg", "jpeg"], key=st.session_state.uploader_key)
        
        st.markdown("---")
        if st.button("Lernzettel erstellen", use_container_width=True): action = "/zettel"
        if st.button("Klausur-Modus (Start/Auswerten)", use_container_width=True): action = "/klausur"
        if st.button("Sokratischer Modus", use_container_width=True): action = "/sokratisch"

# 8.3 Eingabe verarbeiten (Textfeld ODER Button-Klick ODER Kachel)
prompt = None

if gewaehlter_foliensatz != "Kein Foliensatz gewählt":
    prompt = st.chat_input(f"Frage zu {gewaehlter_foliensatz} stellen...")
    
    # MAGIC UX: Kacheln anzeigen, wenn der Chat noch komplett leer ist
    if len(st.session_state.messages) == 0:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: gray;'>Womit wollen wir heute starten?</h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 3x2 Raster für die 6 Kacheln
        col1, col2, col3 = st.columns(3)
        col4, col5, col6 = st.columns(3)
        
        if col1.button("🎯 Quiz starten", use_container_width=True): 
            prompt = "/quiz Prüfe mein Wissen!"
        if col2.button("📇 Karteikarten generieren", use_container_width=True): 
            prompt = "/karten Erstelle mir Karteikarten zum Foliensatz."
        if col3.button("📝 Lernzettel erstellen", use_container_width=True): 
            prompt = "/zettel Fasse die wichtigsten Kernkonzepte zusammen."
        
        st.write("") # Abstandhalter zwischen den Reihen
        
        if col4.button("📊 Erkläre den Break-Even-Point", use_container_width=True): 
            prompt = "Erkläre mir den Break-Even-Point einfach und mit einem Beispiel bezogen auf das Skript."
        if col5.button("🤔 Was ist die ABC-Analyse?", use_container_width=True): 
            prompt = "Was ist die ABC-Analyse und wofür braucht man sie in der BWL?"
        if col6.button("💡 Klausur-Tipp geben", use_container_width=True): 
            prompt = "Gib mir eine typische Klausur-Transferaufgabe basierend auf diesem Foliensatz."
            
else:
    # Eure Sicherheits-Sperre bleibt voll erhalten, wenn kein PDF da ist:
    prompt = st.chat_input("Wähle zuerst einen Foliensatz aus, um zu chatten...", disabled=True)

# Hier läuft jetzt alles zusammen: Egal ob Tastatur, Popover-Menü oder Start-Kachel!
user_input = prompt or action

if user_input or uploaded_image:

    # Fallback, falls nur ein Bild aber kein Text kommt
    if uploaded_image and not user_input:
        user_input = "Bitte analysiere meine hochgeladene Lösung/Skizze anhand der aktuellen Referenz."
    # 1. Übersetzung für das UI (Damit der User nicht "/quiz" als eigene Nachricht sieht)
    # 🚨 NEU: Dynamische Anzeige für den Chatverlauf
    if user_input.startswith("/karten"):
        anzahl = user_input.split()[1] if len(user_input.split()) > 1 else "3"
        ui_message = f"🃏 Erstelle mir bitte {anzahl} Karteikarten zum aktuellen Thema."
    else:
        display_texts = {
            "/quiz": "📝 Ich möchte ein kurzes Quiz starten.",
            "/zettel": "📄 Fasse das aktuelle Thema als kompakten Lernzettel zusammen.",
            "/klausur": "🎓 Lass uns den Klausur-Modus starten (bzw. auswerten, falls wir mittendrin sind).",
            "/sokratisch": "🤔 Aktiviere den sokratischen Modus für mich."
        }
        ui_message = display_texts.get(user_input, user_input)
    
    # Visueller Indikator für den User, dass ein Bild angehängt wurde
    if uploaded_image:
        ui_message = f"📸 *[Bild angehängt]*\n\n" + ui_message
    
   # Was der Nutzer im Chatverlauf sieht (Live-Injektion):
    st.session_state.messages.append({"role": "user", "content": ui_message})
    
    # 🚨 FIX: Auch hier den edlen Avatar übergeben
    with st.chat_message("user", avatar="👤"): 
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
        # Anzahl auslesen (Standard: 3)
        anzahl = user_input_lower.split()[1] if len(user_input_lower.split()) > 1 else "3"
        system_override = f"Erstelle exakt {anzahl} kompakte Karteikarten zum Thema. Format: **Vorderseite (Frage):** ... | **Rückseite (Antwort):** ..."

    elif user_input_lower.startswith("/sokratisch"):
        st.session_state.active_mode = None
        system_override = "SOKRATISCHER MODUS: Gib KEINE direkten Antworten. Reagiere auf Wissensfragen mit einer Gegenfrage. Hinterfrage falsche Annahmen des Nutzers. Gib erst nach 3 Fehlversuchen eine geführte Erklärung ab."

    elif user_input_lower.startswith("/quiz"):
        st.session_state.active_mode = "quiz"
        system_override = (
            "QUIZ-MODUS: Stelle genau eine Frage (Offen oder MC) passend zum aktuellen Skript. "
            "\n\nWICHTIGE FORMATIERUNG FÜR MC-FRAGEN: Verwende ZWINGEND eine Aufzählung mit Spiegelstrichen! "
            "Halte dich exakt an dieses Template:\n\n"
            "[Deine Frage]\n\n"
            "- **A)** [Option 1]\n"
            "- **B)** [Option 2]\n"
            "- **C)** [Option 3]\n"
            "- **D)** [Option 4]\n\n"
            "Schreibe die Optionen unter keinen Umständen als zusammenhängenden Fließtext in eine einzige Zeile."
        )

    # 🚨 NEU: Das heimliche Tracking-System für Nutzer-Antworten!
    if not user_input_lower.startswith("/") and st.session_state.active_mode in ["quiz", "klausur"]:
        system_override += "\n\nWICHTIG FÜR DAS TRACKING: Der Nutzer hat gerade eine inhaltliche Frage beantwortet. Bewerte diese Antwort! Hänge ganz am Ende deiner Ausgabe ZWINGEND folgenden unsichtbaren HTML-Tag an: <eval ERGEBNIS SICHERHEIT>. (Wähle zutreffend 'richtig' oder 'falsch' und schätze die Metakognition/Sicherheit des Nutzers anhand seiner Formulierung auf 'sicher', 'unsicher' oder 'geraten'). Beispiel: <eval richtig sicher>"

    FINAL_SYSTEM_PROMPT = SYSTEM_PROMPT + f"\nAktuelles Schwierigkeitsniveau: {st.session_state.level}"

    if system_override:
        FINAL_SYSTEM_PROMPT += "\n\nSONDERBEFEHL FÜR DIESE NACHRICHT:\n" + system_override

    # ==========================================
    # KI-AUFRUF
    # ==========================================
   # 🚨 FIX: Auch hier den Coach-Avatar vergeben
    with st.chat_message("assistant", avatar="🎓"):
        with st.spinner(random.choice(LADE_ZITATE)):
            try:
                answer = ""
                # 🚨 NEU: Wenn ein Bild hochgeladen wurde, zwingen wir das System auf Gemini (Vision)
                if "Groq" in ki_modus and not uploaded_image:
                # --- GROQ PFAD ---
                    if not groq_client: st.error("Groq API Key fehlt!")
                    else:
                        pages_dict = load_pdf_pages(gewaehlter_foliensatz)
                        
                        # 🚨 FIX 3: user_input übergeben, damit die Funktion die Befehle (/quiz etc.) erkennt
                        rag_context = get_rag_context(user_input, pages_dict, top_k=5)
                        
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
                        if uploaded_image:
                            img = Image.open(uploaded_image)
                            full_contents.append(img)
                            # 🚨 NEU: Strenge Anti-Halluzinations-Regel aus eurem Konzept!
                            FINAL_SYSTEM_PROMPT += "\n\nREGEL FÜR BILDER: Analysiere AUSSCHLIESSLICH das hochgeladene Bild. Wenn das Bild unklar, unleserlich oder keine sinnvolle BWL-Skizze ist, sag das offen und bitte um einen Reupload. Erfinde UNTER KEINEN UMSTÄNDEN Bildinhalte und fasse stattdessen NICHT einfach das Skript zusammen!"

                        full_contents.extend(history_for_api)
                        
                        max_retries = 3
                        for attempt in range(max_retries):
                            try:
                                response = google_client.models.generate_content(
                                    model='gemini-2.5-flash',
                                    contents=full_contents,
                                    config=types.GenerateContentConfig(system_instruction=FINAL_SYSTEM_PROMPT)
                                )
                                answer = response.text
                                break # Hat funktioniert! Wir brechen die Schleife ab.
                                
                            except Exception as e:
                                # Wenn der Fehler "unavailable" enthält und wir noch Versuche übrig haben
                                if "unavailable" in str(e).lower() and attempt < max_retries - 1:
                                    wartezeit = 2 ** attempt # Wartet 1s, dann 2s, dann 4s
                                    time.sleep(wartezeit)
                                    continue # Nächster Versuch
                                else:
                                    # Bei anderen echten Fehlern (z.B. API Key falsch) werfen wir den Fehler weiter
                                    raise e
                
                # --- ANTWORT VERARBEITEN ---
                if answer:
                    
                    # 🚨 DIE NOTBREMSE: Löscht alle hartnäckigen Folien/Seiten-Referenzen per Regex
                    # Sucht nach: "Auf Folie X", "Folie X", "Seite Y", "S. Y" etc.
                    answer = re.sub(r'(?i)(auf\s+)?(folie|seite|s\.)\s*\d+', '', answer)

                    # 🚨 NEU: EVAL-Tag auslesen und Lernfortschritt in Datenbank speichern
                    eval_match = re.search(r'<eval\s+(richtig|falsch)\s+(sicher|unsicher|geraten)>', answer, re.IGNORECASE)
                    if eval_match:
                        is_correct = eval_match.group(1).lower() == "richtig"
                        confidence = eval_match.group(2).lower()
                        
                        # Datenbank wird befüllt!
                        record_learning_event(st.session_state.username, gewaehlter_foliensatz, is_correct, st.session_state.level, confidence)
                        
                        # Den unsichtbaren Tag aus der Nachricht löschen, damit der User ihn nicht sieht
                        answer = re.sub(r'<eval[^>]*>', '', answer, flags=re.IGNORECASE).strip()

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

                    # 🚨 FIX: Den Chatverlauf nach JEDER Nachricht in die Cloud pushen
                    user_data = load_user_data(st.session_state.username)
                    if user_data:
                        save_user_data(st.session_state.username, user_data)

                    # 🚨 NEU: Bild aus dem Zwischenspeicher löschen, um Endlosschleife zu verhindern
                    if uploaded_image:
                        st.session_state.uploader_key += 1
                    
                    time.sleep(0.5)
                    st.rerun()

            except Exception as e:
                st.error(f"❌ Fehler bei der Server-Anfrage: {e}")
