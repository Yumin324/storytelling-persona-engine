# style.md — UGCLABs UI Design System Inspired by OpenAI Site UI

## Design Goal

UGCLABs should feel like a premium AI product: calm, intelligent, spacious, minimal, and trustworthy.

The UI should take inspiration from OpenAI's website style:

- clean typography
- generous whitespace
- soft neutral backgrounds
- restrained color palette
- rounded cards
- subtle borders
- simple high-contrast CTAs
- clear hierarchy
- calm motion
- product-focused layout

Avoid loud gradients, neon gaming aesthetics, overly complex dashboards, and cluttered forms.

## Brand Personality

UGCLABs should feel:

- precise
- creative
- technical but approachable
- premium
- calm under complexity
- suitable for a university final-year demo

## Visual Direction

Use a light-first interface with a refined neutral palette.

### Core Colors

```css
--background: #f7f7f4;
--surface: #ffffff;
--surface-muted: #f0f0ed;
--text-primary: #111111;
--text-secondary: #5f5f5b;
--text-muted: #8a8a85;
--border: #deded8;
--border-strong: #c9c9c1;
--accent: #111111;
--accent-hover: #2b2b2b;
--success: #0f7b4f;
--warning: #a16207;
--error: #b42318;
--info: #2563eb;
```

Optional dark panels may be used only for production previews or media viewers.

### Typography

Use system font stack:

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
```

Headings:

- Large page title: 40–52px, tight line height
- Section heading: 22–28px
- Card title: 16–18px
- Body: 14–16px
- Helper text: 12–14px

### Layout

Use a centered max-width layout:

```css
max-width: 1180px;
margin: 0 auto;
padding: 32px 24px;
```

Top nav should be simple:

```txt
UGCLABs                    Persona Bank | Studio | Production
```

Active tab:

- subtle dark text
- bottom border or rounded pill

Inactive tab:

- muted text
- hover darkens text

## Components

### Buttons

Primary button:

- black background
- white text
- rounded-full or rounded-xl
- medium weight
- subtle hover darkening

Secondary button:

- white background
- neutral border
- dark text

Danger button:

- white background
- red text
- red-tinted border

Disabled button:

- muted background
- muted text
- not clickable

### Cards

Cards should be:

```css
background: white;
border: 1px solid var(--border);
border-radius: 24px;
padding: 24px;
box-shadow: 0 1px 2px rgba(0,0,0,0.04);
```

Use cards for:

- persona cards
- studio form sections
- production scene cards
- job status panels

### Forms

Inputs:

- white or slightly muted background
- 1px neutral border
- rounded-xl
- 12–14px padding
- clear labels
- helper text under complex fields

Avoid overwhelming users. Use section cards with short explanations.

### Status Badges

Use small rounded badges.

```txt
Draft      neutral
Queued     gray
Running    blue
Completed  green
Failed     red
Retrying   amber
```

### Progress Bars

Use thin, calm progress bars:

- track: muted gray
- fill: black or blue
- show percentage text beside it

## Page Design

## Persona Bank Page

Header:

```txt
Persona Bank
Create and manage reusable AI influencers for your UGC ad sessions.
```

Primary CTA:

```txt
Create Persona
```

Persona grid:

- 3 columns desktop
- 2 tablet
- 1 mobile

Persona card:

- image thumbnail top
- name, age, gender
- niche badge
- voice name
- status badge
- delete action

Persona creation form should use a stepper:

```txt
1 Identity
2 Physical Attributes
3 Voice
4 Personality
5 Generate
```

## Studio Page

Header:

```txt
Studio
Design the ad concept, product context, and compliant UGC script.
```

Layout:

- Left: form sections
- Right: sticky session summary

Sections:

1. Choose Influencer
2. Session Customizations
3. Environment
4. Product Information
5. Script

Use progressive disclosure. Do not show Production button until script exists.

Script editor:

- table-like scene editor
- each row/card has Visual and Voiceover fields
- show word count for voiceover
- warn if voiceover > 30 words
- warn if testimonial phrase is detected

## Production Page

Header:

```txt
Production
Generate scene-level assets for editing in CapCut.
```

Top summary card:

- persona thumbnail
- product name
- environment
- estimated duration
- job status
- progress bar

Scene cards:

Each card should have a calm technical layout:

```txt
Scene 01         Running
Visual direction
Voiceover
Prompt previews collapsible
First frame preview
Video player
Audio player
Retry / Download ZIP
```

Failed scene cards must be clear, not hidden.

## Media Preview Rules

Images:

- rounded-2xl
- object-cover
- neutral checker or white background

Videos:

- embedded player
- 16:9 ratio
- rounded-2xl

Audio:

- native audio control
- visible file name

## Motion

Use minimal transitions:

- 150ms hover
- 200ms panel expand
- no dramatic animations
- no excessive bouncing/spinning

Loading states:

- use skeleton cards
- use progress indicators
- do not leave blank screens

## Empty States

Persona Bank empty state:

```txt
No personas yet.
Create your first AI influencer to start building UGC ad sessions.
```

Studio no persona selected:

```txt
Select a persona from your bank to begin configuring this ad.
```

Production no session:

```txt
Complete a Studio session first, then continue to Production.
```

## Error UI

Errors should be written in plain language.

Examples:

```txt
OpenAI image generation timed out after 240 seconds. You can retry this step.
```

```txt
Kling video generation failed while polling the provider task. The first frame was saved, so only the video step needs retrying.
```

```txt
ElevenLabs API key is missing. Add ELEVENLABS_API_KEY to your backend .env file.
```

## Responsive Behavior

Desktop:

- two-column layouts allowed
- sticky summaries allowed

Mobile:

- single column
- tabs remain accessible
- forms full width
- media previews stack vertically

## Accessibility

- Use semantic buttons.
- Labels must be linked to inputs.
- Color cannot be the only status indicator.
- Focus states must be visible.
- Buttons must have readable text.

## Final UI Standard

The finished UI should look like a serious AI tool, not a student prototype. It should be simple enough for a non-technical user to operate but detailed enough to show a sophisticated generation pipeline.
