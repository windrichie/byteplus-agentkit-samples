import os
import yaml
from veadk.configs.database_configs import NormalTOSConfig
from veadk.knowledgebase.knowledgebase import KnowledgeBase
from dotenv import load_dotenv

def load_config():
    # 1. Load from .env if it exists
    load_dotenv()
    
    # 2. Load from config.yaml if it exists
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            # Update environment variables from config.yaml
            if "database" in config:
                tos = config["database"].get("tos", {})
                viking = config["database"].get("viking", {})
                
                if "bucket" in tos:
                    os.environ.setdefault("DATABASE_TOS_BUCKET", tos["bucket"])
                if "region" in tos:
                    os.environ.setdefault("DATABASE_TOS_REGION", tos["region"])
                if "endpoint" in tos:
                    os.environ.setdefault("DATABASE_TOS_ENDPOINT", tos["endpoint"])
                if "collection" in viking:
                    os.environ.setdefault("DATABASE_VIKING_COLLECTION", viking["collection"])

def main() -> None:
    load_config()
    
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
        files=[
            "./data/product_info.txt",
            "./data/service_policy.txt",
            "./data/outlet_locations.txt",
            "./data/warranty_terms.txt",
            "./data/troubleshooting_guide.txt",
            "./data/repair_guide.txt",
        ],
        tos_bucket_name=bucket,
    )

if __name__ == "__main__":
    main()
