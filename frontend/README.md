# Neighbour Approved - Frontend Landing Page

Standalone landing page for rapid design iteration and testing.

## 🚀 Quick Start

Simply open the file in your browser:

```bash
# From the project root
open frontend/index.html

# OR serve with Python for hot-reload
cd frontend
python -m http.server 8080
# Visit: http://localhost:8080
```

## 📁 Structure

```bash
frontend/
├── index.html          # Main landing page (standalone)
├── README.md           # This file
└── assets/             # Future: images, icons, etc.
```

## ⚡ Rapid Iteration Features

### Hot Reload Development

For the best development experience with auto-refresh:

```bash
# Install a simple hot-reload server (one-time)
npm install -g live-server

# Start development server with hot reload
cd frontend
live-server --port=8080 --open=index.html
```

### Built-in JavaScript Console

- Open browser DevTools (F12)
- All interactions logged for debugging
- Form submissions tracked
- Scroll animations visible

## 🎨 Design System

### Colors

- **Primary**: WhatsApp Green (`#25D366`)
- **Secondary**: SA Gold (`#FFB612`)
- **Accent**: Trust Blue (`#1877F2`)
- **Text**: Charcoal (`#2C3E50`)
- **Gray**: `#4A5568`

### Typography

- Font: Inter (Google Fonts)
- Headings: 700 weight
- Body: 400 weight
- Buttons: 600 weight

### Components

- **Hero Section**: WhatsApp-style mockup with gradient background
- **Problem/Solution**: Two-column comparison
- **How It Works**: 3-step process cards
- **Social Proof**: Testimonials + stats
- **Waitlist CTA**: Form with validation

## 📱 Responsive Design

- **Mobile-first** approach
- **Flexbox/Grid** layouts
- **Touch-friendly** buttons (min 44px)
- **Optimized fonts** with `clamp()`

### Breakpoints

- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

## 🔧 Customization Guide

### Quick Color Changes

Edit the CSS `:root` variables:

```css
:root {
  --whatsapp-green: #25d366; /* Primary brand color */
  --sa-gold: #ffb612; /* CTA buttons */
  --trust-blue: #1877f2; /* Accent color */
  --charcoal: #2c3e50; /* Text color */
}
```

### Content Updates

All text content is in HTML - no build process needed:

- **Hero headline**: Line ~38
- **Trust indicators**: Lines ~43-47
- **Testimonials**: Lines ~250-260
- **Stats**: Lines ~264-274

### WhatsApp Mockup

Customize the chat mockup:

- **Group name**: Line ~200
- **Message content**: Lines ~205-208
- **Endorsement**: Lines ~210-213

## 📊 Analytics Ready

The page includes conversion tracking placeholders:

```javascript
// Waitlist signup tracking (line ~350)
console.log("Waitlist signup:", { phone, area });

// Page view tracking (line ~380)
console.log("Neighbour Approved landing page loaded");
```

Replace `console.log` with your analytics service:

```javascript
// Google Analytics
gtag("event", "signup", { event_category: "waitlist" });

// Facebook Pixel
fbq("track", "Lead", { content_name: "waitlist" });

// Mixpanel
mixpanel.track("Waitlist Signup", { area: area });
```

## 🎯 A/B Testing Ready

Easy elements to test:

### Headlines

```javascript
const headlines = [
  "Find Trusted Local Services Through Your Neighbors",
  "Stop Gambling with Fake Reviews - Ask Your Neighbors",
  "Your WhatsApp Groups Know the Best Local Services",
];
document.querySelector("h1").textContent =
  headlines[Math.floor(Math.random() * headlines.length)];
```

### CTA Buttons

```javascript
const ctas = ["Join the Waitlist", "Get Early Access", "Find Trusted Services"];
```

### Colors

```javascript
// Test different primary colors
document.documentElement.style.setProperty("--whatsapp-green", "#34D399"); // Different green
```

## 🧪 Testing Checklist

### Functionality

- [ ] Smooth scroll navigation works
- [ ] Form validation prevents empty submissions
- [ ] Form shows success state after submission
- [ ] All hover effects work on desktop
- [ ] Touch interactions work on mobile

### Performance

- [ ] Fonts load quickly (preconnect implemented)
- [ ] No layout shift during load
- [ ] Animations are smooth (60fps)
- [ ] Page loads under 3 seconds

### Accessibility

- [ ] All images have alt text
- [ ] Form inputs have labels
- [ ] Color contrast meets WCAG standards
- [ ] Tab navigation works
- [ ] Screen reader friendly

### Mobile

- [ ] No horizontal scroll
- [ ] Buttons are touch-friendly (44px+)
- [ ] Text is readable without zoom
- [ ] Forms work with mobile keyboards

## 🚀 Deployment Options

### Simple Deployment

- **Netlify**: Drag and drop the `frontend` folder
- **Vercel**: Connect GitHub repo, deploy from `frontend/`
- **GitHub Pages**: Enable in repo settings

### Custom Domain Setup

Update these meta tags for production:

```html
<meta property="og:url" content="https://neighbourapproved.co.za" />
<meta
  property="og:image"
  content="https://neighbourapproved.co.za/og-image.png"
/>
<link rel="canonical" href="https://neighbourapproved.co.za" />
```

## 💡 Future Enhancements

### Interactive Elements

- [ ] Video testimonials
- [ ] Interactive WhatsApp mockup
- [ ] Map showing coverage areas
- [ ] Real-time waitlist counter

### Performance

- [ ] Image optimization and lazy loading
- [ ] CSS/JS minification
- [ ] Service Worker for offline capability
- [ ] Critical CSS inlining

### Features

- [ ] Dark mode toggle
- [ ] Multi-language support (Afrikaans, Zulu)
- [ ] Email capture validation
- [ ] SMS verification for phone numbers

---

**Happy iterating!** 🎨 This setup lets you make changes and see results immediately - perfect for rapid design exploration and user testing.
