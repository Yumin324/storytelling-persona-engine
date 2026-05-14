# UGCLABs Complete System Blueprint

This document is a code-grounded reverse-engineering analysis of UGCLABs, a full-stack multimodal AI orchestration platform for generating consistent persona-driven UGC-style advertisement assets. The analysis is based on the repository state inspected on 2026-05-14. It intentionally avoids reading or exposing secrets from `backend/.env`.

Where behavior is not named explicitly in code but is implied by control flow, this document labels it as "inferred from implementation".

## 1. SYSTEM OVERVIEW

UGCLABs is a React, FastAPI, SQLite, and local-file-storage application that orchestrates multiple generative AI services to produce scene-level assets for UGC-style advertisements. The final edited advertisement is not assembled inside the application. Instead, the application produces reusable production assets: persona reference images, session-specific reference sheets, structured scripts, scene prompts, first-frame images, silent image-to-video clips, voiceover audio, scene metadata, and downloadable ZIP packages.

The central technical problem solved by the system is consistency across multimodal generation. A user first creates a synthetic persona using structured identity, physical, voice, and personality attributes. The backend turns that persona into a base avatar and then into a multi-angle character reference sheet. Later session and production stages reuse those images as provider inputs so image generations can remain visually aligned with the same synthetic identity. Product and environment consistency are handled similarly through reference sheets.

The system is best described as a modular monolith with asynchronous pipeline orchestration. It is not split into separate backend services. The FastAPI backend owns routing, validation, persistence, provider integration, prompt rendering, compliance checks, local storage, and ZIP export. Long-running provider workflows are triggered through HTTP endpoints but executed via FastAPI `BackgroundTasks` and independent SQLAlchemy sessions.

Key subsystems are:

- Frontend SPA: `frontend/src/App.jsx`, `frontend/src/pages/PersonaBank.jsx`, `frontend/src/pages/Studio.jsx`, and `frontend/src/pages/Production.jsx`.
- Backend API layer: `backend/app/main.py` plus routers in `backend/app/routers/`.
- Database layer: SQLAlchemy models in `backend/app/models.py`, Pydantic schemas in `backend/app/schemas.py`, database setup in `backend/app/database.py`.
- Prompt layer: prompt templates in `backend/app/prompts/` rendered by `backend/app/services/prompt_renderer.py`.
- Provider layer: OpenAI LLM, OpenAI image, Kling video, and ElevenLabs voice services in `backend/app/services/`.
- Compliance layer: testimonial and script validation in `backend/app/services/compliance_service.py`.
- Storage and export layer: `backend/app/services/storage_service.py` and `backend/app/services/zip_service.py`.

The platform generates:

- Synthetic personas.
- Persona base avatars.
- Character reference sheets.
- Session character reference sheets with outfit/accessory edits.
- Environment base images and environment reference sheets.
- Product reference sheets from uploaded product images.
- Structured UGC scene scripts.
- Scene-specific first-frame image prompts, Kling animation prompts, and ElevenLabs voice prompts.
- Generated first-frame PNGs, silent MP4 clips, MP3 voiceovers, and scene ZIP files.

## 2. FULL ARCHITECTURE ANALYSIS

### Frontend Architecture

The frontend is a Vite React application using Tailwind CSS. Dependencies in `frontend/package.json` are React 19, React DOM 19, Vite, `@vitejs/plugin-react`, Tailwind, PostCSS, and Autoprefixer. There is no React Router, Redux, Zustand, server-state library, or component framework.

Application navigation is implemented as local tab state in `frontend/src/App.jsx`. The `tabs` object maps:

- `personas` to `PersonaBank`.
- `studio` to `Studio`.
- `production` to `Production`.

`App` stores `activeTab` in `useState`, renders `Layout`, and passes `setActiveTab` as `onNavigate` to pages. `Layout` wraps all pages in `ErrorBoundary`, renders `TopNav`, and renders `SetupBanner`. `TopNav` displays the product label and tab buttons. `SetupBanner` performs a health check against `/api/health`; in current code it only renders an error if the backend cannot be reached. It receives health data but does not display missing provider configuration warnings.

The frontend page structure is:

- `PersonaBank.jsx`: persona creation, voice loading, persona asset job polling, persona listing, retry, and delete.
- `Studio.jsx`: saved session loading/deletion, persona selection, session form, product upload/removal, reference job generation/polling, script generation/editing/validation, local session memory.
- `Production.jsx`: active session loading from `localStorage`, production job history, production start, production polling, scene preview, retry, and ZIP download links.

State management is local and component-level. Cross-tab continuity is handled by `window.localStorage` key `ugclabs_active_session_id`, set in Studio and read by Production. Backend data is fetched through small API wrapper modules under `frontend/src/api/`.

### Backend Architecture

The backend is a FastAPI app in `backend/app/main.py`. At startup, its lifespan handler calls `init_db()` and `StorageService().ensure_base_directories()`. This creates tables and expected storage directories before serving requests.

Routers mounted under `/api` are:

- `health.py`: configuration and provider readiness.
- `voices.py`: ElevenLabs voice listing.
- `personas.py`: persona CRUD and persona asset generation jobs.
- `sessions.py`: ad session CRUD, product uploads, reference generation, script generation, script saving.
- `production.py`: production job creation, production job listing/status, scenes, scene retry, scene ZIP download.
- `files.py`: safe file retrieval from local storage.

The backend uses SQLAlchemy ORM models as persistent state machines. Status values are defined by `Status` enum in `models.py`: `draft`, `queued`, `running`, `completed`, `failed`, `retrying`, `cancelled`.

### Communication Flow Between Frontend and Backend

The frontend uses `fetch` through `apiRequest` in `frontend/src/api/client.js`. `VITE_API_BASE_URL` is used if present; otherwise the frontend defaults to `http://127.0.0.1:8000`.

JSON endpoints use `Content-Type: application/json`. Product image uploads use raw `fetch` and `FormData` in `frontend/src/api/sessions.js` because multipart file upload cannot use the default JSON wrapper.

Files are not served directly from the filesystem. The frontend calls `fileUrl(relativePath)`, which maps a database-stored relative path to `/api/files/{relative_path}`. The backend validates the path through `StorageService.path_from_relative` before returning `FileResponse`.

### API Design Patterns

The backend uses REST-style resources and action endpoints:

- Resource CRUD: `/api/personas`, `/api/sessions`.
- Action endpoints: `/generate-assets`, `/generate-references`, `/generate-script`, `/production/{session_id}/start`, `/retry`.
- Polling endpoints: `/personas/jobs/{job_id}`, `/sessions/{session_id}/reference-job/{job_id}`, `/production/jobs/{job_id}`, `/production/jobs/{job_id}/scenes`.
- File endpoints: `/api/files/{relative_path}` and `/api/production/scenes/{scene_id}/download`.

