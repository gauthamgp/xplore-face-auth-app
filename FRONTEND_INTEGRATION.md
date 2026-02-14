# Frontend Integration Guide - Image Upload

## What the Backend Accepts

Your two endpoints accept images in **ONE of two ways**:

### **Format 1: Base64 String (Recommended)**
Send the image as a **data URI** with base64 encoding
```json
{
  "user_id": "alice",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAA..."
}
```

### **Format 2: Form Data (File Upload)**
Send as multipart form data
```
POST /api/register
Content-Type: multipart/form-data

user_id=alice
image=<binary-file-data>
```

---

## Method 1: Camera Capture → Base64 (Recommended)

### HTML
```html
<video id="video" width="320" height="240" autoplay></video>
<canvas id="canvas" width="320" height="240" style="display:none;"></canvas>
<button onclick="captureAndRegister()">Capture & Register</button>
<button onclick="captureAndVerify()">Capture & Verify</button>
<input type="text" id="username" placeholder="Enter username">
<div id="result"></div>

<script>
  // Initialize camera on page load
  window.onload = function() {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        document.getElementById('video').srcObject = stream;
      })
      .catch(err => console.error('Camera error:', err));
  };

  // Capture frame from video
  function capturePhoto() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Return base64 string with data URI prefix
    return canvas.toDataURL('image/jpeg');
  }

  // Register with captured photo
  async function captureAndRegister() {
    const username = document.getElementById('username').value;
    if (!username) {
      alert('Please enter username');
      return;
    }

    const imageBase64 = capturePhoto();

    const response = await fetch('http://127.0.0.1:5000/api/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: username,
        image: imageBase64  // Format: "data:image/jpeg;base64,..."
      })
    });

    const result = await response.json();
    const resultDiv = document.getElementById('result');
    
    if (result.success) {
      resultDiv.innerHTML = `
        <p style="color: green;">✓ Registered successfully!</p>
        <p>Stored as: ${result.stored_key}</p>
      `;
    } else {
      resultDiv.innerHTML = `
        <p style="color: red;">✗ Registration failed</p>
        <p>${result.message}</p>
      `;
    }
  }

  // Verify with captured photo
  async function captureAndVerify() {
    const username = document.getElementById('username').value;
    if (!username) {
      alert('Please enter username');
      return;
    }

    const imageBase64 = capturePhoto();

    const response = await fetch('http://127.0.0.1:5000/api/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: username,
        image: imageBase64  // Format: "data:image/jpeg;base64,..."
      })
    });

    const result = await response.json();
    const resultDiv = document.getElementById('result');
    
    if (result.verified) {
      resultDiv.innerHTML = `
        <p style="color: green;">✓ Face verified! Welcome ${username}</p>
      `;
    } else {
      resultDiv.innerHTML = `
        <p style="color: red;">✗ Face mismatch - Not verified</p>
      `;
    }
  }
</script>
```

---

## Method 2: File Upload → Base64

### HTML
```html
<input type="text" id="username" placeholder="Enter username">
<input type="file" id="imageFile" accept="image/*">
<button onclick="registerWithFile()">Register</button>
<button onclick="verifyWithFile()">Verify</button>
<div id="result"></div>

<script>
  // Convert file to base64
  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);  // Returns "data:image/jpeg;base64,..."
      reader.onerror = error => reject(error);
      reader.readAsDataURL(file);
    });
  }

  async function registerWithFile() {
    const username = document.getElementById('username').value;
    const fileInput = document.getElementById('imageFile');
    
    if (!username) {
      alert('Please enter username');
      return;
    }
    if (!fileInput.files[0]) {
      alert('Please select an image');
      return;
    }

    const imageBase64 = await fileToBase64(fileInput.files[0]);

    const response = await fetch('http://127.0.0.1:5000/api/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: username,
        image: imageBase64  // Format: "data:image/jpeg;base64,..."
      })
    });

    const result = await response.json();
    document.getElementById('result').innerHTML = result.success 
      ? `<p style="color: green;">✓ Registered: ${result.stored_key}</p>`
      : `<p style="color: red;">✗ Error: ${result.message}</p>`;
  }

  async function verifyWithFile() {
    const username = document.getElementById('username').value;
    const fileInput = document.getElementById('imageFile');
    
    if (!username || !fileInput.files[0]) {
      alert('Please enter username and select image');
      return;
    }

    const imageBase64 = await fileToBase64(fileInput.files[0]);

    const response = await fetch('http://127.0.0.1:5000/api/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: username,
        image: imageBase64
      })
    });

    const result = await response.json();
    document.getElementById('result').innerHTML = result.verified
      ? `<p style="color: green;">✓ Face verified!</p>`
      : `<p style="color: red;">✗ Face mismatch</p>`;
  }
</script>
```

