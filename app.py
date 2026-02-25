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
                    
                    # 1. Tabelas Base
                    tabela_qtd = pd.pivot_table(df, values=col_qtd, index=col_sku, columns='Semana', aggfunc='sum', fill_value=0).astype(int)
                    tabela_rec = pd.pivot_table(df, values=col_receita, index=col_sku, columns='Semana', aggfunc='sum', fill_value=0)
                    
                    tabela_qtd['Total do Mês'] = tabela_qtd.sum(axis=1)
                    tabela_rec['Total do Mês'] = tabela_rec.sum(axis=1)

                    # 2. Cálculo da Curva ABC
                    tabela_abc = pd.DataFrame(index=tabela_rec.index)
                    colunas_analise = [c for c in tabela_rec.columns if str(c).startswith('Semana')] + ['Total do Mês']
                    
                    for col in colunas_analise:
                        serie_ord = tabela_rec[col].sort_values(ascending=False)
                        soma_total = serie_ord.sum()
                        
                        if soma_total > 0:
                            cum_pct = serie_ord.cumsum() / soma_total
                            def get_curva(p):
                                if p <= 0.80: return 'A'
                                elif p <= 0.95: return 'B'
                                else: return 'C'
                            mapa_curva = cum_pct.apply(get_curva)
                            tabela_abc[f"Curva {col}" if 'Semana' in col else "Curva do Mês"] = tabela_abc.index.map(mapa_curva)
                        else:
                            tabela_abc[f"Curva {col}" if 'Semana' in col else "Curva do Mês"] = '-'
                            
                    # 3. Adiciona TOTAL GERAL
                    tabela_qtd.loc['TOTAL GERAL'] = tabela_qtd.sum(axis=0)
                    tabela_rec.loc['TOTAL GERAL'] = tabela_rec.sum(axis=0)
                    
                    # 4. Cálculo de Deltas e Formatação
                    def formatar_brl(valor):
                        return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

                    def calcular_deltas(df_pivot, is_currency=False):
                        df_calc = df_pivot.copy() 
                        df_format = df_pivot.copy() 
                        
                        semanas = [c for c in df_pivot.columns if str(c).startswith('Semana')]
                        semanas = sorted(semanas)
                        cols_finais = [semanas[0]]
                        
                        if is_currency:
                            df_format[semanas[0]] = df_calc[semanas[0]].apply(formatar_brl)
                            df_format['Total do Mês'] = df_calc['Total do Mês'].apply(formatar_brl)
                        
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
                            
                        cols_finais.append('Total do Mês')
                        return df_format[cols_finais]

                    tabela_qtd_final = calcular_deltas(tabela_qtd, is_currency=False)
                    tabela_rec_final = calcular_deltas(tabela_rec, is_currency=True)
                    
                    # 5. Estilização Visual
                    def aplicar_estilos_deltas(df_estilo):
                        estilos = pd.DataFrame('', index=df_estilo.index, columns=df_estilo.columns)
                        for col in df_estilo.columns:
                            if isinstance(col, str) and col.startswith('Δ'):
                                for idx in df_estilo.index:
                                    if idx != 'TOTAL GERAL':
                                        val = df_estilo.at[idx, col]
                                        if isinstance(val, str):
                                            if val.startswith('+') and val != '+0.0%':
                                                estilos.at[idx, col] = 'color: #15803d; font-weight: bold;'
                                            elif val.startswith('-'):
                                                estilos.at[idx, col] = 'color: #b91c1c; font-weight: bold;'
                        
                        if 'TOTAL GERAL' in df_estilo.index:
                            estilos.loc['TOTAL GERAL', :] = 'background-color: #f1f5f9; color: #000000; font-weight: bold;'
                        return estilos
                        
                    def aplicar_estilos_abc(df_estilo):
                        estilos = pd.DataFrame('', index=df_estilo.index, columns=df_estilo.columns)
                        for col in df_estilo.columns:
                            for idx in df_estilo.index:
                                val = df_estilo.at[idx, col]
                                if val == 'A': estilos.at[idx, col] = 'color: #15803d; font-weight: bold;' # Verde
                                elif val == 'B': estilos.at[idx, col] = 'color: #a16207; font-weight: bold;' # Amarelo escuro
                                elif val == 'C': estilos.at[idx, col] = 'color: #b91c1c; font-weight: bold;' # Vermelho
                        return estilos

                    # 6. Renderização das Abas
                    st.success(f"Análise concluída! Foram processadas {len(df)} vendas no período.")
                    aba1, aba2, aba3 = st.tabs(["📦 Volume de Vendas", "💰 Faturamento", "📈 Evolução Curva ABC"])
                    
                    with aba1:
                        st.dataframe(tabela_qtd_final.style.apply(aplicar_estilos_deltas, axis=None), use_container_width=True)
                        
                    with aba2:
                        st.dataframe(tabela_rec_final.style.apply(aplicar_estilos_deltas, axis=None), use_container_width=True)
                        
                    with aba3:
                        # Filtro interativo de Curva ABC
                        curvas_disponiveis = sorted([c for c in tabela_abc['Curva do Mês'].unique() if c != '-'])
                        curvas_selecionadas = st.multiselect("Filtrar por Curva Final do Mês:", options=curvas_disponiveis, default=curvas_disponiveis)
                        
                        tabela_abc_filtrada = tabela_abc[tabela_abc['Curva do Mês'].isin(curvas_selecionadas)]
                        st.dataframe(tabela_abc_filtrada.style.apply(aplicar_estilos_abc, axis=None), use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
