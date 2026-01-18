from __future__ import annotations

import json
import os
import sys

import httpx
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_openai import AzureChatOpenAI

UAP_DISCOVERY_GUIDE = (
    "Fetches the UAP discovery document at /.well-known/uap for a service. "
    "Pass the base URL, and optionally a module_id to fetch a module's document. "
    "Use the returned actions and OpenAPI URL to understand what endpoints exist."
)
UAP_HTTP_GUIDE = (
    "Simple HTTP tool for UAP actions. Provide method, url, and optional json/body. "
    "Use only URLs discovered via UAP or OpenAPI. Return response JSON or text."
)


@tool("uap_discover", description=UAP_DISCOVERY_GUIDE)
def uap_discover(base_url: str, module_id: str | None = None) -> str:
    if not base_url:
        raise ValueError("base_url is required")

    base_url = base_url.rstrip("/")
    with httpx.Client(timeout=10.0) as client:
        root_resp = client.get(f"{base_url}/.well-known/uap")
        root_resp.raise_for_status()
        root_doc = root_resp.json()

        if not module_id:
            return json.dumps(root_doc, indent=2)

        modules = root_doc.get("modules", [])
        module = next((mod for mod in modules if mod.get("id") == module_id), None)
        if not module:
            module_ids = [mod.get("id") for mod in modules]
            return (
                f"Module '{module_id}' not found. Available modules: {module_ids}."
            )

        module_resp = client.get(module["href"])
        module_resp.raise_for_status()
        module_doc = module_resp.json()

    return json.dumps({"uap": root_doc, "module": module_doc}, indent=2)


@tool("uap_http", description=UAP_HTTP_GUIDE)
def uap_http(
    method: str,
    url: str,
    json_body: dict | None = None,
    params: dict | None = None,
) -> str:
    if not method or not url:
        raise ValueError("method and url are required")

    method = method.upper().strip()
    with httpx.Client(timeout=10.0) as client:
        resp = client.request(method, url, json=json_body, params=params)
        resp.raise_for_status()

    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        return json.dumps(resp.json(), indent=2)
    return resp.text


def build_agent() -> tuple[object, str]:
    base_url = os.getenv("UAP_BASE_URL", "http://localhost:8000")
    system_prompt = (
        "You are a travel assistant. To interact with a service, first call "
        "`uap_discover` with the service base URL to read `/.well-known/uap`. "
        "Then choose a module and fetch it by id with the same tool if needed. "
        "Use the module's `actions` and `openapi` to decide which endpoints exist. "
        "Do not invent endpoints. Use `uap_http` to call action URLs. "
        "Actions that include `confirm: user` require explicit user confirmation. "
        f"Base URL: {base_url}"
    )

    llm = AzureChatOpenAI(
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        temperature=0,
    )

    agent = create_agent(llm, tools=[uap_discover, uap_http])
    return agent, system_prompt


def main() -> None:
    load_dotenv()
    agent, system_prompt = build_agent()

    user_query = " ".join(sys.argv[1:]).strip() or (
        "Find available room types for next weekend."
    )

    result = agent.invoke(
        {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_query),
            ]
        }
    )

    messages = result.get("messages", [])
    if messages:
        print(messages[-1].content)


if __name__ == "__main__":
    main()
