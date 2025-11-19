from google.cloud import storage
import inspect

print(inspect.signature(storage.Blob.generate_signed_url))
