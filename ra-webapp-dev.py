import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard de Produção", layout="wide")

# ====================================================================
# [MODIFICADO] FUNÇÃO PARA CARREGAR DADOS DA GOOGLE SHEET
# ====================================================================

# Coloque o ID da sua Google Sheet pública aqui
# (O ID é a string longa na URL, entre "/d/" e "/edit")
GOOGLE_SHEET_ID = "1fKPv_AYEzi5YrM9m_vLrg8dkWLs0X1QoKD0LJTIjWMs" 

# Lista padrão de estágios em ordem
ESTAGIOS_PADRAO = [
    "venda/reserva", "enviado para fabricação", "Fila Produção", 
    "produção", "pronto envio", "enviado loja", 
    "recebido loja", "entrega cliente"
]

# Ícones para cada estágio
estagio_icons = {
    "venda/reserva": "🛒",
    "enviado para fabricação": "🏭",
    "Fila Produção": "⏳",
    "produção": "🔧",
    "pronto envio": "📦",
    "enviado loja": "🚚",
    "recebido loja": "🏬",
    "entrega cliente": "🎯",
}

def get_google_sheet_url(sheet_id, sheet_name):
    """Cria a URL de download CSV para uma aba específica."""
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

@st.cache_data(ttl=600) # Armazena os dados por 10 minutos
def load_data_from_google_sheet(sheet_id):
    """
    Carrega os dados das abas 'Pedidos' e 'Itens' e os transforma
    no formato de DataFrame complexo que o dashboard espera.
    """
    url_pedidos = get_google_sheet_url(sheet_id, "Pedidos")
    url_itens = get_google_sheet_url(sheet_id, "Itens")
    
    try:
        df_pedidos = pd.read_csv(url_pedidos)
        df_itens = pd.read_csv(url_itens)
    except Exception as e:
        st.error(f"Erro ao ler a Google Sheet. Verifique o ID e se as abas 'Pedidos' e 'Itens' existem. Erro: {e}")
        return pd.DataFrame()

    # --- [AJUSTE 1] Tratamento de Duplicatas e Tipos ---
    # Converte NFs para string em ambos os DFs ANTES de qualquer operação
    # .str.strip() remove espaços em branco (ex: " 123 " vira "123")
    df_pedidos['NF'] = df_pedidos['NF'].astype(str).str.strip()
    df_itens['NF'] = df_itens['NF'].astype(str).str.strip()

    # Garante que estamos usando apenas a ÚLTIMA linha de um pedido (NF)
    # Se uma NF for inserida duas vezes, a última (mais abaixo na planilha) será usada
    df_pedidos = df_pedidos.drop_duplicates(subset=['NF'], keep='last')
    
    # --- 1. Processar Status (Com base no 'Estagio_Atual') ---
    
    def build_status_lists(row):
        estagio_atual_nome = row["Estagio_Atual"]
        estagios = ESTAGIOS_PADRAO.copy()
        status_list = []
        
        try:
            current_index = estagios.index(estagio_atual_nome)
        except ValueError:
            # Se o nome do estágio estiver errado na planilha, marca tudo como pendente
            return estagios, ["pendente"] * len(estagios)
        
        for i in range(len(estagios)):
            if i < current_index:
                status_list.append("completado")
            elif i == current_index:
                status_list.append("atual")
            else:
                status_list.append("pendente")
        
        return estagios, status_list

    status_data = df_pedidos.apply(build_status_lists, axis=1, result_type='expand')
    df_pedidos['estagio'] = status_data[0]
    df_pedidos['status'] = status_data[1]

    # --- 2. Processar Endereços (Combinar colunas em um dict) ---
    def create_endereco_dict(row):
        return {
            "tipo": row["Endereco_Tipo"],
            "rua": row["Endereco_Rua"],
            "bairro": row["Endereco_Bairro"]
        }
    df_pedidos["endereco"] = df_pedidos.apply(create_endereco_dict, axis=1)
    
    # --- 3. Processar Itens (Agrupar e converter para lista de dicts) ---
    # A conversão de tipo já foi feita no [AJUSTE 1]
    
    itens_agrupados = df_itens.groupby('NF').apply(lambda x: x.to_dict('records')).reset_index(name='itens')
    
    # --- 4. Juntar Pedidos com Itens ---
    df_final = pd.merge(df_pedidos, itens_agrupados, on="NF", how="left")
    
    # Preenche 'itens' vazios com uma lista vazia para evitar erros
    df_final['itens'] = df_final['itens'].apply(lambda x: x if isinstance(x, list) else [])
    
    return df_final

