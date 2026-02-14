# API Quick Reference

## Two Main Endpoints

### 1. Register Endpoint
```
POST /api/register
```

**What it does:** Stores a reference photo for a user in S3

**Input (JSON):**
```json
{
  "user_id": "alice",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABA..."
}
```

**Output (Success):**
```json
{
  "success": true,
  "message": "Reference photo stored successfully.",
  "user_id": "alice",
  "stored_key": "users/alice/ref_12345.jpg"
}
```

---

### 2. Verify Endpoint
```
POST /api/verify
```

**What it does:** Checks if a submitted photo matches the user's registered reference photos

**Input (JSON):**
```json
{
  "user_id": "alice",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABA..."
}
```

**Output (Match Found):**
```json
{
  "success": true,
  "verified": true,
  "message": "Face matches registered user.",
  "user_id": "alice"
}
```

**Output (No Match):**
```json
{
  "success": true,
  "verified": false,
  "message": "User invalid. Face does not match the registered user."
}
```

---

## How to Get Base64 Image from Frontend

### From Camera Stream
```javascript
function capturePhoto() {
  // Assuming you have a video element and canvas
  const video = document.getElementById('video');
  const canvas = document.getElementById('canvas');
  const context = canvas.getContext('2d');
  
  // Draw current video frame to canvas
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  
  // Get base64 string
  const base64 = canvas.toDataURL('image/jpeg');
  return base64;  // includes 'data:image/jpeg;base64,' prefix
}
```

### From File Upload
```javascript
function handleFileUpload(event) {
  const file = event.target.files[0];
  const reader = new FileReader();
  
  reader.onload = function(e) {
    const base64 = e.target.result;  // includes 'data:image/jpeg;base64,' prefix
    console.log(base64);
  };
  
  reader.readAsDataURL(file);
}
```

---

## Complete Frontend Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Face Auth</title>
</head>
<body>
    <input type="text" id="username" placeholder="Username">
    <button onclick="handleRegister()">Register</button>
    <button onclick="handleVerify()">Verify</button>
    
    <video id="video" width="320" height="240" autoplay></video>
    <canvas id="canvas" style="display:none;"></canvas>
    
    <div id="result"></div>

    <script>
        // Initialize camera
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                document.getElementById('video').srcObject = stream;
            });

        function capturePhoto() {
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
            return canvas.toDataURL('image/jpeg');
        }

        async function handleRegister() {
            const username = document.getElementById('username').value;
            const imageBase64 = capturePhoto();

            const response = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: username,
                    image: imageBase64
                })
            });

            const result = await response.json();
            document.getElementById('result').innerHTML = 
                result.success ? '✓ Registered!' : '✗ ' + result.message;
        }

        async function handleVerify() {
            const username = document.getElementById('username').value;
            const imageBase64 = capturePhoto();

            const response = await fetch('/api/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: username,
                    image: imageBase64
                })
            });

            const result = await response.json();
            document.getElementById('result').innerHTML = 
                result.verified ? '✓ Face verified!' : '✗ Face mismatch';
        }
    </script>
</body>
</html>
```

---

## Deployment

**Local Testing:**
```bash
python -m pip install -r requirements.txt
uvicorn app:app --reload
# Access: http://localhost:8000/api-test
```

**Production (Render/Railway/Fly):**
1. Push code to GitHub
2. Add environment variables in hosting platform dashboard
3. Automatic deployment on every push!

**Your public URLs will be:**
- Register: `https://your-app.onrender.com/api/register`
- Verify: `https://your-app.onrender.com/api/verify`
