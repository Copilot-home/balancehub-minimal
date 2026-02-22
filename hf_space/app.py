import os
import requests
import gradio as gr

DEFAULT_URL = os.getenv("BALANCEHUB_URL", "http://host.docker.internal:8000")


def fetch_health(base_url: str):
    base = base_url.rstrip("/")
    health = requests.get(f"{base}/system/health", timeout=8).json()
    connectors = requests.get(f"{base}/catalog/connectors", timeout=8).json()

    axis_health = health.get("axis_health", {})
    top_vol = health.get("top_volatility", [])

    return {
        "system_health": health.get("system_health"),
        "axis_health": axis_health,
        "top_volatility": top_vol,
        "spof": health.get("single_point_of_failure", []),
        "deg_violation": health.get("deg_violation", []),
        "connector_count": len(connectors.get("items", [])),
    }


with gr.Blocks(title="BalanceHub Live Health Viewer") as demo:
    gr.Markdown("# BalanceHub Live Health Viewer")
    url = gr.Textbox(value=DEFAULT_URL, label="BalanceHub Base URL")
    output = gr.JSON(label="System Health")
    btn = gr.Button("Refresh")
    btn.click(fetch_health, inputs=[url], outputs=[output])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
