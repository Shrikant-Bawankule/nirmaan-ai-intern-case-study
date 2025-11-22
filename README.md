# Nirmaan AI — Communication Scorer (Case Study)

A Streamlit web application built for the **Nirmaan AI Intern Case Study**, designed to evaluate student self-introductions using a **rubric-based scoring engine** combined with **NLP, semantic similarity, grammar analysis, filler-word detection, sentiment analysis, and vocabulary richness**.

This project provides:
- A clean dark-themed Streamlit UI  
- Automatic analysis of student transcripts  
- Rule-based scoring aligned with the official rubric  
- Optional semantic similarity signals using Sentence Transformers  
- JSON output suitable for downstream automation  
- Quick Stats (word count, characters, sentences, WPM estimation)  
- No hard-coded paths — fully GitHub-friendly

---

## 🚀 Features

### ✔ Rule-based rubric scoring
Implements all 6 official rubric criteria:
1. **Content & Structure**  
2. **Speech Rate**  
3. **Language & Grammar**  
4. **Vocabulary Richness**  
5. **Clarity**  
6. **Engagement**

### ✔ NLP-enhanced scoring
- Grammar analysis (LanguageTool with heuristic fallback)  
- Filler-word frequency detection  
- TTR vocabulary richness  
- Sentiment scoring using VADER  
- Optional semantic similarity (Sentence Transformers)

### ✔ Polished Dark UI
- Modern card-based layout  
- Quick stats for transcript input  
- Interactive table of per-criterion scores  
- Downloadable JSON results  

---

## 📂 Project Structure