Long-running image/video/voice operations are asynchronous from the user's perspective: the initial endpoint creates a job row, returns quickly, and enqueues background work. Script generation is asynchronous in Python (`async def`) but is executed within the request/response cycle.

### Data Flow From User Input to Final Output

1. User creates persona attributes in Persona Bank.
2. Frontend posts persona JSON to `/api/personas`.
3. Backend validates required physical, voice, and personality fields.
4. Frontend calls `/api/personas/{id}/generate-assets`.
5. Backend creates a `persona_generation_jobs` row and runs a background task.
6. Persona pipeline renders `character_base.json`, generates `base.png`, renders `character_reference.json`, and generates `reference_sheet.png`.
7. User opens Studio, selects a completed persona, enters session outfit/accessories, environment, product metadata, CTA, scene count, and uploads product images.
8. Backend stores session data in `ad_sessions` and uploads in `storage/sessions/{session_id}/uploads/`.
9. User triggers reference generation. Backend validates readiness and generates session character, environment, and product reference images.
10. User triggers script generation. Backend renders `script_writer.md`, calls GPT 5.2 through OpenAI Responses API, validates script compliance, repairs once if needed, and stores `script_json`.
11. User edits and saves script if desired. Backend validates edits before storing them.
12. User opens Production and starts generation. Backend validates script and references, creates a `production_jobs` row, creates `scenes` rows, and runs a background production job.
13. Each scene is processed: scene prompts are generated by GPT 5.2, first frame is generated by GPT Image 2.0, video is generated by Kling image-to-video, voiceover is generated by ElevenLabs, and a ZIP is created.
14. Frontend polls job and scene endpoints, previews assets, and exposes scene ZIP download links.

### External AI Integration Points

- OpenAI LLM: `OpenAILLMService` calls `https://api.openai.com/v1/responses` for script JSON and scene prompt JSON.
- OpenAI Image: `OpenAIImageService` calls `/v1/images/generations` for no-reference generation and `/v1/images/edits` when reference images are supplied.
- Kling: `KlingVideoService` calls configured `KLING_API_BASE_URL` and either `/v1/videos/image2video` or `/v1/videos/omni-video` depending on model alias.
- ElevenLabs: `ElevenLabsVoiceService` calls `/v1/voices` and `/v1/text-to-speech/{voice_id}`.

### Request Lifecycle Example: Production Start

1. Frontend calls `startProduction(session.id)` in `frontend/src/api/production.js`.
2. Backend route `POST /api/production/{session_id}/start` loads the `AdSession`.
3. `validate_production_session` checks that `script_json` exists, the script passes `ComplianceService.validate_script`, and session character, environment, and product references exist.
4. Backend creates a `ProductionJob` with `queued` status.
5. Backend creates one `Scene` row for each script scene using `script_visual` and `script_voiceover`.
6. Backend commits, refreshes, and returns the job.
7. FastAPI `BackgroundTasks` starts `run_production_prompt_job(job.id)`.
8. Frontend immediately asks `/api/production/jobs/{job_id}/scenes` and begins polling every 2.5 seconds.
9. Background work processes scene assets concurrently according to `PRODUCTION_SCENE_CONCURRENCY`.
10. The UI updates as paths and statuses are written to SQLite.

## 3. PERSONA ENGINE (CORE MODULE)

### Persona Data Model

The primary persona table is `personas` in `backend/app/models.py`. Fields are:

- `id`: integer primary key.
- `name`: required string up to 120 characters.
- `age`: required integer.
- `gender`: required string.
- `physical_json`: JSON object containing physical identity attributes.
- `voice_json`: JSON object containing ElevenLabs voice selection and settings.
- `personality_json`: JSON object containing behavioral and content-positioning attributes.
- `base_image_path`: relative path to base avatar.
- `reference_sheet_path`: relative path to character reference sheet.
- `status`: status enum.
- `error_message`: provider or validation failure text.
- `created_at`, `updated_at`: timestamp mixin fields.

Pydantic schema `PersonaBase` enforces `name`, `age` between 18 and 70, and `gender` exactly `Male` or `Female`.

### Physical Attribute System

Backend-required physical fields are declared in `REQUIRED_PHYSICAL_FIELDS` in `backend/app/routers/personas.py`:

- `ethnicity`
- `skin_tone`
- `face_shape`
- `jawline`
- `cheekbones`
- `eye_shape`
- `eye_color`
- `eyebrow_shape`
- `eyebrow_color`
- `nose_shape`
- `mouth_shape`
- `lip_fullness`
- `hair_length`
- `hair_texture`
- `default_hair_color`
- `facial_hair`
- `body_type`
- `distinguishing_features`

Frontend options are hard-coded in `PersonaBank.jsx`. For female personas, the UI hides the facial hair selector and sends `facial_hair: "None"`. Distinguishing features are multi-select checkboxes with a special `None` option.

These fields are injected directly into the `character_base.json` prompt. The base avatar prompt names all identity attributes and asks for realistic facial geometry, natural asymmetry, skin texture, and hair detail. This makes the structured data the first identity source for the persona.

### Personality Attribute System

Backend-required personality fields are:

- `core_personality`
- `content_niche`
- `communication_style`
- `humor_level`
- `values`

`values` must be a list with at most two entries. The frontend seeds defaults such as `Relatable`, `Lifestyle`, `Storytelling`, `Subtle`, and `Authenticity`. Personality fields are not used to generate face geometry. They are used in script generation and voice prompt generation to condition writing style, tone, niche, and communication framing.

### Voice Selection Logic

Voices are fetched from ElevenLabs through `GET /api/voices`. `ElevenLabsVoiceService.list_voices` normalizes each provider voice to:

- `voice_id`
- `name`
- `provider`
- `category`
- `description`
- `labels`
- `gender`
- `preview_url`

The frontend filters voices by selected persona gender when a voice has a gender label. The selected voice is stored in `voice_json`, including `voice_id`, `voice_name`, provider, gender category, and default voice settings:

- `stability: 0.5`
- `similarity_boost: 0.75`
- `style: 0.2`
- `use_speaker_boost: true`

The backend only requires that `voice_json.voice_id` exists. During production, `ensure_voiceover` retrieves `persona.voice_json.voice_id` and passes it to ElevenLabs.

### Character Reference Sheet Generation Flow

The persona generation pipeline is implemented in `backend/app/services/persona_generation_service.py`.

