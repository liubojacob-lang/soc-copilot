import os

import uvicorn

uvicorn.run(
    "main:app",
    host="0.0.0.0",  # nosec B104 - container entrypoint
    port=int(os.getenv("PORT", "8088")),
    reload=False,
)
