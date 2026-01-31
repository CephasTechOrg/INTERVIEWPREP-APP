// Dark Mode Toggle
const themeToggle = document.getElementById('themeToggle');
const menuToggle = document.getElementById('menuToggle');
const closeMenu = document.getElementById('closeMenu');
const html = document.documentElement;
isActive = false;

// Initialize dark mode from localStorage
function initTheme() {
  const savedTheme = localStorage.getItem('theme') || 'light';
  if (savedTheme === 'dark') {
    html.classList.add('dark-mode');
    updateThemeIcon(true);
  }
}

function updateThemeIcon(isDark) {
  const icon = themeToggle.querySelector('i');
  if (isDark) {
    icon.className = 'fas fa-sun';
  } else {
    icon.className = 'fas fa-moon';
  }
}
  
if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    html.classList.toggle('dark-mode');
    const isDark = html.classList.contains('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeIcon(isDark);
  });
}

if (menuToggle) {
  menuToggle.addEventListener('click', () => {
    document.querySelector('.nav-links').classList.add('active');
  });
}

if (closeMenu) {
  closeMenu.addEventListener('click', () => {
    document.querySelector('.nav-links').classList.remove('active');
  });
}

// Initialize theme on load
document.addEventListener('DOMContentLoaded', initTheme);

// Smooth Scroll Navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    const href = this.getAttribute('href');
    if (href !== '#' && document.querySelector(href)) {
      e.preventDefault();
      document.querySelector(href).scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  });
});

// Scroll Animations
const observerOptions = {
  threshold: 0.1,
  rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, observerOptions);

// Observe all elements with scroll-animate class
document.querySelectorAll('.scroll-animate').forEach(el => {
  observer.observe(el);
});

// Navbar scroll effect
let lastScrollTop = 0;
const navbar = document.querySelector('nav');

window.addEventListener('scroll', () => {
  const scrollTop = window.scrollY;
  
  if (scrollTop > 100) {
    navbar.classList.add('scrolled');
  } else {
    navbar.classList.remove('scrolled');
  }
  
  lastScrollTop = scrollTop;
}, false);

// Interactive Feature Cards
document.querySelectorAll('.feature-card').forEach((card, index) => {
  card.addEventListener('mouseenter', () => {
    card.style.zIndex = 10;
  });
  
  card.addEventListener('mouseleave', () => {
    card.style.zIndex = 1;
  });
});

// Company Logo Interaction
document.querySelectorAll('.company-logo').forEach(logo => {
  logo.addEventListener('click', function() {
    this.style.animation = 'none';
    setTimeout(() => {
      this.style.animation = 'slideInScale 0.6s ease-out';
    }, 10);
  });
});

// Counter Animation for Stats
function animateCounter(element, target, duration = 2000) {
  let start = 0;
  const match = target.match(/\d+/);
  if (!match) return;
  
  const targetNum = parseInt(match[0]);
  const increment = targetNum / (duration / 16);
  
  const timer = setInterval(() => {
    start += increment;
    if (start >= targetNum) {
      element.textContent = targetNum + (target.includes('+') ? '+' : '');
      clearInterval(timer);
    } else {
      element.textContent = Math.floor(start) + (target.includes('+') ? '+' : '');
    }
  }, 16);
}

// Trigger counters when stats section is visible
const statsObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting && !entry.target.dataset.counted) {
      const statNumbers = entry.target.querySelectorAll('.stat-number');
      statNumbers.forEach(stat => {
        const text = stat.textContent.trim();
        animateCounter(stat, text);
      });
      entry.target.dataset.counted = 'true';
      statsObserver.unobserve(entry.target);
    }
  });
}, observerOptions);

const statsSection = document.querySelector('.stats');
if (statsSection) {
  statsObserver.observe(statsSection);
}

// Staggered Animation for Grid Items
function staggerAnimations() {
  const grids = [
    '.features-grid',
    '.types-grid',
    '.company-logos',
    '.tracks-grid',
    '.steps'
  ];

  grids.forEach(selector => {
    const items = document.querySelectorAll(selector + ' > *');
    items.forEach((item, index) => {
      item.style.opacity = '0';
      item.style.animation = `fadeInUp 0.6s ease-out forwards`;
      item.style.animationDelay = `${index * 0.1}s`;
    });
  });
}

document.addEventListener('DOMContentLoaded', staggerAnimations);

