import streamlit as st
import pandas as pd
import re
import io
import unicodedata
from datetime import datetime

st.set_page_config(page_title="Gestor de Ponto Blindado", layout="wide")
st.title("📊 Gestor de Ponto - MDU FTZ CE")

# --- LISTA OFICIAL ---
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

# --- FUNÇÃO NOVA: REMOVE ACENTOS ---
def normalizar(texto):
    """Transforma 'João Eudes' em 'JOAO EUDES' para facilitar a busca."""
    if not texto: return ""
    # Remove acentos e joga pra maiúsculo
    nfkd = unicodedata.normalize('NFKD', texto)
    texto_sem_acento = u"".join([c for c in nfkd if not unicodedata.combining(c)])
    return texto_sem_acento.upper().strip()

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
    if any(p in msg for p in ["início", "inicio", "🟢", "cheguei", "iniciando"]): return "inicio"
    if any(p in msg for p in ["ida ao", "almoço", "almoco", "🍽️"]) and "volta" not in msg: return "almoco"
    if any(p in msg for p in ["volta", "retorno", "🔙", "voltei"]): return "volta"
    if any(p in msg for p in ["fim", "expediente", "🔴", "finalizado", "encerrado", "tchau"]): return "fim"
    return None

def obter_membros_equipe(nome_zap):
    """Busca inteligente ignorando acentos."""
    nome_zap_norm = normalizar(nome_zap) # Ex: O zap manda 'João', vira 'JOAO'
    
    for oficial in LISTA_OFICIAL:
        oficial_norm = normalizar(oficial) # Ex: Lista tem 'JOAO EUDES'
        
        # Divide o nome oficial em pedaços (Ex: ['JOAO', 'EUDES', 'DE', 'SOUSA'])
        partes = oficial_norm.split()
        
        # Verifica se o PRIMEIRO ou o SEGUNDO nome estão dentro do nome do Zap
        # Ex: Se zap for "Eudes", ele acha "JOAO EUDES"
        match = False
        if partes[0] in nome_zap_norm: match = True
        if len(partes) > 1 and partes[1] in nome_zap_norm: match = True
        
        # Verificação inversa: Se o nome do zap estiver dentro do oficial (Ex: zap "David" em "Antonio David")
        if nome_zap_norm in oficial_norm and len(nome_zap_norm) > 3: match = True

        if match:
            # Achou! Retorna a equipe inteira
            for membros in EQUIPES.values():
                if oficial in membros: return membros
            return [oficial]
    return []

# --- INTERFACE ---
arquivo_upload = st.file_uploader("📂 Carregue o arquivo conversa.txt", type="txt")

if arquivo_upload:
    stringio = io.StringIO(arquivo_upload.getvalue().decode("utf-8", errors="ignore"))
    linhas = stringio.readlines()
    
    tabela_ponto = {}
    padrao = re.compile(r"(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}) - (.*?): (.*)")
    
    # Conjunto para diagnóstico
    nomes_ignorados = set()
    
    # 1. Datas
    datas = set()
    for l in linhas:
        m = padrao.search(l)
        if m: datas.add(m.group(1))
    
    # Inicializa tabela vazia
    for d in datas:
        for f in LISTA_OFICIAL:
            tabela_ponto[(d, f)] = {"Início": "00:00:00", "Almoço": "00:00:00", "Volta": "00:00:00", "Fim": "00:00:00"}

    # 2. Processamento
    for l in linhas:
        l = l.replace("‎", "").strip()
        m = padrao.search(l)
        if m:
            u_data, u_hora, u_remetente, conteudo = m.groups()
            texto_analise = conteudo
            
            # Tenta identificar equipe
            equipe = obter_membros_equipe(u_remetente)
            
            # Se não achou equipe, guarda o nome para o diagnóstico
            if not equipe:
                nomes_ignorados.add(u_remetente)
            
            cat = identificar_categoria(texto_analise)
            
            if cat and equipe:
                for membro in equipe:
                    if (u_data, membro) in tabela_ponto:
                        col = {"inicio": "Início", "almoco": "Almoço", "volta": "Volta", "fim": "Fim"}[cat]
                        if tabela_ponto[(u_data, membro)][col] == "00:00:00":
                            tabela_ponto[(u_data, membro)][col] = f"{u_hora}:00"
        
    # 3. Montar Tabela
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

    # 4. Exibição
    st.subheader("📋 Relatório")
    dia_f = st.date_input("Filtrar Data:", value=None)
    if dia_f:
        df = df[df["Data_O"].dt.date == dia_f]
    
    st.dataframe(df.drop(columns=["Data_O"]), use_container_width=True)

    # 5. DIAGNÓSTICO DE ERROS (AQUI ESTÁ O SEGREDO)
    with st.sidebar:
        st.header("🕵️ Diagnóstico")
        st.warning("Se alguém está zerado, verifique se o nome dele aparece na lista abaixo:")
        st.write(list(nomes_ignorados))
        st.info("Dica: Se o nome estiver na lista acima, significa que o código não conseguiu vincular ele à Lista Oficial.")

    # Copiar
    txt = "Data\tFuncionario\tInicio\tAlmoco\tVolta\tFim\tIntervalo\tTotal\n"
    for _, r in df.iterrows():
        txt += f"{r['Data']}\t{r['Funcionário']}\t{r['Início']}\t{r['Almoço']}\t{r['Volta']}\t{r['Fim']}\t{r['Intervalo']}\t{r['Total']}\n"
    st.subheader("✂️ Copiar")
    st.text_area("Ctrl+A e Ctrl+C:", txt, height=200)

