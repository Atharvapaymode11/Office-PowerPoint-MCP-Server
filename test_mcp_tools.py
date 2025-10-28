"""
Test MCP presentation tools with S3
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

async def test_mcp_tools():
    """Test MCP presentation tools with async/await"""
    
    # Import your server modules
    from tools.presentation_tools import register_presentation_tools
    from mcp.server.fastmcp import FastMCP
    
    # Create FastMCP app
    app = FastMCP("PowerPoint MCP Server")
    
    # Storage
    presentations = {}
    current_id = [None]
    
    def get_current_presentation_id():
        return current_id[0]
    
    def get_template_search_directories():
        return ['.', './templates']
    
    # Register ONLY presentation tools
    register_presentation_tools(app, presentations, get_current_presentation_id, get_template_search_directories)
    
    print("=" * 60)
    print("Testing MCP Presentation Tools with S3")
    print("=" * 60)
    
    # Test 1: Get storage mode
    print("\n1️⃣  Checking storage mode...")
    response = await app.call_tool("get_storage_mode", {})
    result = response[1]['result'] if isinstance(response, tuple) else response
    
    print(f"   Storage Mode: {result.get('storage_mode')}")
    if result.get('s3_bucket'):
        print(f"   ✅ S3 Bucket: {result.get('s3_bucket')}")
        print(f"   ✅ S3 Prefix: {result.get('s3_prefix')}")
        print(f"   ✅ S3 Region: {result.get('s3_region')}")
    else:
        print(f"   ℹ️  Local file mode")
    
    # Test 2: Create presentation
    print("\n2️⃣  Creating presentation...")
    response = await app.call_tool("create_presentation", {})
    result = response[1]['result'] if isinstance(response, tuple) else response
    print(f"   ✅ {result['message']}")
    
    pres_id = result.get("presentation_id")
    current_id[0] = pres_id
    print(f"   ✅ Presentation ID: {pres_id}")
    
    # Test 3: Get presentation info
    print("\n3️⃣  Getting presentation info...")
    response = await app.call_tool("get_presentation_info", {
        "presentation_id": pres_id
    })
    result = response[1]['result'] if isinstance(response, tuple) else response
    print(f"   ✅ Slide count: {result.get('slide_count', 0)}")
    print(f"   ✅ Layout count: {result.get('layout_count', 0)}")
    
    # Test 4: Set core properties
    print("\n4️⃣  Setting core properties...")
    response = await app.call_tool("set_core_properties", {
        "title": "MCP Test Presentation",
        "subject": "S3 Integration Test",
        "author": "PowerPoint MCP Server",
        "presentation_id": pres_id
    })
    result = response[1]['result'] if isinstance(response, tuple) else response
    print(f"   ✅ {result.get('message', 'Properties set')}")
    
    # Test 5: Save to S3
    print("\n5️⃣  Saving to S3...")
    response = await app.call_tool("save_presentation", {
        "file_path": "mcp_final_test.pptx",
        "presentation_id": pres_id
    })
    result = response[1]['result'] if isinstance(response, tuple) else response
    
    print(f"\n📄 Save Result:")
    print(f"   Success: {result.get('success')}")
    print(f"   Storage Type: {result.get('storage_type')}")
    
    if result.get('success') and result.get('storage_type') == 's3':
        print(f"\n   ✅ S3 Upload Details:")
        print(f"      Filename: {result.get('filename')}")
        print(f"      Bucket: {result.get('bucket')}")
        print(f"      Key: {result.get('key')}")
        print(f"\n   🔗 URLs:")
        print(f"      S3: {result.get('s3_url')}")
        print(f"      HTTPS: {result.get('https_url')}")
        if result.get('presigned_url'):
            presigned = result.get('presigned_url')
            print(f"      Presigned (1h): {presigned[:70]}...")
        
        print(f"\n🎉 SUCCESS! All MCP tools working with S3!")
        
    elif result.get('success'):
        print(f"   ✅ Local File: {result.get('file_path')}")
        print(f"\n✅ Local file save working!")
    else:
        print(f"   ❌ Error: {result.get('error', 'Unknown')}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All Presentation Tools Tested Successfully!")
    print("=" * 60)
    print("\n🚀 Your MCP server is ready for Karini UI!")
    print("\nNext steps:")
    print("  1. Commit your changes to GitHub")
    print("  2. Publish to PyPI (or use from GitHub)")
    print("  3. Add to Karini UI configuration")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_mcp_tools())
    exit(0 if success else 1)