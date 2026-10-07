# Third-party notices

Prepared by **Dhruba Poudel**.

FigureRelay's original code and documentation are licensed under Apache-2.0. Dependencies, package managers, build tools, CI actions, and runtime distributions keep their own copyrights and licence terms. The root LICENSE does not relicense those components.

## Application dependencies

| Component | Role | Upstream licence |
| --- | --- | --- |
| React and React DOM | Browser interface | [MIT](https://github.com/react/react/blob/main/LICENSE); [included licence](docs/third-party/react-LICENSE) also covers the React repository's Scheduler package used by React DOM. |
| FastAPI | HTTP application | [MIT](https://github.com/fastapi/fastapi/blob/master/LICENSE) |
| Uvicorn | Local HTTP server | [BSD-3-Clause](https://github.com/Kludex/uvicorn/blob/main/LICENSE.md) |
| python-multipart | Multipart upload parser | [Apache-2.0](https://github.com/Kludex/python-multipart/blob/main/LICENSE.txt) |
| openpyxl | Excel workbook reading | MIT; [official package metadata](https://pypi.org/project/openpyxl/3.1.5/) and included distribution notice in the snapshot below. |
| python-docx | Word document generation | [MIT](https://github.com/python-openxml/python-docx/blob/master/LICENSE); [included licence](docs/third-party/python-docx-LICENSE). |
| python-pptx | PowerPoint generation | [MIT](https://github.com/scanny/python-pptx/blob/master/LICENSE); [included licence](docs/third-party/python-pptx-LICENSE). |
| defusedxml | Safer XML parsing support | [PSF-2.0](https://github.com/tiran/defusedxml/blob/main/LICENSE); [included licence](docs/third-party/defusedxml-LICENSE). |

Backend dependencies bring additional components such as Starlette, Pydantic, lxml, Pillow, XlsxWriter, and et_xmlfile. The [backend distribution snapshot](docs/third-party/backend-license-index.md) records the actual package notices retained during prototype verification, including runtime and test dependencies and their embedded third-party notices. Version selection remains governed by the requirement files and frontend lockfile; the snapshot is not a dependency lockfile.

## Development and automation

| Component | Role | Upstream licence |
| --- | --- | --- |
| Vite and its React plugin | Browser development and build | [MIT and included third-party notices](https://github.com/vitejs/vite/blob/main/LICENSE); [React plugin MIT](https://github.com/vitejs/vite-plugin-react/blob/main/LICENSE). |
| TypeScript | Static type checking | [Apache-2.0](https://github.com/microsoft/TypeScript/blob/main/LICENSE.txt) |
| React type definitions | Type checking | [MIT](https://github.com/DefinitelyTyped/DefinitelyTyped/blob/master/LICENSE) |
| pytest | Backend tests | [MIT](https://github.com/pytest-dev/pytest/blob/main/LICENSE) |
| HTTPX | HTTP test client | [BSD-3-Clause](https://github.com/encode/httpx/blob/master/LICENSE.md) |
| pnpm | Frontend dependency installation | [MIT and upstream notices](https://github.com/pnpm/pnpm/blob/main/LICENSE) |
| actions/checkout, actions/setup-python, actions/setup-node | GitHub CI tools | MIT; see each action repository's licence. |
| pnpm/action-setup | GitHub CI package-manager setup | [MIT](https://github.com/pnpm/action-setup/blob/master/LICENSE.md) |

The [Developer Certificate of Origin 1.1](DCO) is reproduced verbatim under its own permission to copy and distribute unchanged. It is not FigureRelay's software licence. The project's code of conduct is original project text.

## Distribution responsibilities

Retain the complete notices and licences shipped with the exact dependency versions you distribute. Preserve the React notice with a browser bundle. Python wheels include distribution licence files; retain them in environments or containers that redistribute those packages. Binary wheels may contain native components with additional terms recorded in their notices. Python, Node.js, operating-system packages, and container base images have their own notices as well.

Refresh the inventory when dependencies change and review all components in a release bundle or image. This document records provenance and notices; it is not a certification that an arbitrary downstream distribution meets every licence obligation.
