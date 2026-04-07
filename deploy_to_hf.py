"""Deploy TrustGuard-Env to Hugging Face Space"""
from huggingface_hub import HfApi
import os

# Load from environment variable for security
TOKEN = os.getenv('HF_TOKEN', 'your-token-here')
REPO_ID = 'eressss/trustguard-env'

api = HfApi(token=TOKEN)

# Files to upload
files_to_upload = [
    'README.md',
    'inference.py',
    'server/app.py',
    'server/demo.py',
    'IMPROVEMENTS.md',
    'OPTIMIZATION_SUMMARY.md',
    'FINAL_STATUS.md',
]

print(f"🚀 Deploying to {REPO_ID}...")
print(f"📦 Uploading {len(files_to_upload)} files...\n")

for file_path in files_to_upload:
    if os.path.exists(file_path):
        try:
            print(f"⬆️  Uploading {file_path}...", end=" ")
            api.upload_file(
                path_or_fileobj=file_path,
                path_in_repo=file_path,
                repo_id=REPO_ID,
                repo_type='space'
            )
            print("✅")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print(f"⚠️  File not found: {file_path}")

print(f"\n✅ Deployment complete!")
print(f"🌐 View your space at: https://huggingface.co/spaces/{REPO_ID}")
