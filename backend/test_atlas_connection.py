"""
Atlas connection test — runs the same code path as production db.py.
Usage:
    cd backend
    python test_atlas_connection.py

Before running, ensure MONGODB_URI in .env has the real password, e.g.:
    MONGODB_URI=mongodb+srv://admin_db_user:YourRealPassword@synaptiq-prod.ici39nk.mongodb.net/
                                            ^^^^^^^^^^^^^^^^
"""
import asyncio
import os
import sys
import time
from pathlib import Path

# Load .env from the same directory
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")


async def main():
    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URL", "")
    db_name = os.environ.get("MONGODB_DB_NAME") or os.environ.get("DB_NAME", "")

    print("=" * 60)
    print("SYNAPTIQ Atlas Connection Test")
    print("=" * 60)
    print(f"URI scheme:    {uri[:20]}..." if uri else "URI: NOT SET")

    # Mask password in display
    if uri and "@" in uri:
        parts = uri.split("@")
        cred_part = parts[0]  # mongodb+srv://user:pass
        host_part = "@".join(parts[1:])
        if ":" in cred_part.split("//")[-1]:
            user = cred_part.split("//")[-1].split(":")[0]
            pwd = cred_part.split("//")[-1].split(":")[1]
            masked = uri.replace(f":{pwd}@", ":***@")
        else:
            masked = uri
        print(f"URI (masked):  {masked}")
    print(f"Database name: {db_name}")
    print()

    # Check for placeholder password
    if "FILL_IN_YOUR_PASSWORD" in uri:
        print("FAIL: Password is still the placeholder 'FILL_IN_YOUR_PASSWORD'")
        print("      Edit backend/.env and replace FILL_IN_YOUR_PASSWORD with your")
        print("      real Atlas database user password, then re-run this script.")
        sys.exit(1)

    if not uri:
        print("FAIL: No MongoDB URI configured.")
        sys.exit(1)

    if not db_name:
        print("FAIL: No database name configured.")
        sys.exit(1)

    # Connect using the exact same parameters as production db.py
    from motor.motor_asyncio import AsyncIOMotorClient

    is_atlas = uri.startswith("mongodb+srv://")
    kwargs = {
        "maxPoolSize": 5,
        "minPoolSize": 1,
        "connectTimeoutMS": 10_000,
        "serverSelectionTimeoutMS": 10_000,
        "socketTimeoutMS": 30_000,
        "retryWrites": True,
        "w": "majority",
        "appName": "SYNAPTIQ-test",
    }
    if is_atlas:
        kwargs["tls"] = True
        kwargs["tlsAllowInvalidCertificates"] = False

    print(f"Connecting ({'Atlas SRV' if is_atlas else 'local'})...")
    t0 = time.time()

    client = AsyncIOMotorClient(uri, **kwargs)
    db = client[db_name]

    try:
        # 1. Ping
        result = await db.command("ping")
        elapsed = round((time.time() - t0) * 1000)
        print(f"[PASS] Ping succeeded in {elapsed}ms — {result}")

        # 2. Server info
        info = await db.command("buildInfo")
        print(f"[PASS] MongoDB version: {info.get('version')}")

        # 3. Server description
        desc = client.topology_description
        print(f"[PASS] Topology type: {desc.topology_type}")

        # 4. Database name
        print(f"[PASS] Database: {db.name}")

        # 5. Collections
        cols = await db.list_collection_names()
        print(f"[PASS] Collections visible: {len(cols)}")
        if cols:
            print(f"       Sample: {sorted(cols)[:8]}")

        # 6. Index check on users collection
        if "users" in cols:
            idxs = await db.users.list_indexes().to_list(None)
            print(f"[PASS] users indexes: {len(idxs)} (including _id)")
            unique = [i["name"] for i in idxs if i.get("unique")]
            if unique:
                print(f"       Unique: {unique}")
        else:
            print("[INFO] users collection not yet created (first run)")

        print()
        print("=" * 60)
        print("RESULT: ALL CHECKS PASSED — Atlas connection is working")
        print("=" * 60)

    except Exception as e:
        elapsed = round((time.time() - t0) * 1000)
        print(f"[FAIL] Connection failed after {elapsed}ms")
        print(f"       Error type: {type(e).__name__}")
        print(f"       Error msg:  {e}")
        print()
        err = str(e).lower()
        if "authentication" in err or "auth" in err:
            print("DIAGNOSIS: Authentication failed.")
            print("  → Wrong username or password in MONGODB_URI")
            print("  → Check Atlas: Database Access → verify username + reset password if needed")
        elif "serverselectiontimeouterror" in type(e).__name__.lower() or "timeout" in err:
            print("DIAGNOSIS: Could not reach Atlas cluster.")
            print("  → Check Atlas: Network Access → add your IP or 0.0.0.0/0 temporarily")
            print("  → Run: nc -zv ac-a0iea4g-shard-00-00.ici39nk.mongodb.net 27017")
        elif "ssl" in err or "tls" in err or "certificate" in err:
            print("DIAGNOSIS: TLS/SSL error.")
            print("  → Rarely occurs with Atlas — try updating certifi: pip install --upgrade certifi")
        else:
            print("DIAGNOSIS: Unexpected error — see full message above")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
