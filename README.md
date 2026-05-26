<p align="center">
  <img src="assets/logo/logo.png" alt="THOTH Logo" width="220"/>
</p>

<h1 align="center">🏛️ THOTH — Smart Museum Guide Robot</h1>

<p align="center">
  🤖 Autonomous Robot • 🧠 AI Assistant • 🗺 Interactive Museum Navigation • 🌍 Multilingual Experience
  <br/>
  🎓 <em>Graduation Project — Computer Engineering Department</em>
  <br/>
  📄 <a href="https://1drv.ms/p/c/bd8ed2cd16a50bce/IQBYlDNgkJ1pRIw_BMN9P5J8AeVqttAr_z9GDYysugIFq0g?e=kc4d3k">View Graduation Project 1 Final Presentation</a>
</p>

---

> 🏛️ Smart Interactive Museum Guide designed for the Grand Egyptian Museum

---

# 🧠 Overview

**THOTH** is an AI-powered autonomous museum guide robot designed to enhance visitor interaction inside smart museums through intelligent assistance, interactive navigation, multilingual communication, and real-time exhibit exploration.

The system combines:

- 🤖 Robotics & Navigation
- 🧠 Artificial Intelligence & LLMs
- 🖥️ Full-Stack Touchscreen Interface
- 📷 Computer Vision & Recognition
- 🌍 Multilingual Visitor Support

THOTH aims to provide visitors with a futuristic museum experience where they can:

- browse exhibits interactively
- ask questions using voice or text
- navigate museum halls
- receive personalized multilingual explanations
- interact naturally with the robot through an intelligent touchscreen system

---

# ✨ Key Features

## 🖥️ Interactive Touchscreen Web Application

- 🏛️ Museum-themed modern UI
- 📚 Exhibit browsing & filtering
- 🌍 EN / AR / FR multilingual support
- 🗺️ Interactive museum map
- 🤖 AI chatbot interface
- ♿ Accessibility settings
- 📱 Touchscreen-optimized responsive design

---

## 🧠 AI & Voice Interaction

- 🎤 Speech-to-text support
- 🔊 Text-to-speech responses
- 🤖 LLM-powered question answering
- 🌍 Multilingual conversations
- 🧩 Exhibit-aware contextual responses

---

## 📷 Computer Vision

- 👤 Age recognition system
- 😀 Emotion / mood recognition
- 🖼️ Exhibit-aware interaction support
- 🧠 Future visitor analytics support

---

## 🤖 Robotics & Navigation

- 🗺️ Simulated museum navigation
- 📍 Robot localization support
- 🚧 Obstacle avoidance architecture
- 🔌 ROS2-ready integration layer
- ⚡ Future hardware deployment support

---

# 🏗️ System Architecture

```txt
       ┌────────────────────────────┐
       │   🖥 Touchscreen Web App   │
       │ React + TypeScript UI      │
       └─────────────┬──────────────┘
                     │ REST APIs
                     ▼
       ┌────────────────────────────┐
       │     ⚡ FastAPI Backend      │
       │  Business Logic & Services │
       └─────────────┬──────────────┘
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
┌──────────┐   ┌──────────┐   ┌─────────────┐
│ 🧠 LLM   │   │ 🗄️ DB    │   │ 🤖 ROS2     │
│ Gemini   │   │PostgreSQL│   │ Navigation  │
│ Whisper  │   │Exhibits  │   │ Simulation  │
└──────────┘   └──────────┘   └─────────────┘
```

---

# 🔗 ROS 2 — Node & Topic Graph

Runtime communication between the sensing layer, the Nav2 navigation stack,
and the web-app docent stack. Boxes are ROS nodes / process groups; labelled
arrows are ROS topics (publisher → subscriber).

