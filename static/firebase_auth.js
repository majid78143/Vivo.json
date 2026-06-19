// ── DreamDrop Firebase Auth ────────────────────────────────────
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js';
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword,
         signInWithPopup, GoogleAuthProvider, sendPasswordResetEmail,
         sendEmailVerification, signOut, onAuthStateChanged,
         updatePassword, reauthenticateWithCredential, EmailAuthProvider
       } from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js';

const firebaseConfig = window.FIREBASE_CONFIG;
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

async function sendTokenToServer(user) {
  const idToken = await user.getIdToken();
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const r = await fetch('/set-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify({ idToken })
  });
  const data = await r.json();
  if (data.redirect) window.location.href = data.redirect;
  return data;
}

function showError(msg) {
  const el = document.getElementById('authError');
  if (el) { el.textContent = msg; el.style.display = 'block'; }
  if (window.Toast) Toast.show(msg, 'error', 5000);
}

function showLoading(btn, loading) {
  if (!btn) return;
  btn.disabled = loading;
  btn.innerHTML = loading
    ? '<span class="spin-anim">⏳</span> Please wait...'
    : btn.dataset.original;
}

// ── Email Login ────────────────────────────────────────────────
const loginForm = document.getElementById('loginForm');
if (loginForm) {
  const btn = document.getElementById('loginBtn');
  if (btn) btn.dataset.original = btn.innerHTML;
  loginForm.addEventListener('submit', async e => {
    e.preventDefault();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    if (!email || !password) { showError('Fill all fields'); return; }
    showLoading(btn, true);
    try {
      const cred = await signInWithEmailAndPassword(auth, email, password);
      if (!cred.user.emailVerified) {
        showError('Please verify your email first. Check your inbox.');
        await signOut(auth);
        showLoading(btn, false);
        return;
      }
      await sendTokenToServer(cred.user);
    } catch(err) {
      const msgs = {
        'auth/user-not-found': 'No account found with this email',
        'auth/wrong-password': 'Incorrect password',
        'auth/invalid-email': 'Invalid email address',
        'auth/too-many-requests': 'Too many attempts. Try later.',
        'auth/invalid-credential': 'Invalid email or password'
      };
      showError(msgs[err.code] || err.message);
      showLoading(btn, false);
    }
  });
}

// ── Register ───────────────────────────────────────────────────
const registerForm = document.getElementById('registerForm');
if (registerForm) {
  const btn = document.getElementById('registerBtn');
  if (btn) btn.dataset.original = btn.innerHTML;
  registerForm.addEventListener('submit', async e => {
    e.preventDefault();
    const name = document.getElementById('name').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirm = document.getElementById('confirmPassword').value;
    if (!name || !email || !password) { showError('Fill all fields'); return; }
    if (password.length < 8) { showError('Password must be at least 8 characters'); return; }
    if (password !== confirm) { showError('Passwords do not match'); return; }
    showLoading(btn, true);
    try {
      const cred = await createUserWithEmailAndPassword(auth, email, password);
      await cred.user.updateProfile({ displayName: name });
      await sendEmailVerification(cred.user);
      await signOut(auth);
      showLoading(btn, false);
      document.getElementById('authError').style.display = 'none';
      const success = document.getElementById('authSuccess');
      if (success) {
        success.textContent = '✅ Verification email sent! Please check your inbox.';
        success.style.display = 'block';
      }
      registerForm.reset();
    } catch(err) {
      const msgs = {
        'auth/email-already-in-use': 'Email already registered',
        'auth/weak-password': 'Password too weak',
        'auth/invalid-email': 'Invalid email address'
      };
      showError(msgs[err.code] || err.message);
      showLoading(btn, false);
    }
  });
}

// ── Forgot Password ────────────────────────────────────────────
const forgotForm = document.getElementById('forgotForm');
if (forgotForm) {
  forgotForm.addEventListener('submit', async e => {
    e.preventDefault();
    const email = document.getElementById('email').value.trim();
    if (!email) { showError('Enter your email'); return; }
    const btn = document.getElementById('forgotBtn');
    showLoading(btn, true);
    try {
      await sendPasswordResetEmail(auth, email);
      const success = document.getElementById('authSuccess');
      if (success) {
        success.textContent = '✅ Password reset email sent! Check your inbox.';
        success.style.display = 'block';
      }
      showError('');
      forgotForm.reset();
    } catch(err) {
      const msgs = {
        'auth/user-not-found': 'No account found',
        'auth/invalid-email': 'Invalid email'
      };
      showError(msgs[err.code] || err.message);
    } finally { showLoading(btn, false); }
  });
}

// ── Google Login ───────────────────────────────────────────────
const googleBtn = document.getElementById('googleBtn');
if (googleBtn) {
  googleBtn.addEventListener('click', async () => {
    showLoading(googleBtn, true);
    try {
      const result = await signInWithPopup(auth, googleProvider);
      await sendTokenToServer(result.user);
    } catch(err) {
      if (err.code !== 'auth/popup-closed-by-user') {
        showError(err.message);
      }
      showLoading(googleBtn, false);
    }
  });
}

// ── Change Password ────────────────────────────────────────────
const changePwForm = document.getElementById('changePasswordForm');
if (changePwForm) {
  changePwForm.addEventListener('submit', async e => {
    e.preventDefault();
    const current = document.getElementById('currentPassword').value;
    const newPw = document.getElementById('newPassword').value;
    const confirm = document.getElementById('confirmNewPassword').value;
    if (newPw !== confirm) { showError('Passwords do not match'); return; }
    if (newPw.length < 8) { showError('Min 8 characters'); return; }
    const user = auth.currentUser;
    if (!user) { window.location.href = '/login'; return; }
    const btn = document.getElementById('changePwBtn');
    showLoading(btn, true);
    try {
      const cred = EmailAuthProvider.credential(user.email, current);
      await reauthenticateWithCredential(user, cred);
      await updatePassword(user, newPw);
      if (window.Toast) Toast.show('Password changed!', 'success');
      changePwForm.reset();
    } catch(err) {
      showError(err.code === 'auth/wrong-password' ? 'Current password incorrect' : err.message);
    } finally { showLoading(btn, false); }
  });
}

// ── Logout ─────────────────────────────────────────────────────
const logoutBtn = document.getElementById('logoutBtn');
if (logoutBtn) {
  logoutBtn.addEventListener('click', async () => {
    try { await signOut(auth); } catch(e) {}
    window.location.href = '/logout';
  });
}

window.firebaseAuth = auth;
      
