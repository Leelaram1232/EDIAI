import asyncio
import httpx
import json

BASE_URL = "http://127.0.0.1:8000/api"

async def verify_all():
    print("=== STARTING END-TO-END ITX INTEGRATION TESTS ===")
    
    # 1. Sign up a new user (or handle existing user gracefully)
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n[Step 1] Creating/Authenticating test user...")
        email = "test_groq_user@example.com"
        password = "SecurePassword123!"
        
        signup_payload = {
            "email": email,
            "name": "Groq Tester",
            "password": password
        }
        
        try:
            signup_res = await client.post(f"{BASE_URL}/auth/signup", json=signup_payload)
            if signup_res.status_code == 201:
                print(" -> Test user signed up successfully.")
            elif signup_res.status_code == 400:
                print(" -> Test user already exists or signup skipped (expected).")
            else:
                print(f" -> Signup warning: {signup_res.status_code} - {signup_res.text}")
        except Exception as e:
            print(f" -> Signup request error (continuing to login): {e}")

        # 2. Login to get JWT Token
        login_payload = {
            "email": email,
            "password": password
        }
        login_res = await client.post(f"{BASE_URL}/auth/login", json=login_payload)
        if login_res.status_code != 200:
            print(f"FAILED TO LOGIN: {login_res.status_code} - {login_res.text}")
            return
        
        token_data = login_res.json()
        token = token_data["access_token"]
        print(" -> Logged in successfully. Received JWT token.")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # 3. Test Type Tree Builder
        print("\n[Step 2] Testing Type Tree Builder (/api/itx/build-type-tree)...")
        type_tree_payload = {
            "sample_data": "ID,Name,Salary,Active\n101,John Doe,75000.50,Y\n102,Jane Smith,82000.00,N",
            "requirements": "CSV format, comma-delimited, header row present, validate Salary as numeric and Active as Y/N flag"
        }
        
        tt_res = await client.post(f"{BASE_URL}/itx/build-type-tree", json=type_tree_payload, headers=headers)
        if tt_res.status_code != 200:
            print(f" -> Build Type Tree failed: {tt_res.status_code} - {tt_res.text}")
        else:
            tt_data = tt_res.json()
            print(f" -> Build Type Tree success! Status code: {tt_res.status_code}")
            print(f" -> Confidence score: {tt_data.get('confidence')}")
            
            meta = tt_data.get("metadata", {})
            print(f" -> Generated Artifact ID: {meta.get('artifact_id')}")
            print(f" -> JSON Schema extracted successfully: {bool(meta.get('json_schema'))}")
            print(f" -> MTS XML Script generated successfully: {bool(meta.get('mts_script'))}")
            
            # Print a snippet of the generated MTS code
            mts = meta.get('mts_script', '')
            if mts:
                snippet = mts[:300].replace('\n', ' ')
                print(f" -> MTS snippet: {snippet}...")

        # 4. Test Mapping Assistant
        print("\n[Step 3] Testing Mapping Assistant (/api/itx/suggest-mapping)...")
        mapping_payload = {
            "source_data": "ID,Name,Salary,Active",
            "target_data": "EmpNum,FullName,AnnualSalary,IsActiveFlag",
            "requirements": "Map ID to EmpNum. Concatenate or pass Name to FullName. Map Salary to AnnualSalary. Map Active ('Y'/'N') to IsActiveFlag ('1'/'0')."
        }
        
        map_res = await client.post(f"{BASE_URL}/itx/suggest-mapping", json=mapping_payload, headers=headers)
        if map_res.status_code != 200:
            print(f" -> Suggest Mapping failed: {map_res.status_code} - {map_res.text}")
        else:
            map_data = map_res.json()
            print(f" -> Suggest Mapping success! Status code: {map_res.status_code}")
            print(f" -> Confidence score: {map_data.get('confidence')}")
            
            meta = map_data.get("metadata", {})
            print(f" -> Generated Artifact ID: {meta.get('artifact_id')}")
            print(f" -> MMS Script generated successfully: {bool(meta.get('mms_script'))}")
            
            mms = meta.get('mms_script', '')
            if mms:
                snippet = mms[:300].replace('\n', ' ')
                print(f" -> MMS snippet: {snippet}...")

        # 5. Test Debug Assistant
        print("\n[Step 4] Testing Debug Tracer (/api/itx/debug)...")
        debug_payload = {
            "trace_content": "CARD 1 Input Validation Failure\nOffset: 48\nExpected format: YYYYMMDD\nActual value found: 2026-05-27",
            "error_message": "Type validation error at field 'TransactionDate'"
        }
        
        dbg_res = await client.post(f"{BASE_URL}/itx/debug", json=debug_payload, headers=headers)
        if dbg_res.status_code != 200:
            print(f" -> Debug Tracer failed: {dbg_res.status_code} - {dbg_res.text}")
        else:
            dbg_data = dbg_res.json()
            print(f" -> Debug Tracer success! Status code: {dbg_res.status_code}")
            print(f" -> Analysis details: {dbg_data.get('content')[:180]}...")

        # 6. Test Artifact Listing & Downloads
        print("\n[Step 5] Checking Artifacts list...")
        art_res = await client.get(f"{BASE_URL}/itx/artifacts", headers=headers)
        if art_res.status_code != 200:
            print(f" -> Listing artifacts failed: {art_res.status_code} - {art_res.text}")
        else:
            artifacts = art_res.json()
            print(f" -> Total generated artifacts in DB: {len(artifacts)}")
            for a in artifacts[:3]:
                print(f"    - Artifact ID: {a['id']} | Name: {a['name']} | Format: {a['format']}")
                
                # Test downloading this artifact
                dl_res = await client.get(f"{BASE_URL}/itx/artifacts/{a['id']}/download", headers=headers)
                print(f"      Download status: {dl_res.status_code} | Bytes: {len(dl_res.content)}")

if __name__ == "__main__":
    asyncio.run(verify_all())
