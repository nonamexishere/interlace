# Interlace UI Design System

**Status**: Active  
**Last updated**: 2026-08  
**Scope**: Tauri 2 + Svelte 5 frontend (`crates/interlace-tauri`)  
**Aesthetic goal**: Calm, private, archival, high-trust desktop tool

Interlace is a local-first personal archive. The UI must feel like a serious, long-lived tool that the user trusts with a lifetime of messages — never flashy, never “AI-generated”, never marketing-site.

Primary references:  
Linear (density + precision) · Obsidian (calm + focus) · Apple Notes / Mail (native desktop reading) · Beeper / clean chat clients (message hierarchy)

Visual quality reference: GitButler and NeoHtop.  
Prefer the density, calmness and polish of these apps over generic web aesthetics.

---

## 1. Principles

1. **Privacy & Trust first**  
   The interface should feel quiet and permanent. No playful illustrations, no gradient hero sections, no “delight” animations that distract from content.

2. **Information density with breathability**  
   Desktop tool → denser than mobile web. Timelines and search results must show many items without feeling cramped. Consistent 4/8 px spacing scale.

3. **Content is the hero**  
   Message text, search hits, and person timelines are the main actors. Chrome, sidebars, and controls stay secondary and quiet.

4. **Native desktop feel**  
   Respect macOS window chrome, keyboard navigation, focus rings, and system appearance. Prefer system fonts where possible.

5. **Owned components only**  
   All interactive UI comes from the existing shadcn-svelte / Bits UI set in `$lib/components/ui`. Do not invent one-off styled elements.

6. **Explicit states**  
   Every list/view must have clear Empty, Loading, Error, and Partial states. Never show a blank white/gray area.

---

## 2. Design Tokens

### Color (Zinc / Slate based)

Use CSS variables already provided by the shadcn setup.

- Background: `background` / `card` / `popover`
- Foreground: `foreground` / `muted-foreground`
- Borders: `border` / `input`
- Accent: single muted accent (prefer indigo or emerald, low saturation)
- Destructive: standard red for delete/merge actions
- Success / Warning: only for status indicators (import success, integrity warnings)

Dark mode is the primary archival aesthetic. Light mode must also be fully supported and follow system preference by default.

### Typography

- Font stack: system UI + Inter / Geist as fallback (`font-sans`)
- Message body: 14–15 px, comfortable line-height (1.5–1.6)
- Secondary / meta: 12–13 px, `muted-foreground`
- Headings: restrained scale (no giant display type)

Avoid decorative or display fonts.

### Spacing & Radius

- Base unit: 4 px
- Common gaps: `gap-2`, `gap-3`, `gap-4`, `gap-6`
- Padding: `p-3`, `p-4`, `p-6`
- Border radius: `rounded-md` (small controls), `rounded-lg` / `rounded-xl` (cards, dialogs)
- Shadows: minimal (`shadow-sm` / `shadow-md` only)

### Icons

- Only Lucide (`@lucide/svelte`)
- Stroke width consistent
- Size: 16 px default, 14 px in dense lists, 20 px in empty states

---

## 3. Layout Patterns

### Primary Shell
- Left sidebar (People / Navigation) — fixed width, collapsible
- Main content area (Timeline / Search / Review)
- Optional right inspector / detail panel
- Custom or native titlebar that respects traffic lights and allows window dragging

### Timeline / Message View
- Virtualized list
- Clear visual hierarchy: sender → timestamp → body → attachments
- Group consecutive messages from the same person
- Subtle separators between days/conversations
- Media thumbnails with lightbox support

### Search
- Prominent, always-available search input
- Instant results with keyboard navigation
- Clear hit highlighting
- Filters (person, platform, date range) as secondary controls

### Import & Review
- Progress is visible and cancelable
- Review queue for identity merges must feel safe and reversible
- Doctor / integrity warnings are calm but unmistakable

---

## 4. Component Guidelines

- Prefer existing shadcn-svelte primitives (`Button`, `Card`, `Dialog`, `Input`, `Command`, `ScrollArea`, `Separator`, `Badge`, `Avatar`, `Tooltip`, etc.)
- Extend only by composition or by adding variants inside the owned component files
- Never hard-code colors or spacing outside the token system
- All interactive elements must have visible focus styles and keyboard support

### Required States for every major view
- Empty (with helpful next action)
- Loading / skeleton
- Error (recoverable + non-recoverable)
- Success / confirmation (especially after import or merge)

---

## 5. Motion & Feedback

- Prefer Svelte transitions (`fade`, `fly`, `slide`) with short durations (150–250 ms)
- No bouncy or long entrance animations
- Loading indicators should be subtle (spinner or skeleton)
- Toast / sonner for non-blocking feedback only

---

## 6. Accessibility & Desktop UX

- Full keyboard navigation
- Visible focus rings
- Proper ARIA roles on custom components
- Respect `prefers-reduced-motion`
- Window resize must not break layouts (sidebar collapses gracefully)
- High contrast support via tokens

---

## 7. Anti-Patterns (Do Not Do)

- Generic AI aesthetic (Inter + purple gradients + rounded cards everywhere)
- Decorative illustrations or empty-state mascots
- Mobile-first breakpoints that waste desktop space
- One-off CSS that bypasses the design tokens
- Auto-playing media or surprise animations
- Over-use of color for non-semantic purposes

---

## 8. Implementation Notes for Agents

When generating or modifying UI code:

1. Always import from `$lib/components/ui/...`
2. Use `cn()` / `tailwind-variants` for class composition
3. Follow the spacing and radius tokens above
4. Provide all four states (empty / loading / error / content)
5. Prefer composition over new components
6. Keep the visual language consistent with the rest of the app

This document is the single source of truth for visual decisions.  
Architecture, data model, and CLI contracts remain in `docs/design/DESIGN.md`.