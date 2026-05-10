# system_spec.md — UGCLABs Product Specification

## Product Summary

UGCLABs is a structured AI production system for generating B-roll style UGC ads using synthetic AI personas. The output is not a fully edited final video. The output is a set of scene-level production assets:

- first-frame image
- silent B-roll video clip
- voiceover audio clip
- scene prompt metadata
- downloadable scene zip

The user then composites the assets in CapCut or another editor.

## Core Principle

UGCLABs does not create testimonial ads. The AI persona is synthetic and has no lived experience. The script must never imply that the persona personally used, benefited from, suffered from, or transformed because of the product.

Allowed framing:

- Product presenter
- Product explainer
- Product demonstration
- Problem-aware product reveal
- Audience-focused benefit explanation

Forbidden framing:

- "I tried this"
- "This changed my life"
- "My skin was dry before this"
- "I was struggling until..."
- Any first-person experience claim
- Any unverifiable performance claim

## Application Navigation

The app has three main tabs:

```txt
Persona Bank | Studio | Production
```

## Tab 1 — Persona Bank

### Purpose

Persona Bank is where users create, view, and delete AI personas.

### Entry Point

The first visible action is a `Create Persona` button.

Clicking it opens a creation form with:

- Name
- Age, numeric, 18–70
- Gender, Male/Female

After this initial identity section, the persona editor shows three internal sections:

1. Physical Attributes
2. Voice
3. Personality Attributes

### Physical Attributes

All values must be stored as structured JSON.

Fields:

- Ethnicity: White, Black, East Asian, South Asian, Southeast Asian, Middle Eastern, Hispanic
- Skin Tone: Very Fair, Fair, Medium, Olive, Brown, Dark
- Face Shape: Oval, Round, Square, Heart, Diamond, Oblong
- Jawline: Soft, Defined, Sharp
- Cheekbones: High, Medium, Low
- Eye Shape: Almond, Round, Hooded, Monolid, Upturned, Downturned
- Eye Color: Brown, Dark Brown, Hazel, Green, Blue, Grey, Amber
- Eyebrow Shape: Straight, Arched, Flat, Curved, Angled
- Eyebrow Color: Black, Blonde, Brown, Dark Brown, Red
- Nose Shape: Straight, Button, Wide, Narrow, Upturned, Hooked
- Mouth Shape: Wide, Medium, Small
- Lip Fullness: Thin, Medium, Full
- Hair Length: Bald, Buzz cut, Short, Medium, Long, Very long
- Hair Texture: Straight, Wavy, Curly, Coily, Kinky
- Default Hair Color: Black, Dark Brown, Brown, Dirty Blonde, Blonde, Auburn, Red, Grey, White
- Facial Hair, male only: None, Light stubble, Full stubble, Short beard, Medium beard, Full beard, Goatee, Mustache
- Body Type: Slim, Athletic, Average, Curvy, Muscular, Plus-size
- Distinguishing Features, multi-select: None, Freckles, Moles, Dimples, Birthmark, Vitiligo, Visible tattoos, Pierced ears, Scar

### Voice

The user selects from ElevenLabs voices.

Requirements:

- Backend must fetch configured ElevenLabs voices where possible.
- UI must filter voices by persona gender where metadata allows.
- If gender metadata is unavailable, allow manual category fields in configuration.
- Store voice ID, voice name, provider, and voice settings JSON.

### Personality Attributes

Fields:

- Core Personality: Relatable, Ambitious, Laid-back, Intellectual, Adventurous, Nurturing, Confident, Quirky, Minimalist, Trendy, Authentic, Sarcastic, Empathetic, Bold
- Content Niche: Lifestyle, Fitness, Beauty, Skincare, Tech, Food, Travel, Wellness, Fashion, Parenting, Finance, Gaming, Home, Pets
- Communication Style: Storytelling, Problem-solution, Review-based, Tutorial, Comparison, Emotional appeal
- Humor Level: None, Dry, Subtle, Moderate, Highly comedic
- Values, pick up to 2: Sustainability, Self-improvement, Family, Freedom, Community, Luxury, Minimalism, Health, Authenticity, Innovation

### Generate Influencer Flow

When the user clicks `Generate Influencer`:

