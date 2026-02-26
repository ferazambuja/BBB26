"""JSON schemas for BBB26 manual data files."""

PAREDAO_SCHEMA = {
    "type": "object",
    "required": ["paredoes"],
    "properties": {
        "paredoes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["numero", "status", "data", "titulo"],
                "properties": {
                    "numero": {"type": "integer", "minimum": 1},
                    "status": {"type": "string", "enum": ["em_andamento", "finalizado"]},
                    "data": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                    "titulo": {"type": "string", "minLength": 1},
                    "data_formacao": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                    "semana": {"type": "integer", "minimum": 1},
                    "total_esperado": {"type": "integer", "minimum": 1},
                    "formacao": {"type": "object"},
                    "indicados_finais": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["nome"],
                            "properties": {
                                "nome": {"type": "string", "minLength": 1},
                                "grupo": {"type": "string"},
                                "como": {"type": "string"},
                            },
                        },
                    },
                    "votos_casa": {"type": "object"},
                    "resultado": {
                        "type": "object",
                        "properties": {
                            "eliminado": {"type": "string"},
                            "votos": {"type": "object"},
                        },
                    },
                },
            },
        },
    },
}

MANUAL_EVENTS_SCHEMA = {
    "type": "object",
    "required": ["participants"],
    "properties": {
        "participants": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["status"],
                "properties": {
                    "status": {"type": "string"},
                    "exit_date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                    "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                },
            },
        },
        "weekly_events": {"type": "array"},
        "power_events": {"type": "array"},
        "special_events": {"type": "array"},
        "scheduled_events": {"type": "array"},
        "cartola_points_log": {"type": "array"},
    },
}

PROVAS_SCHEMA = {
    "type": "object",
    "required": ["provas"],
    "properties": {
        "provas": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["numero", "tipo", "week", "date"],
                "properties": {
                    "numero": {"type": "integer", "minimum": 1},
                    "tipo": {"type": "string", "enum": ["lider", "anjo", "bate_volta"]},
                    "week": {"type": "integer", "minimum": 1},
                    "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                    "vencedor": {"type": ["string", "null"]},
                },
            },
        },
    },
}


def validate_input_files():
    """Validate all manual data files against their schemas.

    Raises jsonschema.ValidationError if any file is invalid.
    """
    import json
    from pathlib import Path

    try:
        from jsonschema import validate, ValidationError
    except ImportError:
        print("Warning: jsonschema not installed — skipping schema validation")
        return

    schemas = [
        ("data/paredoes.json", PAREDAO_SCHEMA),
        ("data/manual_events.json", MANUAL_EVENTS_SCHEMA),
        ("data/provas.json", PROVAS_SCHEMA),
    ]

    for filepath, schema in schemas:
        p = Path(filepath)
        if not p.exists():
            print(f"Warning: {filepath} not found — skipping validation")
            continue
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        try:
            validate(instance=data, schema=schema)
            print(f"  {filepath} — schema valid")
        except ValidationError as e:
            raise ValidationError(
                f"Schema validation failed for {filepath}: {e.message}"
            ) from e

    print("Schema validation passed")
