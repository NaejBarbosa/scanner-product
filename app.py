import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image
import re
import datetime
import io
import numpy as np
import cv2  # Biblioteca para processamento digital de imagens
import pytesseract

st.set_page_config(page_title="Entrada de Paletes", layout="centered")
st.title("❄️ Entrada de Paletes - Câmara Fria")

# Inicializa variáveis no estado da sessão do Streamlit
if "ean" not in st.session_state:
    st.session_state.ean = ""
if "validade_formatada" not in st.session_state:
    st.session_state.validade_formatada = ""

# Função para extrair o EAN correto de sequências numéricas longas
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

# Função avançada para tratar a imagem e melhorar a leitura do OCR
def tratar_imagem_para_ocr(img_pil):
    # Converte a imagem PIL para o formato do OpenCV (numpy array BGR)
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    # 1. Converte para tons de cinza (essencial para OCR)
    cinza = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # 2. Melhora o contraste adaptativo (CLAHE) - Excelente para corrigir sombras e reflexos de plástico
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    contraste = clahe.apply(cinza)
    
    # 3. Limiarização Adaptativa (Binarização) - Transforma o fundo em branco puro e as letras em preto puro
    binaria = cv2.adaptiveThreshold(
        contraste, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Converte de volta para imagem PIL para que o Pytesseract possa ler
    return Image.fromarray(binaria)

# Função para buscar data escrita na etiqueta por meio de processamento de texto (OCR)
def extrair_validade_por_ocr(img):
    try:
        # Aplica o tratamento de imagem antes de rodar o leitor de texto
        img_tratada = tratar_imagem_para_ocr(img)
        
        # Opcional: Descomente a linha abaixo caso queira ver a imagem tratada na barra lateral para testes
        # st.sidebar.image(img_tratada, caption="Imagem Otimizada para o OCR")

        # Configuração do Tesseract voltada para leitura de blocos de texto estruturados (--psm 3 ou 6)
        config_tesseract = r'--psm 3'
        texto_completo = pytesseract.image_to_string(img_tratada, lang='por', config=config_tesseract).upper()
        
        # Remove espaços extras para evitar que datas com espaços (ex: 11 / 01 / 27) quebrem o Regex
        texto_completo = re.sub(r'\s+', ' ', texto_completo)
        
        # Expressão regular flexível para capturar datas no formato DD/MM/AA ou DD/MM/AAAA
        padrao_data = r"(\d{2}/\d{2}/\d{2,4})"
        
        # Palavras-chave de gatilho comuns em etiquetas industriais e logísticas
        gatilhos = ["VALIDADE", "VAL.", "VAL:", "VENC", "VENCIMENTO", "VAL/DE", "FABRICAÇÃO", "DATA"]
        
        for gatilho in gatilhos:
            if gatilho in texto_completo:
                posicao = texto_completo.find(gatilho)
                # Pega os 40 caracteres subsequentes à palavra-chave para análise
                texto_posterior = texto_completo[posicao:posicao+40]
                
                datas_encontradas = re.findall(padrao_data, texto_posterior)
                if datas_encontradas:
                    data_crua = datas_encontradas[0] # Pega a primeira data que aparecer após o gatilho
                    
                    # Padroniza o ano com 4 dígitos (ex: 27 -> 2027)
                    partes = data_crua.split("/")
                    if len(partes[2]) == 2:
                        partes[2] = "20" + partes[2]
                        
                    return f"{partes[0]}/{partes[1]}/{partes[2]}"
                    
        return None
    except Exception as e:
        st.sidebar.error(f"Aviso do processador visual: {e}")
        return None

# Função compartilhada para processar a imagem (foto ou upload)
def processar_imagem(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            decoded_objects = decode(img)

            # --- PASSO 1: TENTATIVA DE LEITURA DO CÓDIGO DE BARRAS ---
            if decoded_objects:
                for obj in decoded_objects:
                    codigo_puro = obj.data.decode("utf-8")
                    st.success(f"Código detectado na etiqueta: {codigo_puro}")

                    # Tratamento se o código lido for o padrão GS1-128 completo
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
                        st.session_state.ean = limpar_e_filtrar_ean(codigo_puro)
                        st.session_state.validade_formatada = ""
                    break
            else:
                st.info("Nenhum código de barras linear identificado. Tentando leitura visual...")
                st.session_state.ean = ""
                st.session_state.validade_formatada = ""

            # --- PASSO 2: FALLBACK PARA LEITURA VISUAL DA VALIDADE (OCR TRATADO) ---
            if not st.session_state.validade_formatada:
                data_ocr = extrair_validade_por_ocr(img)
                if data_ocr:
                    st.session_state.validade_formatada = data_ocr
                    st.success(f"Data capturada via texto: {data_ocr}")
                else:
                    st.warning("Data de validade não encontrada automaticamente. Digite no campo abaixo.")

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

        # Limpa o estado para a próxima leitura
        st.session_state.ean = ""
        st.session_state.validade_formatada = ""
