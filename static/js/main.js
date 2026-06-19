// ── DreamDrop Main JS ──────────────────────────────────────────
'use strict';

// ── Theme ──────────────────────────────────────────────────────
const Theme = {
  init() {
    const saved = localStorage.getItem('dd-theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    const toggle = document.getElementById('themeToggle');
    if (toggle) {
      toggle.checked = saved === 'dark';
      toggle.addEventListener('change', () => this.toggle());
    }
  },
  toggle() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('dd-theme', next);
  }
};

// ── Toast ──────────────────────────────────────────────────────
const Toast = {
  container: null,
  init() {
    this.container = document.getElementById('toastContainer');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.className = 'toast-container';
      this.container.id = 'toastContainer';
      document.body.appendChild(this.container);
    }
  },
  show(message, type = 'info', duration = 3000) {
    if (!this.container) this.init();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = { success: '✅', error: '❌', info: '💜' };
    toast.innerHTML = `${icons[type] || '💬'} ${message}`;
    this.container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }
};

// ── Confetti ───────────────────────────────────────────────────
function launchConfetti(count = 60) {
  const colors = ['#A78BFA','#F9A8D4','#67E8F9','#FCD34D','#6EE7B7'];
  for (let i = 0; i < count; i++) {
    const el = document.createElement('div');
    el.className = 'confetti-piece';
    el.style.cssText = `
      left:${Math.random()*100}vw;
      top:-10px;
      background:${colors[Math.floor(Math.random()*colors.length)]};
      width:${6+Math.random()*8}px;
      height:${6+Math.random()*8}px;
      animation-duration:${2+Math.random()*3}s;
      animation-delay:${Math.random()*1}s;
      border-radius:${Math.random()>0.5?'50%':'2px'};
    `;
    document.body.appendChild(el);
    el.addEventListener('animationend', () => el.remove());
  }
}

// ── Ripple ─────────────────────────────────────────────────────
function addRipple(el) {
  el.style.position = 'relative';
  el.style.overflow = 'hidden';
  el.addEventListener('click', function(e) {
    const rect = this.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = e.clientX - rect.left - size/2;
    const y = e.clientY - rect.top - size/2;
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.cssText = `width:${size}px;height:${size}px;left:${x}px;top:${y}px`;
    this.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
  });
}

// ── Hero Slider ────────────────────────────────────────────────
const HeroSlider = {
  current: 0,
  slides: [],
  dots: [],
  timer: null,
  init() {
    this.slides = Array.from(document.querySelectorAll('.hero-slide'));
    this.dots = Array.from(document.querySelectorAll('.hero-dot'));
    if (!this.slides.length) return;
    this.show(0);
    this.startAuto();
    this.dots.forEach((d, i) => d.addEventListener('click', () => {
      this.show(i); this.resetAuto();
    }));
    const slider = document.querySelector('.hero-slider');
    if (slider) {
      let startX = 0;
      slider.addEventListener('touchstart', e => { startX = e.touches[0].clientX; });
      slider.addEventListener('touchend', e => {
        const diff = startX - e.changedTouches[0].clientX;
        if (Math.abs(diff) > 50) {
          diff > 0 ? this.next() : this.prev();
          this.resetAuto();
        }
      });
    }
  },
  show(idx) {
    this.slides.forEach(s => s.classList.remove('active'));
    this.dots.forEach(d => d.classList.remove('active'));
    this.current = (idx + this.slides.length) % this.slides.length;
    this.slides[this.current].classList.add('active');
    if (this.dots[this.current]) this.dots[this.current].classList.add('active');
  },
  next() { this.show(this.current + 1); },
  prev() { this.show(this.current - 1); },
  startAuto() { this.timer = setInterval(() => this.next(), 4000); },
  resetAuto() { clearInterval(this.timer); this.startAuto(); }
};

// ── Skeleton Loader ────────────────────────────────────────────
function showSkeletons(container, count = 4) {
  if (!container) return;
  container.innerHTML = '';
  for (let i = 0; i < count; i++) {
    const sk = document.createElement('div');
    sk.className = 'skeleton skeleton-card';
    container.appendChild(sk);
  }
}

function hideSkeletons(container) {
  const sks = container ? container.querySelectorAll('.skeleton') : [];
  sks.forEach(s => s.remove());
}

