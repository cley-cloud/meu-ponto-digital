import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime

st.set_page_config(page_title="Gestor de Ponto MDU", layout="wide")

st.title("📊 Gestor de Ponto - MDU FTZ CE")

# --- CONFIGURAÇÕES INICIAIS ---
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
        seg = int(diff.total_seconds())
        if seg < 0: return "00h 00m"
        return f"{seg // 3600:02d}h {(seg % 3600) // 60:02d}m"
    return "00h 00m"

def identificar_categoria(texto):
    msg = texto.lower().strip()
    if any(p in msg for p in ["início", "inicio", "🟢", "cheguei"]): return "inicio"
    if any(p in msg for p in ["ida ao", "almoço", "almoco", "🍽️"]) and "volta" not in msg: return "almoco"
    if any(p in msg for p in ["volta", "retorno", "🔙", "voltei"]): return "volta"
    if any(p in msg for p in ["fim", "expediente", "🔴", "finalizado", "encerrado"]): return "fim"
    return None

def obter_membros_equipe(nome_zap):
    nome_zap = nome_zap.upper()
    for oficial in LISTA_OFICIAL:
        primeiro_nome = oficial.split()[0]
        if primeiro_nome in nome_zap or oficial in nome_zap:
            for membros in EQUIPES.values():
                if oficial in membros: return membros
            return [oficial]
    return []

# --- INTERFACE E PROCESSAMENTO ---
arquivo_upload = st.file_uploader("Upload do arquivo .txt do WhatsApp", type="txt")

if arquivo_upload:
    stringio = io.StringIO(arquivo_upload.getvalue().decode("utf-8", errors="ignore"))
    linhas = stringio.readlines()
    
    tabela_ponto = {}
    padrao = re.compile(r"(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}) - (.*?): (.*)")
    
    # 1. Mapear datas e inicializar todos os 10 técnicos
    datas_encontradas = set()
    for l in linhas:
        m = padrao.search(l)
        if m: datas_encontradas.add(m.group(1))
    
    for d in datas_encontradas:
        for f in LISTA_OFICIAL:
            tabela_ponto[(d, f)] = {"Início": "00:00:00", "Almoço": "00:00:00", "Volta": "00:00:00", "Fim": "00:00:00"}

    # 2. Preencher horários
    u_remetente, u_data, u_hora = None, None, None
    for l in linhas:
        l = l.strip()
        m = padrao.search(l)
        if m:
            u_data, u_hora, u_remetente, conteudo = m.groups()
            texto_analise = conteudo
        else:
            texto_analise = l
        
        cat = identificar_categoria(texto_analise)
        if cat and u_remetente:
            membros = obter_membros_equipe(u_remetente)
            for m_nome in membros:
                if (u_data, m_nome) in tabela_ponto:
                    col = {"inicio": "Início", "almoco": "Almoço", "volta": "Volta", "fim": "Fim"}[cat]
                    if tabela_ponto[(u_data, m_nome)][col] == "00:00:00":
                        tabela_ponto[(u_data, m_nome)][col] = f"{u_hora}:00"

    # 3. Gerar Lista para Tabela
    dados = []
    for (d, f), p in tabela_ponto.items():
        d_obj = datetime.strptime(d, "%d/%m/%Y")
        e_sab = d_obj.weekday() == 5
        h_ini, h_alm, h_vlt, h_fim = converter_para_hora(p["Início"]), converter_para_hora(p["Almoço"]), converter_para_hora(p["Volta"]), converter_para_hora(p["Fim"])
        
        int_v = "00h 00m" if e_sab else calcular_diferenca(h_vlt, h_alm)
        tot_v = "00h 00m"
        if h_ini and h_fim:
            delta = h_fim - h_ini
            if not e_sab and h_vlt and h_alm: delta -= (h_vlt - h_alm)
            s = int(delta.total_seconds())
            if s > 0: tot_v = f"{s // 3600:02d}h {(s % 3600) // 60:02d}m"
        
        dados.append({"Data_O": d_obj, "Data": d, "Funcionário": f, **p, "Intervalo": int_v, "Total": tot_v})

    df = pd.DataFrame(dados).sort_values(by=["Data_O", "Funcionário"], ascending=[False, True])
    
    # Filtro de Data
    dia_f = st.date_input("Filtrar dia:", value=None)
    if dia_f:
        df = df[df["Data_O"].dt.date == dia_f]

    st.dataframe(df.drop(columns=["Data_O"]), use_container_width=True)

    # Bloco de Cópia
    st.subheader("✂️ Bloco de Cópia")
    txt_copy = "Data\tFuncionario\tInicio\tAlmoco\tVolta\tFim\tIntervalo\tTotal\n"
    for _, r in df.iterrows():
        txt_copy += f"{r['Data']}\t{r['Funcionário']}\t{r['Início']}\t{r['Almoço']}\t{r['Volta']}\t{r['Fim']}\t{r['Intervalo']}\t{r['Total']}\n"
    st.text_area("Copie e cole no Sheets:", txt_copy, height=200)
