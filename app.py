import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Análise Semanal ML", layout="wide")
st.title("Oscilação Semanal de Vendas por SKU")

# Upload do relatório
uploaded_file = st.file_uploader("Arraste o relatório do Mercado Livre (Excel)", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # Lê o arquivo
        df = pd.read_excel(uploaded_file)
        
        # Mapeamento de colunas padrão do ML (Ajuste se o seu relatório vier diferente)
        col_sku = 'SKU'
        col_data = 'Data da venda' # Mercado Livre geralmente usa 'Data da venda' ou 'Data de criação'
        col_qtd = 'Unidades'       # Mercado Livre geralmente usa 'Unidades'

        # Verifica se as colunas existem
        if not all(col in df.columns for col in [col_sku, col_data, col_qtd]):
            st.error(f"Erro: O relatório precisa conter as colunas exatas: '{col_sku}', '{col_data}' e '{col_qtd}'.")
        else:
            # Limpa e converte datas
            df[col_data] = pd.to_datetime(df[col_data]).dt.normalize()
            df = df.dropna(subset=[col_sku])
            
            # Pega o primeiro dia do relatório como Dia 0
            data_inicial = df[col_data].min()
            
            # Cria a marcação de semanas (0-7 dias = Sem 1, 8-14 = Sem 2, etc.)
            df['Dias_Desde_Inicio'] = (df[col_data] - data_inicial).dt.days
            
            # Função para classificar as semanas
            def classificar_semana(dias):
                if dias < 7: return 'Semana 1'
                elif dias < 14: return 'Semana 2'
                elif dias < 21: return 'Semana 3'
                elif dias < 28: return 'Semana 4'
                else: return 'Semana 5+'
                
            df['Semana'] = df['Dias_Desde_Inicio'].apply(classificar_semana)
            
            # Gera a tabela dinâmica (Pivot)
            tabela_semanal = pd.pivot_table(
                df, 
                values=col_qtd, 
                index=col_sku, 
                columns='Semana', 
                aggfunc='sum', 
                fill_value=0
            )
            
            # Exibe os resultados
            st.dataframe(tabela_semanal, use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
