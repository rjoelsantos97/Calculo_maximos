import streamlit as st
import pandas as pd
import math

# Função para carregar os dados dos arquivos de Excel
@st.cache_data
def carregar_dados(file_vendas, file_config_estoque, file_config_limite, file_stock_manual):
    dados_vendas = pd.read_excel(file_vendas)
    config_estoque = pd.read_excel(file_config_estoque)
    config_limite = pd.read_excel(file_config_limite)
    stock_manual = pd.read_excel(file_stock_manual)
    return dados_vendas, config_estoque, config_limite, stock_manual

# Mapeamento dos tipos de armazém para cada cidade
tipo_armazem = {
    'Braga': 'Local',
    'Porto': 'Local',
    'Coimbra': 'Local',
    'Lisboa': 'Regional',
    'SMFeira': 'Central',
    'Lousada': 'Local',
    'Seixal': 'Local',
    'Albergaria': 'Local',
    'Sintra': 'Local'
}

# Função para arredondar para o próximo múltiplo de uma quantidade específica
def arredondar_excesso(valor, multiplo):
    if multiplo == 0:
        return valor
    return math.ceil(valor / multiplo) * multiplo

# Função para obter a classificação ABCDEF a partir do arquivo de configuração
def obter_abcdef(vendas_armazem, config_estoque, tipo):
    config_tipo = config_estoque[config_estoque['Tipo'] == tipo]
    for _, config in config_tipo.iterrows():
        if vendas_armazem >= config['Vendas']:
            return config['ABC']
    return 'F'  # Retorna 'F' se nenhuma condição for atendida

# Função para obter a configuração correta de acordo com as vendas e o tipo (Normal/Direto)
def obter_configuracao_estoque(vendas_armazem, config_estoque, tipo):
    config_tipo = config_estoque[config_estoque['Tipo'] == tipo]
    for _, config in config_tipo.iterrows():
        if vendas_armazem >= config['Vendas']:
            return config
    return config_tipo.iloc[-1]  # Retorna a última linha se nenhuma condição for atendida

# Função para calcular o stock máximo baseado na lógica fornecida
def calcular_stock_maximo(row, config_estoque, armazem, tipo, config_limite, stock_manual):
    vendas_armazem = row[armazem]
    qtd_veiculo = row['QtVeiculo']
    
    # Verificar se existe um valor de stock manual para esta referência e armazém
    stock_manual_row = stock_manual[stock_manual['RótulosdeLinha'] == row['Rótulos de Linha']]
    if not stock_manual_row.empty:
        stock_manual_valor = stock_manual_row[f'{armazem} SM'].values[0]
        return stock_manual_valor  # Usa o valor do stock manual, mesmo que seja 0
    
    # Verificar se as vendas do armazém são suficientes conforme o limite
    if row['Tipodesc'] not in config_limite['Tipodesc'].values:
        return 0
    vendas_minimas = int(config_limite.loc[config_limite['Tipodesc'] == row['Tipodesc'], armazem].values[0])
    if vendas_armazem < vendas_minimas:
        return 0
    
    # Determinar se é 'Normal' ou 'Direto'
    tipo_config = 'Normal'
    if config_limite.loc[config_limite['Tipodesc'] == row['Tipodesc'], 'Stock Direto'].values[0] == 1:
        tipo_config = 'Direto'
    
    # Obter a configuração correta de acordo com as vendas e o tipo
    config = obter_configuracao_estoque(vendas_armazem, config_estoque, tipo_config)
    
    # Obter a configuração de cálculo (semanas ou unidades)
    if tipo == 'Central':
        valor = config['Central']
        calculo = config['calculo_Central']
    elif tipo == 'Regional':
        valor = config['Regional']
        calculo = config['calculo_Regional']
    elif tipo == 'Local':
        valor = config['Local']
        calculo = config['calculo_Local']
    
    # Definir o valor de estoque com base na configuração
    if tipo_config == 'Direto':
        if calculo == 'sm':
            return arredondar_excesso(vendas_armazem / 52 * valor, qtd_veiculo)
        else:  # 'un'
            return arredondar_excesso(valor, qtd_veiculo)
    
    if armazem == 'SMFeira' and tipo_config == 'Normal':
        total_vendas = sum([row[coluna] for coluna in tipo_armazem])
        if calculo == 'sm':
            return arredondar_excesso(total_vendas / 52 * valor, qtd_veiculo)
        else:  # 'un'
            return arredondar_excesso(valor, qtd_veiculo)
    
    if calculo == 'sm':
        return arredondar_excesso(vendas_armazem / 52 * valor, qtd_veiculo)
    else:  # 'un'
        return arredondar_excesso(valor, qtd_veiculo)