// ── Pull to Refresh ────────────────────────────────────────────
const PullToRefresh = {
  startY: 0,
  indicator: null,
  init() {
    this.indicator = document.querySelector('.ptr-indicator');
    if (!this.indicator) return;
    document.addEventListener('touchstart', e => { this.startY = e.touches[0].clientY; }, { passive: true });
    document.addEventListener('touchend', e => {
      const dy = e.changedTouches[0].clientY - this.startY;
      if (dy > 80 && window.scrollY === 0) {
        this.indicator.classList.add('visible');
        this.indicator.textContent = '🔄 Refreshing...';
        setTimeout(() => window.location.reload(), 800);
      }
    }, { passive: true });
  }
};

// ── Infinite Scroll ────────────────────────────────────────────
const InfiniteScroll = {
  loading: false,
  page: 1,
  endpoint: null,
  container: null,
  init(endpoint, container) {
    this.endpoint = endpoint;
    this.container = container;
    window.addEventListener('scroll', () => this.check(), { passive: true });
  },
  check() {
    if (this.loading) return;
    const threshold = document.body.offsetHeight - window.scrollY - window.innerHeight;
    if (threshold < 200) this.load();
  },
  async load() {
    if (!this.endpoint || !this.container) return;
    this.loading = true;
    this.page++;
    try {
      const r = await fetch(`${this.endpoint}?page=${this.page}`);
      const data = await r.json();
      if (data.html) this.container.insertAdjacentHTML('beforeend', data.html);
      if (data.end) window.removeEventListener('scroll', () => this.check());
    } catch(e) {
      console.error(e);
    } finally {
      this.loading = false;
    }
  }
};

// ── API helper ─────────────────────────────────────────────────
const API = {
  csrfToken: null,
  init() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    this.csrfToken = meta ? meta.getAttribute('content') : '';
  },
  async post(url, data = {}, isForm = false) {
    const options = {
      method: 'POST',
      headers: { 'X-CSRFToken': this.csrfToken }
    };
    if (isForm) {
      options.body = data;
    } else {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(data);
    }
    const r = await fetch(url, options);
    return r.json();
  },
  async get(url) {
    const r = await fetch(url);
    return r.json();
  }
};

// ── Wishlist ───────────────────────────────────────────────────
async function toggleWishlist(productId, btn) {
  try {
    const res = await API.post('/wishlist/toggle', { product_id: productId });
    if (res.success) {
      const isAdded = res.action === 'added';
      btn.textContent = isAdded ? '❤️' : '🤍';
      Toast.show(isAdded ? 'Added to wishlist' : 'Removed from wishlist',
                 isAdded ? 'success' : 'info');
    }
  } catch(e) { Toast.show('Error', 'error'); }
}

