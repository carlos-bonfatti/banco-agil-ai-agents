from typing import TypedDict

from banco_agil.engine import Engine
from banco_agil.session import Session


class Turn(TypedDict):
    session: Session
    message: str
    event_id: str
    response: str
    route: str


def build_graph(engine: Engine):
    """Orquestração opcional com nós por responsabilidade.

    Não serializa Session (contém lock). Persistência de conversa ainda é local.
    Para checkpoints distribuídos, substituir por estado serializável + session store.
    """
    from langgraph.graph import END, START, StateGraph

    def route(turn):
        s = turn["session"]
        route = "triage" if s.stage in {"cpf", "birth"} else "dispatch"
        if s.stage in {"income", "employment", "expenses", "dependents", "debts"}:
            route = "interview"
        elif s.stage in {"amount", "offer_interview"}:
            route = "credit"
        return {"route": route}

    def execute(turn):
        return {"response": engine.respond(turn["session"], turn["message"], turn["event_id"])}

    graph = StateGraph(Turn)
    graph.add_node("route", route)
    for name in ("triage", "dispatch", "interview", "credit"):
        graph.add_node(name, execute)
        graph.add_edge(name, END)
    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route",
        lambda turn: turn["route"],
        {name: name for name in ("triage", "dispatch", "interview", "credit")},
    )
    return graph.compile()