# Aplicar o cálculo do stock máximo e a classificação ABCDEF para cada armazém
@st.cache_data
def calcular_resultados(dados_vendas, config_estoque, config_limite, stock_manual):
    resultados = dados_vendas.copy()
    for armazem, tipo in tipo_armazem.items():
        resultados[f'ABCDEF_{armazem}'] = resultados[armazem].apply(lambda x: obter_abcdef(x, config_estoque, 'Normal'))
        resultados[f'Stock_Maximo_{armazem}'] = resultados.apply(
            lambda row: calcular_stock_maximo(row, config_estoque, armazem, tipo, config_limite, stock_manual), axis=1
        )
        resultados[f'Valor_Stock_{armazem}'] = resultados[f'Stock_Maximo_{armazem}'] * resultados['P5PT']
    return resultados

# Função para mostrar alertas
def mostrar_alertas(dados_vendas, config_limite):
    tipodesc_vendas = set(dados_vendas['Tipodesc'])
    tipodesc_limite = set(config_limite['Tipodesc'])
    diff = tipodesc_vendas - tipodesc_limite
    if diff:
        st.warning(f"As seguintes Tipodesc estão nas vendas mas não no ficheiro limite: {', '.join(diff)}")

# Função para análise dos valores de stock
def analise_valores(resultados):
    st.subheader("Análise de Valores de Stock")
    for armazem in tipo_armazem.keys():
        total_valor = resultados[f'Valor_Stock_{armazem}'].sum()
        st.write(f"Total de Valor de Stock em {armazem}: {total_valor:.2f}")

    st.subheader("Análise de Valores de Stock por ABC")
    for armazem in tipo_armazem.keys():
        st.write(f"Valores de Stock em {armazem} por ABC:")
        abc_valores = resultados.groupby(f'ABCDEF_{armazem}')[f'Valor_Stock_{armazem}'].sum()
        st.write(abc_valores)

# Função para exibir resultados em páginas
def exibir_resultados_paginados(dataframe, page_size=20):
    total_rows = len(dataframe)
    total_pages = (total_rows // page_size) + 1
    page = st.number_input('Página', 1, total_pages, 1)
    start_row = (page - 1) * page_size
    end_row = min(start_row + page_size, total_rows)
    st.write(dataframe[start_row:end_row])

# Interface do Streamlit
def main():
    st.title("Cálculo de Stock Máximo")
    
    dados_vendas, config_estoque, config_limite, stock_manual = carregar_dados()
    
    if dados_vendas is not None and config_estoque is not None and config_limite is not None and stock_manual is not None:
        st.write("Dados carregados com sucesso!")
        mostrar_alertas(dados_vendas, config_limite)
        resultados = calcular_resultados(dados_vendas, config_estoque, config_limite, stock_manual)
        
        # Exibir resultados paginados
        exibir_resultados_paginados(resultados)
        
        # Análise dos valores de stock
        analise_valores(resultados)
        
        # Permitir o download do arquivo de resultados
        csv = resultados.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Baixar resultados",
            data=csv,
            file_name='resultado_stocks_maximos.csv',
            mime='text/csv',
        )
    else:
        st.write("Por favor, carregue todos os arquivos necessários.")

if __name__ == "__main__":
    main()
