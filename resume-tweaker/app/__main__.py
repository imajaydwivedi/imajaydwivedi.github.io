import os

import uvicorn

if __name__ == "__main__":
    # Local runs default to 127.0.0.1:8000. The container sets PORT=80 and binds 0.0.0.0.
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )
