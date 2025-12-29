import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime

st.set_page_config(page_title="Gestor de Ponto por Equipes", layout="wide")

st.title("📊 Gestor de Ponto - Equipes Técnicas")
st.markdown("Filtre por data na barra lateral para visualizar e copiar dias específicos.")

# --- MAPEAMENTO DE EQUIPES ---
EQUIPES = {
    "Equipe 1": ["JOSE HELDER DA SILVA", "JOAO EUDES DE SOUSA"],
    "Equipe 2": ["JOSE ALVES BARBOSA JÚNIOR", "ANTÔNIO DAVID SERAFIM VIEIRA"],
    "Equipe 3": ["ROBERTO SÉRGIO DOS SANTOS", "JOSEMBERG PAULO DA SILVA"],
    "Equipe 4": ["LUIZ CARLOS SILVA DOS SANTOS", "RYAN GABRIEL SALES RICCIARDI"],
    "Equipe 5": ["EDIGLEYSTON", "RAPHAEL"]
}

def converter_para_hora(texto_hora):
    try:
        if texto_hora and texto_hora != "--":
            return datetime.strptime(texto_hora, "%H:%M:%S")
    except: return None
    return None

def calcular_diferenca(hora_fim, hora_inicio):
    if hora_fim and hora_inicio:
        diff = hora_fim - hora_inicio
        total_segundos = int(diff.total_seconds())
        if total_segundos < 0: return "--"
        return f"{total_segundos // 3600:02d}h {(total_segundos % 3600) // 60:02d}m"
    return "--"

def formatar_hora_padrao(texto, hora_envio):
    match = re.search(r"(\d{1,2})[:hH](\d{2})", texto)
    if match: return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}:00"
    return f"{hora_envio}:00"

def identificar_categoria(texto):
    msg = texto.lower().strip()
    if any(p in msg for p in ["inic", "chegu", "comec", "inici"]): return "inicio"
    if any(p in msg for p in ["almo", "pausa", "comer"]):
        if "volt" not in msg: return "almoco"
    if any(p in msg for p in ["volta do", "retorn", "voltei", "voltand"]) or ("volta" in msg and len(msg) < 15):
        return "volta"
    if any(p in msg for p in ["fim", "espedi", "expedi", "encer", "tchau", "finali", "termin"]): return "fim"
    return None

def obter_parceiros(nome_remetente):
    nome_remetente_upper = nome_remetente.upper()
    for equipe, membros in EQUIPES.items():
        if any(membro in nome_remetente_upper or nome_remetente_upper in membro for membro in membros):
            return membros
    return [nome_remetente]

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Filtros")
    arquivo_upload = st.file_uploader("1. Carregue o arquivo conversa.txt", type="txt")
    
    # Filtro de Data
    st.markdown("---")
    st.subheader("2. Selecione o Dia")
    filtro_data = st.date_input("Escolha uma data para filtrar", value=None)
    if st.button("Limpar Filtro de Data"):
        st.rerun()

# --- PROCESSAMENTO ---
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
            membros_equipe = obter_parceiros(u_func)
            for funcionario in membros_equipe:
                chave = (u_data, funcionario)
                if chave not in tabela_ponto:
                    tabela_ponto[chave] = {"Início": "--", "Almoço": "--", "Volta": "--", "Fim": "--"}
                col_map = {"inicio": "Início", "almoco": "Almoço", "volta": "Volta", "fim": "Fim"}
                tabela_ponto[chave][col_map[cat]] = hora_f

    if tabela_ponto:
        dados_lista = []
        for (data, func), pontos in tabela_ponto.items():
            h_ini = converter_para_hora(pontos["Início"])
            h_alm = converter_para_hora(pontos["Almoço"])
            h_vlt = converter_para_hora(pontos["Volta"])
            h_fim = converter_para_hora(pontos["Fim"])
            dur_alm = calcular_diferenca(h_vlt, h_alm)
            total_trabalhado = "--"
            if h_ini and h_fim:
                total_delta = h_fim - h_ini
                if h_vlt and h_alm: total_delta -= (h_vlt - h_alm)
                seg = int(total_delta.total_seconds())
                if seg > 0: total_trabalhado = f"{seg // 3600:02d}h {(seg % 3600) // 60:02d}m"

            data_obj = datetime.strptime(data, "%d/%m/%Y")
            dados_lista.append({
                "Data_Obj": data_obj, "Data_Filtro": data_obj.date(), "Data": data, "Funcionário": func,
                **pontos, "Intervalo": dur_alm, "Total Líquido": total_trabalhado
            })
        
        df_completo = pd.DataFrame(dados_lista).sort_values(by=["Data_Obj", "Funcionário"])
        
        # APLICAÇÃO DO FILTRO DE DATA
        if filtro_data:
            df_final = df_completo[df_completo["Data_Filtro"] == filtro_data].copy()
            st.success(f"Exibindo registros de: {filtro_data.strftime('%d/%m/%Y')}")
        else:
            df_final = df_completo.copy()
            st.info("Exibindo todos os dias encontrados. Use o calendário na lateral para filtrar.")

        df_final = df_final.drop(columns=["Data_Obj", "Data_Filtro"])

        # EXIBIÇÃO
        st.subheader("📋 Tabela de Registros")
        st.dataframe(df_final, use_container_width=True)

        st.subheader("✂️ Bloco de Cópia (Pronto para Sheets)")
        buffer_copia = "Data\tFuncionario\tInicio\tAlmoco\tVolta\tFim\tIntervalo\tTotal\n"
        for _, row in df_final.iterrows():
            buffer_copia += f"{row['Data']}\t{row['Funcionário']}\t{row['Início']}\t{row['Almoço']}\t{row['Volta']}\t{row['Fim']}\t{row['Intervalo']}\t{row['Total Líquido']}\n"
        
        st.text_area("Selecione tudo abaixo para copiar:", buffer_copia, height=200)
    else:
        st.warning("Nenhum dado de ponto reconhecido no arquivo.")
else:
    st.info("Por favor, faça o upload do arquivo conversa.txt na barra lateral.")
                                                    
