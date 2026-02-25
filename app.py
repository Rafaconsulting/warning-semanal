import streamlit as st
import pandas as pd

st.set_page_config(page_title="Análise Semanal ML", layout="wide")
st.title("Oscilação Semanal de Vendas por SKU")

uploaded_file = st.file_uploader("Arraste o relatório do Mercado Livre (Excel)", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # Lê a planilha inteira sem definir cabeçalho inicialmente
        df_raw = pd.read_excel(uploaded_file, header=None)
        
        # Procura qual linha contém a palavra 'SKU' para definir como cabeçalho
        header_row = None
        for i, row in df_raw.iterrows():
            if 'SKU' in row.values:
                header_row = i
                break
                
        if header_row is None:
            st.error("Erro: Não foi possível encontrar a coluna 'SKU' em nenhuma linha do relatório.")
        else:
            # Lê o arquivo novamente, agora começando da linha correta
            df = pd.read_excel(uploaded_file, header=header_row)
            
            col_sku = 'SKU'
            col_data = 'Data da venda' 
            
            # O ML às vezes traz mais de uma coluna "Unidades". Pegamos a primeira.
            col_qtd = 'Unidades'

            if not all(col in df.columns for col in [col_sku, col_data, col_qtd]):
                st.error(f"Erro: O relatório precisa conter as colunas: '{col_sku}', '{col_data}' e '{col_qtd}'.")
            else:
                # Remove linhas onde SKU está vazio
                df = df.dropna(subset=[col_sku])
                
                # Trata a coluna de data (pega apenas a parte da data, ignorando o horário)
                # Como o ML manda "25 de fevereiro de 2026 08:46 hs.", precisamos limpar
                df[col_data] = df[col_data].astype(str).str.split(' ').str[0:3].str.join(' ')
                
                # Mapeamento de meses em português para inglês para o pandas conseguir ler
                meses_pt_en = {
                    'janeiro': 'January', 'fevereiro': 'February', 'março': 'March',
                    'abril': 'April', 'maio': 'May', 'junho': 'June',
                    'julho': 'July', 'agosto': 'August', 'setembro': 'September',
                    'outubro': 'October', 'novembro': 'November', 'dezembro': 'December',
                    'de': '' # Remove a preposição 'de'
                }
                
                for pt, en in meses_pt_en.items():
                    df[col_data] = df[col_data].str.replace(f' {pt} ', f' {en} ', case=False)
                
                # Converte para formato de data
                df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
                df = df.dropna(subset=[col_data]) # Remove datas inválidas
                
                # Pega o primeiro dia do relatório como Dia 0
                data_inicial = df[col_data].min()
                
                # Cria a marcação de semanas
                df['Dias_Desde_Inicio'] = (df[col_data] - data_inicial).dt.days
                
                def classificar_semana(dias):
                    if dias < 7: return 'Semana 1'
                    elif dias < 14: return 'Semana 2'
                    elif dias < 21: return 'Semana 3'
                    elif dias < 28: return 'Semana 4'
                    else: return 'Semana 5+'
                    
                df['Semana'] = df['Dias_Desde_Inicio'].apply(classificar_semana)
                
                # Converte unidades para número, garantindo que não dê erro de soma
                df[col_qtd] = pd.to_numeric(df[col_qtd], errors='coerce').fillna(0)
                
                # Gera a tabela dinâmica (Pivot)
                tabela_semanal = pd.pivot_table(
                    df, 
                    values=col_qtd, 
                    index=col_sku, 
                    columns='Semana', 
                    aggfunc='sum', 
                    fill_value=0
                )
                
                # Garante que os números apareçam inteiros e não com casas decimais
                tabela_semanal = tabela_semanal.astype(int)
                
                # Exibe os resultados
                st.dataframe(tabela_semanal, use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
