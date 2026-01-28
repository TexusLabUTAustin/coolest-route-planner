# Fix S3 Access Denied Error

You're getting "Access Denied" because the S3 file is not publicly accessible. Here are two ways to fix it:

## **Option 1: Make the File Public (Easiest)**

### **Step 1: Make the Object Public**

1. Go to **AWS Console** → **S3** → Your bucket
2. Click on the file `UTCI_1600.tif`
3. Go to the **"Permissions"** tab
4. Scroll down to **"Object ACL"** section
5. Click **"Edit"**
6. Check the box: **"Grant public read access"**
7. Click **"Save changes"**
8. Confirm by clicking **"Save changes"** again in the popup

### **Step 2: Verify Public Access**

1. Still in the **"Permissions"** tab
2. Scroll to **"Access control list (ACL)"**
3. You should see: **"Public access: Objects can be public"**
4. Under **"Public access"**, you should see an entry with:
   - **Principal**: `Everyone (public access)`
   - **Type**: `Object Read`

### **Step 3: Test the URL**

Open this URL in your browser (replace with your bucket name):
```
https://your-bucket-name.s3.amazonaws.com/UTCI_1600.tif
```

It should start downloading or show file info (not an error).

---

## **Option 2: Make the Bucket Public (Alternative)**

If Option 1 doesn't work, make the entire bucket public:

### **Step 1: Bucket Permissions**

1. Go to **AWS Console** → **S3** → Your bucket
2. Go to **"Permissions"** tab (bucket level, not file level)
3. Scroll to **"Block public access (bucket settings)"**
4. Click **"Edit"**
5. **Uncheck all 4 boxes:**
   - ☐ Block all public access
   - ☐ Block public access to buckets and objects granted through new access control lists (ACLs)
   - ☐ Block public access to buckets and objects granted through any access control lists (ACLs)
   - ☐ Block public access to buckets and objects granted through new public bucket or access point policies
   - ☐ Block public and cross-account access to buckets and objects through any public bucket or access point policies
6. Click **"Save changes"**
7. Type `confirm` and click **"Confirm"**

### **Step 2: Bucket Policy (Optional but Recommended)**

1. Still in **"Permissions"** tab
2. Scroll to **"Bucket policy"**
3. Click **"Edit"**
4. Paste this policy (replace `your-bucket-name`):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::your-bucket-name/*"
        }
    ]
}
```

5. Click **"Save changes"**

### **Step 3: Make the File Public**

Follow **Option 1, Step 1** above to make the specific file public.

---

## **Option 3: Use Pre-Signed URL (More Secure)**

If you want to keep the file private but still accessible:

### **Step 1: Generate Pre-Signed URL**

Using AWS CLI:
```bash
aws s3 presign s3://your-bucket-name/UTCI_1600.tif --expires-in 31536000
```

This creates a URL valid for 1 year (31,536,000 seconds).

### **Step 2: Use in Railway**

Copy the pre-signed URL and set it as `UTCI_S3_URL` in Railway.

**Note:** Pre-signed URLs expire, so you'll need to regenerate them periodically.

---

## **Quick Checklist**

- [ ] File has "Grant public read access" enabled in Object ACL
- [ ] Bucket has "Block public access" settings disabled (if needed)
- [ ] Bucket policy allows public read (optional but recommended)
- [ ] URL works when opened in browser (no Access Denied error)
- [ ] `UTCI_S3_URL` is set correctly in Railway variables

---

## **Verify It's Working**

After making changes:

1. **Test in browser**: Open `https://your-bucket-name.s3.amazonaws.com/UTCI_1600.tif`
   - Should download or show file info
   - Should NOT show "Access Denied" XML error

2. **Check Railway logs**: After redeploy, you should see:
   - `✓ UTCI file downloaded successfully`

3. **Test the API**: Try processing a route - it should work now!