1. `generate_persona_assets` route sets persona status to `queued`.
2. It creates `PersonaGenerationJob` with `current_step = "Queued"`.
3. Background task loads persona in a new SQLAlchemy session.
4. Job enters `running`; persona enters `running`.
5. `build_persona_prompt_context` builds a context containing persona identity, voice, personality, empty session/environment/product/scene objects, and UTC timestamp.
6. `PromptRenderer` renders `character_base.json`.
7. `OpenAIImageService.generate_image` generates `storage/personas/{persona_id}/base.png` with no input images.
8. `persona.base_image_path` is stored as a relative path.
9. `PromptRenderer` renders `character_reference.json`.
10. `OpenAIImageService.generate_image` generates `storage/personas/{persona_id}/reference_sheet.png`, using the base image as an edit input.
11. Persona and job become `completed`; paths are stored.

### Identity Consistency Strategy Across Generations

Identity consistency is maintained through a layered reference strategy:

- Structured persona attributes define the first visual identity.
- `base.png` becomes the image source for the character reference sheet.
- `reference_sheet.png` becomes the image source for session-specific character editing.
- `session_character_reference.png` becomes the image source for production scene first frames.

This is not a learned identity embedding system. It is a prompt-and-reference-image consistency strategy. Inferred from implementation: the system relies on GPT Image 2.0's image edit capability to preserve identity when reference images are supplied.

### Reference Image Reuse and Injection

Reference image paths are stored as relative filesystem paths in database columns. Before a provider call, `StorageService.path_from_relative` converts each safe relative path to an absolute local path. The OpenAI image service then opens each file and submits it as `image[]` multipart fields to `/v1/images/edits`.

Session character generation injects only the persona character reference. Scene first-frame generation injects:

- Session character reference.
- Environment reference.
- Product reference only when the product is revealed in this scene or earlier.

Product reveal state is computed by `is_product_revealed_by_scene_number`, which scans script scenes for the product name and otherwise defaults reveal to scene 3 and later.

## 4. PROMPT ENGINEERING PIPELINE

### Prompt Rendering System

Prompts are stored in `backend/app/prompts/`. JSON prompt files contain a `prompt` string plus metadata fields such as `name`, `model`, and `purpose`. Markdown prompt files are read directly. `PromptRenderer` supports placeholders in the form `{{ path.to.value }}`. It resolves nested values from a context dictionary and JSON-serializes dictionaries/lists when inserted.

The renderer also prevents prompt path traversal by requiring `template_name` to be a filename and ensuring the resolved path remains inside the prompt directory.

### All Prompt Templates Found

The repository contains these templates:

- `character_base.json`
- `character_reference.json`
- `session_character_edit.json`
- `environment_base.json`
- `environment_reference.json`
- `product_reference.json`
- `script_writer.md`
- `scene_prompt_writer.md`

### Character Generation Prompt

`character_base.json` is used by `persona_generation_service`. It constructs a hyper-realistic waist-up base avatar from name, age, gender, and all physical identity fields. It includes prohibitions against props, products, text, watermarks, logos, stylization, cartoon/illustration, fantasy features, exaggerated makeup, smoothing, and face reshaping.

Dynamic context injected:

- `persona.name`
- `persona.age`
- `persona.gender`
- every physical identity field
- `meta.timestamp`

### Character Reference Prompt

`character_reference.json` is used after the base avatar exists. It uses the base image as the only identity source and requests a 3x3 contact sheet. It explicitly asks for front, three-quarter, profile, waist-up, close face crop, neutral pose, and candid pose variations while preserving identity.

This prompt is a transformation prompt: one image source becomes a multi-panel reference sheet.

### Session Character Edit Prompt

`session_character_edit.json` applies session outfit and accessories to the existing character reference sheet. It tells the image model to change only clothing and listed accessories while preserving identity, reference sheet structure, face, skin, hair, anatomy, body proportions, lighting, camera angles, and distinguishing features.

This prompt supports ad-session-specific styling without overwriting the permanent persona identity.

### Environment Base and Environment Reference Prompts

`environment_base.json` generates a single photorealistic environment image from:

- `environment.primary_environment`
- `environment.time_of_day`
- `environment.lighting_style`
- `environment.aesthetic`

`environment_reference.json` uses the base environment image as the only source and generates a 3x3 environment reference sheet with consistent room, lighting, aesthetic, perspective, and materials. It requests useful B-roll viewpoints such as establishing view, product placement surface, background depth angle, and close detail.

### Product Reference Prompt

`product_reference.json` uses uploaded product images as source inputs. It creates a 9-angle product reference sheet. It explicitly prohibits hallucinating unreadable text, logos, claims, ingredients, buttons, ports, hidden packaging sides, or materials that are not visible. If a side is not visible, the prompt tells the model to keep it neutral and visually consistent rather than inventing details.

This is the strongest anti-hallucination prompt in the image-reference layer.

### Script Writer Prompt

`script_writer.md` generates strict JSON for UGC-style ad scripts. It is injected with:

- persona name
- core personality
- content niche
- communication style
- humor level
- values
- product name, category, key benefits, target audience, CTA, scene count
- outfit, accessories
- environment, time of day, lighting style, aesthetic
- timestamp

The required arc is:

1. Hook
2. Problem statement
3. Solution/product reveal
4. Demonstration plus benefits
5. CTA

For more than five scenes, the demonstration and benefit section expands while the CTA remains final-only.

The prompt forbids first-person experience claims, testimonials, personal before/after stories, medical/cure/guaranteed/miracle claims, and any claim that the synthetic persona personally used or was changed by the product.

### Scene Prompt Writer Prompt

`scene_prompt_writer.md` converts one approved script scene into:

- `image_prompt` for GPT Image 2.0 first-frame generation.
- `video_prompt` for Kling 3.0 image-to-video generation.
- `voice_prompt` for ElevenLabs TTS input.
- `safety_notes`.

It receives scene visual direction, voiceover, product reveal state, persona summary/name/gender/personality/style/voice ID, session styling, reference paths, environment fields, and product fields.

Image prompt rules enforce vertical 9:16 framing, phone-shot UGC realism, iPhone visual language, reference-sheet consistency, non-cinematic style, no testimonial performance, and no watermarks/UI/text.

Video prompt rules enforce 8-second silent Kling clip, vertical preservation, natural handheld movement, slow movement, no impossible camera physics, no audio, and stable product visibility.

Voice prompt rules require Eleven v3 inline audio tags, no more than two tags unless needed, and preservation of every original voiceover word in the same order. Backend tests verify that ElevenLabs only uses the generated voice prompt if it still contains all required spoken words in order.

### Prompt Chaining Logic

Prompt chaining is explicit in service orchestration:

