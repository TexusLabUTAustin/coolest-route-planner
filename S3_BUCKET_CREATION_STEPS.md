# S3 Bucket Creation - Complete Settings Guide

## Step-by-Step Settings

### **Step 1: General Configuration**

1. **Bucket name**
   - Enter: `coolest-route-planner-utci` (or any unique name)
   - Must be globally unique across all AWS accounts
   - Lowercase letters, numbers, hyphens, and periods only
   - Must start and end with a letter or number

2. **AWS Region**
   - Choose: `US East (N. Virginia) us-east-1` (recommended for Railway)
   - Or choose the region closest to your Railway deployment
   - This affects latency and cost slightly

### **Step 2: Object Ownership**

- **ACLs disabled (recommended)**
  - Select: "ACLs disabled (recommended)"
  - This uses bucket policies instead of ACLs (modern approach)

- **ACLs enabled** (if you need fine-grained control)
  - Select: "ACLs enabled"
  - Choose: "Bucket owner preferred" (default)

### **Step 3: Block Public Access Settings**

**For Public Access (Easiest):**
- ✅ **Uncheck all 4 boxes:**
  - ☐ Block all public access
  - ☐ Block public access to buckets and objects granted through new access control lists (ACLs)
  - ☐ Block public access to buckets and objects granted through any access control lists (ACLs)
  - ☐ Block public access to buckets and objects granted through new public bucket or access point policies
  - ☐ Block public and cross-account access to buckets and objects through any public bucket or access point policies

- ⚠️ **Warning dialog will appear** - Click "I acknowledge that the current settings might result in this bucket and the objects within becoming public"

**For Private Access (More Secure):**
- ✅ **Keep all 4 boxes checked** (default)
- You'll need to create a pre-signed URL later

### **Step 4: Bucket Versioning**

- **Disable versioning** (recommended for this use case)
  - Select: "Disable"
  - You don't need version history for a single static file

### **Step 5: Tags (Optional)**

- **Add tags** (optional, for organization)
  - Key: `Project`
  - Value: `CoolestRoutePlanner`
  - Key: `Environment`
  - Value: `Production`

### **Step 6: Default Encryption**

- **Server-side encryption**
  - Select: "Enable"
  - **Encryption type**: Choose one:
    - **AWS managed keys (SSE-S3)** - Recommended (simplest)
    - **AWS KMS key (SSE-KMS)** - More control, costs extra
    - **Customer managed keys** - Advanced, not needed here

### **Step 7: Object Lock**

- **Disable Object Lock** (recommended)
  - Select: "Disable"
  - Object Lock is for compliance/retention policies (not needed here)

### **Step 8: Review and Create**

- Review all settings
- Click **"Create bucket"**

---

## **Recommended Settings Summary**

For the easiest setup (public file):

```
Bucket name: coolest-route-planner-utci
Region: US East (N. Virginia) us-east-1
Object Ownership: ACLs disabled (recommended)
Block Public Access: ALL UNCHECKED ⚠️
Bucket Versioning: Disable
Tags: Optional
Default Encryption: Enable (SSE-S3)
Object Lock: Disable
```

---

## **After Creating the Bucket**

### **Make the File Public (if you chose public access):**

1. Click on your bucket name
2. Click "Upload"
3. Upload `UTCI_1600.tif`
4. After upload, click on the file
5. Go to "Permissions" tab
6. Under "Object ACL", click "Edit"
7. Select "Grant public read access"
8. Click "Save changes"

### **Get the Public URL:**

The URL format will be:
```
https://coolest-route-planner-utci.s3.amazonaws.com/UTCI_1600.tif
```

Or with region:
```
https://coolest-route-planner-utci.s3.us-east-1.amazonaws.com/UTCI_1600.tif
```

---

## **Alternative: Private Bucket with Pre-signed URL**

If you kept the bucket private:

1. After uploading, use AWS CLI to generate a pre-signed URL:
   ```bash
   aws s3 presign s3://coolest-route-planner-utci/UTCI_1600.tif --expires-in 31536000
   ```
   (Valid for 1 year)

2. Use this pre-signed URL in Railway's `UTCI_S3_URL` variable

---

## **Quick Checklist**

- [ ] Bucket name is unique and valid
- [ ] Region selected (us-east-1 recommended)
- [ ] Public access settings configured (all unchecked for public)
- [ ] Encryption enabled (SSE-S3)
- [ ] Bucket created successfully
- [ ] File uploaded
- [ ] File permissions set to public (if using public access)
- [ ] URL copied for Railway environment variable

