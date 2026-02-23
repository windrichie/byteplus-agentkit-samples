from veadk.knowledgebase.knowledgebase import KnowledgeBase
import os
import tos


def main() -> None:
    bucket = os.getenv("DATABASE_TOS_BUCKET")
    if not bucket:
        raise ValueError("DATABASE_TOS_BUCKET is required")

    region = os.getenv("DATABASE_TOS_REGION", "cn-hongkong")
    endpoint = os.getenv("DATABASE_TOS_ENDPOINT", f"tos-{region}.bytepluses.com")
    ak = os.getenv("BYTEPLUS_ACCESS_KEY") or os.getenv("VOLCENGINE_ACCESS_KEY")
    sk = os.getenv("BYTEPLUS_SECRET_KEY") or os.getenv("VOLCENGINE_SECRET_KEY")
    if not ak or not sk:
        raise ValueError("BYTEPLUS_ACCESS_KEY and BYTEPLUS_SECRET_KEY are required")

    client = tos.TosClientV2(ak=ak, sk=sk, endpoint=endpoint, region=region)
    client.head_bucket(bucket)

    with open("/tmp/product_info.txt", "w") as f:
        f.write(
            "Product list and prices:\n1. High-Performance Laptop (Laptop Pro) - Price: 8999\n   - For professional design and gaming, equipped with the latest GPU.\n2. SmartPhone (SmartPhone X) - Price: 4999\n   - 5G support, long battery life.\n3. Tablet (Tablet Air) - Price: 2999\n   - Lightweight and portable, suitable for work and entertainment."
        )
    with open("/tmp/service_policy.txt", "w") as f:
        f.write(
            "After-sales policy:\n1. Warranty: All electronics come with a 1-year free warranty.\n2. Returns/Exchanges: 7-day no-reason returns; exchanges within 15 days for quality issues.\n3. Support: 7x24 customer support."
        )

    with open("/tmp/product_info.txt", "rb") as f:
        client.put_object(
            bucket=bucket,
            key="knowledgebase/product_info.txt",
            content=f.read(),
        )
    with open("/tmp/service_policy.txt", "rb") as f:
        client.put_object(
            bucket=bucket,
            key="knowledgebase/service_policy.txt",
            content=f.read(),
        )

    kb = KnowledgeBase(
        backend="viking",
        app_name=os.getenv("DATABASE_VIKING_COLLECTION", "agentkit_knowledge_app"),
    )
    for object_key in [
        "knowledgebase/product_info.txt",
        "knowledgebase/service_policy.txt",
    ]:
        response = kb._backend._add_doc(tos_url=f"{bucket}/{object_key}")
        if response.get("code") != 0:
            raise ValueError(
                f"Failed to add doc {object_key}: {response.get('code')} {response.get('message')}"
            )


if __name__ == "__main__":
    main()
