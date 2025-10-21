# MyeGPT

An agentic conversation application for researchers to mine the MMRF-CoMMpass dataset, built with LangChain.

Designed towards smartphone browsers, it aims to accelerate hypothesis generation among wet-lab researchers by giving access to clinical cohort data at their fingertips.

<img height="800" width="536" alt="Phone site demonstration screenshot" src="https://github.com/user-attachments/assets/8ecc60f5-4d9d-4f6e-8685-0f9b557500be" />


## Demo

1. Text-based query

https://github.com/user-attachments/assets/288c50f7-5bc7-4172-a06d-d8d0ae4d6dbb

2. Analysis (1) - multi-variable visualizations

https://github.com/user-attachments/assets/7a5aca54-c233-4831-8ace-6de29e6df061

3. Analysis (2) - survival analysis

https://github.com/user-attachments/assets/fa7cb2aa-dbcc-454f-9492-5d4df8242db9


## Project structure

```
myegpt/
├── README.md
├── src/
│   ├── main.py (entry point for python)
│   ├── agent.py (function to query the agent)
│   ├── prompt.py (system prompt)
│   ├── dbdesc.py (database description)
│   ├── eval.py (Langsmith evaluator)
│   └── static/
│       ├── index.html
│       ├── styles.css
│       ├── [favicon files]
│       └── script.js
├── refdata/
│   └── gene_annotation.tsv
├── schema/
│   └── descriptions of flatfile tables
├── Dockerfile
├── requirements.txt
├── create_database.py
└── .gitignore
```

## Acknowledgements
- Multiple Myeloma Research Foundation (MMRF) CoMMpass (Relating Clinical Outcomes in MM to Personal Assessment of Genetic Profile) trial (NCT01454297)
- Patients and family members who contributed to the study
- All members of the Chng Wee Joo lab for their inputs
