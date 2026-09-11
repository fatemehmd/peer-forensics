# Prior work on LLM peer influence (5-min scan) and how this project differs

- **Do as We Do, Not as You Think (ICLR 2025, arXiv 2501.13381)** – Asch-style: 1 subject agent + 6 peers giving a wrong answer; conformity rises with majority size, drops with a dissenter. *Opinions/answers, not actions.*
- **Conformity in LLMs (arXiv 2410.12428)** and **LLMs Exhibit Normative Conformity (arXiv 2604.19301)** – same family; normative vs informational conformity.
- **Most LLM Conformity Needs No Speaker (arXiv 2607.05545)** – key methodological warning: much "conformity" is explained by the *information* in the peer messages, not the *peer* framing. → Our `solo_info` vs `peers_doing` contrast is exactly this control (same technical info, no peers).
- **Persuading LLMs to comply with objectionable requests (PNAS 2026)** – social proof and authority cues raise compliance with harmful requests, single-turn chat.
- **Obedience to unsafe clinical instructions (Milgram-style)** – responsibility transfer and conformity cues raise unsafe compliance.
- **Model Forensics (Singh, Kroiz, Rajamanoharan, Nanda 2026)** – R1's deception depended on the tampering message coming from *a previous instance of itself*: source identity of a message matters causally.

**Gap this project fills:** all of the above measure stated answers or single-turn compliance. Nobody has tested whether peer messages causally shift an *agent's rule-breaking actions* in a tool-using loop, or whether peers suppress *reporting to humans* (bystander effect). Those are the two things the METR report describes and could not explain.
