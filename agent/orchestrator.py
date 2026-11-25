"""
AgentOrchestrator — the SalesAgent.respond() sequence as an explicit graph:

    load_profile → analyze_intent → policy_act → retrieve_context
                 → compose_prompt → compliance_check → persist_pending

Built with LangGraph when it is installed, otherwise the same nodes run sequentially.
Dependencies are injected so the graph is testable without LLM, Chroma or MongoDB.
`persist_pending` only writes when a persist function and a client are given: when
called from SalesAgent.respond(), persistence stays with generate_response() as before.
"""

from typing import Any, Callable, Dict, List, Optional, TypedDict

from compliance import check_message
from config import ACTION_DIRECTIVES, SALES_STRATEGIES

DEFAULT_INTENT = "intérêt global"


class AgentState(TypedDict, total=False):
    user_message: str
    user_data: Dict[str, Any]
    conversation_history: str
    client_id: Optional[str]
    conversation_id: Optional[str]
    features: Dict[str, Any]
    legacy_action: str
    intent: Dict[str, Any]
    strategy: Dict[str, Any]
    decision: Dict[str, Any]
    rag_context: str
    sources: List[Dict[str, Any]]
    system_prompt: str
    response: str
    compliance: Dict[str, Any]
    explanation: str
    message_id: Optional[str]


NODES = ["load_profile", "analyze_intent", "policy_act", "retrieve_context",
         "compose_prompt", "compliance_check", "persist_pending"]


class AgentOrchestrator:
    def __init__(
        self,
        llm,
        analyze_intent: Callable[[str], Dict],
        retrieve: Callable[[str, int], List[Dict]],
        build_context: Callable[[List[Dict]], str],
        source_of: Callable[[Dict], Dict],
        decide: Callable[..., Dict],
        build_features: Callable[..., Dict],
        legacy_decision: Callable[[Dict], str],
        generate_explanation: Callable[..., str],
        persist: Optional[Callable[..., Any]] = None,
        index_info: Optional[Callable[[], Dict]] = None,
        use_langgraph: bool = True,
    ):
        self.llm = llm
        self._intent = analyze_intent
        self._retrieve = retrieve
        self._build_context = build_context
        self._source_of = source_of
        self._decide = decide
        self._build_features = build_features
        self._legacy_decision = legacy_decision
        self._explain = generate_explanation
        self._persist = persist
        self._index_info = index_info or (lambda: {})
        self.graph = self._compile() if use_langgraph else None

    # ---------------- graph ----------------

    def _compile(self):
        try:
            from langgraph.graph import END, StateGraph
        except ImportError:
            return None
        graph = StateGraph(AgentState)
        for name in NODES:
            graph.add_node(name, getattr(self, name))
        graph.set_entry_point(NODES[0])
        for a, b in zip(NODES, NODES[1:]):
            graph.add_edge(a, b)
        graph.add_edge(NODES[-1], END)
        return graph.compile()

    def invoke(self, user_message: str, user_data: Dict, conversation_history: str = "",
               client_id: Optional[str] = None, conversation_id: Optional[str] = None) -> AgentState:
        state: AgentState = {
            "user_message": user_message, "user_data": user_data,
            "conversation_history": conversation_history,
            "client_id": client_id, "conversation_id": conversation_id,
        }
        if self.graph is not None:
            return self.graph.invoke(state)
        for name in NODES:
            state.update(getattr(self, name)(state))
        return state

    # ---------------- nodes ----------------

    def load_profile(self, state: AgentState) -> Dict:
        return {"features": self._build_features(state["user_data"]),
                "legacy_action": self._legacy_decision(state["user_data"])}

    def analyze_intent(self, state: AgentState) -> Dict:
        intent = self._intent(state["user_message"])
        label = intent["intention"]["label"]
        strategy = SALES_STRATEGIES.get(label) or SALES_STRATEGIES[DEFAULT_INTENT]
        print(f"detected intent: {intent['intention']}")
        return {"intent": intent, "strategy": strategy}

    def policy_act(self, state: AgentState) -> Dict:
        client_id = state.get("client_id") or (state["user_data"].get("data") or {}).get("user_id")
        decision = self._decide(str(client_id), state["features"], state["legacy_action"])
        return {"decision": decision}

    def retrieve_context(self, state: AgentState) -> Dict:
        if not state["strategy"]["use_rag"]:
            return {"rag_context": "", "sources": []}
        query = self.llm.query_rag_llm(state["conversation_history"], state["user_message"])
        docs = self._retrieve(query, 3)
        # same "Retrieved RAG info: ..." block query_rag() produces in the legacy flow
        context = f"Retrieved RAG info: {self._build_context(docs)}"
        print(f"RAG Context: {context}")
        return {"rag_context": context, "sources": [self._source_of(d) for d in docs]}

    def compose_prompt(self, state: AgentState) -> Dict:
        system_prompt = state["strategy"]["system_prompt"]
        decision = state["decision"]
        if decision["mode"] == "active" and decision["action"] in ACTION_DIRECTIVES:
            system_prompt = f"{system_prompt}\n{ACTION_DIRECTIVES[decision['action']]}"
        response = self.llm.query_llm(
            False, state["user_data"], state["rag_context"], system_prompt=system_prompt,
            user_message=state["user_message"],
            conversation_history=state["conversation_history"],
        )
        return {"system_prompt": system_prompt, "response": response}

    def compliance_check(self, state: AgentState) -> Dict:
        result = check_message(state["response"], state["rag_context"],
                               state["user_data"].get("user_data_str", ""),
                               state["sources"], state["strategy"]["use_rag"])
        if not result["passed"]:
            print(f"[compliance] issues: {result['issues']}")
        return {"compliance": result}

    def persist_pending(self, state: AgentState) -> Dict:
        intent = state["intent"]["intention"]
        explanation = self._explain(
            "respond", (state["user_data"].get("data") or {}).get("produits_recommandes"),
            state["system_prompt"], intent["label"], confidence_score=intent["score"],
        ) + self.decision_block(state)

        decision = {**state["decision"], "sources": state["sources"],
                    "compliance": state["compliance"], "rag_index": self._index_info()}
        decision.pop("features", None)
        out = {"explanation": explanation, "decision": decision, "message_id": None}
        if self._persist and state.get("client_id"):
            message_id, conversation_id = self._persist(
                client_id=state["client_id"], corps=state["response"], expediteur="ai",
                statut="pending", msg_type="email", conversation_id=state.get("conversation_id"),
                subject="Re: Votre demande d'information", argumentation=explanation,
                decision=decision,
            )
            out.update(message_id=message_id, conversation_id=conversation_id)
        return out

    # ---------------- dashboard argumentation ----------------

    def decision_block(self, state: AgentState) -> str:
        return format_decision_block(state["decision"], state["sources"], state["compliance"],
                                     self._index_info())