// ── Order placement ────────────────────────────────────────────
async function placeOrder(data) {
  const btn = document.getElementById('placeOrderBtn');
  if (btn) { btn.disabled = true; btn.textContent = 'Placing order...'; }
  try {
    const res = await API.post('/place-order', data);
    if (res.success) {
      launchConfetti();
      Toast.show('Order placed successfully! 🎉', 'success', 4000);
      setTimeout(() => window.location.href = '/orders', 2000);
    } else {
      Toast.show(res.error || 'Failed to place order', 'error');
    }
  } catch(e) {
    Toast.show('Network error', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Place Order'; }
  }
}

// ── Coupon ─────────────────────────────────────────────────────
async function applyCoupon() {
  const input = document.getElementById('couponInput');
  if (!input || !input.value.trim()) {
    Toast.show('Enter a coupon code', 'error'); return;
  }
  try {
    const res = await API.post('/coupon/apply', { code: input.value.trim() });
    if (res.success) {
      Toast.show(`Coupon applied! ${res.discount}${res.type==='percent'?'%':' off'}`, 'success');
      window.appliedDiscount = { discount: res.discount, type: res.type };
      updateTotal();
    } else {
      Toast.show(res.error || 'Invalid coupon', 'error');
    }
  } catch(e) { Toast.show('Error applying coupon', 'error'); }
}

// ── Spin Wheel ─────────────────────────────────────────────────
async function spinWheel() {
  const btn = document.getElementById('spinBtn');
  const wheel = document.getElementById('spinWheel');
  if (!btn) return;
  btn.disabled = true;
  if (wheel) {
    const deg = 720 + Math.floor(Math.random() * 360);
    wheel.style.transition = 'transform 3s cubic-bezier(0.17,0.67,0.12,0.99)';
    wheel.style.transform = `rotate(${deg}deg)`;
  }
  try {
    const res = await API.post('/spin-wheel');
    setTimeout(() => {
      if (res.success) {
        if (res.prize > 0) {
          launchConfetti();
          Toast.show(`🎉 You won ${res.prize} coins!`, 'success', 5000);
          const coinsEl = document.getElementById('userCoins');
          if (coinsEl) coinsEl.textContent = parseInt(coinsEl.textContent || 0) + res.prize;
        } else {
          Toast.show('Better luck next time! 😅', 'info');
        }
      } else {
        Toast.show(res.error || 'Spin failed', 'error');
      }
      btn.disabled = false;
    }, 3200);
  } catch(e) {
    Toast.show('Error', 'error'); btn.disabled = false;
  }
}

// ── Daily Reward ───────────────────────────────────────────────
async function claimDailyReward() {
  const btn = document.getElementById('dailyRewardBtn');
  if (btn) btn.disabled = true;
  try {
    const res = await API.post('/daily-reward');
    if (res.success) {
      launchConfetti(30);
      Toast.show(`🎁 Daily reward: ${res.reward} coins!`, 'success', 5000);
    } else {
      Toast.show(res.error || 'Already claimed today', 'error');
    }
  } catch(e) { Toast.show('Error', 'error'); }
  finally { if (btn) btn.disabled = false; }
}

// ── Chat ───────────────────────────────────────────────────────
const Chat = {
  form: null,
  messageList: null,
  init() {
    this.form = document.getElementById('chatForm');
    this.messageList = document.getElementById('chatMessages');
    if (!this.form) return;
    this.form.addEventListener('submit', e => { e.preventDefault(); this.send(); });
    this.scrollToBottom();
    this.startPolling();
  },
  scrollToBottom() {
    if (this.messageList) {
      this.messageList.scrollTop = this.messageList.scrollHeight;
    }
  },
  async send() {
    const input = document.getElementById('chatInput');
    const imageInput = document.getElementById('chatImage');
    if (!input || (!input.value.trim() && !imageInput?.files?.length)) return;
    const formData = new FormData();
    formData.append('message', input.value.trim());
    if (imageInput && imageInput.files[0]) {
      formData.append('image', imageInput.files[0]);
    }
    const sendBtn = document.getElementById('chatSendBtn');
    if (sendBtn) sendBtn.disabled = true;
    try {
      const csrfMeta = document.querySelector('meta[name="csrf-token"]');
      const r = await fetch('/chat/send', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfMeta ? csrfMeta.content : '' },
        body: formData
      });
      const data = await r.json();
      if (data.success) {
        input.value = '';
        if (imageInput) imageInput.value = '';
        this.appendMessage(data.message);
        this.scrollToBottom();
      } else {
        Toast.show(data.error || 'Send failed', 'error');
      }
    } catch(e) { Toast.show('Network error', 'error'); }
    finally { if (sendBtn) sendBtn.disabled = false; }
  },
  appendMessage(msg) {
    if (!this.messageList) return;
    const div = document.createElement('div');
    const isUser = msg.sender === 'user';
    div.className = `msg-bubble msg-${isUser ? 'user' : 'admin'} fade-in`;
    let content = '';
    if (msg.image) content += `<img src="${msg.image}" class="msg-image" onclick="openImg('${msg.image}')">`;
    if (msg.text) content += `<div>${msg.text}</div>`;
    content += `<div class="msg-time">${new Date(msg.sent_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</div>`;
    div.innerHTML = content;
    this.messageList.appendChild(div);
  },
  startPolling() {
    // Poll every 5s for new messages
    setInterval(async () => {
      try {
        const r = await fetch(window.location.href);
        // Simplified: reload if admin sent message
      } catch(e) {}
    }, 5000);
  }
};

// ── Notifications ──────────────────────────────────────────────
async function markRead(nid) {
  try {
    await API.post(`/api/notifications/read/${nid}`);
    const el = document.querySelector(`[data-notif="${nid}"]`);
    if (el) el.classList.remove('unread');
  } catch(e) {}
}

