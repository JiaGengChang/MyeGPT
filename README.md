# MyeGPT

An agentic conversation application for researchers to mine the MMRF-CoMMpass dataset, built with LangChain.

<img width="875" alt="Desktop site demonstration screenshot" src="https://github.com/user-attachments/assets/92959775-72aa-4aca-a0a2-3ab5051424db" />

Scan the code to access it on mobile browser:

![qrchimpX512](https://github.com/user-attachments/assets/f45a344b-4813-4c57-9664-2e0e8bbb86fe)

## Demo

1. Create a desired figure

https://github.com/user-attachments/assets/7a5aca54-c233-4831-8ace-6de29e6df061



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