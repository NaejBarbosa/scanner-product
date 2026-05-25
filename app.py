import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image
import re
import datetime
import io
import pytesseract  # OCR leve para leitura de texto nas imagens

st.set_page_config(page_title="Entrada de Paletes", layout="centered")
st.title("❄️ Entrada de Paletes - Câmara Fria")

# Inicializa variáveis no estado da sessão do Streamlit
if "ean" not in st.session_state:
    st.session_state.ean = ""
if "validade_formatada" not in st.session_state:
    st.session_state.validade_formatada = ""

# Função para extrair o EAN correto de sequências numéricas longas
def limpar_e_filtrar_ean(codigo_bruto):
    # Remove qualquer caractere que não seja número
    codigo_limpo = re.sub(r"\D", "", codigo_bruto)
    
    # Se for uma sequência muito grande (Ex: código de barras logístico longo de 30-40 dígitos)
    if len(codigo_limpo) > 14:
        # Geralmente em etiquetas industriais de código longo (como GS1), o EAN vem após os dígitos iniciais "01"
        if codigo_limpo.startswith("01") and len(codigo_limpo) >= 16:
            return codigo_limpo[2:16] # Retorna os 14 dígitos comerciais (EAN/DUN-14)
        
        # Fallback: Tenta localizar uma sequência típica de EAN-13 ou DUN-14 dentro da string longa
        match = re.search(r"\b(\d{13,14})\b", codigo_limpo)
        if match:
            return match.group(1)
            
        # Segundo Fallback: pega os primeiros 14 dígitos numéricos que fazem sentido comercial
        return codigo_limpo[:14]
        
    return codigo_limpo

# Função para buscar data escrita na etiqueta por meio de processamento de texto (OCR)
def extrair_validade_por_ocr(img):
    try:
        # Extrai o texto da imagem usando o idioma português
        texto_completo = pytesseract.image_to_string(img, lang='por').upper()
        
        # Expressão regular para capturar datas no formato DD/MM/AA ou DD/MM/AAAA
        padrao_data = r"\b(\d{2}/\d{2}/\d{2,4})\b"
        
        # Palavras-chave comuns encontradas em etiquetas de paletes/caixas
        gatilhos = ["VALIDADE", "VAL.", "VAL:", "VENC", "VENCIMENTO", "VAL/DE"]
        
        for gatilho in gatilhos:
            if gatilho in texto_completo:
                # Isola o texto a partir do ponto onde a palavra-chave foi localizada
                posicao = texto_completo.find(gatilho)
                texto_posterior = texto_completo[posicao:]
                
                # Encontra todas as ocorrências de data no bloco de texto recortado
                datas_encontradas = re.findall(padrao_data, texto_posterior)
                if datas_encontradas:
                    data_crua = datas_encontradas[0]
                    
                    # Garante que o ano tenha 4 dígitos (ex: converte "27" para "2027")
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
                            # Isola os 14 dígitos do produto comercial (posições 2 a 16)
                            st.session_state.ean = codigo_puro[2:16]
                            
                            if "17" in codigo_puro[16:19]:
                                idx_17 = codigo_puro.find("17", 16)
                                data_str = codigo_puro[idx_17+2 : idx_17+8]

                                # Extrai os dados no formato AAMMDD
                                ano = "20" + data_str[0:2]
                                mes = data_str[2:4]
                                dia = data_str[4:6]

                                # Salva formatado em padrão brasileiro (dd/mm/aaaa)
                                st.session_state.validade_formatada = f"{dia}/{mes}/{ano}"
                        except Exception:
                            st.warning("Erro ao processar padrão GS1-128.")
                            st.session_state.validade_formatada = ""
                    else:
                        # Se capturou um código numérico longo genérico, aplica a limpeza para extrair o EAN correto
                        st.session_state.ean = limpar_e_filtrar_ean(codigo_puro)
                        st.session_state.validade_formatada = ""
                    break
            else:
                st.info("Nenhum código de barras linear identificado. Tentando leitura visual...")
                st.session_state.ean = ""
                st.session_state.validade_formatada = ""

            # --- PASSO 2: FALLBACK PARA LEITURA VISUAL DA VALIDADE (OCR) ---
            # Se a validade não pôde ser extraída do código de barras, busca no texto impresso da etiqueta
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
