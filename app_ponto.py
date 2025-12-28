import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="Gestor de Ponto Profissional", layout="wide")

st.title("📊 Gestor de Ponto - WhatsApp")
st.markdown("Filtre, visualize e copie os dados para sua planilha principal.")

LISTA_FUNCIONARIOS = ["Clayverton", "João Silva", "Maria Souza"]

def formatar_hora_padrao(texto, hora_envio):
    match = re.search(r"(\d{1,2})[:hH](\d{2})", texto)
    if match:
        return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}:00"
    return f"{hora_envio}:00"

def identificar_categoria(texto):
    msg = texto.lower().strip()
    if any(p in msg for p in ["início", "inicio", "iniciando", "cheguei"]): return "inicio"
    if any(p in msg for p in ["almoço", "almoco", "pausa"]): return "almoco"
    if any(p in msg for p in ["voltei", "volta", "retorno"]): return "volta"
    if any(p in msg for p in ["fim", "encerrado", "finalizando", "terminando"]): return "fim"
    return None

arquivo_upload = st.file_uploader("Escolha o arquivo conversa.txt", type="txt")

if arquivo_upload is not None:
    stringio = io.StringIO(arquivo_upload.getvalue().decode("utf-8", errors="ignore"))
    linhas = stringio.readlines()

    tabela_ponto = {}
    padrao_msg = re.compile(r"(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}) - (.*?): (.*)")
    
    u_func, u_data, u_hora = None, None, None

    for linha in linhas:
        linha = linha.replace("‎", "").strip()
        match = padrao_msg.search(linha)
        
        if match:
            data, hora, remetente, conteudo = match.groups()
            u_func, u_data, u_hora = remetente, data, hora
            texto_analise = conteudo
        else:
            texto_analise = linha
        
        cat = identificar_categoria(texto_analise)
        if cat and u_func:
            hora_f = formatar_hora_padrao(texto_analise, u_hora)
            chave = (u_data, u_func)
            if chave not in tabela_ponto:
                tabela_ponto[chave] = {"Início": "", "Almoço": "", "Volta": "", "Fim": ""}
            
            col_map = {"inicio": "Início", "almoco": "Almoço", "volta": "Volta", "fim": "Fim"}
            tabela_ponto[chave][col_map[cat]] = hora_f

    if tabela_ponto:
        dados_lista = []
        for (data, func), pontos in sorted(tabela_ponto.items()):
            dados_lista.append({"Data": data, "Funcionário": func, **pontos})
        
        df = pd.DataFrame(dados_lista)
        
        # --- ÁREA DE VISUALIZAÇÃO ---
        st.subheader("📋 Visualização dos Dados")
        st.dataframe(df, use_container_width=True)

        # --- ÁREA DE CÓPIA PARA GOOGLE SHEETS / EXCEL ---
        st.subheader("✂️ Copiar para Planilha (Sheets/Excel)")
        st.info("O bloco abaixo está formatado para que você selecione e cole direto nas colunas da sua planilha.")

        # Criamos uma string tabulada (separada por TAB) que o Sheets entende como colunas
        buffer_copia = "Data\tFuncionario\tInicio\tAlmoco\tVolta\tFim\n"
        for _, row in df.iterrows():
            buffer_copia += f"{row['Data']}\t{row['Funcionário']}\t{row['Início']}\t{row['Almoço']}\t{row['Volta']}\t{row['Fim']}\n"

        # Widget de área de texto para o usuário copiar facilmente
        st.text_area("Selecione tudo abaixo (Ctrl+A), copie (Ctrl+C) e cole no seu Sheets:", 
                     buffer_copia, height=200)

        # Botão de download CSV como alternativa
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button(label="📥 Baixar CSV Completo", data=csv, file_name="ponto_limpo.csv", mime="text/csv")
    else:
        st.error("Não encontramos comandos de ponto (Início, Almoço, etc) neste arquivo.")