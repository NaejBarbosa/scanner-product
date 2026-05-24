import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image
import datetime

st.set_page_config(page_title="Entrada de Paletes", layout="centered")
st.title("❄️ Entrada de Paletes - Câmara Fria")

# Inicializa variáveis no estado da sessão do Streamlit
if "ean" not in st.session_state:
    st.session_state.ean = ""
if "validade" not in st.session_state:
    st.session_state.validade = datetime.date.today()

# Função compartilhada para processar a imagem (foto ou upload)
def processar_imagem(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            decoded_objects = decode(img)
            
            if decoded_objects:
                for obj in decoded_objects:
                    codigo_puro = obj.data.decode("utf-8")
                    st.success(f"Código detectado: {codigo_puro}")
                    
                    # Lógica para processar padrão GS1-128 (Etiquetas de caixas)
                    if len(codigo_puro) >= 24 and codigo_puro.startswith("01"):
                        try:
                            st.session_state.ean = codigo_puro[2:16]
                            if "17" in codigo_puro[16:19]:
                                idx_17 = codigo_puro.find("17", 16)
                                data_str = codigo_puro[idx_17+2 : idx_17+8]
                                
                                ano = int("20" + data_str[0:2])
                                mes = int(data_str[2:4])
                                dia = int(data_str[4:6])
                                st.session_state.validade = datetime.date(ano, mes, dia)
                        except Exception:
                            st.warning("Erro ao processar padrão GS1-128.")
                    else:
                        # Código simples ou QR Code comum
                        st.session_state.ean = codigo_puro
                        st.info("Código simples detectado. Ajuste a validade se necessário.")
                    break
            else:
                st.error("Nenhum código de barras ou QR Code foi encontrado na imagem. Tente aproximar mais ou focar melhor.")
        except Exception as e:
            st.error(f"Erro ao processar o arquivo de imagem: {e}")

# --- SEÇÃO DO SCANNER (ABAS) ---
st.subheader("📷 Capturar Etiqueta")
aba_camera, aba_upload = st.tabs(["Usar Câmera", "Fazer Upload de Imagem"])

with aba_camera:
    # Captura a foto direto pelo componente nativo
    foto_capturada = st.camera_input("Clique abaixo para tirar foto do código", key="camera_scanner")
    if foto_capturada:
        processar_imagem(foto_capturada)

with aba_upload:
    # Permite o upload de arquivos PNG, JPG ou JPEG
    arquivo_carregado = st.file_uploader("Escolha uma foto da sua galeria", type=["png", "jpg", "jpeg"], key="upload_scanner")
    if arquivo_carregado:
        processar_imagem(arquivo_carregado)

# --- SEÇÃO DO FORMULÁRIO ---
st.subheader("📝 Dados do Palete")

with st.form("form_entrada"):
    # Os campos são preenchidos automaticamente se a imagem for decodificada com sucesso
    ean_input = st.text_input("Código EAN / Produto", value=st.session_state.ean)
    validade_input = st.date_input("Data de Validade", value=st.session_state.validade)
    
    quantidade = st.number_input("Quantidade de Caixas", min_value=1, step=1)
    camara = st.selectbox("Câmara de Destino", ["Câmara Fria 01", "Câmara Fria 02", "Congelados 01"])
    operador = st.text_input("Nome do Operador")
    
    submit_button = st.form_submit_button(label="Registrar Entrada 📥")

if submit_button:
    # Validação simples antes de salvar
    if not ean_input:
        st.error("O código do produto não pode ficar vazio.")
    else:
        st.balloons()
        st.success(f"Palete registrado com sucesso na {camara}!")
        # Limpa o estado para a próxima leitura
        st.session_state.ean = ""
        st.session_state.validade = datetime.date.today()
