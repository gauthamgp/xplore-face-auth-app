# Face Auth App — Flow Diagrams

Use these in presentations or paste the Mermaid code into [mermaid.live](https://mermaid.live) to export as PNG/SVG.

---

## 1. End-to-End Flow (Detailed)

```mermaid
flowchart TB
    subgraph User["User actions"]
        A[Open app] --> B[Select user e.g. Alice]
        B --> C[Sign in]
        C --> D[See dashboard]
        D --> E[Click Verify yourself]
        E --> F[Allow camera]
        F --> G[Capture photo]
        G --> H[Submit for verification]
    end

    subgraph Browser["Browser"]
        C --> B1[POST /login]
        B1 --> D
        H --> B2[POST /verify with image]
        B2 --> B3[Show result toast]
    end

    subgraph Server["Server"]
        B1 --> S1[Set session: username]
        B2 --> S2[Read session]
        S2 --> S3[Get user folder]
        S3 --> S4[Save image to temp file]
        S4 --> S5[Call face verification]
        S5 --> S6[Return JSON success/fail]
    end

    subgraph Verification["Face verification"]
        S5 --> V1[Load reference images]
        V1 --> V2[For each reference]
        V2 --> V3[Detect face in live image]
        V3 --> V4[Detect face in reference]
        V4 --> V5[Align + encode to embedding]
        V5 --> V6[Compare distance]
        V6 --> V7{Match?}
        V7 -->|Yes| V8[Verified]
        V7 -->|No| V2
        V8 --> S6
    end

    S6 --> B3
```

---

## 2. Face Verification Pipeline (What happens inside “verify”)

```mermaid
flowchart LR
    A[Live image] --> B[Face detector]
    C[Reference image] --> D[Face detector]
    B --> E[Align face]
    D --> E
    E --> F[Neural network]
    F --> G[Embedding vector]
    G --> H[Distance]
    H --> I{Below threshold?}
    I -->|Yes| J[Same person]
    I -->|No| K[Different person]
```

---

## 3. Simplified One-Page Flow (For slides)

```mermaid
flowchart TB
    Start([User opens app]) --> Login[Choose user & Sign in]
    Login --> Dashboard[Dashboard: form + Verify button]
    Dashboard --> Camera[Click Verify → Camera on]
    Camera --> Capture[Capture → Submit]
    Capture --> Send[Send image to server]
    Send --> Check{Session valid?}
    Check -->|No| Reject1[401 Not logged in]
    Check -->|Yes| Compare[Compare face to user folder]
    Compare --> Face{Face match?}
    Face -->|Yes| Success[Welcome message]
    Face -->|No| Reject2[User invalid]
    Success --> Done([User can submit form])
    Reject1 --> Done
    Reject2 --> Done
```

---

## 4. Data Flow (What data goes where)

```mermaid
flowchart LR
    subgraph Client
        Cam[Camera] --> Img[Image bytes]
        Img --> B64[Base64 in JSON]
        B64 --> POST[POST /verify]
    end

    subgraph Server
        POST --> Session[Read session]
        Session --> Folder[users/username/]
        POST --> Temp[Temp file]
        Temp --> DeepFace[DeepFace.verify]
        Folder --> Refs[Reference images]
        Refs --> DeepFace
        DeepFace --> Result[JSON response]
    end

    Result --> Client
```

---

## How to use

- **GitHub/GitLab:** These Mermaid blocks render automatically in `.md` files.
- **Export image:** Copy a code block → paste at [mermaid.live](https://mermaid.live) → export PNG/SVG.
- **Presentations:** Use the “Simplified one-page flow” for a single slide; use “End-to-End” for a detailed walkthrough.