- Structured persona attributes -> `character_base.json` -> base image.
- Base image -> `character_reference.json` -> character reference sheet.
- Character reference sheet plus session styling -> `session_character_edit.json` -> session character reference.
- Environment fields -> `environment_base.json` -> environment base.
- Environment base -> `environment_reference.json` -> environment reference.
- Uploaded product images -> `product_reference.json` -> product reference.
- Persona/product/environment/session context -> `script_writer.md` -> script JSON.
- Script scene plus references/context -> `scene_prompt_writer.md` -> image/video/voice prompts.
- Scene prompt plus reference sheets -> first-frame image.
- First-frame image plus video prompt -> silent video.
- Voiceover plus voice prompt plus persona voice ID -> voiceover MP3.

### Constraints Enforcement

Constraints are enforced both in prompts and code:

- Prompt instructions prohibit deceptive/testimonial claims.
- OpenAI LLM calls use strict JSON schema output formats.
- `ComplianceService.validate_script` validates JSON shape, scene count, required fields, voiceover word count, banned testimonial phrases, and CTA placement.
- Generated scripts get one automatic repair attempt if validation fails.
- Edited scripts are validated before saving.
- Scene prompt output must include required string fields and string-list `safety_notes`.
- `ElevenLabsVoiceService._speech_text_with_expression` rejects voice prompts that fail to preserve the original spoken words in order.

## 5. SCRIPT INTELLIGENCE ENGINE

Script generation is implemented in `backend/app/services/script_generation_service.py`.

The route `POST /api/sessions/{session_id}/generate-script` loads the session and calls `generate_compliant_script`. The script context merges:

- persona identity fields
- persona personality fields
- persona voice fields
- session outfit and accessories
- environment JSON
- product JSON
- existing script JSON if present
- timestamp

Before calling the LLM, `validate_script_inputs` checks:

- `number_of_scenes` between 3 and 10.
- product `name` exists.
- product `category` exists.
- `key_benefits` exists.
- `target_audience` exists.
- `cta` exists.

The LLM call uses `OpenAILLMService.generate_script`, which posts to the OpenAI Responses API using model `OPENAI_LLM_MODEL`, defaulting to `gpt-5.2`. It requests a strict JSON schema named `ugclabs_script` with required `persona_summary` and `scenes`, and each scene must contain `scene_id`, `visual`, and `voiceover`.

The generated script must follow a UGC structure from hook to problem to solution/product reveal to demonstration/benefit to final CTA. This structure is prompt-driven, then code-validated for count, word length, banned phrases, and CTA placement.

### Constraints Preventing False Claims

False-claim prevention is implemented with a combined prompt and validator strategy. The prompt forbids:

- First-person product use.
- Testimonials.
- Personal transformations.
- Medical/cure/guaranteed/miracle claims.
- Synthetic persona claims of lived product experience.

The validator rejects these banned phrases:

- `I tried`
- `I've tried`
- `I used`
- `I've used`
- `I started using`
- `my results`
- `my skin was`
- `my hair was`
- `changed my life`
- `saved me`
- `cured`
- `guaranteed`
- `miracle`
- `before I found`
- `I struggled with`
- `I was suffering`

This list is intentionally narrow and phrase-based. A limitation is that semantically equivalent deceptive claims may bypass it if they do not match the banned phrase list.

### Personality-Conditioned Generation Logic

Personality conditioning is injected into the script prompt, not enforced by separate code. The prompt receives `core_personality`, `content_niche`, `communication_style`, `humor_level`, and `values`. Inferred from implementation: GPT 5.2 is expected to adapt the script's tone and framing based on these fields. The backend does not perform separate tone scoring or personality validation.

### Editing and Regeneration Workflow

The frontend stores the generated script in `scriptDraft`. `ScriptEditor` allows editing `persona_summary`, each scene ID, each visual direction, and each voiceover. Local validation in `Studio.jsx` warns about missing fields, wrong scene count, banned phrases, and voiceovers over 30 words. The backend validator is stricter: it enforces maximum 16 words per voiceover. This mismatch is an implementation risk because the UI may show "passes local validation" for a 17-30 word voiceover that the backend later rejects.

Regeneration is simply another call to `generateScript(session.id)`, which overwrites `script_json` with the newly generated result.

## 6. PRODUCTION PIPELINE ENGINE

Production orchestration is implemented in `backend/app/services/production_prompt_service.py`.

### Script to Scene Breakdown

The script is already scene-broken by the script intelligence engine. Starting production creates one database `Scene` row per script scene. Each row stores:

- `scene_number`
- `script_visual`
- `script_voiceover`
- initial `status = queued`

The production system then enriches each scene with production prompts and generated media.

### Scene-Level Orchestration

For each scene, `process_scene_assets` executes:

1. `ensure_scene_prompts`
2. `ensure_first_frame`
3. `ensure_video`
4. `ensure_voiceover`
5. `ensure_scene_zip`

Each `ensure_` method is idempotent at the field level: if the relevant path or prompt already exists, it returns without regenerating that asset. This enables retry behavior to resume partially completed scenes.

### Image Prompts

`ensure_scene_prompts` calls GPT 5.2 using `scene_prompt_writer.md`. The returned `image_prompt` is saved on the scene. Before first-frame generation, `apply_session_styling_to_image_prompt` appends mandatory outfit/accessory rules to the image prompt, ensuring the scene first frame uses the session character reference and does not revert to original persona styling.

`ensure_first_frame` sends reference images to OpenAI image editing:

- Session character reference.
- Environment reference.
- Product reference only if the product is revealed.

It requests `size = "1024x1536"` then normalizes output with Pillow. The normalization function crops to a 9:16 ratio and resizes to `1024x1792`. There is a minor inconsistency here: the requested OpenAI size constant is `1024x1536`, which is 2:3, while the target aspect ratio constant is 9:16 and resize output is 1024x1792. The post-processing step corrects the final saved image to 9:16.

### Kling Animation Prompts

`ensure_video` requires `first_frame_path`, sends the first-frame image and `scene.video_prompt` to Kling, creates a task, polls until completion, downloads the video, and stores `video_path`.

Kling payload includes:

- model name from `KLING_VIDEO_MODEL`, normalized through aliases.
- prompt.
- duration `"8"`.
- mode `"pro"` unless configured model string contains `"std"`.
- sound `"off"`.

For omni models, payload uses `image_list` with `type: "first_frame"` and `multi_shot: false`. For regular models, it uses `image`.

### ElevenLabs Voice Prompts

`ensure_voiceover` extracts `voice_id` from the persona. It sends:

- selected voice ID.
- original `scene.script_voiceover`.
- generated `scene.voice_prompt`.
- output path.

`ElevenLabsVoiceService` decides whether to use `voice_prompt` as the API text. It strips audio tags and verifies all original spoken words appear in order. If yes, it uses the tagged prompt; otherwise it falls back to the clean script voiceover. This prevents the generated voice prompt from silently rewriting the advertisement line.

