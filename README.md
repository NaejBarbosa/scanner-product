# ❄️ Coletor de Entrada - Câmaras Frias

Aplicativo web mobile desenvolvido em Python e Streamlit para automatizar o registro de paletes em ambientes refrigerados. O sistema utiliza a câmera do smartphone para escanear etiquetas, eliminando a digitação manual e reduzindo erros de operação.

## 🚀 Funcionalidades

*   **Scanner em Tempo Real**: Captura de códigos diretamente pela câmera do celular (suporta Web Mobile).
*   **Leitura Híbrida**: Decodifica códigos de barras tradicionais (EAN-13, Code 128), padrões industriais (GS1-128) e QR Codes.
*   **Inteligência na Etiqueta**: Separa automaticamente o código EAN e a **Data de Validade** ao ler etiquetas padrão GS1-128 (como as caixas da Sadia/BRF).
*   **Interface Otimizada**: Botões grandes e foco automático pensados para operadores que utilizam luvas térmicas.

## 📦 Estrutura do Projeto

```text
├── app.py          # Código principal da aplicação Streamlit
├── requirements.txt # Dependências de bibliotecas Python
├── packages.txt     # Dependência de sistema Linux (obrigatório para o deploy)
└── README.md        # Documentação do projeto
```

## 🛠️ Como Executar Localmente

### Pré-requisitos

Antes de rodar o projeto, você precisa instalar a biblioteca de sistema `zbar` no seu computador:

*   **Windows**: Baixe e instale o instalador do [zbar para Windows](https://sourceforge.net). Certifique-se de adicionar o caminho de instalação às variáveis de ambiente do sistema.
*   **macOS**: Execute `brew install zbar` no terminal.
*   **Linux (Ubuntu/Debian)**: Execute `sudo apt-get install libzbar0` no terminal.

### Passo a Passo

1. Clone este repositório:
   ```bash
   git clone https://github.com
   cd NOME_DO_REPOSITORIO
   ```

2. Crie e ative um ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Linux/macOS:
   source venv/bin/activate
   ```

3. Instale as dependências do Python:
   ```bash
   pip install -r requirements.txt
   ```

4. Inicie o aplicativo:
   ```bash
   streamlit run app.py
   ```

---

## ☁️ Deploy no Streamlit Community Cloud

Este projeto está configurado para ser publicado gratuitamente no **Streamlit Cloud**. O arquivo `packages.txt` garante que o servidor Linux do Streamlit instale os drivers de câmera necessários automaticamente.

1. Suba o código atualizado para o seu repositório no **GitHub**.
2. Acesse [share.streamlit.io](https://streamlit.io) e faça login com sua conta do GitHub.
3. Clique em **"New app"**.
4. Selecione o repositório, a branch (ex: `main`) e digite `app.py` no campo *Main file path*.
5. Clique em **"Deploy!"**. Em poucos minutos seu link web mobile estará ativo.

---

## 📋 Como Funciona a Separação dos Dados (GS1-128)

Ao escanear uma etiqueta padrão de caixa de frigorífico, o algoritmo processa os Identificadores de Aplicação (IAs):
*   **Prefixos `(01)`**: Identificam os 14 dígitos do código do produto (EAN/DUN-14).
*   **Prefixos `(17)`**: Identificam os 6 dígitos sequenciais da data de validade no formato `AAMMDD` (Ano, Mês e Dia).

Se um QR Code ou código simples for escaneado, o sistema preenche apenas o campo do produto e libera a data para ajuste manual.
