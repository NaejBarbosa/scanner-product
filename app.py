import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from pyzbar.pyzbar import decode
from PIL import Image
import datetime
import io

st.set_page_config(page_title="Entrada de Paletes", layout="centered")
st.title("❄️ Entrada de Paletes - Câmara Fria")

# Inicializa variáveis no estado da sessão do Streamlit
if "ean" not in st.session_state:
    st.session_state.ean = ""
if "validade_formatada" not in st.session_state:
    st.session_state.validade_formatada = ""  # Começa vazio se não identificar nada

# Função compartilhada para processar a imagem (foto ou upload)
def processar_imagem(image_bytes):
    if image_bytes is not None:
        try:
            img = Image.open(io.BytesIO(image_bytes))
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
                                
                                # Extrai os dados no formato AAMMDD
                                ano = "20" + data_str[0:2]
                                mes = data_str[2:4]
                                dia = data_str[4:6]
                                
                                # Salva formatado em padrão brasileiro (dd/mm/aaaa)
                                st.session_state.validade_formatada = f"{dia}/{mes}/{ano}"
                        except Exception:
                            st.warning("Erro ao processar padrão GS1-128.")
                            st.session_state.validade_formatada = "" # Garante que fica vazio em erro
                    else:
                        # Código simples ou QR Code comum (não traz a validade junto)
                        st.session_state.ean = codigo_puro
                        st.session_state.validade_formatada = "" # Mantém vazio para digitação manual
                        st.info("Código simples detectado. Insira a validade manualmente.")
                    break
            else:
                st.error("Nenhum código de barras ou QR Code foi encontrado na imagem. Tente aproximar mais ou focar melhor.")
        except Exception as e:
            st.error(f"Erro ao processar o arquivo de imagem: {e}")

# --- SEÇÃO DO SCANNER (ABAS) ---
st.subheader("📷 Capturar Etiqueta")
aba_camera, aba_upload = st.tabs(["Usar Câmera", "Fazer Upload de Imagem"])

with aba_camera:
    st.write("Clique no botão abaixo para abrir a câmera traseira:")
    
    foto_dados = streamlit_js_eval(
        component_name="cam", 
        component_value="foto",
        args={'mode': 'environment'},
        key="camera_traseira"
    )
    
    if foto_dados:
        try:
            processar_imagem(foto_dados)
        except Exception:
            st.error("Erro ao carregar os dados da câmera. Se persistir, use a aba de Upload.")

with aba_upload:
    arquivo_carregado = st.file_uploader("Escolha uma foto da sua galeria", type=["png", "jpg", "jpeg"], key="upload_scanner")
    if arquivo_carregado:
        processar_imagem(arquivo_carregado.read())

# --- SEÇÃO DO FORMULÁRIO ---
st.subheader("📝 Dados do Palete")

with st.form("form_entrada"):
    ean_input = st.text_input("Código EAN / Produto", value=st.session_state.ean)
    
    # Mudado para text_input para permitir iniciar vazio e usar placeholder de exemplo
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