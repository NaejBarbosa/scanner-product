import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image
import re
import numpy as np
import cv2
import pytesseract
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration
import queue # Fila segura para comunicação entre Threads

st.set_page_config(page_title="Entrada de Paletes", layout="wide") # Maximiza a largura da tela
st.title("❄️ Entrada de Paletes - Automação Câmara Fria")

# Configuração estável e atualizada do servidor ICE (STUN) com portas explícitas
RTC_CONFIGURATION = RTCConfiguration(
    {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {"urls": ["stun:stun1.l.google.com:19302"]}
        ]
    }
)

# Inicializa variáveis no estado da sessão do Streamlit
if "ean" not in st.session_state:
    st.session_state.ean = ""
if "validade_formatada" not in st.session_state:
    st.session_state.validade_formatada = ""

# Criamos uma fila thread-safe global para receber os dados detectados pela câmera
if "fila_dados" not in st.session_state:
    st.session_state.fila_dados = queue.Queue()

# --- FUNÇÕES DE LIMPEZA E TRATAMENTO VISUAL ---

def limpar_e_filtrar_ean(codigo_bruto):
    codigo_limpo = re.sub(r"\D", "", codigo_bruto)
    if len(codigo_limpo) > 14:
        if codigo_limpo.startswith("01") and len(codigo_limpo) >= 16:
            return codigo_limpo[2:16]
        match = re.search(r"\b(\d{13,14})\b", codigo_limpo)
        if match:
            return match.group(1)
        return codigo_limpo[:14]
    return codigo_limpo

def tratar_imagem_para_ocr(img_cv):
    cinza = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    contraste = clahe.apply(cinza)
    binaria = cv2.adaptiveThreshold(
        contraste, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    return binaria

def extrair_validade_por_ocr(img_cv):
    try:
        img_tratada = tratar_imagem_para_ocr(img_cv)
        config_tesseract = r'--psm 3'
        texto_completo = pytesseract.image_to_string(img_tratada, lang='por', config=config_tesseract).upper()
        texto_completo = re.sub(r'\s+', ' ', texto_completo)
        
        padrao_data = r"(\d{2}/\d{2}/\d{2,4})"
        gatilhos = ["VALIDADE", "VAL.", "VAL:", "VENC", "VENCIMENTO", "VAL/DE", "FABRICAÇÃO", "DATA"]
        
        for gatilho in gatilhos:
            if gatilho in texto_completo:
                posicao = texto_completo.find(gatilho)
                texto_posterior = texto_completo[posicao:posicao+40]
                datas_encontradas = re.findall(padrao_data, texto_posterior)
                if datas_encontradas:
                    data_crua = datas_encontradas[0]
                    partes = data_crua.split("/")
                    if len(partes[2]) == 2:
                        partes[2] = "20" + partes[2]
                    return f"{partes[0]}/{partes[1]}/{partes[2]}"
        return None
    except Exception:
        return None

# --- PROCESSADOR DE VÍDEO EM TEMPO REAL (THREAD ISOLADA) ---

class DetectorAutomatico(VideoProcessorBase):
    def recv(self, frame):
        img_cv = frame.to_ndarray(format="bgr24")
        
        # 1. Busca código de barras no frame atual
        decoded_objects = decode(img_cv)
        ean_detectado = None
        validade_detectada = None

        if decoded_objects:
            for obj in decoded_objects:
                codigo_puro = obj.data.decode("utf-8")
                
                if len(codigo_puro) >= 24 and codigo_puro.startswith("01"):
                    try:
                        ean_detectado = codigo_puro[2:16]
                        if "17" in codigo_puro[16:19]:
                            idx_17 = codigo_puro.find("17", 16)
                            data_str = codigo_puro[idx_17+2 : idx_17+8]
                            validade_detectada = f"{data_str[4:6]}/{data_str[2:4]}/20{data_str[0:2]}"
                    except Exception:
                        pass
                else:
                    ean_detectado = limpar_e_filtrar_ean(codigo_puro)
                break
        
        # 2. Se achou código de barras mas não a validade, tenta extrair via OCR
        if ean_detectado and not validade_detectada:
            validade_detectada = extrair_validade_por_ocr(img_cv)
            
        # Se capturou pelo menos uma das informações, envia de forma segura para a fila
        if ean_detectado or validade_detectada:
            st.session_state.fila_dados.put({"ean": ean_detectado, "validade": validade_detectada})

        return frame

# --- RENDERIZAÇÃO DA INTERFACE LADO A LADO ---

# Captura de forma assíncrona os dados gerados pela thread da câmera
try:
    # Se houver dados novos enviados pela câmera na fila, processa
    dados_capturados = st.session_state.fila_dados.get_nowait()
    if dados_capturados.get("ean"):
        st.session_state.ean = dados_capturados["ean"]
    if dados_capturados.get("validade"):
        st.session_state.validade_formatada = dados_capturados["validade"]
except queue.Empty:
    pass

# Divisão de espaço na tela (Dando maior peso visual para a câmera)
col_camera, col_formulario = st.columns([1.5, 1.0], gap="large")

with col_camera:
    st.subheader("📷 Scanner Contínuo Automático")
    st.caption("Aponte para o código de barras ou o bloco de texto de validade da caixa.")
    
    # CSS customizado para garantir que o container do player de vídeo ocupe 100% do espaço da coluna
    st.markdown(
        """
        <style>
        div[data-testid="stWebRtcStreamer"] video {
            width: 100% !important;
            height: auto !important;
            max-height: 550px;
            border-radius: 10px;
            border: 2px solid #4CAF50;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Streamer de vídeo otimizado
    webrtc_streamer(
        key="scanner_continuo",
        video_processor_factory=DetectorAutomatico,
        rtc_configuration=RTC_CONFIGURATION,
        media_stream_constraints={"video": {"facingMode": "environment"}, "audio": False},
    )
    
    if st.button("🔄 Limpar Campos / Nova Leitura", use_container_width=True):
        st.session_state.ean = ""
        st.session_state.validade_formatada = ""
        # Limpa restos pendentes na fila
        while not st.session_state.fila_dados.empty():
            st.session_state.fila_dados.get()
        st.rerun()

with col_formulario:
    st.subheader("📝 Dados do Palete")

    if st.session_state.ean:
        st.success(f"✓ Código do Produto capturado!")
    if st.session_state.validade_formatada:
        st.success(f"✓ Data de validade capturada!")

    with st.form("form_entrada"):
        ean_input = st.text_input("Código EAN / Produto", value=st.session_state.ean)

        validade_input = st.text_input(
            "Data de Validade", 
            value=st.session_state.validade_formatada,
            placeholder="dd/mm/aaaa"
        )

        quantidade = st.number_input("Quantidade de Caixas", min_value=1, step=1)
        camara = st.selectbox("Câmara de Destino", ["Câmara Fria 01", "Câmara Fria 02", "Congelados 01"])
        operador = st.text_input("Nome do Operador")

        submit_button = st.form_submit_button(label="Registrar Entrada 📥", use_container_width=True)

    if submit_button:
        if not ean_input:
            st.error("O código do produto não pode ficar vazio.")
        elif not validade_input:
            st.error("A data de validade é obrigatória para o registro.")
        else:
            st.balloons()
            st.success(f"Palete registrado com sucesso na {camara}!")
            
            # Limpa tudo para o próximo palete
            st.session_state.ean = ""
            st.session_state.validade_formatada = ""
            while not st.session_state.fila_dados.empty():
                st.session_state.fila_dados.get()
            st.rerun()
