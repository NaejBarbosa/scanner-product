import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image
import re
import easyocr  # Importante: instale via pip install easyocr
import numpy as np

st.set_page_config(page_title="Entrada de Paletes", layout="centered")
st.title("❄️ Entrada de Paletes - Câmara Fria")

# Inicializa o leitor de OCR (armazenado em cache para não recarregar a cada clique)
@st.cache_resource
def carregar_leitor_ocr():
    return easyocr.Reader(['pt']) # Define o idioma para português

reader = carregar_leitor_ocr()

if "ean" not in st.session_state:
    st.session_state.ean = ""
if "validade_formatada" not in st.session_state:
    st.session_state.validade_formatada = ""

# Função para buscar data escrita no texto da imagem via OCR
def extrair_validade_por_ocr(img):
    try:
        # Converte a imagem PIL para formato aceito pelo EasyOCR
        img_np = np.array(img)
        resultados = reader.readtext(img_np)
        
        # Junta todas as linhas de texto detectadas
        texto_completo = " ".join([res[1].upper() for res in resultados])
        
        # Expressão regular para capturar datas no formato DD/MM/AA ou DD/MM/AAAA
        padrao_data = r"\b(\d{2}/\d{2}/\d{2,4})\b"
        
        # Palavras-chave comuns em etiquetas industriais
        gatilhos = ["VALIDADE", "VAL.", "VAL:", "VENC", "VENCIMENTO"]
        
        for gatilho in gatilhos:
            if gatilho in texto_completo:
                # Corta o texto a partir de onde achou a palavra "Validade"
                posicao = texto_completo.find(gatilho)
                texto_posterior = texto_completo[posicao:]
                
                # Procura a primeira data que aparece logo após a palavra-chave
                datas_encontradas = re.findall(padrao_data, texto_posterior)
                if datas_encontradas:
                    data_crua = datas_encontradas[0]
                    # Garante o formato de 4 dígitos para o ano (ex: 27 -> 2027)
                    partes = data_crua.split("/")
                    if len(partes)[2] == 2:
                        partes[2] = "20" + partes[2]
                    return f"{partes[0]}/{partes[1]}/{partes[2]}"
                    
        return None
    except Exception as e:
        st.sidebar.error(f"Erro no OCR: {e}")
        return None

# Função compartilhada para processar a imagem
def processar_imagem(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            decoded_objects = decode(img)

            # 1. TENTA PROCESSAR O CÓDIGO DE BARRAS
            if decoded_objects:
                for obj in decoded_objects:
                    codigo_puro = obj.data.decode("utf-8")
                    st.success(f"Código detectado: {codigo_puro}")

                    # Lógica GS1-128 original
                    if len(codigo_puro) >= 24 and codigo_puro.startswith("01"):
                        try:
                            st.session_state.ean = codigo_puro[2:16]
                            if "17" in codigo_puro[16:19]:
                                idx_17 = codigo_puro.find("17", 16)
                                data_str = codigo_puro[idx_17+2 : idx_17+8]
                                ano = "20" + data_str[0:2]
                                mes = data_str[2:4]
                                dia = data_str[4:6]
                                st.session_state.validade_formatada = f"{dia}/{mes}/{ano}"
                        except Exception:
                            st.warning("Erro ao processar padrão GS1-128.")
                            st.session_state.validade_formatada = ""
                    else:
                        st.session_state.ean = codigo_puro
                        st.session_state.validade_formatada = ""
                    break
            else:
                st.info("Nenhum código de barras linear lido. Tentando identificar via texto...")
                st.session_state.ean = ""

            # 2. SE A VALIDADE ESTIVER VAZIA, TENTA BUSCAR POR OCR NA IMAGEM
            if not st.session_state.validade_formatada:
                data_ocr = extrair_validade_por_ocr(img)
                if data_ocr:
                    st.session_state.validade_formatada = data_ocr
                    st.success(f"Validade identificada visualmente: {data_ocr}")
                else:
                    st.warning("Não foi possível ler a validade automaticamente. Digite manualmente.")

        except Exception as e:
            st.error(f"Erro ao processar o arquivo de imagem: {e}")

# --- SEÇÃO DO SCANNER (ABAS) ---
st.subheader("📷 Capturar Etiqueta")
aba_camera, aba_upload = st.tabs(["Usar Câmera", "Fazer Upload de Imagem"])

with aba_camera:
    foto_capturada = st.camera_input("Clique abaixo para tirar foto do código", key="camera_scanner")
    if foto_capturada:
        processar_imagem(foto_capturada)

with aba_upload:
    arquivo_carregado = st.file_uploader("Escolha uma foto da sua galeria", type=["png", "jpg", "jpeg"], key="upload_scanner")
    if arquivo_carregado:
        processar_imagem(arquivo_carregado)

# --- SEÇÃO DO FORMULÁRIO ---
st.subheader("📝 Dados do Palete")

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
        st.session_state.ean = ""
        st.session_state.validade_formatada = ""
