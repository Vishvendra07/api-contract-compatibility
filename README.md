# API Contract Compatibility Gate

Run two consumer contracts against live local API revisions and catch two independent breaks before confirming the compatibility fix.

[Source](project.py) · [Demo evidence](evidence/demo.json) · [Verification](evidence/checks.json)

## Run locally

Requires Python 3.11+.

```sh
python -m pip install -r requirements.txt
python project.py
python -m unittest discover -v
```

## Engineering decision

Validate both caller-facing response shape and request rejection behavior. Keep compatible fields when sharing an additive new representation.

Local HTTP handlers, authored JSON Schemas and fixture data. The results are verified for these two consumer contracts.



[Technology or project reference](https://python-jsonschema.readthedocs.io/en/stable/)
