"""OpenAPI schema configuration for the FastAPI application."""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.schemas.errors import ErrorResponse


def configure_openapi(app: FastAPI) -> None:
    """Document validation failures as the API's unified HTTP 400 response."""

    def custom_openapi() -> dict:
        if app.openapi_schema is not None:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        component_schemas = schema.setdefault("components", {}).setdefault("schemas", {})
        error_response_schema = ErrorResponse.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        component_schemas.update(error_response_schema.pop("$defs", {}))
        component_schemas["ErrorResponse"] = error_response_schema

        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                if not isinstance(operation, dict) or "responses" not in operation:
                    continue

                responses = operation["responses"]
                if "422" not in responses:
                    continue

                responses.pop("422")
                responses.setdefault(
                    "400",
                    {
                        "description": "요청 형식, 타입, 범위 또는 입력값이 올바르지 않습니다.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                )

        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
