# MyeGPT

An agentic conversation application for researchers to mine the MMRF-CoMMpass dataset, built with LangChain.

https://github.com/user-attachments/assets/44b4ea1b-146a-4c48-ae7f-677d3e19ec6a

Scan the code to access it on mobile browser:

![qrchimpX512](https://github.com/user-attachments/assets/f45a344b-4813-4c57-9664-2e0e8bbb86fe)

## Demo

1. Survival analysis based on TP53 mutation status

https://github.com/user-attachments/assets/50ad070b-e316-4a1e-9451-2cf1ab1954ca


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

## Copyright
©2025 Chang Jia Geng. All rights reserved.
Contact for licensing and permission: changjiageng@u.nus.edu
