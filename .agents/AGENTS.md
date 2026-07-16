# NarraVox Studios: Project Guidelines & Executive Summary

This document serves as the project guidelines and context for Antigravity when working on the **Narravox** ecosystem (incorporating **PhoenixDub AI** and **Cine Gen**).

---

## 🎙️ Executive Summary: Projeto Narravox

### 1. Vision & Core Mission
* **Goal**: Democratic accessibility to AI media technology for content creators, modders, and communities without dependence on expensive cloud resources or closed-source giants.
* **Current Phase**: Automated video/game dubbing AI (English to Portuguese, shifting from Chatterbox TTS to Qwen3-TTS in v1.0).
* **Future Phase**: Generative Video AI (automation & creation of original series on YouTube, locally run).
* **Beta Feature**: Integrated AI music & set generation (Vortex Music).

### 2. Technical Edge (Core Strength)
* **Hardware Optimization**: Fully optimized to run locally with high performance on entry-level GPUs (specifically targeting **NVIDIA RTX 3050 6GB VRAM**).
* **Usability**: Eliminating the terminal barrier with a native, visually rich, one-click installer (`setup.exe`) and an elegant premium dashboard interface.

### 3. Financial & Launch Plan
* **Short-Term (Community)**: Focus on crowdfunding (Apoia.se / Polar.sh). Integration of prominent donation buttons in the installer and control panel. Initial monthly target: **R$ 1,500** to ensure full-time development.
* **Medium-Term (Grants)**: Apply for open-source grants (Sequoia Fellowship, Gitcoin, Mozilla Open Source Support) to secure independent developer funding.
* **Long-Term (Seed Funding)**: Target seed investment (R$ 100,000 to R$ 500,000) from open-source-friendly venture funds (e.g., OSS Capital, Bossanova, Canary) via convertible notes/profit sharing (Mútuo Conversível / Dividendos) to maintain absolute voting control.

### 4. Business & Legal Model
* **B2B Strategy**: The software remains free and open-source for the community. Monetization is driven by B2B corporate contracts (R$ 10k to R$ 100k) for real-time support, custom integrations, and consulting.
* **Legal Setup**: CNPJ (LTDA) will only be established *after* funding approval, using the investment capital to pay for accounting setup, preserving the founder's personal savings.
* **Language barrier**: Funding proposals, grants, and international correspondence are drafted in English (assisted by AI translation/subtitles).

---

## 🛠️ Behavioral & Coding Rules for Antigravity

When writing code or assisting the user, Antigravity must strictly adhere to the following rules:

### 1. Hardware Optimization First
* Keep GPU/VRAM efficiency as the highest priority. All scripts, models, and orchestration pipelines must be optimized to run within **6GB of VRAM** (RTX 3050 target).
* Always prompt or guide the user to free VRAM when moving between processing stages (e.g., close LM Studio before initiating Qwen3-TTS).

### 2. User Experience & Aesthetics
* The interface must feel premium, state-of-the-art, and modern.
* Use rich styling (glassmorphism, tailored HSL color palettes, custom gradients, Outfit/Inter typography, and smooth micro-animations). Avoid browser defaults and generic colors.
* Make sure installer links, donation buttons (Apoia.se/Polar.sh) and dashboard shortcuts are prominent, intuitive, and beautifully styled.

### 3. Localization and Translation Support
* Since international fund applications and developer grants are crucial, help the user translate proposals, drafts, and video scripts into English when requested.
* Ensure code documentation maintains both Portuguese and English versions where appropriate.

### 4. Pragmatic Development (Fail Fast & Iterate)
* Focus on completing and testing local features first.
* Embrace the open-source philosophy: the software doesn't need to be perfect before launch. Real-world user feedback and bug reports from the community will drive the v1.0 evolution.

### 5. Modularização por Tokens (Limite de 2.000 Tokens)
* **Regra de 2.000 Tokens**: Qualquer arquivo de código que precise ser modificado ou atualizado deve ser mantido estritamente abaixo do limite de **2.000 tokens** (aproximadamente **500 linhas**).
* **Bypass de Arquivos Existentes**: Se um arquivo existente estiver atualmente abaixo de 2.000 tokens, não precisa mexer. Se estiver acima mas não precisar de modificações na tarefa atual, também não mexa.
* **Refatoração sob Demanda**: Se você precisar atualizar ou modificar um arquivo que excede 2.000 tokens, você deve obrigatoriamente dividir as alterações em módulos de no máximo 2.000 tokens (500 linhas) antes de proceder com a atualização.

### 6. Strict Security & Package Installation Guard (Segurança e Validação)
* **Aprovação Prévia Obrigatória**: Antigravity NUNCA deve baixar ou instalar pacotes, bibliotecas, scripts ou executáveis sem solicitar autorização explícita do usuário primeiro.
* **Validação de Fontes**: Toda e qualquer pesquisa ou download deve priorizar canais oficiais e extremamente confiáveis (ex: Hugging Face oficial, GitHub oficial, PyPI oficial, sites de documentação oficiais).
* **Varredura e Pesquisa de Reputação**: Antes de propor qualquer instalação de ferramenta ou biblioteca menos comum, Antigravity deve obrigatoriamente realizar uma pesquisa na web para verificar o que outros usuários comentam sobre segurança, bugs e confiabilidade daquela ferramenta.
* **Aviso de Riscos**: Caso seja estritamente necessário usar uma fonte menos conhecida ou de terceiros, o usuário deve ser alertado claramente sobre os possíveis riscos de segurança antes de qualquer tomada de decisão.