### Synchronization of Multimodal Outputs

Scene synchronization is structural rather than timeline-based. Each scene is assumed to be 8 seconds by prompt convention and Kling duration. The voiceover is constrained to 16 words, intended to fit the 8-second clip. The final application does not mux audio with video and does not produce a single edited ad timeline. It creates separate synchronized scene kits containing first frame, silent video, voiceover, and metadata.

### Full Production Pipeline Step by Step

1. User clicks `Generate Ad` in Production.
2. Backend validates script and references.
3. Backend creates `ProductionJob`.
4. Backend creates one `Scene` row per script scene.
5. Background production job sets job to `running`.
6. Scenes are processed concurrently with a semaphore controlled by `PRODUCTION_SCENE_CONCURRENCY`, default `2`.
7. For each scene, GPT 5.2 creates image, video, and voice prompts.
8. Compliance validates scene prompt output shape and banned testimonial language.
9. GPT Image 2.0 creates first frame from reference sheets.
10. Pillow normalizes the frame to vertical 9:16.
11. Kling creates and completes silent video from the first frame.
12. ElevenLabs generates voiceover audio using the persona voice.
13. ZIP service packages scene metadata and assets.
14. Job progress updates after image, video, and voice paths exist.
15. Job becomes `completed` if all scenes complete, otherwise `failed` with count of failed scene steps.

## 7. ASSET MANAGEMENT SYSTEM

The storage layer is implemented in `StorageService`. `STORAGE_ROOT` defaults to `./storage`, which resolves relative to the backend process working directory. In the repository, generated assets are under `backend/storage/`.

### Folder Structure

Base directories created at startup:

- `storage/personas`
- `storage/sessions`
- `storage/jobs`
- `storage/uploads`

Observed and deterministic paths:

- `storage/personas/{persona_id}/base.png`
- `storage/personas/{persona_id}/reference_sheet.png`
- `storage/sessions/{session_id}/session_character_reference.png`
- `storage/sessions/{session_id}/environment_base.png`
- `storage/sessions/{session_id}/environment_reference.png`
- `storage/sessions/{session_id}/product_reference.png`
- `storage/sessions/{session_id}/uploads/product_001.jpg`
- `storage/jobs/{job_id}/scene_01/first_frame.png`
- `storage/jobs/{job_id}/scene_01/video.mp4`
- `storage/jobs/{job_id}/scene_01/voiceover.mp3`
- `storage/jobs/{job_id}/scene_01/scene_01_assets.zip`

### Naming Conventions

Personas use stable filenames `base.png` and `reference_sheet.png`. Sessions use stable filenames for reference assets. Uploads are named incrementally as `product_{index:03d}{extension}` based on existing upload count. Scenes use `scene_{scene_number:02d}` directories and stable media filenames.

### Scene-Based Asset Grouping

Every production scene has its own directory. This makes retries and downloads independent per scene. A scene can fail while successful scenes remain downloadable.

### ZIP Export Logic

`ZipService.create_scene_zip` writes:

- `scene_metadata.json`
- `first_frame.png`
- `video.mp4`
- `voiceover.mp3`

Metadata includes scene number, script visual, script voiceover, all generated prompts, safety notes, and stored relative paths.

### Retrieval and Reuse Mechanisms

Images, videos, audio, and ZIP paths are persisted in SQLite as relative strings. Runtime code converts them to absolute paths through `StorageService.path_from_relative`. The method rejects absolute paths and `..` path traversal. File serving uses the same safe conversion.

Reference invalidation occurs in `sessions.py`. If persona, outfit, or accessories change, the session character reference path is cleared and file deleted. If environment changes, environment base and reference are cleared. If product details/uploads change, product reference is cleared.

## 8. DATABASE DESIGN (SQLITE + SQLALCHEMY)

The database is SQLite by default: `sqlite:///./ugclabs.db`. SQLAlchemy `create_all` creates tables at startup. A lightweight migration helper `_ensure_sqlite_columns` adds `safety_notes_json` to `scenes` if missing.

### Tables and Models

`personas` stores permanent synthetic persona profiles and their generated base/reference image paths.

`persona_generation_jobs` stores persona asset-generation job status, current step, error, start time, and completion time. It has `persona_id` foreign key to `personas`.

`ad_sessions` stores a configured advertisement session for a persona. It stores outfit, accessories, environment, product data, uploaded product image paths, generated script JSON, session reference asset paths, status, and error.

`session_reference_jobs` stores session reference generation job state. It has `session_id` foreign key to `ad_sessions`.

`production_jobs` stores production run status, progress percentage, current step, errors, start and completion timestamps. It has `session_id` foreign key to `ad_sessions`.

`scenes` stores production scene rows. Each scene links to a session and production job and stores script directions, generated prompts, safety notes, generated asset paths, ZIP path, status, and error.

`api_logs` stores provider call summaries for observability: provider, operation, optional related entity type/id, request summary JSON, response summary JSON, status, status code, duration, error, and created timestamp.

### Relationships

- One `Persona` has many `AdSession` rows.
- One `Persona` has many `PersonaGenerationJob` rows.
- One `AdSession` belongs to one `Persona`.
- One `AdSession` has many `SessionReferenceJob` rows.
- One `AdSession` has many `ProductionJob` rows.
- One `AdSession` has many `Scene` rows.
- One `ProductionJob` has many `Scene` rows.
- One `Scene` belongs to one `AdSession` and one `ProductionJob`.

SQLAlchemy uses `cascade="all, delete-orphan"` on relationships from persona to sessions/jobs and from session/job to child rows. Deleting a persona through the ORM deletes its sessions and associated job/scene rows. File deletion for entire persona/session deletion is not implemented in the route, so filesystem artifacts may remain after database deletion.

### Constraints and Indexing

Primary keys are indexed by default. Several fields have `index=True`:

- `Persona.id`
- `PersonaGenerationJob.id`
- `PersonaGenerationJob.persona_id`
- `AdSession.id`
- `AdSession.persona_id`
- `SessionReferenceJob.id`
- `SessionReferenceJob.session_id`
- `ProductionJob.id`
- `ProductionJob.session_id`
- `Scene.id`
- `Scene.session_id`
- `Scene.job_id`
- `ApiLog.id`
- `ApiLog.provider`
- `ApiLog.related_type`
- `ApiLog.related_id`

There are no uniqueness constraints for persona names, scene numbers per job, or product uploads. There are no explicit database-level JSON schema constraints. Most validation is application-level.

### Persistence Strategy for AI-Generated Assets

SQLite persists metadata and relative paths. Binary assets are not stored in the database. This avoids database bloat but requires filesystem and database consistency. If files are deleted manually, database rows may point to missing assets. Some routes handle this by checking file existence before returning `FileResponse`; generation steps often assume required stored paths exist.