```txt
   ┌──────────────┐                              ┌──────────────┐
   │ LiDAR Driver │                              │   Camera     │
   └──────┬───────┘                              └──────┬───────┘
          │ /scan                                       │ /image_raw
          ▼                                  ┌──────────┴──────────┐
   ┌──────────────────────────┐              ▼                     ▼
   │       Nav2 Stack         │       ┌────────────┐        ┌────────────┐
   │ ┌─────────┐ ┌──────────┐ │       │  Age Node  │        │ Mood Node  │
   │ │  AMCL   │ │MapServer │ │       └──────┬─────┘        └─────┬──────┘
   │ └─────────┘ └──────────┘ │              │ /age               │ /mood
   │ ┌─────────┐ ┌──────────┐ │              ▼                    ▼
   │ │Planner +│ │   BT     │◀┐      ┌────────────────────────────────────┐
   │ │Control  │ │Navigator │ │      │           Docent Stack             │
   │ └─────────┘ └──────────┘ │      │                                    │
   └──────┬───────────────────┘ │    │      ┌──────────────────────┐      │
          │  /cmd_vel           │    │      │   Web App + LLM      │      │
          ▼                     │    │      │ FastAPI · React      │      │
   ┌──────────────┐             │    │      │ Gemini · Whisper     │──┐   │
   │ Serial Node  │             │    │      └──┬───────────────────┘  │   │
   └──────┬───────┘             │    │         ▲                      │   │
          │ serial              │    │         │                      │   │
          ▼                     │    │  ┌──────┴────────┐    ┌────────▼─┐ │
   ┌──────────────┐             │    │  │ Prompt Builder│    │   Tour   │ │
   │ Arduino +    │             │    │  │ age+mood+     │    │Coordinat.│ │
   │ Motors       │             │    │  │ exhibit       │    └──────────┘ │
   └──────────────┘             │    │  └───────▲───────┘                 │
                                │    │          │                         │
              /amcl_pose ───────┘    │  ┌───────┴──────────┐              │
              /goal_pose ────────────┼──┤  Database /      │              │
                                     │  │  Exhibit Loader  │              │
                                     │  └──────────────────┘              │
                                     └────────────────────────────────────┘
```

**Topics actually used by the FastAPI backend (`web-app/backend/app/services/ros_service.py`):**

| Direction | Name | Type | Purpose |
|---|---|---|---|
| Subscribe | `/amcl_pose` | `geometry_msgs/PoseWithCovarianceStamped` | Live robot pose → blue dot on the web map |
| Publish   | `/initialpose` | `geometry_msgs/PoseWithCovarianceStamped` | Bootstraps AMCL so it can produce the `map → odom` transform |
| Action client | `navigate_to_pose` | `nav2_msgs/action/NavigateToPose` | Sends each exhibit/tour goal in the `map` frame |
| Service client | `/lifecycle_manager_{localization,navigation}/manage_nodes` | `nav2_msgs/srv/ManageLifecycleNodes` | Best-effort STARTUP if Nav2 isn't auto-activated |

---

# 🛠️ Technologies Used

| Layer                 | Technologies                          |
| --------------------- | ------------------------------------- |
| **Frontend**          | React, Vite, TypeScript, Tailwind CSS |
| **Backend**           | FastAPI, Python                       |
| **Database**          | PostgreSQL, SQLAlchemy, Alembic       |
| **AI / LLM**          | OpenAI, Gemini, Whisper               |
| **Vision**            | OpenCV, Deep Learning Models          |
| **Simulation**        | ROS2, Gazebo, Nav2                    |
| **Future Deployment** | Docker, AWS                           |

---

# 📂 Repository Structure

```txt
THOTH/
│
├── web-app/           # Full-stack touchscreen web application
│   ├── frontend/      #   React + TypeScript UI
│   └── backend/       #   FastAPI REST API & database layer
│
├── ai-service/        # LLM / STT / TTS integration
├── simulation/        # ROS2 & Gazebo navigation simulation
├── docs/              # Architecture diagrams & documentation
├── assets/            # Logos, screenshots, demo media
└── docker-compose.yml
```

---

# 🚀 Current Features (Grad 1)

## ✅ Implemented / In Progress

- Full-stack touchscreen web application
- Exhibit browsing system
- Multilingual architecture (EN / AR / FR)
- Interactive museum map
- AI chatbot interface
- Backend API architecture
- PostgreSQL database structure
- Simulation-ready architecture
- AI integration preparation

---

# 🖥️ Full-Stack Web Application

The web application acts as the central interaction layer between:

- visitors
- AI systems
- exhibit database
- future ROS2 robot systems

### Main Modules

