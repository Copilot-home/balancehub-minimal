import sys
import logging
from pathlib import Path

# Add paths for config
BASE_DIR = Path("/Users/andy/my_too_test")
sys.path.append(str(BASE_DIR / "autonomous_operator"))

try:
    from config import NOTION_TOKEN
    from notion_client import Client
except ImportError:
    print("❌ notion-client or config not found.")
    sys.exit(1)

def create_portal_baseline_page(parent_page_id):
    """Tạo trang Technical Baseline trên Notion."""
    if not NOTION_TOKEN:
        print("❌ NOTION_TOKEN missing.")
        return
    
    try:
        notion = Client(auth=NOTION_TOKEN)
        print(f"🏗️ Creating Technical Baseline page under {parent_page_id}...")
        
        new_page = notion.pages.create(
            parent={"page_id": parent_page_id},
            properties={
                "title": {"title": [{"text": {"content": "📐 APΩ-Portal Technical Baseline v1.0"}}]}
            },
            children=[
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {"rich_text": [{"text": {"content": "Ecosystem Portal Specification"}}]}
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": "Identity: WordPress.com OAuth2 | Governance: RBAC + Policy Engine | Observability: KPI Dashboard"}}] }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"text": {"content": "1. Identity Contract"}}] }
                },
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "language": "json",
                        "rich_text": [{"text": {"content": '{\n  "auth_url": "https://public-api.wordpress.com/oauth2/authorize",\n  "token_url": "https://public-api.wordpress.com/oauth2/token",\n  "scope": "auth sites posts media"\n}'}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"text": {"content": "2. Governance Pillars"}}] }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [{"text": {"content": "Determinism: Every publication signed with provenance."}}] }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [{"text": {"content": "Drift Detection: Fail-closed on schema or scope mismatch."}}] }
                }
            ]
        )
        print(f"✅ Page created successfully! ID: {new_page['id']}")
        print(f"🔗 URL: {new_page.get('url')}")
        return new_page['id']
            
    except Exception as e:
        print(f"❌ Creation failed: {e}")

if __name__ == "__main__":
    # CORE_LOGIC Parent ID: d3df6fa6-4699-423d-bb19-79a411795624
    create_portal_baseline_page("d3df6fa6-4699-423d-bb19-79a411795624")
