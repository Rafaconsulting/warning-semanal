import streamlit as st
import pandas as pd

st.set_page_config(page_title="Análise Semanal ML", layout="wide")
st.title("Oscilação Semanal de Vendas por SKU")

uploaded_file = st.file_uploader("Arraste o relatório do Mercado Livre (Excel)", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # Lê a planilha inteira sem definir cabeçalho inicialmente
        df_raw = pd.read_excel(uploaded_file, header=None)
        
        # O ML possui linhas mescladas no topo. Vamos descobrir em qual linha está a palavra 'SKU'
        header_row = None
        for i, row in df_raw.iterrows():
            valores_linha = [str(val).strip() for val in row.values]
            if 'SKU' in valores_linha:
                header_row = i
                break
                
        if header_row is None:
            st.error("Erro: Não foi possível encontrar a coluna 'SKU' no relatório.")
        else:
            # Lê o arquivo novamente começando exatamente da linha correta
            df = pd.read_excel(uploaded_file, header=header_row)
            
            col_sku = 'SKU'
            col_data = 'Data da venda' 
            col_qtd = 'Unidades' # O ML tem mais de uma coluna 'Unidades', o pandas pegará a primeira da esquerda (correta)

            if not all(col in df.columns for col in [col_sku, col_data, col_qtd]):
                st.error(f"Erro: O relatório precisa conter as colunas: '{col_sku}', '{col_data}' e '{col_qtd}'.")
            else:
                # Remove linhas onde SKU está vazio (geralmente totais no fim da planilha)
                df = df.dropna(subset=[col_sku])
                
                # Tradutor específico para a data do Mercado Livre Brasil ("25 de fevereiro de 2026 08:46 hs.")
                def limpar_data_ml(data_str):
                    try:
                        partes = str(data_str).lower().split()
                        if len(partes) >= 5:
                            dia = partes[0]
                            mes_texto = partes[2]
                            ano = partes[4]
                            
                            meses = {
                                'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03',
                                'abril': '04', 'maio': '05', 'junho': '06',
                                'julho': '07', 'agosto': '08', 'setembro': '09',
                                'outubro': '10', 'novembro': '11', 'dezembro': '12'
                            }
                            
                            mes = meses.get(mes_texto, '01')
                            return pd.to_datetime(f"{ano}-{mes}-{dia}")
                    except:
                        pass
                    return pd.NaT

                # Aplica o tradutor
                df[col_data] = df[col_data].apply(limpar_data_ml)
                
                # Remove linhas onde a data falhou em ser lida
                df = df.dropna(subset=[col_data]) 
                
                if df.empty:
                    st.warning("Erro: As datas não puderam ser processadas. Verifique a coluna 'Data da venda'.")
                else:
                    # Pega o primeiro dia de venda registrado no relatório para marcar como 'Dia 0'
                    data_inicial = df[col_data].min()
                    df['Dias_Desde_Inicio'] = (df[col_data] - data_inicial).dt.days
                    
                    # Classifica as vendas em semanas a partir da data de início
                    def classificar_semana(dias):
                        if dias < 7: return 'Semana 1'
                        elif dias < 14: return 'Semana 2'
                        elif dias < 21: return 'Semana 3'
                        elif dias < 28: return 'Semana 4'
                        else: return 'Semana 5+'
                        
                    df['Semana'] = df['Dias_Desde_Inicio'].apply(classificar_semana)
                    
                    # Converte unidades para número (para evitar erros se o ML mandar texto)
                    df[col_qtd] = pd.to_numeric(df[col_qtd], errors='coerce').fillna(0)
                    
                    # Cria a Pivot Table cruzando SKU x Semanas x Soma das Unidades
                    tabela_semanal = pd.pivot_table(
                        df, 
                        values=col_qtd, 
                        index=col_sku, 
                        columns='Semana', 
                        aggfunc='sum', 
                        fill_value=0
                    )
                    
                    # Força números inteiros
                    tabela_semanal = tabela_semanal.astype(int)
                    
                    # Interface visual
                    st.success(f"Análise concluída! Foram processadas {len(df)} vendas no período.")
                    st.dataframe(tabela_semanal, use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