## 9. FRONTEND ARCHITECTURE (REACT)

### Tab System

The tab system is a hand-written local state router. `App.jsx` stores the active tab and renders the page component. `TopNav` maps the same `tabs` object into buttons. The UGCLABs title button navigates back to Persona Bank.

### State Management Approach

The app uses only React local state and effects:

- `PersonaBank` stores personas, voices, active jobs, form state, loading flags, and errors.
- `Studio` stores personas, saved sessions, selected persona, current session, form fields, product uploads, reference job, script draft, loading flags, and errors.
- `Production` stores current session, persona, active job, job history, scenes, loading flags, and errors.

No state is shared through Context. The only persistent browser-side state is `ugclabs_active_session_id`.

### Modal/Form Flows

There are no modal components. Persona creation uses a collapsible form toggled by `isFormOpen`. Studio and Production are page-level forms with sections.

Persona form steps:

1. Identity.
2. Physical attributes.
3. Voice.
4. Personality.
5. Generate.

Studio form sections:

- Saved sessions.
- Choose influencer.
- Session customizations.
- Environment.
- Product information.
- Generated references.
- Script.
- Sticky session summary.

Production sections:

- Previous generations.
- Production summary.
- Asset generation progress.
- Scene cards.

### Session Handling

Sessions are saved backend-side through `/api/sessions`. The frontend can list and load saved sessions. Loading a session hydrates product CTA state with `hydrateProduct`, maps saved persona ID to a persona object, resets upload file inputs, and stores session ID in local storage.

The Production page loads the active session ID from local storage on mount. It can also load historical production jobs and switch the active session based on selected job.

### API Request Handling

`apiRequest` wraps JSON fetch calls. It extracts error messages from either string `detail`, object `detail.message`, object `detail.errors`, Pydantic validation arrays, or `body.message`. Uploads and ZIP downloads are custom. ZIP download is just an anchor link to the backend download endpoint.

### UI-to-Backend Interaction Flow

Persona Bank:

- `listPersonas` on mount.
- `listVoices` on mount.
- `createPersona` on form submit.
- `generatePersonaAssets` immediately after create.
- `getPersonaJob` polling every 2.5 seconds while active jobs exist.
- `deletePersona` on delete.

Studio:

- `listPersonas` and `listSessions` on mount.
- `getSession` and `listPersonas` when loading a saved session.
- `createSession` or `updateSession` for save.
- `uploadProductImages` and `removeProductImage` for uploads.
- `generateReferences` then `getReferenceJob` polling every 3 seconds.
- `generateScript` for script generation.
- `saveScript` for edited scripts.

Production:

- `getSession` and `listPersonas` for active session.
- `listProductionJobs` on mount.
- `startProduction` on `Generate Ad`.
- `getProductionJob` and `getProductionScenes` polling every 2.5 seconds.
- `retryScene` for failed scenes.
- direct link to `sceneDownloadUrl` for ZIP.

## 10. EXTERNAL AI INTEGRATION LAYER

### GPT Image 2.0 Usage Patterns

The code uses `OPENAI_IMAGE_MODEL`, defaulting to `gpt-image-2`. Prompt metadata labels this as GPT Image 2.0. `OpenAIImageService.generate_image` chooses between:

- `/v1/images/generations` when no input images exist.
- `/v1/images/edits` when reference images exist.

Outputs are saved as PNG. The service can parse either base64 image data or a downloadable image URL.

Image generation is used for:

- Persona base avatar.
- Persona character reference sheet.
- Session character reference sheet.
- Environment base image.
- Environment reference sheet.
- Product reference sheet.
- Scene first frames.

### Kling 3.0 Video Generation Logic

The code uses `KLING_VIDEO_MODEL`, defaulting to `kling-v3`, and normalizes aliases such as `kling-3.0` to `kling-v3`. It supports API key bearer auth or access-key/secret-key JWT auth.

Video generation is a two-step task flow:

1. `create_video_task` posts image and prompt.
2. `poll_video_task` polls until completed, failed, cancelled, or timeout.

Polling checks multiple possible response shapes for status and video URL, making the integration tolerant of provider response variation.

### ElevenLabs Voice Synthesis Integration

ElevenLabs is used for both voice listing and text-to-speech.

Voice listing:

- Calls `/v1/voices`.
- Normalizes voice metadata for frontend selection.

Voice synthesis:

- Calls `/v1/text-to-speech/{voice_id}`.
- Sends `output_format=mp3_44100_128`.
- Uses default voice settings.
- Adds `model_id` only when `ELEVENLABS_DEFAULT_MODEL` is configured.
- Saves MP3 bytes to local storage.

### GPT 5.2 Reasoning Role

The OpenAI LLM model defaults to `gpt-5.2`. It is used for structured reasoning/writing tasks:

- Generating compliant scripts from persona/product/session context.
- Repairing invalid generated scripts once.
- Translating approved script scenes into production prompts for image, video, and voice.

The LLM is not used for file storage, provider task control, or compliance validation. Those are deterministic backend operations.

### Failure Handling and Retries

All provider clients inherit retry/log behavior from `ProviderService`.

Retryable HTTP statuses are:

- 408
- 409
- 425
- 429
- 500
- 502
- 503
- 504

Default backoff is 2, 5, 10 seconds. Image generation overrides backoff to 5, 15, 30 seconds. Provider errors are normalized with provider, operation, message, retryable flag, raw error summary, and optional status code. API calls are logged to `api_logs`.

Pipeline failures update job/entity status to `failed` and store `error_message`. Scene-level retry can resume partial work because each generation step checks whether its output already exists.

### Latency Handling Strategies

Latency is handled through:

- Background jobs for persona assets, references, and production.
- Polling from frontend.
- Provider timeouts configured in settings.
- Production scene concurrency controlled by `PRODUCTION_SCENE_CONCURRENCY`.
- Progress percentage based on completed image/video/voice units.

Script generation remains request-bound and can block the frontend until complete. It has timeout and retry behavior but no job row.

## 11. SYSTEM LIMITATIONS & RISKS

Technical bottlenecks:

- FastAPI `BackgroundTasks` run in-process. Jobs may be lost if the server process restarts.
- SQLite is adequate for MVP state but limited for concurrent long-running writes.
- Each production scene performs multiple slow network calls.
- Large local videos and ZIP files can grow storage quickly.
- API logging commits inside provider calls, which may add write contention.

API dependency risks:

- OpenAI, Kling, and ElevenLabs availability directly affects core workflows.
- Provider API response shapes may change. Kling code is flexible, but still dependent on configured base URL and status conventions.
- Provider timeouts may fail long generations.
- Missing provider credentials stop features at runtime.

