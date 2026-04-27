# Dashboard Application

<cite>
**Referenced Files in This Document**
- [layout.tsx](file://veritas-ai/frontend/app/layout.tsx)
- [page.tsx (Dashboard)](file://veritas-ai/frontend/app/dashboard/page.tsx)
- [Dashboard.tsx](file://veritas-ai/frontend/components/Dashboard.tsx)
- [TruthGauge.tsx](file://veritas-ai/frontend/components/TruthGauge.tsx)
- [useWebSocket.ts](file://veritas-ai/frontend/hooks/useWebSocket.ts)
- [page.tsx (Developers)](file://veritas-ai/frontend/app/developers/page.tsx)
- [page.tsx (Feedback)](file://veritas-ai/frontend/app/feedback/page.tsx)
- [page.tsx (Timeline)](file://veritas-ai/frontend/app/timeline/page.tsx)
- [Navbar.tsx](file://veritas-ai/frontend/components/Navbar.tsx)
- [api.ts](file://veritas-ai/frontend/services/api.ts)
- [api.ts (types)](file://veritas-ai/frontend/types/api.ts)
- [globals.css](file://veritas-ai/frontend/app/globals.css)
- [next.config.mjs](file://veritas-ai/frontend/next.config.mjs)
- [tailwind.config.ts](file://veritas-ai/frontend/tailwind.config.ts)
- [package.json](file://veritas-ai/frontend/package.json)
</cite>

## Update Summary
**Changes Made**
- Enhanced Dashboard component with new voice-controlled interface featuring central 'voice orb'
- Added state-based animations for listening (cyan pulse), processing (purple pulse), and speaking (pink pulse)
- Integrated real-time status indicators with holographic scan effects
- Improved TruthGauge integration with enhanced visual feedback
- Added neon pulse animations and advanced styling patterns
- Updated component composition strategies to support voice-enabled interactions

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document describes the Next.js dashboard application for the Veritas AI platform. It focuses on the main dashboard interface and specialized pages, covering the global layout and navigation, enhanced voice-controlled interface with central 'voice orb', real-time truth scoring visualization, claim analysis interface, trend monitoring displays, the TruthGauge component, WebSocket integration via a custom hook, and the developers, feedback, and timeline pages. It also documents responsive design patterns, grid layouts, and component composition strategies used across the dashboard ecosystem.

## Project Structure
The dashboard is a Next.js application with a strict file-per-page structure under the app directory, shared components in components/, reusable hooks in hooks/, typed API contracts in types/, and service utilities in services/. Tailwind CSS provides styling and glassmorphism effects, while TypeScript ensures type safety. The enhanced dashboard now features a sophisticated voice-controlled interface with state-based animations and real-time visual feedback.

```mermaid
graph TB
subgraph "App Layer"
L["layout.tsx"]
D["dashboard/page.tsx"]
Dev["developers/page.tsx"]
F["feedback/page.tsx"]
T["timeline/page.tsx"]
end
subgraph "Components"
Nav["Navbar.tsx"]
Dash["Dashboard.tsx"]
TG["TruthGauge.tsx"]
end
subgraph "Hooks"
WS["useWebSocket.ts"]
end
subgraph "Services & Types"
API["services/api.ts"]
Types["types/api.ts"]
end
subgraph "Styling"
CSS["app/globals.css"]
TW["tailwind.config.ts"]
NC["next.config.mjs"]
end
L --> Nav
D --> Dash
Dash --> TG
Dash --> WS
WS --> API
API --> Types
Dev --> API
F --> API
T --> API
L --> CSS
CSS --> TW
NC --> L
```

**Diagram sources**
- [layout.tsx:1-25](file://veritas-ai/frontend/app/layout.tsx#L1-L25)
- [page.tsx (Dashboard):1-17](file://veritas-ai/frontend/app/dashboard/page.tsx#L1-L17)
- [page.tsx (Developers):1-153](file://veritas-ai/frontend/app/developers/page.tsx#L1-L153)
- [page.tsx (Feedback):1-175](file://veritas-ai/frontend/app/feedback/page.tsx#L1-L175)
- [page.tsx (Timeline):1-128](file://veritas-ai/frontend/app/timeline/page.tsx#L1-L128)
- [Navbar.tsx:1-52](file://veritas-ai/frontend/components/Navbar.tsx#L1-L52)
- [Dashboard.tsx:1-393](file://veritas-ai/frontend/components/Dashboard.tsx#L1-L393)
- [TruthGauge.tsx:1-52](file://veritas-ai/frontend/components/TruthGauge.tsx#L1-L52)
- [useWebSocket.ts:1-143](file://veritas-ai/frontend/hooks/useWebSocket.ts#L1-L143)
- [api.ts:1-32](file://veritas-ai/frontend/services/api.ts#L1-L32)
- [api.ts (types):1-66](file://veritas-ai/frontend/types/api.ts#L1-L66)
- [globals.css:1-219](file://veritas-ai/frontend/app/globals.css#L1-L219)
- [tailwind.config.ts:1-24](file://veritas-ai/frontend/tailwind.config.ts#L1-L24)
- [next.config.mjs:1-8](file://veritas-ai/frontend/next.config.mjs#L1-L8)

**Section sources**
- [layout.tsx:1-25](file://veritas-ai/frontend/app/layout.tsx#L1-L25)
- [globals.css:1-219](file://veritas-ai/frontend/app/globals.css#L1-L219)
- [tailwind.config.ts:1-24](file://veritas-ai/frontend/tailwind.config.ts#L1-L24)
- [next.config.mjs:1-8](file://veritas-ai/frontend/next.config.mjs#L1-L8)
- [package.json:1-27](file://veritas-ai/frontend/package.json#L1-L27)

## Core Components
- Global Layout and Navigation: The root layout defines the HTML shell, global CSS, and embeds the fixed navbar. The navbar provides navigation across dashboard, timeline, feedback, and developers pages.
- Enhanced Dashboard Page: Renders the main interactive interface for claim analysis with voice input, central 'voice orb' with state-based animations, real-time progress, alerts, and truth visualization.
- TruthGauge: A reusable SVG-based gauge that visualizes truth scores with color-coded confidence thresholds and enhanced visual feedback.
- WebSocket Hook: Provides real-time streaming via WebSocket, managing connection lifecycle, reconnection, and state for progress, alerts, and results.
- Specialized Pages: Developers page for API reference and pricing, Feedback page for user insights, Timeline page for historical analysis.

**Section sources**
- [layout.tsx:1-25](file://veritas-ai/frontend/app/layout.tsx#L1-L25)
- [Navbar.tsx:1-52](file://veritas-ai/frontend/components/Navbar.tsx#L1-L52)
- [page.tsx (Dashboard):1-17](file://veritas-ai/frontend/app/dashboard/page.tsx#L1-L17)
- [Dashboard.tsx:1-393](file://veritas-ai/frontend/components/Dashboard.tsx#L1-L393)
- [TruthGauge.tsx:1-52](file://veritas-ai/frontend/components/TruthGauge.tsx#L1-L52)
- [useWebSocket.ts:1-143](file://veritas-ai/frontend/hooks/useWebSocket.ts#L1-L143)
- [page.tsx (Developers):1-153](file://veritas-ai/frontend/app/developers/page.tsx#L1-L153)
- [page.tsx (Feedback):1-175](file://veritas-ai/frontend/app/feedback/page.tsx#L1-L175)
- [page.tsx (Timeline):1-128](file://veritas-ai/frontend/app/timeline/page.tsx#L1-L128)

## Architecture Overview
The dashboard follows a layered architecture with enhanced voice control capabilities:
- Presentation Layer: Next.js app directory pages and shared components with sophisticated visual feedback.
- Domain Layer: Dashboard logic orchestrates WebSocket messages, speech recognition, voice synthesis, and the central voice orb interface.
- Integration Layer: Services encapsulate API base URLs and helpers; types define contracts for WebSocket and HTTP payloads.
- Infrastructure: Tailwind CSS for styling, Next.js runtime, and browser APIs (WebSocket, SpeechRecognition, SpeechSynthesis).

```mermaid
graph TB
Browser["Browser"]
Next["Next.js App Router"]
Layout["Root Layout (layout.tsx)"]
Navbar["Navbar.tsx"]
DashboardPage["dashboard/page.tsx"]
DashboardComp["Dashboard.tsx"]
TruthGaugeComp["TruthGauge.tsx"]
WSHook["useWebSocket.ts"]
APIService["services/api.ts"]
TypesAPI["types/api.ts"]
Browser --> Next
Next --> Layout
Layout --> Navbar
Next --> DashboardPage
DashboardPage --> DashboardComp
DashboardComp --> TruthGaugeComp
DashboardComp --> WSHook
WSHook --> APIService
APIService --> TypesAPI
```

**Diagram sources**
- [layout.tsx:1-25](file://veritas-ai/frontend/app/layout.tsx#L1-L25)
- [Navbar.tsx:1-52](file://veritas-ai/frontend/components/Navbar.tsx#L1-L52)
- [page.tsx (Dashboard):1-17](file://veritas-ai/frontend/app/dashboard/page.tsx#L1-L17)
- [Dashboard.tsx:1-393](file://veritas-ai/frontend/components/Dashboard.tsx#L1-L393)
- [TruthGauge.tsx:1-52](file://veritas-ai/frontend/components/TruthGauge.tsx#L1-L52)
- [useWebSocket.ts:1-143](file://veritas-ai/frontend/hooks/useWebSocket.ts#L1-L143)
- [api.ts:1-32](file://veritas-ai/frontend/services/api.ts#L1-L32)
- [api.ts (types):1-66](file://veritas-ai/frontend/types/api.ts#L1-L66)

## Detailed Component Analysis

### Layout and Navigation
- Root layout sets metadata, global CSS, and renders the Navbar and page content inside a grid-pattern background.
- Navbar provides a fixed top bar with links to Home, Intelligence (dashboard), Timeline, Feedback, and API (developers), highlighting the active route.

```mermaid
sequenceDiagram
participant U as "User"
participant N as "Navbar.tsx"
participant R as "Next Router"
participant P as "Target Page"
U->>N : Click navigation link
N->>R : navigate(href)
R-->>P : Render target page
P-->>U : Display page content
```

**Diagram sources**
- [layout.tsx:1-25](file://veritas-ai/frontend/app/layout.tsx#L1-L25)
- [Navbar.tsx:1-52](file://veritas-ai/frontend/components/Navbar.tsx#L1-L52)

**Section sources**
- [layout.tsx:1-25](file://veritas-ai/frontend/app/layout.tsx#L1-L25)
- [Navbar.tsx:1-52](file://veritas-ai/frontend/components/Navbar.tsx#L1-L52)

### Enhanced Dashboard Page and Voice-Controlled Interface
- The dashboard page wraps the Dashboard component with a centered container and a title area.
- Enhanced Dashboard orchestrates:
  - Central 'voice orb' with state-based animations (listening/pulsing cyan, processing/purple, speaking/pink)
  - Voice input via Web Speech Recognition (continuous, interim results).
  - Manual text input with Enter-to-execute.
  - Real-time progress bar and stage indicators driven by WebSocket messages.
  - Alerts display for anomalies.
  - Truth visualization using TruthGauge and confidence breakdown cards.
  - Summary rendering and "Why True/False" explanations with voice synthesis.

```mermaid
sequenceDiagram
participant U as "User"
participant D as "Dashboard.tsx"
participant H as "useWebSocket.ts"
participant S as "WebSocket Server"
participant G as "TruthGauge.tsx"
U->>D : Speak or click voice orb
D->>H : sendQuery(query)
H->>S : WebSocket send {query}
S-->>H : progress/status messages
H-->>D : streamData/alerts/progress/stage
D->>G : render TruthGauge(score)
D-->>U : Live UI updates, alerts, summary
```

**Diagram sources**
- [page.tsx (Dashboard):1-17](file://veritas-ai/frontend/app/dashboard/page.tsx#L1-L17)
- [Dashboard.tsx:1-393](file://veritas-ai/frontend/components/Dashboard.tsx#L1-L393)
- [useWebSocket.ts:1-143](file://veritas-ai/frontend/hooks/useWebSocket.ts#L1-L143)
- [TruthGauge.tsx:1-52](file://veritas-ai/frontend/components/TruthGauge.tsx#L1-L52)

**Section sources**
- [page.tsx (Dashboard):1-17](file://veritas-ai/frontend/app/dashboard/page.tsx#L1-L17)
- [Dashboard.tsx:1-393](file://veritas-ai/frontend/components/Dashboard.tsx#L1-L393)

### Voice Orb Interface
- The central voice orb serves as the primary interface for voice-controlled interactions.
- State-based animations:
  - Listening state: Cyan pulse animation with pulsing glow effect
  - Processing state: Purple pulse animation with orbital motion
  - Speaking state: Pink pulse animation with rapid pulse cycle
  - Idle state: Subtle gray border with hover effects
- Inner ring animation creates a ping effect during processing states.
- Icon changes based on state: Mic/MicOff for listening, Brain for processing, Volume for speaking.

```mermaid
flowchart TD
Start(["Voice Orb State Detection"]) --> CheckListening{"isListening?"}
CheckListening --> |Yes| CheckSpeaking{"isSpeaking?"}
CheckListening --> |No| CheckProcessing{"isProcessing?"}
CheckSpeaking --> |Yes| SetSpeaking["Set speaking state<br/>Pink glow + volume icon"]
CheckSpeaking --> |No| SetIdle["Set idle state<br/>Gray border + hover"]
CheckProcessing --> |Yes| SetProcessing["Set processing state<br/>Purple glow + brain icon"]
CheckProcessing --> |No| SetIdle
SetSpeaking --> Render["Apply styles and animations"]
SetProcessing --> Render
SetIdle --> Render
```

**Diagram sources**
- [Dashboard.tsx:127-154](file://veritas-ai/frontend/components/Dashboard.tsx#L127-L154)

**Section sources**
- [Dashboard.tsx:127-194](file://veritas-ai/frontend/components/Dashboard.tsx#L127-L194)

### Enhanced TruthGauge Component
- Renders a circular SVG gauge representing the truth score percentage with enhanced visual feedback.
- Color transitions based on thresholds:
  - Green for high confidence (cyan glow).
  - Purple for moderate confidence (purple glow).
  - Red for low confidence (pink glow).
- Uses animated stroke dashoffset to visualize progress with enhanced drop shadows for glowing effects.
- Integrated with voice orb state for synchronized visual feedback.

```mermaid
flowchart TD
Start(["Enhanced TruthGauge"]) --> GetScore["Read score prop"]
GetScore --> CalcPercent["Compute percentage"]
CalcPercent --> Thresholds{"Threshold check"}
Thresholds --> |>= 75%| Green["Set cyan color<br/>and cyan glow"]
Thresholds --> |>= 40%| Purple["Set purple color<br/>and purple glow"]
Thresholds --> |< 40%| Red["Set pink color<br/>and pink glow"]
Green --> Draw["Draw SVG circle with enhanced strokeDashoffset"]
Purple --> Draw
Red --> Draw
Draw --> End(["Display percentage with neon glow"])
```

**Diagram sources**
- [TruthGauge.tsx:1-52](file://veritas-ai/frontend/components/TruthGauge.tsx#L1-L52)

**Section sources**
- [TruthGauge.tsx:1-52](file://veritas-ai/frontend/components/TruthGauge.tsx#L1-L52)

### WebSocket Integration via useWebSocket Hook
- Establishes and manages a WebSocket connection to the backend streaming endpoint.
- Handles:
  - Connection open/close/reconnect with exponential backoff.
  - Parsing incoming messages and routing to appropriate state:
    - Processing stages and progress.
    - Complete results.
    - Alerts.
    - Errors.
  - Sending queries and resetting state before transmission.
- Exposes streamData, alerts, activeStatus, error, progress, currentStage, and sendQuery to consumers.

```mermaid
sequenceDiagram
participant C as "Caller (Dashboard)"
participant H as "useWebSocket.ts"
participant W as "WebSocket"
participant B as "Backend"
C->>H : connect()
H->>W : new WebSocket(url)
W-->>H : onopen
H-->>C : setActiveStatus("idle")
C->>H : sendQuery(query)
H->>W : send({query})
loop Streaming
B-->>H : {"status" : "processing"|...}
H-->>C : update progress/stage/alerts
end
B-->>H : {"status" : "complete", "data" : payload}
H-->>C : append streamData, set complete
W-->>H : onclose
H-->>C : schedule reconnect
```

**Diagram sources**
- [useWebSocket.ts:1-143](file://veritas-ai/frontend/hooks/useWebSocket.ts#L1-L143)
- [api.ts:1-32](file://veritas-ai/frontend/services/api.ts#L1-L32)
- [api.ts (types):56-66](file://veritas-ai/frontend/types/api.ts#L56-L66)

**Section sources**
- [useWebSocket.ts:1-143](file://veritas-ai/frontend/hooks/useWebSocket.ts#L1-L143)
- [api.ts:1-32](file://veritas-ai/frontend/services/api.ts#L1-L32)
- [api.ts (types):56-66](file://veritas-ai/frontend/types/api.ts#L56-L66)

### Developers Page (API Integration)
- Presents API endpoints, authentication requirements, and example payloads.
- Includes a pricing tiers section and a quick start curl example.
- Uses API base URL from services/api.ts.

```mermaid
flowchart TD
Open["Open Developers Page"] --> ViewEndpoints["View endpoints list"]
ViewEndpoints --> CopyKey["Copy API key"]
CopyKey --> TryEndpoint["Try endpoint with curl or client"]
TryEndpoint --> Integrate["Integrate into application"]
```

**Diagram sources**
- [page.tsx (Developers):1-153](file://veritas-ai/frontend/app/developers/page.tsx#L1-L153)
- [api.ts:18-19](file://veritas-ai/frontend/services/api.ts#L18-L19)

**Section sources**
- [page.tsx (Developers):1-153](file://veritas-ai/frontend/app/developers/page.tsx#L1-L153)
- [api.ts:1-32](file://veritas-ai/frontend/services/api.ts#L1-L32)

### Feedback Page (User Insights)
- Collects user feedback on verification results with original query, original score, user flag, optional corrected score, and comments.
- Submits to the backend feedback endpoint and shows a success state.

```mermaid
flowchart TD
Start(["Open Feedback Page"]) --> Fill["Fill form fields"]
Fill --> Submit["Click Submit"]
Submit --> Post["POST /feedback"]
Post --> Ok{"HTTP 2xx?"}
Ok --> |Yes| Success["Show Thank You screen"]
Ok --> |No| Error["Show error message"]
```

**Diagram sources**
- [page.tsx (Feedback):1-175](file://veritas-ai/frontend/app/feedback/page.tsx#L1-L175)
- [api.ts:18-19](file://veritas-ai/frontend/services/api.ts#L18-L19)

**Section sources**
- [page.tsx (Feedback):1-175](file://veritas-ai/frontend/app/feedback/page.tsx#L1-L175)
- [api.ts:1-32](file://veritas-ai/frontend/services/api.ts#L1-L32)

### Timeline Page (Historical Analysis)
- Loads historical verification entries from the backend and displays them in a vertical timeline.
- Supports filtering by query text and expanding entries to show summaries.
- Uses status-specific styling and percent formatting.

```mermaid
sequenceDiagram
participant U as "User"
participant T as "Timeline.tsx"
participant API as "Backend"
U->>T : Open Timeline
T->>API : GET /history?limit=50
API-->>T : {items : [...]}
T-->>U : Render timeline entries
U->>T : Filter/Search
T-->>U : Update filtered list
U->>T : Expand item
T-->>U : Show expanded summary
```

**Diagram sources**
- [page.tsx (Timeline):1-128](file://veritas-ai/frontend/app/timeline/page.tsx#L1-L128)
- [api.ts:18-19](file://veritas-ai/frontend/services/api.ts#L18-L19)
- [api.ts (types):42-54](file://veritas-ai/frontend/types/api.ts#L42-L54)

**Section sources**
- [page.tsx (Timeline):1-128](file://veritas-ai/frontend/app/timeline/page.tsx#L1-L128)
- [api.ts:1-32](file://veritas-ai/frontend/services/api.ts#L1-L32)
- [api.ts (types):42-54](file://veritas-ai/frontend/types/api.ts#L42-L54)

## Dependency Analysis
- Component Coupling:
  - Dashboard depends on TruthGauge, useWebSocket, and browser speech APIs.
  - useWebSocket depends on services/api.ts for WebSocket URL and types/api.ts for message contracts.
  - Pages depend on services/api.ts for API base URL and types for typing.
- Styling Cohesion:
  - globals.css centralizes theme tokens, glassmorphism, gradients, ambient glows, grid pattern, and animations including new voice orb effects.
  - tailwind.config.ts extends color palette aligned with the theme.
- Build and Runtime:
  - next.config.mjs configures standalone output and disables strict mode.
  - package.json lists Next.js, React, Tailwind, Lucide icons, and Recharts.

```mermaid
graph LR
Dashboard["Dashboard.tsx"] --> TruthGauge["TruthGauge.tsx"]
Dashboard --> WS["useWebSocket.ts"]
WS --> API["services/api.ts"]
API --> Types["types/api.ts"]
Layout["layout.tsx"] --> Navbar["Navbar.tsx"]
Dev["developers/page.tsx"] --> API
Feed["feedback/page.tsx"] --> API
Time["timeline/page.tsx"] --> API
Layout --> CSS["app/globals.css"]
CSS --> TW["tailwind.config.ts"]
NextCfg["next.config.mjs"] --> Layout
Pkg["package.json"] --> NextCfg
```

**Diagram sources**
- [Dashboard.tsx:1-393](file://veritas-ai/frontend/components/Dashboard.tsx#L1-L393)
- [TruthGauge.tsx:1-52](file://veritas-ai/frontend/components/TruthGauge.tsx#L1-L52)
- [useWebSocket.ts:1-143](file://veritas-ai/frontend/hooks/useWebSocket.ts#L1-L143)
- [api.ts:1-32](file://veritas-ai/frontend/services/api.ts#L1-L32)
- [api.ts (types):1-66](file://veritas-ai/frontend/types/api.ts#L1-L66)
- [layout.tsx:1-25](file://veritas-ai/frontend/app/layout.tsx#L1-L25)
- [Navbar.tsx:1-52](file://veritas-ai/frontend/components/Navbar.tsx#L1-L52)
- [page.tsx (Developers):1-153](file://veritas-ai/frontend/app/developers/page.tsx#L1-L153)
- [page.tsx (Feedback):1-175](file://veritas-ai/frontend/app/feedback/page.tsx#L1-L175)
- [page.tsx (Timeline):1-128](file://veritas-ai/frontend/app/timeline/page.tsx#L1-L128)
- [globals.css:1-219](file://veritas-ai/frontend/app/globals.css#L1-L219)
- [tailwind.config.ts:1-24](file://veritas-ai/frontend/tailwind.config.ts#L1-L24)
- [next.config.mjs:1-8](file://veritas-ai/frontend/next.config.mjs#L1-L8)
- [package.json:1-27](file://veritas-ai/frontend/package.json#L1-L27)

**Section sources**
- [Dashboard.tsx:1-393](file://veritas-ai/frontend/components/Dashboard.tsx#L1-L393)
- [useWebSocket.ts:1-143](file://veritas-ai/frontend/hooks/useWebSocket.ts#L1-L143)
- [api.ts:1-32](file://veritas-ai/frontend/services/api.ts#L1-L32)
- [api.ts (types):1-66](file://veritas-ai/frontend/types/api.ts#L1-L66)
- [globals.css:1-219](file://veritas-ai/frontend/app/globals.css#L1-L219)
- [tailwind.config.ts:1-24](file://veritas-ai/frontend/tailwind.config.ts#L1-L24)
- [next.config.mjs:1-8](file://veritas-ai/frontend/next.config.mjs#L1-L8)
- [package.json:1-27](file://veritas-ai/frontend/package.json#L1-L27)

## Performance Considerations
- WebSocket Efficiency:
  - Reconnection with exponential backoff prevents resource thrashing on transient failures.
  - Resetting state before sending queries avoids stale UI updates.
- Rendering Optimizations:
  - TruthGauge uses SVG and minimal DOM updates; consider memoizing props if reused frequently.
  - Dashboard batches UI updates from WebSocket messages; avoid unnecessary re-renders by keeping payloads normalized.
  - Voice orb animations use CSS keyframes for optimal performance.
- Network Resilience:
  - API base URL normalization and protocol detection ensure compatibility across environments.
- Styling:
  - Glassmorphism and backdrop filters are visually intensive; ensure GPU acceleration is available and avoid excessive blur on lower-end devices.
  - New animations use hardware-accelerated properties (transform, opacity) for smooth performance.

## Troubleshooting Guide
- WebSocket Not Connecting:
  - Verify WS_BASE_URL resolves to the correct backend address and scheme (ws/wss).
  - Check for CORS and reverse proxy configuration on the backend.
- No Real-Time Updates:
  - Confirm the backend emits processing, complete, and alert messages with correct status fields.
  - Inspect browser console for JSON parse errors or onclose/onerror events.
- Voice Recognition Issues:
  - Ensure SpeechRecognition is available and enabled; handle fallbacks gracefully.
  - Check microphone permissions and device availability.
  - Voice orb may not animate if speech recognition fails to initialize.
- Voice Synthesis Problems:
  - Verify SpeechSynthesis API availability in the browser.
  - Check audio permissions and device availability.
- Timeline Loading Errors:
  - Validate /history endpoint availability and response shape match HistoryResponse.
- Styling Glitches:
  - Confirm Tailwind content paths include components and app directories.
  - Ensure globals.css is imported in layout.tsx and theme colors align with tailwind.config.ts.
- Animation Issues:
  - Verify CSS keyframes for orb-pulse, neon-pulse, and fadeUp animations are properly defined.
  - Check that animation-duration and timing-function values are compatible with hardware acceleration.

**Section sources**
- [useWebSocket.ts:1-143](file://veritas-ai/frontend/hooks/useWebSocket.ts#L1-L143)
- [api.ts:1-32](file://veritas-ai/frontend/services/api.ts#L1-L32)
- [page.tsx (Timeline):1-128](file://veritas-ai/frontend/app/timeline/page.tsx#L1-L128)
- [globals.css:1-219](file://veritas-ai/frontend/app/globals.css#L1-L219)
- [tailwind.config.ts:1-24](file://veritas-ai/frontend/tailwind.config.ts#L1-L24)

## Conclusion
The dashboard integrates a modern, responsive UI with enhanced voice-controlled interactions, real-time streaming, sophisticated visual feedback through the central voice orb, and comprehensive truth visualization. The modular component architecture, centralized services, and robust WebSocket handling enable scalable development and maintenance. The new voice orb interface provides intuitive control with state-based animations and real-time status indicators. Specialized pages for developers, feedback, and timeline complement the core dashboard, delivering a complete analytical and integrative platform with advanced voice interaction capabilities.

## Appendices

### Responsive Design Patterns and Grid Layouts
- Container Utilities:
  - Centered containers with max-width and horizontal padding for readability.
  - Grid layouts adapt from single-column on small screens to multi-column on larger screens (e.g., confidence breakdown cards).
- Typography and Spacing:
  - Consistent use of font weights and spacing tokens for visual hierarchy.
- Interactive Elements:
  - Hover and active states with subtle transitions and glow effects.
- Animations:
  - Fade-in and slide-in animations for content appearance.
  - Hardware-accelerated animations for smooth voice orb interactions.

**Section sources**
- [Dashboard.tsx:228-393](file://veritas-ai/frontend/components/Dashboard.tsx#L228-L393)
- [page.tsx (Developers):113-135](file://veritas-ai/frontend/app/developers/page.tsx#L113-L135)
- [page.tsx (Timeline):77-124](file://veritas-ai/frontend/app/timeline/page.tsx#L77-L124)
- [globals.css:1-219](file://veritas-ai/frontend/app/globals.css#L1-L219)

### Component Composition Strategies
- Orchestration:
  - Dashboard composes TruthGauge, useWebSocket, browser APIs, and voice orb for a cohesive experience.
- Reusability:
  - TruthGauge is self-contained and reusable across pages.
- Type Safety:
  - Strongly typed WebSocketMessage and QueryResponse reduce runtime errors.
- Styling Consistency:
  - Shared CSS utilities (glass, gradient-text, ambient-glow) unify the look and feel.
- Voice Integration:
  - Central voice orb coordinates with WebSocket state and TruthGauge visualization.
  - State-based animations provide immediate visual feedback for user actions.

**Section sources**
- [Dashboard.tsx:1-393](file://veritas-ai/frontend/components/Dashboard.tsx#L1-L393)
- [TruthGauge.tsx:1-52](file://veritas-ai/frontend/components/TruthGauge.tsx#L1-L52)
- [api.ts (types):56-66](file://veritas-ai/frontend/types/api.ts#L56-L66)
- [globals.css:20-34](file://veritas-ai/frontend/app/globals.css#L20-L34)

### Voice Control Features
- Speech Recognition:
  - Continuous speech recognition with interim results for real-time transcription.
  - Automatic query submission when speech recognition ends.
- Voice Synthesis:
  - Text-to-speech synthesis for vocalized output with voice selection.
  - Automatic cancellation of previous speech when new content arrives.
- Visual Feedback:
  - Voice orb state changes reflect current voice activity.
  - Real-time progress indicators during processing stages.
- Accessibility:
  - Keyboard navigation support for manual text input.
  - Screen reader friendly status indicators and progress bars.

**Section sources**
- [Dashboard.tsx:34-122](file://veritas-ai/frontend/components/Dashboard.tsx#L34-L122)
- [globals.css:102-132](file://veritas-ai/frontend/app/globals.css#L102-L132)