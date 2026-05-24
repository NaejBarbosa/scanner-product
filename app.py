import streamlit as st
from camera_input_live import camera_input_live
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

# --- SEÇÃO DO SCANNER ---
st.subheader("📷 Escanear Etiqueta da Caixa")
st.write("Aponte a câmera para o código de barras GS1-128 ou EAN.")

# Captura o frame da câmera em tempo real
image_file = camera_input_live(debounce=500)

if image_file:
    # Converte o arquivo para uma imagem PIL legível pela pyzbar
    img = Image.open(image_file)
    decoded_objects = decode(img)
    
    if decoded_objects:
        for obj in decoded_objects:
            codigo_puro = obj.data.decode("utf-8")
            st.success(["Código detectado com sucesso!"])
            
            # Lógica para processar padrão GS1-128 (Etiquetas de caixas como Sadia)
            # Exemplo de string GS1 comum: 019789123456789017261231 (01=EAN, 17=Validade em AAMMDD)
            if len(codigo_puro) >= 24 and codigo_puro.startswith("01"):
                try:
                    # Extrai o EAN (posições após o identificador 01)
                    st.session_state.ean = codigo_puro[2:16]
                    
                    # Procura o identificador de validade '17' e extrai a data (AAMMDD)
                    if "17" in codigo_puro[16:19]:
                        idx_17 = codigo_puro.find("17", 16)
                        data_str = codigo_puro[idx_17+2 : idx_17+8] # Pega os 6 dígitos seguintes
                        
                        ano = int("20" + data_str[0:2])
                        mes = int(data_str[2:4])
                        dia = int(data_str[4:6])
                        st.session_state.validade = datetime.date(ano, mes, dia)
                except Exception:
                    st.warning("Padrão de código detectado, mas houve erro ao separar os dados.")
            else:
                # Código de barras simples (apenas EAN comum de 13 ou 14 dígitos)
                st.session_state.ean = codigo_puro
                st.info("Código simples detectado. Insira a validade manualmente abaixo.")
            
            # Interrompe no primeiro código encontrado para evitar loops visuais
            break

# --- SEÇÃO DO FORMULÁRIO ---
st.subheader("📝 Dados do Palete")

with st.form("form_entrada"):
    # Os campos puxam automaticamente os valores salvos no session_state pelo scanner
    ean_input = st.text_input("Código EAN / Produto", value=st.session_state.ean)
    validade_input = st.date_input("Data de Validade", value=st.session_state.validade)
    
    # Campos adicionais para o operador preencher manualmente
    quantidade = st.number_input("Quantidade de Caixas", min_value=1, step=1)
    camara = st.selectbox("Câmara de Destino", ["Câmara Fria 01", "Câmara Fria 02", "Congelados 01"])
    operador = st.text_input("Nome do Operador")
    
    submit_button = st.form_submit_button(label="Registrar Entrada 📥")

if submit_button:
    # Aqui você conecta com seu banco de dados ou planilha
    st.balloons()
    st.success(f"Palete registrado com sucesso na {camara}!")
    # Limpa os dados para o próximo palete
    st.session_state.ean = ""
    st.session_state.validade = datetime.date.today()
  