Consistency failure points:

- Image-reference consistency depends on provider behavior, not deterministic identity locks.
- The product reveal heuristic defaults to scene 3 if product name is not detected.
- Edited scripts can change product reveal timing without explicit UI controls.
- Frontend and backend script word-count limits differ.
- Deleted files may leave database paths stale.

Performance issues:

- No CDN, thumbnailing, or streaming optimization beyond direct file serving.
- Frontend polls fixed intervals, which can create unnecessary traffic.
- Scene preview uses full media URLs; generated images/videos may be large.
- ZIP creation duplicates asset bytes, increasing disk usage.

Scaling limitations:

- Local filesystem storage does not support horizontal backend scaling.
- No external queue, worker pool, or distributed lock.
- No user authentication or multi-tenant isolation.
- No database migrations beyond one manual SQLite column patch.
- No cleanup policy for old jobs/assets/logs.

Security and compliance risks:

- Product uploads are MIME-type checked and size-limited, but deeper image validation is limited.
- File path traversal protections exist, but deleted database rows do not delete all files.
- The banned phrase validator is useful but not semantically complete.
- API logs avoid raw headers/keys, but request summaries include paths and model names.

## 12. INNOVATION & TECHNICAL INSIGHTS

UGCLABs' main innovation is its practical orchestration of multiple generative services into a consistent staged production workflow. It does not call one model once and hope for a complete ad. Instead, it decomposes ad generation into reference creation, structured writing, scene prompt generation, first-frame generation, motion generation, voice synthesis, and export packaging.

Notable design elements:

- Reference-first identity strategy: persona identity becomes a base image, then a reference sheet, then a session-specific reference sheet, then scene image input.
- Separate reference axes: character, environment, and product are generated and reused independently.
- Prompt-chain architecture: every generation stage has an explicit prompt template and context object.
- Compliance-as-code: banned testimonial language and structural script rules are validated in deterministic Python after LLM generation.
- Repair loop: scripts get one LLM repair attempt after backend validation failure.
- Scene kits instead of final muxed video: the system produces editor-ready components, reducing complexity while still supporting real production workflows.
- Partial retry: scene asset steps are idempotent enough to resume after failure.
- Provider abstraction: OpenAI LLM, OpenAI Image, Kling, and ElevenLabs all share retry/error logging concepts.

The persona consistency methodology is especially important. The code uses a chain of visual anchors rather than relying only on natural-language descriptions. This is suitable for university-level research discussion because it highlights a core challenge in multimodal AI systems: identity persistence across heterogeneous generative models. UGCLABs addresses this by turning each stage's output into a stable reference input for the next stage.

## COMPLETE END-TO-END SYSTEM EXPLANATION

The user starts in Persona Bank. They enter a synthetic influencer's name, age, gender, physical attributes, voice selection, and personality traits. The frontend validates basic form completeness and sends the persona to the backend. The backend validates required fields, stores the persona in SQLite, and then starts a persona generation job. GPT Image 2.0 generates a base avatar from the structured physical identity prompt. The same image is reused to generate a 3x3 character reference sheet. The persona is now reusable.

The user moves to Studio. They select a completed persona, choose outfit and accessories, configure environment conditions, enter product metadata, choose scene count and CTA, and upload product reference images. The backend stores this as an ad session. When the user generates references, the backend edits the persona reference sheet into a session character sheet with outfit/accessory changes, generates an environment base and environment reference sheet, and converts uploaded product images into a product reference sheet.

The user then generates a script. GPT 5.2 receives persona personality, product data, environment, session styling, scene count, and CTA. It returns strict JSON with `persona_summary` and scenes. The backend validates scene count, voiceover length, banned testimonial phrases, and CTA placement. If validation fails, GPT 5.2 gets one repair prompt. The accepted script is saved to the session. The user can edit the script and save it, but the backend validates edits before persistence.

The user continues to Production. The frontend loads the active session ID from local storage and shows the script and reference readiness. When production starts, the backend creates a production job and scene rows. For each scene, GPT 5.2 converts approved script directions into first-frame, animation, and voice prompts. GPT Image 2.0 generates a vertical first frame using the session character and environment references, plus the product reference after reveal. Kling 3.0 animates that first frame into an 8-second silent vertical clip. ElevenLabs synthesizes voiceover using the persona's selected voice and validated expressive tags. The backend packages the first frame, video, audio, and metadata into a scene ZIP.

The final output is a set of downloadable scene-level asset kits. Each kit can be reconstructed from database metadata and storage paths: scene script, prompts, safety notes, first-frame PNG, silent video MP4, voiceover MP3, and ZIP package. The final edited advertisement is assembled outside UGCLABs using the generated assets.

## CODEBASE INVENTORY APPENDIX

This appendix identifies every functional source area found during inspection.

### Root Files

- `README.md`: developer setup, environment, run instructions, demo walkthrough, storage notes, troubleshooting, and smoke-test commands.
- `package.json`: root script wrapper exposing `npm run dev`.
- `scripts/dev.mjs`: starts backend Uvicorn and frontend Vite together, prefixes output streams, handles shutdown, and chooses Windows virtualenv Python when present.
- `.env.example`: documented environment template. Real secrets are expected in `backend/.env`, which was not inspected for this analysis.

### Backend Core Files

- `backend/app/main.py`: creates FastAPI app, configures CORS for Vite localhost origins, initializes DB/storage on lifespan startup, and includes all routers.
- `backend/app/config.py`: Pydantic settings model. Defines app environment, database URL, storage root, provider credentials, provider model names, timeout settings, retry count, and production scene concurrency. It also exposes `provider_readiness`.
- `backend/app/database.py`: SQLAlchemy engine/session setup, `Base`, dependency `get_db`, startup `init_db`, and SQLite column compatibility patch for `scenes.safety_notes_json`.
- `backend/app/models.py`: SQLAlchemy ORM models and status enum.
- `backend/app/schemas.py`: Pydantic request/response schemas for personas, sessions, jobs, scenes, scripts, and API logs.
- `backend/app/errors.py`: provider error dataclasses and normalized error conversion.
- `backend/app/__init__.py`, `backend/app/services/__init__.py`, `backend/app/routers/__init__.py`, `backend/app/prompts/__init__.py`: package marker files.

### Backend Routers and Endpoints

Health:

- `GET /api/health`: returns app status, provider readiness, missing config, `.env.example` completeness, database configured flag, and storage configured flag.

Voices:

- `GET /api/voices`: calls ElevenLabs and returns normalized voices.

Personas:

