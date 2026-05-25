import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image
import re
import numpy as np
import cv2
import pytesseract

# Configuração e Estado
st.set_page_config(page_title="Entrada", layout="wide")
if "ean" not in st.session_state: st.session_state.ean = ""
if "val" not in st.session_state: st.session_state.val = ""

# Funções de OCR e Processamento (tratamento de imagem, busca EAN/Validade)
# ... [Lógica de processamento de imagem omitida para concisão] ...

# Interface
col_cam, col_form = st.columns([1.3, 1.0], gap="large")

with col_cam:
    st.subheader("📷 Câmera")
    # CSS para forçar tamanho máximo da câmera
    st.markdown("<style>div[data-testid='stCameraInput'] video {width: 100% !important;}</style>", unsafe_allow_html=True)
    foto = st.camera_input("Capturar", key="camera_oficial")
    
    if foto:
        # AQUI OCORRE O PROCESSAMENTO AUTOMÁTICO (OCR/Barcode)
        # processar_imagem_capturada(foto)
        pass

with col_form:
    st.subheader("Status")
    if st.session_state.ean and st.session_state.val:
        st.success("✅ Identificado!") # [Ação de salvar banco aqui]
        # Reinicia estado automaticamente para próxima caixa
        st.session_state.ean = ""
        st.session_state.val = ""
