import streamlit as st
import pandas as pd
import math

# Função para carregar os dados dos arquivos de Excel
def carregar_dados():
    dados_vendas = st.file_uploader("Carregar arquivo de vendas", type=["xlsx"])
    config_estoque = st.file_uploader("Carregar arquivo de configuração", type=["xlsx"])
    config_limite = st.file_uploader("Carregar arquivo de limite", type=["xlsx"])
    stock_manual = st.file_uploader("Carregar arquivo de stock manual", type=["xlsx"])

    if dados_vendas and config_estoque and config_limite and stock_manual:
        return (pd.read_excel(dados_vendas),
                pd.read_excel(config_estoque),
                pd.read_excel(config_limite),
                pd.read_excel(stock_manual))
    else:
        return None, None, None, None

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

# Aplicar o cálculo do stock máximo e a classificação ABCDEF para cada armazém
def calcular_resultados(dados_vendas, config_estoque, config_limite, stock_manual):
    for armazem, tipo in tipo_armazem.items():
        dados_vendas[f'ABC {armazem}'] = dados_vendas[armazem].apply(lambda x: obter_abcdef(x, config_estoque, 'Normal'))
        dados_vendas[f'{armazem} SM'] = dados_vendas.apply(
            lambda row: calcular_stock_maximo(row, config_estoque, armazem, tipo, config_limite, stock_manual), axis=1
        )
    return dados_vendas

# Interface do Streamlit
def main():
    st.title("Cálculo de Stock Máximo")
    
    dados_vendas, config_estoque, config_limite, stock_manual = carregar_dados()
    
    if dados_vendas is not None and config_estoque is not None and config_limite is not None and stock_manual is not None:
        st.write("Dados carregados com sucesso!")
        resultados = calcular_resultados(dados_vendas, config_estoque, config_limite, stock_manual)
        st.write(resultados)
        
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
