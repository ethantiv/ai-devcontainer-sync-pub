---
name: read-arxiv-paper
description: >
  This skill should be used when the user asks to "read an arxiv paper",
  "summarize an arxiv paper", "analyze a paper from arxiv", "explain an arxiv paper",
  "review an arxiv paper", "fetch arxiv source", "download arxiv paper",
  provides an arxiv URL (arxiv.org/abs/... or arxiv.org/pdf/...), or mentions
  reading, summarizing, reviewing, or analyzing academic papers from arxiv.
---

# Read arXiv Paper

Download an arXiv paper's LaTeX source, read and analyze it, and produce a project-contextualized summary in a local `./arxiv/knowledge/` directory.

## Workflow

### Step 1: Normalize the URL

Extract the arXiv ID from the provided URL. Supported input formats:
- `https://arxiv.org/abs/2601.07372`
- `https://www.arxiv.org/abs/2601.07372`
- `https://arxiv.org/pdf/2601.07372`
- Just the ID: `2601.07372`

Construct the **TeX source** URL (not the PDF):

```
https://arxiv.org/src/{arxiv_id}
```

### Step 2: Download the Paper Source

Download the source archive to `./arxiv/{arxiv_id}.tar.gz` in the project root.

```bash
mkdir -p ./arxiv
curl -L -o ./arxiv/{arxiv_id}.tar.gz https://arxiv.org/src/{arxiv_id}
```

Skip download if the file already exists.

### Step 3: Unpack the Archive

Extract contents into `./arxiv/{arxiv_id}/`:

```bash
mkdir -p ./arxiv/{arxiv_id}
tar -xzf ./arxiv/{arxiv_id}.tar.gz -C ./arxiv/{arxiv_id}
```

Handle edge cases:
- Some papers have a single `.tex` file (not a tarball) — detect by checking file type with `file` command and rename accordingly.
- Some archives unpack into a subdirectory — check and adjust paths.

### Step 4: Locate the Entrypoint

Find the main LaTeX file. Search strategy:
1. Look for `main.tex`, `paper.tex`, or `ms.tex`
2. If not found, search for `.tex` files containing `\documentclass`
3. If multiple candidates, pick the one with `\begin{document}`

```bash
grep -rl '\\documentclass' ./arxiv/{arxiv_id}/ --include='*.tex'
```

### Step 5: Read the Paper

Starting from the entrypoint:
1. Read the main `.tex` file
2. Follow `\input{...}` and `\include{...}` directives to read referenced source files
3. Read `.bbl` or `.bib` files for references if present
4. Skip binary files (images, compiled outputs)

Focus on extracting: title, authors, abstract, all sections, key equations, algorithms, and conclusions.

### Step 6: Produce a Summary

Generate a markdown summary at `./arxiv/knowledge/summary_{tag}.md` in the **current project directory** (not in `~/.cache`).

#### Tag Generation

Derive a short, descriptive `tag` from the paper's core topic (e.g., `conditional_memory`, `sparse_attention`, `rl_from_feedback`). Before writing, verify the filename does not already exist to avoid overwriting.

```bash
mkdir -p ../arxiv/knowledge
ls ./arxiv/knowledge/summary_*.md 2>/dev/null  # check existing summaries
```

#### Summary Structure

```markdown
# {Paper Title}

**Authors:** {authors}
**arXiv:** [{arxiv_id}](https://arxiv.org/abs/{arxiv_id})
**Date:** {publication date}

## Key Idea

{1-2 paragraph summary of the core contribution}

## Method

{Description of the approach, architecture, or algorithm}

## Key Results

{Main experimental findings and comparisons}

## Relevance to This Project

{How the paper's techniques relate to this project and what to try}

## Notable Details

{Interesting implementation details, hyperparameters, or insights worth remembering}
```

#### Project Contextualization

The "Relevance to This Project" section is critical. To write it:
1. Read relevant parts of the current codebase to understand the project's architecture and goals
2. Identify concrete connections between the paper's techniques and the project
3. Suggest specific ideas or experiments inspired by the paper

Ask which aspects to focus on if project context is unclear or too broad.

## Notes

- Always fetch the **TeX source** (`/src/`), never the PDF — LaTeX source is far more readable and token-efficient.
- The `./arxiv/` directory stores downloaded sources locally; the `./arxiv/knowledge/` directory keeps summaries accessible within the project.
- When multiple papers are processed, each gets a unique `summary_{tag}.md` file.