def format_decision_block(decision: Dict, sources: List[Dict], compliance: Optional[Dict],
                          index_info: Dict) -> str:
    """Appended to `argumentation`, which the admin dashboard already displays."""
    lines = ["", "4. Décision next-best-action :"]
    applied = decision["action"]
    lines.append(f"   Action appliquée : {applied} (mode {decision['mode']})")
    if decision.get("policy_action") and decision["policy_action"] != applied:
        lines.append(f"   Action proposée par la politique (non appliquée) : {decision['policy_action']}")
    lines.append(f"   Version du modèle : {decision['model_version']}")
    if decision.get("reason_codes"):
        lines.append(f"   Justification : {', '.join(decision['reason_codes'])}")
    if decision.get("fallback_reason"):
        lines.append(f"   Repli : {decision['fallback_reason']}")
    lines.append(f"   Actions autorisées : {', '.join(decision.get('allowed_actions') or [])}")
    lines.append(f"   Identifiants : decision_id={decision['decision_id']} trace_id={decision['trace_id']}")
    lines.append("")
    lines.append(f"5. Sources documentaires (index {index_info.get('index_version', 'n/a')}) :")
    if sources:
        for s in sources:
            page = f", p. {s['page']}" if s.get("page") is not None else ""
            lines.append(f"   - {s['source']} (version {s['document_version']}{page})")
    else:
        lines.append("   - aucune")
    if compliance is not None:
        lines.append("")
        status = "conforme" if compliance["passed"] else "à vérifier : " + ", ".join(compliance["issues"])
        lines.append(f"6. Contrôle de conformité : {status}")
    return "\n".join(lines) + "\n"
