# S3 Setup Guide for UTCI File

This guide will help you upload the `UTCI_1600.tif` file to AWS S3 and configure your Railway backend to download it automatically.

## Step 1: Create AWS S3 Bucket

1. **Sign in to AWS Console**
   - Go to https://aws.amazon.com/console/
   - Sign in or create an account

2. **Navigate to S3**
   - Search for "S3" in the AWS console
   - Click "Create bucket"

3. **Configure Bucket**
   - **Bucket name**: `coolest-route-planner-utci` (must be globally unique)
   - **Region**: Choose closest to your Railway deployment (e.g., `us-east-1`)
   - **Block Public Access**: 
     - **Option A (Public)**: Uncheck "Block all public access" if you want public access
     - **Option B (Private)**: Keep it private and use pre-signed URLs (recommended)
   - Click "Create bucket"

## Step 2: Upload UTCI File

1. **Upload via AWS Console**
   - Click on your bucket
   - Click "Upload"
   - Click "Add files"
   - Select `scripts/UTCI_1600.tif`
   - Click "Upload"
   - Wait for upload to complete (may take 10-20 minutes for 1.9GB)

2. **Alternative: Upload via AWS CLI**
   ```bash
   # Install AWS CLI if not installed
   brew install awscli  # macOS
   # or download from https://aws.amazon.com/cli/
   
   # Configure AWS credentials
   aws configure
   # Enter your AWS Access Key ID
   # Enter your AWS Secret Access Key
   # Enter default region (e.g., us-east-1)
   # Enter default output format (json)
   
   # Upload file
   aws s3 cp scripts/UTCI_1600.tif s3://coolest-route-planner-utci/UTCI_1600.tif
   ```

## Step 3: Make File Publicly Accessible (Option A)

1. **Set Object to Public**
   - Click on the uploaded file in S3
   - Go to "Permissions" tab
   - Under "Object ACL", click "Edit"
   - Select "Grant public read access"
   - Click "Save changes"

2. **Get Public URL**
   - The URL will be: `https://coolest-route-planner-utci.s3.amazonaws.com/UTCI_1600.tif`
   - Or: `https://coolest-route-planner-utci.s3.us-east-1.amazonaws.com/UTCI_1600.tif`
   - Copy this URL

## Step 4: Create Pre-Signed URL (Option B - Recommended)

If you kept the bucket private, create a pre-signed URL that's valid for a long time:

```python
import boto3
from datetime import timedelta

s3_client = boto3.client('s3',
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    region_name='us-east-1'
)

# Generate pre-signed URL valid for 1 year
url = s3_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': 'coolest-route-planner-utci', 'Key': 'UTCI_1600.tif'},
    ExpiresIn=31536000  # 1 year in seconds
)
print(url)
```

Or use AWS CLI:
```bash
aws s3 presign s3://coolest-route-planner-utci/UTCI_1600.tif --expires-in 31536000
```

## Step 5: Configure Railway Environment Variable

1. **Go to Railway Dashboard**
   - Navigate to your backend service
   - Go to "Variables" tab

2. **Add Environment Variable**
   - **Name**: `UTCI_S3_URL`
   - **Value**: Your S3 URL (public or pre-signed)
     - Public: `https://coolest-route-planner-utci.s3.amazonaws.com/UTCI_1600.tif`
     - Pre-signed: `https://coolest-route-planner-utci.s3.amazonaws.com/UTCI_1600.tif?X-Amz-Algorithm=...`
   - Click "Add"

3. **Redeploy**
   - Railway will automatically redeploy
   - The backend will download the file on startup if it doesn't exist

## Step 6: Verify It Works

1. **Check Railway Logs**
   - Go to Railway → Your service → "Logs"
   - Look for: "Downloading UTCI file from S3" or "UTCI file found at /app/scripts/UTCI_1600.tif"

2. **Test the Backend**
   - The file should download automatically on first startup
   - Subsequent restarts will use the cached file

## Cost Considerations

- **S3 Storage**: ~$0.023 per GB/month = ~$0.04/month for 1.9GB
- **Data Transfer Out**: First 100GB/month free, then $0.09/GB
- **Total**: Very cheap (likely < $1/month)

## Security Notes

- **Public Bucket**: Anyone with the URL can download (fine for public data)
- **Private Bucket + Pre-signed URL**: More secure, but URL expires
- **IAM User**: Create a dedicated IAM user with minimal S3 permissions for production

## Troubleshooting

- **Download fails**: Check S3 URL is correct and accessible
- **File not found**: Verify file name matches exactly
- **Slow download**: Consider using CloudFront CDN for faster downloads
- **Permission denied**: Check bucket/object permissions

