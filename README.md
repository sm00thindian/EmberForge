# EmberForge Companion

**A Personal Physical AI Companion for Makers, Musicians & Problem Solvers**  
*Glowing with practical wisdom, creative spark, and quiet presence — right on your workbench or porch in rural Oklahoma.*

[![Status](https://img.shields.io/badge/Status-Phase%200%20Setup%20Complete-brightgreen)](https://drive.google.com/drive/folders/1zx81C6WtJgi0lBX9VWcnGYJVXfT1cOme)
[![Hardware](https://img.shields.io/badge/Hardware-ESP32--S3-orange)](https://www.espressif.com/)
[![LLM](https://img.shields.io/badge/LLM-Grok%20%2F%20xAI%20API-blue)](https://x.ai/)
[![License](https://img.shields.io/badge/License-Personal%20Project-lightgrey)](.)

---

## Vision

EmberForge is a personal, physical AI companion that feels like a warm digital ember from a forge — glowing with practical wisdom, creative spark, and quiet presence. It lives on a desk, workbench, or porch in rural Oklahoma. 

It is **not** a generic chatbot in a box. It is a trusted maker's companion that helps its owner:

- Create music and lyrics (raw alternative rock, post-grunge, reflective indie folk — Glass Canons + Kilynn Ross style)
- Solve real hands-on problems (motorcycle fixes, property projects, outdoor gear, fishing, knife making, etc.)
- Explore ideas and carry personal knowledge safely
- Blend the tangible magic of physical projects with deep customization powered by Grok

The device should feel **handcrafted and authentic** — a bit gritty, warm, and real rather than polished corporate tech. It supports both quick voice interactions and deeper creative sessions.

---

## Core Philosophy & Uniqueness

- **Maker-first & hands-on**: Designed so the builder enjoys the process as much as the result.
- **Creatively alive**: Excellent at helping with music/lyric brainstorming in raw alternative rock, post-grunge, and reflective indie folk styles.
- **Practically wise**: Strong at real-world problem solving (motorcycle maintenance, property projects, outdoor adventures, fishing, knife crafting).
- **Private & user-controlled**: Knowledge base is 100% owner-owned. No forced cloud lock-in. Designed with graceful degradation for intermittent rural internet.
- **Warm but honest personality**: Can be encouraging, direct, or switch into "grumpy artist" mode when requested. Optional gentle faith-integrated responses (scripture-aware but never preachy unless asked).
- **Modular & extensible**: Start simple, add capabilities over time without rewriting everything.

---

## Target Form Factor (MVP)

- Small physical device using **ESP32-S3** (Xiao or similar recommended for audio capabilities)
- **Push-to-talk button** (wake word support planned later)
- Small color or monochrome screen for visual feedback and text display
- Microphone + speaker for voice I/O
- 3D-printable or simple enclosure (optionally with warm amber/orange LED "ember" glow effect)
- WiFi for cloud features; designed with future local/offline paths in mind
- Optional web dashboard (accessible from phone or computer) for managing agents, uploading knowledge, and deeper interactions

---

## Key Features (Phased Development)

### Phase 1: Core Voice Loop (Foundation)
Hardware setup + basic push-to-talk → Grok response on screen + voice output.

### Phase 2: Agent System
Multiple custom agents with distinct personalities and system prompts (Creative/Music agent, Practical/Maker agent, Personal Knowledge agent, etc.).

### Phase 3: Knowledge Base
Upload personal documents/text for private RAG/context injection. Owner-owned knowledge that stays private.

### Phase 4: Voice Personality
TTS with different voices + optional voice cloning path. Natural, characterful responses.

### Phase 5: Creative Tools
Specialized music/lyric co-writer agent + prompt optimization helpers tailored to Glass Canons / Kilynn Ross sonic identity.

### Phase 6: Advanced Capabilities
Dashboard, multi-device support, local LLM fallback options, and fun extensions (trip planner, story mode, maintenance logger, etc.).

---

## Tech Stack Preferences

| Layer          | Technology                          | Notes |
|----------------|-------------------------------------|-------|
| **Hardware**   | ESP32-S3 (Xiao ESP32-S3 or equivalent) | Excellent audio support, small form factor |
| **LLM**        | Grok / xAI API (primary)            | Intelligence + agent personalities. Easy to swap |
| **Backend**    | Python + FastAPI                    | Runs on home computer, mini-PC, or VPS |
| **STT**        | OpenAI Whisper or local alternative | Voice input |
| **TTS**        | ElevenLabs (quality + cloning) or local | Natural voice output |
| **Knowledge**  | Simple file-based or ChromaDB       | Private RAG / vector store |
| **Frontend**   | Streamlit or lightweight React      | Web dashboard for agent management (later phases) |
| **Firmware**   | Arduino / ESP-IDF                   | Readable, well-commented code |
| **Storage**    | Google Drive (this folder)          | Project docs, prompts, knowledge base |

**Design Principles**: Modularity, clear documentation, test one piece at a time. Rural context considered — works gracefully with intermittent connectivity.

---

## Development Approach (Critical)

We work **strictly step-by-step and modular**. Never build everything at once.

For every phase or request, you will receive:
1. Clear plan with goals and success criteria
2. Parts list / wiring (text description + ASCII or simple diagram)
3. Complete, copy-paste ready code with explanations
4. Testing steps
5. Next logical step options

High-quality system prompts for agents are crafted carefully. Everything is documented so the project remains maintainable and enjoyable to build.

---

## Proposed Project Structure (in this Google Drive folder)

```
EmberForge_Companion/
├── README.md                 ← You are here
├── docs/
│   ├── phase-1-core-voice-loop.md
│   ├── agent-prompts/
│   └── hardware-notes/
├── firmware/
│   ├── esp32_voice_loop/
│   └── ...
├── backend/
│   ├── fastapi_app/
│   └── agents/
├── knowledge_base/           ← Private documents & RAG sources (owner only)
├── prompts/                  ← System prompts, style guides, music co-writer templates
└── assets/
    ├── enclosure/
    └── images/
```

---

## Success Criteria for the Project

- A working physical device you can actually talk to and get useful responses from
- At least 3 distinct, high-quality custom agents (Creative/Music, Practical/Maker, Personal Knowledge)
- Clean, well-commented code you can understand and modify
- The build process itself is enjoyable and educational
- The final companion feels personal and unique — not just "another AI gadget"

---

## Current Status (June 2026)

- ✅ Google Drive connection tested and verified (folder accessible)
- ✅ This README.md created in the project folder
- ⏳ Awaiting your signal to begin **Phase 1: Core Voice Loop**

---

## How to Begin

When you're ready, simply say:

> **"Start Phase 1"**

or

> **"Let's begin with the hardware and core voice loop"**

I will then provide:
- Detailed parts list for the MVP
- Wiring diagram
- Complete firmware code for push-to-talk + Grok API integration
- Backend skeleton
- Testing procedure
- Clear success criteria for Phase 1

---

## Notes for the Builder

This project is designed to be built incrementally in a rural Oklahoma context — respecting intermittent internet, hands-on maker joy, and the desire for a companion that feels like it belongs on a workbench next to tools, fishing gear, and guitar picks.

Everything stays under your control. The knowledge base lives in **your** Google Drive and local systems.

Let's build something real.

---

*EmberForge Companion — Where the digital ember meets the maker's forge.*

**Project anchored at:** https://drive.google.com/drive/folders/1zx81C6WtJgi0lBX9VWcnGYJVXfT1cOme

---

*Last updated: June 16, 2026*  
*Maintained by: Kilynn Weber (with Grok as technical collaborator)*