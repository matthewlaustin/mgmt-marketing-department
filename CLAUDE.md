# Pool Geek marketing department

This repo is the home of an AI-staffed marketing department: the Director, the shared contracts
between roles, and each specialist's code and working rules under `roles/<role>/`.

- `roles/product-development/` is the Product Development specialist (formerly the
  `pool-geek-data-specialist` repo). When working there, follow its own `CLAUDE.md` and `PLAN.md`;
  every path in them is relative to that folder. Its working data (`data/`, `reports/`) was left
  out of this repo and lives in Neon and R2.
- Specialists take assignments from the Director, not from Matthew directly. The Director sets
  the manufacturer development plan with Matthew and assigns from it.
- Run that folder's tests (`python3 -m pytest -q` from inside it) before committing a change to
  its code.

## Matthew's preferences
- Send reports, results and questions for Matthew as an Artifact page he can review in the
  Claude desktop or iOS app, with places to answer questions and leave follow-ups in the page.
  Answers and selections save automatically (no Save button); read them back with ArtifactData.
  Keep the chat reply short and link the page.
- Never ask Matthew a series of questions in chat: no question lists in the reply and no
  multiple-choice prompts in the terminal. Put every question on an Artifact page.
- Matthew does not want `.md` files as the way to correspond with him. Markdown in this repo is
  for the agents; anything for Matthew to read or answer goes on an Artifact page.
