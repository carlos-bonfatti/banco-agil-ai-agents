import os
from uuid import uuid4

import streamlit as st

from banco_agil.bootstrap import build_engine
from banco_agil.domain import DomainError
from banco_agil.presentation import greeting
from banco_agil.privacy import display_message
from banco_agil.session import Session

st.set_page_config(
    page_title="Banco Ágil", page_icon="🏦", layout="wide", initial_sidebar_state="collapsed"
)
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(ellipse at 12% 8%, #D5C9F2 0, transparent 48%),
                    radial-gradient(ellipse at 95% 85%, #CDDFED 0, transparent 50%),
                    linear-gradient(145deg, #E3E6F2, #E9E4F2 55%, #DDE8F0);
        background-attachment: fixed;
    }
    [data-testid="stHeader"] {background: transparent;}
    [data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {
        background: transparent;
    }
    .stMainBlockContainer {max-width: 1120px; padding-top: 2rem; padding-bottom: 6rem;}
    [data-testid="stBottomBlockContainer"] {max-width: 1120px; margin-inline: auto;}
    h1 {font-size: 2.2rem !important; letter-spacing: -0.06rem;}
    [data-testid="stChatMessage"] {border-radius: 20px; padding: 1.1rem;
        border: 1px solid #E1DBED; line-height: 1.6; background: #FFFFFF;
        box-shadow: 0 8px 28px rgba(43, 32, 78, .06);}
    [data-testid="stChatMessageContent"] {min-width: 0; overflow-wrap: anywhere;}
    [data-testid="stChatInput"] {border-radius: 18px; background: #FFFFFF;
        border: 1px solid #D3C9E6; box-shadow: 0 8px 32px rgba(43, 32, 78, .12);}
    [data-testid="stChatInput"]:focus-within {border-color: #5B35D5;
        box-shadow: 0 0 0 3px rgba(91, 53, 213, .13);}
    .stButton button {border-radius: 14px; min-height: 48px; height: auto;
        padding: .75rem 1rem; font-weight: 600; white-space: normal;}
    .stButton button p {white-space: normal; overflow-wrap: anywhere; line-height: 1.4;}
    .stButton button:focus-visible {outline: 3px solid #5B35D5; outline-offset: 3px;}
    .agil-topbar {display: flex; align-items: center; justify-content: space-between;
        gap: 1rem; background: #FFFFFF; padding: 1rem 1.5rem;
        border-radius: 22px 22px 0 0; border: 1px solid #E1DBED;}
    .agil-brand {font-size: 1.25rem; font-weight: 750; color: #302052;
        display: flex; align-items: center; gap: .65rem;}
    .agil-mark {background: #5B35D5; color: #FFFFFF; padding: .3rem .65rem;
        border-radius: 12px; font-size: 1.35rem;}
    .agil-topbar small {color: #62596F; font-size: .85rem;}
    .agil-hero {background: radial-gradient(circle at 90% 10%, #7552D5, transparent 55%),
        linear-gradient(120deg, #302052, #493094);
        box-shadow: 0 14px 36px rgba(48, 32, 82, .14);
        border-radius: 0 0 26px 26px; padding: 2.5rem;
        display: grid; grid-template-columns: 1.4fr 1fr; align-items: center;
        gap: 2.5rem; color: #FFFFFF;}
    .agil-eyebrow {font-size: .75rem; font-weight: 650; letter-spacing: .13rem;
        text-transform: uppercase; color: #DDD0FF;}
    .agil-hero h1 {color: #FFFFFF; font-size: clamp(2.2rem, 4vw, 3.5rem) !important;
        line-height: 1.06; letter-spacing: -.08rem; margin: .8rem 0 1rem; padding: 0;
        overflow-wrap: break-word; height: auto;}
    .agil-hero p {color: #F0EAFE; margin: 0; font-size: 1rem; line-height: 1.6;}
    .agil-start {background: #FFFFFF; padding: 1.6rem; border-radius: 20px;
        color: #231D35; box-shadow: 0 12px 30px rgba(25, 13, 54, .15);}
    .agil-start h2 {color: #231D35; font-size: 1.3rem; margin: 0 0 1rem; padding: 0;}
    .agil-start p {color: #62596F; font-size: .9rem;}
    .agil-start ol {margin: .9rem 0 0; padding-left: 1.2rem; font-size: .9rem;
        line-height: 1.8; color: #413750;}
    [data-testid="stVerticalBlockBorderWrapper"] {border-radius: 18px; background: #FFFFFF;}
    [data-testid="stExpander"] {background: rgba(255, 255, 255, .7);
        border-radius: 14px;}
    @media (max-width: 760px) {
        .stMainBlockContainer {padding-top: 1.5rem; padding-inline: 1rem;}
        h1 {font-size: 1.8rem !important;}
        .agil-topbar {padding: 1rem;}
        .agil-topbar small {font-size: .75rem;}
        .agil-hero {padding: 1.5rem; grid-template-columns: 1fr; gap: 1.4rem;}
        .agil-hero h1 {font-size: 2.2rem !important;}
        [data-testid="stHorizontalBlock"] {flex-wrap: wrap; gap: .75rem;}
        [data-testid="stColumn"] {width: 100% !important; min-width: 0 !important;
            flex: 1 1 100% !important;}
    }
    </style>
    <header class="agil-topbar">
        <div class="agil-brand"><span class="agil-mark" aria-hidden="true">á</span>Banco Ágil</div>
        <small>Atendimento digital · Banco fictício</small>
    </header>
    <section class="agil-hero" aria-label="Apresentação do Banco Ágil">
        <div>
            <div class="agil-eyebrow">Simples de conversar. Fácil de entender.</div>
            <h1>Seu próximo passo.<br>Mais simples.</h1>
            <p>Consulte seu limite, solicite um aumento, atualize seu score
            ou acompanhe o câmbio. Tudo em uma conversa.</p>
        </div>
        <aside class="agil-start" aria-label="Como funciona o atendimento">
            <h2>Um atendimento, do início ao fim.</h2>
            <p>O Assistente Ágil orienta cada etapa. Para experimentar,
            use os dados fictícios disponíveis abaixo.</p>
            <ol><li>Informe CPF e nascimento.</li>
            <li>Escolha o que deseja resolver.</li>
            <li>Acompanhe a resposta na conversa.</li></ol>
        </aside>
    </section>
    """,
    unsafe_allow_html=True,
)
demo_llm = os.getenv("BANCO_LLM_MODE", "demo") == "demo"
demo_fx = os.getenv("BANCO_FX_MODE", "demo") == "demo"
if demo_llm or demo_fx:
    details = []
    if demo_llm:
        details.append("interpretação local")
    if demo_fx:
        details.append("cotações fictícias")
    st.caption("Demonstração · " + " · ".join(details))


@st.cache_resource
def shared_engine(configuration: tuple[str, ...]):
    return build_engine()


engine = shared_engine(
    tuple(
        os.getenv(name, "")
        for name in (
            "BANCO_DATA_DIR",
            "BANCO_LLM_MODE",
            "BANCO_FX_MODE",
            "GEMINI_MODEL",
            "BANCO_MAX_LLM_CALLS_PER_SESSION",
            "BANCO_MAX_LLM_CALLS_PER_ENGINE",
            "BANCO_SESSION_IDLE_SECONDS",
        )
    )
)
if "bank_session" not in st.session_state:
    st.session_state.bank_session = Session()
    st.session_state.messages = [("assistant", greeting())]

session = st.session_state.bank_session
if session.cpf is not None:
    try:
        session.authenticated_cpf()
    except DomainError as exc:
        st.session_state.messages = [("assistant", str(exc))]
        st.session_state.pop("pending_turn", None)

command = None

with st.sidebar:
    st.subheader("Ambiente de avaliação")
    if os.getenv("BANCO_LLM_MODE", "demo") == "demo":
        st.info("Interpretação local de demonstração. Este modo não utiliza um LLM.")
    else:
        st.caption("Interpretação por Gemini; decisões bancárias verificadas em código.")
    if os.getenv("BANCO_FX_MODE", "demo") == "demo":
        st.warning("As cotações exibidas são fictícias.")
    st.write("Cliente fictício: **000.000.000-01**")
    st.write("Nascimento: **01/01/1990**")
    st.caption("Use apenas dados fictícios. Identificadores são ocultados no histórico.")
    if st.button(
        "Encerrar atendimento", disabled=session.stage == "closed", use_container_width=True
    ):
        command = "encerrar atendimento"
    if st.button(
        "Cancelar tarefa",
        disabled=session.stage in {"cpf", "birth", "menu", "closed"},
        use_container_width=True,
    ):
        command = "cancelar tarefa"
    if st.button("Nova conversa", use_container_width=True):
        st.session_state.bank_session.close()
        st.session_state.bank_session = Session()
        st.session_state.messages = [("assistant", greeting())]
        st.session_state.pop("pending_turn", None)
        st.rerun()

labels = {
    "cpf": "Identificação",
    "birth": "Autenticação",
    "menu": "Como podemos ajudar?",
    "amount": "Novo limite",
    "offer_interview": "Atualização de score",
    "income": "Entrevista · 1 de 5",
    "employment": "Entrevista · 2 de 5",
    "expenses": "Entrevista · 3 de 5",
    "dependents": "Entrevista · 4 de 5",
    "debts": "Entrevista · 5 de 5",
    "closed": "Atendimento encerrado",
}
status = (
    "Conversa encerrada"
    if session.stage == "closed"
    else "Identificação em andamento"
    if session.cpf is None
    else "Cliente autenticado"
)
st.caption(status + " · " + labels.get(session.stage, "Atendimento"))
hints = {
    "cpf": "Informe o CPF fictício com ou sem pontuação.",
    "birth": "Exemplos: 01/01/1990 ou 01011990.",
    "amount": "Informe o limite total desejado, como 2.500,00.",
    "income": "Informe a renda mensal, como 5.000,00.",
    "employment": "Responda formal, autônomo ou desempregado.",
    "expenses": "Informe o total mensal, como 2.000,00.",
    "dependents": "Informe um número de 0 a 99.",
    "debts": "Responda sim ou não.",
    "closed": "O histórico foi limpo. Use Nova conversa para começar novamente.",
}
if session.stage in hints and session.stage not in {"cpf", "birth"}:
    st.caption(hints[session.stage])
if session.stage in {"cpf", "birth"}:
    with st.expander("Dados fictícios para experimentar"):
        st.write("**CPF:** 000.000.000-01 ou 00000000001")
        st.write("**Nascimento:** 01/01/1990 ou 01011990")
        st.caption("Use somente os dados fictícios. O histórico oculta CPF e nascimento.")
interview_stages = ["income", "employment", "expenses", "dependents", "debts"]
if session.stage in interview_stages:
    completed = interview_stages.index(session.stage)
    st.progress(completed / 5, text=f"{completed} de 5 respostas concluídas")
if session.stage == "menu":
    st.subheader("O que você quer fazer?")
    actions = [
        ("Consultar limite", "consultar limite", "Veja o limite registrado no seu cadastro."),
        ("Pedir aumento", "aumentar limite", "Informe o limite desejado para análise."),
        ("Atualizar score", "atualizar score", "Responda uma entrevista de cinco perguntas."),
        ("Consultar câmbio", "cotação", "Consulte dólar, euro ou libra em reais."),
    ]
    for index, (label, action, description) in enumerate(actions):
        if index % 2 == 0:
            columns = st.columns(2)
        column = columns[index % 2]
        with column.container(border=True):
            st.caption(description)
            if st.button(label, use_container_width=True):
                command = action
    st.caption("Você também pode escrever seu pedido no campo abaixo.")

st.markdown("#### Converse com o Assistente Ágil")

for role, content in st.session_state.messages:
    with st.chat_message(role, avatar="🟣" if role == "assistant" else "👤"):
        st.write(content)

placeholders = {
    "cpf": "Digite seu CPF fictício, com ou sem pontuação",
    "birth": "Digite seu nascimento (DD/MM/AAAA ou DDMMAAAA)",
    "menu": "Como posso ajudar?",
    "amount": "Digite o limite total desejado",
    "offer_interview": "Deseja atualizar seu score? Responda sim ou não",
    "income": "Digite sua renda mensal",
    "employment": "Digite formal, autônomo ou desempregado",
    "expenses": "Digite suas despesas mensais",
    "dependents": "Digite a quantidade de dependentes",
    "debts": "Possui dívidas? Responda sim ou não",
    "closed": "Atendimento encerrado — use Nova conversa",
}
message = st.chat_input(
    placeholders.get(session.stage, "Digite sua resposta"),
    max_chars=2000,
    disabled=session.stage == "closed",
)
message = command or message
if message and "pending_turn" not in st.session_state:
    st.session_state.pending_turn = {
        "message": message,
        "event": str(uuid4()),
        "display": display_message(message, session.stage),
        "recorded": False,
    }
if "pending_turn" in st.session_state:
    turn = st.session_state.pending_turn
    message, event = turn["message"], turn["event"]
    if not turn["recorded"]:
        st.session_state.messages.append(("user", turn["display"]))
        turn["recorded"] = True
    with st.chat_message("user"):
        st.write(turn["display"])
    with st.chat_message("assistant"):
        with st.spinner("Preparando sua resposta…"):
            if os.getenv("BANCO_GRAPH", "local") == "langgraph":
                from banco_agil.graph import build_graph

                if "bank_graph" not in st.session_state:
                    st.session_state.bank_graph = build_graph(engine)
                answer = st.session_state.bank_graph.invoke(
                    {"session": session, "message": message, "event_id": event}
                )["response"]
            else:
                answer = engine.respond(session, message, event)
        st.write(answer)
    if session.stage == "closed":
        st.session_state.messages = [("assistant", answer)]
    else:
        # Histórico visual limitado; não é enviado ao modelo.
        st.session_state.messages = (st.session_state.messages + [("assistant", answer)])[-80:]
    st.session_state.pop("pending_turn", None)
    st.rerun()
