# UI Design Showcase - Media Organizer Pro

## 🎨 Design System

Modern glassmorphic design with elegant animations, perfect contrast, and smooth interactions for both dark and light modes.

### Color Palette

**Light Mode:**
- Primary: `#6366f1` (Indigo)
- Secondary: `#8b5cf6` (Purple)
- Accent: `#06b6d4` (Cyan)
- Background: `#f8fafc` (Slate 50)

**Dark Mode:**
- Primary: `#818cf8` (Indigo 400)
- Secondary: `#a78bfa` (Purple 400)
- Accent: `#22d3ee` (Cyan 400)
- Background: `#0f172a` (Slate 900)

---

## 🧩 Components

### Button Variants

```jsx
import Button from '@/components/ui/Button';

// Default with gradient and shine effect
<Button variant="default">Process Files</Button>

// Secondary
<Button variant="secondary">Filter Audio</Button>

// Accent
<Button variant="accent">Convert Video</Button>

// Destructive
<Button variant="destructive">Delete</Button>

// Outline
<Button variant="outline">Cancel</Button>

// Ghost
<Button variant="ghost">Skip</Button>

// Glass (frosted glass effect)
<Button variant="glass">Settings</Button>

// Gradient (animated rainbow gradient)
<Button variant="gradient">Start Now</Button>
```

**Features:**
- ✨ Shine effect on hover (default, secondary, accent)
- 🎯 Smooth scale animation on click
- 🌈 Gradient backgrounds with smooth transitions
- 💫 Shadow effects that match button color
- ⚡ Lift animation on hover

### Card Variants

```jsx
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

// Default glassmorphic card
<Card variant="default">
  <CardHeader>
    <CardTitle>Smart Organization</CardTitle>
  </CardHeader>
  <CardContent>Content here</CardContent>
</Card>

// Enhanced glass with gradient
<Card variant="glass">...</Card>

// Elevated with shadow
<Card variant="elevated">...</Card>

// Glowing card with pulsing effect
<Card variant="glow">...</Card>
```

**Features:**
- 🔮 Glassmorphism with backdrop blur
- ✨ Gradient overlay on hover
- 🎯 Lift animation on hover
- 💎 Border glow effects
- 🌊 Smooth transitions

### Input Component

```jsx
import Input from '@/components/ui/Input';

// Default glass input
<Input 
  variant="default" 
  placeholder="Enter file path..." 
/>

// Enhanced glass
<Input 
  variant="glass" 
  placeholder="Search files..." 
/>
```

**Features:**
- 🔮 Glassmorphic background
- 💫 Focus ring with primary color
- ✨ Shadow effect on focus
- 🎯 Smooth border transitions

---

## 🎭 Animations

### Available Animations

```jsx
// Float animation (6s loop)
<div className="animate-float">🎬</div>

// Gradient shift (3s loop)
<div className="animate-gradient bg-gradient-to-r from-primary via-secondary to-accent">
  Animated Gradient
</div>

// Pulse glow (2s loop)
<div className="animate-pulse-glow">Glowing Element</div>

// Scale bounce (2s loop)
<div className="animate-scale-bounce">Bouncing</div>

// Glow pulse (2s loop)
<div className="animate-glow-pulse">Pulsing Glow</div>

// Slow spin (8s loop)
<div className="animate-spin-slow">⚙️</div>

// Slide up (entrance animation)
<div className="animate-slide-up">Content</div>

// Fade in
<div className="animate-fade-in">Content</div>
```

---

## 🎨 Utility Classes

### Glass Effects

```jsx
// Standard glass card
<div className="glass-card">Content</div>

// Frosted glass
<div className="frosted-glass">Content</div>

// Glow border (appears on hover)
<div className="glow-border">Content</div>
```

### Text Effects

```jsx
// Static gradient text
<h1 className="text-gradient">Media Organizer Pro</h1>

// Animated gradient text
<h1 className="text-gradient-animated">Made Simple</h1>

// Neon glow text
<span className="neon-text">Live</span>
```

### Background Effects

```jsx
// Animated grid background
<div className="bg-grid">Content</div>

// Noise texture overlay
<div className="noise-overlay" />

// Gradient radial
<div className="bg-gradient-radial from-primary to-transparent">
  Content
</div>
```

---

## 🌓 Dark/Light Mode

Theme toggle is handled automatically via DaisyUI themes. The design system provides perfect contrast in both modes:

**Light Mode:**
- High contrast text on light backgrounds
- Subtle shadows for depth
- Bright accent colors

**Dark Mode:**
- Comfortable reading with reduced eye strain
- Enhanced glow effects
- Vibrant accent colors that pop

---

## 📱 Responsive Design

All components are fully responsive:
- Mobile-first approach
- Touch-friendly button sizes
- Adaptive layouts with Tailwind grid
- Smooth transitions between breakpoints

---

## ✨ Best Practices

1. **Use glass variants** for overlays and modals
2. **Combine animations** sparingly for emphasis
3. **Leverage gradient buttons** for primary actions
4. **Apply glow effects** to highlight active states
5. **Use frosted-glass** for navigation elements

---

## 🎯 Usage Examples

### Hero Section
```jsx
<div className="text-center">
  <h1 className="text-5xl font-bold mb-4">
    Media Organization{' '}
    <span className="text-gradient-animated">Made Simple</span>
  </h1>
  <Button variant="gradient" size="xl">
    Get Started
  </Button>
</div>
```

### Feature Card
```jsx
<Card variant="glass" className="glow-border">
  <CardContent className="p-6">
    <div className="animate-float">🎬</div>
    <h3 className="font-bold">Smart Organization</h3>
    <p>Automatically organize your media files</p>
  </CardContent>
</Card>
```

### Status Badge
```jsx
<div className="frosted-glass px-4 py-2 rounded-xl">
  <span className="animate-pulse-glow">
    🟢 Online
  </span>
</div>
```

---

## 🚀 Performance

All animations use CSS transforms and opacity for optimal performance:
- GPU-accelerated animations
- No layout thrashing
- Smooth 60fps animations
- Minimal repaints

---

Built with ❤️ using React, TailwindCSS, and DaisyUI