// ── PWA Install ────────────────────────────────────────────────
const PWA = {
  deferredPrompt: null,
  init() {
    window.addEventListener('beforeinstallprompt', e => {
      e.preventDefault();
      this.deferredPrompt = e;
      const banner = document.getElementById('installBanner');
      if (banner && !localStorage.getItem('dd-pwa-dismissed')) {
        banner.style.display = 'flex';
      }
    });
    const btn = document.getElementById('installBtn');
    if (btn) btn.addEventListener('click', () => this.install());
    const dismiss = document.getElementById('installDismiss');
    if (dismiss) dismiss.addEventListener('click', () => {
      const banner = document.getElementById('installBanner');
      if (banner) banner.style.display = 'none';
      localStorage.setItem('dd-pwa-dismissed', '1');
    });
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/static/sw.js').catch(e => {});
    }
  },
  async install() {
    if (!this.deferredPrompt) return;
    this.deferredPrompt.prompt();
    const { outcome } = await this.deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      Toast.show('App installed! 🎉', 'success');
      const banner = document.getElementById('installBanner');
      if (banner) banner.style.display = 'none';
    }
    this.deferredPrompt = null;
  }
};

// ── Image viewer ───────────────────────────────────────────────
function openImg(src) {
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.9);z-index:9999;display:flex;align-items:center;justify-content:center;';
  overlay.innerHTML = `<img src="${src}" style="max-width:90%;max-height:90vh;border-radius:12px;">`;
  overlay.addEventListener('click', () => overlay.remove());
  document.body.appendChild(overlay);
}

// ── Copy to clipboard ──────────────────────────────────────────
function copyText(text, msg = 'Copied!') {
  navigator.clipboard.writeText(text).then(() => Toast.show(msg, 'success'));
}

// ── Bottom nav active ──────────────────────────────────────────
function setActiveNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(item => {
    const href = item.getAttribute('href') || '';
    item.classList.toggle('active',
      href === path || (href !== '/' && path.startsWith(href)));
  });
}

// ── Admin: order status update ─────────────────────────────────
async function updateOrderStatus(orderId, status, tracking = '', delivery = '') {
  try {
    const res = await API.post(`/admin/orders/${orderId}/update`,
      { status, tracking_code: tracking, estimated_delivery: delivery });
    if (res.success) {
      Toast.show('Order updated!', 'success');
      location.reload();
    } else {
      Toast.show(res.error || 'Update failed', 'error');
    }
  } catch(e) { Toast.show('Error', 'error'); }
}

// ── Admin: send notification ───────────────────────────────────
async function sendAdminNotification(uid, title, body) {
  try {
    const res = await API.post('/admin/notifications/send', { uid, title, body });
    if (res.success) Toast.show('Notification sent!', 'success');
    else Toast.show(res.error || 'Failed', 'error');
  } catch(e) { Toast.show('Error', 'error'); }
}

// ── Address form validation ────────────────────────────────────
function validateAddress(form) {
  const required = ['name','phone','address_line','city','state','pincode'];
  for (const field of required) {
    const el = form.querySelector(`[name="${field}"]`);
    if (!el || !el.value.trim()) {
      Toast.show(`Please fill: ${field.replace('_',' ')}`, 'error');
      el && el.focus();
      return false;
    }
  }
  const phone = form.querySelector('[name="phone"]').value.trim();
  if (!/^\d{10}$/.test(phone)) {
    Toast.show('Enter valid 10-digit phone', 'error');
    return false;
  }
  const pin = form.querySelector('[name="pincode"]').value.trim();
  if (!/^\d{6}$/.test(pin)) {
    Toast.show('Enter valid 6-digit pincode', 'error');
    return false;
  }
  return true;
}

// ── Init ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  Theme.init();
  Toast.init();
  API.init();
  PullToRefresh.init();
  HeroSlider.init();
  Chat.init();
  PWA.init();
  setActiveNav();

  // Ripple on all buttons
  document.querySelectorAll('.btn, .nav-item, .menu-item').forEach(addRipple);

  // Flash messages → toasts
  document.querySelectorAll('.flash-msg').forEach(el => {
    Toast.show(el.textContent, el.dataset.type || 'info', 4000);
    el.remove();
  });

  // Fade-in page
  document.body.classList.add('page-transition');

  // Scroll banner duplicate for seamless loop
  const sb = document.querySelector('.scroll-banner-inner');
  if (sb) {
    sb.innerHTML += sb.innerHTML;
  }

  // Lazy load images
  if ('IntersectionObserver' in window) {
    const imgObs = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          const img = e.target;
          if (img.dataset.src) { img.src = img.dataset.src; delete img.dataset.src; }
          imgObs.unobserve(img);
        }
      });
    });
    document.querySelectorAll('img[data-src]').forEach(img => imgObs.observe(img));
  }
});