# ====================================================================
# FIM DA FUNÇÃO DE CARREGAMENTO
# ====================================================================


# --- CSS (Sem alterações) ---
st.markdown(
    """
    <style>
        body { background-color: #f7f7f7; color: #333; }
        .header-container { background-color: #002a5c; color: white; padding: 1rem 2rem; border-radius: 8px; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .header-pedido { font-size: 1.2rem; font-weight: bold; }
        .header-links { font-size: 0.9rem; font-weight: 500; }
        .header-links span { margin-left: 2rem; }
        .greeting { font-size: 2rem; font-weight: bold; color: #1976d2; margin-top: 1.5rem; }
        .status-message { font-size: 1.1rem; color: #555; margin-bottom: 2rem; }
        .stepper-container { position: relative; display: flex; justify-content: space-between; padding: 2rem 0; width: 100%; }
        .stepper-line { position: absolute; top: 30px; left: 0; right: 0; height: 5px; background: #e0e0e0; z-index: 1; }
        .stepper-line-progress { position: absolute; top: 30px; left: 0; height: 5px; background: #8bc34a; z-index: 2; width: 0%; transition: width 0.5s ease; }
        .step { display: flex; flex-direction: column; align-items: center; text-align: center; z-index: 3; width: 100px; }
        .step-icon { width: 60px; height: 60px; border-radius: 50%; display: grid; place-items: center; font-size: 1.8rem; font-weight: bold; background: #f7f7f7; color: white; border: 5px solid #e0e0e0; transition: all 0.3s ease; }
        .step-label { font-size: 0.75rem; font-weight: 600; margin-top: 0.75rem; color: #777; }
        .step-icon.pending { background-color: #e0e0e0; border-color: #e0e0e0; color: #fff; }
        .step.pending .step-label { color: #aaa; }
        .step-icon.completed, .step-icon.current { background-color: #8bc34a; border-color: #8bc34a; color: #fff; }
        .step.completed .step-label, .step.current .step-label { color: #333; font-weight: 700; }
        .resumo-card { background-color: #fff; border-radius: 0.75rem; box-shadow: 0 4px 10px rgba(0,0,0,0.05); padding: 1.5rem; margin-top: 1rem; width: 100%; border: 1px solid #eee; }
        .resumo-item { font-size: 0.9rem; margin: 6px 0; }
        .section-header { font-size: 1rem; font-weight: 700; color: #1976d2; text-transform: uppercase; margin-top: 2.5rem; margin-bottom: 0.5rem; padding-bottom: 5px; border-bottom: 2px solid #eee; }
        .address-line { font-size: 0.95rem; color: #333; line-height: 1.6; }
        .item-layout { display: flex; align-items: center; gap: 1.5rem; }
        .item-image img { width: 120px; height: 120px; object-fit: cover; border-radius: 8px; border: 1px solid #eee; }
        .item-details { flex: 1; }
        .item-title { font-size: 1.1rem; font-weight: 700; color: #111; }
        .item-spec, .item-quantity { font-size: 0.9rem; color: #555; margin-top: 0.5rem; }
        .item-price { font-size: 1rem; font-weight: 700; color: #333; margin-top: 0.75rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Carrega os dados da Google Sheet ---
df = load_data_from_google_sheet(GOOGLE_SHEET_ID)

# --- Filtro no Sidebar ---
if not df.empty:
    # Ordena as NFs para melhor seleção, pode remover se preferir a ordem da planilha
    nf_options = sorted(df["NF"].unique())
    nf_filtro = st.sidebar.selectbox("Selecionar NF", options=nf_options)
else:
    st.sidebar.error("Não foi possível carregar dados da Google Sheet.")
    st.stop() # Para a execução se os dados não forem carregados


# --- Filtragem ---
# Graças ao [AJUSTE 1], o 'df' já contém apenas NFs únicas (a última de cada)
# Então o 'iloc[0]' sempre pegará o registro correto e mais atualizado.
registro = df[df["NF"] == nf_filtro]

if not registro.empty:
    estagios = registro.iloc[0]["estagio"]
    status = registro.iloc[0]["status"]
    cliente = registro.iloc[0]["Cliente"]
    valor_total = registro.iloc[0]["Valor_Total"] # Nome da coluna da Sheet
    
    endereco = registro.iloc[0]["endereco"]
    itens = registro.iloc[0]["itens"]
    primeiro_item_nome = itens[0]['nome'] if itens else "N/A" 

    # 1. Renderiza o Header Azul
    st.markdown(
        f"""
        <div class="header-container">
            <div class="header-pedido">N° do Pedido: {nf_filtro}</div>
            <div class="header-links">
                <span>MEUS PEDIDOS</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 2. Encontra o estágio atual para a mensagem
    total_steps = len(status)
    current_index = 0
    current_stage_name = "Processo Iniciado"
    if "atual" in status:
        current_index = status.index("atual")
        current_stage_name = estagios[current_index]
    elif "completado" in status:
        current_index = status.count("completado") - 1
        current_stage_name = estagios[current_index]
        if current_index == total_steps - 1:
             current_stage_name = "Pedido Entregue"

    # 3. Renderiza a Saudação e a Mensagem de Status
    st.markdown(f'<div class="greeting">Olá, {cliente}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="status-message">Seu pedido já está em: <strong>{current_stage_name}</strong>. Acompanhe abaixo!</p>', unsafe_allow_html=True)

    # 4. Calcula a % da linha de progresso
    progress_line_pct = (current_index / (total_steps - 1)) * 100 if total_steps > 1 else 0

    # 5. Renderiza o "Stepper"
    stepper_html = f"""
        <div class="stepper-container">
            <div class="stepper-line"></div>
            <div class="stepper-line-progress" style="width: {progress_line_pct}%;"></div>
    """
    for e, s in zip(estagios, status):
        classe = "completed" if s == "completado" else ("current" if s == "atual" else "pending")
        icone = estagio_icons.get(e, "❓")
        stepper_html += f"""
        <div class="step {classe}">
            <div class="step-icon {classe}">
                {icone}
            </div>
            <div class="step-label">{e}</div>
        </div>
        """
    stepper_html += "</div>"
    st.markdown(stepper_html, unsafe_allow_html=True)
    
    # 7. Cards de Endereço e Resumo
    col1, col2 = st.columns(2)
    
    with col2:
        # Card de Endereço
        html_endereco = f"""
        <div class="section-header">ENDEREÇO DE ENTREGA</div>
        <div class="resumo-card">
            <div class="address-line"><strong>{endereco['tipo']}</strong></div>
            <div class="address-line">{endereco['rua']}</div>
            <div class="address-line">{endereco['bairro']}</div>
            </div>
        </div>
        """
        st.markdown(html_endereco, unsafe_allow_html=True)
    
    # --- [AJUSTE 2] Card de Resumo do Status ---
    with col1:
        # Formata o valor para o padrão BRL (R$ 1.234,56)
        # Tive que usar .replace() pois o f-string format :.2f usa o padrão americano
        valor_formatado = f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        html_status = f"""
        <div class="section-header">RESUMO DO PEDIDO</div>
        <div class="resumo-card">
            <div class="resumo-item" style="font-size: 1rem; margin-bottom: 12px;">
                <strong>Último Status:</strong> 
                <span style="color: #1976d2; font-weight: 700;">{current_stage_name}</span>
            </div>
        </div>
        """
        st.markdown(html_status, unsafe_allow_html=True)

    # Card de Itens
    st.markdown('<div class="section-header">ITENS DA ENTREGA</div>', unsafe_allow_html=True)
    
    if not itens:
        st.markdown('<div class="resumo-card"><div class="address-line">Nenhum item encontrado para este pedido.</div></div>', unsafe_allow_html=True)
    
    for item in itens:
        valor_total_item = item['qtd'] * item['valor_unit']
        # Formata o valor do item
        valor_item_formatado = f"R$ {valor_total_item:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        item_html = f"""
        <div class="resumo-card">
            <div class="item-layout">
                <div class="item-image">
                    <img src="{item['img_url']}" alt="{item['nome']}">
                </div>
                <div class="item-details">
                    <div class="item-title">{item['nome']}</div>
                    <div class="item-spec">Cor: {item['cor']}</div>
                    <div class="item-spec">Tamanho: {item['tamanho']}</div>
                    <div class="item-quantity">Quantidade: {item['qtd']}</div>
                    <div class="item-price">Valor dos produtos: {valor_item_formatado}</div>
                </div>
            </div>
        </div>
        """
        st.markdown(item_html, unsafe_allow_html=True)

else:
    st.warning("Nenhum registro encontrado com a NF selecionada.")

# streamlit run ra-webapp-dev.py
