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

# --- SEÇÃO DO SCANNER NATIVO ---
st.subheader("📷 Escanear Etiqueta da Caixa")

# Este componente cria o botão nativo para abrir a câmera do celular
image_file = st.camera_input("Clique abaixo para tirar foto do código de barras/QR Code")

if image_file:
    # Converte o arquivo capturado para uma imagem legível pela pyzbar
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
        st.error("Nenhum código de barras ou QR Code foi encontrado na foto. Tente aproximar mais ou focar melhor.")

# --- SEÇÃO DO FORMULÁRIO ---
st.subheader("📝 Dados do Palete")

with st.form("form_entrada"):
    ean_input = st.text_input("Código EAN / Produto", value=st.session_state.ean)
    validade_input = st.date_input("Data de Validade", value=st.session_state.validade)
    
    quantidade = st.number_input("Quantidade de Caixas", min_value=1, step=1)
    camara = st.selectbox("Câmara de Destino", ["Câmara Fria 01", "Câmara Fria 02", "Congelados 01"])
    operador = st.text_input("Nome do Operador")
    
    submit_button = st.form_submit_button(label="Registrar Entrada 📥")

if submit_button:
    st.balloons()
    st.success(f"Palete registrado com sucesso na {camara}!")
    st.session_state.ean = ""
    st.session_state.validade = datetime.date.today()