- `GET /api/personas`: list personas newest first.
- `POST /api/personas`: create a persona after required-field validation.
- `GET /api/personas/{persona_id}`: fetch one persona.
- `DELETE /api/personas/{persona_id}`: delete persona row and ORM children.
- `POST /api/personas/{persona_id}/generate-assets`: create persona generation job and enqueue background asset generation.
- `GET /api/personas/jobs/{job_id}`: fetch persona generation job.

Sessions:

- `POST /api/sessions`: create ad session.
- `GET /api/sessions`: list sessions by most recently updated.
- `GET /api/sessions/{session_id}`: fetch one session.
- `PUT /api/sessions/{session_id}`: update session and invalidate stale reference files.
- `DELETE /api/sessions/{session_id}`: delete session row and ORM children.
- `POST /api/sessions/{session_id}/upload-product-images`: upload PNG/JPG/WEBP product images, maximum 8 MB per file.
- `DELETE /api/sessions/{session_id}/product-images?image_path=...`: remove one uploaded product image and clear product reference.
- `POST /api/sessions/{session_id}/generate-references`: validate session and enqueue reference-generation job.
- `GET /api/sessions/{session_id}/reference-job/{job_id}`: fetch one reference job scoped to session.
- `POST /api/sessions/{session_id}/generate-script`: generate and validate script during request.
- `PUT /api/sessions/{session_id}/script`: validate and save edited script JSON.

Production:

- `POST /api/production/{session_id}/start`: validate session, create production job, create scene rows, enqueue production.
- `GET /api/production/jobs`: list production jobs newest first.
- `GET /api/production/jobs/{job_id}`: fetch production job.
- `GET /api/production/jobs/{job_id}/scenes`: list scenes for a production job.
- `POST /api/production/scenes/{scene_id}/retry`: mark scene retrying and enqueue scene retry.
- `GET /api/production/scenes/{scene_id}/download`: return scene ZIP file response.

Files:

- `GET /api/files/{relative_path:path}`: safely serve stored local file.

### Backend Services

- `prompt_renderer.py`: placeholder-based template renderer with path safety and JSON/list serialization.
- `compliance_service.py`: word counting, banned testimonial phrase detection, script validation, and scene prompt output validation.
- `storage_service.py`: deterministic storage paths, directory creation, relative path conversion, and path traversal prevention.
- `zip_service.py`: scene ZIP creation with metadata and media files.
- `provider_base.py`: shared provider key checks, retry loop, backoff, HTTP error normalization, API logging, and output path creation.
- `api_log_service.py`: creates `ApiLog` records.
- `openai_llm_service.py`: OpenAI Responses API integration for strict JSON script and scene prompt generation.
- `openai_image_service.py`: OpenAI image generation/edit integration and response image saving.
- `kling_video_service.py`: Kling image-to-video task creation, polling, JWT/API-key auth, video URL extraction, and video download.
- `elevenlabs_voice_service.py`: ElevenLabs voice listing, text-to-speech, voice metadata normalization, audio tag preservation checks, and MP3 saving.
- `persona_generation_service.py`: persona base and character reference generation pipeline.
- `session_reference_service.py`: session character, environment, and product reference generation pipeline. Uses `asyncio.gather` to run independent reference tasks concurrently.
- `script_generation_service.py`: script prompt construction, OpenAI script generation, compliance validation, and one repair attempt.
- `production_prompt_service.py`: production orchestration, scene concurrency, scene prompt generation, first-frame generation, Kling video generation, ElevenLabs voiceover generation, ZIP creation, progress updates, and scene retry.

### Frontend Source Files

- `frontend/src/main.jsx`: React root creation and CSS import.
- `frontend/src/App.jsx`: local tab router.
- `frontend/src/styles/index.css`: Tailwind imports, global font/background/body/button focus styles.
- `frontend/tailwind.config.js`: content paths, extended neutral color tokens, and font family.
- `frontend/postcss.config.js`: Tailwind and Autoprefixer setup.

Components:

- `Layout.jsx`: page shell with nav, setup banner, main container, and error boundary.
- `TopNav.jsx`: tab navigation and UGCLABs title button.
- `SetupBanner.jsx`: backend reachability health check. Current implementation renders only backend-unreachable errors.
- `StatusBadge.jsx`: status-to-color badge mapping.
- `ProgressBar.jsx`: clamped percentage bar.
- `ErrorPanel.jsx`: reusable error message panel.
- `ErrorBoundary.jsx`: class-based React error boundary with reset button.

API modules:

- `client.js`: API base URL, file URL builder, health check, JSON request wrapper, error extraction.
- `personas.js`: persona CRUD and persona job calls.
- `voices.js`: voice listing call.
- `sessions.js`: session CRUD, upload, image removal, reference job, script generation, script saving.
- `production.js`: production start/list/status/scenes/retry/download URL helpers.

Pages:

- `PersonaBank.jsx`: persona form, physical/personality option definitions, voice filtering, active persona job polling, persona card rendering, local validation.
- `Studio.jsx`: saved sessions, persona selection, session customization forms, environment/product forms, upload preview/removal, reference job polling, script editor, local script validation, local storage session memory.
- `Production.jsx`: active session loading, production history, job polling, progress display, scene media preview, retry, and ZIP download.

### Tests

`backend/tests/test_prompt_and_compliance.py` verifies:

- PromptRenderer replaces placeholders.
- Banned testimonial phrases are detected.
- Script JSON shape and word-count validation work.
- Scene prompt JSON validation catches missing required fields.
- ElevenLabs tagged voice prompt is used only when original script words are preserved.
- ElevenLabs falls back to raw script if the voice prompt does not include the script words.

### Existing Documentation Files

- `docs/system_spec.md`: product-level specification of tabs, flows, fields, status values, and final deliverable.
- `docs/architecture.md`: intended technical architecture and storage/API notes. Some listed future/planned files such as `pipeline_service.py`, `workers/`, and `frontend/src/api/files.js` are not present in the current source tree.
- `docs/pipeline_spec.md`: pipeline-level generation specification.
- `docs/prompt_templates.md`: prompt integration specification.
- `docs/style.md`: UI design system guidance.
- `docs/AGENT.md`: present in repository inventory but not required for runtime architecture analysis.

### Current Runtime Data Observed

The repository contains a local SQLite file at `backend/ugclabs.db`. A schema inspection showed the seven expected tables: `ad_sessions`, `api_logs`, `persona_generation_jobs`, `personas`, `production_jobs`, `scenes`, and `session_reference_jobs`. At inspection time it contained 3 personas, 3 persona generation jobs, 1 ad session, 1 session reference job, 1 production job, 5 scenes, and 365 API log rows.

The `backend/storage` tree contained generated persona, session, and job assets, including PNG first frames, MP4 videos, MP3 voiceovers, and scene ZIPs. This confirms the local file persistence model is active in the working copy.
