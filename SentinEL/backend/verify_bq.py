from google.cloud import bigquery
import pandas as pd
import os

# Set project explicitly if needed, though client should pick it up
project_id = "sentinel-ai-project-482208"
client = bigquery.Client(project=project_id)

query = f"""
    SELECT prompt, response, quality_score, is_synthetic, created_at
    FROM `{project_id}.retail_ai.gemini_tuning_dataset`
    ORDER BY created_at DESC
    LIMIT 10
"""

try:
    df = client.query(query).to_dataframe()
    
    if df.empty:
        print("No data found in BigQuery table.")
        html_content = "<p>No data found in BigQuery table yet.</p>"
    else:
        # Format for better readability
        pd.set_option('display.max_colwidth', 100)
        print(df)
        html_content = df.to_html(classes='table table-striped table-bordered', index=False)

    with open("bq_results.html", "w") as f:
        f.write(f"""
        <html>
        <head>
            <title>BigQuery Data Verification</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>
                body {{ padding: 40px; background-color: #f8f9fa; }}
                h1 {{ color: #0d6efd; margin-bottom: 20px; }}
                .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                td {{ max-width: 400px; word-wrap: break-word; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ BigQuery Verification: gemini_tuning_dataset</h1>
                <p><strong>Query:</strong> <code>{query}</code></p>
                <div class="table-responsive">
                    {html_content}
                </div>
            </div>
        </body>
        </html>
        """)
    print(f"Successfully generated bq_results.html with {len(df)} rows.")

except Exception as e:
    print(f"Error querying BigQuery: {e}")
