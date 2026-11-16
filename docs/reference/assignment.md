# INFO 490 Project 2: requirements, condensed

Condensed on 16 Nov 2026 from the assignment brief (P2-A3 and P2-A4) the builder pasted. The brief on Canvas is the authority; check it when a detail matters.

## Dates
- **P2-A3, first draft:** due 9 Nov 2026, 11:59 PM. The builder is submitting by 18 Nov 2026.
- **P2-A4, final GitHub push and video:** 8 Dec 2026, 11:59 PM.

## The final application (100 points)

### Part 1: Product scope and user experience (10)
- State the startup name, the problem, target users, core value proposition and primary features. Document any substantial change from P2-A2.
- At least **three meaningful features** that serve the problem. No padding.
- Clear navigation, consistent design, working forms, user feedback, and a complete end-to-end workflow.
- Explain how the product differs from alternatives. There is no need to prove it has no competitors, only why a user might prefer it.

### Part 2: Django application development (25)
- **Models and ORM:** meaningful models, relationships between them, migrations, create/read/update/delete where relevant.
- **Views, templates, URLs:** function- or class-based views, organised templates, template inheritance, working URL routing, model-driven URLs where relevant.
- **Forms:** user-input forms, validation, processing, error messages, database interaction.
- **Authentication:** login and logout, protected routes, user-specific data, permission checks.
- **APIs and data:** at least one meaningful internal JSON API or external API integration, and at least one data feature (search and filtering, dashboards, visualisation, reporting, statistics, CSV or JSON export).

### Part 3: AI integration (25)
- At least one meaningful AI feature **inside the Django application**, not a standalone notebook.
- Explain the model choice: capabilities, compute, latency, cost, accuracy, privacy, scalability.
- Document the workflow: input → Django view → preprocessing → model → postprocessing → database or interface. Say how results are validated and how the user receives them.
- Depth: a chatbot or a plain API pass-through is not enough. The AI must interact with the app's functionality, data or workflow.
- Reliability: handle invalid inputs, missing data, model errors, API failures, unexpected outputs, and safety and privacy concerns. Fail gracefully.

### Part 4: Evaluation, testing and improvement (15)
- Define metrics that fit the product.
- At least **five realistic tests**, in a table: test, input, expected behaviour, actual output, quality (1–10), latency.
- At least **two genuine failure cases**: what failed, why, the impact, what could improve.
- At least **one improvement**: before → modification → after, with evidence.

### Part 5: Deployment, cost and production readiness (15)
- Deploy on a suitable host (PythonAnywhere, Render, Railway or similar) so the primary workflow works. A reproducible local deployment is allowed with a clear technical justification, for example specialised hardware.
- Describe the resources needed: CPU, GPU, RAM, storage, database hosting, AI inference.
- Compare at least two realistic deployment approaches: hardware, monthly cost, latency, maintenance, scalability, privacy.
- Scalability at 10,000 daily active users: infrastructure, the main bottleneck, how AI cost changes, how to keep performance, what architecture changes are needed. State assumptions.
- Security and reliability: environment variables, input validation, authentication and permissions, key protection, error handling, rate limiting, logging and monitoring, privacy, AI-related risks.

### Part 6: Documentation and reproducibility (10)
- The repository holds the Django code, migrations, AI code, `requirements.txt`, `.gitignore` and `README.md`.
- `README.md`: name and purpose, features, installation, dependencies, environment variables, database setup, how to run, how to reach the AI functionality.
- `README_AI.md` or a clear AI section: models and services, why they were chosen, preprocessing, the workflow, output handling, known limitations, safety measures.
- Code quality: organised, readable names, separated responsibilities, no needless duplication, no exposed credentials, reproducible setup.

## First draft (P2-A3), graded separately (100 points)

| Requirement | Points | What it must contain |
| --- | --- | --- |
| 1. Updated product scope | 15 | One page: the finalised idea, the problem, target users, three planned core features, and any significant changes from P2-A2. If nothing changed, the P2-A2 submission can be referenced |
| 2. Functional Django foundation | 40 | A working Django project with at least one app; at least two meaningful models with at least one relationship; working views and templates; at least one working form; at least one database-backed workflow (user input → view → database → visible result). A static landing page does not count |
| 3. Initial AI implementation or technical plan | 20 | The AI feature; the proposed model or technique; its input and output; how it will interact with Django; evidence of initial experimentation or a working prototype if available. Full integration is not required, but feasibility must have been considered |
| 4. Progress and roadmap | 15 | A table with current status, responsible member and expected completion for: Django core features, database and APIs, AI integration, evaluation and testing, deployment, documentation |
| 5. GitHub organisation and reproducibility | 10 | The current code pushed to GitHub with a README explaining how to run the prototype. The repository must be accessible to the instructor. The URL is submitted on Canvas |

## Final submission (P2-A4)
1. The final GitHub repository. The instructor grades the version in the repository.
2. A video of no more than three minutes that shows the actual application:

| Time | Part | Content |
| --- | --- | --- |
| 0:00–0:30 | Startup overview | The problem and the target users |
| 0:30–1:45 | Product demonstration | The main user workflow |
| 1:45–2:30 | AI integration | The AI feature working inside Django |
| 2:30–3:00 | Final status | Current limitations and next steps |

3. Final documentation in the repository: README, dependencies, setup instructions, AI documentation.

## Rules from the brief
- AI must be part of a meaningful workflow. A disconnected notebook or a generic API wrapper is insufficient.
- Do not commit `.env` files, keys, passwords or model weights. Add patterns such as `*.bin`, `*.safetensors` and `*.pt` to `.gitignore`.
- The application must run from the instructions in the repository.
- Document actual results. Do not fabricate test outcomes or claim unbuilt features work.
- Finish the most important features before adding optional ones.
- Project 2 must be a different startup idea from Project 1.
- The instructor's stated goal: build a meaningful product, understand how it works, evaluate its limitations, and show how it could continue after the class.