1. Validate all fields.
2. Generate base persona image using GPT Image 2.0 and character base prompt.
3. Use the base image to generate canonical character reference sheet using GPT Image 2.0.
4. Save generated files to local storage.
5. Create persona database record.
6. Show confirmation card with image thumbnail, name, age, gender, and niche.

### Persona Card

Each saved persona card shows:

- base image thumbnail
- name
- age
- gender
- niche tag
- created date
- delete button

## Tab 2 — Studio

### Purpose

Studio is where the user designs a specific ad session using a saved persona.

### Section 1 — Choose Influencer

Display all saved personas in a visual grid.

Each card shows:

- thumbnail
- name
- gender
- age
- niche
- Select button

Selecting a persona loads it into the current session.

### Section 2 — Session Customizations

These are per-session overrides. They do not permanently alter the saved persona.

Fields:

- Outfit: free text
- Accessories: multi-select, including Glasses, Earrings, Necklace, Bracelet, Ring, Hat, Bandana, Watch

When the user generates script/session references, backend uses the character reference sheet and GPT Image 2.0 session-edit prompt to create a session-specific character reference sheet.

### Section 3 — Environment

Fields:

- Primary Environment: Kitchen, Living room, Bedroom, Bathroom, Home gym, Car interior
- Time of Day: Morning, Midday, Golden hour, Evening, Night
- Lighting Style: Natural light, Soft studio, Moody dim, Overcast
- Aesthetic: Minimal clean, Cozy warm, Urban gritty, Luxury, Rustic, Modern trendy

When session references are generated:

1. Generate base environment image using GPT Image 2.0.
2. Generate environment reference sheet using GPT Image 2.0.
3. Save both assets.

### Section 4 — Product Information

Fields:

- Product reference images, file upload
- Product Name
- Product Category: Skincare, Haircare, Supplement, Fitness equipment, Tech gadget, Apparel, Home product, Pet product, Service, App, Other
- Key Benefits
- Target Audience
- Number of Scenes, each scene is exactly 8 seconds
- Call to Action: Link in bio, Use code [X], Shop now, Try for free, Limited time offer, Custom

When session references are generated:

1. Upload product images to local storage.
2. Use GPT Image 2.0 product reference sheet prompt.
3. Save product reference sheet.

### Generate Script

The script generator receives:

- persona personality
- niche
- communication style
- humor level
- values
- product details
- key benefits
- target audience
- number of scenes
- CTA

Output format:

```txt
Scene ID | Visual | Voiceover
```

Required structure:

1. Hook
2. Problem Statement
3. Solution / Product Reveal
4. Demonstration + Benefits
5. CTA

Scene count controls total length:

```txt
total duration = number_of_scenes × 8 seconds
```

Voiceover must be short enough for 8 seconds. Target 12–15 words. Absolute maximum 16 words only if needed.

User can:

- edit script
- regenerate script
- continue to production

## Tab 3 — Production

### Purpose

Production turns the approved script into generated scene assets.

### Pre-Generation Summary

Show:

- selected influencer thumbnail and name
- session outfit/accessories
- environment
- product name and product image
- collapsed script preview
- estimated video length

### Generate Ad Flow

When the user clicks `Generate Ad`:

1. Create production job.
2. Return job ID immediately.
3. Frontend polls job status.
4. Backend uses production prompt agent to break each script scene into:
   - GPT Image 2.0 first-frame prompt
   - Kling 3.0 animation prompt
   - ElevenLabs voice prompt with expression tags
5. For each scene:
   - generate first-frame image
   - generate silent B-roll video
   - generate voiceover audio
   - save all files
   - update scene card
6. Allow scene zip download.

### Scene Card

Each scene card displays:

- scene ID
- original visual direction
- original voiceover
- first-frame prompt preview
- animation prompt preview
- voice prompt preview
- first-frame image
- video clip
- voiceover audio
- status badge
- error message if failed
- retry button
- download zip button

## Status Values

Use consistent statuses:

```txt
draft
queued
running
completed
failed
retrying
cancelled
```

## Expected Final Outcome

The expected deliverable is not a single final edited advertisement. The expected deliverable is a complete production asset kit per scene, suitable for manual finishing in CapCut.
