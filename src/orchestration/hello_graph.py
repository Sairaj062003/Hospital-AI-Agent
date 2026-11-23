from typing import TypedDict

from langgraph.graph import StateGraph, END


class GreetingState(TypedDict):
    name: str
    greeting: str
    shout: bool


def greet_node(state: GreetingState) -> dict:
    return {"greeting": f"Hello, {state['name']}!"}


def shout_node(state: GreetingState) -> dict:
    return {"greeting": state["greeting"].upper()}


def route_after_greet(state: GreetingState) -> str:
    return "shout_step" if state["shout"] else END


def build_graph():
    graph = StateGraph(GreetingState)
    graph.add_node("greet", greet_node)
    graph.add_node("shout_step", shout_node)

    graph.set_entry_point("greet")
    graph.add_conditional_edges("greet", route_after_greet, {"shout_step": "shout_step", END: END})
    graph.add_edge("shout_step", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()

    result = app.invoke({"name": "Patient", "greeting": "", "shout": False})
    print("No shout:", result)

    result = app.invoke({"name": "Patient", "greeting": "", "shout": True})
    print("With shout:", result)
