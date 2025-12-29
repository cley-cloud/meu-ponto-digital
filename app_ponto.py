import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime

st.set_page_config(page_title="Gestor de Ponto Equipes v4.1", layout="wide")

st.title("📊 Gestor de Ponto - Equipes Técnicas")

# --- LISTA OFICIAL E EQUIPES ---
LISTA_OFICIAL = [
    "JOAO EUDES DE SOUSA", "JOSE HELDER DA SILVA", "JOSE ALVES BARBOSA JÚNIOR",
    "RYAN GABRIEL SALES RICCIARDI", "ROBERTO SÉRGIO DOS SANTOS", "JOSEMBERG PAULO DA SILVA",
    "LUIZ CARLOS SILVA DOS SANTOS", "ANTÔNIO DAVID SERAFIM VIEIRA", "EDIGLEYSTON", "RAPHAEL"
]

EQUIPES = {
    "Equipe 1": ["JOSE HELDER DA SILVA", "JOAO EUDES DE SOUSA"],
    "Equipe 2": ["JOSE ALVES BARBOSA JÚNIOR", "ANTÔNIO DAVID SERAFIM VIEIRA"],
    "Equipe 3": ["ROBERTO SÉRGIO DOS SANTOS", "JOSEMBERG PAULO DA SILVA"],
    "Equipe 4": ["LUIZ CARLOS SILVA DOS SANTOS", "RYAN GABRIEL SALES RICCIARDI"],
    "Equipe 5": ["EDIGLEYSTON", "RAPHAEL"]
}

def converter_para_hora(texto_hora):
    try:
        if texto_hora and texto_hora != "00:00:00":
            return datetime.strptime(texto_hora, "%H:%M:%S")
    except: return None
    return None

def calcular_diferenca(hora_fim, hora_inicio):
    if hora_fim and hora_inicio:
        diff = hora_fim - hora_inicio
        total_segundos = int(diff.total_seconds())
        if total_segundos < 0: return "00h 00m"
        return f"{total_segundos // 3600:02d}h {(total_segundos % 3600) // 60:02d}m"
    return "00h 00m"

def formatar_hora_padrao(texto, hora_envio):
    match = re.search(r"(\d{1,2})[:hH](\d{2})", texto)
    if match: return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}:00"
    return f"{hora_envio}:00"

def identificar_categoria(texto):
    msg = texto.lower().strip()
    # Filtro de tamanho para garantir que seja comando de ponto
    if len(msg) > 35 and not any(x in msg for x in ["expediente", "trabalho"]): return None
    
    if any(p in msg for p in ["inic", "chegu", "comec"]): return "inicio"
    if any(p in msg for p in ["almo", "pausa", "comer"]) and "volt" not in msg: return "almoco"
    if any(p in msg for p in ["volta", "retorn", "voltei"]): return "volta"
    if any(p in msg for p in ["fim", "espedi", "expedi", "encer", "tchau", "finali"]): return "fim"
    return None

def obter_membros_equipe(nome_contato):
    """Busca ultra flexível: se o nome no WhatsApp tiver QUALQUER parte do nome oficial, ele aceita."""
    nome_contato = nome_contato.upper()
    
    # 1. Tenta achar o técnico pelo nome no contato do WhatsApp
    for nome_oficial in LISTA_OFICIAL:
        primeiro_nome = nome_oficial.split()[0]
        # Se o nome do contato contém o nome oficial OU o primeiro nome do oficial
        if nome_oficial in nome_contato or primeiro_nome in nome_contato:
            # Encontrou o técnico, agora retorna a equipe dele
            for membros in EQUIPES.values():
                if nome_oficial in membros:
                    return membros
            return [nome_oficial]
    return []

# --- INTERFACE ---
arquivo_upload = st.file_uploader("1. Carregue o arquivo conversa.txt", type="txt")

if arquivo_upload is not None:
    st.markdown("---")
    filtro_data = st.date_input("📅 Filtrar por dia (opcional)", value=None)

    stringio = io.StringIO(arquivo_upload.getvalue().decode("utf-8", errors="ignore"))
    linhas = stringio.readlines()

    tabela_ponto = {}
    # Padrão para mensagens normais e mensagens de sistema/mídia
    padrao_msg = re.compile(r"(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}) - (.*?): (.*)")
    
    datas_no_arquivo = set()
    for linha in linhas:
        match = padrao_msg.search(linha)
        if match: datas_no_arquivo.add(match.group(1))

    for data in datas_no_arquivo:
        for funcionario in LISTA_OFICIAL:
            tabela_ponto[(data, funcionario)] = {"Início": "00:00:00", "Almoço": "00:00:00", "Volta": "00:00:00", "Fim": "00:00:00"}

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
            equipe = obter_membros_equipe(u_func)
            for func_nome in equipe:
                if (u_data, func_nome) in tabela_ponto:
                    col_map = {"inicio": "Início", "almoco": "Almoço", "volta": "Volta", "fim": "Fim"}
                    tabela_ponto[(u_data, func_nome)][col_map[cat]] = hora_f

    if tabela_ponto:
        dados_lista = []
        for (data, func), pontos in tabela_ponto.items():
            data_obj = datetime.strptime(data, "%d/%m/%Y")
            e_sabado = data_obj.weekday() == 5
            h_ini = converter_para_hora(pontos["Início"])
            h_alm = converter_para_hora(pontos["Almoço"])
            h_vlt = converter_para_hora(pontos["Volta"])
            h_fim = converter_para_hora(pontos["Fim"])
            
            dur_alm = "00h 00m" if e_sabado else calcular_diferenca(h_vlt, h_alm)
            total_trabalhado = "00h 00m"
            if h_ini and h_fim:
                total_delta = h_fim - h_ini
                if not e_sabado and h_vlt and h_alm: total_delta -= (h_vlt - h_alm)
                seg = int(total_delta.total_seconds())
                if seg > 0: total_trabalhado = f"{seg // 3600:02d}h {(seg % 3600) // 60:02d}m"

            dados_lista.append({
                "Data_Obj": data_obj, "Data_Filtro": data_obj.date(), "Data": data, "Funcionário": func,
                **pontos, "Intervalo": dur_alm, "Total": total_trabalhado
            })
        
        df_completo = pd.DataFrame(dados_lista).sort_values(by=["Data_Obj", "Funcionário"])
        
        if filtro_data:
            df_final = df_completo[df_completo["Data_Filtro"] == filtro_data].copy()
        else:
            df_final = df_completo.copy()

        df_final = df_final.drop(columns=["Data_Obj", "Data_Filtro"])
        st.subheader("📋 Relatório Conferido")
        st.dataframe(df_final, use_container_width=True)
        
        buffer_copia = "Data\tFuncionario\tInicio\tAlmoco\tVolta\tFim\tIntervalo\tTotal\n"
        for _, row in df_final.iterrows():
            buffer_copia += f"{row['Data']}\t{row['Funcionário']}\t{row['Início']}\t{row['Almoço']}\t{row['Volta']}\t{row['Fim']}\t{row['Intervalo']}\t{row['Total']}\n"
        st.text_area("Copiar para Sheets:", buffer_copia, height=200)
