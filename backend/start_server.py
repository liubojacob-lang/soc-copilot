import os

import uvicorn

uvicorn.run(
    "main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8088")), reload=False
)  # nosec B104 - container entrypoint
