# OpenAPI Client

This folder holds the auto-generated client bindings derived from the Django REST Framework schema.

## Contents

- `openapi.json` – OpenAPI 3.0 schema (generated via `python manage.py generateschema`)
- `openapi.yaml` – YAML version of the same schema
- `client/` – Optional language-specific SDK (e.g., TypeScript fetch client via `openapi-generator-cli`)

For a quick refresh:

```bash
python manage.py generateschema --format openapi-json > docs/OpenAPI/openapi.json
python manage.py generateschema --format openapi-yaml > docs/OpenAPI/openapi.yaml
```

To generate a TypeScript client (requires Java + openapi-generator-cli on PATH):

```bash
openapi-generator-cli generate \
  -i docs/OpenAPI/openapi.yaml \
  -g typescript-fetch \
  -o docs/OpenAPI/client
```

> Note: The repo does not commit the generated SDK by default. Feel free to ignore `docs/OpenAPI/client/` or add it to `.gitignore` if the SDK becomes large.
