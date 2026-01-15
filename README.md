# AI-Powered Fantasy Sports Broadcaster (Backend)

A distributed system that automates the generation of "TV-style" sports commentary. This project uses a microservices architecture to scrape real-time game data, generate scripts using **GPT-4**, and synthesize multi-speaker audio using **Azure Neural TTS**.

## Architecture

The system follows a producer-consumer pattern decoupled by a message queue:

1.  **Data Ingestion (Python):** Scrapes fantasy football match-ups and stats, formats them into a JSON payload, and publishes to **RabbitMQ**.
2.  **Message Queue (RabbitMQ):** buffers jobs to ensure scalability and decoupling.
3.  **Processing Service (.NET 8 / C#):**
    * Consumes messages from the queue.
    * **Azure OpenAI (GPT-4):** Generates a dynamic, personality-driven script (Host vs. Color Commentator).
    * **Azure Speech Services:** Synthesizes the script into audio using distinct neural voices ("Matt" and "Jose") with specific emotional tuning.
    * **Output:** Generates broadcast-ready `.wav` files.

## Tech Stack

* **Core Logic:** C# (.NET 8 BackgroundService)
* **Ingestion:** Python 3.x
* **Messaging:** RabbitMQ
* **AI Services:**
    * Azure OpenAI (GPT-4 Turbo)
    * Azure Cognitive Services (Speech SDK / Neural TTS)
* **Logging:** Microsoft.Extensions.Logging

## Project Structure

```text
/Root
│
├── BroadcasterService/       # C# .NET Worker Service
│   ├── Worker.cs             # Main consumer logic & AI orchestration
│   ├── Program.cs            # DI Container & Host setup
│   └── BroadcasterService.csproj
│
├── Scraper/                  # Python Data Ingestion
│   ├── scraper.py            # Fetches data & publishes to RabbitMQ
│   └── requirements.txt      # Python dependencies
│
└── Output/                   # Generated Audio Files (.wav) stored here
