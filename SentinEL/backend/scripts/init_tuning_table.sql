CREATE TABLE IF NOT EXISTS `sentinel-ai-project-482208.retail_ai.gemini_tuning_dataset` (
    origin_id STRING OPTIONS(description="Original Firestore Analysis ID"),
    prompt STRING OPTIONS(description="Input prompt for the model (User Profile + Policy context)"),
    response STRING OPTIONS(description="Ideal output response (The rewritten email)"),
    quality_score FLOAT64 OPTIONS(description="Audit score (0-100)"),
    is_synthetic BOOL OPTIONS(description="Whether this response was synthetically rewritten by Gemini"),
    created_at TIMESTAMP OPTIONS(description="Creation timestamp")
);
