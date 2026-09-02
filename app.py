"""
Hugging Face Spaces Entry Point
Serves the FastAPI ScrapeAI Dashboard with full Gradio Spaces compatibility.
"""

import os
import gradio as gr
from backend.server import app as fastapi_app

# Gradio container
with gr.Blocks(title="ScrapeAI • Universal Scraper & RAG") as demo:
    gr.HTML("""
        <meta http-equiv="refresh" content="0; url=/" />
        <div style="text-align:center; padding: 2rem; font-family: sans-serif;">
            <h2>Loading ScrapeAI Web Dashboard...</h2>
            <p>If not redirected automatically, <a href="/" target="_self">click here to open ScrapeAI</a>.</p>
        </div>
    """)

# Mount Gradio onto FastAPI
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
