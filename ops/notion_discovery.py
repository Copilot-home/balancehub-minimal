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

def discover_notion_databases(target_page_id=None):
    """Tìm kiếm databases hoặc liệt kê con của một trang."""
    if not NOTION_TOKEN:
        print("❌ NOTION_TOKEN missing.")
        return
    
    try:
        notion = Client(auth=NOTION_TOKEN)
        
        if target_page_id:
            print(f"🔍 Inspecting page {target_page_id} children...")
            children = notion.blocks.children.list(block_id=target_page_id).get("results", [])
            found_db = False
            for child in children:
                type = child.get("type")
                # print(f"- [BLOCK:{type}] ID: {child['id']}")
                if type == "child_database":
                    print(f"  🌟 DATABASE FOUND: {child['child_database']['title']} | ID: {child['id']}")
                    found_db = True
                elif type == "child_page":
                    print(f"  📄 PAGE FOUND: {child['child_page']['title']} | ID: {child['id']}")
            
            if not found_db:
                print("  ⚠️ No databases found in this page's immediate children.")
            return

        print("🔍 Searching for Notion items...")
        results = notion.search().get("results", [])
        
        if not results:
            print("⚠️ No items found. Please share items with the integration.")
            return

        print("\n✅ Found Items:")
        for item in results:
            obj_type = item.get("object")
            if obj_type == "database":
                title = item.get("title", [{}])[0].get("plain_text", "Untitled")
                print(f"- [DATABASE] {title} | ID: {item['id']}")
            elif obj_type == "page":
                properties = item.get("properties", {})
                title_prop = properties.get("title") or properties.get("Name")
                title = "Untitled"
                if title_prop and title_prop.get("title"):
                    title = title_prop["title"][0].get("plain_text", "Untitled")
                print(f"- [PAGE] {title} | ID: {item['id']}")
            
    except Exception as e:
        print(f"❌ Operation failed: {e}")

if __name__ == "__main__":
    # Test with CORE_LOGIC ID first. If not found, run broad search.
    # CORE_LOGIC: d3df6fa6-4699-423d-bb19-79a411795624
    if len(sys.argv) > 1:
        discover_notion_databases(sys.argv[1])
    else:
        # Check sub-pages of CORE_LOGIC first
        discover_notion_databases("d3df6fa6-4699-423d-bb19-79a411795624")
        # Then show all
        print("\n--- GLOBAL SEARCH ---")
        discover_notion_databases()
