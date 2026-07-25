# 🎬 OpenDailies
**The Open-Source Review Tool for Animators & VFX Artists**

OpenDailies is a lightweight, high-performance video review and annotation tool tailored specifically for animation and VFX workflows. My goal is to bridge the gap between expensive studio software (like RV or Shotgrid) and clunky desktop players (like VLC). 

[![Download Latest Release](https://img.shields.io/badge/Download-Latest_Release-blue)](https://github.com/pkgamelog/OpenDailies/releases)
[![Join Discord](https://img.shields.io/badge/Discord-Join_Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/BtKkfyuQN)

---

### 🤖 A Quick Disclaimer (Transparency & AI)
Just to be fully transparent: **I am an animator, not a professional software engineer.** I have been building OpenDailies with the heavy assistance of AI (like ChatGPT/Claude) to bring the tools I've always wanted into reality. 

Because of this, the underlying codebase might not follow perfect enterprise-level software architecture, and you might find some quirky bugs! However, the app is built with a focus on real-world animation workflows, and it works. I’m learning as I go, and I welcome anyone who wants to contribute, optimize, or help clean up the code on GitHub!

---

### ✅ CURRENTLY IMPLEMENTED (What you can use today)

**🎨 Annotation & Drawing**
* **Photoshop-style Pixel Eraser:** Pressure-sensitive opacity, partial stroke erasing, and a live hollow-cursor that scales with brush size.
* **Per-Tool Brush Memory:** Your pen remembers it’s 3px, and your eraser remembers it’s 20px.
* **Interactive Brush Resizing:** Hold `F` and drag left/right to visually scale your brush (Maya style).

**🎥 Playback & Timeline**
* **Maya-Style Timeline:** Auto-fits to the window, dynamic zoom, double-click to reset. Includes trim handles, annotation keyframes, and bookmark markers.
* **A/B Compare:** Load two takes side-by-side with synced playback.
* **Fully Customizable Shortcuts:** A dedicated UI to remap any tool or playback action.

**🔄 Pipeline Integration (The Tier-S Feature)**
* **Live Link (Maya Playblast):** Leave OpenDailies open on your second monitor. When you playblast from Maya, OpenDailies instantly auto-reloads the video while preserving your exact frame, timeline zoom, and annotations.
* **Before/After Slider:** When a Live Link playblast updates, a wipe slider appears. Drag left to see the old animation, drag right to see the new one.

---

### 📋 DRAFT ROADMAP (Future Priorities)

*Feedback from the community will shape this list! Join our Discord to vote.*

🔴 **HIGH PRIORITY (Core Animation Needs)**
* **Maya-Style "Play Every Frame" Toggle:** Slows down playback to decode every single frame perfectly, rather than dropping frames to maintain real-time.
* **Real-Time Audio Scrubbing:** Play 2-3 frames of audio when dragging the timeline slider to pinpoint exact dialogue beats for lip-sync.
* **Frame-Accurate Audio Sync:** Lock audio strictly to the video frame index to prevent drift.
* **Audio Offset Delay:** A frame-offset spinner to nudge externally recorded scratch audio tracks forwards or backwards.

🟡 **MEDIUM PRIORITY (Performance & Visual Feedback)**
* **RAM/Disk Cache System:** A background thread that pre-decodes upcoming video frames into RAM for buttery-smooth playback of heavy files.
* **Waveform Timeline Overlay:** Extract the audio waveform via FFmpeg and render it behind the timeline slider.
* **Fixed Frame-Rate Clamp:** Force the engine to strictly adhere to project FPS.

🔵 **LOW PRIORITY (Workflow Quality-of-Life)**
* **Multi-Track Audio:** Allow importing a dialogue track and temp music track simultaneously.
* **Audio Peak Markers:** Auto-detect sharp volume spikes (clapperboards) and drop colored bookmarks.
* **Mute/Solo Audio Toggles:** Quick transport buttons to mute audio while scrubbing.

---

### 💬 Community & Support
Join the OpenDailies Discord server to ask questions, suggest features, report bugs, or share your animation workflows!
👉 **[Join the Discord](https://discord.gg/BtKkfyuQN)**
```
