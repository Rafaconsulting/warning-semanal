import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Análise Semanal ML", layout="wide")
st.title("Oscilação Semanal e Deltas por SKU")

uploaded_file = st.file_uploader("Arraste o relatório do Mercado Livre (Excel)", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file, header=None)
        
        header_row = None
        for i, row in df_raw.iterrows():
            valores_linha = [str(val).strip() for val in row.values]
            if 'SKU' in valores_linha:
                header_row = i
                break
                
        if header_row is None:
            st.error("Erro: Não foi possível encontrar a coluna 'SKU' no relatório.")
        else:
            df = pd.read_excel(uploaded_file, header=header_row)
            
            col_sku = 'SKU'
            col_data = 'Data da venda' 
            col_qtd = 'Unidades'
            
            possiveis_receitas = ['Receita (BRL)', 'Total (BRL)', 'Total', 'Receita', 'Valor da venda', 'Faturamento']
            col_receita = next((col for col in possiveis_receitas if col in df.columns), None)

            if not all(col in df.columns for col in [col_sku, col_data, col_qtd]):
                st.error(f"Erro: O relatório precisa conter as colunas: '{col_sku}', '{col_data}' e '{col_qtd}'.")
            elif not col_receita:
                st.error("Erro: Não encontrei a coluna de Receita/Total financeiro no relatório.")
            else:
                df = df.dropna(subset=[col_sku])
                
                def limpar_moeda(val):
                    if isinstance(val, (int, float)): return float(val)
                    val = str(val).replace('R$', '').replace('BRL', '').strip()
                    if '.' in val and ',' in val:
                        val = val.replace('.', '').replace(',', '.')
                    elif ',' in val:
                        val = val.replace(',', '.')
                    try:
                        return float(val)
                    except:
                        return 0.0

                df[col_receita] = df[col_receita].apply(limpar_moeda)
                
                def limpar_data_ml(data_str):
                    try:
                        partes = str(data_str).lower().split()
                        if len(partes) >= 5:
                            dia, mes_texto, ano = partes[0], partes[2], partes[4]
                            meses = {'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03',
                                     'abril': '04', 'maio': '05', 'junho': '06', 'julho': '07', 
                                     'agosto': '08', 'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'}
                            return pd.to_datetime(f"{ano}-{meses.get(mes_texto, '01')}-{dia}")
                    except:
                        pass
                    return pd.NaT

                df[col_data] = df[col_data].apply(limpar_data_ml)
                df = df.dropna(subset=[col_data]) 
                
                if df.empty:
                    st.warning("Erro: Falha ao processar as datas.")
                else:
                    data_inicial = df[col_data].min()
                    df['Dias_Desde_Inicio'] = (df[col_data] - data_inicial).dt.days
                    
                    def classificar_semana(dias):
                        if dias < 7: return 'Semana 1'
                        elif dias < 14: return 'Semana 2'
                        elif dias < 21: return 'Semana 3'
                        elif dias < 28: return 'Semana 4'
                        else: return 'Semana 5+'
                        
                    df['Semana'] = df['Dias_Desde_Inicio'].apply(classificar_semana)
                    df[col_qtd] = pd.to_numeric(df[col_qtd], errors='coerce').fillna(0)
                    
                    tabela_qtd = pd.pivot_table(df, values=col_qtd, index=col_sku, columns='Semana', aggfunc='sum', fill_value=0).astype(int)
                    tabela_rec = pd.pivot_table(df, values=col_receita, index=col_sku, columns='Semana', aggfunc='sum', fill_value=0)
                    
                    def formatar_brl(valor):
                        return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

                    def calcular_deltas(df_pivot, is_currency=False):
                        df_calc = df_pivot.copy() 
                        df_format = df_pivot.copy() 
                        semanas = sorted(df_pivot.columns.tolist())
                        cols_finais = [semanas[0]]
                        
                        if is_currency:
                            df_format[semanas[0]] = df_calc[semanas[0]].apply(formatar_brl)
                        
                        for i in range(1, len(semanas)):
                            s_ant = semanas[i-1]
                            s_atu = semanas[i]
                            delta_col = f"Δ {s_atu}"
                            
                            df_format[delta_col] = np.where(
                                df_calc[s_ant] == 0,
                                np.where(df_calc[s_atu] > 0, 1.0, 0.0),
                                (df_calc[s_atu] - df_calc[s_ant]) / df_calc[s_ant]
                            )
                            
                            df_format[delta_col] = df_format[delta_col].apply(lambda x: f"{x*100:+.1f}%")
                            
                            if is_currency:
                                df_format[s_atu] = df_calc[s_atu].apply(formatar_brl)
                            
                            cols_finais.extend([delta_col, s_atu])
                            
                        return df_format[cols_finais]

                    tabela_qtd_final = calcular_deltas(tabela_qtd, is_currency=False)
                    tabela_rec_final = calcular_deltas(tabela_rec, is_currency=True)
                    
                    # Estilização de cores
                    def colorir_deltas(val):
                        if isinstance(val, str) and '%' in val:
                            if val.startswith('+') and val != '+0.0%':
                                return 'color: #15803d; font-weight: bold;'
                            elif val.startswith('-'):
                                return 'color: #b91c1c; font-weight: bold;'
                        return ''
                    
                    try:
                        styled_qtd = tabela_qtd_final.style.map(colorir_deltas)
                        styled_rec = tabela_rec_final.style.map(colorir_deltas)
                    except AttributeError:
                        styled_qtd = tabela_qtd_final.style.applymap(colorir_deltas)
                        styled_rec = tabela_rec_final.style.applymap(colorir_deltas)
                    
                    st.success(f"Análise concluída! Foram processadas {len(df)} vendas no período.")
                    
                    aba1, aba2 = st.tabs(["📦 Volume de Vendas", "💰 Faturamento Bruto"])
                    
                    with aba1:
                        st.dataframe(styled_qtd, use_container_width=True)
                        
                    with aba2:
                        st.dataframe(styled_rec, use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
