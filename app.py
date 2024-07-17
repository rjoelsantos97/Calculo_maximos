import pandas as pd
import math
import streamlit as st

# Função para arredondar para o próximo múltiplo de uma quantidade específica
def arredondar_excesso(valor, multiplo):
    if multiplo == 0:
        return valor
    return math.ceil(valor / multiplo) * multiplo

# Função para obter a classificação ABCDEF a partir do arquivo de configuração
def obter_abcdef(vendas_armazem, config_estoque, tipo):
    config_tipo = config_estoque[config_estoque['Tipo'] == tipo]
    for _, config in config_tipo.iterrows():
        if vendas_armazem >= int(config['Vendas']):
            return config['ABC']
    return 'F'  # Retorna 'F' se nenhuma condição for atendida

# Função para obter a configuração correta de acordo com as vendas e o tipo (Normal/Direto)
def obter_configuracao_estoque(vendas_armazem, config_estoque, tipo):
    config_tipo = config_estoque[config_estoque['Tipo'] == tipo]
    for _, config in config_tipo.iterrows():
        if vendas_armazem >= int(config['Vendas']):
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

# Configuração do Streamlit
st.title('Gestão de Stock')

# Carregar os arquivos
st.sidebar.title('Carregar Arquivos')
uploaded_vendas = st.sidebar.file_uploader("Carregar ficheiro de vendas", type=['xlsx'])
uploaded_configuracao = st.sidebar.file_uploader("Carregar ficheiro de configuração", type=['xlsx'])
uploaded_limite = st.sidebar.file_uploader("Carregar ficheiro de limite", type=['xlsx'])
uploaded_stock_manual = st.sidebar.file_uploader("Carregar ficheiro de stock manual", type=['xlsx'])

if uploaded_vendas and uploaded_configuracao and uploaded_limite and uploaded_stock_manual:
    dados_vendas = pd.read_excel(uploaded_vendas)
    config_estoque = pd.read_excel(uploaded_configuracao)
    config_limite = pd.read_excel(uploaded_limite)
    stock_manual = pd.read_excel(uploaded_stock_manual)
    
    # Converter colunas 'Vendas' para int, ignorando erros
    config_estoque['Vendas'] = pd.to_numeric(config_estoque['Vendas'], errors='coerce').fillna(0).astype(int)
    config_limite['Vendas'] = pd.to_numeric(config_limite['Vendas'], errors='coerce').fillna(0).astype(int)
    
    # Mostrar os dados carregados
    st.subheader('Dados de Vendas')
    st.dataframe(dados_vendas)
    st.subheader('Configuração de Estoque')
    st.dataframe(config_estoque)
    st.subheader('Limite de Estoque')
    st.dataframe(config_limite)
    st.subheader('Stock Manual')
    st.dataframe(stock_manual)
    
    # Verificar Tipodesc no ficheiro de vendas que não estão no ficheiro de limite
    tipodesc_nao_encontrados = dados_vendas[~dados_vendas['Tipodesc'].isin(config_limite['Tipodesc'])]['Tipodesc'].unique()
    if len(tipodesc_nao_encontrados) > 0:
        st.warning(f"Tipodesc não encontrados no ficheiro de limite: {', '.join(tipodesc_nao_encontrados)}")

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

    # Aplicar o cálculo do stock máximo e a classificação ABCDEF para cada armazém
    for armazem, tipo in tipo_armazem.items():
        dados_vendas[f'ABCDEF_{armazem}'] = dados_vendas[armazem].apply(lambda x: obter_abcdef(x, config_estoque, 'Normal'))
        dados_vendas[f'Stock_Maximo_{armazem}'] = dados_vendas.apply(
            lambda row: calcular_stock_maximo(row, config_estoque, armazem, tipo, config_limite, stock_manual), axis=1
        )

    # Exibir resultados
    st.subheader('Resultados')
    st.dataframe(dados_vendas)

    # Download dos resultados
    st.download_button(
        label="Download resultados",
        data=dados_vendas.to_csv(index=False),
        file_name='resultado_stocks_maximos.csv',
        mime='text/csv'
    )

    # Editar a configuração de estoque
    st.subheader('Editar Configuração de Estoque')
    edited_config_estoque = st.experimental_data_editor(config_estoque)
    st.write('Configuração de Estoque editada:')
    st.dataframe(edited_config_estoque)

    # Download da configuração de estoque editada
    st.download_button(
        label="Download configuração editada",
        data=edited_config_estoque.to_csv(index=False),
        file_name='configuracao_estoque_editada.csv',
        mime='text/csv'
    )
else:
    st.sidebar.warning("Por favor, carregue todos os arquivos necessários.")
