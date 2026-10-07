"""Start the local application; container deployments must publish on loopback.

Copyright 2026 Dhruba Poudel
SPDX-License-Identifier: Apache-2.0
"""

import os
import uvicorn

from .app import create_app


def main():
    uvicorn.run(create_app(), host=os.environ.get("FIGURERELAY_HOST", "127.0.0.1"),
                port=int(os.environ.get("FIGURERELAY_PORT", "8080")), log_level="info")


if __name__ == "__main__":
    main()
