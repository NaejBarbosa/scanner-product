import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image
import re
import numpy as np
import cv2
import pytesseract
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

st.set_page_config(page_title="Entrada de Paletes", layout="wide") # Layout wide para tela maior
st.title("❄️ Entrada de Paletes - Automação Câmara Fria")

# Configuração estável do protocolo WebRTC para conexões em redes móveis/Wi-Fi
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:://google.com"]}]}
)

# Inicializa as variáveis de estado caso não existam
if "ean" not in st.session_state:
    st.session_state.ean = ""
if "validade_formatada" not in st.session_state:
    st.session_state.validade_formatada = ""

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

# --- PROCESSADOR DE VÍDEO EM TEMPO REAL ---

class DetectorAutomatico(VideoProcessorBase):
    def recv(self, frame):
        # Converte o frame atual do vídeo para formato OpenCV (BGR)
        img_cv = frame.to_ndarray(format="bgr24")
        
        # Só realiza a busca se os campos atuais do formulário estiverem vazios
        if not st.session_state.ean or not st.session_state.validade_formatada:
            
            # 1. Tentativa com código de barras no frame atual
            decoded_objects = decode(img_cv)
            if decoded_objects:
                for obj in decoded_objects:
                    codigo_puro = obj.data.decode("utf-8")
                    
                    if len(codigo_puro) >= 24 and codigo_puro.startswith("01"):
                        try:
                            st.session_state.ean = codigo_puro[2:16]
                            if "17" in codigo_puro[16:19]:
                                idx_17 = codigo_puro.find("17", 16)
                                data_str = codigo_puro[idx_17+2 : idx_17+8]
                                st.session_state.validade_formatada = f"{data_str[4:6]}/{data_str[2:4]}/20{data_str[0:2]}"
                        except Exception:
                            pass
                    else:
                        st.session_state.ean = limpar_e_filtrar_ean(codigo_puro)
                    break
            
            # 2. Se o código de barras não trouxe a validade, aplica OCR no frame atual
            if st.session_state.ean and not st.session_state.validade_formatada:
                data_ocr = extrair_validade_por_ocr(img_cv)
                if data_ocr:
                    st.session_state.validade_formatada = data_ocr

        return frame

# --- DIVISÃO DA TELA (LAYOUT MAIOR E LADO A LADO) ---

col_camera, col_formulario = st.columns([1.3, 1.0], gap="large")

with col_camera:
    st.subheader("📷 Scanner Automático em Tempo Real")
    st.info("Aponte a câmera para a etiqueta. O sistema fará a leitura contínua e preencherá o formulário automaticamente.")
    
    # Renderiza o componente de vídeo contínuo ocupando o espaço máximo da coluna
    webrtc_streamer(
        key="scanner_continuo",
        video_processor_factory=DetectorAutomatico,
        rtc_configuration=RTC_CONFIGURATION,
        media_stream_constraints={"video": {"facingMode": "environment"}, "audio": False}, # Força câmera traseira no celular
    )
    
    # Botão auxiliar para resetar os campos e permitir uma nova leitura
    if st.button("🔄 Limpar Campos para Novo Escaneamento"):
        st.session_state.ean = ""
        st.session_state.validade_formatada = ""
        st.rerun()

with col_formulario:
    st.subheader("📝 Dados do Palete")

    # Exibe alertas visuais de sucesso dinâmicos fora do loop de renderização do vídeo
    if st.session_state.ean:
        st.success(f"✓ Código do Produto capturado!")
    if st.session_state.validade_formatada:
        st.success(f"✓ Data de validade capturada: {st.session_state.validade_formatada}")

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

        submit_button = st.form_submit_button(label="Registrar Entrada 📥")

    if submit_button:
        if not ean_input:
            st.error("O código do produto não pode ficar vazio.")
        elif not validade_input:
            st.error("A data de validade é obrigatória para o registro.")
        else:
            st.balloons()
            st.success(f"Palete registrado com sucesso na {camara}!")
            
            # Reseta as variáveis para a próxima caixa automática
            st.session_state.ean = ""
            st.session_state.validade_formatada = ""
            st.rerun()
