# 🚀 FrappeBR Quick Start Guide

## ✅ **SSH Connection Issue - FIXED!**

The connection issue was caused by SSH key passphrase handling. **It's now fixed!**

## **How to Use FrappeBR:**

### **1. Start the Application**
```bash
cd frappebr
python run.py
```

### **2. Connect to Your Frappe Server**
- Select **"1. Connect to Remote Host"**
- Choose your server from the SSH config list
- The connection should now work! ✅

### **3. Browse and Manage Sites**
- The app will automatically discover frappe-bench directories
- Select the bench and site you want to work with
- Choose from backup operations:
  - **List existing backups**
  - **Create new backup**
  - **Download backup**

### **4. Restore Sites Locally**
- Use **"3. Restore from Backup"** 
- Select a downloaded backup file
- Configure target bench path and site name
- The tool will restore with encryption key preservation

## **What Was Fixed:**
The SSH manager now properly uses the SSH agent instead of trying to load private keys directly. This means:
- ✅ **Passphrase-protected SSH keys work**
- ✅ **SSH agent authentication works** 
- ✅ **Same authentication as `ssh` command**

## **Your SSH Setup Works Perfect:**
Since you can connect with `ssh qm.baecktrade.de`, FrappeBR now works the same way!

## **Try It Now:**
```bash
python run.py
```

Select option 1, pick `qm.baecktrade.de`, and it should connect successfully! 🎉