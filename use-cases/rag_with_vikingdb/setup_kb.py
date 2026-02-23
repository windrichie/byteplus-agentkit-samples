import os
from veadk.configs.database_configs import NormalTOSConfig
from veadk.knowledgebase.knowledgebase import KnowledgeBase


def main() -> None:
    bucket = os.getenv("DATABASE_TOS_BUCKET")
    if not bucket:
        raise ValueError("DATABASE_TOS_BUCKET is required")

    knowledge_collection_name = os.getenv("DATABASE_VIKING_COLLECTION", "")
    if not knowledge_collection_name:
        raise ValueError("DATABASE_VIKING_COLLECTION is required")

    with open("/tmp/product_info.txt", "w") as f:
        f.write(
            "Product list and prices:\n1. High-Performance Laptop (Laptop Pro) - Price: 8999\n   - For professional design and gaming, equipped with the latest GPU.\n2. SmartPhone (SmartPhone X) - Price: 4999\n   - 5G support, long battery life.\n3. Tablet (Tablet Air) - Price: 2999\n   - Lightweight and portable, suitable for work and entertainment."
        )
    with open("/tmp/service_policy.txt", "w") as f:
        f.write(
            "After-sales policy:\n1. Warranty: All electronics come with a 1-year free warranty.\n2. Returns/Exchanges: 7-day no-reason returns; exchanges within 15 days for quality issues.\n3. Support: 7x24 customer support."
        )

    provider = os.getenv("CLOUD_PROVIDER")
    is_byteplus = bool(provider and provider.lower() == "byteplus")
    if is_byteplus:
        kb = KnowledgeBase(
            backend="viking",
            backend_config={
                "index": knowledge_collection_name,
                "tos_config": NormalTOSConfig(
                    bucket=os.getenv("DATABASE_TOS_BUCKET", ""),
                    region=os.getenv("DATABASE_TOS_REGION", "cn-hongkong"),
                    endpoint=os.getenv(
                        "DATABASE_TOS_ENDPOINT", "tos-cn-hongkong.bytepluses.com"
                    ),
                ),
            },
        )
    else:
        kb = KnowledgeBase(backend="viking", index=knowledge_collection_name)

    kb.add_from_files(
        files=["/tmp/product_info.txt", "/tmp/service_policy.txt"],
        tos_bucket_name=bucket,
    )

if __name__ == "__main__":
    main()
