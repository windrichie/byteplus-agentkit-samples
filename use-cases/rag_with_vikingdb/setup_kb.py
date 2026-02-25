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

    provider = os.getenv("CLOUD_PROVIDER")
    is_byteplus = bool(provider and provider.lower() == "byteplus")
    if is_byteplus:
        kb = KnowledgeBase(
            backend="viking",
            backend_config={
                "index": knowledge_collection_name,
                "tos_config": NormalTOSConfig(
                    bucket=bucket,
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
        files=["./data/product_info.txt", "./data/service_policy.txt"],
        tos_bucket_name=bucket,
    )

if __name__ == "__main__":
    main()
