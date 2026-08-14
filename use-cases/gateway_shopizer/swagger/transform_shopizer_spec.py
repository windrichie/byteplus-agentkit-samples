#!/usr/bin/env python3
"""Produce the gateway-import OpenAPI spec for the Shopizer legacy app.

Transformations applied for the Volcengine APIG MCP gateway ("HTTP 转 MCP"),
following the proven playbook (see colleague's transform_spec.py):
  * servers: single URL pointing at the Shopizer deployment (paths already
    carry /api/v1, so no extra base path is added here).
  * Curate to a small, well-described ops/admin toolset (order ops, sales
    analysis inputs, catalog management, customer 360). Fewer, sharper tools
    = better agent tool selection.
  * Rewrite operationIds to snake_case tool names (list_orders, get_product...).
  * Append agent-facing usage notes to operation descriptions.
  * Compliance with APIG ConvertMcpConfig rules:
      - GET/POST/PUT/DELETE/PATCH only
      - JSON / form-urlencoded request bodies only (multipart ops dropped
        upstream in shopizer-mcp-openapi3.json)
      - exactly ONE response per operation (200 preferred, else 201/default)
      - array query/path params serialized as CSV (explode=false)
  * Drop securitySchemes + x-* leftovers; prune unreferenced component schemas.

Usage:
  python3 transform_shopizer_spec.py
"""

import copy
import json
import pathlib

import yaml

HERE = pathlib.Path(__file__).resolve().parent
INPUT = HERE / "shopizer-mcp-openapi3.json"
SERVER_URL = "http://45.78.208.93:8080"

PAGINATION = "Supports 'page' (0-based) and 'count' query params for pagination."

# (path, method) -> (new operationId, extra description note)
KEEP = {
    # ---- Order operations (admin) ----
    ("/api/v1/private/orders", "get"): (
        "list_orders",
        f"Lists store orders (admin view). {PAGINATION} Each order includes status, totals and customer id."),
    ("/api/v1/private/orders/{id}", "get"): (
        "get_order",
        "Full detail of one order: line items, amounts, status, shipping/billing."),
    ("/api/v1/private/orders/{id}/history", "get"): (
        "get_order_history",
        "Status-change history of an order, newest first."),
    ("/api/v1/private/orders/customers/{id}", "get"): (
        "list_orders_by_customer",
        f"All orders placed by one customer id. {PAGINATION}"),
    ("/api/v1/private/orders/payment/capturable", "get"): (
        "list_capturable_payments",
        "Orders with authorized payments that can still be captured."),

    # ---- Catalog: read ----
    ("/api/v1/products", "get"): (
        "list_products",
        f"Storefront product list. {PAGINATION} Optional 'category' query param filters by category id."),
    ("/api/v1/products/{id}", "get"): (
        "get_product",
        "One product with price, quantity (stock), sku, description and categories."),
    ("/api/v1/category", "get"): (
        "list_categories",
        "All product categories with id, code and display name."),
    ("/api/v1/category/{id}", "get"): (
        "get_category",
        "One category by id."),
    ("/api/v1/search", "post"): (
        "search_products",
        "Full-text product search. Body: {\"query\": \"<text>\"}. Returns matching products."),

    # ---- Catalog: write (admin) ----
    ("/api/v1/private/product", "post"): (
        "create_product",
        "Creates a product. Required: sku, price, quantity, and descriptions "
        "(name + description per language, e.g. English). Do not set 'id'; the server assigns it."),
    ("/api/v1/private/product/{id}", "put"): (
        "update_product",
        "Updates a product by id (e.g. change price or quantity). Send the full product object."),
    ("/api/v1/private/product/{sku}/inventory", "get"): (
        "get_product_inventory",
        "Inventory records for a product sku — use this for stock-level questions."),
    ("/api/v1/private/product/unique", "get"): (
        "check_product_sku_available",
        "Checks whether a sku is free (query param 'sku'). Use before create_product."),

    # ---- Customers (admin) ----
    ("/api/v1/private/customers", "get"): (
        "list_customers",
        f"Lists registered customers (admin view). {PAGINATION}"),

    # ---- Store info ----
    ("/api/v1/store/{code}", "get"): (
        "get_store",
        "Store profile for a store code (the default store code is 'DEFAULT'): name, currency, address."),
    ("/api/v1/private/stores", "get"): (
        "list_stores",
        "All stores in this Shopizer instance (admin view)."),
}


def collect_refs(node, found):
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            found.add(ref.rsplit("/", 1)[1])
        for v in node.values():
            collect_refs(v, found)
    elif isinstance(node, list):
        for v in node:
            collect_refs(v, found)


def strip_keys(node, banned):
    """Recursively drop x-* extension keys and other banned keys, and fix
    Swagger-2.0-isms the converter left behind (`type: file` is illegal in
    OpenAPI 3 — files are `type: string, format: binary`)."""
    if isinstance(node, dict):
        if node.get("type") == "file":
            node = {**node, "type": "string", "format": "binary"}
        return {k: strip_keys(v, banned) for k, v in node.items()
                if k not in banned and not (isinstance(k, str) and k.startswith("x-"))}
    if isinstance(node, list):
        return [strip_keys(v, banned) for v in node]
    return node


def main():
    spec = json.loads(INPUT.read_text())
    out = {
        "openapi": "3.0.1",
        "info": {
            "title": "Shopizer Legacy E-commerce API (MCP curated)",
            "description": (
                "Curated operations surface of the Shopizer commerce backend "
                "(orders, catalog, customers, store), prepared for MCP tool conversion. "
                "Endpoints under /api/v1/private/ are admin operations."
            ),
            "version": "1.0",
        },
        "servers": [{"url": SERVER_URL}],
    }

    new_paths = {}
    for path, item in spec["paths"].items():
        kept_ops = {}
        for method, op in item.items():
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            key = (path, method)
            if key not in KEEP:
                continue
            op = copy.deepcopy(op)
            tool_name, note = KEEP[key]
            op["operationId"] = tool_name
            base_desc = op.get("description") or op.get("summary") or ""
            op["description"] = (base_desc.rstrip(". ") + ". " + note).strip(". ")
            op.pop("security", None)  # auth is configured at the gateway, not per-op
            kept_ops[method] = op
        if kept_ops:
            new_paths[path] = kept_ops

    missing = [v[0] for k, v in KEEP.items()
               if k[0] not in new_paths or k[1] not in new_paths.get(k[0], {})]
    if missing:
        raise SystemExit(f"ERROR: allowlisted operations not found in source spec: {missing}")
    out["paths"] = new_paths

    # prune schemas transitively
    schemas = spec.get("components", {}).get("schemas", {})
    needed = set()
    collect_refs(new_paths, needed)
    while True:
        extra = set()
        for name in needed:
            collect_refs(schemas.get(name, {}), extra)
        if extra <= needed:
            break
        needed |= extra
    out["components"] = {"schemas": {k: v for k, v in schemas.items() if k in needed}}

    out = strip_keys(out, banned={"securitySchemes"})

    json_path = HERE / "shopizer-gateway.json"
    yaml_path = HERE / "shopizer-gateway.yml"
    json_path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    yaml_path.write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True))

    n_ops = sum(1 for item in new_paths.values() for m in item
                if m in ("get", "post", "put", "delete", "patch"))
    print(f"Wrote {json_path.name} + {yaml_path.name}: {len(new_paths)} paths, "
          f"{n_ops} operations, {len(needed)} schemas, servers[0]={SERVER_URL}")


if __name__ == "__main__":
    main()