---

## Method 3: Direct Form Data (File Upload)

If you prefer **NOT** to convert to base64, you can send the file directly:

### HTML
```html
<form onsubmit="handleFormSubmit(event)">
  <input type="text" name="user_id" placeholder="Username" required>
  <input type="file" name="image" accept="image/*" required>
  <button type="submit">Register</button>
</form>

<script>
  async function handleFormSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    
    const response = await fetch('http://127.0.0.1:5000/api/register', {
      method: 'POST',
      body: formData  // Automatically sends as multipart/form-data
      // NO Content-Type header needed - browser sets it automatically
    });

    const result = await response.json();
    console.log(result);
  }
</script>
```

---

## Testing Instructions for QA Team

### **Test Scenario 1: Camera Capture**
1. Open the app in browser
2. Allow camera permission
3. Enter username: `alice`
4. Click "Capture & Register"
5. **Expected Response:**
   ```json
   {
     "success": true,
     "message": "Reference photo stored successfully.",
     "user_id": "alice",
     "stored_key": "users/alice/ref_uuid.jpg"
   }
   ```

### **Test Scenario 2: Verify Same Person**
1. Keep same username: `alice`
2. Capture another photo of the same person
3. Click "Capture & Verify"
4. **Expected Response:**
   ```json
   {
     "success": true,
     "verified": true,
     "message": "Face matches registered user.",
     "user_id": "alice"
   }
   ```

### **Test Scenario 3: Verify Different Person**
1. Change username to: `bob`
2. Capture photo of a DIFFERENT person
3. Click "Capture & Verify"
4. **Expected Response:**
   ```json
   {
     "success": true,
     "verified": false,
     "message": "User invalid. Face does not match the registered user."
   }
   ```

### **Test Scenario 4: File Upload**
1. Use the file upload version
2. Upload a JPG/PNG image file
3. Enter username and click Register
4. Should get same success response

---

## Important Notes for Frontend

1. **Image Format:** JPG and PNG both supported
2. **Base64 String:** Must include the prefix `data:image/jpeg;base64,` or `data:image/png;base64,`
3. **User ID:** Can be `user_id` or `username` (both work)
4. **Always check response:** 
   - `result.success` tells if request succeeded
   - `result.verified` tells if face matched (for verify endpoint)
5. **Error Handling:**
   ```javascript
   if (!result.success) {
     console.error('API Error:', result.message);
   }
   ```

---

## Using Existing Test Page

Your app already has a built-in test page at:
```
http://127.0.0.1:5000/api-test
```

Use this to test both endpoints with camera capture before building custom UI!

---

## Development Server URLs

### Local Testing
```
Register: http://127.0.0.1:5000/api/register
Verify:   http://127.0.0.1:5000/api/verify
Test Page: http://127.0.0.1:5000/api-test
```

### Production (After Deployment to Render)
```
Register: https://your-app-name.onrender.com/api/register
Verify:   https://your-app-name.onrender.com/api/verify
Test Page: https://your-app-name.onrender.com/api-test
```

---

## Quick Copy-Paste for Testing

### cURL - Register
```bash
curl -X POST http://127.0.0.1:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "image": "data:image/jpeg;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
  }'
```

### cURL - Verify
```bash
curl -X POST http://127.0.0.1:5000/api/verify \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "image": "data:image/jpeg;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
  }'
```
