
import os
import json
import numpy as np
import tensorflow as tf
import pandas as pd

# Define paths
DATA_DIR = os.path.dirname(os.path.abspath(__file__)) + "/../data"
STRATEGIES_PATH = os.path.join(DATA_DIR, "strategies.csv")
SAVED_MODEL_DIR = os.path.dirname(os.path.abspath(__file__)) + "/saved_user_model"
EMBEDDINGS_PATH = os.path.dirname(os.path.abspath(__file__)) + "/strategy_embeddings.json"

def generate_artifacts():
    print("Generating dummy artifacts for integration testing...")
    
    # 1. Generate Strategy Embeddings (Random)
    if not os.path.exists(STRATEGIES_PATH):
        print("Strategies file not found!")
        return

    df = pd.read_csv(STRATEGIES_PATH)
    embeddings = []
    
    for _, row in df.iterrows():
        # Generate random 32-dim vector
        vector = np.random.normal(size=32).tolist()
        embeddings.append({
            "id": str(row["strategy_id"]),
            "embedding": vector,
            "description": row["description"],  # Metadata for validation
            "type": row["type"]
        })
        
    with open(EMBEDDINGS_PATH, "w") as f:
        for emb in embeddings:
            f.write(json.dumps(emb) + "\n")
            
    print(f"Generated {len(embeddings)} strategy embeddings at {EMBEDDINGS_PATH}")

    # 2. Skip Dummy User Tower Model generation due to TF/Keras version conflicts in this environment.
    # We will rely on the RecommendationService's fallback logic or use a pre-existing model if available.
    print("Skipping User Tower model generation (TF dependency issues).")
    
    # class DummyUserTower(tf.keras.Model):
    #     def __init__(self):
    #         super().__init__()
    #         self.dense = tf.keras.layers.Dense(32, activation="relu")
    #         
    #     @tf.function(input_signature=[
    #         {"user_id": tf.TensorSpec(shape=(None,), dtype=tf.string, name="user_id"),
    #          "user_risk_score": tf.TensorSpec(shape=(None,), dtype=tf.float32, name="user_risk_score")}
    #     ])
    #     def call(self, inputs):
    #         # Ignore user_id for dummy model, just use risk score to generate some vector
    #         risk = tf.expand_dims(inputs["user_risk_score"], -1) # (batch, 1)
    #         # Pad to 32 dims roughly mechanism
    #         # Here we just output a random-like vector based on risk (consistent for same risk)
    #         # But for simplicity, let's just use a Dense layer on risk
    #         return self.dense(risk)

    # model = DummyUserTower()
    # # Build model with dummy data
    # dummy_input = {
    #     "user_id": tf.constant(["u1", "u2"]),
    #     "user_risk_score": tf.constant([0.1, 0.9], dtype=tf.float32)
    # }
    # _ = model(dummy_input)
    # 
    # # Save
    # tf.saved_model.save(model, SAVED_MODEL_DIR)
    # print(f"Saved dummy User Tower model to {SAVED_MODEL_DIR}")

if __name__ == "__main__":
    generate_artifacts()
