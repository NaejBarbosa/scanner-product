import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image
import re
import datetime
import io
import numpy as np
import cv2  # Processamento de imagem para melhorar o contraste
import pytesseract

st.set_page_config(page_title="Entrada de Paletes", layout="wide")
st.title("❄️ Entrada de Paletes - Automação Câmara Fria")

# Inicializa variáveis no estado da sessão do Streamlit
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

def tratar_imagem_para_ocr(img_pil):
    # Converte a imagem PIL para o formato do OpenCV (numpy array BGR)
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    # 1. Converte para tons de cinza
    cinza = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # 2. Melhora o contraste adaptativo (CLAHE) - Corrige sombras da câmara fria
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    contraste = clahe.apply(cinza)
    
    # 3. Binarização - Deixa o fundo branco puro e as letras pretas puras
    binaria = cv2.adaptiveThreshold(
        contraste, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    return Image.fromarray(binaria)

def extrair_validade_por_ocr(img_pil):
    try:
        # Otimiza o contraste antes de enviar ao Tesseract
        img_tratada = tratar_imagem_para_ocr(img_pil)

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

# --- PROCESSADOR CENTRAL DA IMAGEM ---

def processar_imagem(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            decoded_objects = decode(img)

            # 1. TENTA LER O CÓDIGO DE BARRAS
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
            else:
                st.session_state.ean = ""

            # 2. SE O CÓDIGO NÃO TROUXE A VALIDADE, TENTA EXTRAIR VISUALMENTE PELO OCR TRATADO
            if not st.session_state.validade_formatada:
                data_ocr = extrair_validade_por_ocr(img)
                if data_ocr:
                    st.session_state.validade_formatada = data_ocr

        except Exception as e:
            st.error(f"Erro ao processar o arquivo de imagem: {e}")

# --- RENDERIZAÇÃO DA INTERFACE EM COLUNAS ---

col_camera, col_formulario = st.columns([1.4, 1.0], gap="large")

with col_camera:
    st.subheader("📷 Capturar Etiqueta")
    
    # Injeta CSS para expandir o tamanho visual do preview da câmera
    st.markdown(
        """
        <style>
        div[data-testid="stCameraInput"] video {
            width: 100% !important;
            height: auto !important;
            max-height: 500px;
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Abas mantendo as opções de Câmera e Upload manual da galeria
    aba_camera, aba_upload = st.tabs(["Usar Câmera do Celular", "Fazer Upload de Foto"])
    
    with aba_camera:
        foto_capturada = st.camera_input("Tirar foto da etiqueta", key="camera_scanner")
        if foto_capturada:
            processar_imagem(foto_capturada)

    with aba_upload:
        arquivo_carregado = st.file_uploader("Escolha uma foto da sua galeria", type=["png", "jpg", "jpeg"], key="upload_scanner")
        if arquivo_carregado:
            processar_imagem(arquivo_carregado)
            
    if st.button("🔄 Limpar Campos para Nova Leitura", use_container_width=True):
        st.session_state.ean = ""
        st.session_state.validade_formatada = ""
        st.rerun()

with col_formulario:
    st.subheader("📝 Dados do Palete")

    # --- VERIFICAÇÃO AUTOMÁTICA DE REGISTRO PASSO A PASSO ---
    # Se ambos os dados principais foram capturados pela imagem (ou preenchidos), pula etapas de cliques
    if st.session_state.ean and st.session_state.validade_formatada:
        st.balloons()
        st.success("✨ Dados identificados e validados com sucesso!")
        st.info(f"PRODUTO: {st.session_state.ean} | VALIDADE: {st.session_state.validade_formatada}")
        
        # [Opcional] Chame sua função de salvar no banco de dados aqui.
        
        # Limpa o estado para que na próxima foto o formulário não fique travado
        st.session_state.ean = ""
        st.session_state.validade_formatada = ""

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

        submit_button = st.form_submit_button(label="Registrar Manualmente 📥", use_container_width=True)

    if submit_button:
        if not ean_input:
            st.error("O código do produto não pode ficar vazio.")
        elif not validade_input:
            st.error("A data de validade é obrigatória para o registro.")
        else:
            st.success(f"Palete registrado com sucesso na {camara}!")
            st.session_state.ean = ""
            st.session_state.validade_formatada = ""
            st.rerun()
