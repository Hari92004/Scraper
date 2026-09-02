import os
import uvicorn

# Satisfy Hugging Face ZeroGPU supervisor if running on ZERO hardware
try:
    import spaces
    @spaces.GPU
    def check_gpu():
        return True
except Exception:
    pass

from backend.server import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f">> Launching ScrapeAI on Hugging Face Spaces (Port: {port})...")
    uvicorn.run(app, host="0.0.0.0", port=port)