- 🏠 Home / Welcome Page
- 📚 Exhibit Browsing
- 🖼️ Exhibit Details
- 🗺️ Interactive Museum Map
- 🤖 AI Chatbot
- ⚙️ Accessibility & Settings

---

# 🗄️ Database Features

The database supports:

- 🌍 EN / AR / FR multilingual exhibits
- 🏛️ Exhibit metadata
- 🖼️ Multimedia assets
- 🗺️ Museum hall mapping
- 🤖 Chatbot session history
- 📍 Navigation integration

---

# 🧩 Architecture Principles

- Clean separation:
  ```txt
  models → schemas → routers → services
  ```
- Backend-controlled multilingual responses
- Modular AI integration
- ROS2-ready navigation APIs
- Scalable full-stack architecture
- Future cloud deployment support

---

# 📸 Application Preview

## 🏠 THOTH Home Page

<p align="center">
  <img src="assets/screenshots/THOTH_HomePage.jpg" alt="THOTH Home Page" width="85%"/>
</p>

Modern museum-inspired touchscreen interface designed for smart interactive visitor experiences.

---

## 🖼️ Exhibit Exploration Interface

<p align="center">
  <img src="assets/screenshots/THOTH_Exhibits.jpg" alt="THOTH Exhibits Page" width="85%"/>
</p>

Interactive exhibit browsing system with multilingual support and intelligent navigation-ready architecture.

---

# 🎥 Demo Videos

## 🤖 Ask THOTH — AI Museum Assistant Demo

<p align="center">
  <a href="assets/demo-videos/Web-App/Ask_THOTH_Demo.mp4">
    <img src="https://img.shields.io/badge/▶️-Watch%20Ask%20THOTH%20Demo-blue?style=for-the-badge" />
  </a>
</p>

Demonstration of the THOTH AI assistant handling interactive museum-related conversations inside the touchscreen web application — multilingual voice + text chat, exhibit-aware answers, and TTS playback.

---

## 🗺️ Navigation & Tours — Web App Demo

<p align="center">
  <a href="assets/demo-videos/Web-App/Navigation_Web_Demo.mp4">
    <img src="https://img.shields.io/badge/▶️-Watch%20Navigation%20Demo-goldenrod?style=for-the-badge" />
  </a>
</p>

End-to-end run of the web app driving the simulated robot in Gazebo through Nav2: launching preset tours, building custom multi-stop tours, single-exhibit "Navigate Here", live robot pose on the museum map, and on-arrival narration in the visitor's chosen language.

---

# 👥 Team Members

| Member | Role |
|---|---|
| **[@Mohamed Abdallah Eldairouty](https://github.com/MohamedEldairouty)** — 221001719 | 🌐 Full-Stack Web Application |
| **[@Leena Gouda](https://github.com/leena-gouda)** — 221001794 | 🧠 AI / LLM / Voice Interaction |
| **[@Nayrouz Ahmed](https://github.com/Nayrouzahmed12)** — 221011969 | 😀 Mood Recognition & Image Processing |
| **[@Youssef Waleed](https://github.com/Youssefwaleed2005)** — 221000928 | 👤 Age Recognition & Image Processing |
| **[@Habiba Ghoneim](https://github.com/HabibaGhoneim)** — 221000287 | 🗺️ Simulation & Navigation |
| **[@Saged Khaled](https://github.com/sagedkhaled263)** — 221001150 | 🗺️ Simulation & Navigation |

---

# 🎓 Supervisors

- **Dr. Marwa Elshenawy**
- **Dr. Mohamed El-Habrouk**

Department of Computer Engineering
Arab Academy for Science, Technology & Maritime Transport

---

# 🚀 Future Work

- 🤖 Physical robot deployment
- 📡 Real ROS2 navigation integration
- 🧠 Enhanced conversational AI
- 🖼️ Real exhibit recognition
- ☁️ Cloud deployment
- 📱 Mobile companion application
- 🎯 Personalized museum tours

---

# 📜 License

This project is developed for academic purposes only.
All rights reserved © THOTH Team 2026

---

<p align="center">
  🏛️ <strong>THOTH</strong> — Bringing Museums to Life Through AI & Robotics
</p>
