(function () {
  "use strict";

  const form = document.getElementById("main-form");
  const btnVerify = document.getElementById("btn-verify");
  const btnSubmit = document.getElementById("btn-submit");
  const verifyStatus = document.getElementById("verify-status");
  const modal = document.getElementById("camera-modal");
  const video = document.getElementById("camera-video");
  const canvas = document.getElementById("camera-canvas");
  const btnCapture = document.getElementById("btn-capture");
  const btnSubmitCapture = document.getElementById("btn-submit-capture");
  const btnCloseCamera = document.getElementById("btn-close-camera");
  const resultToast = document.getElementById("result-toast");

  let stream = null;
  let capturedDataUrl = null;

  function showToast(message, isSuccess) {
    resultToast.textContent = message;
    resultToast.className = "toast " + (isSuccess ? "success" : "error");
    resultToast.hidden = false;
    setTimeout(function () {
      resultToast.hidden = true;
    }, 5000);
  }

  function setVerifyState(verified, text) {
    verifyStatus.textContent = text || "";
    verifyStatus.className = "verify-status" + (verified ? " verified" : verified === false ? " invalid" : "");
    btnSubmit.disabled = !verified;
  }

  function openCamera() {
    capturedDataUrl = null;
    btnSubmitCapture.disabled = true;
    modal.hidden = false;
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "user" } })
      .then(function (s) {
        stream = s;
        video.srcObject = stream;
      })
      .catch(function (err) {
        showToast("Could not access camera: " + (err.message || "Permission denied"), false);
        modal.hidden = true;
      });
  }

  function closeCamera() {
    if (stream) {
      stream.getTracks().forEach(function (t) {
        t.stop();
      });
      stream = null;
    }
    video.srcObject = null;
    modal.hidden = true;
    capturedDataUrl = null;
  }

  function captureFrame() {
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);
    capturedDataUrl = canvas.toDataURL("image/jpeg", 0.92);
    btnSubmitCapture.disabled = false;
  }

  function submitForVerification() {
    if (!capturedDataUrl) return;
    btnSubmitCapture.disabled = true;
    btnSubmitCapture.textContent = "Verifying…";

    fetch("/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: capturedDataUrl }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) throw new Error(data.message || "Verification failed");
          return data;
        });
      })
      .then(function (data) {
        closeCamera();
        btnSubmitCapture.textContent = "Submit for verification";
        if (data.verified) {
          setVerifyState(true, "Verified");
          showToast(data.message || "Welcome! Authentication successful.", true);
        } else {
          setVerifyState(false, "User invalid");
          showToast(data.message || "User invalid. Face does not match.", false);
        }
      })
      .catch(function (err) {
        btnSubmitCapture.disabled = false;
        btnSubmitCapture.textContent = "Submit for verification";
        showToast(err.message || "Verification request failed", false);
        setVerifyState(false, "Verification failed");
      });
  }

  btnVerify.addEventListener("click", openCamera);
  btnCloseCamera.addEventListener("click", closeCamera);
  btnCapture.addEventListener("click", captureFrame);
  btnSubmitCapture.addEventListener("click", submitForVerification);

  modal.addEventListener("click", function (e) {
    if (e.target === modal) closeCamera();
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (btnSubmit.disabled) {
      showToast("Please verify yourself first.", false);
      return;
    }
    showToast("Form submitted successfully (demo).", true);
  });
})();