// Button Ripple Effect
document.querySelectorAll('button, a.btn-primary, a.btn-secondary, a.btn-cta').forEach(button => {
  button.addEventListener('click', function(e) {
    if (this.tagName === 'BUTTON' && !this.classList.contains('theme-toggle')) {
      const ripple = document.createElement('span');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;

      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = x + 'px';
      ripple.style.top = y + 'px';
      ripple.classList.add('ripple');

      this.appendChild(ripple);

      setTimeout(() => ripple.remove(), 600);
    }
  });
});

// Add ripple CSS dynamically
const rippleStyle = document.createElement('style');
rippleStyle.textContent = `
  .ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.6);
    transform: scale(0);
    animation: ripple-animation 0.6s ease-out;
    pointer-events: none;
  }

  @keyframes ripple-animation {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }
`;
document.head.appendChild(rippleStyle);

// Parallax effect on scroll
window.addEventListener('scroll', () => {
  const scrollY = window.scrollY;
  
  // Subtle parallax for hero
  const hero = document.querySelector('.hero');
  if (hero && scrollY < window.innerHeight) {
    hero.style.transform = `translateY(${scrollY * 0.3}px)`;
    hero.style.opacity = `${1 - scrollY / (window.innerHeight * 1.5)}`;
  }
});

// Mobile Menu Toggle (if needed)
const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
const navLinks = document.querySelector('.nav-links');

if (mobileMenuBtn) {
  mobileMenuBtn.addEventListener('click', () => {
    navLinks.classList.toggle('active');
  });
}

// Prevent event bubbling for nav links on mobile
document.querySelectorAll('.nav-links a').forEach(link => {
  link.addEventListener('click', () => {
    if (navLinks) navLinks.classList.remove('active');
  });
});

// Page load animation
window.addEventListener('load', () => {
  document.body.classList.remove('loading');
});

// Add scroll reveal for sections on mobile
if (window.innerWidth <= 768) {
  document.querySelectorAll('section').forEach(section => {
    section.classList.add('scroll-animate');
    observer.observe(section);
  });
}

// Smooth anchor link handling
document.querySelectorAll('a[href*="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    const href = this.getAttribute('href');
    const target = document.querySelector(href);
    
    if (target) {
      e.preventDefault();
      const offsetTop = target.offsetTop - 80;
      
      window.scrollTo({
        top: offsetTop,
        behavior: 'smooth'
      });
    }
  });
});

// Accessibility: keyboard navigation
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    if (navLinks) navLinks.classList.remove('active');
    closePaymentModal();
  }
});

// ============================================
// PRICING & PAYMENT SYSTEM
// ============================================

const API_BASE = localStorage.getItem('api_base') || 'http://127.0.0.1:8000/api/v1';
let currentPaymentMethod = 'stripe';
let selectedPlan = null;
let selectedPrice = null;

// Payment Modal Management
function createPaymentModal() {
  const modal = document.createElement('div');
  modal.id = 'paymentModal';
  modal.className = 'payment-modal';
  modal.innerHTML = `
    <div class="payment-modal-content">
      <button class="payment-modal-close" onclick="closePaymentModal()">×</button>
      
      <div class="payment-modal-header">
        <h2 class="payment-modal-title" id="paymentTitle">Choose Plan</h2>
        <p class="payment-modal-subtitle" id="paymentSubtitle">Select your payment method</p>
      </div>

      <div class="payment-options">
        <div class="payment-option active" data-method="stripe" onclick="selectPaymentMethod('stripe', this)">
          <i class="fab fa-stripe"></i>
          <div class="payment-option-name">Stripe</div>
        </div>
        <div class="payment-option" data-method="paystack" onclick="selectPaymentMethod('paystack', this)">
          <i class="fas fa-credit-card"></i>
          <div class="payment-option-name">Paystack</div>
        </div>
      </div>

      <form id="paymentForm" class="payment-form">
        <div class="payment-info">
          <i class="fas fa-info-circle"></i> You'll be redirected to complete your payment securely.
        </div>

        <div class="form-group-pricing">
          <label class="form-label-pricing">Email Address</label>
          <input type="email" id="paymentEmail" class="form-control-pricing" placeholder="your@email.com" required/>
        </div>

        <button type="submit" class="btn-pay" id="payBtn">
          <i class="fas fa-lock"></i> <span id="payBtnText">Proceed to Payment</span>
        </button>
      </form>

      <p style="text-align: center; color: var(--text-muted); font-size: 12px; margin-top: 20px;">
        <i class="fas fa-lock"></i> Payments are secured and encrypted
      </p>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Form submission
  document.getElementById('paymentForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    await processPayment();
  });
}

async function openPaymentModal(plan, price) {
  selectedPlan = plan;
  selectedPrice = price;
  
  const modal = document.getElementById('paymentModal') || createPaymentModal();
  const paymentModal = document.getElementById('paymentModal');
  
  if (!paymentModal) {
    createPaymentModal();
    await openPaymentModal(plan, price);
    return;
  }
  
  // Update modal content
  const planNames = { starter: 'Starter', pro: 'Pro', elite: 'Elite' };
  document.getElementById('paymentTitle').textContent = `Upgrade to ${planNames[plan]}`;
  document.getElementById('paymentSubtitle').textContent = `Pay $${(price / 100).toFixed(2)}/month`;
  
  paymentModal.classList.add('active');
  
  // Reset form
  document.getElementById('paymentForm').reset();
  currentPaymentMethod = 'stripe';
  
  // Get user email if authenticated
  const token = localStorage.getItem('token');
  if (token) {
    try {
      const response = await fetch(`${API_BASE}/users/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const user = await response.json();
        document.getElementById('paymentEmail').value = user.email;
      }
    } catch (err) {
      console.log('Could not fetch user data');
    }
  }
}

