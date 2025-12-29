import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime

st.set_page_config(page_title="Gestor de Ponto Inteligente", layout="wide")

st.title("📊 Gestor de Ponto - WhatsApp")
st.markdown("Sistema personalizado para a equipe de técnicos.")

# --- LISTA DE TÉCNICOS CADASTRADOS ---
LISTA_FUNCIONARIOS = [
    "JOAO EUDES DE SOUSA",
    "JOSE HELDER DA SILVA",
    "JOSE ALVES BARBOSA JÚNIOR",
    "RYAN",
    "ROBERTO SÉRGIO DOS SANTOS",
    "JOSEMBERG PAULO DA SILVA",
    "LUIZ CARLOS SILVA DOS SANTOS",
    "ANTÔNIO DAVID SERAFIM VIEIRA",
    "EDIGLEYSTON",
    "RAPHAEL"
]

def converter_para_hora(texto_hora):
    try:
        if texto_hora and texto_hora != "--":
            return datetime.strptime(texto_hora, "%H:%M:%S")
    except:
        return None
    return None

def calcular_diferenca(hora_fim, hora_inicio):
    if hora_fim and hora_inicio:
        diff = hora_fim - hora_inicio
        total_segundos = int(diff.total_seconds())
        if total_segundos < 0: return "--"
        horas = total_segundos // 3600
        minutos = (total_segundos % 3600) // 60
        return f"{horas:02d}h {minutos:02d}m"
    return "--"

def formatar_hora_padrao(texto, hora_envio):
    match = re.search(r"(\d{1,2})[:hH](\d{2})", texto)
    if match:
        return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}:00"
    return f"{hora_envio}:00"

def identificar_categoria(texto):
    msg = texto.lower().strip()
    if any(p in msg for p in ["inic", "chegu", "comec", "inici"]): return "inicio"
    if any(p in msg for p in ["almo", "pausa", "comer"]):
        if "volt" not in msg: return "almoco"
    if any(p in msg for p in ["volta do", "retorn", "voltei", "voltand"]) or ( "volta" in msg and len(msg) < 15):
        return "volta"
    if any(p in msg for p in ["fim", "espedi", "expedi", "encer", "tchau", "finali", "termin"]): return "fim"
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
            
            # Identifica se a mensagem cita algum técnico da lista (equipe)
            mencionados = [f for f in LISTA_FUNCIONARIOS if f.split()[0].lower() in texto_analise.lower()]
            equipe = mencionados if mencionados else [u_func]
            
            for func_nome in equipe:
                # Padroniza o nome para o formato oficial da lista se houver correspondência parcial
                nome_oficial = next((f for f in LISTA_FUNCIONARIOS if f.lower() in func_nome.lower() or func_nome.lower() in f.lower()), func_nome)
                
                chave = (u_data, nome_oficial)
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
                if h_vlt and h_alm:
                    total_delta -= (h_vlt - h_alm)
                
                seg = int(total_delta.total_seconds())
                if seg > 0:
                    total_trabalhado = f"{seg // 3600:02d}h {(seg % 3600) // 60:02d}m"

            data_obj = datetime.strptime(data, "%d/%m/%Y")
            dados_lista.append({
                "Data_Obj": data_obj, "Data": data, "Funcionário": func,
                **pontos, "Almoço(Tempo)": dur_alm, "Total Líquido": total_trabalhado
            })
        
        df = pd.DataFrame(dados_lista).sort_values(by=["Data_Obj", "Funcionário"]).drop(columns=["Data_Obj"])
        st.subheader("📋 Relatório de Ponto - Equipe Técnica")
        st.dataframe(df, use_container_width=True)

        # Botão de Cópia
        buffer_copia = "Data\tFuncionario\tInicio\tAlmoco\tVolta\tFim\tIntervalo\tTotal\n"
        for _, row in df.iterrows():
            buffer_copia += f"{row['Data']}\t{row['Funcionário']}\t{row['Início']}\t{row['Almoço']}\t{row['Volta']}\t{row['Fim']}\t{row['Almoço(Tempo)']}\t{row['Total Líquido']}\n"
        
        st.text_area("Copie para o Sheets (Ctrl+A, Ctrl+C):", buffer_copia, height=200)
    else:
        st.info("Aguardando upload do arquivo para processar o ponto dos técnicos.")
        
