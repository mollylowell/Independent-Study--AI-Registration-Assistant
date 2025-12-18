# Independent Study: AI Registration Assistant

## Overview
This project is an AI-powered course registration assistant developed as part of an independent study at Fairfield University. Built with Python and Streamlit, the application demonstrates how artificial intelligence and analytics can be applied to streamline academic advising and course registration through natural-language interaction.

Students can enter plain-language requests such as:

“I need 15 credits, avoid Friday classes, and finish my language requirement.”

The assistant interprets these requests, converts them into structured academic constraints, and generates conflict-free, degree-aligned schedules that follow institutional rules, prerequisites, and credit requirements. In addition to producing a schedule, the system explains why each course was selected and how it contributes to degree progress, making the registration process more transparent and user-friendly.

---

## Problem Motivation
University course registration is often complex, time-consuming, and unclear for students. Many students struggle to understand how degree requirements, prerequisites, and scheduling constraints interact, leading to suboptimal course choices and advising bottlenecks.

This project explores how AI-driven systems can:
- Reduce friction in the registration process
- Provide personalized, data-driven course recommendations
- Improve transparency in academic decision-making
- Support (not replace) academic advisors with explainable logic

---

## Key Features
- Natural language input that converts everyday language into structured scheduling constraints
- Rule-based scheduling engine modeling credit limits, prerequisites, co-requisites, and time conflicts
- Degree progress tracking across Magis Core, Dolan Core, and program requirements
- Transparent recommendations explaining why specific courses were selected
- Interactive web interface built entirely in Streamlit
- CSV-based course and student history inputs for flexible testing

---

## Technical Stack
- Programming Language: Python
- Framework: Streamlit
- Libraries: Pandas, JSON
- Data Inputs: Course catalogs, degree-requirement schemas, mock student records
- Core Techniques: NLP interpretation, constraint generation, rule-based scheduling logic

---

## Project Structure
app/        → Streamlit application (user interface)  
src/        → Core scheduling logic, rule engines, and parsers  
data/       → Course and section datasets  

---

## How the System Works
1. The user enters scheduling preferences in natural language.
2. The system parses text into structured academic constraints.
3. Degree rules and completed coursework are evaluated.
4. A conflict-free schedule is generated using rule-based logic.
5. The system explains how each course supports degree progress.

---

## How to Run Locally

Clone the repository:
git clone https://github.com/mollylowell/Independent-Study--AI-Registration-Assistant.git  
cd Independent-Study--AI-Registration-Assistant  

Install dependencies:
pip install -r requirements.txt  

Run the application:
streamlit run app/app.py  

The app will open in your browser at:
http://localhost:8501

---

## Example User Prompts
- “15 credits, avoid Friday classes, no classes before 10am”
- “Finish my Magis Core requirements and include my capstone”
- “Prefer Tuesday/Thursday classes and minimize schedule gaps”
- “Build a balanced schedule that satisfies remaining Business Core requirements”

---

## Learning Objectives
This independent study focused on developing practical skills in:
- Applied Artificial Intelligence and natural language processing
- Data modeling and automation of institutional rules
- Analytics-driven decision systems
- User experience design for non-technical users
- Modular, portable software engineering practices

---

## Outcomes
This prototype demonstrates how AI-driven tools can enhance academic operations by simplifying registration workflows, providing personalized recommendations, and improving transparency through explainable logic.

Ultimately, this project illustrates the potential for AI-assisted advising systems to transform university registration into a more intuitive, equitable, and technology-enhanced experience.

---

## Future Enhancements
Potential future extensions include optimization-based scheduling, multi-major support, calendar exports, live deployment, and deeper system integration.

---

## Author
Molly Lowell  
Master of Business Administration (MBA), Business Analytics  
Dolan School of Business, Fairfield University  

Email: mollylowell1@gmail.com  
Email: molly.lowell@student.fairfield.edu

