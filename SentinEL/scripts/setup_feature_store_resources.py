
import logging
import time
from google.cloud import aiplatform
from google.cloud.aiplatform_v1 import (
    FeatureRegistryServiceClient,
    FeatureOnlineStoreAdminServiceClient,
    FeatureGroup,
    FeatureView,
    CreateFeatureGroupRequest,
    CreateFeatureViewRequest,
    FeatureOnlineStore,
    Feature
)
from google.cloud.aiplatform_v1.types import BigQuerySource

# 配置
PROJECT_ID = "sentinel-ai-project-482208"
REGION = "us-central1"
FEATURE_ONLINE_STORE_NAME = "sentinel_online_store"
FEATURE_GROUP_NAME = "user_realtime_features"
FEATURE_VIEW_NAME = "user_realtime_view"
BQ_SOURCE_URI = "bq://sentinel-ai-project-482208.sentinel_features.user_realtime_aggregates"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_feature_store_resources():
    aiplatform.init(project=PROJECT_ID, location=REGION)
    
    # 1. Check/Create Feature Online Store
    admin_client = FeatureOnlineStoreAdminServiceClient(client_options={"api_endpoint": f"{REGION}-aiplatform.googleapis.com"})
    store_path = admin_client.feature_online_store_path(PROJECT_ID, REGION, FEATURE_ONLINE_STORE_NAME)
    
    try:
        admin_client.get_feature_online_store(name=store_path)
        logger.info(f"Feature Online Store {FEATURE_ONLINE_STORE_NAME} already exists.")
    except Exception:
        logger.info(f"Creating Feature Online Store {FEATURE_ONLINE_STORE_NAME}...")
        feature_online_store = FeatureOnlineStore(
            bigtable=FeatureOnlineStore.Bigtable(
                auto_scaling=FeatureOnlineStore.Bigtable.AutoScaling(
                    min_node_count=1,
                    max_node_count=3,
                    cpu_utilization_target=50
                )
            )
        )
        request = {
            "parent": f"projects/{PROJECT_ID}/locations/{REGION}",
            "feature_online_store_id": FEATURE_ONLINE_STORE_NAME,
            "feature_online_store": feature_online_store,
        }
        lro = admin_client.create_feature_online_store(request=request)
        logger.info("Feature Online Store creation submitted. This takes minutes...")
        # We won't block here for the full creation if it takes too long, 
        # but for safety we should at least wait for it to be created before View.
        # Ideally we wait.
        lro.result() 
        logger.info("Feature Online Store created.")

    # 2. Create Feature Group
    registry_client = FeatureRegistryServiceClient(client_options={"api_endpoint": f"{REGION}-aiplatform.googleapis.com"})
    
    fg_path = registry_client.feature_group_path(PROJECT_ID, REGION, FEATURE_GROUP_NAME)
    
    try:
        registry_client.get_feature_group(name=fg_path)
        logger.info(f"Feature Group {FEATURE_GROUP_NAME} already exists.")
    except Exception:
        logger.info(f"Creating Feature Group {FEATURE_GROUP_NAME}...")
        feature_group = FeatureGroup(
            big_query=FeatureGroup.BigQuery(
                big_query_source=BigQuerySource(input_uri=BQ_SOURCE_URI),
                entity_id_columns=["entity_id"]
            )
        )
        request = CreateFeatureGroupRequest(
            parent=f"projects/{PROJECT_ID}/locations/{REGION}",
            feature_group=feature_group,
            feature_group_id=FEATURE_GROUP_NAME
        )
        lro = registry_client.create_feature_group(request=request)
        logger.info("Feature Group creation submitted. Waiting...")
        lro.result()
        logger.info("Feature Group created.")

    # 2.5 Ensure Features Exist (Explicit Registration)
    features_to_register = [
        "realtime_clicks_5m", "rage_clicks_5m", "policy_views_5m", 
        "cart_additions_5m", "active_session_duration"
    ]

    for feat_name in features_to_register:
        # Manually construct path to avoid signature issues
        feat_path = f"projects/{PROJECT_ID}/locations/{REGION}/featureGroups/{FEATURE_GROUP_NAME}/features/{feat_name}"
        try:
            registry_client.get_feature(name=feat_path)
            logger.info(f"Feature {feat_name} already exists.")
        except Exception:
            logger.info(f"Creating Feature {feat_name}...")
            request = {
                "parent": fg_path,
                "feature_id": feat_name,
                "feature": Feature(), 
            }
            lro = registry_client.create_feature(request=request)
            lro.result()
            logger.info(f"Feature {feat_name} created.")

    # 3. Create Feature View
    admin_client = FeatureOnlineStoreAdminServiceClient(client_options={"api_endpoint": f"{REGION}-aiplatform.googleapis.com"})
    fv_path = admin_client.feature_view_path(PROJECT_ID, REGION, FEATURE_ONLINE_STORE_NAME, FEATURE_VIEW_NAME)
    
    try:
        admin_client.get_feature_view(name=fv_path)
        logger.info(f"Feature View {FEATURE_VIEW_NAME} already exists.")
    except Exception:
        logger.info(f"Creating Feature View {FEATURE_VIEW_NAME}...")
        
        # Sync every 5 minutes
        sync_config = FeatureView.SyncConfig(cron="*/5 * * * *")
        
        feature_view = FeatureView(
            feature_registry_source=FeatureView.FeatureRegistrySource(
                feature_groups=[
                    FeatureView.FeatureRegistrySource.FeatureGroup(
                        feature_group_id=FEATURE_GROUP_NAME,
                        feature_ids=[
                            "realtime_clicks_5m", 
                            "rage_clicks_5m", 
                            "policy_views_5m", 
                            "cart_additions_5m", 
                            "active_session_duration"
                        ]
                    )
                ]
            ),
            sync_config=sync_config
        )
        
        request = CreateFeatureViewRequest(
            parent=f"projects/{PROJECT_ID}/locations/{REGION}/featureOnlineStores/{FEATURE_ONLINE_STORE_NAME}",
            feature_view=feature_view,
            feature_view_id=FEATURE_VIEW_NAME
        )
        
        lro = admin_client.create_feature_view(request=request)
        logger.info("Feature View creation submitted. Waiting...")
        lro.result()
        logger.info("Feature View created.")

if __name__ == "__main__":
    setup_feature_store_resources()
