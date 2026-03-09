# Embedding Server (Google Colab)

1. Open Google Colab (https://colab.research.google.com)
2. Select GPU runtime: Runtime → Change runtime type → T4 GPU
3. Paste the code below into a cell and run it
4. Copy the ngrok URL and set it as EMBEDDING_API_URL in your .env

## Code

```python
# Cell 1: Install dependencies
!pip install sentence-transformers fastapi uvicorn pyngrok

# Cell 2: Start server
import torch
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import threading
from pyngrok import ngrok

# Load model (downloads ~1.2GB first time)
model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True)
model.to("cuda" if torch.cuda.is_available() else "cpu")
print(f"Model loaded on {model.device}")

app = FastAPI()

class EmbedRequest(BaseModel):
    texts: list[str]

@app.post("/embed")
async def embed(req: EmbedRequest):
    embeddings = model.encode(req.texts, normalize_embeddings=True)
    return {"embeddings": embeddings.tolist()}

@app.get("/health")
async def health():
    return {"status": "ok", "model": "Qwen3-Embedding-0.6B", "device": str(model.device)}

# Start ngrok tunnel
public_url = ngrok.connect(8001)
print(f"\nEmbedding server ready!")
print(f"Set this in your .env:")
print(f"EMBEDDING_API_URL={public_url}/embed\n")

# Run server
uvicorn.run(app, host="0.0.0.0", port=8001)
```

Note: You need a free ngrok auth token. Get one at https://dashboard.ngrok.com/signup
then run: `!ngrok authtoken YOUR_TOKEN` before starting the server.
