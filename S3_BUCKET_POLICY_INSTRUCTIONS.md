# S3 Bucket Policy - How to Apply

## **Bucket Policy (Replace `your-bucket-name` with your actual bucket name)**

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

## **Step-by-Step Instructions**

### **1. Copy the Policy**

Copy the policy above and replace `your-bucket-name` with your actual S3 bucket name.

**Example:** If your bucket is `coolest-route-planner-utci`, the Resource line should be:
```json
"Resource": "arn:aws:s3:::coolest-route-planner-utci/*"
```

### **2. Apply in AWS Console**

1. Go to **AWS Console** → **S3**
2. Click on your bucket name
3. Go to the **"Permissions"** tab
4. Scroll down to **"Bucket policy"** section
5. Click **"Edit"**
6. Paste your bucket policy (with your bucket name replaced)
7. Click **"Save changes"**

### **3. Verify**

- You should see the policy displayed in the Bucket policy section
- No errors should appear
- The policy should show `"Effect": "Allow"` and `"Principal": "*"`

### **4. Still Need Object ACL**

**Important:** Even with the bucket policy, you still need to make the individual file public:

1. Click on `UTCI_1600.tif` in your bucket
2. Go to **"Permissions"** tab
3. Under **"Object ACL"**, click **"Edit"**
4. Check **"Grant public read access"**
5. Click **"Save changes"**

### **5. Test**

Open this URL in your browser:
```
https://your-bucket-name.s3.amazonaws.com/UTCI_1600.tif
```

It should download or show file info (not "Access Denied").

---

## **What This Policy Does**

- **`"Principal": "*"`** - Allows anyone (public access)
- **`"Action": "s3:GetObject"`** - Allows reading/downloading objects
- **`"Resource": "arn:aws:s3:::bucket-name/*"`** - Applies to all objects in the bucket
- **`"Effect": "Allow"`** - Grants permission (not deny)

---

## **Security Note**

This policy makes **all objects in your bucket publicly readable**. If you only want the UTCI file public:

1. Use the bucket policy above (for convenience)
2. OR use Object ACL only (more secure, but requires setting it per file)

For a single static file, either approach works fine.