function closePaymentModal() {
  const modal = document.getElementById('paymentModal');
  if (modal) {
    modal.classList.remove('active');
  }
}

function selectPaymentMethod(method, element) {
  currentPaymentMethod = method;
  
  // Update UI
  document.querySelectorAll('.payment-option').forEach(opt => {
    opt.classList.remove('active');
  });
  element.classList.add('active');
  
  // Update button text
  const btnText = method === 'stripe' ? 'Pay with Stripe' : 'Pay with Paystack';
  document.getElementById('payBtnText').textContent = btnText;
}

async function processPayment() {
  if (!selectedPlan || !selectedPrice) {
    alert('Invalid plan selection');
    return;
  }
  
  const email = document.getElementById('paymentEmail').value;
  if (!email) {
    alert('Please enter your email');
    return;
  }
  
  const payBtn = document.getElementById('payBtn');
  payBtn.disabled = true;
  payBtn.textContent = 'Processing...';
  
  try {
    if (currentPaymentMethod === 'stripe') {
      await processStripePayment(email);
    } else {
      await processPaystackPayment(email);
    }
  } catch (error) {
    console.error('Payment error:', error);
    alert('Payment processing not enabled: ' + error.message);
    payBtn.disabled = false;
    payBtn.textContent = 'Try Again';
  }
}

async function processStripePayment(email) {
  const response = await fetch(`${API_BASE}/billing/stripe/checkout-session`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(localStorage.getItem('token') && {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      })
    },
    body: JSON.stringify({
      planId: selectedPlan,
      email: email,
      successUrl: `${window.location.origin}/dashboard.html?subscription=success`,
      cancelUrl: `${window.location.origin}/index.html?subscription=cancelled`
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create checkout session');
  }
  
  const data = await response.json();
  
  if (data.url) {
    window.location.href = data.url;
  } else {
    throw new Error('No checkout URL returned');
  }
}

async function processPaystackPayment(email) {
  const response = await fetch(`${API_BASE}/billing/paystack/initialize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(localStorage.getItem('token') && {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      })
    },
    body: JSON.stringify({
      planId: selectedPlan,
      email: email,
      redirectUrl: `${window.location.origin}/dashboard.html?subscription=success`
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to initialize payment');
  }
  
  const data = await response.json();
  
  if (data.authorizationUrl) {
    window.location.href = data.authorizationUrl;
  } else {
    throw new Error('No payment URL returned');
  }
}

// Subscribe Button Handler
document.addEventListener('DOMContentLoaded', () => {
  // Initialize payment modal once on page load
  createPaymentModal();
  
  // Add click handlers to subscribe buttons
  document.querySelectorAll('.btn-subscribe').forEach(btn => {
    btn.addEventListener('click', () => {
      const plan = btn.getAttribute('data-plan');
      const price = btn.getAttribute('data-price');
      openPaymentModal(plan, price);
    });
  });
  
  // Close modal when clicking outside
  document.addEventListener('click', (e) => {
    const modal = document.getElementById('paymentModal');
    if (modal && e.target === modal) {
      closePaymentModal();
    }
  });
});
